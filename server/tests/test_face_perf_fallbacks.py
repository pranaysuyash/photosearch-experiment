import time

from src.enhanced_face_clustering import EnhancedFaceClusterer


def test_detect_faces_returns_fast_when_models_missing(tmp_path):
    # Ensure the clusterer does not attempt heavyweight model init during pytest
    clusterer = EnhancedFaceClusterer(db_path=str(tmp_path / "faces.db"), auto_load_models=False)
    clusterer.models_loaded = False
    clusterer.face_detector = None

    t0 = time.perf_counter()
    faces = clusterer.detect_faces("/does/not/exist.jpg")
    elapsed = time.perf_counter() - t0

    assert faces == []
    assert elapsed < 0.2  # should short-circuit immediately in test mode
