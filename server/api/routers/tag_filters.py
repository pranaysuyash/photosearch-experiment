import json
import sqlite3
from collections import Counter
from typing import Literal, Optional, cast

from fastapi import APIRouter, HTTPException

from server.config import settings
from server.models.schemas.tag_filters import (
    Legacy2TagFilterCreateRequest,
    Legacy2TagFilterUpdateRequest,
    TagFilterCreateRequest,
    TagFilterUpdateRequest,
)
from server.multi_tag_filter_db import MultiTagFilterDB, get_multi_tag_filter_db


router = APIRouter()


@router.post("/tag-filters/legacy2")
async def create_tag_filter_legacy2(request: Legacy2TagFilterCreateRequest):
    """Create a new tag filter with custom expressions and logic."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")

        filter_id = tag_filter_db.create_tag_filter(
            name=request.name,
            tag_expressions=[expr.dict() for expr in request.tag_expressions],
            combination_operator=request.combination_operator,
        )

        if not filter_id:
            raise HTTPException(status_code=400, detail="Failed to create tag filter")

        return {"success": True, "filter_id": filter_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tag-filters/legacy2/{filter_id}")
async def get_tag_filter_legacy2(filter_id: str):
    """Get details of a specific tag filter."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")
        tag_filter = tag_filter_db.get_tag_filter(filter_id)

        if not tag_filter:
            raise HTTPException(status_code=404, detail="Tag filter not found")

        return {"tag_filter": tag_filter}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tag-filters/legacy2")
