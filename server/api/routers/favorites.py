from fastapi import APIRouter, Body, HTTPException


router = APIRouter()


@router.post("/favorites/toggle")
async def toggle_favorite(payload: dict = Body(...)):
    """
    Toggle favorite status of a file.

    Body: {"file_path": "/path/to/file.jpg", "notes": "optional notes"}
    """
    file_path = payload.get("file_path")
    notes = payload.get("notes", "")

    if not file_path:
        raise HTTPException(status_code=400, detail="file_path is required")

    try:
        from server import main as main_module

        is_favorited = main_module.photo_search_engine.toggle_favorite(file_path, notes)
        return {"success": True, "is_favorited": is_favorited}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/favorites")
async def get_favorites(limit: int = 1000, offset: int = 0):
    """
    Get all favorited files.
    """
    try:
        from server import main as main_module

        favorites = main_module.photo_search_engine.get_favorites(limit, offset)
        return {"count": len(favorites), "results": favorites}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/favorites/check")
async def check_favorite(file_path: str):
    """
    Check if a file is favorited.

    Query param: file_path=/path/to/file.jpg
    """
    try:
        from server import main as main_module

        is_favorited = main_module.photo_search_engine.is_favorite(file_path)
        return {"is_favorited": is_favorited}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/favorites")
async def remove_favorite(payload: dict = Body(...)):
    """
    Remove a file from favorites.

    Body: {"file_path": "/path/to/file.jpg"}
    """
    file_path = payload.get("file_path")

    if not file_path:
        raise HTTPException(status_code=400, detail="file_path is required")

    try:
        from server import main as main_module

        success = main_module.photo_search_engine.remove_favorite(file_path)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
