import tempfile
from fastapi.testclient import TestClient
from server.main import app
from server.config import settings
from pathlib import Path

client = TestClient(app)


def test_issue_token_and_fetch_thumbnail(monkeypatch):
    # Prepare settings
    monkeypatch.setattr(settings, "SIGNED_URL_SECRET", "test_secret")
    monkeypatch.setattr(settings, "IMAGE_TOKEN_ISSUER_KEY", "issuer-key")

    # Create a temporary media dir with an image file
    with tempfile.TemporaryDirectory() as td:
        media_dir = Path(td)
        monkeypatch.setattr(settings, "MEDIA_DIR", media_dir)

        # Create a small JPEG file
        from PIL import Image

        img_path = media_dir / "sample.jpg"
        Image.new("RGB", (32, 32), color=(255, 0, 0)).save(img_path)

        # Try issuing token without API key -> 401
        res = client.post("/image/token", json={"path": str(img_path)})
        assert res.status_code == 401

        # Issue token with API key
        res = client.post("/image/token", headers={"x-api-key": "issuer-key"}, json={"path": str(img_path), "ttl": 60})
        assert res.status_code == 200
        token = res.json().get("token")
        assert token

        # Use token to get thumbnail
        res2 = client.get(f"/image/thumbnail?token={token}&size=64")
        assert res2.status_code == 200
        assert res2.headers.get("content-type") == "image/jpeg"


def test_issue_token_path_outside_media(monkeypatch):
    monkeypatch.setattr(settings, "SIGNED_URL_SECRET", "test_secret")
    monkeypatch.setattr(settings, "IMAGE_TOKEN_ISSUER_KEY", "issuer-key")

    with tempfile.TemporaryDirectory() as td:
        media_dir = Path(td)
        monkeypatch.setattr(settings, "MEDIA_DIR", media_dir)

        outside_path = Path("/etc/passwd")
        res = client.post("/image/token", headers={"x-api-key": "issuer-key"}, json={"path": str(outside_path)})
        assert res.status_code == 403
