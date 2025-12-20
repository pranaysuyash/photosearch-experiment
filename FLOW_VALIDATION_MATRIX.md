# Living Museum Flow Validation Matrix (Current vs Planned vs Experimental)

This document maps user-facing flows to their status, evidence in the repo,
and how to validate them. It is meant to answer:
- What flows exist today?
- What is planned but not done?
- What is experimental or future-idea territory?
- How do we validate each flow (API/UI/background)?

Sources referenced:
- `docs/USER_FLOWS.md` (baseline flows)
- `NEXT_5_FEATURES_IMPLEMENTATION_PLAN.md` (near-term plan)
- `ROADMAP.md` (mid/long-term)
- `IMPLEMENTED_FEATURES_COMPLETE_DOCS.md` (implementation claims)
- `docs/MEDIA_ANALYSIS_CAPABILITIES.md` (ideas/experiments)

---

## Status Legend

- Implemented: code + endpoints exist and are wired
- Partial: code exists but UI wiring or data pipeline is incomplete
- Planned: in roadmap/docs but not implemented
- Experimental: idea stage or prototype-level

---

## Current Flows (Implemented or Partial)

### 1) Scan and Index (Desktop/Local)
- Status: Implemented
- Evidence: `src/photo_search.py`, `src/file_discovery.py`, `src/metadata_extractor.py`,
  `server/main.py` (`/scan`, `/index`), `server/jobs.py`
- Validation:
  - API: POST `/scan` (small directory) -> job ID
  - UI: Import/scan flow (see `ui/src/pages/Import.tsx`)

### 2) Metadata Search
- Status: Implemented
- Evidence: `src/metadata_search.py`, `server/main.py` (`/search`)
- Validation:
  - API: GET `/search?query=...`
  - UI: search bar -> results grid

### 3) Semantic Search (text -> images)
- Status: Implemented
- Evidence: `server/embedding_generator.py`, `server/lancedb_store.py`,
  `server/main.py` (`/search/semantic`)
- Validation:
  - API: GET `/search/semantic?query=...`
  - UI: semantic mode toggle -> result similarity ordering

### 4) Timeline Browsing
- Status: Implemented
- Evidence: `server/timeline_db.py`, `server/main.py` (`/timeline`)
- Validation:
  - API: GET `/timeline`
  - UI: timeline view (month/day grouping)

### 5) Photo Detail + Version History
- Status: Implemented
- Evidence: `ui/src/components/gallery/PhotoDetail.tsx`,
  `server/photo_versions_db.py`, `/versions/*`
- Validation:
  - UI: open photo -> view metadata, version stack
  - API: GET `/versions/photo/{path}`

### 6) Duplicates Review Lens
- Status: Implemented
- Evidence: `src/enhanced_duplicate_detection.py`, `server/duplicates_db.py`,
  `/duplicates/*` endpoints, `ui/src/pages/DuplicatesPage.tsx`
- Validation:
  - API: POST `/duplicates/scan`, GET `/duplicates`
  - UI: duplicates review flow

### 7) People (Face Detection + Clustering + Viewer Integration)
- Status: Implemented (clustering and viewer integration); detection is available
- Evidence: `src/face_clustering.py`, `src/face_backends.py`,
  `server/face_clustering_db.py`, `server/face_detection_service.py`,
  `/faces/*`, `/api/photos/{path}/people`
- Validation:
  - API: POST `/faces/cluster` or GET `/faces/clusters`
  - UI: People page + per-photo chips

### 8) OCR Text Search + Highlighting
- Status: Implemented (requires optional OCR deps)
- Evidence: `src/enhanced_ocr_search.py`, `/ocr/*` endpoints
- Validation:
  - API: POST `/ocr/extract`, GET `/ocr/search`
  - UI: OCR search panel
  - Note: local OCR libs may be missing unless installed

### 9) Notes / Captions (Per-photo)
- Status: Implemented
- Evidence: `server/notes_db.py`, `/api/photos/{path}/notes`, `NotesEditor.tsx`
- Validation:
  - API: POST `/api/photos/{path}/notes`, GET `/api/notes/search`
  - UI: notes editor in photo detail

### 10) Tags, Ratings, Favorites
- Status: Implemented
- Evidence: `server/tags_db.py`, `server/ratings_db.py`,
  `/tags/*`, `/api/photos/{path}/rating`, `/favorites/*`
- Validation:
  - API: tag CRUD, rating set/get, favorites toggle
  - UI: photo detail chips

### 11) Export + Share Links
- Status: Implemented (share link system exists)
- Evidence: `/export/*`, `/share`, `/shared/*`,
  `server/signed_urls.py`, `ui/src/components/export/ExportDialog.tsx`
- Validation:
  - API: POST `/export`, POST `/share`, GET `/shared/{id}`
  - UI: export dialog + share flow

### 12) Bulk Actions + Trash + Undo
- Status: Implemented
- Evidence: `/bulk/*`, `/trash/*`, `server/bulk_actions_db.py`, `server/trash_db.py`
- Validation:
  - API: POST `/bulk/delete`, POST `/bulk/undo/{id}`
  - UI: bulk action UX

### 13) Smart Albums / Smart Collections
- Status: Implemented (rules engine + DB)
- Evidence: `server/smart_albums.py`, `server/albums_db.py`,
  `server/smart_collections_db.py`, `/albums/*`, `/collections/smart/*`
- Validation:
  - API: create smart collection + fetch photos
  - UI: smart album builder (advanced features UI)

