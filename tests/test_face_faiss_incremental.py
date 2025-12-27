"""
Property Tests for FAISS Incremental Index Updates

Feature: advanced-face-features
Property 2: Incremental Index Updates
Validates: Requirements 1.3

For any new face detection, the FAISS index should be updated incrementally
without requiring a full rebuild of the entire index.
"""

import time
import numpy as np
import pytest
from server.face_embedding_index import FAISSIndex


@pytest.mark.property
def test_incremental_add_property():
    """
    Property Test 2: Incremental Index Updates

    Tests that adding new faces doesn't require full index rebuild.
    """
    dimension = 512
    initial_size = 1000

    # Create index and add initial embeddings
    index = FAISSIndex(dimension=dimension, index_type="IndexFlatIP")

    np.random.seed(42)
    initial_embeddings = {}
    for i in range(initial_size):
        emb = np.random.rand(dimension).astype(np.float32)
        emb = emb / np.linalg.norm(emb)
        initial_embeddings[f"face_{i}"] = (emb, None)

    # Bulk load initial embeddings
    start = time.perf_counter()
    index.bulk_load(initial_embeddings)
    initial_load_time = (time.perf_counter() - start) * 1000

    # Verify initial count
    assert index.count() == initial_size, f"Expected {initial_size} faces, got {index.count()}"

    # Add new faces incrementally (one at a time)
    new_faces = 100
    incremental_times = []

    for i in range(initial_size, initial_size + new_faces):
        emb = np.random.rand(dimension).astype(np.float32)
        emb = emb / np.linalg.norm(emb)

        start = time.perf_counter()
        index.add_prototype(f"face_{i}", emb, None)
        elapsed = (time.perf_counter() - start) * 1000
        incremental_times.append(elapsed)

    # Each incremental add should be very fast (<10ms per face)
    avg_incremental_time = sum(incremental_times) / len(incremental_times)
    assert avg_incremental_time < 10, (
        f"Average incremental add took {avg_incremental_time:.2f}ms, " f"exceeding 10ms threshold"
    )

    # Verify count increased
    assert index.count() == initial_size + new_faces, f"Expected {initial_size + new_faces} faces, got {index.count()}"

    # Verify search still works
    query = np.random.rand(dimension).astype(np.float32)
    query = query / np.linalg.norm(query)
    results = index.search(query, k=10, threshold=0.0)
    assert len(results) > 0, "Search should still work after incremental adds"

    # Total incremental time should be much less than rebuilding
    total_incremental_time = sum(incremental_times)
    # Rebuilding would take similar time to initial load
    assert total_incremental_time < initial_load_time, (
        f"Incremental adds ({total_incremental_time:.2f}ms) should be faster than "
        f"rebuild ({initial_load_time:.2f}ms)"
    )


@pytest.mark.property
def test_incremental_add_accuracy():
    """
    Test that incremental adds maintain search accuracy.
    Results should be consistent whether faces are added in bulk or incrementally.
    """
    dimension = 512
    total_faces = 500

    # Create two indices
    index_bulk = FAISSIndex(dimension=dimension, index_type="IndexFlatIP")
    index_incremental = FAISSIndex(dimension=dimension, index_type="IndexFlatIP")

    np.random.seed(42)

    # Prepare all embeddings
    all_embeddings = {}
    for i in range(total_faces):
        emb = np.random.rand(dimension).astype(np.float32)
        emb = emb / np.linalg.norm(emb)
        all_embeddings[f"face_{i}"] = (emb, None)

    # Build bulk index
    index_bulk.bulk_load(all_embeddings)

    # Build incremental index (add one by one)
    for cluster_id, (emb, label) in all_embeddings.items():
        index_incremental.add_prototype(cluster_id, emb, label)

    # Both should have same count
    assert index_bulk.count() == index_incremental.count() == total_faces

    # Test search with same query
    query = np.random.rand(dimension).astype(np.float32)
    query = query / np.linalg.norm(query)

    bulk_results = index_bulk.search(query, k=10, threshold=0.0)
    incremental_results = index_incremental.search(query, k=10, threshold=0.0)

    # Should return same number of results
    assert len(bulk_results) == len(
        incremental_results
    ), f"Bulk: {len(bulk_results)} results, Incremental: {len(incremental_results)} results"

    # Top results should be the same (or very similar)
    if bulk_results and incremental_results:
        # Check if top 3 results match
        bulk_top_ids = [r.cluster_id for r in bulk_results[:3]]
        incremental_top_ids = [r.cluster_id for r in incremental_results[:3]]

        # At least 2 out of 3 top results should match
        matches = sum(1 for a, b in zip(bulk_top_ids, incremental_top_ids) if a == b)
        assert matches >= 2, f"Top results differ: Bulk={bulk_top_ids}, Incremental={incremental_top_ids}"

        # Similarity scores should be very close
        for bulk_r, inc_r in zip(bulk_results[:5], incremental_results[:5]):
            assert (
                abs(bulk_r.similarity - inc_r.similarity) < 0.001
            ), f"Similarity scores differ: {bulk_r.similarity} vs {inc_r.similarity}"


