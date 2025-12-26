import tempfile
from fastapi.testclient import TestClient
from server.main import app
from server.config import settings
from pathlib import Path

client = TestClient(app)


def test_thumbnail_path_outside_media_denied(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        # Set MEDIA_DIR to a safe tmpdir
        monkeypatch.setattr(settings, "MEDIA_DIR", Path(td))

        # Attempt to fetch a path outside of MEDIA_DIR using path param
        outside = "/etc/passwd"
        client.get(f"/image/thumbnail?path={outside}")

        # When SANDBOX_STRICT is False by default in dev, the endpoint may allow BASE_DIR fallback.
        # Force strict mode and retry
        monkeypatch.setattr(settings, "SANDBOX_STRICT", True)
        res2 = client.get(f"/image/thumbnail?path={outside}")
        assert res2.status_code == 403
