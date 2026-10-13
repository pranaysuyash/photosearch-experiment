# Next 5 Must-Have Features Analysis

**Date**: 2025-12-17
**Context**: Post Core Baseline (4/5 complete)
**Status**: Ready for Selection

---

## 🎯 Recommended Next 5 Features

### Priority Tier 1: Complete Core Baseline

#### 1. **Albums** (Create, Add Photos, View) - P0 ⭐
**Why**: Last remaining P0 feature from Core Baseline
**User Value**: Essential organization tool - every photo app has this
**Complexity**: High (6-8 hours)
**Dependencies**: None

**Scope**:
- Create/rename/delete albums
- Add/remove photos from albums
- View album contents
- Set album cover photo
- Smart Albums (auto-generated based on rules)

**Backend Needs**:
- SQLite database tables (2 tables)
- 8 REST API endpoints
- Album CRUD operations
- Photo membership management

**Frontend Needs**:
- 6 new components (AlbumGrid, AlbumCard, AlbumDetail, etc.)
- Album picker dialog
- Integration with multi-select

---

### Priority Tier 2: UX Essentials (P1 from Roadmap)

#### 2. **Grid Zoom** (Dense ↔ Comfortable) - P1 🔍
**Why**: Critical for usability - users want control over grid density
**User Value**: See more photos at once OR see larger previews
**Complexity**: Low (1-2 hours)
**Dependencies**: None

**Scope**:
- 3 zoom levels: Dense (4 cols), Comfortable (3 cols), Spacious (2 cols)
- Smooth grid reflow on zoom change
- Persist zoom preference
- Keyboard shortcuts (+/-)

**Implementation**:
- CSS grid column adjustments
- State management in PhotoSearchContext
- LocalStorage persistence
- Animation on transition

#### 3. **Rotate/Flip** (Basic Edit) - P1 🔄
**Why**: Most common quick-fix operation users need
**User Value**: Fix orientation without opening external editor
**Complexity**: Medium (2-3 hours)
**Dependencies**: None

**Scope**:
- Rotate 90° CW/CCW
- Flip horizontal/vertical
- Apply to original file OR create new version
- Undo/redo support

**Backend Needs**:
- Image transformation endpoint (PIL/Pillow)
- File versioning (keep original)
- Update EXIF orientation tag

**Frontend Needs**:
- Rotate/flip buttons in PhotoDetail
- Preview during transformation
- Success/error feedback

---

### Priority Tier 3: Organization & Discovery (Phase 3)

#### 4. **Duplicate Detection** (Hash + Perceptual) - Phase 3 🔎
**Why**: High user value - everyone has duplicates
**User Value**: Free up storage, clean library
**Complexity**: Medium (3-4 hours)
**Dependencies**: None

**Scope**:
- Exact duplicates (MD5 hash comparison)
- Near duplicates (perceptual hash - dHash/pHash)
- Group similar photos (CLIP similarity)
- Review UI with side-by-side comparison
- Bulk delete duplicates

**Backend Needs**:
- Hash computation during scan
- Perceptual hash library (imagehash)
- Duplicate grouping algorithm
- `/duplicates` endpoint

**Frontend Needs**:
- Duplicates review page
- Side-by-side comparison
- Select master + delete others
- Progress indicator

#### 5. **Location Clustering** (Group by City/Country) - Phase 3 📍
**Why**: Leverage existing GPS data, natural organization
**User Value**: "Show me all photos from Paris"
**Complexity**: Medium (3-4 hours)
**Dependencies**: GPS metadata (already extracted)

**Scope**:
- Reverse geocoding (GPS → City/Country)
- Cluster photos by location
- Location-based smart albums
- Map view integration with PhotoGlobe

**Backend Needs**:
- Reverse geocoding API (OpenStreetMap Nominatim)
- Location clustering algorithm
- `/locations` endpoint
- Cache geocoding results

**Frontend Needs**:
- Locations page/sidebar
- Location-based filters
- PhotoGlobe location markers
- "Photos near here" feature

---

## 📊 Comparison Matrix

| Feature | Priority | Complexity | Time | User Impact | Tech Debt Risk |
|---------|----------|------------|------|-------------|----------------|
| **Albums** | P0 | High | 6-8h | 🟢 Critical | Low |
| **Grid Zoom** | P1 | Low | 1-2h | 🟢 High | None |
| **Rotate/Flip** | P1 | Medium | 2-3h | 🟢 High | Low |
| **Duplicates** | Phase 3 | Medium | 3-4h | 🟡 Medium | Medium |
| **Location Clustering** | Phase 3 | Medium | 3-4h | 🟡 Medium | Low |

