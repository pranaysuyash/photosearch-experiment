# Metadata Enhancement Implementation Plan

**Created**: 2025-12-29
**Branch**: To be determined (suggest: `feature/metadata-enhancement`)
**Status**: Planning Phase
**Priority**: High (Post Face Recognition merge)

---

## Executive Summary

After completing Face Recognition, the next high-value feature is **Enhanced Metadata Search**. This builds on existing infrastructure (`metadata_extractor.py`, `metadata_search.py`) to provide comprehensive searchable metadata similar to professional tools like Adobe Lightroom and Capture One.

**Strategic Value:**
- Complements Face Recognition with rich technical search
- Differentiates from Google Photos/Apple Photos with professional-grade metadata
- Enables power users and photographers to find photos by camera settings
- Foundation for future Analytics Dashboard

---

## Current State Assessment

### ✅ What We Have

**Comprehensive Extraction** (`src/metadata_extractor.py`):
- ✅ EXIF data (all tags including MakerNote)
- ✅ GPS coordinates with decimal conversion
- ✅ Image properties (resolution, color space, ICC profiles)
- ✅ Video properties (ffprobe integration)
- ✅ Audio metadata (mutagen support)
- ✅ PDF, SVG, HEIC support
- ✅ File hashes (MD5, SHA256)
- ✅ Extended attributes (xattr)

**Search Infrastructure** (`src/metadata_search.py`):
- ✅ SQLite database with versioning
- ✅ Query engine with shortcuts (`camera:Canon`, `size:>5MB`)
- ✅ Batch extraction with change detection
- ✅ Version history tracking
- ✅ Favorites system

**Integration**:
- ✅ Used in `server/main.py` (line 196-200) for new file indexing
- ✅ Auto-scan on startup
- ✅ Real-time file watcher integration

### ❌ What's Missing

1. **Limited EXIF field coverage in database** - Only basic fields stored
2. **No UI for metadata browsing** - Extraction happens, but UI doesn't expose it
3. **No advanced search filters** - Can't search by ISO, aperture, lens, etc.
4. **No metadata editor** - Can't bulk edit or fix metadata
5. **No autocomplete for technical fields** - Hard to discover searchable values
6. **Camera/Lens database** - No normalization (Canon vs CANON)

---

## Implementation Phases

## Phase 1: Enhanced Metadata Extraction & Storage (3-4 days)

### Goal
Store all extracted metadata fields in searchable database columns.

### Tasks

#### 1.1 Database Schema Extension
**File**: `server/schema_extensions.py`

Add new columns to `metadata` table (or create `photo_metadata_extended` table):

```sql
-- Camera & Lens
camera_make TEXT,
camera_model TEXT,
lens_model TEXT,
lens_make TEXT,

-- Exposure Settings
iso INTEGER,
aperture REAL,           -- f-number (e.g., 2.8)
shutter_speed TEXT,      -- e.g., "1/250"
shutter_speed_decimal REAL,  -- For range queries
exposure_compensation REAL,
exposure_mode TEXT,
exposure_program TEXT,
metering_mode TEXT,

-- Focal Length
focal_length REAL,       -- in mm
focal_length_35mm INTEGER,  -- 35mm equivalent

-- Flash
flash_used BOOLEAN,
flash_mode TEXT,

-- White Balance
white_balance TEXT,
color_temperature INTEGER,

-- Image Quality
image_quality TEXT,      -- RAW, JPEG, etc.
color_space TEXT,        -- sRGB, AdobeRGB, etc.
bit_depth INTEGER,

-- Software
software TEXT,
edit_software TEXT,

-- Copyright & Attribution
copyright TEXT,
creator TEXT,
creator_tool TEXT,

-- Composite Fields (calculated)
exposure_triangle TEXT,  -- "ISO 400, f/2.8, 1/250" for quick display
searchable_text TEXT     -- Full-text search index
```

**Migration**: Create migration script to add columns without data loss.

#### 1.2 Metadata Mapper
**File**: `server/metadata_mapper.py` (NEW)

