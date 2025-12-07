import sys
import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Add parent directory to path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from photo_search import PhotoSearch

from server.config import settings

app = FastAPI(title=settings.APP_NAME, description="Backend for the Living Museum Interface", debug=settings.DEBUG)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS, 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Core Logic
# We prefer a persistent instance
photo_search_engine = PhotoSearch()

# Initialize Semantic Search Components
from server.lancedb_store import LanceDBStore
from server.embedding_generator import EmbeddingGenerator
from server.image_loader import load_image

# Lazily loaded or initialized here
# Note: EmbeddingGenerator loads a model (~500MB), so it might take a moment on first request or startup
vector_store = LanceDBStore()
embedding_generator = None # Load lazily or on startup

@app.on_event("startup")
async def startup_event():
    global embedding_generator
    print("Initializing Embedding Model...")
    # Initialize in background or here? For now, simple synchronous load.
    try:
        embedding_generator = EmbeddingGenerator()
        print("Embedding Model Loaded.")
    except Exception as e:
        print(f"Failed to load embedding model: {e}")

class ScanRequest(BaseModel):
    path: str

class SearchRequest(BaseModel):
    query: str
    limit: int = 50

@app.get("/")
async def root():
    return {"status": "ok", "message": "PhotoSearch API is running"}

def process_semantic_indexing(files_to_index: List[str]):
    """
    Helper to generate embeddings for a list of file paths.
    """
    global embedding_generator
    if not embedding_generator:
        embedding_generator = EmbeddingGenerator()
        
    print(f"Indexing {len(files_to_index)} files for semantic search...")
    
    # 1. Deduplication: Filter out files that are already indexed
    # Using Full Path as ID to avoid collisions
    try:
        existing_ids = vector_store.get_all_ids()
        files_to_process = [f for f in files_to_index if f not in existing_ids]
    except Exception as e:
        print(f"Error checking existing IDs: {e}")
        files_to_process = files_to_index

    if not files_to_process:
        print("All files already indexed. Skipping.")
        return

    print(f"Processing {len(files_to_process)} new files (skipped {len(files_to_index) - len(files_to_process)} existing)...")
    
    ids = []
    vectors = []
    metadatas = []
    
    for i, file_path in enumerate(files_to_process):
        if i % 10 == 0:
            print(f"  Processed {i}/{len(files_to_process)}...")
            
        try:
            # Check for valid image or video extensions
            valid_img_exts = ['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif', '.heic', '.tiff', '.tif']
            valid_vid_exts = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v']
            
            is_video = False
            if any(file_path.lower().endswith(ext) for ext in valid_vid_exts):
                 is_video = True
            elif not any(file_path.lower().endswith(ext) for ext in valid_img_exts):
                continue
            
            img = None
            if is_video:
                from server.image_loader import extract_video_frame
                # Extract frame
                try:
                    img = extract_video_frame(file_path)
                except Exception as ve:
                    print(f"Skipping video {os.path.basename(file_path)}: {ve}")
                    continue
            else:
                img = load_image(file_path)

            if img:
                vec = embedding_generator.generate_image_embedding(img)
                if vec:
                    # FIX: Use full path as ID to ensure uniqueness
                    ids.append(file_path) 
                    vectors.append(vec)
                    # Store minimalist metadata, relies on main DB for details
                    metadatas.append({
                        "path": file_path, 
                        "filename": os.path.basename(file_path),
                        "type": "video" if is_video else "image"
                    })
        except Exception as e:
            print(f"Failed to embed {file_path}: {e}")
            
    if ids:
        time_start = __import__("time").time()
        vector_store.add_batch(ids, vectors, metadatas)
        print(f"Added {len(ids)} vectors to LanceDB in {__import__('time').time() - time_start:.2f}s.")

