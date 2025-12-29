# Face Validation Notes (2025-12-27)

## What Was Done
- Fixed signed thumbnail URL caching to use the API-owned caches (testable reset hooks).
- Ran backend tests with existing `.venv` (140 passed).
- Ran UI tests with `pnpm test:run` (25 passed).
- Ran UI lint (`pnpm exec eslint "src/**/*.{ts,tsx}"`) with no errors.
- Ran face schema migrations (already at v6, no changes applied).
- Confirmed both servers are running via `./scripts/dev-status.sh`.

## Findings (InsightFace and Fallbacks)
- Primary detection and embeddings use InsightFace (buffalo_l) via `src/face_backends.py` and `src/face_embeddings.py`.
- Detection fallbacks are implemented: MediaPipe, Ultralytics YOLO, and a Remote HTTP API backend.
- Embedding fallbacks are implemented: CLIP (SentenceTransformers) and a Remote HTTP embedding backend.
- Fallback selection is controlled by config/env in `server/config.py`:
  - `FACE_BACKENDS`, `FACE_YOLO_WEIGHTS`, `FACE_REMOTE_DETECT_URL`
  - `FACE_EMBEDDING_BACKENDS`, `FACE_CLIP_EMBEDDING_MODEL`, `FACE_REMOTE_EMBEDDING_URL`
- Temporal constraints are now enforced in natural-language face searches using `photo_metadata.db` timestamps.

## Remaining Work
- See `FACE_TODOS.md` for the remaining tasks, including hosted provider adapters,
  embedding compatibility gating + tests, and README updates for fallback configs.

## Latest Validation (local run)
- Ran `./.venv/bin/python -m pytest server/tests/test_face_attribute_query.py server/tests/test_face_attribute_query_api.py server/tests/test_face_clustering_db.py server/tests/test_faces_attributes_api.py -q` (8 passed).
- Ran `./.venv/bin/python -m pytest server/tests/test_natural_language_search_api.py tests/test_natural_language_search.py -q` (29 passed).
- Ran `pnpm exec eslint "src/**/*.{ts,tsx}" 2>&1 | tail -n 30` with no lint output.
- Ran `./.venv/bin/python -m pytest server/tests/test_natural_language_search_db.py -q` (1 passed).
- Natural-language search now orders results by match count, then face count.
- Ran `./.venv/bin/python -m pytest server/tests/test_natural_language_search_api.py -q` (2 passed).
- Ran `./.venv/bin/python server/face_schema_migrations.py face_clusters.db` (already at schema v8).
- Confirmed both servers are running via `./scripts/dev-status.sh` (backend 8000, frontend 5173).

## Latest Validation (2025-12-28)
- Ran `node ./node_modules/eslint/bin/eslint.js "src/**/*.{ts,tsx}" --cache --cache-location .eslintcache -f json -o /tmp/eslint.json` in `ui` (0 errors).
- `pnpm exec eslint "src/**/*.{ts,tsx}" 2>&1 | tail -n 30` exceeds 10 minutes in this environment; ESLint results verified via cached run instead.

## Latest Integration (2025-12-29)
- Routed `/analytics/faces` to `/faces/advanced`, `/analytics/duplicates` to `/duplicates`, and `/analytics/albums` to `/albums`.
- Added `/duplicates` route and ActionsPod entry.
- Rewired OCR panel to `/ocr/*` endpoints with basic OCR support (no region geometry).
- Added optional OCR language support in `server/api/routers/ocr.py` and `server/models/schemas/ocr.py`.
- Removed legacy advanced panels that were unlinked from routes to eliminate dead UI modules.
- Added `/api/faces/backends/status` and surfaced backend/embedding status + fallback warnings in People UI.

## Latest UI Exposure (2025-12-30)
- Added a Power Search entry in People to surface `AdvancedFaceSearch` (natural language, temporal, similarity).
- Redirected `/faces/advanced` to `/people` so the advanced entry point lands on the fully functional face UI.

## Latest UI/Logic Fixes (2025-12-29)
- Fixed Similar Face Search empty-state logic to show "No Similar Faces Found" only after a search.
- Updated `NON_FACE_TODOS.md` to reflect resolved lint issues (no non-face lint debt pending).

## Latest Validation (2025-12-29)
- Ran `pnpm -C ui exec tsc -b --pretty false` (success).
- Ran `pnpm -C ui test:run` (26 tests passed).
- Ran `./.venv/bin/pytest server/tests/test_face_*.py -q` (27 passed).
- Ran `./.venv/bin/ruff check .` (All checks passed).
- Ran `pnpm exec eslint "src/**/*.{ts,tsx}" 2>&1 | tail -n 30` in `ui` (no output).
- Confirmed both servers are running via `./scripts/dev-status.sh` (backend 8000, frontend 5173).
- Verified only `.venv` exists; no extra/broken venv folders detected.