**Total Estimated Time**: 15-21 hours

---

## 🎯 Alternative Sets (If Different Goals)

### Option A: "Complete Core Baseline ASAP"
1. Albums (P0) - 6-8h
2. Grid Zoom (P1) - 1-2h
3. Rotate/Flip (P1) - 1-2h
4. Multi-select improvements - 2h
5. Keyboard shortcuts - 2h

**Theme**: Finish all baseline features
**Total**: 12-16h

### Option B: "Organization & Discovery Focus"
1. Albums (P0) - 6-8h
2. Duplicate Detection - 3-4h
3. Location Clustering - 3-4h
4. Face Recognition - 6-8h
5. Smart Albums - 4-5h

**Theme**: Advanced photo management
**Total**: 22-29h

### Option C: "Quick Wins & Polish"
1. Grid Zoom (P1) - 1-2h
2. Rotate/Flip (P1) - 2-3h
3. Keyboard shortcuts - 2h
4. Export improvements - 2h
5. Performance optimizations - 3h

**Theme**: UX polish without heavy backend work
**Total**: 10-12h

---

## 🔍 Deep Dive: Recommended Set

### Feature 1: Albums (P0) ⭐

**Database Schema**:
```sql
CREATE TABLE albums (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  cover_photo_path TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  is_smart BOOLEAN DEFAULT FALSE,
  smart_rules JSON  -- For smart albums
);

CREATE TABLE album_photos (
  album_id TEXT REFERENCES albums(id) ON DELETE CASCADE,
  photo_path TEXT NOT NULL,
  added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  sort_order INTEGER DEFAULT 0,
  PRIMARY KEY (album_id, photo_path)
);
```

**API Endpoints**:
```python
POST   /albums                     # Create album
GET    /albums                     # List all albums
GET    /albums/{id}                # Get album details + photos
PUT    /albums/{id}                # Update album
DELETE /albums/{id}                # Delete album
POST   /albums/{id}/photos         # Add photos to album
DELETE /albums/{id}/photos         # Remove photos from album
PUT    /albums/{id}/cover          # Set cover photo
```

**Smart Album Rules**:
```json
{
  "type": "screenshots",
  "rules": [
    {"field": "filename", "operator": "contains", "value": "Screenshot"}
  ]
}
```

---

### Feature 2: Grid Zoom (P1) 🔍

**Implementation**:
```typescript
// ui/src/contexts/PhotoSearchContext.tsx
const [gridZoom, setGridZoom] = useState<'dense' | 'comfortable' | 'spacious'>('comfortable');

// ui/src/components/gallery/PhotoGrid.tsx
const getGridColumns = (zoom: string) => {
  switch (zoom) {
    case 'dense': return 'grid-cols-4';
    case 'comfortable': return 'grid-cols-3';
    case 'spacious': return 'grid-cols-2';
  }
};
```

**Keyboard Shortcuts**:
- `+` / `=` → Zoom in (more columns)
- `-` / `_` → Zoom out (fewer columns)
- `0` → Reset to default

---

### Feature 3: Rotate/Flip (P1) 🔄

**Backend**:
```python
# server/main.py
@app.post("/photos/transform")
async def transform_photo(req: TransformRequest):
    # req: { path, operation: 'rotate_cw' | 'rotate_ccw' | 'flip_h' | 'flip_v' }
    from PIL import Image
    img = Image.open(req.path)

    if req.operation == 'rotate_cw':
        img = img.rotate(-90, expand=True)
    elif req.operation == 'rotate_ccw':
        img = img.rotate(90, expand=True)
    elif req.operation == 'flip_h':
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    elif req.operation == 'flip_v':
        img = img.transpose(Image.FLIP_TOP_BOTTOM)

    # Save to new file or overwrite with backup
    backup_path = f"{req.path}.backup"
    shutil.copy(req.path, backup_path)
    img.save(req.path)

    return {"ok": True, "backup": backup_path}
```

---

### Feature 4: Duplicate Detection (Phase 3) 🔎

**Algorithm**:
```python
# Exact duplicates
import hashlib
def md5_hash(file_path):
    return hashlib.md5(open(file_path, 'rb').read()).hexdigest()

# Near duplicates (perceptual hash)
from imagehash import dhash
from PIL import Image
def perceptual_hash(file_path):
    return str(dhash(Image.open(file_path)))

# CLIP similarity for visual duplicates
# Already have CLIP embeddings - use cosine similarity
```

