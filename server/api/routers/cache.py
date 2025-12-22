from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException


router = APIRouter()


@router.get("/cache/stats")
async def get_cache_stats():
    """Get statistics about the caching system."""
    try:
        from src.cache_manager import cache_manager

        stats = cache_manager.get_stats()
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/clear")
async def clear_cache(cache_type: Optional[str] = None):
    """Clear cache entries."""
    try:
        from src.cache_manager import cache_manager

        cache_manager.clear_cache(cache_type)
        return {"success": True, "message": f"Cleared {cache_type or 'all'} cache"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/health")
async def cache_health_check():
    """Health check for cache system."""
    try:
        from src.cache_manager import cache_manager

        stats = cache_manager.get_stats()

        # Calculate cache hit rates if possible
        # For now, return basic health information
        health = {
            "status": "healthy",
            "caches": list(stats.keys()),
            "total_entries": sum(s["size"] for s in stats.values()),
            "timestamp": datetime.now().isoformat(),
        }

        return health
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
