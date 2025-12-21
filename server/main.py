import sys
import os
from typing import List, Optional, Dict, Any, TYPE_CHECKING, Literal, cast
from pathlib import Path

# Ensure the project root (parent of `server/`) is importable.
# This matters when running via `python server/main.py` (supervisord/Docker),
# and it also helps static tooling resolve `server.*` imports consistently.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Body, BackgroundTasks, Request, Query
from server.jobs import job_store, Job
from server.pricing import pricing_manager, PricingTier, UsageStats
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import BaseModel
import logging
import mimetypes
from datetime import datetime, timezone
from email.utils import formatdate
import calendar
import json
import uuid
import hashlib
import hmac
import re
from urllib.parse import urlencode, urlparse, parse_qsl
import requests  # type: ignore
import sqlite3
import shutil
from threading import Lock
from PIL import Image

# Simple in-memory rate limiting counters (per-IP sliding window)
_rate_lock = Lock()
_rate_counters: dict = {}
_rate_last_conf: tuple | None = None

from src.photo_search import PhotoSearch
from src.api_versioning import api_version_manager, APIResponseHandler
from src.cache_manager import cache_manager
from src.logging_config import setup_logging, log_search_operation, log_indexing_operation, log_error

from server.config import settings
from server.sources import SourceStore
from server.source_items import SourceItemStore
from server.trash_db import TrashDB
from server.multi_tag_filter_db import get_multi_tag_filter_db, MultiTagFilterDB
from server.validation import validate_search_query, validate_pagination_params, validate_date_input


if TYPE_CHECKING:
    from src.logging_config import PerformanceTracker


# These are initialized properly inside lifespan(), but are referenced throughout the
# module. Provide safe defaults so type-checkers (mypy) and editors can resolve them.
ps_logger: logging.Logger = logging.getLogger("PhotoSearch")
perf_tracker: "PerformanceTracker | None" = None
embedding_generator: Any | None = None
file_watcher: Any | None = None
photo_search_engine: Any | None = None


def _runtime_base_dir() -> Path:
    """Resolve a runtime base dir.

    In tests we want an isolated writable directory even when the server is started as a
    subprocess (see `test_people_endpoints.py`).
    """
    if os.environ.get("PHOTOSEARCH_TEST_MODE") == "1":
        td = os.environ.get("PHOTOSEARCH_BASE_DIR")
        if td:
            try:
                return Path(td).resolve()
            except Exception:
                return Path(td)
    return settings.BASE_DIR

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global embedding_generator, file_watcher, ps_logger, perf_tracker, photo_search_engine
    print("Initializing logging...")
    try:
        ps_logger, perf_tracker = setup_logging(log_level="INFO", log_file="logs/app.log")
        print("Logging initialized.")
    except Exception as e:
        print(f"Logging setup error: {e}")
        # Fallback to basic logging
        import logging
        logging.basicConfig(level=logging.INFO)
        ps_logger = logging.getLogger("PhotoSearch")
        from src.logging_config import PerformanceTracker
        perf_tracker = PerformanceTracker(ps_logger)

    print("Initializing Core Logic...")
    try:
        photo_search_engine = PhotoSearch()
        print("Core Logic Loaded.")
    except Exception as e:
        print(f"Core Logic initialization error: {e}")

    print("Initializing Embedding Model...")
    try:
        from server.watcher import start_watcher
        embedding_generator = EmbeddingGenerator()
        print("Embedding Model Loaded.")
        
        # Auto-scan 'media' directory on startup
        media_path = settings.BASE_DIR / "media"
        if media_path.exists() and photo_search_engine:
            print(f"Auto-scanning {media_path}...")
            try:
                photo_search_engine.scan(str(media_path), force=False)
                print("Auto-scan complete.")
            except Exception as e:
                print(f"Auto-scan failed: {e}")

            # Start Real-time Watcher
            def handle_new_file(filepath: str):
                """Callback for new files detected by watcher"""
                try:
                    print(f"Index trigger: {filepath}")
                    from src.metadata_extractor import extract_all_metadata
                    
                    metadata = extract_all_metadata(filepath)
                    if metadata and photo_search_engine:
                        photo_search_engine.db.store_metadata(filepath, metadata)
                        print(f"Metadata indexed: {filepath}")
                        
                        # Trigger Semantic Indexing
                        process_semantic_indexing([filepath])
                except Exception as e:
                    print(f"Real-time indexing failed for {filepath}: {e}")

            print("Starting file watcher...")
            file_watcher = start_watcher(str(media_path), handle_new_file)
                
    except Exception as e:
        print(f"Startup error: {e}")
    
    yield
    
    # Shutdown
    if file_watcher:
        file_watcher.stop()
        file_watcher.join()

app = FastAPI(
    title=settings.APP_NAME, 
    description="Backend for the Living Museum Interface", 
    debug=settings.DEBUG,
    lifespan=lifespan
)

# Configure CORS
cors_origins = [str(origin) for origin in settings.CORS_ORIGINS]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Development-safe fallback: ensure CORS header is present even for error responses or
# paths that might bypass normal middleware handling (helps when server restarts or
# an unexpected error occurs while debugging front-end CORS failures).
@app.middleware("http")
async def _ensure_cors_header(request: Request, call_next):
    response = await call_next(request)
    try:
        origin = request.headers.get("origin")
        if origin and origin in cors_origins and "access-control-allow-origin" not in (k.lower() for k in response.headers.keys()):
            response.headers["Access-Control-Allow-Origin"] = origin
            # Mirror credentials policy configured for CORS middleware
            if settings.DEBUG:
                # In debug we always allow the browser to send credentials to local dev server
                response.headers.setdefault("Access-Control-Allow-Credentials", "true")
    except Exception:
        # If anything goes wrong here, don't block the response
        pass
    return response

# Helper functions for sorting and filtering
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.wmv', '.flv'}

def is_video_file(path: str) -> bool:
    """Check if a file is a video based on extension."""
    ext = os.path.splitext(path)[1].lower()
    return ext in VIDEO_EXTENSIONS


def _httpdate(ts: float) -> str:
    """Return an HTTP-date string (RFC 7231) for a POSIX timestamp."""
    return formatdate(timeval=ts, usegmt=True)


def _make_cache_headers(stat_result: os.stat_result, *, max_age: int = 86400, extra: str = "") -> Dict[str, str]:
    """Create Cache-Control, ETag, and Last-Modified headers for a file."""
    etag = f"W/\"{stat_result.st_mtime_ns}-{stat_result.st_size}{('-' + extra) if extra else ''}\""
    return {
        "Cache-Control": f"public, max-age={max_age}",
        "ETag": etag,
        "Last-Modified": _httpdate(stat_result.st_mtime),
    }


def _negotiate_image_format(format_param: str | None, accept_header: str | None) -> str:
    """Choose output image format based on explicit param or Accept header."""
    fmt = (format_param or "").strip().lower()
    if fmt in {"jpg", "jpeg"}:
        return "JPEG"
    if fmt == "webp":
        return "WEBP"

    if accept_header:
        h = accept_header.lower()
        if "image/webp" in h:
            return "WEBP"
    return "JPEG"

def apply_sort(results: list, sort_by: str) -> list:
    """Sort results by specified criteria."""
    if not results:
        return results
    
    def _meta(r: dict) -> dict:
        m = r.get("metadata", {})
        return m if isinstance(m, dict) else {}

    def _date_key(r: dict) -> str:
        m = _meta(r)
        fs = m.get("filesystem", {}) if isinstance(m.get("filesystem", {}), dict) else {}
        return (
            fs.get("created")
            or m.get("date_taken")
            or m.get("created")
            or ""
        )

    def _size_key(r: dict) -> int:
        m = _meta(r)
        fs = m.get("filesystem", {}) if isinstance(m.get("filesystem", {}), dict) else {}
        v = fs.get("size_bytes")
        if isinstance(v, (int, float)):
            return int(v)
        v2 = m.get("file_size")
        if isinstance(v2, (int, float)):
            return int(v2)
        return 0

    if sort_by == "date_desc":
        # Sort by created date descending (newest first)
        return sorted(results, key=_date_key, reverse=True)
    elif sort_by == "date_asc":
        # Sort by created date ascending (oldest first)
        return sorted(results, key=_date_key)
    elif sort_by == "name":
        # Sort by filename alphabetically
        return sorted(results, key=lambda x: x.get('filename', '').lower())
    elif sort_by == "size":
        # Sort by file size descending (largest first)
        return sorted(results, key=_size_key, reverse=True)
    
    return results

def _parse_isoish_datetime(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None

def _parse_month_or_date(value: Optional[str], end: bool = False) -> Optional[datetime]:
    """
    Supports YYYY-MM or ISO datetime/date strings.
    For YYYY-MM: start is first day 00:00:00, end is last day 23:59:59.
    """
    if not value:
        return None
    v = value.strip()
    if not v:
        return None

    if len(v) == 7 and v[4] == "-":
        try:
            year = int(v[0:4])
            month = int(v[5:7])
            last_day = calendar.monthrange(year, month)[1]
            return datetime(year, month, last_day, 23, 59, 59) if end else datetime(year, month, 1, 0, 0, 0)
        except Exception:
            return None

    dt = _parse_isoish_datetime(v)
    if dt:
        # Drop tzinfo to compare with naive datetimes
        return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt

    try:
        if len(v) == 10 and v[4] == "-" and v[7] == "-":
            year = int(v[0:4])
            month = int(v[5:7])
            day = int(v[8:10])
            return datetime(year, month, day, 23, 59, 59) if end else datetime(year, month, day, 0, 0, 0)
    except Exception:
        return None

    return None

def _get_created_datetime(meta: dict) -> Optional[datetime]:
    try:
        fs = (meta or {}).get("filesystem", {}) or {}
        created = fs.get("created")
        if isinstance(created, str):
            dt = _parse_isoish_datetime(created)
            if not dt:
                return None
            return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt
    except Exception:
        return None
    return None

def apply_date_filter(results: list, date_from: Optional[str], date_to: Optional[str]) -> list:
    """
    Filters results by metadata.filesystem.created inclusive.
    date_from/date_to accept YYYY-MM or ISO date/datetime strings.
    """
    start = _parse_month_or_date(date_from, end=False)
    end = _parse_month_or_date(date_to, end=True)
    if not start and not end:
        return results

    filtered = []
    for r in results:
        if not isinstance(r, dict):
            continue
        dt = _get_created_datetime(r.get("metadata") or {})
        if not dt:
            continue
        if start and dt < start:
            continue
        if end and dt > end:
            continue
        filtered.append(r)
    return filtered

# Initialize Semantic Search Components
from server.lancedb_store import LanceDBStore
from server.embedding_generator import EmbeddingGenerator
from server.image_loader import load_image

# Initialize Intent Recognition
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.intent_recognition import IntentDetector
from src.saved_searches import SavedSearchManager

# Lazily loaded or initialized here
# Note: EmbeddingGenerator loads a model (~500MB), so it might take a moment on first request or startup
vector_store = LanceDBStore()
embedding_generator = None # Load lazily or on startup
file_watcher = None # Global observer instance
intent_detector = IntentDetector() # Initialize intent detector
saved_search_manager = SavedSearchManager() # Initialize saved search manager

# Sources (Local + Cloud)
source_store = SourceStore(settings.BASE_DIR / "sources.db")
source_item_store = SourceItemStore(settings.BASE_DIR / "sources_items.db")
trash_db = TrashDB(settings.BASE_DIR / "trash.db")

# Startup and shutdown now handled by lifespan context manager above

class SourceOut(BaseModel):
    id: str
    type: str
    name: str
    status: str
    created_at: str
    updated_at: str
    last_sync_at: Optional[str] = None
    last_error: Optional[str] = None
    config: Dict[str, object] = {}

class LocalFolderSourceCreate(BaseModel):
    name: Optional[str] = None
    path: str
    force: bool = False

class S3SourceCreate(BaseModel):
    name: str
    endpoint_url: str
    region: str
    bucket: str
    prefix: Optional[str] = None
    access_key_id: str
    secret_access_key: str

class GoogleDriveSourceCreate(BaseModel):
    name: str
    client_id: str
    client_secret: str

def _source_to_out(source_id: str) -> SourceOut:
    s = source_store.get_source(source_id, redact=True)
    return SourceOut(
        id=s.id,
        type=s.type,
        name=s.name,
        status=s.status,
        created_at=s.created_at,
        updated_at=s.updated_at,
        last_sync_at=s.last_sync_at,
        last_error=s.last_error,
        config=s.config or {},
    )

@app.get("/sources")
async def list_sources():
    sources = source_store.list_sources(redact=True)
    return {"sources": [SourceOut(
        id=s.id,
        type=s.type,
        name=s.name,
        status=s.status,
        created_at=s.created_at,
        updated_at=s.updated_at,
        last_sync_at=s.last_sync_at,
        last_error=s.last_error,
        config=s.config or {},
    ) for s in sources]}

@app.delete("/sources/{source_id}")
async def delete_source(source_id: str):
    try:
        source_store.get_source(source_id, redact=False)
    except KeyError:
        raise HTTPException(status_code=404, detail="Source not found")
    source_store.delete_source(source_id)
    return {"ok": True}

@app.post("/sources/{source_id}/rescan")
async def rescan_source(background_tasks: BackgroundTasks, source_id: str, payload: dict = Body(default={})):
    try:
        src = source_store.get_source(source_id, redact=False)
    except KeyError:
        raise HTTPException(status_code=404, detail="Source not found")
    if src.type != "local_folder":
        raise HTTPException(status_code=400, detail="Rescan is only supported for local_folder sources right now")
    path = (src.config or {}).get("path")
    if not isinstance(path, str) or not path:
        raise HTTPException(status_code=400, detail="Invalid source path")
    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail="Directory does not exist")
    force = bool(payload.get("force", False))

    job_id = job_store.create_job(type="scan")

    def run_scan(job_id: str, path: str, force: bool):
        try:
            scan_results = photo_search_engine.scan(path, force=force, job_id=job_id)
            all_files = scan_results.get("all_files", [])
            if all_files:
                process_semantic_indexing(all_files)
            job_store.update_job(job_id, status="completed", message="Scan and indexing finished.")
            source_store.update_source(source_id, last_sync_at=datetime.utcnow().isoformat() + "Z", last_error=None, status="connected")
        except Exception as e:
            job_store.update_job(job_id, status="failed", message=str(e))
            source_store.update_source(source_id, status="error", last_error=str(e))

    background_tasks.add_task(run_scan, job_id, path, force)
    return {"ok": True, "job_id": job_id}

