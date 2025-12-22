"""
System Router - API schema, cache, and logging endpoints.

Uses Depends(get_state) for accessing shared application state.
"""
import time

from fastapi import APIRouter, Depends

from server.api.deps import get_state
from server.core.state import AppState


router = APIRouter()


@router.get("/api/schema")
async def get_api_schema(state: AppState = Depends(get_state)):
    """Get the API schema and version information."""
    schema = state.api_version_manager.get_api_schema()
    return schema


@router.get("/api/actions/detect-apps")
async def detect_installed_apps():
    """Return installed apps for action integrations (stub for web/dev)."""
    return {"apps": []}


@router.get("/api/cache/stats")
async def get_api_cache_stats(state: AppState = Depends(get_state)):
    """Get cache statistics and performance metrics."""
    stats = state.cache_manager.stats()
    return stats


@router.post("/api/cache/clear")
async def clear_api_cache(state: AppState = Depends(get_state)):
    """Clear all cache entries."""
    state.cache_manager.clear()
    return {"message": "Cache cleared successfully"}


@router.get("/api/cache/cleanup")
async def cleanup_cache(state: AppState = Depends(get_state)):
    """Clean up expired cache entries."""
    removed_count = state.cache_manager.cleanup()
    return {"message": f"Cleaned up {removed_count} expired entries"}


@router.get("/api/logs/test")
async def test_logging(state: AppState = Depends(get_state)):
    """Test endpoint to verify logging functionality."""
    start = time.time()

    # Log a test message
    state.ps_logger.info("Test log message from API endpoint")

    execution_time = (time.time() - start) * 1000

    # Log the operation
    if state.log_search_operation:
        state.log_search_operation(
            state.ps_logger,
            query="test",
            mode="test",
            results_count=0,
            execution_time=execution_time,
        )

    return {"message": "Test log message sent", "execution_time_ms": execution_time}
