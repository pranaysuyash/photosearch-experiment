"""Semantic indexing pipeline tests: batching + per-image fallback.

Real libraries contain files that load fine but fail mid-embed (truncated
buffers, exotic formats); one such file must not discard the whole batch.
"""

import pytest

from server.config import settings
from server.services.semantic_indexing import process_semantic_indexing


class BatchFailingGenerator:
    """Batch call explodes (e.g. one poison image); single calls succeed.

    Poison images are marked by size (2x2) so the test can write real PNGs
    that survive the pipeline's load_image stage.
    """

    model_name = "fake-model"
    POISON_SIZE = (2, 2)

    def __init__(self):
        self.single_calls = 0

    def generate_image_embeddings(self, images):
        raise RuntimeError("batch blew up")

    def generate_image_embedding(self, image):
        if image.size == self.POISON_SIZE:
            raise ValueError("poison image")
        self.single_calls += 1
        return [0.1, 0.2, 0.3]

    @property
    def embedding_dimension(self):
        return 3


class FakeVectorStore:
    def __init__(self):
        self.rows = {}
        self.stamp = None
        self.reset_called = False

    def get_index_model(self):
        return None

    def get_all_ids(self):
        return set()

    def add_batch(self, ids, vectors, metadatas):
        for i, vid in enumerate(ids):
            self.rows[vid] = vectors[i]

    def set_index_model(self, model, dim):
        self.stamp = (model, dim)

    def reset(self):
        self.reset_called = True


def make_images(tmp_path, count, poison_index=None):
    """Write real PNGs (the pipeline loads from disk); `poison_index` gets a
    2x2 image that the fake generator refuses. Pass "all" to poison every
    image (a total embed failure)."""
    from PIL import Image

    images = []
    paths = []
    for i in range(count):
        poisoned = poison_index == "all" or (poison_index is not None and i == poison_index)
        size = (2, 2) if poisoned else (4, 4)
        p = tmp_path / f"img_{i}.png"
        Image.new("RGB", size).save(p)
        images.append(Image.open(p))
        paths.append(str(p))
    return paths, images


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "VECTOR_STORE_PATH", tmp_path / "vs")
    return tmp_path


def test_batch_failure_falls_back_per_image(isolated, tmp_path):
    paths, images = make_images(tmp_path, 5, poison_index=2)
    gen = BatchFailingGenerator()
    store = FakeVectorStore()

    process_semantic_indexing(paths, gen, store)

    # 4 of 5 indexed; the poison image skipped without killing the batch.
    assert len(store.rows) == 4
    assert gen.single_calls == 4
    assert store.stamp == ("fake-model", 3)


def test_happy_batch_path_writes_all(isolated, tmp_path):
    paths, images = make_images(tmp_path, 4)

    class GoodGenerator(BatchFailingGenerator):
        def __init__(self):
            super().__init__()
            self.batch_calls = 0

        def generate_image_embeddings(self, images):
            self.batch_calls += 1
            return [[0.1, 0.2, 0.3] for _ in images]

    gen = GoodGenerator()
    store = FakeVectorStore()
    process_semantic_indexing(paths, gen, store)

    assert gen.batch_calls == 1  # batch path used, no fallback
    assert len(store.rows) == 4
    assert store.stamp == ("fake-model", 3)


def test_total_embed_failure_writes_nothing(isolated, tmp_path):
    paths, images = make_images(tmp_path, 3, poison_index="all")
    # Every image is 2x2 → every single embed fails too.
    gen = BatchFailingGenerator()
    store = FakeVectorStore()

    process_semantic_indexing(paths, gen, store)

    assert store.rows == {}
    assert store.stamp is None  # nothing stamped; nothing written
