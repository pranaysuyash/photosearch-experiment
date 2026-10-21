"""Router-level tests: captions routes (state.db_path regression) and /ai/analyze.

Regression proof (S2): /api/captions/* previously raised AttributeError
(`state.db_path` does not exist on AppState) and returned 500 on every call;
these tests pin the fixed behavior (200 with provider status, index sync on
generate/update/delete, reindex endpoint) plus the real /api/ai/analyze
(prior implementation returned a hardcoded mock).
"""

import pytest
from fastapi.testclient import TestClient

from server.main import app

client = TestClient(app)


def make_png(path):
    from PIL import Image

    Image.new("RGB", (4, 4), color=(200, 30, 30)).save(path)
    return str(path)


class FakeVLMService:
    """In-memory stand-in for VLMCaptionService (no network, no real DB)."""

    provider_name = "ollama"
    _captions = {}
    _calls = []

    def __init__(self, db_path):
        self.db_path = db_path

    def is_enabled(self):
        return True

    def get_available_providers(self):
        return [{"id": "ollama", "name": "Ollama (Local)", "available": True}]

    def generate_caption(self, photo_path, force=False):
        FakeVLMService._calls.append(("generate", photo_path))
        return {"caption": "A dog on the beach.", "model": "gemma4:e4b", "provider": "ollama"}

    def get_caption(self, photo_path):
        return FakeVLMService._captions.get(photo_path)

    def update_caption(self, photo_path, caption):
        FakeVLMService._captions[photo_path] = {"caption": caption, "is_edited": True}

    def delete_caption(self, photo_path):
        FakeVLMService._captions.pop(photo_path, None)

    def get_all_captions(self):
        return [
            {
                "photo_path": p,
                "caption": c["caption"],
                "model_version": "m",
                "provider": "ollama",
                "caption_updated_at": "2026-10-19",
            }
            for p, c in FakeVLMService._captions.items()
        ]

    def get_stats(self):
        return {"total_captions": len(FakeVLMService._captions)}

    def analyze_photo(self, photo_path):
        return {
            "analysis": {
                "caption": "A dog on the beach.",
                "tags": ["dog", "beach"],
                "objects": ["dog"],
                "scene": "beach",
                "colors": ["blue"],
                "quality": 4.5,
            },
            "model": "gemma4:e4b",
            "provider": "ollama",
        }


class FakeCaptionIndex:
    def __init__(self):
        self.indexed = {}
        self.dropped = []

    def index_caption(self, path, caption, gen, caption_updated_at=None):
        self.indexed[path] = caption
        return {"indexed": True}

    def drop(self, path):
        self.dropped.append(path)

    def get_count(self):
        return len(self.indexed)

    def ensure_indexed(self, rows, gen, force=False):
        for r in rows:
            self.indexed[r["photo_path"]] = r["caption"]
        return {"indexed": len(rows), "skipped": 0, "errors": 0}

    def get_stats(self):
        return {"captions_indexed": len(self.indexed)}

    def search(self, q, limit=50, min_score=0.0):
        return []


@pytest.fixture
def fake_vlm(monkeypatch, tmp_path):
    FakeVLMService._captions = {}
    FakeVLMService._calls = []
    monkeypatch.setattr("server.vlm_caption_service.VLMCaptionService", FakeVLMService)
    index = FakeCaptionIndex()

    # Reach into the built app state (first request triggers lazy build in deps).
    client.get("/api/captions/status")
    st = client.app.state.ps
    monkeypatch.setattr(st, "captions_db_path", str(tmp_path / "captions.db"))
    monkeypatch.setattr(st, "caption_index", index)
    monkeypatch.setattr(
        st,
        "embedding_generator",
        type(
            "G",
            (),
            {
                "model_name": "fake",
                "generate_text_embedding": lambda self, t: [0.1, 0.2],
                "embedding_dimension": 2,
            },
        )(),
    )
    yield index


class TestCaptionsRouter:
    def test_status_no_longer_500s(self, fake_vlm):
        """S2 regression: previously AttributeError → 500 on every captions route."""
        response = client.get("/api/captions/status")
        assert response.status_code == 200
        body = response.json()
        assert body["enabled"] is True
        assert body["active_provider"] == "ollama"

    def test_generate_syncs_search_index(self, fake_vlm, tmp_path):
        photo = make_png(tmp_path / "x.png")
        response = client.post("/api/captions/generate", json={"photo_path": str(photo)})

        assert response.status_code == 200
        assert response.json()["caption"] == "A dog on the beach."
        assert fake_vlm.indexed[str(photo)] == "A dog on the beach."

    def test_update_and_delete_sync_index(self, fake_vlm, tmp_path):
        photo = str(tmp_path / "y.png")
        client.put("/api/captions/", json={"photo_path": photo, "caption": "edited caption"})
        assert fake_vlm.indexed[photo] == "edited caption"

        client.delete(f"/api/captions/{photo}")
        assert photo in fake_vlm.dropped

    def test_reindex_endpoint_backfills(self, fake_vlm):
        FakeVLMService._captions["/p.jpg"] = {"caption": "stored caption", "is_edited": False}
        response = client.post("/api/captions/reindex")
        assert response.status_code == 200
        body = response.json()
        assert body["total_captions"] == 1
        assert body["indexed"] == 1


class TestAnalyzeEndpoint:
    def test_analyze_returns_real_provider_output(self, fake_vlm, monkeypatch, tmp_path):
        photo = make_png(tmp_path / "analyze.png")

        # The route builds its own service; point it at the fake too.
        monkeypatch.setattr("server.vlm_caption_service.VLMCaptionService", FakeVLMService)

        response = client.post("/ai/analyze", json={"path": str(photo)})
        assert response.status_code == 200
        body = response.json()

        # Response schema preserved from the mock era; values now real.
        assert set(["caption", "tags", "objects", "scene", "colors", "quality", "analysis_date"]) <= set(body)
        assert body["caption"] == "A dog on the beach."
        assert body["tags"] == ["dog", "beach"]
        assert body["quality"] == 4.5
        assert body["provider"] == "ollama"
        # The hardcoded mock is gone:
        assert body["caption"] != "We found an interesting photo with various visual elements"

    def test_analyze_503_when_no_provider(self, fake_vlm, monkeypatch, tmp_path):
        photo = make_png(tmp_path / "nope.png")

        class DisabledService(FakeVLMService):
            def is_enabled(self):
                return False

        monkeypatch.setattr("server.vlm_caption_service.VLMCaptionService", DisabledService)
        response = client.post("/ai/analyze", json={"path": str(photo)})
        assert response.status_code == 503
        assert "Ollama" in response.json()["detail"]

    def test_analyze_404_for_missing_file(self, fake_vlm, monkeypatch):
        response = client.post("/ai/analyze", json={"path": "/nonexistent/photo.png"})
        assert response.status_code == 404
