"""
Face Database Query Optimizer

Provides comprehensive database indexing and query optimization for face recognition system.
Implements missing indexes and query pattern optimizations for production performance.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any
import time

logger = logging.getLogger(__name__)


class FaceDatabaseOptimizer:
    """
    Database optimizer for face recognition system.

    Adds missing indexes, analyzes query patterns, and provides performance monitoring.
    """

    def __init__(self, db_path: Path):
        """Initialize optimizer with database path."""
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """Connect to the database."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA cache_size=20000")  # Increased cache
        self.conn.execute("PRAGMA temp_store=MEMORY")
        self.conn.execute("PRAGMA mmap_size=268435456")  # 256MB mmap

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def add_missing_indexes(self) -> Dict[str, bool]:
        """
        Add all missing indexes for optimal query performance.

        Returns:
            Dict of index_name -> success_status
        """
        if not self.conn:
            raise RuntimeError("Database not connected")

        # Define all needed indexes
        indexes = {
            # Face table indexes
            "idx_faces_confidence": "CREATE INDEX IF NOT EXISTS idx_faces_confidence ON faces(confidence DESC)",
            "idx_faces_created_at": "CREATE INDEX IF NOT EXISTS idx_faces_created_at ON faces(created_at DESC)",
            "idx_faces_updated_at": "CREATE INDEX IF NOT EXISTS idx_faces_updated_at ON faces(updated_at DESC)",
            "idx_faces_image_confidence": "CREATE INDEX IF NOT EXISTS idx_faces_image_confidence ON faces(image_path, confidence DESC)",
            # Cluster table indexes
            "idx_clusters_label": "CREATE INDEX IF NOT EXISTS idx_clusters_label ON clusters(label)",
            "idx_clusters_size": "CREATE INDEX IF NOT EXISTS idx_clusters_size ON clusters(size DESC)",
            "idx_clusters_created_at": "CREATE INDEX IF NOT EXISTS idx_clusters_created_at ON clusters(created_at DESC)",
            "idx_clusters_updated_at": "CREATE INDEX IF NOT EXISTS idx_clusters_updated_at ON clusters(updated_at DESC)",
            "idx_clusters_label_size": "CREATE INDEX IF NOT EXISTS idx_clusters_label_size ON clusters(label, size DESC)",
            # Cluster membership indexes
            "idx_membership_face": "CREATE INDEX IF NOT EXISTS idx_membership_face ON cluster_membership(face_id)",
            "idx_membership_cluster": "CREATE INDEX IF NOT EXISTS idx_membership_cluster ON cluster_membership(cluster_id)",
            # Image clusters indexes
            "idx_image_clusters_face_count": "CREATE INDEX IF NOT EXISTS idx_image_clusters_face_count ON image_clusters(face_count DESC)",
            "idx_image_clusters_updated": "CREATE INDEX IF NOT EXISTS idx_image_clusters_updated ON image_clusters(updated_at DESC)",
            # Composite indexes for common query patterns
            "idx_faces_cluster_confidence": "CREATE INDEX IF NOT EXISTS idx_faces_cluster_confidence ON faces(cluster_id, confidence DESC)",
            "idx_faces_image_cluster": "CREATE INDEX IF NOT EXISTS idx_faces_image_cluster ON faces(image_path, cluster_id)",
        }

        # Add indexes for face_clustering_db tables if they exist
        cursor = self.conn.cursor()

        # Check if face_clustering_db tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        if "face_detections" in tables:
            indexes.update(
                {
                    "idx_detections_photo": "CREATE INDEX IF NOT EXISTS idx_detections_photo ON face_detections(photo_path)",
                    "idx_detections_confidence": "CREATE INDEX IF NOT EXISTS idx_detections_confidence ON face_detections(confidence DESC)",
                    "idx_detections_created": "CREATE INDEX IF NOT EXISTS idx_detections_created ON face_detections(created_at DESC)",
                }
            )

        if "cluster_coherence" in tables:
            indexes.update(
                {
                    "idx_coherence_cluster": "CREATE INDEX IF NOT EXISTS idx_coherence_cluster ON cluster_coherence(cluster_id)",
                    "idx_coherence_score": "CREATE INDEX IF NOT EXISTS idx_coherence_score ON cluster_coherence(coherence_score DESC)",
                    "idx_coherence_mixed": "CREATE INDEX IF NOT EXISTS idx_coherence_mixed ON cluster_coherence(is_mixed_suspected)",
                }
            )

        if "cluster_operations" in tables:
            indexes.update(
                {
                    "idx_operations_timestamp": "CREATE INDEX IF NOT EXISTS idx_operations_timestamp ON cluster_operations(timestamp DESC)",
                    "idx_operations_type": "CREATE INDEX IF NOT EXISTS idx_operations_type ON cluster_operations(operation_type)",
                    "idx_operations_cluster": "CREATE INDEX IF NOT EXISTS idx_operations_cluster ON cluster_operations(cluster_id)",
                }
            )

        if "hidden_clusters" in tables:
            indexes.update(
                {
                    "idx_hidden_cluster": "CREATE INDEX IF NOT EXISTS idx_hidden_cluster ON hidden_clusters(cluster_id)",
                    "idx_hidden_created": "CREATE INDEX IF NOT EXISTS idx_hidden_created ON hidden_clusters(created_at DESC)",
                }
            )

        if "review_queue" in tables:
            indexes.update(
                {
                    "idx_review_detection": "CREATE INDEX IF NOT EXISTS idx_review_detection ON review_queue(detection_id)",
                    "idx_review_similarity": "CREATE INDEX IF NOT EXISTS idx_review_similarity ON review_queue(similarity_score DESC)",
                    "idx_review_created": "CREATE INDEX IF NOT EXISTS idx_review_created ON review_queue(created_at DESC)",
                    "idx_review_status": "CREATE INDEX IF NOT EXISTS idx_review_status ON review_queue(status)",
                }
            )

        # Execute index creation
        results = {}
        for index_name, sql in indexes.items():
            try:
                start_time = time.time()
                self.conn.execute(sql)
                duration = time.time() - start_time
                results[index_name] = True
                logger.info(f"Created index {index_name} in {duration:.2f}s")
            except Exception as e:
                results[index_name] = False
                logger.error(f"Failed to create index {index_name}: {e}")

        self.conn.commit()
        return results

    def analyze_query_performance(self) -> Dict[str, Any]:
        """
        Analyze common query patterns and their performance.

        Returns:
            Performance analysis results
        """
        if not self.conn:
            raise RuntimeError("Database not connected")

        cursor = self.conn.cursor()

        # Test common query patterns
        queries = {
            "cluster_list": "SELECT id, label, size FROM clusters ORDER BY size DESC LIMIT 100",
            "face_by_cluster": "SELECT COUNT(*) FROM cluster_membership WHERE cluster_id = 1",
            "photos_with_faces": "SELECT DISTINCT image_path FROM faces LIMIT 100",
            "high_confidence_faces": "SELECT COUNT(*) FROM faces WHERE confidence > 0.8",
            "recent_clusters": "SELECT COUNT(*) FROM clusters WHERE created_at > datetime('now', '-7 days')",
        }

        results = {}
        for query_name, sql in queries.items():
            try:
                start_time = time.time()
                cursor.execute(f"EXPLAIN QUERY PLAN {sql}")
                plan = cursor.fetchall()

                start_time = time.time()
                cursor.execute(sql)
                rows = cursor.fetchall()
                duration = time.time() - start_time

                results[query_name] = {
                    "duration_ms": duration * 1000,
                    "row_count": len(rows),
                    "query_plan": [{"detail": row[3]} for row in plan],
                    "uses_index": any("USING INDEX" in str(row) for row in plan),
                }
            except Exception as e:
                results[query_name] = {"error": str(e)}

        return results

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive database statistics.

        Returns:
            Database statistics and health metrics
        """
        if not self.conn:
            raise RuntimeError("Database not connected")

        cursor = self.conn.cursor()

        stats = {}

        # Table row counts
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                stats[f"{table}_count"] = count
            except Exception as e:
                stats[f"{table}_count"] = f"Error: {e}"

        # Index information
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        stats["index_count"] = len(indexes)
        stats["indexes"] = indexes

        # Database size
        cursor.execute("PRAGMA page_count")
        page_count = cursor.fetchone()[0]
        cursor.execute("PRAGMA page_size")
        page_size = cursor.fetchone()[0]
        stats["database_size_mb"] = (page_count * page_size) / (1024 * 1024)

        # WAL mode info
        cursor.execute("PRAGMA journal_mode")
        journal_mode = cursor.fetchone()[0]
        stats["journal_mode"] = journal_mode

        # Cache info
        cursor.execute("PRAGMA cache_size")
        cache_size = cursor.fetchone()[0]
        stats["cache_size_pages"] = cache_size

        return stats

    def optimize_database(self) -> Dict[str, Any]:
        """
        Run comprehensive database optimization.

        Returns:
            Optimization results and performance improvements
        """
        if not self.conn:
            raise RuntimeError("Database not connected")

        results = {"started_at": time.time(), "steps": []}

        # Step 1: Add missing indexes
        logger.info("Adding missing database indexes...")
        index_results = self.add_missing_indexes()
        successful_indexes = sum(1 for success in index_results.values() if success)
        results["steps"].append(
            {
                "step": "add_indexes",
                "successful_indexes": successful_indexes,
                "total_indexes": len(index_results),
                "details": index_results,
            }
        )

        # Step 2: Analyze and vacuum
        logger.info("Running database analysis and cleanup...")
        try:
            self.conn.execute("ANALYZE")
            self.conn.execute("VACUUM")
            results["steps"].append({"step": "analyze_vacuum", "success": True})
        except Exception as e:
            results["steps"].append({"step": "analyze_vacuum", "success": False, "error": str(e)})

        # Step 3: Performance analysis
        logger.info("Analyzing query performance...")
        try:
            perf_results = self.analyze_query_performance()
            results["steps"].append(
                {
                    "step": "performance_analysis",
                    "success": True,
                    "results": perf_results,
                }
            )
        except Exception as e:
            results["steps"].append({"step": "performance_analysis", "success": False, "error": str(e)})

        # Step 4: Final statistics
        try:
            final_stats = self.get_database_stats()
            results["final_stats"] = final_stats
        except Exception as e:
            results["final_stats"] = {"error": str(e)}

        results["completed_at"] = time.time()
        results["duration_seconds"] = results["completed_at"] - results["started_at"]

        return results


def optimize_face_database(db_path: Path) -> Dict[str, Any]:
    """
    Convenience function to optimize face database.

    Args:
        db_path: Path to face clustering database

    Returns:
        Optimization results
    """
    with FaceDatabaseOptimizer(db_path) as optimizer:
        return optimizer.optimize_database()


def get_face_database_stats(db_path: Path) -> Dict[str, Any]:
    """
    Convenience function to get database statistics.

    Args:
        db_path: Path to face clustering database

    Returns:
        Database statistics
    """
    with FaceDatabaseOptimizer(db_path) as optimizer:
        return optimizer.get_database_stats()
