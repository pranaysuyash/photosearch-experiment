from fastapi import APIRouter, HTTPException

from server.config import settings
from server.models.schemas.edits import EditData
from server.photo_edits_db import get_photo_edits_db


router = APIRouter()


@router.get("/api/photos/{file_path:path}/edits")
async def get_photo_edits(file_path: str):
    """Get edit instructions for a photo."""
    try:
        edits_db = get_photo_edits_db(settings.BASE_DIR / "edits.db")
        edit_data = edits_db.get_edit(file_path)
        return {"edit_data": edit_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/photos/{file_path:path}/edits")
async def set_photo_edits(file_path: str, edit_data: EditData):
    """Save edit instructions for a photo."""
    try:
        edits_db = get_photo_edits_db(settings.BASE_DIR / "edits.db")
        edits_db.set_edit(file_path, edit_data.dict())

        return {"success": True, "edit_data": edit_data.dict()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/photos/{file_path:path}/edits")
async def delete_photo_edits(file_path: str):
    """Delete edit instructions for a photo."""
    try:
        # To delete, we'll set the edit data to empty
        edits_db = get_photo_edits_db(settings.BASE_DIR / "edits.db")
        edits_db.set_edit(file_path, {})

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
