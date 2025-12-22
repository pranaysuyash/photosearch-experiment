"""
Saved Searches Router

Uses Depends(get_state) for accessing shared application state.
"""
from fastapi import APIRouter, Depends, HTTPException

from server.models.schemas.saved_searches import SaveSearchRequest, UpdateSearchRequest
from server.api.deps import get_state
from server.core.state import AppState


router = APIRouter()


@router.post("/searches/save")
async def save_search(request: SaveSearchRequest, state: AppState = Depends(get_state)):
    """Save a search query for later reuse."""
    try:
        search_id = state.saved_search_manager.save_search(
            query=request.query,
            mode=request.mode,
            results_count=request.results_count,
            intent=request.intent,
            is_favorite=request.is_favorite,
            notes=request.notes,
            metadata=request.metadata,
        )
        return {"search_id": search_id, "message": "Search saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/searches")
async def get_saved_searches(
    state: AppState = Depends(get_state),
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "updated_at",
    sort_order: str = "DESC",
    favorites_only: bool = False,
):
    """Get saved searches with pagination and filtering."""
    try:
        searches = state.saved_search_manager.get_saved_searches(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
            filter_favorites=favorites_only,
        )
        return {"count": len(searches), "searches": searches}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/searches/{search_id}")
async def get_saved_search(search_id: int, state: AppState = Depends(get_state)):
    """Get a specific saved search by ID."""
    try:
        search = state.saved_search_manager.get_saved_search_by_id(search_id)
        if not search:
            raise HTTPException(status_code=404, detail="Search not found")
        return search
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/searches/{search_id}/execute")
async def execute_saved_search(search_id: int, state: AppState = Depends(get_state)):
    """Execute a saved search and log the execution."""
    try:
        # Get the saved search
        search = state.saved_search_manager.get_saved_search_by_id(search_id)
        if not search:
            raise HTTPException(status_code=404, detail="Search not found")

        # Execute search using photo_search_engine
        photo_search_engine = state.photo_search_engine
        if photo_search_engine:
            results = photo_search_engine.query_engine.search(search["query"])
            results_count = len(results) if results else 0
        else:
            results_count = 0

        # Log the execution
        state.saved_search_manager.log_search_execution(
            search_id=search_id,
            results_count=results_count,
            execution_time_ms=0,
            user_agent="api",
            ip_address="localhost",
        )

        return {
            "search": search,
            "results_count": results_count,
            "message": "Search executed and logged",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/searches/{search_id}")
async def update_saved_search(search_id: int, request: UpdateSearchRequest, state: AppState = Depends(get_state)):
    """Update a saved search (favorite status or notes)."""
    try:
        search = state.saved_search_manager.get_saved_search_by_id(search_id)
        if not search:
            raise HTTPException(status_code=404, detail="Search not found")

        if request.is_favorite is not None:
            new_favorite_status = state.saved_search_manager.toggle_favorite(search_id)
            search["is_favorite"] = new_favorite_status

        if request.notes is not None:
            state.saved_search_manager.update_search_notes(search_id, request.notes)
            search["notes"] = request.notes

        return {"search": search, "message": "Search updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/searches/{search_id}")
async def delete_saved_search(search_id: int, state: AppState = Depends(get_state)):
    """Delete a saved search."""
    try:
        success = state.saved_search_manager.delete_saved_search(search_id)
        if not success:
            raise HTTPException(status_code=404, detail="Search not found")
        return {"message": "Search deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/searches/analytics")
async def get_search_analytics(state: AppState = Depends(get_state)):
    """Get overall search analytics and insights."""
    try:
        return state.saved_search_manager.get_overall_analytics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/searches/analytics/detailed")
async def get_detailed_analytics(state: AppState = Depends(get_state), days: int = 30):
    """Get detailed search analytics for a specific time period."""
    try:
        return state.saved_search_manager.get_detailed_analytics(days=days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/searches/analytics/trends")
async def get_search_trends(state: AppState = Depends(get_state), days: int = 90):
    """Get search trends over time."""
    try:
        return state.saved_search_manager.get_search_trends(days=days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/searches/analytics/export")
async def export_analytics(state: AppState = Depends(get_state), format_type: str = "json", days: int = 30):
    """Export analytics data in various formats."""
    try:
        if format_type not in ["json", "csv", "text"]:
            raise HTTPException(status_code=400, detail="Format must be 'json', 'csv', or 'text'")

        exported_data = state.saved_search_manager.export_analytics(
            format_type=format_type,
            days=days,
        )

        if format_type == "json":
            import json
            return json.loads(exported_data)
        else:
            from fastapi.responses import PlainTextResponse
            return PlainTextResponse(exported_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/searches/history")
async def get_search_history(
    state: AppState = Depends(get_state),
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "executed_at",
    sort_order: str = "DESC",
):
    """Get search history (all searches, not just saved ones)."""
    try:
        history = state.saved_search_manager.get_search_history(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return {"count": len(history), "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/searches/recurring")
async def get_recurring_searches(state: AppState = Depends(get_state), threshold: int = 2):
    """Get searches that have been executed multiple times."""
    try:
        recurring = state.saved_search_manager.get_recurring_searches(threshold=threshold)
        return {"count": len(recurring), "recurring_searches": recurring}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/searches/performance")
async def get_search_performance(state: AppState = Depends(get_state)):
    """Get performance metrics for searches."""
    try:
        return state.saved_search_manager.get_search_performance()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/searches/history/clear")
async def clear_search_history(state: AppState = Depends(get_state)):
    """Clear all search history (but keep saved searches)."""
    try:
        deleted_count = state.saved_search_manager.clear_search_history()
        return {"deleted_count": deleted_count, "message": "Search history cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
