# Living Museum - Feature Implementation Documentation

## Table of Contents
1. [Introduction](#introduction)
2. [Implemented Features Overview](#implemented-features-overview)
3. [Detailed Feature Documentation](#detailed-feature-documentation)
4. [API Endpoints Reference](#api-endpoints-reference)
5. [UI Components Reference](#ui-components-reference)
6. [Database Schema](#database-schema)
7. [Testing Coverage](#testing-coverage)
8. [Performance Considerations](#performance-considerations)
9. [Security Implementation](#security-implementation)

## Introduction

This document provides comprehensive documentation for all features implemented in the Living Museum photo search application. The implementation followed the NEXT_5_FEATURES_IMPLEMENTATION_PLAN.md specification and includes all 11 core features plus additional functionality.

## Implemented Features Overview

The following features have been successfully implemented:

### Core Features:
1. **Duplicates Review Lens** - UI components to identify and manage duplicate photos
2. **Editor Wiring** - Complete integration of photo editor UI with backend endpoints
3. **People ↔ Viewer Integration** - Per-photo people chips and filtering
4. **Per-photo Notes/Captions** - Individual photo annotations with storage
5. **Export/Share Polish** - Enhanced export functionality with presets and sharing

### Advanced Features:
6. **Provenance Chips** - Local/Cloud/Offline state indicators
7. **Safe Bulk Actions** - Undo-enabled batch operations
8. **Multi-tag Filtering** - AND/OR logic for tag combinations
9. **Version Stacks** - Edited copy and original management
10. **Place Correction & Location Clustering** - Enhanced location management
11. **AI Insights Generation** - Automatic photo analysis and recommendations

## Detailed Feature Documentation

### 1. Duplicates Review Lens

#### Purpose
The Duplicates Review Lens allows users to identify, review, and manage duplicate photos in their library using advanced detection algorithms.

#### Components
- `DuplicatesReview.tsx` - Main UI component for reviewing duplicate groups
- `DuplicatesDB` - Database module for managing duplicate identification
- API endpoints:
  - `GET /api/duplicates` - Retrieve duplicate groups
  - `POST /api/duplicates/scan` - Scan for duplicates
  - `POST /api/duplicates/{group_id}/resolve` - Resolve duplicate groups
  - `DELETE /api/duplicates/{group_id}` - Delete duplicate groups

#### Architecture
The duplicates system uses hash-based comparison algorithms to identify duplicate candidates, with both exact and perceptual matching capabilities. Results are stored in the duplicates database with resolution tracking.

#### Usage
```typescript
// Example usage in React component
const handleResolveDuplicates = async (groupId: string) => {
  const resolution = await api.resolveDuplicateGroup(
    groupId, 
    'keep_first',  // or 'keep_all', 'delete_all', 'keep_selected'
    [firstPhotoPath]  // for 'keep_selected' option
  );
};
```

### 2. Editor Wiring

#### Purpose
Complete integration of photo editing capabilities with backend endpoints to support non-destructive editing.

#### Components
- `PhotoEditor.tsx` - Comprehensive photo editing UI
- `PhotoEditsDB` - Database module for storing edit instructions
- API endpoints:
  - `GET /api/photos/{path}/edits` - Get edit instructions
  - `POST /api/photos/{path}/edits` - Save edit instructions
  - `DELETE /api/photos/{path}/edits` - Reset edits

#### Architecture
Uses non-destructive editing approach where only transformation instructions are stored. Actual image processing happens on the client-side with instructions saved to the server for persistence.

#### Usage
```typescript
// Example usage for applying edits
const applyEdits = async (photoPath: string, editInstructions: any) => {
  // Save edit instructions to backend
  await api.setPhotoEdits(photoPath, editInstructions);
  
  // Edits are automatically applied in the UI
};
```

### 3. People ↔ Viewer Integration

#### Purpose
Enables per-photo people tagging with clustering and filtering capabilities.

#### Components
- `PeopleChips.tsx` - Chips showing people in each photo
- `FaceClusterer` - Backend module for face clustering
- API endpoints:
  - `GET /api/faces/clusters` - Get all face clusters
  - `POST /api/faces/cluster` - Cluster faces in specific images
  - `GET /api/faces/photos/{person_name}` - Get photos of a person
  - `POST /api/faces/clusters/{cluster_id}/label` - Name a cluster

#### Architecture
Combines face detection with clustering algorithms to group similar faces, enabling people recognition across the photo library.

#### Usage
```typescript
// Get all people in photos
const getPeopleClusters = async () => {
  const clusters = await api.getFaceClusters();
  return clusters; // Array of person clusters
};
```

### 4. Per-photo Notes/Captions

#### Purpose
Individual photo annotation system with rich text capabilities and search support.

#### Components
- `NotesEditor.tsx` - Rich text editor for photo notes
- `NotesDB` - Database module for storing photo annotations
- API endpoints:
  - `GET /api/photos/{path}/notes` - Get photo note
  - `POST /api/photos/{path}/notes` - Save photo note
  - `DELETE /api/photos/{path}/notes` - Delete photo note
  - `GET /api/notes/search` - Search notes by content

#### Architecture
Stores notes separately from photo metadata with full-text search capabilities using SQLite's FTS.

#### Usage
```typescript
// Add a note to a photo
await api.setPhotoNote(photoPath, "This is a beautiful sunset");

// Search for notes containing specific text
const results = await api.searchNotes("beautiful sunset");
```

### 5. Export/Share Polish

#### Purpose
Enhanced export and sharing functionality with presets and security options.

#### Components
- `ExportDialog.tsx` - Comprehensive export and sharing UI
- `ShareManager` - Backend module for share link management
- API endpoints:
  - `POST /api/export` - Export photos with options
  - `POST /api/share` - Create share links
  - `GET /api/shared/{share_id}` - Access shared content
  - `GET /api/export/presets` - Get available export presets

#### Architecture
Supports both direct download and secure share links with expiration and password protection.

#### Usage
```typescript
// Create a share link
const shareInfo = await api.createShareLink(
  [photoPath1, photoPath2],
  24,  // expires in 24 hours
  "optional_password"  // optional password
);

console.log(shareInfo.share_url); // Share this link
```

### 6. Provenance Chips

#### Purpose
Visual indicators showing the source and availability state of photos (Local/Cloud/Offline).

#### Components
- `ProvenanceChips.tsx` - Status indicators for each photo
- `SourceTracker` - Backend module for tracking photo sources
- API endpoints:
  - `GET /api/photos/{path}/provenance` - Get source information
  - `POST /api/photos/{path}/provenance` - Update source information

#### Architecture
Tracks photo source origins (local drive, cloud service, imported) and availability status with appropriate UI indicators.

#### Usage
```typescript
// Get provenance information
const provenance = await api.getPhotoProvenance(photoPath);
// Returns source type, availability status, and sync status
```

### 7. Safe Bulk Actions

#### Purpose
Batch operations with undo functionality to prevent accidental data loss.

#### Components
- `BulkActionsManager.tsx` - Bulk operation UI with undo capability
- `BulkTransactionLog` - Backend module for tracking bulk operations
- API endpoints:
  - `POST /api/bulk/{action}` - Perform bulk action
  - `POST /api/bulk/undo/{transaction_id}` - Undo bulk action
  - `GET /api/bulk/history` - Get bulk action history

#### Architecture
Maintains transaction logs for all bulk operations with metadata needed for reversal.

#### Usage
```typescript
// Perform bulk delete with undo
const transactionId = await api.bulkDelete([photo1, photo2, photo3]);
// If needed, undo the operation
await api.undoBulkAction(transactionId);
```

### 8. Multi-tag Filtering

#### Purpose
Advanced tag filtering with AND/OR logic for complex searches.

#### Components
- `MultiTagFilter.tsx` - Tag combination UI with logic selector
- `TagFilterEngine` - Database module for complex tag queries
- API endpoints:
  - `GET /api/tags/search` - Search tags by name
  - `POST /api/tags/filter` - Apply complex tag filters
  - `GET /api/tags/stats` - Get tag statistics

#### Architecture
Uses SQL-based tag combination with support for complex boolean operations.

#### Usage
```typescript
// Search with multiple tags using AND/OR logic
const results = await api.searchByTags(
  ["beach", "sunset"],    // tags to include
  "OR",                  // combination logic
  ["people"]             // tags to exclude
);
```

### 9. Version Stacks

#### Purpose
Management of photo versions (original + edited copies) in hierarchical stacks.

#### Components
- `VersionStackViewer.tsx` - UI for viewing and managing version stacks
- `PhotoVersionsDB` - Database module for version relationships
- API endpoints:
  - `GET /api/versions/photo/{path}` - Get all versions of a photo
  - `POST /api/versions` - Create new version
  - `PUT /api/versions/{version_id}` - Update version metadata
  - `DELETE /api/versions/{version_id}` - Remove version from stack

#### Architecture
Tracks relationships between original photos and their edited variants with complete edit history.

#### Usage
```typescript
// Get all versions of a photo
const stack = await api.getPhotoVersionStack(photoPath);
// Create a new version
const versionId = await api.createPhotoVersion(
  originalPath,
  newPath,
  "edit",
  "Brighter Version"
);
```

### 10. Place Correction & Location Clustering

#### Purpose
Enhanced location management with correction capabilities and place clustering.

#### Components
- `LocationCorrection.tsx` - UI for place name correction
- `LocationClusterer` - Backend module for location grouping
- API endpoints:
  - `GET /api/locations/photo/{path}` - Get location for photo
  - `POST /api/locations/photo/{path}` - Set location for photo
  - `GET /api/locations/nearby` - Get photos at nearby locations
  - `GET /api/locations/clusters` - Get location clusters

#### Architecture
Uses geospatial clustering algorithms to group photos taken at similar locations, with manual correction capabilities.

#### Usage
```typescript
// Get location clusters
const clusters = await api.getLocationClusters();
// Set corrected location name
await api.setPhotoLocation(
  photoPath,
  latitude,
  longitude,
  "Central Park, New York"  // corrected name
);
```

### 11. AI Insights Generation

#### Purpose
Automatic photo analysis and recommendation system powered by machine learning.

#### Components
- `AIInsightsPanel.tsx` - UI for displaying AI insights
- `AIInsightsEngine` - Machine learning module for photo analysis
- API endpoints:
  - `POST /api/ai/insights/generate` - Generate insights for photo
  - `GET /api/ai/insights/{photo_path}` - Get insights for photo
  - `GET /api/ai/insights/recommendations` - Get recommendations
  - `GET /api/ai/stats` - Get AI processing statistics

#### Architecture
Uses computer vision models to analyze photo content and generate insights about composition, subjects, and potential improvements.

#### Usage
```typescript
// Generate AI insights for a photo
const insights = await api.generateAIInsights(photoPath);
// Get recommendations for photo improvement
const recommendations = await api.getPhotoRecommendations(photoPath);
```

## API Endpoints Reference

### Duplicates Endpoints
- `GET /api/duplicates` - Get duplicate groups
- `POST /api/duplicates/scan` - Scan for duplicates
- `POST /api/duplicates/{group_id}/resolve` - Resolve duplicate group
- `DELETE /api/duplicates/{group_id}` - Delete duplicate group

### Editor Endpoints
- `GET /api/photos/{path}/edits` - Get edit instructions for photo
- `POST /api/photos/{path}/edits` - Save edit instructions
- `DELETE /api/photos/{path}/edits` - Reset edit instructions
- `GET /api/edits/stats` - Get editing statistics

### People Endpoints
- `GET /api/faces/clusters` - Get all face clusters
- `POST /api/faces/cluster` - Cluster faces in images
- `GET /api/faces/photos/{person_name}` - Get photos with specific person
- `POST /api/faces/clusters/{cluster_id}/label` - Label a face cluster

### Notes Endpoints
- `GET /api/photos/{path}/notes` - Get note for photo
- `POST /api/photos/{path}/notes` - Set note for photo
- `DELETE /api/photos/{path}/notes` - Delete note for photo
- `GET /api/notes/search` - Search across all notes

### Export/Share Endpoints
- `POST /api/export` - Export photos with options
- `POST /api/share` - Create share links
- `GET /api/shared/{share_id}` - Access shared content
- `GET /api/export/presets` - Get export presets

### Provenance Endpoints
- `GET /api/photos/{path}/provenance` - Get source information
- `POST /api/photos/{path}/provenance` - Update source information

### Bulk Actions Endpoints
- `POST /api/bulk/{action}` - Perform bulk operation
- `POST /api/bulk/undo/{transaction_id}` - Undo bulk operation
- `GET /api/bulk/history` - Get bulk action history

### Multi-tag Filtering Endpoints
- `GET /api/tags/search` - Search tags
- `POST /api/tags/filter` - Apply tag filters
- `GET /api/tags/stats` - Get tag statistics

### Version Stacks Endpoints
- `GET /api/versions/photo/{path}` - Get version stack for photo
- `POST /api/versions` - Create new version
- `PUT /api/versions/{version_id}` - Update version
- `DELETE /api/versions/{version_id}` - Delete version

### Location Endpoints
- `GET /api/locations/photo/{path}` - Get location for photo
- `POST /api/locations/photo/{path}` - Set location for photo
- `GET /api/locations/nearby` - Get nearby photos
- `GET /api/locations/clusters` - Get location clusters

### AI Insights Endpoints
- `POST /api/ai/insights/generate` - Generate AI insights
- `GET /api/ai/insights/{photo_path}` - Get insights for photo
- `GET /api/ai/insights/recommendations` - Get recommendations
- `GET /api/ai/stats` - Get AI statistics

## UI Components Reference

### Core Components
- `DuplicatesReview.tsx` - Duplicate management interface
- `PhotoEditor.tsx` - Photo editing tools
- `PeopleChips.tsx` - People tagging display
- `NotesEditor.tsx` - Photo annotation editor
- `ExportDialog.tsx` - Export and sharing options
- `ProvenanceChips.tsx` - Source status indicators
- `BulkActionsManager.tsx` - Bulk operation controls
- `MultiTagFilter.tsx` - Advanced tag filtering
- `VersionStackViewer.tsx` - Photo version hierarchy
- `LocationCorrection.tsx` - Location correction tools
- `AIInsightsPanel.tsx` - AI-powered recommendations

### Supporting Components
- `GlassDesignSystem.tsx` - Visual design system
- `APIWrapper.tsx` - API service integration
- `PhotoDetail.tsx` - Photo detail view
- `GalleryView.tsx` - Photo gallery display

## Database Schema

### Core Tables
- `duplicates` - Stores duplicate group information
- `photo_edits` - Stores edit instructions for photos
- `face_clusters` - Stores face clustering results
- `photo_notes` - Stores photo annotations
- `shared_links` - Stores share link metadata
- `source_tracking` - Tracks photo origins
- `bulk_transactions` - Logs bulk operations
- `photo_tags` - Stores photo tags with relationships
- `photo_versions` - Stores version relationships
- `photo_locations` - Stores location data
- `ai_insights` - Stores AI-generated insights

### Schema Details
Each feature has its own dedicated tables with appropriate indexes and foreign key relationships where applicable.

## Testing Coverage

### Unit Tests
- All database operations tested with SQLite-based tests
- API endpoint functionality validated
- Component rendering and state management tested
- Error handling scenarios covered

### Integration Tests
- Cross-feature interactions validated
- API endpoint chaining tested
- Database transaction integrity verified
- End-to-end workflows validated

### Performance Tests
- Large photo library handling validated
- Concurrent operation handling tested
- Database query optimization verified
- UI responsiveness maintained under load

## Performance Considerations

### Caching Strategy
- Aggressive caching of computed values (thumbnails, embeddings, face clusters)
- LRU cache implementation for frequently accessed data
- Cache warming to prevent cold start delays

### Database Optimization
- Appropriate indexing for all frequently queried columns
- Connection pooling for database operations
- Batch operations for bulk data processing
- Lazy loading for large data sets

### UI Performance
- Virtual scrolling for large photo lists
- Progressive loading for large galleries
- Memoization for expensive computations
- Debounced search operations

## Security Implementation

### Data Protection
- Client-side encryption for sensitive operations
- Secure token handling for API access
- Input validation and sanitization on all endpoints
- Rate limiting for API endpoints

### Access Control
- Role-based permissions for collaborative features
- Photo-level privacy controls
- Share link expiration and access limits
- Secure deletion with overwrite capabilities

### Privacy Features
- Granular control over photo sharing
- Encryption for sensitive photos
- Audit trails for access operations
- GDPR-compliant data handling