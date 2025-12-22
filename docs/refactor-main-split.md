# Main Refactor Log (refactor/main-split)

This document summarizes the main.py refactor into routers, schemas, utils, and services while preserving behavior.

## Goals
- Keep `server/main.py` as the FastAPI entrypoint and composition root.
- Move endpoint bodies into `server/api/routers/*` with no behavioral changes.
- Centralize shared helpers and initialization so routers stay thin.
- Preserve all routes and OpenAPI contract.

## High-level changes
- Extracted endpoints into routers under `server/api/routers/`.
- Extracted request/response models into `server/models/schemas/`.
- Extracted utility helpers into `server/utils/`.
- Added `server/services/` for non-router logic.
- Centralized non-router component initialization under `server/core/components.py`.
- Centralized shared app state under `server/core/state.py`.

## Key moves
- Sources endpoints and helpers -> `server/api/routers/sources.py`.
- Search endpoint -> `server/api/routers/search.py`.
- Semantic search endpoints -> `server/api/routers/semantic_search.py`.
- Trash and library removal endpoints -> `server/api/routers/trash.py`.
- Search explanation helpers -> `server/utils/search_explanations.py`.
- `validate_file_path` -> `server/utils/files.py`.
- `process_semantic_indexing` -> `server/services/semantic_indexing.py`.
- Component initialization (face clustering, OCR, modal system, code splitting, tauri, video analyzer) -> `server/core/components.py`.
- Shared app state (vector store, intent detector, saved search manager, source stores, trash DB) -> `server/core/state.py`.

## Router inventory (selected)
- `server/api/routers/intent.py`
- `server/api/routers/advanced_intent_search.py`
- `server/api/routers/saved_searches.py`
- `server/api/routers/stats.py`
- `server/api/routers/cache.py`
- `server/api/routers/system.py`
- `server/api/routers/pricing.py`
- `server/api/routers/ocr.py`
- `server/api/routers/dialogs.py`
- `server/api/routers/code_splitting.py`
- `server/api/routers/tauri.py`
- `server/api/routers/export.py`
- `server/api/routers/share.py`
- `server/api/routers/admin.py`
- `server/api/routers/images.py`
- `server/api/routers/faces_legacy.py`
- `server/api/routers/face_recognition.py`
- `server/api/routers/people_photo_association.py`
- `server/api/routers/video.py`
- `server/api/routers/video_analysis.py`
- `server/api/routers/image_analysis.py`
- `server/api/routers/favorites.py`
- `server/api/routers/bulk.py`
- `server/api/routers/indexing.py`
- `server/api/routers/tags.py`
- `server/api/routers/albums.py`
- `server/api/routers/locations.py`
- `server/api/routers/ratings.py`
- `server/api/routers/notes.py`
- `server/api/routers/stories.py`
- `server/api/routers/duplicates.py`
- `server/api/routers/transforms.py`
- `server/api/routers/photo_edits.py`
- `server/api/routers/edits.py`
- `server/api/routers/versions.py`
- `server/api/routers/ai_insights.py`
- `server/api/routers/collaborative_spaces.py`
- `server/api/routers/privacy.py`
- `server/api/routers/smart_collections.py`
- `server/api/routers/tag_filters.py`

## Parity check vs `gemini/fix-face-scan`
- Route inventory: 308 method+path pairs on both branches.
- OpenAPI path count: 265 on both branches.
- OpenAPI schema parity: identical after normalizing description whitespace.
- Differences observed: description whitespace only (no route or schema differences).

### How to rerun the parity check
Use the venv in this repo. The scripts below read the FastAPI app without running a server.

