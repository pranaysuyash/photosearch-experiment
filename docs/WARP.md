# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

**Living Museum** - AI-powered photo search application with semantic search, 3D globe visualization, and comprehensive metadata extraction. Built with Python (FastAPI backend) + React (frontend) + LanceDB (vector storage).

**Target**: Self-hosted media management with local/cloud support, privacy-focused alternative to Google Photos.

## Common Commands

### Python Backend Development

```bash
# Activate virtual environment (REQUIRED for all Python commands)
source .venv/bin/activate  # or `.venv/bin/activate` from project root

# Install/update Python dependencies
pip install -r requirements.txt

# Run FastAPI server (port 8000)
python server/main.py
# OR with uvicorn directly:
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000

# Run file discovery (scan for media)
python file_discovery.py --scan --path ~/Pictures

# Extract metadata from media files
python metadata_extractor.py <file_path> --output metadata.json

# Analyze formats in catalog
python format_analyzer.py --stats

# Interactive photo search
python photo_search.py --search

# Quick metadata search
python photo_search.py --quick-search "camera=Canon"
```

### Frontend Development

```bash
# Navigate to UI directory first
cd ui

# Install dependencies (first time setup)
npm install

# Start dev server (port 5173)
npm run dev

# Build for production
npm run build

# Run linter
npm run lint

# Preview production build
npm run preview
```

### Testing

Python tests use simple assertion-based functions (not pytest/unittest):
```bash
# Test vector store
python test_vector_store.py

# Test embedding generation
python test_embedding.py

# Test image loader
python test_loader.py
```

No formal test framework - tests are standalone scripts with `if __name__ == "__main__"` blocks.

## Architecture Overview

### Backend (Python)

**Core Components:**
- `photo_search.py` - Unified interface: scan → extract → index → search
- `metadata_search.py` - SQLite database with version tracking, query engine
- `metadata_extractor.py` - Comprehensive extraction (EXIF, GPS, video, filesystem, xattr)
- `file_discovery.py` - Recursive directory scanning, incremental updates
- `format_analyzer.py` - Media format analysis and statistics

**Server (FastAPI):**
- `server/main.py` - REST API with endpoints for scan, search, export
- `server/config.py` - Pydantic settings (loads from `.env`)
- `server/lancedb_store.py` - Vector storage (embeddings)
- `server/embedding_generator.py` - CLIP-based embeddings (images + text)
- `server/image_loader.py` - Image preprocessing, video frame extraction
- `server/watcher.py` - Real-time file system monitoring (watchdog)
- `server/jobs.py` - In-memory job tracking for async operations

**Data Flow:**
1. **Scan**: `file_discovery.py` → catalog JSON
2. **Extract**: `metadata_extractor.py` → SQLite DB (via `metadata_search.py`)
3. **Embed**: `embedding_generator.py` → LanceDB vectors (via `lancedb_store.py`)
4. **Search**: Query engine searches SQLite + vector similarity
5. **Serve**: FastAPI exposes REST endpoints consumed by React UI

**Key Decisions:**
- **LanceDB chosen over FAISS/ChromaDB** (see `experiments/EXPERIMENT_LOG.md` - best balance of speed/disk usage)
- **CLIP embeddings** (512-dim, `clip-ViT-B-32` model via sentence-transformers)
- **SQLite for metadata** (with JSON storage for flexibility, full-text search)
- **File hashing** for change detection (SHA-256)

### Frontend (React + TypeScript)

**Stack:**
- React 19 + TypeScript + Vite
- Tailwind CSS + shadcn/ui components
- React Three Fiber (3D globe visualization)
- React Router (navigation)

**Key Features:**
- PhotoGrid (masonry layout with infinite scroll)
- PhotoGlobe (3D globe with GPS markers using NASA texture)
- PhotoDetail modal (full metadata display)
- Advanced search syntax (`filename:`, `size:>5MB`, `date:`, `camera:`)
- Multi-select + bulk export (ZIP download)
- Dark/light theme toggle
- Timeline visualization (photos over time)

### Database Schema

**SQLite Tables** (in `photo_metadata.db`):
- `metadata` - Current metadata for each file (path, hash, JSON blob, version)
- `metadata_history` - Version history of metadata changes
- `deleted_metadata` - Soft-deleted files tracking

**LanceDB** (in `data/vector_store/`):
- Columnar vector storage with metadata
- Uses full file path as ID for uniqueness
- 512-dimensional CLIP embeddings

## Development Practices

### Module Design
- **One task = One file** principle (each `.py` file is standalone + importable)
- All modules have CLI interfaces (`if __name__ == "__main__"`)
- Type hints required for function signatures
- Google-style docstrings

### Error Handling
- Graceful failures with logging (`logging` module, not just `print`)
- Try-except blocks for I/O operations
- Validation at API boundaries

