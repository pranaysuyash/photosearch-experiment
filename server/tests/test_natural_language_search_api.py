import os
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.api.routers.face_recognition import router
from server.config import settings
from server.face_clustering_db import FaceClusteringDB


def test_parse_natural_language_search_with_known_people(tmp_path, monkeypatch):
    monkeypatch.setenv("PHOTOSEARCH_TEST_MODE", "1")

    original_db_path = settings.FACE_CLUSTERS_DB_PATH
    db_path = tmp_path / "face_clusters.db"
    settings.FACE_CLUSTERS_DB_PATH = str(db_path)

    try:
        face_db = FaceClusteringDB(Path(settings.FACE_CLUSTERS_DB_PATH))
        face_db.add_face_cluster(label="John")

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post(
            "/api/search/natural-language",
            json={"query": "photos with john from last year"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        parsed = data["parsed"]
        assert parsed["original_query"] == "photos with john from last year"
        assert parsed["temporal_constraint"]["relative_period"] == "last year"
        names = {c["name"] for c in parsed["person_constraints"]}
        assert "John" in names
    finally:
        settings.FACE_CLUSTERS_DB_PATH = original_db_path
        os.environ.pop("PHOTOSEARCH_TEST_MODE", None)


def test_execute_natural_language_search(tmp_path, monkeypatch):
    monkeypatch.setenv("PHOTOSEARCH_TEST_MODE", "1")

    original_db_path = settings.FACE_CLUSTERS_DB_PATH
    db_path = tmp_path / "face_clusters.db"
    settings.FACE_CLUSTERS_DB_PATH = str(db_path)

    try:
        face_db = FaceClusteringDB(Path(settings.FACE_CLUSTERS_DB_PATH))
        cluster_id = face_db.add_face_cluster(label="John")

        photo_path = "/unit/test/happy_john.jpg"
        bbox = {"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2}
        detection_id = face_db.add_face_detection(
            photo_path=photo_path,
            bounding_box=bbox,
            embedding=[0.1] * 8,
            quality_score=0.9,
            age_estimate=30,
            emotion="happy",
            emotion_confidence=0.9,
        )
        face_db.associate_person_with_photo(photo_path, cluster_id, detection_id, 0.95)

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post(
            "/api/search/natural-language",
            json={"query": "happy photos with john", "execute": True, "limit": 10, "offset": 0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert any(photo["photo_path"] == photo_path for photo in data["photos"])
    finally:
        settings.FACE_CLUSTERS_DB_PATH = original_db_path
        os.environ.pop("PHOTOSEARCH_TEST_MODE", None)


def test_execute_natural_language_search_with_temporal(tmp_path, monkeypatch):
    monkeypatch.setenv("PHOTOSEARCH_TEST_MODE", "1")

    original_db_path = settings.FACE_CLUSTERS_DB_PATH
    original_metadata_path = settings.PHOTO_METADATA_DB_PATH
    db_path = tmp_path / "face_clusters.db"
    metadata_path = tmp_path / "photo_metadata.db"
    settings.FACE_CLUSTERS_DB_PATH = str(db_path)
    settings.PHOTO_METADATA_DB_PATH = str(metadata_path)

    try:
        face_db = FaceClusteringDB(Path(settings.FACE_CLUSTERS_DB_PATH))
        cluster_id = face_db.add_face_cluster(label="John")

        photo_path = "/unit/test/temporal_john.jpg"
        bbox = {"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2}
        detection_id = face_db.add_face_detection(
            photo_path=photo_path,
            bounding_box=bbox,
            embedding=[0.1] * 8,
            quality_score=0.9,
            age_estimate=30,
            emotion="happy",
            emotion_confidence=0.9,
        )
        face_db.associate_person_with_photo(photo_path, cluster_id, detection_id, 0.95)

        created_date = (datetime.now() - timedelta(days=30)).isoformat(timespec="seconds")
        with sqlite3.connect(str(metadata_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    file_hash TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    version INTEGER DEFAULT 1,
                    deleted_at TIMESTAMP
                )
            """
            )
            metadata = {
                "filesystem": {
                    "created": created_date,
                    "modified": created_date,
                }
            }
            conn.execute(
                "INSERT INTO metadata (file_path, file_hash, metadata_json) VALUES (?, ?, ?)",
                (photo_path, "hash", json.dumps(metadata)),
            )

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post(
            "/api/search/natural-language",
            json={"query": "photos with john from last year", "execute": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert any(photo["photo_path"] == photo_path for photo in data["photos"])
    finally:
        settings.FACE_CLUSTERS_DB_PATH = original_db_path
        settings.PHOTO_METADATA_DB_PATH = original_metadata_path
        os.environ.pop("PHOTOSEARCH_TEST_MODE", None)
