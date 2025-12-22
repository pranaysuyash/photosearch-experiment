from typing import Optional

from fastapi import APIRouter, HTTPException

from server.config import settings
from server.duplicates_db import get_duplicates_db
from server.models.schemas.duplicates import DuplicateResolution


router = APIRouter()


@router.get("/api/duplicates")
async def get_duplicates(hash_type: Optional[str] = None, limit: int = 100, offset: int = 0):
    """Get duplicate groups."""
    try:
        duplicates_db = get_duplicates_db(settings.BASE_DIR / "duplicates.db")
        groups = duplicates_db.get_duplicate_groups(hash_type, limit, offset)
        return {"count": len(groups), "groups": [g.__dict__ for g in groups]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/duplicates/scan")
async def scan_duplicates(type: str = "exact", limit: int = 1000):
    """Scan for duplicates."""
    try:
        if type not in ["exact", "perceptual"]:
            raise HTTPException(status_code=400, detail="Type must be 'exact' or 'perceptual'")

        from server import main as main_module

        # Get all photo paths from database
        cursor = main_module.photo_search_engine.db.conn.cursor()
        cursor.execute("SELECT file_path FROM metadata WHERE deleted_at IS NULL LIMIT ?", (limit,))
        all_files = [row[0] for row in cursor.fetchall()]

        duplicates_db = get_duplicates_db(settings.BASE_DIR / "duplicates.db")

        if type == "exact":
            groups = duplicates_db.find_exact_duplicates(all_files)
        else:
            # For perceptual duplicates, we'd implement image similarity detection
            # For now, return empty
            groups = []

        return {
            "scanned": len(all_files),
            "duplicate_groups_found": len(groups),
            "groups": [g.__dict__ for g in groups],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/duplicates/{group_id}/resolve")
async def resolve_duplicates(group_id: str, resolution: DuplicateResolution):
    """Resolve a duplicate group."""
    try:
        duplicates_db = get_duplicates_db(settings.BASE_DIR / "duplicates.db")
        keep_files = resolution.keep_files or []
        success = duplicates_db.resolve_duplicates(group_id, resolution.resolution, keep_files)
        return {"success": success, "group_id": group_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/duplicates/{group_id}")
async def delete_duplicate_group(group_id: str):
    """Delete a duplicate group."""
    try:
        duplicates_db = get_duplicates_db(settings.BASE_DIR / "duplicates.db")
        success = duplicates_db.delete_group(group_id)
        return {"success": success, "group_id": group_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/duplicates/stats")
async def get_duplicates_stats():
    """Get duplicate statistics."""
    try:
        duplicates_db = get_duplicates_db(settings.BASE_DIR / "duplicates.db")
        stats = duplicates_db.get_duplicate_stats()
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/duplicates/cleanup")
async def cleanup_duplicates():
    """Clean up entries for missing files."""
    try:
        duplicates_db = get_duplicates_db(settings.BASE_DIR / "duplicates.db")
        cleaned_count = duplicates_db.cleanup_missing_files()
        return {"cleaned_files": cleaned_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
