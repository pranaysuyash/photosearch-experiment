# Feature Analysis & Implementation Plan
**Date**: 2025-12-17
**Analyst**: Claude
**Status**: Analysis Complete - Ready for Implementation

---

## Executive Summary

After analyzing the project documentation (ROADMAP.md, PROJECT_AUDIT_REPORT.md, USER_FLOWS.md, API_SPEC.md) and the current codebase, I've identified that the app is a **media management system with AI-powered semantic search and 3D globe visualization** called "Living Museum".

The app has completed **Phase 0, 1, and 2**, with basic functionality in place. According to the roadmap, we're currently in the **Core Baseline** phase where essential media management features need to be implemented.

---

## Selected 5 Must-Have Features for Implementation

Based on the roadmap's **Core Baseline** section (P0 priority) and the documented user flows, I've selected these 5 features:

### ✅ 1. **Sort By** (Date/Name/Size) - P0
**Status**: UI EXISTS, Backend PARTIAL SUPPORT
- **Design Language Alignment**: ✅ Uses existing `btn-glass` glass-morphism design
- **Component**: `SortControls.tsx` exists with 4 sort options
- **API**: Frontend sends `sort_by` parameter to `/search` endpoint
- **Backend**: Needs verification of full implementation

### ✅ 2. **Filter by Media Type** (Photos/Videos/All) - P0
**Status**: UI EXISTS, Backend PARTIAL SUPPORT
- **Design Language Alignment**: ✅ Uses existing glass-morphism buttons
- **Component**: `MediaTypeFilter.tsx` exists with 3 filter options
- **API**: Frontend sends `type_filter` parameter to `/search` endpoint
- **Backend**: Needs verification of filter logic

### ✅ 3. **Favorites** (Star toggle with filter) - P0
**Status**: BACKEND EXISTS, UI COMPONENTS EXIST, INTEGRATION NEEDED
- **Design Language Alignment**: ✅ Uses glass-morphism design
- **Components**:
  - `FavoritesToggle.tsx` - Star button component
  - `FavoritesFilter.tsx` - Filter UI component
- **API**: Full backend implementation exists:
  - `POST /favorites/toggle` ✅
  - `GET /favorites` ✅
  - `GET /favorites/check` ✅
  - `DELETE /favorites` ✅
  - `POST /bulk/favorite` ✅
- **Frontend Integration**: `api.ts` has all methods defined
- **Missing**: Integration into PhotoGrid/PhotoDetail

### ❌ 4. **Delete/Trash** - P0
**Status**: BACKEND EXISTS, UI MISSING
- **API**: Backend implementation exists:
  - `POST /bulk/delete` ✅ (requires `confirm: true`)
- **Frontend Integration**: `api.ts` has `deletePhotos()` method
- **Missing**:
  - UI components for delete action
  - Confirmation dialog
  - Multi-select integration
  - Trash/undo functionality

### ❌ 5. **Albums/Collections** - P0
**Status**: NOT IMPLEMENTED
- **Backend**: No API endpoints exist
- **Frontend**: No UI components exist
- **Scope**:
  - Create album
  - Add/remove photos from album
  - View album
  - Delete album
  - Album metadata (name, description, cover photo)

---

## Implementation Status Matrix

| Feature | UI Component | API Client | Backend API | Integration | Priority |
|---------|-------------|------------|-------------|-------------|----------|
| Sort By | ✅ EXISTS | ✅ EXISTS | ⚠️ VERIFY | ⚠️ PARTIAL | P0 |
| Media Type Filter | ✅ EXISTS | ✅ EXISTS | ⚠️ VERIFY | ⚠️ PARTIAL | P0 |
| Favorites | ✅ EXISTS | ✅ EXISTS | ✅ COMPLETE | ❌ MISSING | P0 |
| Delete/Trash | ❌ MISSING | ✅ EXISTS | ✅ COMPLETE | ❌ MISSING | P0 |
| Albums | ❌ MISSING | ❌ MISSING | ❌ MISSING | ❌ MISSING | P0 |

---

## Detailed Feature Analysis

### Feature 1: Sort By (Date/Name/Size) ✅

**Current Implementation:**
```typescript
// ui/src/components/gallery/SortControls.tsx
const SORT_OPTIONS = [
  { value: 'date_desc', label: 'Newest First', icon: Calendar },
  { value: 'date_asc', label: 'Oldest First', icon: Calendar },
  { value: 'name', label: 'Name (A-Z)', icon: FileText },
  { value: 'size', label: 'Size (Largest)', icon: HardDrive },
]
```

