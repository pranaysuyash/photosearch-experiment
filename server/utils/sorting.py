import calendar
from datetime import datetime
from typing import Optional


def _parse_isoish_datetime(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _parse_month_or_date(value: Optional[str], end: bool = False) -> Optional[datetime]:
    """
    Supports YYYY-MM or ISO datetime/date strings.
    For YYYY-MM: start is first day 00:00:00, end is last day 23:59:59.
    """
    if not value:
        return None
    v = value.strip()
    if not v:
        return None

    if len(v) == 7 and v[4] == "-":
        try:
            year = int(v[0:4])
            month = int(v[5:7])
            last_day = calendar.monthrange(year, month)[1]
            return datetime(year, month, last_day, 23, 59, 59) if end else datetime(year, month, 1, 0, 0, 0)
        except Exception:
            return None

    dt = _parse_isoish_datetime(v)
    if dt:
        # Drop tzinfo to compare with naive datetimes
        return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt

    try:
        if len(v) == 10 and v[4] == "-" and v[7] == "-":
            year = int(v[0:4])
            month = int(v[5:7])
            day = int(v[8:10])
            return datetime(year, month, day, 23, 59, 59) if end else datetime(year, month, day, 0, 0, 0)
    except Exception:
        return None

    return None


def _get_created_datetime(meta: dict) -> Optional[datetime]:
    try:
        fs = (meta or {}).get("filesystem", {}) or {}
        created = fs.get("created")
        if isinstance(created, str):
            dt = _parse_isoish_datetime(created)
            if not dt:
                return None
            return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt
    except Exception:
        return None
    return None


def apply_date_filter(results: list, date_from: Optional[str], date_to: Optional[str]) -> list:
    """
    Filters results by metadata.filesystem.created inclusive.
    date_from/date_to accept YYYY-MM or ISO date/datetime strings.
    """
    start = _parse_month_or_date(date_from, end=False)
    end = _parse_month_or_date(date_to, end=True)
    if not start and not end:
        return results

    filtered = []
    for r in results:
        if not isinstance(r, dict):
            continue
        dt = _get_created_datetime(r.get("metadata") or {})
        if not dt:
            continue
        if start and dt < start:
            continue
        if end and dt > end:
            continue
        filtered.append(r)
    return filtered


def apply_sort(results: list, sort_by: str) -> list:
    """Sort results by specified criteria."""
    if not results:
        return results

    def _meta(r: dict) -> dict:
        m = r.get("metadata", {})
        return m if isinstance(m, dict) else {}

    def _date_key(r: dict) -> str:
        m = _meta(r)
        fs = m.get("filesystem", {}) if isinstance(m.get("filesystem", {}), dict) else {}
        return fs.get("created") or m.get("date_taken") or m.get("created") or ""

    def _size_key(r: dict) -> int:
        m = _meta(r)
        fs = m.get("filesystem", {}) if isinstance(m.get("filesystem", {}), dict) else {}
        v = fs.get("size_bytes")
        if isinstance(v, (int, float)):
            return int(v)
        v2 = m.get("file_size")
        if isinstance(v2, (int, float)):
            return int(v2)
        return 0

    if sort_by == "date_desc":
        # Sort by created date descending (newest first)
        return sorted(results, key=_date_key, reverse=True)
    if sort_by == "date_asc":
        # Sort by created date ascending (oldest first)
        return sorted(results, key=_date_key)
    if sort_by == "name":
        # Sort by filename alphabetically
        return sorted(results, key=lambda x: x.get("filename", "").lower())
    if sort_by == "size":
        # Sort by file size descending (largest first)
        return sorted(results, key=_size_key, reverse=True)

    return results
