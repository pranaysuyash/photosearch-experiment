# Gemini Code Review Request

## Context
This is a **local-first photo management app** with semantic search capabilities. Built with:
- **Frontend**: React + TypeScript + Vite + TailwindCSS
- **Backend**: FastAPI + SQLite (metadata) + LanceDB (vectors)
- **AI**: CLIP embeddings for semantic image search

## Recent Changes That Need Review

### 1. `usePhotoSearch` Hook - Infinite Scroll Fix
**File**: `ui/src/hooks/usePhotoSearch.ts`

**Problem Fixed**: Infinite API calls with `offset=0` causing request storms.

**Review Questions**:
1. Is the ref-based approach correct for preventing stale closures?
2. Will the `initialFetchDoneRef` pattern cause issues if the component remounts?
3. Is there a race condition between `doSearch` and `loadMore`?
4. Should we use `useSyncExternalStore` instead of refs for better React 18 compatibility?

```typescript
// Key pattern to review:
const optionsRef = useRef(options);
optionsRef.current = options; // Update on every render

const doSearch = useCallback(async (...) => {
  const opts = optionsRef.current; // Read from ref
}, []); // NO dependencies
```

---

### 2. Search Mode Architecture
**Files**: `ui/src/App.tsx`, `server/main.py`

**Current Behavior**:
- Default mode is `metadata` (returns all 1067 files)
- User can switch to `semantic` for AI search

**Review Questions**:
1. Is it better to auto-switch modes? (metadata when query empty, semantic when typing)
2. Should we preload semantic results when the user starts typing?
3. Is the hybrid search mode worth keeping or should we simplify?

---

### 3. Backend Search Performance
**File**: `server/main.py` (lines 334-375)

**Current Behavior**:
- Empty query: Direct SQLite query to get ALL files
- With query: Use QueryEngine for filtering

**Review Questions**:
1. For 10k+ photos, should we paginate at the database level instead of Python slicing?
2. Is the `apply_sort` function sorting efficiently? Should sorting be pushed to SQL?
3. Should we cache the "all photos" result for browsing mode?

```python
# Current approach - review for scale:
cursor.execute("SELECT file_path, metadata_json FROM metadata")
results = []
for row in cursor.fetchall():
    results.append({...})  # All in memory
```

---

### 4. IntersectionObserver Memory Leak Risk
**File**: `ui/src/components/StoryMode.tsx`

**Review Questions**:
1. Is the `IntersectionObserver` properly cleaned up on unmount?
2. Should we use a ref instead of `document.getElementById` for the sentinel element?
3. Is infinite scroll triggering correctly when `hasMore` becomes false?

---

### 5. UI State Consistency
**Files**: `ui/src/App.tsx`, `ui/src/components/BigSearchHero.tsx`

**Review Questions**:
1. Is the conditional rendering between BigSearchHero and compact header smooth?
2. Are the Framer Motion `layoutId` animations causing layout shifts?
3. Is `showBigHero` logic correct: `photos.length === 0 && !loading && viewMode === 'story'`?

---

## Specific Code Areas to Audit

### Critical Files
1. `ui/src/hooks/usePhotoSearch.ts` - Core data fetching logic
2. `ui/src/App.tsx` - Main app state and routing
3. `server/main.py` - API endpoints (especially `/search`)
4. `ui/src/components/StoryMode.tsx` - Photo grid and infinite scroll

### Things to Check
- [ ] React hooks rules violations
- [ ] Missing useCallback/useMemo causing re-renders
- [ ] API error handling completeness
- [ ] TypeScript type safety (any loose `any` types?)
- [ ] Memory leaks (observers, event listeners, timers)
- [ ] Race conditions in async operations

---

## Questions for Gemini

1. **Architecture**: Is the separation between metadata search and semantic search clean? Should they be combined?

2. **State Management**: We're using local state + refs. Would Zustand/Jotai be better for this complexity?

3. **Performance**: With 1000+ photos loading, what virtualization approach would you recommend? (react-window, react-virtuoso, tanstack-virtual)

4. **Error Boundaries**: Are we handling errors consistently? What patterns should we adopt?

5. **Testing**: What test coverage would you prioritize? Unit tests for hooks? E2E for search flow?

---

## How to Run

```bash
# Backend
cd /Users/pranay/Projects/photosearch_experiment
source .venv/bin/activate
python3 -m server.main

# Frontend
cd ui
npm run dev
```

App runs at http://localhost:5173, API at http://127.0.0.1:8000
