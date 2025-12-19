# Living Museum - Quick Start Guide

This guide provides practical examples of how to use the newly implemented features in the Living Museum photo search application.

## 1. Duplicates Review Lens

### Finding and Managing Duplicates
1. Navigate to the "Duplicates" page from the main menu
2. Click "Scan for Duplicates" to detect similar photos
3. Review duplicate groups by clicking on them to expand
4. Choose resolution options:
   - Keep all: Keep all photos in the group
   - Keep first: Keep the first photo, delete others
   - Delete duplicates: Remove all but the first photo
   - Custom: Select which photos to keep

### API Usage
```javascript
// Scan for duplicates
fetch('/api/duplicates/scan', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ type: 'exact' })
});

// Retrieve duplicate groups
fetch('/api/duplicates')
  .then(response => response.json())
  .then(data => console.log(data.groups));
```

## 2. Photo Editor

### Editing a Photo
1. Open any photo in the viewer
2. Click the "Edit" button (looks like an image with an arrow)
3. Use the controls to adjust brightness, contrast, saturation
4. Use rotation and flip controls to orient the photo
5. Use crop tool to select a region to keep
6. Click "Save Edit" to store the edit instructions

### API Usage
```javascript
// Save edit instructions
fetch('/api/photos/path/to/photo.jpg/edits', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    brightness: 10,
    contrast: 5,
    saturation: -5,
    rotation: 90,
    flipH: false,
    flipV: true
  })
});
```

## 3. Per-Photo Notes

### Adding Notes
1. In the photo detail view, find the "Notes" section
2. Click "Add Note" or the edit icon
3. Type your note in the text area
4. Click "Save" to store the note

### API Usage
```javascript
// Set a note for a photo
fetch('/api/photos/path/to/photo.jpg/notes', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ note: "This is my vacation photo with family" })
});

// Get a note for a photo
fetch('/api/photos/path/to/photo.jpg/notes')
  .then(response => response.json())
  .then(data => console.log(data.note));
```

## 4. Export & Share

### Creating an Export
1. Select multiple photos in the gallery view
2. Click the "Export" button in the action bar
3. Choose an export preset (High Quality, Web Sharing, Print Ready)
4. Adjust options like resolution and metadata inclusion
5. Click "Export" to download the file

### Creating Share Links
1. Select multiple photos
2. Click the "Share" button in the action bar
3. Set expiration time (1 hour to 1 month)
4. Optionally add a password
5. Click "Create Share Link" to generate the link
6. Use the copy button to copy the link to your clipboard

### API Usage
```javascript
// Create a share link
fetch('/share', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    paths: ['/photo1.jpg', '/photo2.jpg'],
    expiration_hours: 24,
    password: 'optional_password'
  })
})
.then(response => response.json())
.then(data => console.log(data.share_url));

// Export photos
fetch('/export', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    paths: ['/photo1.jpg', '/photo2.jpg'],
    options: {
      format: 'zip',
      include_metadata: true,
      max_resolution: 1920
    }
  })
});
```

## 5. Multi-tag Filtering

### Filtering Photos by Multiple Tags
1. Open the search interface
2. Use the multi-tag filter component to add tags
3. Select AND/OR logic (AND = photos must have all tags; OR = photos have any of the tags)
4. The photo grid will update to show matching photos

### API Usage
```javascript
// Search with multiple tags
const response = fetch('/search?tags=beach,vacation,family&tag_logic=OR');
```

## 6. Version Stacks

### Managing Photo Versions
1. In the photo detail view, look for the "Version Stack" section
2. If there are multiple versions, you'll see a stack representation
3. Click to expand and see all versions of the photo
4. Click any version to view it in the main viewer

### API Usage
```javascript
// Create a new version record
fetch('/versions', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    original_path: '/original/photo.jpg',
    version_path: '/edited/photo_v1.jpg',
    version_type: 'edited',
    version_name: 'Summer Edit',
    version_description: 'Enhanced summer colors'
  })
});
```

## 7. Place Correction & Location Clustering

### Correcting Location Names
1. In the photo detail view, find the location section
2. If GPS coordinates exist, click "Edit" to correct the place name
3. Update city, region, and country fields as needed
4. Save to update the location information

### Viewing Location Clusters
1. Navigate to the Places section
2. View clusters of photos organized by location
3. Click on a cluster to see all photos from that place

### API Usage
```javascript
// Add corrected location info
fetch('/locations', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    photo_path: '/path/to/photo.jpg',
    latitude: 40.7128,
    longitude: -74.0060,
    corrected_place_name: 'Manhattan, NYC',
    city: 'New York',
    region: 'New York',
    country: 'USA'
  })
});

// Get location clusters
fetch('/locations/clusters?min_photos=2')
  .then(response => response.json())
  .then(data => console.log(data.clusters));
```

## 8. Safe Bulk Actions

### Performing Bulk Operations
1. Select multiple photos in the gallery view
2. Choose an action (Delete, Favorite, etc.)
3. The action will be performed safely
4. A notification toast will appear with an "Undo" option
5. Click "Undo" within the notification to reverse the action

## API Error Handling

All API endpoints follow a consistent error response format:

```javascript
{
  "detail": "Error description"
}
```

Common HTTP status codes:
- 200: Success
- 400: Bad request (validation error)
- 404: Resource not found
- 500: Internal server error

## Environment Variables

The application uses the following environment variables:

- `VITE_API_URL`: Base URL for API calls (default: http://127.0.0.1:8000)
- `PS_INTENT_PORT`: Port for the UI server (default: 8501)

## Troubleshooting

### Common Issues

1. **Photos not showing in exports**: Verify the file paths are accessible to the server
2. **Location clustering not working**: Ensure photos have valid GPS EXIF data
3. **Face detection not working**: Check if required face detection libraries are installed
4. **Version stacks not appearing**: Verify version records are properly created in the database

### Verifying Installation

To verify all features are working correctly:

```bash
# Run the test suite
pytest tests/test_new_features.py
pytest tests/test_integration.py

# Verify API endpoints are accessible
curl http://localhost:8000/api/notes/stats
curl http://localhost:8000/api/versions/stats
curl http://localhost:8000/api/locations/stats
```