```python
class MetadataMapper:
    """
    Maps raw EXIF/metadata to database columns.
    Handles:
    - Field normalization (Canon vs CANON)
    - Unit conversions (shutter speed to decimal)
    - Composite field generation
    """

    def map_camera_metadata(self, raw_exif: dict) -> dict:
        """Extract camera-specific fields"""

    def normalize_camera_make(self, make: str) -> str:
        """Normalize camera manufacturer names"""

    def parse_shutter_speed(self, shutter: str) -> tuple[str, float]:
        """Convert shutter speed to display + decimal"""

    def build_exposure_triangle(self, iso: int, aperture: float, shutter: str) -> str:
        """Create human-readable exposure summary"""
```

#### 1.3 Update Extraction Pipeline
**File**: `src/metadata_extractor.py`

Modify `extract_all_metadata()` to include new mapping:

```python
def extract_all_metadata(filepath: str) -> Dict[str, Any]:
    # ... existing extraction ...

    # NEW: Map to searchable fields
    from server.metadata_mapper import MetadataMapper
    mapper = MetadataMapper()

    metadata['searchable_fields'] = mapper.map_camera_metadata(
        metadata.get('exif', {})
    )

    return metadata
```

#### 1.4 Update Storage
**File**: `src/metadata_search.py`

Update `MetadataDatabase.store_metadata()` to extract and store new fields:

```python
def store_metadata(self, filepath: str, metadata: Dict[str, Any]) -> bool:
    # ... existing code ...

    # Extract searchable fields
    searchable = metadata.get('searchable_fields', {})

    cursor.execute("""
        INSERT OR REPLACE INTO metadata_extended (
            file_path, camera_make, camera_model, iso, aperture, ...
        ) VALUES (?, ?, ?, ?, ?, ...)
    """, (
        filepath,
        searchable.get('camera_make'),
        searchable.get('camera_model'),
        searchable.get('iso'),
        searchable.get('aperture'),
        ...
    ))
```

**Testing**:
- Unit tests for MetadataMapper
- Integration test: scan folder → verify database columns populated
- Test with various camera manufacturers (Canon, Nikon, Sony, Fuji)

---

## Phase 2: Search API & Autocomplete (2-3 days)

### Goal
Expose metadata fields via REST API with autocomplete support.

### Tasks

#### 2.1 Metadata Fields Endpoint
**File**: `server/api/routers/metadata.py` (NEW)

```python
from fastapi import APIRouter, Query
from typing import List, Optional

router = APIRouter(prefix="/api/metadata", tags=["metadata"])

@router.get("/fields")
def get_available_fields():
    """
    Get list of all searchable metadata fields with value counts.

    Returns:
        {
            "camera_make": ["Canon", "Nikon", "Sony"],
            "iso": [100, 200, 400, 800, 1600],
            "aperture": [1.4, 1.8, 2.8, 4.0],
            ...
        }
    """

@router.get("/fields/{field_name}/values")
def get_field_values(
    field_name: str,
    query: Optional[str] = None,
    limit: int = 50
):
    """
    Get autocomplete suggestions for a specific field.

    Example: /api/metadata/fields/camera_make/values?query=can
    Returns: ["Canon", "Canon EOS"]
    """

@router.get("/search")
def search_by_metadata(
    camera_make: Optional[str] = None,
    camera_model: Optional[str] = None,
    iso_min: Optional[int] = None,
    iso_max: Optional[int] = None,
    aperture_min: Optional[float] = None,
    aperture_max: Optional[float] = None,
    focal_length_min: Optional[int] = None,
    focal_length_max: Optional[int] = None,
    lens_model: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Search photos by metadata fields.
    Supports range queries and exact matches.
    """

@router.get("/stats")
def get_metadata_stats():
    """
    Get aggregate statistics about photo metadata.

    Returns:
        {
            "total_photos": 10000,
            "cameras": {"Canon": 5000, "Nikon": 3000, "Sony": 2000},
            "most_common_iso": 400,
            "most_common_aperture": 2.8,
            "lens_distribution": {...}
        }
    """
```

#### 2.2 Enhanced Search Endpoint
**File**: `server/api/routers/search.py`

Add metadata filters to existing `/api/search` endpoint:

```python
@router.get("/search")
def search_photos(
    query: str,
    # ... existing params ...

    # NEW: Metadata filters
    camera: Optional[str] = None,
    lens: Optional[str] = None,
    iso_range: Optional[str] = None,  # "400-1600"
    aperture_range: Optional[str] = None,  # "1.4-2.8"
    focal_length_range: Optional[str] = None,  # "24-70"
):
    """
    Enhanced search with metadata filters.
    """
```

