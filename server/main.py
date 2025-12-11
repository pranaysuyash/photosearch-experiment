import sys
import os
from typing import List, Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException, Body, BackgroundTasks
from server.jobs import job_store, Job
from server.pricing import pricing_manager, PricingTier, UsageStats
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

# Helper functions for sorting and filtering
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.wmv', '.flv'}

def is_video_file(path: str) -> bool:
    """Check if a file is a video based on extension."""
    ext = os.path.splitext(path)[1].lower()
    return ext in VIDEO_EXTENSIONS

def apply_sort(results: list, sort_by: str) -> list:
    """Sort results by specified criteria."""
    if not results:
        return results
    
    if sort_by == "date_desc":
        # Sort by created date descending (newest first)
        return sorted(results, key=lambda x: x.get('metadata', {}).get('filesystem', {}).get('created', ''), reverse=True)
    elif sort_by == "date_asc":
        # Sort by created date ascending (oldest first)
        return sorted(results, key=lambda x: x.get('metadata', {}).get('filesystem', {}).get('created', ''))
    elif sort_by == "name":
        # Sort by filename alphabetically
        return sorted(results, key=lambda x: x.get('filename', '').lower())
    elif sort_by == "size":
        # Sort by file size descending (largest first)
        return sorted(results, key=lambda x: x.get('metadata', {}).get('filesystem', {}).get('size_bytes', 0), reverse=True)
    
    return results

# Initialize Core Logic
# We prefer a persistent instance
photo_search_engine = PhotoSearch()

# Initialize Semantic Search Components
from server.lancedb_store import LanceDBStore
from server.embedding_generator import EmbeddingGenerator
from server.image_loader import load_image

from server.watcher import start_watcher

# Lazily loaded or initialized here
# Note: EmbeddingGenerator loads a model (~500MB), so it might take a moment on first request or startup
vector_store = LanceDBStore()
embedding_generator = None # Load lazily or on startup
file_watcher = None # Global observer instance

@app.on_event("startup")
async def startup_event():
    global embedding_generator, file_watcher
    print("Initializing Embedding Model...")
    # Initialize in background or here? For now, simple synchronous load.
    try:
        embedding_generator = EmbeddingGenerator()
        print("Embedding Model Loaded.")
        
        # Auto-scan 'media' directory on startup
        media_path = settings.BASE_DIR / "media"
        if media_path.exists():
            print(f"Auto-scanning {media_path}...")
            # 1. Run full scan check
            try:
                photo_search_engine.scan(str(media_path), force=False)
                print("Auto-scan complete.")
            except Exception as e:
                print(f"Auto-scan failed: {e}")

            # 2. Start Real-time Watcher
            def handle_new_file(filepath: str):
                """Callback for new files detected by watcher"""
                try:
                    print(f"Index trigger: {filepath}")
                    # Extract Metadata (Single file update using BatchExtractor's underlying logic)
                    # We can use the lower-level extract function
                    from metadata_extractor import extract_all_metadata
                    
                    metadata = extract_all_metadata(filepath)
                    if metadata:
                        photo_search_engine.db.store_metadata(filepath, metadata)
                        print(f"Metadata indexed: {filepath}")
                        
                        # Trigger Semantic Indexing
                        process_semantic_indexing([filepath])
                except Exception as e:
                    print(f"Real-time indexing failed for {filepath}: {e}")

            print("Starting file watcher...")
            file_watcher = start_watcher(str(media_path), handle_new_file)
                
    except Exception as e:
        print(f"Startup error: {e}")

@app.on_event("shutdown")
def shutdown_event():
    if file_watcher:
        file_watcher.stop()
        file_watcher.join()

class ScanRequest(BaseModel):
    path: str

