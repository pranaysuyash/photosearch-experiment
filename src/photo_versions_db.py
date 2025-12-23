"""Compatibility shim for tests and legacy imports.

Some tests and older modules import `PhotoVersionsDB` (and helpers) from
`src.photo_versions_db`, but the implementation lives in `server.photo_versions_db`.

This module re-exports the public symbols to keep import paths stable.
"""

from server.photo_versions_db import PhotoVersionsDB, get_photo_versions_db

__all__ = ["PhotoVersionsDB", "get_photo_versions_db"]
