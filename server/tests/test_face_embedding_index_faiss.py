import numpy as np
import pytest

from server.face_embedding_index import FAISS_AVAILABLE, FAISSIndex


pytestmark = pytest.mark.skipif(not FAISS_AVAILABLE, reason="faiss not installed")


def _unit(v: np.ndarray) -> np.ndarray:
    v = v.astype(np.float32)
    return v / (np.linalg.norm(v) + 1e-8)


def test_faiss_index_ivf_falls_back_then_upgrades():
    # nlist=3 means we should upgrade to IVF once we have 3+ prototypes.
    idx = FAISSIndex(dimension=4, index_type="IndexIVFFlat", nlist=3)

    e1 = _unit(np.array([1.0, 0.0, 0.0, 0.0]))
    e2 = _unit(np.array([0.0, 1.0, 0.0, 0.0]))
    e3 = _unit(np.array([0.0, 0.0, 1.0, 0.0]))

    idx.add_prototype("c1", e1, "one")
    assert idx.count() == 1
    # Should still be in FlatIP fallback until enough vectors exist.
    assert idx.get_stats().get("active_index_type") == "faiss_IndexFlatIP"

    idx.add_prototype("c2", e2, "two")
    assert idx.count() == 2
    assert idx.get_stats().get("active_index_type") == "faiss_IndexFlatIP"

    # Third vector triggers upgrade.
    idx.add_prototype("c3", e3, "three")
    assert idx.count() == 3
    assert idx.get_stats().get("active_index_type") == "faiss_IndexIVFFlat"

    # Query should find nearest neighbour.
    res = idx.search(e1, k=1, threshold=0.0)
    assert res
    assert res[0].cluster_id == "c1"


def test_faiss_index_remove_rebuilds_and_searches():
    idx = FAISSIndex(dimension=4, index_type="IndexIVFFlat", nlist=3)

    e1 = _unit(np.array([1.0, 0.0, 0.0, 0.0]))
    e2 = _unit(np.array([0.0, 1.0, 0.0, 0.0]))
    e3 = _unit(np.array([0.0, 0.0, 1.0, 0.0]))

    idx.bulk_load(
        {
            "c1": (e1, "one"),
            "c2": (e2, "two"),
            "c3": (e3, "three"),
        }
    )

    assert idx.get_stats().get("active_index_type") == "faiss_IndexIVFFlat"
    assert idx.remove_prototype("c2") is True
    assert idx.count() == 2

    res = idx.search(e1, k=2, threshold=0.0)
    assert res
    assert res[0].cluster_id == "c1"
    # Ensure removed id never appears
    assert all(r.cluster_id != "c2" for r in res)
