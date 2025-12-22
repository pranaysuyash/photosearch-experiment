import os
from pathlib import Path

from server.config import settings


def _runtime_base_dir() -> Path:
    """Resolve a runtime base dir.

    In tests we want an isolated writable directory even when the server is started as a
    subprocess (see `test_people_endpoints.py`).
    """
    if os.environ.get("PHOTOSEARCH_TEST_MODE") == "1":
        td = os.environ.get("PHOTOSEARCH_BASE_DIR")
        if td:
            try:
                return Path(td).resolve()
            except Exception:
                return Path(td)
    return settings.BASE_DIR