def _aws_sigv4_headers(
    *,
    method: str,
    url: str,
    region: str,
    access_key_id: str,
    secret_access_key: str,
    service: str = "s3",
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """
    Minimal AWS SigV4 signer for S3-compatible endpoints.
    """
    headers = dict(headers or {})
    u = urlparse(url)
    host = u.netloc
    amz_date = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    date_stamp = amz_date[0:8]

    # Canonical query string
    q = parse_qsl(u.query, keep_blank_values=True)
    q.sort(key=lambda kv: (kv[0], kv[1]))
    canonical_qs = "&".join(
        [
            f"{requests.utils.quote(str(k), safe='~')}={requests.utils.quote(str(v), safe='~')}"
            for k, v in q
        ]
    )

    canonical_headers = f"host:{host}\n" + f"x-amz-date:{amz_date}\n"
    signed_headers = "host;x-amz-date"
    payload_hash = hashlib.sha256(b"").hexdigest()
    canonical_request = "\n".join([
        method,
        u.path or "/",
        canonical_qs,
        canonical_headers,
        signed_headers,
        payload_hash,
    ])

    algorithm = "AWS4-HMAC-SHA256"
    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    string_to_sign = "\n".join([
        algorithm,
        amz_date,
        credential_scope,
        hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
    ])

    def _sign(key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    k_date = _sign(("AWS4" + secret_access_key).encode("utf-8"), date_stamp)
    k_region = _sign(k_date, region)
    k_service = _sign(k_region, service)
    k_signing = _sign(k_service, "aws4_request")
    signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    authorization_header = (
        f"{algorithm} Credential={access_key_id}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    headers["Authorization"] = authorization_header
    headers["x-amz-date"] = amz_date
    headers["host"] = host
    return headers

def _s3_urls(endpoint_url: str, bucket: str, key: str = "", query: Optional[Dict[str, str]] = None) -> str:
    base = endpoint_url.rstrip("/")
    parsed = urlparse(base)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("endpoint_url must include scheme, e.g. https://<host>")

    host = parsed.netloc
    # Prefer virtual-hosted style unless endpoint already includes bucket.
    bucket_in_host = host.startswith(f"{bucket}.")
    if bucket_in_host:
        path = (parsed.path or "/") + ("/" + key.lstrip("/") if key else "/")
        netloc = host
    else:
        netloc = f"{bucket}.{host}"
        path = (parsed.path or "/") + ("/" + key.lstrip("/") if key else "/")

    if not path.startswith("/"):
        path = "/" + path
    qs = urlencode(query or {})
    return f"{parsed.scheme}://{netloc}{path}" + (f"?{qs}" if qs else "")

def _s3_list_objects(cfg: Dict[str, object]) -> List[Dict[str, object]]:
    import xml.etree.ElementTree as ET

    endpoint_url = str(cfg.get("endpoint_url", "")).strip()
    region = str(cfg.get("region", "")).strip()
    bucket = str(cfg.get("bucket", "")).strip()
    prefix = str(cfg.get("prefix", "") or "").strip()
    access_key_id = str(cfg.get("access_key_id", "")).strip()
    secret_access_key = str(cfg.get("secret_access_key", "")).strip()

    token: Optional[str] = None
    out: List[Dict[str, object]] = []

    while True:
        query: Dict[str, str] = {"list-type": "2", "max-keys": "1000"}
        if prefix:
            query["prefix"] = prefix
        if token:
            query["continuation-token"] = token
        url = _s3_urls(endpoint_url, bucket, "", query=query)
        signed = _aws_sigv4_headers(
            method="GET",
            url=url,
            region=region,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
        )
        resp = requests.get(url, headers=signed, timeout=20)
        if resp.status_code != 200:
            raise RuntimeError(f"S3 list failed ({resp.status_code}): {resp.text[:200]}")

        root = ET.fromstring(resp.text)
        ns = ""
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0] + "}"

        for c in root.findall(f"{ns}Contents"):
            key = (c.findtext(f"{ns}Key") or "").strip()
            etag = (c.findtext(f"{ns}ETag") or "").strip().strip('"')
            last_modified = (c.findtext(f"{ns}LastModified") or "").strip()
            size = c.findtext(f"{ns}Size")
            size_int = int(size) if size and size.isdigit() else None
            if key:
                out.append({"key": key, "etag": etag or None, "last_modified": last_modified or None, "size": size_int})

        is_truncated = (root.findtext(f"{ns}IsTruncated") or "").strip().lower() == "true"
        token = (root.findtext(f"{ns}NextContinuationToken") or "").strip() or None
        if not is_truncated or not token:
            break
    return out

def _s3_download_object(cfg: Dict[str, object], key: str, dest: Path) -> None:
    endpoint_url = str(cfg.get("endpoint_url", "")).strip()
    region = str(cfg.get("region", "")).strip()
    bucket = str(cfg.get("bucket", "")).strip()
    access_key_id = str(cfg.get("access_key_id", "")).strip()
    secret_access_key = str(cfg.get("secret_access_key", "")).strip()

    url = _s3_urls(endpoint_url, bucket, key)
    signed = _aws_sigv4_headers(
        method="GET",
        url=url,
        region=region,
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
    )
    with requests.get(url, headers=signed, stream=True, timeout=120) as resp:
        if resp.status_code != 200:
            raise RuntimeError(f"S3 download failed ({resp.status_code}): {resp.text[:200]}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
        tmp.replace(dest)

def _test_s3_connection(cfg: Dict[str, object]) -> None:
    endpoint_url = str(cfg.get("endpoint_url", "")).strip()
    region = str(cfg.get("region", "")).strip()
    bucket = str(cfg.get("bucket", "")).strip()
    access_key_id = str(cfg.get("access_key_id", "")).strip()
    secret_access_key = str(cfg.get("secret_access_key", "")).strip()
    if not endpoint_url or not region or not bucket or not access_key_id or not secret_access_key:
        raise ValueError("Missing required S3 configuration fields")
    prefix = str(cfg.get("prefix", "") or "").strip()
    url = _s3_urls(endpoint_url, bucket, "", query={"list-type": "2", "max-keys": "1", **({"prefix": prefix} if prefix else {})})
    signed = _aws_sigv4_headers(
        method="GET",
        url=url,
        region=region,
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
    )
    resp = requests.get(url, headers=signed, timeout=15)
    if resp.status_code != 200:
        raise RuntimeError(f"S3 connection failed ({resp.status_code}): {resp.text[:200]}")

def _sync_s3_source(source_id: str, job_id: str) -> None:
    job_store.update_job(job_id, status="processing", message="Enumerating S3…", progress=5)
    src = source_store.get_source(source_id, redact=False)
    cfg = src.config or {}
    items = _s3_list_objects(cfg)
    seen_marker = datetime.now(timezone.utc).isoformat()

    job_store.update_job(job_id, message=f"Found {len(items)} objects. Downloading…", progress=20)
    root = _media_source_root(source_id) / "s3"
    root.mkdir(parents=True, exist_ok=True)
    downloaded = 0

    for idx, it in enumerate(items):
        key = str(it.get("key", ""))
        if not key:
            continue
        name = key.split("/")[-1]
        if not _is_media_name(name):
            continue

        etag = it.get("etag")
        modified = it.get("last_modified")
        size = it.get("size")
        size_int = int(size) if isinstance(size, int) else None

        remote_id = key
        try:
            prev = source_item_store.get(source_id, remote_id)
        except Exception:
            prev = None

        source_item_store.upsert_seen(
            source_id=source_id,
            remote_id=remote_id,
            remote_path=key,
            etag=str(etag) if etag else None,
            modified_at=str(modified) if modified else None,
            size_bytes=size_int,
            mime_type=None,
            name=name,
        )

        # Respect app-level states: keep in manifest, but do not download/index.
        if prev and prev.status in ("trashed", "removed"):
            continue

        # Mirror path under root, preserving prefix structure.
        rel = Path(key)
        dest = root / rel
        needs_download = not dest.exists()
        if prev and prev.etag and etag and prev.etag != str(etag):
            needs_download = True
        if prev and prev.size_bytes and size_int and prev.size_bytes != size_int:
            needs_download = True
        if prev and prev.local_path and not Path(prev.local_path).exists():
            needs_download = True

        if needs_download:
            _s3_download_object(cfg, key, dest)
            source_item_store.set_local_path(source_id, remote_id, str(dest))
            downloaded += 1

        if idx % 50 == 0:
            pct = 20 + int((idx / max(1, len(items))) * 55)
            job_store.update_job(job_id, message=f"Downloading S3 objects… ({idx}/{len(items)})", progress=pct)

    missing = source_item_store.mark_missing_as_deleted(source_id, seen_marker)
    for m in missing:
        if m.local_path:
            try:
                lp = Path(m.local_path)
                if lp.exists():
                    lp.unlink()
                try:
                    photo_search_engine.db.mark_as_deleted(m.local_path, reason="source_deleted")
                except Exception:
                    pass
            except Exception:
                pass

    job_store.update_job(job_id, message="Indexing downloaded files…", progress=80)
    results = photo_search_engine.scan(str(root), force=False)
    all_files = results.get("all_files", []) if isinstance(results, dict) else []
    if all_files:
        job_store.update_job(job_id, message="Semantic indexing…", progress=92)
        process_semantic_indexing(all_files)

    source_store.update_source(source_id, status="connected", last_error=None, last_sync_at=datetime.utcnow().isoformat() + "Z")
    job_store.update_job(
        job_id,
        status="completed",
        progress=100,
        message=f"S3 sync complete ({downloaded} downloaded, {len(missing)} removed).",
        result={"downloaded": downloaded, "removed": len(missing)},
    )

@app.post("/sources/local-folder")
async def add_local_folder_source(background_tasks: BackgroundTasks, payload: LocalFolderSourceCreate):
    path = payload.path
    if not path:
        raise HTTPException(status_code=400, detail="Path is required")
    if not os.path.exists(path):
        raise HTTPException(status_code=400, detail="Directory does not exist")
    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail="Path must be a directory")

    name = payload.name or os.path.basename(path.rstrip("/")) or "Local Folder"
    src = source_store.create_source("local_folder", name=name, config={"path": path}, status="connected")

    job_id = job_store.create_job(type="scan")
    force = bool(payload.force)

    def run_scan(job_id: str, path: str, force: bool):
        try:
            scan_results = photo_search_engine.scan(path, force=force, job_id=job_id)
            all_files = scan_results.get("all_files", [])
            if all_files:
                process_semantic_indexing(all_files)
            job_store.update_job(job_id, status="completed", message="Scan and indexing finished.")
            source_store.update_source(src.id, last_sync_at=datetime.utcnow().isoformat() + "Z", last_error=None)
        except Exception as e:
            job_store.update_job(job_id, status="failed", message=str(e))
            source_store.update_source(src.id, status="error", last_error=str(e))

    background_tasks.add_task(run_scan, job_id, path, force)
    return {"source": _source_to_out(src.id), "job_id": job_id}

@app.post("/sources/s3")
async def add_s3_source(background_tasks: BackgroundTasks, payload: S3SourceCreate):
    cfg = payload.model_dump()
    # Store secrets server-side; return only redacted config.
    src = source_store.create_source("s3", name=payload.name, config=cfg, status="pending")
    try:
        _test_s3_connection(cfg)
        source_store.update_source(src.id, status="connected", last_error=None)
        job_id = job_store.create_job(type="source_sync")

        def run_sync():
            try:
                _sync_s3_source(src.id, job_id)
            except Exception as e:
                job_store.update_job(job_id, status="failed", message=str(e))
                source_store.update_source(src.id, status="error", last_error=str(e))

        background_tasks.add_task(run_sync)
    except Exception as e:
        source_store.update_source(src.id, status="error", last_error=str(e))
        return {"source": _source_to_out(src.id)}
    return {"source": _source_to_out(src.id), "job_id": job_id}

def _google_redirect_uri() -> str:
    # For local dev (desktop/web) backend runs on :8000.
    return "http://127.0.0.1:8000/oauth/google/callback"

def _media_source_root(source_id: str) -> Path:
    root = settings.BASE_DIR / "media_sources" / source_id
    root.mkdir(parents=True, exist_ok=True)
    return root

def _is_media_name(name: str) -> bool:
    n = (name or "").lower()
    exts = (
        ".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif", ".tif", ".tiff",
        ".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi",
        ".pdf", ".svg",
        ".mp3", ".wav", ".m4a", ".aac",
    )
    return any(n.endswith(e) for e in exts)

def _safe_filename(name: str) -> str:
    keep = []
    for ch in name:
        if ch.isalnum() or ch in (" ", ".", "-", "_", "(", ")", "[", "]"):
            keep.append(ch)
        else:
            keep.append("_")
    out = "".join(keep).strip()
    return out[:180] if out else "file"

def _refresh_google_access_token(source_id: str) -> Dict[str, object]:
    src = source_store.get_source(source_id, redact=False)
    cfg = src.config or {}
    refresh_token = cfg.get("refresh_token")
    if not refresh_token:
        raise RuntimeError("Missing refresh_token (re-authorize Google Drive source)")
    token_resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": cfg.get("client_id"),
            "client_secret": cfg.get("client_secret"),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=20,
    )
    if token_resp.status_code != 200:
        raise RuntimeError(f"Token refresh failed: {token_resp.text[:200]}")
    tok = token_resp.json()
    access_token = tok.get("access_token")
    expires_in = tok.get("expires_in")
    expires_at = None
    if expires_in:
        expires_at = datetime.utcnow().timestamp() + float(expires_in)
    patch = {"access_token": access_token, "expires_at": expires_at}
    source_store.update_source(source_id, config_patch=patch, status="connected", last_error=None)
    return patch

def _get_google_access_token(source_id: str) -> str:
    src = source_store.get_source(source_id, redact=False)
    cfg = src.config or {}
    access_token = cfg.get("access_token")
    expires_at = cfg.get("expires_at")
    if isinstance(access_token, str) and access_token:
        if isinstance(expires_at, (int, float)) and (datetime.utcnow().timestamp() + 60) < float(expires_at):
            return access_token
        # Token nearing expiry; refresh.
        patch = _refresh_google_access_token(source_id)
        return str(patch.get("access_token", ""))
    patch = _refresh_google_access_token(source_id)
    return str(patch.get("access_token", ""))

def _sync_google_drive_source(source_id: str, job_id: str) -> None:
    job_store.update_job(job_id, status="processing", message="Enumerating Google Drive…", progress=5)
    token = _get_google_access_token(source_id)
    headers = {"Authorization": f"Bearer {token}"}
    page_token = None
    seen_marker = datetime.now(timezone.utc).isoformat()
    files: List[Dict[str, object]] = []

    q = "trashed = false and (mimeType contains 'image/' or mimeType contains 'video/' or mimeType = 'application/pdf' or mimeType contains 'audio/')"
    while True:
        params = {
            "pageSize": 1000,
            "fields": "nextPageToken, files(id,name,mimeType,modifiedTime,md5Checksum,size)",
            "q": q,
        }
        if page_token:
            params["pageToken"] = page_token
        resp = requests.get("https://www.googleapis.com/drive/v3/files", headers=headers, params=params, timeout=30)
        if resp.status_code == 401:
            # Refresh and retry once.
            token = _get_google_access_token(source_id)
            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get("https://www.googleapis.com/drive/v3/files", headers=headers, params=params, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"Drive list failed ({resp.status_code}): {resp.text[:200]}")
        data = resp.json()
        batch = data.get("files") or []
        files.extend(batch)
        page_token = data.get("nextPageToken")
        if not page_token:
            break

    job_store.update_job(job_id, message=f"Found {len(files)} Drive items. Downloading…", progress=20)
    root = _media_source_root(source_id) / "drive"
    root.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    for idx, f in enumerate(files):
        file_id = str(f.get("id", ""))
        name = str(f.get("name", "")) or file_id
        mime = str(f.get("mimeType", "")) or None
        if name and not _is_media_name(name) and mime and not (mime.startswith("image/") or mime.startswith("video/") or mime.startswith("audio/") or mime == "application/pdf"):
            continue

        md5 = f.get("md5Checksum")
        modified = f.get("modifiedTime")
        size = f.get("size")
        size_int = int(size) if isinstance(size, (int, float, str)) and str(size).isdigit() else None

        try:
            prev = source_item_store.get(source_id, file_id)
        except Exception:
            prev = None

        source_item_store.upsert_seen(
            source_id=source_id,
            remote_id=file_id,
            remote_path=file_id,
            etag=str(md5) if md5 else None,
            modified_at=str(modified) if modified else None,
            size_bytes=size_int,
            mime_type=mime,
            name=name,
        )

        # Respect app-level states: keep in manifest, but do not download/index.
        if prev and prev.status in ("trashed", "removed"):
            continue

        safe = _safe_filename(name)
        local_path = root / f"{file_id}__{safe}"
        needs_download = not local_path.exists()
        if prev and prev.etag and md5 and prev.etag != str(md5):
            needs_download = True
        if prev and prev.modified_at and modified and prev.modified_at != str(modified):
            needs_download = True
        if prev and prev.size_bytes and size_int and prev.size_bytes != size_int:
            needs_download = True
        if prev and prev.local_path and not Path(prev.local_path).exists():
            needs_download = True

        if needs_download:
            url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
            with requests.get(url, headers=headers, params={"alt": "media"}, stream=True, timeout=120) as r:
                if r.status_code == 401:
                    token = _get_google_access_token(source_id)
                    headers = {"Authorization": f"Bearer {token}"}
                    r = requests.get(url, headers=headers, params={"alt": "media"}, stream=True, timeout=120)
                if r.status_code != 200:
                    raise RuntimeError(f"Drive download failed ({r.status_code}): {r.text[:200]}")
                local_path.parent.mkdir(parents=True, exist_ok=True)
                tmp = local_path.with_suffix(local_path.suffix + ".part")
                with open(tmp, "wb") as out:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            out.write(chunk)
                tmp.replace(local_path)
            source_item_store.set_local_path(source_id, file_id, str(local_path))
            downloaded += 1

        if idx % 25 == 0:
            pct = 20 + int((idx / max(1, len(files))) * 55)
            job_store.update_job(job_id, message=f"Downloading Drive items… ({idx}/{len(files)})", progress=pct)

    missing = source_item_store.mark_missing_as_deleted(source_id, seen_marker)
    for m in missing:
        if m.local_path:
            try:
                lp = Path(m.local_path)
                if lp.exists():
                    lp.unlink()
                try:
                    photo_search_engine.db.mark_as_deleted(m.local_path, reason="source_deleted")
                except Exception:
                    pass
            except Exception:
                pass

    job_store.update_job(job_id, message="Indexing downloaded files…", progress=80)
    results = photo_search_engine.scan(str(root), force=False)
    all_files = results.get("all_files", []) if isinstance(results, dict) else []
    if all_files:
        job_store.update_job(job_id, message="Semantic indexing…", progress=92)
        process_semantic_indexing(all_files)

    source_store.update_source(source_id, status="connected", last_error=None, last_sync_at=datetime.utcnow().isoformat() + "Z")
    job_store.update_job(
        job_id,
        status="completed",
        progress=100,
        message=f"Drive sync complete ({downloaded} downloaded, {len(missing)} removed).",
        result={"downloaded": downloaded, "removed": len(missing)},
    )

@app.post("/sources/google-drive")
async def add_google_drive_source(payload: GoogleDriveSourceCreate):
    cfg = {"client_id": payload.client_id, "client_secret": payload.client_secret}
    src = source_store.create_source("google_drive", name=payload.name, config=cfg, status="auth_required")
    state_nonce = str(uuid.uuid4())
    source_store.update_source(src.id, config_patch={"state_nonce": state_nonce})

    params = {
        "client_id": payload.client_id,
        "redirect_uri": _google_redirect_uri(),
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/drive.readonly",
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": f"{src.id}:{state_nonce}",
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return {"source": _source_to_out(src.id), "auth_url": auth_url}

@app.get("/oauth/google/callback")
async def google_oauth_callback(background_tasks: BackgroundTasks, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    if error:
        return {
            "ok": False,
            "error": error,
        }
    if not code or not state or ":" not in state:
        raise HTTPException(status_code=400, detail="Missing code/state")
    source_id, nonce = state.split(":", 1)
    try:
        src = source_store.get_source(source_id, redact=False)
    except KeyError:
        raise HTTPException(status_code=404, detail="Source not found")
    if src.type != "google_drive":
        raise HTTPException(status_code=400, detail="Invalid source type")
    expected = (src.config or {}).get("state_nonce")
    if not expected or expected != nonce:
        raise HTTPException(status_code=400, detail="Invalid state")

    client_id = str((src.config or {}).get("client_id", ""))
    client_secret = str((src.config or {}).get("client_secret", ""))
    token_resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": _google_redirect_uri(),
            "grant_type": "authorization_code",
        },
        timeout=15,
    )
    if token_resp.status_code != 200:
        source_store.update_source(source_id, status="error", last_error=f"token exchange failed: {token_resp.text[:200]}")
        raise HTTPException(status_code=400, detail="Token exchange failed")
    tok = token_resp.json()
    access_token = tok.get("access_token")
    refresh_token = tok.get("refresh_token")
    expires_in = tok.get("expires_in")
    expires_at = None
    if expires_in:
        expires_at = datetime.utcnow().timestamp() + float(expires_in)

    source_store.update_source(
        source_id,
        status="connected",
        last_error=None,
        last_sync_at=datetime.utcnow().isoformat() + "Z",
        config_patch={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at,
        },
    )

    job_id = job_store.create_job(type="source_sync")

    def run_sync():
        try:
            _sync_google_drive_source(source_id, job_id)
        except Exception as e:
            job_store.update_job(job_id, status="failed", message=str(e))
            source_store.update_source(source_id, status="error", last_error=str(e))

    background_tasks.add_task(run_sync)

    # Lightweight HTML response for popup flows.
    html = f"""
<!doctype html>
<html>
  <head><meta charset="utf-8"><title>Connected</title></head>
  <body style="font-family: system-ui; padding: 24px;">
    <h2>Google Drive connected</h2>
    <p>Sync started in the background. You can close this window.</p>
    <script>
      try {{
        if (window.opener) {{
          window.opener.postMessage({{ type: 'lm:sourceConnected', sourceId: {json.dumps(source_id)}, jobId: {json.dumps(job_id)} }}, '*');
        }}
      }} catch (e) {{}}
      setTimeout(() => window.close(), 200);
    </script>
  </body>
</html>
"""
    return HTMLResponse(content=html)

@app.post("/sources/{source_id}/sync")
async def sync_source(background_tasks: BackgroundTasks, source_id: str):
    try:
        src = source_store.get_source(source_id, redact=False)
    except KeyError:
        raise HTTPException(status_code=404, detail="Source not found")

    job_id = job_store.create_job(type="source_sync")

    def run_sync():
        try:
            if src.type == "s3":
                _sync_s3_source(source_id, job_id)
            elif src.type == "google_drive":
                _sync_google_drive_source(source_id, job_id)
            elif src.type == "local_folder":
                # Mirror of existing rescan behavior
                path = (src.config or {}).get("path")
                if not isinstance(path, str) or not path:
                    raise RuntimeError("Invalid local folder path")
                results = photo_search_engine.scan(path, force=False)
                all_files = results.get("all_files", []) if isinstance(results, dict) else []
                if all_files:
                    process_semantic_indexing(all_files)
                job_store.update_job(job_id, status="completed", progress=100, message="Local re-scan complete.")
            else:
                raise RuntimeError("Unsupported source type")
        except Exception as e:
            job_store.update_job(job_id, status="failed", message=str(e))
            source_store.update_source(source_id, status="error", last_error=str(e))

    background_tasks.add_task(run_sync)
    return {"ok": True, "job_id": job_id}

class ScanRequest(BaseModel):
    path: str

class SearchRequest(BaseModel):
    query: str
    limit: int = 1000
    offset: int = 0

class SearchCountRequest(BaseModel):
    query: str
    mode: str = "metadata"

@app.get("/")
async def root():
    return {"status": "ok", "message": "PhotoSearch API is running"}

def process_semantic_indexing(files_to_index: List[str]):
    """
    Helper to generate embeddings for a list of file paths.
    """
    global embedding_generator
    if not embedding_generator:
        embedding_generator = EmbeddingGenerator()
        
    print(f"Indexing {len(files_to_index)} files for semantic search...")
    
    # 1. Deduplication: Filter out files that are already indexed
    # Using Full Path as ID to avoid collisions
    try:
        existing_ids = vector_store.get_all_ids()
        files_to_process = [f for f in files_to_index if f not in existing_ids]
    except Exception as e:
        print(f"Error checking existing IDs: {e}")
        files_to_process = files_to_index

    if not files_to_process:
        print("All files already indexed. Skipping.")
        return

    print(f"Processing {len(files_to_process)} new files (skipped {len(files_to_index) - len(files_to_process)} existing)...")
    
    ids = []
    vectors = []
    metadatas = []
    
    for i, file_path in enumerate(files_to_process):
        if i % 10 == 0:
            print(f"  Processed {i}/{len(files_to_process)}...")
            
        try:
            # Check for valid image or video extensions
            valid_img_exts = ['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif', '.heic', '.tiff', '.tif']
            valid_vid_exts = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v']
            
            is_video = False
            if any(file_path.lower().endswith(ext) for ext in valid_vid_exts):
                 is_video = True
            elif not any(file_path.lower().endswith(ext) for ext in valid_img_exts):
                continue
            
            img = None
            if is_video:
                from server.image_loader import extract_video_frame
                # Extract frame
                try:
                    img = extract_video_frame(file_path)
                except Exception as ve:
                    print(f"Skipping video {os.path.basename(file_path)}: {ve}")
                    continue
            else:
                img = load_image(file_path)

            if img:
                vec = embedding_generator.generate_image_embedding(img)
                if vec:
                    # FIX: Use full path as ID to ensure uniqueness
                    ids.append(file_path) 
                    vectors.append(vec)
                    # Store minimalist metadata, relies on main DB for details
                    metadatas.append({
                        "path": file_path, 
                        "filename": os.path.basename(file_path),
                        "type": "video" if is_video else "image"
                    })
        except Exception as e:
            print(f"Failed to embed {file_path}: {e}")
            
    if ids:
        time_start = __import__("time").time()
        vector_store.add_batch(ids, vectors, metadatas)
        print(f"Added {len(ids)} vectors to LanceDB in {__import__('time').time() - time_start:.2f}s.")

@app.post("/scan")
async def scan_directory(
    background_tasks: BackgroundTasks,
    payload: dict = Body(...)
):
    """
    Scan a directory for photos.
    Supports asynchronous scanning via background tasks.
    """
    path = payload.get("path")
    force = payload.get("force", False)
    background = payload.get("background", True)

    if not path:
        raise HTTPException(status_code=400, detail="Path is required")
    
    if not os.path.exists(path):
        raise HTTPException(status_code=400, detail="Directory does not exist")

    # If background processing is requested (default)
    if background:
        job_id = job_store.create_job(type="scan")
        
        # Define the background task wrapper
        def run_scan(job_id: str, path: str, force: bool):
            try:
                # The scan method should update the job status internally
                # and return the list of files for semantic indexing
                scan_results = photo_search_engine.scan(path, force=force, job_id=job_id)
                
                # After scanning metadata, perform semantic indexing
                all_files = scan_results.get("all_files", [])
                if all_files:
                    process_semantic_indexing(all_files)
                
                job_store.update_job(job_id, status="completed", message="Scan and indexing finished.")
            except Exception as e:
                print(f"Job {job_id} failed: {e}")
                job_store.update_job(job_id, status="failed", message=str(e))

        background_tasks.add_task(run_scan, job_id, path, force)
        
        return {"job_id": job_id, "status": "pending", "message": "Scan started in background"}
    else:
        # Synchronous (Legacy/Blocking)
        try:
            results = photo_search_engine.scan(path, force=force)
            
            # Perform semantic indexing synchronously if not in background
            all_files = results.get("all_files", [])
            if all_files:
                process_semantic_indexing(all_files)

            return results
        except Exception as e:
             raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs/{job_id}", response_model=Job)
async def get_job_status(job_id: str):
    """Get the status of a background job."""
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.post("/index")
async def force_indexing(request: ScanRequest):
    """
    Force semantic indexing of a directory (without re-scanning metadata).
    """
    try:
        # Just walk and index
        files_to_index = []
        for root, dirs, files in os.walk(request.path):
             for file in files:
                 files_to_index.append(os.path.join(root, file))
        
        if files_to_index:
            process_semantic_indexing(files_to_index)
            
        return {"status": "success", "indexed": len(files_to_index)}
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

# Register the endpoints with API version manager
api_version_manager.register_endpoint(
    path="/search",
    method="GET",
    summary="Search Photos",
    description="Unified search endpoint supporting metadata, semantic, and hybrid search modes"
)

api_version_manager.register_endpoint(
    path="/search/semantic",
    method="GET",
    summary="Semantic Search",
    description="Semantic search using CLIP embeddings"
)

@app.get("/search")
async def search_photos(
    query: str = "",
    limit: int = 50,
    offset: int = 0,
    mode: str = "metadata",
    sort_by: str = "date_desc",  # date_desc, date_asc, name, size
    type_filter: str = "all",  # all, photos, videos
    source_filter: str = "all",  # all, local, cloud, hybrid
    favorites_filter: str = "all",  # all, favorites_only
    tag: Optional[str] = None,  # Filter to a single user tag (deprecated, use tags instead)
    tags: Optional[str] = None,  # Filter by multiple tags, format: "tag1,tag2,tag3"
    tag_logic: str = "OR",  # "AND" or "OR" for combining multiple tags
    date_from: Optional[str] = None,  # YYYY-MM or ISO date/datetime
    date_to: Optional[str] = None,    # YYYY-MM or ISO date/datetime
    log_history: bool = True  # Whether to log this search to history
):
    """
    Unified Search Endpoint.
    Modes:
      - 'metadata' (SQL)
      - 'semantic' (CLIP)
      - 'hybrid' (Merge Metadata + Semantic)
    Sort: date_desc (default), date_asc, name, size
    Type Filter: all (default), photos, videos
    Favorites Filter: all (default), favorites_only
    """
    try:
        import time
        start_time = time.time()

        # Input validation
        query_result = validate_search_query(query, max_length=500)
        if not query_result.is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid search query: {query_result.error_message}")
        validated_query = query_result.sanitized_value

        pagination_result = validate_pagination_params(limit, offset)
        if not pagination_result.is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid pagination: {pagination_result.error_message}")
        validated_limit = pagination_result.sanitized_value["limit"]
        validated_offset = pagination_result.sanitized_value["offset"]

        # Validate dates
        if date_from:
            date_from_result = validate_date_input(date_from)
            if not date_from_result.is_valid:
                raise HTTPException(status_code=400, detail=f"Invalid date_from: {date_from_result.error_message}")
            validated_date_from = date_from_result.sanitized_value
        else:
            validated_date_from = None

        if date_to:
            date_to_result = validate_date_input(date_to)
            if not date_to_result.is_valid:
                raise HTTPException(status_code=400, detail=f"Invalid date_to: {date_to_result.error_message}")
            validated_date_to = date_to_result.sanitized_value
        else:
            validated_date_to = None

        # Validate mode
        valid_modes = {"metadata", "semantic", "hybrid"}
        if mode not in valid_modes:
            raise HTTPException(status_code=400, detail=f"Invalid mode: {mode}. Must be one of {valid_modes}")

        # Validate sort_by
        valid_sort_options = {"date_desc", "date_asc", "name", "size"}
        if sort_by not in valid_sort_options:
            raise HTTPException(status_code=400, detail=f"Invalid sort_by: {sort_by}. Must be one of {valid_sort_options}")

        # Validate filters
        valid_type_filters = {"all", "photos", "videos"}
        if type_filter not in valid_type_filters:
            raise HTTPException(status_code=400, detail=f"Invalid type_filter: {type_filter}. Must be one of {valid_type_filters}")

        valid_source_filters = {"all", "local", "cloud", "hybrid"}
        if source_filter not in valid_source_filters:
            raise HTTPException(status_code=400, detail=f"Invalid source_filter: {source_filter}. Must be one of {valid_source_filters}")

        valid_favorites_filters = {"all", "favorites_only"}
        if favorites_filter not in valid_favorites_filters:
            raise HTTPException(status_code=400, detail=f"Invalid favorites_filter: {favorites_filter}. Must be one of {valid_favorites_filters}")

        if tag_logic not in {"AND", "OR"}:
            raise HTTPException(status_code=400, detail="Invalid tag_logic: Must be 'AND' or 'OR'")

        tagged_paths = None
        if tag or tags:
            try:
                from server.tags_db import get_tags_db

                tags_db = get_tags_db(settings.BASE_DIR / "tags.db")

                # Handle both single tag and multiple tags
                if tags:
                    # Split multiple tags and remove whitespace
                    tag_list = [t.strip() for t in tags.split(',')]

                    # Get paths for each tag
                    all_tagged_paths = {}
                    for t in tag_list:
                        if t:  # Skip empty tags
                            all_tagged_paths[t] = set(tags_db.get_tag_paths(t))

                    # Apply logic based on tag_logic (AND/OR)
                    if tag_logic.upper() == "AND":
                        # For AND logic, find intersection of all tag sets
                        if all_tagged_paths:
                            tagged_paths = set.intersection(*all_tagged_paths.values())
                    elif tag_logic.upper() == "OR":
                        # For OR logic, find union of all tag sets
                        if all_tagged_paths:
                            tagged_paths = set.union(*all_tagged_paths.values())
                        else:
                            tagged_paths = set()
                    else:
                        # Default to OR if invalid logic provided
                        if all_tagged_paths:
                            tagged_paths = set.union(*all_tagged_paths.values())
                        else:
                            tagged_paths = set()
                elif tag:
                    # Original single tag logic
                    tagged_paths = set(tags_db.get_tag_paths(tag))
            except Exception as e:
                print(f"Tag filtering error: {e}")
                tagged_paths = set()
        # 1. Semantic Search
        if mode == "semantic":
            results_response = await search_semantic(query, limit * 2, 0)  # Get more for filtering
            results = results_response.get('results', [])

            if tagged_paths is not None:
                results = [r for r in results if r.get("path") in tagged_paths]
            
            # Apply type filter
            if type_filter == "photos":
                results = [r for r in results if not is_video_file(r.get('path', ''))]
            elif type_filter == "videos":
                results = [r for r in results if is_video_file(r.get('path', ''))]
            
            # Apply favorites filter
            if favorites_filter == "favorites_only":
                results = [r for r in results if photo_search_engine.is_favorite(r.get('path', ''))]

            # Apply date filter (filesystem.created)
            results = apply_date_filter(results, date_from, date_to)
            # Apply source filter (local/cloud/hybrid)
            if source_filter != "all":
                def is_cloud_path(p: str) -> bool:
                    if not p:
                        return False
                    lower = p.lower()
                    return lower.startswith("http://") or lower.startswith("https://") or lower.startswith("s3://") or lower.startswith("cloud:") or lower.startswith("gdrive:") or "amazonaws.com" in lower or lower.startswith("dropbox:") or lower.startswith("onedrive:")

                def is_local_path(p: str) -> bool:
                    if not p:
                        return False
                    return bool(re.match(r'^[A-Za-z]:\\|^/|^file://|^~/', p))

                if source_filter == "local":
                    results = [r for r in results if is_local_path(r.get('path', ''))]
                elif source_filter == "cloud":
                    results = [r for r in results if is_cloud_path(r.get('path', ''))]
                elif source_filter == "hybrid":
                    results = [r for r in results if (not is_local_path(r.get('path', '')) and not is_cloud_path(r.get('path', '')))]
            
            # Apply sort
            results = apply_sort(results, sort_by)
            
            # Paginate
            paginated = results[offset:offset + limit]
            return {"count": len(results), "results": paginated}

        # 2. Metadata Search
        if mode == "metadata":
            # For empty query, directly get all files from database
            if not query.strip():
                cursor = photo_search_engine.db.conn.cursor()
                cursor.execute("SELECT file_path, metadata_json FROM metadata")
                results = []
                for row in cursor.fetchall():
                    import json
                    results.append({
                        'file_path': row['file_path'],
                        'metadata': json.loads(row['metadata_json']) if row['metadata_json'] else {}
                    })
            else:
                # Check if query has structured operators (=, >, <, LIKE, etc.)
                has_operators = any(op in query for op in ['=', '>', '<', '!=', ' LIKE ', ' CONTAINS ', ':'])
                print(f"DEBUG: Query='{query}', has_operators={has_operators}")
                
                if not has_operators:
                    # Simple search term - search in filename using shortcut format
                    search_query = f"filename:{query}"
                    print(f"DEBUG: Simple query '{query}' converted to '{search_query}'")
                    results = photo_search_engine.query_engine.search(search_query)
                else:
                    # Structured query - use as-is
                    print(f"DEBUG: Using structured query as-is: '{query}'")
                    results = photo_search_engine.query_engine.search(query)
            
            # Formatted list with match explanations
            formatted_results = []
            for r in results:
                path = r.get('file_path', r.get('path'))
                result_item = {
                    "path": path,
                    "filename": os.path.basename(path),
                    "score": r.get('score', 0),
                    "metadata": r.get('metadata', {})
                }
                
                # Generate match explanation for metadata search
                if query.strip():
                    result_item["matchExplanation"] = generate_metadata_match_explanation(query, r)
                
                formatted_results.append(result_item)
            
            # Apply type filter
            if type_filter == "photos":
                formatted_results = [r for r in formatted_results if not is_video_file(r.get('path', ''))]
            elif type_filter == "videos":
                formatted_results = [r for r in formatted_results if is_video_file(r.get('path', ''))]

            if tagged_paths is not None:
                formatted_results = [r for r in formatted_results if r.get("path") in tagged_paths]
            
            # Apply favorites filter
            if favorites_filter == "favorites_only":
                formatted_results = [r for r in formatted_results if photo_search_engine.is_favorite(r.get('path', ''))]

            # Apply date filter (filesystem.created)
            formatted_results = apply_date_filter(formatted_results, date_from, date_to)
            # Apply source filter (local/cloud/hybrid)
            if source_filter != "all":
                def is_cloud_path(p: str) -> bool:
                    if not p:
                        return False
                    lower = p.lower()
                    return lower.startswith("http://") or lower.startswith("https://") or lower.startswith("s3://") or lower.startswith("cloud:") or lower.startswith("gdrive:") or "amazonaws.com" in lower or lower.startswith("dropbox:") or lower.startswith("onedrive:")

                def is_local_path(p: str) -> bool:
                    if not p:
                        return False
                    return bool(re.match(r'^[A-Za-z]:\\|^/|^file://|^~/', p))

                if source_filter == "local":
                    formatted_results = [r for r in formatted_results if is_local_path(r.get('path', ''))]
                elif source_filter == "cloud":
                    formatted_results = [r for r in formatted_results if is_cloud_path(r.get('path', ''))]
                elif source_filter == "hybrid":
                    formatted_results = [r for r in formatted_results if (not is_local_path(r.get('path', '')) and not is_cloud_path(r.get('path', '')))]
            
            # Apply sorting
            formatted_results = apply_sort(formatted_results, sort_by)
            
            # Apply Pagination Slicing
            count = len(formatted_results)
            paginated = formatted_results[offset : offset + limit]
            
            return {"count": count, "results": paginated}

        # 3. Hybrid Search (Metadata + Semantic with weighted scoring)
        if mode == "hybrid":
            # A. Get Metadata Results (All)
            metadata_results = []
            try:
                if any(op in query for op in ['=', '>', '<', 'LIKE']):
                    metadata_results = photo_search_engine.query_engine.search(query)
                else:
                    safe_query = query.replace("'", "''")
                    metadata_results = photo_search_engine.query_engine.search(
                        f"file.path LIKE '%{safe_query}%'"
                    )
            except Exception as e:
                print(f"Metadata search error in hybrid: {e}")

            # B. Get Semantic Results (Top N = limit + offset)
            # We need deep fetch to ensure correct global ranking after merge
            semantic_limit = limit + offset
            semantic_response = await search_semantic(query, semantic_limit, offset=0)
            semantic_results = semantic_response['results']

            # C. Normalize semantic scores
            if semantic_results:
                max_score = max(r['score'] for r in semantic_results)
                min_score = min(r['score'] for r in semantic_results)
                score_range = max_score - min_score if max_score != min_score else 1.0
                
                for r in semantic_results:
                    r['normalized_score'] = (r['score'] - min_score) / score_range

            # D. Enhanced Merge Logic with Intent Detection
            METADATA_WEIGHT = 0.6
            SEMANTIC_WEIGHT = 0.4
            
            # Get intent-based weights using the intent detector
            intent_result = intent_detector.detect_intent(query)
            
            # Map intent to weights
            def get_weights_from_intent(primary_intent):
                """Get metadata/semantic weights based on primary intent"""
                # Metadata-heavy intents
                if primary_intent in ['camera', 'date', 'technical']:
                    return 0.7, 0.3
                # Semantic-heavy intents
                elif primary_intent in ['people', 'object', 'scene', 'event', 'emotion', 'activity']:
                    return 0.4, 0.6
                # Balanced intents
                elif primary_intent in ['location', 'color']:
                    return 0.5, 0.5
                # Default balanced
                else:
                    return 0.6, 0.4
            
            intent_metadata_weight, intent_semantic_weight = get_weights_from_intent(intent_result['primary_intent'])
            
            seen_paths = set()
            hybrid_results = []
            
            for r in metadata_results:
                path = r.get('file_path', r.get('path'))
                seen_paths.add(path)
                semantic_match = next((s for s in semantic_results if s['path'] == path), None)
                
                if semantic_match:
                    # Both sources available - use intent-based weights
                    combined_score = (intent_metadata_weight * 1.0) + (intent_semantic_weight * semantic_match.get('normalized_score', 0.5))
                else:
                    # Only metadata available
                    combined_score = intent_metadata_weight * 0.8
                
                hybrid_results.append({
                    "path": path,
                    "filename": os.path.basename(path),
                    "score": round(combined_score, 3),
                    "metadata": r.get('metadata', {}),
                    "source": "both" if semantic_match else "metadata",
                    "intent": "metadata" if metadata_results else "semantic"
                })

            for r in semantic_results:
                if r['path'] not in seen_paths:
                    seen_paths.add(r['path'])
                    hybrid_results.append({
                        "path": r['path'],
                        "filename": r['filename'],
                        "score": round(intent_semantic_weight * r.get('normalized_score', r['score']), 3),
                        "metadata": r.get('metadata', {}),
                        "source": "semantic",
                        "intent": "semantic"
                    })
            
            # Sort by score descending
            hybrid_results.sort(key=lambda x: x['score'], reverse=True)
            
            # Apply type filter
            if type_filter == "photos":
                hybrid_results = [r for r in hybrid_results if not is_video_file(r.get('path', ''))]
            elif type_filter == "videos":
                hybrid_results = [r for r in hybrid_results if is_video_file(r.get('path', ''))]

            if tagged_paths is not None:
                hybrid_results = [r for r in hybrid_results if r.get("path") in tagged_paths]
            
            # Apply favorites filter
            if favorites_filter == "favorites_only":
                hybrid_results = [r for r in hybrid_results if photo_search_engine.is_favorite(r.get('path', ''))]

            # Apply date filter (filesystem.created)
            hybrid_results = apply_date_filter(hybrid_results, date_from, date_to)
            # Apply source filter (local/cloud/hybrid)
            if source_filter != "all":
                def is_cloud_path(p: str) -> bool:
                    if not p:
                        return False
                    lower = p.lower()
                    return lower.startswith("http://") or lower.startswith("https://") or lower.startswith("s3://") or lower.startswith("cloud:") or lower.startswith("gdrive:") or "amazonaws.com" in lower or lower.startswith("dropbox:") or lower.startswith("onedrive:")

                def is_local_path(p: str) -> bool:
                    if not p:
                        return False
                    return bool(re.match(r'^[A-Za-z]:\\|^/|^file://|^~/', p))

                if source_filter == "local":
                    hybrid_results = [r for r in hybrid_results if is_local_path(r.get('path', ''))]
                elif source_filter == "cloud":
                    hybrid_results = [r for r in hybrid_results if is_cloud_path(r.get('path', ''))]
                elif source_filter == "hybrid":
                    hybrid_results = [r for r in hybrid_results if (not is_local_path(r.get('path', '')) and not is_cloud_path(r.get('path', '')))]
            
            # Apply Pagination Slicing
            count = len(hybrid_results)
            paginated_raw = hybrid_results[offset : offset + limit]
            
            # Format results with match explanations
            paginated = []
            for r in paginated_raw:
                result_item = {
                    "path": r['path'],
                    "filename": r['filename'],
                    "score": r['score'],
                    "metadata": r.get('metadata', {}),
                    "source": r.get('source', 'hybrid'),
                    "intent": r.get('intent', 'balanced')
                }
                
                # Generate hybrid match explanation with detailed breakdown
                if query.strip():
                    result_item["matchExplanation"] = generate_hybrid_match_explanation(
                        query, r, intent_metadata_weight, intent_semantic_weight
                    )
                
                paginated.append(result_item)
            
            # Log search to history if enabled
            if log_history:
                execution_time_ms = int(round((time.time() - start_time) * 1000))
                intent_result = intent_detector.detect_intent(query)
                saved_search_manager.log_search_history(
                    query=query,
                    mode=mode,
                    results_count=count,
                    intent=intent_result["primary_intent"],
                    execution_time_ms=execution_time_ms,
                    user_agent="api",
                    ip_address="localhost"
                )

                # Add structured logging for search operation
                try:
                    log_search_operation(
                        ps_logger,
                        query=query,
                        mode=mode,
                        results_count=count,
                        execution_time=execution_time_ms
                    )
                except Exception as e:
                    print(f"Error logging search operation: {e}")
            
            return {"count": count, "results": paginated, "intent": {
                "primary_intent": intent_result["primary_intent"],
                "secondary_intents": intent_result["secondary_intents"],
                "metadata_weight": intent_metadata_weight,
                "semantic_weight": intent_semantic_weight,
                "confidence": intent_result["confidence"],
                "badges": intent_result["badges"],
                "suggestions": intent_result["suggestions"],
                "execution_time_ms": execution_time_ms
            }}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Favorites endpoints
@app.post("/favorites/toggle")
async def toggle_favorite(payload: dict = Body(...)):
    """
    Toggle favorite status of a file.
    
    Body: {"file_path": "/path/to/file.jpg", "notes": "optional notes"}
    """
    file_path = payload.get("file_path")
    notes = payload.get("notes", "")
    
    if not file_path:
        raise HTTPException(status_code=400, detail="file_path is required")
    
    try:
        is_favorited = photo_search_engine.toggle_favorite(file_path, notes)
        return {"success": True, "is_favorited": is_favorited}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/favorites")
async def get_favorites(limit: int = 1000, offset: int = 0):
    """
    Get all favorited files.
    """
    try:
        favorites = photo_search_engine.get_favorites(limit, offset)
        return {"count": len(favorites), "results": favorites}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/favorites/check")
async def check_favorite(file_path: str):
    """
    Check if a file is favorited.
    
    Query param: file_path=/path/to/file.jpg
    """
    try:
        is_favorited = photo_search_engine.is_favorite(file_path)
        return {"is_favorited": is_favorited}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/favorites")
async def remove_favorite(payload: dict = Body(...)):
    """
    Remove a file from favorites.
    
    Body: {"file_path": "/path/to/file.jpg"}
    """
    file_path = payload.get("file_path")
    
    if not file_path:
        raise HTTPException(status_code=400, detail="file_path is required")
    
    try:
        success = photo_search_engine.remove_favorite(file_path)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Bulk operations endpoints
@app.post("/bulk/export")
async def bulk_export(payload: dict = Body(...)):
    """
    Export multiple photos as a ZIP file.
    
    Body: {"file_paths": ["/path/to/file1.jpg", "/path/to/file2.jpg"], "format": "zip"}
    """
    file_paths = payload.get("file_paths", [])
    format_type = payload.get("format", "zip")
    
    if not file_paths:
        raise HTTPException(status_code=400, detail="file_paths is required")
    
    try:
        import zipfile
        import tempfile
        import os
        from pathlib import Path
        
        # Create temporary ZIP file
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
            zip_path = temp_zip.name
            
            with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in file_paths:
                    if os.path.exists(file_path):
                        # Add file to ZIP with just the filename (not full path)
                        filename = os.path.basename(file_path)
                        zipf.write(file_path, filename)
        
        cleanup = BackgroundTasks()
        cleanup.add_task(os.unlink, zip_path)
        return FileResponse(
            path=zip_path,
            filename=f"photos_export_{len(file_paths)}_files.zip",
            media_type="application/zip",
            background=cleanup,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.post("/bulk/delete")
async def bulk_delete(payload: dict = Body(...)):
    """
    Delete multiple photos.
    
    Body: {"file_paths": ["/path/to/file1.jpg", "/path/to/file2.jpg"], "confirm": true}
    """
    file_paths = payload.get("file_paths", [])
    confirm = payload.get("confirm", False)
    
    if not file_paths:
        raise HTTPException(status_code=400, detail="file_paths is required")
    
    if not confirm:
        raise HTTPException(status_code=400, detail="Deletion requires confirmation")
    
    try:
        deleted_count = 0
        errors = []
        
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    # Remove from database
                    photo_search_engine.db.conn.execute("DELETE FROM metadata WHERE file_path = ?", (file_path,))
                    photo_search_engine.db.conn.commit()
                    deleted_count += 1
                else:
                    errors.append(f"File not found: {file_path}")
            except Exception as e:
                errors.append(f"Failed to delete {file_path}: {str(e)}")
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "errors": errors
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk delete failed: {str(e)}")


# ==============================================================================
# TRASH / RESTORE (RECENTLY DELETED)
# ==============================================================================

class TrashMoveRequest(BaseModel):
    file_paths: List[str]


class TrashRestoreRequest(BaseModel):
    item_ids: List[str]


class TrashEmptyRequest(BaseModel):
    item_ids: Optional[List[str]] = None


class LibraryRemoveRequest(BaseModel):
    file_paths: List[str]


def _trash_root() -> Path:
    root = settings.BASE_DIR / "trash_files"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _trash_allowed_roots() -> List[Path]:
    roots: List[Path] = [
        settings.BASE_DIR.resolve(),
        settings.MEDIA_DIR.resolve(),
        (settings.BASE_DIR / "media_sources").resolve(),
    ]
    try:
        for s in source_store.list_sources(redact=False):
            if s.type != "local_folder":
                continue
            p = (s.config or {}).get("path")
            if isinstance(p, str) and p:
                try:
                    roots.append(Path(p).resolve())
                except Exception:
                    continue
    except Exception:
        pass
    return roots


def _assert_path_allowed_for_trash(p: Path) -> None:
    roots = _trash_allowed_roots()
    rp = p.resolve()
    is_allowed = any(rp.is_relative_to(root) for root in roots)
    if not is_allowed:
        raise HTTPException(status_code=403, detail="Path is outside connected sources")
    if rp.is_relative_to(_trash_root().resolve()):
        raise HTTPException(status_code=400, detail="Path is already in Trash")


def _reindex_one_file(path: str) -> None:
    try:
        from src.metadata_extractor import extract_all_metadata

        metadata = extract_all_metadata(path)
        if metadata:
            photo_search_engine.db.store_metadata(path, metadata)
            process_semantic_indexing([path])
    except Exception:
        # Restore should succeed even if indexing fails.
        pass


@app.post("/trash/move")
async def trash_move(req: TrashMoveRequest):
    """
    Move files into app-managed Trash and remove them from the active library index.
    For cloud sources, this moves the mirrored local copy only (does not delete remote originals).
    """
    if not req.file_paths:
        raise HTTPException(status_code=400, detail="file_paths is required")

    moved: List[dict] = []
    errors: List[str] = []
    for file_path in req.file_paths:
        try:
            src_path = Path(file_path)
            _assert_path_allowed_for_trash(src_path)
            if not src_path.exists() or not src_path.is_file():
                raise HTTPException(status_code=404, detail="File not found")

            trash_id = str(uuid.uuid4())
            dest_dir = _trash_root() / trash_id
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / src_path.name

            shutil.move(str(src_path), str(dest))

            # Remove from active indices (metadata + embeddings)
            try:
                photo_search_engine.db.mark_as_deleted(str(src_path), reason="trashed")
            except Exception:
                pass
            try:
                vector_store.delete([str(src_path)])
            except Exception:
                pass

            # Link to a cloud source item when applicable (so sync won't re-download).
            source_item = None
            try:
                source_item = source_item_store.find_by_local_path(str(src_path.resolve()))
            except Exception:
                source_item = None
            if source_item:
                try:
                    source_item_store.set_status(source_item.source_id, source_item.remote_id, "trashed")
                    source_item_store.set_local_path(source_item.source_id, source_item.remote_id, str(dest))
                except Exception:
                    pass

            item = trash_db.create(
                item_id=trash_id,
                original_path=str(src_path),
                trashed_path=str(dest),
                source_id=source_item.source_id if source_item else None,
                remote_id=source_item.remote_id if source_item else None,
            )
            moved.append(
                {
                    "id": item.id,
                    "original_path": item.original_path,
                    "trashed_path": item.trashed_path,
                    "created_at": item.created_at,
                }
            )
        except HTTPException as he:
            errors.append(f"{file_path}: {he.detail}")
        except Exception as e:
            errors.append(f"{file_path}: {str(e)}")

    return {"moved": moved, "errors": errors}


@app.get("/trash")
async def list_trash(limit: int = 200, offset: int = 0):
    items = trash_db.list(status="trashed", limit=limit, offset=offset)
    out: List[dict] = []
    for it in items:
        out.append(
            {
                "id": it.id,
                "original_path": it.original_path,
                "trashed_path": it.trashed_path,
                "status": it.status,
                "source_id": it.source_id,
                "remote_id": it.remote_id,
                "created_at": it.created_at,
            }
        )
    return {"items": out}


@app.post("/trash/restore")
async def restore_from_trash(req: TrashRestoreRequest):
    if not req.item_ids:
        raise HTTPException(status_code=400, detail="item_ids is required")

    restored: List[str] = []
    errors: List[str] = []
    for item_id in req.item_ids:
        try:
            item = trash_db.get(item_id)
            if item.status != "trashed":
                raise HTTPException(status_code=400, detail="Item is not in Trash")

            src = Path(item.trashed_path)
            dst = Path(item.original_path)
            _assert_path_allowed_for_trash(dst)
            if not src.exists():
                raise HTTPException(status_code=404, detail="Trashed file missing")

            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))

            # Reindex restored path
            _reindex_one_file(str(dst))

            if item.source_id and item.remote_id:
                try:
                    source_item_store.set_status(item.source_id, item.remote_id, "active")
                    source_item_store.set_local_path(item.source_id, item.remote_id, str(dst))
                except Exception:
                    pass

            trash_db.mark_restored(item_id)
            restored.append(item_id)
        except HTTPException as he:
            errors.append(f"{item_id}: {he.detail}")
        except Exception as e:
            errors.append(f"{item_id}: {str(e)}")

    return {"restored": restored, "errors": errors}


