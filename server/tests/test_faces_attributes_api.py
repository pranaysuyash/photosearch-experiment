from fastapi.testclient import TestClient
from fastapi import FastAPI

from server.api.routers.people_photo_association import router
from server.face_clustering_db import FaceClusteringDB
from server.config import settings


def test_faces_in_photo_includes_attributes(tmp_path):
    # Use an isolated DB for this test to ensure migrations with new columns
    original_base = settings.BASE_DIR
    settings.BASE_DIR = tmp_path  # type: ignore[attr-defined]
    db_path = settings.BASE_DIR / "face_clusters.db"  # type: ignore[operator]

    if db_path.exists():
        db_path.unlink()

    face_db = FaceClusteringDB(db_path)

    photo_path = "/unit/test/photo.jpg"
    bbox = {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4}

    detection_id = face_db.add_face_detection(
        photo_path=photo_path,
        bounding_box=bbox,
        embedding=[0.1] * 8,
        quality_score=0.8,
        age_estimate=25,
        age_confidence=0.7,
        emotion="happy",
        emotion_confidence=0.9,
        pose_type="frontal",
        pose_confidence=0.85,
        gender="female",
        gender_confidence=0.8,
        lighting_score=0.6,
        occlusion_score=0.9,
        resolution_score=0.7,
        overall_quality=0.82,
    )

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    resp = client.get(f"/api/photos/{photo_path}/faces")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"]
    assert data["photo_path"] == photo_path
    assert data["face_count"] >= 1

    faces = data["faces"]
    face = next((f for f in faces if f["detection_id"] == detection_id), None)
    assert face is not None

    # Attributes
    assert face["age_estimate"] == 25
    assert face["age_confidence"] == 0.7
    assert face["emotion"] == "happy"
    assert face["emotion_confidence"] == 0.9
    assert face["pose_type"] == "frontal"
    assert face["pose_confidence"] == 0.85
    assert face["gender"] == "female"
    assert face["gender_confidence"] == 0.8

    # Quality
    assert face["quality_score"] == 0.8
    assert face["overall_quality"] == 0.82
    assert face["lighting_score"] == 0.6
    assert face["occlusion_score"] == 0.9
    assert face["resolution_score"] == 0.7

    # Restore settings
    settings.BASE_DIR = original_base  # type: ignore[attr-defined]
