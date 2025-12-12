# Technology Stack

## Backend (Python)
- **Framework**: FastAPI for REST API
- **Language**: Python 3.9+
- **Database**: SQLite for metadata storage
- **Vector Store**: LanceDB for semantic search embeddings
- **AI/ML**: 
  - Sentence Transformers for text/image embeddings
  - CLIP models for semantic search
  - Pillow for image processing
  - FFmpeg for video processing

### Key Python Libraries
```
fastapi              # Web framework
uvicorn             # ASGI server
sentence-transformers # AI embeddings
lancedb             # Vector database
pillow              # Image processing
ffmpeg-python       # Video processing
exifread            # EXIF metadata extraction
python-magic        # File type detection
watchdog            # File system monitoring
tqdm                # Progress bars
```

## Frontend (React + TypeScript)
- **Framework**: React 19 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **3D Graphics**: Three.js with React Three Fiber
- **UI Components**: Radix UI primitives
- **State Management**: React hooks
- **Routing**: React Router DOM

### Key Frontend Libraries
```
react               # UI framework
typescript          # Type safety
vite                # Build tool
tailwindcss         # Styling
@react-three/fiber  # 3D graphics
@react-three/drei   # 3D helpers
framer-motion       # Animations
axios               # HTTP client
react-window        # Virtualization
```

## Development Commands

### Backend Setup
```bash
# Navigate to project root
cd /path/to/photosearch_experiment

# Activate virtual environment
source venv/bin/activate  # Mac/Linux
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Start development server
cd server
python main.py
# or
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup
```bash
# Navigate to UI directory
cd ui

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

### Full Stack Development
```bash
# Terminal 1: Backend
cd server && python main.py

# Terminal 2: Frontend
cd ui && npm run dev

# Access application at:
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

## Testing Commands
```bash
# Backend tests
cd server
python -m pytest tests/

# Frontend tests (if configured)
cd ui
npm test
```

## Production Deployment
```bash
# Build frontend
cd ui && npm run build

# Start production server
cd server
uvicorn main:app --host 0.0.0.0 --port 8000

# Or with gunicorn for production
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## Environment Configuration
- Copy `.env.example` to `.env` and configure:
  - API keys for AI services
  - Database paths
  - CORS origins
  - Media directories

## Code Quality Standards

### Issue Resolution Policy
- **Zero tolerance for tech debt**: All issues must be resolved before proceeding with new features
- **No minor warnings allowed**: Even "minor" warnings must be resolved - no shortcuts or simplifications
- **Complete closure**: Every diagnostic issue, dependency warning, and code smell must be addressed
- **Diagnostic checks**: Always run `getDiagnostics` on files before and after changes
- **Dependency management**: Keep requirements files clean, versioned, and conflict-free
- **Import hygiene**: Ensure all imports are valid and dependencies are installed
- **Error handling**: Implement graceful degradation for optional dependencies

### Quality Assurance Commands
```bash
# Check for Python issues
python -m py_compile src/*.py server/*.py

# Check dependencies
pip check

# Verify imports work
python -c "import sys; sys.path.append('.'); from src.photo_search import PhotoSearch"

# Run diagnostics in IDE
# Use getDiagnostics tool on all modified files
```

## Performance Notes
- **Embedding Model**: ~500MB download on first run
- **Vector Store**: LanceDB chosen for best speed/storage balance
- **File Watching**: Real-time indexing with Watchdog
- **Thumbnails**: Generated on-demand with PIL
- **Caching**: Browser caching for images with long TTL