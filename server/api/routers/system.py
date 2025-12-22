from fastapi import APIRouter


router = APIRouter()


@router.get("/api/schema")
async def get_api_schema():
    """Get the API schema and version information."""
    from server import main as main_module

    schema = main_module.api_version_manager.get_api_schema()
    return schema


@router.get("/api/actions/detect-apps")
async def detect_installed_apps():
    """Return installed apps for action integrations (stub for web/dev)."""
    return {"apps": []}


@router.get("/api/cache/stats")
async def get_api_cache_stats():
    """Get cache statistics and performance metrics."""
    from server import main as main_module

    stats = main_module.cache_manager.stats()
    return stats


@router.post("/api/cache/clear")
async def clear_api_cache():
    """Clear all cache entries."""
    from server import main as main_module

    main_module.cache_manager.clear()
    return {"message": "Cache cleared successfully"}


@router.get("/api/cache/cleanup")
async def cleanup_cache():
    """Clean up expired cache entries."""
    from server import main as main_module

    removed_count = main_module.cache_manager.cleanup()
    return {"message": f"Cleaned up {removed_count} expired entries"}


@router.get("/api/logs/test")
async def test_logging():
    """Test endpoint to verify logging functionality."""
    import time
    from server import main as main_module

    start = time.time()

    # Log a test message
    main_module.ps_logger.info("Test log message from API endpoint")

    execution_time = (time.time() - start) * 1000

    # Log the operation
    main_module.log_search_operation(
        main_module.ps_logger,
        query="test",
        mode="test",
        results_count=0,
        execution_time=execution_time,
    )

    return {"message": "Test log message sent", "execution_time_ms": execution_time}
