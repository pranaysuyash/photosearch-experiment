# Technical Implementation Guide - Living Museum Interface

## Architecture Overview

### System Components
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React UI      │    │   FastAPI       │    │   AI Models     │
│   (Frontend)    │◄──►│   (Backend)     │◄──►│   (Local)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Browser       │    │   SQLite        │    │   LanceDB       │
│   (Rendering)   │    │   (Metadata)    │    │   (Vectors)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Data Flow
1. **File Discovery** → `src/file_discovery.py`
2. **Metadata Extraction** → `src/metadata_extractor.py`
3. **Vector Generation** → `server/embedding_generator.py`
4. **Storage** → SQLite (metadata) + LanceDB (vectors)
5. **API Layer** → `server/main.py`
6. **Frontend** → React components

---

## Search System Implementation

### 1. Metadata Search Engine

#### Backend Implementation (`server/main.py`)
```python
@app.get("/search")
async def search_photos(
    query: str = "",
    mode: str = "metadata",
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "date_desc",
    type_filter: str = "all"
):
    if mode == "metadata":
        # Direct SQL query through QueryEngine
        if not query.strip():
            # Return all files for empty query
            cursor = photo_search_engine.db.conn.cursor()
            cursor.execute("SELECT file_path, metadata_json FROM metadata")
            results = cursor.fetchall()
        else:
            # Use QueryEngine for structured queries
            results = photo_search_engine.query_engine.search(query)

        # Format and filter results
        formatted_results = format_metadata_results(results)
        filtered_results = apply_type_filter(formatted_results, type_filter)
        sorted_results = apply_sort(filtered_results, sort_by)

        return paginate_results(sorted_results, offset, limit)
```

#### Query Engine (`src/metadata_search.py`)
```python
class QueryEngine:
    def __init__(self, db: MetadataDatabase):
        self.db = db

    def search(self, query: str) -> List[Dict[str, Any]]:
        # Parse SQL-like query into database operations
        parsed_query = self.parse_query(query)
        sql_query = self.build_sql_query(parsed_query)

        cursor = self.db.conn.cursor()
        cursor.execute(sql_query)
        return cursor.fetchall()

    def parse_query(self, query: str) -> Dict:
        # Convert user query to SQL components
        # Handles: field.subfield = "value", AND/OR logic, comparisons
        pass
```

### 2. Semantic Search Engine

#### Embedding Generation (`server/embedding_generator.py`)
```python
class EmbeddingGenerator:
    def __init__(self):
        # Load CLIP model for text-to-image embeddings
        self.model = SentenceTransformer('clip-ViT-B-32')

    def generate_text_embedding(self, text: str) -> List[float]:
        # Generate embedding for search query
        embedding = self.model.encode([text])
        return embedding[0].tolist()

    def generate_image_embedding(self, image_path: str) -> List[float]:
        # Generate embedding for image content
        image = load_image(image_path)
        embedding = self.model.encode([image])
        return embedding[0].tolist()
```

#### Vector Store (`server/lancedb_store.py`)
```python
class LanceDBStore:
    def __init__(self):
        self.db = lancedb.connect("data/vector_store")
        self.table = None

    def search(self, query_embedding: List[float], limit: int = 20) -> List[Dict]:
        # Perform vector similarity search
        results = self.table.search(query_embedding).limit(limit).to_list()

        # Format results with similarity scores
        formatted_results = []
        for result in results:
            formatted_results.append({
                'path': result['path'],
                'score': float(result['_distance']),
                'metadata': result.get('metadata', {})
            })

        return formatted_results
```

### 3. Hybrid Search Implementation

