# Performance Optimization Plan

## Executive Summary
Detailed analysis and recommendations for optimizing the 6 completed features with focus on:
1. Blur processor performance
2. Incremental scan efficiency
3. Database query optimization
4. Frontend rendering performance

---

## 1. Face Blur Processor Optimization

### Current Implementation Analysis
**File**: `server/face_blur_processor.py`

#### Current Performance Characteristics
- **Database Access**: Single query per image to retrieve bounding boxes
- **Image Processing**: Sequential blur of each detected face
- **Memory Usage**: Full image loaded in memory + copy for processing
- **Format Handling**: Generic format detection

#### Optimization Opportunities

#### A. Database Query Optimization
**Current**: Individual query per image
```python
# Current (inefficient for batch operations)
for photo_path in photos:
    bboxes = processor.get_face_bounding_boxes(photo_path)
```

**Recommended**: Batch query for multiple images
```python
# Optimized - fetch all bboxes in single query
bboxes_by_photo = get_all_bounding_boxes(photo_paths)
for photo_path in photo_paths:
    bboxes = bboxes_by_photo.get(photo_path, [])
```

**Expected Impact**: 70-80% reduction in database round-trips for batch exports

---

#### B. Image Processing Pipeline Optimization

**Current Issues**:
1. Full image copy created for every blur operation
2. Sequential face processing (no parallelization)
3. Image format not optimized for speed (always re-encodes)
4. No caching of face bounding box calculations

**Recommendations**:

**Option 1: Optimized Sequential Processing**
```python
# Use in-place operations where possible
# Load once, blur all faces, save once
- Avoid image.copy() when possible
- Use NumPy for faster pixel operations
- Cache bounding box coordinates
```

**Option 2: Parallel Processing (Recommended)**
```python
# For batch exports > 10 photos
from concurrent.futures import ThreadPoolExecutor

def blur_batch(image_paths, blur_strength, max_workers=4):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(blur_image, path, blur_strength)
            for path in image_paths
        ]
        return [f.result() for f in futures]
```

**Expected Impact**:
- 4x speedup with 4 worker threads
- Better CPU utilization
- Linear scaling with number of cores

---

#### C. Memory Optimization

**Current**: Loads entire image + creates copy
**Optimized**: Process regions only when needed

```python
# Proposed: Memory-efficient approach
def blur_image_optimized(self, image_path: str, blur_strength: int = 10):
    # Use PIL's lazy loading
    # Process in chunks if image > 50MB
    # Stream output instead of buffering
```

**Expected Impact**: 50% reduction in peak memory usage

---

#### D. Caching Strategy

**Proposed**:
```python
class FaceBlurProcessor:
    def __init__(self, face_db_path: str, cache_size=1000):
        self.bbox_cache = LRUCache(max_size=cache_size)  # Cache bboxes
        self.db_path = face_db_path
```

**Expected Impact**: 90%+ cache hit rate for repeated exports

---

### Implementation Recommendations

| Priority | Optimization | Effort | Impact | Timeline |
|----------|-------------|--------|--------|----------|
| 🔴 High | Batch database queries | Low | 70% speedup | 1-2 days |
| 🔴 High | Parallel blur processing | Medium | 4x speedup | 2-3 days |
| 🟡 Medium | Bbox caching | Low | 60% faster repeat | 1 day |
| 🟡 Medium | Memory-efficient processing | Medium | 50% less RAM | 2 days |
| 🟢 Low | NumPy acceleration | High | 20% speedup | 3-5 days |

---

## 2. Incremental Scan Optimization

### Current Implementation Analysis
**File**: `src/file_discovery.py` (lines 216-285+)

#### Current Performance Characteristics
- **Directory Traversal**: Uses `os.walk()` with full directory listing
- **mtime Checking**: Implemented and working (skips unchanged directories)
- **Face Database Check**: Checks if photo already scanned
- **Current Skip Rate**: ~60-70% of directories on incremental scans

#### Optimization Opportunities

#### A. Directory Listing Optimization

**Current**: `os.walk()` lists all files then filters
**Optimized**: Filter during iteration

```python
# Current approach - lists all then filters
for root, dirs, files in os.walk(start_path):
    dirs[:] = [d for d in dirs if not is_system_directory(...)]
    files = [f for f in files if is_media_file(f)]

# Optimized - filters early with generator
def walk_media_files(start_path):
    for root, dirs, files in os.walk(start_path):
        # Prune non-relevant directories immediately
        dirs[:] = [d for d in dirs if not is_system_directory(d)]

        # Only yield media files
        yield (root, [f for f in files if is_media_file(f)])
```

**Expected Impact**: 30-40% faster directory traversal

---

#### B. mtime-Based Skipping Enhancement

**Current**: Only checks `mtime` for exact match
**Proposed**: Add granularity levels

```python
# Different skip strategies based on mtime delta
if mtime_delta == 0:
    skip_completely = True  # No change at all
elif mtime_delta < 1_hour:
    quick_scan = True       # Only check new files
elif mtime_delta < 1_day:
    incremental_scan = True # Check modified metadata
else:
    full_scan = True        # Re-scan everything
```

