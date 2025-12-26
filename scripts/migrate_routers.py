#!/usr/bin/env python3
"""
Auto-migration script for router lazy imports.
Replaces 'from server import main as main_module' pattern with Depends(get_state).
"""

import re
import sys


def migrate_router(filepath: str) -> tuple[bool, int]:
    """
    Migrate a router file from lazy imports to Depends(get_state).
    Returns (was_modified, imports_removed).
    """
    with open(filepath, "r") as f:
        content = f.read()

    original = content

    # Count lazy imports
    lazy_count = content.count("from server import main as main_module")
    if lazy_count == 0:
        return False, 0

    # Check if already has DI imports
    has_di = "from server.api.deps import get_state" in content

    # Step 1: Add Depends import if needed
    if "Depends" not in content:
        content = re.sub(
            r"from fastapi import ([^\n]+)", lambda m: f"from fastapi import {m.group(1)}, Depends", content, count=1
        )

    # Step 2: Add state imports after last server import
    if not has_di:
        # Find last import line
        lines = content.split("\n")
        last_import_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("from server.") or line.startswith("from fastapi"):
                last_import_idx = i

        # Insert after last server import
        lines.insert(last_import_idx + 1, "from server.api.deps import get_state")
        lines.insert(last_import_idx + 2, "from server.core.state import AppState")
        content = "\n".join(lines)

    # Step 3: Remove inline lazy imports
    content = re.sub(r"\s+from server import main as main_module\n", "\n", content)

    # Step 4: Replace main_module.X with state.X
    content = content.replace("main_module.", "state.")

    # Step 5: Add state parameter to async def functions that use state.
    # Find functions that reference state. and add state parameter
    def add_state_param(match):
        func_def = match.group(0)
        # Don't modify if already has state param
        if "state:" in func_def or "state =" in func_def:
            return func_def
        # Add state parameter at the end of parameters
        if func_def.endswith("):"):
            return func_def[:-2] + ", state: AppState = Depends(get_state)):"
        elif func_def.endswith(")"):
            return func_def[:-1] + ", state: AppState = Depends(get_state))"
        return func_def

    # Match async def ... that are likely to need state
    # We need to find functions that reference state. but don't have state param

    # Simpler approach: find all async def lines and check if function body uses state.
    lines = content.split("\n")
    new_lines = []
    func_uses_state = False

    for i, line in enumerate(lines):
        # Check if this is a function definition
        if line.strip().startswith("async def ") or line.strip().startswith("def "):
            # Check if next lines use state.
            func_body_start = i + 1
            func_uses_state = False
            for j in range(func_body_start, min(i + 30, len(lines))):
                if lines[j].strip().startswith("async def ") or lines[j].strip().startswith("def "):
                    break
                if "state." in lines[j]:
                    func_uses_state = True
                    break

            if func_uses_state and "state:" not in line and "state=" not in line:
                # Need to add state parameter
                if line.rstrip().endswith("):"):
                    # Has no parameters or params in parentheses
                    if "()" in line:
                        line = line.replace("():", "(state: AppState = Depends(get_state)):")
                    else:
                        # Has other params
                        line = line.rstrip()[:-2] + ", state: AppState = Depends(get_state)):"
                elif "(\n" in line or line.rstrip().endswith("("):
                    # Multi-line params - handle later with more context
                    pass

        new_lines.append(line)

    content = "\n".join(new_lines)

    if content != original:
        with open(filepath, "w") as f:
            f.write(content)
        return True, lazy_count

    return False, 0


def main():
    if len(sys.argv) < 2:
        print("Usage: python migrate_routers.py <file1.py> [file2.py ...]")
        sys.exit(1)

    total_removed = 0
    files_modified = 0

    for filepath in sys.argv[1:]:
        if not filepath.endswith(".py"):
            continue
        modified, count = migrate_router(filepath)
        if modified:
            files_modified += 1
            total_removed += count
            print(f"  ✓ {filepath}: {count} imports removed")
        else:
            print(f"  - {filepath}: no changes needed")

    print(f"\nSummary: {files_modified} files modified, {total_removed} lazy imports removed")


if __name__ == "__main__":
    main()
