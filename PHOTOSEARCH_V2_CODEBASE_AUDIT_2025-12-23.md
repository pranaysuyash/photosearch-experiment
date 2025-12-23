# PhotoSearch v2 — Codebase Audit (Evidence-Driven)

**Date:** 2025-12-23
**Workspace:** `/Users/pranay/Projects/photosearch_experiment`
**Primary Metric:** Backend capability utilization ("Hidden Genius" P0)

---

## What this report is

This audit focuses on **shipping value already present in the backend** by measuring and improving **frontend utilization of backend endpoints** (the “Hidden Genius” problem), while also covering key correctness, performance, and security risks discovered during evidence collection.

All findings are backed by concrete evidence references (`file:line` or generated artifacts under `audit_artifacts/`).

---

## Evidence & artifacts generated

These files were generated during discovery and are intended to be treated as appendices / reproducible evidence:

- `audit_artifacts/backend_endpoint_inventory.md` — full endpoint inventory with usage mapping.
- `audit_artifacts/backend_endpoint_inventory_stats.txt` — utilization summary.
- `audit_artifacts/backend_endpoints_unused_api_only.txt` — unused `/api*` endpoints (highest ROI for surfacing).
- `audit_artifacts/frontend_endpoints_called_count.txt` — frontend endpoint references count.
- `audit_artifacts/ui-build.txt` — production build output (chunk sizes + warnings).
- `audit_artifacts/bundle-report.html` — **asset-size bundle report** (fallback; sourcemap analyzers failed).

---

## Executive summary (P0-driven)

### Backend capability utilization (P0 metric)

- **Total backend endpoints:** 325
- **Matched as used by frontend:** 205
- **Unused by frontend:** 120
- **Frontend unique endpoint references captured:** 242

Evidence:

- `audit_artifacts/backend_endpoint_inventory_stats.txt` (generated):
  - `Total endpoints: 325`
  - `Used by frontend: 205`
  - `Unused by frontend: 120`
  - `Unique frontend evidence paths captured: 112`
- `audit_artifacts/frontend_endpoints_called_count.txt`: `242`

### The “Hidden Genius” list (highest ROI)

There are **11 unused `/api*` endpoints** that represent **user-facing power features** (face workflows, cache management, advanced scan/analytics) that exist server-side but are not surfaced in the UI.

Evidence: `audit_artifacts/backend_endpoints_unused_api_only.txt`

---

## Key findings & recommendations

### P0 — Hidden Genius: surface unused high-value endpoints

#### Finding P0.1 — Face workflows exist server-side but are not fully surfaced

Unused endpoints include:

- `GET /api/faces/clusters/{cluster_id}/photos` (returns photos + face confidence per cluster)
- `GET /api/faces/crop/{face_id}` (face thumbnails / crops)
- `POST /api/faces/{face_id}/assign` (manual correction)
- `POST /api/faces/{face_id}/create-person` (promote unidentified face into a person)
- `GET /api/people/{person_id}/analytics` (per-person insights)

Evidence:

- Unused list: `audit_artifacts/backend_endpoints_unused_api_only.txt`
- Cluster photos endpoint behavior: `server/api/routers/face_recognition.py:402` (`@router.get("/api/faces/clusters/{cluster_id}/photos")`)
- Face crop endpoint: `server/api/routers/face_recognition.py:726` (`@router.get("/api/faces/crop/{face_id}")`)
- Assign face endpoint: `server/api/routers/face_recognition.py:619` (`@router.post("/api/faces/{face_id}/assign")`)
- Create person endpoint: `server/api/routers/face_recognition.py:652` (`@router.post("/api/faces/{face_id}/create-person")`)
- Person analytics endpoint: `server/api/routers/face_recognition.py:905` (`@router.get("/api/people/{person_id}/analytics")`)

Impact:

- Users can’t perform the most valuable “face product loop”: **review → correct → name → browse photos per person → see analytics**.
- This directly undercuts “Smart Search” credibility (people intent) and reduces retention.

Smallest viable fix (UI surfacing plan):

1. In the People/Face UI, add a “Photos” tab that calls `GET /api/faces/clusters/{cluster_id}/photos` and renders results.
2. Use `GET /api/faces/crop/{face_id}` to show face thumbnails in review lists.
3. Add “Assign to person…” and “Create person…” actions in the Unidentified/Low-confidence face review panel.
4. Add a lightweight “Insights” section in Person detail that calls `GET /api/people/{person_id}/analytics`.

Acceptance criteria:

- A user can open a person and see **photos for that person** sourced from `GET /api/faces/clusters/{cluster_id}/photos`.
- Unidentified faces can be assigned or promoted, and the UI reflects the updated person membership.
- Person detail page shows analytics payload without errors when face recognition is enabled.

Rollback plan:

- Feature flag the new UI actions (or hide behind an “Advanced” toggle). Roll back by disabling the flag and leaving endpoints intact.

Effort sizing:

- **M (2–4 days)** for UI integration + basic UX + error handling; **S** if minimal UI only.

---