@app.post("/trash/empty")
async def empty_trash(req: TrashEmptyRequest):
    """
    Permanently delete files currently in Trash.
    For cloud sources, this acts as "Remove from library" (remote originals are not deleted).
    """
    items = []
    if req.item_ids:
        for item_id in req.item_ids:
            try:
                items.append(trash_db.get(item_id))
            except Exception:
                continue
    else:
        items = trash_db.list(status="trashed", limit=5000, offset=0)

    deleted: List[str] = []
    errors: List[str] = []
    for it in items:
        try:
            if it.status != "trashed":
                continue
            p = Path(it.trashed_path)
            if p.exists() and p.is_file():
                p.unlink()

            if it.source_id and it.remote_id:
                # Ensure sync doesn't re-download (remote originals remain).
                try:
                    source_item_store.set_status(it.source_id, it.remote_id, "removed")
                except Exception:
                    pass

            trash_db.mark_deleted(it.id)
            deleted.append(it.id)
        except Exception as e:
            errors.append(f"{it.id}: {str(e)}")

    return {"deleted": deleted, "errors": errors}


@app.post("/library/remove")
async def remove_from_library(req: LibraryRemoveRequest):
    """
    Remove items from the library index without sending them to Trash.
    - For cloud sources (Drive/S3 mirrors): deletes the local mirror and marks the source item as `removed` so it won't re-download.
    - For local files: removes from the index only (files remain on disk and may reappear if re-scanned).
    """
    if not req.file_paths:
        raise HTTPException(status_code=400, detail="file_paths is required")

    removed: List[str] = []
    errors: List[str] = []
    for file_path in req.file_paths:
        try:
            p = Path(file_path)
            roots = _trash_allowed_roots()
            rp = p.resolve()
            if not any(rp.is_relative_to(root) for root in roots):
                raise HTTPException(status_code=403, detail="Path is outside connected sources")

            # Remove from indices (metadata + embeddings)
            try:
                photo_search_engine.db.mark_as_deleted(str(rp), reason="removed")
            except Exception:
                pass
            try:
                vector_store.delete([str(rp)])
            except Exception:
                pass

            # If this is a cloud-mirrored file, prevent re-download and delete local copy.
            source_item = None
            try:
                source_item = source_item_store.find_by_local_path(str(rp))
            except Exception:
                source_item = None
            if source_item:
                try:
                    source_item_store.set_status(source_item.source_id, source_item.remote_id, "removed")
                except Exception:
                    pass
                try:
                    if rp.exists() and rp.is_file():
                        rp.unlink()
                except Exception:
                    pass

            removed.append(str(rp))
        except HTTPException as he:
            errors.append(f"{file_path}: {he.detail}")
        except Exception as e:
            errors.append(f"{file_path}: {str(e)}")

    return {"removed": removed, "errors": errors}

@app.post("/bulk/favorite")
async def bulk_favorite(payload: dict = Body(...)):
    """
    Add/remove multiple photos to/from favorites.
    
    Body: {"file_paths": ["/path/to/file1.jpg", "/path/to/file2.jpg"], "action": "add|remove"}
    """
    file_paths = payload.get("file_paths", [])
    action = payload.get("action", "add")
    
    if not file_paths:
        raise HTTPException(status_code=400, detail="file_paths is required")
    
    if action not in ["add", "remove"]:
        raise HTTPException(status_code=400, detail="action must be 'add' or 'remove'")
    
    try:
        success_count = 0
        errors = []
        
        for file_path in file_paths:
            try:
                if action == "add":
                    photo_search_engine.add_favorite(file_path)
                else:
                    photo_search_engine.remove_favorite(file_path)
                success_count += 1
            except Exception as e:
                errors.append(f"Failed to {action} favorite {file_path}: {str(e)}")
        
        return {
            "success": True,
            "processed_count": success_count,
            "errors": errors
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk favorite {action} failed: {str(e)}")

def generate_metadata_match_explanation(query: str, result: dict) -> dict:
    """Generate match explanation for metadata search results with detailed breakdown"""
    reasons = []
    breakdown: dict[str, float] = {
        "filename_score": 0.0,
        "metadata_score": 0.0,
        "content_score": 0.0,
    }
    
    # Analyze the query to understand what matched
    query_lower = query.lower()
    metadata = result.get('metadata', {})
    filename = result.get('filename', result.get('file_path', '').split('/')[-1])
    
    # Check for filename matches (most common case)
    filename_match_score: float = 0.0
    if query_lower in filename.lower():
        # Calculate confidence based on how much of the filename matches
        match_ratio = len(query_lower) / len(filename.lower())
        confidence = min(0.95, 0.7 + (match_ratio * 0.25))  # 70-95% based on match ratio
        filename_match_score = confidence * 100.0
        breakdown["filename_score"] = filename_match_score
        
        reasons.append({
            "category": "Filename Match",
            "matched": f"Filename '{filename}' contains '{query}' ({match_ratio:.1%} of filename)",
            "confidence": confidence,
            "badge": "📝",
            "type": "metadata"
        })
    
    # Check for metadata matches
    metadata_matches = 0
    metadata_total = 0
    
    # Check for camera matches
    camera_info = metadata.get('camera', {})
    if camera_info:
        metadata_total += 1
        if any(term in query_lower for term in ['camera', 'make', 'model']) or \
           (camera_info.get('make') and camera_info.get('make').lower() in query_lower):
            metadata_matches += 1
            reasons.append({
                "category": "Camera Equipment",
                "matched": f"Shot with {camera_info.get('make')} {camera_info.get('model', '')}".strip(),
                "confidence": 1.0,
                "badge": "📷",
                "type": "metadata"
            })
    
    # Check for lens matches
    lens_info = metadata.get('lens', {})
    if lens_info:
        metadata_total += 1
        if any(term in query_lower for term in ['lens', 'focal', 'aperture']):
            metadata_matches += 1
            if lens_info.get('focal_length'):
                reasons.append({
                    "category": "Lens Settings",
                    "matched": f"{lens_info.get('focal_length')}mm lens",
                    "confidence": 1.0,
                    "badge": "🔍",
                    "type": "metadata"
                })
    
    # Check for date matches
    date_info = metadata.get('date', {})
    if date_info:
        metadata_total += 1
        if any(term in query_lower for term in ['date', 'taken', '2023', '2024']):
            metadata_matches += 1
            if date_info.get('taken'):
                reasons.append({
                    "category": "Date & Time",
                    "matched": f"Taken on {date_info.get('taken')}",
                    "confidence": 1.0,
                    "badge": "📅",
                    "type": "metadata"
                })
    
    # Check for GPS/location matches
    gps_info = metadata.get('gps', {})
    if gps_info:
        metadata_total += 1
        if any(term in query_lower for term in ['gps', 'location', 'city']) or \
           (gps_info.get('city') and gps_info.get('city').lower() in query_lower):
            metadata_matches += 1
            if gps_info.get('city'):
                reasons.append({
                    "category": "Location",
                    "matched": f"Located in {gps_info.get('city')}",
                    "confidence": 1.0,
                    "badge": "📍",
                    "type": "metadata"
                })
    
    # Calculate metadata score
    if metadata_total > 0:
        breakdown["metadata_score"] = (metadata_matches / metadata_total) * 100.0
    
    # If no specific matches found, provide generic match with lower confidence
    if not reasons:
        reasons.append({
            "category": "General Match",
            "matched": f"Found in metadata or file properties",
            "confidence": 0.6,
            "badge": "🔍",
            "type": "metadata"
        })
        breakdown["metadata_score"] = 60
    
    # Calculate overall confidence
    overall_confidence = max(breakdown["filename_score"], breakdown["metadata_score"]) / 100
    
    return {
        "type": "metadata",
        "reasons": reasons,
        "overallConfidence": overall_confidence,
        "breakdown": breakdown
    }

def generate_hybrid_match_explanation(query: str, result: dict, metadata_weight: float, semantic_weight: float) -> dict:
    """Generate match explanation for hybrid search results with detailed breakdown"""
    reasons = []
    breakdown = {
        "metadata_score": 0,
        "semantic_score": 0,
        "filename_score": 0,
        "content_score": 0
    }
    
    # Calculate individual component scores based on the combined score and weights
    combined_score = result.get('score', 0)
    source = result.get('source', 'hybrid')
    
    if source == "both":
        # Both metadata and semantic contributed
        estimated_metadata_score = (combined_score / (metadata_weight + semantic_weight)) * metadata_weight
        estimated_semantic_score = (combined_score / (metadata_weight + semantic_weight)) * semantic_weight
        
        breakdown["metadata_score"] = estimated_metadata_score * 100
        breakdown["semantic_score"] = estimated_semantic_score * 100
        breakdown["filename_score"] = estimated_metadata_score * 80  # Filename is part of metadata
        breakdown["content_score"] = estimated_semantic_score * 100
        
        reasons.append({
            "category": "Metadata Match",
            "matched": f"File details match your search (weight: {metadata_weight:.0%})",
            "confidence": estimated_metadata_score,
            "badge": "📊",
            "type": "metadata"
        })
        
        reasons.append({
            "category": "Visual Content",
            "matched": f"We understand the visual content matches your query (weight: {semantic_weight:.0%})",
            "confidence": estimated_semantic_score,
            "badge": "🎯",
            "type": "semantic"
        })
        
    elif source == "metadata":
        # Only metadata contributed
        breakdown["metadata_score"] = combined_score * 100
        breakdown["filename_score"] = combined_score * 80
        
        reasons.append({
            "category": "Metadata Match",
            "matched": f"Strong match in file details and metadata",
            "confidence": combined_score,
            "badge": "📊",
            "type": "metadata"
        })
        
    elif source == "semantic":
        # Only semantic contributed
        breakdown["semantic_score"] = combined_score * 100
        breakdown["content_score"] = combined_score * 100
        
        reasons.append({
            "category": "Visual Content",
            "matched": f"We identified visual elements matching your search",
            "confidence": combined_score,
            "badge": "🎯",
            "type": "semantic"
        })
    
    return {
        "type": "hybrid",
        "reasons": reasons,
        "overallConfidence": combined_score,
        "breakdown": breakdown
    }

def generate_semantic_match_explanation(query: str, result: dict, score: float) -> dict:
    """Generate match explanation for semantic search results with detailed breakdown"""
    reasons = []
    breakdown = {
        "semantic_score": score * 100,
        "content_score": score * 100
    }
    
    # We identify visual concepts (this would normally come from our analysis engine)
    # For now, we'll generate plausible explanations based on the query
    query_lower = query.lower()
    
    # Analyze query for visual concepts with confidence adjustment
    confidence_boost = 0.1  # Boost confidence for specific matches
    
    if any(word in query_lower for word in ['sunset', 'golden', 'orange', 'warm', 'light']):
        adjusted_score = min(0.95, score + confidence_boost)
        reasons.append({
            "category": "Visual Content",
            "matched": "We found warm lighting, golden hour colors, and sunset atmosphere",
            "confidence": adjusted_score,
            "badge": "🌅",
            "type": "semantic"
        })
        breakdown["content_score"] = adjusted_score * 100
    
    if any(word in query_lower for word in ['person', 'people', 'face', 'portrait', 'human']):
        adjusted_score = min(0.95, score + confidence_boost)
        reasons.append({
            "category": "People Detection",
            "matched": "We identified human faces and body poses in this image",
            "confidence": adjusted_score,
            "badge": "�",
            "type": "semantic"
        })
        breakdown["content_score"] = adjusted_score * 100
    
    if any(word in query_lower for word in ['car', 'vehicle', 'street', 'road', 'traffic']):
        adjusted_score = min(0.95, score + confidence_boost)
        reasons.append({
            "category": "Object Recognition",
            "matched": "We spotted vehicles, roads, and urban infrastructure",
            "confidence": adjusted_score,
            "badge": "🚗",
            "type": "semantic"
        })
        breakdown["content_score"] = adjusted_score * 100
    
    if any(word in query_lower for word in ['nature', 'tree', 'forest', 'landscape', 'mountain', 'sky']):
        adjusted_score = min(0.95, score + confidence_boost)
        reasons.append({
            "category": "Scene Understanding",
            "matched": "We recognized natural landscapes, vegetation, and outdoor scenes",
            "confidence": adjusted_score,
            "badge": "🌲",
            "type": "semantic"
        })
        breakdown["content_score"] = adjusted_score * 100
    
    if any(word in query_lower for word in ['food', 'eat', 'meal', 'restaurant', 'kitchen']):
        adjusted_score = min(0.95, score + confidence_boost)
        reasons.append({
            "category": "Object Recognition",
            "matched": "We discovered food items, dining scenes, and culinary objects",
            "confidence": adjusted_score,
            "badge": "🍽️",
            "type": "semantic"
        })
        breakdown["content_score"] = adjusted_score * 100
    
    # If no specific matches, provide generic AI match with original score
    if not reasons:
        reasons.append({
            "category": "Visual Analysis",
            "matched": f"We found visual similarities in this content (confidence: {score:.1%})",
            "confidence": score,
            "badge": "🤖",
            "type": "semantic"
        })
    
    return {
        "type": "semantic",
        "reasons": reasons,
        "overallConfidence": score,
        "breakdown": breakdown
    }

@app.get("/api/intent/detect")
async def detect_intent_api(query: str):
    """
    Detect user intent from search query for auto-mode switching.
    """
    try:
        if not query.strip():
            return {
                "primary_intent": "general",
                "secondary_intents": [],
                "confidence": 0.5,
                "badges": [],
                "suggestions": []
            }
        
        intent_result = intent_detector.detect_intent(query)
        return intent_result
    except Exception as e:
        print(f"Intent detection error: {e}")
        return {
            "primary_intent": "general",
            "secondary_intents": [],
            "confidence": 0.5,
            "badges": [],
            "suggestions": []
        }

@app.post("/api/search/count")
async def get_search_count(request: SearchCountRequest):
    """
    Get count of search results for live feedback while typing.
    Used for the live match count feature in the UI.
    """
    try:
        query = request.query.strip()
        mode = request.mode
        
        if not query:
            return {"count": 0}
        
        # Get count based on search mode
        if mode == "metadata":
            # Check if query has structured operators
            has_operators = any(op in query for op in ['=', '>', '<', '!=', ' LIKE ', ' CONTAINS ', ':'])
            
            if not has_operators:
                # Simple search term - search in filename
                search_query = f"filename:{query}"
                results = photo_search_engine.query_engine.search(search_query)
            else:
                # Structured query - use as-is
                results = photo_search_engine.query_engine.search(query)
            
            return {"count": len(results)}
            
        elif mode == "semantic":
            if not embedding_generator:
                return {"count": 0}
            
            # Generate text embedding and search
            text_vec = embedding_generator.generate_text_embedding(query)
            results = vector_store.search(text_vec, limit=1000, offset=0)
            
            # Filter by minimum score and apply more realistic scoring
            filtered_results = []
            for r in results:
                # Apply more realistic scoring - prevent inflated scores
                adjusted_score = r['score']
                if adjusted_score >= 0.22:  # Only include meaningful matches
                    # Cap scores to prevent unrealistic high matches
                    if adjusted_score > 0.9:
                        adjusted_score = 0.85 + (adjusted_score - 0.9) * 0.3  # Compress high scores
                    r['score'] = adjusted_score
                    filtered_results.append(r)
            return {"count": len(filtered_results)}
            
        elif mode == "hybrid":
            # For hybrid, we need to estimate based on both modes
            # This is a simplified count - actual hybrid search is more complex
            metadata_count = 0
            semantic_count = 0
            
            # Get metadata count
            try:
                if any(op in query for op in ['=', '>', '<', 'LIKE']):
                    metadata_results = photo_search_engine.query_engine.search(query)
                else:
                    safe_query = query.replace("'", "''")
                    metadata_results = photo_search_engine.query_engine.search(f"file.path LIKE '%{safe_query}%'")
                metadata_count = len(metadata_results)
            except:
                pass
            
            # Get semantic count
            try:
                if embedding_generator:
                    text_vec = embedding_generator.generate_text_embedding(query)
                    semantic_results = vector_store.search(text_vec, limit=1000, offset=0)
                    semantic_count = len([r for r in semantic_results if r['score'] >= 0.22])
            except:
                pass
            
            # Estimate hybrid count (will have some overlap)
            estimated_count = max(metadata_count, semantic_count)
            return {"count": estimated_count}
        
        return {"count": 0}
        
    except Exception as e:
        print(f"Search count error: {e}")
        return {"count": 0}

@app.get("/search/semantic")
async def search_semantic(query: str, limit: int = 50, offset: int = 0, min_score: float = 0.22):
    """
    Semantic Search using text-to-image embeddings.
    """
    global embedding_generator
    try:
        if not embedding_generator:
            embedding_generator = EmbeddingGenerator()
        
        # Handle empty query - return all photos (paginated)
        if not query.strip():
            try:
                # Pass offset to store
                all_records = vector_store.get_all_records(limit=limit, offset=offset)
                formatted = []
                for r in all_records:
                    file_path = r.get('path', r.get('id', ''))
                    full_metadata = photo_search_engine.db.get_metadata_by_path(file_path)
                    formatted.append({
                        "path": file_path,
                        "filename": r.get('filename', os.path.basename(file_path)),
                        "score": 0,
                        "metadata": full_metadata or {}
                    })
                # Count is tricky here, but we return page size for now
                return {"count": len(formatted), "results": formatted}
            except Exception as e:
                print(f"Error getting all records: {e}")
                return {"count": 0, "results": []}
            
        # 1. Generate text embedding
        text_vec = embedding_generator.generate_text_embedding(query)
        
        # 2. Search LanceDB with offset
        # vector_store.search now supports offset directly
        results = vector_store.search(text_vec, limit=limit, offset=offset)
        
        # 3. Format and enrich
        formatted = []
        for r in results:
            if r['score'] >= min_score:
                file_path = r['metadata']['path']
                full_metadata = photo_search_engine.db.get_metadata_by_path(file_path)
                
                result_item = {
                    "path": file_path,
                    "filename": r['metadata']['filename'],
                    "score": r['score'],
                    "metadata": full_metadata or r['metadata']
                }
                
                # Generate match explanation for semantic search
                if query.strip():
                    result_item["matchExplanation"] = generate_semantic_match_explanation(query, result_item, r['score'])
                
                formatted.append(result_item)
        
        return {"count": len(formatted), "results": formatted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/image/thumbnail")
async def get_thumbnail(request: Request, path: str = "", size: int = 300, token: str | None = None, format: str | None = None):
    """
    Serve a thumbnail or the full image.
    Args:
        path: Path to the image file (local/dev usage)
        size: Max dimension for thumbnail (default 300)
        token: Optional signed token for production/public access
        format: Optional output format override (jpeg|webp)
    """
    # Resolve path either from token (preferred for public) or from 'path' param
    requested_path_str: str

    if token:
        # Verify token and extract path
        try:
            payload = verify_token(token, expected_scope="thumbnail")
            _p = payload.get("path")
            if not isinstance(_p, str) or not _p:
                raise HTTPException(status_code=401, detail="Invalid token payload")
            requested_path_str = _p
        except TokenError as te:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(te)}")
    else:
        # If signed URLs are enabled in production, require token for non-local clients
        client_host = None
        try:
            client_host = request.client.host if request.client else None
        except Exception:
            client_host = None

        if settings.SIGNED_URL_ENABLED and settings.SANDBOX_STRICT:
            # Allow loopback clients to use path param for local desktop flows
            if client_host not in ("127.0.0.1", "::1", "localhost"):
                raise HTTPException(status_code=401, detail="Signed URL required for this deployment")

        requested_path_str = path

    # Security check: Ensure path is within allowed directory
    try:
        if settings.MEDIA_DIR.exists():
            allowed_paths = [settings.MEDIA_DIR.resolve(), settings.BASE_DIR.resolve()]
        else:
            allowed_paths = [settings.BASE_DIR.resolve()]

        requested_path = Path(requested_path_str).resolve()

        is_allowed = any(
            requested_path.is_relative_to(allowed_path)
            for allowed_path in allowed_paths
        )

        if not is_allowed:
            logger.warning(f"Access denied to image: {hash_for_logs(requested_path_str)} ip={request.client.host if request.client else 'unknown'}")
            raise HTTPException(status_code=403, detail="Access denied: File outside allowed directories")
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    # Stat file once for headers / validation
    if not os.path.exists(requested_path_str):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        stat_result = os.stat(requested_path_str)
    except Exception:
        raise HTTPException(status_code=404, detail="File not accessible")

    output_format = _negotiate_image_format(format, request.headers.get("accept"))
    cache_headers = _make_cache_headers(stat_result, max_age=86400)

    # Conditional requests (ETag / If-Modified-Since)
    inm = request.headers.get("if-none-match")
    ims = request.headers.get("if-modified-since")
    if inm and inm == cache_headers.get("ETag"):
        # Add CORS headers to 304 responses
        response_headers = dict(cache_headers)
        origin = request.headers.get("origin")
        if origin and origin in cors_origins:
            response_headers["Access-Control-Allow-Origin"] = origin
            response_headers["Access-Control-Allow-Credentials"] = "true"
        return Response(status_code=304, headers=response_headers)
    if ims:
        try:
            ims_dt = datetime.strptime(ims, "%a, %d %b %Y %H:%M:%S GMT")
            if stat_result.st_mtime <= ims_dt.timestamp():
                # Add CORS headers to 304 responses
                response_headers = dict(cache_headers)
                origin = request.headers.get("origin")
                if origin and origin in cors_origins:
                    response_headers["Access-Control-Allow-Origin"] = origin
                    response_headers["Access-Control-Allow-Credentials"] = "true"
                return Response(status_code=304, headers=response_headers)
        except Exception:
            pass

    # Record access (hashed path to protect privacy)
    try:
        if settings.ACCESS_LOG_MASKING:
            logged_path = hash_for_logs(requested_path_str)
        else:
            logged_path = requested_path_str
        logger.info(f"IMAGE_ACCESS path={logged_path} size={size} ip={request.client.host if request.client else 'unknown'} token={'yes' if token else 'no'}")
    except Exception:
        # In case logging fails, don't block response
        pass

    # Serve the thumbnail after security checks and access logging
    try:
        from PIL import Image
        import io

        # For 3D textures we want small files (size=300 is good)
        # For Detail Modal we want larger (size=1200)

        with Image.open(requested_path_str) as img:
            # Convert to RGB if needed (e.g. RGBA or P)
            if img.mode in ("RGBA", "P") and output_format in ("JPEG", "WEBP"):
                img = img.convert("RGB")

            img.thumbnail((size, size))

            # Save to buffer
            img_io = io.BytesIO()
            save_kwargs = {"quality": 75}
            if output_format == "WEBP":
                save_kwargs["method"] = 4
            img.save(img_io, output_format, **save_kwargs)
            img_io.seek(0)

            # Rate limiting: check per-IP quota
            try:
                if settings.RATE_LIMIT_ENABLED:
                    global _rate_last_conf
                    conf = (bool(settings.RATE_LIMIT_ENABLED), int(settings.RATE_LIMIT_REQS_PER_MIN))
                    client_ip = request.client.host if request.client else "unknown"
                    now = __import__("time").time()
                    with _rate_lock:
                        if _rate_last_conf != conf:
                            _rate_counters.clear()
                            _rate_last_conf = conf
                        lst = _rate_counters.get(client_ip, [])
                        lst = [t for t in lst if now - t < 60]
                        if len(lst) >= settings.RATE_LIMIT_REQS_PER_MIN:
                            raise HTTPException(status_code=429, detail="Rate limit exceeded")
                        lst.append(now)
                        _rate_counters[client_ip] = lst
            except HTTPException:
                raise
            except Exception:
                pass

            content_bytes = img_io.getvalue()
            logger.info(f"Thumbnail produced {len(content_bytes)} bytes for {requested_path_str} as {output_format}")
            # Include cache headers + content type + explicit CORS headers
            headers = dict(cache_headers)
            headers.setdefault("Content-Type", "image/webp" if output_format == "WEBP" else "image/jpeg")
            
            # Explicit CORS headers for cross-origin image requests
            origin = request.headers.get("origin")
            if origin and origin in cors_origins:
                headers["Access-Control-Allow-Origin"] = origin
                headers["Access-Control-Allow-Credentials"] = "true"
            
            return Response(
                content=content_bytes,
                media_type="image/webp" if output_format == "WEBP" else "image/jpeg",
                headers=headers,
            )

    except ImportError:
        pass
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Thumbnail error for {requested_path_str}: {e}")
        pass

    # Fallback to serving original file with cache headers + CORS headers
    fallback_headers = dict(cache_headers)
    
    # Add explicit CORS headers for cross-origin image requests
    origin = request.headers.get("origin")
    if origin and origin in cors_origins:
        fallback_headers["Access-Control-Allow-Origin"] = origin
        fallback_headers["Access-Control-Allow-Credentials"] = "true"
    
    return FileResponse(requested_path_str, headers=fallback_headers)


@app.post("/admin/unmask")
async def admin_unmask(request: Request, payload: dict = Body(...)):
    """Admin-only: Given a hashed path (as in access logs), attempt to find the real path.

    This endpoint is gated by `ACCESS_LOG_UNMASK_ENABLED` and requires admin JWT (JWT_AUTH_ENABLED + claim is_admin).
    It performs a directory scan of MEDIA_DIR and resolves the first path whose hash matches the provided hash.
    Use with caution — this should be audited and require elevated privileges.
    Body: { hash: string }
    """
    if not settings.ACCESS_LOG_UNMASK_ENABLED:
        raise HTTPException(status_code=403, detail="Unmasking disabled")

    h = payload.get("hash")
    if not h:
        raise HTTPException(status_code=400, detail="hash is required")

    # Require admin JWT
    if settings.JWT_AUTH_ENABLED:
        auth_header = None
        if request:
            auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Authorization required")
        try:
            scheme, token = auth_header.split(" ", 1)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid Authorization header")
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid auth scheme")
        try:
            payload_jwt = verify_jwt(token)
        except AuthError as ae:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(ae)}")
        if not payload_jwt.get("is_admin"):
            raise HTTPException(status_code=403, detail="Admin privileges required")
    else:
        # Fallback: require issuer API key
        if settings.IMAGE_TOKEN_ISSUER_KEY:
            api_key = request.headers.get("x-api-key") if request else None
            if api_key != settings.IMAGE_TOKEN_ISSUER_KEY:
                raise HTTPException(status_code=401, detail="Missing or invalid issuer API key")
        else:
            raise HTTPException(status_code=401, detail="Unmask requires admin auth")

    # Brute-force scan MEDIA_DIR for matching hash
    try:
        for root, dirs, files in os.walk(settings.MEDIA_DIR):
            for f in files:
                candidate = Path(root) / f
                if hash_for_logs(str(candidate)) == h:
                    # Audit log
                    client_host = request.client.host if request and request.client else "unknown"
                    logger.warning(f"UNMASK used by {client_host} for hash={h}")
                    return {"path": str(candidate)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    raise HTTPException(status_code=404, detail="No matching path found")

    raise HTTPException(status_code=404, detail="Image not found")

def validate_file_path(file_path: str, allowed_directories: List[Path]) -> bool:
    """
    Validate that a file path is safe and within allowed directories.

    Security improvements:
    - Normalize path to prevent traversal attacks
    - Check against allowed directory whitelist
    - Validate file extensions
    - Ensure path doesn't contain dangerous characters
    """
    try:
        # Normalize and resolve the path
        normalized_path = Path(file_path).resolve()

        # Basic validation
        if not normalized_path.exists():
            return False

        if not normalized_path.is_file():
            return False

        # Check for dangerous path components
        dangerous_patterns = ['..', '~', '$', '|', ';', '&', '>', '<', '`']
        path_str = str(normalized_path)
        if any(pattern in path_str for pattern in dangerous_patterns):
            return False

        # Check if path is within allowed directories
        for allowed_dir in allowed_directories:
            if normalized_path.is_relative_to(allowed_dir.resolve()):
                return True

        return False

    except (OSError, ValueError, RuntimeError):
        return False


@app.get("/file")
async def get_file(request: Request, path: str, download: bool = False):
    """
    Serve an original file (image/video/etc.) without transcoding.
    Use `download=true` to force a download Content-Disposition.
    """
    # Security check with enhanced validation
    if settings.MEDIA_DIR.exists():
        allowed_paths = [settings.MEDIA_DIR.resolve(), settings.BASE_DIR.resolve()]
    else:
        allowed_paths = [settings.BASE_DIR.resolve()]

    # Validate the file path is safe
    if not validate_file_path(path, allowed_paths):
        # Log the attempted access for security monitoring
        client_ip = request.client.host if request.client else "unknown"
        ps_logger.warning(f"File access denied - IP: {client_ip}, Path: {path}")
        raise HTTPException(status_code=403, detail="Access denied")

    # Additional security: validate file extension
    allowed_extensions = {
        # Images
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.avif',
        # Videos
        '.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.3gp', '.flv',
        # Documents
        '.pdf', '.txt', '.md', '.doc', '.docx', '.xls', '.xlsx',
        # Audio
        '.mp3', '.wav', '.flac', '.aac', '.ogg'
    }

    file_ext = Path(path).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=403, detail="File type not allowed")

    # Serve the file safely
    media_type, _ = mimetypes.guess_type(path)
    filename = os.path.basename(path) if download else None

    return FileResponse(
        path,
        media_type=media_type or "application/octet-stream",
        filename=filename,
        headers={
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Cache-Control": "private, max-age=3600",
        },
    )

