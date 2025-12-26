"""
Integration tests for the people API endpoints.
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

from face_clustering_db import FaceClusteringDB


def test_people_api_integration():
    """Test the people API endpoints integration."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_face_clusters.db"

    try:
        # Initialize database
        face_db = FaceClusteringDB(db_path)

        # Create a test cluster (person)
        cluster_id = face_db.add_face_cluster(label="Test Person")

        # Test photo path
        test_photo_path = "/test/integration/photo.jpg"

        # Test adding a detection
        detection_id = face_db.add_face_detection(
            photo_path=test_photo_path,
            bounding_box={"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4},
        )

        # Test associating person with photo
        face_db.associate_person_with_photo(
            photo_path=test_photo_path,
            cluster_id=cluster_id,
            detection_id=detection_id,
            confidence=0.98,
        )

        # Test getting people in photo (simulates GET /api/photos/{photo_path}/people)
        associations = face_db.get_people_in_photo(test_photo_path)
        assert len(associations) == 1
        assert associations[0].cluster_id == cluster_id

        # Test adding person to photo (simulates POST /api/photos/{photo_path}/people)
        face_db.add_person_to_photo(test_photo_path, cluster_id, detection_id, confidence=0.99)
        associations = face_db.get_people_in_photo(test_photo_path)
        assert associations[0].confidence == 0.99

        # Test removing person from photo (simulates DELETE /api/photos/{photo_path}/people/{person_id})
        face_db.remove_person_from_photo(test_photo_path, cluster_id, detection_id)
        associations = face_db.get_people_in_photo(test_photo_path)
        assert len(associations) == 0

        print("✅ People API integration test passed!")

    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    test_people_api_integration()
    print("🎉 People API integration test completed successfully!")