@pytest.mark.property
def test_incremental_remove_property():
    """
    Test that removing faces works (though it may require rebuild for IndexFlatIP).
    For IndexIVFFlat, removal might be more complex, but basic functionality should work.
    """
    dimension = 512
    initial_size = 1000

    index = FAISSIndex(dimension=dimension, index_type="IndexFlatIP")

    np.random.seed(42)
    embeddings = {}
    for i in range(initial_size):
        emb = np.random.rand(dimension).astype(np.float32)
        emb = emb / np.linalg.norm(emb)
        embeddings[f"face_{i}"] = (emb, None)

    index.bulk_load(embeddings)
    assert index.count() == initial_size

    # Remove a face
    removed = index.remove_prototype("face_0")
    assert removed is True, "Should successfully remove face"
    assert index.count() == initial_size - 1, f"Expected {initial_size - 1} faces after removal, got {index.count()}"

    # Verify removed face is not in search results
    query = np.random.rand(dimension).astype(np.float32)
    query = query / np.linalg.norm(query)
    results = index.search(query, k=100, threshold=0.0)

    result_ids = [r.cluster_id for r in results]
    assert "face_0" not in result_ids, "Removed face should not appear in search results"

    # Verify other faces still work
    assert len(results) > 0, "Search should still return results after removal"


@pytest.mark.property
def test_indexivfflat_incremental():
    """
    Test incremental updates for IndexIVFFlat.
    IndexIVFFlat should support incremental adds after initial training.
    """
    dimension = 512
    initial_size = 200  # Need enough for training (nlist=100)

    index = FAISSIndex(dimension=dimension, index_type="IndexIVFFlat", nlist=100)

    np.random.seed(42)

    # Initial batch for training
    initial_embeddings = {}
    for i in range(initial_size):
        emb = np.random.rand(dimension).astype(np.float32)
        emb = emb / np.linalg.norm(emb)
        initial_embeddings[f"face_{i}"] = (emb, None)

    # Bulk load (trains the index)
    index.bulk_load(initial_embeddings)
    assert index.count() == initial_size

    # Add more faces incrementally
    new_faces = 50
    for i in range(initial_size, initial_size + new_faces):
        emb = np.random.rand(dimension).astype(np.float32)
        emb = emb / np.linalg.norm(emb)

        start = time.perf_counter()
        index.add_prototype(f"face_{i}", emb, None)
        elapsed = (time.perf_counter() - start) * 1000

        # Incremental add should be fast
        assert elapsed < 50, f"Incremental add took {elapsed:.2f}ms, exceeding 50ms threshold"

    # Verify count
    assert index.count() == initial_size + new_faces

    # Verify search still works
    query = np.random.rand(dimension).astype(np.float32)
    query = query / np.linalg.norm(query)
    results = index.search(query, k=10, threshold=0.0)
    assert len(results) > 0, "Search should work after incremental adds"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "property"])
