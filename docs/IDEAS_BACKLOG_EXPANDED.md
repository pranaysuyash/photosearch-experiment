# Expanded Ideas Backlog (Mapped to current codebase)

Source: consolidated from `old_project_docs/` content, `docs/IDEAS_FROM_OLD_PROJECT.md` Appendix, and current repository scan (Dec 9, 2025).

Purpose: capture every potential opportunity as a backlog item, annotate whether it's already implemented (in whole/part), and provide a recommended next step and priority.

How to use this file:

- Items with status `IMPLEMENTED` should be reviewed for completeness. Add tests / docs / UX polish.
- Items marked `PARTIAL` need follow-up: either complete implementation or refine UX/testing.
- Items marked `MISSING` are opportunities for new work.
- Use Priority (Quick Win, P0 - High Impact, P1 - Medium, P2 - Low) to triage into sprints.

---

## Legend

- Status: IMPLEMENTED / PARTIAL / MISSING
- Priority: Quick Win / P0 / P1 / P2 (based on impact/effort)

## High-Level Summary

- Quantity: ~120+ distinct opportunities found across old docs and audits.
- Implementation: A reasonable number are partially implemented or experimentally present (fast index experiments, UI components). Much of the offline/online dual-mode and desktop security/canonicalization work remains partial or is only in docs.

---

## Backlog (categories sorted topically)

### A. Core Search & Retrieval

1. Semantic / Hybrid search (CLIP-based) with natural language queries

   - Status: PARTIAL — The code has search & embedding experiments (vector store files, FAISS benchmarks), and semantic search API surfaces are present.
   - Priority: P0
   - Next step: Add a feature checklist and tests validating AI search quality; expose hybrid-mode toggle and saved search UI.
   - Source: `old_project_docs/FAST_INDEXES.md`, tests & experiments in repo.

2. Saved searches, search history, analytics & recent searches

   - Status: PARTIAL — Search history features are surfaced in docs and UI audits; saved searches API not fully integrated.
   - Priority: Quick Win
   - Next step: Implement `apiGetSaved`, `apiAddSaved` endpoints or UI to persist saved searches; add small UI and tests.
   - Source: `IDEAS_FROM_OLD_PROJECT.md`, `codex-review` audits.

3. Intent Recognition (12 intents, AI suggestions and badges)

   - Status: PARTIAL — Intent-first docs exist; code has SearchBar with suggestions but full intent system not complete.
   - Priority: P0
   - Next step: Implement a lightweight IntentRecognizer pipeline based on rules and optional ML tier; show badges in suggestions; add analytics to track accuracy.
   - Source: `old_project_docs/ENHANCED_SEARCH_INTENT_IMPLEMENTATION.md`.

4. Search caching (LRU cache + TTL + optional Redis for distributed deployments)

   - Status: PARTIAL — The cache manager is documented but not fully integrated across all search paths.
   - Priority: P1
   - Next step: Implement and instrument search caching; validate benefits with benchmarks.
   - Source: `old_project_docs/SEARCH_CACHING.md`.

5. Fast ANN indexes (FAISS / hnswlib / Annoy) with `fast` manager
   - Status: PARTIAL — There are benchmarks and vector store experiments (README, experiments/), and `requirements.txt` references. Index manager code seems to be proposed in docs.
   - Priority: P0
   - Next step: Stabilize the Index Manager, expose API endpoints (build/status/search) and integrate `fast_backend` selection logic; add test coverage.
   - Source: `old_project_docs/FAST_INDEXES.md`.

### B. Offline-first & Caching

6. Offline manifest & IndexedDB caching with manifest hash

   - Status: PARTIAL — Offline docs exist and show the manifest approach, but not fully integrated in UI.
   - Priority: P0
   - Next step: Implement demo_manifest generator, manifest loader, and IndexedDB hydrate process for `offline-first` grid rendering. Add offline-aware network detection and banner.
   - Source: `old_project_docs/OFFLINE_CAPABILITIES.md`, `OFFLINE_PHASE1_PROGRESS.md`.