#### 2.3 Frontend API Client
**File**: `frontend/src/api/client.ts`

Add metadata endpoints:

```typescript
export const metadataApi = {
  getFields: () => api.get('/metadata/fields'),

  getFieldValues: (field: string, query?: string) =>
    api.get(`/metadata/fields/${field}/values`, { params: { query } }),

  searchByMetadata: (filters: MetadataFilters) =>
    api.get('/metadata/search', { params: filters }),

  getStats: () => api.get('/metadata/stats'),
}
```

**Testing**:
- API integration tests for all endpoints
- Test autocomplete with partial queries
- Test range queries (ISO 400-1600)
- Load test with 10k+ photos

---

## Phase 3: UI Components (3-4 days)

### Goal
Build user interface for metadata browsing and filtering.

### Tasks

#### 3.1 Metadata Panel Component
**File**: `frontend/src/components/MetadataPanel.tsx` (NEW)

```tsx
interface MetadataPanelProps {
  photoPath: string;
  metadata: PhotoMetadata;
}

export const MetadataPanel: React.FC<MetadataPanelProps> = ({
  photoPath,
  metadata
}) => {
  return (
    <div className="metadata-panel glassmorphism">
      {/* Camera Section */}
      <MetadataSection
        title="Camera"
        icon={<Camera />}
        fields={[
          { label: "Make", value: metadata.camera_make },
          { label: "Model", value: metadata.camera_model },
        ]}
      />

      {/* Exposure Triangle */}
      <MetadataSection
        title="Exposure"
        icon={<Settings />}
        fields={[
          { label: "ISO", value: metadata.iso },
          { label: "Aperture", value: `f/${metadata.aperture}` },
          { label: "Shutter", value: metadata.shutter_speed },
        ]}
      />

      {/* Lens Section */}
      <MetadataSection
        title="Lens"
        icon={<Aperture />}
        fields={[
          { label: "Model", value: metadata.lens_model },
          { label: "Focal Length", value: `${metadata.focal_length}mm` },
        ]}
      />

      {/* ... more sections ... */}
    </div>
  );
};
```

#### 3.2 Advanced Filters Component
**File**: `frontend/src/components/AdvancedFilters.tsx` (NEW)

```tsx
export const AdvancedFilters: React.FC = () => {
  const [filters, setFilters] = useState<MetadataFilters>({});

  return (
    <div className="advanced-filters glassmorphism">
      <h3>Advanced Filters</h3>

      {/* Camera Filter with Autocomplete */}
      <AutocompleteField
        label="Camera"
        field="camera_make"
        value={filters.camera_make}
        onChange={(value) => setFilters({ ...filters, camera_make: value })}
      />

      {/* ISO Range Slider */}
      <RangeSlider
        label="ISO"
        min={100}
        max={12800}
        step={100}
        values={[filters.iso_min ?? 100, filters.iso_max ?? 12800]}
        onChange={([min, max]) =>
          setFilters({ ...filters, iso_min: min, iso_max: max })
        }
      />

      {/* Aperture Range */}
      <RangeSlider
        label="Aperture"
        min={1.4}
        max={22}
        step={0.1}
        values={[filters.aperture_min ?? 1.4, filters.aperture_max ?? 22]}
        onChange={([min, max]) =>
          setFilters({ ...filters, aperture_min: min, aperture_max: max })
        }
      />

      {/* Focal Length Range */}
      <RangeSlider
        label="Focal Length"
        min={10}
        max={600}
        step={1}
        values={[filters.focal_length_min ?? 10, filters.focal_length_max ?? 600]}
        onChange={([min, max]) =>
          setFilters({ ...filters, focal_length_min: min, focal_length_max: max })
        }
      />

      {/* Lens Autocomplete */}
      <AutocompleteField
        label="Lens"
        field="lens_model"
        value={filters.lens_model}
        onChange={(value) => setFilters({ ...filters, lens_model: value })}
      />

      <Button onClick={() => onApplyFilters(filters)}>
        Apply Filters
      </Button>
    </div>
  );
};
```

#### 3.3 Metadata Stats Dashboard
**File**: `frontend/src/pages/MetadataStats.tsx` (NEW)

