# Metadata System Implementation Plan - 2025

**Status**: Starting Phase 1
**Branch**: `feature/metadata-enhancement-2025`
**Focus**: Professional-grade metadata for photographers

---

## Overview

PhotoSearch has extracted 240+ metadata fields but needs enhanced UI, search, editing, and EXIF write-back capabilities for professional photographers. This plan prioritizes implementation based on photographer needs and ROI.

---

## Phase 1: Foundation & Professional Metadata Extraction (Week 1-2)

### 1.1 IPTC Core Metadata Extraction
- **Goal**: Add ~50 IPTC fields for copyright, creator, and content description
- **Library**: `iptcinfo3`
- **Fields**: Copyright notice, creator info, rights terms, keywords, location, event
- **Effort**: 2-3 days
- **Acceptance**: Extract and store IPTC data for sample photos

### 1.2 XMP Metadata Extraction
- **Goal**: Add ~50 XMP fields (Dublin Core, Photoshop, Camera Raw)
- **Library**: `python-xmp-toolkit`
- **Fields**: Title, description, keywords, subject codes, scene codes
- **Effort**: 3-4 days
- **Acceptance**: Parse and store XMP namespaces

### 1.3 Database Schema Enhancement
- **Goal**: Normalize extracted metadata for searchable columns
- **Tasks**:
  - Expand `photo_metadata` table with IPTC/XMP columns
  - Add indexed columns: `copyright`, `creator`, `keywords`, `location`, `event`
  - Maintain backward compatibility with existing data
  - Create migration script for existing photos
- **Effort**: 2-3 days
- **Acceptance**: Schema migration runs without data loss

### 1.4 Perceptual Hashing for Duplicates
- **Goal**: Add 3-5 hash types for improved duplicate detection
- **Library**: `imagehash`
- **Hashes**: phash, dhash, ahash
- **Effort**: 1 day
- **Acceptance**: Hash-based duplicate detection working

---

## Phase 2: Professional Search & Filter Interface (Week 2-3)

### 2.1 Advanced Metadata Filters API
- **Goal**: Build backend API for complex metadata searches
- **Endpoints**:
  - `/api/metadata/search` - Filter by camera, lens, exposure, IPTC data
  - `/api/metadata/autocomplete/{field}` - Autocomplete for dropdowns
  - `/api/metadata/stats` - Statistics endpoints
- **Effort**: 2-3 days
- **Acceptance**: Search returns results in <200ms for 50K photos

### 2.2 Frontend Advanced Filter Component
- **Goal**: Professional-grade filter UI (glassmorphic design)
- **Features**:
  - Camera make/model autocomplete
  - Range sliders for ISO, aperture, focal length, year
  - Lens autocomplete
  - Copyright/creator search
  - Keyword tag selector
  - Location/city search
  - Date range picker
- **Effort**: 3-4 days
- **Acceptance**: Filters work smoothly, remember last used settings

### 2.3 Enhanced Metadata Panel
- **Goal**: Display all extracted metadata in organized UI
- **Sections**:
  - Camera: Make, model, serial number
  - Exposure: ISO, aperture, shutter speed, exposure bias, metering
  - Lens: Model, focal length, aperture range
  - Location: GPS, address, reverse geocoding results
  - Copyright: Creator, copyright notice, rights terms, credit line
  - Content: Title, description, keywords, subject codes, event
  - File: Size, format, creation date, color space
- **Effort**: 2 days
- **Acceptance**: All sections display correctly, copy-to-clipboard works

---

## Phase 3: Statistics & Analytics (Week 3)

### 3.1 Metadata Statistics Dashboard
- **Goal**: Professional analytics for shooting patterns
- **Charts**:
  - Camera usage pie chart
  - ISO usage histogram
  - Focal length distribution
  - Lens usage frequency
  - Shooting timeline (photos per month/year)
  - Library totals (photo count, total file size)
- **Effort**: 2-3 days
- **Acceptance**: Charts render correctly, filterable by date range

---

## Phase 4: Bulk Editing & EXIF Write-Back (Week 4)

### 4.1 Bulk Metadata Editor
- **Goal**: Edit metadata for multiple photos simultaneously
- **Features**:
  - Multi-select photos
  - Bulk edit copyright, creator, keywords
  - Preserve existing metadata (partial updates)
  - Validation before applying changes
  - Error reporting (which files failed, why)
- **Effort**: 2-3 days
- **Acceptance**: Bulk operations work correctly

