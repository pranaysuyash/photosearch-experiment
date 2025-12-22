from fastapi import APIRouter, HTTPException

from server.config import settings
from server.models.schemas.smart_collections import (
    SmartCollectionCreateRequest,
    SmartCollectionUpdateRequest,
)
from server.smart_collections_db import get_smart_collections_db


router = APIRouter()


@router.post("/collections/smart")
async def create_smart_collection(request: SmartCollectionCreateRequest):
    """Create a new smart collection with auto-inclusion rules."""
    try:
        collections_db = get_smart_collections_db(settings.BASE_DIR / "collections.db")

        collection_id = collections_db.create_smart_collection(
            name=request.name,
            description=request.description,
            rule_definition=request.rule_definition,
            auto_update=request.auto_update,
            privacy_level=request.privacy_level,
        )

        if not collection_id:
            raise HTTPException(status_code=400, detail="Collection name already exists")

        return {"success": True, "collection_id": collection_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections/smart")
async def get_smart_collections(limit: int = 50, offset: int = 0):
    """Get all smart collections."""
    try:
        collections_db = get_smart_collections_db(settings.BASE_DIR / "collections.db")
        collections = collections_db.get_smart_collections(limit, offset)
        return {"collections": collections, "count": len(collections)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections/smart/{collection_id}")
async def get_smart_collection(collection_id: str):
    """Get a specific smart collection."""
    try:
        collections_db = get_smart_collections_db(settings.BASE_DIR / "collections.db")
        collection = collections_db.get_smart_collection(collection_id)

        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")

        return {"collection": collection}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/collections/smart/{collection_id}")
async def update_smart_collection(collection_id: str, request: SmartCollectionUpdateRequest):
    """Update a smart collection."""
    try:
        collections_db = get_smart_collections_db(settings.BASE_DIR / "collections.db")

        success = collections_db.update_smart_collection(
            collection_id=collection_id,
            name=request.name,
            description=request.description,
            rule_definition=request.rule_definition,
            auto_update=request.auto_update,
            privacy_level=request.privacy_level,
            is_favorite=request.is_favorite,
        )

        if not success:
            raise HTTPException(status_code=404, detail="Collection not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/collections/smart/{collection_id}")
async def delete_smart_collection(collection_id: str):
    """Delete a smart collection."""
    try:
        collections_db = get_smart_collections_db(settings.BASE_DIR / "collections.db")
        success = collections_db.delete_smart_collection(collection_id)

        if not success:
            raise HTTPException(status_code=404, detail="Collection not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections/smart/{collection_id}/photos")
async def get_photos_for_collection(collection_id: str):
    """Get photos that match the collection's rules."""
    try:
        collections_db = get_smart_collections_db(settings.BASE_DIR / "collections.db")
        photo_paths = collections_db.get_photos_for_collection(collection_id)

        # In a real implementation, we would get full photo metadata
        # For now, return just the paths
        return {"photos": photo_paths, "count": len(photo_paths)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections/smart/by-rule/{rule_type}")
async def get_collections_by_rule_type(rule_type: str):
    """Get collections that use a specific type of rule."""
    try:
        collections_db = get_smart_collections_db(settings.BASE_DIR / "collections.db")
        collections = collections_db.get_collections_by_rule_type(rule_type)
        return {"collections": collections, "count": len(collections)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections/smart/stats")
async def get_smart_collections_stats():
    """Get statistics about smart collections."""
    try:
        collections_db = get_smart_collections_db(settings.BASE_DIR / "collections.db")
        stats = collections_db.get_collections_stats()
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