async def get_tag_filters_legacy2(limit: int = 50, offset: int = 0):
    """Get all tag filters."""
    try:
        with sqlite3.connect(settings.BASE_DIR / "tag_filters.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM tag_filters ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
            rows = cursor.fetchall()

            return {
                "filters": [dict(row) for row in rows],
                "count": len(rows),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tag-filters/legacy2/{filter_id}")
async def update_tag_filter_legacy2(filter_id: str, request: Legacy2TagFilterUpdateRequest):
    """Update a tag filter."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")

        # Get existing filter first
        existing_filter = tag_filter_db.get_tag_filter(filter_id)
        if not existing_filter:
            raise HTTPException(status_code=404, detail="Tag filter not found")

        # Update the filter
        with sqlite3.connect(settings.BASE_DIR / "tag_filters.db") as conn:
            update_fields = []
            params = []

            if request.name is not None:
                update_fields.append("name = ?")
                params.append(request.name)

            if request.tag_expressions is not None:
                update_fields.append("tag_expressions = ?")
                params.append(json.dumps([expr.dict() for expr in request.tag_expressions]))

            if request.combination_operator is not None:
                update_fields.append("combination_operator = ?")
                params.append(request.combination_operator)

            update_fields.append("updated_at = CURRENT_TIMESTAMP")

            if update_fields:
                sql = f"UPDATE tag_filters SET {', '.join(update_fields)} WHERE id = ?"
                params.append(filter_id)

                cursor = conn.execute(sql, params)

                if cursor.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Tag filter not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tag-filters/legacy2/{filter_id}")
async def delete_tag_filter_legacy2(filter_id: str):
    """Delete a tag filter."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")
        success = tag_filter_db.delete_tag_filter(filter_id)

        if not success:
            raise HTTPException(status_code=404, detail="Tag filter not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tag-filters/legacy2/apply")
async def apply_tag_filter_legacy2(request: Legacy2TagFilterCreateRequest):
    """Apply a tag filter and get matching photos."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")

        matching_photos = tag_filter_db.apply_tag_filter(
            tag_expressions=[expr.dict() for expr in request.tag_expressions],
            combination_operator=request.combination_operator,
        )

        return {
            "photos": matching_photos,
            "count": len(matching_photos),
            "filter_used": {
                "name": "Temporary Filter",
                "expressions": [expr.dict() for expr in request.tag_expressions],
                "operator": request.combination_operator,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/photos/by-tags/legacy2")
async def get_photos_by_tags_legacy2(
    tags: str,  # Comma-separated list of tags
    operator: str = "OR",  # OR or AND
    exclude_tags: Optional[str] = None,  # Comma-separated list of tags to exclude
    limit: int = 100,
    offset: int = 0,
):
    """Get photos by multiple tags with AND/OR logic."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")

        tag_list = [tag.strip() for tag in tags.split(",")]
        exclude_list = [tag.strip() for tag in exclude_tags.split(",")] if exclude_tags else []

        op_upper = operator.upper()
        if op_upper not in ("AND", "OR"):
            op_upper = "OR"
        operator_literal = cast(Literal["AND", "OR"], op_upper)

        matching_photos = tag_filter_db.get_photos_by_tags(
            tags=tag_list,
            operator=operator_literal,
            exclude_tags=exclude_list or None,
        )

        # Apply pagination
        paginated_photos = matching_photos[offset : offset + limit]

        return {
            "photos": paginated_photos,
            "total_count": len(matching_photos),
            "filter": {
                "included_tags": tag_list,
                "excluded_tags": exclude_list,
                "operator": operator,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tags/common")
async def get_common_tags(photo_paths: str, limit: int = 10):
    """Get common tags across multiple photos."""
    try:
        tag_filter_db: MultiTagFilterDB = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")

        path_list = [path.strip() for path in photo_paths.split(",")]

        common: set[str] | None = None
        for p in path_list:
            if not p:
                continue
            tags = set(tag_filter_db.get_tags_for_photo(p))
            common = tags if common is None else (common & tags)

        common_tags = sorted(common or [])[:limit]
        return {"common_tags": common_tags, "count": len(common_tags)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tags/search")
async def search_tags(query: str, limit: int = 20):
    """Search for tags by name."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")
        matching_tags = tag_filter_db.search_tags(query, limit)

        return {"tags": matching_tags, "count": len(matching_tags)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tags/stats")
async def get_tag_stats():
    """Get statistics about tags in the system."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")
        stats = tag_filter_db.get_tag_stats()

        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tag-filters")
async def create_tag_filter(request: TagFilterCreateRequest):
    """Create a new tag filter with custom expressions and logic."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")

        filter_id = tag_filter_db.create_tag_filter(
            name=request.name,
            tag_expressions=[expr.dict() for expr in request.tag_expressions],
            combination_operator=request.combination_operator,
        )

        if not filter_id:
            raise HTTPException(status_code=400, detail="Failed to create tag filter")

        return {"success": True, "filter_id": filter_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tag-filters/{filter_id}")
async def get_tag_filter(filter_id: str):
    """Get details of a specific tag filter."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")
        tag_filter = tag_filter_db.get_tag_filter(filter_id)

        if not tag_filter:
            raise HTTPException(status_code=404, detail="Tag filter not found")

        return {"tag_filter": tag_filter}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tag-filters")
async def get_tag_filters(limit: int = 50, offset: int = 0):
    """Get all tag filters."""
    try:
        with sqlite3.connect(settings.BASE_DIR / "tag_filters.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM tag_filters ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
            rows = cursor.fetchall()

            return {
                "filters": [dict(row) for row in rows],
                "count": len(rows),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tag-filters/{filter_id}")
async def update_tag_filter(filter_id: str, request: TagFilterUpdateRequest):
    """Update a tag filter."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")

        # Get existing filter first
        existing_filter = tag_filter_db.get_tag_filter(filter_id)
        if not existing_filter:
            raise HTTPException(status_code=404, detail="Tag filter not found")

        # Update the filter
        with sqlite3.connect(settings.BASE_DIR / "tag_filters.db") as conn:
            update_fields = []
            params = []

            if request.name is not None:
                update_fields.append("name = ?")
                params.append(request.name)

            if request.tag_expressions is not None:
                update_fields.append("tag_expressions = ?")
                params.append(json.dumps([expr.dict() for expr in request.tag_expressions]))

            if request.combination_operator is not None:
                update_fields.append("combination_operator = ?")
                params.append(request.combination_operator)

            update_fields.append("updated_at = CURRENT_TIMESTAMP")

            if update_fields:
                sql = f"UPDATE tag_filters SET {', '.join(update_fields)} WHERE id = ?"
                params.append(filter_id)

                cursor = conn.execute(sql, params)

                if cursor.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Tag filter not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tag-filters/{filter_id}")
async def delete_tag_filter(filter_id: str):
    """Delete a tag filter."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")
        success = tag_filter_db.delete_tag_filter(filter_id)

        if not success:
            raise HTTPException(status_code=404, detail="Tag filter not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tag-filters/apply")
async def apply_tag_filter(request: TagFilterCreateRequest):
    """Apply a tag filter and get matching photos."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")

        matching_photos = tag_filter_db.apply_tag_filter(
            tag_expressions=[expr.dict() for expr in request.tag_expressions],
            combination_operator=request.combination_operator,
        )

        return {
            "photos": matching_photos,
            "count": len(matching_photos),
            "filter_used": {
                "name": "Temporary Filter",
                "expressions": [expr.dict() for expr in request.tag_expressions],
                "operator": request.combination_operator,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/photos/by-tags")
async def get_photos_by_tags(
    tags: str,  # Comma-separated list of tags
    operator: str = "OR",  # OR or AND
    exclude_tags: Optional[str] = None,  # Comma-separated list of tags to exclude
    limit: int = 100,
    offset: int = 0,
):
    """Get photos by multiple tags with AND/OR logic."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")

        tag_list = [tag.strip() for tag in tags.split(",")]
        exclude_list = [tag.strip() for tag in exclude_tags.split(",")] if exclude_tags else []

        op_upper = operator.upper()
        if op_upper not in ("AND", "OR"):
            op_upper = "OR"
        operator_literal = cast(Literal["AND", "OR"], op_upper)

        matching_photos = tag_filter_db.get_photos_by_tags(
            tags=tag_list,
            operator=operator_literal,
            exclude_tags=exclude_list or None,
        )

        # Apply pagination
        paginated_photos = matching_photos[offset : offset + limit]

        return {
            "photos": paginated_photos,
            "total_count": len(matching_photos),
            "filter": {
                "included_tags": tag_list,
                "excluded_tags": exclude_list,
                "operator": operator,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tags/common/legacy2")
async def get_common_tags_legacy2(photo_paths: str, limit: int = 10):
    """Get common tags across multiple photos."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")

        path_list = [path.strip() for path in photo_paths.split(",")]

        # In a real implementation, we would find common tags across all these photos
        # For now, we'll just return an example implementation
        all_tags = []

        for path in path_list:
            tags = tag_filter_db.get_tags_for_photo(path)
            all_tags.extend(tags)

        # Count occurrences and return most frequent
        tag_counts = Counter(all_tags)
        common_tags = [tag for tag, count in tag_counts.most_common(limit)]

        return {"common_tags": common_tags, "count": len(common_tags)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tags/search/legacy2")
async def search_tags_legacy2(query: str, limit: int = 20):
    """Search for tags by name."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")
        matching_tags = tag_filter_db.search_tags(query, limit)

        return {"tags": matching_tags, "count": len(matching_tags)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tags/stats/legacy2")
async def get_tag_stats_legacy2():
    """Get statistics about tags in the system."""
    try:
        tag_filter_db = get_multi_tag_filter_db(settings.BASE_DIR / "tag_filters.db")

        # This would include stats about tag usage, most popular tags, etc.
        # In a full implementation, we'd return comprehensive statistics
        tag_counts = tag_filter_db.get_photo_tags_with_counts()

        return {
            "stats": {
                "total_tags": len(tag_counts),
                "top_tags": tag_counts[:10],  # Top 10 most used tags
                "total_tagged_photos": sum(tc["photo_count"] for tc in tag_counts),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