class SearchRequest(BaseModel):
    query: str
    limit: int = 1000
    offset: int = 0

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
async def search_photos(
    query: str = "", 
    limit: int = 50, 
    offset: int = 0, 
    mode: str = "metadata",
    sort_by: str = "date_desc",  # date_desc, date_asc, name, size
    type_filter: str = "all"  # all, photos, videos
):
    """
    Unified Search Endpoint.
    Modes: 
      - 'metadata' (SQL)
      - 'semantic' (CLIP)
      - 'hybrid' (Merge Metadata + Semantic)
    Sort: date_desc (default), date_asc, name, size
    Type Filter: all (default), photos, videos
    """
    try:
        # 1. Semantic Search
        if mode == "semantic":
            results_response = await search_semantic(query, limit * 2, 0)  # Get more for filtering
            results = results_response.get('results', [])
            
            # Apply type filter
            if type_filter == "photos":
                results = [r for r in results if not is_video_file(r.get('path', ''))]
            elif type_filter == "videos":
                results = [r for r in results if is_video_file(r.get('path', ''))]
            
            # Apply sort
            results = apply_sort(results, sort_by)
            
            # Paginate
            paginated = results[offset:offset + limit]
            return {"count": len(results), "results": paginated}

        # 2. Metadata Search
        if mode == "metadata":
            # For empty query, directly get all files from database
            if not query.strip():
                cursor = photo_search_engine.db.conn.cursor()
                cursor.execute("SELECT file_path, metadata_json FROM metadata")
                results = []
                for row in cursor.fetchall():
                    import json
                    results.append({
                        'file_path': row['file_path'],
                        'metadata': json.loads(row['metadata_json']) if row['metadata_json'] else {}
                    })
            else:
                # Use QueryEngine for actual search queries
                results = photo_search_engine.query_engine.search(query)
            
            # Formatted list
            formatted_results = [
                {
                    "path": r.get('file_path', r.get('path')),
                    "filename": os.path.basename(r.get('file_path', r.get('path'))),
                    "score": r.get('score', 0),
                    "metadata": r.get('metadata', {})
                }
                for r in results
            ]
            
            # Apply type filter
            if type_filter == "photos":
                formatted_results = [r for r in formatted_results if not is_video_file(r.get('path', ''))]
            elif type_filter == "videos":
                formatted_results = [r for r in formatted_results if is_video_file(r.get('path', ''))]
            
            # Apply sorting
            formatted_results = apply_sort(formatted_results, sort_by)
            
            # Apply Pagination Slicing
            count = len(formatted_results)
            paginated = formatted_results[offset : offset + limit]
            
            return {"count": count, "results": paginated}

        # 3. Hybrid Search (Metadata + Semantic with weighted scoring)
        if mode == "hybrid":
            # A. Get Metadata Results (All)
            metadata_results = []
            try:
                if any(op in query for op in ['=', '>', '<', 'LIKE']):
                    metadata_results = photo_search_engine.query_engine.search(query)
                else:
                    safe_query = query.replace("'", "''")
                    metadata_results = photo_search_engine.query_engine.search(
                        f"file.path LIKE '%{safe_query}%'"
                    )
            except Exception as e:
                print(f"Metadata search error in hybrid: {e}")

            # B. Get Semantic Results (Top N = limit + offset)
            # We need deep fetch to ensure correct global ranking after merge
            semantic_limit = limit + offset
            semantic_response = await search_semantic(query, semantic_limit, offset=0)
            semantic_results = semantic_response['results']

            # C. Normalize semantic scores
            if semantic_results:
                max_score = max(r['score'] for r in semantic_results)
                min_score = min(r['score'] for r in semantic_results)
                score_range = max_score - min_score if max_score != min_score else 1.0
                
                for r in semantic_results:
                    r['normalized_score'] = (r['score'] - min_score) / score_range

            # D. Merge Logic
            METADATA_WEIGHT = 0.6
            SEMANTIC_WEIGHT = 0.4
            
            seen_paths = set()
            hybrid_results = []
            
            for r in metadata_results:
                path = r.get('file_path', r.get('path'))
                seen_paths.add(path)
                semantic_match = next((s for s in semantic_results if s['path'] == path), None)
                
                if semantic_match:
                    combined_score = (METADATA_WEIGHT * 1.0) + (SEMANTIC_WEIGHT * semantic_match.get('normalized_score', 0.5))
                else:
                    combined_score = METADATA_WEIGHT * 0.8
                
                hybrid_results.append({
                    "path": path,
                    "filename": os.path.basename(path),
                    "score": round(combined_score, 3),
                    "metadata": r.get('metadata', {}),
                    "source": "both" if semantic_match else "metadata"
                })

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
            
            # Apply Pagination Slicing
            count = len(hybrid_results)
            paginated = hybrid_results[offset : offset + limit]
            
            return {"count": count, "results": paginated}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search/semantic")
