"""
Unit Tests for All New Features

Comprehensive unit tests for all features implemented in the Living Museum project.
"""

import pytest
import tempfile
from pathlib import Path
import sqlite3
import json
from datetime import datetime, timedelta

# Test imports for the new features
from server.notes_db import NotesDB
from server.photo_versions_db import PhotoVersionsDB
from server.location_clusters_db import LocationClustersDB
from server.multi_tag_filter_db import MultiTagFilterDB
from server.collaborative_spaces_db import CollaborativeSpacesDB
from server.ai_insights_db import AIInsightsDB
from server.privacy_controls_db import PrivacyControlsDB
from server.bulk_actions_db import BulkActionsDB


def create_temp_db_path():
    """Create a temporary database file for testing."""
    return Path(tempfile.mktemp(suffix=".db"))


class TestNotesDB:
    """Unit tests for NotesDB functionality."""

    def test_initialization(self):
        """Test that NotesDB initializes correctly."""
        db_path = create_temp_db_path()
        db = NotesDB(db_path)

        # Verify database and tables were created
        assert db_path.exists()

        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='photo_notes'
            """)
            assert cursor.fetchone() is not None

    def test_set_and_get_note(self):
        """Test setting and getting a note."""
        db_path = create_temp_db_path()
        db = NotesDB(db_path)

        photo_path = "/test/photo.jpg"
        note_content = "This is a test note"

        # Set note
        success = db.set_note(photo_path, note_content)
        assert success is True

        # Get note
        retrieved_note = db.get_note(photo_path)
        assert retrieved_note == note_content

    def test_update_note(self):
        """Test updating an existing note."""
        db_path = create_temp_db_path()
        db = NotesDB(db_path)

        photo_path = "/test/photo.jpg"

        # Set initial note
        db.set_note(photo_path, "Initial note")
        assert db.get_note(photo_path) == "Initial note"

        # Update note
        success = db.set_note(photo_path, "Updated note")
        assert success is True
        assert db.get_note(photo_path) == "Updated note"

    def test_delete_note(self):
        """Test deleting a note."""
        db_path = create_temp_db_path()
        db = NotesDB(db_path)

        photo_path = "/test/photo.jpg"
        note = "Test note for deletion"

        # Set note
        db.set_note(photo_path, note)
        assert db.get_note(photo_path) == note

        # Delete note
        success = db.delete_note(photo_path)
        assert success is True
        assert db.get_note(photo_path) is None

    def test_get_photos_with_notes(self):
        """Test getting all photos with notes."""
        db_path = create_temp_db_path()
        db = NotesDB(db_path)

        # Add some test notes
        test_data = [
            ("/test1.jpg", "Note for photo 1"),
            ("/test2.jpg", "Note for photo 2"),
            ("/test3.jpg", "Note for photo 3")
        ]

        for path, note in test_data:
            db.set_note(path, note)

        # Get all photos with notes
        photos_with_notes = db.get_photos_with_notes()
        assert len(photos_with_notes) == 3

        returned_paths = [p["photo_path"] for p in photos_with_notes]
        for path, _ in test_data:
            assert path in returned_paths

    def test_search_notes(self):
        """Test searching notes by content."""
        db_path = create_temp_db_path()
        db = NotesDB(db_path)

        # Add test notes
        db.set_note("/test1.jpg", "This is a vacation photo")
        db.set_note("/test2.jpg", "Family gathering at home")
        db.set_note("/test3.jpg", "Vacation with family")

        # Search for "vacation"
        results = db.search_notes("vacation")
        assert len(results) == 2  # Should find 2 photos with "vacation"

        # Search for "family"
        results = db.search_notes("family")
        assert len(results) == 2  # Should find 2 photos with "family"


class TestPhotoVersionsDB:
    """Unit tests for PhotoVersionsDB functionality."""

    def test_initialization(self):
        """Test that PhotoVersionsDB initializes correctly."""
        db_path = create_temp_db_path()
        db = PhotoVersionsDB(db_path)

        # Verify database and tables were created
        assert db_path.exists()

        with sqlite3.connect(db_path) as conn:
            for table_name in ["photo_versions", "version_stacks"]:
                cursor = conn.execute(f"""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='{table_name}'
                """)
                assert cursor.fetchone() is not None

    def test_create_and_get_version(self):
        """Test creating and getting a photo version."""
        db_path = create_temp_db_path()
        db = PhotoVersionsDB(db_path)

        original_path = "/test/original.jpg"
        version_path = "/test/edited.jpg"

        # Create a version
        version_id = db.create_version(
            original_path=original_path,
            version_path=version_path,
            version_type="edit",
            version_name="Brightness Adjustment",
            version_description="Increased brightness and contrast",
            edit_instructions={"brightness": 10, "contrast": 5}
        )
        assert version_id != ""

        # Get the version stack
        stack = db.get_version_stack(original_path)
        assert stack is not None
        assert len(stack.versions) >= 1  # Should have at least 1 version

        # Find the specific version in the stack
        version = next((v for v in stack.versions if v.version_path == version_path), None)
        assert version is not None
        assert version.version_name == "Brightness Adjustment"
        assert version.version_type == "edit"

    def test_update_version_metadata(self):
        """Test updating version metadata."""
        db_path = create_temp_db_path()
        db = PhotoVersionsDB(db_path)

        # Create a version
        original_path = "/test/original.jpg"
        version_path = "/test/edited.jpg"

        version_id = db.create_version(
            original_path=original_path,
            version_path=version_path,
            version_type="edit",
            version_name="Old Name"
        )

        # Update version metadata
        success = db.update_version_metadata(
            version_path=version_path,
            version_name="New Name",
            version_description="New Description"
        )
        assert success is True

        # Verify update
        stack = db.get_version_stack(original_path)
        version = next((v for v in stack.versions if v.version_path == version_path), None)
        assert version is not None
        assert version.version_name == "New Name"
        assert version.version_description == "New Description"

    def test_delete_version(self):
        """Test deleting a version."""
        db_path = create_temp_db_path()
        db = PhotoVersionsDB(db_path)

        # Create a version
        original_path = "/test/original.jpg"
        version_path = "/test/edited.jpg"

        version_id = db.create_version(
            original_path=original_path,
            version_path=version_path,
            version_type="edit",
            version_name="To be deleted"
        )

        # Verify it exists
        stack_before = db.get_version_stack(original_path)
        assert stack_before is not None
        original_count = len(stack_before.versions)
        assert original_count >= 1

        # Delete the version
        success = db.delete_version(version_id)
        assert success is True

        # Verify it's been removed
        stack_after = db.get_version_stack(original_path)
        assert len(stack_after.versions) < original_count


class TestLocationClustersDB:
    """Unit tests for LocationClustersDB functionality."""

    def test_initialization(self):
        """Test that LocationClustersDB initializes correctly."""
        db_path = create_temp_db_path()
        db = LocationClustersDB(db_path)

        # Verify database and tables were created
        assert db_path.exists()

        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='photo_locations'
            """)
            assert cursor.fetchone() is not None

    def test_add_and_get_photo_location(self):
        """Test adding and getting photo location information."""
        db_path = create_temp_db_path()
        db = LocationClustersDB(db_path)

        photo_path = "/test/photo.jpg"

        # Add location information
        success = db.add_photo_location(
            photo_path=photo_path,
            latitude=40.7128,
            longitude=-74.0060,
            original_place_name="New York City",
            corrected_place_name="Manhattan, NYC",
            country="USA",
            region="New York",
            city="New York City"
        )
        assert success is True

        # Get location information
        location = db.get_photo_location(photo_path)
        assert location is not None
        assert location.latitude == 40.7128
        assert location.longitude == -74.0060
        assert location.corrected_place_name == "Manhattan, NYC"
        assert location.city == "New York City"

    def test_update_photo_location(self):
        """Test updating photo location information."""
        db_path = create_temp_db_path()
        db = LocationClustersDB(db_path)

        photo_path = "/test/photo.jpg"

        # Add initial location
        db.add_photo_location(
            photo_path=photo_path,
            latitude=40.7128,
            longitude=-74.0060,
            original_place_name="New York",
            corrected_place_name="New York City"
        )

        # Update location information
        success = db.update_photo_location(
            photo_path=photo_path,
            corrected_place_name="Manhattan, NYC",
            country="USA",
            region="New York",
            city="New York City"
        )
        assert success is True

        # Verify update
        location = db.get_photo_location(photo_path)
        assert location is not None
        assert location.corrected_place_name == "Manhattan, NYC"
        assert location.city == "New York City"

    def test_get_photos_by_place(self):
        """Test getting photos by place name."""
        db_path = create_temp_db_path()
        db = LocationClustersDB(db_path)

        # Add some photos to the same place
        test_data = [
            ("/test1.jpg", 40.7128, -74.0060, "Central Park", "Central Park, NYC"),
            ("/test2.jpg", 40.7829, -73.9654, "Central Park", "Central Park, NYC"),
            ("/test3.jpg", 34.0522, -118.2437, "Los Angeles", "Hollywood, LA")
        ]

        for path, lat, lng, orig_name, corr_name in test_data:
            db.add_photo_location(
                photo_path=path,
                latitude=lat,
                longitude=lng,
                original_place_name=orig_name,
                corrected_place_name=corr_name
            )

        # Search for photos in Central Park
        central_park_photos = db.get_photos_by_place("Central Park")
        # Should find at least the photos with "Central Park" in their names
        assert len(central_park_photos) >= 2

        # Search for photos in Hollywood
        hollywood_photos = db.get_photos_by_place("Hollywood")
        assert len(hollywood_photos) >= 1


