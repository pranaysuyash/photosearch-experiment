# Task 10.5: ChromaDB Experiment

## 🎯 Goal
Benchmark ChromaDB (embedded open-source vector DB) for use as the vector store.

## 🧪 Experiment
- **Script**: `experiments/vector_store_chroma.py`
- **Data**: 1000 Real Images (CIFAR-10 resized)
- **Model**: CLIP ViT-B/32 (512 dimensions)

## 📊 Results
| Metric | Result | vs FAISS |
|:---|:---|:---|
| **Ingest (1k)** | 160.03ms | 12x Slower |
| **Search (1k)** | 0.95ms | 10x Slower |

## 💡 Findings
1. **Developer Experience**: Superior. Handles storage, persistence, and metadata in one API.
2. **Performance**: Slower than FAISS/Numpy but sub-millisecond search is perfectly acceptable for UI applications.
3. **Metadata**: Built-in filtering (`where={"date": "..."}`) which is a huge plus over FAISS.

## 📝 Usage
```bash
pip install chromadb
python experiments/vector_store_chroma.py
```
