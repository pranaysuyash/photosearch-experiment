"""
Test cases for the face clustering database module.
"""
import os
import tempfile
import shutil
from pathlib import Path
import sys
import inspect

# Add the server directory to the Python path
current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from face_clustering_db import FaceClusteringDB, FaceDetection, FaceCluster, PhotoPersonAssociation


def test_face_clustering_db_basic_operations():
    """Test basic database operations for face clustering."""
    # Create a temporary directory for the test database
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_face_clusters.db"
    
    try:
        # Initialize database
        face_db = FaceClusteringDB(db_path)
        
        # Test adding a face cluster (person)
        cluster_id = face_db.add_face_cluster(label="Test Person")
        assert cluster_id.startswith("cluster_")
        
        # Test adding a face detection
        detection_id = face_db.add_face_detection(
            photo_path="/test/photo.jpg",
            bounding_box={"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4},
            embedding=[0.1, 0.2, 0.3],
            quality_score=0.95
        )
        assert detection_id.startswith("face_")
        
        # Test associating person with photo
        face_db.associate_person_with_photo(
            photo_path="/test/photo.jpg",
            cluster_id=cluster_id,
            detection_id=detection_id,
            confidence=0.98
        )
        
        # Test getting people in photo
        associations = face_db.get_people_in_photo("/test/photo.jpg")
        assert len(associations) == 1
        assert associations[0].cluster_id == cluster_id
        assert associations[0].detection_id == detection_id
        assert associations[0].confidence == 0.98
        
        # Test adding person to photo (should update if already exists)
        face_db.add_person_to_photo("/test/photo.jpg", cluster_id, detection_id, confidence=0.99)
        associations = face_db.get_people_in_photo("/test/photo.jpg")
        assert associations[0].confidence == 0.99
        
        # Test removing person from photo
        face_db.remove_person_from_photo("/test/photo.jpg", cluster_id, detection_id)
        associations = face_db.get_people_in_photo("/test/photo.jpg")
        assert len(associations) == 0
        
        # Test getting all clusters
        clusters = face_db.get_all_clusters()
        assert len(clusters) == 1
        assert clusters[0].cluster_id == cluster_id
        assert clusters[0].label == "Test Person"
        
        # Test updating cluster label
        face_db.update_cluster_label(cluster_id, "Updated Name")
        clusters = face_db.get_all_clusters()
        assert clusters[0].label == "Updated Name"
        
        print("✅ All basic operations tests passed!")
        
    finally:
        # Clean up
        shutil.rmtree(temp_dir)


def test_face_clustering_db_edge_cases():
    """Test edge cases and error handling."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_face_clusters.db"
    
    try:
        face_db = FaceClusteringDB(db_path)
        
        # Test getting people from non-existent photo
        associations = face_db.get_people_in_photo("/nonexistent/photo.jpg")
        assert len(associations) == 0
        
        # Test removing non-existent association (should not raise error)
        face_db.remove_person_from_photo("/test/photo.jpg", "nonexistent_cluster", "nonexistent_detection")
        
        # Test cleanup of missing photos
        face_db.add_face_detection("/missing/photo.jpg", {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4})
        cluster_id = face_db.add_face_cluster()
        detection_id = face_db.add_face_detection("/missing/photo.jpg", {"x": 0.2, "y": 0.3, "width": 0.4, "height": 0.5})  # Different bounding box
        face_db.associate_person_with_photo("/missing/photo.jpg", cluster_id, detection_id, 0.9)
        
        cleaned_count = face_db.cleanup_missing_photos()
        assert cleaned_count == 1
        
        print("✅ All edge case tests passed!")
        
    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    test_face_clustering_db_basic_operations()
    test_face_clustering_db_edge_cases()
    print("🎉 All face clustering database tests completed successfully!")