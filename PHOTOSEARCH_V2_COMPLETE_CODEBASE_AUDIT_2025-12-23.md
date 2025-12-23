# PhotoSearch v2 - Complete Codebase Audit

**Date:** 2025-12-23
**Auditor:** GitHub Copilot (AI)
**Project Location:** `/Users/pranay/Projects/photosearch_experiment`
**Commit/Version:** `cbd4306ba2b8ab4adcd295e521d118de5846cbd5` (from `audit_artifacts/discovery_20251223_155700.txt`)
**Audit Duration:** Incremental, evidence-backed (see `audit_artifacts/` timestamps)

---

## Executive Summary

### Current State (3-5 paragraphs)

PhotoSearch v2 is a surprisingly feature-rich system already: a FastAPI backend with hundreds of routes and a React/Vite UI that calls a meaningful portion of them. Discovery confirms a split monorepo-ish structure with Python backend in `server/` and React frontend in `ui/`, plus an optional Tauri desktop wrapper in `src-tauri/` (`audit_artifacts/discovery_20251223_155700.txt`).

The headline risk is still the **Hidden Genius Problem**—not because nothing is wired, but because several _high leverage_ capabilities are present server-side but not consistently reachable from the UI. Utilization is decent in raw percentage terms (**216/325 endpoints used ≈ 66%**) and the previously remaining face scan/status/name endpoints are now exposed (see `audit_artifacts/backend_endpoint_inventory_stats.txt`, `audit_artifacts/face_scan_single_status_person_wired_20251223_221900.txt`).

Search and intelligence tooling exists (intent detection endpoints, match explanations, semantic search scaffolding). The current UX, however, contains contradictory patterns: the UI both **auto-detects search mode** and offers **manual mode selection**, which can create user confusion and mode “flapping” (evidence in the prior audit: `ui/src/contexts/PhotoSearchContext.tsx:165–225` and `ui/src/components/layout/DynamicNotchSearch.tsx:417`). The smallest viable fix here is to formalize “Auto vs Manual override” and prevent auto-switching while manual override is active.

On desktop security, Tauri is configured with minimal permissions (`src-tauri/capabilities/default.json`) and the app CSP is now enabled (prod `csp` + dev-only `devCsp`) in `src-tauri/tauri.conf.json:25–28` (see `audit_artifacts/tauri_csp_enabled_20251223_233200.txt`). A follow-up desktop runtime smoke test is still recommended to ensure the tightened CSP does not break UI features.

Verification credibility: backend tests are green under test-mode controls (evidence: `audit_artifacts/pytest_full_green_20251223_154836.txt`).

### Critical Findings

**Top 5 Blockers (P0):**

1. **Desktop security verification gap: CSP enabled but needs runtime validation + tightening pass** — config: `src-tauri/tauri.conf.json:25–28`; evidence artifacts: `audit_artifacts/tauri_csp_enabled_20251223_233200.txt`, `audit_artifacts/tauri_cargo_check_20251223_233420.txt`.
2. **Smart Search UX contradiction (auto-routing vs manual mode selection) causes mode flapping** — `ui/src/contexts/PhotoSearchContext.tsx:165–225` + `ui/src/components/layout/DynamicNotchSearch.tsx:417`.
3. **Code splitting blocked: oversized main bundle + dynamic+static import conflict** — evidence: `audit_artifacts/ui-build.txt` and `audit_artifacts/bundle-report.html`.
4. **Audit-grade truth maintenance risk: generated inventories can drift from current line anchors** — example: `audit_artifacts/backend_endpoint_inventory.md` can list older anchors; current anchors should be re-verified against decorators.
5. **Match explanations generated but not consistently surfaced in UI** — implementations: `server/utils/search_explanations.py:1`, `:123`, `:202`; routed usage: `server/api/routers/search.py:525`, `:877`, `server/api/routers/semantic_search.py:179`; frontend type exists: `ui/src/api.ts:84–95`.

**Top 5 High Priority (P1):**

1. **Advanced OCR endpoints are present and used, but UX integration appears fragmented** — calls present in `audit_artifacts/frontend_endpoints_called.txt` (`/api/ocr/*`); requires consistent entry point + results surface.
2. **Discovery experience (globe) needs performance proof + pin clustering/instancing verification** — UI uses three.js deps (`ui/package.json` shows `three`, `@react-three/fiber`, `@react-three/drei`; `audit_artifacts/discovery_20251223_155700.txt`).
3. **Frontend test coverage and quality gates are unclear; TS errors artifact exists** — `audit_artifacts/typescript-errors.txt`.
4. **Accessibility gaps (discernible text + labels)** — examples: `ui/src/components/advanced/FaceRecognitionPanel.tsx:535`, `:625`, `:639`, `:653`, `:705`.
5. **Style/lint hygiene: inline styles used in React** — examples: `ui/src/components/advanced/FaceRecognitionPanel.tsx:313`, `ui/src/pages/People.tsx:681`.

### Quick Wins (Top 10)