@app.post("/scan")
async def scan_directory(request: ScanRequest, force: bool = False):
    """
    Trigger a scan of a directory.
    This is a blocking operation for now.
    """
    try:
        if not os.path.exists(request.path):
            raise HTTPException(status_code=404, detail="Directory not found")
            
        # 1. Metadata Scan
        catalog = photo_search_engine.scan(request.path, force=force)
        
        file_count = 0
        all_files = []
        if 'catalog' in catalog:
            for folder, files in catalog['catalog'].items():
                for f in files:
                    full_path = os.path.join(folder, f['name'])
                    all_files.append(full_path)
                file_count += len(files)
        
        # 2. Semantic Indexing (Synchronous for now, MVP)
        if all_files:
             process_semantic_indexing(all_files)
                
        return {
            "status": "success", 
            "message": f"Scanned {file_count} files", 
            "extracted_vectors": len(all_files),
            "stats": catalog.get('metadata', {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/index")
async def force_indexing(request: ScanRequest):
    """
    Force semantic indexing of a directory (without re-scanning metadata).
    """
    try:
        # Just walk and index
        files_to_index = []
        for root, dirs, files in os.walk(request.path):
             for file in files:
                 files_to_index.append(os.path.join(root, file))
        
        if files_to_index:
            process_semantic_indexing(files_to_index)
            
        return {"status": "success", "indexed": len(files_to_index)}
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
async def search_photos(query: str = "", option: int = 14): 
    """
    Metadata Search (Legacy/Fast).
    """
    try:
        if not query:
            query = "type:image"

        results = photo_search_engine.query_engine.search(query)
        
        formatted_results = []
        for res in results:
            formatted_results.append({
                "path": res['path'],
                "filename": os.path.basename(res['path']),
                "score": res.get('score', 0),
                "metadata": res.get('metadata', {}) 
            })
            
        return {"count": len(formatted_results), "results": formatted_results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search/semantic")
async def search_semantic(query: str, limit: int = 50):
    """
    Semantic Search using text-to-image embeddings.
    """
    global embedding_generator
    try:
        if not embedding_generator:
            embedding_generator = EmbeddingGenerator()
            
        # 1. Generate text embedding
        text_vec = embedding_generator.generate_text_embedding(query)
        
        # 2. Search LanceDB
        results = vector_store.search(text_vec, limit=limit)
        
        # 3. Format
        formatted = []
        for r in results:
            formatted.append({
                "path": r['metadata']['path'],
                "filename": r['metadata']['filename'],
                "score": r['score'],
                "metadata": r['metadata'] # Pass through extra metadata
            })
            
        return {"count": len(formatted), "results": formatted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/image/thumbnail")
async def get_thumbnail(path: str, size: int = 300):
    """
    Serve a thumbnail or the full image.
    Args:
        path: Path to the image file
        size: Max dimension for thumbnail (default 300)
    """
    # Security check: Ensure path is within allowed directory
    allowed_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    abs_path = os.path.abspath(path)
    
    if not abs_path.startswith(allowed_root):
         raise HTTPException(status_code=403, detail="Access denied")

    if os.path.exists(path):
        try:
            from PIL import Image
            import io
            from fastapi.responses import Response
            
            # For 3D textures we want small files (size=300 is good)
            # For Detail Modal we want larger (size=1200)
            
            # Open image
            with Image.open(path) as img:
                # Convert to RGB if needed (e.g. RGBA or P)
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                    
                # Calculate new aspect ratio
                # thumbnail() modifies in-place and preserves aspect ratio
                img.thumbnail((size, size))
                
                # Save to buffer
                img_io = io.BytesIO()
                img.save(img_io, 'JPEG', quality=70)
                img_io.seek(0)
                
                # Return in-memory bytes with caching headers
                return Response(
                    content=img_io.getvalue(), 
                    media_type="image/jpeg", 
                    headers={"Cache-Control": "public, max-age=31536000"}
                )
                
        except ImportError:
            # Fallback if Pillow not working
            pass # fall through to local file
        except Exception as e:
            print(f"Thumbnail error: {e}")
            pass # fall through to local file

        # Fallback to serving original file
        return FileResponse(path)

    raise HTTPException(status_code=404, detail="Image not found")

@app.get("/stats")
async def get_stats():
    """
    Return system statistics for the dashboard/timeline.
    """
    try:
        # Leverage existing stats logic or db
        stats = photo_search_engine.db.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/timeline")
async def get_timeline():
    """
    Return distribution of photos over time for the Sonic Timeline.
    Grouping by month for now.
    """
    try:
        # We need a method to get date stats. 
        # photo_search_engine.db has get_stats() but that's summary.
        # We'll execute a raw query on the db for now until we extend MetadataDatabase.
        
        # Connect to db safely using the existing connection if available
        # The MetadataDatabase handles connection in __init__
        
        cursor = photo_search_engine.db.conn.cursor()
        
        # Query: Count photos per month
        # SQLite: strftime('%Y-%m', created_at)
        # Fix: Use COALESCE to ensure safety against nulls
        query = """
            SELECT strftime('%Y-%m', json_extract(metadata_json, '$.filesystem.created')) as month, COUNT(*) as count
            FROM metadata
            WHERE json_extract(metadata_json, '$.filesystem.created') IS NOT NULL
            GROUP BY month
            ORDER BY month ASC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        
        timeline_data = [{"date": row[0], "count": row[1]} for row in rows]
        return {"timeline": timeline_data}
        
    except Exception as e:
        # Fallback if table doesn't exist or other error
        print(f"Timeline error: {e}")
        return {"timeline": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