async def search_semantic(query: str, limit: int = 50, offset: int = 0, min_score: float = 0.22):
    """
    Semantic Search using text-to-image embeddings.
    """
    global embedding_generator
    try:
        if not embedding_generator:
            embedding_generator = EmbeddingGenerator()
        
        # Handle empty query - return all photos (paginated)
        if not query.strip():
            try:
                # Pass offset to store
                all_records = vector_store.get_all_records(limit=limit, offset=offset)
                formatted = []
                for r in all_records:
                    file_path = r.get('path', r.get('id', ''))
                    full_metadata = photo_search_engine.db.get_metadata_by_path(file_path)
                    formatted.append({
                        "path": file_path,
                        "filename": r.get('filename', os.path.basename(file_path)),
                        "score": 0,
                        "metadata": full_metadata or {}
                    })
                # Count is tricky here, but we return page size for now
                return {"count": len(formatted), "results": formatted}
            except Exception as e:
                print(f"Error getting all records: {e}")
                return {"count": 0, "results": []}
            
        # 1. Generate text embedding
        text_vec = embedding_generator.generate_text_embedding(query)
        
        # 2. Search LanceDB with offset
        # vector_store.search now supports offset directly
        results = vector_store.search(text_vec, limit=limit, offset=offset)
        
        # 3. Format and enrich
        formatted = []
        for r in results:
            if r['score'] >= min_score:
                file_path = r['metadata']['path']
                full_metadata = photo_search_engine.db.get_metadata_by_path(file_path)
                
                formatted.append({
                    "path": file_path,
                    "filename": r['metadata']['filename'],
                    "score": r['score'],
                    "metadata": full_metadata or r['metadata']
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


# ========== PRICING ENDPOINTS ==========

@app.get("/pricing", response_model=List[PricingTier])
async def get_pricing_tiers():
    """
    Get all available pricing tiers.
    """
    return pricing_manager.get_all_tiers()


@app.get("/pricing/{tier_name}", response_model=PricingTier)
async def get_pricing_tier(tier_name: str):
    """
    Get details for a specific pricing tier.
    """
    tier = pricing_manager.get_tier(tier_name)
    if not tier:
        raise HTTPException(status_code=404, detail="Pricing tier not found")
    return tier


@app.get("/pricing/recommend", response_model=PricingTier)
async def recommend_pricing_tier(image_count: int):
    """
    Recommend a pricing tier based on image count.
    """
    if image_count < 0:
        raise HTTPException(status_code=400, detail="Image count must be positive")
    
    return pricing_manager.get_tier_by_image_count(image_count)


@app.get("/usage/{user_id}", response_model=UsageStats)
async def get_usage_stats(user_id: str):
    """
    Get current usage statistics for a user.
    """
    # Get current image count from database
    try:
        cursor = photo_search_engine.db.conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM metadata")
        result = cursor.fetchone()
        image_count = result['count'] if result else 0
    except Exception as e:
        print(f"Error getting image count: {e}")
        image_count = 0
    
    # Track usage and return stats
    return pricing_manager.track_usage(user_id, image_count)


@app.get("/usage/check/{user_id}")
async def check_usage_limit(user_id: str, additional_images: int = 0):
    """
    Check if user can add more images without exceeding their limit.
    """
    if additional_images < 0:
        raise HTTPException(status_code=400, detail="Additional images must be positive")
    
    can_add = pricing_manager.check_limit(user_id, additional_images)
    
    return {
        "can_add": can_add,
        "message": "User can add images" if can_add else "User would exceed their image limit"
    }


@app.post("/usage/upgrade/{user_id}")
async def upgrade_user_tier(user_id: str, new_tier: str):
    """
    Upgrade a user to a new pricing tier.
    """
    success = pricing_manager.upgrade_tier(user_id, new_tier)
    
    if not success:
        raise HTTPException(status_code=400, detail="Invalid tier or user not found")
    
    return {
        "success": True,
        "message": f"User {user_id} upgraded to {new_tier} tier",
        "new_tier": new_tier
    }

class ExportRequest(BaseModel):
    paths: List[str]
    format: str = "zip"  # Future: could support "json" for metadata export

@app.post("/export")
async def export_photos(request: ExportRequest):
    """
    Export selected photos as a ZIP file.
    
    Args:
        request: ExportRequest with list of file paths
        
    Returns:
        Streaming ZIP file download
    """
    import zipfile
    import io
    from fastapi.responses import StreamingResponse
    
    if not request.paths:
        raise HTTPException(status_code=400, detail="No files specified")
    
    if len(request.paths) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 files per export")
    
    # Validate paths are within allowed directories
    valid_paths = []
    for path in request.paths:
        try:
            requested_path = Path(path).resolve()
            if settings.MEDIA_DIR.exists():
                allowed_paths = [settings.MEDIA_DIR.resolve(), settings.BASE_DIR.resolve()]
            else:
                allowed_paths = [settings.BASE_DIR.resolve()]
            
            is_allowed = any(
                requested_path.is_relative_to(allowed_path) 
                for allowed_path in allowed_paths
            )
            
            if is_allowed and os.path.exists(path):
                valid_paths.append(path)
        except ValueError:
            continue
    
    if not valid_paths:
        raise HTTPException(status_code=400, detail="No valid files to export")
    
    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for path in valid_paths:
            filename = os.path.basename(path)
            # Handle duplicate filenames by adding parent folder
            if any(os.path.basename(p) == filename and p != path for p in valid_paths):
                parent = os.path.basename(os.path.dirname(path))
                filename = f"{parent}_{filename}"
            zip_file.write(path, filename)
    
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=photos_export.zip"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
