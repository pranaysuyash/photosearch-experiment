import os
from email.utils import formatdate
from typing import Dict


def _httpdate(ts: float) -> str:
    """Return an HTTP-date string (RFC 7231) for a POSIX timestamp."""
    return formatdate(timeval=ts, usegmt=True)


def _make_cache_headers(stat_result: os.stat_result, *, max_age: int = 86400, extra: str = "") -> Dict[str, str]:
    """Create Cache-Control, ETag, and Last-Modified headers for a file."""
    etag = f"W/\"{stat_result.st_mtime_ns}-{stat_result.st_size}{('-' + extra) if extra else ''}\""
    return {
        "Cache-Control": f"public, max-age={max_age}",
        "ETag": etag,
        "Last-Modified": _httpdate(stat_result.st_mtime),
    }
