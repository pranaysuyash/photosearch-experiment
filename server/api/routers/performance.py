"""
Performance Monitoring API Router - Phase 7

Provides REST API endpoints for performance monitoring, optimization,
and system resource management.

Endpoints:
- Performance metrics and monitoring
- System optimization controls
- Resource usage statistics
- Cache management
- Database performance analysis

Features:
- Real-time performance monitoring
- Optimization recommendations
- Resource usage tracking
- Performance baseline measurement
- System health checks
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from server.config import settings
from server.api.deps import get_state
from server.core.state import AppState
from server.face_performance_optimizer import FacePerformanceOptimizer, OptimizationConfig

logger = logging.getLogger(__name__)

router = APIRouter()

# Request/Response Models


class OptimizationConfigRequest(BaseModel):
    """Request model for optimization configuration"""

    enable_caching: bool = Field(default=True, description="Enable intelligent caching")
    cache_size_mb: int = Field(default=512, description="Cache size in MB")
    max_concurrent_threads: int = Field(default=4, description="Maximum concurrent processing threads")
    batch_size: int = Field(default=32, description="Batch size for processing")
    memory_limit_mb: int = Field(default=2048, description="Memory limit in MB")
    enable_gpu_acceleration: bool = Field(default=True, description="Enable GPU acceleration if available")
    enable_query_optimization: bool = Field(default=True, description="Enable database query optimization")


class BatchProcessingRequest(BaseModel):
    """Request model for optimized batch processing"""

    image_paths: List[str] = Field(..., description="List of image paths to process")
    user_id: str = Field(default="default_user", description="User identifier")
    processing_options: Dict[str, Any] = Field(default_factory=dict, description="Additional processing options")


class PerformanceResponse(BaseModel):
    """Response model for performance operations"""

    status: str
    message: str
    data: Optional[Dict[str, Any]] = None


# Global performance optimizer instance
_performance_optimizer = None


def get_performance_optimizer(state: AppState = Depends(get_state)) -> FacePerformanceOptimizer:
    """Get or create performance optimizer instance"""
    global _performance_optimizer

    if _performance_optimizer is None:
        from server.privacy_controls import PrivacyControlsManager

        # Initialize privacy manager
        privacy_manager = PrivacyControlsManager(settings.FACE_CLUSTERS_DB_PATH)

        # Create optimizer with default config
        config = OptimizationConfig()
        _performance_optimizer = FacePerformanceOptimizer(
            face_clusterer=state.face_clusterer, privacy_manager=privacy_manager, config=config
        )

        # Run initial optimization
        _performance_optimizer.optimize_system()

    return _performance_optimizer


# System Optimization Endpoints


@router.post("/api/performance/optimize", response_model=PerformanceResponse)
async def optimize_system(
    config_request: OptimizationConfigRequest,
    background_tasks: BackgroundTasks,
    optimizer: FacePerformanceOptimizer = Depends(get_performance_optimizer),
):
    """
    Perform comprehensive system optimization.

    Applies database indexing, memory optimization, caching setup,
    and performance tuning based on provided configuration.
    """
    try:
        # Update optimizer configuration
        OptimizationConfig(
            enable_caching=config_request.enable_caching,
            cache_size_mb=config_request.cache_size_mb,
            max_concurrent_threads=config_request.max_concurrent_threads,
            batch_size=config_request.batch_size,
            memory_limit_mb=config_request.memory_limit_mb,
            enable_gpu_acceleration=config_request.enable_gpu_acceleration,
            enable_query_optimization=config_request.enable_query_optimization,
        )

        # Apply optimizations
        optimization_results = optimizer.optimize_system()

        return PerformanceResponse(
            status="success", message="System optimization completed successfully", data=optimization_results
        )

    except Exception as e:
        logger.error(f"System optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/performance/status")
async def get_performance_status(optimizer: FacePerformanceOptimizer = Depends(get_performance_optimizer)):
    """
    Get current system performance status and metrics.

    Returns real-time performance metrics, resource usage,
    and optimization status.
    """
    try:
        performance_report = optimizer.get_performance_report()

        return {"status": "success", "performance_report": performance_report, "timestamp": datetime.now().isoformat()}

    except Exception as e:
        logger.error(f"Performance status retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/performance/metrics")
async def get_performance_metrics(
    limit: int = 100, optimizer: FacePerformanceOptimizer = Depends(get_performance_optimizer)
):
    """
    Get detailed performance metrics history.

    Returns historical performance data for analysis and monitoring.
    """
    try:
        # Get recent metrics
        recent_metrics = optimizer.metrics[-limit:] if optimizer.metrics else []

        # Convert to serializable format
        metrics_data = []
        for metric in recent_metrics:
            metrics_data.append(
                {
                    "operation": metric.operation,
                    "timestamp": metric.start_time,
                    "duration": metric.duration,
                    "memory_usage_mb": metric.memory_after - metric.memory_before,
                    "items_processed": metric.items_processed,
                    "cache_hits": metric.cache_hits,
                    "cache_misses": metric.cache_misses,
                    "success": metric.success,
                    "error_message": metric.error_message,
                }
            )

        return {
            "status": "success",
            "metrics": metrics_data,
            "total_metrics": len(optimizer.metrics),
            "returned_metrics": len(metrics_data),
        }

    except Exception as e:
        logger.error(f"Performance metrics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Optimized Processing Endpoints


@router.post("/api/performance/process-batch")
async def process_batch_optimized(
    request: BatchProcessingRequest, optimizer: FacePerformanceOptimizer = Depends(get_performance_optimizer)
):
    """
    Process batch of images with all performance optimizations enabled.

    Uses intelligent caching, concurrent processing, memory management,
    and privacy controls for optimal performance.
    """
    try:
        # Validate image paths
        valid_paths = []
        for path in request.image_paths:
            if os.path.exists(path):
                valid_paths.append(path)
            else:
                logger.warning(f"Image path not found: {path}")

        if not valid_paths:
            raise HTTPException(status_code=400, detail="No valid image paths provided")

        # Process with optimizations
        results = optimizer.process_batch_optimized(
            image_paths=valid_paths, user_id=request.user_id, processing_options=request.processing_options
        )

        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Optimized batch processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Cache Management Endpoints


@router.get("/api/performance/cache/stats")
async def get_cache_statistics(optimizer: FacePerformanceOptimizer = Depends(get_performance_optimizer)):
    """Get intelligent cache statistics and performance metrics."""
    try:
        if not optimizer.cache:
            return {"status": "disabled", "message": "Intelligent caching is not enabled"}

        cache_stats = optimizer.cache.get_stats()

        return {
            "status": "enabled",
            "cache_statistics": cache_stats,
            "recommendations": _generate_cache_recommendations(cache_stats),
        }

    except Exception as e:
        logger.error(f"Cache statistics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/performance/cache/clear")
async def clear_cache(
    user_id: Optional[str] = None, optimizer: FacePerformanceOptimizer = Depends(get_performance_optimizer)
):
    """
    Clear intelligent cache.

    Can clear all cache or cache for specific user (privacy compliance).
    """
    try:
        if not optimizer.cache:
            raise HTTPException(status_code=400, detail="Caching is not enabled")

        if user_id:
            # Clear cache for specific user
            optimizer.cache.clear_user_data(user_id)
            message = f"Cache cleared for user {user_id}"
        else:
            # Clear all cache
            optimizer.cache.cache.clear()
            optimizer.cache.current_size = 0
            optimizer.cache.cache_stats = {"hits": 0, "misses": 0, "evictions": 0}
            message = "All cache cleared"

        return {"status": "success", "message": message, "cache_stats": optimizer.cache.get_stats()}

    except Exception as e:
        logger.error(f"Cache clearing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Memory Management Endpoints


@router.get("/api/performance/memory")
async def get_memory_usage(optimizer: FacePerformanceOptimizer = Depends(get_performance_optimizer)):
    """Get current memory usage statistics and trends."""
    try:
        memory_usage = optimizer.memory_manager.get_memory_usage()
        memory_trend = optimizer.memory_manager.get_memory_trend()

        return {
            "status": "success",
            "memory_usage": memory_usage,
            "memory_trend": memory_trend,
            "memory_limit_mb": optimizer.config.memory_limit_mb,
            "within_limits": optimizer.memory_manager.check_memory_limit(),
        }

    except Exception as e:
        logger.error(f"Memory usage retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/performance/memory/optimize")
async def optimize_memory(optimizer: FacePerformanceOptimizer = Depends(get_performance_optimizer)):
    """Perform memory optimization and garbage collection."""
    try:
        memory_before = optimizer.memory_manager.get_memory_usage()

        # Perform memory optimization
        optimizer.memory_manager.optimize_memory()

        memory_after = optimizer.memory_manager.get_memory_usage()

        memory_freed = memory_before["rss_mb"] - memory_after["rss_mb"]

        return {
            "status": "success",
            "message": "Memory optimization completed",
            "memory_before_mb": memory_before["rss_mb"],
            "memory_after_mb": memory_after["rss_mb"],
            "memory_freed_mb": memory_freed,
        }

    except Exception as e:
        logger.error(f"Memory optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Database Performance Endpoints


@router.get("/api/performance/database/analyze")
async def analyze_database_performance(
    query: Optional[str] = None, optimizer: FacePerformanceOptimizer = Depends(get_performance_optimizer)
):
    """Analyze database query performance and optimization status."""
    try:
        if not optimizer.db_optimizer:
            raise HTTPException(status_code=400, detail="Database optimizer not available")

        if query:
            # Analyze specific query
            analysis = optimizer.db_optimizer.analyze_query_performance(query)
            return {"status": "success", "query_analysis": analysis}
        else:
            # General database performance info
            return {
                "status": "success",
                "message": "Database performance analysis available",
                "optimization_status": optimizer.optimization_stats.get("database_optimized", False),
                "available_operations": [
                    "Query performance analysis",
                    "Index optimization",
                    "Database settings optimization",
                ],
            }

    except Exception as e:
        logger.error(f"Database performance analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/performance/database/optimize")
async def optimize_database(optimizer: FacePerformanceOptimizer = Depends(get_performance_optimizer)):
    """Optimize database indexes and settings for better performance."""
    try:
        if not optimizer.db_optimizer:
            raise HTTPException(status_code=400, detail="Database optimizer not available")

        # Optimize indexes
        index_results = optimizer.db_optimizer.optimize_indexes()

        # Optimize settings
        optimizer.db_optimizer.optimize_database_settings()

        # Update optimization status
        optimizer.optimization_stats["database_optimized"] = True

        return {
            "status": "success",
            "message": "Database optimization completed",
            "index_optimization": index_results,
            "settings_optimized": True,
        }

    except Exception as e:
        logger.error(f"Database optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# System Health Endpoints


@router.get("/api/performance/health")
async def get_system_health(optimizer: FacePerformanceOptimizer = Depends(get_performance_optimizer)):
    """Get comprehensive system health check."""
    try:
        # Memory health
        memory_usage = optimizer.memory_manager.get_memory_usage()
        memory_healthy = memory_usage["percent"] < 80

        # Cache health
        cache_healthy = True
        cache_stats = {}
        if optimizer.cache:
            cache_stats = optimizer.cache.get_stats()
            cache_healthy = cache_stats["hit_rate"] > 0.3  # At least 30% hit rate

        # Overall health
        overall_healthy = memory_healthy and cache_healthy

        health_status = {
            "overall_health": "healthy" if overall_healthy else "warning",
            "memory_health": {
                "status": "healthy" if memory_healthy else "warning",
                "usage_percent": memory_usage["percent"],
                "usage_mb": memory_usage["rss_mb"],
            },
            "cache_health": {
                "status": "healthy" if cache_healthy else "warning",
                "enabled": optimizer.cache is not None,
                "stats": cache_stats,
            },
            "optimization_status": optimizer.optimization_stats,
            "recommendations": optimizer._generate_performance_recommendations(),
        }

        return {"status": "success", "health_check": health_status, "timestamp": datetime.now().isoformat()}

    except Exception as e:
        logger.error(f"System health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/performance/cleanup")
async def cleanup_resources(optimizer: FacePerformanceOptimizer = Depends(get_performance_optimizer)):
    """Clean up system resources and optimize performance."""
    try:
        # Perform resource cleanup
        optimizer.cleanup_resources()

        # Get updated stats
        memory_usage = optimizer.memory_manager.get_memory_usage()
        cache_stats = optimizer.cache.get_stats() if optimizer.cache else {}

        return {
            "status": "success",
            "message": "Resource cleanup completed",
            "memory_usage": memory_usage,
            "cache_stats": cache_stats,
        }

    except Exception as e:
        logger.error(f"Resource cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper Functions


def _generate_cache_recommendations(cache_stats: Dict[str, Any]) -> List[str]:
    """Generate cache optimization recommendations"""
    recommendations = []

    if cache_stats.get("hit_rate", 0) < 0.5:
        recommendations.append("Cache hit rate is low - consider increasing cache size or adjusting cache strategy")

    if cache_stats.get("cache_size_mb", 0) > 400:  # Assuming 512MB default
        recommendations.append("Cache is nearly full - consider increasing cache size or clearing old entries")

    if cache_stats.get("evictions", 0) > cache_stats.get("hits", 1):
        recommendations.append("High eviction rate - cache size may be too small for workload")

    if not recommendations:
        recommendations.append("Cache performance is optimal")

    return recommendations