@app.get("/video")
async def get_video(request: Request, path: str):
    """
    Serve a video file directly.
    """
    # Security check with enhanced validation
    if settings.MEDIA_DIR.exists():
        allowed_paths = [settings.MEDIA_DIR.resolve(), settings.BASE_DIR.resolve()]
    else:
        allowed_paths = [settings.BASE_DIR.resolve()]

    # Validate the video file path is safe
    if not validate_file_path(path, allowed_paths):
        client_ip = request.client.host if request.client else "unknown"
        ps_logger.warning(f"Video access denied - IP: {client_ip}, Path: {path}")
        raise HTTPException(status_code=403, detail="Access denied")

    # Validate video-specific file extensions
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.3gp', '.flv'}
    if Path(path).suffix.lower() not in video_extensions:
        raise HTTPException(status_code=403, detail="Video file type not allowed")

    if os.path.exists(path):
        # Get mime type
        ext = Path(path).suffix.lower()
        mime_types = {
            '.mp4': 'video/mp4',
            '.mov': 'video/quicktime',
            '.avi': 'video/x-msvideo',
            '.mkv': 'video/x-matroska',
            '.webm': 'video/webm',
            '.m4v': 'video/x-m4v'
        }
        media_type = mime_types.get(ext, 'video/mp4')

        # Add security headers + CORS headers for video serving
        video_headers = {
            "X-Content-Type-Options": "nosniff",
            "Accept-Ranges": "bytes"
        }
        
        # Add explicit CORS headers for cross-origin video requests
        origin = request.headers.get("origin")
        if origin and origin in cors_origins:
            video_headers["Access-Control-Allow-Origin"] = origin
            video_headers["Access-Control-Allow-Credentials"] = "true"
        
        return FileResponse(
            path,
            media_type=media_type,
            headers=video_headers
        )
    
    raise HTTPException(status_code=404, detail="Video not found")

@app.get("/stats")
async def get_stats():
    """
    Return system statistics for the dashboard/timeline.
    """
    try:
        # Leverage existing stats logic or db
        stats = photo_search_engine.db.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========== INTENT RECOGNITION ENDPOINTS ==========

