from fastapi import APIRouter, HTTPException

from server.config import settings
from server.models.schemas.versions import (
    LegacyVersionCreateRequest,
    LegacyVersionUpdateRequest,
    VersionCreateRequest,
    VersionUpdateRequest,
)
from server.photo_versions_db import get_photo_versions_db


router = APIRouter()


@router.post("/versions-legacy")
async def create_photo_version_legacy(request: LegacyVersionCreateRequest):
    """Create a new photo version record."""
    try:
        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")

        original_path = "/" + request.original_path.lstrip("/")
        version_path = "/" + request.version_path.lstrip("/")

        version_id = versions_db.create_version(
            original_path=original_path,
            version_path=version_path,
            version_type=request.version_type,
            version_name=request.version_name,
            version_description=request.version_description,
            edit_instructions=request.editing_instructions,
            parent_version_id=request.parent_version_id,
        )

        return {"success": True, "version_id": version_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/versions-legacy/original/{original_path:path}")
async def get_versions_for_original_legacy(original_path: str):
    """Get all versions for a given original photo."""
    try:
        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")
        normalized_path = "/" + original_path.lstrip("/")
        versions = versions_db.get_versions_for_original(normalized_path)
        return {"original_path": normalized_path, "versions": versions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/versions-legacy/stack/{version_path:path}")
async def get_version_stack_legacy(version_path: str):
    """Get the entire version stack for a given photo path."""
    try:
        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")
        normalized_path = "/" + version_path.lstrip("/")
        stack = versions_db.get_version_stack(normalized_path)
        return {"stack": stack.dict() if stack else None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/versions-legacy/{version_path:path}")
async def update_version_metadata_legacy(
    version_path: str, request: LegacyVersionUpdateRequest
):
    """Update metadata for a specific version."""
    try:
        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")
        normalized_path = "/" + version_path.lstrip("/")
        success = versions_db.update_version_metadata(
            normalized_path,
            version_name=request.version_name,
            version_description=request.version_description,
        )

        if not success:
            raise HTTPException(status_code=404, detail="Version not found")

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/versions-legacy/{version_id}")
async def delete_photo_version_legacy(version_id: str):
    """Delete a photo version record."""
    try:
        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")
        success = versions_db.delete_version(version_id)

        if not success:
            raise HTTPException(status_code=404, detail="Version not found")

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/versions-legacy/stats")
async def get_version_stats_legacy():
    """Get statistics about photo versions."""
    try:
        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")
        stats = versions_db.get_version_stats()
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/versions")
async def create_photo_version(request: VersionCreateRequest):
    """Create a new photo version record."""
    try:
        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")

        version_id = versions_db.create_version(
            original_path=request.original_path,
            version_path=request.version_path,
            version_type=request.version_type,
            version_name=request.version_name,
            version_description=request.version_description,
            edit_instructions=request.edit_instructions,
            parent_version_id=request.parent_version_id,
        )

        if not version_id:
            raise HTTPException(
                status_code=400, detail="Failed to create photo version"
            )

        return {"success": True, "version_id": version_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/versions/photo/{photo_path:path}")
async def get_photo_versions(photo_path: str):
    """Get all versions for a photo (original + all edits)."""
    try:
        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")
        version_stack = versions_db.get_version_stack_for_photo(photo_path)

        if not version_stack:
            # If no stack exists, return just the single photo
            return {"versions": [], "count": 0, "original_path": photo_path}

        return {
            "versions": [v.dict() for v in version_stack.versions],
            "count": len(version_stack.versions),
            "original_path": version_stack.original_path,
            "stack_id": version_stack.id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/versions/stack/{original_path:path}")
async def get_version_stack(original_path: str):
    """Get the complete version stack for an original photo."""
    try:
        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")
        version_stack = versions_db.get_version_stack_for_original(original_path)

        if not version_stack:
            raise HTTPException(
                status_code=404, detail="No version stack found for this photo"
            )

        versions = [v.dict() for v in version_stack.versions]
        return {
            # New shape
            "stack": {
                "id": version_stack.id,
                "original_path": version_stack.original_path,
                "version_count": version_stack.version_count,
                "created_at": version_stack.created_at,
                "updated_at": version_stack.updated_at,
                "versions": versions,
            },
            # Back-compat convenience fields expected by some tests/clients
            "original_path": version_stack.original_path,
            "versions": versions,
            "count": len(versions),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/versions/{version_path:path}")
async def update_version_metadata(version_path: str, request: VersionUpdateRequest):
    """Update metadata for a specific version."""
    try:
        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")

        success = versions_db.update_version_metadata(
            version_path=version_path,
            version_name=request.version_name,
            version_description=request.version_description,
        )

        if not success:
            raise HTTPException(status_code=404, detail="Version not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/versions/{version_id}")
async def delete_photo_version(version_id: str):
    """Delete a specific photo version (not the original)."""
    try:
        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")
        success = versions_db.delete_version(version_id)

        if not success:
            raise HTTPException(status_code=404, detail="Version not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/versions/stacks")
async def get_all_version_stacks(limit: int = 50, offset: int = 0):
    """Get all version stacks with pagination."""
    try:
        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")
        stacks = versions_db.get_all_stacks(limit, offset)

        return {
            "stacks": [s.dict() for s in stacks],
            "count": len(stacks),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/versions/stats")
async def get_version_stats():
    """Get statistics about photo versions."""
    try:
        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")
        stats = versions_db.get_version_stats()
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/versions/merge-stacks")
async def merge_version_stacks(payload: dict):
    """Merge two version stacks (when determining they're the same photo)."""
    try:
        path1 = payload.get("path1")
        path2 = payload.get("path2")

        if not path1 or not path2:
            raise HTTPException(
                status_code=400, detail="Both path1 and path2 are required"
            )

        versions_db = get_photo_versions_db(settings.BASE_DIR / "versions.db")
        success = versions_db.merge_version_stacks(path1, path2)

        if not success:
            raise HTTPException(
                status_code=400, detail="Failed to merge version stacks"
            )

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