1) Dump route inventory + OpenAPI for current branch:
```
PHOTOSEARCH_TEST_MODE=1 PHOTOSEARCH_BASE_DIR=/tmp/ps_refactor_test \
  .venv/bin/python - <<'PY'
import hashlib
import json
from fastapi.routing import APIRoute
from server.main import app

routes = []
for r in app.routes:
    if isinstance(r, APIRoute):
        methods = sorted([m for m in r.methods if m not in {"HEAD", "OPTIONS"}])
        routes.append({"path": r.path, "name": r.name, "methods": methods})

routes_sorted = sorted(routes, key=lambda x: (x["path"], ",".join(x["methods"])))
openapi = app.openapi()
openapi_json = json.dumps(openapi, sort_keys=True)
openapi_hash = hashlib.sha256(openapi_json.encode("utf-8")).hexdigest()

with open('/tmp/ps_routes_refactor.json', 'w', encoding='utf-8') as f:
    json.dump(routes_sorted, f, indent=2)
with open('/tmp/ps_openapi_refactor_full.json', 'w', encoding='utf-8') as f:
    json.dump(openapi, f, indent=2, sort_keys=True)

print(len(routes_sorted), len(openapi.get('paths', {})), openapi_hash)
PY
```

2) Check out a `gemini/fix-face-scan` worktree and dump the same:
```
git worktree add /tmp/photosearch_gemini gemini/fix-face-scan
PHOTOSEARCH_TEST_MODE=1 PHOTOSEARCH_BASE_DIR=/tmp/ps_gemini_test \
  /Users/pranay/Projects/photosearch_experiment/.venv/bin/python - <<'PY'
import hashlib
import json
from fastapi.routing import APIRoute
from server.main import app

routes = []
for r in app.routes:
    if isinstance(r, APIRoute):
        methods = sorted([m for m in r.methods if m not in {"HEAD", "OPTIONS"}])
        routes.append({"path": r.path, "name": r.name, "methods": methods})

routes_sorted = sorted(routes, key=lambda x: (x["path"], ",".join(x["methods"])))
openapi = app.openapi()
openapi_json = json.dumps(openapi, sort_keys=True)
openapi_hash = hashlib.sha256(openapi_json.encode("utf-8")).hexdigest()

with open('/tmp/ps_routes_gemini.json', 'w', encoding='utf-8') as f:
    json.dump(routes_sorted, f, indent=2)
with open('/tmp/ps_openapi_gemini_full.json', 'w', encoding='utf-8') as f:
    json.dump(openapi, f, indent=2, sort_keys=True)

print(len(routes_sorted), len(openapi.get('paths', {})), openapi_hash)
PY
```

3) Compare:
```
python3 - <<'PY'
import json

with open('/tmp/ps_routes_refactor.json', 'r', encoding='utf-8') as f:
    ref = json.load(f)
with open('/tmp/ps_routes_gemini.json', 'r', encoding='utf-8') as f:
    gem = json.load(f)

def to_set(items):
    out = set()
    for item in items:
        for m in item['methods']:
            out.add((m, item['path']))
    return out

ref_set = to_set(ref)
gem_set = to_set(gem)
print("missing", sorted(gem_set - ref_set))
print("extra", sorted(ref_set - gem_set))

with open('/tmp/ps_openapi_refactor_full.json', 'r', encoding='utf-8') as f:
    ref_open = json.load(f)
with open('/tmp/ps_openapi_gemini_full.json', 'r', encoding='utf-8') as f:
    gem_open = json.load(f)

def normalize(obj, key=None):
    if isinstance(obj, dict):
        return {k: normalize(v, k) for k, v in obj.items()}
    if isinstance(obj, list):
        return [normalize(v, key) for v in obj]
    if isinstance(obj, str) and key == 'description':
        return " ".join(obj.split())
    return obj

print("openapi_equal_after_description_norm", normalize(ref_open) == normalize(gem_open))
PY
```

## Notes
- OCR warnings appear if OCR dependencies are not installed. This does not affect route inventory or OpenAPI output.
- Face/insight models may download on first import in a clean worktree.

## Current state of `server/main.py`
- No endpoint bodies remain in `server/main.py`.
- `server/main.py` composes routers, sets up middleware, and exposes shared globals and helpers.
