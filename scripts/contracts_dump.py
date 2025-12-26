#!/usr/bin/env python3
"""
Dump API contracts (routes + OpenAPI) for parity checking.

Usage:
    python scripts/contracts_dump.py [--output-dir tests/contracts]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def normalize_description(desc: str | None) -> str:
    """Normalize whitespace in descriptions for stable comparison."""
    if not desc:
        return ""
    return " ".join(desc.split())


def dump_routes(app) -> list[dict]:
    """Extract route inventory from FastAPI app."""
    routes = []
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
                routes.append(
                    {
                        "path": route.path,
                        "method": method,
                        "name": getattr(route, "name", None),
                        "summary": normalize_description(getattr(route, "summary", None)),
                    }
                )
    # Sort for deterministic output
    routes.sort(key=lambda r: (r["path"], r["method"]))
    return routes


def dump_openapi(app) -> dict:
    """Extract OpenAPI schema with normalized descriptions."""
    schema = app.openapi()

    # Normalize descriptions in paths
    if "paths" in schema:
        for path_data in schema["paths"].values():
            for op_data in path_data.values():
                if isinstance(op_data, dict) and "description" in op_data:
                    op_data["description"] = normalize_description(op_data["description"])
                if isinstance(op_data, dict) and "summary" in op_data:
                    op_data["summary"] = normalize_description(op_data["summary"])

    return schema


def main():
    parser = argparse.ArgumentParser(description="Dump API contracts")
    parser.add_argument(
        "--output-dir", type=Path, default=Path("tests/contracts"), help="Directory to write contract files"
    )
    args = parser.parse_args()

    # Import app without triggering model downloads by not running lifespan
    # We only need the route definitions, not the runtime state
    import os

    os.environ["PHOTOSEARCH_SKIP_MODELS"] = "1"  # Signal to skip heavy init

    from server.main import app

    # Dump routes
    routes = dump_routes(app)
    routes_file = args.output_dir / "routes.json"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with open(routes_file, "w") as f:
        json.dump(routes, f, indent=2)
    print(f"✓ Routes dumped to {routes_file} ({len(routes)} endpoints)")

    # Dump OpenAPI
    openapi = dump_openapi(app)
    openapi_file = args.output_dir / "openapi.json"
    with open(openapi_file, "w") as f:
        json.dump(openapi, f, indent=2, sort_keys=True)
    print(f"✓ OpenAPI dumped to {openapi_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
