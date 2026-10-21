"""
In-memory sliding-window rate limiting for non-loopback callers.

The desktop app's loopback traffic is never throttled — it is the owner on a
trusted socket. Paired devices and unauthenticated strangers share a
per-IP bucket, which caps the blast radius of a run-away web client or a
casual scanner without adding any dependency.

This supersedes the thumbnail-only limiter (server/api/routers/images.py) for
everything except that endpoint's own, stricter budget, and the never-wired
counters declared in server/main.py.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from starlette.responses import JSONResponse

from server.config import settings
from server.principal import is_exempt
from server.ui_static import UI_MOUNT_PATH

WINDOW_SECONDS = 60.0


class RateLimitMiddleware:
    def __init__(self, app):
        self.app = app
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _client_key(self, scope) -> str:
        client = scope.get("client")
        host = client[0] if client else "unknown"
        forwarded = None
        for name, value in scope.get("headers") or []:
            if name == b"x-forwarded-for":
                forwarded = value.decode("latin-1")
                break
        if settings.TRUST_PROXY and forwarded:
            host = forwarded.split(",")[0].strip()
        return host

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") == "OPTIONS" or not settings.RATE_LIMIT_ENABLED:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        # Static assets are high-volume and harmless; exempt paths answered by
        # the principal gate are equally irrelevant here.
        if path.startswith(UI_MOUNT_PATH) or is_exempt(path):
            await self.app(scope, receive, send)
            return

        from server.principal import LOOPBACK_HOSTS

        key = self._client_key(scope)
        if key in LOOPBACK_HOSTS or key == "testclient":
            await self.app(scope, receive, send)
            return

        now = time.monotonic()
        with self._lock:
            bucket = self._hits[key]
            cutoff = now - WINDOW_SECONDS
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= settings.RATE_LIMIT_REQS_PER_MIN:
                retry_after = int(WINDOW_SECONDS - (now - bucket[0])) + 1
                response = JSONResponse(
                    {"detail": "Too many requests"},
                    status_code=429,
                    headers={"Retry-After": str(retry_after)},
                )
                await response(scope, receive, send)
                return
            bucket.append(now)

        await self.app(scope, receive, send)
