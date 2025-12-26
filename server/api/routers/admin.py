import os
from pathlib import Path

from fastapi import APIRouter, Body, HTTPException, Request

from server.auth import AuthError, verify_jwt
from server.config import settings
from server.security_utils import hash_for_logs


router = APIRouter()


@router.post("/admin/unmask")
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
                    import logging

                    logger = logging.getLogger("photosearch")
                    logger.warning(f"UNMASK used by {client_host} for hash={h}")
                    return {"path": str(candidate)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    raise HTTPException(status_code=404, detail="No matching path found")
