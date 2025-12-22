from fastapi import APIRouter, Body, HTTPException, Depends
from server.api.deps import get_state
from server.core.state import AppState


router = APIRouter()


@router.post("/favorites/toggle")
async def toggle_favorite(payload: dict = Body(...), state: AppState = Depends(get_state)):
    """
    Toggle favorite status of a file.

    Body: {"file_path": "/path/to/file.jpg", "notes": "optional notes"}
    """
    file_path = payload.get("file_path")
    notes = payload.get("notes", "")

    if not file_path:
        raise HTTPException(status_code=400, detail="file_path is required")

    try:

        is_favorited = state.photo_search_engine.toggle_favorite(file_path, notes)
        return {"success": True, "is_favorited": is_favorited}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/favorites")
async def get_favorites(limit: int = 1000, offset: int = 0, state: AppState = Depends(get_state)):
    """
    Get all favorited files.
    """
    try:

        favorites = state.photo_search_engine.get_favorites(limit, offset)
        return {"count": len(favorites), "results": favorites}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/favorites/check")
async def check_favorite(file_path: str, state: AppState = Depends(get_state)):
    """
    Check if a file is favorited.

    Query param: file_path=/path/to/file.jpg
    """
    try:

        is_favorited = state.photo_search_engine.is_favorite(file_path)
        return {"is_favorited": is_favorited}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/favorites")
async def remove_favorite(payload: dict = Body(...), state: AppState = Depends(get_state)):
    """
    Remove a file from favorites.

    Body: {"file_path": "/path/to/file.jpg"}
    """
    file_path = payload.get("file_path")

    if not file_path:
        raise HTTPException(status_code=400, detail="file_path is required")

    try:

        success = state.photo_search_engine.remove_favorite(file_path)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