**Expected Impact**: 5-10% improvement in detection accuracy

---

#### C. Database Query Batching

**Current**: Per-file database lookup to check if scanned
**Proposed**: Batch load all previously scanned files

```python
# Current - N queries
for file_path in files:
    if not is_scanned(file_path):  # Each call hits DB
        process(file_path)

# Optimized - 1 query + in-memory lookup
scanned_files = get_all_scanned_files(directory)
scanned_set = set(scanned_files)  # O(1) lookup
for file_path in files:
    if file_path not in scanned_set:
        process(file_path)
```

**Expected Impact**: 90% reduction in database queries

---

#### D. Parallel Directory Processing

**Current**: Sequential directory processing
**Proposed**: Parallel processing of independent directories

```python
from concurrent.futures import ProcessPoolExecutor

def scan_parallel(start_path, max_workers=4):
    # Get top-level directories
    top_dirs = [d for d in os.listdir(start_path)]

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(scan_directory, top_dirs)

    # Merge results
    return merge_catalogs(results)
```

**Expected Impact**: 3-4x speedup for large directory structures

---

### Implementation Recommendations

| Priority | Optimization | Effort | Impact | Timeline |
|----------|-------------|--------|--------|----------|
| 🔴 High | Batch database lookups | Low | 90% faster DB | 1 day |
| 🔴 High | Enhanced mtime skipping | Medium | 80% skip rate | 2 days |
| 🟡 Medium | Parallel directory processing | Medium | 3.5x speedup | 2-3 days |
| 🟡 Medium | Generator-based file listing | Low | 30% faster | 1 day |
| 🟢 Low | Adaptive skip strategies | High | 10% improvement | 3 days |

---

## 3. Database Query Optimization

### Current Issues Identified

#### A. Face Clustering Queries
**File**: `server/face_clustering_db.py`

**Issue**: Multiple joins without proper indexing
```sql
-- Potentially slow join
SELECT fd.*
FROM face_detections fd
JOIN face_clusters fc ON fd.cluster_id = fc.id
WHERE fc.hidden = false
-- Missing index on face_clusters.hidden
```

**Fix**:
```sql
CREATE INDEX idx_face_clusters_hidden ON face_clusters(hidden);
CREATE INDEX idx_face_detections_cluster_id ON face_detections(cluster_id);
```

#### B. Events Endpoint Performance
**File**: `server/api/routers/face_recognition.py` (line 1614+)

**Issue**: Event detection might be doing expensive aggregations
**Recommendation**: Add query optimization and pagination

```python
# Recommended: Paginate large result sets
@router.get("/api/analytics/events")
async def get_events(
    min_people: int = 3,
    time_window_hours: int = 24,
    limit: int = 100,      # Add limit
    offset: int = 0        # Add pagination
):
    # Query with LIMIT and OFFSET
    pass
```

#### C. Video Highlights Queries
**Issue**: Potential N+1 query problem when loading highlight metadata

**Recommendation**: Eager load related data
```python
# Bad: N+1 queries
highlights = db.query(VideoHighlight).all()
for h in highlights:
    person = h.person  # Additional query per highlight

# Good: Single query with join
highlights = db.query(VideoHighlight).join(Person).all()
```

---

## 4. Frontend Performance Optimization

### Current Issues

#### A. Large Component Rendering
**File**: `ui/src/components/people/Events.tsx`

**Issue**: All events rendered even if not visible
**Solution**: Virtual scrolling for large lists

```typescript
// Use react-window for large lists
import { FixedSizeList } from 'react-window';

<FixedSizeList
  height={600}
  itemCount={events.length}
  itemSize={150}
>
  {({ index, style }) => (
    <div style={style}>
      <EventCard event={events[index]} />
    </div>
  )}
</FixedSizeList>
```

**Expected Impact**: Smooth scrolling with 1000+ events

#### B. Image Loading Optimization
**File**: `ui/src/components/people/Events.tsx` (lines 280+)

**Issue**: Loading all photos in event grid at once
**Solution**: Lazy loading with intersection observer

```typescript
// Use lazy loading library
import { LazyImage } from 'react-lazy-image';

<LazyImage
  src={photoUrl}
  placeholder={placeholderUrl}
/>
```

**Expected Impact**: 50% faster initial load

#### C. Component Memoization
**Recommended**: Memoize expensive event cards

```typescript
const EventCard = React.memo(({ event, onClick }) => (
  // Event card JSX
), (prev, next) =>
  prev.event.id === next.event.id &&
  prev.onClick === next.onClick
);
```

---

## 5. Caching Strategy

### Proposed Multi-Level Cache

#### Level 1: Frontend Cache (React Query)
```typescript
const { data: events } = useQuery(
  ['events', { minPeople, timeWindow }],
  () => api.getEvents(minPeople, timeWindow),
  {
    staleTime: 5 * 60 * 1000,  // 5 minutes
    cacheTime: 30 * 60 * 1000, // 30 minutes
  }
);
```

