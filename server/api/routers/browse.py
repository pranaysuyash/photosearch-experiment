"""
Browse router - photo browsing without search dependency.

This router provides endpoints for browsing photos directly from the metadata
database, independent of search modes or embedding models.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
import os
import json

from server.api.deps import get_state
from server.core.state import AppState
from server.utils.files import is_video_file
from server.utils.sorting import apply_sort, apply_date_filter

router = APIRouter()


@router.get("/browse")
async def browse_photos(
    state: AppState = Depends(get_state),
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "date_desc",
    type_filter: str = "all",
    source_filter: str = "all",
    favorites_filter: str = "all",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """
    Browse all photos without search.

    This endpoint returns photos directly from the metadata database,
    independent of search mode or embedding models.

    Args:
        limit: Max photos to return (default 50)
        offset: Pagination offset
        sort_by: Sorting order (date_desc, date_asc, name, size)
        type_filter: Filter by type (all, photos, videos)
        source_filter: Filter by source (all, local, cloud, hybrid)
        favorites_filter: Filter by favorites (all, favorites_only)
        date_from: Optional date filter start
        date_to: Optional date filter end

    Returns:
        {"count": int, "results": [...], "hasMore": bool}
    """
    try:
        photo_search_engine = state.photo_search_engine

        if not photo_search_engine or not photo_search_engine.db:
            raise HTTPException(status_code=503, detail="Photo database not initialized")

        # Query metadata directly
        cursor = photo_search_engine.db.conn.cursor()
        cursor.execute("SELECT file_path, metadata_json FROM metadata")

        results = []
        for row in cursor.fetchall():
            file_path = row["file_path"]
            metadata = json.loads(row["metadata_json"]) if row["metadata_json"] else {}

            results.append(
                {
                    "path": file_path,
                    "filename": os.path.basename(file_path),
                    "score": 0,
                    "metadata": metadata,
                }
            )

        # Apply type filter
        if type_filter == "photos":
            results = [r for r in results if not is_video_file(r.get("path", ""))]
        elif type_filter == "videos":
            results = [r for r in results if is_video_file(r.get("path", ""))]

        # Apply favorites filter
        if favorites_filter == "favorites_only":
            results = [r for r in results if photo_search_engine.is_favorite(r.get("path", ""))]

        # Apply date filter
        if date_from or date_to:
            results = apply_date_filter(results, date_from, date_to)

        # Apply sorting
        results = apply_sort(results, sort_by)

        # Get total count before pagination
        total_count = len(results)

        # Apply pagination
        paginated = results[offset : offset + limit]
        has_more = (offset + len(paginated)) < total_count

        return {
            "count": total_count,
            "results": paginated,
            "hasMore": has_more,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Browse failed: {str(e)}")
