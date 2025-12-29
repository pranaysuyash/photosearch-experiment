# Metadata Implementation Documentation

**Date**: 2025-12-29
**Analysis**: Comprehensive metadata system architecture and implementation

## Overview

The PhotoSearch system implements a sophisticated metadata extraction, storage, and retrieval system that handles comprehensive file information including EXIF data, GPS coordinates, file system metadata, and calculated properties.

## Core Components

### 1. Metadata Extraction (`src/metadata_extractor.py`)

**Purpose**: Extract comprehensive metadata from any file type

**Key Features**:
- **Filesystem Metadata**: File size, permissions, timestamps, owner/group info
- **EXIF Data**: Complete EXIF extraction including MakerNote data
- **GPS Coordinates**: Decimal conversion from DMS format, altitude, speed
- **Image Properties**: Resolution, format, color space, ICC profiles
- **Video Properties**: Complete ffprobe data (format, streams, chapters)
- **Audio Properties**: Using mutagen (MP3, FLAC, OGG, WAV, AAC, M4A)
- **PDF Properties**: Document info, page count, encryption status
- **SVG Properties**: XML parsing for dimensions and element counts
- **File Hashes**: MD5 and SHA256 for integrity verification
- **Extended Attributes**: macOS/Linux xattr support
- **Calculated Metadata**: Aspect ratios, megapixels, orientation, file age

**Supported Formats**:
- Images: JPG, PNG, HEIC/HEIF, GIF, WebP, TIFF, SVG
- Video: MP4, MOV, AVI, MKV, WebM (via ffprobe)
- Audio: MP3, FLAC, OGG, WAV, AAC, M4A (via mutagen)
- Documents: PDF (via pypdf)

**Key Functions**:
- `extract_all_metadata(filepath)` - Main extraction function
- `extract_filesystem_metadata()` - File system information
- `extract_exif_metadata()` - Complete EXIF data including MakerNote
- `extract_gps_metadata()` - GPS coordinates with decimal conversion
- `extract_image_properties()` - Image dimensions and properties
- `extract_video_properties()` - Video metadata via ffprobe
- `calculate_inferred_metadata()` - Derived metadata like aspect ratios

### 2. Metadata Database (`src/metadata_search.py`)

**Purpose**: SQLite-based metadata storage with version tracking and search capabilities

**Database Schema**:
```sql
-- Main metadata table
CREATE TABLE metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,
    file_hash TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1,
    deleted_at TIMESTAMP
)

-- Version history table
CREATE TABLE metadata_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    extracted_at TIMESTAMP NOT NULL,
    version INTEGER NOT NULL,
    changes_json TEXT
)

-- Deleted files table
CREATE TABLE deleted_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deletion_reason TEXT
)

-- Favorites table
CREATE TABLE favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,
    favorited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
)
```

**Key Features**:
- **Version Tracking**: Automatic versioning when metadata changes
- **Change Detection**: SHA256 hash-based file modification detection
- **Deleted File Tracking**: Preserves metadata of deleted files
- **Favorites System**: Mark files as favorites with notes
- **Query Engine**: Advanced search with nested field access
- **Batch Extraction**: Process multiple files efficiently
- **Smart Updates**: Only re-extract modified files

**Key Classes**:
- `MetadataDatabase` - Database operations and management
- `BatchExtractor` - Batch metadata extraction from catalogs
- `QueryEngine` - Search and query functionality

**Search Capabilities**:
- Field-specific queries: `camera=Canon`, `width>1920`
- Nested field access: `exif.image.Make`, `filesystem.size_bytes`
- User-friendly shortcuts: `filename:sunset`, `size:>5MB`
- Boolean operators: `AND`, `OR` combination
- Comparison operators: `=`, `!=`, `>`, `<`, `>=`, `<=`, `LIKE`, `CONTAINS`
- Export functionality: JSON and CSV export

### 3. API Integration

**Metadata Access Points**:

1. **Face Recognition API** (`server/api/routers/face_recognition.py`)
   - Extracts photo timestamps from metadata
   - Uses metadata for face detection workflows
   - Integrates with metadata database for batch processing

2. **Tags API** (`server/api/routers/tags.py`)
   - Retrieves metadata when tagging photos
   - Returns metadata in tag responses

3. **Bulk Operations API** (`server/api/routers/bulk.py`)
   - Bulk metadata cleanup operations
   - Deleted metadata management

4. **Duplicates API** (`server/api/routers/duplicates.py`)
   - Uses metadata database for duplicate detection
   - Queries metadata for file comparison

5. **Smart Collections API** (`server/api/routers/smart_collections.py`)
   - Uses metadata for smart album generation
   - Metadata-based automatic organization

### 4. Frontend Integration

**UI Components Using Metadata**:

1. **Photo Info Tab** (`ui/src/components/gallery/tabs/InfoTab.tsx`)
   - Displays image dimensions (width, height)
   - Shows file size and creation date
   - Metadata: `image.width`, `image.height`, `filesystem.size_human`, `filesystem.created`

2. **Photo Details Tab** (`ui/src/components/gallery/tabs/DetailsTab.tsx`)
   - Shows comprehensive EXIF and metadata information
   - Technical camera details, GPS data, etc.

3. **Photo Grid** (`ui/src/components/gallery/PhotoGrid.tsx`)
   - Uses metadata for photo display and filtering
   - Aspect ratio calculations for grid layout

4. **Enhanced Search UI** (`ui/src/components/search/EnhancedSearchUI.tsx`)
   - Metadata-based filtering and search
   - Advanced search options using metadata fields

5. **Export Dialog** (`ui/src/components/export/ExportDialog.tsx`)
   - Uses metadata for export operations
   - File properties for export settings

