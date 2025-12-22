import os

from fastapi import APIRouter, BackgroundTasks, Body, HTTPException, Depends
from fastapi.responses import FileResponse
from server.api.deps import get_state
from server.core.state import AppState


router = APIRouter()


@router.post("/bulk/export")
async def bulk_export(payload: dict = Body(...)):
    """
    Export multiple photos as a ZIP file.

    Body: {"file_paths": ["/path/to/file1.jpg", "/path/to/file2.jpg"], "format": "zip"}
    """
    file_paths = payload.get("file_paths", [])
    format_type = payload.get("format", "zip")

    if not file_paths:
        raise HTTPException(status_code=400, detail="file_paths is required")

    try:
        import zipfile
        import tempfile

        # Create temporary ZIP file
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_zip:
            zip_path = temp_zip.name

            with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file_path in file_paths:
                    if os.path.exists(file_path):
                        # Add file to ZIP with just the filename (not full path)
                        filename = os.path.basename(file_path)
                        zipf.write(file_path, filename)

        cleanup = BackgroundTasks()
        cleanup.add_task(os.unlink, zip_path)
        return FileResponse(
            path=zip_path,
            filename=f"photos_export_{len(file_paths)}_files.zip",
            media_type="application/zip",
            background=cleanup,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/bulk/delete")
async def bulk_delete(payload: dict = Body(...), state: AppState = Depends(get_state)):
    """
    Delete multiple photos.

    Body: {"file_paths": ["/path/to/file1.jpg", "/path/to/file2.jpg"], "confirm": true}
    """
    file_paths = payload.get("file_paths", [])
    confirm = payload.get("confirm", False)

    if not file_paths:
        raise HTTPException(status_code=400, detail="file_paths is required")

    if not confirm:
        raise HTTPException(status_code=400, detail="Deletion requires confirmation")

    try:

        deleted_count = 0
        errors = []

        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    # Remove from database
                    state.photo_search_engine.db.conn.execute(
                        "DELETE FROM metadata WHERE file_path = ?",
                        (file_path,),
                    )
                    state.photo_search_engine.db.conn.commit()
                    deleted_count += 1
                else:
                    errors.append(f"File not found: {file_path}")
            except Exception as e:
                errors.append(f"Failed to delete {file_path}: {str(e)}")

        return {
            "success": True,
            "deleted_count": deleted_count,
            "errors": errors,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk delete failed: {str(e)}")


@router.post("/bulk/favorite")
async def bulk_favorite(payload: dict = Body(...), state: AppState = Depends(get_state)):
    """
    Add/remove multiple photos to/from favorites.

    Body: {"file_paths": ["/path/to/file1.jpg", "/path/to/file2.jpg"], "action": "add|remove"}
    """
    file_paths = payload.get("file_paths", [])
    action = payload.get("action", "add")

    if not file_paths:
        raise HTTPException(status_code=400, detail="file_paths is required")

    if action not in ["add", "remove"]:
        raise HTTPException(status_code=400, detail="action must be 'add' or 'remove'")

    try:

        success_count = 0
        errors = []

        for file_path in file_paths:
            try:
                if action == "add":
                    state.photo_search_engine.add_favorite(file_path)
                else:
                    state.photo_search_engine.remove_favorite(file_path)
                success_count += 1
            except Exception as e:
                errors.append(f"Failed to {action} favorite {file_path}: {str(e)}")

        return {
            "success": True,
            "processed_count": success_count,
            "errors": errors,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk favorite {action} failed: {str(e)}")
