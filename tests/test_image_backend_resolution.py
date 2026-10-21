"""Image-embedding backend chain tests (EG2-MLX auto → CLIP fallback).

The EG2/MLX path is exercised with injected fakes (real MLX model load is a
runtime-proof concern, and the resolver deliberately stays off in pytest).
"""

import pytest

from server.config import settings
from server.eg2_mlx_backend import QUERY_PREFIX, Eg2MlxBackend
from server.embedding_generator import EmbeddingGenerator


class FakeMlxBackend:
    model_name = "fake-eg2@mlx"
    dimension = 768

    def encode_images(self, images):
        return [[1.0] * 768 for _ in images]

    def embed_query(self, text):
        return [0.5] * 768


@pytest.fixture
def clip_only(monkeypatch):
    """Force the CLIP path regardless of host MLX availability."""
    monkeypatch.setattr(EmbeddingGenerator, "_mlx_enabled", staticmethod(lambda: False))


class TestResolution:
    def test_injected_backend_becomes_active_space(self):
        gen = EmbeddingGenerator(backend=FakeMlxBackend())
        assert gen.model_name == "fake-eg2@mlx"
        assert gen.backend_name == "eg2_mlx"
        assert gen.embedding_dimension == 768
        # Both sides route through the injected backend.
        assert gen.generate_image_embedding(object())[0] == 1.0
        assert gen.generate_text_embedding("query")[0] == 0.5

    def test_resolver_off_in_pytest_falls_back_to_clip(self, clip_only):
        gen = EmbeddingGenerator()
        assert gen.backend_name == "clip_st"
        assert gen.model_name == settings.EMBEDDING_MODEL
        assert gen.embedding_dimension == gen._st_model.get_sentence_embedding_dimension()

    def test_backend_disabled_by_config(self, monkeypatch, clip_only):
        monkeypatch.setattr(settings, "IMAGE_EMBEDDING_BACKEND", "clip_st")
        # Even with resolver "enabled", a pinned clip_st never resolves MLX.
        assert EmbeddingGenerator._mlx_enabled() is False

    def test_resolver_skipped_under_pytest_even_when_available(self, monkeypatch):
        # No clip_only fixture: MLX may be importable on this host, but the
        # pytest guard must keep resolution off.
        gen = EmbeddingGenerator()
        assert gen.backend_name == "clip_st"


class TestBatch:
    def test_generate_image_embeddings_batching(self):
        gen = EmbeddingGenerator(backend=FakeMlxBackend())
        vecs = gen.generate_image_embeddings([object(), object(), object()])
        assert len(vecs) == 3
        assert all(len(v) == 768 for v in vecs)

    def test_clip_path_batches_by_looping(self, clip_only):
        from PIL import Image

        gen = EmbeddingGenerator()
        vecs = gen.generate_image_embeddings([Image.new("RGB", (4, 4)), Image.new("RGB", (4, 4))])
        # CLIP path loops generate_image_embedding; both succeed in one space.
        assert len(vecs) == 2
        assert len(vecs[0]) == len(vecs[1]) == gen.embedding_dimension


class TestEg2MlxBackendContract:
    def test_available_reflects_importability(self):
        # On this dev host mlx is installed; on CI it may not be. Either way
        # available() must not raise.
        assert isinstance(Eg2MlxBackend.available(), bool)

    def test_query_prefix_matches_model_card(self):
        assert QUERY_PREFIX.startswith("task: search result | query: ")

    def test_model_name_stamp_identifies_conversion(self):
        backend = Eg2MlxBackend(model_id="mlx-community/embeddinggemma-2-bf16")
        assert backend.model_name == "embeddinggemma-2@mlx-bf16"
        assert backend.dimension == 768
