"""Device pairing for the web companion.

The owner's desktop (loopback) starts a pairing attempt, gets a short numeric
code, and enters it on the other device at ``/app/pair``. Completing the code
mints a session token (cookie + bearer) that makes that browser the owner.

Codes are in-memory and single-use with a short TTL by design: a restart
invalidating a not-yet-completed pairing is the correct behaviour, so nothing
here needs to persist. Revocation rotates the session secret, which signs out
every paired device at once.
"""

from __future__ import annotations

import random
import socket
import threading
import time
from typing import Dict

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from server.config import settings
from server.principal import (
    DEFAULT_USER,
    Principal,
    issue_session_token,
    resolve_principal,
    rotate_session_secret,
)

router = APIRouter(prefix="/pair", tags=["pairing"])

_lock = threading.Lock()
_pending: Dict[str, float] = {}  # code -> monotonic expiry


def _loopback_owner(request: Request) -> Principal:
    principal = resolve_principal(request)
    if principal is None or principal.via != "loopback":
        raise HTTPException(
            status_code=403,
            detail="Pairing is started from the desktop app, not from other devices",
        )
    return principal


def _sweep_expired() -> None:
    now = time.monotonic()
    for code in [c for c, exp in _pending.items() if exp < now]:
        _pending.pop(code, None)


def _suggested_lan_url(request: Request) -> str | None:
    """Best-effort LAN address for the human to type on the other device.

    A UDP connect finds the outbound interface address without sending a
    packet. Cosmetic only — the code works from any address this server
    answers on.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(0.2)
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
        return f"http://{ip}:{settings.PORT}{UI_HINT_PATH}"
    except OSError:
        return None


UI_HINT_PATH = "/app/pair"


class PairStartResponse(BaseModel):
    code: str
    expires_in: int
    suggested_url: str | None = None


class PairCompleteRequest(BaseModel):
    code: str


class PairCompleteResponse(BaseModel):
    user_id: str
    token: str


@router.post("/start", response_model=PairStartResponse)
async def start_pairing(request: Request):
    if not settings.PAIRING_ENABLED:
        raise HTTPException(status_code=404, detail="Pairing is disabled")
    _loopback_owner(request)

    with _lock:
        _sweep_expired()
        # Four digits keep the phone-typing cost low; the code is only usable
        # within its short TTL and a failed guess costs one attempt, so the
        # entropy budget is fine for a LAN-companion trust model.
        code = f"{random.randint(0, 9999):04d}"
        _pending[code] = time.monotonic() + settings.PAIRING_CODE_TTL_SECONDS

    return PairStartResponse(
        code=code,
        expires_in=settings.PAIRING_CODE_TTL_SECONDS,
        suggested_url=_suggested_lan_url(request),
    )


@router.post("/complete", response_model=PairCompleteResponse)
async def complete_pairing(request: Request, body: PairCompleteRequest, response: Response):
    if not settings.PAIRING_ENABLED:
        raise HTTPException(status_code=404, detail="Pairing is disabled")

    with _lock:
        _sweep_expired()
        expiry = _pending.pop(body.code.strip(), None)
    if expiry is None:
        raise HTTPException(status_code=400, detail="Unknown or expired code")

    token = issue_session_token(DEFAULT_USER)
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        path="/",
    )
    return PairCompleteResponse(user_id=DEFAULT_USER, token=token)


@router.post("/revoke")
async def revoke_pairing(request: Request):
    _loopback_owner(request)
    rotate_session_secret()
    with _lock:
        _pending.clear()
    return {"ok": True, "detail": "All paired devices signed out"}


@router.get("/status")
async def pairing_status(request: Request):
    principal = resolve_principal(request)
    return {
        "pairing_enabled": settings.PAIRING_ENABLED,
        "paired": principal is not None,
        "via": principal.via if principal else None,
        "user_id": principal.id if principal else None,
    }