|   # | Item                                                                        | Effort |  Impact   | Evidence                                                                                                                                                                                                |
| --: | --------------------------------------------------------------------------- | :----: | :-------: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
|   1 | Tauri CSP enabled (verify + tighten)                                        |   S    | Very High | Config: `src-tauri/tauri.conf.json:25–28`; artifacts: `audit_artifacts/tauri_csp_enabled_20251223_233200.txt`, `audit_artifacts/tauri_cargo_check_20251223_233420.txt`                                  |
|   2 | Cache clear is already exposed (Performance page) (`POST /api/cache/clear`) |   XS   |   High    | Backend: `server/api/routers/system.py:37`; UI: `ui/src/pages/PerformanceDashboard.tsx:93` + `ui/src/api.ts:1477`; artifact: `audit_artifacts/cache_clear_wired_20251223_171259.txt`                    |
|   3 | Advanced scan directory is now exposed (verify + polish)                    |   XS   |   High    | Backend: `server/main_advanced_features.py:197`; UI: `ui/src/pages/AdvancedFeaturesPage.tsx:202`; artifact: `audit_artifacts/scan_directory_wired_20251223_185027.txt`                                  |
|   4 | Comprehensive stats is now exposed (verify + polish)                        |   XS   |   High    | Backend: `server/main_advanced_features.py:313`; UI: `ui/src/pages/AdvancedFeaturesPage.tsx:232`; artifact: `audit_artifacts/comprehensive_stats_wired_20251223_200847.txt`                             |
|   5 | Cluster photos drill-down is already exposed (PersonDetail)                 |   XS   |   High    | Backend: `server/api/routers/face_recognition.py:460`; UI: `ui/src/pages/PersonDetail.tsx:81`; artifact: `audit_artifacts/cluster_photos_wired_fix_20251223_165102.txt`                                 |
|   6 | Face crop preview is now exposed (verify + polish)                          |   XS   |  Medium   | Backend: `server/api/routers/face_recognition.py:855`; UI: `ui/src/pages/UnidentifiedFaces.tsx:102`; artifact: `audit_artifacts/face_loop_and_person_analytics_wired_20251223_202105.txt`               |
|   7 | Face assign + create-person are now exposed (verify + polish)               |   XS   |   High    | Backend: `server/api/routers/face_recognition.py:735`, `:772`; UI: `ui/src/pages/UnidentifiedFaces.tsx:79`, `:90`; artifact: `audit_artifacts/face_loop_and_person_analytics_wired_20251223_202105.txt` |
|   8 | Person analytics is now exposed (verify + polish)                           |   XS   |   High    | Backend: `server/api/routers/face_recognition.py:1039`; UI: `ui/src/pages/PersonDetail.tsx:128`; artifact: `audit_artifacts/face_loop_and_person_analytics_wired_20251223_202105.txt`                   |
|   9 | Enforce search mode semantics: Auto vs Manual override                      |   S    |   High    | `ui/src/contexts/PhotoSearchContext.tsx:165–225`                                                                                                                                                        |
|  10 | Standardize “Why this matched” component                                    |   M    |   High    | `server/utils/search_explanations.py:*` + `ui/src/api.ts:84–95`                                                                                                                                         |

### Overall Health Scores

(0 = missing/broken, 4 = excellent)

| Category             | Score (0-4) | Justification                                                                                                                                                                                         |
| -------------------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend Utilization  | 2.8         | 216/325 endpoints used (~66%); high-ROI API-only “Hidden Genius” list is now empty (`audit_artifacts/backend_endpoint_inventory_stats.txt`, `audit_artifacts/backend_endpoints_unused_api_only.txt`). |
| Search Experience    | 2.6         | Intent + multiple modes exist, but UX contradictions and explanation surfacing gaps remain.                                                                                                           |
| Glass Design System  | 2.7         | Glass surfaces present, but needs token governance and contrast verification across components.                                                                                                       |
| Adaptive UI          | 2.5         | Multiple modes exist (notch/bubble/mobile), but needs parity and stable mode selection.                                                                                                               |
| Discovery Experience | 2.2         | Three.js stack present; performance/UX metrics not yet proven in artifacts.                                                                                                                           |
| Accessibility        | 2.0         | No demonstrated WCAG audit outputs; likely gaps in focus management and clickable divs (needs evidence pass).                                                                                         |
| Performance          | 2.3         | Bundle size evidence indicates major chunk; needs code splitting + RUM/latency metrics.                                                                                                               |
| Code Quality         | 2.8         | Tests green backend; architecture has many modules; still some drift and duplication risk.                                                                                                            |
| Testing              | 2.9         | Backend tests green (`audit_artifacts/pytest_full_green_20251223_154836.txt`); frontend coverage unclear.                                                                                             |
| Documentation        | 3.0         | Extensive docs folder; audit artifacts provide reproducible evidence.                                                                                                                                 |
| **Overall Average**  | **2.58**    | Solid base with real functionality; needs “Hidden Genius surfacing” and security hardening to become a product.                                                                                       |

---

## A. Backend-Frontend Capability Gap Analysis

### A1. API Endpoint Inventory & Utilization

#### Evidence & counts

- Discovery + stack confirmation: `audit_artifacts/discovery_20251223_155700.txt`
- Endpoint decorator count: 353 (`audit_artifacts/discovery_20251223_155700.txt`)
- Inventory + utilization mapping: `audit_artifacts/backend_endpoint_inventory.md`
- Utilization totals: `audit_artifacts/backend_endpoint_inventory_stats.txt`

#### Gap summary

- Total endpoints: **325**
- Used by frontend: **216** (~66%)
- Unused by frontend: **109**

**High-value endpoints (API-prefixed, audit-minimal list)**
(These are immediately product-relevant; the API-only unused list is now empty — see `audit_artifacts/backend_endpoints_unused_api_only.txt`.)

