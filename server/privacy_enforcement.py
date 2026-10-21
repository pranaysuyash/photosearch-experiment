"""
Serve-time photo access enforcement.

Bridges PrivacyControlsDB to the image/file serving paths. Policy:

- A photo with NO privacy control record is default-open (backward
  compatibility: the library predates per-photo controls, and the owner's
  own library must keep rendering).
- A photo WITH a control is gated by check_access_permission (owner,
  public visibility, or allowed users/groups).
- Requester identity follows the privacy router's convention: the
  X-User-ID header, defaulting to "default_user".

Key normalization: controls may be stored under the raw requested string
or the resolved absolute path, so both are tried (plus MEDIA_DIR-relative
forms) before concluding no control exists.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from server.config import settings
from server.privacy_controls_db import get_privacy_controls_db

DEFAULT_USER = "default_user"


class PhotoAccessDenied(PermissionError):
    """Raised when a privacy control denies access to a photo."""


def user_id_from_request(request) -> str:
    """Identity for privacy evaluation.

    The principal gate (server/principal.py) is authoritative when it has
    resolved a caller: loopback is the owner and a paired device's session
    token carries the id. The X-User-ID header / ?user_id= query fallback only
    applies when no principal was resolved (exempt paths, direct handler
    calls) — header first, query param for <img src> URLs that cannot carry
    headers.
    """
    principal = getattr(getattr(request, "state", None), "principal", None)
    if principal is not None:
        return principal.id
    header_id = request.headers.get("X-User-ID")
    if header_id:
        return header_id
    try:
        query_id = request.query_params.get("user_id")
    except AttributeError:
        query_id = None
    return query_id or DEFAULT_USER


def _candidate_keys(path_str: str) -> Iterator[str]:
    seen: set[str] = set()
    candidates = [path_str]
    try:
        candidates.append(str(Path(path_str).resolve()))
    except OSError:
        pass
    try:
        media = settings.MEDIA_DIR.resolve()
        for candidate in list(candidates):
            try:
                resolved = str(Path(candidate).resolve())
            except OSError:
                continue
            if resolved.startswith(str(media)):
                rel = resolved[len(str(media)) :]
                candidates.extend([rel, rel.lstrip("/"), "/" + rel.lstrip("/")])
    except Exception:
        pass
    for candidate in candidates:
        if candidate and candidate not in seen:
            seen.add(candidate)
            yield candidate


def assert_photo_access_allowed(path_str: str, user_id: str) -> None:
    """Raise PhotoAccessDenied if a privacy control denies this user."""
    db = get_privacy_controls_db(Path(settings.FACE_CLUSTERS_DB_PATH).parent / "privacy.db")
    for key in _candidate_keys(path_str):
        try:
            control = db.get_photo_privacy(key)
        except Exception:
            control = None
        if control is None:
            continue
        # First control record found governs.
        if not db.check_access_permission(key, user_id):
            raise PhotoAccessDenied(f"privacy control denies access to {key}")
        return
    # No control record: default-open.
    return
