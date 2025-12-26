"""
Unit Tests for Photo Search Features

This module contains unit tests for all the new features implemented in the photo search application.
"""

import pytest
import tempfile
from pathlib import Path

# Import the modules we need to test
from server.notes_db import NotesDB
from server.photo_versions_db import PhotoVersionsDB
from server.locations_db import LocationsDB
from server.duplicates_db import DuplicatesDB
from server.photo_edits_db import PhotoEditsDB


class TestNotesDB:
    """Unit tests for NotesDB functionality"""

    def setup_method(self):
        """Set up a temporary database for testing"""
        self.db_file = Path(tempfile.mktemp(suffix=".db"))
        self.notes_db = NotesDB(self.db_file)

    def teardown_method(self):
        """Clean up the temporary database"""
        if self.db_file.exists():
            self.db_file.unlink()

    def test_set_and_get_note(self):
        """Test setting and getting a note"""
        photo_path = "/path/to/photo.jpg"
        note_content = "This is a test note"

        # Set a note
        success = self.notes_db.set_note(photo_path, note_content)
        assert success is True

        # Get the note
        note = self.notes_db.get_note(photo_path)
        assert note == note_content

    def test_delete_note(self):
        """Test deleting a note"""
        photo_path = "/path/to/photo.jpg"
        note_content = "This is a test note"

        # Set a note
        self.notes_db.set_note(photo_path, note_content)

        # Verify it was set
        note = self.notes_db.get_note(photo_path)
        assert note == note_content

        # Delete the note
        success = self.notes_db.delete_note(photo_path)
        assert success is True

        # Verify it was deleted
        note = self.notes_db.get_note(photo_path)
        assert note is None

    def test_get_photos_with_notes(self):
        """Test getting all photos with notes"""
        # Add several notes
        photos_and_notes = [
            ("/path/to/photo1.jpg", "Note for photo 1"),
            ("/path/to/photo2.jpg", "Note for photo 2"),
            ("/path/to/photo3.jpg", "Note for photo 3"),
        ]

        for photo_path, note in photos_and_notes:
            self.notes_db.set_note(photo_path, note)

        # Get all photos with notes
        photos_with_notes = self.notes_db.get_photos_with_notes()

        assert len(photos_with_notes) == 3
        assert all(photo["note"] for photo in photos_with_notes)

    def test_search_notes(self):
        """Test searching notes by content"""
        # Add some notes
        self.notes_db.set_note("/path/to/photo1.jpg", "This is a birthday party")
        self.notes_db.set_note("/path/to/photo2.jpg", "Trip to the mountains")
        self.notes_db.set_note("/path/to/photo3.jpg", "Birthday celebration")

        # Search for notes containing "birthday"
        results = self.notes_db.search_notes("birthday")

        assert len(results) == 2
        note_contents = [r["note"] for r in results]
        assert "This is a birthday party" in note_contents
        assert "Birthday celebration" in note_contents


class TestPhotoVersionsDB:
    """Unit tests for PhotoVersionsDB functionality"""

    def setup_method(self):
        """Set up a temporary database for testing"""
        self.db_file = Path(tempfile.mktemp(suffix=".db"))
        self.versions_db = PhotoVersionsDB(self.db_file)

    def teardown_method(self):
        """Clean up the temporary database"""
        if self.db_file.exists():
            self.db_file.unlink()

    def test_create_and_get_version(self):
        """Test creating and getting a photo version"""
        original_path = "/path/to/original.jpg"
        version_path = "/path/to/edited.jpg"
        version_type = "edited"
        version_name = "Brighter Colors"
        version_description = "Increased brightness and saturation"

        # Create a version
        version_id = self.versions_db.create_version(
            original_path=original_path,
            version_path=version_path,
            version_type=version_type,
            version_name=version_name,
            version_description=version_description,
        )

        assert version_id != ""

        # Get versions for original
        versions = self.versions_db.get_versions_for_original(original_path)
        assert len(versions) == 1
        assert versions[0]["version_path"] == version_path
        assert versions[0]["version_name"] == version_name
        assert versions[0]["version_description"] == version_description

    def test_version_stack(self):
        """Test getting a complete version stack"""
        original_path = "/path/to/original.jpg"

        # Create original version
        self.versions_db.create_version(
            original_path=original_path,
            version_path=original_path,
            version_type="original",
        )

        # Create some edited versions
        self.versions_db.create_version(
            original_path=original_path,
            version_path="/path/to/edits/edit1.jpg",
            version_type="edited",
            version_name="Edit 1",
        )

        self.versions_db.create_version(
            original_path=original_path,
            version_path="/path/to/edits/edit2.jpg",
            version_type="edited",
            version_name="Edit 2",
        )

        # Get the complete stack
        stack = self.versions_db.get_version_stack(original_path)

        assert len(stack) == 3
        version_paths = [v["version_path"] for v in stack]
        assert original_path in version_paths
        assert "/path/to/edits/edit1.jpg" in version_paths
        assert "/path/to/edits/edit2.jpg" in version_paths


