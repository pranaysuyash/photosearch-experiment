"""
Dialogs Router

Uses Depends(get_state) for accessing shared application state.
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from server.models.schemas.dialogs import (
    DialogActionRequest,
    DialogRequest,
    InputDialogRequest,
    ProgressDialogRequest,
)
from server.api.deps import get_state
from server.core.state import AppState


router = APIRouter()


@router.post("/dialogs/create")
async def create_dialog(request: DialogRequest, state: AppState = Depends(get_state)):
    """Create a new dialog."""
    try:
        create_kwargs: dict[str, Any] = {
            "dialog_type": request.dialog_type,
            "title": request.title,
            "message": request.message,
            "actions": request.options or [],
            "user_id": request.user_id,
        }
        if request.timeout is not None:
            create_kwargs["expires_in"] = int(request.timeout)

        dialog_id = state.modal_system.create_dialog(**create_kwargs)
        return {"status": "success", "dialog_id": dialog_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dialogs/active")
async def get_active_dialogs(state: AppState = Depends(get_state), user_id: str = "system"):
    """Get all active dialogs for a user."""
    try:
        dialogs = state.modal_system.get_active_dialogs(user_id)
        return {"status": "success", "dialogs": dialogs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dialogs/{dialog_id}")
async def get_dialog(dialog_id: str, state: AppState = Depends(get_state), user_id: str = "system"):
    """Get details for a specific dialog."""
    try:
        dialog = state.modal_system.get_dialog(dialog_id)
        if dialog and dialog.get("user_id") == user_id:
            return {"status": "success", "dialog": dialog}
        else:
            raise HTTPException(status_code=404, detail="Dialog not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dialogs/{dialog_id}/action")
async def dialog_action(dialog_id: str, request: DialogActionRequest, state: AppState = Depends(get_state)):
    """Record an action on a dialog."""
    try:
        success = state.modal_system.record_dialog_action(
            dialog_id,
            request.action,
            action_data={},
            user_id=request.user_id,
        )
        return {"status": "success" if success else "failed", "recorded": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dialogs/{dialog_id}/close")
async def close_dialog(dialog_id: str, request: DialogActionRequest, state: AppState = Depends(get_state)):
    """Close a dialog."""
    try:
        success = state.modal_system.close_dialog(
            dialog_id,
            request.action,
            request.user_id,
        )
        return {"status": "success" if success else "failed", "closed": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dialogs/{dialog_id}/dismiss")
async def dismiss_dialog(dialog_id: str, state: AppState = Depends(get_state), user_id: str = "system"):
    """Dismiss a dialog."""
    try:
        success = state.modal_system.dismiss_dialog(dialog_id, user_id)
        return {"status": "success" if success else "failed", "dismissed": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dialogs/confirmation")
async def create_confirmation_dialog(request: DialogRequest, state: AppState = Depends(get_state)):
    """Create a confirmation dialog."""
    try:
        create_kwargs: dict[str, Any] = {
            "dialog_type": "confirmation",
            "title": request.title,
            "message": request.message,
            "actions": request.options or ["Yes", "No"],
            "user_id": request.user_id,
            "context": "confirmation",
        }
        if request.timeout is not None:
            create_kwargs["expires_in"] = int(request.timeout)

        dialog_id = state.modal_system.create_dialog(**create_kwargs)
        return {"status": "success", "dialog_id": dialog_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dialogs/error")
async def create_error_dialog(request: DialogRequest, state: AppState = Depends(get_state)):
    """Create an error dialog."""
    try:
        create_kwargs: dict[str, Any] = {
            "dialog_type": "error",
            "title": request.title,
            "message": request.message,
            "data": {"details": ""},
            "user_id": request.user_id,
            "context": "error",
            "priority": 10,
        }
        if request.timeout is not None:
            create_kwargs["expires_in"] = int(request.timeout)

        dialog_id = state.modal_system.create_dialog(**create_kwargs)
        return {"status": "success", "dialog_id": dialog_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dialogs/progress")
async def create_progress_dialog(request: ProgressDialogRequest, state: AppState = Depends(get_state)):
    """Create a progress dialog."""
    try:
        dialog_id = state.modal_system.create_progress_dialog(
            title=request.title,
            message=request.message,
            total_steps=request.max_value,
            user_id=request.user_id,
        )
        # Best-effort initial progress update
        try:
            denom = float(request.max_value) if request.max_value else 100.0
            pct = (float(request.current_value) / denom) * 100.0
            state.modal_system.update_progress_dialog(dialog_id, progress=pct, message=request.message)
        except Exception:
            pass
        return {"status": "success", "dialog_id": dialog_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dialogs/progress/{dialog_id}")
async def update_progress_dialog(dialog_id: str, request: ProgressDialogRequest, state: AppState = Depends(get_state)):
    """Update a progress dialog."""
    try:
        denom = float(request.max_value) if request.max_value else 100.0
        pct = (float(request.current_value) / denom) * 100.0
        success = state.modal_system.update_progress_dialog(
            dialog_id,
            progress=pct,
            message=request.message,
        )
        return {"status": "success" if success else "failed", "updated": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dialogs/progress/{dialog_id}/complete")
async def complete_progress_dialog(dialog_id: str, state: AppState = Depends(get_state), user_id: str = "system"):
    """Complete a progress dialog."""
    try:
        success = state.modal_system.complete_progress_dialog(dialog_id, success=True)
        return {"status": "success" if success else "failed", "completed": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dialogs/input")
async def create_input_dialog(request: InputDialogRequest, state: AppState = Depends(get_state)):
    """Create an input dialog."""
    try:
        dialog_id = state.modal_system.create_dialog(
            dialog_type="input",
            title=request.title,
            message=request.message,
            data={"input_type": request.input_type, "default_value": request.default_value},
            user_id=request.user_id,
            context="input",
        )
        return {"status": "success", "dialog_id": dialog_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dialogs/history")
async def get_dialog_history(state: AppState = Depends(get_state), user_id: str = "system", limit: int = 50):
    """Get dialog history for a user."""
    try:
        history = state.modal_system.get_dialog_history(user_id=user_id, limit=limit)
        return {"status": "success", "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dialogs/stats")
async def get_dialog_stats(state: AppState = Depends(get_state)):
    """Get dialog statistics."""
    try:
        stats = state.modal_system.get_dialog_statistics()
        return {"status": "success", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