#### Scoring Algorithm (`server/main.py`)
```python
async def hybrid_search(query: str, limit: int, offset: int):
    # A. Get metadata results
    metadata_results = photo_search_engine.query_engine.search(query)

    # B. Get semantic results
    semantic_response = await search_semantic(query, limit + offset, 0)
    semantic_results = semantic_response['results']

    # C. Normalize semantic scores (0-1 range)
    if semantic_results:
        max_score = max(r['score'] for r in semantic_results)
        min_score = min(r['score'] for r in semantic_results)
        score_range = max_score - min_score if max_score != min_score else 1.0

        for r in semantic_results:
            r['normalized_score'] = (r['score'] - min_score) / score_range

    # D. Merge with weighted scoring
    METADATA_WEIGHT = 0.6  # Precision focus
    SEMANTIC_WEIGHT = 0.4  # Content relevance

    seen_paths = set()
    hybrid_results = []

    # Process metadata results first (higher weight)
    for r in metadata_results:
        path = r.get('file_path', r.get('path'))
        seen_paths.add(path)

        # Find matching semantic result
        semantic_match = next((s for s in semantic_results if s['path'] == path), None)

        if semantic_match:
            # Both metadata and semantic match
            combined_score = (METADATA_WEIGHT * 1.0) + (SEMANTIC_WEIGHT * semantic_match['normalized_score'])
        else:
            # Only metadata match
            combined_score = METADATA_WEIGHT * 0.8

        hybrid_results.append({
            "path": path,
            "filename": os.path.basename(path),
            "score": round(combined_score, 3),
            "metadata": r.get('metadata', {}),
            "source": "both" if semantic_match else "metadata"
        })

    # Add semantic-only results
    for r in semantic_results:
        if r['path'] not in seen_paths:
            hybrid_results.append({
                "path": r['path'],
                "filename": r['filename'],
                "score": round(SEMANTIC_WEIGHT * r['normalized_score'], 3),
                "metadata": r.get('metadata', {}),
                "source": "semantic"
            })

    # Sort by combined score (descending)
    hybrid_results.sort(key=lambda x: x['score'], reverse=True)

    return hybrid_results
```

---

## Frontend Implementation

### 1. Search Context Management

#### PhotoSearchContext (`ui/src/contexts/PhotoSearchContext.tsx`)
```typescript
interface PhotoSearchContextType {
  photos: Photo[];
  loading: boolean;
  error: Error | null;
  hasMore: boolean;
  searchQuery: string;
  searchMode: SearchMode;
  sortBy: string;
  typeFilter: string;
  timelineData: any[];
  timelineLoading: boolean;
  setSearchQuery: (query: string) => void;
  setSearchMode: (mode: SearchMode) => void;
  setSortBy: (sort: string) => void;
  setTypeFilter: (filter: string) => void;
  loadMore: () => void;
  search: (query: string) => void;
}

export function PhotoSearchProvider({ children }: { children: React.ReactNode }) {
  // State management for search functionality
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(false);

  // Prevent concurrent requests and manage state
  const offsetRef = useRef(0);
  const loadingRef = useRef(false);
  const searchAbortControllerRef = useRef<AbortController | null>(null);

  const doSearch = useCallback(async (query: string, isLoadMore: boolean = false) => {
    if (loadingRef.current) return;

    // Cancel any ongoing search
    if (searchAbortControllerRef.current) {
      searchAbortControllerRef.current.abort();
    }
    searchAbortControllerRef.current = new AbortController();

    loadingRef.current = true;
    setLoading(true);

    try {
      const res = await api.search(
        query,
        searchMode,
        LIMIT,
        isLoadMore ? offsetRef.current : 0,
        sortBy,
        typeFilter,
        searchAbortControllerRef.current?.signal
      );

      // Handle results based on load type
      if (!isLoadMore) {
        setPhotos(res.results || []);
        offsetRef.current = res.results?.length || 0;
      } else {
        setPhotos(prev => [...prev, ...(res.results || [])]);
        offsetRef.current += res.results?.length || 0;
      }

    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') return;
      setError(err instanceof Error ? err : new Error("Search failed"));
    } finally {
      loadingRef.current = false;
      setLoading(false);
    }
  }, [searchMode, sortBy, typeFilter]);

  // ... rest of context implementation
}
```

### 2. Timeline Implementation

#### SonicTimeline Component (`ui/src/components/SonicTimeline.tsx`)
```typescript
export function SonicTimeline({ onDateClick }: SonicTimelineProps) {
  const { timelineData, timelineLoading } = usePhotoSearchContext();
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [isMinimized, setIsMinimized] = useState(false);

  const maxCount = Math.max(...timelineData.map(d => d.count));

  return (
    <motion.div className="fixed bottom-0 left-0 right-0 bg-gradient-to-t from-slate-900/95 via-slate-900/80 to-transparent backdrop-blur-xl border-t border-white/5 z-40">
      {/* Timeline bars */}
      <div className="flex items-end gap-[3px] overflow-x-auto pb-3 px-6">
        {timelineData.map((item, i) => {
          const heightPercent = (item.count / maxCount) * 100;
          const isHovered = hoveredIndex === i;

          return (
            <motion.div
              key={item.date}
              className={`w-3 min-w-[12px] rounded-t-md cursor-pointer transition-all duration-200 relative ${
                isHovered
                  ? 'bg-gradient-to-t from-blue-400 via-purple-400 to-pink-400 scale-110'
                  : 'bg-gradient-to-t from-white/20 to-white/5 hover:from-white/40'
              }`}
              style={{ height: `${Math.max(heightPercent, 8)}%` }}
              onMouseEnter={() => setHoveredIndex(i)}
              onMouseLeave={() => setHoveredIndex(null)}
              onClick={() => onDateClick?.(item.date)}
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
            >
              {/* Tooltip on hover */}
              {isHovered && (
                <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 bg-white/10 backdrop-blur-xl text-white text-[11px] px-3 py-1.5 rounded-lg shadow-xl border border-white/10 whitespace-nowrap z-[60]">
                  <div className="font-semibold">{formatDate(item.date)}</div>
                  <div className="text-white/60">{item.count} photos</div>
                  <div className="text-blue-300 text-[10px] mt-0.5">Click to filter</div>
                </div>
              )}
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}
```

