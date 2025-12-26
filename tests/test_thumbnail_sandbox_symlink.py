import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from server.main import app
from server.config import settings

client = TestClient(app)


def test_symlink_outside_media_is_denied(monkeypatch):
    monkeypatch.setattr(settings, "SIGNED_URL_ENABLED", False)
    monkeypatch.setattr(settings, "SANDBOX_STRICT", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)

    with tempfile.TemporaryDirectory() as td_media, tempfile.TemporaryDirectory() as td_outside:
        media_dir = Path(td_media)
        outside_dir = Path(td_outside)
        monkeypatch.setattr(settings, "MEDIA_DIR", media_dir)

        # Create real image outside
        outside_img = outside_dir / "outside.jpg"
        from PIL import Image

        Image.new("RGB", (16, 16), color=(1, 2, 3)).save(outside_img)

        # Symlink inside media pointing to outside file
        symlink_path = media_dir / "link.jpg"
        symlink_path.symlink_to(outside_img)

        res = client.get(f"/image/thumbnail?path={symlink_path}&size=32")
        assert res.status_code == 403


def test_sandbox_strict_blocks_non_loopback_without_token(monkeypatch):
    monkeypatch.setattr(settings, "SIGNED_URL_ENABLED", True)
    monkeypatch.setattr(settings, "SANDBOX_STRICT", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)

    with tempfile.TemporaryDirectory() as td_media:
        media_dir = Path(td_media)
        monkeypatch.setattr(settings, "MEDIA_DIR", media_dir)

        img_path = media_dir / "local.jpg"
        from PIL import Image

        Image.new("RGB", (8, 8), color=(10, 20, 30)).save(img_path)

        # Simulate a non-loopback client by setting a header; TestClient uses testserver host by default,
        # but we can force a remote-looking X-Forwarded-For to exercise the branch.
        res = client.get(
            f"/image/thumbnail?path={img_path}&size=32",
            headers={"x-forwarded-for": "203.0.113.10"},
        )
        assert res.status_code == 401

        # Token-based access should work
        monkeypatch.setattr(settings, "SIGNED_URL_SECRET", "test_secret")
        monkeypatch.setattr(settings, "IMAGE_TOKEN_ISSUER_KEY", "issuer-key")
        tok = client.post(
            "/image/token",
            headers={"x-api-key": "issuer-key"},
            json={"path": str(img_path), "ttl": 60},
        )
        assert tok.status_code == 200
        token = tok.json()["token"]

        res2 = client.get(f"/image/thumbnail?token={token}&size=32")
        assert res2.status_code == 200
        assert res2.headers.get("content-type")
