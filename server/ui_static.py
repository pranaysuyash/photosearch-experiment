"""
Serve the web-companion UI build from the API process.

The desktop shell loads ``ui/dist`` through Tauri's asset protocol and talks
to this server on loopback. Browsers on other devices need the UI delivered
from the *same origin* as the API so that no CORS, no absolute API URL, and
no second server are involved. That build (``npm run build:web`` →
``ui/dist-web``, Vite ``base: /app/``) is mounted here at ``/app``.

Why a prefix and not a root catch-all: the API's routes live at the top level
(``/search``, ``/browse``, ``/image`` …). A catch-all would turn every API
typo into a 200 HTML page and would add a route to the OpenAPI contract; a
mount does neither.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

UI_MOUNT_PATH = "/app"

logger = logging.getLogger(__name__)


class SPAStaticFiles(StaticFiles):
    """StaticFiles whose misses fall back to ``index.html``.

    BrowserRouter deep links (``/app/people/42``) are client-side routes with
    no file behind them; a hard refresh must still load the app shell.
    """

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
            return await super().get_response("index.html", scope)


def mount_ui(app: FastAPI, dist_dir: Path, *, enabled: bool = True) -> bool:
    """Mount the UI build at ``/app`` when it exists. Returns True if mounted.

    A missing build is normal (fresh checkout, desktop-only install) and is
    logged, not raised: the API must come up regardless.
    """
    if not enabled:
        return False
    index = dist_dir / "index.html"
    if not index.is_file():
        logger.info("Web UI not mounted: %s has no index.html (run `npm run build:web`)", dist_dir)
        return False
    app.mount(UI_MOUNT_PATH, SPAStaticFiles(directory=str(dist_dir), html=True), name="ui")
    logger.info("Web UI mounted at %s from %s", UI_MOUNT_PATH, dist_dir)
    return True
