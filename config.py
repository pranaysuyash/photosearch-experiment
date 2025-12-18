"""
Compatibility shim.

The backend historically imported `settings` from a top-level `config` module.
We keep that import path stable while the canonical settings live in `server/config.py`.
"""

from server.config import settings  # noqa: F401

