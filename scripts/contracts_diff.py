#!/usr/bin/env python3
"""
Compare current API contracts against committed baselines.

Usage:
    python scripts/contracts_diff.py [--baseline-dir tests/contracts]

Exit codes:
    0 - No differences
    1 - Differences found (intentional changes need baseline update)
    2 - Error (missing files, etc.)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def load_json(path: Path) -> dict | list:
    """Load JSON file."""
    with open(path) as f:
        return json.load(f)


def compare_routes(baseline: list[dict], current: list[dict]) -> list[str]:
    """Compare route inventories and return differences."""
    diffs = []

    baseline_set = {(r["path"], r["method"]) for r in baseline}
    current_set = {(r["path"], r["method"]) for r in current}

    added = current_set - baseline_set
    removed = baseline_set - current_set

    for path, method in sorted(added):
        diffs.append(f"+ {method} {path}")

    for path, method in sorted(removed):
        diffs.append(f"- {method} {path}")

    return diffs


def compare_openapi(baseline: dict, current: dict) -> list[str]:
    """Compare OpenAPI schemas and return high-level differences."""
    diffs = []

    baseline_paths = set(baseline.get("paths", {}).keys())
    current_paths = set(current.get("paths", {}).keys())

    for path in sorted(current_paths - baseline_paths):
        diffs.append(f"+ OpenAPI path: {path}")

    for path in sorted(baseline_paths - current_paths):
        diffs.append(f"- OpenAPI path: {path}")

    # Check for schema changes in existing paths
    for path in baseline_paths & current_paths:
        baseline_ops = set(baseline["paths"][path].keys())
        current_ops = set(current["paths"][path].keys())

        for op in sorted(current_ops - baseline_ops):
            diffs.append(f"+ {path}: {op.upper()} operation added")

        for op in sorted(baseline_ops - current_ops):
            diffs.append(f"- {path}: {op.upper()} operation removed")

    return diffs


def main():
    parser = argparse.ArgumentParser(description="Compare API contracts")
    parser.add_argument(
        "--baseline-dir",
        type=Path,
        default=Path("tests/contracts"),
        help="Directory containing baseline contract files",
    )
    parser.add_argument(
        "--current-dir",
        type=Path,
        default=None,
        help="Directory containing current contracts (default: generate fresh)",
    )
    args = parser.parse_args()

    # Check baseline files exist
    routes_baseline = args.baseline_dir / "routes.json"
    openapi_baseline = args.baseline_dir / "openapi.json"

    if not routes_baseline.exists():
        print(f"❌ Baseline not found: {routes_baseline}")
        print("   Run: python scripts/contracts_dump.py")
        return 2

    if not openapi_baseline.exists():
        print(f"❌ Baseline not found: {openapi_baseline}")
        print("   Run: python scripts/contracts_dump.py")
        return 2

    # Generate current contracts
    if args.current_dir:
        current_routes = load_json(args.current_dir / "routes.json")
        current_openapi = load_json(args.current_dir / "openapi.json")
    else:
        # Generate fresh from app
        import os

        os.environ["PHOTOSEARCH_SKIP_MODELS"] = "1"

        from server.main import app

        # Import dump functions
        from scripts.contracts_dump import dump_routes, dump_openapi

        current_routes = dump_routes(app)
        current_openapi = dump_openapi(app)

    # Load baselines
    baseline_routes = load_json(routes_baseline)
    baseline_openapi = load_json(openapi_baseline)

    # Compare
    route_diffs = compare_routes(baseline_routes, current_routes)
    openapi_diffs = compare_openapi(baseline_openapi, current_openapi)

    all_diffs = route_diffs + openapi_diffs

    if not all_diffs:
        print("✓ No contract differences found")
        print(f"  Routes: {len(current_routes)} endpoints")
        return 0

    print(f"❌ Contract differences found ({len(all_diffs)} changes):\n")
    for diff in all_diffs:
        print(f"  {diff}")

    print("\n  If these changes are intentional, update baselines:")
    print("    python scripts/contracts_dump.py")

    return 1


if __name__ == "__main__":
    sys.exit(main())
