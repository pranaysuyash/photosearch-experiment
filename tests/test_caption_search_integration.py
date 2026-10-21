"""Caption search index + vector-store stamping tests.

Covers P0.1 (captions become searchable) and the P2 index-stamping
infrastructure: upsert/search/drop, lazy re-embedding on model change, and
the dimension guard that fails soft instead of returning garbage.
"""

import pytest

from server.caption_search_index import CaptionSearchIndex
from server.config import settings
from server.lancedb_store import LanceDBStore


class FakeEmbeddingGenerator:
    """Deterministic text embedder: maps words to orthogonal axes."""

    def __init__(self, model_name="fake-model-v1", dim=8):
        self.model_name = model_name
        self._dim = dim

    def generate_text_embedding(self, text):
        vec = [0.0] * self._dim
        for token in text.lower().split():
            vec[ord(token[0]) % self._dim] = 1.0
        # normalize
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]

    @property
    def embedding_dimension(self):
        return self._dim


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    # "" disables the dedicated caption embedder: unit tests exercise the
    # fallback path with the fake generator and never touch the network.
    monkeypatch.setattr(settings, "VECTOR_STORE_PATH", tmp_path / "vector_store")
    monkeypatch.setattr(settings, "CAPTION_EMBEDDING_MODEL", "")
    return CaptionSearchIndex()


class TestCaptionSearchIndex:
    def test_index_and_search_roundtrip(self, isolated_store):
        gen = FakeEmbeddingGenerator()
        isolated_store.index_caption("/a/beach.jpg", "dog running on the beach", gen)
        isolated_store.index_caption("/b/kitchen.jpg", "cooking dinner kitchen", gen)

        hits = isolated_store.search(gen.generate_text_embedding("dog beach"), limit=5)

        assert isolated_store.get_count() == 2
        assert hits, "expected at least one hit"
        assert hits[0]["path"] == "/a/beach.jpg"
        assert hits[0]["caption"] == "dog running on the beach"
        assert hits[0]["embedding_model"] == "fake-model-v1"

    def test_index_is_upsert_not_append(self, isolated_store):
        gen = FakeEmbeddingGenerator()
        isolated_store.index_caption("/a.jpg", "first caption", gen)
        isolated_store.index_caption("/a.jpg", "second caption", gen)

        assert isolated_store.get_count() == 1
        hits = isolated_store.search(gen.generate_text_embedding("second caption"), limit=5)
        assert hits[0]["caption"] == "second caption"

    def test_empty_caption_is_noop(self, isolated_store):
        gen = FakeEmbeddingGenerator()
        result = isolated_store.index_caption("/a.jpg", "   ", gen)
        assert result["indexed"] is False
        assert isolated_store.get_count() == 0

    def test_drop_removes_vector(self, isolated_store):
        gen = FakeEmbeddingGenerator()
        isolated_store.index_caption("/a.jpg", "caption text", gen)
        isolated_store.drop("/a.jpg")
        assert isolated_store.get_count() == 0

    def test_search_min_score_filters(self, isolated_store):
        gen = FakeEmbeddingGenerator()
        isolated_store.index_caption("/orthogonal.jpg", "zzz qqq xxx", gen)
        # "www" hashes to an axis none of z/q/x use → cosine similarity 0.
        hits = isolated_store.search(gen.generate_text_embedding("www"), limit=5, min_score=0.5)
        assert hits == []


