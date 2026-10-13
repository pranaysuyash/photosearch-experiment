from fastapi.testclient import TestClient
from fastapi import FastAPI

from server.api.routers.core import router as core_router
from server.config import settings

app = FastAPI()
app.include_router(core_router)

client = TestClient(app)


def test_server_config_endpoint(monkeypatch):
    monkeypatch.setattr(settings, "SIGNED_URL_ENABLED", True)
    monkeypatch.setattr(settings, "SANDBOX_STRICT", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    monkeypatch.setattr(settings, "ACCESS_LOG_MASKING", True)
    monkeypatch.setattr(settings, "JWT_AUTH_ENABLED", False)

    res = client.get("/server/config")
    assert res.status_code == 200
    data = res.json()
    assert data["signed_url_enabled"] is True
    assert data["sandbox_strict"] is True
    assert data["rate_limit_enabled"] is False
    assert data["access_log_masking"] is True
    assert data["jwt_auth_enabled"] is False


def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "service" in data
    assert "env" in data
