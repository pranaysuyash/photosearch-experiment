import os
import requests
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor

# Config
TARGET_DIR = "media"
COUNT = 50
CATEGORIES = ["nature", "architecture", "people", "technology", "food"]

def ensure_dir():
    if not os.path.exists(TARGET_DIR):
        os.makedirs(TARGET_DIR)

async def download_image(session, idx, category):
    try:
        # Lorem Picsum or Unsplash Source (using Unsplash Source via redirect often works better for variety)
        # Using picsum for stability: https://picsum.photos/800/800?random={idx}
        url = f"https://picsum.photos/seed/{category}{idx}/800/800"
        
        async with session.get(url) as response:
            if response.status == 200:
                filename = f"{TARGET_DIR}/{category}_{idx}.jpg"
                with open(filename, 'wb') as f:
                    f.write(await response.read())
                print(f"Downloaded {filename}")
            else:
                print(f"Failed {url}")
    except Exception as e:
        print(f"Error {url}: {e}")

async def main():
    ensure_dir()
    print(f"Downloading {COUNT} demo images to {TARGET_DIR}...")
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(COUNT):
            category = CATEGORIES[i % len(CATEGORIES)]
            tasks.append(download_image(session, i, category))
        
        await asyncio.gather(*tasks)
    
    print("Download complete.")

if __name__ == "__main__":
    asyncio.run(main())
