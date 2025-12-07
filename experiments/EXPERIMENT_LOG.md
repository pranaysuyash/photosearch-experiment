# Experiment Log

**Purpose:** Document findings from all experiments in the Task 10 series.

---

## Quick Reference

| Task | Experiment | Winner? | Notes |
|:---|:---|:---|:---|
| 10.1 | CLIP Embeddings | ✅ Baseline | 512-dim, ~500ms model load |
| 10.2 | Numpy Vector Store | ✅ Baseline | Fast for <10k, O(n) search |
| 10.3 | Integration Prototype | ✅ Works | End-to-end proof |
| 10.4 | FAISS Vector Store | ⬜ Pending | - |
| 10.5 | ChromaDB Vector Store | ⬜ Pending | - |
| 10.6 | LanceDB Vector Store | ⬜ Pending | - |
| 10.7 | OpenAI CLIP Embeddings | ⬜ Pending | - |
| 10.8 | SigLIP Embeddings | ⬜ Pending | - |
| 10.9 | Video Frame Extraction | ⬜ Pending | - |
| 10.10 | Multimodal LLM Captions | ⬜ Pending | - |

---

## Task 10.1: CLIP Embeddings (Baseline)

**Date:** 2025-12-07  
**File:** `server/embedding_generator.py`  
**Model:** `clip-ViT-B-32` via sentence-transformers

### Metrics
- Model load time: ~3-4 seconds (first run), ~500ms (cached)
- Embedding generation: ~50ms per image
- Dimension: 512 floats

### Findings
- Works reliably for images and text
- Same vector space allows cross-modal search
- Memory: ~500MB for model

### Verdict
✅ **BASELINE ESTABLISHED** - Use this as reference for other experiments.

---

## Task 10.2: Numpy Vector Store (Baseline)

**Date:** 2025-12-07  
**File:** `server/vector_store.py`  
**Algorithm:** Brute-force cosine similarity via normalized dot product

### Metrics
- Add: O(1) (amortized via vstack)
- Search: O(n) - linear scan
- Memory: n * 512 * 4 bytes = ~2KB per vector

### Findings
- Pre-normalization is a good optimization
- Pickle persistence works but not atomic
- No deduplication logic

### Verdict
✅ **BASELINE ESTABLISHED** - Simple and fast enough for <10k items.

---

## Task 10.3: Integration Prototype

**Date:** 2025-12-07  
**File:** `experiment_semantic_search.py`

### What We Learned
- End-to-end pipeline works: Scan → Embed → Store → Search
- Video files are skipped (expected, image-only indexer)
- Interactive REPL is useful for testing

### Issues Found
- Hardcoded `media/` path
- No error recovery (aborts on first failure)

### Verdict
✅ **PROTOTYPE COMPLETE** - Ready to experiment with alternatives.

---

## Task 10.4: FAISS Vector Store

**Date:** 2025-12-07
**File:** `experiments/vector_store_faiss.py`
**Data:** 1000 Real Images (CIFAR-10, resized to 224x224)

### Metrics
- **Ingest**: 13.84ms for 1000 vectors (~0.01ms/vector)
- **Search**: 0.0935ms (~93 microseconds)
- **Load Time**: 4.17ms
- **Dependencies**: `faiss-cpu`, `numpy`

### Findings
- **Speed**: Extremely fast. 0.1ms search time is negligible.
- **Complexity**: Requires managing index + metadata separately (unlike dictionaries).
- **Install**: `faiss-cpu` worked smoothly on Mac.

### Verdict
✅ **STRONG CONTENDER** - Much faster than likely needed, but adds complexity.
- **Pros**: Speed, Scalability (>1M).
- **Cons**: No metadata filtering built-in (must filter post-search or use IDMapping), separate persistence.

---

## Task 10.5: ChromaDB Vector Store

**Date:** 2025-12-07
**File:** `experiments/vector_store_chroma.py`
**Data:** 1000 Real Images

### Metrics
- **Ingest**: 160.03ms for 1000 vectors (~0.16ms/vector)
- **Search**: 0.9479ms (~1ms)
- **Install Size**: Heavier (installs onnxruntime, tokenizers etc.)
- **Dependencies**: `chromadb`

### Findings
- **Speed**: ~10x slower than FAISS but still sub-millisecond search for 1k items.
- **Features**: Built-in persistence (SQLite + files) and metadata storage.
- **DX**: Easiest API. `collection.add()` and `collection.query()`.

### Verdict
✅ **BALANCED CHOICE** - Best developer experience. Slower than FAISS but feature-rich.
- **Pros**: Easy setup, metadata filtering included.
- **Cons**: Heavier dependencies. Slower ingest.

---

## Task 10.6: LanceDB Vector Store

**Date:** 2025-12-07
**File:** `experiments/vector_store_lance.py`
**Data:** 1000 Real Images

### Metrics
- **Ingest**: 25.83ms (Fast!)
- **Search**: 3.82ms (~4ms)
- **Disk Usage**: 2.02 MB (Efficient)
- **Dependencies**: `lancedb`, `pyarrow`

### Findings
- **Speed**: Ingest is nearly as fast as FAISS (25ms vs 13ms) and much faster than Chroma (160ms).
- **Architecture**: Native disk-based (columnar). fast append. 
- **Tradeoff**: Search is slightly slower (4ms) than in-memory FAISS (0.1ms), but negligible for UI.

### Verdict
✅ **TOP SYSTEM CANDIDATE** - High performance, on-disk (no RAM limit), simple API.
- **Pros**: Fast ingest, persistent by default, lightweight.
- **Cons**: Newer ecosystem than FAISS/Chroma.

---

## Benchmark Protocol

For fair comparison, each vector store experiment should:

1. **Setup:** Install dependencies, initialize store
2. **Ingest:** Add N vectors (100, 1000, 10000)
3. **Search:** Query 10 times, measure avg latency
4. **Persist:** Save to disk, measure time
5. **Reload:** Load from disk, measure time
6. **Memory:** Report RAM usage

### Test Code Template
```python
import time
import numpy as np

N_VECTORS = [100, 1000, 10000]
DIMENSION = 512
QUERIES = 10

for n in N_VECTORS:
    # Generate random vectors
    vectors = np.random.rand(n, DIMENSION).astype('float32')
    
    # Time ingestion
    start = time.time()
    for i, vec in enumerate(vectors):
        store.add(f"id_{i}", vec.tolist(), {})
    ingest_time = time.time() - start
    
    # Time search
    query = np.random.rand(DIMENSION).astype('float32')
    start = time.time()
    for _ in range(QUERIES):
        store.search(query.tolist(), limit=5)
    search_time = (time.time() - start) / QUERIES
    
    print(f"N={n}: Ingest={ingest_time:.2f}s, Search={search_time*1000:.2f}ms")
```

---

**Last Updated:** 2025-12-07