6. **Analytics Dashboard** (`ui/src/components/advanced/AnalyticsDashboard.tsx`)
   - Metadata statistics and visualizations
   - Camera usage, resolution distribution, etc.

7. **Photo Context** (`ui/src/contexts/PhotoSearchContext.tsx`)
   - Global metadata management
   - State management for metadata operations

## Metadata Structure

### Top-Level Metadata Categories

```json
{
  "file": {
    "path": "/path/to/file.jpg",
    "name": "file.jpg",
    "extension": ".jpg",
    "mime_type": "image/jpeg"
  },
  "filesystem": {
    "size_bytes": 2048576,
    "size_human": "2.0 MB",
    "created": "2024-12-29T10:30:00",
    "modified": "2024-12-29T10:30:00",
    "accessed": "2024-12-29T10:35:00",
    "permissions_octal": "0644",
    "owner": "username",
    "group": "groupname"
  },
  "image": {
    "width": 1920,
    "height": 1080,
    "format": "JPEG",
    "mode": "RGB",
    "dpi": [300, 300],
    "bits_per_pixel": 24,
    "megapixels": 2.1
  },
  "exif": {
    "image": {
      "Make": "Canon",
      "Model": "EOS R5",
      "Software": "Adobe Photoshop"
    },
    "exif": {
      "ExposureTime": "1/125",
      "FNumber": "f/2.8",
      "ISOSpeedRatings": 400
    },
    "gps": {
      "latitude": 37.7749,
      "longitude": -122.4194,
      "altitude": 10.5
    }
  },
  "calculated": {
    "aspect_ratio": "16:9",
    "aspect_ratio_decimal": 1.778,
    "orientation": "landscape",
    "file_age": {
      "days": 30,
      "human_readable": "30 days ago"
    }
  }
}
```

## Advanced Features

### 1. Intelligent Change Detection
- SHA256 hash-based file modification detection
- Only re-extracts metadata when files change
- Automatic version tracking with history

### 2. User-Friendly Search Shortcuts
- `filename:sunset` → Search by filename
- `camera:Canon` → Search by camera make
- `size:>5MB` → Search by file size
- `width:>1920` → Search by resolution
- `date:2024` → Search by date
- `format:jpg` → Search by file format

### 3. Nested Field Access
- `exif.image.Make` → Camera manufacturer
- `filesystem.size_bytes` → File size in bytes
- `gps.latitude` → GPS latitude coordinate
- `calculated.aspect_ratio` → Aspect ratio

### 4. Batch Operations
- Extract metadata for entire catalogs
- Filter by directory or file format
- Progress tracking with tqdm
- Error handling and statistics

### 5. Favorites System
- Mark files as favorites
- Add notes to favorites
- Query favorited files
- Toggle favorite status

### 6. Export Capabilities
- JSON export with full metadata
- CSV export with flattened fields
- Search result export
- Custom field selection

## Integration Points

### 1. Face Recognition Integration
- Extract timestamps from metadata for face detection
- Use GPS data for location-based face clustering
- Camera metadata for photo organization

### 2. OCR Integration
- Metadata for document processing
- File properties for OCR quality assessment
- Creation dates for document timeline

### 3. Video Processing
- Video metadata extraction for face tracking
- Duration and resolution for processing decisions
- Format detection for codec selection

### 4. Search Integration
- Metadata-based filtering in search queries
- Faceted search using metadata fields
- Advanced search with metadata constraints

### 5. Analytics Integration
- Camera usage statistics
- Resolution distribution analysis
- File size and format analytics
- Timeline generation based on dates

## Performance Optimizations

### 1. Database Optimizations
- WAL mode for better concurrent access
- Optimized pragma settings (synchronous, cache_size)
- Comprehensive indexing on common search fields
- Connection pooling and timeout management

### 2. Extraction Optimizations
- Smart change detection avoids unnecessary re-extraction
- Batch processing with progress tracking
- Error handling prevents single-file failures
- Chunked file reading for large files

### 3. Search Optimizations
- Early termination when limit reached
- Efficient JSON parsing and caching
- Field extraction optimization
- Smart query parsing with shortcuts

## Storage and Scalability

### Database Files
- `metadata.db` - Main metadata database
- `photo_metadata.db` - Legacy metadata database (2.3MB)
- SQLite with WAL journaling
- Automatic indexing on common fields

### Storage Efficiency
- Compressed JSON storage for metadata
- Version history only stores changes
- Deleted file tracking for audit trail
- Hash-based deduplication

### Scalability Considerations
- Tested with thousands of files
- Efficient index structure for fast queries
- Batch processing support
- Progressive extraction with filters

## Future Enhancement Opportunities

### 1. Performance
- Implement Redis caching for frequently accessed metadata
- Add full-text search for metadata fields
- Optimize JSON storage with compression
- Implement metadata pre-computation

### 2. Features
- Add metadata editing capabilities
- Implement metadata-based auto-tagging
- Add location-based photo organization
- Create metadata-driven smart albums

### 3. Integration
- Enhanced face recognition metadata integration
- Video metadata timeline generation
- Audio metadata for music organization
- Document metadata for OCR workflows

### 4. Analytics
- Advanced metadata analytics dashboard
- Camera usage trends over time
- Storage usage by file type
- Metadata quality assessment

## Conclusion

The PhotoSearch metadata implementation provides a comprehensive, scalable, and efficient system for extracting, storing, and querying file metadata. The modular architecture allows for easy integration with other system components while maintaining high performance and data integrity.

The system successfully handles multiple file formats, provides powerful search capabilities, and maintains version history for data tracking. Future enhancements could focus on performance optimization, advanced analytics, and tighter integration with other system components.
