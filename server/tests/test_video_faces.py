"""
Test script for video face processing.

Tests the VideoFaceService data model and basic operations.
"""

import sqlite3
import tempfile
from pathlib import Path

# Add parent to path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_video_tables():
    """Test that video tables are created correctly by migration."""
    from server.face_schema_migrations import run_migrations

    # Create temp database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    try:
        # Apply migrations
        run_migrations(db_path)
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        # Check video_assets table
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='video_assets'")
        assert cursor.fetchone() is not None, "video_assets table should exist"

        # Check face_tracks table
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='face_tracks'")
        assert cursor.fetchone() is not None, "face_tracks table should exist"

        # Check track_detections table
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='track_detections'")
        assert cursor.fetchone() is not None, "track_detections table should exist"

        # Check face_detections has new columns
        cursor = conn.execute("PRAGMA table_info(face_detections)")
        columns = {row["name"] for row in cursor.fetchall()}
        assert "source_type" in columns, "source_type column should exist"
        assert "video_id" in columns, "video_id column should exist"
        assert "frame_number" in columns, "frame_number column should exist"
        assert "timestamp_ms" in columns, "timestamp_ms column should exist"
        assert "is_best_frame" in columns, "is_best_frame column should exist"

        print("✅ All video tables created correctly")

        conn.close()
    finally:
        db_path.unlink()


def test_video_service_init():
    """Test VideoFaceService initialization."""
    from server.video_face_service import VideoFaceService

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    try:
        service = VideoFaceService(db_path)

        assert service.db_path == db_path
        assert service.sample_fps == 1.0
        assert service.iou_threshold == 0.3
        assert service.embedding_threshold == 0.6

        print("✅ VideoFaceService initializes correctly")
    finally:
        db_path.unlink()


def test_video_id_generation():
    """Test video ID generation."""
    from server.video_face_service import VideoFaceService

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    try:
        service = VideoFaceService(db_path)

        video_id1 = service._generate_video_id("/path/to/video1.mp4")
        video_id2 = service._generate_video_id("/path/to/video2.mp4")
        video_id3 = service._generate_video_id("/path/to/video1.mp4")

        assert video_id1.startswith("video_")
        assert video_id1 != video_id2
        assert video_id1 == video_id3, "Same path should give same ID"

        print("✅ Video ID generation works correctly")
    finally:
        db_path.unlink()


def test_iou_calculation():
    """Test IOU calculation."""
    from server.video_face_service import VideoFaceService

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    try:
        service = VideoFaceService(db_path)

        box1 = {"x": 0, "y": 0, "width": 100, "height": 100}
        box2 = {"x": 50, "y": 50, "width": 100, "height": 100}

        iou = service._calculate_iou(box1, box2)

        # Intersection: 50x50 = 2500
        # Union: 100*100 + 100*100 - 2500 = 17500
        # IOU = 2500 / 17500 ≈ 0.143
        assert 0.1 < iou < 0.2, f"IOU should be ~0.143, got {iou}"

        # Same box should have IOU of 1
        iou_same = service._calculate_iou(box1, box1)
        assert iou_same == 1.0, f"Same box IOU should be 1.0, got {iou_same}"

        # Non-overlapping boxes should have IOU of 0
        box3 = {"x": 200, "y": 200, "width": 100, "height": 100}
        iou_none = service._calculate_iou(box1, box3)
        assert iou_none == 0.0, f"Non-overlapping IOU should be 0, got {iou_none}"

        print("✅ IOU calculation works correctly")
    finally:
        db_path.unlink()


def test_embedding_similarity():
    """Test embedding similarity calculation."""
    import numpy as np
    from server.video_face_service import VideoFaceService

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    try:
        service = VideoFaceService(db_path)

        emb1 = np.array([1.0, 0.0, 0.0])
        emb2 = np.array([1.0, 0.0, 0.0])
        emb3 = np.array([0.0, 1.0, 0.0])

        # Same vectors should have similarity of 1
        sim_same = service._embedding_similarity(emb1, emb2)
        assert abs(sim_same - 1.0) < 0.001, f"Same vectors should have sim 1.0, got {sim_same}"

        # Orthogonal vectors should have similarity of 0
        sim_ortho = service._embedding_similarity(emb1, emb3)
        assert abs(sim_ortho) < 0.001, f"Orthogonal vectors should have sim 0, got {sim_ortho}"

        print("✅ Embedding similarity works correctly")
    finally:
        db_path.unlink()


