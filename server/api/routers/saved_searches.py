from fastapi import APIRouter, HTTPException

from server.models.schemas.saved_searches import SaveSearchRequest, UpdateSearchRequest


router = APIRouter()


@router.post("/searches/save")
async def save_search(request: SaveSearchRequest):
    """
    Save a search query for later reuse.

    Args:
        request: SaveSearchRequest with search details

    Returns:
        ID of the saved search
    """
    try:
        from server import main as main_module

        search_id = main_module.saved_search_manager.save_search(
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
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "updated_at",
    sort_order: str = "DESC",
    favorites_only: bool = False,
):
    """
    Get saved searches with pagination and filtering.

    Args:
        limit: Maximum number of results
        offset: Pagination offset
        sort_by: Field to sort by
        sort_order: Sort order (ASC or DESC)
        favorites_only: Only return favorite searches

    Returns:
        List of saved searches
    """
    try:
        from server import main as main_module

        searches = main_module.saved_search_manager.get_saved_searches(
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
async def get_saved_search(search_id: int):
    """
    Get a specific saved search by ID.

    Args:
        search_id: ID of the search

    Returns:
        Saved search details
    """
    try:
        from server import main as main_module

        search = main_module.saved_search_manager.get_saved_search_by_id(search_id)
        if not search:
            raise HTTPException(status_code=404, detail="Search not found")
        return search
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/searches/{search_id}/execute")
async def execute_saved_search(search_id: int):
    """
    Execute a saved search and log the execution.

    Args:
        search_id: ID of the saved search

    Returns:
        Search results and execution details
    """
    try:
        from server import main as main_module

        # Get the saved search
        search = main_module.saved_search_manager.get_saved_search_by_id(search_id)
        if not search:
            raise HTTPException(status_code=404, detail="Search not found")

        # Execute the search using the existing search endpoint
        results = await main_module.search_photos(
            query=search["query"],
            mode=search["mode"],
            limit=50,
            offset=0,
        )

        # Log the execution
        main_module.saved_search_manager.log_search_execution(
            search_id=search_id,
            results_count=results["count"],
            execution_time_ms=0,  # Would need to measure this in production
            user_agent="api",
            ip_address="localhost",
        )

        return {
            "search": search,
            "results": results,
            "message": "Search executed and logged",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/searches/{search_id}")
async def update_saved_search(search_id: int, request: UpdateSearchRequest):
    """
    Update a saved search (favorite status or notes).

    Args:
        search_id: ID of the search
        request: UpdateSearchRequest with fields to update

    Returns:
        Updated search details
    """
    try:
        from server import main as main_module

        search = main_module.saved_search_manager.get_saved_search_by_id(search_id)
        if not search:
            raise HTTPException(status_code=404, detail="Search not found")

        if request.is_favorite is not None:
            new_favorite_status = main_module.saved_search_manager.toggle_favorite(search_id)
            search["is_favorite"] = new_favorite_status

        if request.notes is not None:
            main_module.saved_search_manager.update_search_notes(search_id, request.notes)
            search["notes"] = request.notes

        return {"search": search, "message": "Search updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/searches/{search_id}")
async def delete_saved_search(search_id: int):
    """
    Delete a saved search.

    Args:
        search_id: ID of the search to delete

    Returns:
        Confirmation message
    """
    try:
        from server import main as main_module

        success = main_module.saved_search_manager.delete_saved_search(search_id)
        if not success:
            raise HTTPException(status_code=404, detail="Search not found")
        return {"message": "Search deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/searches/analytics")
async def get_search_analytics():
    """
    Get overall search analytics and insights.

    Returns:
        Analytics data including popular searches, recent searches, etc.
    """
    try:
        from server import main as main_module

        return main_module.saved_search_manager.get_overall_analytics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/searches/analytics/detailed")
async def get_detailed_analytics(days: int = 30):
    """
    Get detailed search analytics for a specific time period.

    Args:
        days: Number of days to analyze (default: 30)

    Returns:
        Detailed analytics data with trends and insights
    """
    try:
        from server import main as main_module

        return main_module.saved_search_manager.get_detailed_analytics(days=days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/searches/analytics/trends")
async def get_search_trends(days: int = 90):
    """
    Get search trends over time.

    Args:
        days: Number of days to calculate trends for (default: 90)

    Returns:
        Trend data showing search evolution over time
    """
    try:
        from server import main as main_module

        return main_module.saved_search_manager.get_search_trends(days=days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/searches/analytics/export")
async def export_analytics(format_type: str = "json", days: int = 30):
    """
    Export analytics data in various formats.

    Args:
        format_type: Output format ('json', 'csv', 'text') - default: json
        days: Number of days to include in analysis - default: 30

    Returns:
        Analytics data in specified format
    """
    try:
        if format_type not in ["json", "csv", "text"]:
            raise HTTPException(status_code=400, detail="Format must be 'json', 'csv', or 'text'")

        from server import main as main_module

        exported_data = main_module.saved_search_manager.export_analytics(
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
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "executed_at",
    sort_order: str = "DESC",
):
    """
    Get search history (all searches, not just saved ones).

    Args:
        limit: Maximum number of results
        offset: Pagination offset
        sort_by: Field to sort by
        sort_order: Sort order (ASC or DESC)

    Returns:
        Search history records
    """
    try:
        from server import main as main_module

        history = main_module.saved_search_manager.get_search_history(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return {"count": len(history), "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/searches/recurring")
async def get_recurring_searches(threshold: int = 2):
    """
    Get searches that have been executed multiple times.

    Args:
        threshold: Minimum number of executions to be considered recurring

    Returns:
        List of recurring searches
    """
    try:
        from server import main as main_module

        recurring = main_module.saved_search_manager.get_recurring_searches(threshold=threshold)
        return {"count": len(recurring), "recurring_searches": recurring}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/searches/performance")
async def get_search_performance():
    """
    Get performance metrics for searches.

    Returns:
        Performance data including average execution time, etc.
    """
    try:
        from server import main as main_module

        return main_module.saved_search_manager.get_search_performance()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/searches/history/clear")
async def clear_search_history():
    """
    Clear all search history (but keep saved searches).

    Returns:
        Number of records deleted
    """
    try:
        from server import main as main_module

        deleted_count = main_module.saved_search_manager.clear_search_history()
        return {"deleted_count": deleted_count, "message": "Search history cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
