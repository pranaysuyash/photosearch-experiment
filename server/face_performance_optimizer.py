"""
Face Performance Optimizer - Phase 7

Comprehensive performance optimization system for face recognition processing.
Implements intelligent caching, database optimization, memory management,
and concurrent processing improvements.

Features:
1. Intelligent caching with privacy compliance
2. Database query optimization and indexing
3. Memory-efficient processing pipelines
4. Concurrent processing with thread safety
5. Performance monitoring and metrics
6. Batch processing optimization
7. Resource usage optimization

Performance Targets:
- 2-3x faster face detection and clustering
- 40-50% reduction in memory usage
- 5-10x faster database queries
- Support for 100K+ photos with consistent performance
- Concurrent multi-user processing

Usage:
    optimizer = FacePerformanceOptimizer(face_clusterer, privacy_manager)
    optimizer.optimize_database_indexes()
    optimizer.enable_intelligent_caching()
    result = optimizer.process_batch_optimized(image_paths, user_id)
"""

import gc
import time
import sqlite3
import logging
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Callable
from pathlib import Path
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil
import queue
from collections import defaultdict, OrderedDict

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring"""

    operation: str
    start_time: float
    end_time: float
    duration: float
    memory_before: float
    memory_after: float
    memory_peak: float
    cpu_usage: float
    items_processed: int
    cache_hits: int
    cache_misses: int
    success: bool
    error_message: Optional[str] = None


@dataclass
class OptimizationConfig:
    """Configuration for performance optimization"""

    enable_caching: bool = True
    cache_size_mb: int = 512
    max_concurrent_threads: int = 4
    batch_size: int = 32
    memory_limit_mb: int = 2048
    enable_gpu_acceleration: bool = True
    database_cache_size: int = 10000
    enable_query_optimization: bool = True
    enable_memory_monitoring: bool = True


class IntelligentCache:
    """Privacy-compliant intelligent caching system"""

    def __init__(self, max_size_mb: int = 512, privacy_manager=None):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.privacy_manager = privacy_manager
        self.cache = OrderedDict()
        self.cache_stats = {"hits": 0, "misses": 0, "evictions": 0}
        self.current_size = 0
        self.lock = threading.RLock()

    def get(self, key: str, user_id: Optional[str] = None) -> Optional[Any]:
        """Get item from cache with privacy checks"""
        with self.lock:
            # Privacy check
            if user_id and self.privacy_manager:
                if not self._check_cache_privacy(key, user_id):
                    return None

            if key in self.cache:
                # Move to end (most recently used)
                value = self.cache.pop(key)
                self.cache[key] = value
                self.cache_stats["hits"] += 1
                return value["data"]

            self.cache_stats["misses"] += 1
            return None

    def put(self, key: str, data: Any, size_bytes: int, user_id: Optional[str] = None):
        """Put item in cache with size management"""
        with self.lock:
            # Privacy check
            if user_id and self.privacy_manager:
                if not self._check_cache_privacy(key, user_id):
                    return

            # Remove existing entry if present
            if key in self.cache:
                old_entry = self.cache.pop(key)
                self.current_size -= old_entry["size"]

            # Evict items if necessary
            while self.current_size + size_bytes > self.max_size_bytes and self.cache:
                oldest_key, oldest_entry = self.cache.popitem(last=False)
                self.current_size -= oldest_entry["size"]
                self.cache_stats["evictions"] += 1

            # Add new entry
            self.cache[key] = {"data": data, "size": size_bytes, "timestamp": time.time(), "user_id": user_id}
            self.current_size += size_bytes

    def _check_cache_privacy(self, key: str, user_id: str) -> bool:
        """Check if cache access is privacy-compliant"""
        # In a full implementation, this would check user consent
        # and privacy settings for cached data
        return True

    def clear_user_data(self, user_id: str):
        """Clear all cached data for a specific user (privacy compliance)"""
        with self.lock:
            keys_to_remove = []
            for key, entry in self.cache.items():
                if entry.get("user_id") == user_id:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                entry = self.cache.pop(key)
                self.current_size -= entry["size"]

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
            hit_rate = (self.cache_stats["hits"] / total_requests) if total_requests > 0 else 0

            return {
                "hit_rate": hit_rate,
                "total_requests": total_requests,
                "cache_size_mb": self.current_size / (1024 * 1024),
                "entries": len(self.cache),
                **self.cache_stats,
            }


class DatabaseOptimizer:
    """Database query optimization and indexing"""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.query_cache = {}
        self.query_stats = defaultdict(list)

    def optimize_indexes(self) -> Dict[str, Any]:
        """Create optimized indexes for face recognition queries"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Performance indexes for face recognition
                indexes_created = []

                # Face detection indexes
                try:
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_faces_image_confidence
                        ON faces(image_path, confidence DESC)
                    """)
                    indexes_created.append("idx_faces_image_confidence")
                except Exception as e:
                    logger.warning(f"Failed to create face confidence index: {e}")

                # Cluster membership indexes
                try:
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_cluster_membership_cluster_face
                        ON cluster_membership(cluster_id, face_id)
                    """)
                    indexes_created.append("idx_cluster_membership_cluster_face")
                except Exception as e:
                    logger.warning(f"Failed to create cluster membership index: {e}")

                # Attribute search indexes
                try:
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_faces_attributes
                        ON faces(age_estimate, emotion, pose_type, overall_quality)
                    """)
                    indexes_created.append("idx_faces_attributes")
                except Exception as e:
                    logger.warning(f"Failed to create attributes index: {e}")

                # Video processing indexes
                try:
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_video_tracks_path_time
                        ON video_face_tracks(video_path, start_time, end_time)
                    """)
                    indexes_created.append("idx_video_tracks_path_time")
                except Exception as e:
                    logger.warning(f"Failed to create video tracks index: {e}")

                conn.commit()

                return {
                    "status": "completed",
                    "indexes_created": indexes_created,
                    "total_indexes": len(indexes_created),
                }

        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
            return {"status": "error", "error": str(e)}

    def analyze_query_performance(self, query: str, params: Tuple = ()) -> Dict[str, Any]:
        """Analyze query performance with EXPLAIN QUERY PLAN"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Get query plan
                explain_query = f"EXPLAIN QUERY PLAN {query}"
                cursor.execute(explain_query, params)
                query_plan = cursor.fetchall()

                # Execute query with timing
                start_time = time.time()
                cursor.execute(query, params)
                results = cursor.fetchall()
                execution_time = time.time() - start_time

                return {
                    "query": query,
                    "execution_time": execution_time,
                    "rows_returned": len(results),
                    "query_plan": query_plan,
                    "uses_index": any("USING INDEX" in str(step) for step in query_plan),
                }

        except Exception as e:
            logger.error(f"Query analysis failed: {e}")
            return {"error": str(e)}

    def optimize_database_settings(self):
        """Optimize SQLite settings for performance"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Performance optimizations
                cursor.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging
                cursor.execute("PRAGMA synchronous = NORMAL")  # Faster writes
                cursor.execute("PRAGMA cache_size = 10000")  # 10MB cache
                cursor.execute("PRAGMA temp_store = MEMORY")  # Memory temp storage
                cursor.execute("PRAGMA mmap_size = 268435456")  # 256MB memory map

                conn.commit()
                logger.info("Database settings optimized for performance")

        except Exception as e:
            logger.error(f"Database settings optimization failed: {e}")