def test_tracklet_building():
    """Test tracklet building logic."""
    import numpy as np
    from server.video_face_service import VideoFaceService, FrameFace

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    try:
        service = VideoFaceService(db_path)

        # Create mock detections for 2 faces over 3 frames
        detections = [
            # Face 1 - consistent position
            FrameFace(
                detection_id="f1_0",
                frame_number=0,
                timestamp_ms=0,
                bounding_box={"x": 100, "y": 100, "width": 50, "height": 50},
                embedding=np.array([1.0] + [0.0] * 511),
                quality_score=0.8,
            ),
            FrameFace(
                detection_id="f1_1",
                frame_number=1,
                timestamp_ms=1000,
                bounding_box={"x": 105, "y": 105, "width": 50, "height": 50},
                embedding=np.array([0.99] + [0.01] * 511),
                quality_score=0.9,
            ),
            FrameFace(
                detection_id="f1_2",
                frame_number=2,
                timestamp_ms=2000,
                bounding_box={"x": 110, "y": 110, "width": 50, "height": 50},
                embedding=np.array([0.98] + [0.02] * 511),
                quality_score=0.85,
            ),
            # Face 2 - different position
            FrameFace(
                detection_id="f2_0",
                frame_number=0,
                timestamp_ms=0,
                bounding_box={"x": 300, "y": 300, "width": 50, "height": 50},
                embedding=np.array([0.0] + [1.0] + [0.0] * 510),
                quality_score=0.7,
            ),
            FrameFace(
                detection_id="f2_1",
                frame_number=1,
                timestamp_ms=1000,
                bounding_box={"x": 305, "y": 305, "width": 50, "height": 50},
                embedding=np.array([0.01] + [0.99] + [0.01] * 510),
                quality_score=0.75,
            ),
        ]

        tracks = service.build_tracklets(detections, "test_video")

        # Should have 2 tracks: one with 3 detections, one with 2
        assert len(tracks) == 2, f"Expected 2 tracks, got {len(tracks)}"

        track_sizes = sorted([len(t.detections) for t in tracks])
        assert track_sizes == [2, 3], f"Expected track sizes [2, 3], got {track_sizes}"

        print("✅ Tracklet building works correctly")
    finally:
        db_path.unlink()


def test_best_frame_selection():
    """Test best frame selection."""
    import numpy as np
    from server.video_face_service import VideoFaceService, FrameFace, FaceTrack

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    try:
        service = VideoFaceService(db_path)

        detections = [
            FrameFace(
                detection_id="f1",
                frame_number=0,
                timestamp_ms=0,
                bounding_box={"x": 0, "y": 0, "width": 50, "height": 50},
                embedding=np.array([1.0] * 512),
                quality_score=0.5,
            ),
            FrameFace(
                detection_id="f2",
                frame_number=1,
                timestamp_ms=1000,
                bounding_box={"x": 0, "y": 0, "width": 50, "height": 50},
                embedding=np.array([1.0] * 512),
                quality_score=0.9,  # Best quality
            ),
            FrameFace(
                detection_id="f3",
                frame_number=2,
                timestamp_ms=2000,
                bounding_box={"x": 0, "y": 0, "width": 50, "height": 50},
                embedding=np.array([1.0] * 512),
                quality_score=0.7,
            ),
        ]

        track = FaceTrack(
            track_id="test_track",
            video_id="test_video",
            detections=detections,
            start_frame=0,
            end_frame=2,
        )

        tracks = service.select_best_frames([track])

        assert (
            tracks[0].best_detection_id == "f2"
        ), f"Best frame should be f2 (quality 0.9), got {tracks[0].best_detection_id}"

        print("✅ Best frame selection works correctly")
    finally:
        db_path.unlink()


if __name__ == "__main__":
    print("Testing Video Face Service...")
    print()

    test_video_tables()
    test_video_service_init()
    test_video_id_generation()
    test_iou_calculation()
    test_embedding_similarity()
    test_tracklet_building()
    test_best_frame_selection()

    print()
    print("=" * 50)
    print("All video face service tests passed! ✅")
