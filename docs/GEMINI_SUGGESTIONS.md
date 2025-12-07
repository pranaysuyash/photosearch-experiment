# Gemini's Suggestions & Self-Reflections
**Owner:** Gemini (Google Deepmind)
**Context:** Tracking self-identified improvements, potential refactors, and future ideas to collaborate with Claude.

---

## 🚀 Status Update: Vector Stores Benchmarked (Tasks 10.4 - 10.6)
**Date:** 2025-12-07

**Tasks Completed:**
1.  **Task 10.4 (FAISS)**: ✅ Done. `experiments/vector_store_faiss.py`.
2.  **Task 10.5 (Chroma)**: ✅ Done. `experiments/vector_store_chroma.py`.
3.  **Task 10.6 (LanceDB)**: ✅ Done. `experiments/vector_store_lance.py`.

**Benchmark Summary (1000 Real Vectors):**
| Store | Ingest | Search | Persistence | Verdict |
|:---|:---|:---|:---|:---|
| **FAISS** | 13ms | 0.09ms | Manual (Pickle) | 🏎️ Pure Speed |
| **Chroma** | 160ms | 0.95ms | Native (SQLite) | 🛠️ Great DX |
| **Lance** | 25ms | 3.82ms | Native (Files) | ⚖️ **Goldilocks** |

---

## ❓ Questions/Handoff for Claude

### 1. The "Docker Question"
Tasks 10.7 (Qdrant), 10.8 (Weaviate), and 10.9 (Milvus) require Docker.
**Argument**: For a **Local Desktop App** (packaged with Tauri/Electron), asking users to install Docker is a huge barrier.
**Proposal**: **Skip server-based experiments.** Declare a winner from the Embedded Trio (Lance/Chroma/FAISS) and move to Task 11 (Integration).

### 2. The Recommendation
I recommend **LanceDB** or **ChromaDB**.
*   **LanceDB**: If we prioritize disk efficiency and raw ingest speed (fast scanning of photos).
*   **ChromaDB**: If we prioritize rich metadata filtering out-of-the-box (e.g. "Find photos from 2023"). FAISS requires us to build that logic ourselves.

### 3. Next Steps
*   Awaiting your decision on the Vector Store choice.
*   Should I proceed to **Task 10.14 (Video Frames)** or start **Task 11 (Production Integration)** with the winner?

---

## 🏗️ Architecture for Task 9 (3D Museum)
*   **Library**: `react-three-fiber` + `drei`
*   **Performance**: Will likely need `InstancedMesh` for rendering hundreds of photos in 3D.
*   **Transition**: How do we go from 2D Story Mode to 3D? A "Enter Museum" button in the Hero Carousel?

---

## 🤝 Collaboration Log
*   **2025-12-07**: Addressed Claude's critical security findings. Path traversal fixed.
*   **2025-12-07**: Completed Task 7 (Spotlight) & Task 8 (Story Mode).
*   **2025-12-07**: Updated docs/tasks/TASK*.md files.
*   **2025-12-07**: Completed Task 10 (Semantic Intelligence Experiments).
*   **2025-12-07**: Accepted Task 10 Expansion (Vector Store Benchmarks).
*   **2025-12-07**: Benchmarked FAISS, Chroma, LanceDB.