### 4.2 EXIF Write-Back System
- **Goal**: Write metadata changes back to image files
- **Library**: `piexif`
- **Features**:
  - Write copyright to EXIF Copyright tag
  - Write creator to EXIF Artist tag
  - Write keywords to EXIF Keywords tag
  - Backup before modifying
  - File integrity validation
  - Automatic rollback on failure
- **Supported Formats**: JPEG, TIFF, DNG
- **Effort**: 3-4 days
- **Acceptance**: Metadata written correctly, files readable in other apps

---

## Phase 5: Advanced Features (Week 5+)

### 5.1 Reverse Geocoding
- **Goal**: Convert GPS coordinates to human-readable addresses
- **Library**: OpenStreetMap Nominatim API (or Google)
- **Fields**: City, state, country, timezone, elevation, neighborhood
- **Effort**: 2 days
- **Acceptance**: Addresses look correct for sample photos

### 5.2 RAW Image Support
- **Goal**: Extract metadata from CR2, NEF, ARW, DNG files
- **Library**: `rawpy` for reading, `exiftool` as fallback
- **Fields**: Camera calibration, white balance, black/white levels
- **Effort**: 3-4 days
- **Priority**: MEDIUM (after Phase 4)

### 5.3 Image Quality Metrics
- **Goal**: Assess image quality (sharpness, exposure, noise)
- **Metrics**: Blur score, sharpness, noise level, contrast
- **Library**: `opencv-python`, `scikit-image`
- **Effort**: 2-3 days
- **Priority**: MEDIUM

### 5.4 Color Analysis
- **Goal**: Extract color palette and dominant colors
- **Analysis**: k-means color clustering, vibrancy score
- **Library**: `opencv-python`, `scikit-learn`
- **Effort**: 1-2 days
- **Priority**: LOW

---

## Phase 6: Data Integrity & Migration (Ongoing)

### 6.1 Schema Migration System
- **Goal**: Migrate existing photos to new schema safely
- **Features**:
  - Batch processing (avoid memory issues)
  - Progress reporting
  - Rollback capability
  - Data integrity validation
- **Performance**: Process 1,000+ photos/minute
- **Acceptance**: Migrate 100K photo libraries without data loss

### 6.2 Testing & Validation
- **Goal**: Comprehensive testing for metadata operations
- **Test Coverage**:
  - IPTC/XMP extraction accuracy
  - Search performance and correctness
  - EXIF write-back integrity
  - Migration data preservation
  - Large library handling (50K-100K photos)

---

## Implementation Order

| Week | Phase | Key Tasks | Deliverable |
|------|-------|-----------|-------------|
| 1-2 | Phase 1 | IPTC, XMP, DB schema, hashing | Extraction working, schema upgraded |
| 2-3 | Phase 2 | Search API, filters, metadata panel | Professional search interface |
| 3 | Phase 3 | Statistics dashboard | Analytics working |
| 4 | Phase 4 | Bulk editor, EXIF write-back | Metadata editing working |
| 5+ | Phase 5 | Reverse geocoding, RAW, quality | Advanced features |
| Ongoing | Phase 6 | Migration, testing | Data integrity confirmed |

---

## Technical Dependencies

### Required Libraries
- `iptcinfo3` - IPTC metadata
- `python-xmp-toolkit` - XMP metadata
- `piexif` - EXIF writing
- `imagehash` - Perceptual hashing
- `rawpy` - RAW file support (Phase 5)
- `opencv-python` - Image analysis (Phase 5)

### Database
- Extend `photo_metadata` table
- Add indexes on searchable columns
- Create migration scripts

### APIs
- Backend: Enhanced search/filter endpoints
- Frontend: React components with glassmorphic design

---

## Success Metrics

- ✅ Extract 300+ metadata fields (vs. current 240)
- ✅ Search 50K photos in <200ms
- ✅ Professional metadata editing UI
- ✅ Photographer-grade statistics
- ✅ EXIF write-back working correctly
- ✅ 100% backward compatibility
- ✅ 95%+ extraction success rate

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Data loss during migration | Backup existing DB, test rollback |
| Performance degradation | Index searchable columns, profile early |
| Library compatibility issues | Test with actual photo files |
| EXIF write failures | Backup system, file validation |
| Large library handling | Batch processing, memory management |

---

## Notes

- All phases maintain backward compatibility with existing data
- Design follows glassmorphism theme (consistent with current UI)
- Professional photographer focus (like Adobe Lightroom, Capture One)
- Modular implementation allows independent phase completion
