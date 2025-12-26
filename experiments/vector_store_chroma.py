"""
Experiment: ChromaDB Vector Store
Task: 10.5
Date: 2025-12-07
Purpose: Benchmark ChromaDB against FAISS/Numpy.

Dependencies:
    pip install chromadb

Findings:
- Ingestion Speed: TBD
- Search Speed: TBD
- Persistence: TBD

Recommendation:
- TBD
"""

import time
import os
import shutil
import chromadb
from typing import List, Dict, Any
from pathlib import Path

# Reuse baseline embedding generator
from server.embedding_generator import EmbeddingGenerator
from server.image_loader import load_image


class ChromaVectorStore:
    """
    ChromaDB wrapper.
    """

    def __init__(self, persist_path: str = "data/chroma_benchmark"):
        """Initialize Chroma client."""
        # Reset for benchmark
        if os.path.exists(persist_path):
            shutil.rmtree(persist_path)

        self.client = chromadb.PersistentClient(path=persist_path)
        self.collection = self.client.create_collection(name="benchmark", metadata={"hnsw:space": "cosine"})

    def add_batch(self, ids: List[str], embeddings: List[List[float]], metadata_list: List[Dict] = None):
        """Add batch."""
        if metadata_list is None:
            # Chroma requires non-empty metadata in some versions or proper None handling
            # Let's add dummy metadata to be safe
            metadata_list = [{"item_id": id} for id in ids]

        self.collection.add(ids=ids, embeddings=embeddings, metadatas=metadata_list)

    def search(self, query_embedding: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """Search."""
        results = self.collection.query(query_embeddings=[query_embedding], n_results=limit)

        # Parse results
        out = []
        if results["ids"]:
            ids = results["ids"][0]
            distances = results["distances"][0]
            metadatas = results["metadatas"][0]

            for i in range(len(ids)):
                out.append(
                    {
                        "id": ids[i],
                        "score": 1.0 - distances[i],  # Cosine distance to similarity
                        "metadata": metadatas[i],
                    }
                )
        return out


def run_benchmark():
    print("\n" + "=" * 50)
    print("Task 10.5: ChromaDB Benchmark")
    print("=" * 50)

    # 1. Setup Data Paths
    data_dir = Path("data/benchmark")
    if not data_dir.exists():
        print("Data not found.")
        return

    images = sorted(list(data_dir.glob("*.png")))
    if not images:
        print("No images found.")
        return

    print(f"Found {len(images)} images.")

    # 2. Generate Embeddings (Pre-computation)
    print("Generating embeddings...")
    generator = EmbeddingGenerator()
    vectors = []
    ids = []

    gen_start = time.time()
    for i, img_path in enumerate(images):
        try:
            img = load_image(img_path)
            vec = generator.generate_image_embedding(img)
            vectors.append(vec)
            ids.append(img_path.name)
        except:
            pass
    print(f"Generated {len(vectors)} embeddings in {time.time() - gen_start:.2f}s")

    # 3. Chroma Benchmark
    print("\n--- ChromaDB Performance ---")
    store = ChromaVectorStore()

    # Ingestion
    start = time.time()
    store.add_batch(ids, vectors, None)
    ingest_time = time.time() - start
    print(f"Ingest (1000 items): {ingest_time*1000:.2f}ms")

    # Search Speed
    query_vec = vectors[0]
    start = time.time()
    for _ in range(100):
        store.search(query_vec, limit=5)
    search_time = (time.time() - start) / 100 * 1000
    print(f"Search (Avg of 100 runs): {search_time:.4f}ms")

    print("\n" + "=" * 50)
    print("✓ Chroma Experiment Complete")
    print("=" * 50)


if __name__ == "__main__":
    run_benchmark()
