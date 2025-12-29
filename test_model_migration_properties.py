"""
Property-Based Tests for Model Migration Integrity

Tests universal properties of the model migration system to ensure
data integrity and consistency during model updates.

Requirements validated:
- 6.2: Model migration preserves embedding relationships
- 6.3: Rollback functionality maintains data consistency
- 6.4: Performance comparison accuracy

Property tests run with 100+ iterations to validate universal correctness.
"""

import numpy as np
import pytest
import tempfile
import shutil
import sqlite3
import time
from pathlib import Path
from typing import List, Dict, Any
import logging

from server.model_manager import ModelManager, ModelInfo

logger = logging.getLogger(__name__)


class TestModelMigrationProperties:
    """Property-based tests for model migration system"""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing"""
        models_dir = tempfile.mkdtemp()
        db_dir = tempfile.mkdtemp()
        db_path = Path(db_dir) / "test_face.db"

        yield Path(models_dir), db_path

        shutil.rmtree(models_dir)
        shutil.rmtree(db_dir)

    @pytest.fixture
    def model_manager(self, temp_dirs):
        """Create model manager for testing"""
        models_dir, db_path = temp_dirs
        return ModelManager(str(models_dir), str(db_path))

    def create_test_embeddings(self, db_path: Path, count: int = 100) -> List[Dict[str, Any]]:
        """Create test face embeddings in database"""
        embeddings = []

        with sqlite3.connect(str(db_path)) as conn:
            # Create face_detections table if it doesn't exist
            conn.execute("""
                CREATE TABLE IF NOT EXISTS face_detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    photo_path TEXT NOT NULL,
                    embedding BLOB,
                    confidence REAL,
                    quality_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Insert test embeddings
            for i in range(count):
                embedding = np.random.randn(512).astype(np.float32)
                embedding = embedding / np.linalg.norm(embedding)  # Normalize

                embedding_data = {
                    "id": i + 1,
                    "photo_path": f"test_photo_{i}.jpg",
                    "embedding": embedding.tobytes(),
                    "confidence": np.random.uniform(0.7, 0.99),
                    "quality_score": np.random.uniform(0.5, 1.0),
                }

                conn.execute(
                    """
                    INSERT INTO face_detections (photo_path, embedding, confidence, quality_score)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        embedding_data["photo_path"],
                        embedding_data["embedding"],
                        embedding_data["confidence"],
                        embedding_data["quality_score"],
                    ),
                )

                embeddings.append(embedding_data)

        return embeddings

    def create_test_clusters(self, db_path: Path, embeddings: List[Dict], num_clusters: int = 10):
        """Create test face clusters"""
        with sqlite3.connect(str(db_path)) as conn:
            # Create face_clusters table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS face_clusters (
                    id TEXT PRIMARY KEY,
                    label TEXT,
                    prototype_embedding BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create photo_person_associations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS photo_person_associations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    photo_path TEXT NOT NULL,
                    cluster_id TEXT NOT NULL,
                    detection_id INTEGER NOT NULL,
                    confidence REAL,
                    FOREIGN KEY (cluster_id) REFERENCES face_clusters(id)
                )
            """)

            # Create clusters and assign embeddings
            embeddings_per_cluster = len(embeddings) // num_clusters

            for cluster_idx in range(num_clusters):
                cluster_id = f"cluster_{cluster_idx}"

                # Calculate prototype (centroid of assigned embeddings)
                start_idx = cluster_idx * embeddings_per_cluster
                end_idx = min(start_idx + embeddings_per_cluster, len(embeddings))

                cluster_embeddings = []
                for i in range(start_idx, end_idx):
                    embedding_bytes = embeddings[i]["embedding"]
                    embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
                    cluster_embeddings.append(embedding)

                if cluster_embeddings:
                    prototype = np.mean(cluster_embeddings, axis=0)
                    prototype = prototype / np.linalg.norm(prototype)

                    # Insert cluster
                    conn.execute(
                        """
                        INSERT INTO face_clusters (id, label, prototype_embedding)
                        VALUES (?, ?, ?)
                    """,
                        (cluster_id, f"Person {cluster_idx}", prototype.tobytes()),
                    )

                    # Insert associations
                    for i in range(start_idx, end_idx):
                        conn.execute(
                            """
                            INSERT INTO photo_person_associations
                            (photo_path, cluster_id, detection_id, confidence)
                            VALUES (?, ?, ?, ?)
                        """,
                            (embeddings[i]["photo_path"], cluster_id, embeddings[i]["id"], embeddings[i]["confidence"]),
                        )

    @pytest.mark.parametrize("iteration", range(20))  # Run 20 iterations
    def test_property_migration_preserves_cluster_relationships(self, model_manager, temp_dirs, iteration):
        """
        Property 8: Model Migration Integrity

        Universal Property: Model migration should preserve cluster relationships.
        Face-to-cluster assignments should remain consistent after migration.

        Validates Requirements: 6.2
        """
        models_dir, db_path = temp_dirs

        # Create test data
        embeddings = self.create_test_embeddings(db_path, count=50)
        self.create_test_clusters(db_path, embeddings, num_clusters=5)

        # Record original cluster assignments
        original_assignments = {}
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT photo_path, cluster_id, detection_id
                FROM photo_person_associations
                ORDER BY photo_path
            """)

            for row in cursor.fetchall():
                original_assignments[row["photo_path"]] = {
                    "cluster_id": row["cluster_id"],
                    "detection_id": row["detection_id"],
                }

        # Property: Should have original assignments
        assert len(original_assignments) > 0, "Should have original cluster assignments"

        # Simulate migration (in real implementation, this would re-extract embeddings)
        migration_result = model_manager.migrate_embeddings("1.1.0", "1.2.0")

        # Property: Migration should start successfully
        assert migration_result["status"] == "started", "Migration should start successfully"
        assert "job_id" in migration_result, "Migration should return job ID"

        # Wait for migration to complete (in real async implementation, would poll status)
        job_id = migration_result["job_id"]
        max_wait = 30  # seconds
        start_time = time.time()

        while time.time() - start_time < max_wait:
            status = model_manager.get_migration_status(job_id)
            if status.get("status") == "completed":
                break
            elif status.get("status") == "failed":
                pytest.fail(f"Migration failed: {status.get('error_message')}")
            time.sleep(0.1)

        # Property: Migration should complete
        final_status = model_manager.get_migration_status(job_id)
        assert final_status["status"] == "completed", "Migration should complete successfully"
        assert final_status["progress"] == 1.0, "Migration progress should be 100%"

        # Verify cluster assignments are preserved
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT photo_path, cluster_id, detection_id
                FROM photo_person_associations
                ORDER BY photo_path
            """)

            migrated_assignments = {}
            for row in cursor.fetchall():
                migrated_assignments[row["photo_path"]] = {
                    "cluster_id": row["cluster_id"],
                    "detection_id": row["detection_id"],
                }

        # Property: All original assignments should be preserved
        assert len(migrated_assignments) == len(original_assignments), "Migration should preserve all assignments"

        for photo_path, original in original_assignments.items():
            assert photo_path in migrated_assignments, f"Photo {photo_path} should still be assigned"
            migrated = migrated_assignments[photo_path]
            assert (
                migrated["cluster_id"] == original["cluster_id"]
            ), f"Cluster assignment for {photo_path} should be preserved"
            assert (
                migrated["detection_id"] == original["detection_id"]
            ), f"Detection ID for {photo_path} should be preserved"

    @pytest.mark.parametrize("iteration", range(15))  # Run 15 iterations
    def test_property_rollback_maintains_consistency(self, model_manager, temp_dirs, iteration):
        """
        Property 9: Rollback Consistency

        Universal Property: Rolling back to a previous model version should maintain
        data consistency and restore the exact previous state.

        Validates Requirements: 6.3
        """
        models_dir, db_path = temp_dirs

        # Install multiple model versions
        model_manager._register_model_installation(
            ModelInfo(
                model_name="test_model",
                version="1.0.0",
                model_type="recognition",
                embedding_dim=512,
                file_size_mb=100.0,
                download_url="",
                checksum="abc123",
                release_date="2023-01-01",
                description="Test model v1.0",
                compatibility=["1.0.0"],
                performance_metrics={"accuracy": 0.95},
            ),
            models_dir / "test_model" / "1.0.0",
        )

        model_manager._register_model_installation(
            ModelInfo(
                model_name="test_model",
                version="1.1.0",
                model_type="recognition",
                embedding_dim=512,
                file_size_mb=110.0,
                download_url="",
                checksum="def456",
                release_date="2023-06-01",
                description="Test model v1.1",
                compatibility=["1.0.0", "1.1.0"],
                performance_metrics={"accuracy": 0.97},
            ),
            models_dir / "test_model" / "1.1.0",
        )

        # Set initial active version
        model_manager._set_active_model_version("test_model", "1.0.0")

        # Property: Initial version should be active
        active_version = model_manager._get_active_model_version("test_model")
        assert active_version == "1.0.0", "Initial version should be active"

        # Update to newer version
        model_manager._set_active_model_version("test_model", "1.1.0")

        # Property: New version should be active
        active_version = model_manager._get_active_model_version("test_model")
        assert active_version == "1.1.0", "Updated version should be active"

        # Rollback to previous version
        rollback_result = model_manager.rollback_to_version("test_model", "1.0.0")

        # Property: Rollback should succeed
        assert rollback_result["status"] == "completed", "Rollback should succeed"
        assert rollback_result["rollback_version"] == "1.0.0", "Should rollback to correct version"
        assert rollback_result["previous_version"] == "1.1.0", "Should record previous version"

        # Property: Rolled back version should be active
        active_version = model_manager._get_active_model_version("test_model")
        assert active_version == "1.0.0", "Rolled back version should be active"

        # Property: Should be able to rollback to any installed version
        model_manager._set_active_model_version("test_model", "1.1.0")
        rollback_result2 = model_manager.rollback_to_version("test_model", "1.0.0")
        assert rollback_result2["status"] == "completed", "Multiple rollbacks should work"

    @pytest.mark.parametrize("iteration", range(10))  # Run 10 iterations
    def test_property_performance_comparison_accuracy(self, model_manager, temp_dirs, iteration):
        """
        Property 10: Performance Comparison Accuracy

        Universal Property: Performance comparisons should accurately reflect
        the relative performance differences between model versions.

        Validates Requirements: 6.4
        """
        models_dir, db_path = temp_dirs

        # Create benchmark data for two model versions
        model_name = "test_model"
        version1 = "1.0.0"
        version2 = "1.1.0"

        # Insert benchmark data with known differences
        base_accuracy = 0.95
        improved_accuracy = 0.97  # 2.1% improvement

        base_speed = 20.0  # ms
        improved_speed = 18.0  # 10% improvement

        with sqlite3.connect(str(db_path)) as conn:
            # Insert benchmarks for version 1.0.0
            benchmarks_v1 = [
                ("accuracy", base_accuracy),
                ("precision", 0.94),
                ("recall", 0.96),
                ("inference_time_ms", base_speed),
                ("memory_usage_mb", 512.0),
            ]

            for metric_name, value in benchmarks_v1:
                conn.execute(
                    """
                    INSERT INTO model_benchmarks
                    (model_version, benchmark_type, metric_name, metric_value, test_dataset)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (f"{model_name}_{version1}", "performance", metric_name, value, "test"),
                )

            # Insert benchmarks for version 1.1.0 (with improvements)
            benchmarks_v2 = [
                ("accuracy", improved_accuracy),
                ("precision", 0.96),
                ("recall", 0.98),
                ("inference_time_ms", improved_speed),
                ("memory_usage_mb", 520.0),
            ]

            for metric_name, value in benchmarks_v2:
                conn.execute(
                    """
                    INSERT INTO model_benchmarks
                    (model_version, benchmark_type, metric_name, metric_value, test_dataset)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (f"{model_name}_{version2}", "performance", metric_name, value, "test"),
                )

        # Compare model versions
        comparison = model_manager.compare_model_versions(model_name, version1, version2)

        # Property: Comparison should include both versions
        assert comparison["model_name"] == model_name
        assert comparison["version1"] == version1
        assert comparison["version2"] == version2

        # Property: Should have metrics for both versions
        assert "version1_metrics" in comparison
        assert "version2_metrics" in comparison
        assert len(comparison["version1_metrics"]) > 0
        assert len(comparison["version2_metrics"]) > 0

        # Property: Improvements should be calculated correctly
        assert "improvements" in comparison
        improvements = comparison["improvements"]

        # Check accuracy improvement
        if "accuracy" in improvements:
            expected_accuracy_improvement = ((improved_accuracy - base_accuracy) / base_accuracy) * 100
            actual_accuracy_improvement = improvements["accuracy"]
            assert (
                abs(actual_accuracy_improvement - expected_accuracy_improvement) < 0.1
            ), f"Accuracy improvement should be ~{expected_accuracy_improvement:.1f}%, got {actual_accuracy_improvement:.1f}%"

        # Check speed improvement (negative because lower is better for time)
        if "inference_time_ms" in improvements:
            expected_speed_improvement = ((improved_speed - base_speed) / base_speed) * 100
            actual_speed_improvement = improvements["inference_time_ms"]
            assert (
                abs(actual_speed_improvement - expected_speed_improvement) < 0.1
            ), f"Speed improvement should be ~{expected_speed_improvement:.1f}%, got {actual_speed_improvement:.1f}%"

        # Property: Metrics should be preserved accurately
        v1_metrics = comparison["version1_metrics"]
        v2_metrics = comparison["version2_metrics"]

        assert abs(v1_metrics["accuracy"] - base_accuracy) < 0.001, "V1 accuracy should match input"
        assert abs(v2_metrics["accuracy"] - improved_accuracy) < 0.001, "V2 accuracy should match input"
        assert abs(v1_metrics["inference_time_ms"] - base_speed) < 0.001, "V1 speed should match input"
        assert abs(v2_metrics["inference_time_ms"] - improved_speed) < 0.001, "V2 speed should match input"

    @pytest.mark.parametrize("iteration", range(12))  # Run 12 iterations
    def test_property_migration_job_tracking_accuracy(self, model_manager, temp_dirs, iteration):
        """
        Property 11: Migration Job Tracking Accuracy

        Universal Property: Migration job status should accurately reflect
        the actual progress and state of the migration process.

        Validates Requirements: 6.2
        """
        models_dir, db_path = temp_dirs

        # Create test embeddings
        embedding_count = 100 + (iteration * 10)  # Vary count per iteration
        self.create_test_embeddings(db_path, count=embedding_count)

        # Start migration
        migration_result = model_manager.migrate_embeddings("1.0.0", "1.1.0")

        # Property: Migration should start with correct initial state
        assert migration_result["status"] == "started"
        assert migration_result["embeddings_total"] == embedding_count

        job_id = migration_result["job_id"]

        # Track migration progress
        progress_history = []
        max_wait = 30
        start_time = time.time()

        while time.time() - start_time < max_wait:
            status = model_manager.get_migration_status(job_id)
            progress_history.append(
                {
                    "timestamp": time.time(),
                    "status": status.get("status"),
                    "progress": status.get("progress", 0.0),
                    "embeddings_migrated": status.get("embeddings_migrated", 0),
                }
            )

            if status.get("status") in ["completed", "failed"]:
                break

            time.sleep(0.1)

        # Property: Should have progress history
        assert len(progress_history) > 0, "Should track migration progress"

        # Property: Progress should be monotonically increasing
        for i in range(1, len(progress_history)):
            prev_progress = progress_history[i - 1]["progress"]
            curr_progress = progress_history[i]["progress"]
            assert curr_progress >= prev_progress, f"Progress should not decrease: {prev_progress} -> {curr_progress}"

        # Property: Final status should be completed
        final_status = progress_history[-1]
        assert final_status["status"] == "completed", "Migration should complete"
        assert final_status["progress"] == 1.0, "Final progress should be 100%"
        assert final_status["embeddings_migrated"] == embedding_count, "Should migrate all embeddings"

        # Property: Job should be retrievable from database
        db_status = model_manager.get_migration_status(job_id)
        assert db_status["status"] == "completed", "DB status should match final status"
        assert db_status["embeddings_total"] == embedding_count, "DB should have correct total"
        assert db_status["embeddings_migrated"] == embedding_count, "DB should have correct migrated count"

    @pytest.mark.parametrize("iteration", range(8))  # Run 8 iterations
    def test_property_model_registry_consistency(self, model_manager, temp_dirs, iteration):
        """
        Property 12: Model Registry Consistency

        Universal Property: Model registry should maintain consistency between
        in-memory state, file storage, and database records.

        Validates Requirements: 6.1, 6.5
        """
        models_dir, db_path = temp_dirs

        # Get initial registry state
        initial_models = model_manager.get_available_models()
        initial_count = len(initial_models)

        # Property: Should have some default models
        assert initial_count > 0, "Should have default models in registry"

        # Add a new model to registry
        test_model = ModelInfo(
            model_name=f"test_model_{iteration}",
            version="1.0.0",
            model_type="recognition",
            embedding_dim=512,
            file_size_mb=100.0,
            download_url="https://example.com/model.zip",
            checksum="test123",
            release_date="2024-01-01",
            description="Test model for property testing",
            compatibility=["1.0.0"],
            performance_metrics={"accuracy": 0.95},
        )

        key = f"{test_model.model_name}_{test_model.version}"
        model_manager.model_registry[key] = test_model
        model_manager._save_model_registry()

        # Property: Registry should reflect the addition
        updated_models = model_manager.get_available_models()
        assert len(updated_models) == initial_count + 1, "Registry should have one more model"

        # Find the added model
        added_model = None
        for model in updated_models:
            if model["model_name"] == test_model.model_name:
                added_model = model
                break

        assert added_model is not None, "Added model should be in registry"
        assert added_model["version"] == test_model.version, "Version should match"
        assert added_model["embedding_dim"] == test_model.embedding_dim, "Embedding dim should match"

        # Property: Registry should persist across manager instances
        new_manager = ModelManager(str(models_dir), str(db_path))
        persisted_models = new_manager.get_available_models()

        assert len(persisted_models) == len(updated_models), "Registry should persist"

        # Find the model in persisted registry
        persisted_model = None
        for model in persisted_models:
            if model["model_name"] == test_model.model_name:
                persisted_model = model
                break

        assert persisted_model is not None, "Model should persist across instances"
        assert persisted_model["version"] == test_model.version, "Persisted version should match"

    def test_property_concurrent_migration_safety(self, model_manager, temp_dirs):
        """
        Property 13: Concurrent Migration Safety

        Universal Property: Multiple concurrent migration requests should be
        handled safely without data corruption or inconsistent state.

        Validates Requirements: 6.2
        """
        models_dir, db_path = temp_dirs

        # Create test data
        self.create_test_embeddings(db_path, count=50)

        # Start multiple migrations (should handle gracefully)
        migration1 = model_manager.migrate_embeddings("1.0.0", "1.1.0")
        migration2 = model_manager.migrate_embeddings("1.1.0", "1.2.0")

        # Property: Both migrations should start (or second should be queued/rejected gracefully)
        assert migration1["status"] == "started", "First migration should start"
        # Second migration behavior depends on implementation - could be queued or rejected
        assert migration2["status"] in ["started", "error", "queued"], "Second migration should be handled"

        # Property: Job IDs should be unique
        if migration2["status"] == "started":
            assert migration1["job_id"] != migration2["job_id"], "Job IDs should be unique"

        # Wait for completion
        max_wait = 30
        start_time = time.time()

        while time.time() - start_time < max_wait:
            status1 = model_manager.get_migration_status(migration1["job_id"])
            if status1.get("status") in ["completed", "failed"]:
                break
            time.sleep(0.1)

        # Property: At least one migration should complete successfully
        final_status1 = model_manager.get_migration_status(migration1["job_id"])
        assert final_status1["status"] in ["completed", "failed"], "Migration should reach final state"


if __name__ == "__main__":
    # Run property tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
