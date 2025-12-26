import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional

from server.config import settings


class TokenError(Exception):
    pass


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + pad).encode("utf-8"))


def issue_token(
    path: str,
    uid: Optional[str] = None,
    ttl: Optional[int] = None,
    scope: str = "thumbnail",
) -> str:
    """
    Issue a signed token for accessing a file path via endpoints like `/image/thumbnail?token=...`.

    Token format: base64url(payload_json) + "." + base64url(hmac_sha256(payload_json)).
    """
    if not isinstance(path, str) or not path:
        raise TokenError("path is required")
    if ttl is None:
        ttl = int(getattr(settings, "SIGNED_URL_TTL_SECONDS", 3600))

    now = int(time.time())
    payload: Dict[str, Any] = {
        "path": path,
        "uid": uid,
        "scope": scope,
        "iat": now,
        "exp": now + int(ttl),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    secret = getattr(settings, "SIGNED_URL_SECRET", None)
    if not secret:
        # In dev/test it is better to degrade to the default dev secret than to 500.
        # In production we still fail closed.
        if getattr(settings, "ENV", "development") == "development":
            secret = "dev_signed_url_secret_change_me"
        else:
            raise TokenError("SIGNED_URL_SECRET is not configured")

    sig = hmac.new(str(secret).encode("utf-8"), payload_bytes, hashlib.sha256).digest()
    return f"{_b64url_encode(payload_bytes)}.{_b64url_encode(sig)}"


def verify_token(token: str, expected_scope: Optional[str] = None) -> Dict[str, Any]:
    if not isinstance(token, str) or "." not in token:
        raise TokenError("malformed token")
    try:
        p64, s64 = token.split(".", 1)
        payload_bytes = _b64url_decode(p64)
        sig_bytes = _b64url_decode(s64)
    except Exception as e:
        raise TokenError("malformed token") from e

    secret = getattr(settings, "SIGNED_URL_SECRET", None)
    if not secret:
        if getattr(settings, "ENV", "development") == "development":
            secret = "dev_signed_url_secret_change_me"
        else:
            raise TokenError("SIGNED_URL_SECRET is not configured")

    expected_sig = hmac.new(str(secret).encode("utf-8"), payload_bytes, hashlib.sha256).digest()
    if not hmac.compare_digest(sig_bytes, expected_sig):
        raise TokenError("invalid signature")

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        raise TokenError("invalid payload") from e

    exp = payload.get("exp")
    if not isinstance(exp, int):
        raise TokenError("missing exp")
    if int(time.time()) > exp:
        raise TokenError("expired token")

    if expected_scope is not None:
        if payload.get("scope") != expected_scope:
            raise TokenError("scope mismatch")

    if "path" not in payload or not payload.get("path"):
        raise TokenError("missing path")

    return payload