class TestEnsureIndexed:
    def ROWS(self, updated="2026-10-19 10:00:00"):
        return [
            {
                "photo_path": "/a.jpg",
                "caption": "a beach",
                "model_version": "m",
                "provider": "p",
                "caption_updated_at": updated,
            },
            {
                "photo_path": "/b.jpg",
                "caption": "b kitchen",
                "model_version": "m",
                "provider": "p",
                "caption_updated_at": updated,
            },
        ]

    def test_backfill_indexes_all(self, isolated_store):
        gen = FakeEmbeddingGenerator()
        stats = isolated_store.ensure_indexed(self.ROWS(), gen)
        assert stats["indexed"] == 2
        assert isolated_store.get_count() == 2

    def test_fresh_run_skips_existing(self, isolated_store):
        gen = FakeEmbeddingGenerator()
        isolated_store.ensure_indexed(self.ROWS(), gen)
        stats = isolated_store.ensure_indexed(self.ROWS(), gen)
        assert stats["indexed"] == 0
        assert stats["skipped"] == 2

    def test_model_change_reembeds(self, isolated_store):
        gen_v1 = FakeEmbeddingGenerator(model_name="fake-model-v1")
        isolated_store.ensure_indexed(self.ROWS(), gen_v1)

        gen_v2 = FakeEmbeddingGenerator(model_name="fake-model-v2")
        stats = isolated_store.ensure_indexed(self.ROWS(), gen_v2)

        assert stats["indexed"] == 2
        # And the rows now carry the new stamp.
        hits = isolated_store.search(gen_v2.generate_text_embedding("a beach"), limit=5)
        assert all(h["embedding_model"] == "fake-model-v2" for h in hits)

    def test_caption_edit_reembeds(self, isolated_store):
        gen = FakeEmbeddingGenerator()
        isolated_store.ensure_indexed(self.ROWS(), gen)

        edited = self.ROWS()  # /b keeps its original 10:00 timestamp
        edited[0]["caption"] = "a beach at sunset"
        edited[0]["caption_updated_at"] = "2026-10-19 11:00:00"
        stats = isolated_store.ensure_indexed(edited, gen)
        assert stats["indexed"] == 1  # only the edited row

    def test_caption_edit_detected_via_updated_at_key(self, isolated_store):
        """VLMCaptionService.get_all_captions() exposes `updated_at`, not
        `caption_updated_at`; both spellings must drive re-embedding."""
        gen = FakeEmbeddingGenerator()
        rows = [
            {"photo_path": "/a.jpg", "caption": "a beach", "updated_at": "2026-10-19 10:00:00"},
        ]
        isolated_store.ensure_indexed(rows, gen)
        rows[0]["caption"] = "a beach at dusk"
        rows[0]["updated_at"] = "2026-10-20 09:00:00"
        stats = isolated_store.ensure_indexed(rows, gen)
        assert stats["indexed"] == 1


class FakeDedicatedST:
    """Stand-in for the dedicated caption embedder (SentenceTransformer)."""

    def __init__(self, name):
        self.name = name

    def encode(self, texts, normalize_embeddings=True, prompt_name=None):
        import numpy as np

        single = isinstance(texts, str)
        batch = [texts] if single else list(texts)
        out = []
        for t in batch:
            v = [0.0] * 4
            v[0 if prompt_name == "query" else 1] = 1.0
            out.append(v)
        return np.array(out[0] if single else out)


@pytest.fixture
def dedicated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "VECTOR_STORE_PATH", tmp_path / "vs")
    monkeypatch.setattr(settings, "CAPTION_EMBEDDING_MODEL", "fake/caption-model")
    monkeypatch.setattr("sentence_transformers.SentenceTransformer", FakeDedicatedST)
    return CaptionSearchIndex()


class TestDedicatedModelPaths:
    def test_index_without_generator_when_dedicated_model_present(self, dedicated_store):
        """Seed path passes embedding_generator=None; must index via the model."""
        result = dedicated_store.index_caption("/a.jpg", "some caption", None)
        assert result["indexed"] is True
        assert dedicated_store.get_count() == 1

    def test_rows_stamped_with_resolved_model_name(self, dedicated_store):
        dedicated_store.index_caption("/a.jpg", "some caption", None)
        hits = dedicated_store.search(dedicated_store.embed_query("some caption"), limit=5)
        assert hits[0]["embedding_model"] == "fake/caption-model"
        assert dedicated_store.get_index_model()["model"] == "fake/caption-model"

    def test_ensure_indexed_rerun_is_idempotent_with_dedicated_model(self, dedicated_store):
        """S2 regression: per-row stamp came from the (None) generator →
        'unknown' ≠ active model → every rerun re-embedded all captions."""
        rows = [
            {"photo_path": "/a.jpg", "caption": "a beach", "updated_at": "t1"},
            {"photo_path": "/b.jpg", "caption": "a kitchen", "updated_at": "t1"},
        ]
        first = dedicated_store.ensure_indexed(rows, None)
        second = dedicated_store.ensure_indexed(rows, None)
        assert first["indexed"] == 2
        assert second == {"indexed": 0, "skipped": 2, "errors": 0}


