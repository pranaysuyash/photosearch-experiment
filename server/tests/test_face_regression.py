"""
P0 Regression Tests for Face Intelligence System

Run with: pytest server/tests/test_face_regression.py -v
Or standalone: python server/tests/test_face_regression.py
"""

import sys
import tempfile
import shutil
from pathlib import Path

import numpy as np
import pytest

# Add server directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from face_clustering_db import FaceClusteringDB


@pytest.fixture
def face_db():
    """Create a temporary face database for testing."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_face.db"
    db = FaceClusteringDB(db_path)
    yield db
    shutil.rmtree(temp_dir)


@pytest.fixture
def populated_db(face_db):
    """Create a database with test data."""
    # Create two clusters
    cluster_a = face_db.add_face_cluster(label="Person A")
    cluster_b = face_db.add_face_cluster(label="Person B")

    # Create embeddings
    emb_a1 = np.random.randn(512).astype(np.float32)
    emb_a2 = np.random.randn(512).astype(np.float32)
    emb_b1 = np.random.randn(512).astype(np.float32)

    # Add face detections
    det_a1 = face_db.add_face_detection(
        photo_path="/photo1.jpg",
        bounding_box={"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2},
        embedding=emb_a1.tolist(),
        quality_score=0.95,
    )
    det_a2 = face_db.add_face_detection(
        photo_path="/photo2.jpg",
        bounding_box={"x": 0.2, "y": 0.2, "width": 0.2, "height": 0.2},
        embedding=emb_a2.tolist(),
        quality_score=0.85,
    )
    det_b1 = face_db.add_face_detection(
        photo_path="/photo3.jpg",
        bounding_box={"x": 0.3, "y": 0.3, "width": 0.2, "height": 0.2},
        embedding=emb_b1.tolist(),
        quality_score=0.90,
    )

    # Associate faces with clusters
    face_db.associate_person_with_photo("/photo1.jpg", cluster_a, det_a1, confidence=0.98)
    face_db.associate_person_with_photo("/photo2.jpg", cluster_a, det_a2, confidence=0.92)
    face_db.associate_person_with_photo("/photo3.jpg", cluster_b, det_b1, confidence=0.95)

    return {
        "db": face_db,
        "cluster_a": cluster_a,
        "cluster_b": cluster_b,
        "det_a1": det_a1,
        "det_a2": det_a2,
        "det_b1": det_b1,
        "emb_a1": emb_a1,
        "emb_a2": emb_a2,
        "emb_b1": emb_b1,
    }


# ============================================================================
# P0.1: Undo Snapshot Tests
# ============================================================================


class TestUndoRestoresExactState:
    """Verify undo restores exact prior state."""

    def test_undo_merge_restores_associations(self, populated_db):
        """After merge + undo, associations match original."""
        db = populated_db["db"]
        cluster_a = populated_db["cluster_a"]
        cluster_b = populated_db["cluster_b"]

        # Get original state
        original_assoc_b = db.get_people_in_photo("/photo3.jpg")
        assert len(original_assoc_b) == 1
        assert original_assoc_b[0].cluster_id == cluster_b

        # Merge B into A (B is source=deleted, A is target=kept)
        db.merge_clusters_with_undo(cluster_b, cluster_a)

        # Verify merge happened
        merged_assoc = db.get_people_in_photo("/photo3.jpg")
        assert len(merged_assoc) == 1
        assert merged_assoc[0].cluster_id == cluster_a

        # Undo
        result = db.undo_last_operation()
        assert result is not None
        assert result["undone"]

        # Verify associations restored
        restored_assoc = db.get_people_in_photo("/photo3.jpg")
        assert len(restored_assoc) == 1
        assert restored_assoc[0].cluster_id == cluster_b

    def test_undo_merge_restores_assignment_state(self, populated_db):
        """After merge + undo, assignment_state matches original."""
        db = populated_db["db"]
        cluster_a = populated_db["cluster_a"]
        cluster_b = populated_db["cluster_b"]
        det_b1 = populated_db["det_b1"]

        # Confirm the face in cluster B first
        db.confirm_face_assignment(det_b1, cluster_b)

        # Verify confirmed
        assoc = db.get_people_in_photo("/photo3.jpg")[0]
        original_state = assoc.assignment_state
        assert original_state == "user_confirmed"

        # Merge B into A (B is source=deleted, A is target=kept)
        db.merge_clusters_with_undo(cluster_b, cluster_a)

        # Undo
        db.undo_last_operation()  # Undo merge

        # Verify assignment_state restored
        restored_assoc = db.get_people_in_photo("/photo3.jpg")[0]
        assert restored_assoc.assignment_state == original_state


class TestPrototypeHandling:
    """Verify prototype is computed and restored correctly."""

    def test_undo_merge_restores_prototype(self, populated_db):
        """After merge + undo, prototype matches original."""
        db = populated_db["db"]
        cluster_a = populated_db["cluster_a"]
        cluster_b = populated_db["cluster_b"]

        # Recompute prototypes to ensure they exist
        db.recompute_all_prototypes()

        # Get original prototype for cluster B
        import sqlite3

        with sqlite3.connect(str(db.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT prototype_embedding, prototype_count FROM face_clusters WHERE cluster_id = ?",
                (cluster_b,),
            ).fetchone()
            original_prototype = row["prototype_embedding"]
            original_count = row["prototype_count"]

        # Merge B into A (B is source=deleted, A is target=kept)
        db.merge_clusters_with_undo(cluster_b, cluster_a)

        # Undo
        db.undo_last_operation()

        # Verify prototype restored
        with sqlite3.connect(str(db.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT prototype_embedding, prototype_count FROM face_clusters WHERE cluster_id = ?",
                (cluster_b,),
            ).fetchone()
            restored_prototype = row["prototype_embedding"]
            restored_count = row["prototype_count"]

        # Compare (byte-for-byte)
        if original_prototype is not None:
            assert restored_prototype == original_prototype
        assert restored_count == original_count


# ============================================================================
# P0.2: Transactionality Tests
# ============================================================================


class TestTransactionality:
    """Verify operation + log are in single transaction."""

    def test_merge_is_atomic(self, populated_db):
        """Merge and log entry are in same transaction."""
        db = populated_db["db"]
        cluster_a = populated_db["cluster_a"]
        cluster_b = populated_db["cluster_b"]

        # Merge B into A (B is source=deleted, A is target=kept)
        db.merge_clusters_with_undo(cluster_b, cluster_a)

        # Both should exist: merged state AND log entry
        import sqlite3

        with sqlite3.connect(str(db.db_path)) as conn:
            # Check cluster B is deleted
            rows = conn.execute("SELECT * FROM face_clusters WHERE cluster_id = ?", (cluster_b,)).fetchall()
            assert len(rows) == 0

            # Check log entry exists
            log = conn.execute(
                "SELECT * FROM person_operations_log WHERE operation_type = 'merge' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            assert log is not None


# ============================================================================
# Smoke Test Script (standalone runner)
# ============================================================================


def run_smoke_test():
    """10-minute manual smoke test."""
    print("=" * 60)
    print("FACE INTELLIGENCE P0 SMOKE TEST")
    print("=" * 60)

    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "smoke_test.db"

    try:
        db = FaceClusteringDB(db_path)

        # 1. Create cluster, confirm face
        print("\n1. Create cluster and confirm face...")
        cluster_id = db.add_face_cluster(label="Test Person")
        emb = np.random.randn(512).astype(np.float32).tolist()
        det_id = db.add_face_detection("/photo1.jpg", {"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2}, emb, 0.9)
        db.associate_person_with_photo("/photo1.jpg", cluster_id, det_id, 0.95)
        db.confirm_face_assignment(det_id, cluster_id)

        assoc = db.get_people_in_photo("/photo1.jpg")[0]
        assert assoc.assignment_state == "user_confirmed", "❌ Confirm failed"
        print("   ✅ Confirm works")

        # 2. Merge two clusters
        print("\n2. Merge clusters...")
        cluster2 = db.add_face_cluster(label="To Merge")
        emb2 = np.random.randn(512).astype(np.float32).tolist()
        det2 = db.add_face_detection("/photo2.jpg", {"x": 0.2, "y": 0.2, "w": 0.2, "h": 0.2}, emb2, 0.85)
        db.associate_person_with_photo("/photo2.jpg", cluster2, det2, 0.90)

        db.merge_clusters_with_undo(cluster2, cluster_id)
        assoc2 = db.get_people_in_photo("/photo2.jpg")[0]
        assert assoc2.cluster_id == cluster_id, "❌ Merge failed"
        print("   ✅ Merge works")

        # 3. Undo merge
        print("\n3. Undo merge...")
        db.undo_last_operation()
        assoc2_undo = db.get_people_in_photo("/photo2.jpg")[0]
        assert assoc2_undo.cluster_id == cluster2, "❌ Undo failed"
        print("   ✅ Undo works")

        # 4. Reject face
        print("\n4. Reject face...")
        db.reject_face_from_cluster(det2, cluster2)

        import sqlite3

        with sqlite3.connect(str(db_path)) as conn:
            rows = conn.execute("SELECT * FROM face_rejections WHERE detection_id = ?", (det2,)).fetchall()
            assert len(rows) == 1, "❌ Rejection not recorded"
        print("   ✅ Reject works")

        # 5. Undo reject
        print("\n5. Undo reject...")
        db.undo_last_operation()

        with sqlite3.connect(str(db_path)) as conn:
            rows = conn.execute("SELECT * FROM face_rejections WHERE detection_id = ?", (det2,)).fetchall()
            assert len(rows) == 0, "❌ Undo reject failed"
        print("   ✅ Undo reject works")

        # 6. Prototype recompute
        print("\n6. Recompute prototypes...")
        db.recompute_all_prototypes()

        with sqlite3.connect(str(db_path)) as conn:
            row = conn.execute(
                "SELECT prototype_embedding FROM face_clusters WHERE cluster_id = ?",
                (cluster_id,),
            ).fetchone()
            assert row[0] is not None, "❌ Prototype not computed"
        print("   ✅ Prototype recompute works")

        print("\n" + "=" * 60)
        print("🎉 ALL P0 SMOKE TESTS PASSED!")
        print("=" * 60)

    finally:
        shutil.rmtree(temp_dir)


# ============================================================================
# P0.4: Review Queue Tests
# ============================================================================


class TestReviewQueue:
    """Test review queue operations."""

    def test_add_to_review_queue(self, face_db):
        """Test adding items to review queue."""
        cluster = face_db.add_face_cluster(label="Test Person")
        det = face_db.add_face_detection("/test.jpg", {"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2})

        item_id = face_db.add_to_review_queue(det, cluster, 0.52, "gray_zone")
        assert item_id > 0

        queue = face_db.get_review_queue()
        assert len(queue) == 1
        assert queue[0]["detection_id"] == det
        assert queue[0]["similarity"] == 0.52
        assert queue[0]["reason"] == "gray_zone"

    def test_review_queue_count(self, face_db):
        """Test review queue count."""
        cluster = face_db.add_face_cluster(label="Test Person")

        assert face_db.get_review_queue_count() == 0

        for i in range(3):
            det = face_db.add_face_detection(f"/test{i}.jpg", {"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2})
            face_db.add_to_review_queue(det, cluster, 0.51 + i * 0.01, "gray_zone")

        assert face_db.get_review_queue_count() == 3

    def test_resolve_confirm(self, face_db):
        """Test confirming a review item."""
        cluster = face_db.add_face_cluster(label="Test Person")
        det = face_db.add_face_detection("/test.jpg", {"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2})
        face_db.add_to_review_queue(det, cluster, 0.52, "gray_zone")

        result = face_db.resolve_review_item(det, "confirm", cluster)
        assert result is True

        # Queue should be empty now
        assert face_db.get_review_queue_count() == 0

    def test_resolve_reject(self, face_db):
        """Test rejecting a review item."""
        cluster = face_db.add_face_cluster(label="Test Person")
        det = face_db.add_face_detection("/test.jpg", {"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2})
        face_db.add_to_review_queue(det, cluster, 0.52, "gray_zone")

        result = face_db.resolve_review_item(det, "reject", cluster)
        assert result is True

        # Queue should be empty
        assert face_db.get_review_queue_count() == 0

        # Should be in rejections table
        import sqlite3

        with sqlite3.connect(str(face_db.db_path)) as conn:
            rows = conn.execute("SELECT * FROM face_rejections WHERE detection_id = ?", (det,)).fetchall()
            assert len(rows) == 1

    def test_resolve_skip(self, face_db):
        """Test skipping a review item."""
        cluster = face_db.add_face_cluster(label="Test Person")
        det = face_db.add_face_detection("/test.jpg", {"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2})
        face_db.add_to_review_queue(det, cluster, 0.52, "gray_zone")

        result = face_db.resolve_review_item(det, "skip")
        assert result is True

        # Queue should be empty (skipped items don't show up)
        assert face_db.get_review_queue_count() == 0


if __name__ == "__main__":
    run_smoke_test()