7. Offline search (embedding cache, local CLIP option) and hybrid mode

   - Status: MISSING
   - Priority: P1
   - Next step: Keep indexing pipeline into a local cache, provide an optional model-in-browser (or Electron-bundled) capability for embedded semantics.
   - Source: `old_project_docs/OFFLINE_CAPABILITIES.md`.

8. Thumbnail resolver with offline fallback (cache → file → API → placeholder)
   - Status: PARTIAL — Many audit references and offline image loading docs exist; UI code still uses API-dependent thumbnails.
   - Priority: Quick Win
   - Next step: Implement a central thumbnail resolver; persist thumbnails, serve placeholder with skeletons during heavy loads.
   - Source: `old_project_docs/DIRECT_FILE_ACCESS_IMPLEMENTATION.md`, `OFFLINE_IMAGE_LOADING_SOLUTION.md`.

### C. Desktop / Electron (if applicable)

9. Secure file handling with custom protocols (photo-thumbnail://, photo-file://) and IPC allowlist

   - Status: MISSING/PARTIAL — Clear docs recommending this exist, including `preload.js` and CSP headers; repo may not have production Electron implementation yet.
   - Priority: P0 (High security impact)
   - Next step: Implement protocol handlers, preload IPC with zod validation, CSP enforcement, and dedicated file serving paths.
   - Source: `old_project_docs/DIRECT_FILE_ACCESS_IMPLEMENTATION.md`, `DESKTOP_APP_AUDIT.md`.

10. First-run experience: scan folder CTA, pre-scan counts, demo mode, and onboarding improvements

- Status: PARTIAL — UI audit notes describe it; some 'FirstRunModal' exists in codex reviews.
- Priority: Quick Win
- Next step: Add a more actionable empty-state with a Scan CTA and directory pick; present pre-scan counts and background job status.
- Source: `codex-review/first-run-audit.md`.

### D. Indexing, Jobs & Queue

11. Persistent job queue (file-backed or sqlite) with job center UI

- Status: PARTIAL — Jobs are referenced heavily in audits; the state modeling (job states) and executor plan exists in docs; UI job center not full.
- Priority: P0
- Next step: Implement executor worker and persistent job store (file or sqlite), job enqueue API, and job-detail UI (jobs drawer + logs). Add resumable jobs on restart.
- Source: `old_project_docs/server_refactor_unified_plan_starter_prs.md`, `codex-review` audit docs.

12. Re-index, OCR, face/trip detection tasks enqueued as jobs (non-blocking)

- Status: PARTIAL — Doc specs and UI suggestions exist; back-end features partly implemented as separate scripts.
- Priority: P1
- Next step: Integrate those work steps as queued jobs with job id and UI mapping.
- Source: `codex-review/single-file-experience-spec.md`.

### E. Storage & Migrations

13. Optional SQLite backend for storage (migrations + CLI tools)

- Status: PARTIAL — The docs (old) describe a full migration plan; current repo has a metadata_search util referencing sqlite3 and `metadata` tools.
- Priority: P1
- Next step: Validate migration scripts and provide a set of easy commands for users to convert file-based store to sqlite, plus backups and integrity checks.
- Source: `old_project_docs/SQLITE_STORAGE.md`.

### F. People, OCR & Media Intelligence

14. Face detection, clustering, naming, and person albums

- Status: PARTIAL — Face clustering docs exist; UI components (People view) appear in old docs but not fully implemented in current UI.
- Priority: P1
- Next step: Build an initial face detection and clustering pipeline; expose a basic UI for face labeling and a person timeline.
- Source: `IDEAS_FROM_OLD_PROJECT.md` (People & Faces), `old_project_docs`.

15. OCR indexing (text extraction) and search (has_text:true filter + text highlight)

- Status: PARTIAL — API interface exists for OCR snippet endpoints in old docs; implementation partly stubbed.
- Priority: P1
- Next step: Integrate an OCR engine, store text snippets, add OCR search filters and highlight snippet preview.
- Source: `old_project_docs`.

### G. AI / Captioning / Tagging / FAL

16. Auto-tagging + caption generation with settable VLM (Qwen, GPT-4V) and model selection UI

- Status: PARTIAL — FAL/Qwen image edit scripts exist (assets and examples); caption generation is documented.
- Priority: P0
- Next step: Add a service that generates captions & tags in batch with user approval workflows; add an AI provider selection and status UI.
- Source: `FAL_QWEN_IMAGE_EDIT.md`, `IDEAS_FROM_OLD_PROJECT.md`.

17. FAL Qwen asset generation (batch icons/backgrounds) and integration

- Status: PARTIAL — Scripts and batch asset generator docs exist.
- Priority: P1
- Next step: Stabilize script, add skip-existing behavior, add a CLI for asset generation and import to UI.
- Source: `FAL_QWEN_IMAGE_EDIT.md`.

### H. UI/UX, Design System & Motion

18. Modal / Dialog system (consistent ModalContainer, focus trap, scroll-lock)

- Status: PARTIAL — The project uses shadcn components and there are docs. Enhanced Modal System doc exists.
- Priority: Quick Win
- Next step: Adopt the EnhancedModal patterns, implement standardized `ModalContainer`, and migrate modals incrementally.
- Source: `old_project_docs/ENHANCED_MODAL_SYSTEM.md`, `shadcn` docs.

19. Command palette (Cmd+K): actionable items (open photo, run saved searches, scan folder)

- Status: PARTIAL — Command palette exists but needs actionful items (open photo in detail) and saved search integrations.
- Priority: Quick Win
- Next step: Wire the command palette to open `PhotoDetail` and run saved searches; add SC/UX indicators for current search mode.
- Source: `codex-review` documents.

20. View modes: Masonry / Film strip / Timeline / Map and matrix of features

- Status: PARTIAL — Masonry grid and basic view modes exist; Map/Trips & Places are placeholders.
- Priority: P1
- Next step: Complete Places view with map integration (Leaflet) + trips auto-detection; finalize timeline behavior.
- Source: `old_project_docs/VIEW_MODES_DOCUMENTATION.md`, `FRONTEND_V3_OWNERSHIP_PLAN.md`.

21. Keyboard Shortcuts and a11y (search × focus, help, keyboard nav)

- Status: PARTIAL — Many keyboard affordances exist but are inconsistent (e.g., theme toggling mismatch documented).
- Priority: Quick Win
- Next step: Centralize a keyboard manager, add consistent `?` help panel, ensure a11y tests pass.
- Source: `codex-review` audits.

### I. Similarity, Lookalikes & Cleanup

22. Duplicate/Lookalike detection with UI (side-by-side, batch dedupe)

- Status: MISSING/PARTIAL — Docs exist and dup detection discussed; not fully in current UI.
- Priority: P1
- Next step: Add a duplicate detection pipeline (hash + visual embeddings) and a UX for safe batch dedupe with undo.
- Source: `IDEAS_FROM_OLD_PROJECT.md`.

### J. Image Editing & Enhancement

23. Basic edits & AI editing (crop/rotate/flip + queued non-destructive edits, FAL for advanced edits)

- Status: PARTIAL — Basic edit operations referenced; FAL Qwen integration is script-based.
- Priority: P1
- Next step: Add an edit service that queues and performs small edits; show job progress and assemble an edit history with undo.
- Source: `codex-review`, `FAL_QWEN_IMAGE_EDIT.md`.

### K. Security, Permissions, & Privacy

24. Path validation, IPC allowlists, CSP, minimal surface for preload

- Status: MISSING/PARTIAL — Security audit mentions these items; code may not fully implement.
- Priority: P0
- Next step: Enforce IPC channel allowlists, Zod validation on IPC payloads, CSP headers, and path validation functions.
- Source: `DESKTOP_APP_AUDIT.md`, `TECHNICAL_REVIEW_CHECKLIST.md`.

25. Share links with expiry, password protection, max-views controls

- Status: PARTIAL — API design for share links exists in old docs and `UserManagementService` stubs.
- Priority: P2
- Next step: Add ShareLink resource support in user management and UI for creating/revoking links.
- Source: `USER_MANAGEMENT_SERVICE.md`.

### L. Testing, QA & Visual Regression

26. Visual testing utilities (`dismissOverlays`, `stableScreenshot`) and performance benchmarks in CI

- Status: PARTIAL — Many visual test docs exist; utilities noted in `old_project_docs` and codex-review docs. CI integration may be incomplete.
- Priority: Quick Win
- Next step: Add a standard test helper library, update Playwright harness, expose visual test baseline snapshots.
- Source: `old_project_docs/TESTING_IMPROVEMENTS_SUMMARY.md`.

27. Accessibility checks and coverage for key flows (Axe, keyboard navigation)

- Status: PARTIAL — Accessibility audit docs exist; tests are recommended.
- Priority: P1
- Next step: Add automated axe checks in CI and expand test coverage for focus management and aria roles.
- Source: `old_project_docs/ACCESSIBILITY*` and `TESTING_IMPROVEMENTS_SUMMARY.md`.

### M. CI, Build & Ops

28. Vector library dependency management (FAISS optional) + bench and fallback picks

- Status: PARTIAL — FAISS is listed as a possible dependency in `requirements.txt`, and vector store experiments exist.
- Priority: P1
- Next step: Add a robust optional dependency strategy; implement fallback selection and auto-detection in the fast index manager.
- Source: `FAST_INDEXES.md`, `README.md` experiments.

29. Bundle optimization & code splitting, lazy load heavy features (leaflet, big UI components)

- Status: PARTIAL — The project has notes re code splitting and `vite` config, but not comprehensive implementation.
- Priority: P1
- Next step: Audit bundles with `npm run analyze` and implement lazy-loading / react-lazy where needed; add a performance budget to CI.
- Source: `old_project_docs` and `Performance` docs.

### N. Small UX & Product Opportunities (Quick Wins)

30. Favorites (heart), rating, quick toggle + filter

- Status: PARTIAL — Favorites exist in docs; UI components in some versions.
- Priority: Quick Win
- Next step: Add a favorite toggle button on cards and a favorites filter; wire APIs.
- Source: `IDEAS_FROM_OLD_PROJECT.md`.

31. Saved searches showcase and `recent` list in command palette

- Status: MISSING
- Priority: Quick Win
- Next step: Add saved search storage and integrate into command palette; add keybindings.
- Source: `IDEAS_FROM_OLD_PROJECT.md`.

32. Export presets (copy/symlink or preset-size EXIF stripped) and local share

- Status: MISSING/PARTIAL
- Priority: P2
- Next step: Add an export modal with minimal options; add `strip EXIF` option for privacy.
- Source: `IDEAS_FROM_OLD_PROJECT.md`.

---

## Suggested Roadmap (high-level sequencing)

1. Quick Wins (Weeks 0-2): offline banner + cached catalog fallback; command palette actions; favorites/ratings; prominent Scan CTA on empty states; job drawer surface skeleton.
2. Short-Term (Weeks 3-6): job queue + persistent jobs; thumbnail resolver & caching; UI work for job drawer, scan progress and pre-scan counts; add FAISS/hnsw manager progress and CLI to build.
3. Medium (Weeks 6-12): Intent recognition + saved searches + advanced search suggestion; face clustering basics + OCR extraction store; offline embedding search research; SQLite backend optional migration tooling.
4. Long-term / Big Bets (Weeks 12+): plugin marketplace/spec; shipped local model support for offline CLIP/embedding; full offline-first experience; desktop hardening, custom protocols & security.

## Next actionable steps (Immediate recommendations)

- Add this file to project `docs/` and open as the canonical backlog for idea triage.
- Choose 3 Quick Wins to implement as high-priority sprint items and convert into tasks/Issues:
  - (A) Scan CTA + offline banner & cached manifest (Quick Win)
  - (B) Command palette: open photo + saved searches + scan path action (Quick Win)
  - (C) Job drawer skeleton + job state persistence (Quick Win / P0)
- Create a triage board in the repo and split these items into `Quick Win / P0 / P1` and assign owners & estimates.

---

If you'd like, I can:

- A: Generate a CSV/issue list with each item, source file reference, status, and suggested effort to upload to GH Issues.
- B: Create a `Backlog` GitHub project with Quick Win / Next / Blocked columns and add the top N tasks.
- C: Start implementing a Quick Win (e.g., offline banner + cached manifest) and add tests and a small CLI script to generate the demo manifest.

Tell me which of these you'd like me to perform next — I can proceed with creating issues, a triage board, or a PR implementing the Quick Win.
