from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends

from server.config import settings
from server.models.schemas.notes import NoteCreate
from server.notes_db import get_notes_db
from server.api.deps import get_state
from server.core.state import AppState


router = APIRouter()


@router.get("/api/photos/{file_path:path}/notes")
async def get_photo_notes(file_path: str):
    """Get notes for a photo."""
    try:
        notes_db = get_notes_db(settings.BASE_DIR / "notes.db")
        note_obj = notes_db.get_note_with_metadata(file_path) or {}
        return {"note": note_obj.get("note"), "updated_at": note_obj.get("updated_at")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/photos/{file_path:path}/notes")
async def set_photo_notes(file_path: str, note_req: NoteCreate):
    """Set notes for a photo."""
    try:
        notes_db = get_notes_db(settings.BASE_DIR / "notes.db")
        success = notes_db.set_note(file_path, note_req.note)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to set note")

        meta = notes_db.get_note_with_metadata(file_path) or {}
        return {"success": True, "note": meta.get("note"), "updated_at": meta.get("updated_at")}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/photos/{file_path:path}/notes")
async def delete_photo_notes(file_path: str):
    """Delete notes for a photo."""
    try:
        notes_db = get_notes_db(settings.BASE_DIR / "notes.db")
        success = notes_db.delete_note(file_path)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete note")

        return {"success": True, "note": None, "updated_at": None}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/notes/search")
async def search_notes(query: str, limit: int = 100, offset: int = 0, state: AppState = Depends(get_state)):
    """Search notes by content."""
    try:
        notes_db = get_notes_db(settings.BASE_DIR / "notes.db")
        results = notes_db.search_notes(query, limit, offset)

        # Get full metadata for each photo
        photos = []
        for row in results:
            note_path = row.get("photo_path")
            if not note_path:
                continue
            try:
                metadata = state.photo_search_engine.db.get_metadata(note_path)
                if metadata:
                    photos.append(
                        {
                            "path": note_path,
                            "filename": Path(note_path).name,
                            "metadata": metadata,
                        }
                    )
            except Exception:
                continue

        return {"photos": photos, "total": len(photos)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/notes/stats")
async def get_notes_stats(state: AppState = Depends(get_state)):
    """Get notes statistics."""
    try:
        notes_db = get_notes_db(settings.BASE_DIR / "notes.db")
        stats = notes_db.get_notes_stats()
        return {"stats": stats}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