### 14) Locations + Place Correction
- Status: Implemented (DB + endpoints)
- Evidence: `server/locations_db.py`, `server/location_clusters_db.py`, `/locations/*`
- Validation:
  - API: POST `/locations`, GET `/locations/clusters`
  - UI: places view (if wired)

### 15) Provenance Chips (Local/Cloud/Offline)
- Status: Partial (UI uses mock data)
- Evidence: `ui/src/components/provenance/ProvenanceChips.tsx`
- Validation:
  - UI: chips render, but backend feed is not wired
  - Planned: server endpoint for per-photo provenance

### 16) AI Insights Storage
- Status: Partial (DB + endpoints exist; generation not wired)
- Evidence: `server/ai_insights_db.py`, `/ai/insights*`
- Validation:
  - API: POST `/ai/insights` (manual insert), GET `/ai/insights`
  - Planned: actual model-backed generation

### 17) Sources (Local + S3 + Google Drive)
- Status: Implemented (local + API-based S3/Drive sync)
- Evidence: `server/sources.py`, `server/source_items.py`, `/sources/*`
- Validation:
  - API: add local folder, rescan
  - S3/Drive: requires credentials; can test with a sandbox account

---

## Planned Flows (Near-Term Roadmap)

From `NEXT_5_FEATURES_IMPLEMENTATION_PLAN.md`:

- Provenance chips backend feed (Local/Cloud/Offline) -> Planned
- Safe bulk actions UX polish -> Planned
- Multi-tag filtering UX -> Planned (API exists)
- Version stacks UX polish -> Planned (API exists)
- Place correction UI integration -> Planned
- Multi-backend face models -> In progress (backend support exists)

From `ROADMAP.md` and `NEXT_PHASE_FEATURE_PLAN.md`:

- Video content analysis and search -> Planned
- Cloud integration (Dropbox/OneDrive) -> Planned
- Mobile companion app -> Planned
- Advanced AI pipeline (custom training) -> Planned
- Collaboration and sharing (multi-user workflows) -> Planned

---

## Experimental / Plausible Flows (Idea Stage)

From `docs/MEDIA_ANALYSIS_CAPABILITIES.md` and `docs/INNOVATION_OPPORTUNITIES.md`:

- Segmentation (semantic/instance/panoptic)
- Background removal, object removal, inpainting, restoration
- Object detection and scene classification
- Best-shot selection and aesthetic scoring
- Video understanding and highlight extraction
- Audio transcription and keyword search

These are mapped in detail in:
- `AI_MEDIA_USE_CASES_EXECUTION_PROVIDER_MATRIX.md`

---

## Validation Checklist (Suggested)

For each current flow, validation should include:
- API smoke test (curl, basic payload)
- UI visual check (manual browser or MCP)
- DB state check where relevant

Suggested status markers for each flow:
- Not started
- API validated
- UI validated
- Fully validated (API + UI)

---

## Notes / Gaps Identified During Server Startup

- FastAPI rejected `Request | None` annotations; fixed in `server/main.py`.
- OCR libraries are optional and may not be installed (Tesseract/EasyOCR).
- Provenance chips are UI-side mock data; no backend endpoint observed.
- AI insights have storage + endpoints but no generation pipeline.

---

## API Smoke Check (Run with `.venv`)

Server was running locally and the following quick checks were executed:

### OK (200)
- `/`
- `/stats`
- `/pricing`
- `/tags`
- `/sources`
- `/timeline`
- `/faces/stats`
- `/ocr/stats`
- `/versions/stats`
- `/locations/stats`
- `/intent/detect?query=beach`
- `/search?query=beach`
- `/search/semantic?query=beach`

---

## Validation Run (2025-12-20 13:38 +0530)

Backend + frontend restarted via `bash start.sh`. API validation run against
`http://127.0.0.1:8000` using a sample photo from `photo_catalog.json`:
`/Users/pranay/Projects/photosearch_experiment/media/benchmark_0563.png`

### API Checks (All 200)
- Health + core: `/`, `/stats`, `/pricing`, `/sources`, `/timeline`
- Search + intent: `/intent/detect?query=beach`, `/search?query=beach`, `/search/semantic?query=beach`
- People/faces: `/faces/stats`, `/api/faces/stats`, `/api/photos/{path}/people`
- OCR: `/ocr/stats`
- Versions: `/versions/stats`, `/versions/photo/{path}`
- Duplicates: `/api/duplicates/stats`
- Tags + notes + ratings: `/tags`, `/api/notes/stats`, `/api/ratings/stats`
- Albums + collections: `/albums`, `/collections/smart`
- Favorites: `/favorites`, `/favorites/check?file_path=...`
- Share: `/share`, `/shared/{share_id}`
- Photo edits (read): `/api/photos/{path}/edits`

### API Checks with Writes (All 200)
- Notes: `POST /api/photos/{path}/notes`
- Ratings: `POST /api/photos/{path}/rating`
- Favorites: `POST /favorites/toggle`
- Tags: `POST /tags`, `POST /tags/{tag_name}/photos`
- Share link: `POST /share`

### UI Validation
- Not executed (no browser MCP resources detected in this environment).

### Issues Resolved During Validation
- `/collections/smart` failed due to SQLite `INDEX` syntax in table creation.
- `/api/faces/stats` failed due to missing `deleted_at` column in metadata table.
- `/api/photos/{path}/people` failed due to legacy face DB schema mismatch.
