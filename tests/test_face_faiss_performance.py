"""
Property Tests for FAISS Face Search Performance

Feature: advanced-face-features
Property 1: FAISS Search Performance
Validates: Requirements 1.1

For any face collection with more than 10,000 faces, similarity search operations
should complete in under 100ms with FAISS indexing.
"""

import time
import numpy as np
import pytest
from server.face_embedding_index import FAISSIndex, LinearIndex


@pytest.mark.property
@pytest.mark.parametrize("collection_size", [1000, 5000, 10000, 20000])
def test_faiss_search_performance_property(collection_size):
    """
    Property Test 1: FAISS Search Performance

    Tests that FAISS search completes in <100ms for collections >=10K faces.
    For smaller collections, we verify it's still fast.
    """
    # Create FAISS index
    dimension = 512
    index = FAISSIndex(dimension=dimension, index_type="IndexFlatIP")

    # Generate random embeddings (simulating face embeddings)
    np.random.seed(42)  # For reproducibility
    embeddings = {}
    for i in range(collection_size):
        # Generate random normalized embedding
        emb = np.random.rand(dimension).astype(np.float32)
        emb = emb / np.linalg.norm(emb)  # L2 normalize
        embeddings[f"face_{i}"] = (emb, None)  # (embedding, label)

    # Bulk load embeddings
    index.bulk_load(embeddings)

    # Generate query embedding
    query = np.random.rand(dimension).astype(np.float32)
    query = query / np.linalg.norm(query)

    # Measure search time
    start_time = time.perf_counter()
    results = index.search(query, k=10, threshold=0.0)
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    # Property assertion: <100ms for collections >=10K
    if collection_size >= 10000:
        assert elapsed_ms < 100, (
            f"FAISS search took {elapsed_ms:.2f}ms for {collection_size} faces, " f"exceeding 100ms threshold"
        )
    else:
        # For smaller collections, just verify it's reasonable (<50ms)
        assert elapsed_ms < 50, (
            f"FAISS search took {elapsed_ms:.2f}ms for {collection_size} faces, " f"which is unexpectedly slow"
        )

    # Verify we got results
    assert len(results) > 0, "Search should return results"
    assert len(results) <= 10, "Should return at most k results"

    # Verify results are sorted by similarity (descending)
    similarities = [r.similarity for r in results]
    assert similarities == sorted(similarities, reverse=True), "Results should be sorted by similarity (descending)"


@pytest.mark.property
def test_faiss_vs_linear_performance_comparison():
    """
    Compare FAISS performance vs LinearIndex for large collections.
    FAISS should be significantly faster for 10K+ faces.
    """
    collection_size = 10000
    dimension = 512

    # Create both indices
    faiss_index = FAISSIndex(dimension=dimension, index_type="IndexFlatIP")
    linear_index = LinearIndex()

    # Generate embeddings
    np.random.seed(42)
    embeddings = {}
    for i in range(collection_size):
        emb = np.random.rand(dimension).astype(np.float32)
        emb = emb / np.linalg.norm(emb)
        cluster_id = f"face_{i}"
        embeddings[cluster_id] = (emb, None)

    # Load into both indices
    faiss_index.bulk_load(embeddings)
    linear_index.bulk_load(embeddings)

    # Generate query
    query = np.random.rand(dimension).astype(np.float32)
    query = query / np.linalg.norm(query)

    # Time FAISS search
    start = time.perf_counter()
    faiss_results = faiss_index.search(query, k=10, threshold=0.0)
    faiss_time = (time.perf_counter() - start) * 1000

    # Time Linear search
    start = time.perf_counter()
    linear_results = linear_index.search(query, k=10, threshold=0.0)
    linear_time = (time.perf_counter() - start) * 1000

    # FAISS should be faster (or at least comparable for exact search)
    # For IndexFlatIP, they should be similar, but FAISS might be slightly faster
    # due to optimized C++ implementation
    print(f"FAISS: {faiss_time:.2f}ms, Linear: {linear_time:.2f}ms")

    # Both should complete in reasonable time
    assert faiss_time < 100, f"FAISS took {faiss_time:.2f}ms, exceeding 100ms"

    # Results should be similar (same algorithm, different implementation)
    assert len(faiss_results) == len(linear_results), "Should return same number of results"

    # Top result should be the same (or very similar)
    if faiss_results and linear_results:
        # They might differ slightly due to floating point precision, but should be close
        faiss_sim = faiss_results[0].similarity
        linear_sim = linear_results[0].similarity
        assert (
            abs(faiss_sim - linear_sim) < 0.001
        ), f"Top result similarity differs: FAISS={faiss_sim}, Linear={linear_sim}"


@pytest.mark.property
def test_faiss_indexivfflat_performance():
    """
    Test IndexIVFFlat performance for very large collections.
    IndexIVFFlat should be faster than IndexFlatIP for 50K+ faces.
    """
    collection_size = 50000
    dimension = 512

    # Create IndexIVFFlat
    index = FAISSIndex(dimension=dimension, index_type="IndexIVFFlat", nlist=100)

    # Generate embeddings
    np.random.seed(42)
    embeddings = {}
    for i in range(collection_size):
        emb = np.random.rand(dimension).astype(np.float32)
        emb = emb / np.linalg.norm(emb)
        embeddings[f"face_{i}"] = (emb, None)

    # Bulk load (this will train the index)
    start = time.perf_counter()
    index.bulk_load(embeddings)
    build_time = (time.perf_counter() - start) * 1000

    # Build should complete in reasonable time (<30 seconds = 30000ms)
    assert build_time < 30000, f"IndexIVFFlat build took {build_time:.2f}ms, exceeding 30s threshold"

    # Generate query
    query = np.random.rand(dimension).astype(np.float32)
    query = query / np.linalg.norm(query)

    # Measure search time
    start = time.perf_counter()
    results = index.search(query, k=10, threshold=0.0)
    search_time = (time.perf_counter() - start) * 1000

    # Search should be fast (<100ms even for 50K faces)
    assert search_time < 100, (
        f"IndexIVFFlat search took {search_time:.2f}ms for {collection_size} faces, " f"exceeding 100ms threshold"
    )

    # Should return results
    assert len(results) > 0, "Search should return results"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "property"])