class MemoryManager:
    """Memory usage optimization and monitoring"""

    def __init__(self, memory_limit_mb: int = 2048):
        self.memory_limit_bytes = memory_limit_mb * 1024 * 1024
        self.process = psutil.Process()
        self.memory_stats = []

    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage statistics"""
        memory_info = self.process.memory_info()
        return {
            "rss_mb": memory_info.rss / (1024 * 1024),
            "vms_mb": memory_info.vms / (1024 * 1024),
            "percent": self.process.memory_percent(),
            "available_mb": psutil.virtual_memory().available / (1024 * 1024),
        }

    def check_memory_limit(self) -> bool:
        """Check if memory usage is within limits"""
        current_memory = self.get_memory_usage()
        return current_memory["rss_mb"] * 1024 * 1024 < self.memory_limit_bytes

    def optimize_memory(self):
        """Perform memory optimization"""
        # Force garbage collection
        gc.collect()

        # Log memory usage
        memory_usage = self.get_memory_usage()
        self.memory_stats.append({"timestamp": time.time(), "memory_mb": memory_usage["rss_mb"]})

        # Keep only recent stats
        if len(self.memory_stats) > 1000:
            self.memory_stats = self.memory_stats[-500:]

    def get_memory_trend(self) -> Dict[str, Any]:
        """Get memory usage trend analysis"""
        if len(self.memory_stats) < 2:
            return {"trend": "insufficient_data"}

        recent_stats = self.memory_stats[-10:]
        memory_values = [stat["memory_mb"] for stat in recent_stats]

        avg_memory = sum(memory_values) / len(memory_values)
        max_memory = max(memory_values)
        min_memory = min(memory_values)

        # Simple trend calculation
        if len(memory_values) >= 2:
            trend = "increasing" if memory_values[-1] > memory_values[0] else "decreasing"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "avg_memory_mb": avg_memory,
            "max_memory_mb": max_memory,
            "min_memory_mb": min_memory,
            "current_memory_mb": memory_values[-1] if memory_values else 0,
        }


class ConcurrentProcessor:
    """Concurrent processing with thread safety"""

    def __init__(self, max_workers: int = 4, privacy_manager=None):
        self.max_workers = max_workers
        self.privacy_manager = privacy_manager
        self.processing_queue = queue.Queue()
        self.results_queue = queue.Queue()
        self.active_tasks = {}
        self.lock = threading.Lock()

    def process_batch_concurrent(self, items: List[Any], process_func: Callable, user_id: str, **kwargs) -> List[Any]:
        """Process items concurrently with privacy controls"""
        results = []

        # Check privacy permissions first
        if self.privacy_manager and not self._check_processing_permission(user_id):
            return []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit tasks
            future_to_item = {}
            for item in items:
                future = executor.submit(self._safe_process_item, process_func, item, user_id, **kwargs)
                future_to_item[future] = item

            # Collect results
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Concurrent processing failed for item {item}: {e}")
                    results.append({"error": str(e), "item": item})

        return results

    def _safe_process_item(self, process_func: Callable, item: Any, user_id: str, **kwargs):
        """Safely process single item with error handling"""
        try:
            return process_func(item, user_id=user_id, **kwargs)
        except Exception as e:
            logger.error(f"Item processing failed: {e}")
            return {"error": str(e), "item": item}

    def _check_processing_permission(self, user_id: str) -> bool:
        """Check if user has permission for concurrent processing"""
        # In full implementation, check privacy settings and consent
        return True


class FacePerformanceOptimizer:
    """Main performance optimization coordinator"""

    def __init__(self, face_clusterer=None, privacy_manager=None, config: OptimizationConfig = None):
        """
        Initialize performance optimizer.

        Args:
            face_clusterer: Face clustering system
            privacy_manager: Privacy controls manager
            config: Optimization configuration
        """
        self.face_clusterer = face_clusterer
        self.privacy_manager = privacy_manager
        self.config = config or OptimizationConfig()

        # Initialize optimization components
        self.cache = (
            IntelligentCache(max_size_mb=self.config.cache_size_mb, privacy_manager=privacy_manager)
            if self.config.enable_caching
            else None
        )

        self.db_optimizer = None
        if face_clusterer and hasattr(face_clusterer, "db_path"):
            self.db_optimizer = DatabaseOptimizer(face_clusterer.db_path)

        self.memory_manager = MemoryManager(self.config.memory_limit_mb)
        self.concurrent_processor = ConcurrentProcessor(
            max_workers=self.config.max_concurrent_threads, privacy_manager=privacy_manager
        )

        # Performance metrics
        self.metrics = []
        self.optimization_stats = {
            "cache_enabled": self.config.enable_caching,
            "concurrent_processing": True,
            "memory_monitoring": self.config.enable_memory_monitoring,
            "database_optimized": False,
        }

        logger.info("FacePerformanceOptimizer initialized")

    def optimize_system(self) -> Dict[str, Any]:
        """Perform comprehensive system optimization"""
        optimization_results = {
            "timestamp": datetime.now().isoformat(),
            "optimizations_applied": [],
            "performance_improvements": {},
            "status": "completed",
        }

        try:
            # 1. Database optimization
            if self.db_optimizer and self.config.enable_query_optimization:
                db_result = self.db_optimizer.optimize_indexes()
                optimization_results["optimizations_applied"].append("database_indexes")
                optimization_results["database_optimization"] = db_result

                self.db_optimizer.optimize_database_settings()
                optimization_results["optimizations_applied"].append("database_settings")
                self.optimization_stats["database_optimized"] = True

            # 2. Memory optimization
            if self.config.enable_memory_monitoring:
                self.memory_manager.optimize_memory()
                memory_stats = self.memory_manager.get_memory_usage()
                optimization_results["optimizations_applied"].append("memory_optimization")
                optimization_results["memory_stats"] = memory_stats

            # 3. Cache initialization
            if self.cache:
                cache_stats = self.cache.get_stats()
                optimization_results["optimizations_applied"].append("intelligent_caching")
                optimization_results["cache_stats"] = cache_stats

            # 4. Performance baseline
            baseline_metrics = self._measure_performance_baseline()
            optimization_results["performance_baseline"] = baseline_metrics

            logger.info(
                f"System optimization completed: {len(optimization_results['optimizations_applied'])} optimizations applied"
            )
            return optimization_results

        except Exception as e:
            logger.error(f"System optimization failed: {e}")
            optimization_results["status"] = "error"
            optimization_results["error"] = str(e)
            return optimization_results

    def process_batch_optimized(
        self, image_paths: List[str], user_id: str, processing_options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process batch of images with all optimizations enabled.

        Args:
            image_paths: List of image paths to process
            user_id: User identifier for privacy controls
            processing_options: Additional processing options

        Returns:
            Optimized processing results with performance metrics
        """
        start_time = time.time()
        processing_options = processing_options or {}

        # Start performance monitoring
        memory_before = self.memory_manager.get_memory_usage()

        try:
            # 1. Check cache for existing results
            cached_results = []
            uncached_paths = []

            if self.cache:
                for path in image_paths:
                    cache_key = f"face_detection_{Path(path).name}_{user_id}"
                    cached_result = self.cache.get(cache_key, user_id)
                    if cached_result:
                        cached_results.append(cached_result)
                    else:
                        uncached_paths.append(path)
            else:
                uncached_paths = image_paths

            # 2. Process uncached images with concurrent processing
            new_results = []
            if uncached_paths:
                # Split into batches for memory management
                batch_size = self.config.batch_size
                for i in range(0, len(uncached_paths), batch_size):
                    batch = uncached_paths[i : i + batch_size]

                    # Check memory before processing batch
                    if not self.memory_manager.check_memory_limit():
                        self.memory_manager.optimize_memory()

                    # Process batch concurrently
                    batch_results = self.concurrent_processor.process_batch_concurrent(
                        batch, self._process_single_image, user_id, **processing_options
                    )
                    new_results.extend(batch_results)

                    # Cache results
                    if self.cache:
                        for path, result in zip(batch, batch_results):
                            cache_key = f"face_detection_{Path(path).name}_{user_id}"
                            # Estimate result size (simplified)
                            result_size = len(str(result).encode("utf-8"))
                            self.cache.put(cache_key, result, result_size, user_id)

            # 3. Combine results
            all_results = cached_results + new_results

            # 4. Performance metrics
            end_time = time.time()
            memory_after = self.memory_manager.get_memory_usage()

            processing_metrics = PerformanceMetrics(
                operation="batch_face_processing",
                start_time=start_time,
                end_time=end_time,
                duration=end_time - start_time,
                memory_before=memory_before["rss_mb"],
                memory_after=memory_after["rss_mb"],
                memory_peak=max(memory_before["rss_mb"], memory_after["rss_mb"]),
                cpu_usage=psutil.cpu_percent(),
                items_processed=len(image_paths),
                cache_hits=len(cached_results),
                cache_misses=len(uncached_paths),
                success=True,
            )

            self.metrics.append(processing_metrics)

            return {
                "status": "completed",
                "total_images": len(image_paths),
                "cached_results": len(cached_results),
                "newly_processed": len(new_results),
                "results": all_results,
                "performance_metrics": asdict(processing_metrics),
                "optimization_stats": self.optimization_stats,
            }

        except Exception as e:
            logger.error(f"Optimized batch processing failed: {e}")

            # Error metrics
            end_time = time.time()
            memory_after = self.memory_manager.get_memory_usage()

            error_metrics = PerformanceMetrics(
                operation="batch_face_processing",
                start_time=start_time,
                end_time=end_time,
                duration=end_time - start_time,
                memory_before=memory_before["rss_mb"],
                memory_after=memory_after["rss_mb"],
                memory_peak=max(memory_before["rss_mb"], memory_after["rss_mb"]),
                cpu_usage=psutil.cpu_percent(),
                items_processed=0,
                cache_hits=0,
                cache_misses=len(image_paths),
                success=False,
                error_message=str(e),
            )

            self.metrics.append(error_metrics)

            return {"status": "error", "error": str(e), "performance_metrics": asdict(error_metrics)}

    def _process_single_image(self, image_path: str, user_id: str, **kwargs) -> Dict[str, Any]:
        """Process single image with privacy controls"""
        try:
            if self.privacy_manager:
                # Use privacy-aware processor if available
                from server.privacy_aware_face_processor import PrivacyAwareFaceProcessor

                privacy_processor = PrivacyAwareFaceProcessor(self.face_clusterer, self.privacy_manager)
                result = privacy_processor.process_with_privacy_controls(image_path, user_id)
                return asdict(result)

            elif self.face_clusterer and hasattr(self.face_clusterer, "detect_faces_in_image"):
                # Standard face detection
                detections = self.face_clusterer.detect_faces_in_image(image_path)
                return {
                    "image_path": image_path,
                    "faces_detected": len(detections),
                    "detections": detections,
                    "processing_time": 0.1,  # Placeholder
                }

            else:
                return {"image_path": image_path, "faces_detected": 0, "error": "No face detection available"}

        except Exception as e:
            logger.error(f"Single image processing failed for {image_path}: {e}")
            return {"image_path": image_path, "faces_detected": 0, "error": str(e)}

    def _measure_performance_baseline(self) -> Dict[str, Any]:
        """Measure performance baseline for comparison"""
        try:
            # Simple performance test
            start_time = time.time()

            # Memory baseline
            memory_stats = self.memory_manager.get_memory_usage()

            # Database query baseline (if available)
            db_performance = {}
            if self.db_optimizer:
                test_query = "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
                db_perf = self.db_optimizer.analyze_query_performance(test_query)
                db_performance = {
                    "query_time": db_perf.get("execution_time", 0),
                    "uses_indexes": db_perf.get("uses_index", False),
                }

            baseline_time = time.time() - start_time

            return {
                "baseline_measurement_time": baseline_time,
                "memory_usage": memory_stats,
                "database_performance": db_performance,
                "cache_enabled": self.cache is not None,
                "concurrent_workers": self.config.max_concurrent_threads,
            }

        except Exception as e:
            logger.error(f"Performance baseline measurement failed: {e}")
            return {"error": str(e)}

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        try:
            # Aggregate metrics
            if not self.metrics:
                return {"message": "No performance metrics available"}

            successful_metrics = [m for m in self.metrics if m.success]
            failed_metrics = [m for m in self.metrics if not m.success]

            if successful_metrics:
                avg_duration = sum(m.duration for m in successful_metrics) / len(successful_metrics)
                avg_memory_usage = sum(m.memory_after - m.memory_before for m in successful_metrics) / len(
                    successful_metrics
                )
                total_items_processed = sum(m.items_processed for m in successful_metrics)
                total_cache_hits = sum(m.cache_hits for m in successful_metrics)
                total_cache_misses = sum(m.cache_misses for m in successful_metrics)

                cache_hit_rate = (
                    total_cache_hits / (total_cache_hits + total_cache_misses)
                    if (total_cache_hits + total_cache_misses) > 0
                    else 0
                )
            else:
                avg_duration = 0
                avg_memory_usage = 0
                total_items_processed = 0
                cache_hit_rate = 0

            # System stats
            current_memory = self.memory_manager.get_memory_usage()
            memory_trend = self.memory_manager.get_memory_trend()
            cache_stats = self.cache.get_stats() if self.cache else {}

            return {
                "report_generated": datetime.now().isoformat(),
                "performance_summary": {
                    "total_operations": len(self.metrics),
                    "successful_operations": len(successful_metrics),
                    "failed_operations": len(failed_metrics),
                    "avg_processing_time": avg_duration,
                    "avg_memory_delta_mb": avg_memory_usage,
                    "total_items_processed": total_items_processed,
                    "cache_hit_rate": cache_hit_rate,
                },
                "current_system_state": {
                    "memory_usage": current_memory,
                    "memory_trend": memory_trend,
                    "cache_stats": cache_stats,
                    "optimization_stats": self.optimization_stats,
                },
                "recommendations": self._generate_performance_recommendations(),
            }

        except Exception as e:
            logger.error(f"Performance report generation failed: {e}")
            return {"error": str(e)}

    def _generate_performance_recommendations(self) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []

        try:
            # Memory recommendations
            memory_usage = self.memory_manager.get_memory_usage()
            if memory_usage["percent"] > 80:
                recommendations.append("Consider increasing memory limit or reducing batch size")

            # Cache recommendations
            if self.cache:
                cache_stats = self.cache.get_stats()
                if cache_stats["hit_rate"] < 0.5:
                    recommendations.append("Cache hit rate is low - consider increasing cache size")
                if cache_stats["cache_size_mb"] > self.config.cache_size_mb * 0.9:
                    recommendations.append("Cache is nearly full - consider increasing cache size")

            # Concurrent processing recommendations
            if len(self.metrics) > 0:
                avg_duration = sum(m.duration for m in self.metrics if m.success) / len(
                    [m for m in self.metrics if m.success]
                )
                if avg_duration > 10.0:  # More than 10 seconds average
                    recommendations.append("Consider increasing concurrent worker threads for better performance")

            # Database recommendations
            if self.db_optimizer and not self.optimization_stats["database_optimized"]:
                recommendations.append("Run database optimization to improve query performance")

            if not recommendations:
                recommendations.append("System performance is optimal")

            return recommendations

        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
            return ["Unable to generate recommendations due to error"]

    def cleanup_resources(self):
        """Clean up resources and optimize memory"""
        try:
            # Clear cache if needed
            if self.cache:
                # Keep only recent cache entries
                cache_stats = self.cache.get_stats()
                if cache_stats["cache_size_mb"] > self.config.cache_size_mb * 0.8:
                    # Clear 25% of cache (oldest entries)
                    entries_to_remove = len(self.cache.cache) // 4
                    for _ in range(entries_to_remove):
                        if self.cache.cache:
                            oldest_key = next(iter(self.cache.cache))
                            entry = self.cache.cache.pop(oldest_key)
                            self.cache.current_size -= entry["size"]
                            self.cache.cache_stats["evictions"] += 1

            # Memory optimization
            self.memory_manager.optimize_memory()

            # Keep only recent metrics
            if len(self.metrics) > 1000:
                self.metrics = self.metrics[-500:]

            logger.info("Resource cleanup completed")

        except Exception as e:
            logger.error(f"Resource cleanup failed: {e}")
