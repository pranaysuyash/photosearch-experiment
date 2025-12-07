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

app = FastAPI(title="PhotoSearch API", description="Backend for the Living Museum Interface")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Core Logic
# We prefer a persistent instance
photo_search_engine = PhotoSearch()

class ScanRequest(BaseModel):
    path: str

class SearchRequest(BaseModel):
    query: str
    option: int = 14 # Default to custom/quick search

@app.get("/")
async def root():
    return {"status": "ok", "message": "PhotoSearch API is running"}

@app.post("/scan")
async def scan_directory(request: ScanRequest, force: bool = False):
    """
    Trigger a scan of a directory.
    This is a blocking operation for now.
    """
    try:
        if not os.path.exists(request.path):
            raise HTTPException(status_code=404, detail="Directory not found")
            
        # We can reuse the scan logic from PhotoSearch
        # Note: This runs directly. For large libraries, we might need a background task later.
        catalog = photo_search_engine.scan(request.path, force=force)
        
        # Calculate true file count from nested catalog structure
        # Catalog structure is {'catalog': {'folder_path': [files]}, 'metadata': ...}
        file_count = 0
        if 'catalog' in catalog:
            for files in catalog['catalog'].values():
                file_count += len(files)
                
        return {"status": "success", "message": f"Scanned {file_count} files", "stats": catalog.get('metadata', {})}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
async def search_photos(query: str = "", option: int = 14): 
    """
    Search for photos using the CLI query engine.
    """
    try:
        # Handle empty query -> return all recent
        if not query:
            # We construct a "match all" query or simply return recent files from DB
            # For now, let's use a broad term or specific wildcard if supported.
            # Assuming our engine handles "date" or similar broad terms.
            # Better approach: Direct DB query for recent.
            # Use "type:image" to get all images.
            query = "type:image"

        results = photo_search_engine.query_engine.search(query)
        
        # Format results for API
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
