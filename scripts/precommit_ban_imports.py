#!/usr/bin/env python3
"""
Pre-commit hook: Ban lazy imports of server.main in routers/services.

Prevents patterns like:
    from server import main as main_module
    import server.main
    from server.main import something

Routers should use: from server.api.deps import get_state
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

BANNED_IMPORT_MODULES = {"server.main"}
ENFORCE_DIRS = [Path("server/api/routers"), Path("server/services")]
ALLOW_MARKER = "allow-main-import"


def is_in_enforced_dir(path: Path) -> bool:
    return any(d in path.parents or path == d for d in ENFORCE_DIRS)


def check_file(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return errors

    if ALLOW_MARKER in text:
        return errors

    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return errors

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in BANNED_IMPORT_MODULES:
                    errors.append(f"{path}:{node.lineno}: banned import '{alias.name}'")
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod in BANNED_IMPORT_MODULES:
                errors.append(f"{path}:{node.lineno}: banned 'from {mod} import ...'")
            if mod == "server" and any(a.name == "main" for a in node.names):
                errors.append(f"{path}:{node.lineno}: banned 'from server import main'")

    # Quick string guard for common alias pattern
    if "from server import main as" in text or "import server.main" in text:
        if not any("banned" in e for e in errors):
            errors.append(f"{path}: banned main import pattern detected")

    return errors


def main(argv: list[str]) -> int:
    files = [Path(a) for a in argv[1:] if a.endswith(".py")]
    errors: list[str] = []

    for f in files:
        if f.exists() and is_in_enforced_dir(f):
            errors.extend(check_file(f))

    if errors:
        print("❌ Banned lazy imports detected:\n")
        for e in errors:
            print(f"  {e}")
        print(f"\nFix: Use 'from server.api.deps import get_state' with Depends().")
        print(f"Escape hatch: Add '{ALLOW_MARKER}' comment if truly unavoidable.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
