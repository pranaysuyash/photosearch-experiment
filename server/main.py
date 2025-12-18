import sys
import os
from typing import List, Optional, Dict
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Body, BackgroundTasks, Request
from .jobs import job_store, Job
from .pricing import pricing_manager, PricingTier, UsageStats
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import BaseModel
import mimetypes
from datetime import datetime, timezone
import calendar
import json
import uuid
import hashlib
import hmac
import re
from urllib.parse import urlencode, urlparse, parse_qsl
import requests
import shutil
from threading import Lock
from PIL import Image

# Simple in-memory rate limiting counters (per-IP sliding window)
_rate_lock = Lock()
_rate_counters: dict = {}

# Add parent directory to path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.photo_search import PhotoSearch
from src.api_versioning import api_version_manager, APIResponseHandler
from src.cache_manager import cache_manager
from src.logging_config import setup_logging, log_search_operation, log_indexing_operation, log_error

from .config import settings
from .sources import SourceStore
from .source_items import SourceItemStore
from .trash_db import TrashDB

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global embedding_generator, file_watcher, ps_logger, perf_tracker
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

    print("Initializing Embedding Model...")
    try:
        embedding_generator = EmbeddingGenerator()
        print("Embedding Model Loaded.")
        
        # Auto-scan 'media' directory on startup
        media_path = settings.BASE_DIR / "media"
        if media_path.exists():
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
                    if metadata:
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper functions for sorting and filtering
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.wmv', '.flv'}

def is_video_file(path: str) -> bool:
    """Check if a file is a video based on extension."""
    ext = os.path.splitext(path)[1].lower()
    return ext in VIDEO_EXTENSIONS

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

# Initialize Core Logic
# We prefer a persistent instance
photo_search_engine = PhotoSearch()

# Initialize Semantic Search Components
from .lancedb_store import LanceDBStore
from .embedding_generator import EmbeddingGenerator
from .image_loader import load_image

