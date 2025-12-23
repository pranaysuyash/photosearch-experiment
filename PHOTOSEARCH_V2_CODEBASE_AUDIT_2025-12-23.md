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
- `audit_artifacts/merge_suggestions_evidence_20251223_161343.txt` — evidence that Merge Suggestions exists in code but is not imported by any route/page.
- `audit_artifacts/merge_suggestions_wired_20251223_163850.txt` — evidence that Merge Suggestions is now wired into the People page (reachable via UI).
- `audit_artifacts/cluster_photos_wired_fix_20251223_165102.txt` — evidence that PersonDetail calls `/api/faces/clusters/{cluster_id}/photos` and the backend route exists.
- `audit_artifacts/cache_clear_wired_20251223_171259.txt` — evidence that Performance UI calls the correct backend cache clear endpoint (`/api/cache/clear`).
- `audit_artifacts/scan_directory_wired_20251223_185027.txt` — evidence that Advanced Features UI calls `POST /api/advanced/scan-directory`.
- `audit_artifacts/comprehensive_stats_wired_20251223_200847.txt` — evidence that Advanced Features UI calls `GET /api/advanced/comprehensive-stats`.
- `audit_artifacts/face_loop_and_person_analytics_wired_20251223_202105.txt` — evidence that Unidentified Faces + Person Detail now call assign/create-person/crop/analytics endpoints.
- `audit_artifacts/ui-build_20251223_164126.txt` — fresh UI build output after wiring Merge Suggestions (exit code in `audit_artifacts/ui-build_20251223_164126_exitcode.txt`).
- `audit_artifacts/ui-build_20251223_175128.txt` — fresh UI build output after exposing scan-directory (exit code in `audit_artifacts/ui-build_20251223_175128.exitcode.txt`).
- `audit_artifacts/ui-build_20251223_201045.txt` — fresh UI build output after exposing comprehensive stats (exit code in `audit_artifacts/ui-build_20251223_201045.exitcode.txt`).
- `audit_artifacts/ui-build_20251223_202544.txt` — fresh UI build output after wiring face correction loop + analytics (exit code in `audit_artifacts/ui-build_20251223_202544.exitcode.txt`).
- `audit_artifacts/face_scan_single_status_person_wired_20251223_221900.txt` — evidence that People UI now calls person-name lookup + scan-single + scan-status endpoints.
- `audit_artifacts/ui_build_latest.txt` — latest production UI build output after surfacing the remaining face endpoints (exit code in `audit_artifacts/ui_build_latest.exitcode.txt`).

---

## Executive summary (P0-driven)

### Backend capability utilization (P0 metric)

- **Total backend endpoints:** 325
- **Matched as used by frontend:** 216
- **Unused by frontend:** 109
- **Frontend unique endpoint references captured:** 266

Evidence:

- `audit_artifacts/backend_endpoint_inventory_stats.txt` (generated):
  - `Total endpoints: 325`
  - `Used by frontend: 216`
  - `Unused by frontend: 109`
  - `Unique frontend evidence paths captured: 116`
- `audit_artifacts/frontend_endpoints_called_count.txt`: `266`

### The “Hidden Genius” list (highest ROI)

There are **0 unused `/api*` endpoints** remaining on the high-ROI “Hidden Genius” list — the last three face scan/name endpoints have now been surfaced.

Note: the utilization metric is primarily based on **frontend references** (e.g., `ui/src/api.ts`) and may count features as “used” even when they are **not reachable from any UI entry point**. Merge Suggestions is one concrete example (see Finding P0.1b).

Evidence:

- `audit_artifacts/backend_endpoints_unused_api_only.txt` (now empty)
- Wiring proof: `audit_artifacts/face_scan_single_status_person_wired_20251223_221900.txt`

---

## Key findings & recommendations

### P0 — Hidden Genius: surface unused high-value endpoints

#### Finding P0.1 — Face correction loop + analytics are now surfaced (closed)

The high-value face correction loop endpoints are now wired through the UI:

- `POST /api/faces/{face_id}/assign`
- `POST /api/faces/{face_id}/create-person`
- `GET /api/faces/crop/{face_id}`
- `GET /api/people/{person_id}/analytics`

Evidence:

- Wiring: `audit_artifacts/face_loop_and_person_analytics_wired_20251223_202105.txt`
  - Frontend call sites:
    - `ui/src/pages/UnidentifiedFaces.tsx:79` (`/api/faces/${faceId}/assign`)
    - `ui/src/pages/UnidentifiedFaces.tsx:90` (`/api/faces/${faceId}/create-person`)
    - `ui/src/pages/UnidentifiedFaces.tsx:102` (`/api/faces/crop/${faceId}`)
    - `ui/src/pages/PersonDetail.tsx:128` (`/api/people/${encodeURIComponent(clusterId)}/analytics`)
  - Backend routes:
    - `server/api/routers/face_recognition.py:735` (`@router.post("/api/faces/{face_id}/assign")`)
    - `server/api/routers/face_recognition.py:772` (`@router.post("/api/faces/{face_id}/create-person")`)
    - `server/api/routers/face_recognition.py:855` (`@router.get("/api/faces/crop/{face_id}")`)
    - `server/api/routers/face_recognition.py:1039` (`@router.get("/api/people/{person_id}/analytics")`)
