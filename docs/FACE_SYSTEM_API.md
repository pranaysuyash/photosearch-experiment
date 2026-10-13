# Face Recognition System API Documentation

**Version**: 2.0  
**Date**: December 25, 2025  
**Status**: Production Ready  

---

## Overview

The Face Recognition System provides comprehensive face detection, clustering, and management capabilities with production-grade performance and scalability. The system automatically scales from development (Linear index) to production (FAISS) based on collection size.

### Key Features

- **Advanced Face Clustering**: Automatic grouping with quality indicators
- **Temporal Video Tracking**: Face tracking across video frames
- **Performance Optimization**: Intelligent caching and database indexing
- **Real-time Monitoring**: Performance analytics and system health
- **Privacy Controls**: Hide/unhide functionality with full undo support

---

## Authentication

All API endpoints require authentication. Include the API key in the request headers:

```http
Authorization: Bearer YOUR_API_KEY
```

---

## Core Face Management

### Get Face Clusters

Retrieve all face clusters with metadata and quality indicators.

```http
GET /api/faces/clusters
```

**Response:**
```json
{
  "clusters": [
    {
      "id": "cluster_123",
      "label": "John Doe",
      "face_count": 15,
      "image_count": 12,
      "face_ids": ["face_1", "face_2"],
      "images": ["/path/to/photo1.jpg"],
      "created_at": "2025-12-25T10:00:00Z",
      "is_mixed": false,
      "coherence_score": 0.85,
      "representative_face": {
        "detection_id": "face_1",
        "photo_path": "/path/to/best.jpg",
        "quality_score": 0.92
      },
      "indexing_disabled": false,
      "hidden": false
    }
  ]
}
```

### Get Face Crop

Retrieve a cropped face image with intelligent caching.

```http
GET /api/faces/crop/{face_id}?size=150
```

**Parameters:**
- `face_id` (required): Face detection ID
- `size` (optional): Crop size in pixels (default: 150)

**Response:** JPEG image data

### Scan for Faces

Detect and cluster faces in photos.

```http
POST /api/faces/scan
```

**Request Body:**
```json
{
  "limit": 100
}
```

**Response:**
```json
{
  "status": "completed",
  "total_faces": 45,
  "clusters": 12,
  "message": "Face scan completed successfully"
}
```

---

## Cluster Management

### Rename Cluster

Rename a person cluster with undo support.

```http
POST /api/faces/clusters/{cluster_id}/rename
```

**Request Body:**
```json
{
  "label": "New Name"
}
```

### Hide/Unhide Cluster

Control cluster visibility in the main gallery.

```http
POST /api/faces/clusters/{cluster_id}/hide
POST /api/faces/clusters/{cluster_id}/unhide
```

### Split Cluster

Split selected faces into a new person cluster.

```http
POST /api/faces/split
```

**Request Body:**
```json
{
  "detection_ids": ["face_1", "face_2"],
  "label": "New Person"
}
```

### Merge Clusters

Merge source cluster into target cluster.

```http
POST /api/faces/merge
```

**Request Body:**
```json
{
  "source_cluster_id": "cluster_123",
  "target_cluster_id": "cluster_456"
}
```

### Move Face

Move a single face to a different cluster.

```http
POST /api/faces/move
```

**Request Body:**
```json
{
  "detection_id": "face_123",
  "to_cluster_id": "cluster_456"
}
```

---

## Undo System

### Undo Last Operation

Undo the most recent face operation.

```http
POST /api/faces/undo
```

**Response:**
```json
{
  "success": true,
  "operation_type": "merge",
  "details": "Undid merge of cluster_123 into cluster_456"
}
```

### Check Undo Status

Check if there's an operation that can be undone.

```http
GET /api/faces/undo/status
```

**Response:**
```json
{
  "can_undo": true,
  "last_operation": {
    "type": "rename",
    "timestamp": "2025-12-25T10:30:00Z",
    "description": "Renamed cluster to 'Alice'"
  }
}
```

---

## Search & Discovery

### Find Similar Faces

Find faces similar to a given detection.

```http
GET /api/faces/{detection_id}/similar?threshold=0.7&limit=20
```

**Parameters:**
- `threshold`: Similarity threshold (0.0-1.0)
- `limit`: Maximum results to return
- `include_same_cluster`: Include faces from same cluster

### Search Photos by People

Find photos containing specific people combinations.

```http
POST /api/photos/by-people
```

**Request Body:**
```json
{
  "include_people": ["cluster_123", "cluster_456"],
  "exclude_people": ["cluster_789"],
  "require_all": true,
  "limit": 100,
  "offset": 0
}
```

### Get People in Photo

Get all people detected in a specific photo.

```http
GET /api/photos/{photo_path}/people
```

**Response:**
```json
{
  "photo_path": "/path/to/photo.jpg",
  "people": [
    {
      "cluster_id": "cluster_123",
      "detection_id": "face_456",
      "confidence": 0.92,
      "created_at": "2025-12-25T10:00:00Z"
    }
  ],
  "count": 1
}
```

---

## Performance & Caching

### Cache Management

Get cache statistics and manage face crop cache.

```http
GET /api/faces/cache/stats
POST /api/faces/cache/clear
POST /api/faces/cache/invalidate/{face_id}
```