### Configuration
- `.env` file for settings (never commit secrets)
- `server/config.py` uses Pydantic for validation
- Auto-detects device (MPS/CUDA/CPU) for PyTorch

### File Organization
```
Root modules: Core logic (scan, extract, search)
server/: FastAPI backend + AI components
ui/: React frontend (separate npm project)
experiments/: Vector store benchmarks (FAISS/Chroma/LanceDB)
docs/: Architecture, roadmaps, historical decisions
data/: Generated databases, vector stores (gitignored)
media/: Default scan directory for local testing
```

### API Conventions
- FastAPI with Pydantic models for request/response validation
- CORS enabled for localhost:5173 (Vite dev server)
- Background tasks for long operations (scanning)
- File serving for media preview (`/file/<path>` endpoint)

## Important Notes

### Dependencies
**Python** (requires 3.9+):
- Core: `Pillow`, `exifread`, `ffmpeg-python`, `python-magic`, `xattr`, `tqdm`
- AI/ML: `sentence-transformers`, `torch`
- Vector: `lancedb`, `pyarrow`
- API: `fastapi`, `uvicorn`, `pydantic-settings`
- Watch: `watchdog`

**Node** (UI):
- Vite + React 19 + TypeScript
- Three.js (3D rendering)
- Tailwind + shadcn/ui

### Platform Notes
- **xattr** (extended attributes) only works on macOS/Linux (gracefully skips on Windows)
- **ffmpeg** must be installed system-wide for video metadata extraction
- **MPS acceleration** (Apple Silicon) auto-detected for embeddings

### Testing Strategy
Tests are simple scripts without pytest/unittest framework. Run individually to verify functionality. No test suite runner configured.

### Real-time Features
- **File watcher** (`watchdog`) monitors `media/` directory on server startup
- Automatically indexes new files added while server is running
- Callback triggers metadata extraction + embedding generation

### Search Capabilities
**Metadata Search** (SQL-based):
- Field queries: `camera=Canon`, `format=jpg`, `size:>5MB`
- Date queries: `date:2024-01-15`, `date:>2024-01-01`
- Boolean logic: `AND`, `OR`, `NOT`
- Partial matching on filenames

**Semantic Search** (Vector-based):
- Text queries: "sunset at the beach"
- Image similarity (future: upload image to find similar)
- Cross-modal (text finds images)

### Environment Variables
Required in `.env`:
- `ENV` - development/production
- `DEBUG` - boolean
- `APP_NAME` - API title
- `CORS_ORIGINS` - list of allowed origins

Optional:
- `MEDIA_DIR` - custom media directory path

### File Paths
- Always use `Path` objects (from `pathlib`) for cross-platform compatibility
- Relative paths resolved from `settings.BASE_DIR` (project root)
- Full paths used as IDs in vector store to avoid collisions

## Common Development Tasks

### Adding New Metadata Fields
1. Extract in `metadata_extractor.py` (add to extraction logic)
2. SQLite stores JSON - no schema migration needed
3. Update `metadata_search.py` query engine if search needed
4. Add UI display in `ui/src/components/PhotoDetail.tsx`

### Adding New Search Filters
1. Add field extraction if not present (see above)
2. Extend `QueryEngine.parse_query()` in `metadata_search.py`
3. Add UI input in search bar (advanced syntax)

### Changing Vector Store Backend
- Implementations in `experiments/` directory (FAISS, Chroma, LanceDB)
- Current production: `server/lancedb_store.py`
- Interface: `add_batch()`, `search()`, `get_all_ids()`
- Swap by changing import in `server/main.py`

### Performance Tuning
- **Batch embedding generation**: Process 32 images at once (not single-threaded)
- **Vector search limit**: Default k=1000 (adjust in API calls)
- **SQLite indexing**: Indices on `file_path`, `file_hash`, `extracted_at`
- **Lazy loading**: Embedding model loads on first use (not import time)

## Known Issues & Limitations

- **No authentication**: Single-user deployment only
- **No pagination** in some endpoints (timeline, stats)
- **Video search**: Only first frame indexed (no scene detection)
- **Face recognition**: Not implemented (planned)
- **Cloud storage**: Local files only (S3/GCS planned)

## Documentation

**Key docs to reference**:
- `README.md` - Task-by-task implementation history (Tasks 1-3, 10 complete)
- `PROJECT_OVERVIEW.md` - Original vision and principles
- `docs/ROADMAP.md` - Current phase and future features
- `experiments/EXPERIMENT_LOG.md` - Vector store benchmark results
- `docs/antigravity/DEVELOPMENT_GUIDE.md` - Coding standards (historical)

**Documentation Status**: Many docs in `docs/` are historical/outdated. Trust code over old docs.