```tsx
export const MetadataStatsPage: React.FC = () => {
  const { data: stats } = useQuery('metadata-stats', metadataApi.getStats);

  return (
    <div className="metadata-stats">
      <h2>Photo Library Statistics</h2>

      {/* Camera Distribution Chart */}
      <Card title="Camera Distribution">
        <PieChart data={stats?.cameras} />
      </Card>

      {/* ISO Usage Histogram */}
      <Card title="ISO Usage">
        <BarChart data={stats?.iso_distribution} />
      </Card>

      {/* Focal Length Heatmap */}
      <Card title="Focal Length Usage">
        <HistogramChart data={stats?.focal_length_distribution} />
      </Card>

      {/* Most Used Lenses */}
      <Card title="Most Used Lenses">
        <List data={stats?.top_lenses} />
      </Card>
    </div>
  );
};
```

#### 3.4 Integration with Existing UI

**Photo Detail Modal** (`frontend/src/components/PhotoDetail.tsx`):
- Add "Technical Info" tab alongside existing tabs
- Show MetadataPanel in this tab

**Search Bar** (`frontend/src/components/SearchBar.tsx`):
- Add "Advanced Filters" button
- Show AdvancedFilters in dropdown/modal

**Settings Page** (`frontend/src/pages/Settings.tsx`):
- Add link to "Library Statistics" (MetadataStatsPage)

**Testing**:
- Visual regression tests for all components
- Interaction tests (autocomplete, sliders)
- Test with various screen sizes (responsive design)

---

## Phase 4: Metadata Editor (2-3 days)

### Goal
Allow users to edit and bulk-update metadata.

### Tasks

#### 4.1 Edit Metadata Endpoint
**File**: `server/api/routers/metadata.py`

```python
@router.patch("/{photo_path:path}")
def update_metadata(
    photo_path: str,
    updates: MetadataUpdate
):
    """
    Update metadata for a single photo.
    Writes back to EXIF if possible.
    """

@router.post("/bulk-update")
def bulk_update_metadata(
    photo_paths: List[str],
    updates: MetadataUpdate
):
    """
    Bulk update metadata for multiple photos.
    """
```

#### 4.2 Metadata Editor Component
**File**: `frontend/src/components/MetadataEditor.tsx` (NEW)

```tsx
export const MetadataEditor: React.FC<{
  photos: Photo[];
  onSave: (updates: MetadataUpdate) => void;
}> = ({ photos, onSave }) => {
  return (
    <div className="metadata-editor glassmorphism">
      <h3>Edit Metadata ({photos.length} photos)</h3>

      <TextField
        label="Copyright"
        value={metadata.copyright}
        onChange={(value) => setMetadata({ ...metadata, copyright: value })}
      />

      <TextField
        label="Creator"
        value={metadata.creator}
        onChange={(value) => setMetadata({ ...metadata, creator: value })}
      />

      <TextField
        label="Keywords"
        value={metadata.keywords}
        placeholder="Comma-separated tags"
        onChange={(value) => setMetadata({ ...metadata, keywords: value })}
      />

      <Button onClick={() => onSave(metadata)}>
        Save Changes
      </Button>
    </div>
  );
};
```

#### 4.3 EXIF Write-Back
**File**: `src/metadata_writer.py` (NEW)

```python
class MetadataWriter:
    """
    Safely writes metadata back to image files.
    Uses exiftool or piexif for EXIF writing.
    """

    def write_metadata(self, filepath: str, updates: dict) -> bool:
        """Write metadata to file"""

    def validate_updates(self, updates: dict) -> bool:
        """Validate metadata before writing"""

    def backup_file(self, filepath: str) -> str:
        """Create backup before modifying"""
```

**Testing**:
- Test write-back with various image formats (JPEG, PNG, TIFF, RAW)
- Verify EXIF integrity after write
- Test bulk updates with 100+ photos
- Test rollback on failure

---

## Phase 5: Migration & Data Backfill (1-2 days)

### Goal
Migrate existing photos to new metadata schema.

### Tasks

#### 5.1 Migration Script
**File**: `scripts/migrate_metadata_v2.py` (NEW)

