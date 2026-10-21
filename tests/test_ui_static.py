"""Web-companion static serving (server/ui_static.py).

Exercised on a bare FastAPI app so the test does not import server.main and
drag the model stack in; the mount helper is the unit under test.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.ui_static import UI_MOUNT_PATH, mount_ui


def _build(tmp_path: Path) -> Path:
    dist = tmp_path / "dist-web"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>shell</title>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log('ok')", encoding="utf-8")
    return dist


def _app_with_ui(dist: Path, **kwargs) -> tuple[FastAPI, bool]:
    app = FastAPI()

    @app.get("/health")
    def health():
        return {"ok": True}

    mounted = mount_ui(app, dist, **kwargs)
    return app, mounted


def test_mount_serves_index_and_assets(tmp_path: Path):
    app, mounted = _app_with_ui(_build(tmp_path))
    assert mounted is True
    client = TestClient(app)

    index = client.get(f"{UI_MOUNT_PATH}/")
    assert index.status_code == 200
    assert "shell" in index.text
    assert index.headers["content-type"].startswith("text/html")

    asset = client.get(f"{UI_MOUNT_PATH}/assets/app.js")
    assert asset.status_code == 200
    assert "console.log" in asset.text


def test_deep_links_fall_back_to_index_for_browser_router(tmp_path: Path):
    app, _ = _app_with_ui(_build(tmp_path))
    client = TestClient(app)

    for deep in ("people", "people/42", "settings", "studio/ai-insights"):
        response = client.get(f"{UI_MOUNT_PATH}/{deep}")
        assert response.status_code == 200, deep
        assert "shell" in response.text, deep


def test_api_routes_are_not_shadowed(tmp_path: Path):
    app, _ = _app_with_ui(_build(tmp_path))
    client = TestClient(app)
    assert client.get("/health").json() == {"ok": True}
    # Outside the mount nothing falls back to the SPA shell.
    assert client.get("/definitely-not-a-route").status_code == 404


def test_missing_build_is_a_noop(tmp_path: Path):
    app, mounted = _app_with_ui(tmp_path / "absent")
    assert mounted is False
    assert all(getattr(r, "name", None) != "ui" for r in app.routes)
    assert TestClient(app).get(f"{UI_MOUNT_PATH}/").status_code == 404


def test_disabled_flag_skips_mount_even_when_build_exists(tmp_path: Path):
    _, mounted = _app_with_ui(_build(tmp_path), enabled=False)
    assert mounted is False