**Integration Points:**
- ✅ Component exists and follows design system
- ✅ Uses glass-morphism styling (`btn-glass`, `btn-glass--muted`)
- ✅ Frontend sends `sort_by` to API
- ⚠️ Need to verify backend sorting logic in `/search` endpoint

**Action Required:**
1. Verify backend implementation in `server/main.py` line 397
2. Test sort functionality end-to-end
3. If backend incomplete, implement sorting in query logic

---

### Feature 2: Filter by Media Type (Photos/Videos/All) ✅

**Current Implementation:**
```typescript
// ui/src/components/gallery/MediaTypeFilter.tsx
const TYPE_FILTERS = [
  { value: 'all', label: 'All', icon: Layers },
  { value: 'photos', label: 'Photos', icon: Image },
  { value: 'videos', label: 'Videos', icon: Video },
]
```

**Integration Points:**
- ✅ Component exists with proper design language
- ✅ Uses pill-style buttons with glass effect
- ✅ Frontend sends `type_filter` to API
- ⚠️ Need to verify backend filtering logic

**Action Required:**
1. Verify backend implementation in `/search` endpoint
2. Test filter combinations (e.g., filter + sort + search)
3. Ensure proper MIME type detection

---

### Feature 3: Favorites (Star Toggle) ✅⚠️

**Current Implementation - Backend:**
```python
# server/main.py
@app.post("/favorites/toggle")  # Toggle favorite status
@app.get("/favorites")          # Get all favorites
@app.get("/favorites/check")    # Check if file is favorited
@app.delete("/favorites")       # Remove favorite
@app.post("/bulk/favorite")     # Bulk add/remove
```

**Current Implementation - Frontend:**
```typescript
// ui/src/components/gallery/FavoritesToggle.tsx
export function FavoritesToggle({
  isFavorited,
  onToggle,
  className = '',
}: FavoritesToggleProps)

// ui/src/components/gallery/FavoritesFilter.tsx
// Filter component to show all/favorites only/non-favorites
```

**Integration Gaps:**
1. ❌ PhotoGrid doesn't show favorite stars on thumbnails
2. ❌ PhotoDetail doesn't have favorite toggle
3. ❌ No state management for favorite status
4. ❌ FavoritesFilter not integrated into search flow

**Action Required:**
1. Add favorite toggle to PhotoDetail modal
2. Add favorite badge/star overlay to PhotoGrid items
3. Integrate FavoritesFilter into main search/filter bar
4. Add optimistic updates for favorite toggle
5. Implement state persistence (check on load, update on toggle)

**Design Considerations:**
- Use existing yellow star icon (matches Figma: `fill-yellow-400`)
- Place toggle in PhotoDetail header (top-right)
- Show subtle star badge on grid thumbnails (top-right corner)
- Maintain glass-morphism aesthetic

---

### Feature 4: Delete/Trash ❌

**Current Implementation - Backend:**
```python
# server/main.py line 778
@app.post("/bulk/delete")
async def bulk_delete(req: BulkDeleteRequest):
    # Requires confirm: true to proceed
    # Returns deleted count
```

**Current Implementation - Frontend:**
```typescript
// ui/src/api.ts line 349
deletePhotos: async (filePaths: string[], confirm: boolean = false) => {
  const res = await apiClient.post('/bulk/delete', {
    file_paths: filePaths,
    confirm,
  });
  return res.data;
}
```

**Missing Components:**
1. ❌ Delete button in PhotoDetail
2. ❌ Multi-select delete action
3. ❌ Confirmation dialog component
4. ❌ Trash/undo mechanism
5. ❌ Visual feedback after deletion

**Implementation Plan:**

**Phase 1 - Basic Delete:**
1. Add delete button to PhotoDetail (Trash icon)
2. Create confirmation dialog using glass-morphism design
3. Wire up single-photo delete
4. Remove deleted photo from grid immediately

**Phase 2 - Multi-select Delete:**
1. Integrate with existing multi-select system (if exists)
2. Add bulk delete action in ActionsPod
3. Show count of selected items to delete
4. Batch delete API call

**Phase 3 - Trash/Undo:**
1. Implement soft delete (move to trash)
2. Add 5-second undo toast notification
3. Add "Recently Deleted" view
4. Permanent delete after 30 days

**Design System Integration:**
- Use Lucide `Trash2` icon
- Red accent color for destructive actions: `text-red-400/80 hover:text-red-400`
- Glass-morphism dialog: `glass-panel` with backdrop blur
- Confirmation requires explicit "Delete" button click
- Cancel button should be prominent

---

### Feature 5: Albums/Collections ❌

