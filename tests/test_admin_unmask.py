from fastapi.testclient import TestClient
from server.main import app
from server.config import settings
from server.auth import create_jwt
from pathlib import Path
import tempfile

client = TestClient(app)


def test_admin_unmask(monkeypatch):
    # Prepare
    monkeypatch.setattr(settings, "ACCESS_LOG_UNMASK_ENABLED", True)
    monkeypatch.setattr(settings, "JWT_AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "JWT_SECRET", "jwt-secret")

    with tempfile.TemporaryDirectory() as td:
        media_dir = Path(td)
        monkeypatch.setattr(settings, "MEDIA_DIR", media_dir)

        # create a file
        p = media_dir / "photo.jpg"
        p.write_text("x")

        # compute hash (use same salt default 'dev_salt' unless overridden)
        from server.security_utils import hash_for_logs

        h = hash_for_logs(str(p))

        # Create admin JWT
        admin_payload = {"sub": "admin", "is_admin": True}
        token = create_jwt(admin_payload)

        res = client.post("/admin/unmask", json={"hash": h}, headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        assert res.json().get("path") == str(p)
