# Gemini Full Review - Photo Search Experiment

**Date**: 2025-12-08 21:13  
**Project**: Living Museum / Photo Search Experiment  
**Context**: User requests comprehensive review of all outstanding issues

---

## ❌ Critical Bugs

### 1. Photo Click Not Working After Search
- **Location**: Search results view
- **Expected**: Clicking a photo should open the PhotoDetail modal
- **Actual**: Nothing happens when clicking photos in search results
- **Files**: `App.tsx`, `PhotoGrid.tsx`, search result handlers
- **Priority**: HIGH

### 2. 3D View Toggle Not Working During Search
- **Location**: View toggle (Home/3D) when search is active
- **Expected**: Switching to 3D view should show globe with search results
- **Actual**: View doesn't switch when in search mode
- **Files**: `App.tsx`, view state management
- **Priority**: HIGH

### 3. Difficult to Open Images on Globe
- **Location**: `PhotoGlobe.tsx`
- **Expected**: Clicking photo markers on globe should open PhotoDetail
- **Actual**: Hard to click/select photos on the 3D globe
- **Cause**: Click target too small, raycasting issues
- **Priority**: MEDIUM

### 4. Globe Photo Markers Not Rotating With Globe
- **Location**: `PhotoGlobe.tsx`
- **Expected**: Photo dot markers should rotate with the Earth when it spins
- **Actual**: Markers stay stationary while globe rotates underneath
- **Cause**: Markers in separate group, not parented to globe mesh
- **Priority**: HIGH

### 5. Semantic Search Score/Cutoff Missing
- **Location**: `server/main.py`, `lancedb_store.py`
- **Expected**: Semantic search should show relevance scores and filter low-score results
- **Actual**: Score cutoff logic was removed or not working
- **Priority**: MEDIUM

---

## 🎨 Globe Visual Issues

### 6. Globe Needs Proper Earth Texture
- **Current**: Procedural blue/green shader (looks artificial)
- **Desired**: Realistic Earth with country boundaries
- **Options**:
  1. NASA Blue Marble texture (local file in `ui/public/`)
  2. Switch to `react-globe.gl` library (has countries built-in)
  3. GeoJSON country boundaries as 3D lines
- **Recommendation**: Download NASA texture, store locally, load via TextureLoader
- **Priority**: MEDIUM

---

## 🔍 Search Feature Gaps

### 7. Search Query Syntax
Users cannot currently search by:
- **Filename**: Need `filename:vacation.jpg` or `name:sunset`
- **Metadata values**: Need `width:>1920`, `format:JPEG`, `year:2024`
- **Date ranges**: Need `date:2024-01 to 2024-03`
- **File size**: Need `size:>5MB`
- **Location**: Need `near:Paris` or `gps:48.8,2.3`

### 8. Search Mode Clarity
UI should explain:
- **Metadata mode**: Exact match on filenames, paths, EXIF fields
- **Semantic mode**: AI understanding of image content ("sunset on beach")
- **Hybrid mode**: Combines both (recommended default)

---

## 🎯 UI/UX Issues

### 9. Timeline Visibility (SonicTimeline)
- Text appears cut off in some cases
- Bars need better labeling/formatting
- Consider making purpose clearer (photo count by date)

### 10. Home Page Default Display
- Needs to show ALL photos by default (currently working after fix)
- Limit should be increased or pagination added

---

## 📁 Files to Review

```
# Frontend
ui/src/App.tsx                    - Main state, view switching, photo selection
ui/src/components/PhotoGrid.tsx   - Grid view click handlers  
ui/src/components/PhotoGlobe.tsx  - 3D globe, markers, interactions
ui/src/components/StoryMode.tsx   - Home view click handlers
ui/src/components/PhotoDetail.tsx - Photo detail modal
ui/src/components/SonicTimeline.tsx - Timeline bar visualization
ui/src/hooks/usePhotoSearch.ts    - Search hook

# Backend
server/main.py                    - API endpoints, search logic
server/lancedb_store.py           - Vector search, score cutoffs
metadata_search.py                - Metadata database queries
```

---

## ✅ Recently Completed

1. ✅ Consolidated 1060 media files into `media/` folder
2. ✅ Added comprehensive metadata extraction (audio, PDF, SVG, HEIC)
3. ✅ PhotoDetail shows ALL metadata fields
4. ✅ Server returns full metadata from SQLite for search results
5. ✅ Home page displays photos by default (semantic mode with empty query)

---

## 🔧 Recommended Fix Priority

1. **Photo click** in search results - blocking user flow
2. **Globe markers** not rotating - visual bug, confusing
3. **View toggle** during search - blocking navigation
4. **Globe Earth texture** - aesthetic improvement
5. **Search score cutoff** - quality improvement
6. **Globe click targets** - usability improvement
7. **Search syntax** - feature enhancement
