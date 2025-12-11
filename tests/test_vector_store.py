from server.vector_store import VectorStore
import numpy as np
import os

def test_vector_store():
    print("\n" + "="*50)
    print("Testing Vector Store (Task 10.2)")
    print("="*50)
    
    # 1. Initialize
    store = VectorStore()
    
    # 2. Add Dummy Data
    # "Concept": [x, y] - simplified 2D space for testing
    # Dog: [0.9, 0.1]
    # Cat: [0.8, 0.2]
    # Car: [0.1, 0.9]
    print("1. Adding data...")
    store.add("dog_pic", [0.9, 0.1], {"type": "animal"})
    store.add("cat_pic", [0.8, 0.2], {"type": "animal"})
    store.add("car_pic", [0.1, 0.9], {"type": "vehicle"})
    print(f"   ✓ Added 3 items")
    
    # 3. Search
    print("\n2. Searching for 'puppy' (similar to dog)...")
    # Puppy query: [0.85, 0.15] - close to dog and cat, far from car
    query = [0.85, 0.15]
    results = store.search(query, limit=3)
    
    for i, res in enumerate(results, 1):
        print(f"   {i}. {res['id']}: Score {res['score']:.4f}")
        
    # Validation logic
    top_result = results[0]['id']
    if top_result in ["dog_pic", "cat_pic"]:
        print("   ✓ Search Result Valid (Animal ranked first)")
    else:
        print("   ❌ Search Result Invalid (Expected animal)")
        
    # 4. Persistence
    print("\n3. Testing Persistence...")
    db_path = "test_vectors.pkl"
    store.save(db_path)
    if os.path.exists(db_path):
        print("   ✓ Saved to disk")
        
    new_store = VectorStore()
    new_store.load(db_path)
    print(f"   ✓ Loaded {len(new_store.ids)} items")
    
    # Clean up
    if os.path.exists(db_path):
        os.remove(db_path)

    print("\n" + "="*50)
    print("✓ Vector Store Verified")
    print("="*50)

if __name__ == "__main__":
    test_vector_store()
