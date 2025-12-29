import os
import sys
from pathlib import Path

# Ensure project root on sys.path for imports like `server` and `src`
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Stabilize native libs during pytest to avoid runaway threading/segfaults
for var in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ.setdefault(var, "1")

# Disable tqdm monitor threads during tests
os.environ.setdefault("TQDM_DISABLE", "1")

# Enable faulthandler for clearer native traces if something crashes
os.environ.setdefault("PYTHONFAULTHANDLER", "1")


def pytest_configure(config):
    """Pytest hook to ensure env/path settings are applied before tests run."""
    # Re-apply path/env in case other tooling mutated them
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    for var in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        os.environ.setdefault(var, "1")
    os.environ.setdefault("TQDM_DISABLE", "1")
    os.environ.setdefault("PYTHONFAULTHANDLER", "1")
