# Task 10.6: LanceDB Experiment

## 🎯 Goal
Benchmark LanceDB (Serverless, disk-based vector DB) for use as the vector store.

## 🧪 Experiment
- **Script**: `experiments/vector_store_lance.py`
- **Data**: 1000 Real Images (CIFAR-10 resized)
- **Model**: CLIP ViT-B/32 (512 dimensions)

## 📊 Results
| Metric | Result | vs FAISS | vs Chroma |
|:---|:---|:---|:---|
| **Ingest (1k)** | 25.83ms | ~2x Slower | **6x Faster** |
| **Search (1k)** | 3.82ms | 40x Slower | 4x Slower |
| **Persistence**| Native | Manual | Native |

## 💡 Findings
1. **Ingest Speed**: Incredible. Writing to disk (Lance format) is almost as fast as FAISS writing to RAM.
2. **Search Speed**: 4ms is "slow" compared to 0.1ms, but for a user-facing app, anything under 100ms is instant.
3. **Architecture**: It doesn't need to load the whole index into RAM (unlike FAISS). It relies on disk caching. This suggests it scales better for large libraries without eating RAM.

## 📝 Usage
```bash
pip install lancedb
python experiments/vector_store_lance.py
```
