# Suggested Issues & Implementation Backlog (for GitHub or project tracker)

Each suggested issue includes a short description, approximate estimate, priority, and possible labels.

1. Path sandboxing & security for image endpoints

   - Description: Ensure `GET /image/thumbnail` and any file serving route only serves files within `settings.MEDIA_DIR`. Use `pathlib.Path.resolve()` and refuse requests outside allowed root.
   - Priority: Critical
   - Estimate: 0.5–1d
   - Labels: security, bug, server

2. Add `mode` param to search API and UI toggle

   - Description: Backend accepts `?mode=metadata|semantic|hybrid` and `ui` adds segmented toggle with tooltips and placeholder examples. Create a `searchSemantic` helper for the UI.
   - Priority: High
   - Estimate: 2–3d
   - Labels: front-end, feature, api

3. Implement async `POST /scan` & jobs API

   - Description: Make `/scan` return `job_id` when `?async=true`. Add `GET /jobs/{id}` for progress and state. Create a job tray UI to show progress and allow pause/cancel.
   - Priority: High
   - Estimate: 3–5d
   - Labels: feature, backend, ui, performance

4. Device detection & configuration for embedding model

   - Description: Auto-detect MPS/CPU/CUDA on startup and expose via `settings`. Provide tips in UI settings or an advanced panel for model device.
   - Priority: Medium
   - Estimate: 0.5d
   - Labels: backend, config

5. Embedding ID mapping & deduping

   - Description: Use hashed ID for vector store entries based on `sha256(file_path + file_hash + model_version)`. Add a table for mapping in metadata DB.
   - Priority: Medium
   - Estimate: 1–2d
   - Labels: backend, db

6. Job backlog async worker (local-first approach)

   - Description: Implement a local job queue with `asyncio` or `threading` for background indexing. For CI dev, provide a wrapper to run Celery/RQ if needed.
   - Priority: Medium
   - Estimate: 3–4d
   - Labels: backend, infra

7. Tauri packaging (Phase 2)

   - Description: Setup Tauri using sidecar method for bundling Python and package for macOS. Implement permissions & file access signing for mac.
   - Priority: Low (deferred)
   - Estimate: 2–4 weeks
   - Labels: desktop, tauri

8. UI Enhancements: Photo detail, duplicates, and batch operations

   - Description: Implement detail view with metadata, version history, duplicate grouping and batch actions with undo.
   - Priority: Medium
   - Estimate: 2–3 weeks
   - Labels: front-end, feature

9. Testing & CI: Add integration tests for API endpoints and UI flows

   - Description: Add `pytest` tests for endpoints and Playwright for core UI flows (toggle, scan, search). Add GitHub Actions skeleton.
   - Priority: Medium
   - Estimate: 3–5d
   - Labels: testing, ci

10. Observability & monitoring
    - Description: Add structured logs and optional telemetry; add simple metrics and error reporting hooks.
    - Priority: Low
    - Estimate: 1–2d
    - Labels: infra, ops

Use these as GitHub Issues to break down the work, assign owners, and track progress.
