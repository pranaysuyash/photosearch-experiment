import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from server.main import app
from server.config import settings

client = TestClient(app)


def test_thumbnail_cache_headers_and_conditional(monkeypatch):
    # Relax sandbox for local path testing
    monkeypatch.setattr(settings, "SIGNED_URL_ENABLED", False)
    monkeypatch.setattr(settings, "SANDBOX_STRICT", False)
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)

    with tempfile.TemporaryDirectory() as td:
        media_dir = Path(td)
        monkeypatch.setattr(settings, "MEDIA_DIR", media_dir)

        from PIL import Image

        img_path = media_dir / "sample.jpg"
        Image.new("RGB", (64, 64), color=(0, 255, 0)).save(img_path)

        url = f"/image/thumbnail?path={img_path}&size=64"

        # Prefer WebP via Accept header
        res = client.get(url, headers={"accept": "image/webp"})
        assert res.status_code == 200
        assert res.headers.get("cache-control")
        assert res.headers.get("etag")
        assert res.headers.get("last-modified")
        assert res.headers.get("content-type") in {"image/webp", "image/jpeg"}

        etag = res.headers.get("etag")
        # Conditional request should short-circuit with 304
        res2 = client.get(url, headers={"if-none-match": etag})
        assert res2.status_code == 304
        assert res2.content == b""

        # Explicit format override to JPEG
        res3 = client.get(url + "&format=jpeg")
        assert res3.status_code == 200
        assert res3.headers.get("content-type") == "image/jpeg"
