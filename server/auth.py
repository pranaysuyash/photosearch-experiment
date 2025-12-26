import base64
import json
import hmac
import hashlib
from typing import Dict, Any
from .config import settings


def _b64url_decode(data: str) -> bytes:
    padding = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


class AuthError(Exception):
    pass


def verify_jwt(token: str) -> Dict[str, Any]:
    """Minimal HS256 JWT verifier (no external dependency).

    Expects token in header.payload.sig (base64url). Verifies HMAC-SHA256.
    This is intentionally minimal for the project so it can be used in tests and
    simple deployments. For production, prefer a full JWT library or OIDC.
    """
    if not settings.JWT_SECRET:
        raise AuthError("JWT_SECRET not configured")

    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError:
        raise AuthError("Malformed token")

    try:
        sig = _b64url_decode(sig_b64)
    except Exception:
        raise AuthError("Invalid signature encoding")

    expected_sig = hmac.new(
        settings.JWT_SECRET.encode("utf-8"),
        f"{header_b64}.{payload_b64}".encode("utf-8"),
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(expected_sig, sig):
        raise AuthError("Invalid signature")

    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception:
        raise AuthError("Invalid payload")

    # Optional issuer check
    if settings.JWT_ISSUER and payload.get("iss") != settings.JWT_ISSUER:
        raise AuthError("Invalid issuer")

    # Optional expiry check
    exp = payload.get("exp")
    if exp and int(exp) < int(__import__("time").time()):
        raise AuthError("Token expired")

    return payload


def create_jwt(payload: Dict[str, Any]) -> str:
    """Create a minimal HS256 JWT for test/dev purposes.

    Note: This is not intended to replace a full auth provider.
    """
    header = {"alg": settings.JWT_ALGO, "typ": "JWT"}
    header_b64 = (
        base64.urlsafe_b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8")).rstrip(b"=").decode("ascii")
    )
    payload_b64 = (
        base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        .rstrip(b"=")
        .decode("ascii")
    )
    sig = hmac.new(
        settings.JWT_SECRET.encode("utf-8"),
        f"{header_b64}.{payload_b64}".encode("utf-8"),
        hashlib.sha256,
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode("ascii")
    return f"{header_b64}.{payload_b64}.{sig_b64}"
