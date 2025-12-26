"""
Face Recognition Performance Monitor

Provides comprehensive performance monitoring, analytics, and insights for the face recognition system.
Tracks query performance, cache hit rates, and system health metrics.
"""

import time
import logging
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import threading

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Single performance measurement."""

    timestamp: float
    operation: str
    duration_ms: float
    success: bool
    metadata: Dict[str, Any]


class PerformanceMonitor:
    """
    Real-time performance monitoring for face recognition operations.

    Tracks:
    - Query execution times
    - Cache hit/miss rates
    - Index performance
    - Database optimization impact
    - User operation patterns
    """

    def __init__(self, max_metrics: int = 10000):
        """Initialize performance monitor."""
        self.max_metrics = max_metrics
        self.metrics: deque = deque(maxlen=max_metrics)
        self.operation_stats = defaultdict(list)
        self.lock = threading.Lock()

        # Cache statistics
        self.cache_stats = {"hits": 0, "misses": 0, "total_requests": 0}

        # Index statistics
        self.index_stats = {
            "searches": 0,
            "total_search_time": 0.0,
            "avg_search_time": 0.0,
        }

    def record_metric(self, operation: str, duration_ms: float, success: bool = True, **metadata) -> None:
        """Record a performance metric."""
        metric = PerformanceMetric(
            timestamp=time.time(),
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            metadata=metadata,
        )

        with self.lock:
            self.metrics.append(metric)
            self.operation_stats[operation].append(duration_ms)

            # Keep only recent stats per operation
            if len(self.operation_stats[operation]) > 1000:
                self.operation_stats[operation] = self.operation_stats[operation][-500:]

    def record_cache_hit(self, operation: str = "face_crop"):
        """Record a cache hit."""
        with self.lock:
            self.cache_stats["hits"] += 1
            self.cache_stats["total_requests"] += 1

    def record_cache_miss(self, operation: str = "face_crop"):
        """Record a cache miss."""
        with self.lock:
            self.cache_stats["misses"] += 1
            self.cache_stats["total_requests"] += 1

    def record_index_search(self, duration_ms: float):
        """Record an embedding index search."""
        with self.lock:
            self.index_stats["searches"] += 1
            self.index_stats["total_search_time"] += duration_ms
            self.index_stats["avg_search_time"] = self.index_stats["total_search_time"] / self.index_stats["searches"]

    def get_operation_stats(self, operation: str) -> Dict[str, Any]:
        """Get statistics for a specific operation."""
        with self.lock:
            durations = self.operation_stats.get(operation, [])

            if not durations:
                return {"operation": operation, "count": 0}

            durations_sorted = sorted(durations)
            count = len(durations)

            return {
                "operation": operation,
                "count": count,
                "avg_ms": sum(durations) / count,
                "min_ms": min(durations),
                "max_ms": max(durations),
                "p50_ms": durations_sorted[count // 2],
                "p95_ms": durations_sorted[int(count * 0.95)],
                "p99_ms": durations_sorted[int(count * 0.99)],
            }

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        with self.lock:
            total = self.cache_stats["total_requests"]
            if total == 0:
                return {
                    "hit_rate": 0.0,
                    "miss_rate": 0.0,
                    "total_requests": 0,
                    "hits": 0,
                    "misses": 0,
                }

            return {
                "hit_rate": self.cache_stats["hits"] / total,
                "miss_rate": self.cache_stats["misses"] / total,
                "total_requests": total,
                "hits": self.cache_stats["hits"],
                "misses": self.cache_stats["misses"],
            }

    def get_index_stats(self) -> Dict[str, Any]:
        """Get embedding index performance statistics."""
        with self.lock:
            return dict(self.index_stats)

    def get_recent_metrics(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get metrics from the last N minutes."""
        cutoff = time.time() - (minutes * 60)

        with self.lock:
            recent = [asdict(metric) for metric in self.metrics if metric.timestamp >= cutoff]

        return recent

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        # Common operations to analyze
        operations = [
            "face_crop",
            "cluster_list",
            "similar_faces",
            "face_search",
            "database_query",
            "embedding_search",
        ]

        summary = {
            "timestamp": time.time(),
            "cache_performance": self.get_cache_stats(),
            "index_performance": self.get_index_stats(),
            "operation_stats": {},
            "system_health": self._assess_system_health(),
        }

        for op in operations:
            stats = self.get_operation_stats(op)
            if stats["count"] > 0:
                summary["operation_stats"][op] = stats

        return summary

    def _assess_system_health(self) -> Dict[str, Any]:
        """Assess overall system health based on performance metrics."""
        cache_stats = self.get_cache_stats()

        # Health indicators
        health = {"status": "healthy", "issues": [], "recommendations": []}

        # Check cache performance
        if cache_stats["total_requests"] > 100:
            hit_rate = cache_stats["hit_rate"]
            if hit_rate < 0.5:
                health["issues"].append("Low cache hit rate")
                health["recommendations"].append("Consider increasing cache size or reviewing cache invalidation")
                health["status"] = "degraded"

        # Check query performance
        db_stats = self.get_operation_stats("database_query")
        if db_stats["count"] > 0 and db_stats["avg_ms"] > 100:
            health["issues"].append("Slow database queries")
            health["recommendations"].append("Run database optimization or add missing indexes")
            health["status"] = "degraded"

        # Check embedding search performance
        search_stats = self.get_operation_stats("embedding_search")
        if search_stats["count"] > 0 and search_stats["avg_ms"] > 50:
            health["issues"].append("Slow embedding searches")
            health["recommendations"].append("Consider upgrading to FAISS backend for better performance")
            if health["status"] == "healthy":
                health["status"] = "degraded"

        return health

    def reset_stats(self):
        """Reset all performance statistics."""
        with self.lock:
            self.metrics.clear()
            self.operation_stats.clear()
            self.cache_stats = {"hits": 0, "misses": 0, "total_requests": 0}
            self.index_stats = {
                "searches": 0,
                "total_search_time": 0.0,
                "avg_search_time": 0.0,
            }


