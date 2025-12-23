"""Compatibility shim for tests and legacy imports.

The implementation lives in `server.bulk_actions_db`.
"""

from server.bulk_actions_db import BulkActionsDB

__all__ = ["BulkActionsDB"]