**Status**: Complete Greenfield Implementation Required

**Feature Requirements** (from USER_FLOWS.md & roadmap):
1. Create album with name and optional description
2. Add/remove photos to/from albums
3. View album contents in grid
4. Album cover photo (auto or manual selection)
5. Delete album (keep photos)
6. Search within album
7. Album metadata (created date, photo count)

**Database Schema Needed:**
```sql
-- Albums table
CREATE TABLE albums (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  cover_photo_path TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Album membership junction table
CREATE TABLE album_photos (
  album_id TEXT REFERENCES albums(id) ON DELETE CASCADE,
  photo_path TEXT NOT NULL,
  added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  sort_order INTEGER DEFAULT 0,
  PRIMARY KEY (album_id, photo_path)
);
```

**Backend API Endpoints Needed:**
```python
POST   /albums                     # Create album
GET    /albums                     # List all albums
GET    /albums/{id}                # Get album details + photos
PUT    /albums/{id}                # Update album (name, description)
DELETE /albums/{id}                # Delete album
POST   /albums/{id}/photos         # Add photos to album
DELETE /albums/{id}/photos         # Remove photos from album
PUT    /albums/{id}/cover          # Set cover photo
GET    /albums/{id}/search         # Search within album
```

**Frontend Components Needed:**
1. `AlbumGrid.tsx` - Grid view of all albums
2. `AlbumCard.tsx` - Album tile with cover, name, count
3. `AlbumDetail.tsx` - Album view with PhotoGrid
4. `CreateAlbumDialog.tsx` - Create/edit album modal
5. `AddToAlbumDialog.tsx` - Multi-select add to album
6. `AlbumPicker.tsx` - Select album from list

**Implementation Plan:**

**Phase 1 - Backend Foundation:**
1. Create database schema in LanceDB or separate SQLite
2. Implement CRUD API endpoints
3. Add album photos management endpoints
4. Write unit tests

**Phase 2 - Basic UI:**
1. Add "Albums" section to navigation
2. Create AlbumGrid page showing all albums
3. Implement AlbumCard with glass-morphism design
4. Add "Create Album" floating action button

**Phase 3 - Album Management:**
1. AlbumDetail page with PhotoGrid integration
2. Add to album from PhotoDetail (single)
3. Multi-select "Add to Album" action
4. Set cover photo functionality

**Phase 4 - Polish:**
1. Drag-and-drop reordering within album
2. Album search and filters
3. Smart albums (auto-generated based on rules)
4. Album sharing (future scope)

**Design System Integration:**
- Albums use same grid layout as PhotoGrid
- Album cards: glass-morphism with gradient overlay
- Cover photo as background with text overlay
- Photo count badge (top-right): `glass-panel` with `text-xs`
- Create album button: floating action button (bottom-right)
- Navigation: Add "Albums" icon to ModeRail

**Estimated Complexity**: HIGH
- New database tables
- 8 new API endpoints
- 6 new UI components
- State management for album membership
- Integration with existing multi-select system

---

## Design System Consistency Check

All proposed implementations maintain the existing design language:

### Glass-Morphism Components (`glass.ts` design tokens)
```typescript
// Existing design system
.glass-panel = backdrop-blur-xl bg-white/10 border border-white/20
.btn-glass = backdrop-blur-md bg-white/5 hover:bg-white/10
.btn-glass--primary = accent color with glass effect
.btn-glass--muted = subtle gray with glass effect
```

### Color Palette
- Primary: Purple/Blue gradients
- Success: Green (`text-green-400`)
- Warning: Yellow (`text-yellow-400`)
- Danger: Red (`text-red-400`)
- Muted: Gray with opacity

### Typography
- Headlines: `text-4xl font-semibold`
- Body: `text-base font-normal`
- Captions: `text-xs text-muted-foreground`

### Icons
- Library: Lucide React icons
- Consistent sizing: `size={16}` for buttons, `size={20}` for headers

---

## Integration with Existing Systems

### Multi-Select System
- Used by bulk export (verified in code)
- Delete and Favorites need to integrate with this
- Albums "Add to Album" needs multi-select

### PhotoDetail Modal
- Favorite toggle (top-right)
- Delete button (action menu)
- Add to album (action menu)

### ActionsPod/ContextMenu
- Bulk actions when items selected
- Delete, favorite, add to album

### SearchContext
- Filters need to trigger search refresh
- Sort needs to update query parameters
- State management for filter/sort persistence

---

## Questions for User

Before implementation, I need clarification on these decisions:

### 1. **Delete Behavior - Soft or Hard Delete?**
   - **Option A**: Immediate permanent deletion (simpler, dangerous)
   - **Option B**: Move to trash with 30-day retention (safer, requires trash management)
   - **Option C**: Move to trash with manual empty (macOS style)

### 2. **Albums Storage - Where to persist?**
   - **Option A**: Separate SQLite database (simpler, separate from vectors)
   - **Option B**: LanceDB metadata (keep everything in vector store)
   - **Option C**: JSON files in `.living-museum/albums/` (portable, no DB)

### 3. **Favorites Storage - Current Implementation?**
   - Need to verify: Is favorites data in LanceDB, SQLite, or filesystem?
   - This affects Albums implementation decision

### 4. **Albums Scope - Smart Albums?**
   - Should initial release include smart albums (auto-populated by rules)?
   - Or just manual albums for MVP?

### 5. **Multi-Select UI - Current Status?**
   - Is multi-select already implemented in PhotoGrid?
   - Or do we need to implement selection mode?

### 6. **Priority Order - Which 3 to implement first?**
   Given time constraints:
   - **Favorites Integration** (80% done, highest ROI)
   - **Delete** (medium complexity, critical feature)
   - **Albums** (highest complexity, can be Phase 2)
   - Sort/Filter (verify and fix if broken)

---

## Implementation Recommendations

### **Immediate Actions (This Session):**

1. ✅ **Verify Sort & Filter Backend** (30 min)
   - Read `/search` endpoint implementation
   - Test with real queries
   - Fix any bugs

2. ✅ **Integrate Favorites** (2 hours)
   - Add toggle to PhotoDetail
   - Add filter to search bar
   - Implement state management
   - Test end-to-end

3. ⚠️ **Implement Delete (Basic)** (2 hours)
   - Add delete button to PhotoDetail
   - Create confirmation dialog
   - Wire up API call
   - Handle grid refresh

### **Next Session:**

4. **Implement Delete (Multi-select)** (1 hour)
5. **Delete Trash/Undo** (2 hours)
6. **Albums Backend** (3-4 hours)
7. **Albums Frontend** (4-5 hours)

---

## Technical Debt Notes

### Items to Address During Implementation:

1. **Error Handling**: Add proper error boundaries around delete/favorite operations
2. **Optimistic Updates**: Implement for better UX (show change before API confirms)
3. **Loading States**: Add skeleton loaders for album grids
4. **Accessibility**: Ensure keyboard navigation for all new components
5. **Analytics**: Track favorite/delete/album actions for usage insights
6. **Testing**: Add integration tests for CRUD operations
7. **Documentation**: Update API_SPEC.md with new endpoints

---

## Success Criteria

### For Each Feature:

**Sort By:**
- [ ] Backend correctly sorts by all 4 options
- [ ] UI updates without page refresh
- [ ] Sort persists across page navigation
- [ ] Works with filters and search

**Media Type Filter:**
- [ ] Correctly filters photos vs videos
- [ ] Handles mixed metadata edge cases
- [ ] Works with sort and search
- [ ] Performance acceptable on large libraries

**Favorites:**
- [ ] Toggle works in PhotoDetail
- [ ] Star visible in PhotoGrid
- [ ] Filter shows only favorites
- [ ] State persists across sessions
- [ ] Bulk favorite works

**Delete:**
- [ ] Single delete with confirmation
- [ ] Multi-select delete
- [ ] Undo functionality (5 seconds)
- [ ] Grid updates immediately
- [ ] Deleted items not in search results

**Albums:**
- [ ] Create/edit/delete albums
- [ ] Add/remove photos
- [ ] View album contents
- [ ] Set cover photo
- [ ] Search within album
- [ ] Performance: <100ms to load album
- [ ] UI matches design system

---

## Appendix: Code Locations

### Frontend
- **Components**: `/ui/src/components/gallery/`
- **API Client**: `/ui/src/api.ts`
- **Design System**: `/ui/src/design/glass.ts`
- **State**: `/ui/src/contexts/PhotoSearchContext.tsx`

### Backend
- **Main API**: `/server/main.py`
- **Database**: `/server/lancedb_store.py`
- **Config**: `/server/config.py`

### Docs
- **Roadmap**: `/docs/ROADMAP.md`
- **User Flows**: `/docs/USER_FLOWS.md`
- **API Spec**: `/docs/API_SPEC.md`

---

## Next Steps

1. **Get User Feedback** on questions above
2. **Prioritize 3 features** for immediate implementation
3. **Verify backend** sort and filter implementation
4. **Implement favorites integration** (highest ROI)
5. **Create detailed technical specs** for albums

---

**Document End**