#### Finding P0.2 — Advanced “scan directory” and “comprehensive stats” exist but are not reachable

Unused endpoints include:

- `POST /api/advanced/scan-directory` (kicks off background jobs for faces/duplicates/OCR)
- `GET /api/advanced/comprehensive-stats` (feature stats + library stats)

Evidence:

- Unused list: `audit_artifacts/backend_endpoints_unused_api_only.txt`
- Implementation:
  - `server/main_advanced_features.py:197` (`@app.post("/api/advanced/scan-directory")`)
  - `server/main_advanced_features.py:313` (`@app.get("/api/advanced/comprehensive-stats")`)

Impact:

- You have a “one-click power user workflow” implemented, but users can’t discover or use it.

Smallest viable fix:

- Add a Settings → Advanced page section:
  - Directory picker + “Run comprehensive scan” (calls `/api/advanced/scan-directory`).
  - A “Stats” panel (calls `/api/advanced/comprehensive-stats`).

Acceptance criteria:

- Triggering a scan returns `job_ids` and UI displays “started” state.
- Stats panel renders at least `library_stats` and `active_jobs` fields.

Rollback plan:

- UI-only rollback: remove the settings panel; endpoints remain.

Effort sizing:

- **S (0.5–1.5 days)**.

---

#### Finding P0.3 — Cache clear endpoint exists but is not exposed

Unused endpoint:

- `POST /api/cache/clear`

Evidence:

- Unused list: `audit_artifacts/backend_endpoints_unused_api_only.txt`
- Implementation: `server/api/routers/system.py:37` (`@router.post("/api/cache/clear")`)

Impact:

- Debugging/performance support is harder (especially for Tauri/offline flows).

Smallest viable fix:

- Add Settings → Diagnostics → “Clear cache” button.

Acceptance criteria:

- Clicking button calls endpoint and shows success message.

Rollback plan:

- Remove button.

Effort sizing:

- **XS (1–2 hours)**.

---

### P0 — Smart Search coherence: auto-routing vs manual mode toggles

#### Finding P0.4 — The UI simultaneously auto-switches search mode and offers manual mode selection

Evidence:

- Auto-switching behavior: `ui/src/contexts/PhotoSearchContext.tsx:165–225` (detectSearchMode + `setSearchMode(detectedMode)`)
  - Example: `ui/src/contexts/PhotoSearchContext.tsx:222–223` logs and sets detected mode.
- Manual mode dropdown sets mode directly: `ui/src/components/layout/DynamicNotchSearch.tsx:417` (`setSearchMode(item.id as any)`)

Impact:

- Users may experience mode “flapping” (manual selection overridden by auto-detection).
- This is a direct product contradiction if the goal is “Smart Search auto-routing”.

Smallest viable fix:

- Introduce a single explicit concept: **Search Mode = Auto | Manual**.
  - Default: Auto.
  - If user chooses a manual mode from the dropdown, set a “manual override” flag and _stop auto-switching_ until cleared.
  - Add “Auto” as a dropdown option to re-enable.

Acceptance criteria:

- Selecting a manual mode remains stable across query edits.
- Re-enabling Auto resumes mode detection.

Rollback plan:

- Keep old behavior behind a feature flag (or revert the override flag logic).

Effort sizing:

- **S (0.5–1.5 days)**.

---

### P1 — Match explanations exist but need consistent UI surfacing

#### Finding P1.1 — Backend generates match explanations; frontend types them; UX consistency is the gap

Evidence:

- Metadata explanation generation: `server/api/routers/search.py:347` (`generate_metadata_match_explanation`)
- Hybrid explanation generation: `server/api/routers/search.py:586` (`generate_hybrid_match_explanation`)
- Semantic explanation generation: `server/api/routers/semantic_search.py:179` (`generate_semantic_match_explanation`)
- Frontend typing: `ui/src/api.ts:84–95` (`MatchExplanation`, `matchExplanation?: MatchExplanation`)

Impact:

- Explanations are a differentiator (trust + transparency) but can feel invisible if not surfaced consistently.

Smallest viable fix:

- Standardize a “Why this matched” UI component used by all result cards.
- Show explanation when present; show a consistent fallback (“Matched by filename/date/visual similarity…”) when absent.

Acceptance criteria:

- For a non-empty query, at least one mode shows `matchExplanation` in the UI.

Rollback plan:

- Component-only rollback.

Effort sizing:

- **S (1–2 days)**.

---

### P1 — Performance: single oversized main chunk + broken code-splitting

#### Finding P1.2 — `index-*.js` is ~1.55MB (gzip 443KB) and IntentRecognition chunking is blocked

Evidence:

- Build output: `audit_artifacts/ui-build.txt`:
  - `dist/assets/index-*.js 1,547.52 kB │ gzip: 443.15 kB`
  - Warning: `IntentRecognition.tsx` both dynamic and static import → prevents code splitting.