```python
#!/usr/bin/env python3
"""
Migrate existing photo metadata to enhanced schema.

Usage:
    python scripts/migrate_metadata_v2.py --dry-run
    python scripts/migrate_metadata_v2.py --batch-size 1000
"""

def migrate_photos(batch_size: int = 1000, dry_run: bool = False):
    """
    Re-extract and map metadata for all existing photos.
    """

    # 1. Get all photos from database
    # 2. Extract metadata with new mapper
    # 3. Update database with new fields
    # 4. Log progress and errors
```

#### 5.2 Run Migration

```bash
# Test on small sample
python scripts/migrate_metadata_v2.py --dry-run --limit 100

# Full migration with progress bar
python scripts/migrate_metadata_v2.py --batch-size 1000
```

**Testing**:
- Verify no data loss
- Check performance (should handle 10k+ photos in <10 minutes)
- Test rollback mechanism

---

## Success Criteria

### Functional Requirements
- ✅ All camera metadata fields searchable in UI
- ✅ Autocomplete works for camera/lens models
- ✅ Range sliders functional for ISO/aperture/focal length
- ✅ Metadata editor can bulk update 100+ photos
- ✅ Statistics page shows library insights
- ✅ No performance degradation on 10k+ photo libraries

### Non-Functional Requirements
- ✅ Migration completes without data loss
- ✅ API response time <200ms for metadata queries
- ✅ UI remains responsive during filtering
- ✅ All components follow glassmorphism design system
- ✅ 90%+ test coverage for new code

---

## Rollout Plan

### Week 1: Backend Foundation
- Day 1-2: Database schema + MetadataMapper
- Day 3-4: Search API + Autocomplete endpoints
- Day 5: Testing & bug fixes

### Week 2: Frontend UI
- Day 1-2: MetadataPanel + AdvancedFilters components
- Day 3: MetadataStats page
- Day 4: Integration with existing UI
- Day 5: Testing & polish

### Week 3: Editor & Migration
- Day 1-2: Metadata editor + write-back
- Day 3: Migration script + backfill
- Day 4-5: End-to-end testing + documentation

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| **EXIF write-back corrupts files** | High | Always create backups before writing; extensive testing with various formats |
| **Migration takes too long** | Medium | Batch processing with progress tracking; run during off-hours |
| **Performance degradation on large libraries** | Medium | Index all searchable columns; use query optimization |
| **Camera name normalization errors** | Low | Maintain mapping table; allow manual corrections |
| **UI complexity confuses users** | Low | Progressive disclosure; hide advanced filters by default |

---

## Future Enhancements (Post-MVP)

1. **Metadata Presets** - Save/load common search filters
2. **Export Metadata** - Export metadata to CSV/Excel
3. **Metadata Sync** - Sync EXIF between files and database
4. **AI-Suggested Tags** - Auto-tag based on scene detection
5. **Metadata Timeline** - Visualize shooting patterns over time
6. **GPS Data Enhancement** - Reverse geocoding for location names
7. **RAW File Support** - Extract RAW metadata (CR2, NEF, ARW)

---

## Dependencies

### Python Libraries
- `exifread` (already installed)
- `piexif` (for EXIF writing) - **NEW**
- `exiftool-python` (optional, for advanced write-back) - **NEW**

### Frontend Libraries
- `@headlessui/react` (for range sliders)
- `recharts` (for statistics charts) - **NEW**
- `react-select` (for autocomplete) - **NEW**

---

## Documentation Updates Required

1. **README.md** - Add "Advanced Metadata Search" to features list
2. **API.md** - Document new `/api/metadata/*` endpoints
3. **USER_GUIDE.md** - Tutorial on using advanced filters
4. **DEVELOPER.md** - Metadata extraction and mapping architecture

---

## Questions for User

1. **Priority Fields**: Which metadata fields are most important to you?
   - Camera/lens info?
   - Exposure settings (ISO, aperture, shutter)?
   - GPS/location data?
   - Copyright/creator info?

2. **Write-Back**: Should we support writing metadata back to files, or keep it database-only?

3. **RAW Support**: Do you shoot RAW? Should we prioritize RAW metadata extraction?

4. **Bulk Operations**: What bulk operations would be most useful?
   - Bulk copyright assignment?
   - Bulk keyword tagging?
   - Bulk location correction?

---

**Status**: Ready for review and approval
**Next Steps**: User feedback → Start Phase 1 implementation
