# Handoff for Review (Claude & Copilot)

**Status**: Phase 1 (Security & Toggles), Phase 2 (Async Scanning), and Phase 3 (Hybrid & Polish) are COMPLETE.

## 1. Completed High-Priority Items
The following items from the consolidated `AI_COLLABORATORS_REVIEW.md` and `TODO_ISSUES.md` have been implemented:

### A. Path Security (Critical)
- **Implemented**: Strict path validation in `server/main.py`.
- **Mechanism**: Use `pathlib.Path.resolve().is_relative_to(settings.BASE_DIR)`.
- **Endpoint**: `GET /image/thumbnail` now returns 403 for traversal attempts.

### B. Search Modes & Hybrid Logic (High)
- **Implemented**:
    - `GET /search?mode=metadata`: SQL-based search (default).
    - `GET /search?mode=semantic`: Vector-based search (LanceDB + CLIP).
    - `GET /search?mode=hybrid`: **[NEW]** Aggregates Metadata (exact/fuzzy) and Semantic results, prioritizing exact matches.
- **Frontend**: Added `SearchToggle` component (segmented control) in `ui/src/components/SearchToggle.tsx`.

### C. Async Scanning & Jobs (High)
- **Implemented**:
    - `POST /scan` now accepts `{ background: true }` and returns `{ job_id: "..." }`.
    - `GET /jobs/{id}` returns job status and progress.
    - In-memory `JobStore` implemented in `server/jobs.py` (Local-first, simpler than Redis).
- **Frontend**: `Spotlight.tsx` updated to poll for job status instead of blocking UI.

### D. SQLite Threading Fix
- **Fix**: Added `check_same_thread=False` to `server/metadata_search.py` to allow background worker threads to write to the SQLite DB.

## 2. Verification Status
- **Manual Verification**:
    - `curl` tests passed for all endpoints.
    - Path traversal verified blocked.
    - Async scan verified to complete successfully in background.
- **Automated Tests**:
    - Unit tests (`tests/`) are pending (see backlog).

## 3. Remaining / Deferred Items
The following items were deprioritized or deferred for future sprints:

1.  **Duplicate Detection**: `TODO #5` (Embedding ID dedup) was deferred.
2.  **First Run Modal**: Suggested by reviewers, but not implemented in this sprint (priority given to core functionality).
3.  **Tauri Migration**: Deferred as per original plan.

## 4. How to Run
1.  **Backend**: `.venv/bin/python -m uvicorn server.main:app --reload`
2.  **Frontend**: `npm run dev` (in `ui/` folder)

## 5. Artifacts Created
- `task.md`: Tasks breakdown.
- `implementation_plan.md`: Technical design.
- `walkthrough.md`: Verification logs.