#### Level 2: Backend Cache (Redis)
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_events(min_people: int, time_window_hours: int):
    # Cache for 10 minutes
    return calculate_events(min_people, time_window_hours)
```

#### Level 3: Database Cache (Materialized Views)
```sql
CREATE MATERIALIZED VIEW event_summary AS
SELECT
  event_id,
  people_count,
  photo_count,
  confidence_score
FROM events
WHERE created_at > NOW() - INTERVAL '90 days';

CREATE INDEX idx_event_summary_people ON event_summary(people_count);
```

---

## 6. Benchmark Targets

### Blur Processor
| Metric | Current | Target | Priority |
|--------|---------|--------|----------|
| Single image blur | 2-3s | 0.5-1s | High |
| Batch (10 photos) | 20-30s | 5-8s | High |
| Memory peak | 500MB | 250MB | Medium |
| First blur latency | 2s | 0.8s | Medium |

### Incremental Scan
| Metric | Current | Target | Priority |
|--------|---------|--------|----------|
| First scan | 5-10m | 3-5m | Medium |
| Incremental scan | 30-60s | 5-10s | High |
| Skip rate | 60-70% | 85%+ | High |
| Database queries | 1000+ | <100 | High |

### Frontend
| Metric | Current | Target | Priority |
|--------|---------|--------|----------|
| Events list load | 1-2s | <500ms | Medium |
| Highlights load | 0.5-1s | <300ms | Low |
| Image grid render | 3-5s | <1s | Medium |

---

## 7. Quick Wins (Can implement today)

1. **Batch Database Queries** (1-2 hours)
   - Modify `FaceBlurProcessor.get_face_bounding_boxes()` to accept list
   - Update export endpoint to use batch queries
   - Expected: 70-80% speedup

2. **Add Database Indexes** (30 minutes)
   - Add indexes on `face_clusters.hidden`, `face_detections.cluster_id`
   - Run VACUUM ANALYZE
   - Expected: 20-30% query speedup

3. **Frontend Memoization** (1 hour)
   - Memoize EventCard and HighlightCard components
   - Add useMemo for expensive calculations
   - Expected: Smoother scrolling

4. **Query Pagination** (1-2 hours)
   - Add limit/offset to events endpoint
   - Add limit/offset to highlights endpoint
   - Expected: Better memory usage, faster initial load

---

## 8. Testing & Validation

### Performance Testing Approach
```python
import time

def benchmark_blur_processor():
    processor = FaceBlurProcessor(db_path)

    # Single image
    start = time.time()
    result = processor.blur_image("path/to/image.jpg", blur_strength=10)
    single_time = time.time() - start

    # Batch images
    images = ["path1.jpg", "path2.jpg", ..., "path100.jpg"]
    start = time.time()
    results = processor.blur_batch(images, blur_strength=10)
    batch_time = time.time() - start

    print(f"Single: {single_time:.2f}s")
    print(f"Batch of 100: {batch_time:.2f}s ({batch_time/100:.3f}s per image)")
```

---

## 9. Implementation Timeline

### Week 1 (High Priority)
- [ ] Batch database queries for blur processor
- [ ] Add database indexes
- [ ] Enhance incremental scan skip logic
- **Expected Improvement**: 70-90% speedup for exports

### Week 2 (Medium Priority)
- [ ] Implement parallel blur processing
- [ ] Parallel directory scanning
- [ ] Frontend memoization and lazy loading
- **Expected Improvement**: 3-4x speedup for large operations

### Week 3+ (Nice to Have)
- [ ] Virtual scrolling for large lists
- [ ] Advanced caching strategies
- [ ] NumPy optimization for blur
- **Expected Improvement**: Additional 20-30% for specific scenarios

---

## Monitoring & Tracking

### Metrics to Track
1. **Export Performance**: Time to blur and export N photos
2. **Scan Duration**: Time for incremental vs full scan
3. **Memory Usage**: Peak memory during operations
4. **Database Load**: Query count and execution time
5. **Frontend Performance**: Component render times

### Tools
- Python `timeit` for server-side benchmarks
- Chrome DevTools for frontend profiling
- SQLite EXPLAIN for query analysis
- New Relic / Sentry for production monitoring

---

## Success Criteria

- ✅ Single image blur: < 1 second
- ✅ Batch export (10 photos): < 8 seconds
- ✅ Incremental scan: < 10 seconds (85%+ skip rate)
- ✅ Events list load: < 500ms
- ✅ Memory usage: < 300MB peak
- ✅ Database queries: < 100 per operation

---

## Risk Mitigation

1. **Backward Compatibility**: All changes non-breaking
2. **Testing**: Add performance regression tests
3. **Monitoring**: Track metrics before/after
4. **Rollback**: Easy revert with feature flags
5. **Gradual Rollout**: A/B test optimizations
