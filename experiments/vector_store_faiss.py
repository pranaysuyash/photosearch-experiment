"""
Experiment: FAISS Vector Store
Task: 10.4
Date: 2025-12-07
Purpose: Benchmark FAISS (Facebook AI Similarity Search) against Numpy baseline using real images.

Dependencies:
    pip install faiss-cpu

Findings:
- Ingestion Speed: TBD
- Search Speed: TBD
- Persistence: TBD

Recommendation:
- TBD
"""

import time
import os
import faiss
import numpy as np
import pickle
from typing import List, Dict, Any
from pathlib import Path

# Reuse baseline embedding generator to process real images
from server.embedding_generator import EmbeddingGenerator
from server.image_loader import load_image

class FaissVectorStore:
    """
    FAISS-based vector store implementation.
    Uses IndexFlatIP (Inner Product) for cosine similarity with normalized vectors.
    """
    
    def __init__(self, dimension: int = 512):
        """Initialize FAISS index."""
        self.dimension = dimension
        self.ids: List[str] = []
        self.metadata: List[Dict[str, Any]] = []
        
        # IndexFlatIP is exact search using inner product
        # Equivalent to cosine similarity if vectors are normalized
        self.index = faiss.IndexFlatIP(dimension)
        
    def add(self, id: str, embedding: List[float], metadata: Dict[str, Any] = None):
        """Add a vector to the store."""
        if metadata is None:
            metadata = {}
            
        self.ids.append(id)
        self.metadata.append(metadata)
        
        # Convert to numpy and normalize
        vector = np.array([embedding], dtype=np.float32)
        faiss.normalize_L2(vector)
        
        self.index.add(vector)
        
    def add_batch(self, ids: List[str], embeddings: List[List[float]], metadata_list: List[Dict] = None):
        """Add multiple vectors at once (FAISS is optimized for this)."""
        if metadata_list is None:
            metadata_list = [{} for _ in ids]
            
        self.ids.extend(ids)
        self.metadata.extend(metadata_list)
        
        vectors = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(vectors)
        self.index.add(vectors)
    
    def search(self, query_embedding: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """Search for similar vectors."""
        if self.index.ntotal == 0:
            return []
            
        # Prepare query
        query = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query)
        
        # Search
        scores, indices = self.index.search(query, limit)
        
        results = []
        # indices[0] because we sent 1 query vector
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1: # No result found
                continue
                
            results.append({
                'id': self.ids[idx],
                'score': float(score),
                'metadata': self.metadata[idx]
            })
            
        return results
    
    def save(self, path_prefix: str):
        """
        Persist to disk. FAISS saves index separately from metadata.
        path_prefix.index = faiss index
        path_prefix.pkl = metadata
        """
        faiss.write_index(self.index, f"{path_prefix}.index")
        with open(f"{path_prefix}.pkl", 'wb') as f:
            pickle.dump({
                'ids': self.ids,
                'metadata': self.metadata
            }, f)
        print(f"Saved FAISS index + metadata to {path_prefix}.*")
    
    def load(self, path_prefix: str):
        """Load from disk."""
        if not os.path.exists(f"{path_prefix}.index"):
            print("Index not found.")
            return

        self.index = faiss.read_index(f"{path_prefix}.index")
        with open(f"{path_prefix}.pkl", 'rb') as f:
            data = pickle.load(f)
            self.ids = data['ids']
            self.metadata = data['metadata']
        print(f"Loaded {self.index.ntotal} vectors.")


def run_benchmark():
    print("\n" + "="*50)
    print("Task 10.4: FAISS Benchmark (Real Images)")
    print("="*50)
    
    # 1. Setup Data Paths
    data_dir = Path("data/benchmark")
    if not data_dir.exists():
        print("Benchmark data not found. Run experiments/setup_data.py first.")
        return

    images = sorted(list(data_dir.glob("*.png")))
    if not images:
        print("No images found in data/benchmark.")
        return
        
    print(f"Found {len(images)} images to process.")
    
    # 2. Generate Embeddings (Pre-computation step)
    # We time this separately because we care about STORE performance, 
    # but we need vectors first.
    print("Loading CLIP model for embedding generation...")
    generator = EmbeddingGenerator()
    
    print("Generating embeddings (this may take time)...")
    vectors = []
    ids = []
    
    gen_start = time.time()
    for i, img_path in enumerate(images):
        try:
            img = load_image(img_path)
            vec = generator.generate_image_embedding(img)
            vectors.append(vec)
            ids.append(img_path.name)
            if i % 100 == 0:
                print(f"  Processed {i}/{len(images)}...")
        except Exception as e:
            print(f"  Failed {img_path.name}: {e}")
            
    print(f"Generated {len(vectors)} embeddings in {time.time() - gen_start:.2f}s")
    
    # 3. FAISS Benchmark
    print("\n--- FAISS Performance ---")
    store = FaissVectorStore()
    
    # Ingestion
    start = time.time()
    store.add_batch(ids, vectors, None) # Use batch add for fairness
    ingest_time = time.time() - start
    print(f"Ingest (1000 items): {ingest_time*1000:.2f}ms")
    
    # Search Speed
    query_vec = vectors[0] # Search for the first image
    start = time.time()
    for _ in range(100):
        store.search(query_vec, limit=5)
    search_time = (time.time() - start) / 100 * 1000
    print(f"Search (Avg of 100 runs): {search_time:.4f}ms")
    
    # 4. Persistence
    print("\n--- Persistence ---")
    store.save("data/faiss_benchmark")
    
    new_store = FaissVectorStore()
    start = time.time()
    new_store.load("data/faiss_benchmark")
    load_time = time.time() - start
    print(f"Load Time: {load_time*1000:.2f}ms")
    print(f"Loaded {new_store.index.ntotal} items.")
    
    # Cleanup
    for ext in ['.index', '.pkl']:
        if os.path.exists(f"data/faiss_benchmark{ext}"):
            os.remove(f"data/faiss_benchmark{ext}")

    print("\n" + "="*50)
    print("✓ FAISS Experiment Complete")
    print("="*50)

if __name__ == "__main__":
    run_benchmark()
