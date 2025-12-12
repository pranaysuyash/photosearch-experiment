# Project Structure

## Root Directory Organization

```
photosearch_experiment/
├── .env                    # Environment variables (gitignored)
├── .env.example           # Environment template
├── requirements.txt       # Root Python dependencies
├── README.md             # Main project documentation
├── 
├── src/                  # Core Python modules (modular design)
│   ├── file_discovery.py     # Task 1: File system scanning
│   ├── format_analyzer.py    # Task 2: Format analysis
│   ├── metadata_extractor.py # Task 3: Metadata extraction
│   ├── metadata_search.py    # Metadata search engine
│   └── photo_search.py       # Main search orchestrator
│
├── server/               # FastAPI backend
│   ├── main.py              # API endpoints and server setup
│   ├── config.py            # Server configuration
│   ├── requirements.txt     # Server-specific dependencies
│   ├── embedding_generator.py # AI embedding generation
│   ├── image_loader.py      # Image processing utilities
│   ├── lancedb_store.py     # Vector database interface
│   ├── vector_store.py      # Vector storage abstraction
│   ├── watcher.py           # File system monitoring
│   ├── jobs.py              # Background job management
│   ├── pricing.py           # Commercial pricing logic
│   └── tests/               # Backend tests
│
├── ui/                   # React frontend
│   ├── package.json         # Frontend dependencies
│   ├── vite.config.ts       # Vite build configuration
│   ├── tsconfig.json        # TypeScript configuration
│   ├── tailwind.config.js   # Tailwind CSS configuration
│   ├── src/                 # React source code
│   │   ├── App.tsx             # Main application component
│   │   ├── components/         # Reusable UI components
│   │   ├── pages/              # Route components
│   │   └── api.ts              # API client utilities
│   └── dist/                # Built frontend assets
│
├── data/                 # Application data
│   ├── metadata.db          # SQLite metadata database
│   ├── vector_store/        # LanceDB vector storage
│   └── temp/                # Temporary processing files
│
├── media/                # Sample/test media files
│   ├── *.jpg, *.png         # Test images
│   └── *.mp4, *.mov         # Test videos
│
├── experiments/          # Research and benchmarking
│   ├── EXPERIMENT_LOG.md    # Experiment documentation
│   ├── vector_store_*.py    # Vector store benchmarks
│   └── setup_data.py        # Test data generation
│
├── docs/                 # Comprehensive documentation
│   ├── API_SPEC.md          # API documentation
│   ├── PROJECT_OVERVIEW.md  # High-level overview
│   ├── ROADMAP.md           # Development roadmap
│   └── antigravity/         # AI-generated technical docs
│
└── .kiro/                # Kiro IDE configuration
    └── steering/            # AI assistant guidance
        ├── product.md          # Product overview
        ├── tech.md             # Technology stack
        └── structure.md        # This file
```

## Key Architectural Principles

### Modular Design ("One Task = One File")
- Each core functionality is isolated in a single Python file
- Files can be imported and reused independently
- Clear separation of concerns between modules

### Backend-Focused Architecture
- **src/**: Core business logic (file discovery, metadata, search)
- **server/**: Web API layer (FastAPI endpoints, background jobs)
- Clean separation between core logic and web interface

### Frontend Structure
- **Component-based**: Reusable React components with TypeScript
- **Route-based**: Pages organized by application routes
- **Utility-focused**: Shared utilities and API clients

## File Naming Conventions

### Python Files
- **snake_case** for all Python files and modules
- Descriptive names indicating primary function
- Examples: `file_discovery.py`, `metadata_extractor.py`

### React/TypeScript Files
- **PascalCase** for components: `PhotoGrid.tsx`, `SearchBar.tsx`
- **camelCase** for utilities: `api.ts`, `utils.ts`
- **kebab-case** for configuration: `vite.config.ts`

### Data Files
- **snake_case** for databases: `metadata.db`, `photo_catalog.json`
- **kebab-case** for configuration: `package.json`, `requirements.txt`

## Import Patterns

### Python Imports
```python
# Core modules (relative imports within src/)
from src.photo_search import PhotoSearch
from src.metadata_extractor import extract_all_metadata

# Server modules (relative imports within server/)
from server.config import settings
from server.lancedb_store import LanceDBStore

# Cross-module imports (absolute from project root)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

### TypeScript Imports
```typescript
// Absolute imports with @ alias
import { SearchBar } from '@/components/SearchBar'
import { api } from '@/api'

// Relative imports for local files
import './App.css'
```

## Database Organization

### SQLite (Metadata)
- **Location**: `data/metadata.db`
- **Purpose**: File metadata, search indices, application state
- **Schema**: JSON-based flexible metadata storage

### LanceDB (Vectors)
- **Location**: `data/vector_store/`
- **Purpose**: AI embeddings for semantic search
- **Format**: Optimized columnar storage for vector similarity

## Configuration Management

### Environment Variables
- **Development**: `.env` (gitignored)
- **Template**: `.env.example` (committed)
- **Server config**: `server/config.py` (Pydantic settings)

### Build Configuration
- **Frontend**: `ui/vite.config.ts`, `ui/package.json`
- **Backend**: `server/requirements.txt`, `requirements.txt`
- **Styling**: `ui/tailwind.config.js`

## Development Workflow

### Tech Debt and Issue Resolution Policy
**CRITICAL**: Before starting any task, ensure all issues and tech debt are resolved:
- **Check diagnostics** on all relevant files before making changes
- **Resolve ALL issues**: Syntax errors, import issues, dependency conflicts, AND minor warnings
- **No shortcuts**: Minor warnings are not acceptable - complete resolution required
- **Fix version conflicts** and missing dependencies
- **Clean up duplicate entries** in configuration files
- **Maintain code quality** - no broken code or warnings should be left behind
- **Scope limitation**: When working on a specific task, avoid touching non-relevant files UNLESS they have issues that need resolution
- **Issue priority**: Tech debt resolution overrides task scope limitations

### Adding New Features
1. **Pre-flight check**: Run diagnostics and resolve any existing issues
2. **Core logic**: Add to `src/` following one-task-one-file principle
3. **API endpoints**: Extend `server/main.py` with new routes
4. **Frontend**: Add components to `ui/src/components/`
5. **Documentation**: Update relevant docs in `docs/`
6. **Post-flight check**: Verify no new issues were introduced

### Testing Strategy
- **Backend**: Unit tests in `server/tests/`
- **Integration**: API endpoint testing
- **Frontend**: Component testing (when configured)

### Data Flow
1. **File Discovery** → `src/file_discovery.py`
2. **Metadata Extraction** → `src/metadata_extractor.py`
3. **Vector Generation** → `server/embedding_generator.py`
4. **Storage** → SQLite + LanceDB
5. **API** → `server/main.py`
6. **Frontend** → React components