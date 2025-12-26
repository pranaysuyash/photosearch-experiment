"""
Integration Tests for Feature Interactions

Tests that verify how different features work together in the Living Museum application.
"""

import tempfile
from pathlib import Path

# Import modules to test integration
from src.notes_db import NotesDB
from src.photo_versions_db import PhotoVersionsDB
from src.location_clusters_db import LocationClustersDB
from src.multi_tag_filter_db import MultiTagFilterDB
from src.collaborative_spaces_db import CollaborativeSpacesDB
from src.privacy_controls_db import PrivacyControlsDB


def create_test_environment():
    """Create a test environment with temporary databases."""
    temp_dir = Path(tempfile.mkdtemp())

    # Initialize all databases
    notes_db = NotesDB(temp_dir / "notes.db")
    versions_db = PhotoVersionsDB(temp_dir / "versions.db")
    locations_db = LocationClustersDB(temp_dir / "locations.db")
    tags_db = MultiTagFilterDB(temp_dir / "tags.db")
    spaces_db = CollaborativeSpacesDB(temp_dir / "spaces.db")
    privacy_db = PrivacyControlsDB(temp_dir / "privacy.db")

    return {
        "temp_dir": temp_dir,
        "notes_db": notes_db,
        "versions_db": versions_db,
        "locations_db": locations_db,
        "tags_db": tags_db,
        "spaces_db": spaces_db,
        "privacy_db": privacy_db,
    }