**UI Flow**:
1. Run duplicate scan
2. Show groups of similar photos
3. User selects master photo
4. Bulk delete others (with undo)

---

### Feature 5: Location Clustering (Phase 3) 📍

**Reverse Geocoding**:
```python
# Use Nominatim (free, no API key)
from geopy.geocoders import Nominatim

def reverse_geocode(lat, lon):
    geolocator = Nominatim(user_agent="living-museum")
    location = geolocator.reverse(f"{lat}, {lon}")
    return {
        "city": location.raw.get('address', {}).get('city'),
        "country": location.raw.get('address', {}).get('country')
    }
```

**Clustering**:
```python
from sklearn.cluster import DBSCAN
import numpy as np

# Cluster GPS coordinates
coords = np.array([[lat, lon] for lat, lon in gps_data])
clusters = DBSCAN(eps=0.5, min_samples=5).fit(coords)
```

---

## 🎨 Design System Extensions

### Albums
- Album cards: Glass-morphism with gradient overlay
- Album grid: Same layout as PhotoGrid
- Cover photo: Full-bleed background with text overlay
- Icon: 📁 Folder icon for regular albums, ⚡ Lightning for smart albums

### Grid Zoom
- Zoom control: Segmented control (Dense | Comfortable | Spacious)
- Location: Top-right of search bar, next to filters
- Icons: Grid icons with different densities

### Rotate/Flip
- Toolbar: Bottom of PhotoDetail (overlay)
- Buttons: Icon-only with tooltips
- Icons: 🔄 Rotate CW, 🔃 Rotate CCW, ⬌ Flip H, ⬍ Flip V

---

## 🚀 Implementation Order Recommendation

### Week 1: Complete Core Baseline
1. **Day 1-2**: Albums backend (database + API) - 6h
2. **Day 3**: Albums frontend (components) - 4h
3. **Day 4**: Smart Albums logic - 3h
4. **Day 5**: Grid Zoom + Rotate/Flip - 4h

**Outcome**: All P0 + P1 features complete

### Week 2: Organization Features
5. **Day 1**: Duplicate Detection - 4h
6. **Day 2**: Location Clustering - 4h
7. **Day 3**: Testing & polish - 4h

**Outcome**: Phase 3 Organization features delivered

---

## ❓ Questions for User

### 1. **Albums Priority**
- Should we do Albums first (complete Core Baseline)?
- Or skip to quick wins (Grid Zoom + Rotate)?

### 2. **Smart Albums Scope**
- Auto-generated only (Screenshots, Videos, etc.)?
- Or also user-defined rules (advanced)?

### 3. **Duplicate Detection**
- Just exact duplicates (hash)?
- Or also similar photos (perceptual hash)?
- CLIP-based visual similarity?

### 4. **Location Clustering**
- Use free OpenStreetMap (slower, rate-limited)?
- Or paid service (Google/Mapbox) for better accuracy?

### 5. **Rotate/Flip Behavior**
- Overwrite original (with backup)?
- Or create new version (keep original)?

---

## 📈 Success Metrics

### Albums
- [ ] Can create/rename/delete albums
- [ ] Can add/remove photos from albums
- [ ] Smart albums auto-populate
- [ ] Album covers display correctly
- [ ] Performance: <100ms to load album

### Grid Zoom
- [ ] 3 zoom levels work correctly
- [ ] Grid reflows smoothly
- [ ] Keyboard shortcuts work
- [ ] Zoom preference persists

### Rotate/Flip
- [ ] Rotation works correctly
- [ ] Flip works correctly
- [ ] Original preserved (or backed up)
- [ ] EXIF orientation updated

### Duplicates
- [ ] Finds exact duplicates
- [ ] Finds similar photos (if enabled)
- [ ] Side-by-side comparison works
- [ ] Bulk delete works with undo

### Location Clustering
- [ ] GPS → City/Country works
- [ ] Photos grouped by location
- [ ] Location filter works
- [ ] PhotoGlobe integration works

---

## 🎯 Recommendation

**Start with the recommended set**:
1. Albums (complete P0)
2. Grid Zoom (easy win)
3. Rotate/Flip (high user value)
4. Duplicate Detection (clean library)
5. Location Clustering (leverage GPS data)

This provides:
- ✅ Core Baseline 100% complete
- ✅ UX improvements (zoom, rotate)
- ✅ Organization features (duplicates, locations)
- ✅ Balanced complexity (mix of easy + hard)
- ✅ High user value across all features

**Estimated Total**: 15-21 hours across 5 features

---

**Document Version**: 1.0
**Last Updated**: 2025-12-17
