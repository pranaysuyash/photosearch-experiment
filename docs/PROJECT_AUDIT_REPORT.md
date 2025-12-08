# Project Audit Report: Living Museum (PhotoSearch Experiment)

**Date**: 2025-12-08  
**Auditor**: Gemini  
**Status**: Beta (Functional Core, UX Gaps)

---

## 1. Where We Were Supposed To Be (Goals)

According to `ROADMAP.md`, we aim for a "Phase 1 - UX & API Polishing" state:
- ✅ **Secure local runs:** Thumbnails served, local execution works.
- 🚧 **Background Task Queue:** Mentions Redis/Celery. **Current Status**: Implemented as simple `BackgroundTasks` in FastAPI. No robust job queue yet.
- 🚧 **Feedback UI:** "Progress UI hook". **Current Status**: Basic job ID returned, but full progress bar/polling UI not fully polished.
- ✅ **Metadata:** goal was comprehensive. **Current Status**: **Exceeded Expectations**. Extractor now handles Audio, PDF, SVG, etc.

## 2. Where We Stand (Current Architecture)

### Backend (`server/`)
- **Framework**: FastAPI (Solid, well-structured).
- **Search**: Hybrid approach.
    - `metadata`: SQLite-based (Reliable).
    - `semantic`: LanceDB + CLIP (Working, but recent "cutoff" logic regression needs fix).
- **Metadata**: `metadata_extractor.py` is robust and feature-rich.
- **Issues**:
    - `main.py` has a simple "sync" loading of checking embeddings on startup which slows down large library restarts.
    - No true "Job Queue" persistence (if server dies, background tasks die).

### Frontend (`ui/src/`)
- **Framework**: React + Vite + Tailwind + Framer Motion.
- **3D Globe**: `react-three-fiber`.
    - **Visuals**: Currently procedural (looks "game-y"). Needs realistic texture.
    - **Bug**: Markers do not rotate with the Earth.
- **Search UI**:
    - **Bug**: Clicking photos in search results does nothing.
    - **Bug**: View toggle (List/Globe) often mistakenly disabled or ineffective during search.

---

## 3. Critical Issues & Blockers

| ID | Issue | Severity | Status |
|----|-------|----------|--------|
| **BUG-01** | **Photo Click Dead**: Search result cards are not clickable. | 🔴 Critical | Ready to Fix |
| **BUG-02** | **Globe Markers**: Dots float in space, don't rotate with Earth. | 🔴 Critical | Ready to Fix |
| **BUG-03** | **View Switching**: Toggle breaks when search is active. | 🟠 High | Ready to Fix |
| **VIS-01** | **Globe Texture**: Procedural noise instead of Earth map. | 🟠 High | Solution Proposed |
| **INF-01** | **Job Queue**: Missing robust async queue (using FastAPI BackgroundTasks). | 🟡 Medium | Phase 2 Item |

---

## 4. Road to "Release Candidate"

To consider this "feature complete" for Phase 1:

1.  **Fix Interaction Loop**: Search -> Click -> Detail View -> Back. (Must work 100%).
2.  **Fix 3D Visualization**: Globe must look real and markers must stick to countries.
3.  **Refine Search**:
    -   Restore "Score Cutoff" (don't show 50% matches).
    -   Default to "Hybrid" or "Semantic" (users don't understand "Metadata" vs "Semantic").
4.  **Consolidated UI**: Ensure Timeline, Map, and Grid work harmoniously.

## 5. Next Steps (Immediate)

1.  **Fix BUG-01 & BUG-03**: Restore basic navigation flow.
2.  **Fix BUG-02 & VIS-01**: Revamp `PhotoGlobe` (Fix rotation grouping, load NASA texture).
3.  **Restore Search Quality**: Re-introduce score threshold in `main.py`.

---

**Recommendation**: Proceed immediately to **Phase 2 Execution** to fix the Critical Bugs (1, 2, 3).
