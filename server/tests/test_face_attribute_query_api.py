import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.api.routers.face_recognition import router
from server.config import settings
from server.face_clustering_db import FaceClusteringDB


def test_face_attribute_query_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("PHOTOSEARCH_TEST_MODE", "1")

    original_db_path = settings.FACE_CLUSTERS_DB_PATH
    db_path = tmp_path / "face_clusters.db"
    settings.FACE_CLUSTERS_DB_PATH = str(db_path)

    try:
        face_db = FaceClusteringDB(Path(settings.FACE_CLUSTERS_DB_PATH))

        photo_path = "/unit/test/happy_kid.jpg"
        bbox = {"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2}
        face_db.add_face_detection(
            photo_path=photo_path,
            bounding_box=bbox,
            embedding=[0.1] * 8,
            quality_score=0.92,
            age_estimate=8,
            age_confidence=0.8,
            emotion="happy",
            emotion_confidence=0.9,
            pose_type="frontal",
            pose_confidence=0.95,
            gender="female",
            gender_confidence=0.9,
            lighting_score=0.7,
            occlusion_score=0.95,
            resolution_score=0.85,
            overall_quality=0.9,
        )

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post(
            "/api/photos/by-face-attributes/query",
            json={"query": "happy kids under 10", "limit": 10, "offset": 0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["filters"].get("max_age") == 10
        assert "happy" in data["filters"].get("emotions", [])
        assert any(photo["photo_path"] == photo_path for photo in data["photos"])
    finally:
        settings.FACE_CLUSTERS_DB_PATH = original_db_path
        os.environ.pop("PHOTOSEARCH_TEST_MODE", None)