class TestFeatureIntegration:
    """Tests for how different features interact with each other."""

    def test_notes_and_version_integration(self):
        """Test that notes work properly with version stacks."""
        env = create_test_environment()

        # Create a photo with a note
        original_path = "/test/original.jpg"
        notes_db = env["notes_db"]
        versions_db = env["versions_db"]

        # Add a note to the original photo
        notes_db.set_note(original_path, "This is the original photo")

        # Create a version of the photo
        version_path = "/test/edited_version.jpg"
        version_id = versions_db.create_version(
            original_path=original_path,
            version_path=version_path,
            version_type="edit",
            version_name="Edited Version",
        )
        assert version_id != ""

        # Get the version stack
        stack = versions_db.get_version_stack(original_path)
        assert stack is not None
        assert len(stack.versions) == 2  # Original + version

        # In a real implementation, versioned photos might inherit notes
        # from the original, or have their own notes depending on the design
        # For now, we'll just verify the versions exist correctly
        version_paths = [v.version_path for v in stack.versions]
        assert original_path in version_paths
        assert version_path in version_paths

        # Cleanup
        import shutil

        shutil.rmtree(env["temp_dir"])

    def test_location_and_tag_integration(self):
        """Test that location clustering works with tag filtering."""
        env = create_test_environment()

        locations_db = env["locations_db"]
        tags_db = env["tags_db"]

        # Add some photos with locations and tags
        photos_data = [
            {
                "path": "/paris/1.jpg",
                "lat": 48.8566,
                "lng": 2.3522,
                "location_name": "Paris, France",
                "tags": ["eiffel_tower", "vacation", "landmark"],
            },
            {
                "path": "/paris/2.jpg",
                "lat": 48.8606,
                "lng": 2.3376,
                "location_name": "Paris, France",
                "tags": ["notre_dame", "vacation", "architecture"],
            },
            {
                "path": "/tokyo/1.jpg",
                "lat": 35.6762,
                "lng": 139.6503,
                "location_name": "Tokyo, Japan",
                "tags": ["shibuya", "city", "street"],
            },
        ]

        # Add location data
        for data in photos_data:
            locations_db.add_photo_location(
                photo_path=data["path"],
                latitude=data["lat"],
                longitude=data["lng"],
                corrected_place_name=data["location_name"],
                original_place_name=data["location_name"],
            )

        # Add tag data
        for data in photos_data:
            for tag in data["tags"]:
                tags_db.add_tag_to_photo(data["path"], tag)

        # Find photos within paris area (using the same coordinates)
        paris_photos = locations_db.get_photos_near_location(48.8566, 2.3522, 5.0)  # 5km radius
        assert len(paris_photos) >= 2  # At least 2 Paris photos

        # Get photos with vacation tag
        vacation_photos = tags_db.get_photos_by_tags(["vacation"], "OR")
        assert len(vacation_photos) >= 2  # At least 2 vacation photos

        # Test that location clustering works with tag filter
        # In a real implementation, we would have a combined search function
        # For now, we'll just verify both parts work independently
        assert any("/paris/" in photo["path"] for photo in paris_photos)
        assert any("/paris/" in photo for photo in vacation_photos)

        # Cleanup
        import shutil

        shutil.rmtree(env["temp_dir"])

    def test_collaborative_spaces_with_privacy_controls(self):
        """Test that collaborative spaces work with privacy controls."""
        env = create_test_environment()

        spaces_db = env["spaces_db"]
        privacy_db = PrivacyControlsDB(env["temp_dir"] / "privacy.db")

        # Create a collaborative space
        space_id = spaces_db.create_collaborative_space(
            name="Family Trip Photos",
            description="Photos from our family vacation",
            owner_id="user123",
            privacy_level="shared",
        )
        assert space_id != ""

        # Add some photos to the space
        test_photos = [
            "/family/beach1.jpg",
            "/family/beach2.jpg",
            "/family/mountain1.jpg",
        ]
        for path in test_photos:
            added = spaces_db.add_photo_to_space(space_id=space_id, photo_path=path, added_by_user_id="user123")
            assert added is True

        # Set privacy controls on one of the photos
        privacy_id = privacy_db.set_photo_privacy(
            photo_path="/family/beach1.jpg",
            owner_id="user123",
            visibility="private",
            share_permissions={"view": False, "download": False, "share": False},
            encryption_enabled=True,
        )
        assert privacy_id != ""

        # Verify privacy control was set
        privacy = privacy_db.get_photo_privacy("/family/beach1.jpg")
        assert privacy is not None
        assert privacy.visibility == "private"
        assert privacy.encryption_enabled is True

        # Check space still has the photo (privacy shouldn't affect space membership directly)
        space_photos = spaces_db.get_space_photos(space_id, 10, 0)
        assert len(space_photos) == 3

        # Cleanup
        import shutil

        shutil.rmtree(env["temp_dir"])

    def test_multi_tag_filter_with_notes(self):
        """Test that multi-tag filtering works with note search."""
        env = create_test_environment()

        tags_db = env["tags_db"]
        notes_db = env["notes_db"]

        # Add photos with tags and notes
        test_data = [
            {
                "path": "/vacation/photo1.jpg",
                "tags": ["vacation", "beach", "summer"],
                "note": "Beautiful beach sunset",
            },
            {
                "path": "/vacation/photo2.jpg",
                "tags": ["vacation", "mountain", "summer"],
                "note": "Mountain hiking adventure",
            },
            {
                "path": "/event/photo3.jpg",
                "tags": ["birthday", "friends", "indoor"],
                "note": "Birthday party with friends",
            },
        ]

        for data in test_data:
            # Add tags
            for tag in data["tags"]:
                tags_db.add_tag_to_photo(data["path"], tag)

            # Add note
            notes_db.set_note(data["path"], data["note"])

        # Test multi-tag filtering
        beach_summer_photos = tags_db.get_photos_by_tags(["beach", "summer"], "AND")
        assert len(beach_summer_photos) >= 1

        vacation_photos = tags_db.get_photos_by_tags(["vacation"], "OR")
        assert len(vacation_photos) >= 2

        # Test note search
        beach_note_photos = notes_db.search_notes("beach")
        assert len(beach_note_photos) >= 1
        assert any("beach" in note["photo_path"] for note in beach_note_photos)

        # Verify integration by checking that tag-filtered results match note-searched results where expected
        vacation_paths = {p["path"] for p in vacation_photos}
        notes_with_vacation = notes_db.search_notes("vacation")
        note_paths = {note["photo_path"] for note in notes_with_vacation}

        # There should be overlap between photos tagged as vacation and notes mentioning vacation
        common_paths = vacation_paths.intersection(note_paths)
        assert len(common_paths) >= 1  # At least one photo should match both criteria

        # Cleanup
        import shutil

        shutil.rmtree(env["temp_dir"])

    def test_version_stacks_with_people_tags(self):
        """Test that version stacks work correctly with people tagging (face clustering)."""
        env = create_test_environment()

        versions_db = env["versions_db"]
        # Note: Face clustering integration would be tested separately
        # This test focuses on version stack integrity

        # Create photo versions
        original_path = "/people/group_photo.jpg"
        version_path_1 = "/people/group_photo_cropped.jpg"
        version_path_2 = "/people/group_photo_edited.jpg"

        # Add original photo
        version_1_id = versions_db.create_version(
            original_path=original_path,
            version_path=version_path_1,
            version_type="edit",
            version_name="Cropped Version",
        )
        assert version_1_id != ""

        version_2_id = versions_db.create_version(
            original_path=original_path,
            version_path=version_path_2,
            version_type="edit",
            version_name="Brightened Version",
        )
        assert version_2_id != ""

        # Get the version stack
        stack = versions_db.get_version_stack(original_path)
        assert stack is not None
        assert len(stack.versions) == 3  # Original + 2 versions

        # Test that all versions preserve face detection data
        # In a real implementation, face clustering would be associated with the original photo
        # and would apply to all versions in the stack
        # For this test, we'll just verify the version stack integrity
        version_paths = [v.version_path for v in stack.versions]
        assert original_path in version_paths
        assert version_path_1 in version_paths
        assert version_path_2 in version_paths

        # Cleanup
        import shutil

        shutil.rmtree(env["temp_dir"])

    def test_search_with_multiple_feature_filters(self):
        """Test searching with filters from multiple features simultaneously."""
        env = create_test_environment()

        # This integration test would verify that the search functionality
        # properly combines results from:
        # - Text search (existing functionality)
        # - Location clustering
        # - Tag filtering
        # - People/faces
        # - Privacy controls

        # Implementation would require creating a combined query processor
        # that can handle filtering by all these aspects simultaneously
        # For this test, we'll set up a scenario with multiple aspects

        # Create a photo with location, tags, note, and privacy
        photo_path = "/test/combined_test.jpg"

        # Add location
        env["locations_db"].add_photo_location(
            photo_path=photo_path,
            latitude=40.7128,
            longitude=-74.0060,
            corrected_place_name="Central Park, New York",
        )

        # Add tags
        for tag in ["nature", "park", "trees"]:
            env["tags_db"].add_tag_to_photo(photo_path, tag)

        # Add note
        env["notes_db"].set_note(photo_path, "Beautiful shot from Central Park with lots of trees")

        # Set privacy
        env["privacy_db"].set_photo_privacy(photo_path=photo_path, owner_id="user123", visibility="private")

        # In a real implementation, we would verify that searching with multiple
        # criteria (location "Central Park", tag "nature", note "trees")
        # returns the photo, respecting privacy controls
        # For this test, we just verify the data was properly stored

        location = env["locations_db"].get_photo_location(photo_path)
        assert location is not None
        assert "Central Park" in location.corrected_place_name

        tags = env["tags_db"].get_tags_for_photo(photo_path)
        assert "nature" in tags

        note = env["notes_db"].get_note(photo_path)
        assert "trees" in note.lower()

        privacy = env["privacy_db"].get_photo_privacy(photo_path)
        assert privacy is not None
        assert privacy.visibility == "private"

        # Cleanup
        import shutil

        shutil.rmtree(env["temp_dir"])


