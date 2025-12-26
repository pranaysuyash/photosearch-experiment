from fastapi.testclient import TestClient
from server.main import app
from server.config import settings
from pathlib import Path
import tempfile

client = TestClient(app)


def test_rate_limit_triggers(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_REQS_PER_MIN", 2)

    with tempfile.TemporaryDirectory() as td:
        media_dir = Path(td)
        monkeypatch.setattr(settings, "MEDIA_DIR", media_dir)

        # Create a small JPEG file
        from PIL import Image

        img_path = media_dir / "sample.jpg"
        Image.new("RGB", (32, 32), color=(255, 0, 0)).save(img_path)

        # Issue token via issuer key to allow thumbnail access
        monkeypatch.setattr(settings, "SIGNED_URL_SECRET", "test_secret")
        monkeypatch.setattr(settings, "IMAGE_TOKEN_ISSUER_KEY", "issuer-key")
        res = client.post("/image/token", headers={"x-api-key": "issuer-key"}, json={"path": str(img_path), "ttl": 60})
        token = res.json().get("token")

        # First request OK
        r1 = client.get(f"/image/thumbnail?token={token}&size=64")
        assert r1.status_code == 200
        # Second request OK
        r2 = client.get(f"/image/thumbnail?token={token}&size=64")
        assert r2.status_code == 200
        # Third request should be rate-limited
        r3 = client.get(f"/image/thumbnail?token={token}&size=64")
        assert r3.status_code == 429