| Endpoint                                  | Method | Purpose                             | Called by Frontend? | Evidence                                                                                                                                                                                  | Priority to Expose |
| ----------------------------------------- | ------ | ----------------------------------- | :-----------------: | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :----------------: |
| `/api/advanced/scan-directory`            | POST   | Power indexing / ingestion workflow |         ✅          | Backend: `server/main_advanced_features.py:197`; UI: `ui/src/pages/AdvancedFeaturesPage.tsx:202`                                                                                          |         P0         |
| `/api/advanced/comprehensive-stats`       | GET    | System/library deep stats           |         ✅          | Backend: `server/main_advanced_features.py:313`; UI: `ui/src/pages/AdvancedFeaturesPage.tsx:232`                                                                                          |         P1         |
| `/api/cache/clear`                        | POST   | Clear caches deterministically      |         ✅          | Backend: `server/api/routers/system.py:37`; UI: `ui/src/api.ts:1477`                                                                                                                      |         P0         |
| `/api/faces/clusters/{cluster_id}/photos` | GET    | Browse photos in a face cluster     |         ✅          | Backend: `server/api/routers/face_recognition.py:460`; UI: `ui/src/pages/PersonDetail.tsx:81`                                                                                             |         P0         |
| `/api/faces/crop/{face_id}`               | GET    | Face crop preview / inline UI       |         ✅          | Backend: `server/api/routers/face_recognition.py:855`; UI: `ui/src/pages/UnidentifiedFaces.tsx:102`; artifact: `audit_artifacts/face_loop_and_person_analytics_wired_20251223_202105.txt` |        DONE        |
| `/api/faces/person/{person_name}`         | GET    | Direct person-name face lookup      |         ✅          | Backend: `server/api/routers/face_recognition.py:356`; UI: `ui/src/pages/People.tsx:251`; artifact: `audit_artifacts/face_scan_single_status_person_wired_20251223_221900.txt`            |        DONE        |
| `/api/faces/scan-single`                  | POST   | Single-image face scan (debug/UX)   |         ✅          | Backend: `server/api/routers/face_recognition.py:310`; UI: `ui/src/pages/People.tsx:275`; artifact: `audit_artifacts/face_scan_single_status_person_wired_20251223_221900.txt`            |        DONE        |
| `/api/faces/scan-status/{job_id}`         | GET    | Scan job progress polling           |         ✅          | Backend: `server/api/routers/face_recognition.py:299`; UI: `ui/src/pages/People.tsx:299`; artifact: `audit_artifacts/face_scan_single_status_person_wired_20251223_221900.txt`            |        DONE        |
| `/api/faces/{face_id}/assign`             | POST   | Assign face to person               |         ✅          | Backend: `server/api/routers/face_recognition.py:735`; UI: `ui/src/pages/UnidentifiedFaces.tsx:79`; artifact: `audit_artifacts/face_loop_and_person_analytics_wired_20251223_202105.txt`  |        DONE        |
| `/api/faces/{face_id}/create-person`      | POST   | Convert face to new person entity   |         ✅          | Backend: `server/api/routers/face_recognition.py:772`; UI: `ui/src/pages/UnidentifiedFaces.tsx:90`; artifact: `audit_artifacts/face_loop_and_person_analytics_wired_20251223_202105.txt`  |        DONE        |
| `/api/people/{person_id}/analytics`       | GET    | Person-level analytics              |         ✅          | Backend: `server/api/routers/face_recognition.py:1039`; UI: `ui/src/pages/PersonDetail.tsx:128`; artifact: `audit_artifacts/face_loop_and_person_analytics_wired_20251223_202105.txt`     |        DONE        |

> Note: `audit_artifacts/backend_endpoint_inventory.md` is used for inventory-scale evidence, but **line anchors can drift**. The P0/P1 endpoints above have been re-verified against current decorators for accuracy where possible.

### A2. Hidden Features Audit

| Feature                        | Backend Implementation                                                                                                                | Frontend Exposure                    | Impact of Hiding                                          | Effort to Surface | Priority |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ | --------------------------------------------------------- | :---------------: | :------: |
| Cache clear (ops reset)        | `POST /api/cache/clear` (`server/api/routers/system.py:37`)                                                                           | **Exposed via Performance UI**       | Improves recovery from stale/bad caches; easier debugging |        XS         |    P0    |
| Advanced scan directory        | `POST /api/advanced/scan-directory` (`server/main_advanced_features.py:197`)                                                          | **Exposed via Advanced Features UI** | Power users can batch ingest/repair                       |       XS–S        |    P0    |
| Deep stats                     | `GET /api/advanced/comprehensive-stats` (`server/main_advanced_features.py:313`)                                                      | **Exposed via Advanced Features UI** | Better trust/transparency for pipeline health             |        XS         |    P1    |
| Face cluster merge suggestions | `GET /api/faces/clusters/merge-suggestions` (`server/api/routers/face_recognition.py:1694`) + dismiss (`:1724`)                       | **Exposed in People UI**             | Improves People quality by merging duplicates             |       XS–S        |    P0    |
| Face: browse cluster photos    | `GET /api/faces/clusters/{cluster_id}/photos` (`server/api/routers/face_recognition.py:460`)                                          | **Exposed via PersonDetail**         | Improves drill-down from People into real photos          |        XS         |    P0    |
| Face: assign/create person     | `POST /api/faces/{face_id}/assign` (`server/api/routers/face_recognition.py:735`), `POST /api/faces/{face_id}/create-person` (`:772`) | **Exposed via Unidentified Faces**   | Core people workflow becomes tangible + correctable       |        XS         |    P0    |
| Person analytics               | `GET /api/people/{person_id}/analytics` (`server/api/routers/face_recognition.py:1039`)                                               | **Exposed via PersonDetail**         | Restores differentiation (“memory intelligence”)          |        XS         |    P1    |
| Match explanations             | `server/utils/search_explanations.py:*`                                                                                               | Typed but inconsistently shown       | AI feels arbitrary; weak trust                            |         M         |    P0    |