class TestMultiTagFilterDB:
    """Unit tests for MultiTagFilterDB functionality."""

    def test_initialization(self):
        """Test that MultiTagFilterDB initializes correctly."""
        db_path = create_temp_db_path()
        db = MultiTagFilterDB(db_path)

        # Verify database and tables were created
        assert db_path.exists()

        with sqlite3.connect(db_path) as conn:
            for table_name in ["tag_filters", "photo_tags"]:
                cursor = conn.execute(f"""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='{table_name}'
                """)
                assert cursor.fetchone() is not None

    def test_create_and_get_tag_filter(self):
        """Test creating and getting a tag filter."""
        db_path = create_temp_db_path()
        db = MultiTagFilterDB(db_path)

        # Create a tag filter
        expressions = [
            {"tag": "beach", "operator": "has"},
            {"tag": "sunset", "operator": "has"},
            {"tag": "people", "operator": "not_has"}
        ]

        filter_id = db.create_tag_filter(
            name="Beach Photos without People",
            tag_expressions=expressions,
            combination_operator="AND"
        )
        assert filter_id != ""

        # Get the filter
        retrieved_filter = db.get_tag_filter(filter_id)
        assert retrieved_filter is not None
        assert retrieved_filter.name == "Beach Photos without People"
        assert retrieved_filter.combination_operator == "AND"
        assert len(retrieved_filter.tag_expressions) == 3

    def test_apply_tag_filter(self):
        """Test applying a tag filter."""
        db_path = create_temp_db_path()
        db = MultiTagFilterDB(db_path)

        # Add some photos with tags
        test_photos = [
            ("/beach1.jpg", ["beach", "sunset"]),
            ("/beach2.jpg", ["beach", "water"]),
            ("/city1.jpg", ["city", "people"]),
            ("/nature1.jpg", ["trees", "landscape"])
        ]

        for path, tags in test_photos:
            for tag in tags:
                db.add_tag_to_photo(path, tag)

        # Create a filter that looks for "beach" AND "sunset"
        expressions = [
            {"tag": "beach", "operator": "has"},
            {"tag": "sunset", "operator": "has"}
        ]

        # Apply the filter
        matching_photos = db.apply_tag_filter(
            tag_expressions=expressions,
            combination_operator="AND"
        )

        # Should only match beach1.jpg (which has both 'beach' and 'sunset')
        assert "/beach1.jpg" in matching_photos
        # beach2.jpg should not be included (has 'beach' but not 'sunset')
        assert "/beach2.jpg" not in matching_photos