- Code evidence:
  - Dynamic import: `ui/src/router/MainRouter.tsx:41` (`lazy(() => import('../components/search/IntentRecognition'))`)
  - Static import: `ui/src/components/search/EnhancedSearchUI.tsx:19` (`import { IntentRecognition } from './IntentRecognition';`)
  - Static import: `ui/src/pages/Search.tsx:9` (`import IntentRecognition from '../components/search/IntentRecognition';`)

Smallest viable fix:

- Pick one approach:
  - Either keep IntentRecognition always-on (remove lazy import), or
  - Make it truly lazy: remove static imports and route all usage through the lazy-loaded component.

Acceptance criteria:

- Vite build warning about mixed static/dynamic import disappears.
- App behavior unchanged.

Rollback plan:

- Revert imports.

Effort sizing:

- **XS/S (1–4 hours)**.

Bundle appendix:

- `audit_artifacts/bundle-report.html` provides an **asset inventory** fallback. Module-level treemap analysis is currently blocked by invalid sourcemaps (“generated column Infinity”).

---

### P1 — Tauri security: CSP disabled

#### Finding P1.3 — Tauri CSP is explicitly null

Evidence:

- `src-tauri/tauri.conf.json:26` → `"csp": null`

Impact:

- Disabling CSP materially increases risk of XSS-style payloads becoming RCE-adjacent inside a desktop shell.

Smallest viable fix:

- Set a restrictive CSP appropriate for the shipped UI:
  - allow `self` for scripts/styles
  - allow images from `self`, `data:`, and any required file/custom protocols
  - if you need inline styles/scripts, prefer nonces/hashes rather than `unsafe-inline`

Acceptance criteria:

- Tauri app runs with CSP enabled and the UI loads.
- No CSP-related console errors for normal operation.

Rollback plan:

- Keep CSP change isolated to config; revert config if it blocks release.

Effort sizing:

- **S (0.5–2 days)** depending on required allowances.

---

### P2 — API ergonomics: duplicated intent endpoints with inconsistent prefix

#### Finding P2.1 — Intent detection exists as both `/api/intent/detect` and `/intent/detect`

Evidence:

- `server/api/routers/intent.py:9` → `@router.get("/api/intent/detect")`
- `server/api/routers/intent.py:37` → `@router.get("/intent/detect")`

Impact:

- Harder client implementation and documentation; increases drift risk (payload shapes differ between the two handlers).

Smallest viable fix:

- Pick one canonical path (recommend `/api/intent/detect`) and treat the other as a backwards-compatible alias.
- Ensure both endpoints return the same response schema (or add a `version` field and document differences).

Acceptance criteria:

- Frontend calls only one canonical endpoint.
- OpenAPI schema documents one preferred endpoint.

Rollback plan:

- Keep both endpoints operational; rollback by switching frontend to the prior path.

Effort sizing:

- **S (0.5–1 day)**.

---

### P2 — Tauri build reliability: config uses npm while repo uses pnpm

#### Finding P2.2 — `src-tauri/tauri.conf.json` hardcodes `npm run` for UI

Evidence:

- `src-tauri/tauri.conf.json:9` → `beforeDevCommand": "cd ui && npm run dev"`
- `src-tauri/tauri.conf.json:10` → `beforeBuildCommand": "cd ui && npm run build"`

Impact:

- Tauri dev/build may fail or use the wrong lockfile semantics depending on environment.

Smallest viable fix:

- Update commands to `pnpm` to match the repo’s workflow.

Acceptance criteria:

- Tauri dev mode successfully starts UI and backend on a clean machine following `README.md`.

Rollback plan:

- Revert config changes.

Effort sizing:

- **XS (15–45 minutes)**.

---

## Test/build signals captured

Evidence artifacts:

- TypeScript check: `audit_artifacts/typescript-exitcode.txt` = `0` (and `audit_artifacts/typescript-errors.txt` empty)
- UI production build: `audit_artifacts/ui-build-exitcode.txt` = `0` (see `audit_artifacts/ui-build.txt`)
- Backend tests (pytest): **partial verification completed** (see notes below)

Notes:

- Pytest initially failed during collection due to missing imports (`BaseModel`, typing names) in `server/api/routers/face_recognition.py`. This was fixed by adding the missing imports.
- Some tests referenced a legacy import path (`src.notes_db`). A compatibility shim was added at `src/notes_db.py` to re-export `NotesDB` from `server.notes_db`.

Verified in this session:

- UI tests: `pnpm test:run` exit code `0` (per terminal history)
- Backend feature/integration subset: `tests/test_features_unit.py` + `tests/test_integration.py` → **37 passed**

Not yet re-verified in this session:

- Full backend pytest suite (`python -m pytest`) — the most recent full run attempt was canceled before completion, so the audit does **not** claim full-green backend tests at this time.

---

## Appendix pointers

- Endpoint inventory (authoritative): `audit_artifacts/backend_endpoint_inventory.md`
- Utilization stats: `audit_artifacts/backend_endpoint_inventory_stats.txt`
- Unused `/api*` endpoints list: `audit_artifacts/backend_endpoints_unused_api_only.txt`
- Bundle report (asset sizes): `audit_artifacts/bundle-report.html`
