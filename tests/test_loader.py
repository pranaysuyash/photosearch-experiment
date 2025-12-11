from server.image_loader import load_image, process_image, get_image_metadata
from pathlib import Path
import sys

def test_loader():
    # Use the test image created/verified previously
    test_image_path = Path("media/sample1.jpg")
    
    # 1. Test Metadata Extraction
    print(f"\n--- Testing Metadata Extraction ---")
    try:
        meta = get_image_metadata(test_image_path)
        print("Success!")
        for k, v in meta.items():
            print(f"  {k}: {v}")
    except Exception as e:
        print(f"Failed: {e}")
        sys.exit(1)

    # 2. Test Loading
    print(f"\n--- Testing Image Loading ---")
    try:
        img = load_image(test_image_path)
        print(f"Success! Loaded {img.format} image: {img.size} mode={img.mode}")
    except Exception as e:
        print(f"Failed: {e}")
        sys.exit(1)

    # 3. Test Processing (Resize)
    print(f"\n--- Testing Image Processing (Resize to 100px) ---")
    try:
        processed = process_image(img, target_size=100)
        print(f"Success! New size: {processed.size}")
        if max(processed.size) > 100:
            print("Error: Image was not resized correctly.")
            sys.exit(1)
    except Exception as e:
        print(f"Failed: {e}")
        sys.exit(1)
        
    # 4. Test Error Handling
    print(f"\n--- Testing Error Handling (Missing File) ---")
    try:
        load_image("non_existent_image.jpg")
        print("Error: Should have failed for missing file.")
    except FileNotFoundError:
        print("Success! Caught FileNotFoundError.")
    except Exception as e:
        print(f"Unexpected error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_loader()
