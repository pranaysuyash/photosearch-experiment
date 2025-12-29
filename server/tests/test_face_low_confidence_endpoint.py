import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.api.routers.face_recognition import router
from server.config import settings
from server.core.bootstrap import build_state


def test_low_confidence_endpoint_includes_total(tmp_path):
    db_path = tmp_path / "face_clusters.db"

    # Minimal legacy schema required by /api/faces/low-confidence
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE faces (
              id INTEGER PRIMARY KEY,
              image_path TEXT NOT NULL,
              confidence REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE clusters (
              id INTEGER PRIMARY KEY,
              label TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE cluster_membership (
              face_id INTEGER NOT NULL,
              cluster_id INTEGER NOT NULL
            )
            """
        )

        # Two low-confidence faces (< 0.8), one high confidence
        conn.execute(
            "INSERT INTO faces (id, image_path, confidence) VALUES (?, ?, ?)",
            (1, "/tmp/face1.jpg", 0.3),
        )
        conn.execute(
            "INSERT INTO faces (id, image_path, confidence) VALUES (?, ?, ?)",
            (2, "/tmp/face2.jpg", 0.79),
        )
        conn.execute(
            "INSERT INTO faces (id, image_path, confidence) VALUES (?, ?, ?)",
            (3, "/tmp/face3.jpg", 0.95),
        )

        conn.execute("INSERT INTO clusters (id, label) VALUES (?, ?)", (10, "Test Person"))
        conn.execute("INSERT INTO cluster_membership (face_id, cluster_id) VALUES (?, ?)", (2, 10))

        conn.commit()

    original_path = settings.FACE_CLUSTERS_DB_PATH
    settings.FACE_CLUSTERS_DB_PATH = str(db_path)

    try:
        app = FastAPI()
        app.include_router(router)

        # Ensure state.face_clusterer is non-null so endpoint isn't 503.
        app.state.ps = build_state(skip_heavy_components=True)
        app.state.ps.face_clusterer = object()

        client = TestClient(app)
        resp = client.get(
            "/api/faces/low-confidence",
            params={"threshold": 0.8, "limit": 1, "offset": 0},
        )

        assert resp.status_code == 200
        data = resp.json()

        assert data["threshold"] == 0.8
        assert data["limit"] == 1
        assert data["offset"] == 0

        # Count is page size; total is full result size
        assert data["count"] == 1
        assert data["total"] == 2
        assert len(data["faces"]) == 1

        face = data["faces"][0]
        assert "face_id" in face
        assert "image_path" in face
        assert "confidence" in face
    finally:
        settings.FACE_CLUSTERS_DB_PATH = original_path
