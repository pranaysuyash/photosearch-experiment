import os
import time
from pathlib import Path
from typing import List, Optional

from server.embedding_generator import EmbeddingGenerator
from server.image_loader import load_image
from server.vector_store import VectorStore

class SemanticSearchExperiment:
    def __init__(self, media_dir: str = "media"):
        self.media_dir = Path(media_dir)
        self.generator = None
        self.store = VectorStore()
        
    def initialize(self):
        """Load model and prepare components."""
        print("Loading AI Model (CLIP)...")
        start = time.time()
        self.generator = EmbeddingGenerator()
        print(f"Model loaded in {time.time() - start:.2f}s")
        
    def index_images(self):
        """Scan and index images in the media directory."""
        if not self.media_dir.exists():
            print(f"Error: Media directory {self.media_dir} does not exist.")
            return

        print(f"\nScanning {self.media_dir}...")
        files = [f for f in self.media_dir.glob("*") if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp')]
        
        if not files:
            print("No images found to index.")
            return

        print(f"Found {len(files)} images. Indexing...")
        
        for i, file_path in enumerate(files, 1):
            try:
                # 1. Load Image
                image = load_image(file_path)
                
                # 2. Generate Embedding
                embedding = self.generator.generate_image_embedding(image)
                
                # 3. Store
                self.store.add(
                    id=file_path.name,
                    embedding=embedding,
                    metadata={"path": str(file_path)}
                )
                print(f"[{i}/{len(files)}] Indexed {file_path.name}")
                
            except Exception as e:
                print(f"[{i}/{len(files)}] Failed {file_path.name}: {e}")
                
        print(f"\nIndexing Complete. {len(self.store.ids)} images in vector store.")

    def run_interactive_loop(self):
        """Run the search REPL."""
        if not self.store.ids:
            print("Index is empty. Exiting.")
            return

        print("\n" + "="*50)
        print("Semantic Search Experiment")
        print("Type a query (e.g. 'dog in snow') or 'exit' to quit.")
        print("="*50)

        while True:
            query = input("\nQuery: ").strip()
            if query.lower() in ('exit', 'quit', 'q'):
                break
            
            if not query:
                continue

            try:
                # 1. Generate Text Embedding
                query_vec = self.generator.generate_text_embedding(query)
                
                # 2. Search
                results = self.store.search(query_vec, limit=5)
                
                # 3. Display
                print(f"\nTop matches for '{query}':")
                for i, res in enumerate(results, 1):
                    score = res['score']
                    filename = res['id']
                    print(f"  {i}. {filename} (Score: {score:.4f})")
                    
            except Exception as e:
                print(f"Search failed: {e}")

if __name__ == "__main__":
    experiment = SemanticSearchExperiment()
    experiment.initialize()
    experiment.index_images()
    experiment.run_interactive_loop()
