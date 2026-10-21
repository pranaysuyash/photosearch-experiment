"""Image-quality space tests (EG2 background index + rerank + endpoints).

The EG2 embedder is faked; LanceDB and the fusion/rerank logic run for real.
"""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from server.config import settings
from server.image_quality_index import PhotoQualityIndex, QualityIndexBuilder
from server.main import app

client = TestClient(app)


class FakeQualityEmbedder:
    model_name = "fake-eg2"
    dimension = 4

    def __init__(self):
        self.vectors = {}

    def available(self):
        return True

    def encode_images(self, images):
        return [[1.0, 0.0, 0.0, 0.0] for _ in images]

    def embed_query(self, text):
        return [1.0, 0.0, 0.0, 0.0]


@pytest.fixture
def quality_index(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "VECTOR_STORE_PATH", tmp_path / "vs")
    return PhotoQualityIndex(embedder=FakeQualityEmbedder())


def make_builder(tmp_path, monkeypatch, quality_index, fast_ids, loader=None):
    monkeypatch.setattr(settings, "VECTOR_STORE_PATH", tmp_path / "vs")

    class FakeVectorStore:
        def get_all_ids(self):
            return set(fast_ids)

    from PIL import Image

    if loader is None:
        loader = lambda path: Image.new("RGB", (2, 2))  # noqa: E731

    return QualityIndexBuilder(quality_index, FakeVectorStore(), loader)


class TestPhotoQualityIndex:
    def test_index_images_stores_one_vector_per_image(self, quality_index):
        stats = quality_index.index_images(
            [
                {"path": "/a.jpg", "image": "img", "filename": "a.jpg"},
                {"path": "/b.jpg", "image": "img", "filename": "b.jpg"},
            ]
        )
        assert stats == {"indexed": 2, "errors": 0}
        assert quality_index.get_count() == 2
        assert quality_index.get_index_model()["model"] == "fake-eg2"

    def test_pending_diffs_against_fast_space(self, quality_index):
        quality_index.index_images([{"path": "/a.jpg", "image": "i"}])
        assert quality_index.pending({"/a.jpg", "/b.jpg", "/c.jpg"}) == ["/b.jpg", "/c.jpg"]

    def test_coverage_and_rerank(self, quality_index):
        quality_index.index_images([{"path": "/a.jpg", "image": "i"}])
        assert quality_index.coverage(["/a.jpg", "/b.jpg"]) == 0.5
        scores = quality_index.rerank(FakeQualityEmbedder().embed_query("q"), ["/a.jpg", "/b.jpg"])
        assert set(scores) == {"/a.jpg"}
        assert scores["/a.jpg"] == pytest.approx(1.0)


class TestBuilder:
    def test_build_batch_embeds_pending_only(self, tmp_path, monkeypatch, quality_index):
        from PIL import Image

        def loader(path):
            if path.endswith("b.jpg"):
                raise FileNotFoundError(path)
            return Image.new("RGB", (2, 2))

        builder = make_builder(tmp_path, monkeypatch, quality_index, fast_ids={"/a.jpg", "/b.jpg"}, loader=loader)
        stats = builder.build_batch(batch_size=8)
        assert stats["indexed"] == 1
        assert quality_index.get_count() == 1

    def test_idle_gate_uses_activity_clock(self, tmp_path, monkeypatch, quality_index):
        from server.core import state as state_mod

        builder = make_builder(tmp_path, monkeypatch, quality_index, fast_ids=set())
        monkeypatch.setattr(state_mod.activity_clock, "seconds_since_activity", lambda: 999.0)
        assert builder._idle() is True
        monkeypatch.setattr(state_mod.activity_clock, "seconds_since_activity", lambda: 5.0)
        monkeypatch.setattr(settings, "IMAGE_QUALITY_IDLE_SECONDS", 300.0)
        assert builder._idle() is False

    def test_start_stop_lifecycle(self, tmp_path, monkeypatch, quality_index):
        builder = make_builder(tmp_path, monkeypatch, quality_index, fast_ids=set())
        builder.start()
        assert builder.running is True
        builder.stop()
        builder.thread.join(timeout=5)
        assert builder.running is False