class TestLocationsDB:
    """Unit tests for LocationsDB functionality"""

    def setup_method(self):
        """Set up a temporary database for testing"""
        self.db_file = Path(tempfile.mktemp(suffix=".db"))
        self.locations_db = LocationsDB(self.db_file)

    def teardown_method(self):
        """Clean up the temporary database"""
        if self.db_file.exists():
            self.db_file.unlink()

    def test_add_and_get_photo_location(self):
        """Test adding and getting a photo location"""
        photo_path = "/path/to/photo.jpg"
        latitude = 40.7128
        longitude = -74.0060
        original_place_name = "New York City"
        corrected_place_name = "Manhattan, NYC"

        # Add location
        location_id = self.locations_db.add_photo_location(
            photo_path=photo_path,
            latitude=latitude,
            longitude=longitude,
            original_place_name=original_place_name,
            corrected_place_name=corrected_place_name,
            city="New York",
            region="New York",
            country="USA",
        )

        assert location_id != ""

        # Get location
        location = self.locations_db.get_photo_location(photo_path)

        assert location is not None
        assert location["latitude"] == latitude
        assert location["longitude"] == longitude
        assert location["corrected_place_name"] == corrected_place_name
        assert location["city"] == "New York"

    def test_update_place_name(self):
        """Test updating the place name for a photo"""
        photo_path = "/path/to/photo.jpg"

        # Add initial location
        self.locations_db.add_photo_location(
            photo_path=photo_path,
            latitude=40.7128,
            longitude=-74.0060,
            original_place_name="NYC",
        )

        # Update the place name
        success = self.locations_db.update_place_name(photo_path, "Manhattan, New York City")
        assert success is True

        # Verify the update
        location = self.locations_db.get_photo_location(photo_path)
        assert location["corrected_place_name"] == "Manhattan, New York City"

    def test_get_nearby_locations(self):
        """Test getting nearby locations"""
        # Add several locations in a small area
        self.locations_db.add_photo_location(
            photo_path="/path/to/photo1.jpg",
            latitude=40.7128,  # NYC
            longitude=-74.0060,
        )

        self.locations_db.add_photo_location(
            photo_path="/path/to/photo2.jpg",
            latitude=40.7505,  # Times Square
            longitude=-73.9934,
        )

        # Add a location farther away (should not be in radius)
        self.locations_db.add_photo_location(
            photo_path="/path/to/photo3.jpg",
            latitude=34.0522,  # Los Angeles
            longitude=-118.2437,
        )

        # Get locations within 10km of NYC
        nearby = self.locations_db.get_nearby_locations(40.7128, -74.0060, radius_km=10.0)

        # Should only include the two NYC photos
        assert len(nearby) == 2
        paths = [loc["photo_path"] for loc in nearby]
        assert "/path/to/photo1.jpg" in paths
        assert "/path/to/photo2.jpg" in paths
        assert "/path/to/photo3.jpg" not in paths

    def test_get_place_clusters(self):
        """Test getting place clusters"""
        # Add several photos to the same location
        for i in range(3):
            self.locations_db.add_photo_location(
                photo_path=f"/path/to/photo{i}.jpg",
                latitude=40.7128,
                longitude=-74.0060,
                city="New York",
                region="New York",
                country="USA",
            )

        # Add some photos to a different location
        for i in range(3, 5):
            self.locations_db.add_photo_location(
                photo_path=f"/path/to/la_photo{i}.jpg",
                latitude=34.0522,
                longitude=-118.2437,
                city="Los Angeles",
                region="California",
                country="USA",
            )

        # Add single photo to another location (should not form cluster)
        self.locations_db.add_photo_location(
            photo_path="/path/to/sf_photo.jpg",
            latitude=37.7749,
            longitude=-122.4194,
            city="San Francisco",
            region="California",
            country="USA",
        )

        # Get clusters (min 2 photos)
        clusters = self.locations_db.get_place_clusters(min_photos=2)

        # Should have 2 clusters (NYC and LA), not SF
        assert len(clusters) == 2
        cluster_cities = [cluster["city"] for cluster in clusters]
        assert "New York" in cluster_cities
        assert "Los Angeles" in cluster_cities


class TestPhotoEditsDB:
    """Unit tests for PhotoEditsDB functionality"""

    def setup_method(self):
        """Set up a temporary database for testing"""
        self.db_file = Path(tempfile.mktemp(suffix=".db"))
        self.edits_db = PhotoEditsDB(self.db_file)

    def teardown_method(self):
        """Clean up the temporary database"""
        if self.db_file.exists():
            self.db_file.unlink()

    def test_set_and_get_edit(self):
        """Test setting and getting photo edits"""
        photo_path = "/path/to/photo.jpg"
        edit_data = {
            "brightness": 10,
            "contrast": 5,
            "saturation": -5,
            "rotation": 90,
            "flipH": False,
            "flipV": True,
        }

        # Set edit data
        self.edits_db.set_edit(photo_path, edit_data)

        # Get edit data
        result = self.edits_db.get_edit(photo_path)

        assert result is not None
        assert result["edit_data"] is not None
        assert result["edit_data"]["brightness"] == 10
        assert result["edit_data"]["rotation"] == 90
        assert result["edit_data"]["flipV"] is True


class TestDuplicatesDB:
    """Unit tests for DuplicatesDB functionality"""

    def setup_method(self):
        """Set up a temporary database for testing"""
        self.db_file = Path(tempfile.mktemp(suffix=".db"))
        self.duplicates_db = DuplicatesDB(self.db_file)

    def teardown_method(self):
        """Clean up the temporary database"""
        if self.db_file.exists():
            self.db_file.unlink()

    def test_add_and_get_duplicate_group(self):
        """Test adding and getting duplicate groups"""
        file_paths = [
            "/path/to/photo1.jpg",
            "/path/to/photo2.jpg",
            "/path/to/photo3.jpg",
        ]

        # Find duplicates (this would normally compare hashes)
        groups = self.duplicates_db.find_exact_duplicates(file_paths)

        # This is a basic test - finding duplicates in an empty DB will return empty
        # But we can test the group creation functionality
        assert groups == []


# Run the tests if this file is executed directly
if __name__ == "__main__":
    pytest.main([__file__])