class TestCollaborativeSpacesDB:
    """Unit tests for CollaborativeSpacesDB functionality."""

    def test_initialization(self):
        """Test that CollaborativeSpacesDB initializes correctly."""
        db_path = create_temp_db_path()
        db = CollaborativeSpacesDB(db_path)

        # Verify database and tables were created
        assert db_path.exists()

        with sqlite3.connect(db_path) as conn:
            for table_name in ["collaborative_spaces", "space_members", "space_photos"]:
                cursor = conn.execute(f"""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='{table_name}'
                """)
                assert cursor.fetchone() is not None

    def test_create_and_get_collaborative_space(self):
        """Test creating and getting a collaborative space."""
        db_path = create_temp_db_path()
        db = CollaborativeSpacesDB(db_path)

        # Create a collaborative space
        space_id = db.create_collaborative_space(
            name="Family Photos",
            description="Photos shared with family",
            owner_id="user123",
            privacy_level="shared",
            max_members=10
        )
        assert space_id != ""

        # Get the space
        retrieved_space = db.get_collaborative_space(space_id)
        assert retrieved_space is not None
        assert retrieved_space.name == "Family Photos"
        assert retrieved_space.owner_id == "user123"
        assert retrieved_space.privacy_level == "shared"

    def test_add_and_remove_member(self):
        """Test adding and removing members from a space."""
        db_path = create_temp_db_path()
        db = CollaborativeSpacesDB(db_path)

        # Create a space
        space_id = db.create_collaborative_space(
            name="Test Space",
            description="A test space",
            owner_id="user123"
        )

        # Add a member
        member_added = db.add_member_to_space(
            space_id=space_id,
            user_id="user456",
            role="contributor"
        )
        assert member_added is True

        # Verify member exists
        members = db.get_space_members(space_id)
        assert len(members) == 2  # Owner + new member
        member_ids = [m.user_id for m in members]
        assert "user456" in member_ids

        # Remove the member
        member_removed = db.remove_member_from_space(space_id, "user456")
        assert member_removed is True

        # Verify member is gone
        members_after_removal = db.get_space_members(space_id)
        assert len(members_after_removal) == 1  # Just the owner
        remaining_member_ids = [m.user_id for m in members_after_removal]
        assert "user456" not in remaining_member_ids

    def test_add_and_remove_photo_from_space(self):
        """Test adding and removing photos from a space."""
        db_path = create_temp_db_path()
        db = CollaborativeSpacesDB(db_path)

        # Create a space
        space_id = db.create_collaborative_space(
            name="Test Space",
            description="A test space",
            owner_id="user123"
        )

        # Add a photo to the space
        photo_added = db.add_photo_to_space(
            space_id=space_id,
            photo_path="/path/to/photo.jpg",
            added_by_user_id="user123",
            caption="A test photo"
        )
        assert photo_added is True

        # Verify photo exists in space
        photos = db.get_space_photos(space_id)
        assert len(photos) == 1
        assert photos[0].photo_path == "/path/to/photo.jpg"

        # Remove the photo from space
        photo_removed = db.remove_photo_from_space(space_id, "/path/to/photo.jpg")
        assert photo_removed is True

        # Verify photo is gone
        photos_after_removal = db.get_space_photos(space_id)
        assert len(photos_after_removal) == 0


