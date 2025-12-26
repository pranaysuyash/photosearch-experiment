import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse

import requests  # type: ignore
from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException
from fastapi.responses import HTMLResponse

from server.config import settings
from server.models.schemas.sources import (
    GoogleDriveSourceCreate,
    LocalFolderSourceCreate,
    S3SourceCreate,
    SourceOut,
)
from server.api.deps import get_state
from server.core.state import AppState


router = APIRouter()


def _source_to_out(state: AppState, source_id: str) -> SourceOut:
    s = state.source_store.get_source(source_id, redact=True)
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


@router.get("/sources")
async def list_sources(state: AppState = Depends(get_state)):
    sources = state.source_store.list_sources(redact=True)
    return {
        "sources": [
            SourceOut(
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
            for s in sources
        ]
    }


@router.delete("/sources/{source_id}")
async def delete_source(source_id: str, state: AppState = Depends(get_state)):
    try:
        state.source_store.get_source(source_id, redact=False)
    except KeyError:
        raise HTTPException(status_code=404, detail="Source not found")
    state.source_store.delete_source(source_id)
    return {"ok": True}


@router.post("/sources/{source_id}/rescan")
async def rescan_source(
    background_tasks: BackgroundTasks,
    source_id: str,
    payload: dict = Body(default={}),
    state: AppState = Depends(get_state),
):
    try:
        src = state.source_store.get_source(source_id, redact=False)
    except KeyError:
        raise HTTPException(status_code=404, detail="Source not found")
    if src.type != "local_folder":
        raise HTTPException(
            status_code=400,
            detail="Rescan is only supported for local_folder sources right now",
        )
    path = (src.config or {}).get("path")
    if not isinstance(path, str) or not path:
        raise HTTPException(status_code=400, detail="Invalid source path")
    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail="Directory does not exist")
    force = bool(payload.get("force", False))

    job_id = state.job_store.create_job(type="scan")

    def run_scan(job_id: str, path: str, force: bool, state: AppState):
        try:
            scan_results = state.photo_search_engine.scan(
                path,
                force=force,
                job_id=job_id,
            )
            all_files = scan_results.get("all_files", [])
            if all_files:
                state.process_semantic_indexing(all_files)
            state.job_store.update_job(
                job_id,
                status="completed",
                message="Scan and indexing finished.",
            )
            state.source_store.update_source(
                source_id,
                last_sync_at=datetime.utcnow().isoformat() + "Z",
                last_error=None,
                status="connected",
            )
        except Exception as e:
            state.job_store.update_job(job_id, status="failed", message=str(e))
            state.source_store.update_source(
                source_id,
                status="error",
                last_error=str(e),
            )

    background_tasks.add_task(run_scan, job_id, path, force, state)
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
        [f"{requests.utils.quote(str(k), safe='~')}={requests.utils.quote(str(v), safe='~')}" for k, v in q]
    )

    canonical_headers = f"host:{host}\n" + f"x-amz-date:{amz_date}\n"
    signed_headers = "host;x-amz-date"
    payload_hash = hashlib.sha256(b"").hexdigest()
    canonical_request = "\n".join(
        [
            method,
            u.path or "/",
            canonical_qs,
            canonical_headers,
            signed_headers,
            payload_hash,
        ]
    )

    algorithm = "AWS4-HMAC-SHA256"
    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    string_to_sign = "\n".join(
        [
            algorithm,
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )

    def _sign(key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    k_date = _sign(("AWS4" + secret_access_key).encode("utf-8"), date_stamp)
    k_region = _sign(k_date, region)
    k_service = _sign(k_region, service)
    k_signing = _sign(k_service, "aws4_request")
    signature = hmac.new(
        k_signing,
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    authorization_header = (
        f"{algorithm} Credential={access_key_id}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    headers["Authorization"] = authorization_header
    headers["x-amz-date"] = amz_date
    headers["host"] = host
    return headers


def _s3_urls(
    endpoint_url: str,
    bucket: str,
    key: str = "",
    query: Optional[Dict[str, str]] = None,
) -> str:
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
                out.append(
                    {
                        "key": key,
                        "etag": etag or None,
                        "last_modified": last_modified or None,
                        "size": size_int,
                    }
                )

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
    url = _s3_urls(
        endpoint_url,
        bucket,
        "",
        query={
            "list-type": "2",
            "max-keys": "1",
            **({"prefix": prefix} if prefix else {}),
        },
    )
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


def _sync_s3_source(state: AppState, source_id: str, job_id: str) -> None:
    state.job_store.update_job(
        job_id,
        status="processing",
        message="Enumerating S3…",
        progress=5,
    )
    src = state.source_store.get_source(source_id, redact=False)
    cfg = src.config or {}
    items = _s3_list_objects(cfg)
    seen_marker = datetime.now(timezone.utc).isoformat()

    state.job_store.update_job(
        job_id,
        message=f"Found {len(items)} objects. Downloading…",
        progress=20,
    )
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
            prev = state.source_item_store.get(source_id, remote_id)
        except Exception:
            prev = None

        state.source_item_store.upsert_seen(
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
            state.source_item_store.set_local_path(source_id, remote_id, str(dest))
            downloaded += 1

        if idx % 50 == 0:
            pct = 20 + int((idx / max(1, len(items))) * 55)
            state.job_store.update_job(
                job_id,
                message=f"Downloading S3 objects… ({idx}/{len(items)})",
                progress=pct,
            )

    missing = state.source_item_store.mark_missing_as_deleted(source_id, seen_marker)
    for m in missing:
        if m.local_path:
            try:
                lp = Path(m.local_path)
                if lp.exists():
                    lp.unlink()
                try:
                    state.photo_search_engine.db.mark_as_deleted(
                        m.local_path,
                        reason="source_deleted",
                    )
                except Exception:
                    pass
            except Exception:
                pass

    state.job_store.update_job(
        job_id,
        message="Indexing downloaded files…",
        progress=80,
    )
    results = state.photo_search_engine.scan(str(root), force=False)
    all_files = results.get("all_files", []) if isinstance(results, dict) else []
    if all_files:
        state.job_store.update_job(
            job_id,
            message="Semantic indexing…",
            progress=92,
        )
        state.process_semantic_indexing(all_files)

    state.source_store.update_source(
        source_id,
        status="connected",
        last_error=None,
        last_sync_at=datetime.utcnow().isoformat() + "Z",
    )
    state.job_store.update_job(
        job_id,
        status="completed",
        progress=100,
        message=f"S3 sync complete ({downloaded} downloaded, {len(missing)} removed).",
        result={"downloaded": downloaded, "removed": len(missing)},
    )


@router.post("/sources/local-folder")
async def add_local_folder_source(
    background_tasks: BackgroundTasks,
    payload: LocalFolderSourceCreate,
    state: AppState = Depends(get_state),
):
    path = payload.path
    if not path:
        raise HTTPException(status_code=400, detail="Path is required")
    if not os.path.exists(path):
        raise HTTPException(status_code=400, detail="Directory does not exist")
    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail="Path must be a directory")

    name = payload.name or os.path.basename(path.rstrip("/")) or "Local Folder"
    src = state.source_store.create_source(
        "local_folder",
        name=name,
        config={"path": path},
        status="connected",
    )

    job_id = state.job_store.create_job(type="scan")
    force = bool(payload.force)

    def run_scan(job_id: str, path: str, force: bool, state: AppState):
        try:
            scan_results = state.photo_search_engine.scan(
                path,
                force=force,
                job_id=job_id,
            )
            all_files = scan_results.get("all_files", [])
            if all_files:
                state.process_semantic_indexing(all_files)
            state.job_store.update_job(
                job_id,
                status="completed",
                message="Scan and indexing finished.",
            )
            state.source_store.update_source(
                src.id,
                last_sync_at=datetime.utcnow().isoformat() + "Z",
                last_error=None,
            )
        except Exception as e:
            state.job_store.update_job(job_id, status="failed", message=str(e))
            state.source_store.update_source(
                src.id,
                status="error",
                last_error=str(e),
            )

    background_tasks.add_task(run_scan, job_id, path, force, state)
    return {"source": _source_to_out(state, src.id), "job_id": job_id}


@router.post("/sources/s3")
async def add_s3_source(
    background_tasks: BackgroundTasks, payload: S3SourceCreate, state: AppState = Depends(get_state)
):
    cfg = payload.model_dump()
    # Store secrets server-side; return only redacted config.
    src = state.source_store.create_source(
        "s3",
        name=payload.name,
        config=cfg,
        status="pending",
    )
    try:
        _test_s3_connection(cfg)
        state.source_store.update_source(src.id, status="connected", last_error=None)
        job_id = state.job_store.create_job(type="source_sync")

        def run_sync(state: AppState = Depends(get_state)):
            try:
                _sync_s3_source(state, src.id, job_id)
            except Exception as e:
                state.job_store.update_job(job_id, status="failed", message=str(e))
                state.source_store.update_source(
                    src.id,
                    status="error",
                    last_error=str(e),
                )

        background_tasks.add_task(run_sync)
    except Exception as e:
        state.source_store.update_source(src.id, status="error", last_error=str(e))
        return {"source": _source_to_out(state, src.id)}
    return {"source": _source_to_out(state, src.id), "job_id": job_id}


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
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
        ".heic",
        ".heif",
        ".tif",
        ".tiff",
        ".mp4",
        ".mov",
        ".m4v",
        ".mkv",
        ".webm",
        ".avi",
        ".pdf",
        ".svg",
        ".mp3",
        ".wav",
        ".m4a",
        ".aac",
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


def _refresh_google_access_token(state: AppState, source_id: str) -> Dict[str, object]:
    src = state.source_store.get_source(source_id, redact=False)
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
    state.source_store.update_source(
        source_id,
        config_patch=patch,
        status="connected",
        last_error=None,
    )
    return patch


def _get_google_access_token(state: AppState, source_id: str) -> str:
    src = state.source_store.get_source(source_id, redact=False)
    cfg = src.config or {}
    access_token = cfg.get("access_token")
    expires_at = cfg.get("expires_at")
    if isinstance(access_token, str) and access_token:
        if isinstance(expires_at, (int, float)) and (datetime.utcnow().timestamp() + 60) < float(expires_at):
            return access_token
        # Token nearing expiry; refresh.
        patch = _refresh_google_access_token(state, source_id)
        return str(patch.get("access_token", ""))
    patch = _refresh_google_access_token(state, source_id)
    return str(patch.get("access_token", ""))


def _sync_google_drive_source(state: AppState, source_id: str, job_id: str) -> None:
    state.job_store.update_job(
        job_id,
        status="processing",
        message="Enumerating Google Drive…",
        progress=5,
    )
    token = _get_google_access_token(state, source_id)
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
        resp = requests.get(
            "https://www.googleapis.com/drive/v3/files",
            headers=headers,
            params=params,
            timeout=30,
        )
        if resp.status_code == 401:
            # Refresh and retry once.
            token = _get_google_access_token(state, source_id)
            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get(
                "https://www.googleapis.com/drive/v3/files",
                headers=headers,
                params=params,
                timeout=30,
            )
        if resp.status_code != 200:
            raise RuntimeError(f"Drive list failed ({resp.status_code}): {resp.text[:200]}")
        data = resp.json()
        batch = data.get("files") or []
        files.extend(batch)
        page_token = data.get("nextPageToken")
        if not page_token:
            break

    state.job_store.update_job(
        job_id,
        message=f"Found {len(files)} Drive items. Downloading…",
        progress=20,
    )
    root = _media_source_root(source_id) / "drive"
    root.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    for idx, f in enumerate(files):
        file_id = str(f.get("id", ""))
        name = str(f.get("name", "")) or file_id
        mime = str(f.get("mimeType", "")) or None
        if (
            name
            and not _is_media_name(name)
            and mime
            and not (
                mime.startswith("image/")
                or mime.startswith("video/")
                or mime.startswith("audio/")
                or mime == "application/pdf"
            )
        ):
            continue

        md5 = f.get("md5Checksum")
        modified = f.get("modifiedTime")
        size = f.get("size")
        size_int = int(size) if isinstance(size, (int, float, str)) and str(size).isdigit() else None

        try:
            prev = state.source_item_store.get(source_id, file_id)
        except Exception:
            prev = None

        state.source_item_store.upsert_seen(
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
            with requests.get(
                url,
                headers=headers,
                params={"alt": "media"},
                stream=True,
                timeout=120,
            ) as r:
                if r.status_code == 401:
                    token = _get_google_access_token(state, source_id)
                    headers = {"Authorization": f"Bearer {token}"}
                    r = requests.get(
                        url,
                        headers=headers,
                        params={"alt": "media"},
                        stream=True,
                        timeout=120,
                    )
                if r.status_code != 200:
                    raise RuntimeError(f"Drive download failed ({r.status_code}): {r.text[:200]}")
                local_path.parent.mkdir(parents=True, exist_ok=True)
                tmp = local_path.with_suffix(local_path.suffix + ".part")
                with open(tmp, "wb") as out:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            out.write(chunk)
                tmp.replace(local_path)
            state.source_item_store.set_local_path(
                source_id,
                file_id,
                str(local_path),
            )
            downloaded += 1

        if idx % 25 == 0:
            pct = 20 + int((idx / max(1, len(files))) * 55)
            state.job_store.update_job(
                job_id,
                message=f"Downloading Drive items… ({idx}/{len(files)})",
                progress=pct,
            )

    missing = state.source_item_store.mark_missing_as_deleted(source_id, seen_marker)
    for m in missing:
        if m.local_path:
            try:
                lp = Path(m.local_path)
                if lp.exists():
                    lp.unlink()
                try:
                    state.photo_search_engine.db.mark_as_deleted(
                        m.local_path,
                        reason="source_deleted",
                    )
                except Exception:
                    pass
            except Exception:
                pass

    state.job_store.update_job(
        job_id,
        message="Indexing downloaded files…",
        progress=80,
    )
    results = state.photo_search_engine.scan(str(root), force=False)
    all_files = results.get("all_files", []) if isinstance(results, dict) else []
    if all_files:
        state.job_store.update_job(
            job_id,
            message="Semantic indexing…",
            progress=92,
        )
        state.process_semantic_indexing(all_files)

    state.source_store.update_source(
        source_id,
        status="connected",
        last_error=None,
        last_sync_at=datetime.utcnow().isoformat() + "Z",
    )
    state.job_store.update_job(
        job_id,
        status="completed",
        progress=100,
        message=(f"Drive sync complete ({downloaded} downloaded, {len(missing)} removed)."),
        result={"downloaded": downloaded, "removed": len(missing)},
    )


@router.post("/sources/google-drive")
async def add_google_drive_source(payload: GoogleDriveSourceCreate, state: AppState = Depends(get_state)):
    cfg = {"client_id": payload.client_id, "client_secret": payload.client_secret}
    src = state.source_store.create_source(
        "google_drive",
        name=payload.name,
        config=cfg,
        status="auth_required",
    )
    state_nonce = str(uuid.uuid4())
    state.source_store.update_source(src.id, config_patch={"state_nonce": state_nonce})

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
    return {"source": _source_to_out(state, src.id), "auth_url": auth_url}


@router.get("/oauth/google/callback")
async def google_oauth_callback(
    background_tasks: BackgroundTasks,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
):
    if error:
        return {
            "ok": False,
            "error": error,
        }
    if not code or not state or ":" not in state:
        raise HTTPException(status_code=400, detail="Missing code/state")
    source_id, nonce = state.split(":", 1)
    try:
        src = state.source_store.get_source(source_id, redact=False)
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
        state.source_store.update_source(
            source_id,
            status="error",
            last_error=f"token exchange failed: {token_resp.text[:200]}",
        )
        raise HTTPException(status_code=400, detail="Token exchange failed")
    tok = token_resp.json()
    access_token = tok.get("access_token")
    refresh_token = tok.get("refresh_token")
    expires_in = tok.get("expires_in")
    expires_at = None
    if expires_in:
        expires_at = datetime.utcnow().timestamp() + float(expires_in)

    state.source_store.update_source(
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

    job_id = state.job_store.create_job(type="source_sync")

    def run_sync(state: AppState = Depends(get_state)):
        try:
            _sync_google_drive_source(state, source_id, job_id)
        except Exception as e:
            state.job_store.update_job(job_id, status="failed", message=str(e))
            state.source_store.update_source(
                source_id,
                status="error",
                last_error=str(e),
            )

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


@router.post("/sources/{source_id}/sync")
async def sync_source(background_tasks: BackgroundTasks, source_id: str, state: AppState = Depends(get_state)):
    try:
        src = state.source_store.get_source(source_id, redact=False)
    except KeyError:
        raise HTTPException(status_code=404, detail="Source not found")

    job_id = state.job_store.create_job(type="source_sync")

    def run_sync(state: AppState = Depends(get_state)):
        try:
            if src.type == "s3":
                _sync_s3_source(state, source_id, job_id)
            elif src.type == "google_drive":
                _sync_google_drive_source(state, source_id, job_id)
            elif src.type == "local_folder":
                # Mirror of existing rescan behavior
                path = (src.config or {}).get("path")
                if not isinstance(path, str) or not path:
                    raise RuntimeError("Invalid local folder path")
                results = state.photo_search_engine.scan(path, force=False)
                all_files = results.get("all_files", []) if isinstance(results, dict) else []
                if all_files:
                    state.process_semantic_indexing(all_files)
                state.job_store.update_job(
                    job_id,
                    status="completed",
                    progress=100,
                    message="Local re-scan complete.",
                )
            else:
                raise RuntimeError("Unsupported source type")
        except Exception as e:
            state.job_store.update_job(job_id, status="failed", message=str(e))
            state.source_store.update_source(
                source_id,
                status="error",
                last_error=str(e),
            )

    background_tasks.add_task(run_sync)
    return {"ok": True, "job_id": job_id}