### 3. UX Features Implementation

#### Scroll to Top Button (`ui/src/App.tsx`)
```typescript
function AppContent() {
  const [showScrollTop, setShowScrollTop] = useState(false);

  // Scroll detection
  useEffect(() => {
    const handleScroll = () => {
      setShowScrollTop(window.scrollY > 500);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToTop = useCallback(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  return (
    <div>
      {/* Main content */}

      {/* Scroll to top button */}
      <AnimatePresence>
        {showScrollTop && (
          <motion.button
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            onClick={scrollToTop}
            className="fixed bottom-32 right-6 z-50 p-3 bg-primary text-primary-foreground rounded-full shadow-lg"
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
          >
            <ArrowUp size={20} />
          </motion.button>
        )}
      </AnimatePresence>
    </div>
  );
}
```

#### Timeline Date Filtering (`ui/src/App.tsx`)
```typescript
const handleTimelineClick = useCallback((date: string) => {
  // Convert YYYY-MM format to natural language search
  const [year, month] = date.split('-');
  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];
  const monthName = monthNames[parseInt(month, 10) - 1];

  // Set search query and switch to metadata mode for precision
  setSearchQuery(`${monthName} ${year}`);
  setSearchMode('metadata');
}, [setSearchQuery, setSearchMode]);
```

---

## Performance Optimizations

### 1. Search Performance

#### Request Deduplication
```typescript
// Prevent duplicate concurrent requests
const searchAbortControllerRef = useRef<AbortController | null>(null);
const lastSearchParamsRef = useRef<string>('');

const doSearch = useCallback(async (query: string, isLoadMore: boolean = false) => {
  // Create search signature to prevent duplicates
  const searchParams = `${query}|${searchMode}|${sortBy}|${typeFilter}`;
  if (!isLoadMore && searchParams === lastSearchParamsRef.current) {
    console.log('Skipping duplicate search');
    return;
  }

  // Cancel ongoing requests
  if (searchAbortControllerRef.current) {
    searchAbortControllerRef.current.abort();
  }
  searchAbortControllerRef.current = new AbortController();

  // Perform search with abort signal
  const response = await api.search(query, mode, limit, offset, sort, filter,
    searchAbortControllerRef.current?.signal);
}, []);
```

#### Connection Pooling
```typescript
// API client with connection reuse
class APIClient {
  private baseURL: string;
  private agent: any;

  constructor() {
    this.baseURL = 'http://127.0.0.1:8000';
    // Reuse connections for better performance
    this.agent = new (require('https').Agent)({
      keepAlive: true,
      maxSockets: 10
    });
  }

  async request(endpoint: string, options: RequestInit = {}) {
    return fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      // Remove problematic headers that browsers reject
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      }
    });
  }
}
```

### 2. UI Performance

#### Virtualization for Large Collections
```typescript
// Use react-window for efficient rendering of large photo grids
import { FixedSizeList as List } from 'react-window';

function PhotoGrid({ photos }: { photos: Photo[] }) {
  const ROW_HEIGHT = 300;
  const PHOTOS_PER_ROW = 4;
  const rowCount = Math.ceil(photos.length / PHOTOS_PER_ROW);

  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => {
    const startIndex = index * PHOTOS_PER_ROW;
    const rowPhotos = photos.slice(startIndex, startIndex + PHOTOS_PER_ROW);

    return (
      <div style={style} className="flex gap-4 p-4">
        {rowPhotos.map(photo => (
          <PhotoCard key={photo.path} photo={photo} />
        ))}
      </div>
    );
  };

  return (
    <AutoSizer>
      {({ height, width }) => (
        <List
          height={height}
          width={width}
          itemCount={rowCount}
          itemSize={ROW_HEIGHT}
          overscanCount={2}
        >
          {Row}
        </List>
      )}
    </AutoSizer>
  );
}
```