class FaceAnalytics:
    """
    Advanced analytics for face recognition system usage and performance.

    Provides insights into:
    - User behavior patterns
    - System usage trends
    - Performance bottlenecks
    - Optimization opportunities
    """

    def __init__(self, db_path: Path):
        """Initialize analytics with database path."""
        self.db_path = db_path

    def get_usage_analytics(self) -> Dict[str, Any]:
        """Get comprehensive usage analytics."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            analytics = {
                "timestamp": time.time(),
                "cluster_analytics": self._get_cluster_analytics(conn),
                "face_analytics": self._get_face_analytics(conn),
                "operation_analytics": self._get_operation_analytics(conn),
                "growth_trends": self._get_growth_trends(conn),
            }

        return analytics

    def _get_cluster_analytics(self, conn) -> Dict[str, Any]:
        """Analyze cluster distribution and quality."""
        cursor = conn.cursor()

        # Cluster size distribution
        cursor.execute("""
            SELECT
                CASE
                    WHEN face_count = 1 THEN 'singleton'
                    WHEN face_count BETWEEN 2 AND 5 THEN 'small'
                    WHEN face_count BETWEEN 6 AND 20 THEN 'medium'
                    WHEN face_count BETWEEN 21 AND 100 THEN 'large'
                    ELSE 'very_large'
                END as size_category,
                COUNT(*) as cluster_count,
                SUM(face_count) as total_faces
            FROM face_clusters
            WHERE hidden = 0
            GROUP BY size_category
        """)
        size_distribution = {
            row["size_category"]: {
                "clusters": row["cluster_count"],
                "faces": row["total_faces"],
            }
            for row in cursor.fetchall()
        }

        # Labeled vs unlabeled
        cursor.execute("""
            SELECT
                CASE
                    WHEN label IS NOT NULL AND label != '' AND label NOT LIKE 'Person %'
                    THEN 'labeled'
                    ELSE 'unlabeled'
                END as label_status,
                COUNT(*) as count
            FROM face_clusters
            WHERE hidden = 0
            GROUP BY label_status
        """)
        label_distribution = {row["label_status"]: row["count"] for row in cursor.fetchall()}

        # Quality distribution (if coherence data exists)
        coherence_distribution = {}
        try:
            cursor.execute("""
                SELECT
                    CASE
                        WHEN coherence_score >= 0.8 THEN 'high'
                        WHEN coherence_score >= 0.6 THEN 'medium'
                        ELSE 'low'
                    END as quality,
                    COUNT(*) as count
                FROM cluster_coherence cc
                JOIN face_clusters fc ON cc.cluster_id = fc.cluster_id
                WHERE fc.hidden = 0
                GROUP BY quality
            """)
            coherence_distribution = {row["quality"]: row["count"] for row in cursor.fetchall()}
        except sqlite3.OperationalError:
            pass  # Table doesn't exist

        return {
            "size_distribution": size_distribution,
            "label_distribution": label_distribution,
            "quality_distribution": coherence_distribution,
        }

    def _get_face_analytics(self, conn) -> Dict[str, Any]:
        """Analyze face detection patterns."""
        cursor = conn.cursor()

        # Confidence distribution
        cursor.execute("""
            SELECT
                CASE
                    WHEN confidence >= 0.9 THEN 'very_high'
                    WHEN confidence >= 0.8 THEN 'high'
                    WHEN confidence >= 0.6 THEN 'medium'
                    ELSE 'low'
                END as confidence_level,
                COUNT(*) as count
            FROM face_detections
            GROUP BY confidence_level
        """)
        confidence_distribution = {row["confidence_level"]: row["count"] for row in cursor.fetchall()}

        # Photos with face counts
        cursor.execute("""
            SELECT face_count, COUNT(*) as photo_count
            FROM (
                SELECT photo_path, COUNT(*) as face_count
                FROM face_detections
                GROUP BY photo_path
            )
            GROUP BY face_count
            ORDER BY face_count
        """)
        faces_per_photo = {row["face_count"]: row["photo_count"] for row in cursor.fetchall()}

        return {
            "confidence_distribution": confidence_distribution,
            "faces_per_photo_distribution": faces_per_photo,
        }

    def _get_operation_analytics(self, conn) -> Dict[str, Any]:
        """Analyze user operations and patterns."""
        cursor = conn.cursor()

        operations = {}

        # Check if operations table exists
        try:
            cursor.execute("""
                SELECT operation_type, COUNT(*) as count
                FROM cluster_operations
                WHERE timestamp > datetime('now', '-30 days')
                GROUP BY operation_type
                ORDER BY count DESC
            """)
            operations = {row["operation_type"]: row["count"] for row in cursor.fetchall()}
        except sqlite3.OperationalError:
            pass  # Table doesn't exist

        return {"recent_operations": operations, "operation_frequency": len(operations)}

    def _get_growth_trends(self, conn) -> Dict[str, Any]:
        """Analyze growth trends over time."""
        cursor = conn.cursor()

        # Cluster growth over last 30 days
        cursor.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as new_clusters
            FROM face_clusters
            WHERE created_at > datetime('now', '-30 days')
            GROUP BY DATE(created_at)
            ORDER BY date
        """)
        cluster_growth = [{"date": row["date"], "count": row["new_clusters"]} for row in cursor.fetchall()]

        # Face detection growth
        cursor.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as new_faces
            FROM face_detections
            WHERE created_at > datetime('now', '-30 days')
            GROUP BY DATE(created_at)
            ORDER BY date
        """)
        face_growth = [{"date": row["date"], "count": row["new_faces"]} for row in cursor.fetchall()]

        return {"cluster_growth_30d": cluster_growth, "face_growth_30d": face_growth}


# Global performance monitor instance
_global_monitor: Optional[PerformanceMonitor] = None


def get_global_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def reset_global_monitor() -> None:
    """Reset the global performance monitor."""
    global _global_monitor
    _global_monitor = PerformanceMonitor()


# Decorator for automatic performance monitoring
def monitor_performance(operation: str):
    """Decorator to automatically monitor function performance."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            monitor = get_global_monitor()
            start_time = time.time()
            success = True

            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                success = False
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                monitor.record_metric(operation, duration_ms, success)

        return wrapper

    return decorator