Merge Suggestions UI evidence:

- People page wiring: `ui/src/pages/People.tsx:28` (import) and `ui/src/pages/People.tsx:420` (render)
- Artifact: `audit_artifacts/merge_suggestions_wired_20251223_163850.txt`

Cluster photos UI evidence:

- Person detail route exists: `ui/src/router/MainRouter.tsx:82` (`/people/:clusterId`)
- UI call site: `ui/src/pages/PersonDetail.tsx:81` (calls `/api/faces/clusters/${clusterId}/photos`)
- Backend route: `server/api/routers/face_recognition.py:460`
- Artifact: `audit_artifacts/cluster_photos_wired_fix_20251223_165102.txt`

### A3. Smart Search API Integration

**Is Smart Search API implemented?** Partially.

- Intent detection endpoints exist and are called by UI:
  - `GET /api/intent/detect` — `server/api/routers/intent.py:9`, used by `ui/src/components/search/IntentRecognition.tsx:47` (inventory evidence: `audit_artifacts/backend_endpoint_inventory.md`).
  - Also legacy path: `GET /intent/detect` — `server/api/routers/intent.py:37`.

**Is it used by the frontend?** Yes (intent endpoints are called), but UI still offers manual mode selection.

**Manual mode toggles present in UI?** Yes.

- Evidence (prior audit, still applicable):
  - Auto-switching behavior: `ui/src/contexts/PhotoSearchContext.tsx:165–225` (detectSearchMode + `setSearchMode(detectedMode)`).
  - Manual mode dropdown: `ui/src/components/layout/DynamicNotchSearch.tsx:417`.

#### Smallest viable fix

- Add a single explicit concept: SearchModeControl = `Auto | ManualOverride`.
- When manual override is set, do not apply `detectSearchMode` updates.

Acceptance criteria

- Selecting a manual mode remains stable across query edits.
- Re-enabling Auto resumes detection.

Rollback

- Feature flag the override.

Effort: **S (0.5–1.5 days)**.

### A4. Confidence & Match Explanation Visibility

**Are match explanations generated?** ✅ Yes.

- Implementations:
  - `server/utils/search_explanations.py:1` (`generate_metadata_match_explanation`)
  - `server/utils/search_explanations.py:123` (`generate_hybrid_match_explanation`)
  - `server/utils/search_explanations.py:202` (`generate_semantic_match_explanation`)
- Routed usage:
  - `server/api/routers/search.py:525` and `server/api/routers/search.py:877`
  - `server/api/routers/semantic_search.py:179`

**Are explanations shown to users?** ⚠️ Partially / inconsistent.

- UI types exist: `ui/src/api.ts:84–95` defines `MatchExplanation` and `matchExplanation?: MatchExplanation`.

#### P0 recommendation

- Standardize a single “Why this matched” UI component used in all result cards.

---

## B. Search Experience Quality

### B1. Natural Language Understanding

Evidence of intent plumbing:

- Intent endpoints exist (`server/api/routers/intent.py:9`, `:37`).
- UI intent recognition component exists: `ui/src/components/search/IntentRecognition.tsx:47` (inventory evidence).

Test matrix (needs real interactive traces; use this table as execution plan):

| Query Type | Example                   | Expected Routing   | Actual Behavior                 | Evidence                                    | Issues                                            |
| ---------- | ------------------------- | ------------------ | ------------------------------- | ------------------------------------------- | ------------------------------------------------- |
| Temporal   | “photos from last summer” | Metadata           | Not measured in this audit pass | No trace artifact captured (add trace logs) | Likely date parsing gaps                          |
| Semantic   | “sunset at beach”         | CLIP semantic      | Not measured in this audit pass | No trace artifact captured (add trace logs) | Needs confidence display                          |
| Hybrid     | “birthday party 2023”     | Fusion             | Not measured in this audit pass | No trace artifact captured (add trace logs) | Ranking conflicts                                 |
| Entity     | “photos of John”          | Face/person search | Not measured in this audit pass | No trace artifact captured (add trace logs) | Face correction loop now wired; needs trace proof |
| Location   | “New York”                | Geotag filter      | Not measured in this audit pass | No trace artifact captured (add trace logs) | Globe integration needed                          |
| Ambiguous  | “blue”                    | Ask-clarify        | Not measured in this audit pass | No UX artifact captured (add fallback UI)   | Needs disambiguation UI                           |

Smallest viable fix

- Instrument and log routing decisions in one place (client + server), then surface as “search chips” for debugging.

### B2. Result Quality & Relevance

Evidence exists that result explanation building is implemented (see A4). Missing: consistent UI surfacing and result limiting principles to “2 perfect results.”

Smallest viable fix

- Default to top-$k$=20 display with “Show more” expansion.
- Display confidence/explanation badges.

### B3. Search Failure Modes

No-results and low-confidence UX requires explicit, user-facing handling.

Smallest viable fix

- Add a “No results” panel with suggestions sourced from intent suggestions endpoint (`GET /intent/suggestions` exists; called by UI: `audit_artifacts/frontend_endpoints_called.txt`).

### B4. Search Performance Profiling

Evidence artifacts exist for build size but not for end-to-end search timing.

Smallest viable fix

- Add timing spans (client) and log durations for: query → intent → backend call → render.
- Store in an in-memory ring buffer and expose in the existing performance dashboard UI (`ui/src/pages/PerformanceDashboard.tsx`).

