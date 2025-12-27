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

## Remaining Work
- See `FACE_TODOS.md` for the remaining tasks, including hosted provider adapters,
  embedding compatibility gating + tests, and README updates for fallback configs.
