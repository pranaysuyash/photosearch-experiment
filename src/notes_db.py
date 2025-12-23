"""Compatibility shim for tests and legacy imports.

Some tests and older modules import `NotesDB` from `src.notes_db`, but the
implementation lives in `server.notes_db`.

This module re-exports `NotesDB` to keep import paths stable.
"""

from server.notes_db import NotesDB

__all__ = ["NotesDB"]
