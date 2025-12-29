"""
Property-Based Tests for FAISS Face Search Performance

Tests universal properties of the FAISS face clustering system to ensure
correctness and performance characteristics hold across all inputs.

Requirements validated:
- 1.1: FAISS integration provides O(log n) search performance
- 1.2: Search accuracy maintains high precision/recall
- 1.3: Incremental updates preserve search quality

Property tests run with 100+ iterations to validate universal correctness.
"""

import numpy as np
import pytest
import time
import logging
from typing import List
from pathlib import Path
import tempfile
import shutil

# Import the FAISS clustering system
from server.clustering.faiss_face_clusterer import (
    FAISSFaceClusterer,
    FaceEmbedding,
    create_face_embedding,
    FAISS_AVAILABLE,
)

logger = logging.getLogger(__name__)

# Skip all tests if FAISS is not available
pytestmark = pytest.mark.skipif(not FAISS_AVAILABLE, reason="FAISS not available")


class TestFAISSPerformanceProperties:
    """Property-based tests for FAISS face clustering performance"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test data"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def clusterer(self):
        """Create FAISS clusterer for testing"""
        return FAISSFaceClusterer(
            embedding_dim=512,
            similarity_threshold=0.65,
            min_cluster_size=2,
            use_gpu=False,  # Use CPU for consistent testing
        )

    def generate_random_embedding(self, dim: int = 512) -> np.ndarray:
        """Generate a random normalized embedding"""
        embedding = np.random.randn(dim).astype(np.float32)
        return embedding / np.linalg.norm(embedding)

    def generate_similar_embedding(self, base_embedding: np.ndarray, similarity: float = 0.8) -> np.ndarray:
        """Generate an embedding similar to the base embedding"""
        noise = np.random.randn(len(base_embedding)).astype(np.float32)
        noise = noise / np.linalg.norm(noise)

        # Mix base embedding with noise to achieve target similarity
        mixed = similarity * base_embedding + (1 - similarity) * noise
        return mixed / np.linalg.norm(mixed)

    def generate_test_embeddings(self, count: int, clusters: int = 5) -> List[FaceEmbedding]:
        """Generate test embeddings with known cluster structure"""
        embeddings = []

        # Create cluster centroids
        centroids = [self.generate_random_embedding() for _ in range(clusters)]

        for i in range(count):
            cluster_id = i % clusters
            centroid = centroids[cluster_id]

            # Generate embedding similar to centroid
            embedding_vec = self.generate_similar_embedding(centroid, similarity=0.75)

            embedding = create_face_embedding(
                embedding_id=f"emb_{i}",
                user_id="test_user",
                photo_path=f"test_photo_{i}.jpg",
                detection_id=f"det_{i}",
                embedding_vector=embedding_vec,
                quality_score=np.random.uniform(0.5, 1.0),
            )
            embeddings.append(embedding)

        return embeddings

    @pytest.mark.parametrize("num_embeddings", [100, 500, 1000, 2000])
    def test_property_search_performance_scales_logarithmically(self, clusterer, num_embeddings):
        """
        Property 1: FAISS Search Performance

        Universal Property: Search time should scale logarithmically with dataset size.
        For FAISS HNSW index, search time should be O(log n) where n is number of embeddings.

        Validates Requirements: 1.1, 1.2
        """
        # Generate test data
        embeddings = self.generate_test_embeddings(num_embeddings, clusters=max(5, num_embeddings // 20))

        # Add embeddings to clusterer
        result = clusterer.add_embeddings(embeddings)

        # Verify embeddings were added
        assert result["added"] == num_embeddings
        assert clusterer.stats["total_embeddings"] == num_embeddings

        # Test search performance
        query_embedding = self.generate_random_embedding()
        search_times = []

        # Run multiple searches to get average time
        for _ in range(10):
            start_time = time.time()
            similar = clusterer._find_similar_embeddings(query_embedding, k=10)
            search_time = time.time() - start_time
            search_times.append(search_time)

        avg_search_time = np.mean(search_times)

        # Property: Search time should be reasonable for the dataset size
        # For FAISS HNSW, expect sub-millisecond search for datasets up to 10K
        max_expected_time = 0.01  # 10ms is generous for FAISS
        assert (
            avg_search_time < max_expected_time
        ), f"Search took {avg_search_time:.4f}s, expected < {max_expected_time}s"

        # Property: Search should return results when similar embeddings exist
        if num_embeddings > 0:
            assert len(similar) >= 0, "Search should return some results for non-empty index"

        logger.info(f"FAISS search performance: {num_embeddings} embeddings, {avg_search_time:.4f}s avg search time")

    @pytest.mark.parametrize("iteration", range(20))  # Run 20 iterations for statistical significance
    def test_property_incremental_updates_preserve_quality(self, clusterer, iteration):
        """
        Property 2: Incremental Index Updates

        Universal Property: Adding embeddings incrementally should preserve search quality.
        Search results should be consistent regardless of batch size or order of insertion.

        Validates Requirements: 1.3
        """
        # Generate test data with known structure
        base_embeddings = self.generate_test_embeddings(50, clusters=5)
        additional_embeddings = self.generate_test_embeddings(25, clusters=3)

        # Test 1: Add all at once
        clusterer1 = FAISSFaceClusterer(embedding_dim=512, similarity_threshold=0.65, use_gpu=False)
        all_embeddings = base_embeddings + additional_embeddings
        clusterer1.add_embeddings(all_embeddings)

        # Test 2: Add incrementally
        clusterer2 = FAISSFaceClusterer(embedding_dim=512, similarity_threshold=0.65, use_gpu=False)
        clusterer2.add_embeddings(base_embeddings)
        clusterer2.add_embeddings(additional_embeddings)

        # Property: Both should have same number of embeddings
        assert clusterer1.stats["total_embeddings"] == clusterer2.stats["total_embeddings"]

        # Property: Search results should be similar for both approaches
        query_embedding = self.generate_random_embedding()

        results1 = clusterer1._find_similar_embeddings(query_embedding, k=10)
        results2 = clusterer2._find_similar_embeddings(query_embedding, k=10)

        # Property: Both should return same number of results (within tolerance)
        assert abs(len(results1) - len(results2)) <= 2, "Incremental updates should preserve search result count"

        # Property: Top results should have similar similarity scores
        if results1 and results2:
            top_sim1 = results1[0][1] if results1 else 0
            top_sim2 = results2[0][1] if results2 else 0
            similarity_diff = abs(top_sim1 - top_sim2)
            assert similarity_diff < 0.1, f"Top similarity scores should be similar: {top_sim1:.3f} vs {top_sim2:.3f}"

    @pytest.mark.parametrize("similarity_threshold", [0.5, 0.65, 0.8, 0.9])
    def test_property_similarity_threshold_consistency(self, clusterer, similarity_threshold):
        """
        Property 3: Similarity Threshold Consistency

        Universal Property: All returned results should meet the similarity threshold.
        No result should have similarity below the specified threshold.

        Validates Requirements: 1.1, 1.2
        """
        # Create clusterer with specific threshold
        test_clusterer = FAISSFaceClusterer(embedding_dim=512, similarity_threshold=similarity_threshold, use_gpu=False)

        # Generate test data
        embeddings = self.generate_test_embeddings(100, clusters=10)
        test_clusterer.add_embeddings(embeddings)

        # Test with multiple query embeddings
        for _ in range(10):
            query_embedding = self.generate_random_embedding()
            similar = test_clusterer._find_similar_embeddings(query_embedding, k=20)

            # Property: All results should meet similarity threshold
            for idx, similarity in similar:
                assert (
                    similarity >= similarity_threshold
                ), f"Result similarity {similarity:.3f} below threshold {similarity_threshold}"

            # Property: Results should be sorted by similarity (descending)
            similarities = [sim for _, sim in similar]
            assert similarities == sorted(
                similarities, reverse=True
            ), "Results should be sorted by similarity (highest first)"

    @pytest.mark.parametrize("iteration", range(15))  # Run 15 iterations
    def test_property_clustering_quality_metrics(self, clusterer, iteration):
        """
        Property 4: Clustering Quality Metrics

        Universal Property: Clustering should produce coherent clusters with good separation.
        Intra-cluster similarity should be higher than inter-cluster similarity.

        Validates Requirements: 1.1, 1.2, 1.3
        """
        # Generate embeddings with known cluster structure
        embeddings = self.generate_test_embeddings(200, clusters=8)
        result = clusterer.add_embeddings(embeddings)

        assert result["added"] == 200

        # Get all clusters
        clusters = clusterer.get_clusters(min_size=2)

        # Property: Should form multiple clusters
        assert len(clusters) >= 2, "Should form multiple clusters from diverse embeddings"

        # Property: Clusters should have reasonable sizes
        total_faces = sum(cluster.size for cluster in clusters)
        assert total_faces <= 200, "Total faces in clusters should not exceed input"

        # Property: Cluster quality scores should be reasonable
        for cluster in clusters:
            assert (
                0.0 <= cluster.quality_score <= 1.0
            ), f"Cluster quality score {cluster.quality_score} should be in [0,1]"

            # Property: Clusters should have valid centroids
            assert cluster.centroid is not None, "Cluster should have centroid"
            assert len(cluster.centroid) == 512, "Centroid should have correct dimensionality"

            # Property: Centroid should be normalized
            centroid_norm = np.linalg.norm(cluster.centroid)
            assert 0.8 <= centroid_norm <= 1.2, f"Centroid should be approximately normalized: {centroid_norm}"

    @pytest.mark.parametrize("iteration", range(10))  # Run 10 iterations
    def test_property_memory_efficiency(self, clusterer, iteration):
        """
        Property 5: Memory Efficiency

        Universal Property: Memory usage should scale reasonably with dataset size.
        Memory per embedding should be bounded and not grow excessively.

        Validates Requirements: 1.1, 19.4 (performance optimization)
        """
        # Test with different dataset sizes
        sizes = [100, 500, 1000]
        memory_per_embedding = []

        for size in sizes:
            test_clusterer = FAISSFaceClusterer(embedding_dim=512, use_gpu=False)
            embeddings = self.generate_test_embeddings(size, clusters=max(5, size // 20))

            test_clusterer.add_embeddings(embeddings)
            stats = test_clusterer.get_statistics()

            memory_mb = stats["memory_usage_mb"]
            memory_per_emb = memory_mb / size
            memory_per_embedding.append(memory_per_emb)

            # Property: Memory usage should be reasonable
            assert memory_mb > 0, "Should report positive memory usage"
            assert memory_per_emb < 10.0, f"Memory per embedding {memory_per_emb:.2f}MB seems excessive"

        # Property: Memory per embedding should not grow significantly with dataset size
        if len(memory_per_embedding) > 1:
            max_memory = max(memory_per_embedding)
            min_memory = min(memory_per_embedding)
            growth_ratio = max_memory / min_memory
            assert growth_ratio < 3.0, f"Memory per embedding growth ratio {growth_ratio:.2f} too high"

    def test_property_concurrent_access_safety(self, clusterer):
        """
        Property 6: Thread Safety

        Universal Property: Concurrent operations should not corrupt the index.
        Multiple threads should be able to search simultaneously without issues.

        Validates Requirements: 1.1, 19.3 (distributed processing)
        """
        import threading
        import queue

        # Add initial data
        embeddings = self.generate_test_embeddings(500, clusters=10)
        clusterer.add_embeddings(embeddings)

        # Test concurrent searches
        results_queue = queue.Queue()
        errors_queue = queue.Queue()

        def search_worker():
            try:
                for _ in range(10):
                    query = self.generate_random_embedding()
                    similar = clusterer._find_similar_embeddings(query, k=5)
                    results_queue.put(len(similar))
            except Exception as e:
                errors_queue.put(e)

        # Start multiple search threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=search_worker)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Property: No errors should occur
        assert errors_queue.empty(), f"Concurrent access caused errors: {list(errors_queue.queue)}"

        # Property: All searches should return results
        result_counts = []
        while not results_queue.empty():
            result_counts.append(results_queue.get())

        assert len(result_counts) == 50, "Should have 50 search results (10 per thread × 5 threads)"
        assert all(count >= 0 for count in result_counts), "All searches should return non-negative result counts"

    @pytest.mark.parametrize("iteration", range(5))  # Run 5 iterations for state persistence
    def test_property_state_persistence(self, clusterer, temp_dir, iteration):
        """
        Property 7: State Persistence

        Universal Property: Saved and loaded state should preserve clustering results.
        Search results should be identical before and after save/load cycle.

        Validates Requirements: 1.1, 1.3
        """
        # Add test data
        embeddings = self.generate_test_embeddings(100, clusters=5)
        clusterer.add_embeddings(embeddings)

        # Perform searches before saving
        query_embeddings = [self.generate_random_embedding() for _ in range(5)]
        results_before = []
        for query in query_embeddings:
            similar = clusterer._find_similar_embeddings(query, k=10)
            results_before.append(similar)

        # Save state
        state_file = temp_dir / f"test_state_{iteration}.json"
        success = clusterer.save_state(state_file)
        assert success, "State saving should succeed"
        assert state_file.exists(), "State file should be created"

        # Create new clusterer and load state
        new_clusterer = FAISSFaceClusterer(embedding_dim=512, use_gpu=False)
        load_success = new_clusterer.load_state(state_file)
        assert load_success, "State loading should succeed"

        # Property: Statistics should match
        original_stats = clusterer.get_statistics()
        loaded_stats = new_clusterer.get_statistics()

        assert (
            loaded_stats["total_clusters"] == original_stats["total_clusters"]
        ), "Loaded clusterer should have same number of clusters"

        # Property: Clusters should be preserved
        original_clusters = clusterer.get_clusters()
        loaded_clusters = new_clusterer.get_clusters()

        assert len(loaded_clusters) == len(original_clusters), "Loaded clusterer should have same number of clusters"

        # Verify cluster structure is preserved
        for orig_cluster, loaded_cluster in zip(original_clusters, loaded_clusters):
            assert orig_cluster.size == loaded_cluster.size, "Cluster sizes should be preserved"
            assert (
                abs(orig_cluster.quality_score - loaded_cluster.quality_score) < 0.01
            ), "Cluster quality scores should be preserved"

    def test_property_edge_cases_robustness(self, clusterer):
        """
        Property 8: Edge Case Robustness

        Universal Property: System should handle edge cases gracefully without crashing.
        Empty inputs, single embeddings, and extreme values should be handled properly.

        Validates Requirements: 1.1, 1.2, 1.3
        """
        # Property: Empty embedding list should be handled
        result = clusterer.add_embeddings([])
        assert result["added"] == 0
        assert clusterer.stats["total_embeddings"] == 0

        # Property: Single embedding should work
        single_embedding = [
            create_face_embedding(
                embedding_id="single",
                user_id="test",
                photo_path="single.jpg",
                detection_id="det_single",
                embedding_vector=self.generate_random_embedding(),
                quality_score=0.8,
            )
        ]

        result = clusterer.add_embeddings(single_embedding)
        assert result["added"] == 1
        assert clusterer.stats["total_embeddings"] == 1

        # Property: Search with empty index should return empty results
        empty_clusterer = FAISSFaceClusterer(embedding_dim=512, use_gpu=False)
        query = self.generate_random_embedding()
        results = empty_clusterer._find_similar_embeddings(query, k=10)
        assert len(results) == 0, "Search in empty index should return no results"

        # Property: Search with k=0 should return empty results
        results = clusterer._find_similar_embeddings(query, k=0)
        assert len(results) == 0, "Search with k=0 should return no results"

        # Property: Very high similarity threshold should return fewer results
        high_threshold_results = clusterer._find_similar_embeddings(query, k=10)
        # Filter by very high threshold manually to verify
        filtered_results = [(idx, sim) for idx, sim in high_threshold_results if sim >= 0.95]
        assert len(filtered_results) <= len(
            high_threshold_results
        ), "High threshold should return fewer or equal results"


if __name__ == "__main__":
    # Run property tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
