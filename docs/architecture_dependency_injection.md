# Backend Architecture: Dependency Injection

This document describes the dependency injection (DI) pattern used in the PhotoSearch backend, implemented to eliminate circular imports and improve testability.

## Overview

The backend uses FastAPI's `Depends()` system with a centralized `AppState` container. All routers access shared state through dependency injection rather than importing from `server.main`.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         server/main.py                           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ lifespan():                                              │    │
│  │   state = build_state()  ─────────────────────────────────►  │
│  │   app.state.ps = state                                   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    server/core/state.py                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ @dataclass                                               │    │
│  │ class AppState:                                          │    │
│  │   settings, base_dir                                     │    │
│  │   vector_store, embedding_generator                      │    │
│  │   photo_search_engine, face_clusterer                    │    │
│  │   saved_search_manager, modal_system                     │    │
│  │   ...                                                    │    │
│  │                                                          │    │
│  │   def process_semantic_indexing(files):                  │    │
│  │       # Wrapper method for convenience                   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    server/api/deps.py                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ def get_state(request: Request) -> AppState:             │    │
│  │     return request.app.state.ps                          │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    server/api/routers/*.py                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ @router.get("/endpoint")                                 │    │
│  │ async def handler(state: AppState = Depends(get_state)): │    │
│  │     engine = state.photo_search_engine                   │    │
│  │     ...                                                  │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Key Files

| File | Purpose |
|------|---------|
| `server/core/state.py` | `AppState` dataclass containing all shared runtime state |
| `server/core/bootstrap.py` | `build_state()` function that initializes and returns `AppState` |
| `server/api/deps.py` | `get_state()` dependency function for routers |
| `server/main.py` | Composition root: calls `build_state()` and attaches to `app.state.ps` |

## Usage in Routers

```python
from fastapi import APIRouter, Depends
from server.api.deps import get_state
from server.core.state import AppState

router = APIRouter()

@router.get("/example")
async def example_endpoint(state: AppState = Depends(get_state)):
    # Access any component from state
    engine = state.photo_search_engine
    clusterer = state.face_clusterer

    # Use wrapper methods
    state.process_semantic_indexing(file_list)

    return {"status": "ok"}
```

## Banned Pattern

The following pattern is **banned** and will be rejected by pre-commit hooks:

```python
# ❌ DON'T DO THIS
from server import main as main_module
engine = main_module.photo_search_engine
```

Instead, always use dependency injection:

```python
# ✅ DO THIS
async def handler(state: AppState = Depends(get_state)):
    engine = state.photo_search_engine
```

## Helper Methods on AppState

`AppState` provides convenience wrapper methods for operations that require multiple dependencies:

- `process_semantic_indexing(files: List[str])` - Wraps the semantic indexing call with proper deps

## Pre-commit Hooks

Two hooks are configured in `.pre-commit-config.yaml`:

1. **`ban-lazy-imports`** - Blocks `from server import main` pattern
2. **`file-size-limits`** - Prevents files from growing too large (>1500 lines)

Install hooks: `pre-commit install`

## CI Pipeline

`.github/workflows/ci.yml` runs:
- Pre-commit hooks on all files
- Backend tests (`pytest server/tests/`)
- Lazy import ban check
- API parity check against contract baselines

## Migration History

- **Before**: 147 lazy imports across routers
- **After**: 0 lazy imports, full DI pattern

All routers now use `Depends(get_state)` for accessing shared state.