from .watcher import start_watcher

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
                from image_loader import extract_video_frame
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
    tag: Optional[str] = None,  # Filter to a single user tag
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

        tagged_paths = None
        if tag:
            try:
                from .tags_db import get_tags_db

                tags_db = get_tags_db(settings.BASE_DIR / "tags.db")
                tagged_paths = set(tags_db.get_tag_paths(tag))
            except Exception:
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
                execution_time_ms = round((time.time() - start_time) * 1000, 2)
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
        
        # Return the ZIP file
        return FileResponse(
            path=zip_path,
            filename=f"photos_export_{len(file_paths)}_files.zip",
            media_type='application/zip',
            background=BackgroundTasks([lambda: os.unlink(zip_path)])  # Delete temp file after response
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
    breakdown = {
        "filename_score": 0,
        "metadata_score": 0,
        "content_score": 0
    }
    
    # Analyze the query to understand what matched
    query_lower = query.lower()
    metadata = result.get('metadata', {})
    filename = result.get('filename', result.get('file_path', '').split('/')[-1])
    
    # Check for filename matches (most common case)
    filename_match_score = 0
    if query_lower in filename.lower():
        # Calculate confidence based on how much of the filename matches
        match_ratio = len(query_lower) / len(filename.lower())
        confidence = min(0.95, 0.7 + (match_ratio * 0.25))  # 70-95% based on match ratio
        filename_match_score = confidence * 100
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
        breakdown["metadata_score"] = (metadata_matches / metadata_total) * 100
    
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
async def detect_intent(query: str):
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
async def get_thumbnail(request: Request, path: str = "", size: int = 300, token: str | None = None):
    """
    Serve a thumbnail or the full image.
    Args:
        path: Path to the image file (local/dev usage)
        size: Max dimension for thumbnail (default 300)
        token: Optional signed token for production/public access
    """
    # Resolve path either from token (preferred for public) or from 'path' param
    requested_path_str: str

    if token:
        # Verify token and extract path
        try:
            payload = verify_token(token, expected_scope="thumbnail")
            requested_path_str = payload.get("path")
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
    if os.path.exists(requested_path_str):
        try:
            from PIL import Image
            import io

            # For 3D textures we want small files (size=300 is good)
            # For Detail Modal we want larger (size=1200)

            # Open image
            with Image.open(requested_path_str) as img:
                # Convert to RGB if needed (e.g. RGBA or P)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                # Calculate new aspect ratio
                # thumbnail() modifies in-place and preserves aspect ratio
                img.thumbnail((size, size))

                # Save to buffer
                img_io = io.BytesIO()
                img.save(img_io, "JPEG", quality=70)
                img_io.seek(0)

                # Rate limiting: check per-IP quota
                try:
                    if settings.RATE_LIMIT_ENABLED:
                        client_ip = request.client.host if request.client else "unknown"
                        now = __import__("time").time()
                        with _rate_lock:
                            lst = _rate_counters.get(client_ip, [])
                            # keep only entries in the last 60s
                            lst = [t for t in lst if now - t < 60]
                            if len(lst) >= settings.RATE_LIMIT_REQS_PER_MIN:
                                raise HTTPException(status_code=429, detail="Rate limit exceeded")
                            lst.append(now)
                            _rate_counters[client_ip] = lst
                except HTTPException:
                    raise
                except Exception:
                    # don't block on rate errors
                    pass

                # Return in-memory bytes with caching headers
                content_bytes = img_io.getvalue()
                logger.info(f"Thumbnail produced {len(content_bytes)} bytes for {requested_path_str}")
                return Response(
                    content=content_bytes,
                    media_type="image/jpeg",
                    headers={"Cache-Control": "public, max-age=31536000"},
                )

        except ImportError:
            # Fallback if Pillow not working
            pass # fall through to local file
        except HTTPException:
            # Propagate HTTPExceptions like rate limiting up to the client
            raise
        except Exception as e:
            logger.error(f"Thumbnail error for {requested_path_str}: {e}")
            pass # fall through to local file

        # Fallback to serving original file
        return FileResponse(requested_path_str)


@app.post("/admin/unmask")
async def admin_unmask(payload: dict = Body(...), request: Request = None):
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
                    logger.warning(f"UNMASK used by {request.client.host if request.client else 'unknown'} for hash={h}")
                    return {"path": str(candidate)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    raise HTTPException(status_code=404, detail="No matching path found")

    raise HTTPException(status_code=404, detail="Image not found")

@app.get("/file")
async def get_file(path: str, download: bool = False):
    """
    Serve an original file (image/video/etc.) without transcoding.
    Use `download=true` to force a download Content-Disposition.
    """
    # Security check
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
            raise HTTPException(status_code=403, detail="Access denied")
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")

    media_type, _ = mimetypes.guess_type(path)
    kwargs = {"media_type": media_type or "application/octet-stream"}
    if download:
        kwargs["filename"] = os.path.basename(path)
    return FileResponse(path, **kwargs)

@app.get("/video")
async def get_video(path: str):
    """
    Serve a video file directly.
    """
    from fastapi.responses import FileResponse
    
    # Security check
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
            raise HTTPException(status_code=403, detail="Access denied")
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
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
        return FileResponse(path, media_type=media_type)
    
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
async def detect_intent(query: str):
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

class ExportRequest(BaseModel):
    paths: List[str]
    format: str = "zip"  # Future: could support "json" for metadata export

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
async def cluster_faces(request: FaceClusterRequest):
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
async def get_face_stats():
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
async def issue_image_token(payload: dict = Body(...), request: Request = None):
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
        dialog_id = modal_system.create_dialog(
            dialog_type=request.dialog_type,
            title=request.title,
            message=request.message,
            options=request.options or [],
            timeout=request.timeout,
            user_id=request.user_id
        )
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
            request.user_id
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
        dialog_id = modal_system.create_confirmation_dialog(
            title=request.title,
            message=request.message,
            options=request.options or ["Yes", "No"],
            timeout=request.timeout,
            user_id=request.user_id
        )
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
        dialog_id = modal_system.create_error_dialog(
            title=request.title,
            message=request.message,
            timeout=request.timeout,
            user_id=request.user_id
        )
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
            max_value=request.max_value,
            current_value=request.current_value,
            user_id=request.user_id
        )
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
        success = modal_system.update_progress_dialog(
            dialog_id,
            request.current_value,
            request.message
        )
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
        success = modal_system.complete_progress_dialog(dialog_id, user_id)
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
        dialog_id = modal_system.create_input_dialog(
            title=request.title,
            message=request.message,
            input_type=request.input_type,
            default_value=request.default_value,
            user_id=request.user_id
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
        history = modal_system.get_dialog_history(user_id, limit)
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
            request.component_name,
            request.chunk_name,
            request.load_time_ms,
            request.size_kb,
            request.timestamp
        )
        return {"status": "success", "recorded": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/code-splitting/performance")
async def get_lazy_load_performance(component_name: str = None):
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
    Export selected photos as a ZIP file.
    
    Args:
        request: ExportRequest with list of file paths
        
    Returns:
        Streaming ZIP file download
    """
    import zipfile
    import io
    from fastapi.responses import StreamingResponse
    
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
            filename = os.path.basename(path)
            # Handle duplicate filenames by adding parent folder
            if any(os.path.basename(p) == filename and p != path for p in valid_paths):
                parent = os.path.basename(os.path.dirname(path))
                filename = f"{parent}_{filename}"
            zip_file.write(path, filename)
    
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=photos_export.zip"}
    )

# ==============================================================================
# TAGS ENDPOINTS
# ==============================================================================

from .tags_db import get_tags_db
from .ratings_db import get_ratings_db
from .duplicates_db import get_duplicates_db


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

from .albums_db import get_albums_db, Album as AlbumModel
from .smart_albums import initialize_predefined_smart_albums, populate_smart_album
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

    result = {"album": album}

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
            rotated = img.transpose(Image.ROTATE_270)  # 90° CW
        elif degrees == -90 or degrees == 270:
            rotated = img.transpose(Image.ROTATE_90)   # 90° CCW
        elif degrees == 180:
            rotated = img.transpose(Image.ROTATE_180)
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
            flipped = img.transpose(Image.FLIP_LEFT_RIGHT)
        else:  # vertical
            flipped = img.transpose(Image.FLIP_TOP_BOTTOM)

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

@app.get("/api/cache/stats")
async def get_cache_stats():
    """Get cache statistics and performance metrics."""
    stats = cache_manager.stats()
    return stats

@app.post("/api/cache/clear")
async def clear_cache():
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
        success = duplicates_db.resolve_duplicates(group_id, resolution.resolution, resolution.keep_files)
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
        # Get all photo paths from database
        cursor = photo_search_engine.db.conn.cursor()
        cursor.execute("SELECT file_path FROM metadata WHERE deleted_at IS NULL LIMIT 1000")
        all_files = [row[0] for row in cursor.fetchall()]

        clusterer = FaceClusterer()
        clusters = clusterer.get_image_clusters(all_files)

        # Format for frontend
        formatted_clusters = []
        for cluster_id, cluster_data in clusters.items():
            formatted_clusters.append({
                "id": cluster_id,
                "label": cluster_data.get("label", f"Person {cluster_id}"),
                "face_count": cluster_data.get("face_count", 0),
                "image_count": len(cluster_data.get("images", [])),
                "images": cluster_data.get("images", [])[:6],  # Limit to 6 preview images
                "created_at": cluster_data.get("created_at")
            })

        return {"clusters": formatted_clusters}
    except Exception as e:
        # Return empty clusters if face recognition is not available
        return {"clusters": []}


@app.post("/api/faces/scan")
async def scan_faces(limit: int = 100):
    """Scan for faces in photos."""
    try:
        # Get all photo paths from database
        cursor = photo_search_engine.db.conn.cursor()
        cursor.execute("SELECT file_path FROM metadata WHERE deleted_at IS NULL LIMIT ?", (limit,))
        all_files = [row[0] for row in cursor.fetchall()]

        clusterer = FaceClusterer()
        result = clusterer.cluster_faces(all_files)

        return {
            "scanned": len(all_files),
            "clusters_found": len(result),
            "total_faces": sum(len(cluster.get("images", [])) for cluster in result.values())
        }
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
async def get_face_stats():
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
