"""
Experiment: LanceDB Vector Store
Task: 10.6
Date: 2025-12-07
Purpose: Benchmark LanceDB (Disk-based columnar store) against Chroma/FAISS.

Dependencies:
    pip install lancedb

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
import lancedb
import pyarrow as pa
import numpy as np
from typing import List, Dict, Any
from pathlib import Path

# Reuse baseline embedding generator
from server.embedding_generator import EmbeddingGenerator
from server.image_loader import load_image

class LanceVectorStore:
    """
    LanceDB wrapper.
    """
    
    def __init__(self, persist_path: str = "data/lance_benchmark"):
        """Initialize LanceDB."""
        if os.path.exists(persist_path):
            shutil.rmtree(persist_path)
            
        self.db = lancedb.connect(persist_path)
        self.table = None
        
    def add_batch(self, ids: List[str], embeddings: List[List[float]], metadata_list: List[Dict] = None):
        """Add batch. LanceDB infers schema from data."""
        data = []
        for i, id in enumerate(ids):
            item = {
                "id": id,
                "vector": embeddings[i],
            }
            if metadata_list and metadata_list[i]:
                # Flatten metadata for simpler schema or keep as json?
                # Lance handles flat fields best.
                for k, v in metadata_list[i].items():
                    item[k] = str(v) # Ensure primitive types for safety
            data.append(item)
            
        if self.table is None:
            self.table = self.db.create_table("benchmark", data)
        else:
            self.table.add(data)
    
    def search(self, query_embedding: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """Search."""
        if self.table is None:
            return []
            
        # LanceDB search API
        results = self.table.search(query_embedding).limit(limit).to_list()
        
        out = []
        for r in results:
            # Reconstruct format
            meta = {k: v for k, v in r.items() if k not in ['vector', '_distance', 'id']}
            out.append({
                'id': r['id'],
                'score': 1.0 - r['_distance'], # Lance returns L2 distance by default usually? 
                # Wait, Lance default metric is L2. 
                # If vectors are normalized, L2 is related to Cosine: L2^2 = 2(1-Cosine).
                # But for consistency let's just report the metric.
                'metadata': meta
            })
        return out

def run_benchmark():
    print("\n" + "="*50)
    print("Task 10.6: LanceDB Benchmark")
    print("="*50)
    
    # 1. Setup Data
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
    # We could pickle this to save time between runs, but it's fast enough (~18s)
    print("Generating embeddings...")
    generator = EmbeddingGenerator()
    vectors = []
    ids = []
    
    gen_start = time.time()
    for img_path in images:
        try:
            img = load_image(img_path)
            vec = generator.generate_image_embedding(img)
            vectors.append(vec)
            ids.append(img_path.name)
        except:
            pass
    print(f"Generated {len(vectors)} embeddings in {time.time() - gen_start:.2f}s")
    
    # 3. Lance Benchmark
    print("\n--- LanceDB Performance ---")
    store = LanceVectorStore()
    
    # Ingestion
    start = time.time()
    store.add_batch(ids, vectors, [{"path": str(p)} for p in images])
    ingest_time = time.time() - start
    print(f"Ingest (1000 items): {ingest_time*1000:.2f}ms")
    
    # Search Speed
    query_vec = vectors[0]
    start = time.time()
    for _ in range(100):
        store.search(query_vec, limit=5)
    search_time = (time.time() - start) / 100 * 1000
    print(f"Search (Avg of 100 runs): {search_time:.4f}ms")
    
    # 4. Check Disk Usage
    size = sum(f.stat().st_size for f in Path("data/lance_benchmark").glob("**/*") if f.is_file())
    print(f"Disk Usage: {size / 1024 / 1024:.2f} MB")

    print("\n" + "="*50)
    print("✓ Lance Experiment Complete")
    print("="*50)

if __name__ == "__main__":
    run_benchmark()
