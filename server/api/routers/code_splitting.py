from fastapi import APIRouter, HTTPException, Depends

from server.models.schemas.performance import CodeSplittingConfigRequest, PerformanceRecordRequest
from server.api.deps import get_state
from server.core.state import AppState


router = APIRouter()


@router.get("/code-splitting/config")
async def get_code_splitting_config(state: AppState = Depends(get_state)):
    """
    Get code splitting configuration

    Returns:
        Dictionary with code splitting configuration
    """
    try:
        config = state.code_splitting_config.get_config()
        return {"status": "success", "config": config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/code-splitting/chunk/{chunk_name}")
async def get_chunk_config(chunk_name: str, state: AppState = Depends(get_state)):
    """
    Get configuration for a specific chunk

    Args:
        chunk_name: Name of the chunk

    Returns:
        Dictionary with chunk configuration
    """
    try:
        config = state.code_splitting_config.get_chunk_config(chunk_name)
        if config:
            return {"status": "success", "config": config}
        else:
            raise HTTPException(status_code=404, detail="Chunk not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/code-splitting/chunk/{chunk_name}")
async def set_chunk_config(chunk_name: str, request: CodeSplittingConfigRequest, state: AppState = Depends(get_state)):
    """
    Set configuration for a specific chunk

    Args:
        chunk_name: Name of the chunk
        request: CodeSplittingConfigRequest with configuration

    Returns:
        Dictionary with update status
    """
    try:
        success = state.code_splitting_config.set_chunk_config(chunk_name, request.config)
        return {"status": "success" if success else "failed", "updated": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/code-splitting/enabled")
async def get_code_splitting_enabled(state: AppState = Depends(get_state)):
    """
    Check if code splitting is enabled

    Returns:
        Dictionary with enabled status
    """
    try:
        enabled = state.code_splitting_config.is_code_splitting_enabled()
        return {"status": "success", "enabled": enabled}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/code-splitting/enabled")
async def set_code_splitting_enabled(enabled: bool, state: AppState = Depends(get_state)):
    """
    Enable or disable code splitting

    Args:
        enabled: Boolean indicating whether to enable code splitting

    Returns:
        Dictionary with update status
    """
    try:
        state.code_splitting_config.enable_code_splitting(enabled)
        return {"status": "success", "enabled": enabled}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/code-splitting/performance")
async def record_lazy_load_performance(request: PerformanceRecordRequest, state: AppState = Depends(get_state)):
    """
    Record lazy load performance data

    Args:
        request: PerformanceRecordRequest with performance data

    Returns:
        Dictionary with recording status
    """
    try:
        state.lazy_load_tracker.record_lazy_load(
            component_name=request.component_name,
            load_time_ms=request.load_time_ms,
            chunk_name=request.chunk_name,
            success=True,
        )
        return {"status": "success", "recorded": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/code-splitting/performance")
async def get_lazy_load_performance(component_name: str | None = None, state: AppState = Depends(get_state)):
    """
    Get lazy load performance statistics

    Args:
        component_name: Optional component name to filter by

    Returns:
        Dictionary with performance statistics
    """
    try:
        stats = state.lazy_load_tracker.get_performance_stats(component_name)
        return {"status": "success", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/code-splitting/performance/chunks")
async def get_chunk_performance(state: AppState = Depends(get_state)):
    """
    Get performance statistics by chunk

    Returns:
        Dictionary with chunk performance statistics
    """
    try:
        stats = state.lazy_load_tracker.get_chunk_performance()
        return {"status": "success", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/code-splitting/integration-guide")
async def get_frontend_integration_guide():
    """
    Get frontend integration guide for code splitting

    Returns:
        Dictionary with integration guide
    """
    try:
        from src.code_splitting import get_frontend_integration_guide

        guide = get_frontend_integration_guide()
        return {"status": "success", "guide": guide}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/code-splitting/api-endpoints")
async def get_api_endpoints():
    """
    Get available API endpoints for code splitting

    Returns:
        Dictionary with API endpoints
    """
    try:
        from src.code_splitting import get_api_endpoints

        endpoints = get_api_endpoints()
        return {"status": "success", "endpoints": endpoints}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
