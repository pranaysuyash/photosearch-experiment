# Handoff Instructions for Gemini

**Owner:** Claude (Anthropic)
**Date:** 2025-12-07
**Purpose:** Clear instructions for Gemini to implement vector store experiments.

---

## 🎯 Mission

Implement and benchmark ALL vector stores listed below. Document findings in `experiments/EXPERIMENT_LOG.md`.

---

## 📋 Task Order (Vector Stores First)

### Priority 1: Embedded (No Server Required)
1. **10.4 FAISS** - `experiments/vector_store_faiss.py`
2. **10.5 ChromaDB** - `experiments/vector_store_chroma.py`
3. **10.6 LanceDB** - `experiments/vector_store_lance.py`

### Priority 2: Server-Based (Docker)
4. **10.7 Qdrant** - `experiments/vector_store_qdrant.py`
5. **10.8 Weaviate** - `experiments/vector_store_weaviate.py`
6. **10.9 Milvus** - `experiments/vector_store_milvus.py`

### Priority 3: Cloud (API Key Required)
7. **10.10 Pinecone** - `experiments/vector_store_pinecone.py`

---

## 📦 Benchmark Dataset

Download a small benchmark dataset for fair comparison. Suggestions:

**Option A: COCO Subset (~1000 images)**
```bash
# Download COCO validation subset
pip install fiftyone
python -c "import fiftyone.zoo as foz; foz.load_zoo_dataset('coco-2017', split='validation', max_samples=1000)"
```

**Option B: Unsplash Lite (~1000 images)**
```bash
# Lightweight, high-quality photos
wget https://unsplash.com/data/lite/latest -O unsplash_lite.zip
unzip unsplash_lite.zip -d data/benchmark
```

**Option C: Generate Synthetic Vectors (Pure Speed Test)**
```python
import numpy as np
vectors = np.random.rand(10000, 512).astype('float32')
```

---

## 📝 Experiment Template

Each experiment file MUST follow this structure:

```python
"""
Experiment: [Vector Store Name]
Task: 10.[X]
Date: YYYY-MM-DD
Purpose: Benchmark [Store] against Numpy baseline

Dependencies:
    pip install [package]

Findings:
- [Fill after testing]

Recommendation:
- [Use/Don't use + why]
"""

import time
import numpy as np
from typing import List, Dict, Any

class VectorStore[Name]:
    """
    [Store] implementation with same interface as baseline.
    """

    def __init__(self):
        """Initialize the store."""
        pass

    def add(self, id: str, embedding: List[float], metadata: Dict[str, Any] = None):
        """Add a vector to the store."""
        pass

    def search(self, query_embedding: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """Search for similar vectors. Returns list of {id, score, metadata}."""
        pass

    def save(self, path: str):
        """Persist to disk."""
        pass

    def load(self, path: str):
        """Load from disk."""
        pass


def benchmark():
    """Run standard benchmark."""
    store = VectorStore[Name]()

    N_VECTORS = [100, 1000, 10000]
    DIMENSION = 512
    QUERIES = 10

    for n in N_VECTORS:
        vectors = np.random.rand(n, DIMENSION).astype('float32')

        # Ingest
        start = time.time()
        for i, vec in enumerate(vectors):
            store.add(f"id_{i}", vec.tolist(), {"index": i})
        ingest_time = time.time() - start

        # Search
        query = np.random.rand(DIMENSION).astype('float32')
        start = time.time()
        for _ in range(QUERIES):
            store.search(query.tolist(), limit=5)
        search_time = (time.time() - start) / QUERIES * 1000  # ms

        print(f"N={n}: Ingest={ingest_time:.2f}s, Search={search_time:.2f}ms")


if __name__ == "__main__":
    benchmark()
```

---

## 📊 Metrics to Record

For each vector store, document:

| Metric | How to Measure |
|:---|:---|
| **Install Size** | `pip show [package]` |
| **Ingest Speed** | Time to add N vectors |
| **Search Speed** | Avg query time (ms) |
| **Memory Usage** | `psutil.Process().memory_info().rss` |
| **Disk Size** | Size of persisted file |
| **API Complexity** | Subjective 1-5 rating |
| **Dependencies** | List of required packages |

---

## ⚠️ Notes

1. **Same Interface**: All stores should implement `add()`, `search()`, `save()`, `load()` with the same signatures.
2. **Document Issues**: If something doesn't work, document WHY in the experiment file.
3. **Update EXPERIMENT_LOG.md**: After each experiment, update the log with findings.
4. **Ask Claude**: If stuck or need architectural guidance, ask Claude (user will switch).

---

## 🤝 When to Escalate to Claude

- Architectural decisions (e.g., "Should we use X or Y?")
- Complex bugs that require code review
- Evaluating tradeoffs between approaches
- Before marking any experiment as "Winner"

---

**Good luck, Gemini! Looking forward to the results.**

*— Claude (Anthropic)*
