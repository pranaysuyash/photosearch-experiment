from typing import Optional

from fastapi import APIRouter, HTTPException

from server.bulk_actions_db import get_bulk_actions_db
from server.config import settings
from server.models.schemas.bulk_actions import BulkActionRequest


router = APIRouter()


@router.post("/bulk/action")
async def record_bulk_action(request: BulkActionRequest):
    """Record a bulk action that may need to be undone."""
    try:
        bulk_actions_db = get_bulk_actions_db(settings.BASE_DIR / "bulk_actions.db")

        action_id = bulk_actions_db.record_bulk_action(
            action_type=request.action_type,
            user_id="current_user_id",  # In a real app, this would come from authentication
            affected_paths=request.paths,
            operation_data=request.operation_data,
        )

        if not action_id:
            raise HTTPException(status_code=400, detail="Failed to record bulk action")

        return {"success": True, "action_id": action_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bulk/history/{user_id}")
async def get_bulk_action_history(
    user_id: str,
    action_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """Get bulk action history for a user."""
    try:
        bulk_db = get_bulk_actions_db(settings.BASE_DIR / "bulk_actions.db")
        actions = bulk_db.get_action_history(user_id, action_type, limit, offset)

        return {"actions": actions, "count": len(actions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk/undo/{action_id}")
async def undo_bulk_action(action_id: str):
    """Undo a recorded bulk action."""
    try:
        bulk_db = get_bulk_actions_db(settings.BASE_DIR / "bulk_actions.db")

        # Check if action can be undone
        if not bulk_db.can_undo_action(action_id):
            raise HTTPException(status_code=400, detail="Action cannot be undone")

        # For actual undo, we would need to implement the specific undo logic for each action type
        # This is a simplified implementation that just marks the action as undone
        success = bulk_db.mark_action_undone(action_id)

        if not success:
            raise HTTPException(status_code=400, detail="Failed to undo action")

        return {"success": True, "action_id": action_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bulk/can-undo/{action_id}")
async def can_undo_action(action_id: str):
    """Check if a bulk action can be undone."""
    try:
        bulk_db = get_bulk_actions_db(settings.BASE_DIR / "bulk_actions.db")
        can_undo = bulk_db.can_undo_action(action_id)

        return {"can_undo": can_undo}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bulk/stats/{user_id}")
async def get_bulk_actions_stats(user_id: str):
    """Get statistics about bulk actions for a user."""
    try:
        bulk_db = get_bulk_actions_db(settings.BASE_DIR / "bulk_actions.db")

        recent_actions = bulk_db.get_recent_actions(user_id, minutes=60)  # Last hour
        undone_count = bulk_db.get_undone_actions_count(user_id)

        # Count actions by type
        type_counts: dict[str, int] = {}
        for action in recent_actions:
            action_type = action.action_type
            type_counts[action_type] = type_counts.get(action_type, 0) + 1

        return {
            "stats": {
                "recent_actions": len(recent_actions),
                "undone_actions": undone_count,
                "actions_by_type": type_counts,
                "recent_period_minutes": 60,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