---

## C. Glass Design System & Visual Excellence

### C1. Design System Audit

Evidence of glass usage + token surface area:

- Glass token mapping lives in one place: `ui/src/design/glass.ts:1–9`.
- Core glass surface + button styling is centralized in CSS:
  - `.glass-surface` + blur: `ui/src/index.css:101–116`
  - `.glass-surface--strong`: `ui/src/index.css:118–124`
  - `.btn-glass` + focus/hover variants: `ui/src/index.css:127–176`
- UI components consistently import/use `glass` helper:
  - Example: `ui/src/components/advanced/AnalyticsDashboard.tsx:38` (imports `glass`).
- Evidence capture: `audit_artifacts/mega_audit_greps_20251223_160107.txt`.

Risk / inconsistency signal:

- Hard-coded colors still appear in legacy CSS modules (sample): `audit_artifacts/hardcoded_colors_20251223_160136.txt` (e.g., `ui/src/components/ModalSystem.css:*`, `ui/src/components/features/TauriIntegration.css:*`).

Smallest viable fix:

- Keep `ui/src/design/glass.ts` as the single “glass class contract”, but incrementally migrate legacy CSS modules to use shared tokens (or Tailwind vars) rather than fixed hex values.

### C2. Contrast & Readability

Evidence signals (needs measurement follow-up, but not zero):

- Glass surfaces are explicitly translucent (multiple `rgba(...)` layers): `ui/src/index.css:101–176`.
- Several non-token hex colors exist in legacy styles (sample): `audit_artifacts/hardcoded_colors_20251223_160136.txt`.

Smallest viable fix:

- Run a targeted contrast pass on: search notch, photo detail overlays, modal overlays. Record worst offenders and introduce a “glass text” token pair for light/dark.

### C3. Animation & Glassmorphism Performance

Evidence of expensive primitives:

- Backdrop blur is used across global UI surfaces: `ui/src/index.css:101–176`.

Smallest viable fix:

- Reduce nested blur layers and avoid animating blur/filters on large surfaces (animate opacity/transform instead).

---

## D. Adaptive UI & Responsive Design

### D1. DynamicNotchSearch Component

Evidence of the component and search-mode interactions:

- `DynamicNotchSearch` exists and is used as the global search shell: `ui/src/components/layout/Layout.tsx:23` + `ui/src/components/layout/Layout.tsx:208`.
- Manual mode selection is present: `ui/src/components/layout/DynamicNotchSearch.tsx:417` (`setSearchMode(item.id as any)`), captured in `audit_artifacts/mega_audit_greps_fix_20251223_160116.txt`.
- Auto-detection + auto-set is present: `ui/src/contexts/PhotoSearchContext.tsx:165–225` (see `detectSearchMode` + `setSearchMode(detectedMode)`; captured in `audit_artifacts/mega_audit_greps_fix_20251223_160116.txt`).

Smallest viable fix:

- Add an explicit Auto vs ManualOverride switch (and stop auto-setting mode while in manual override).

### D2. Responsive Layout Bugs

Known issue from prior notes: “search pushed too far right.” Needs a targeted CSS evidence pass.

### D3. Touch Optimization

Evidence that mobile navigation uses icon imagery and compact controls (touch-target risk area):

- `ui/src/components/navigation/MobileNavigation.tsx:98` includes an `<img ...>` element (from `audit_artifacts/mega_audit_greps_20251223_160107.txt`).

Smallest viable fix:

- Add a minimum hit-area utility class (e.g., `min-w-[44px] min-h-[44px]`) for icon buttons and nav items.

---

## E. Discovery & Exploration Experience

### E1. Globe Visualization Performance

Stack evidence:

- Three.js dependencies present: `ui/package.json` includes `three`, `@react-three/fiber`, `@react-three/drei` (`audit_artifacts/discovery_20251223_155700.txt`).

Implementation evidence:

- Globe component implementation: `ui/src/components/features/PhotoGlobe.tsx` (1504 lines; largest UI file after `api.ts`) and uses R3F hooks:
  - `<Canvas>`: `ui/src/components/features/PhotoGlobe.tsx:1457`
  - `useFrame(...)` loops: `ui/src/components/features/PhotoGlobe.tsx:692`, `:755`, `:904`, `:1092` (captured in `audit_artifacts/mega_audit_greps_20251223_160107.txt`).

Smallest viable fix

- Prove pin rendering strategy (instancing/LOD/clustering) with a benchmark page and store trace outputs.

### E2. Gamification & Discovery Mechanics

Evidence:

- No explicit achievement/unlock/streak mechanic implementation surfaced in a broad string/code scan; most “badge” usage appears to be intent/assignment/metadata badges rather than gamification (see `audit_artifacts/mega_audit_followup_fix_20251223_161039.txt`).
- “Badges” exist as part of intent UX:
  - Server mentions badges in search responses: `server/api/routers/search.py:918`.
  - Intent badges endpoint exists: `server/api/routers/intent.py:91–105`.
  - UI fetches intent badges: `ui/src/components/search/IntentRecognition.tsx:83–92`.

Smallest viable fix:

- Treat “badges” as a trust/discovery primitive first (intent badges, confidence badges, source badges) before adding game mechanics.

### E3. Semantic Constellation Mode

Evidence:

- Concept is described in docs (UI idea): `docs/UI_CONCEPT_EXPLORATION.md:44` (captured in `audit_artifacts/mega_audit_followup_fix_20251223_161039.txt`).
- No concrete implementation surfaced in the same scan for constellation/graph/force layout terms (see `audit_artifacts/mega_audit_followup_fix_20251223_161039.txt`).