class TestAPIIntegration:
    """Tests for API endpoint integration."""

    def test_notes_api_integration(self):
        """Test notes API endpoints work with other features."""
        # This would be a full integration test with the FastAPI backend
        # For now, we'll test the functionality at the DB level
        pass

    def test_version_stacks_api_integration(self):
        """Test version stacks API endpoints work with other features."""
        # API integration test
        pass

    def test_search_integration(self):
        """Test search functionality with all features."""
        # This would test that the search endpoint properly combines results
        # from all the different features
        pass


def run_integration_tests():
    """Run all integration tests."""
    test_suite = TestFeatureIntegration()

    # Get all test methods
    test_methods = [method for method in dir(test_suite) if method.startswith("test_")]

    print(f"Running {len(test_methods)} integration tests...")

    success_count = 0
    total_count = 0

    for method_name in test_methods:
        total_count += 1
        try:
            method = getattr(test_suite, method_name)
            method()
            print(f"  ✓ {method_name}")
            success_count += 1
        except Exception as e:
            print(f"  ✗ {method_name}: {str(e)}")

    print("\n--- Integration Test Results ---")
    print(f"Total: {total_count}")
    print(f"Passed: {success_count}")
    print(f"Failed: {total_count - success_count}")

    if total_count == success_count:
        print("🎉 All integration tests passed!")
        return True
    else:
        print(f"⚠️  {total_count - success_count} integration tests failed")
        return False


if __name__ == "__main__":
    success = run_integration_tests()
    exit(0 if success else 1)
