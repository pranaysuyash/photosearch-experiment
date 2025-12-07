# Task 10.4: FAISS Experiment

## 🎯 Goal
Benchmark Facebook AI Similarity Search (FAISS) for use as the vector store in the Photo Search app.

## 🧪 Experiment
- **Script**: `experiments/vector_store_faiss.py`
- **Data**: 1000 Real Images (CIFAR-10 resized)
- **Model**: CLIP ViT-B/32 (512 dimensions)

## 📊 Results
| Metric | Result |
|:---|:---|
| **Ingest (1k)** | 13.84ms |
| **Search (1k)** | 0.09ms |
| **P99 Latency** | <0.2ms |

## 💡 Findings
1. **Speed**: FAISS is the performance king. Even the CPU implementation is vastly faster than needed for our scale.
2. **Complexity**: It is a low-level library. It indexes vectors but does NOT store metadata (filenames, dates). We must maintain a parallel lookup (e.g., `id -> metadata`).
3. **Persistence**: `write_index` saves the vector structure, but we need to pickle the metadata separately.

## 📝 Usage
```bash
pip install faiss-cpu
python experiments/vector_store_faiss.py
```
