#!/usr/bin/env python3
"""
Pre-commit hook: Enforce file size/line limits.

Prevents another monolithic main.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Limits per path prefix (path_prefix, max_lines)
LIMITS = [
    ("server/main.py", 600),
    ("server/api/routers", 1200),
    ("server/services", 1000),
]

ABSOLUTE_MAX = 2000

# Allowlist for known large files (temporary, with migration plan)
ALLOWLIST = {
    "server/api/routers/face_recognition.py": 1600,
    "server/api/routers/search.py": 1200,
    "server/api/routers/sources.py": 1400,
}

ALLOW_MARKER = "allow-big-file"


def line_count(path: Path) -> int:
    try:
        return sum(1 for _ in path.open("r", encoding="utf-8", errors="ignore"))
    except Exception:
        return 0


def applicable_limit(path: Path) -> int | None:
    s = str(path)
    if s in ALLOWLIST:
        return ALLOWLIST[s]
    for prefix, lim in LIMITS:
        if s == prefix or s.startswith(prefix + "/"):
            return lim
    return None


def main(argv: list[str]) -> int:
    files = [Path(a) for a in argv[1:] if a.endswith(".py")]
    errors: list[str] = []

    for f in files:
        if not f.exists():
            continue

        limit = applicable_limit(f)
        if limit is None:
            continue

        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        if ALLOW_MARKER in text:
            continue

        n = line_count(f)
        if n > ABSOLUTE_MAX:
            errors.append(f"{f}: {n} lines exceeds absolute max {ABSOLUTE_MAX}")
        elif n > limit:
            errors.append(f"{f}: {n} lines exceeds limit {limit}")

    if errors:
        print("❌ File size limits exceeded:\n")
        for e in errors:
            print(f"  {e}")
        print("\nFix: Split the file into smaller modules/routers/services.")
        print(f"Escape hatch: Add '{ALLOW_MARKER}' comment or update ALLOWLIST.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
