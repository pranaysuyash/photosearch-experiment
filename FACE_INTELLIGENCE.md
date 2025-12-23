# Face Intelligence System

A comprehensive face detection, recognition, and management system for the PhotoSearch application.

## Features

### Core Capabilities

- **Face Detection**: InsightFace backend with RetinaFace detection
- **Face Recognition**: ArcFace embeddings for face matching
- **Clustering**: DBSCAN clustering to group similar faces
- **Person Management**: Full CRUD operations for managing identified people

### Reversible Operations

All face operations support full undo:
- Merge clusters
- Split faces to new person
- Move face between clusters
- Hide/unhide people
- Rename people
- Confirm/reject face assignments

### Key Features

| Feature | Description |
|---------|-------------|
| **Unknown Bucket** | View unassigned faces that need classification |
| **Trust Signals** | Confirm/reject controls with assignment state badges |
| **Mixed Cluster Detection** | Automatic detection of clusters with multiple people |
| **Review Queue** | Borderline confidence faces for human review |
| **Prototype-Based Assignment** | Fast matching for new faces |
| **Co-occurrence Search** | Find photos with specific combinations of people |
| **Similar Face Search** | "Find more like this face" feature |

## API Reference

### Person Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/faces/clusters` | GET | Get all face clusters |
| `/api/faces/clusters/visible` | GET | Get non-hidden clusters |
| `/api/faces/clusters/hidden` | GET | Get hidden clusters |
| `/api/faces/clusters/{id}/hide` | POST | Hide a person |
| `/api/faces/clusters/{id}/unhide` | POST | Unhide a person |
| `/api/faces/clusters/{id}/rename` | POST | Rename with undo |
| `/api/faces/clusters/{id}/coherence` | GET | Coherence analysis |

### Face Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/faces/{face_id}/confirm` | POST | Confirm face assignment |
| `/api/faces/{face_id}/reject` | POST | Reject face from cluster |
| `/api/faces/split` | POST | Split faces to new person |
| `/api/faces/move` | POST | Move face to different cluster |
| `/api/faces/merge` | POST | Merge clusters with undo |
| `/api/faces/undo` | POST | Undo last operation |
| `/api/faces/unassigned` | GET | Get unknown bucket |

### Search & Retrieval

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/faces/{id}/similar` | GET | Find similar faces |
| `/api/photos/by-people` | POST | Co-occurrence search |
| `/api/photos/by-people-names` | GET | Search by names |
| `/api/photos/{path}/people` | GET | Get people in photo |

### Assignment & Indexing

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/faces/assign` | POST | Assign face to cluster |
| `/api/faces/batch-assign` | POST | Bulk face assignment |
| `/api/faces/index/stats` | GET | Index statistics |
| `/api/faces/prototypes/recompute` | POST | Recompute prototypes |
| `/api/faces/mixed-clusters` | GET | Get suspected mixed clusters |
| `/api/faces/review-queue` | GET | Get faces needing review |

## Usage Examples

### Search Photos by People

```python
# Find photos with Alice AND Bob
result = db.get_photos_with_people(
    include_people=['alice_cluster_id', 'bob_cluster_id'],
    require_all=True
)

# Find photos with Alice but NOT Bob
result = db.get_photos_with_people(
    include_people=['alice_cluster_id'],
    exclude_people=['bob_cluster_id']
)

# Natural language search
result = db.search_photos_by_people("Alice Bob", mode="and")
result = db.search_photos_by_people("Alice !Bob")  # Alice not Bob
```

### Find Similar Faces

```python
# Find faces similar to a specific detection
similar = db.find_similar_faces(
    detection_id='abc123',
    limit=20,
    threshold=0.5
)
```

### Assignment Thresholds

The prototype-based assignment system uses two thresholds:

- **auto_assign_min (0.55)**: Above this, faces are automatically assigned
- **review_min (0.50)**: Above this but below auto_assign, faces go to review queue
- Below review_min: Faces marked as unknown

## Database Schema

### Tables

- `face_detections` - Individual detected faces
- `face_clusters` - People (groups of similar faces)
- `photo_person_associations` - Links photos to people
- `face_rejections` - Tracks rejected face assignments
- `person_operations_log` - Undo log with full snapshots
- `schema_version` - Migration tracking

### Key Columns

| Table | Column | Purpose |
|-------|--------|---------|
| `photo_person_associations` | `assignment_state` | 'auto', 'user_confirmed', 'user_rejected' |
| `face_clusters` | `hidden` | 0=visible, 1=hidden |
| `face_clusters` | `prototype_embedding` | Centroid for fast matching |

## Architecture

```
Frontend (React)
    ├── ClusterManagement.tsx  - People grid with hide/unhide
    ├── PersonDetail.tsx       - Individual person view with confirm/reject
    └── api.ts                 - API client methods

Backend (FastAPI)
    ├── face_recognition.py    - 23 API endpoints
    ├── face_clustering_db.py  - Database operations
    ├── face_embedding_index.py - Similarity search
    └── face_schema_migrations.py - Schema versioning

Database (SQLite)
    └── face_clusters.db       - All face data
```

## Configuration

Add to your `.env` or `config.py`:

```python
FACE_CLUSTERS_DB_PATH = "./data/face_clusters.db"
```

## Performance Notes

- LinearIndex: Suitable for up to ~10K faces
- FaissIndex: Placeholder for 10K+ faces (not yet implemented)
- Prototype-based assignment: O(n) per face where n = number of clusters