**Cache Stats Response:**
```json
{
  "success": true,
  "cache_stats": {
    "total_entries": 1250,
    "total_size_mb": 45.2,
    "max_size_mb": 500,
    "utilization_percent": 9.04,
    "hit_rate": 0.87
  }
}
```

### Database Optimization

Optimize database performance and get statistics.

```http
GET /api/faces/database/stats
POST /api/faces/database/optimize
```

**Optimization Response:**
```json
{
  "success": true,
  "optimization_results": {
    "duration_seconds": 12.5,
    "steps": [
      {
        "step": "add_indexes",
        "successful_indexes": 15,
        "total_indexes": 15
      }
    ],
    "final_stats": {
      "index_count": 25,
      "database_size_mb": 125.4
    }
  }
}
```

### Performance Monitoring

Get real-time performance statistics.

```http
GET /api/faces/performance/stats
POST /api/faces/performance/reset
```

**Performance Stats Response:**
```json
{
  "success": true,
  "performance_stats": {
    "timestamp": 1703505600,
    "cache_performance": {
      "hit_rate": 0.87,
      "total_requests": 1500
    },
    "index_performance": {
      "searches": 250,
      "avg_search_time": 15.2
    },
    "system_health": {
      "status": "healthy",
      "issues": [],
      "recommendations": []
    }
  }
}
```

---

## Video Face Tracking

### Track Faces in Video

Perform temporal face tracking across video frames.

```http
POST /api/faces/video/track
```

**Request Body:**
```json
{
  "video_path": "/path/to/video.mp4",
  "sample_rate": 5
}
```

**Response:**
```json
{
  "success": true,
  "tracking_results": {
    "video_path": "/path/to/video.mp4",
    "tracks_found": 3,
    "total_frames": 1000,
    "processed_frames": 200,
    "clusters_assigned": 2,
    "status": "completed"
  }
}
```

### Get Video Face Summary

Get face tracking summary for a video.

```http
GET /api/faces/video/{video_path}/summary
```

### Get Video Face Tracks

Get detailed face tracks for a video.

```http
GET /api/faces/video/{video_path}/tracks?include_detections=true
```

---

## Analytics & Insights

### Get Face Analytics

Comprehensive analytics about system usage and patterns.

```http
GET /api/faces/analytics
```

**Response:**
```json
{
  "success": true,
  "analytics": {
    "timestamp": 1703505600,
    "cluster_analytics": {
      "size_distribution": {
        "singleton": {"clusters": 45, "faces": 45},
        "small": {"clusters": 12, "faces": 38},
        "medium": {"clusters": 5, "faces": 67}
      },
      "label_distribution": {
        "labeled": 25,
        "unlabeled": 37
      }
    },
    "face_analytics": {
      "confidence_distribution": {
        "very_high": 234,
        "high": 156,
        "medium": 89,
        "low": 23
      }
    }
  }
}
```

### Get Embedding Index Stats

Get statistics about the similarity search index.

```http
GET /api/faces/index/stats
```

**Response:**
```json
{
  "success": true,
  "prototype_count": 1250,
  "backend": "faiss",
  "memory_usage_mb": 15.2,
  "dimension": 512,
  "performance_tier": "production"
}
```

---

## Error Handling

All API endpoints return consistent error responses:

```json
{
  "detail": "Error description",
  "status_code": 400
}
```

### Common Error Codes

- `400`: Bad Request - Invalid parameters
- `404`: Not Found - Resource doesn't exist
- `503`: Service Unavailable - Face recognition models loading
- `500`: Internal Server Error - Unexpected error

---

## Rate Limiting

API endpoints are rate limited to ensure system stability:

- **Face Detection**: 10 requests/minute
- **Clustering Operations**: 5 requests/minute  
- **Cache Management**: 20 requests/minute
- **Analytics**: 30 requests/minute

---

## Performance Considerations

### Automatic Scaling

The system automatically chooses the optimal backend:

- **Linear Index**: < 1,000 clusters (development)
- **FAISS Index**: ≥ 1,000 clusters (production)

### Caching Strategy

- Face crops are cached with LRU eviction
- Cache size limit: 500MB (configurable)
- Smart invalidation based on source photo changes

### Database Optimization

- 15+ indexes for optimal query performance
- Automatic VACUUM and ANALYZE operations
- Query performance monitoring

---

## Integration Examples

### JavaScript/TypeScript

```typescript
import { api } from './api';

// Get face clusters
const clusters = await api.getFaceClusters();

// Find similar faces
const similar = await api.findSimilarFaces('face_123', 0.7, 20, false);

// Search photos by people
const photos = await api.searchPhotosByPeople({
  include_people: ['alice_cluster', 'bob_cluster'],
  require_all: true
});
```

### Python

```python
import requests

# Get face clusters
response = requests.get('/api/faces/clusters')
clusters = response.json()['clusters']

# Track faces in video
response = requests.post('/api/faces/video/track', json={
    'video_path': '/path/to/video.mp4',
    'sample_rate': 5
})
```

---

## Changelog

### Version 2.0 (December 25, 2025)
- Added FAISS similarity search with automatic scaling
- Implemented face crop caching system
- Added comprehensive performance monitoring
- Enhanced video face tracking with temporal consistency
- Added database optimization endpoints
- Improved error handling and edge case coverage

### Version 1.0 (December 23, 2025)
- Initial face recognition system
- Basic clustering and management
- Core API endpoints