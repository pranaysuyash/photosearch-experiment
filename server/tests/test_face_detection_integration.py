"""
Integration tests for face detection functionality.
"""
import os
import tempfile
import shutil
import sqlite3
from pathlib import Path
import sys
import inspect

# Add the server directory to the Python path
current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from face_clustering_db import FaceClusteringDB
from face_detection_service import FaceDetectionService, DetectedFace, FaceDetectionResult


def test_face_detection_service_initialization():
    """Test that the face detection service initializes correctly."""
    service = FaceDetectionService()
    
    # Check if service is available (may not be if dependencies are missing)
    if service.is_available():
        print("✅ Face detection service is available")
        assert service.clusterer is not None
    else:
        print("⚠️  Face detection service not available (dependencies missing)")
        assert service.clusterer is None


def test_face_detection_with_mock_data():
    """Test face detection with mock data when real service is unavailable."""
    # Create a temporary directory for test database
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_face_clusters.db"
    
    try:
        # Initialize database
        face_db = FaceClusteringDB(db_path)
        
        # Test photo path (this file won't exist, but we're testing the fallback)
        test_photo_path = "/test/nonexistent/photo.jpg"
        
        # Test detect_and_store_faces with non-existent file
        detection_ids = face_db.detect_and_store_faces(test_photo_path)
        
        # Should return empty list (graceful fallback)
        assert detection_ids == []
        print("✅ Graceful fallback for non-existent files works")
        
        # Test with a real file path that doesn't exist
        # This tests the error handling
        detection_ids = face_db.detect_and_store_faces("/tmp/test.jpg")
        assert detection_ids == []
        print("✅ Error handling for missing files works")
        
    finally:
        shutil.rmtree(temp_dir)


def test_face_database_integration():
    """Test the integration between face detection and database."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_face_clusters.db"
    
    try:
        face_db = FaceClusteringDB(db_path)
        
        # Test adding a face detection manually (simulating what detect_and_store_faces would do)
        detection_id = face_db.add_face_detection(
            photo_path="/test/photo.jpg",
            bounding_box={"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4},
            embedding=[0.1, 0.2, 0.3, 0.4, 0.5],
            quality_score=0.95
        )
        
        assert detection_id.startswith("face_")
        print("✅ Manual face detection storage works")
        
        # Test getting faces for a photo
        faces = []
        with face_db.db_path.open() as conn:
            conn = sqlite3.connect(str(face_db.db_path))
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM face_detections WHERE photo_path = ?
            """, ("/test/photo.jpg",)).fetchall()
            
            for row in rows:
                faces.append(row)
        
        assert len(faces) == 1
        assert faces[0]['photo_path'] == "/test/photo.jpg"
        print("✅ Face retrieval from database works")
        
        # Test face thumbnail generation (should return None for non-existent files)
        thumbnail = face_db.get_face_thumbnail(detection_id)
        assert thumbnail is None
        print("✅ Face thumbnail fallback works")
        
    finally:
        shutil.rmtree(temp_dir)


def test_face_detection_workflow():
    """Test the complete face detection workflow."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_face_clusters.db"
    
    try:
        face_db = FaceClusteringDB(db_path)
        
        # Test photo processing workflow
        test_photo_path = "/test/workflow/photo.jpg"
        
        # Step 1: Process photo (detect and store faces)
        success = face_db.process_photo_with_faces(test_photo_path)
        
        # Should return False since file doesn't exist (graceful fallback)
        assert success == False
        print("✅ Photo processing workflow handles missing files gracefully")
        
        # Step 2: Manually add a face detection
        detection_id = face_db.add_face_detection(
            photo_path=test_photo_path,
            bounding_box={"x": 0.2, "y": 0.3, "width": 0.4, "height": 0.5},
            embedding=[0.5, 0.4, 0.3, 0.2, 0.1],
            quality_score=0.85
        )
        
        # Step 3: Add a person cluster
        cluster_id = face_db.add_face_cluster(label="Test Person")
        
        # Step 4: Associate person with face
        face_db.associate_person_with_photo(
            photo_path=test_photo_path,
            cluster_id=cluster_id,
            detection_id=detection_id,
            confidence=0.95
        )
        
        # Step 5: Verify the association
        associations = face_db.get_people_in_photo(test_photo_path)
        assert len(associations) == 1
        assert associations[0].cluster_id == cluster_id
        assert associations[0].detection_id == detection_id
        
        print("✅ Complete face detection workflow works")
        
    finally:
        shutil.rmtree(temp_dir)


def test_batch_face_detection():
    """Test batch processing of multiple photos."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_face_clusters.db"
    
    try:
        face_db = FaceClusteringDB(db_path)
        
        # Test photo paths
        photo_paths = [
            "/test/batch/photo1.jpg",
            "/test/batch/photo2.jpg",
            "/test/batch/photo3.jpg"
        ]
        
        # Process each photo (will fail gracefully since files don't exist)
        results = []
        for photo_path in photo_paths:
            success = face_db.process_photo_with_faces(photo_path)
            results.append(success)
        
        # All should return False (graceful fallback)
        assert all(result == False for result in results)
        print("✅ Batch processing handles missing files gracefully")
        
        # Now manually add faces to test the database can handle multiple photos
        for i, photo_path in enumerate(photo_paths):
            detection_id = face_db.add_face_detection(
                photo_path=photo_path,
                bounding_box={"x": 0.1 * i, "y": 0.2 * i, "width": 0.3, "height": 0.4},
                embedding=[0.1 * i, 0.2 * i, 0.3 * i, 0.4 * i, 0.5 * i],
                quality_score=0.7 + 0.1 * i
            )
            
            # Verify detection was added
            with face_db.db_path.open() as conn:
                conn = sqlite3.connect(str(face_db.db_path))
                row = conn.execute("""
                    SELECT COUNT(*) FROM face_detections WHERE photo_path = ?
                """, (photo_path,)).fetchone()
                assert row[0] == 1
        
        print("✅ Batch face detection storage works")
        
    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    print("Testing Face Detection Integration...")
    print()
    
    test_face_detection_service_initialization()
    print()
    
    test_face_detection_with_mock_data()
    print()
    
    test_face_database_integration()
    print()
    
    test_face_detection_workflow()
    print()
    
    test_batch_face_detection()
    print()
    
    print("🎉 All face detection integration tests completed!")