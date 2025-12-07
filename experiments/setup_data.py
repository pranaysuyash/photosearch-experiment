import os
import torch
import torchvision
import torchvision.transforms as transforms
from PIL import Image
from pathlib import Path

def setup_benchmark_data(count=1000, output_dir="data/benchmark"):
    """
    Download first N images from STL10 (96x96 resolution, better than CIFAR)
    to the output directory.
    """
    print(f"Setting up benchmark data ({count} images)...")
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    
    # Check if already exists
    existing = len(list(path.glob("*.png")))
    if existing >= count:
        print(f"✓ Found {existing} images in {output_dir}. Skipping download.")
        return

    print("Downloading STL10 dataset (may take a moment)...")
    try:
        # Download to data/temp
        dataset = torchvision.datasets.STL10(
            root='./data/temp', 
            split='test', 
            download=True,
            transform=None # Keep as PIL Images
        )
        
        print(f"Saving first {count} images to {output_dir}...")
        saved = 0
        for i, (img, label) in enumerate(dataset):
            if saved >= count:
                break
                
            # Save as PNG
            img.save(path / f"benchmark_{i:04d}.png")
            saved += 1
            
        print(f"✓ Successfully saved {saved} images.")
        
        # Cleanup temp if needed (optional, STL10 is ~2GB uncompressed might be heavy? 
        # STL10 binary is ~2.5GB. Maybe too big for just 1000 images?
        # Let's try CIFAR10 if STL10 is huge download.
        # CIFAR10 is ~160MB. Much safer for a quick "experiment".
        
    except Exception as e:
        print(f"Error downloading STL10, falling back to CIFAR10: {e}")
        _download_cifar10(count, path)

def _download_cifar10(count, path):
    path.mkdir(parents=True, exist_ok=True)  # CRITICAL: Ensure dir exists
    print(f"Downloading CIFAR10 dataset to {path}...")
    dataset = torchvision.datasets.CIFAR10(
        root='./data/temp',
        train=False,
        download=True
    )
    
    saved = 0
    for i, (img, label) in enumerate(dataset):
        if saved >= count:
            break
        img = img.resize((224, 224), Image.NEAREST)
        img.save(path / f"benchmark_{i:04d}.png")
        saved += 1
    print(f"✓ Saved {saved} CIFAR10 images (resized to 224x224).")

if __name__ == "__main__":
    # Ensure directory exists and download
    output_path = Path("data/benchmark")
    _download_cifar10(1000, output_path)
