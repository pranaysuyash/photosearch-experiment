"""
The principal gate: who is allowed to call this server, and as whom.

Model: exactly one principal — the owner — reachable from many devices.

- Loopback callers (the desktop shell, local dev, the packaged Tauri app) ARE
  the owner. No ceremony, no configuration.
- Every other client must present a session token minted by the pairing flow
  (``server/api/routers/pairing.py``): either the ``ps_session`` cookie set on
  completion (covers ``<img>``/``<video>`` URLs, which cannot send headers) or
  an ``Authorization: Bearer`` token.

The resolver returns a :class:`Principal`, not a boolean, so a future
multi-user mode (self-hosted server) extends ``resolve_principal`` to map
tokens to other principals — routers keep reading ``request.state.principal``
and never learn the difference.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from dataclasses import dataclass

from fastapi import Request
from starlette.responses import JSONResponse

from server.config import settings
from server.ui_static import UI_MOUNT_PATH

DEFAULT_USER = "default_user"
LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}

EXEMPT_PATHS = frozenset({"/", "/health"})
EXEMPT_PREFIXES = ("/pair", UI_MOUNT_PATH)


@dataclass(frozen=True)
class Principal:
    id: str
    kind: str  # 'owner' today; more kinds are what a multi-user mode adds
    via: str  # 'loopback' | 'cookie' | 'bearer'


# ─────────────────────────────────────────────────────────────────────────────
# Session secret: settings.SESSION_SECRET, else a random secret generated once
# into DATA_DIR/session.key (0600) so a desktop install needs zero config.
# ─────────────────────────────────────────────────────────────────────────────

_secret_lock = threading.Lock()
_cached_secret: str | None = None


def _secret_file_path():
    return settings.DATA_DIR / "session.key"


def get_session_secret() -> str:
    global _cached_secret
    if _cached_secret:
        return _cached_secret
    with _secret_lock:
        if _cached_secret:
            return _cached_secret
        if settings.SESSION_SECRET:
            _cached_secret = settings.SESSION_SECRET
            return _cached_secret
        path = _secret_file_path()
        try:
            if path.is_file():
                existing = path.read_text(encoding="utf-8").strip()
                if existing:
                    _cached_secret = existing
                    return _cached_secret
        except OSError:
            pass
        secret = secrets.token_urlsafe(48)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(secret + "\n", encoding="utf-8")
            path.chmod(0o600)
        except OSError:
            # Unwritable DATA_DIR: fall back to an in-process secret. Sessions
            # then do not survive a restart; pairing still works in-process.
            pass
        _cached_secret = secret
        return _cached_secret


def rotate_session_secret() -> None:
    """Invalidate every minted session (all paired devices sign out)."""
    global _cached_secret
    with _secret_lock:
        try:
            _secret_file_path().unlink(missing_ok=True)
        except OSError:
            pass
        _cached_secret = None


# ─────────────────────────────────────────────────────────────────────────────
# Session tokens: minimal HS256 JWT (same envelope as server/auth.py) so a
# later multi-user mode can swap in a full JWT library without client changes.
# ─────────────────────────────────────────────────────────────────────────────


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    return base64.urlsafe_b64decode((data + "=" * (-len(data) % 4)).encode("ascii"))


def _sign(secret: str, signing_input: str) -> str:
    digest = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    return _b64url(digest)


def issue_session_token(principal_id: str = DEFAULT_USER) -> str:
    secret = get_session_secret()
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64url(
        json.dumps(
            {
                "sub": principal_id,
                "kind": "owner",
                "iat": int(time.time()),
                "exp": int(time.time()) + settings.SESSION_TTL_SECONDS,
            }
        ).encode()
    )
    return f"{header}.{payload}.{_sign(secret, f'{header}.{payload}')}"


def verify_session_token(token: str) -> Principal | None:
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
        expected = _sign(get_session_secret(), f"{header_b64}.{payload_b64}")
        if not hmac.compare_digest(expected, sig_b64):
            return None
        payload = json.loads(_b64url_decode(payload_b64))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return Principal(id=str(payload.get("sub") or DEFAULT_USER), kind="owner", via="token")
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Resolution
# ─────────────────────────────────────────────────────────────────────────────


def _is_test_peer(host: str | None) -> bool:
    """TestClient's default peer ('testclient') counts as loopback so the
    existing test suite keeps its localhost semantics unchanged."""
    return host == "testclient" and (
        os.environ.get("PHOTOSEARCH_TEST_MODE") == "1" or "PYTEST_CURRENT_TEST" in os.environ
    )


def _effective_peer_host(request: Request) -> str | None:
    host = request.client.host if request.client else None
    if settings.TRUST_PROXY:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            host = forwarded.split(",")[0].strip()
    return host


def _is_loopback(request: Request) -> bool:
    host = _effective_peer_host(request)
    if host is None:
        return False
    return host in LOOPBACK_HOSTS or _is_test_peer(host)


def resolve_principal(request: Request) -> Principal | None:
    if _is_loopback(request):
        return Principal(id=DEFAULT_USER, kind="owner", via="loopback")

    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        principal = verify_session_token(auth[7:].strip())
        if principal is not None:
            return Principal(id=principal.id, kind=principal.kind, via="bearer")

    cookie = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if cookie:
        principal = verify_session_token(cookie)
        if principal is not None:
            return Principal(id=principal.id, kind=principal.kind, via="cookie")

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Middleware
# ─────────────────────────────────────────────────────────────────────────────


def is_exempt(path: str) -> bool:
    if path in EXEMPT_PATHS:
        return True
    return any(path == p or path.startswith(p + "/") for p in EXEMPT_PREFIXES)


class PrincipalMiddleware:
    """One gate in front of every route (routers stay untouched).

    OPTIONS passes through so CORS preflights keep working. Exempt paths
    (root, health, pairing, the static UI) resolve no principal.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") == "OPTIONS":
            await self.app(scope, receive, send)
            return

        principal = None
        if not is_exempt(scope.get("path", "")):
            principal = resolve_principal(Request(scope))
            if principal is None:
                response = JSONResponse(
                    {"detail": "Not paired with this server. Pair at /app/pair."},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                )
                await response(scope, receive, send)
                return

        # request.state.principal for dependencies; keep Starlette's scope shape.
        scope.setdefault("state", {})["principal"] = principal
        await self.app(scope, receive, send)