Smallest viable fix:

- If this mode is desired, start as a read-only “semantic scatter/graph” view powered by existing semantic search results, behind a feature flag.

---

## F. Information Architecture & Navigation

### F1. Tabbed Interface Structure

Evidence (representative tab + navigation patterns):

- Primary navigation components exist for desktop-style sidebar and mobile:
  - Sidebar nav list and links: `ui/src/components/navigation/SidebarNavigation.tsx:31–110`.
  - Mobile nav + slide-in sidebar pattern: `ui/src/components/navigation/MobileNavigation.tsx:42–120`.
- Page-level tab switching is implemented using internal state + button groups:
  - People page tabs (“People” / “Needs Review” / “Merge Suggestions”): `ui/src/pages/People.tsx:363–432`.
- Deep detail views also implement tabbed panes:
  - Photo detail tab switcher (“Info/Edit/Details”): `ui/src/components/gallery/tabs/PhotoDetailTabs.tsx:18–70`.

Audit note:

- This section is now evidence-backed for “tabs exist” and “primary navigation exists,” but still needs a UX consistency review (keyboard focus, ARIA labeling, and route parity) as part of the a11y pass (see Section G).

### F2. Navigation Structure

Route map evidence:

- Primary route definitions live in `ui/src/router/MainRouter.tsx`:
  - `Route path='/'` and core app routes: `ui/src/router/MainRouter.tsx:72–131` (captured in `audit_artifacts/mega_audit_greps_20251223_160107.txt`).

Breadcrumb evidence:

- No obvious Breadcrumb component references were found in a broad grep pass (see `audit_artifacts/mega_audit_greps_20251223_160107.txt`, “## Breadcrumb” section produced no matches).

Smallest viable fix:

- Add lightweight breadcrumbs only for deep views (e.g., People → Person detail, Album → Album detail) and keep global search as the primary nav.

---

## G. Accessibility (WCAG 2.2 Level AA)

### G1. Keyboard Navigation

Evidence signals:

- There are multiple modal-overlay patterns implemented as clickable `<div>` backdrops (common and acceptable if focus-trapped correctly, but worth auditing):
  - `ui/src/components/collaboration/CollaborativeSpaces.tsx:301` (overlay onClick close)
  - `ui/src/components/sources/ConnectSourceModal.tsx:173` (overlay onClick close)
  - `ui/src/components/export/ExportDialog.tsx:171` (overlay onClick close)
  - `ui/src/pages/People.tsx:572` and `:607` (overlay close)
  - Evidence capture: `audit_artifacts/mega_audit_greps_20251223_160107.txt`.

Smallest viable fix:

- Ensure all modal dialogs implement focus trapping, Escape-to-close, and restore focus to the triggering element.

### G2. Screen Reader Support

Evidence signals:

- `aria-label` usage exists but is not universal (count in a grep pass): **90 occurrences** (evidence: `audit_artifacts/mega_audit_greps_20251223_160107.txt`).
- `role="..."` usage appears rare in grep pass (**0 occurrences**), which is fine if semantic elements are used, but suggests auditing custom clickable non-semantic elements.

Smallest viable fix:

- Add `aria-live` for search result count changes and ensure icon-only buttons have labels.

### G3. Color & Contrast

Evidence signals:

- Glass UI relies on translucent layers (`rgba(...)`) which can easily drop contrast on busy imagery backgrounds: `ui/src/index.css:101–176`.

Smallest viable fix:

- Introduce a “scrim” token for text-on-image contexts and apply it under text overlays.

---

## H. Performance & Optimization

### H1. Performance Budgets

Evidence:

- Bundle report exists: `audit_artifacts/bundle-report.html` and `audit_artifacts/ui-build.txt`.

Smallest viable fix

- Fix the blocking code splitting issue (dynamic+static import conflict) and enforce chunk budgets in CI.

### H2. Three.js Optimization

Evidence:

- R3F render-loop usage is present (multiple `useFrame(...)` loops): `ui/src/components/features/PhotoGlobe.tsx:692`, `:755`, `:904`, `:1092` (captured in `audit_artifacts/mega_audit_greps_20251223_160107.txt`).

Smallest viable fix:

- Add a debug HUD (FPS, draw calls, texture count if available) for GlobePage and document a baseline trace.

### H3. Image Pipeline Optimization

Backend thumbnail endpoints exist; needs cache hit rate + header verification.

---

## I. Code Quality & Architecture

### I1. Complexity Metrics

Evidence (UI): large file hotspots (SLOC) are already identifiable:

- `ui/src/api.ts` — 2619 lines
- `ui/src/components/features/PhotoGlobe.tsx` — 1504 lines
- `ui/src/components/gallery/PhotoDetail.tsx` — 1469 lines
- `ui/src/components/search/EnhancedSearchUI.tsx` — 1002 lines
- Evidence: `audit_artifacts/mega_audit_greps_20251223_160107.txt`.

Smallest viable fix:

- Split the top 5 TSX files by responsibility (view shell vs data hooks vs pure components) while keeping exports stable.

### I2. TypeScript Strictness

Evidence:

- Typecheck artifacts exist: `audit_artifacts/typescript-errors.txt`.

Type safety signal:

- `as any` / `: any` usage count: **135** (evidence: `audit_artifacts/mega_audit_greps_20251223_160107.txt`).

### I3. State Management Architecture

Evidence:

- App uses React Context for major domains:
  - `ui/src/contexts/AmbientThemeContext.tsx:21` creates context; `:127` uses it.
  - `ui/src/contexts/PhotoSearchContext.tsx:51` creates context; `:487` uses it.
  - Evidence: `audit_artifacts/mega_audit_greps_20251223_160107.txt`.

Smallest viable fix:

- Define strict context value types and reduce `any` usage in context boundaries first (highest leverage).

---

## J. ML Model Integration & Search Intelligence

### J1. CLIP Embedding Pipeline

Evidence of embedding infrastructure exists across `server/embedding_generator.py` and LanceDB docs (see docs; needs direct code anchors in follow-up pass).

### J2. Face Clustering

Backend face clustering is extensive; some key endpoints remain unexposed (A1).

Update (2025-12-23): the remaining high-ROI face scan/status/person endpoints have been surfaced in the UI; the “unused API-only” list is now empty (see `audit_artifacts/backend_endpoints_unused_api_only_count.txt` and `audit_artifacts/face_scan_single_status_person_wired_20251223_221900.txt`).

### J3. OCR for Text in Photos

UI calls OCR endpoints (`audit_artifacts/frontend_endpoints_called.txt` contains `/api/ocr/*`), but product surface needs consolidation.

---

## K. Tauri Security & Desktop Integration

### K1. Tauri Security Configuration

Evidence:

- CSP enabled (prod + dev): `src-tauri/tauri.conf.json:25–28` (see `audit_artifacts/tauri_csp_enabled_20251223_233200.txt`).
- Minimal permissions: `src-tauri/capabilities/default.json` contains `"core:default"` only.

Status

- CSP is now enabled and split correctly between production (`security.csp`) and development (`security.devCsp`). Rust compile check is green (see `audit_artifacts/tauri_cargo_check_20251223_233420.txt`).

Follow-ups

- Run a desktop runtime smoke test (load app, navigate core flows) to confirm the CSP does not break required `connect-src` / asset loading.
- Tighten CSP further once runtime evidence exists (reduce localhost allowances for production if not required).

Acceptance criteria

- App loads with CSP enabled (desktop runtime smoke test evidence captured).
- No remote code execution vectors via overly-relaxed CSP (no production `unsafe-eval`; no unnecessary remote origins).

Rollback

- Allow CSP relaxation only in dev build via env flag.

Effort: **S**.

### K2. Desktop UX

Evidence:

- Window decorations disabled + transparent glass approach in Tauri window settings: `src-tauri/tauri.conf.json:13–24`.

---

## L. Testing Strategy & Coverage

### L1. Test Inventory

Evidence:

- Backend tests are green: `audit_artifacts/pytest_full_green_20251223_154836.txt`.

### L2. Critical Test Gaps

- Frontend unit/integration test posture unclear.

Smallest viable fix

- Add 3 E2E “critical path” tests (search, open detail, face flow) and run them in CI.

---

## M. Documentation & Developer Experience

### M1. README Quality

Evidence:

- `README.md` exists and is substantial (see `README.md:144+` excerpt in workspace). Needs a 5-minute quickstart validation.

### M2. Code Documentation

Evidence signals (quick, imperfect proxies):

- Server-side Python function definitions (rg count): **468**
- Server-side triple-quote occurrences (rg count, includes docstrings + other multi-line strings): **1881**
- Server-side return type hint occurrences (rg count): **427**
- Evidence: `audit_artifacts/mega_audit_followup_fix_20251223_161039.txt`.

Smallest viable fix:

- Standardize docstrings + type hints on the public API boundary layer first (FastAPI routers + service entry points).

---

## N. Feature Completeness & Roadmap

### N1. Feature Matrix (evidence-driven starter)

| Feature                             | Status | Priority | Evidence                                                                          | Effort |
| ----------------------------------- | ------ | :------: | --------------------------------------------------------------------------------- | :----: |
| Smart semantic search               | ✅     |    P0    | Backend + UI calls in inventory (`audit_artifacts/backend_endpoint_inventory.md`) |   —    |
| Match explanations surfaced         | ⚠️     |    P0    | `server/utils/search_explanations.py:*` + UI type `ui/src/api.ts:84–95`           |   M    |
| Face clustering + people management | ✅/⚠️  |    P0    | Many `/api/faces/*` used; key actions missing (A1)                                |  S–M   |
| Globe visualization                 | ✅     |    P1    | Three.js deps present (`ui/package.json`)                                         |   M    |
| Advanced scan directory             | ⚠️     |    P0    | Endpoint exists; UI not calling it                                                |   M    |
| Cache clear                         | ✅     |    P0    | Exposed via Performance UI (wired + verified build)                               |   XS   |

### N2. VLM Integration Roadmap

Evidence:

- Provider / model / execution matrix exists in docs: `docs/AI_MEDIA_USE_CASES_EXECUTION_PROVIDER_MATRIX.md` (present in workspace tree; see project structure).

Smallest viable fix:

- Create a single “VLM provider capability contract” doc + config schema (inputs/outputs, latency budgets, cost limits) and wire it to one feature (e.g., OCR VLM batch captioning) behind a feature flag.

---

## Prioritized Backlog

### P0 Blockers

|   # | Issue                                 | User Impact                      | Evidence                                                                                                                                                               | Fix (smallest viable)         | Effort |
| --: | ------------------------------------- | -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- | :----: |
|   1 | Desktop CSP validation + tightening   | Desktop security regression risk | Config: `src-tauri/tauri.conf.json:25–28`; artifacts: `audit_artifacts/tauri_csp_enabled_20251223_233200.txt`, `audit_artifacts/tauri_cargo_check_20251223_233420.txt` | Runtime smoke + tighten CSP   |   S    |
|   2 | Smart Search UX contradiction         | Confusing search behavior        | `ui/src/contexts/PhotoSearchContext.tsx:165–225`, `ui/src/components/layout/DynamicNotchSearch.tsx:417`                                                                | Auto vs Manual override       |   S    |
|   3 | Bundle too large / splitting blocked  | Slower UI, poorer interactivity  | `audit_artifacts/ui-build.txt`, `audit_artifacts/bundle-report.html`                                                                                                   | Fix imports + enforce budgets |   M    |
|   4 | Match explanations inconsistent in UI | Low trust in AI                  | `server/utils/search_explanations.py:*`, `ui/src/api.ts:84–95`                                                                                                         | Reusable “Why matched” UI     |   M    |

### P1 Critical

|   # | Issue                                  | User Impact                 | Evidence                                                            | Fix                                 | Effort |
| --: | -------------------------------------- | --------------------------- | ------------------------------------------------------------------- | ----------------------------------- | :----: |
|   1 | Advanced OCR UX integration fragmented | OCR feels “bolted on”       | `audit_artifacts/frontend_endpoints_called.txt` (`/api/ocr/*`)      | Unify entry point + results surface |   M    |
|   2 | Discovery (globe) performance unproven | Discovery may feel sluggish | `ui/package.json` + `audit_artifacts/discovery_20251223_155700.txt` | Add perf artifacts + tuning         |   M    |
|   3 | Frontend test coverage unclear         | Regressions slip into UI    | `audit_artifacts/typescript-errors.txt`                             | Add CI gate + smoke tests           |   M    |

### P2-P4

Summarized; expand after evidence passes in sections C–J.

---

## Refactoring Roadmap

### Phase 1: Surface Hidden Genius (Weeks 1-2)

**Goals:** Expose backend capabilities, confidence scores, match explanations.

| Task                              | Description                                         | Effort | Dependencies         |
| --------------------------------- | --------------------------------------------------- | :----: | -------------------- |
| ✅ Expose cache clear             | Wired `POST /api/cache/clear` into Performance UI   |   XS   | none                 |
| ✅ Expose advanced scan directory | Added Advanced Features entry point + started state |   XS   | job/status UX        |
| ✅ Face workflow completion       | Wired assign/create-person/crop + analytics panels  |   XS   | face panel UX        |
| Match explanation UX              | Build reusable component + badge standard           |   M    | result card plumbing |

### Phase 2: Search Quality (Weeks 3-4)

**Goals:** Improve NL understanding, relevance, speed.

### Phase 3: UI Polish (Weeks 5-6)

**Goals:** Glass consistency, responsive fixes, adaptive modes.

### Phase 4: Discovery (Weeks 7-8)

**Goals:** Globe optimization, gamification, exploration.

---

## Acceptance Criteria

### Definition of Done

- [ ] All P0 issues resolved
- [ ] Backend utilization ≥ 70%
- [ ] Search quality score ≥ 3.5/4
- [ ] Glass design consistency ≥ 3.5/4
- [ ] Accessibility score ≥ 3.0/4
- [ ] Test coverage ≥ 70%

---

## Appendices

### A. Tool Output Artifacts

- Discovery: `audit_artifacts/discovery_20251223_155700.txt`
- Endpoint inventory: `audit_artifacts/backend_endpoint_inventory.md`
- Utilization stats: `audit_artifacts/backend_endpoint_inventory_stats.txt`
- Frontend endpoint evidence: `audit_artifacts/frontend_endpoint_evidence.csv`
- Frontend endpoints called list: `audit_artifacts/frontend_endpoints_called.txt`
- UI build logs: `audit_artifacts/ui-build.txt`
- Bundle report: `audit_artifacts/bundle-report.html`
- Backend tests (green): `audit_artifacts/pytest_full_green_20251223_154836.txt`
- Tauri CSP enabled evidence: `audit_artifacts/tauri_csp_enabled_20251223_233200.txt`
- Tauri compile check (green): `audit_artifacts/tauri_cargo_check_20251223_233420.txt`

### B. Commands Reference

- Discovery command batch saved in: `audit_artifacts/discovery_20251223_155700.txt`
- Full pytest run (test mode) saved in: `audit_artifacts/pytest_full_green_20251223_154836.txt`

### C. Before/After Code Examples

- Included as backlog items (apply as small diffs during implementation sprints).

---

## Conclusion

### Summary

PhotoSearch v2 is already a real product skeleton with substantial backend and a capable UI. The fastest route to the stated vision (“2 perfect results in 2 seconds”) is not building net-new capability, but **surfacing what exists**: complete the people workflow, expose advanced scan/stats/caching controls, and make AI reasoning visible.

### Next Steps

1. **Week 1:** Desktop CSP runtime smoke test + search mode stability + bundle splitting fix.
2. **Weeks 2-4:** Surface match explanations + advanced scan directory polish + face workflow polish.
3. **Months 2-3:** Globe performance proof + gamification + accessibility hardening.

### Success Metrics

- Backend utilization: 63% → 70%+ (by exposing high-value endpoints)
- Search trust: increase via explanation badges + stable routing
- Desktop security: CSP enabled; minimal capabilities maintained

---

**Audit Completed:** 2025-12-23
**Total Issues:** P0: 4, P1: 3 (starter set; expand as evidence passes complete)
**Estimated Effort:** ~2–4 person-weeks for Phase 1, depending on UI polish depth