- Build verification: `audit_artifacts/ui-build_20251223_202544.txt` (exit code in `audit_artifacts/ui-build_20251223_202544.exitcode.txt`)

Update:

- Cluster photo browsing is now wired through the UI by `PersonDetail` calling the canonical endpoint:
  - Backend route: `server/api/routers/face_recognition.py:460` (`@router.get("/api/faces/clusters/{cluster_id}/photos")`)
  - UI call site: `ui/src/pages/PersonDetail.tsx:81`
  - Evidence artifact: `audit_artifacts/cluster_photos_wired_fix_20251223_165102.txt`

Impact:

- Users still can’t perform the full “face product loop”: **review → correct → name → (optionally browse) → see analytics**.
- This directly undercuts “Smart Search” credibility (people intent) and reduces retention.

Smallest viable fix (UI surfacing plan):

Status:

- ✅ Face thumbnails/crops are now pulled from the canonical crop endpoint.
- ✅ Unidentified faces can be assigned to an existing person or promoted to a new person.
- ✅ Person detail now exposes per-person analytics.

Update:

- ✅ The remaining face scan/status/name endpoints are now exposed via a People → “Face scan & lookup tools” panel.
- Evidence: `audit_artifacts/face_scan_single_status_person_wired_20251223_221900.txt`
- Build verification: `audit_artifacts/ui_build_latest.txt` (exit code in `audit_artifacts/ui_build_latest.exitcode.txt`)

---

#### Finding P0.1b — Merge Suggestions exists end-to-end, but appears not reachable from any UI route/page

What exists today:

- Backend endpoints:
  - `GET /api/faces/clusters/merge-suggestions`: `server/api/routers/face_recognition.py:1694`
  - `POST /api/faces/clusters/merge-suggestions/dismiss`: `server/api/routers/face_recognition.py:1724`
- Backend DB logic:
  - `server/face_clustering_db.py:1862` (`get_merge_suggestions`)
  - `server/face_clustering_db.py:2002` (`dismiss_merge_suggestion`)
- Frontend API client methods:
  - `ui/src/api.ts:1981–1992` (`getMergeSuggestions`, `dismissMergeSuggestion`)
- UI component implementation:
  - `ui/src/components/people/MergeSuggestions.tsx:1–90` (component + fetch/dismiss/merge flows)

Update:

- `MergeSuggestions` is now wired into the People page as a tab, making it reachable from the UI.
  - UI wiring: `ui/src/pages/People.tsx:28` (import), `ui/src/pages/People.tsx:420` (render)
  - Evidence artifact: `audit_artifacts/merge_suggestions_wired_20251223_163850.txt`

Impact:

- This is a high-ROI “people hygiene” feature (merge duplicates) that directly improves People quality and reduces user frustration from duplicate clusters.

Smallest viable fix (UI surfacing plan):

1. Add a People → “Merge Suggestions” tab/section that renders `MergeSuggestions`.
2. Link to it from the primary People/Clusters UI (e.g., a small badge “Potential duplicates”).

Acceptance criteria:

- A user can navigate to Merge Suggestions from the People UI without deep-linking.
- The screen loads suggestions via `GET /api/faces/clusters/merge-suggestions` and supports Dismiss via the POST endpoint.

Rollback plan:

- UI-only rollback: remove the tab/entry point; keep endpoints and component available for later.

Effort sizing:

- **XS/S (1–6 hours)** depending on routing/nav wiring.

---

#### Finding P0.2 — Advanced scan directory + comprehensive stats are now reachable

Update:

- `GET /api/advanced/comprehensive-stats` is now exposed via the Advanced Features page.

Evidence:

- Unused list: `audit_artifacts/backend_endpoints_unused_api_only.txt`
- Implementation:
  - `server/main_advanced_features.py:197` (`@app.post("/api/advanced/scan-directory")`)
  - `server/main_advanced_features.py:313` (`@app.get("/api/advanced/comprehensive-stats")`)

UI exposure evidence:

- UI call site: `ui/src/pages/AdvancedFeaturesPage.tsx:232`
- Evidence artifact: `audit_artifacts/comprehensive_stats_wired_20251223_200847.txt`

Update:

- `POST /api/advanced/scan-directory` is now exposed in the UI via a “Comprehensive directory scan” panel on the Advanced Features page.
  - UI call site: `ui/src/pages/AdvancedFeaturesPage.tsx:202`
  - Evidence artifact: `audit_artifacts/scan_directory_wired_20251223_185027.txt`

Impact:

- You have a “one-click power user workflow” implemented, but users can’t discover or use it.

Smallest viable fix (remaining):

