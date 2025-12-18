from fastapi.testclient import TestClient
from server.main import app
from server.config import settings
from server.auth import create_jwt
from pathlib import Path
import tempfile

client = TestClient(app)


def test_issue_token_with_jwt(monkeypatch):
    monkeypatch.setattr(settings, "JWT_AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "JWT_SECRET", "jwt-secret")

    with tempfile.TemporaryDirectory() as td:
        media_dir = Path(td)
        monkeypatch.setattr(settings, "MEDIA_DIR", media_dir)

        # create a file
        p = media_dir / "photo.jpg"
        p.write_text("x")

        # No auth header -> 401
        res = client.post("/image/token", json={"path": str(p)})
        assert res.status_code == 401

        # With valid JWT
        token = create_jwt({"sub": "user1"})
        res2 = client.post("/image/token", json={"path": str(p)}, headers={"Authorization": f"Bearer {token}"})
        assert res2.status_code == 200
        assert "token" in res2.json()
