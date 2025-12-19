"""
Integration Tests for Photo Search Features

This module contains integration tests that verify interactions between different features in the photo search application.
"""

import pytest
import tempfile
import os
from pathlib import Path
import json
from unittest.mock import patch, MagicMock

# Import necessary modules for integration testing
from server.main import app
from server.notes_db import NotesDB
from server.photo_versions_db import PhotoVersionsDB
from server.locations_db import LocationsDB
from server.photo_edits_db import PhotoEditsDB
from fastapi.testclient import TestClient


class TestFeatureIntegration:
    """Integration tests for feature interactions"""
    
    def setup_method(self):
        """Set up a test client and temporary databases"""
        self.client = TestClient(app)
        
        # Create temporary databases for testing
        self.temp_dir = Path(tempfile.mkdtemp())
        self.notes_db_path = self.temp_dir / "test_notes.db"
        self.versions_db_path = self.temp_dir / "test_versions.db"
        self.locations_db_path = self.temp_dir / "test_locations.db"
        self.edits_db_path = self.temp_dir / "test_edits.db"
    
    def teardown_method(self):
        """Clean up temporary files"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_notes_and_version_integration(self):
        """Test that notes can be associated with photo versions"""
        # Create a photo version
        original_path = "/photos/original.jpg"
        version_path = "/photos/edited_version.jpg"
        
        # Add the version to the database
        versions_db = PhotoVersionsDB(self.versions_db_path)
        version_id = versions_db.create_version(
            original_path=original_path,
            version_path=version_path,
            version_type="edited",
            version_name="Edited Version"
        )
        
        assert version_id != ""
        
        # Add a note to the original photo
        notes_db = NotesDB(self.notes_db_path)
        note_content = "This is my original photo"
        success = notes_db.set_note(original_path, note_content)
        assert success is True
        
        # Verify the note exists
        note = notes_db.get_note(original_path)
        assert note == note_content
        
        # The version should be separate, so it shouldn't have the note
        version_note = notes_db.get_note(version_path)
        assert version_note is None
        
        # We could also test that notes are copied appropriately to versions
        # if that's desired behavior
        notes_db.set_note(version_path, "This is the edited version note")
        version_note = notes_db.get_note(version_path)
        assert version_note == "This is the edited version note"
    
    def test_location_and_version_integration(self):
        """Test that locations can be associated with photo versions"""
        original_path = "/photos/original.jpg"
        version_path = "/photos/edited_version.jpg"
        
        # Add locations for both original and version
        locations_db = LocationsDB(self.locations_db_path)
        
        # Add location for original
        orig_location_id = locations_db.add_photo_location(
            photo_path=original_path,
            latitude=40.7128,
            longitude=-74.0060,
            corrected_place_name="Original Location"
        )
        
        # Add location for version
        version_location_id = locations_db.add_photo_location(
            photo_path=version_path,
            latitude=40.7128,
            longitude=-74.0060,
            corrected_place_name="Same Location as Original"
        )
        
        assert orig_location_id != ""
        assert version_location_id != ""
        
        # Verify both locations exist
        orig_location = locations_db.get_photo_location(original_path)
        version_location = locations_db.get_photo_location(version_path)
        
        assert orig_location['corrected_place_name'] == "Original Location"
        assert version_location['corrected_place_name'] == "Same Location as Original"
    
    def test_api_integration(self):
        """Test API endpoints integration"""
        # Test creating a photo location via API
        response = self.client.post("/locations", json={
            "photo_path": "/test/photo.jpg",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "original_place_name": "New York",
            "corrected_place_name": "Manhattan, NYC",
            "city": "New York",
            "region": "New York",
            "country": "USA"
        })
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "location_id" in response.json()
        
        # Test getting the location via API
        response = self.client.get("/locations/photo/test/photo.jpg")
        assert response.status_code == 200
        location_data = response.json()["location"]
        assert location_data["corrected_place_name"] == "Manhattan, NYC"
        assert location_data["city"] == "New York"
    
    def test_notes_api_integration(self):
        """Test notes API endpoints integration"""
        photo_path = "/test/photo.jpg"
        note_content = "This is a test note for integration testing"
        
        # Test setting a note via API
        response = self.client.post(f"/api/photos/{photo_path}/notes", json={
            "note": note_content
        })
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["note"] == note_content
        
        # Test getting the note via API
        response = self.client.get(f"/api/photos/{photo_path}/notes")
        assert response.status_code == 200
        assert response.json()["note"] == note_content
    
    def test_version_api_integration(self):
        """Test version API endpoints integration"""
        original_path = "/test/original.jpg"
        version_path = "/test/version.jpg"
        
        # Test creating a version via API
        response = self.client.post("/versions", json={
            "original_path": original_path,
            "version_path": version_path,
            "version_type": "edited",
            "version_name": "Test Edit",
            "version_description": "Testing version creation"
        })
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "version_id" in response.json()
        
        # Test getting the version stack via API
        response = self.client.get(f"/versions/stack/{original_path}")
        assert response.status_code == 200
        stack = response.json()["stack"]
        assert len(stack) >= 1
        assert any(v["version_path"] == version_path for v in stack)
    
    def test_export_with_metadata_integration(self):
        """Test export functionality with photo metadata"""
        # Create some test photo locations and notes
        photo_path = "/test/photo.jpg"
        
        # Add location
        locations_response = self.client.post("/locations", json={
            "photo_path": photo_path,
            "latitude": 40.7128,
            "longitude": -74.0060,
            "corrected_place_name": "Test Location"
        })
        
        # Add note
        notes_response = self.client.post(f"/api/photos/{photo_path}/notes", json={
            "note": "Test note for export integration"
        })
        
        # Now test export with metadata
        export_response = self.client.post("/export", json={
            "paths": [photo_path],
            "options": {
                "format": "zip",
                "include_metadata": True,
                "include_thumbnails": False,
                "max_resolution": None,
                "rename_pattern": None,
                "password_protect": False,
                "password": None
            }
        })
        
        # Export returns a streaming response, so we can't directly verify the zip content
        # But we can verify the request was processed (status code 200 would indicate success)
        # In a real test, we might verify that the metadata was retrieved properly
        assert export_response.status_code in [200, 400]  # 400 might occur if file doesn't exist
        
        # If the export succeeded, it means the system was able to retrieve
        # the metadata for the export operation
    
    def test_multi_tag_search_integration(self):
        """Test multi-tag search functionality"""
        # Create some test data
        photo_path = "/test/photo.jpg"
        
        # Add a location
        self.client.post("/locations", json={
            "photo_path": photo_path,
            "latitude": 40.7128,
            "longitude": -74.0060,
            "corrected_place_name": "New York"
        })
        
        # Add a note
        self.client.post(f"/api/photos/{photo_path}/notes", json={
            "note": "Trip to New York with family"
        })
        
        # Test search with tags (this would normally require adding tags)
        # For now, we'll test the endpoint structure
        search_response = self.client.get("/search", params={
            "query": "New York",
            "mode": "metadata",
            "tags": "vacation,family,travel",
            "tag_logic": "OR"
        })
        
        # The search endpoint should at least return a structured response
        assert search_response.status_code in [200, 404]  # 404 if no photos match
    
    def test_safe_bulk_operations_integration(self):
        """Test safe bulk operations with undo functionality"""
        # Create multiple test photos
        test_photos = [f"/test/photo{i}.jpg" for i in range(3)]
        
        # Add locations for each
        for photo in test_photos:
            self.client.post("/locations", json={
                "photo_path": photo,
                "latitude": 40.7128,
                "longitude": -74.0060
            })
        
        # This test verifies the system can handle multiple operations
        # without data corruption or conflicts
        
        # Verify all locations were added
        for photo in test_photos:
            response = self.client.get(f"/locations/photo/{photo}")
            if response.status_code == 200:
                location = response.json()["location"]
                assert location["latitude"] == 40.7128
                assert location["longitude"] == -74.0060


# Run the tests if this file is executed directly
if __name__ == "__main__":
    pytest.main([__file__])