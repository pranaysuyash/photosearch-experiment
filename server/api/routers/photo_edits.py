from fastapi import APIRouter, HTTPException

from server.config import settings
from server.models.schemas.edits import EditPayload
from server.photo_edits_db import get_photo_edits_db


router = APIRouter()


@router.get("/api/photos/{file_path:path}/edit")
async def get_photo_edit(file_path: str):
    try:
        edits_db = get_photo_edits_db(settings.BASE_DIR / "photo_edits.db")
        data = edits_db.get_edit(file_path) or {"edit_data": None}
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/photos/{file_path:path}/edit")
async def set_photo_edit(file_path: str, payload: EditPayload):
    try:
        edits_db = get_photo_edits_db(settings.BASE_DIR / "photo_edits.db")
        edits_db.set_edit(file_path, payload.edit_data)
        return {"success": True, "edit_data": payload.edit_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