class TestIndexStamping:
    def test_stamp_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "VECTOR_STORE_PATH", tmp_path / "vs")
        store = LanceDBStore(table_name="photos_test")
        assert store.get_index_model() is None  # unstamped by default

        store.set_index_model("clip-ViT-B-32", 512)
        stamp = store.get_index_model()
        assert stamp["model"] == "clip-ViT-B-32"
        assert stamp["dim"] == 512

    def test_dedicated_text_model_used_for_both_sides(self, tmp_path, monkeypatch):
        """When the dedicated caption embedder resolves, it embeds captions and
        queries, and the stamp carries ITS name (not the fallback's)."""
        monkeypatch.setattr(settings, "VECTOR_STORE_PATH", tmp_path / "vs")
        monkeypatch.setattr(settings, "CAPTION_EMBEDDING_MODEL", "fake/caption-model")

        class FakeST:
            def __init__(self, name):
                self.name = name

            def encode(self, texts, normalize_embeddings=True, prompt_name=None):
                import numpy as np

                single = isinstance(texts, str)
                batch = [texts] if single else list(texts)
                out = []
                for t in batch:
                    v = [0.0] * 4
                    v[0 if prompt_name == "query" else 1] = 1.0
                    out.append(v)
                return np.array(out[0] if single else out)

        monkeypatch.setattr("sentence_transformers.SentenceTransformer", FakeST)
        index = CaptionSearchIndex()
        gen = FakeEmbeddingGenerator()

        # Both sides route through the dedicated model (axes 0/1), so a query
        # matches indexed captions even though the fallback gen would disagree.
        index.index_caption("/a.jpg", "some caption", gen)
        hits = index.search(index.embed_query("some caption"), limit=5)
        assert hits and hits[0]["path"] == "/a.jpg"
        assert index.get_index_model()["model"] == "fake/caption-model"

    def test_failed_model_load_falls_back(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "VECTOR_STORE_PATH", tmp_path / "vs")
        monkeypatch.setattr(settings, "CAPTION_EMBEDDING_MODEL", "unreachable/model")

        def boom(*a, **k):
            raise RuntimeError("no network")

        monkeypatch.setattr("sentence_transformers.SentenceTransformer", boom)
        index = CaptionSearchIndex()
        gen = FakeEmbeddingGenerator()
        result = index.index_caption("/a.jpg", "caption text", gen)
        assert result["indexed"] is True  # fallback path worked
        assert index._text_model_failed is True
        # embed_query falls back to the generator when one is supplied.
        vec = index.embed_query("caption text", gen)
        assert len(vec) == gen.embedding_dimension

    def test_stamp_roundtrip_reopen(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "VECTOR_STORE_PATH", tmp_path / "vs")
        LanceDBStore(table_name="photos_test2").set_index_model("siglip2", 768)
        reopened = LanceDBStore(table_name="photos_test2")
        assert reopened.get_index_model()["model"] == "siglip2"

    def test_dimension_guard_blocks_mismatched_query(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "VECTOR_STORE_PATH", tmp_path / "vs")
        store = LanceDBStore(table_name="photos_test3")
        store.set_index_model("clip-ViT-B-32", 512)
        # No rows needed: the guard fires before search executes.
        result = store.search([0.1] * 768, limit=5)
        assert result == []

        # Matching dimension is allowed through (empty table → no hits).
        store.set_index_model("clip-ViT-B-32", 512)
        assert store.search([0.1] * 512, limit=5) == []

    def test_unstamped_table_has_no_guard(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "VECTOR_STORE_PATH", tmp_path / "vs")
        store = LanceDBStore(table_name="photos_test4")
        # Legacy unstamped table: guard passes (nothing to compare against).
        assert store._query_dim_matches([0.1] * 999) is True
