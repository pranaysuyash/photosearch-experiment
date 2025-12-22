from fastapi import APIRouter

from server.config import settings


router = APIRouter()


@router.get("/")
async def root():
    return {"status": "ok", "message": "PhotoSearch API is running"}


@router.get("/server/config")
async def server_config():
    """Return a small subset of server configuration useful for the UI (non-sensitive)."""
    return {
        "signed_url_enabled": bool(settings.SIGNED_URL_ENABLED),
        "sandbox_strict": bool(settings.SANDBOX_STRICT),
        "rate_limit_enabled": bool(settings.RATE_LIMIT_ENABLED),
        "access_log_masking": bool(settings.ACCESS_LOG_MASKING),
        "jwt_auth_enabled": bool(settings.JWT_AUTH_ENABLED),
    }