class TestSearchRerankFusion:
    def make_state(self, fast_results, quality, coverage):
        fast = SimpleNamespace(quality_index=quality)
        return fast, fast_results, coverage

    def _run_semantic(self, vector_results, caption_hits, quality_index):
        import asyncio

        from server.api.routers.semantic_search import search_semantic

        class FakeEmbedding:
            model_name = "fake"

            def generate_text_embedding(self, t):
                return [0.1, 0.2]

        class FakeVectorStore:
            def __init__(self, results):
                self._results = results

            def search(self, q, limit=50, offset=0):
                return self._results[:limit]

        class FakeMetadataDB:
            def get_metadata_by_path(self, p):
                return {}

        state = SimpleNamespace(
            embedding_generator=FakeEmbedding(),
            vector_store=FakeVectorStore(vector_results),
            caption_index=None,
            image_quality_index=quality_index,
            photo_search_engine=SimpleNamespace(db=FakeMetadataDB()),
        )
        return asyncio.run(search_semantic(state=state, query="wolf forest animal", limit=10))

    @staticmethod
    def img(path, score):
        return {"id": path, "score": score, "metadata": {"path": path, "filename": path}}

    @staticmethod
    def make_quality(scores_by_path, all_paths):
        q = SimpleNamespace()
        q.embedder = SimpleNamespace(available=lambda: True, embed_query=lambda t: [1.0, 0.0])
        q.get_count = lambda: len(scores_by_path) or 1
        q.coverage = lambda paths: 1.0 if all(p in scores_by_path for p in paths) else 0.5
        q.rerank = lambda qv, paths: {p: scores_by_path[p] for p in paths if p in scores_by_path}
        return q

    def test_full_coverage_reranks_and_rescores(self):
        fast = [self.img("/a.jpg", 0.9), self.img("/b.jpg", 0.5)]
        quality = self.make_quality({"/a.jpg": 0.55, "/b.jpg": 0.80}, {"/a.jpg", "/b.jpg"})
        result = self._run_semantic(fast, None, quality)
        assert [r["path"] for r in result["results"]] == ["/b.jpg", "/a.jpg"]
        assert result["results"][0]["score"] == 0.80
        assert result["results"][0]["qualityReranked"] is True

    def test_partial_coverage_skips_rerank(self):
        fast = [self.img("/a.jpg", 0.9), self.img("/b.jpg", 0.5)]
        quality = self.make_quality({"/a.jpg": 0.55}, {"/a.jpg"})
        result = self._run_semantic(fast, None, quality)
        assert [r["path"] for r in result["results"]] == ["/a.jpg", "/b.jpg"]
        assert "qualityReranked" not in result["results"][0]

    def test_no_quality_index_is_noop(self):
        fast = [self.img("/a.jpg", 0.9)]
        result = self._run_semantic(fast, None, None)
        assert result["results"][0]["score"] == 0.9


class TestQualityEndpoints:
    def _install(self, monkeypatch, tmp_path):
        # Patch the store path BEFORE constructing the index — otherwise the
        # test writes rows into the real data/vector_store.
        monkeypatch.setattr(settings, "VECTOR_STORE_PATH", tmp_path / "vs")
        qi = PhotoQualityIndex(embedder=FakeQualityEmbedder())
        builder = make_builder(tmp_path, monkeypatch, qi, fast_ids=set())
        client.get("/api/captions/status")  # ensure app state is built
        st = client.app.state.ps
        monkeypatch.setattr(st, "quality_builder", builder)
        return builder

    def test_status_reports_builder(self, tmp_path, monkeypatch):
        self._install(monkeypatch, tmp_path)
        response = client.get("/api/indexing/quality")
        assert response.status_code == 200
        body = response.json()
        assert body["backend"] == "fake-eg2"
        assert body["available"] is True
        assert "pending" in body

    def test_start_and_stop(self, tmp_path, monkeypatch):
        builder = self._install(monkeypatch, tmp_path)
        response = client.post("/api/indexing/quality/start")
        assert response.status_code == 200
        assert builder.running is True

        response = client.post("/api/indexing/quality/stop")
        assert response.status_code == 200
        builder.thread.join(timeout=5)
        assert builder.running is False

    def test_build_once(self, tmp_path, monkeypatch):
        builder = self._install(monkeypatch, tmp_path)
        builder.vector_store = SimpleNamespace(get_all_ids=lambda: {"/a.jpg", "/b.jpg"})

        response = client.post("/api/indexing/quality/build-once")
        assert response.status_code == 200
        assert response.json()["batch"]["indexed"] == 2

    def test_503_when_not_configured(self, tmp_path, monkeypatch):
        client.get("/api/captions/status")
        st = client.app.state.ps
        monkeypatch.setattr(st, "quality_builder", None)
        response = client.get("/api/indexing/quality")
        assert response.status_code == 503
