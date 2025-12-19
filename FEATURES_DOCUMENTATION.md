# Living Museum - Feature Documentation

## Table of Contents
1. [Introduction](#introduction)
2. [Duplicates Review Lens](#duplicates-review-lens)
3. [Photo Editor](#photo-editor)
4. [People ↔ Viewer Integration](#people--viewer-integration)
5. [Per-Photo Notes/Captions](#per-photo-notescaptions)
6. [Export/Share Polish](#exportshare-polish)
7. [Provenance Chips](#provenance-chips)
8. [Safe Bulk Actions](#safe-bulk-actions)
9. [Multi-tag Filtering](#multi-tag-filtering)
10. [Version Stacks](#version-stacks)
11. [Place Correction & Location Clustering](#place-correction--location-clustering)

## Introduction

This document provides comprehensive documentation for all features implemented in the Living Museum photo search application. Each feature is designed with a "glass design language" and follows modern UI/UX principles for an intuitive user experience.

---

## Duplicates Review Lens

### Overview
The Duplicates Review Lens allows users to identify, review, and manage duplicate photos in their library. This feature provides a visual interface to see potential duplicates and resolve them with various options.

### Key Features
- Visual grouping of similar photos
- Multiple resolution strategies (keep first, keep all, delete duplicates)
- Progress tracking during duplicate scanning
- Statistics on duplicates found and space saved

### API Endpoints
- `GET /api/duplicates` - Retrieve all duplicate groups
- `POST /api/duplicates/scan` - Scan for duplicates
- `POST /api/duplicates/{group_id}/resolve` - Resolve a duplicate group
- `DELETE /api/duplicates/{group_id}` - Delete a duplicate group
- `GET /api/duplicates/stats` - Get duplicate statistics

### Usage Example
```javascript
// Scan for duplicates
const scanResult = await api.post('/api/duplicates/scan', { type: 'exact' });

// Get duplicate groups
const groups = await api.get('/api/duplicates');

// Resolve a group by keeping the first image
await api.post(`/api/duplicates/${groupId}/resolve`, {
  resolution: 'delete_duplicates',
  keep_files: [groups[0].files[0].path]
});
```

### UI Component
The `DuplicatesPage.tsx` component provides the main interface for managing duplicates.

---

## Photo Editor

### Overview
The non-destructive photo editor allows users to apply adjustments like brightness, contrast, saturation, rotation, and cropping directly in the browser.

### Key Features
- Non-destructive editing (originals preserved)
- Canvas-based rendering for performance
- Real-time preview of edits
- Crop, brightness, contrast, saturation adjustments
- Rotation and flip controls

### API Endpoints
- `GET /api/photos/{file_path}/edits` - Retrieve edit instructions for a photo
- `POST /api/photos/{file_path}/edits` - Save edit instructions
- `DELETE /api/photos/{file_path}/edits` - Remove edit instructions

### Usage Example
```javascript
// Get existing edits for a photo
const edits = await api.getPhotoEdits('/path/to/photo.jpg');

// Save new edits
await api.setPhotoEdits('/path/to/photo.jpg', {
  brightness: 10,
  contrast: 5,
  saturation: -5,
  rotation: 90,
  flipH: false,
  flipV: false
});
```

### UI Component
The `PhotoEditor.tsx` component provides the editor interface. It can be integrated into the photo detail view.

---

## People ↔ Viewer Integration

### Overview
This feature connects face clustering results with the photo viewer, allowing users to see and manage people associated with specific photos.

### Key Features
- Display people associated with each photo
- Add/remove people from photos
- Link to full person details in the People section
- Visual representation of detected faces

### API Endpoints
- `GET /api/photos/{photo_path}/people` - Get people associated with a photo
- `POST /api/photos/{photo_path}/people` - Add a person to a photo
- `DELETE /api/photos/{photo_path}/people/{person_id}` - Remove a person from a photo

### Usage Example
```javascript
// Get people in a specific photo
const people = await api.getPeopleInPhoto('/path/to/photo.jpg');

// Add person to photo
await api.addPersonToPhoto('/path/to/photo.jpg', 'person123');

// Remove person from photo
await api.removePersonFromPhoto('/path/to/photo.jpg', 'person123');
```

### UI Component
The `PeopleChips.tsx` component displays associated people as interactive chips.

---

## Per-Photo Notes/Captions

### Overview
The notes system allows users to add rich text descriptions, captions, and comments to individual photos.

### Key Features
- Rich text notes for each photo
- Search across all notes
- API endpoints for managing notes
- Integration with photo detail view

### API Endpoints
- `GET /api/photos/{file_path}/notes` - Get a photo's note
- `POST /api/photos/{file_path}/notes` - Set a photo's note
- `DELETE /api/photos/{file_path}/notes` - Remove a photo's note
- `GET /api/notes/search` - Search all notes
- `GET /api/notes/stats` - Get notes statistics

### Usage Example
```javascript
// Get note for a photo
const note = await api.getPhotoNote('/path/to/photo.jpg');

// Set note for a photo
await api.setPhotoNote('/path/to/photo.jpg', 'This is my vacation photo');

// Search notes
const results = await api.searchNotes('vacation', 100, 0);
```

### UI Component
The `NotesEditor.tsx` component provides a rich editing interface for notes.

---

## Export/Share Polish

### Overview
Enhanced export and sharing capabilities with presets, formatting options, and secure share links.

### Key Features
- Export presets (High Quality, Web Sharing, Print Ready)
- Configurable export options (resolution, metadata inclusion, etc.)
- Secure share links with expiration and password protection
- Batch export functionality

### API Endpoints
- `POST /export` - Export photos with options
- `POST /export/presets` - Create an export preset
- `GET /export/presets` - Get available presets
- `POST /share` - Create share link
- `GET /shared/{share_id}` - Get shared content
- `GET /shared/{share_id}/download` - Download shared content

### Usage Example
```javascript
// Export photos with options
await api.exportPhotos(['/photo1.jpg', '/photo2.jpg'], {
  format: 'zip',
  include_metadata: true,
  include_thumbnails: false,
  max_resolution: 1920
});

// Create share link
const shareInfo = await api.createShareLink(
  ['/photo1.jpg', '/photo2.jpg'],
  24, // expires in 24 hours
  'password123' // optional password
);
```

### UI Component
The `ExportDialog.tsx` component provides a comprehensive interface for export and share options.

---

## Provenance Chips

### Overview
Provenance Chips display the source and availability status of photos (Local/Cloud/Offline).

### Key Features
- Visual indicators for photo source (Local, Cloud, Offline)
- Status indicators (Syncing, Available, Degraded)
- Source-specific information and metadata

### UI Component
The `ProvenanceChip.tsx` component displays source and availability status with appropriate icons and colors.

### Usage Example
```jsx
<ProvenanceChip 
  status="cloud" 
  source="Google Drive" 
  lastSync="2023-10-15T10:30:00Z" 
  size="md" 
/>
```

---

## Safe Bulk Actions

### Overview
Safe bulk operations with undo functionality and notification system to prevent accidental data loss.

### Key Features
- Undo functionality for bulk operations (delete, favorite, tag, etc.)
- Toast notifications with action buttons
- Operation history tracking
- Safe deletion with trash functionality

### API Endpoints
- Operations use existing endpoints but with new undo mechanisms

### Usage Example
```javascript
// Using the bulk actions service for safe operations
const { performBulkDelete } = useBulkActions();

// This will show a notification with undo option
performBulkDelete(['/photo1.jpg', '/photo2.jpg']);
```

### UI Component
The system uses the `ToastProvider.tsx` and `Toast.tsx` components for notifications, and a `BulkActionsService.ts` for operation management.

---

## Multi-tag Filtering

### Overview
Advanced search capabilities allowing users to filter photos by multiple tags with AND/OR logic.

### Key Features
- Filter by multiple tags simultaneously
- AND/OR logic for combining tags
- Tag suggestion and auto-completion
- Integration with search functionality

### API Endpoints
- `GET /search?tags=tag1,tag2,tag3&tag_logic=AND` - Search with multi-tag filter

### Usage Example
```javascript
// Search with multiple tags using OR logic
const results = await api.get('/search', {
  params: {
    query: '',
    tags: 'vacation,beach,family',
    tag_logic: 'OR'
  }
});
```

### UI Component
The `MultiTagFilter.tsx` component provides an interface for selecting multiple tags with logic selection.

---

## Version Stacks

### Overview
Group original photos with their edited versions in a visual stack, allowing users to manage related photos together.

### Key Features
- Track original and edited versions
- Visual representation of edit history
- Metadata for each version (name, description, instructions)
- Easy access to any version in the stack

### API Endpoints
- `POST /versions` - Create a photo version record
- `GET /versions/original/{original_path}` - Get all versions for an original
- `GET /versions/stack/{version_path}` - Get entire version stack
- `PUT /versions/{version_path}` - Update version metadata
- `DELETE /versions/{version_id}` - Delete a version record

### Usage Example
```javascript
// Create a new version
const versionId = await api.createPhotoVersion(
  '/original/photo.jpg',      // original path
  '/edited/photo_v1.jpg',     // version path
  'edited',                   // version type
  'Brighter Colors',          // name
  'Increased brightness and saturation'
);

// Get all versions in a stack
const stack = await api.getVersionStack('/original/photo.jpg');
```

### UI Component
The `VersionStack.tsx` component displays the version history in an expandable stack interface.

---

## Place Correction & Location Clustering

### Overview
Tools to correct GPS location names and group photos by location into meaningful place clusters.

### Key Features
- Location name correction interface
- Place clustering by proximity
- City/region/country extraction
- Location statistics and visualization

### API Endpoints
- `POST /locations` - Add/update photo location
- `GET /locations/photo/{photo_path}` - Get location for a photo
- `PUT /locations/photo/{photo_path}` - Update location info
- `GET /locations/places/{place_name}` - Find photos by place name
- `GET /locations/nearby` - Find nearby photos
- `GET /locations/clusters` - Get location clusters
- `GET /locations/stats` - Get location statistics

### Usage Example
```javascript
// Add location info to a photo
await api.addPhotoLocation(
  '/path/to/photo.jpg',
  40.7128,   // latitude
  -74.0060,  // longitude
  'New York', // original GPS name
  'Manhattan, NYC' // corrected name
);

// Get location clusters
const clusters = await api.getPlaceClusters(2); // min 2 photos per cluster
```

### UI Components
- `LocationCorrection.tsx` - For correcting location names
- `PlaceClustering.tsx` - For displaying location clusters

---

## Contributing

### Adding New Features
When adding new features, ensure they follow these patterns:
1. Create appropriate database modules with unit tests
2. Add API endpoints with proper error handling
3. Create reusable UI components with the glass design system
4. Add integration tests demonstrating feature interactions
5. Update this documentation with usage examples

### UI Design Principles
All new components should follow the glass design system:
- Use the `glass` utility classes for surfaces
- Maintain consistent spacing and typography
- Implement appropriate loading and error states
- Ensure accessibility with proper ARIA attributes