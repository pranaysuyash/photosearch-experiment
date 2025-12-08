import sys
import os
from typing import List, Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException, Body, BackgroundTasks
from server.jobs import job_store, Job
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
async def scan_directory(
    background_tasks: BackgroundTasks,
    payload: dict = Body(...)
):
    """
    Scan a directory for photos.
    Supports asynchronous scanning via background tasks.
    """
    path = payload.get("path")
    force = payload.get("force", False)
    background = payload.get("background", True)

    if not path:
        raise HTTPException(status_code=400, detail="Path is required")
    
    if not os.path.exists(path):
        raise HTTPException(status_code=400, detail="Directory does not exist")

    # If background processing is requested (default)
    if background:
        job_id = job_store.create_job(type="scan")
        
        # Define the background task wrapper
        def run_scan(job_id: str, path: str, force: bool):
            try:
                # The scan method should update the job status internally
                # and return the list of files for semantic indexing
                scan_results = photo_search_engine.scan(path, force=force, job_id=job_id)
                
                # After scanning metadata, perform semantic indexing
                all_files = scan_results.get("all_files", [])
                if all_files:
                    process_semantic_indexing(all_files)
                
                job_store.update_job(job_id, status="completed", message="Scan and indexing finished.")
            except Exception as e:
                print(f"Job {job_id} failed: {e}")
                job_store.update_job(job_id, status="failed", message=str(e))

        background_tasks.add_task(run_scan, job_id, path, force)
        
        return {"job_id": job_id, "status": "pending", "message": "Scan started in background"}
    else:
        # Synchronous (Legacy/Blocking)
        try:
            results = photo_search_engine.scan(path, force=force)
            
            # Perform semantic indexing synchronously if not in background
            all_files = results.get("all_files", [])
            if all_files:
                process_semantic_indexing(all_files)

            return results
        except Exception as e:
             raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs/{job_id}", response_model=Job)