class TestAIInsightsDB:
    """Unit tests for AIInsightsDB functionality."""

    def test_initialization(self):
        """Test that AIInsightsDB initializes correctly."""
        db_path = create_temp_db_path()
        db = AIInsightsDB(db_path)

        # Verify database and tables were created
        assert db_path.exists()

        with sqlite3.connect(db_path) as conn:
            for table_name in ["photo_insights", "ai_models", "insight_templates"]:
                cursor = conn.execute(f"""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='{table_name}'
                """)
                assert cursor.fetchone() is not None

    def test_create_and_get_ai_insight(self):
        """Test creating and getting an AI insight."""
        db_path = create_temp_db_path()
        db = AIInsightsDB(db_path)

        # Create an AI insight
        insight_id = db.create_insight(
            photo_path="/test/photo.jpg",
            insight_type="best_shot",
            insight_data={
                "reason": "Good composition and lighting",
                "score": 0.95,
                "elements": ["rule_of_thirds", "golden_hour_lighting"]
            },
            confidence=0.92
        )
        assert insight_id != ""

        # Get the insight
        retrieved_insight = db.get_insight(insight_id)
        assert retrieved_insight is not None
        assert retrieved_insight.photo_path == "/test/photo.jpg"
        assert retrieved_insight.insight_type == "best_shot"
        assert retrieved_insight.confidence == 0.92

        # Verify nested data
        insight_data = retrieved_insight.insight_data
        assert insight_data["reason"] == "Good composition and lighting"
        assert insight_data["score"] == 0.95
        assert "rule_of_thirds" in insight_data["elements"]

    def test_get_insights_by_type(self):
        """Test getting insights by type."""
        db_path = create_temp_db_path()
        db = AIInsightsDB(db_path)

        # Create multiple insights of different types
        for i in range(3):
            db.create_insight(
                photo_path=f"/test{i}.jpg",
                insight_type="best_shot",
                insight_data={"reason": f"Test insight {i}"},
                confidence=0.8 + (i * 0.05)
            )

        for i in range(2):
            db.create_insight(
                photo_path=f"/landscape{i}.jpg",
                insight_type="composition",
                insight_data={"reason": f"Landscape insight {i}"},
                confidence=0.7 + (i * 0.1)
            )

        # Get all "best_shot" insights
        best_shot_insights = db.get_insights_by_type("best_shot")
        assert len(best_shot_insights) == 3

        # Get all "composition" insights
        composition_insights = db.get_insights_by_type("composition")
        assert len(composition_insights) == 2


