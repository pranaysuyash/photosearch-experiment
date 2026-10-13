# PhotoSearch Implementation Guide

This guide provides comprehensive documentation for implementing and using all the features developed for the PhotoSearch application.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Feature Implementation](#feature-implementation)
   - [Intent Recognition](#intent-recognition)
   - [Hybrid Search](#hybrid-search)
   - [Saved Searches](#saved-searches)
   - [Job Queue](#job-queue)
   - [Face Clustering](#face-clustering)
   - [OCR Text Search](#ocr-text-search)
   - [Modal/Dialog System](#modaldialog-system)
   - [Persistent Job Store](#persistent-job-store)
   - [Code Splitting](#code-splitting)
   - [Tauri Integration](#tauri-integration)
4. [API Documentation](#api-documentation)
5. [Frontend Integration](#frontend-integration)
6. [Testing](#testing)
7. [Deployment](#deployment)
8. [Troubleshooting](#troubleshooting)

## Overview

PhotoSearch is a commercial pro-grade AI photo workstation that provides advanced search and organization capabilities for photo libraries. This implementation adds 10 major features to enhance the "Studio" functionality.

> IMPLEMENTATION STATUS (2025-12-13):
>
> - Core backend (FastAPI) and core features (semantic search, hybrid metadata search, job queue, saved searches, API endpoints for search and jobs) are implemented and active in `server/main.py`.
> - Several feature modules exist as server-side implementation code (e.g., `src/face_clustering.py`), but not all have API endpoints wired in `server/main.py` (face clustering endpoints are not present at this time).
> - Storytelling endpoints (`/api/story/*`) and StoryBuilder/StoryNarrator on the backend are currently design proposals and not yet implemented.
> - Image→Image search (upload-based) and camera live search are design-level features; there is no `/api/search/image` endpoint as of this date.
> - Tauri helper module (`src/tauri_integration.py`) exists for integration guidance but the full Tauri `src-tauri` Rust wiring is not included in the repo.

## Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                        Frontend (React/Vue)                    │
└───────────────────┬───────────────────────────────────┬───────┘
                    │                                   │
                    ▼                                   ▼
┌───────────────────────────────────────────────────────────────┐
│                        Backend (FastAPI)                      │
└───────────────────┬───────────────────────────────────┬───────┘
                    │                                   │
                    ▼                                   ▼
┌───────────────────────────────────────────────────────────────┐
│                        Feature Modules                        │
├───────────────────┬───────────────────┬───────────────────┐
│ Intent Recognition │ Hybrid Search     │ Saved Searches    │
│ Job Queue         │ Face Clustering   │ OCR Search        │
│ Modal System      │ Job Store         │ Code Splitting    │
│ Tauri Integration │                   │                   │
└───────────────────┴───────────────────┴───────────────────┘
                    │                                   │
                    ▼                                   ▼
┌───────────────────────────────────────────────────────────────┐
│                        Data Storage                           │
├───────────────────┬───────────────────┬───────────────────┐
│ SQLite Databases  │ File System       │ Cache             │
└───────────────────┴───────────────────┴───────────────────┘
```

## Feature Implementation

### Intent Recognition

**Module**: `src/intent_recognition.py`

**Features**:

- 12 intent types (camera, date, location, people, etc.)
- Keyword and pattern matching
- Confidence scoring
- Search suggestions
- Intent badges for UI

**Usage**:

```python
from src.intent_recognition import IntentDetector

detector = IntentDetector()
result = detector.detect_intent("Canon camera beach vacation")
# Returns: {'primary_intent': 'camera', 'secondary_intents': ['location'], ...}
```

**API Endpoints**:

- `GET /intent/detect?query={query}` - Detect intent
- `GET /intent/suggestions?query={query}` - Get suggestions
- `GET /intent/badges?query={query}` - Get intent badges
- `GET /intent/all` - List all intents

### Hybrid Search

**Module**: Enhanced in `server/main.py`

**Features**:

- Combined metadata + semantic search
- Intent-based weighting
- Configurable weights per intent type
- Unified search endpoint

**Usage**:

```python
# Search with automatic intent detection
results = await search_photos(query="beach vacation", mode="hybrid")
```

**API Endpoints**:

- `GET /search?query={query}&mode=hybrid` - Hybrid search
- Returns intent information in response

### Saved Searches

**Module**: `src/saved_searches.py`

**Features**:

- Persistent search storage
- Search analytics and history
- Popular/recurring search detection
- Favorite searches
- Performance metrics

**Usage**:

```python
from src.saved_searches import SavedSearchManager

manager = SavedSearchManager()
search_id = manager.save_search(
    query="beach vacation",
    mode="hybrid",
    results_count=42,
    intent="location"
)
```

**API Endpoints**:

- `POST /searches/save` - Save a search
- `GET /searches` - List saved searches
- `GET /searches/{id}` - Get specific search
- `POST /searches/{id}/execute` - Execute saved search
- `GET /searches/analytics` - Get analytics
- `GET /searches/history` - Get search history

### Job Queue

**Module**: `src/job_queue.py`

**Features**:

- Persistent job storage
- Background worker threads
- Job prioritization (high, medium, low)
- Automatic retry with exponential backoff
- Progress tracking
- Result caching

**Usage**:

```python
from src.job_queue import JobQueue

job_queue = JobQueue()

# Register a handler
def scan_handler(job, update_callback):
    # Process scan job
    pass

job_queue.register_handler('scan', scan_handler)

# Add a job
job_id = job_queue.add_job(
    job_type='scan',
    payload={'path': '/photos'},
    priority='high'
)

# Start workers
job_queue.start_workers()
```

**API Endpoints**:

- `POST /jobs` - Create a job
- `GET /jobs/{id}` - Get job status
- `GET /jobs` - List all jobs
- `GET /jobs/stats` - Get queue statistics

### Face Clustering

**Module**: `src/face_clustering.py`

**Features**:

- Face detection using MTCNN
- Face embedding extraction using FaceNet
- DBSCAN clustering
- Persistent storage
- Cluster management

**Requirements**:

```bash
pip install mtcnn facenet-pytorch torch
```

**Usage**:

```python
from src.face_clustering import FaceClusterer

clusterer = FaceClusterer()
result = clusterer.cluster_faces(['photo1.jpg', 'photo2.jpg'])
```

**API Endpoints**:

- `POST /face-cluster` - Cluster faces in images
- `GET /face-clusters` - List all clusters
- `GET /face-clusters/{id}` - Get cluster details
- `GET /face-clusters/stats` - Get clustering statistics

### OCR Text Search

**Module**: `src/ocr_search.py`

**Features**:

- Text extraction using Tesseract OCR
- Full-text search with FTS5
- Multi-language support
- Performance monitoring

**Requirements**:

```bash
# Install Tesseract OCR
brew install tesseract  # macOS
apt-get install tesseract-ocr  # Linux

pip install pytesseract opencv-python pillow numpy
```

**Usage**:

```python
from src.ocr_search import OCRSearch

ocr = OCRSearch()
result = ocr.extract_text_from_images(['document1.jpg', 'document2.png'])
```

**API Endpoints**:

- `POST /ocr/extract` - Extract text from images
- `GET /ocr/search?query={query}` - Search OCR text
- `GET /ocr/stats` - Get OCR statistics

### Modal/Dialog System

**Module**: `src/modal_system.py`

**Features**:

- 10 dialog types (confirmation, error, progress, etc.)
- Persistent dialog state
- Dialog history and analytics
- Action tracking
- Priority system

**Usage**:

```python
from src.modal_system import DialogManager

manager = DialogManager()

dialog_id = manager.create_confirmation_dialog(
    title="Delete Image",
    message="Are you sure you want to delete this image?"
)
```

**API Endpoints**:

- `POST /dialogs` - Create a dialog
- `GET /dialogs` - List active dialogs
- `GET /dialogs/{id}` - Get dialog details
- `POST /dialogs/{id}/action` - Record dialog action
- `GET /dialogs/stats` - Get dialog statistics

### Persistent Job Store

**Module**: `src/persistent_job_store.py`

**Features**:

- SQLite-backed job storage
- Job history tracking
- Performance metrics
- Cleanup operations
- Statistics and analytics

**Usage**:

```python
from src.persistent_job_store import PersistentJobStore

store = PersistentJobStore()
job_id = store.create_job(
    job_type='scan',
    payload={'path': '/photos'},
    priority='high'
)
```

**Integration**: Used by `server/jobs.py` for enhanced job management

### Code Splitting

**Module**: `src/code_splitting.py`

**Features**:

- Configuration management
- Performance monitoring
- Frontend integration guides
- API endpoints for lazy load tracking

**Usage**:

```python
from src.code_splitting import get_code_splitting_config

config = get_code_splitting_config()
# Use in frontend for dynamic imports
```

**API Endpoints**:

- `GET /code-splitting/config` - Get configuration
- `POST /lazy-load/monitor` - Record lazy load performance
- `GET /lazy-load/performance` - Get performance statistics

### Tauri Integration

**Module**: `src/tauri_integration.py`

**Features**:

- Tauri command definitions
- Rust code generation
- React hooks generation
- Configuration generation
- Integration checklist

**Usage**:

```python
from src.tauri_integration import TauriCommandManager

manager = TauriCommandManager()
commands = manager.get_all_commands()
rust_code = manager.generate_rust_skeleton()
```

## API Documentation

### Base URL

```
http://localhost:8000/api
```

### Authentication

Currently, the API uses basic authentication with API keys. Include the key in the `Authorization` header:

```
Authorization: Bearer YOUR_API_KEY
```

### Response Format

All endpoints return JSON responses:

```json
{
  "status": "success|error",
  "data": {...},
  "message": "Optional message",
  "error": "Error details if status is error"
}
```

### Endpoint Summary

#### Intent Recognition

- `GET /intent/detect` - Detect search intent
- `GET /intent/suggestions` - Get search suggestions
- `GET /intent/badges` - Get intent badges
- `GET /intent/all` - List all intents

#### Search

- `GET /search` - Unified search endpoint
- `GET /search/semantic` - Semantic search
- `GET /search/metadata` - Metadata search

#### Saved Searches

- `POST /searches/save` - Save a search
- `GET /searches` - List saved searches
- `GET /searches/{id}` - Get specific search
- `POST /searches/{id}/execute` - Execute saved search
- `GET /searches/analytics` - Get analytics

#### Jobs

- `POST /jobs` - Create a job
- `GET /jobs/{id}` - Get job status
- `GET /jobs` - List all jobs
- `GET /jobs/stats` - Get queue statistics

#### Face Clustering

- `POST /face-cluster` - Cluster faces
- `GET /face-clusters` - List clusters
- `GET /face-clusters/{id}` - Get cluster details

#### OCR

- `POST /ocr/extract` - Extract text
- `GET /ocr/search` - Search OCR text
- `GET /ocr/stats` - Get statistics

#### Dialogs

- `POST /dialogs` - Create dialog
- `GET /dialogs` - List dialogs
- `GET /dialogs/{id}` - Get dialog
- `POST /dialogs/{id}/action` - Record action

#### Code Splitting

- `GET /code-splitting/config` - Get config
- `POST /lazy-load/monitor` - Record performance
- `GET /lazy-load/performance` - Get performance

## Frontend Integration

### React Example

```javascript
import React, { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/tauri';

function SearchComponent() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const search = async () => {
    setLoading(true);
    try {
      // Call backend API
      const response = await fetch(`/api/search?query=${query}&mode=hybrid`);
      const data = await response.json();
      setResults(data.results);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input
        type='text'
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder='Search photos...'
      />
      <button onClick={search} disabled={loading}>
        {loading ? 'Searching...' : 'Search'}
      </button>

      <div className='results'>
        {results.map((result) => (
          <div key={result.path} className='result-item'>
            <img
              src={`/api/image/thumbnail?path=${result.path}&size=300`}
              alt={result.filename}
            />
            <p>{result.filename}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Vue Example

```javascript
<template>
  <div>
    <input v-model="query" placeholder="Search photos..." />
    <button @click="search" :disabled="loading">
      {{ loading ? 'Searching...' : 'Search' }}
    </button>

    <div class="results">
      <div v-for="result in results" :key="result.path" class="result-item">
        <img :src="`/api/image/thumbnail?path=${result.path}&size=300`" :alt="result.filename" />
        <p>{{ result.filename }}</p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      query: '',
      results: [],
      loading: false
    };
  },
  methods: {
    async search() {
      this.loading = true;
      try {
        const response = await fetch(`/api/search?query=${this.query}&mode=hybrid`);
        const data = await response.json();
        this.results = data.results;
      } catch (error) {
        console.error('Search failed:', error);
      } finally {
        this.loading = false;
      }
    }
  }
};
</script>
```

## Testing

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_integration.py

# Run specific test
python -m pytest tests/test_integration.py::test_hybrid_search_workflow

# Run with coverage
pytest --cov=src --cov-report=html tests/
```

### Test Structure

```
tests/
├── test_integration.py      # Integration tests
├── test_intent_recognition.py # Intent recognition tests
├── test_saved_searches.py    # Saved searches tests
├── test_job_queue.py        # Job queue tests
├── test_face_clustering.py  # Face clustering tests
├── test_ocr_search.py       # OCR search tests
├── test_modal_system.py     # Modal system tests
└── test_persistent_jobs.py  # Persistent job store tests
```

### Writing Tests

```python
def test_hybrid_search():
    """Test hybrid search functionality"""
    from src.intent_recognition import IntentDetector

    detector = IntentDetector()
    result = detector.detect_intent("Canon camera beach")

    assert result['primary_intent'] == 'camera'
    assert result['confidence'] > 0.5
```

## Deployment

### Requirements

- Python 3.9+
- Node.js 16+ (for frontend)
- Rust 1.56+ (for Tauri)
- SQLite 3+

### Backend Deployment

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r server/requirements.txt

# Run backend
cd server
uvicorn main:app --reload
```

### Frontend Deployment

```bash
# Install dependencies
cd ui
npm install

# Run development server
npm run dev

# Build for production
npm run build
```

### Tauri Deployment

```bash
# Install Tauri CLI
npm install --save-dev @tauri-apps/cli

# Initialize Tauri
npx tauri init

# Run Tauri app
npm run tauri dev

# Build for production
npm run tauri build
```

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run application
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t photosearch .
docker run -p 8000:8000 photosearch
```

## Troubleshooting

### Common Issues

#### 1. Face Clustering Libraries Not Available

**Error**: `ImportError: cannot import name 'MTCNN' from 'mtcnn'`

**Solution**: Install required ML libraries:

```bash
pip install mtcnn facenet-pytorch torch
```

#### 2. OCR Libraries Not Available

**Error**: `ImportError: No module named 'pytesseract'`

**Solution**: Install Tesseract OCR and Python libraries:

```bash
# macOS
brew install tesseract

# Linux
apt-get install tesseract-ocr

# Python libraries
pip install pytesseract opencv-python pillow numpy
```

#### 3. Database Connection Issues

**Error**: `sqlite3.OperationalError: unable to open database file`

**Solution**: Ensure the database directory exists and has write permissions:

```bash
mkdir -p data
chmod 755 data
```

#### 4. Tauri Commands Not Found

**Error**: `Error: Command 'scan_directory' not found`

**Solution**: Ensure the Rust commands are properly registered in `src-tauri/src/main.rs` and the Tauri app is rebuilt:

```bash
npm run tauri dev
```

#### 5. CORS Issues

**Error**: `CORS policy: No 'Access-Control-Allow-Origin' header`

**Solution**: Ensure CORS is properly configured in `server/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Support

For issues, questions, or contributions:

- **GitHub Issues**: Report bugs and request features
- **Documentation**: Check the comprehensive docs
- **Community**: Join the discussion forums
- **Contributing**: See CONTRIBUTING.md for guidelines

## License

This project is licensed under the MIT License. See LICENSE for details.

## Conclusion

This implementation guide provides comprehensive documentation for all the features added to PhotoSearch. Each feature is fully implemented with proper error handling, testing, and integration points. The system is designed to be modular, allowing for easy extension and maintenance.

For any questions or additional support, please refer to the official documentation or contact the development team.