async def get_job_status(job_id: str):
    """Get the status of a background job."""
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

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
async def search_photos(query: str = "", limit: int = 50, mode: str = "metadata"):
    """
    Unified Search Endpoint.
    Modes: 
      - 'metadata' (SQL)
      - 'semantic' (CLIP)
      - 'hybrid' (Merge Metadata + Semantic)
    """
    try:
        # 1. Semantic Search
        if mode == "semantic":
            return await search_semantic(query, limit)

        # 2. Metadata Search
        if mode == "metadata":
            if not query:
                query = "file.mime_type LIKE 'image%'"
            
            results = photo_search_engine.query_engine.search(query)
            formatted_results = [
                {
                    "path": r.get('file_path', r.get('path')),
                    "filename": os.path.basename(r.get('file_path', r.get('path'))),
                    "score": r.get('score', 0),
                    "metadata": r.get('metadata', {})
                }
                for r in results
            ]
            return {"count": len(formatted_results), "results": formatted_results}

        # 3. Hybrid Search (Metadata + Semantic with weighted scoring)
        if mode == "hybrid":
            # A. Get Metadata Results
            metadata_results = []
            try:
                # Try exact field match first
                if any(op in query for op in ['=', '>', '<', 'LIKE']):
                    metadata_results = photo_search_engine.query_engine.search(query)
                else:
                    # Fuzzy path/filename search with proper quoting
                    safe_query = query.replace("'", "''")  # Escape quotes
                    metadata_results = photo_search_engine.query_engine.search(
                        f"file.path LIKE '%{safe_query}%'"
                    )
            except Exception as e:
                print(f"Metadata search error in hybrid: {e}")

            # B. Get Semantic Results
            semantic_response = await search_semantic(query, limit)
            semantic_results = semantic_response['results']

            # C. Normalize semantic scores (typically 0.15-0.35 range -> 0-1)
            if semantic_results:
                max_score = max(r['score'] for r in semantic_results)
                min_score = min(r['score'] for r in semantic_results)
                score_range = max_score - min_score if max_score != min_score else 1.0
                
                for r in semantic_results:
                    # Normalize to 0-1 range
                    r['normalized_score'] = (r['score'] - min_score) / score_range

            # D. Merge with weighted scoring
            METADATA_WEIGHT = 0.6  # Exact matches are weighted higher
            SEMANTIC_WEIGHT = 0.4
            
            seen_paths = set()
            hybrid_results = []
            
            # Add Metadata results first (higher base score for exact matches)
            for r in metadata_results:
                path = r.get('file_path', r.get('path'))
                seen_paths.add(path)
                
                # Check if this file also has semantic match for combined score
                semantic_match = next((s for s in semantic_results if s['path'] == path), None)
                
                if semantic_match:
                    # Combined score: weighted average
                    combined_score = (METADATA_WEIGHT * 1.0) + (SEMANTIC_WEIGHT * semantic_match.get('normalized_score', 0.5))
                else:
                    # Metadata-only match
                    combined_score = METADATA_WEIGHT * 0.8  # Slight penalty for no semantic match
                
                hybrid_results.append({
                    "path": path,
                    "filename": os.path.basename(path),
                    "score": round(combined_score, 3),
                    "metadata": r.get('metadata', {}),
                    "source": "both" if semantic_match else "metadata"
                })

            # Add Semantic-only results
            for r in semantic_results:
                if r['path'] not in seen_paths:
                    seen_paths.add(r['path'])
                    hybrid_results.append({
                        "path": r['path'],
                        "filename": r['filename'],
                        "score": round(SEMANTIC_WEIGHT * r.get('normalized_score', r['score']), 3),
                        "metadata": r.get('metadata', {}),
                        "source": "semantic"
                    })
            
            # Sort by score descending
            hybrid_results.sort(key=lambda x: x['score'], reverse=True)
            
            return {"count": len(hybrid_results), "results": hybrid_results[:limit]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search/semantic")
async def search_semantic(query: str, limit: int = 50, min_score: float = 0.22):
    """
    Semantic Search using text-to-image embeddings.
    Args:
        min_score: Minimum similarity score threshold (default 0.18 filters out irrelevant results)
    """
    global embedding_generator
    try:
        if not embedding_generator:
            embedding_generator = EmbeddingGenerator()
        
        # Handle empty query - return all photos
        if not query.strip():
            # Return all indexed photos without semantic ranking
            try:
                all_records = vector_store.get_all_records(limit=limit)
                formatted = []
                for r in all_records:
                    file_path = r.get('path', r.get('id', ''))
                    # Enrich with full metadata from main database
                    full_metadata = photo_search_engine.db.get_metadata_by_path(file_path)
                    formatted.append({
                        "path": file_path,
                        "filename": r.get('filename', os.path.basename(file_path)),
                        "score": 0,
                        "metadata": full_metadata or {}
                    })
                return {"count": len(formatted), "results": formatted}
            except Exception as e:
                print(f"Error getting all records: {e}")
                return {"count": 0, "results": []}
            
        # 1. Generate text embedding
        text_vec = embedding_generator.generate_text_embedding(query)
        
        # 2. Search LanceDB
        results = vector_store.search(text_vec, limit=limit * 2)  # Get more, then filter
        
        # 3. Format and filter by min_score, enriching with full metadata
        formatted = []
        for r in results:
            if r['score'] >= min_score:  # Only include results above threshold
                file_path = r['metadata']['path']
                
                # Enrich with full metadata from main database
                full_metadata = photo_search_engine.db.get_metadata_by_path(file_path)
                
                formatted.append({
                    "path": file_path,
                    "filename": r['metadata']['filename'],
                    "score": r['score'],
                    "metadata": full_metadata or r['metadata']  # Fallback to LanceDB metadata
                })
        
        # Limit to requested count after filtering
        formatted = formatted[:limit]
            
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
    # In production, use MEDIA_DIR for stricter sandboxing
    # In development, allow BASE_DIR for flexibility
    try:
        # Use stricter MEDIA_DIR if it exists, otherwise fall back to BASE_DIR
        if settings.MEDIA_DIR.exists():
            allowed_paths = [settings.MEDIA_DIR.resolve(), settings.BASE_DIR.resolve()]
        else:
            allowed_paths = [settings.BASE_DIR.resolve()]
        
        requested_path = Path(path).resolve()
        
        # Check if requested path is within any allowed directory
        is_allowed = any(
            requested_path.is_relative_to(allowed_path) 
            for allowed_path in allowed_paths
        )
        
        if not is_allowed:
            print(f"Access denied: {requested_path} is outside allowed directories")
            raise HTTPException(status_code=403, detail="Access denied: File outside allowed directories")
    except ValueError:
        # is_relative_to raises ValueError if different drives on Windows, etc.
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

@app.get("/video")
async def get_video(path: str):
    """
    Serve a video file directly.
    """
    from fastapi.responses import FileResponse
    
    # Security check
    try:
        if settings.MEDIA_DIR.exists():
            allowed_paths = [settings.MEDIA_DIR.resolve(), settings.BASE_DIR.resolve()]
        else:
            allowed_paths = [settings.BASE_DIR.resolve()]
        
        requested_path = Path(path).resolve()
        is_allowed = any(
            requested_path.is_relative_to(allowed_path) 
            for allowed_path in allowed_paths
        )
        
        if not is_allowed:
            raise HTTPException(status_code=403, detail="Access denied")
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if os.path.exists(path):
        # Get mime type
        ext = Path(path).suffix.lower()
        mime_types = {
            '.mp4': 'video/mp4',
            '.mov': 'video/quicktime',
            '.avi': 'video/x-msvideo',
            '.mkv': 'video/x-matroska',
            '.webm': 'video/webm',
            '.m4v': 'video/x-m4v'
        }
        media_type = mime_types.get(ext, 'video/mp4')
        return FileResponse(path, media_type=media_type)
    
    raise HTTPException(status_code=404, detail="Video not found")

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