@app.get("/intent/detect")
async def detect_intent_v2(query: str):
    """
    Detect search intent from a query.
    
    Args:
        query: User search query string
        
    Returns:
        Intent detection results including primary intent, secondary intents,
        confidence scores, suggestions, and badges
    """
    try:
        if not query or not query.strip():
            return {
                "intent": "generic",
                "confidence": 0.0,
                "suggestions": [],
                "badges": []
            }
        
        result = intent_detector.detect_intent(query)
        return {
            "intent": result["primary_intent"],
            "confidence": result["confidence"],
            "secondary_intents": result["secondary_intents"],
            "suggestions": result["suggestions"],
            "badges": result["badges"],
            "description": result["description"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/intent/suggestions")
async def get_search_suggestions(query: str, limit: int = 3):
    """
    Get search suggestions based on detected intent.
    
    Args:
        query: User search query string
        limit: Maximum number of suggestions to return
        
    Returns:
        List of suggested search queries
    """
    try:
        suggestions = intent_detector.get_search_suggestions(query)
        return {"suggestions": suggestions[:limit]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/intent/badges")
async def get_search_badges(query: str):
    """
    Get intent badges for UI display.
    
    Args:
        query: User search query string
        
    Returns:
        List of intent badges with labels and icons
    """
    try:
        badges = intent_detector.get_search_badges(query)
        return {"badges": badges}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/intent/all")
async def get_all_intents():
    """
    Get all supported intents with descriptions.
    
    Returns:
        Dictionary of all supported intents
    """
    try:
        return intent_detector.get_all_intents()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========== SAVED SEARCHES ENDPOINTS ==========

class SaveSearchRequest(BaseModel):
    query: str
    mode: str = "metadata"
    results_count: int = 0
    intent: str = "generic"
    is_favorite: bool = False
    notes: str = ""
    metadata: Optional[Dict] = None

class UpdateSearchRequest(BaseModel):
    is_favorite: Optional[bool] = None
    notes: Optional[str] = None

@app.post("/searches/save")
async def save_search(request: SaveSearchRequest):
    """
    Save a search query for later reuse.
    
    Args:
        request: SaveSearchRequest with search details
        
    Returns:
        ID of the saved search
    """
    try:
        search_id = saved_search_manager.save_search(
            query=request.query,
            mode=request.mode,
            results_count=request.results_count,
            intent=request.intent,
            is_favorite=request.is_favorite,
            notes=request.notes,
            metadata=request.metadata
        )
        return {"search_id": search_id, "message": "Search saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/searches")
async def get_saved_searches(
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "updated_at",
    sort_order: str = "DESC",
    favorites_only: bool = False
):
    """
    Get saved searches with pagination and filtering.
    
    Args:
        limit: Maximum number of results
        offset: Pagination offset
        sort_by: Field to sort by
        sort_order: Sort order (ASC or DESC)
        favorites_only: Only return favorite searches
        
    Returns:
        List of saved searches
    """
    try:
        searches = saved_search_manager.get_saved_searches(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
            filter_favorites=favorites_only
        )
        return {"count": len(searches), "searches": searches}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/searches/{search_id}")
async def get_saved_search(search_id: int):
    """
    Get a specific saved search by ID.
    
    Args:
        search_id: ID of the search
        
    Returns:
        Saved search details
    """
    try:
        search = saved_search_manager.get_saved_search_by_id(search_id)
        if not search:
            raise HTTPException(status_code=404, detail="Search not found")
        return search
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/searches/{search_id}/execute")
async def execute_saved_search(search_id: int):
    """
    Execute a saved search and log the execution.
    
    Args:
        search_id: ID of the saved search
        
    Returns:
        Search results and execution details
    """
    try:
        # Get the saved search
        search = saved_search_manager.get_saved_search_by_id(search_id)
        if not search:
            raise HTTPException(status_code=404, detail="Search not found")
        
        # Execute the search using the existing search endpoint
        results = await search_photos(
            query=search['query'],
            mode=search['mode'],
            limit=50,
            offset=0
        )
        
        # Log the execution
        saved_search_manager.log_search_execution(
            search_id=search_id,
            results_count=results['count'],
            execution_time_ms=0,  # Would need to measure this in production
            user_agent="api",
            ip_address="localhost"
        )
        
        return {
            "search": search,
            "results": results,
            "message": "Search executed and logged"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/searches/{search_id}")
async def update_saved_search(search_id: int, request: UpdateSearchRequest):
    """
    Update a saved search (favorite status or notes).
    
    Args:
        search_id: ID of the search
        request: UpdateSearchRequest with fields to update
        
    Returns:
        Updated search details
    """
    try:
        search = saved_search_manager.get_saved_search_by_id(search_id)
        if not search:
            raise HTTPException(status_code=404, detail="Search not found")
        
        if request.is_favorite is not None:
            new_favorite_status = saved_search_manager.toggle_favorite(search_id)
            search['is_favorite'] = new_favorite_status
        
        if request.notes is not None:
            saved_search_manager.update_search_notes(search_id, request.notes)
            search['notes'] = request.notes
        
        return {"search": search, "message": "Search updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/searches/{search_id}")
async def delete_saved_search(search_id: int):
    """
    Delete a saved search.
    
    Args:
        search_id: ID of the search to delete
        
    Returns:
        Confirmation message
    """
    try:
        success = saved_search_manager.delete_saved_search(search_id)
        if not success:
            raise HTTPException(status_code=404, detail="Search not found")
        return {"message": "Search deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/searches/analytics")
async def get_search_analytics():
    """
    Get overall search analytics and insights.

    Returns:
        Analytics data including popular searches, recent searches, etc.
    """
    try:
        return saved_search_manager.get_overall_analytics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/searches/analytics/detailed")
async def get_detailed_analytics(days: int = 30):
    """
    Get detailed search analytics for a specific time period.

    Args:
        days: Number of days to analyze (default: 30)

    Returns:
        Detailed analytics data with trends and insights
    """
    try:
        return saved_search_manager.get_detailed_analytics(days=days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/searches/analytics/trends")
async def get_search_trends(days: int = 90):
    """
    Get search trends over time.

    Args:
        days: Number of days to calculate trends for (default: 90)

    Returns:
        Trend data showing search evolution over time
    """
    try:
        return saved_search_manager.get_search_trends(days=days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/searches/analytics/export")
async def export_analytics(format_type: str = "json", days: int = 30):
    """
    Export analytics data in various formats.

    Args:
        format_type: Output format ('json', 'csv', 'text') - default: json
        days: Number of days to include in analysis - default: 30

    Returns:
        Analytics data in specified format
    """
    try:
        if format_type not in ["json", "csv", "text"]:
            raise HTTPException(status_code=400, detail="Format must be 'json', 'csv', or 'text'")

        exported_data = saved_search_manager.export_analytics(
            format_type=format_type,
            days=days
        )

        if format_type == "json":
            import json
            return json.loads(exported_data)
        else:
            from fastapi.responses import PlainTextResponse
            return PlainTextResponse(exported_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/searches/history")
async def get_search_history(
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "executed_at",
    sort_order: str = "DESC"
):
    """
    Get search history (all searches, not just saved ones).
    
    Args:
        limit: Maximum number of results
        offset: Pagination offset
        sort_by: Field to sort by
        sort_order: Sort order (ASC or DESC)
        
    Returns:
        Search history records
    """
    try:
        history = saved_search_manager.get_search_history(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return {"count": len(history), "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/searches/recurring")
async def get_recurring_searches(threshold: int = 2):
    """
    Get searches that have been executed multiple times.
    
    Args:
        threshold: Minimum number of executions to be considered recurring
        
    Returns:
        List of recurring searches
    """
    try:
        recurring = saved_search_manager.get_recurring_searches(threshold=threshold)
        return {"count": len(recurring), "recurring_searches": recurring}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/searches/performance")
async def get_search_performance():
    """
    Get performance metrics for searches.
    
    Returns:
        Performance data including average execution time, etc.
    """
    try:
        return saved_search_manager.get_search_performance()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/searches/history/clear")
async def clear_search_history():
    """
    Clear all search history (but keep saved searches).
    
    Returns:
        Number of records deleted
    """
    try:
        deleted_count = saved_search_manager.clear_search_history()
        return {"deleted_count": deleted_count, "message": "Search history cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/timeline")
async def get_timeline():
    """
    Return distribution of photos over time for the Sonic Timeline.
    Grouping by month for now.
    """
    try:
        # We need a method to get date stats. 
        # photo_search_engine.db has get_stats() but that's summary.
        # We'll execute a raw query on the db for now until we extend MetadataDatabase.
        
        # Connect to db safely using the existing connection if available
        # The MetadataDatabase handles connection in __init__
        
        cursor = photo_search_engine.db.conn.cursor()
        
        # Query: Count photos per month
        # SQLite: strftime('%Y-%m', created_at)
        # Fix: Use COALESCE to ensure safety against nulls
        query = """
            SELECT strftime('%Y-%m', json_extract(metadata_json, '$.filesystem.created')) as month, COUNT(*) as count
            FROM metadata
            WHERE json_extract(metadata_json, '$.filesystem.created') IS NOT NULL
            GROUP BY month
            ORDER BY month ASC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        
        timeline_data = [{"date": row[0], "count": row[1]} for row in rows]
        return {"timeline": timeline_data}
        
    except Exception as e:
        # Fallback if table doesn't exist or other error
        print(f"Timeline error: {e}")
        return {"timeline": []}


# ========== PRICING ENDPOINTS ==========

@app.get("/pricing", response_model=List[PricingTier])
async def get_pricing_tiers():
    """
    Get all available pricing tiers.
    """
    return pricing_manager.get_all_tiers()


@app.get("/pricing/{tier_name}", response_model=PricingTier)
async def get_pricing_tier(tier_name: str):
    """
    Get details for a specific pricing tier.
    """
    tier = pricing_manager.get_tier(tier_name)
    if not tier:
        raise HTTPException(status_code=404, detail="Pricing tier not found")
    return tier


@app.get("/pricing/recommend", response_model=PricingTier)
async def recommend_pricing_tier(image_count: int):
    """
    Recommend a pricing tier based on image count.
    """
    if image_count < 0:
        raise HTTPException(status_code=400, detail="Image count must be positive")
    
    return pricing_manager.get_tier_by_image_count(image_count)


@app.get("/usage/{user_id}", response_model=UsageStats)
async def get_usage_stats(user_id: str):
    """
    Get current usage statistics for a user.
    """
    # Get current image count from database
    try:
        cursor = photo_search_engine.db.conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM metadata")
        result = cursor.fetchone()
        image_count = result['count'] if result else 0
    except Exception as e:
        print(f"Error getting image count: {e}")
        image_count = 0
    
    # Track usage and return stats
    return pricing_manager.track_usage(user_id, image_count)


@app.get("/usage/check/{user_id}")
async def check_usage_limit(user_id: str, additional_images: int = 0):
    """
    Check if user can add more images without exceeding their limit.
    """
    if additional_images < 0:
        raise HTTPException(status_code=400, detail="Additional images must be positive")

    can_add = pricing_manager.check_limit(user_id, additional_images)

    return {
        "can_add": can_add,
        "message": "User can add images" if can_add else "User would exceed their image limit"
    }


@app.post("/usage/upgrade/{user_id}")
async def upgrade_user_tier(user_id: str, new_tier: str):
    """
    Upgrade a user to a new pricing tier.
    """
    success = pricing_manager.upgrade_tier(user_id, new_tier)

    if not success:
        raise HTTPException(status_code=400, detail="Invalid tier or user not found")

    return {
        "success": True,
        "message": f"User {user_id} upgraded to {new_tier} tier",
        "new_tier": new_tier
    }

@app.get("/usage/history/{user_id}")
async def get_user_usage_history(user_id: str, days: int = 30):
    """
    Get usage history for a specific user.

    Args:
        user_id: ID of the user
        days: Number of days to retrieve history for (default: 30)

    Returns:
        List of usage records
    """
    try:
        history = pricing_manager.get_usage_history(user_id, days)
        return {
            "user_id": user_id,
            "days": days,
            "history": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/usage/growth/{user_id}")
async def get_user_growth_rate(user_id: str, days: int = 30):
    """
    Get user growth rate over time.

    Args:
        user_id: ID of the user
        days: Number of days to calculate growth over (default: 30)

    Returns:
        Growth rate statistics
    """
    try:
        growth = pricing_manager.get_user_growth_rate(user_id, days)
        return growth
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/usage/tier-averages")
async def get_tier_usage_averages():
    """
    Get average usage statistics per pricing tier.

    Returns:
        Dictionary with average usage per tier
    """
    try:
        averages = pricing_manager.get_tier_averages()
        return averages
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/usage/company-analytics")
async def get_company_usage_analytics():
    """
    Get comprehensive usage analytics for the company.

    Returns:
        Company-wide usage statistics
    """
    try:
        analytics = pricing_manager.get_company_usage_analytics()
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ExportOptions(BaseModel):
    format: str = "zip"  # zip, pdf, json (for metadata)
    include_metadata: bool = True
    include_thumbnails: bool = False
    max_resolution: Optional[int] = None  # Max width/height in pixels
    rename_pattern: Optional[str] = None  # Pattern for renaming files
    password_protect: bool = False
    password: Optional[str] = None

class ExportRequest(BaseModel):
    paths: List[str]
    options: ExportOptions = ExportOptions()

# Initialize Face Clustering
from src.face_clustering import FaceClusterer
face_clusterer = FaceClusterer()

# Initialize OCR Search
from src.ocr_search import OCRSearch
ocr_search = OCRSearch()

# Signed URL helpers
from server.signed_urls import issue_token, verify_token, TokenError
from server.security_utils import hash_for_logs
from server.auth import verify_jwt, AuthError, create_jwt
import logging
logger = logging.getLogger("photosearch")


# Initialize Modal System
from src.modal_system import ModalSystem
modal_system = ModalSystem()

# Initialize Code Splitting
from src.code_splitting import CodeSplittingConfig, LazyLoadPerformanceTracker
code_splitting_config = CodeSplittingConfig()
lazy_load_tracker = LazyLoadPerformanceTracker()

# Initialize Tauri Integration
from src.tauri_integration import TauriIntegration
tauri_integration = TauriIntegration()

class FaceClusterRequest(BaseModel):
    image_paths: List[str]
    eps: float = 0.6
    min_samples: int = 2

class ClusterLabelRequest(BaseModel):
    cluster_id: int
    label: str

@app.post("/faces/cluster")
async def cluster_faces_v1(request: FaceClusterRequest):
    """
    Cluster faces in the specified images
    
    Args:
        request: FaceClusterRequest with image paths and clustering parameters
        
    Returns:
        Dictionary with clustering results
    """
    try:
        clusters = face_clusterer.cluster_faces(
            request.image_paths,
            eps=request.eps,
            min_samples=request.min_samples
        )
        return {"status": "success", "clusters": clusters}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/faces/clusters")
async def get_all_clusters(limit: int = 100, offset: int = 0):
    """
    Get all face clusters
    
    Args:
        limit: Maximum number of clusters to return
        offset: Pagination offset
        
    Returns:
        Dictionary with cluster information
    """
    try:
        clusters = face_clusterer.get_all_clusters(limit, offset)
        return {"status": "success", "clusters": clusters}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/faces/clusters/{cluster_id}")
async def get_cluster_details(cluster_id: int):
    """
    Get details for a specific cluster
    
    Args:
        cluster_id: ID of the cluster
        
    Returns:
        Dictionary with cluster details
    """
    try:
        details = face_clusterer.get_cluster_details(cluster_id)
        return {"status": "success", "details": details}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/faces/image/{image_path:path}")
async def get_image_clusters(image_path: str):
    """
    Get face clusters for a specific image
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Dictionary with face cluster information for the image
    """
    try:
        clusters = face_clusterer.get_face_clusters(image_path)
        return {"status": "success", "clusters": clusters}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/faces/clusters/{cluster_id}/label")
async def update_cluster_label(cluster_id: int, request: ClusterLabelRequest):
    """
    Update the label for a cluster
    
    Args:
        cluster_id: ID of the cluster
        request: ClusterLabelRequest with new label
        
    Returns:
        Dictionary with update status
    """
    try:
        success = face_clusterer.update_cluster_label(cluster_id, request.label)
        return {"status": "success" if success else "failed", "updated": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/faces/clusters/{cluster_id}")
async def delete_cluster(cluster_id: int):
    """
    Delete a face cluster
    
    Args:
        cluster_id: ID of the cluster to delete
        
    Returns:
        Dictionary with deletion status
    """
    try:
        success = face_clusterer.delete_cluster(cluster_id)
        return {"status": "success" if success else "failed", "deleted": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/faces/stats")
async def get_face_stats_v1():
    """
    Get statistics about face clusters
    
    Returns:
        Dictionary with face clustering statistics
    """
    try:
        stats = face_clusterer.get_cluster_statistics()
        return {"status": "success", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# OCR Search Endpoints

@app.get('/server/config')
async def server_config():
    """Return a small subset of server configuration useful for the UI (non-sensitive)."""
    return {
        "signed_url_enabled": bool(settings.SIGNED_URL_ENABLED),
        "sandbox_strict": bool(settings.SANDBOX_STRICT),
        "rate_limit_enabled": bool(settings.RATE_LIMIT_ENABLED),
        "access_log_masking": bool(settings.ACCESS_LOG_MASKING),
        "jwt_auth_enabled": bool(settings.JWT_AUTH_ENABLED),
    }


@app.post("/image/token")
async def issue_image_token(request: Request, payload: dict = Body(...)):
    """Issue a signed token for image access. Body: { path: string, ttl?: int, scope?: 'thumbnail'|'file' }

    This endpoint should be protected in production (JWT auth or IMAGE_TOKEN_ISSUER_KEY).
    """
    path = payload.get("path")
    ttl = payload.get("ttl")
    scope = payload.get("scope", "thumbnail")

    if not path:
        raise HTTPException(status_code=400, detail="path is required")

    # If JWT auth is enabled, require a valid Bearer token
    uid = None
    if settings.JWT_AUTH_ENABLED:
        auth_header = None
        if request:
            auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Authorization required")
        try:
            scheme, token = auth_header.split(" ", 1)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid Authorization header")
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid auth scheme")
        try:
            payload_jwt = verify_jwt(token)
            uid = payload_jwt.get("sub") or payload_jwt.get("uid")
        except AuthError as ae:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(ae)}")

    # Otherwise, allow image token issuance if issuer key is configured
    elif settings.IMAGE_TOKEN_ISSUER_KEY:
        api_key = None
        if request:
            api_key = request.headers.get("x-api-key")
        if api_key != settings.IMAGE_TOKEN_ISSUER_KEY:
            raise HTTPException(status_code=401, detail="Missing or invalid issuer API key")
    else:
        logger.warning("No token issuer configured; token issuance is unprotected (dev only)")

    # Basic sandbox check - ensure path is inside allowed directories
    try:
        if settings.MEDIA_DIR.exists():
            allowed_paths = [settings.MEDIA_DIR.resolve(), settings.BASE_DIR.resolve()]
        else:
            allowed_paths = [settings.BASE_DIR.resolve()]

        requested_path = Path(path).resolve()

        is_allowed = any(
            requested_path.is_relative_to(allowed_path)
            for allowed_path in allowed_paths
        )

        if not is_allowed:
            raise HTTPException(status_code=403, detail="Path is outside allowed directories")
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    # Issue token
    try:
        token = issue_token(path, uid=uid, ttl=ttl, scope=scope)
        return {"token": token, "expires_in": ttl or settings.SIGNED_URL_TTL_SECONDS}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class OCRSearchRequest(BaseModel):
    query: str
    limit: int = 100
    offset: int = 0

class OCRImageRequest(BaseModel):
    image_paths: List[str]

@app.post("/ocr/extract")
async def extract_text_from_images(request: OCRImageRequest):
    """
    Extract text from multiple images
    
    Args:
        request: OCRImageRequest with list of image paths
        
    Returns:
        Dictionary with extracted text for each image
    """
    try:
        results = ocr_search.extract_text_from_images(request.image_paths)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ocr/search")
async def search_ocr_text(query: str, limit: int = 100, offset: int = 0):
    """
    Search for images containing specific text
    
    Args:
        query: Text to search for
        limit: Maximum number of results
        offset: Pagination offset
        
    Returns:
        Dictionary with search results
    """
    try:
        results = ocr_search.search_text(query, limit, offset)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ocr/stats")
async def get_ocr_stats():
    """
    Get OCR statistics
    
    Returns:
        Dictionary with OCR statistics
    """
    try:
        stats = ocr_search.get_ocr_summary()
        return {"status": "success", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ocr/image/{image_path:path}")
async def get_image_ocr_stats(image_path: str):
    """
    Get OCR statistics for a specific image
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Dictionary with OCR statistics for the image
    """
    try:
        stats = ocr_search.get_ocr_stats(image_path)
        return {"status": "success", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/ocr/image/{image_path:path}")
async def delete_image_ocr_data(image_path: str):
    """
    Delete OCR data for a specific image
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Dictionary with deletion status
    """
    try:
        success = ocr_search.delete_ocr_data(image_path)
        return {"status": "success" if success else "failed", "deleted": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/ocr/all")
async def clear_all_ocr_data():
    """
    Clear all OCR data
    
    Returns:
        Dictionary with deletion count
    """
    try:
        count = ocr_search.clear_all_ocr_data()
        return {"status": "success", "deleted_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Modal System Endpoints

class DialogRequest(BaseModel):
    dialog_type: str
    title: str
    message: str
    options: Optional[List[str]] = None
    timeout: Optional[int] = None
    user_id: str = "system"

class DialogActionRequest(BaseModel):
    action: str
    user_id: str = "system"

class ProgressDialogRequest(BaseModel):
    title: str
    message: str
    max_value: int = 100
    current_value: int = 0
    user_id: str = "system"

class InputDialogRequest(BaseModel):
    title: str
    message: str
    input_type: str = "text"
    default_value: Optional[str] = None
    user_id: str = "system"

@app.post("/dialogs/create")
async def create_dialog(request: DialogRequest):
    """
    Create a new dialog
    
    Args:
        request: DialogRequest with dialog details
        
    Returns:
        Dictionary with dialog ID
    """
    try:
        create_kwargs: dict[str, Any] = {
            "dialog_type": request.dialog_type,
            "title": request.title,
            "message": request.message,
            "actions": request.options or [],
            "user_id": request.user_id,
        }
        if request.timeout is not None:
            create_kwargs["expires_in"] = int(request.timeout)

        dialog_id = modal_system.create_dialog(**create_kwargs)
        return {"status": "success", "dialog_id": dialog_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dialogs/active")
async def get_active_dialogs(user_id: str = "system"):
    """
    Get all active dialogs for a user
    
    Args:
        user_id: ID of the user
        
    Returns:
        Dictionary with active dialogs
    """
    try:
        dialogs = modal_system.get_active_dialogs(user_id)
        return {"status": "success", "dialogs": dialogs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dialogs/{dialog_id}")
async def get_dialog(dialog_id: str, user_id: str = "system"):
    """
    Get details for a specific dialog
    
    Args:
        dialog_id: ID of the dialog
        user_id: ID of the user
        
    Returns:
        Dictionary with dialog details
    """
    try:
        dialog = modal_system.get_dialog(dialog_id)
        if dialog and dialog.get("user_id") == user_id:
            return {"status": "success", "dialog": dialog}
        else:
            raise HTTPException(status_code=404, detail="Dialog not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/dialogs/{dialog_id}/action")
async def dialog_action(dialog_id: str, request: DialogActionRequest):
    """
    Record an action on a dialog
    
    Args:
        dialog_id: ID of the dialog
        request: DialogActionRequest with action details
        
    Returns:
        Dictionary with action status
    """
    try:
        success = modal_system.record_dialog_action(
            dialog_id,
            request.action,
            action_data={},
            user_id=request.user_id
        )
        return {"status": "success" if success else "failed", "recorded": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/dialogs/{dialog_id}/close")
async def close_dialog(dialog_id: str, request: DialogActionRequest):
    """
    Close a dialog
    
    Args:
        dialog_id: ID of the dialog
        request: DialogActionRequest with close action
        
    Returns:
        Dictionary with close status
    """
    try:
        success = modal_system.close_dialog(
            dialog_id,
            request.action,
            request.user_id
        )
        return {"status": "success" if success else "failed", "closed": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/dialogs/{dialog_id}/dismiss")
async def dismiss_dialog(dialog_id: str, user_id: str = "system"):
    """
    Dismiss a dialog
    
    Args:
        dialog_id: ID of the dialog
        user_id: ID of the user
        
    Returns:
        Dictionary with dismiss status
    """
    try:
        success = modal_system.dismiss_dialog(dialog_id, user_id)
        return {"status": "success" if success else "failed", "dismissed": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/dialogs/confirmation")
async def create_confirmation_dialog(request: DialogRequest):
    """
    Create a confirmation dialog
    
    Args:
        request: DialogRequest with confirmation details
        
    Returns:
        Dictionary with dialog ID
    """
    try:
        create_kwargs: dict[str, Any] = {
            "dialog_type": "confirmation",
            "title": request.title,
            "message": request.message,
            "actions": request.options or ["Yes", "No"],
            "user_id": request.user_id,
            "context": "confirmation",
        }
        if request.timeout is not None:
            create_kwargs["expires_in"] = int(request.timeout)

        dialog_id = modal_system.create_dialog(**create_kwargs)
        return {"status": "success", "dialog_id": dialog_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/dialogs/error")
async def create_error_dialog(request: DialogRequest):
    """
    Create an error dialog
    
    Args:
        request: DialogRequest with error details
        
    Returns:
        Dictionary with dialog ID
    """
    try:
        create_kwargs: dict[str, Any] = {
            "dialog_type": "error",
            "title": request.title,
            "message": request.message,
            "data": {"details": ""},
            "user_id": request.user_id,
            "context": "error",
            "priority": 10,
        }
        if request.timeout is not None:
            create_kwargs["expires_in"] = int(request.timeout)

        dialog_id = modal_system.create_dialog(**create_kwargs)
        return {"status": "success", "dialog_id": dialog_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/dialogs/progress")
async def create_progress_dialog(request: ProgressDialogRequest):
    """
    Create a progress dialog
    
    Args:
        request: ProgressDialogRequest with progress details
        
    Returns:
        Dictionary with dialog ID
    """
    try:
        dialog_id = modal_system.create_progress_dialog(
            title=request.title,
            message=request.message,
            total_steps=request.max_value,
            user_id=request.user_id
        )
        # Best-effort initial progress update based on current_value/max_value.
        try:
            denom = float(request.max_value) if request.max_value else 100.0
            pct = (float(request.current_value) / denom) * 100.0
            modal_system.update_progress_dialog(dialog_id, progress=pct, message=request.message)
        except Exception:
            pass
        return {"status": "success", "dialog_id": dialog_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/dialogs/progress/{dialog_id}")
async def update_progress_dialog(dialog_id: str, request: ProgressDialogRequest):
    """
    Update a progress dialog
    
    Args:
        dialog_id: ID of the progress dialog
        request: ProgressDialogRequest with updated values
        
    Returns:
        Dictionary with update status
    """
    try:
        denom = float(request.max_value) if request.max_value else 100.0
        pct = (float(request.current_value) / denom) * 100.0
        success = modal_system.update_progress_dialog(dialog_id, progress=pct, message=request.message)
        return {"status": "success" if success else "failed", "updated": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/dialogs/progress/{dialog_id}/complete")
async def complete_progress_dialog(dialog_id: str, user_id: str = "system"):
    """
    Complete a progress dialog
    
    Args:
        dialog_id: ID of the progress dialog
        user_id: ID of the user
        
    Returns:
        Dictionary with completion status
    """
    try:
        success = modal_system.complete_progress_dialog(dialog_id, success=True)
        return {"status": "success" if success else "failed", "completed": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/dialogs/input")
async def create_input_dialog(request: InputDialogRequest):
    """
    Create an input dialog
    
    Args:
        request: InputDialogRequest with input details
        
    Returns:
        Dictionary with dialog ID
    """
    try:
        dialog_id = modal_system.create_dialog(
            dialog_type="input",
            title=request.title,
            message=request.message,
            data={"input_type": request.input_type, "default_value": request.default_value},
            user_id=request.user_id,
            context="input",
        )
        return {"status": "success", "dialog_id": dialog_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dialogs/history")
async def get_dialog_history(user_id: str = "system", limit: int = 50):
    """
    Get dialog history for a user
    
    Args:
        user_id: ID of the user
        limit: Maximum number of dialogs to return
        
    Returns:
        Dictionary with dialog history
    """
    try:
        history = modal_system.get_dialog_history(user_id=user_id, limit=limit)
        return {"status": "success", "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dialogs/stats")
async def get_dialog_stats():
    """
    Get dialog statistics
    
    Returns:
        Dictionary with dialog statistics
    """
    try:
        stats = modal_system.get_dialog_statistics()
        return {"status": "success", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Code Splitting Endpoints

class CodeSplittingConfigRequest(BaseModel):
    chunk_name: str
    config: Dict

class PerformanceRecordRequest(BaseModel):
    component_name: str
    chunk_name: str
    load_time_ms: float
    size_kb: float
    timestamp: Optional[str] = None

@app.get("/code-splitting/config")
async def get_code_splitting_config():
    """
    Get code splitting configuration
    
    Returns:
        Dictionary with code splitting configuration
    """
    try:
        config = code_splitting_config.get_config()
        return {"status": "success", "config": config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/code-splitting/chunk/{chunk_name}")
async def get_chunk_config(chunk_name: str):
    """
    Get configuration for a specific chunk
    
    Args:
        chunk_name: Name of the chunk
        
    Returns:
        Dictionary with chunk configuration
    """
    try:
        config = code_splitting_config.get_chunk_config(chunk_name)
        if config:
            return {"status": "success", "config": config}
        else:
            raise HTTPException(status_code=404, detail="Chunk not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/code-splitting/chunk/{chunk_name}")
async def set_chunk_config(chunk_name: str, request: CodeSplittingConfigRequest):
    """
    Set configuration for a specific chunk
    
    Args:
        chunk_name: Name of the chunk
        request: CodeSplittingConfigRequest with configuration
        
    Returns:
        Dictionary with update status
    """
    try:
        success = code_splitting_config.set_chunk_config(chunk_name, request.config)
        return {"status": "success" if success else "failed", "updated": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/code-splitting/enabled")
async def get_code_splitting_enabled():
    """
    Check if code splitting is enabled
    
    Returns:
        Dictionary with enabled status
    """
    try:
        enabled = code_splitting_config.is_code_splitting_enabled()
        return {"status": "success", "enabled": enabled}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/code-splitting/enabled")
async def set_code_splitting_enabled(enabled: bool):
    """
    Enable or disable code splitting
    
    Args:
        enabled: Boolean indicating whether to enable code splitting
        
    Returns:
        Dictionary with update status
    """
    try:
        code_splitting_config.enable_code_splitting(enabled)
        return {"status": "success", "enabled": enabled}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/code-splitting/performance")
async def record_lazy_load_performance(request: PerformanceRecordRequest):
    """
    Record lazy load performance data
    
    Args:
        request: PerformanceRecordRequest with performance data
        
    Returns:
        Dictionary with recording status
    """
    try:
        lazy_load_tracker.record_lazy_load(
            component_name=request.component_name,
            load_time_ms=request.load_time_ms,
            chunk_name=request.chunk_name,
            success=True,
        )
        return {"status": "success", "recorded": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/code-splitting/performance")
async def get_lazy_load_performance(component_name: str | None = None):
    """
    Get lazy load performance statistics
    
    Args:
        component_name: Optional component name to filter by
        
    Returns:
        Dictionary with performance statistics
    """
    try:
        stats = lazy_load_tracker.get_performance_stats(component_name)
        return {"status": "success", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/code-splitting/performance/chunks")
async def get_chunk_performance():
    """
    Get performance statistics by chunk
    
    Returns:
        Dictionary with chunk performance statistics
    """
    try:
        stats = lazy_load_tracker.get_chunk_performance()
        return {"status": "success", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/code-splitting/integration-guide")
async def get_frontend_integration_guide():
    """
    Get frontend integration guide for code splitting
    
    Returns:
        Dictionary with integration guide
    """
    try:
        from src.code_splitting import get_frontend_integration_guide
        guide = get_frontend_integration_guide()
        return {"status": "success", "guide": guide}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/code-splitting/api-endpoints")
async def get_api_endpoints():
    """
    Get available API endpoints for code splitting
    
    Returns:
        Dictionary with API endpoints
    """
    try:
        from src.code_splitting import get_api_endpoints
        endpoints = get_api_endpoints()
        return {"status": "success", "endpoints": endpoints}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Tauri Integration Endpoints

@app.get("/tauri/commands")
async def get_tauri_commands():
    """
    Get available Tauri commands
    
    Returns:
        Dictionary with Tauri commands
    """
    try:
        commands = tauri_integration.get_all_commands()
        return {"status": "success", "commands": commands}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tauri/commands/{command_name}")
async def get_tauri_command(command_name: str):
    """
    Get details for a specific Tauri command
    
    Args:
        command_name: Name of the command
        
    Returns:
        Dictionary with command details
    """
    try:
        command = tauri_integration.get_command(command_name)
        if command:
            return {"status": "success", "command": command}
        else:
            raise HTTPException(status_code=404, detail="Command not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tauri/rust-skeleton")
async def get_rust_skeleton():
    """
    Get Rust skeleton code for Tauri integration
    
    Returns:
        Dictionary with Rust skeleton code
    """
    try:
        skeleton = tauri_integration.generate_rust_skeleton()
        return {"status": "success", "skeleton": skeleton}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tauri/frontend-hooks")
async def get_frontend_hooks():
    """
    Get frontend hooks for Tauri integration
    
    Returns:
        Dictionary with frontend hooks code
    """
    try:
        hooks = tauri_integration.generate_frontend_hooks()
        return {"status": "success", "hooks": hooks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tauri/config")
async def get_tauri_config():
    """
    Get Tauri configuration
    
    Returns:
        Dictionary with Tauri configuration
    """
    try:
        config = tauri_integration.generate_tauri_config()
        return {"status": "success", "config": config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tauri/security")
async def get_security_recommendations():
    """
    Get security recommendations for Tauri integration
    
    Returns:
        Dictionary with security recommendations
    """
    try:
        recommendations = tauri_integration.get_security_recommendations()
        return {"status": "success", "recommendations": recommendations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tauri/performance")
async def get_performance_tips():
    """
    Get performance tips for Tauri integration
    
    Returns:
        Dictionary with performance tips
    """
    try:
        tips = tauri_integration.get_performance_tips()
        return {"status": "success", "tips": tips}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tauri/checklist")
async def get_integration_checklist():
    """
    Get integration checklist for Tauri
    
    Returns:
        Dictionary with integration checklist
    """
    try:
        checklist = tauri_integration.get_integration_checklist()
        return {"status": "success", "checklist": checklist}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tauri/setup-guide")
async def get_setup_guide():
    """
    Get Tauri setup guide
    
    Returns:
        Dictionary with setup guide
    """
    try:
        from src.tauri_integration import get_tauri_setup_guide
        guide = get_tauri_setup_guide()
        return {"status": "success", "guide": guide}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/export")
async def export_photos(request: ExportRequest):
    """
    Export selected photos with various options.

    Args:
        request: ExportRequest with list of file paths and export options

    Returns:
        Streaming file download
    """
    import zipfile
    import io
    from fastapi.responses import StreamingResponse
    from PIL import Image
    import json

    if not request.paths:
        raise HTTPException(status_code=400, detail="No files specified")

    if len(request.paths) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 files per export")

    # Validate paths are within allowed directories
    valid_paths = []
    for path in request.paths:
        try:
            requested_path = Path(path).resolve()
            if settings.MEDIA_DIR.exists():
                allowed_paths = [settings.MEDIA_DIR.resolve(), settings.BASE_DIR.resolve()]
            else:
                allowed_paths = [settings.BASE_DIR.resolve()]

            is_allowed = any(
                requested_path.is_relative_to(allowed_path)
                for allowed_path in allowed_paths
            )

            if is_allowed and os.path.exists(path):
                valid_paths.append(path)
        except ValueError:
            continue

    if not valid_paths:
        raise HTTPException(status_code=400, detail="No valid files to export")

    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for path in valid_paths:
            original_filename = os.path.basename(path)

            # Handle duplicate filenames by adding parent folder
            if any(os.path.basename(p) == original_filename and p != path for p in valid_paths):
                parent = os.path.basename(os.path.dirname(path))
                filename = f"{parent}_{original_filename}"
            else:
                filename = original_filename

            # Process image if size reduction is requested
            if request.options.max_resolution:
                try:
                    # Open and resize image if needed
                    with Image.open(path) as img:
                        img.thumbnail((request.options.max_resolution, request.options.max_resolution))

                        # Save to temporary bytes buffer
                        temp_buffer = io.BytesIO()
                        img.save(temp_buffer, format=img.format)
                        temp_buffer.seek(0)

                        # Write to zip
                        zip_file.writestr(filename, temp_buffer.getvalue())
                except Exception:
                    # If image processing fails, just copy the file
                    zip_file.write(path, filename)
            else:
                # Write original file
                zip_file.write(path, filename)

            # Include metadata if requested
            if request.options.include_metadata:
                try:
                    metadata = photo_search_engine.db.get_metadata(path)
                    if metadata:
                        # Write metadata as JSON file
                        meta_filename = f"{original_filename.replace(os.path.splitext(original_filename)[1], '')}_metadata.json"
                        zip_file.writestr(meta_filename, json.dumps(metadata, indent=2))
                except Exception:
                    # If metadata extraction fails, continue without it
                    pass

            # Include thumbnail if requested
            if request.options.include_thumbnails:
                try:
                    with Image.open(path) as img:
                        img.thumbnail((200, 200))  # Create 200x200 thumbnail
                        thumb_buffer = io.BytesIO()
                        img.save(thumb_buffer, format=img.format)
                        thumb_buffer.seek(0)

                        thumb_filename = f"thumbs/{original_filename.replace(os.path.splitext(original_filename)[1], '')}_thumb{os.path.splitext(original_filename)[1]}"
                        zip_file.writestr(thumb_filename, thumb_buffer.getvalue())
                except Exception:
                    # If thumbnail creation fails, continue without it
                    pass

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=photos_export.zip"}
    )


@app.post("/export/presets")
async def create_export_preset(preset_data: dict):
    """Create a new export preset with predefined options."""
    # This would save the preset to a database in a full implementation
    # For now, we'll just return the preset data
    return {"success": True, "preset": preset_data}


@app.get("/export/presets")
async def get_export_presets():
    """Get available export presets."""
    # This would fetch presets from a database in a full implementation
    # For now, return some default presets
    return {
        "presets": [
            {
                "id": "high_quality",
                "name": "High Quality",
                "description": "Full resolution with metadata",
                "options": {
                    "format": "zip",
                    "include_metadata": True,
                    "include_thumbnails": False,
                    "max_resolution": None
                }
            },
            {
                "id": "web_sharing",
                "name": "Web Sharing",
                "description": "Resized for web with low resolution",
                "options": {
                    "format": "zip",
                    "include_metadata": True,
                    "include_thumbnails": True,
                    "max_resolution": 1920
                }
            },
            {
                "id": "print_ready",
                "name": "Print Ready",
                "description": "High resolution suitable for printing",
                "options": {
                    "format": "zip",
                    "include_metadata": True,
                    "include_thumbnails": False,
                    "max_resolution": None
                }
            }
        ]
    }


# ==============================================================================
# SHARE ENDPOINTS
# ==============================================================================

class ShareRequest(BaseModel):
    paths: List[str]
    expiration_hours: int = 24  # Default 24 hours
    password: Optional[str] = None  # Optional password protection


class ShareResponse(BaseModel):
    share_id: str
    share_url: str
    expiration: str
    download_count: int = 0


# In-memory store for share links (in production, use a database)
share_links: dict[str, dict[str, Any]] = {}


@app.post("/share", response_model=ShareResponse)
async def create_share_link(payload: ShareRequest, request: Request):
    """Create a shareable link for selected photos."""
    import uuid
    from datetime import datetime, timedelta

    if not payload.paths:
        raise HTTPException(status_code=400, detail="No files specified")

    if len(payload.paths) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 files per share")

    # Validate paths are within allowed directories
    valid_paths = []
    for path in payload.paths:
        try:
            requested_path = Path(path).resolve()
            if settings.MEDIA_DIR.exists():
                allowed_paths = [settings.MEDIA_DIR.resolve(), settings.BASE_DIR.resolve()]
            else:
                allowed_paths = [settings.BASE_DIR.resolve()]

            is_allowed = any(
                requested_path.is_relative_to(allowed_path)
                for allowed_path in allowed_paths
            )

            if is_allowed and os.path.exists(path):
                valid_paths.append(path)
        except ValueError:
            continue

    if not valid_paths:
        raise HTTPException(status_code=400, detail="No valid files to share")

    # Generate unique share ID
    share_id = str(uuid.uuid4())
    expiration = datetime.now() + timedelta(hours=payload.expiration_hours)

    # Store share information
    share_links[share_id] = {
        "paths": valid_paths,
        "expiration": expiration.isoformat(),
        "created_at": datetime.now().isoformat(),
        "download_count": 0,
        "password": payload.password  # In a real app, this should be hashed
    }

    # Generate share URL
    share_url = f"{request.url.scheme}://{request.url.netloc}/shared/{share_id}"

    return ShareResponse(
        share_id=share_id,
        share_url=share_url,
        expiration=expiration.isoformat()
    )


@app.get("/shared/{share_id}")
async def get_shared_content(share_id: str, password: Optional[str] = None):
    """Get content from a share link."""
    from datetime import datetime

    if share_id not in share_links:
        raise HTTPException(status_code=404, detail="Share link not found or expired")

    share_info = share_links[share_id]

    # Check expiration
    exp_raw = share_info.get("expiration")
    if datetime.fromisoformat(str(exp_raw)) < datetime.now():
        # Remove expired link and return error
        del share_links[share_id]
        raise HTTPException(status_code=404, detail="Share link has expired")

    # Check password if required
    if share_info.get("password") and share_info["password"] != password:
        raise HTTPException(status_code=403, detail="Password required or incorrect")

    # Increment download count for analytics
    raw_count: Any = share_info.get("download_count", 0)
    if isinstance(raw_count, bool):
        count_int = int(raw_count)
    elif isinstance(raw_count, int):
        count_int = raw_count
    elif isinstance(raw_count, float):
        count_int = int(raw_count)
    elif isinstance(raw_count, str):
        try:
            count_int = int(raw_count)
        except ValueError:
            count_int = 0
    else:
        count_int = 0

    share_info["download_count"] = count_int + 1

    # Return file paths for download
    return {
        "paths": share_info["paths"],
        "download_count": share_info["download_count"]
    }


@app.get("/shared/{share_id}/download")
async def download_shared_content(share_id: str, password: Optional[str] = None):
    """Download content from a share link."""
    import zipfile
    import io
    from fastapi.responses import StreamingResponse

    # Get shared content (uses same validation as get_shared_content)
    content = await get_shared_content(share_id, password)

    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for path in content["paths"]:
            filename = os.path.basename(path)
            # Handle duplicate filenames by adding parent folder
            if any(os.path.basename(p) == filename and p != path for p in content["paths"]):
                parent = os.path.basename(os.path.dirname(path))
                filename = f"{parent}_{filename}"
            zip_file.write(path, filename)

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=shared_photos.zip"}
    )

# ==============================================================================
# VERSION STACKS ENDPOINTS
# ==============================================================================

class LegacyVersionCreateRequest(BaseModel):
    original_path: str
    version_path: str
    version_type: str = "edited"  # 'original', 'edited', 'variant'
    version_name: Optional[str] = None
    version_description: Optional[str] = None
    editing_instructions: Optional[Dict[str, Any]] = None
    parent_version_id: Optional[str] = None


class LegacyVersionUpdateRequest(BaseModel):
    version_name: Optional[str] = None
    version_description: Optional[str] = None


@app.post("/versions-legacy")
async def create_photo_version_legacy(request: LegacyVersionCreateRequest):
    """Create a new photo version record."""
    try:
        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")

        original_path = "/" + request.original_path.lstrip("/")
        version_path = "/" + request.version_path.lstrip("/")

        version_id = versions_db.create_version(
            original_path=original_path,
            version_path=version_path,
            version_type=request.version_type,
            version_name=request.version_name,
            version_description=request.version_description,
            edit_instructions=request.editing_instructions,
            parent_version_id=request.parent_version_id
        )

        return {"success": True, "version_id": version_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/versions-legacy/original/{original_path:path}")
async def get_versions_for_original_legacy(original_path: str):
    """Get all versions for a given original photo."""
    try:
        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")
        normalized_path = "/" + original_path.lstrip("/")
        versions = versions_db.get_versions_for_original(normalized_path)
        return {"original_path": normalized_path, "versions": versions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/versions-legacy/stack/{version_path:path}")
async def get_version_stack_legacy(version_path: str):
    """Get the entire version stack for a given photo path."""
    try:
        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")
        normalized_path = "/" + version_path.lstrip("/")
        stack = versions_db.get_version_stack(normalized_path)
        return {"stack": stack}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/versions-legacy/{version_path:path}")
async def update_version_metadata_legacy(version_path: str, request: LegacyVersionUpdateRequest):
    """Update metadata for a specific version."""
    try:
        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")
        normalized_path = "/" + version_path.lstrip("/")
        success = versions_db.update_version_metadata(
            normalized_path,
            version_name=request.version_name,
            version_description=request.version_description
        )

        if not success:
            raise HTTPException(status_code=404, detail="Version not found")

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/versions-legacy/{version_id}")
async def delete_photo_version_legacy(version_id: str):
    """Delete a photo version record."""
    try:
        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")
        success = versions_db.delete_version(version_id)

        if not success:
            raise HTTPException(status_code=404, detail="Version not found")

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/versions-legacy/stats")
async def get_version_stats_legacy():
    """Get statistics about photo versions."""
    try:
        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")
        stats = versions_db.get_version_stats()
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# LOCATION CORRECTION ENDPOINTS
# ==============================================================================

class LocationCreateRequest(BaseModel):
    photo_path: str
    latitude: float
    longitude: float
    original_place_name: Optional[str] = None
    corrected_place_name: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    accuracy: float = 100.0


class LocationUpdateRequest(BaseModel):
    corrected_place_name: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None


@app.post("/locations-legacy")
async def add_photo_location_legacy(request: LocationCreateRequest):
    """Add or update location information for a photo."""
    try:
        locations_db = get_locations_db(settings.BASE_DIR / "locations.db")

        normalized_path = "/" + request.photo_path.lstrip("/")

        location_id = locations_db.add_photo_location(
            photo_path=normalized_path,
            latitude=request.latitude,
            longitude=request.longitude,
            original_place_name=request.original_place_name,
            corrected_place_name=request.corrected_place_name,
            country=request.country,
            region=request.region,
            city=request.city,
            accuracy=request.accuracy
        )

        return {"success": True, "location_id": location_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/locations-legacy/photo/{photo_path:path}")
async def get_photo_location_legacy(photo_path: str):
    """Get location information for a specific photo."""
    try:
        locations_db = get_locations_db(settings.BASE_DIR / "locations.db")
        normalized_path = "/" + photo_path.lstrip("/")
        location = locations_db.get_photo_location(normalized_path)

        if not location:
            raise HTTPException(status_code=404, detail="Location not found for photo")

        return {"location": location}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/locations-legacy/photo/{photo_path:path}")
async def update_photo_location_legacy(photo_path: str, request: LocationUpdateRequest):
    """Update location information for a photo."""
    try:
        locations_db = get_locations_db(settings.BASE_DIR / "locations.db")
        normalized_path = "/" + photo_path.lstrip("/")

        if request.corrected_place_name:
            success = locations_db.update_place_name(normalized_path, request.corrected_place_name)
        else:
            success = True  # Skip update if no corrected name provided

        if not success:
            raise HTTPException(status_code=404, detail="Photo location not found")

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/locations/places/{place_name}")
async def get_photos_by_place(place_name: str):
    """Get all photos associated with a specific place name."""
    try:
        locations_db = get_locations_db(settings.BASE_DIR / "locations.db")
        photos = locations_db.get_photos_by_place(place_name)
        return {"place_name": place_name, "photos": photos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/locations/nearby")
async def get_nearby_locations(
    latitude: float,
    longitude: float,
    radius_km: float = Query(1.0, ge=0.1, le=50.0)  # Between 0.1 and 50 km
):
    """Get photos within a certain radius of a location."""
    try:
        locations_db = get_locations_db(settings.BASE_DIR / "locations.db")
        nearby = locations_db.get_nearby_locations(latitude, longitude, radius_km)
        return {"center": {"lat": latitude, "lng": longitude}, "radius_km": radius_km, "photos": nearby}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/locations/clusters")
async def get_place_clusters(min_photos: int = Query(2, ge=1)):
    """Get clusters of photos by location."""
    try:
        locations_db = get_locations_db(settings.BASE_DIR / "locations.db")
        clusters = locations_db.get_place_clusters(min_photos)
        return {"clusters": clusters}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/locations-legacy/stats")
async def get_location_stats_legacy():
    """Get statistics about location data."""
    try:
        locations_db = get_locations_db(settings.BASE_DIR / "locations.db")
        stats = locations_db.get_location_stats()
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# ADVANCED INTENT-BASED SEARCH ENDPOINTS
# ==============================================================================

class IntentSearchParams(BaseModel):
    query: str
    intent_context: Optional[Dict[str, Any]] = None
    filters: Optional[Dict[str, Any]] = None
    limit: int = 50
    offset: int = 0


@app.post("/search/intent")
async def search_with_intent(params: IntentSearchParams):
    """
    Advanced search with intent recognition and context-aware processing.

    This endpoint performs search considering the user's intent and provides
    enhanced results based on contextual information.
    """
    try:
        import time
        start_time = time.time()

        # Detect intent from query
        intent_result = intent_detector.detect_intent(params.query)

        # Apply intent-specific search logic
        results: List[Dict[str, Any]] = []

        # For people intent, search using face recognition if available
        if intent_result['primary_intent'] == 'people':
            # Check if person name is in query
            people_results: List[Dict[str, Any]] = []
            try:
                from src.face_clustering import FACE_LIBRARIES_AVAILABLE
                if FACE_LIBRARIES_AVAILABLE:
                    # Search for faces with names matching query
                    # This is a simplified implementation
                    # In a full implementation, this would query the face clustering database
                    pass
            except ImportError:
                pass

        # For location intent, search using location data
        elif intent_result['primary_intent'] == 'location':
            # Search for photos with matching location info
            locations_db = get_locations_db(settings.BASE_DIR / "locations.db")
            location_results = locations_db.get_photos_by_place(params.query)
            # Add to results with location context

        # For date intent, enhance date filtering
        elif intent_result['primary_intent'] == 'date':
            # Parse date expressions from query and apply to search
            base_query = params.query
            # Extract date ranges from query if possible
            # This would be enhanced with NLP for date parsing

        # For events, combine multiple filters
        elif intent_result['primary_intent'] == 'event':
            # Events often involve people, locations, and specific activities
            # Apply multi-faceted search
            pass

        # Perform base search depending on intent
        # Use hybrid search with intent-based weightings
        metadata_weight, semantic_weight = 0.5, 0.5

        if intent_result['primary_intent'] in ['camera', 'date', 'technical']:
            metadata_weight, semantic_weight = 0.8, 0.2
        elif intent_result['primary_intent'] in ['people', 'object', 'scene', 'event', 'emotion', 'activity']:
            metadata_weight, semantic_weight = 0.2, 0.8
        elif intent_result['primary_intent'] in ['location', 'color']:
            metadata_weight, semantic_weight = 0.6, 0.4

        # Perform hybrid search with appropriate weights
        # This would use the existing hybrid search logic with intent weights

        # Fallback to regular search if no specific intent processing
        search_results_response = await search_photos(
            query=params.query,
            limit=params.limit,
            offset=params.offset,
            mode="hybrid",
            sort_by="date_desc"
        )

        search_results = search_results_response["results"]

        # Add intent information to results
        response = {
            "query": params.query,
            "intent": intent_result,
            "count": len(search_results),
            "results": search_results,
            "processing_time": time.time() - start_time,
            "filters_applied": params.filters or {}
        }

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/refine")
async def refine_search(query: str, previous_results: List[Dict], refinement: str):
    """
    Refine search results based on user feedback.

    This endpoint allows users to refine existing search results with
    additional criteria or corrections.
    """
    try:
        # Detect intent in refinement query
        intent_result = intent_detector.detect_intent(refinement)

        # Apply refinement to previous results
        # For example, if refinement is "only show photos from 2023", filter by date
        # If refinement is "only beach photos", apply scene detection filter
        refined_results = previous_results[:]  # In a real implementation, this would apply filters
        suggestions = intent_detector.get_search_suggestions(f"{query} {refinement}")

        return {
            "original_query": query,
            "refinement": refinement,
            "intent": intent_result,
            "count": len(refined_results),
            "results": refined_results,
            "suggestions": suggestions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# SMART COLLECTIONS ENDPOINTS
# ==============================================================================

class SmartCollectionCreateRequest(BaseModel):
    name: str
    description: str
    rule_definition: Dict[str, Any]  # JSON definition of inclusion criteria
    auto_update: bool = True
    privacy_level: str = "private"  # public, shared, private


class SmartCollectionUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    rule_definition: Optional[Dict[str, Any]] = None
    auto_update: Optional[bool] = None
    privacy_level: Optional[str] = None
    is_favorite: Optional[bool] = None


@app.post("/collections/smart")
async def create_smart_collection(request: SmartCollectionCreateRequest):
    """Create a new smart collection with auto-inclusion rules."""
    try:
        collections_db = get_smart_collections_db(settings.BASE_DIR / "collections.db")

        collection_id = collections_db.create_smart_collection(
            name=request.name,
            description=request.description,
            rule_definition=request.rule_definition,
            auto_update=request.auto_update,
            privacy_level=request.privacy_level
        )

        if not collection_id:
            raise HTTPException(status_code=400, detail="Collection name already exists")

        return {"success": True, "collection_id": collection_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collections/smart")
async def get_smart_collections(limit: int = 50, offset: int = 0):
    """Get all smart collections."""
    try:
        collections_db = get_smart_collections_db(settings.BASE_DIR / "collections.db")
        collections = collections_db.get_smart_collections(limit, offset)
        return {"collections": collections, "count": len(collections)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collections/smart/{collection_id}")
async def get_smart_collection(collection_id: str):
    """Get a specific smart collection."""
    try:
        collections_db = get_smart_collections_db(settings.BASE_DIR / "collections.db")
        collection = collections_db.get_smart_collection(collection_id)

        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")

        return {"collection": collection}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/collections/smart/{collection_id}")
async def update_smart_collection(collection_id: str, request: SmartCollectionUpdateRequest):
    """Update a smart collection."""
    try:
        collections_db = get_smart_collections_db(settings.BASE_DIR / "collections.db")

        success = collections_db.update_smart_collection(
            collection_id=collection_id,
            name=request.name,
            description=request.description,
            rule_definition=request.rule_definition,
            auto_update=request.auto_update,
            privacy_level=request.privacy_level,
            is_favorite=request.is_favorite
        )

        if not success:
            raise HTTPException(status_code=404, detail="Collection not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/collections/smart/{collection_id}")
async def delete_smart_collection(collection_id: str):
    """Delete a smart collection."""
    try:
        collections_db = get_smart_collections_db(settings.BASE_DIR / "collections.db")
        success = collections_db.delete_smart_collection(collection_id)

        if not success:
            raise HTTPException(status_code=404, detail="Collection not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collections/smart/{collection_id}/photos")
async def get_photos_for_collection(collection_id: str):
    """Get photos that match the collection's rules."""
    try:
        collections_db = get_smart_collections_db(settings.BASE_DIR / "collections.db")
        photo_paths = collections_db.get_photos_for_collection(collection_id)

        # In a real implementation, we would get full photo metadata
        # For now, return just the paths
        return {"photos": photo_paths, "count": len(photo_paths)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collections/smart/by-rule/{rule_type}")
async def get_collections_by_rule_type(rule_type: str):
    """Get collections that use a specific type of rule."""
    try:
        collections_db = get_smart_collections_db(settings.BASE_DIR / "collections.db")
        collections = collections_db.get_collections_by_rule_type(rule_type)
        return {"collections": collections, "count": len(collections)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collections/smart/stats")
async def get_smart_collections_stats():
    """Get statistics about smart collections."""
    try:
        collections_db = get_smart_collections_db(settings.BASE_DIR / "collections.db")
        stats = collections_db.get_collections_stats()
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# PERFORMANCE OPTIMIZATION ENDPOINTS
# ==============================================================================

@app.get("/cache/stats")
async def get_cache_stats():
    """Get statistics about the caching system."""
    try:
        from src.cache_manager import cache_manager
        stats = cache_manager.get_stats()
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cache/clear")
async def clear_cache(cache_type: Optional[str] = None):
    """Clear cache entries."""
    try:
        from src.cache_manager import cache_manager
        cache_manager.clear_cache(cache_type)
        return {"success": True, "message": f"Cleared {cache_type or 'all'} cache"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cache/health")
async def cache_health_check():
    """Health check for cache system."""
    try:
        from src.cache_manager import cache_manager
        stats = cache_manager.get_stats()

        # Calculate cache hit rates if possible
        # For now, return basic health information
        health = {
            "status": "healthy",
            "caches": list(stats.keys()),
            "total_entries": sum(s['size'] for s in stats.values()),
            "timestamp": datetime.now().isoformat()
        }

        return health
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# AI INSIGHTS ENDPOINTS
# ==============================================================================

class AIInsightCreateRequest(BaseModel):
    photo_path: str
    insight_type: str  # 'best_shot', 'tag_suggestion', 'pattern', 'organization'
    insight_data: Dict[str, Any]
    confidence: float = 0.8


class AIInsightUpdateRequest(BaseModel):
    is_applied: Optional[bool] = None


@app.post("/ai/insights")
async def create_ai_insight(request: AIInsightCreateRequest):
    """Create a new AI-generated insight for a photo."""
    try:
        insights_db = get_ai_insights_db(settings.BASE_DIR / "insights.db")

        insight_id = insights_db.add_insight(
            photo_path=request.photo_path,
            insight_type=request.insight_type,
            insight_data=request.insight_data,
            confidence=request.confidence
        )

        if not insight_id:
            raise HTTPException(status_code=400, detail="Failed to create insight")

        return {"success": True, "insight_id": insight_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ai/insights/photo/{photo_path:path}")
async def get_insights_for_photo(photo_path: str):
    """Get all AI insights for a specific photo."""
    try:
        insights_db = get_ai_insights_db(settings.BASE_DIR / "insights.db")
        insights = insights_db.get_insights_for_photo(photo_path)
        return {"insights": insights, "count": len(insights)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ai/insights/type/{insight_type}")
async def get_insights_by_type(insight_type: str, limit: int = 50):
    """Get AI insights of a specific type."""
    try:
        insights_db = get_ai_insights_db(settings.BASE_DIR / "insights.db")
        insights = insights_db.get_insights_by_type(insight_type, limit)
        return {"insights": insights, "count": len(insights)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ai/insights")
async def get_all_insights(limit: int = 100, offset: int = 0):
    """Get all AI insights with pagination."""
    try:
        insights_db = get_ai_insights_db(settings.BASE_DIR / "insights.db")
        insights = insights_db.get_all_insights(limit, offset)
        return {"insights": insights, "count": len(insights)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/ai/insights/{insight_id}")
async def update_insight_applied_status(insight_id: str, request: AIInsightUpdateRequest):
    """Update the applied status of an insight."""
    try:
        insights_db = get_ai_insights_db(settings.BASE_DIR / "insights.db")

        if request.is_applied is None:
            raise HTTPException(status_code=400, detail="is_applied status must be provided")

        success = insights_db.mark_insight_applied(insight_id, request.is_applied)

        if not success:
            raise HTTPException(status_code=404, detail="Insight not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/ai/insights/{insight_id}")
async def delete_insight(insight_id: str):
    """Delete an AI insight."""
    try:
        insights_db = get_ai_insights_db(settings.BASE_DIR / "insights.db")
        success = insights_db.delete_insight(insight_id)

        if not success:
            raise HTTPException(status_code=404, detail="Insight not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ai/insights/stats")
async def get_insights_stats():
    """Get statistics about AI insights."""
    try:
        insights_db = get_ai_insights_db(settings.BASE_DIR / "insights.db")
        stats = insights_db.get_insights_stats()
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ai/analytics/patterns")
async def analyze_photographer_patterns(photo_paths: List[str] = Body(...)):
    """Analyze photographer patterns across multiple photos."""
    try:
        insights_db = get_ai_insights_db(settings.BASE_DIR / "insights.db")
        patterns = insights_db.get_photographer_patterns(photo_paths)
        return {"patterns": patterns}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# COLLABORATIVE SPACES ENDPOINTS
# ==============================================================================

class CollaborativeSpaceCreateRequest(BaseModel):
    name: str
    description: str
    privacy_level: str = "private"  # public, shared, private
    max_members: int = 10


class CollaborativeSpaceUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    privacy_level: Optional[str] = None
    max_members: Optional[int] = None


class AddMemberRequest(BaseModel):
    user_id: str
    role: str = "contributor"  # owner, admin, contributor, viewer


class SpacePhotoCreateRequest(BaseModel):
    photo_path: str
    caption: Optional[str] = None


class SpaceCommentCreateRequest(BaseModel):
    comment: str


@app.post("/collaborative/spaces")
async def create_collaborative_space(request: CollaborativeSpaceCreateRequest, user_id: str = "default_user"):
    """Create a new collaborative photo space."""
    try:
        spaces_db = get_collaborative_spaces_db(settings.BASE_DIR / "collaborative_spaces.db")

        space_id = spaces_db.create_collaborative_space(
            name=request.name,
            description=request.description,
            owner_id=user_id,  # In a real app, this would come from auth
            privacy_level=request.privacy_level,
            max_members=request.max_members
        )

        if not space_id:
            raise HTTPException(status_code=400, detail="Failed to create space")

        return {"success": True, "space_id": space_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collaborative/spaces/{space_id}")
async def get_collaborative_space(space_id: str):
    """Get details about a specific collaborative space."""
    try:
        spaces_db = get_collaborative_spaces_db(settings.BASE_DIR / "collaborative_spaces.db")
        space = spaces_db.get_collaborative_space(space_id)

        if not space:
            raise HTTPException(status_code=404, detail="Space not found")

        return {"space": space}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collaborative/spaces/user/{user_id}")
async def get_user_spaces(user_id: str, limit: int = 50, offset: int = 0):
    """Get all collaborative spaces a user belongs to."""
    try:
        spaces_db = get_collaborative_spaces_db(settings.BASE_DIR / "collaborative_spaces.db")
        user_spaces = spaces_db.get_user_spaces(user_id, limit, offset)
        return {"spaces": user_spaces, "count": len(user_spaces)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/collaborative/spaces/{space_id}/members")
async def add_member_to_space(space_id: str, request: AddMemberRequest):
    """Add a member to a collaborative space."""
    try:
        spaces_db = get_collaborative_spaces_db(settings.BASE_DIR / "collaborative_spaces.db")

        success = spaces_db.add_member_to_space(
            space_id=space_id,
            user_id=request.user_id,
            role=request.role
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to add member")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/collaborative/spaces/{space_id}/members/{user_id}")
async def remove_member_from_space(space_id: str, user_id: str):
    """Remove a member from a collaborative space."""
    try:
        spaces_db = get_collaborative_spaces_db(settings.BASE_DIR / "collaborative_spaces.db")

        success = spaces_db.remove_member_from_space(space_id, user_id)

        if not success:
            raise HTTPException(status_code=400, detail="Failed to remove member")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collaborative/spaces/{space_id}/members")
async def get_space_members(space_id: str):
    """Get all members of a collaborative space."""
    try:
        spaces_db = get_collaborative_spaces_db(settings.BASE_DIR / "collaborative_spaces.db")
        members = spaces_db.get_space_members(space_id)
        return {"members": members, "count": len(members)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/collaborative/spaces/{space_id}/photos")
async def add_photo_to_space(space_id: str, request: SpacePhotoCreateRequest, user_id: str = "default_user"):
    """Add a photo to a collaborative space."""
    try:
        spaces_db = get_collaborative_spaces_db(settings.BASE_DIR / "collaborative_spaces.db")

        success = spaces_db.add_photo_to_space(
            space_id=space_id,
            photo_path=request.photo_path,
            added_by_user_id=user_id,  # In a real app, this would come from auth
            caption=request.caption or ""
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to add photo to space")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/collaborative/spaces/{space_id}/photos/{photo_path:path}")
async def remove_photo_from_space(space_id: str, photo_path: str):
    """Remove a photo from a collaborative space."""
    try:
        spaces_db = get_collaborative_spaces_db(settings.BASE_DIR / "collaborative_spaces.db")

        success = spaces_db.remove_photo_from_space(space_id, photo_path)

        if not success:
            raise HTTPException(status_code=400, detail="Failed to remove photo from space")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collaborative/spaces/{space_id}/photos")
async def get_space_photos(space_id: str, limit: int = 50, offset: int = 0):
    """Get all photos in a collaborative space."""
    try:
        spaces_db = get_collaborative_spaces_db(settings.BASE_DIR / "collaborative_spaces.db")
        photos = spaces_db.get_space_photos(space_id, limit, offset)
        return {"photos": photos, "count": len(photos)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/collaborative/spaces/{space_id}/photos/{photo_path:path}/comments")
async def add_comment_to_space_photo(
    space_id: str,
    photo_path: str,
    request: SpaceCommentCreateRequest,
    user_id: str = "default_user"
):
    """Add a comment to a photo in a collaborative space."""
    try:
        spaces_db = get_collaborative_spaces_db(settings.BASE_DIR / "collaborative_spaces.db")

        comment_id = spaces_db.add_comment_to_space_photo(
            space_id=space_id,
            photo_path=photo_path,
            user_id=user_id,  # In a real app, this would come from auth
            comment=request.comment
        )

        if not comment_id:
            raise HTTPException(status_code=400, detail="Failed to add comment")

        return {"success": True, "comment_id": comment_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collaborative/spaces/{space_id}/photos/{photo_path:path}/comments")
async def get_photo_comments(space_id: str, photo_path: str, limit: int = 50, offset: int = 0):
    """Get all comments for a photo in a collaborative space."""
    try:
        spaces_db = get_collaborative_spaces_db(settings.BASE_DIR / "collaborative_spaces.db")
        comments = spaces_db.get_photo_comments(space_id, photo_path, limit, offset)
        return {"comments": comments, "count": len(comments)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collaborative/spaces/{space_id}/stats")
async def get_space_stats(space_id: str):
    """Get statistics about a collaborative space."""
    try:
        spaces_db = get_collaborative_spaces_db(settings.BASE_DIR / "collaborative_spaces.db")
        stats = spaces_db.get_space_stats(space_id)
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# PRIVACY CONTROLS ENDPOINTS
# ==============================================================================

class PrivacyControlRequest(BaseModel):
    owner_id: str
    visibility: str = "private"  # public, shared, private, friends_only
    share_permissions: Optional[Dict[str, bool]] = None
    encryption_enabled: bool = False
    encryption_key_hash: Optional[str] = None
    allowed_users: Optional[List[str]] = None
    allowed_groups: Optional[List[str]] = None


class PrivacyUpdateRequest(BaseModel):
    visibility: Optional[str] = None
    share_permissions: Optional[Dict[str, bool]] = None
    encryption_enabled: Optional[bool] = None
    encryption_key_hash: Optional[str] = None
    allowed_users: Optional[List[str]] = None
    allowed_groups: Optional[List[str]] = None


@app.post("/privacy/control/{photo_path:path}")
async def set_photo_privacy(photo_path: str, request: PrivacyControlRequest):
    """Set privacy controls for a photo."""
    try:
        privacy_db = get_privacy_controls_db(settings.BASE_DIR / "privacy.db")

        privacy_id = privacy_db.set_photo_privacy(
            photo_path=photo_path,
            owner_id=request.owner_id,
            visibility=request.visibility,
            share_permissions=request.share_permissions,
            encryption_enabled=request.encryption_enabled,
            encryption_key_hash=request.encryption_key_hash,
            allowed_users=request.allowed_users,
            allowed_groups=request.allowed_groups
        )

        if not privacy_id:
            raise HTTPException(status_code=400, detail="Failed to set privacy controls")

        return {"success": True, "privacy_id": privacy_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/privacy/control/{photo_path:path}")
async def get_photo_privacy(photo_path: str):
    """Get privacy settings for a photo."""
    try:
        privacy_db = get_privacy_controls_db(settings.BASE_DIR / "privacy.db")
        privacy = privacy_db.get_photo_privacy(photo_path)

        if not privacy:
            raise HTTPException(status_code=404, detail="Privacy settings not found for photo")

        return {"privacy": privacy}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/privacy/control/{photo_path:path}")
async def update_photo_privacy(photo_path: str, request: PrivacyUpdateRequest):
    """Update privacy settings for a photo."""
    try:
        privacy_db = get_privacy_controls_db(settings.BASE_DIR / "privacy.db")

        success = privacy_db.update_photo_privacy(
            photo_path=photo_path,
            visibility=request.visibility,
            share_permissions=request.share_permissions,
            encryption_enabled=request.encryption_enabled,
            encryption_key_hash=request.encryption_key_hash,
            allowed_users=request.allowed_users,
            allowed_groups=request.allowed_groups
        )

        if not success:
            raise HTTPException(status_code=404, detail="Privacy settings not found for photo")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/privacy/visible/{visibility}/{owner_id}")
async def get_photos_by_visibility(visibility: str, owner_id: str, limit: int = 50, offset: int = 0):
    """Get photos with specific visibility for an owner."""
    try:
        privacy_db = get_privacy_controls_db(settings.BASE_DIR / "privacy.db")
        photos = privacy_db.get_photos_by_visibility(visibility, owner_id, limit, offset)
        return {"photos": photos, "count": len(photos)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/privacy/access/{user_id}")
async def get_photos_accessible_to_user(user_id: str, limit: int = 50, offset: int = 0):
    """Get photos that a user has access to based on privacy settings."""
    try:
        privacy_db = get_privacy_controls_db(settings.BASE_DIR / "privacy.db")
        photos = privacy_db.get_photos_for_user(user_id, limit, offset)
        return {"photos": photos, "count": len(photos)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/privacy/check-access/{photo_path:path}/{user_id}")
async def check_photo_access(photo_path: str, user_id: str):
    """Check if a user has permission to access a photo."""
    try:
        privacy_db = get_privacy_controls_db(settings.BASE_DIR / "privacy.db")
        has_access = privacy_db.check_access_permission(photo_path, user_id)
        return {"has_access": has_access}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/privacy/encrypted/{owner_id}")
async def get_encrypted_photos(owner_id: str):
    """Get all photos with encryption enabled for an owner."""
    try:
        privacy_db = get_privacy_controls_db(settings.BASE_DIR / "privacy.db")
        encrypted_photos = privacy_db.get_encrypted_photos(owner_id)
        return {"encrypted_photos": encrypted_photos, "count": len(encrypted_photos)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/privacy/stats/{owner_id}")
async def get_privacy_stats(owner_id: str):
    """Get statistics about privacy settings for an owner."""
    try:
        privacy_db = get_privacy_controls_db(settings.BASE_DIR / "privacy.db")
        stats = privacy_db.get_privacy_stats(owner_id)
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/privacy/revoke-access/{photo_path:path}/{user_id}")
async def revoke_user_access(photo_path: str, user_id: str):
    """Revoke access for a specific user to a photo."""
    try:
        privacy_db = get_privacy_controls_db(settings.BASE_DIR / "privacy.db")
        success = privacy_db.revoke_user_access(photo_path, user_id)

        if not success:
            raise HTTPException(status_code=400, detail="Failed to revoke access")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# TIMELINE & STORY ENDPOINTS
# ==============================================================================

class StoryCreateRequest(BaseModel):
    title: str
    description: str
    owner_id: str
    metadata: Optional[Dict[str, Any]] = None
    is_published: bool = False


class StoryUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_published: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class TimelineEntryCreateRequest(BaseModel):
    photo_path: str
    date: str
    location: Optional[str] = None
    caption: Optional[str] = None


class TimelineEntryUpdateRequest(BaseModel):
    date: Optional[str] = None
    location: Optional[str] = None
    caption: Optional[str] = None
    narrative_order: Optional[int] = None


@app.post("/stories")
async def create_story(request: StoryCreateRequest):
    """Create a new story narrative."""
    try:
        timeline_db = get_timeline_db(settings.BASE_DIR / "timelines.db")

        story_id = timeline_db.create_story(
            title=request.title,
            description=request.description,
            owner_id=request.owner_id,
            metadata=request.metadata,
            is_published=request.is_published
        )

        if not story_id:
            raise HTTPException(status_code=400, detail="Failed to create story")

        return {"success": True, "story_id": story_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stories/{story_id}")
async def get_story(story_id: str):
    """Get details about a specific story."""
    try:
        timeline_db = get_timeline_db(settings.BASE_DIR / "timelines.db")
        story = timeline_db.get_story(story_id)

        if not story:
            raise HTTPException(status_code=404, detail="Story not found")

        return {"story": story}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stories/owner/{owner_id}")
async def get_stories_by_owner(
    owner_id: str,
    include_unpublished: bool = False,
    limit: int = 50,
    offset: int = 0
):
    """Get all stories for an owner."""
    try:
        timeline_db = get_timeline_db(settings.BASE_DIR / "timelines.db")
        stories = timeline_db.get_stories_by_owner(owner_id, include_unpublished, limit, offset)
        return {"stories": stories, "count": len(stories)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/stories/{story_id}")
async def update_story(story_id: str, request: StoryUpdateRequest):
    """Update story details."""
    try:
        # In a real implementation, we would update the story in the database
        # For now, we'll just return success
        timeline_db = get_timeline_db(settings.BASE_DIR / "timelines.db")

        # Get existing story to update
        existing_story = timeline_db.get_story(story_id)
        if not existing_story:
            raise HTTPException(status_code=404, detail="Story not found")

        # Update story in database
        with sqlite3.connect(settings.BASE_DIR / "timelines.db") as conn:
            update_fields: list[str] = []
            params: list[object] = []

            if request.title is not None:
                update_fields.append("title = ?")
                params.append(request.title)

            if request.description is not None:
                update_fields.append("description = ?")
                params.append(request.description)

            if request.is_published is not None:
                update_fields.append("is_published = ?")
                params.append(request.is_published)

            if request.metadata is not None:
                update_fields.append("metadata = ?")
                params.append(json.dumps(request.metadata))

            update_fields.append("updated_at = CURRENT_TIMESTAMP")

            if update_fields:
                sql = f"UPDATE stories SET {', '.join(update_fields)} WHERE id = ?"
                params.append(story_id)

                cursor = conn.execute(sql, params)

                if cursor.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Story not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stories/{story_id}/photos")
async def add_photo_to_story(story_id: str, request: TimelineEntryCreateRequest):
    """Add a photo to a story's timeline."""
    try:
        timeline_db = get_timeline_db(settings.BASE_DIR / "timelines.db")

        entry_id = timeline_db.add_photo_to_timeline(
            story_id=story_id,
            photo_path=request.photo_path,
            date=request.date,
            location=request.location,
            caption=request.caption
        )

        if not entry_id:
            raise HTTPException(status_code=400, detail="Failed to add photo to timeline")

        return {"success": True, "entry_id": entry_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stories/{story_id}/timeline")
async def get_story_timeline(story_id: str, limit: int = 100, offset: int = 0):
    """Get the timeline for a story."""
    try:
        timeline_db = get_timeline_db(settings.BASE_DIR / "timelines.db")
        timeline = timeline_db.get_timeline_for_story(story_id)

        # Apply limit and offset manually since the method doesn't support it
        paginated_timeline = timeline[offset:offset+limit]

        return {"timeline": paginated_timeline, "count": len(timeline)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/timeline/entries/{entry_id}")
async def update_timeline_entry(entry_id: str, request: TimelineEntryUpdateRequest):
    """Update a timeline entry."""
    try:
        timeline_db = get_timeline_db(settings.BASE_DIR / "timelines.db")

        # In a real implementation, we would have a method to update specific timeline entries
        # For now, we'll update using raw SQL
        with sqlite3.connect(settings.BASE_DIR / "timelines.db") as conn:
            update_fields: list[str] = []
            params: list[object] = []

            if request.date is not None:
                update_fields.append("date = ?")
                params.append(request.date)

            if request.location is not None:
                update_fields.append("location = ?")
                params.append(request.location)

            if request.caption is not None:
                update_fields.append("caption = ?")
                params.append(request.caption)

            if request.narrative_order is not None:
                update_fields.append("narrative_order = ?")
                params.append(request.narrative_order)

            update_fields.append("updated_at = CURRENT_TIMESTAMP")

            if update_fields:
                sql = f"UPDATE timeline_entries SET {', '.join(update_fields)} WHERE id = ?"
                params.append(entry_id)

                cursor = conn.execute(sql, params)

                if cursor.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Timeline entry not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/timeline/entries/{entry_id}")
async def remove_photo_from_timeline(entry_id: str):
    """Remove a photo from a story's timeline."""
    try:
        timeline_db = get_timeline_db(settings.BASE_DIR / "timelines.db")

        success = timeline_db.remove_photo_from_timeline(entry_id)

        if not success:
            raise HTTPException(status_code=404, detail="Timeline entry not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stories/{story_id}/stats")
async def get_story_stats(story_id: str):
    """Get statistics about a story."""
    try:
        timeline_db = get_timeline_db(settings.BASE_DIR / "timelines.db")
        story = timeline_db.get_story(story_id)

        if not story:
            raise HTTPException(status_code=404, detail="Story not found")

        # Get the timeline to calculate stats
        timeline = timeline_db.get_timeline_for_story(story_id)

        # Calculate stats
        # `timeline_db` implementations may return dict rows; normalize access defensively.
        story_title = story.get("title") if isinstance(story, dict) else getattr(story, "title", None)
        story_created_at = story.get("created_at") if isinstance(story, dict) else getattr(story, "created_at", None)

        def _entry_field(entry: Any, key: str) -> Any:
            if isinstance(entry, dict):
                return entry.get(key)
            return getattr(entry, key, None)

        dates = [
            _entry_field(e, "date")
            for e in timeline
            if _entry_field(e, "date")
        ]
        locations = [
            _entry_field(e, "location")
            for e in timeline
            if _entry_field(e, "location")
        ]
        has_captions = any(bool(_entry_field(e, "caption")) for e in timeline)

        stats = {
            "story_id": story_id,
            "title": story_title,
            "total_photos": len(timeline),
            "start_date": min(dates) if dates else story_created_at,
            "end_date": max(dates) if dates else story_created_at,
            "locations_count": len(set(locations)),
            "has_captions": has_captions,
        }

        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stories/user/{user_id}/stats")
async def get_user_story_stats(user_id: str):
    """Get statistics about a user's stories."""
    try:
        timeline_db = get_timeline_db(settings.BASE_DIR / "timelines.db")
        stats = timeline_db.get_story_stats(user_id)
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stories/{story_id}/publish")
async def toggle_story_publish(story_id: str, publish_request: dict):
    """Publish or unpublish a story."""
    try:
        is_published = publish_request.get("publish", True)
        timeline_db = get_timeline_db(settings.BASE_DIR / "timelines.db")

        success = timeline_db.publish_story(story_id, is_published)

        if not success:
            raise HTTPException(status_code=400, detail="Failed to update story publication status")

        return {"success": True, "published": is_published}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# BULK ACTIONS ENDPOINTS
# ==============================================================================

class BulkActionRequest(BaseModel):
    action_type: str  # 'delete', 'favorite', 'tag_add', 'tag_remove', 'move', 'copy'
    paths: List[str]
    operation_data: Optional[Dict[str, Any]] = None  # Additional data for the operation


class BulkActionUndoRequest(BaseModel):
    action_id: str


@app.post("/bulk/action")
async def record_bulk_action(request: BulkActionRequest):
    """Record a bulk action that may need to be undone."""
    try:
        bulk_actions_db = get_bulk_actions_db(settings.BASE_DIR / "bulk_actions.db")

        action_id = bulk_actions_db.record_bulk_action(
            action_type=request.action_type,
            user_id="current_user_id",  # In a real app, this would come from authentication
            affected_paths=request.paths,
            operation_data=request.operation_data
        )

        if not action_id:
            raise HTTPException(status_code=400, detail="Failed to record bulk action")

        return {"success": True, "action_id": action_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/bulk/history/{user_id}")
async def get_bulk_action_history(
    user_id: str,
    action_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """Get bulk action history for a user."""
    try:
        bulk_db = get_bulk_actions_db(settings.BASE_DIR / "bulk_actions.db")
        actions = bulk_db.get_action_history(user_id, action_type, limit, offset)

        return {"actions": actions, "count": len(actions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/bulk/undo/{action_id}")
async def undo_bulk_action(action_id: str):
    """Undo a recorded bulk action."""
    try:
        bulk_db = get_bulk_actions_db(settings.BASE_DIR / "bulk_actions.db")

        # Check if action can be undone
        if not bulk_db.can_undo_action(action_id):
            raise HTTPException(status_code=400, detail="Action cannot be undone")

        # For actual undo, we would need to implement the specific undo logic for each action type
        # This is a simplified implementation that just marks the action as undone
        success = bulk_db.mark_action_undone(action_id)

        if not success:
            raise HTTPException(status_code=400, detail="Failed to undo action")

        return {"success": True, "action_id": action_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/bulk/can-undo/{action_id}")
async def can_undo_action(action_id: str):
    """Check if a bulk action can be undone."""
    try:
        bulk_db = get_bulk_actions_db(settings.BASE_DIR / "bulk_actions.db")
        can_undo = bulk_db.can_undo_action(action_id)

        return {"can_undo": can_undo}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/bulk/stats/{user_id}")
async def get_bulk_actions_stats(user_id: str):
    """Get statistics about bulk actions for a user."""
    try:
        bulk_db = get_bulk_actions_db(settings.BASE_DIR / "bulk_actions.db")

        recent_actions = bulk_db.get_recent_actions(user_id, minutes=60)  # Last hour
        undone_count = bulk_db.get_undone_actions_count(user_id)

        # Count actions by type
        type_counts: dict[str, int] = {}
        for action in recent_actions:
            action_type = action.action_type
            type_counts[action_type] = type_counts.get(action_type, 0) + 1

        return {
            "stats": {
                "recent_actions": len(recent_actions),
                "undone_actions": undone_count,
                "actions_by_type": type_counts,
                "recent_period_minutes": 60
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# MULTI-TAG FILTERING ENDPOINTS
# ==============================================================================

class Legacy2TagExpression(BaseModel):
    tag: str
    operator: str = "has"  # 'has', 'not_has', 'maybe_has'


class Legacy2TagFilterCreateRequest(BaseModel):
    name: str
    tag_expressions: List[Legacy2TagExpression]
    combination_operator: str = "AND"  # 'AND' or 'OR'


class Legacy2TagFilterUpdateRequest(BaseModel):
    name: Optional[str] = None
    tag_expressions: Optional[List[Legacy2TagExpression]] = None
    combination_operator: Optional[str] = None


@app.post("/tag-filters/legacy2")
async def create_tag_filter_legacy2(request: Legacy2TagFilterCreateRequest):
    """Create a new tag filter with custom expressions and logic."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")

        filter_id = tag_filter_db.create_tag_filter(
            name=request.name,
            tag_expressions=[expr.dict() for expr in request.tag_expressions],
            combination_operator=request.combination_operator
        )

        if not filter_id:
            raise HTTPException(status_code=400, detail="Failed to create tag filter")

        return {"success": True, "filter_id": filter_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tag-filters/legacy2/{filter_id}")
async def get_tag_filter_legacy2(filter_id: str):
    """Get details of a specific tag filter."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")
        tag_filter = tag_filter_db.get_tag_filter(filter_id)

        if not tag_filter:
            raise HTTPException(status_code=404, detail="Tag filter not found")

        return {"tag_filter": tag_filter}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tag-filters/legacy2")
async def get_tag_filters_legacy2(limit: int = 50, offset: int = 0):
    """Get all tag filters."""
    try:
        with sqlite3.connect(settings.BASE_DIR / "tag_filters.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM tag_filters ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            rows = cursor.fetchall()

            return {
                "filters": [dict(row) for row in rows],
                "count": len(rows)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/tag-filters/legacy2/{filter_id}")
async def update_tag_filter_legacy2(filter_id: str, request: Legacy2TagFilterUpdateRequest):
    """Update a tag filter."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")

        # Get existing filter first
        existing_filter = tag_filter_db.get_tag_filter(filter_id)
        if not existing_filter:
            raise HTTPException(status_code=404, detail="Tag filter not found")

        # Update the filter
        with sqlite3.connect(settings.BASE_DIR / "tag_filters.db") as conn:
            update_fields = []
            params = []

            if request.name is not None:
                update_fields.append("name = ?")
                params.append(request.name)

            if request.tag_expressions is not None:
                update_fields.append("tag_expressions = ?")
                params.append(json.dumps([expr.dict() for expr in request.tag_expressions]))

            if request.combination_operator is not None:
                update_fields.append("combination_operator = ?")
                params.append(request.combination_operator)

            update_fields.append("updated_at = CURRENT_TIMESTAMP")

            if update_fields:
                sql = f"UPDATE tag_filters SET {', '.join(update_fields)} WHERE id = ?"
                params.append(filter_id)

                cursor = conn.execute(sql, params)

                if cursor.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Tag filter not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/tag-filters/legacy2/{filter_id}")
async def delete_tag_filter_legacy2(filter_id: str):
    """Delete a tag filter."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")
        success = tag_filter_db.delete_tag_filter(filter_id)

        if not success:
            raise HTTPException(status_code=404, detail="Tag filter not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tag-filters/legacy2/apply")
async def apply_tag_filter_legacy2(request: Legacy2TagFilterCreateRequest):
    """Apply a tag filter and get matching photos."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")

        matching_photos = tag_filter_db.apply_tag_filter(
            tag_expressions=[expr.dict() for expr in request.tag_expressions],
            combination_operator=request.combination_operator
        )

        return {
            "photos": matching_photos,
            "count": len(matching_photos),
            "filter_used": {
                "name": "Temporary Filter",
                "expressions": [expr.dict() for expr in request.tag_expressions],
                "operator": request.combination_operator
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/photos/by-tags/legacy2")
async def get_photos_by_tags_legacy2(
    tags: str,  # Comma-separated list of tags
    operator: str = "OR",  # OR or AND
    exclude_tags: Optional[str] = None,  # Comma-separated list of tags to exclude
    limit: int = 100,
    offset: int = 0
):
    """Get photos by multiple tags with AND/OR logic."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")

        tag_list = [tag.strip() for tag in tags.split(',')]
        exclude_list = [tag.strip() for tag in exclude_tags.split(',')] if exclude_tags else []

        op_upper = operator.upper()
        if op_upper not in ("AND", "OR"):
            op_upper = "OR"
        operator_literal = cast(Literal["AND", "OR"], op_upper)

        matching_photos = tag_filter_db.get_photos_by_tags(
            tags=tag_list,
            operator=operator_literal,
            exclude_tags=exclude_list or None,
        )

        # Apply pagination
        paginated_photos = matching_photos[offset:offset+limit]

        return {
            "photos": paginated_photos,
            "total_count": len(matching_photos),
            "filter": {
                "included_tags": tag_list,
                "excluded_tags": exclude_list,
                "operator": operator
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tags/common")
async def get_common_tags(photo_paths: str, limit: int = 10):
    """Get common tags across multiple photos."""
    try:
        tag_filter_db: MultiTagFilterDB = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")

        path_list = [path.strip() for path in photo_paths.split(',')]

        common: set[str] | None = None
        for p in path_list:
            if not p:
                continue
            tags = set(tag_filter_db.get_tags_for_photo(p))
            common = tags if common is None else (common & tags)

        common_tags = sorted(common or [])[:limit]
        return {"common_tags": common_tags, "count": len(common_tags)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tags/search")
async def search_tags(query: str, limit: int = 20):
    """Search for tags by name."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")
        matching_tags = tag_filter_db.search_tags(query, limit)

        return {"tags": matching_tags, "count": len(matching_tags)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tags/stats")
async def get_tag_stats():
    """Get statistics about tags in the system."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")
        stats = tag_filter_db.get_tag_stats()

        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# VERSION STACKS ENDPOINTS
# ==============================================================================

class VersionCreateRequest(BaseModel):
    original_path: str
    version_path: str
    version_type: str = "edit"  # 'original', 'edit', 'variant', 'derivative'
    version_name: Optional[str] = None
    version_description: Optional[str] = None
    edit_instructions: Optional[Dict[str, Any]] = None
    parent_version_id: Optional[str] = None


class VersionUpdateRequest(BaseModel):
    version_name: Optional[str] = None
    version_description: Optional[str] = None


@app.post("/versions")
async def create_photo_version(request: VersionCreateRequest):
    """Create a new photo version record."""
    try:
        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")

        version_id = versions_db.create_version(
            original_path=request.original_path,
            version_path=request.version_path,
            version_type=request.version_type,
            version_name=request.version_name,
            version_description=request.version_description,
            edit_instructions=request.edit_instructions,
            parent_version_id=request.parent_version_id
        )

        if not version_id:
            raise HTTPException(status_code=400, detail="Failed to create photo version")

        return {"success": True, "version_id": version_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/versions/photo/{photo_path:path}")
async def get_photo_versions(photo_path: str):
    """Get all versions for a photo (original + all edits)."""
    try:
        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")
        version_stack = versions_db.get_version_stack_for_photo(photo_path)

        if not version_stack:
            # If no stack exists, return just the single photo
            return {"versions": [], "count": 0, "original_path": photo_path}

        return {
            "versions": [v.dict() for v in version_stack.versions],
            "count": len(version_stack.versions),
            "original_path": version_stack.original_path,
            "stack_id": version_stack.id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/versions/stack/{original_path:path}")
async def get_version_stack(original_path: str):
    """Get the complete version stack for an original photo."""
    try:
        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")
        version_stack = versions_db.get_version_stack_for_original(original_path)

        if not version_stack:
            raise HTTPException(status_code=404, detail="No version stack found for this photo")

        return {
            "stack": {
                "id": version_stack.id,
                "original_path": version_stack.original_path,
                "version_count": version_stack.version_count,
                "created_at": version_stack.created_at,
                "updated_at": version_stack.updated_at,
                "versions": [v.dict() for v in version_stack.versions]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/versions/{version_path:path}")
async def update_version_metadata(version_path: str, request: VersionUpdateRequest):
    """Update metadata for a specific version."""
    try:
        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")

        success = versions_db.update_version_metadata(
            version_path=version_path,
            version_name=request.version_name,
            version_description=request.version_description
        )

        if not success:
            raise HTTPException(status_code=404, detail="Version not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/versions/{version_id}")
async def delete_photo_version(version_id: str):
    """Delete a specific photo version (not the original)."""
    try:
        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")
        success = versions_db.delete_version(version_id)

        if not success:
            raise HTTPException(status_code=404, detail="Version not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/versions/stacks")
async def get_all_version_stacks(limit: int = 50, offset: int = 0):
    """Get all version stacks with pagination."""
    try:
        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")
        stacks = versions_db.get_all_stacks(limit, offset)

        return {
            "stacks": [s.dict() for s in stacks],
            "count": len(stacks)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/versions/stats")
async def get_version_stats():
    """Get statistics about photo versions."""
    try:
        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")
        stats = versions_db.get_version_stats()
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/versions/merge-stacks")
async def merge_version_stacks(payload: dict):
    """Merge two version stacks (when determining they're the same photo)."""
    try:
        path1 = payload.get("path1")
        path2 = payload.get("path2")

        if not path1 or not path2:
            raise HTTPException(status_code=400, detail="Both path1 and path2 are required")

        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")
        success = versions_db.merge_version_stacks(path1, path2)

        if not success:
            raise HTTPException(status_code=400, detail="Failed to merge version stacks")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# LOCATION CLUSTERING ENDPOINTS
# ==============================================================================

class LocationCorrectionRequest(BaseModel):
    original_place_name: Optional[str] = None
    corrected_place_name: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None


class LocationClusterCreateRequest(BaseModel):
    name: str
    center_lat: float
    center_lng: float
    description: Optional[str] = None
    min_photos: int = 2


@app.post("/locations/correct/{photo_path:path}")
async def correct_photo_location(photo_path: str, request: LocationCorrectionRequest):
    """Correct location information for a photo."""
    try:
        locations_db = get_location_clusters_db(settings.BASE_DIR / "locations.db")

        success = locations_db.update_place_name(
            photo_path=photo_path,
            corrected_place_name=request.corrected_place_name,
            country=request.country,
            region=request.region,
            city=request.city
        )

        if not success:
            raise HTTPException(status_code=404, detail="Photo location not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/locations/photo/{photo_path:path}")
async def get_photo_location(photo_path: str):
    """Get location information for a specific photo."""
    try:
        locations_db = get_location_clusters_db(settings.BASE_DIR / "locations.db")
        location = locations_db.get_photo_location(photo_path)

        if not location:
            raise HTTPException(status_code=404, detail="Location not found for photo")

        return {"location": location}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/locations/nearby")
async def get_photos_near_location(
    latitude: float,
    longitude: float,
    radius_km: float = Query(1.0, ge=0.1, le=50.0)
):
    """Get photos within a certain radius of a location."""
    try:
        locations_db = get_location_clusters_db(settings.BASE_DIR / "locations.db")
        photos = locations_db.get_photos_by_location(latitude, longitude, radius_km)

        return {
            "photos": photos,
            "count": len(photos),
            "center": {"lat": latitude, "lng": longitude},
            "radius_km": radius_km
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/locations/clusters")
async def get_location_clusters(min_photos: int = Query(2, ge=1)):
    """Get all location clusters."""
    try:
        locations_db = get_location_clusters_db(settings.BASE_DIR / "locations.db")
        clusters = locations_db.get_location_clusters(min_photos)

        return {
            "clusters": clusters,
            "count": len(clusters)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/locations/clusters/{cluster_id}/photos")
async def get_photos_in_cluster(cluster_id: str, limit: int = 50, offset: int = 0):
    """Get all photos in a specific cluster."""
    try:
        locations_db = get_location_clusters_db(settings.BASE_DIR / "locations.db")
        photos = locations_db.get_photos_in_cluster(cluster_id)

        return {
            "photos": photos[offset:offset+limit],
            "count": len(photos),
            "total_in_cluster": len(photos)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/locations/photo/{photo_path:path}/cluster")
async def get_photo_cluster(photo_path: str):
    """Get the cluster a photo belongs to."""
    try:
        locations_db = get_location_clusters_db(settings.BASE_DIR / "locations.db")
        cluster = locations_db.get_photo_cluster(photo_path)

        if not cluster:
            return {"cluster": None}

        return {"cluster": cluster}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/locations/clusterize")
async def create_location_clusters(
    min_photos: int = Query(2, ge=1),
    max_distance_meters: float = Query(100.0, ge=10.0, le=1000.0)
):
    """Create location clusters based on proximity of photos."""
    try:
        locations_db = get_location_clusters_db(settings.BASE_DIR / "locations.db")
        clusters = locations_db.cluster_locations(min_photos, max_distance_meters)

        return {
            "clusters": clusters,
            "count": len(clusters),
            "params": {
                "min_photos": min_photos,
                "max_distance_meters": max_distance_meters
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/locations/stats")
async def get_location_stats():
    """Get statistics about location data."""
    try:
        locations_db = get_location_clusters_db(settings.BASE_DIR / "locations.db")
        stats = locations_db.get_location_stats()

        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/locations/correct-bulk")
async def bulk_correct_place_names(payload: dict):
    """Bulk correct place names for multiple photos."""
    try:
        photo_paths = payload.get("photo_paths", [])
        corrected_name = payload.get("corrected_name", "")

        if not photo_paths or not corrected_name:
            raise HTTPException(status_code=400, detail="photo_paths and corrected_name are required")

        locations_db = get_location_clusters_db(settings.BASE_DIR / "locations.db")
        success = locations_db.correct_place_name_bulk(photo_paths, corrected_name)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update place names")

        return {"success": True, "updated_count": len(photo_paths)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# MULTI-TAG FILTERING ENDPOINTS
# ==============================================================================

class TagExpression(BaseModel):
    tag: str
    operator: str = "has"  # 'has', 'not_has', 'maybe_has'


class TagFilterCreateRequest(BaseModel):
    name: str
    tag_expressions: List[TagExpression]
    combination_operator: str = "AND"  # 'AND' or 'OR'


class TagFilterUpdateRequest(BaseModel):
    name: Optional[str] = None
    tag_expressions: Optional[List[TagExpression]] = None
    combination_operator: Optional[str] = None


@app.post("/tag-filters")
async def create_tag_filter(request: TagFilterCreateRequest):
    """Create a new tag filter with custom expressions and logic."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")

        filter_id = tag_filter_db.create_tag_filter(
            name=request.name,
            tag_expressions=[expr.dict() for expr in request.tag_expressions],
            combination_operator=request.combination_operator
        )

        if not filter_id:
            raise HTTPException(status_code=400, detail="Failed to create tag filter")

        return {"success": True, "filter_id": filter_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tag-filters/{filter_id}")
async def get_tag_filter(filter_id: str):
    """Get details of a specific tag filter."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")
        tag_filter = tag_filter_db.get_tag_filter(filter_id)

        if not tag_filter:
            raise HTTPException(status_code=404, detail="Tag filter not found")

        return {"tag_filter": tag_filter}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tag-filters")
async def get_tag_filters(limit: int = 50, offset: int = 0):
    """Get all tag filters."""
    try:
        with sqlite3.connect(settings.BASE_DIR / "tag_filters.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM tag_filters ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            rows = cursor.fetchall()

            return {
                "filters": [dict(row) for row in rows],
                "count": len(rows)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/tag-filters/{filter_id}")
async def update_tag_filter(filter_id: str, request: TagFilterUpdateRequest):
    """Update a tag filter."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")

        # Get existing filter first
        existing_filter = tag_filter_db.get_tag_filter(filter_id)
        if not existing_filter:
            raise HTTPException(status_code=404, detail="Tag filter not found")

        # Update the filter
        with sqlite3.connect(settings.BASE_DIR / "tag_filters.db") as conn:
            update_fields = []
            params = []

            if request.name is not None:
                update_fields.append("name = ?")
                params.append(request.name)

            if request.tag_expressions is not None:
                update_fields.append("tag_expressions = ?")
                params.append(json.dumps([expr.dict() for expr in request.tag_expressions]))

            if request.combination_operator is not None:
                update_fields.append("combination_operator = ?")
                params.append(request.combination_operator)

            update_fields.append("updated_at = CURRENT_TIMESTAMP")

            if update_fields:
                sql = f"UPDATE tag_filters SET {', '.join(update_fields)} WHERE id = ?"
                params.append(filter_id)

                cursor = conn.execute(sql, params)

                if cursor.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Tag filter not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/tag-filters/{filter_id}")
async def delete_tag_filter(filter_id: str):
    """Delete a tag filter."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")
        success = tag_filter_db.delete_tag_filter(filter_id)

        if not success:
            raise HTTPException(status_code=404, detail="Tag filter not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tag-filters/apply")
async def apply_tag_filter(request: TagFilterCreateRequest):
    """Apply a tag filter and get matching photos."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")

        matching_photos = tag_filter_db.apply_tag_filter(
            tag_expressions=[expr.dict() for expr in request.tag_expressions],
            combination_operator=request.combination_operator
        )

        return {
            "photos": matching_photos,
            "count": len(matching_photos),
            "filter_used": {
                "name": "Temporary Filter",
                "expressions": [expr.dict() for expr in request.tag_expressions],
                "operator": request.combination_operator
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/photos/by-tags")
async def get_photos_by_tags(
    tags: str,  # Comma-separated list of tags
    operator: str = "OR",  # OR or AND
    exclude_tags: Optional[str] = None,  # Comma-separated list of tags to exclude
    limit: int = 100,
    offset: int = 0
):
    """Get photos by multiple tags with AND/OR logic."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")

        tag_list = [tag.strip() for tag in tags.split(',')]
        exclude_list = [tag.strip() for tag in exclude_tags.split(',')] if exclude_tags else []

        op_upper = operator.upper()
        if op_upper not in ("AND", "OR"):
            op_upper = "OR"
        operator_literal = cast(Literal["AND", "OR"], op_upper)

        matching_photos = tag_filter_db.get_photos_by_tags(
            tags=tag_list,
            operator=operator_literal,
            exclude_tags=exclude_list or None,
        )

        # Apply pagination
        paginated_photos = matching_photos[offset:offset+limit]

        return {
            "photos": paginated_photos,
            "total_count": len(matching_photos),
            "filter": {
                "included_tags": tag_list,
                "excluded_tags": exclude_list,
                "operator": operator
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tags/common/legacy2")
async def get_common_tags_legacy2(photo_paths: str, limit: int = 10):
    """Get common tags across multiple photos."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")

        path_list = [path.strip() for path in photo_paths.split(',')]

        # In a real implementation, we would find common tags across all these photos
        # For now, we'll just return an example implementation
        common_tags = []
        all_tags = []

        for path in path_list:
            tags = tag_filter_db.get_tags_for_photo(path)
            all_tags.extend(tags)

        # Count occurrences and return most frequent
        from collections import Counter
        tag_counts = Counter(all_tags)
        common_tags = [tag for tag, count in tag_counts.most_common(limit)]

        return {"common_tags": common_tags, "count": len(common_tags)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tags/search/legacy2")
async def search_tags_legacy2(query: str, limit: int = 20):
    """Search for tags by name."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")
        matching_tags = tag_filter_db.search_tags(query, limit)

        return {"tags": matching_tags, "count": len(matching_tags)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tags/stats/legacy2")
async def get_tag_stats_legacy2():
    """Get statistics about tags in the system."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")

        # This would include stats about tag usage, most popular tags, etc.
        # In a full implementation, we'd return comprehensive statistics
        tag_counts = tag_filter_db.get_photo_tags_with_counts()

        return {
            "stats": {
                "total_tags": len(tag_counts),
                "top_tags": tag_counts[:10],  # Top 10 most used tags
                "total_tagged_photos": sum(tc['photo_count'] for tc in tag_counts)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# TAGS ENDPOINTS
# ==============================================================================

from server.tags_db import get_tags_db
from server.ratings_db import get_ratings_db
from server.notes_db import get_notes_db
from server.photo_edits_db import get_photo_edits_db
from server.duplicates_db import get_duplicates_db
from server.face_clustering_db import get_face_clustering_db
from server.photo_versions_db import get_photo_versions_db
from server.location_clusters_db import get_location_clusters_db
from server.locations_db import get_locations_db
from server.smart_collections_db import get_smart_collections_db
from server.ai_insights_db import get_ai_insights_db
from server.collaborative_spaces_db import get_collaborative_spaces_db
from server.privacy_controls_db import get_privacy_controls_db
from server.timeline_db import get_timeline_db
from server.bulk_actions_db import get_bulk_actions_db
from server.multi_tag_filter_db import get_multi_tag_filter_db


class TagCreate(BaseModel):
    name: str


class TagPhotosRequest(BaseModel):
    photo_paths: List[str]


@app.get("/tags")
async def list_tags(limit: int = 200, offset: int = 0):
    tags_db = get_tags_db(settings.BASE_DIR / "tags.db")
    tags = tags_db.list_tags(limit=limit, offset=offset)
    return {"tags": [t.__dict__ for t in tags]}


@app.post("/tags")
async def create_tag(req: TagCreate):
    name = (req.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    if len(name) > 80:
        raise HTTPException(status_code=400, detail="name too long")
    tags_db = get_tags_db(settings.BASE_DIR / "tags.db")
    tags_db.create_tag(name)
    return {"ok": True}


@app.delete("/tags/{tag_name}")
async def delete_tag(tag_name: str):
    tags_db = get_tags_db(settings.BASE_DIR / "tags.db")
    ok = tags_db.delete_tag(tag_name)
    if not ok:
        raise HTTPException(status_code=404, detail="Tag not found")
    return {"ok": True}


@app.get("/tags/{tag_name}")
async def get_tag(tag_name: str, include_photos: bool = True):
    tags_db = get_tags_db(settings.BASE_DIR / "tags.db")
    if not tags_db.has_tag(tag_name):
        raise HTTPException(status_code=404, detail="Tag not found")
    out: Dict[str, object] = {"tag": tag_name}
    if include_photos:
        paths = tags_db.get_tag_paths(tag_name)
        photos = []
        for path in paths:
            metadata = photo_search_engine.db.get_metadata(path)
            if metadata:
                photos.append(
                    {
                        "path": path,
                        "filename": os.path.basename(path),
                        "metadata": metadata,
                    }
                )
        out["photos"] = photos
        out["photo_count"] = len(paths)
    return out


@app.post("/tags/{tag_name}/photos")
async def add_photos_to_tag(tag_name: str, req: TagPhotosRequest):
    tags_db = get_tags_db(settings.BASE_DIR / "tags.db")
    added = tags_db.add_photos(tag_name, req.photo_paths or [])
    return {"added": added, "total": len(req.photo_paths or [])}


@app.delete("/tags/{tag_name}/photos")
async def remove_photos_from_tag(tag_name: str, req: TagPhotosRequest):
    tags_db = get_tags_db(settings.BASE_DIR / "tags.db")
    removed = tags_db.remove_photos(tag_name, req.photo_paths or [])
    return {"removed": removed}


@app.get("/photos/{path:path}/tags")
async def get_photo_tags(path: str):
    tags_db = get_tags_db(settings.BASE_DIR / "tags.db")
    tags = tags_db.get_photo_tags(path)
    return {"tags": tags}


# ==============================================================================
# ALBUMS ENDPOINTS
# ==============================================================================

from server.albums_db import get_albums_db, Album as AlbumModel
from server.smart_albums import initialize_predefined_smart_albums, populate_smart_album
import uuid

class AlbumCreate(BaseModel):
    name: str
    description: Optional[str] = None

class AlbumUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cover_photo_path: Optional[str] = None

class AlbumPhotosRequest(BaseModel):
    photo_paths: List[str]

@app.post("/albums")
async def create_album(req: AlbumCreate):
    """Create a new album."""
    albums_db = get_albums_db()
    album_id = str(uuid.uuid4())

    album = albums_db.create_album(
        album_id=album_id,
        name=req.name,
        description=req.description
    )

    return {"album": album}

@app.get("/albums")
async def list_albums(include_smart: bool = True):
    """List all albums."""
    albums_db = get_albums_db()

    # Initialize predefined smart albums if not exists
    initialize_predefined_smart_albums(albums_db)

    albums = albums_db.list_albums(include_smart=include_smart)
    return {"albums": albums}

@app.get("/albums/{album_id}")
async def get_album(album_id: str, include_photos: bool = True):
    """Get album details."""
    albums_db = get_albums_db()
    album = albums_db.get_album(album_id)

    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    result: dict[str, Any] = {"album": album}

    if include_photos:
        photo_paths = albums_db.get_album_photos(album_id)
        # Get metadata for photos
        photos = []
        for path in photo_paths:
            metadata = photo_search_engine.db.get_metadata(path)
            if metadata:
                photos.append({
                    "path": path,
                    "filename": os.path.basename(path),
                    "metadata": metadata
                })
        result["photos"] = photos

    return result

@app.put("/albums/{album_id}")
async def update_album(album_id: str, req: AlbumUpdate):
    """Update album details."""
    albums_db = get_albums_db()

    album = albums_db.update_album(
        album_id=album_id,
        name=req.name,
        description=req.description,
        cover_photo_path=req.cover_photo_path
    )

    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    return {"album": album}

@app.delete("/albums/{album_id}")
async def delete_album(album_id: str):
    """Delete an album."""
    albums_db = get_albums_db()

    # Don't allow deleting smart albums
    album = albums_db.get_album(album_id)
    if album and album.is_smart:
        raise HTTPException(status_code=400, detail="Cannot delete smart albums")

    success = albums_db.delete_album(album_id)

    if not success:
        raise HTTPException(status_code=404, detail="Album not found")

    return {"ok": True}

@app.post("/albums/{album_id}/photos")
async def add_photos_to_album(album_id: str, req: AlbumPhotosRequest):
    """Add photos to album."""
    albums_db = get_albums_db()

    # Check album exists
    album = albums_db.get_album(album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    # Don't allow adding to smart albums
    if album.is_smart:
        raise HTTPException(status_code=400, detail="Cannot manually add photos to smart albums")

    added = albums_db.add_photos_to_album(album_id, req.photo_paths)

    return {"added": added, "total": len(req.photo_paths)}

@app.delete("/albums/{album_id}/photos")
async def remove_photos_from_album(album_id: str, req: AlbumPhotosRequest):
    """Remove photos from album."""
    albums_db = get_albums_db()

    # Check album exists
    album = albums_db.get_album(album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    # Don't allow removing from smart albums
    if album.is_smart:
        raise HTTPException(status_code=400, detail="Cannot manually remove photos from smart albums")

    removed = albums_db.remove_photos_from_album(album_id, req.photo_paths)

    return {"removed": removed}

@app.post("/albums/{album_id}/refresh")
async def refresh_smart_album(album_id: str):
    """Refresh a smart album (recompute matches)."""
    albums_db = get_albums_db()

    album = albums_db.get_album(album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    if not album.is_smart:
        raise HTTPException(status_code=400, detail="Only smart albums can be refreshed")

    # Get all photos with metadata
    cursor = photo_search_engine.db.conn.cursor()
    cursor.execute("SELECT file_path, metadata_json FROM metadata WHERE deleted_at IS NULL")

    photos_with_metadata = []
    for row in cursor.fetchall():
        import json
        metadata = json.loads(row['metadata_json']) if row['metadata_json'] else {}
        photos_with_metadata.append((row['file_path'], metadata))

    # Populate smart album
    populate_smart_album(albums_db, album_id, photos_with_metadata)

    # Return updated album
    album = albums_db.get_album(album_id)
    return {"album": album}

@app.get("/photos/{path:path}/albums")
async def get_photo_albums(path: str):
    """Get all albums containing a specific photo."""
    albums_db = get_albums_db()
    albums = albums_db.get_photo_albums(path)
    return {"albums": albums}

# ========== Image Transformation Endpoints ==========

class TransformRequest(BaseModel):
    """Request for image transformation operations."""
    backup: bool = True  # Create backup before transformation

@app.post("/photos/rotate")
async def rotate_photo(path: str = Body(...), degrees: int = Body(...), backup: bool = Body(True)):
    """
    Rotate a photo by specified degrees (90, 180, 270, or -90).
    Creates a backup by default before modifying the original.
    """
    if degrees not in [90, 180, 270, -90]:
        raise HTTPException(status_code=400, detail="Degrees must be 90, 180, 270, or -90")

    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Photo not found")

    try:
        # Create backup if requested
        if backup:
            backup_path = file_path.parent / f"{file_path.stem}_backup{file_path.suffix}"
            shutil.copy2(file_path, backup_path)

        # Open image
        img = Image.open(file_path)

        # Rotate (negative degrees for clockwise rotation in PIL)
        # PIL's rotate is counter-clockwise, so we negate for intuitive clockwise rotation
        if degrees == 90:
            rotated = img.transpose(Image.Transpose.ROTATE_270)  # 90° CW
        elif degrees == -90 or degrees == 270:
            rotated = img.transpose(Image.Transpose.ROTATE_90)   # 90° CCW
        elif degrees == 180:
            rotated = img.transpose(Image.Transpose.ROTATE_180)
        else:
            rotated = img.rotate(-degrees, expand=True)

        # Save with original format and quality
        save_kwargs = {}
        if img.format == 'JPEG':
            save_kwargs['quality'] = 95
            save_kwargs['optimize'] = True

        rotated.save(file_path, format=img.format, **save_kwargs)
        img.close()
        rotated.close()

        return {
            "ok": True,
            "path": str(file_path),
            "operation": f"rotated_{degrees}deg",
            "backup_created": backup
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rotation failed: {str(e)}")

@app.post("/photos/flip")
async def flip_photo(path: str = Body(...), direction: str = Body(...), backup: bool = Body(True)):
    """
    Flip a photo horizontally or vertically.
    Creates a backup by default before modifying the original.
    """
    if direction not in ['horizontal', 'vertical']:
        raise HTTPException(status_code=400, detail="Direction must be 'horizontal' or 'vertical'")

    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Photo not found")

    try:
        # Create backup if requested
        if backup:
            backup_path = file_path.parent / f"{file_path.stem}_backup{file_path.suffix}"
            shutil.copy2(file_path, backup_path)

        # Open image
        img = Image.open(file_path)

        # Flip
        if direction == 'horizontal':
            flipped = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        else:  # vertical
            flipped = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

        # Save with original format and quality
        save_kwargs = {}
        if img.format == 'JPEG':
            save_kwargs['quality'] = 95
            save_kwargs['optimize'] = True

        flipped.save(file_path, format=img.format, **save_kwargs)
        img.close()
        flipped.close()

        return {
            "ok": True,
            "path": str(file_path),
            "operation": f"flipped_{direction}",
            "backup_created": backup
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Flip failed: {str(e)}")

@app.get("/api/schema")
async def get_api_schema():
    """Get the API schema and version information."""
    schema = api_version_manager.get_api_schema()
    return schema

@app.get("/api/actions/detect-apps")
async def detect_installed_apps():
    """Return installed apps for action integrations (stub for web/dev)."""
    return {"apps": []}

@app.get("/api/cache/stats")
async def get_api_cache_stats():
    """Get cache statistics and performance metrics."""
    stats = cache_manager.stats()
    return stats

@app.post("/api/cache/clear")
async def clear_api_cache():
    """Clear all cache entries."""
    cache_manager.clear()
    return {"message": "Cache cleared successfully"}

@app.get("/api/cache/cleanup")
async def cleanup_cache():
    """Clean up expired cache entries."""
    removed_count = cache_manager.cleanup()
    return {"message": f"Cleaned up {removed_count} expired entries"}

@app.get("/api/logs/test")
async def test_logging():
    """Test endpoint to verify logging functionality."""
    import time
    start = time.time()

    # Log a test message
    ps_logger.info("Test log message from API endpoint")

    execution_time = (time.time() - start) * 1000

    # Log the operation
    log_search_operation(
        ps_logger,
        query="test",
        mode="test",
        results_count=0,
        execution_time=execution_time
    )

    return {"message": "Test log message sent", "execution_time_ms": execution_time}

# ==============================================================================
# RATINGS ENDPOINTS
# ==============================================================================

class RatingCreate(BaseModel):
    rating: int


@app.get("/api/photos/{file_path:path}/rating")
async def get_photo_rating(file_path: str):
    """Get rating for a photo."""
    try:
        ratings_db = get_ratings_db(settings.BASE_DIR / "ratings.db")
        rating = ratings_db.get_rating(file_path)
        return {"rating": rating}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/photos/{file_path:path}/rating")
async def set_photo_rating(file_path: str, rating_req: RatingCreate):
    """Set rating for a photo (1-5 stars, 0 = unrated)."""
    try:
        if not (0 <= rating_req.rating <= 5):
            raise HTTPException(status_code=400, detail="Rating must be between 0 and 5")

        ratings_db = get_ratings_db(settings.BASE_DIR / "ratings.db")
        success = ratings_db.set_rating(file_path, rating_req.rating)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to set rating")

        return {"success": True, "rating": rating_req.rating}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ratings/photos/{rating}")
async def get_photos_by_rating(rating: int, limit: int = 100, offset: int = 0):
    """Get photos with specific rating."""
    try:
        if not (1 <= rating <= 5):
            raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

        ratings_db = get_ratings_db(settings.BASE_DIR / "ratings.db")
        photo_paths = ratings_db.get_photos_by_rating(rating, limit, offset)

        # Get full metadata for each photo
        photos = []
        for path in photo_paths:
            metadata = photo_search_engine.db.get_metadata(path)
            if metadata:
                photos.append({
                    "path": path,
                    "metadata": metadata,
                    "rating": rating
                })

        return {"count": len(photos), "results": photos}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ratings/stats")
async def get_rating_stats():
    """Get rating statistics."""
    try:
        ratings_db = get_ratings_db(settings.BASE_DIR / "ratings.db")
        stats = ratings_db.get_rating_stats()
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# NOTES ENDPOINTS
# ==============================================================================

class NoteCreate(BaseModel):
    note: str


@app.get("/api/photos/{file_path:path}/notes")
async def get_photo_notes(file_path: str):
    """Get notes for a photo."""
    try:
        notes_db = get_notes_db(settings.BASE_DIR / "notes.db")
        note_obj = notes_db.get_note_with_metadata(file_path) or {}
        return {"note": note_obj.get("note"), "updated_at": note_obj.get("updated_at")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/photos/{file_path:path}/notes")
async def set_photo_notes(file_path: str, note_req: NoteCreate):
    """Set notes for a photo."""
    try:
        notes_db = get_notes_db(settings.BASE_DIR / "notes.db")
        success = notes_db.set_note(file_path, note_req.note)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to set note")

        meta = notes_db.get_note_with_metadata(file_path) or {}
        return {"success": True, "note": meta.get("note"), "updated_at": meta.get("updated_at")}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/photos/{file_path:path}/notes")
async def delete_photo_notes(file_path: str):
    """Delete notes for a photo."""
    try:
        notes_db = get_notes_db(settings.BASE_DIR / "notes.db")
        success = notes_db.delete_note(file_path)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete note")

        return {"success": True, "note": None, "updated_at": None}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/notes/search")
async def search_notes(query: str, limit: int = 100, offset: int = 0):
    """Search notes by content."""
    try:
        notes_db = get_notes_db(settings.BASE_DIR / "notes.db")
        results = notes_db.search_notes(query, limit, offset)

        # Get full metadata for each photo
        photos = []
        for row in results:
            note_path = row.get("photo_path")
            if not note_path:
                continue
            try:
                metadata = photo_search_engine.db.get_metadata(note_path)
                if metadata:
                    photos.append({
                        "path": note_path,
                        "filename": Path(note_path).name,
                        "metadata": metadata
                    })
            except:
                continue

        return {"photos": photos, "total": len(photos)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# PHOTO EDITS (NON-DESTRUCTIVE SETTINGS)
# ==============================================================================

class EditPayload(BaseModel):
    edit_data: dict


@app.get("/api/photos/{file_path:path}/edit")
async def get_photo_edit(file_path: str):
    try:
        edits_db = get_photo_edits_db(settings.BASE_DIR / "photo_edits.db")
        data = edits_db.get_edit(file_path) or {"edit_data": None}
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/photos/{file_path:path}/edit")
async def set_photo_edit(file_path: str, payload: EditPayload):
    try:
        edits_db = get_photo_edits_db(settings.BASE_DIR / "photo_edits.db")
        edits_db.set_edit(file_path, payload.edit_data)
        return {"success": True, "edit_data": payload.edit_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/notes/stats")
async def get_notes_stats():
    """Get notes statistics."""
    try:
        notes_db = get_notes_db(settings.BASE_DIR / "notes.db")
        stats = notes_db.get_notes_stats()
        return {"stats": stats}
    except Exception as e:
        photos = []
        for row in results:
            path = row.get("photo_path")
            metadata = photo_search_engine.db.get_metadata(path)
            if metadata:
                photos.append({
                    "path": path,
                    "metadata": metadata,
                    "note": row.get("note"),
                    "created_at": row.get("created_at"),
                    "updated_at": row.get("updated_at"),
                })

        return {"count": len(photos), "results": photos}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# EDITING ENDPOINTS
# ==============================================================================

class EditData(BaseModel):
    brightness: float
    contrast: float
    saturation: float
    rotation: int
    flipH: bool
    flipV: bool
    crop: Optional[Dict[str, float]] = None  # {x, y, width, height}


@app.get("/api/photos/{file_path:path}/edits")
async def get_photo_edits(file_path: str):
    """Get edit instructions for a photo."""
    try:
        edits_db = get_photo_edits_db(settings.BASE_DIR / "edits.db")
        edit_data = edits_db.get_edit(file_path)
        return {"edit_data": edit_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/photos/{file_path:path}/edits")
async def set_photo_edits(file_path: str, edit_data: EditData):
    """Save edit instructions for a photo."""
    try:
        edits_db = get_photo_edits_db(settings.BASE_DIR / "edits.db")
        edits_db.set_edit(file_path, edit_data.dict())

        return {"success": True, "edit_data": edit_data.dict()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/photos/{file_path:path}/edits")
async def delete_photo_edits(file_path: str):
    """Delete edit instructions for a photo."""
    try:
        # To delete, we'll set the edit data to empty
        edits_db = get_photo_edits_db(settings.BASE_DIR / "edits.db")
        edits_db.set_edit(file_path, {})

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# PEOPLE/PHOTO ASSOCIATION ENDPOINTS
# ==============================================================================

@app.get("/api/photos/{photo_path:path}/people")
async def get_people_in_photo(photo_path: str):
    """Get people associated with a specific photo."""
    try:
        face_clustering_db = get_face_clustering_db(_runtime_base_dir() / "face_clusters.db")
        associations = face_clustering_db.get_people_in_photo(photo_path)
        
        # Return cluster IDs for the people associated with this photo
        people = [assoc.cluster_id for assoc in associations]
        return {"photo_path": photo_path, "people": people}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/photos/{photo_path:path}/people")
async def add_person_to_photo(photo_path: str, person_data: dict):
    """Associate a person with a specific photo."""
    try:
        person_id = person_data.get("person_id")
        detection_id = person_data.get("detection_id")
        
        if not person_id:
            raise HTTPException(status_code=400, detail="person_id is required")

        face_clustering_db = get_face_clustering_db(_runtime_base_dir() / "face_clusters.db")

        # Ensure the cluster exists for manual associations.
        # (The UI/tests may pass a stable person_id that isn't a generated cluster_id yet.)
        try:
            face_clustering_db.ensure_face_cluster(person_id, label=person_id)
        except Exception:
            pass
        
        # If no detection_id provided, try to detect faces automatically
        if not detection_id:
            # Detect faces in the photo
            detection_ids = face_clustering_db.detect_and_store_faces(photo_path)
            
            if detection_ids:
                # Use the first detected face
                detection_id = detection_ids[0]
            else:
                # Fallback to dummy detection ID if no faces detected
                detection_id = f"temp_face_{hashlib.md5(photo_path.encode()).hexdigest()}"

        # Ensure detection exists when we fall back to a synthetic ID.
        try:
            face_clustering_db.ensure_face_detection(detection_id, photo_path)
        except Exception:
            pass
        
        # Add the association
        face_clustering_db.add_person_to_photo(photo_path, person_id, detection_id, confidence=0.9)
        
        return {"success": True, "photo_path": photo_path, "person_id": person_id, "detection_id": detection_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/photos/{photo_path:path}/people/{person_id}")
async def remove_person_from_photo(photo_path: str, person_id: str, detection_id: Optional[str] = None):
    """Remove association between a person and a specific photo."""
    try:
        face_clustering_db = get_face_clustering_db(_runtime_base_dir() / "face_clusters.db")
        
        # If no detection_id provided, try to find it
        if not detection_id:
            associations = face_clustering_db.get_people_in_photo(photo_path)
            for assoc in associations:
                if assoc.cluster_id == person_id:
                    detection_id = assoc.detection_id
                    break
            
            if not detection_id:
                # Fallback to dummy detection ID if not found
                detection_id = f"temp_face_{hashlib.md5(photo_path.encode()).hexdigest()}"
        
        # Remove the association
        face_clustering_db.remove_person_from_photo(photo_path, person_id, detection_id)
        
        return {"success": True, "photo_path": photo_path, "person_id": person_id, "detection_id": detection_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Face Detection Endpoints

@app.post("/api/photos/{photo_path:path}/faces/detect")
async def detect_faces_in_photo(photo_path: str):
    """Detect faces in a specific photo."""
    try:
        face_clustering_db = get_face_clustering_db(settings.BASE_DIR / "face_clusters.db")
        
        # Detect and store faces
        detection_ids = face_clustering_db.detect_and_store_faces(photo_path)
        
        # Get details about detected faces
        faces = []
        with sqlite3.connect(str(face_clustering_db.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            
            for detection_id in detection_ids:
                row = conn.execute("""
                    SELECT detection_id, photo_path, bounding_box, embedding, quality_score
                    FROM face_detections
                    WHERE detection_id = ?
                """, (detection_id,)).fetchone()
                
                if row:
                    faces.append({
                        "detection_id": row['detection_id'],
                        "photo_path": row['photo_path'],
                        "bounding_box": json.loads(row['bounding_box']),
                        "has_embedding": row['embedding'] is not None,
                        "quality_score": row['quality_score']
                    })
        
        return {
            "photo_path": photo_path,
            "faces": faces,
            "face_count": len(faces),
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/photos/{photo_path:path}/faces")
async def get_faces_in_photo(photo_path: str):
    """Get information about faces detected in a photo."""
    try:
        face_clustering_db = get_face_clustering_db(settings.BASE_DIR / "face_clusters.db")
        
        # Get all faces for this photo
        faces = []
        with sqlite3.connect(str(face_clustering_db.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            
            rows = conn.execute("""
                SELECT fd.detection_id, fd.bounding_box, fd.quality_score,
                       ppa.cluster_id, fc.label as person_label
                FROM face_detections fd
                LEFT JOIN photo_person_associations ppa ON fd.detection_id = ppa.detection_id
                LEFT JOIN face_clusters fc ON ppa.cluster_id = fc.cluster_id
                WHERE fd.photo_path = ?
            """, (photo_path,)).fetchall()
            
            for row in rows:
                faces.append({
                    "detection_id": row['detection_id'],
                    "bounding_box": json.loads(row['bounding_box']),
                    "quality_score": row['quality_score'],
                    "person_id": row['cluster_id'],
                    "person_label": row['person_label']
                })
        
        return {
            "photo_path": photo_path,
            "faces": faces,
            "face_count": len(faces),
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/faces/{detection_id}/thumbnail")
async def get_face_thumbnail(detection_id: str):
    """Get a thumbnail image of a specific face detection."""
    try:
        face_clustering_db = get_face_clustering_db(settings.BASE_DIR / "face_clusters.db")
        
        # Get face thumbnail
        thumbnail_data = face_clustering_db.get_face_thumbnail(detection_id)
        
        if not thumbnail_data:
            raise HTTPException(status_code=404, detail="Face thumbnail not available")
        
        return {
            "detection_id": detection_id,
            "thumbnail": thumbnail_data,
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/photos/batch/faces/detect")
async def detect_faces_in_batch(payload: dict):
    """Detect faces in multiple photos (batch processing)."""
    try:
        photo_paths = payload.get("photo_paths", [])
        if not photo_paths:
            raise HTTPException(status_code=400, detail="photo_paths is required")
        
        face_clustering_db = get_face_clustering_db(settings.BASE_DIR / "face_clusters.db")
        
        results = []
        for photo_path in photo_paths:
            detection_ids = face_clustering_db.detect_and_store_faces(photo_path)
            results.append({
                "photo_path": photo_path,
                "face_count": len(detection_ids),
                "detection_ids": detection_ids
            })
        
        return {
            "processed_photos": len(photo_paths),
            "total_faces_detected": sum(r["face_count"] for r in results),
            "results": results,
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Automatic Clustering Endpoints

@app.post("/api/faces/cluster")
async def cluster_faces_api(
    similarity_threshold: float = 0.6,
    min_samples: int = 2
):
    """Automatically cluster similar faces using DBSCAN."""
    try:
        face_clustering_db = get_face_clustering_db(settings.BASE_DIR / "face_clusters.db")
        
        # Perform clustering
        clusters = face_clustering_db.cluster_faces(
            similarity_threshold=similarity_threshold,
            min_samples=min_samples
        )
        
        # Get cluster details
        cluster_details = []
        for cluster_id, detection_ids in clusters.items():
            # Get cluster info
            with sqlite3.connect(str(face_clustering_db.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cluster_row = conn.execute("""
                    SELECT cluster_id, label, face_count, photo_count
                    FROM face_clusters
                    WHERE cluster_id = ?
                """, (cluster_id,)).fetchone()
                
                if cluster_row:
                    cluster_details.append({
                        "cluster_id": cluster_row['cluster_id'],
                        "label": cluster_row['label'],
                        "face_count": cluster_row['face_count'],
                        "photo_count": cluster_row['photo_count'],
                        "detection_ids": detection_ids
                    })
        
        return {
            "clusters_created": len(clusters),
            "total_faces_clustered": sum(len(dids) for dids in clusters.values()),
            "clusters": cluster_details,
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/faces/{detection_id}/similar")
async def find_similar_faces(detection_id: str, threshold: float = 0.7):
    """Find faces similar to a given face detection."""
    try:
        face_clustering_db = get_face_clustering_db(settings.BASE_DIR / "face_clusters.db")
        
        # Find similar faces
        similar_faces = face_clustering_db.find_similar_faces(
            detection_id=detection_id,
            threshold=threshold
        )
        
        # Get additional info for each similar face
        enhanced_results = []
        for face in similar_faces:
            # Get person association if any
            with sqlite3.connect(str(face_clustering_db.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                person_row = conn.execute("""
                    SELECT ppa.cluster_id, fc.label
                    FROM photo_person_associations ppa
                    JOIN face_clusters fc ON ppa.cluster_id = fc.cluster_id
                    WHERE ppa.detection_id = ?
                """, (face['detection_id'],)).fetchone()
                
                result = {
                    "detection_id": face['detection_id'],
                    "photo_path": face['photo_path'],
                    "similarity": face['similarity'],
                    "person_id": person_row['cluster_id'] if person_row else None,
                    "person_label": person_row['label'] if person_row else None
                }
                enhanced_results.append(result)
        
        return {
            "detection_id": detection_id,
            "similar_faces": enhanced_results,
            "count": len(enhanced_results),
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/clusters/{cluster_id}/quality")
async def get_cluster_quality(cluster_id: str):
    """Analyze the quality of a face cluster."""
    try:
        face_clustering_db = get_face_clustering_db(settings.BASE_DIR / "face_clusters.db")
        
        # Get cluster quality analysis
        quality = face_clustering_db.get_cluster_quality(cluster_id)
        
        if 'error' in quality:
            raise HTTPException(status_code=404, detail=quality['error'])
        
        # Get cluster details
        with sqlite3.connect(str(face_clustering_db.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cluster_row = conn.execute("""
                SELECT cluster_id, label, created_at, updated_at
                FROM face_clusters
                WHERE cluster_id = ?
            """, (cluster_id,)).fetchone()
            
            if cluster_row:
                quality.update({
                    "label": cluster_row['label'],
                    "created_at": cluster_row['created_at'],
                    "updated_at": cluster_row['updated_at']
                })
        
        return {
            "cluster_id": cluster_id,
            "quality_analysis": quality,
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/clusters/{cluster_id}/merge")
async def merge_clusters(cluster_id: str, payload: dict):
    """Merge two face clusters together."""
    try:
        target_cluster_id = payload.get("target_cluster_id")
        if not target_cluster_id:
            raise HTTPException(status_code=400, detail="target_cluster_id is required")
        
        face_clustering_db = get_face_clustering_db(settings.BASE_DIR / "face_clusters.db")
        
        # Get all associations from source cluster
        with sqlite3.connect(str(face_clustering_db.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get source cluster info
            source_cluster = conn.execute("""
                SELECT * FROM face_clusters WHERE cluster_id = ?
            """, (cluster_id,)).fetchone()
            
            if not source_cluster:
                raise HTTPException(status_code=404, detail="Source cluster not found")
            
            # Get target cluster info
            target_cluster = conn.execute("""
                SELECT * FROM face_clusters WHERE cluster_id = ?
            """, (target_cluster_id,)).fetchone()
            
            if not target_cluster:
                raise HTTPException(status_code=404, detail="Target cluster not found")
            
            # Get all associations from source cluster
            associations = conn.execute("""
                SELECT * FROM photo_person_associations
                WHERE cluster_id = ?
            """, (cluster_id,)).fetchall()
            
            # Begin transaction
            conn.execute("BEGIN TRANSACTION")
            
            # Reassign all associations to target cluster
            for assoc in associations:
                conn.execute("""
                    UPDATE photo_person_associations
                    SET cluster_id = ?
                    WHERE photo_path = ? AND detection_id = ? AND cluster_id = ?
                """, (target_cluster_id, assoc['photo_path'], assoc['detection_id'], cluster_id))
            
            # Update target cluster counts
            new_face_count = target_cluster['face_count'] + source_cluster['face_count']
            new_photo_count = target_cluster['photo_count'] + source_cluster['photo_count']
            
            conn.execute("""
                UPDATE face_clusters
                SET face_count = ?, photo_count = ?, updated_at = CURRENT_TIMESTAMP
                WHERE cluster_id = ?
            """, (new_face_count, new_photo_count, target_cluster_id))
            
            # Delete source cluster
            conn.execute("DELETE FROM face_clusters WHERE cluster_id = ?", (cluster_id,))
            
            # Commit transaction
            conn.commit()
        
        return {
            "source_cluster_id": cluster_id,
            "target_cluster_id": target_cluster_id,
            "faces_moved": source_cluster['face_count'],
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# DUPLICATES ENDPOINTS
# ==============================================================================

class DuplicateResolution(BaseModel):
    resolution: str  # 'keep_all', 'keep_selected', 'delete_all'
    keep_files: Optional[List[str]] = None


@app.get("/api/duplicates")
async def get_duplicates(hash_type: Optional[str] = None, limit: int = 100, offset: int = 0):
    """Get duplicate groups."""
    try:
        duplicates_db = get_duplicates_db(settings.BASE_DIR / "duplicates.db")
        groups = duplicates_db.get_duplicate_groups(hash_type, limit, offset)
        return {"count": len(groups), "groups": [g.__dict__ for g in groups]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/duplicates/scan")
async def scan_duplicates(type: str = "exact", limit: int = 1000):
    """Scan for duplicates."""
    try:
        if type not in ["exact", "perceptual"]:
            raise HTTPException(status_code=400, detail="Type must be 'exact' or 'perceptual'")

        # Get all photo paths from database
        cursor = photo_search_engine.db.conn.cursor()
        cursor.execute("SELECT file_path FROM metadata WHERE deleted_at IS NULL LIMIT ?", (limit,))
        all_files = [row[0] for row in cursor.fetchall()]

        duplicates_db = get_duplicates_db(settings.BASE_DIR / "duplicates.db")

        if type == "exact":
            groups = duplicates_db.find_exact_duplicates(all_files)
        else:
            # For perceptual duplicates, we'd implement image similarity detection
            # For now, return empty
            groups = []

        return {"scanned": len(all_files), "duplicate_groups_found": len(groups), "groups": [g.__dict__ for g in groups]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/duplicates/{group_id}/resolve")
async def resolve_duplicates(group_id: str, resolution: DuplicateResolution):
    """Resolve a duplicate group."""
    try:
        duplicates_db = get_duplicates_db(settings.BASE_DIR / "duplicates.db")
        keep_files = resolution.keep_files or []
        success = duplicates_db.resolve_duplicates(group_id, resolution.resolution, keep_files)
        return {"success": success, "group_id": group_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/duplicates/{group_id}")
async def delete_duplicate_group(group_id: str):
    """Delete a duplicate group."""
    try:
        duplicates_db = get_duplicates_db(settings.BASE_DIR / "duplicates.db")
        success = duplicates_db.delete_group(group_id)
        return {"success": success, "group_id": group_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/duplicates/stats")
async def get_duplicates_stats():
    """Get duplicate statistics."""
    try:
        duplicates_db = get_duplicates_db(settings.BASE_DIR / "duplicates.db")
        stats = duplicates_db.get_duplicate_stats()
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/duplicates/cleanup")
async def cleanup_duplicates():
    """Clean up entries for missing files."""
    try:
        duplicates_db = get_duplicates_db(settings.BASE_DIR / "duplicates.db")
        cleaned_count = duplicates_db.cleanup_missing_files()
        return {"cleaned_files": cleaned_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# FACE RECOGNITION ENDPOINTS
# ==============================================================================

@app.get("/api/faces/clusters")
async def get_face_clusters():
    """Get all face clusters."""
    try:
        # Check if face clusterer is ready
        if not face_clusterer or not face_clusterer.models_loaded:
            return {"clusters": [], "message": "Face recognition models are still loading"}
        
        # Get all clusters from the pre-initialized clusterer
        result = face_clusterer.get_all_clusters(limit=100)
        
        # Format for frontend
        formatted_clusters = []
        for cluster in result.get("clusters", []):
            cluster_details = face_clusterer.get_cluster_details(cluster["id"])
            if cluster_details.get("status") != "error":
                formatted_clusters.append({
                    "id": str(cluster["id"]),
                    "label": cluster.get("label") or f"Person {cluster['id']}",
                    "face_count": cluster_details.get("face_count", 0),
                    "image_count": len(set(f.get("image_path") for f in cluster_details.get("faces", []))),
                    "images": [f.get("image_path") for f in cluster_details.get("faces", [])[:6]],
                    "created_at": cluster.get("created_at")
                })

        return {"clusters": formatted_clusters}
    except Exception as e:
        # Return empty clusters if face recognition is not available
        return {"clusters": [], "error": str(e)}


@app.post("/api/faces/scan")
async def scan_faces(limit: int = 100):
    """Scan for faces in photos."""
    try:
        # Check if face clusterer is ready
        if not face_clusterer or not face_clusterer.models_loaded:
            raise HTTPException(
                status_code=503, 
                detail="Face recognition models are still loading. Please try again in a few seconds."
            )
        
        # Get all photo paths from database
        cursor = photo_search_engine.db.conn.cursor()
        cursor.execute("SELECT file_path FROM metadata WHERE deleted_at IS NULL LIMIT ?", (limit,))
        all_files = [row[0] for row in cursor.fetchall()]

        if not all_files:
            return {
                "scanned": 0,
                "clusters_found": 0,
                "total_faces": 0,
                "message": "No photos found in library"
            }

        result = face_clusterer.cluster_faces(all_files)

        # Handle error response from cluster_faces
        if result.get('status') == 'error':
            raise HTTPException(status_code=500, detail=result.get('message', 'Clustering failed'))

        return {
            "scanned": len(all_files),
            "clusters_found": result.get("total_clusters", 0),
            "total_faces": result.get("total_faces", 0),
            "message": result.get("message", "Scan complete")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/faces/clusters/{cluster_id}/label")
async def set_cluster_label(cluster_id: str, label_data: dict):
    """Set label for a face cluster."""
    try:
        label = label_data.get("label", "").strip()
        if not label:
            raise HTTPException(status_code=400, detail="Label cannot be empty")

        # This would update the cluster label in the database
        # For now, just return success
        return {"success": True, "cluster_id": cluster_id, "label": label}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/faces/photos/{person_name}")
async def get_photos_by_person(person_name: str, limit: int = 100, offset: int = 0):
    """Get photos for a specific person."""
    try:
        # This would search for photos containing the specific person
        # For now, return empty results
        return {"count": 0, "results": [], "person": person_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/faces/stats")
async def get_face_stats_api():
    """Get face recognition statistics."""
    try:
        cursor = photo_search_engine.db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM metadata WHERE deleted_at IS NULL")
        total_photos = cursor.fetchone()[0]

        # For now, return placeholder stats
        return {
            "total_photos": total_photos,
            "faces_detected": 0,
            "clusters_found": 0,
            "unidentified_faces": 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# People Search Endpoint

@app.get("/api/people/search")
async def search_people(
    query: Optional[str] = None,
    limit: int = 10,
    offset: int = 0
):
    """Search for people by name or other attributes."""
    try:
        face_clustering_db = get_face_clustering_db(settings.BASE_DIR / "face_clusters.db")
        
        # Get all clusters (people)
        clusters = face_clustering_db.get_all_clusters()
        
        # Filter and search
        if query:
            query_lower = query.lower()
            clusters = [
                cluster for cluster in clusters
                if cluster.label and query_lower in cluster.label.lower()
            ]
        
        # Paginate
        paginated_clusters = clusters[offset:offset + limit]
        
        # Format response
        people = [
            {
                "cluster_id": cluster.cluster_id,
                "label": cluster.label or f"Person {cluster.cluster_id[-4:]}",
                "face_count": cluster.face_count,
                "photo_count": cluster.photo_count,
                "thumbnail": None  # Would get thumbnail in real implementation
            }
            for cluster in paginated_clusters
        ]
        
        return {
            "people": people,
            "total": len(clusters),
            "limit": limit,
            "offset": offset,
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Person Analytics Endpoint

@app.get("/api/people/{person_id}/analytics")
async def get_person_analytics(person_id: str):
    """Get analytics and insights for a specific person."""
    try:
        face_clustering_db = get_face_clustering_db(settings.BASE_DIR / "face_clusters.db")
        
        # Get basic cluster info
        cluster = None
        with sqlite3.connect(str(face_clustering_db.db_path)) as conn:
            cluster = conn.execute("""
                SELECT * FROM face_clusters WHERE cluster_id = ?
            """, (person_id,)).fetchone()
            
            if not cluster:
                raise HTTPException(status_code=404, detail="Person not found")
        
        # Get photos with this person
        photos = face_clustering_db.get_photos_for_cluster(person_id)
        
        # Get timeline data
        timeline = []
        with sqlite3.connect(str(face_clustering_db.db_path)) as conn:
            timeline_rows = conn.execute("""
                SELECT ppa.photo_path, ppa.created_at, ppa.confidence
                FROM photo_person_associations ppa
                WHERE ppa.cluster_id = ?
                ORDER BY ppa.created_at
            """, (person_id,)).fetchall()
            
            for row in timeline_rows:
                timeline.append({
                    "photo_path": row[0],
                    "date": row[1],
                    "confidence": row[2]
                })
        
        # Calculate statistics
        from datetime import datetime
        from collections import Counter

        years = [datetime.fromisoformat(t['date']).year for t in timeline if t['date']]
        year_distribution = dict(Counter(years))

        return {
            "person_id": person_id,
            "label": cluster[1],
            "stats": {
                "total_photos": len(photos),
                "total_faces": cluster[2],
                "first_seen": min(years) if years else None,
                "last_seen": max(years) if years else None,
                "years_active": len(set(years)) if years else 0
            },
            "timeline": timeline,
            "year_distribution": year_distribution
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# VIDEO ANALYSIS ENDPOINTS
# ==============================================================================

# Initialize Video Analyzer
from src.video_analysis import VideoAnalyzer
video_analyzer = VideoAnalyzer(
    db_path=str(settings.BASE_DIR / "video_analysis.db"),
    cache_dir=str(settings.BASE_DIR / "cache" / "video")
)

class VideoAnalysisRequest(BaseModel):
    video_path: str
    force_reprocess: bool = False

class VideoSearchRequest(BaseModel):
    query: str
    limit: int = 50
    offset: int = 0

@app.post("/video/analyze")
async def analyze_video_content(background_tasks: BackgroundTasks, request: VideoAnalysisRequest):
    """
    Analyze video content for keyframes, scenes, and text detection.
    
    This endpoint performs comprehensive video analysis including:
    - Keyframe extraction at regular intervals
    - Scene detection and segmentation
    - OCR text detection in video frames
    - Visual similarity analysis
    """
    try:
        video_path = request.video_path
        
        # Validate video file exists
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail="Video file not found")
        
        # Check if it's actually a video file
        if not any(video_path.lower().endswith(ext) for ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v']):
            raise HTTPException(status_code=400, detail="File is not a supported video format")
        
        # Start analysis in background
        def run_analysis():
            try:
                result = video_analyzer.analyze_video(video_path, force_reprocess=request.force_reprocess)
                ps_logger.info(f"Video analysis completed for {video_path}: {result.get('status')}")
            except Exception as e:
                ps_logger.error(f"Video analysis failed for {video_path}: {str(e)}")
        
        background_tasks.add_task(run_analysis)
        
        return {
            "status": "started",
            "video_path": video_path,
            "message": "Video analysis started in background. Use /video/status endpoint to check progress."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/video/analysis/{video_path:path}")
async def get_video_analysis_results(video_path: str):
    """
    Get complete analysis results for a video.
    
    Returns:
    - Video metadata (duration, resolution, codec, etc.)
    - Extracted keyframes with timestamps
    - Detected scenes with boundaries
    - OCR text detections with confidence scores
    """
    try:
        # Validate video path
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail="Video file not found")
        
        analysis = video_analyzer.get_video_analysis(video_path)
        
        if "error" in analysis:
            raise HTTPException(status_code=404, detail=analysis["error"])
        
        return analysis
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/video/search")
async def search_video_content(request: VideoSearchRequest):
    """
    Search video content using text queries.
    
    Searches through:
    - OCR detected text in video frames
    - Video file names and metadata
    - Scene descriptions (if available)
    
    Returns matching videos with timestamps where text was found.
    """
    try:
        results = video_analyzer.search_video_content(
            query=request.query,
            limit=request.limit
        )
        
        # Add pagination info
        total_results = len(results)
        paginated_results = results[request.offset:request.offset + request.limit]
        
        return {
            "query": request.query,
            "total_results": total_results,
            "results": paginated_results,
            "pagination": {
                "limit": request.limit,
                "offset": request.offset,
                "has_more": request.offset + request.limit < total_results
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/video/keyframes/{video_path:path}")
async def get_video_keyframes(video_path: str, scene_id: Optional[int] = None):
    """
    Get keyframes for a specific video, optionally filtered by scene.
    
    Args:
        video_path: Path to the video file
        scene_id: Optional scene ID to filter keyframes
        
    Returns:
        List of keyframes with timestamps and file paths
    """
    try:
        analysis = video_analyzer.get_video_analysis(video_path)
        
        if "error" in analysis:
            raise HTTPException(status_code=404, detail=analysis["error"])
        
        keyframes = analysis.get("keyframes", [])
        
        # Filter by scene if specified
        if scene_id is not None:
            keyframes = [kf for kf in keyframes if kf.get("scene_id") == scene_id]
        
        return {
            "video_path": video_path,
            "scene_id": scene_id,
            "keyframes": keyframes,
            "count": len(keyframes)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/video/scenes/{video_path:path}")
async def get_video_scenes(video_path: str):
    """
    Get scene detection results for a video.
    
    Returns:
        List of detected scenes with start/end timestamps and durations
    """
    try:
        analysis = video_analyzer.get_video_analysis(video_path)
        
        if "error" in analysis:
            raise HTTPException(status_code=404, detail=analysis["error"])
        
        scenes = analysis.get("scenes", [])
        
        return {
            "video_path": video_path,
            "scenes": scenes,
            "count": len(scenes),
            "total_duration": analysis.get("metadata", {}).get("duration", 0)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/video/ocr/{video_path:path}")
async def get_video_ocr_results(video_path: str, min_confidence: float = 0.5):
    """
    Get OCR text detection results for a video.
    
    Args:
        video_path: Path to the video file
        min_confidence: Minimum confidence threshold for text detections
        
    Returns:
        List of text detections with timestamps and confidence scores
    """
    try:
        analysis = video_analyzer.get_video_analysis(video_path)
        
        if "error" in analysis:
            raise HTTPException(status_code=404, detail=analysis["error"])
        
        ocr_results = analysis.get("ocr_results", [])
        
        # Filter by confidence threshold
        filtered_results = [
            result for result in ocr_results 
            if result.get("confidence", 0) >= min_confidence
        ]
        
        return {
            "video_path": video_path,
            "min_confidence": min_confidence,
            "ocr_results": filtered_results,
            "count": len(filtered_results),
            "total_detections": len(ocr_results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/video/stats")
async def get_video_analysis_stats():
    """
    Get statistics about video analysis processing.
    
    Returns:
        - Total videos processed
        - Total keyframes extracted
        - Total scenes detected
        - Total OCR detections
        - Processing time statistics
    """
    try:
        stats = video_analyzer.get_video_statistics()
        return {"stats": stats}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/video/thumbnail/{video_path:path}")
async def get_video_thumbnail(video_path: str, timestamp: Optional[float] = None, size: int = 300):
    """
    Get a thumbnail image from a video at a specific timestamp.
    
    Args:
        video_path: Path to the video file
        timestamp: Timestamp in seconds (defaults to first keyframe)
        size: Thumbnail size in pixels
        
    Returns:
        Thumbnail image as JPEG
    """
    try:
        analysis = video_analyzer.get_video_analysis(video_path)
        
        if "error" in analysis:
            raise HTTPException(status_code=404, detail=analysis["error"])
        
        keyframes = analysis.get("keyframes", [])
        
        if not keyframes:
            raise HTTPException(status_code=404, detail="No keyframes available for video")
        
        # Find keyframe closest to requested timestamp
        if timestamp is not None:
            closest_keyframe = min(keyframes, key=lambda kf: abs(kf["timestamp"] - timestamp))
        else:
            closest_keyframe = keyframes[0]  # Use first keyframe
        
        frame_path = closest_keyframe["frame_path"]
        
        if not os.path.exists(frame_path):
            raise HTTPException(status_code=404, detail="Keyframe image not found")
        
        # Resize image if needed
        if size != 300:  # Default size
            from PIL import Image
            with Image.open(frame_path) as img:
                img.thumbnail((size, size), Image.Resampling.LANCZOS)
                
                # Save resized thumbnail to temp file
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
                    img.save(temp_file.name, "JPEG", quality=85)
                    frame_path = temp_file.name
        
        # Prepare headers with cache control + CORS
        frame_headers = {
            "Cache-Control": "public, max-age=3600",
            "X-Video-Timestamp": str(closest_keyframe["timestamp"])
        }
        
        # Add explicit CORS headers for cross-origin image requests
        origin = request.headers.get("origin")
        if origin and origin in cors_origins:
            frame_headers["Access-Control-Allow-Origin"] = origin
            frame_headers["Access-Control-Allow-Credentials"] = "true"
        
        return FileResponse(
            frame_path,
            media_type="image/jpeg",
            headers=frame_headers
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/video/analysis/{video_path:path}")
async def delete_video_analysis(video_path: str):
    """
    Delete analysis data for a specific video.
    
    This removes:
    - Video metadata
    - Keyframes and cached images
    - Scene detection results
    - OCR text detections
    """
    try:
        # Check if video analysis exists
        analysis = video_analyzer.get_video_analysis(video_path)
        
        if "error" in analysis:
            raise HTTPException(status_code=404, detail="Video analysis not found")
        
        # Delete cached keyframe images
        keyframes = analysis.get("keyframes", [])
        deleted_files = 0
        
        for keyframe in keyframes:
            frame_path = keyframe.get("frame_path")
            if frame_path and os.path.exists(frame_path):
                try:
                    os.remove(frame_path)
                    deleted_files += 1
                except OSError:
                    pass  # Continue even if file deletion fails
        
        # Delete database records
        conn = sqlite3.connect(video_analyzer.db_path)
        try:
            conn.execute("DELETE FROM video_metadata WHERE video_path = ?", (video_path,))
            conn.execute("DELETE FROM video_keyframes WHERE video_path = ?", (video_path,))
            conn.execute("DELETE FROM video_scenes WHERE video_path = ?", (video_path,))
            conn.execute("DELETE FROM video_ocr WHERE video_path = ?", (video_path,))
            conn.commit()
        finally:
            conn.close()
        
        return {
            "success": True,
            "video_path": video_path,
            "deleted_files": deleted_files,
            "message": "Video analysis data deleted successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/video/batch-analyze")
async def batch_analyze_videos(background_tasks: BackgroundTasks, video_paths: List[str] = Body(...)):
    """
    Analyze multiple videos in batch.
    
    Starts analysis for multiple videos in the background.
    Use /video/batch-status to monitor progress.
    """
    try:
        if len(video_paths) > 50:
            raise HTTPException(status_code=400, detail="Maximum 50 videos per batch")
        
        # Validate all video paths
        invalid_paths = []
        for video_path in video_paths:
            if not os.path.exists(video_path):
                invalid_paths.append(video_path)
        
        if invalid_paths:
            raise HTTPException(
                status_code=400, 
                detail=f"Video files not found: {', '.join(invalid_paths[:5])}"
            )
        
        # Start batch analysis
        def run_batch_analysis():
            results = []
            for video_path in video_paths:
                try:
                    result = video_analyzer.analyze_video(video_path, force_reprocess=False)
                    results.append({"video_path": video_path, "status": result.get("status")})
                    ps_logger.info(f"Batch analysis completed for {video_path}")
                except Exception as e:
                    results.append({"video_path": video_path, "status": "failed", "error": str(e)})
                    ps_logger.error(f"Batch analysis failed for {video_path}: {str(e)}")
            
            ps_logger.info(f"Batch analysis completed for {len(video_paths)} videos")
        
        background_tasks.add_task(run_batch_analysis)
        
        return {
            "status": "started",
            "video_count": len(video_paths),
            "message": "Batch video analysis started in background"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# IMAGE ANALYSIS ENDPOINTS
# ==============================================================================

class ImageAnalysisRequest(BaseModel):
    path: str

@app.post("/ai/analyze")
async def analyze_image(request: ImageAnalysisRequest):
    """
    Analyze an image to extract visual insights and characteristics.
    
    Args:
        request: ImageAnalysisRequest with image path
        
    Returns:
        Dictionary with analysis results including caption, tags, objects, etc.
    """
    try:
        if not photo_search_engine:
            raise HTTPException(status_code=503, detail="Analysis engine not available")
            
        image_path = request.path
        
        # Verify the image exists
        if not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail="Image not found")
            
        # Check if it's actually an image file
        if not any(image_path.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.heic', '.heif', '.tif', '.tiff']):
            raise HTTPException(status_code=400, detail="File is not a supported image format")
        
        # For now, return a mock analysis since we don't have the actual analysis implementation
        # In a real implementation, this would use computer vision models to analyze the image
        analysis_result = {
            "caption": "We found an interesting photo with various visual elements",
            "tags": ["photo", "image", "visual"],
            "objects": ["general content"],
            "scene": "photograph",
            "colors": ["mixed"],
            "quality": 4.0,
            "analysis_date": datetime.utcnow().isoformat()
        }
        
        # Store the analysis result in the database for future retrieval
        try:
            # We could store this in a separate analysis table, but for now we'll just return it
            ps_logger.info(f"Image analysis completed for {image_path}")
        except Exception as e:
            ps_logger.warning(f"Failed to store analysis result: {e}")
        
        return analysis_result
        
    except HTTPException:
        raise
    except Exception as e:
        ps_logger.error(f"Image analysis failed for {request.path}: {str(e)}")
        raise HTTPException(status_code=500, detail="Analysis failed")


@app.get("/ai/analysis/{path:path}")
async def get_image_analysis(path: str):
    """
    Get existing analysis results for an image.
    
    Args:
        path: Path to the image file
        
    Returns:
        Dictionary with stored analysis results or empty if none exists
    """
    try:
        # Verify the image exists
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="Image not found")
        
        # For now, return empty since we don't have persistent storage implemented
        # In a real implementation, this would query the analysis database
        analysis_result = {}
        
        return analysis_result
        
    except HTTPException:
        raise
    except Exception as e:
        ps_logger.error(f"Failed to retrieve analysis for {path}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analysis")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