#### Lazy Loading and Intersection Observer
```typescript
// Efficient infinite scroll implementation
function useInfiniteScroll(hasMore: boolean, loadMore: () => void) {
  const observerTarget = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loading) {
          loadMore();
        }
      },
      { threshold: 0.1, rootMargin: '100px' } // Pre-load before reaching bottom
    );

    if (observerTarget.current) {
      observer.observe(observerTarget.current);
    }

    return () => observer.disconnect();
  }, [hasMore, loading, loadMore]);

  return observerTarget;
}
```

### 3. Memory Management

#### Image Loading Optimization
```typescript
// Optimized image loading with error handling
function PhotoCard({ photo }: { photo: Photo }) {
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);

  const imageUrl = useMemo(() =>
    `http://127.0.0.1:8000/image/thumbnail?path=${encodeURIComponent(photo.path)}&size=800`,
    [photo.path]
  );

  return (
    <div className="photo-card">
      {!imageLoaded && !imageError && (
        <div className="skeleton-loader" />
      )}
      <img
        src={imageUrl}
        alt={photo.filename}
        loading="lazy"
        onLoad={() => setImageLoaded(true)}
        onError={() => setImageError(true)}
        style={{ display: imageError ? 'none' : 'block' }}
      />
      {imageError && (
        <div className="error-placeholder">Failed to load</div>
      )}
    </div>
  );
}
```

---

## Database Schema

### SQLite Metadata Schema
```sql
CREATE TABLE metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,
    filename TEXT NOT NULL,
    file_size INTEGER,
    created_date TEXT,
    modified_date TEXT,
    metadata_json TEXT, -- JSON blob containing all extracted metadata
    indexed_date TEXT DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1
);

CREATE INDEX idx_file_path ON metadata(file_path);
CREATE INDEX idx_filename ON metadata(filename);
CREATE INDEX idx_created_date ON metadata(created_date);
CREATE INDEX idx_file_size ON metadata(file_size);

-- Full-text search index for filename and path
CREATE VIRTUAL TABLE metadata_fts USING fts5(
    file_path, filename, content='metadata', content_rowid='id'
);
```

### LanceDB Vector Schema
```python
# Vector table schema for LanceDB
vector_schema = pa.schema([
    pa.field("id", pa.string()),
    pa.field("path", pa.string()),
    pa.field("vector", pa.list_(pa.float32(), 512)),  # CLIP embedding dimension
    pa.field("metadata", pa.string()),  # JSON metadata
    pa.field("indexed_date", pa.timestamp('s'))
])
```

---

## API Endpoints

### Search Endpoint
```python
@app.get("/search")
async def search_photos(
    query: str = "",
    mode: str = "metadata",  # metadata, semantic, hybrid
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "date_desc",  # date_desc, date_asc, name, size
    type_filter: str = "all",  # all, photos, videos
    min_score: float = 0.22  # minimum similarity score for semantic search
):
    """
    Universal search endpoint supporting three modes:
    - metadata: SQL-based structured search
    - semantic: AI-powered content search
    - hybrid: Combined metadata + semantic with weighted scoring
    """
```

### Timeline Endpoint
```python
@app.get("/timeline")
async def get_timeline():
    """
    Returns photo distribution by month for timeline visualization.
    Format: [{"date": "2023-06", "count": 45}, ...]
    """
    cursor = photo_search_engine.db.conn.cursor()
    cursor.execute("""
        SELECT
            strftime('%Y-%m', created_date) as month,
            COUNT(*) as count
        FROM metadata
        WHERE created_date IS NOT NULL
        GROUP BY month
        ORDER BY month DESC
    """)

    return [{"date": row[0], "count": row[1]} for row in cursor.fetchall()]
```

### Health Check Endpoint
```python
@app.get("/health")
async def health_check():
    """Simple health check for frontend connectivity testing."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
```

---

## Deployment Configuration

### Development Setup
```bash
# Backend (from server directory)
cd server
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python main.py

# Frontend (from ui directory)
cd ui
npm install
npm run dev

# Access points:
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Documentation: http://localhost:8000/docs
```

### Production Deployment
```bash
# Build frontend
cd ui && npm run build

# Production server with gunicorn
cd server
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Or with uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Environment Configuration
```bash
# .env file configuration
CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]
DEBUG=true
BASE_DIR=/path/to/photosearch_experiment
VECTOR_STORE_PATH=data/vector_store
METADATA_DB_PATH=data/metadata.db
```

This technical implementation provides the foundation for understanding how the Living Museum Interface achieves its powerful search capabilities and smooth user experience while maintaining high performance with large photo collections.
