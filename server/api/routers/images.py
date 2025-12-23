import logging
import os
from datetime import datetime
from pathlib import Path
from threading import Lock

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import FileResponse, Response

from server.auth import AuthError, verify_jwt
from server.config import settings
from server.security_utils import hash_for_logs
from server.signed_urls import TokenError, issue_token, verify_token
from server.utils.http import _make_cache_headers
from server.utils.images import _negotiate_image_format

router = APIRouter()
logger = logging.getLogger("photosearch")


# Simple in-memory rate limiting counters (per-IP sliding window)
_rate_lock = Lock()
_rate_counters: dict[str, list[float]] = {}
_rate_last_conf: tuple[bool, int] | None = None


@router.get("/image/thumbnail")
async def get_thumbnail(
    request: Request,
    path: str = "",
    size: int = 300,
    token: str | None = None,
    format: str | None = None,
):
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
                raise HTTPException(
                    status_code=401, detail="Signed URL required for this deployment"
                )

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
            logger.warning(
                f"Access denied to image: {hash_for_logs(requested_path_str)} "
                f"ip={request.client.host if request.client else 'unknown'}"
            )
            raise HTTPException(
                status_code=403,
                detail="Access denied: File outside allowed directories",
            )
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
    cors_origins = {str(origin) for origin in settings.CORS_ORIGINS}
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
        logger.info(
            f"IMAGE_ACCESS path={logged_path} size={size} "
            f"ip={request.client.host if request.client else 'unknown'} "
            f"token={'yes' if token else 'no'}"
        )
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
                    conf = (
                        bool(settings.RATE_LIMIT_ENABLED),
                        int(settings.RATE_LIMIT_REQS_PER_MIN),
                    )
                    client_ip = request.client.host if request.client else "unknown"
                    now = __import__("time").time()
                    global _rate_last_conf
                    with _rate_lock:
                        if _rate_last_conf != conf:
                            _rate_counters.clear()
                            _rate_last_conf = conf
                        lst = _rate_counters.get(client_ip, [])
                        lst = [t for t in lst if now - t < 60]
                        if len(lst) >= settings.RATE_LIMIT_REQS_PER_MIN:
                            raise HTTPException(
                                status_code=429, detail="Rate limit exceeded"
                            )
                        lst.append(now)
                        _rate_counters[client_ip] = lst
            except HTTPException:
                raise
            except Exception:
                pass

            content_bytes = img_io.getvalue()
            logger.info(
                f"Thumbnail produced {len(content_bytes)} bytes for {requested_path_str} as {output_format}"
            )
            # Include cache headers + content type + explicit CORS headers
            headers = dict(cache_headers)
            headers.setdefault(
                "Content-Type",
                "image/webp" if output_format == "WEBP" else "image/jpeg",
            )

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


@router.post("/image/token")
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
            auth_header = request.headers.get("authorization") or request.headers.get(
                "Authorization"
            )
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
            raise HTTPException(
                status_code=401, detail="Missing or invalid issuer API key"
            )
    else:
        logger.warning(
            "No token issuer configured; token issuance is unprotected (dev only)"
        )

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
            raise HTTPException(
                status_code=403, detail="Path is outside allowed directories"
            )
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    # Issue token
    try:
        token = issue_token(path, uid=uid, ttl=ttl, scope=scope)
        return {"token": token, "expires_in": ttl or settings.SIGNED_URL_TTL_SECONDS}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