- Polish: collapse raw JSON behind a disclosure + add a "copy stats" button.

Acceptance criteria:

- Triggering a scan returns `job_ids` and UI displays “started” state.
- Stats panel renders at least `library_stats` and `active_jobs` fields.

Rollback plan:

- UI-only rollback: remove the settings panel; endpoints remain.

Effort sizing:

- **S (0.5–1.5 days)**.

---

#### Finding P0.3 — Cache clear endpoint is now exposed (and wiring was corrected)

Update:

- The backend endpoint exists and is now **called by the UI** via the Performance page.
- The frontend previously used a non-existent `/cache/clear` path; this was corrected to `/api/cache/clear`.

Evidence:

- Backend route: `server/api/routers/system.py:37` (`@router.post("/api/cache/clear")`)
- Frontend API call: `ui/src/api.ts:1477` (`apiClient.post('/api/cache/clear')`)
- UI entry point + button: `ui/src/pages/PerformanceDashboard.tsx:93` (`await api.clearCache()`)
- Route exposure: `ui/src/router/MainRouter.tsx:89` (`Route path='/performance'`)
- Navigation exposure: `ui/src/components/navigation/SidebarNavigation.tsx:45` (`href: '/performance'`)
- Evidence artifact: `audit_artifacts/cache_clear_wired_20251223_171259.txt`

Impact:

- Debugging/performance support is easier, and users have a deterministic “reset caches” escape hatch.

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

- Explanation generation implementations:
  - Metadata: `server/utils/search_explanations.py:1` (`generate_metadata_match_explanation`)
  - Hybrid: `server/utils/search_explanations.py:123` (`generate_hybrid_match_explanation`)
  - Semantic: `server/utils/search_explanations.py:202` (`generate_semantic_match_explanation`)
  - Routed usage examples:
    - Metadata/Hybrid in main search: `server/api/routers/search.py:525`, `server/api/routers/search.py:877`
    - Semantic in semantic search: `server/api/routers/semantic_search.py:179`
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
- Backend tests (pytest): **full verification completed** — `133 passed` (see evidence below)

Notes:

- Pytest initially failed during collection due to missing imports (`BaseModel`, typing names) in `server/api/routers/face_recognition.py`. This was fixed by adding the missing imports.
- Some tests referenced a legacy import path (`src.notes_db`). A compatibility shim was added at `src/notes_db.py` to re-export `NotesDB` from `server.notes_db`.

Verified in this session:

- UI tests: `pnpm test:run` exit code `0` (per terminal history)
- Backend full suite: `pytest` → **133 passed**
  - Evidence: `audit_artifacts/pytest_full_green_20251223_154836.txt`
- (Previously captured subset) Backend feature/integration subset: `tests/test_features_unit.py` + `tests/test_integration.py` → **37 passed**

Additional verification (watchdog runs, 2025-12-23):

- `server/tests/test_automatic_clustering.py` → **6 passed**
  - Evidence: `audit_artifacts/watchdog/server__tests__test_automatic_clustering.py.after_fix.txt`
- `test_people_endpoints.py` → **1 passed** (uvicorn subprocess integration)
  - Evidence: `audit_artifacts/watchdog/test_people_endpoints.py.after_fix.txt`

These were previously identified as failing/stalling under watchdog runs; fixes were applied to:

- `server/face_clustering_db.py` (robust embedding decoding + NULL-cluster filter)
  - Embedding decoding + cluster filtering: `server/face_clustering_db.py:2312–2415` (`find_similar_faces`)
- `server/main.py` (skip auto-scan/watcher in test mode; use runtime base dir for media)

Additional fixes required to reach full-green backend tests:

- Legacy compatibility endpoints (route shims) added to support older client/test paths (e.g. `/notes/{path}`, `/tags/add`, `/people/{path}`, `/locations/{path}`): `server/api/routers/legacy_compat.py`
- TestClient lifecycle robustness: `server/api/deps.py:get_state` now lazily builds AppState when lifespan was bypassed
- Search discoverability: `/search` now merges matches from notes/tags/locations/people-tags DBs so feature annotations are searchable without a full media scan: `server/api/routers/search.py`
- Versions semantics compatibility: `VersionStack` supports both `.versions` access and list-like behavior for legacy tests/clients: `server/photo_versions_db.py`
- Thumbnail rate limiting correctness: fixed undefined-state usage so 429s trigger as expected: `server/api/routers/images.py`

Notes on configuration:

- The full-suite run was executed with `PHOTOSEARCH_TEST_MODE=1` to keep tests deterministic and avoid heavyweight startup behaviors.

---

## Appendix pointers

- Endpoint inventory (authoritative): `audit_artifacts/backend_endpoint_inventory.md`
- Utilization stats: `audit_artifacts/backend_endpoint_inventory_stats.txt`
- Unused `/api*` endpoints list: `audit_artifacts/backend_endpoints_unused_api_only.txt`
- Bundle report (asset sizes): `audit_artifacts/bundle-report.html`
