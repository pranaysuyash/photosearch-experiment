"""
Tests for the PhotoSearch backend API and LanceDB store.
"""
import pytest
import sys
import os

# Add server module to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from server.lancedb_store import LanceDBStore


class TestLanceDBStore:
    """Tests for LanceDBStore vector store."""
    
    @pytest.fixture
    def store(self, tmp_path):
        """Create a temporary LanceDB store for testing."""
        # Override the settings path for testing
        import server.config as config
        original_path = config.settings.VECTOR_STORE_PATH
        config.settings.VECTOR_STORE_PATH = tmp_path / "test_vector_store"
        
        store = LanceDBStore(table_name="test_photos")
        yield store
        
        # Cleanup
        store.reset()
        config.settings.VECTOR_STORE_PATH = original_path
    
    def test_add_and_search(self, store):
        """Test adding embeddings and searching."""
        # Add test data
        test_embedding = [0.1] * 512  # CLIP embeddings are 512-dim
        store.add("test_image.jpg", test_embedding, {"filename": "test_image.jpg"})
        
        # Verify count
        assert store.get_count() == 1
        
        # Search
        results = store.search(test_embedding, limit=10)
        assert len(results) == 1
        assert results[0]['id'] == "test_image.jpg"
        assert results[0]['score'] > 0.99  # Should be nearly 1.0 for same vector
    
    def test_add_batch(self, store):
        """Test batch adding."""
        ids = [f"image_{i}.jpg" for i in range(10)]
        embeddings = [[0.1 * i] * 512 for i in range(10)]
        metadata = [{"filename": f"image_{i}.jpg"} for i in range(10)]
        
        store.add_batch(ids, embeddings, metadata)
        
        assert store.get_count() == 10
    
    def test_get_all_records_pagination(self, store):
        """Test pagination in get_all_records."""
        # Add 25 items
        ids = [f"image_{i}.jpg" for i in range(25)]
        embeddings = [[0.01 * i] * 512 for i in range(25)]
        metadata = [{"filename": f"image_{i}.jpg"} for i in range(25)]
        store.add_batch(ids, embeddings, metadata)
        
        # Get first page
        page1 = store.get_all_records(limit=10, offset=0)
        assert len(page1) == 10
        
        # Get second page
        page2 = store.get_all_records(limit=10, offset=10)
        assert len(page2) == 10
        
        # Get third page (should have 5 items)
        page3 = store.get_all_records(limit=10, offset=20)
        assert len(page3) == 5
        
        # Verify no overlap
        page1_paths = {r['path'] for r in page1}
        page2_paths = {r['path'] for r in page2}
        assert len(page1_paths & page2_paths) == 0
    
    def test_delete(self, store):
        """Test deletion."""
        store.add("to_delete.jpg", [0.1] * 512, {"filename": "to_delete.jpg"})
        assert store.get_count() == 1
        
        store.delete(["to_delete.jpg"])
        assert store.get_count() == 0
    
    def test_get_all_ids(self, store):
        """Test getting all IDs."""
        ids = ["a.jpg", "b.jpg", "c.jpg"]
        embeddings = [[0.1] * 512 for _ in ids]
        store.add_batch(ids, embeddings)
        
        all_ids = store.get_all_ids()
        assert all_ids == set(ids)


class TestSearchAPI:
    """Tests for the search API endpoint logic."""
    
    def test_is_video_file(self):
        """Test video file detection."""
        from server.main import is_video_file
        
        assert is_video_file("video.mp4") == True
        assert is_video_file("video.mov") == True
        assert is_video_file("video.avi") == True
        assert is_video_file("image.jpg") == False
        assert is_video_file("image.png") == False
    
    def test_apply_sort(self):
        """Test sorting logic."""
        from server.main import apply_sort
        
        results = [
            {"path": "/a.jpg", "metadata": {"date_taken": "2024-01-01", "file_size": 100}},
            {"path": "/b.jpg", "metadata": {"date_taken": "2024-06-01", "file_size": 200}},
            {"path": "/c.jpg", "metadata": {"date_taken": "2024-03-01", "file_size": 50}},
        ]
        
        # Sort by date descending
        sorted_desc = apply_sort(results.copy(), "date_desc")
        assert sorted_desc[0]["path"] == "/b.jpg"
        
        # Sort by date ascending
        sorted_asc = apply_sort(results.copy(), "date_asc")
        assert sorted_asc[0]["path"] == "/a.jpg"
        
        # Sort by size
        sorted_size = apply_sort(results.copy(), "size")
        assert sorted_size[0]["path"] == "/b.jpg"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