class TestPrivacyControlsDB:
    """Unit tests for PrivacyControlsDB functionality."""

    def test_initialization(self):
        """Test that PrivacyControlsDB initializes correctly."""
        db_path = create_temp_db_path()
        db = PrivacyControlsDB(db_path)

        # Verify database and tables were created
        assert db_path.exists()

        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='privacy_controls'
            """)
            assert cursor.fetchone() is not None

    def test_set_and_get_photo_privacy(self):
        """Test setting and getting photo privacy settings."""
        db_path = create_temp_db_path()
        db = PrivacyControlsDB(db_path)

        photo_path = "/test/photo.jpg"

        # Set privacy controls
        privacy_id = db.set_photo_privacy(
            photo_path=photo_path,
            owner_id="user123",
            visibility="private",
            share_permissions={"view": True, "download": False, "share": False},
            encryption_enabled=True,
            allowed_users=["user456"],
            allowed_groups=["family_group"]
        )
        assert privacy_id != ""

        # Get privacy settings
        privacy = db.get_photo_privacy(photo_path)
        assert privacy is not None
        assert privacy.owner_id == "user123"
        assert privacy.visibility == "private"
        assert privacy.encryption_enabled is True
        assert "user456" in privacy.allowed_users
        assert "family_group" in privacy.allowed_groups

    def test_update_photo_privacy(self):
        """Test updating photo privacy settings."""
        db_path = create_temp_db_path()
        db = PrivacyControlsDB(db_path)

        photo_path = "/test/photo.jpg"

        # Set initial privacy
        privacy_id = db.set_photo_privacy(
            photo_path=photo_path,
            owner_id="user123",
            visibility="private"
        )

        # Update privacy settings
        success = db.update_photo_privacy(
            photo_path=photo_path,
            visibility="shared",
            share_permissions={"view": True, "download": True},
            encryption_enabled=False,
            allowed_users=["user456", "user789"]
        )
        assert success is True

        # Verify update
        privacy = db.get_photo_privacy(photo_path)
        assert privacy is not None
        assert privacy.visibility == "shared"
        assert privacy.encryption_enabled is False
        assert len(privacy.allowed_users) >= 2


class TestBulkActionsDB:
    """Unit tests for BulkActionsDB functionality."""

    def test_initialization(self):
        """Test that BulkActionsDB initializes correctly."""
        db_path = create_temp_db_path()
        db = BulkActionsDB(db_path)

        # Verify database and tables were created
        assert db_path.exists()

        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='bulk_actions'
            """)
            assert cursor.fetchone() is not None

    def test_record_and_get_bulk_action(self):
        """Test recording and getting a bulk action."""
        db_path = create_temp_db_path()
        db = BulkActionsDB(db_path)

        photo_paths = ["/test1.jpg", "/test2.jpg", "/test3.jpg"]

        # Record a bulk action
        action_id = db.record_bulk_action(
            action_type="delete",
            user_id="user123",
            affected_paths=photo_paths,
            operation_data={"reason": "duplicate"}
        )
        assert action_id != ""

        # Get the action
        action = db.get_bulk_action(action_id)
        assert action is not None
        assert action.action_type == "delete"
        assert action.user_id == "user123"
        assert len(action.affected_paths) == 3
        assert action.operation_data["reason"] == "duplicate"

    def test_undo_bulk_action(self):
        """Test undoing a bulk action."""
        db_path = create_temp_db_path()
        db = BulkActionsDB(db_path)

        photo_paths = ["/test1.jpg", "/test2.jpg"]

        # Record a bulk action
        action_id = db.record_bulk_action(
            action_type="favorite",
            user_id="user123",
            affected_paths=photo_paths,
            operation_data={"favorite": True}
        )

        # Initially, action should be marked as not undone
        action = db.get_bulk_action(action_id)
        assert action is not None
        assert action.status != "undone"

        # Mark as undone
        success = db.mark_action_undone(action_id)
        assert success is True

        # Verify action is marked as undone
        action_after = db.get_bulk_action(action_id)
        assert action_after is not None
        assert action_after.status == "undone"


def run_all_tests():
    """Run all unit tests for the new features."""
    test_classes = [
        TestNotesDB,
        TestPhotoVersionsDB,
        TestLocationClustersDB,
        TestMultiTagFilterDB,
        TestCollaborativeSpacesDB,
        TestAIInsightsDB,
        TestPrivacyControlsDB,
        TestBulkActionsDB
    ]

    print(f"Running unit tests for {len(test_classes)} feature modules...")

    total_tests = 0
    passed_tests = 0
    failed_tests = 0

    for test_class in test_classes:
        print(f"\n--- Testing {test_class.__name__} ---")
        test_instance = test_class()

        # Get all methods starting with 'test_'
        test_methods = [method for method in dir(test_instance) if method.startswith('test_')]

        for method_name in test_methods:
            total_tests += 1
            try:
                method = getattr(test_instance, method_name)
                method()
                print(f"  ✓ {method_name}")
                passed_tests += 1
            except Exception as e:
                print(f"  ✗ {method_name}: {str(e)}")
                failed_tests += 1

    print(f"\n--- Test Results ---")
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")

    if failed_tests == 0:
        print("🎉 All tests passed!")
    else:
        print(f"⚠️  {failed_tests} tests failed")

    return failed_tests == 0

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
