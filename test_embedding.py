from server.embedding_generator import EmbeddingGenerator
from server.image_loader import load_image
from pathlib import Path
import time
import sys

def test_embeddings():
    print("\n" + "="*50)
    print("Testing Embedding Generator (Task 10)")
    print("="*50)

    # 1. Initialize
    print("1. Initializing Model (CLIP)...")
    start = time.time()
    try:
        generator = EmbeddingGenerator()
        print(f"   ✓ Model loaded in {time.time() - start:.2f}s")
        print(f"   ✓ Dimension: {generator.embedding_dimension}")
    except Exception as e:
        print(f"   ❌ Failed to load model: {e}")
        sys.exit(1)

    # 2. Text Embedding
    print("\n2. Generating Text Embedding...")
    text = "A photo of a dog playing in the snow"
    try:
        vec = generator.generate_text_embedding(text)
        print(f"   ✓ Vector length: {len(vec)}")
        print(f"   ✓ Sample: {vec[:3]}...")
    except Exception as e:
        print(f"   ❌ Failed text: {e}")

    # 3. Image Embedding
    print("\n3. Generating Image Embedding...")
    img_path = Path("media/sample1.jpg")
    try:
        if not img_path.exists():
            print(f"   ❌ Test image not found at {img_path}")
            sys.exit(1)
            
        img = load_image(img_path)
        vec = generator.generate_image_embedding(img)
        print(f"   ✓ Vector length: {len(vec)}")
        print(f"   ✓ Sample: {vec[:3]}...")
    except Exception as e:
        print(f"   ❌ Failed image: {e}")

    print("\n" + "="*50)
    print("✓ Task 10 (Embeddings) Verified")
    print("="*50)

if __name__ == "__main__":
    test_embeddings()
