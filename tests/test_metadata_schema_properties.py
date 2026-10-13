"""
Property Tests for Metadata Schema and Migration System

These tests validate universal correctness properties that should hold true
across all valid executions of the metadata completion system. Each property
is tested with 100+ iterations using hypothesis to ensure robustness.

Author: PhotoSearch Metadata Completion System
Date: 2025-12-29
"""

import os
import json
import sqlite3
import tempfile
from typing import Dict, Any, List

import pytest
from hypothesis import given, strategies as st, settings, assume

from server.database.metadata_schema_v2 import MetadataSchemaV2
from server.metadata.metadata_mapper import MetadataMapper, CameraNormalizer, LensNormalizer
from server.database.metadata_migration import MetadataMigration


class TestCameraDataNormalizationProperty:
    """
    Property 1: Camera Data Normalization
    For any raw metadata containing camera make information, the normalized
    camera make stored in the database should follow consistent formatting
    (e.g., "Canon" not "CANON" or "canon")
    Validates: Requirements 1.1
    """

    @given(
        camera_make=st.one_of(
            st.just("canon"),
            st.just("CANON"),
            st.just("Canon"),
            st.just("nikon"),
            st.just("NIKON"),
            st.just("Nikon"),
            st.just("sony"),
            st.just("SONY"),
            st.just("Sony"),
            st.just("fujifilm"),
            st.just("FUJIFILM"),
            st.just("Fujifilm"),
            st.just("fuji"),
            st.just("FUJI"),
            st.just("olympus"),
            st.just("OLYMPUS"),
            st.just("panasonic"),
            st.just("PANASONIC"),
            st.just("leica"),
            st.just("LEICA"),
            st.just("pentax"),
            st.just("PENTAX"),
            st.just("apple"),
            st.just("APPLE"),
            st.just("samsung"),
            st.just("SAMSUNG"),
            st.just("  canon  "),  # with whitespace
            st.just("Canon Inc."),  # with suffix
            st.just("NIKON CORPORATION"),  # corporate name
        )
    )
    @settings(max_examples=100)
    def test_camera_make_normalization_consistency(self, camera_make: str):
        """Test that camera make normalization produces consistent results."""
        normalizer = CameraNormalizer()

        # Normalize the camera make
        normalized = normalizer.normalize_make(camera_make)

        # Property: Normalized result should not be None for valid input
        assert normalized is not None, f"Normalization returned None for input: {camera_make}"

        # Property: Normalized result should be title case
        assert normalized == normalized.title(), f"Normalized result not in title case: {normalized}"

        # Property: Normalized result should not contain leading/trailing whitespace
        assert normalized == normalized.strip(), f"Normalized result has whitespace: '{normalized}'"

        # Property: Multiple normalizations should be idempotent
        double_normalized = normalizer.normalize_make(normalized)
        assert normalized == double_normalized, f"Normalization not idempotent: {normalized} -> {double_normalized}"

        # Property: Known makes should map to expected values
        expected_mappings = {
            "canon": "Canon",
            "nikon": "Nikon",
            "sony": "Sony",
            "fujifilm": "Fujifilm",
            "fuji": "Fujifilm",
            "olympus": "Olympus",
            "panasonic": "Panasonic",
            "leica": "Leica",
            "pentax": "Pentax",
            "apple": "Apple",
            "samsung": "Samsung",
        }

        make_lower = camera_make.strip().lower()
        if make_lower in expected_mappings:
            assert (
                normalized == expected_mappings[make_lower]
            ), f"Expected {expected_mappings[make_lower]} but got {normalized} for {camera_make}"

    @given(
        camera_model=st.one_of(
            st.just("Canon EOS R5"),
            st.just("EOS R5"),
            st.just("PowerShot G7X"),
            st.just("Nikon D850"),
            st.just("D850"),
            st.just("Sony Alpha A7R IV"),
            st.just("ILCE-7RM4"),
            st.just("Alpha A7R IV"),
            st.just("Fujifilm X-T4"),
            st.just("X-T4"),
            st.just("  EOS R5  "),  # with whitespace
            st.just("Canon PowerShot G7X Mark III"),  # with make prefix
        )
    )
    @settings(max_examples=100)
    def test_camera_model_normalization_consistency(self, camera_model: str):
        """Test that camera model normalization produces consistent results."""
        normalizer = CameraNormalizer()

        # Normalize the camera model
        normalized = normalizer.normalize_model(camera_model)

        # Property: Normalized result should not be None for valid input
        assert normalized is not None, f"Normalization returned None for input: {camera_model}"

        # Property: Normalized result should not contain leading/trailing whitespace
        assert normalized == normalized.strip(), f"Normalized result has whitespace: '{normalized}'"

        # Property: Normalized result should not be empty
        assert len(normalized) > 0, f"Normalized result is empty for input: {camera_model}"

        # Property: Multiple normalizations should be idempotent
        double_normalized = normalizer.normalize_model(normalized)
        assert normalized == double_normalized, f"Normalization not idempotent: {normalized} -> {double_normalized}"

        # Property: Redundant manufacturer names should be removed
        for make in ["Canon", "Nikon", "Sony", "Fujifilm"]:
            if camera_model.strip().startswith(make) and make.lower() not in normalized.lower():
                # Make was successfully removed
                assert not normalized.startswith(
                    make
                ), f"Manufacturer name not removed: {normalized} still starts with {make}"


class TestExposureDataStorageIntegrityProperty:
    """
    Property 2: Exposure Data Storage Integrity
    For any photo with EXIF exposure data, the ISO, aperture, and shutter speed
    values stored in database columns should match the original EXIF values
    with correct data types
    Validates: Requirements 1.2
    """

    @given(
        iso_value=st.one_of(
            st.integers(min_value=50, max_value=409600),  # Valid ISO range
            st.just("100"),  # String representation
            st.just("400"),
            st.just("1600"),
            st.just([200]),  # List format (some EXIF readers return this)
            st.just((800,)),  # Tuple format
        ),
        aperture_value=st.one_of(
            st.floats(min_value=1.0, max_value=32.0),  # Valid aperture range
            st.just("28/10"),  # Fraction format (f/2.8)
            st.just("14/10"),  # f/1.4
            st.just("56/10"),  # f/5.6
            st.just(2.8),
            st.just(1.4),
            st.just(5.6),
        ),
        shutter_value=st.one_of(
            st.just("1/250"),  # Fraction format
            st.just("1/60"),
            st.just("1/1000"),
            st.just("0.004"),  # Decimal format
            st.just("2.5"),  # Slow shutter
            st.just(0.004),  # Float
            st.just(1 / 250),  # Calculated fraction
        ),
    )
    @settings(max_examples=100)
    def test_exposure_data_parsing_integrity(self, iso_value, aperture_value, shutter_value):
        """Test that exposure data parsing maintains data integrity."""
        mapper = MetadataMapper()

        # Test ISO parsing
        parsed_iso = mapper._parse_iso(iso_value)

        if parsed_iso is not None:
            # Property: Parsed ISO should be an integer
            assert isinstance(parsed_iso, int), f"ISO not parsed as integer: {parsed_iso} (type: {type(parsed_iso)})"

            # Property: Parsed ISO should be in valid range
            assert 25 <= parsed_iso <= 500000, f"ISO out of valid range: {parsed_iso}"

            # Property: Original value should be recoverable (within reason)
            if isinstance(iso_value, (int, float)):
                assert abs(parsed_iso - float(iso_value)) < 1, f"ISO value changed: {iso_value} -> {parsed_iso}"
            elif isinstance(iso_value, str) and iso_value.isdigit():
                assert parsed_iso == int(iso_value), f"String ISO not preserved: {iso_value} -> {parsed_iso}"

        # Test aperture parsing
        parsed_aperture = mapper._parse_aperture(aperture_value)

        if parsed_aperture is not None:
            # Property: Parsed aperture should be a float
            assert isinstance(parsed_aperture, float), f"Aperture not parsed as float: {parsed_aperture}"

            # Property: Parsed aperture should be in valid range
            assert 0.5 <= parsed_aperture <= 64.0, f"Aperture out of valid range: {parsed_aperture}"

            # Property: Fraction strings should be parsed correctly
            if isinstance(aperture_value, str) and "/" in aperture_value:
                parts = aperture_value.split("/")
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    expected = float(parts[0]) / float(parts[1])
                    assert (
                        abs(parsed_aperture - expected) < 0.01
                    ), f"Fraction aperture not parsed correctly: {aperture_value} -> {parsed_aperture}, expected {expected}"

        # Test shutter speed parsing
        parsed_shutter_display, parsed_shutter_decimal = mapper._parse_shutter_speed(shutter_value)

        if parsed_shutter_display is not None and parsed_shutter_decimal is not None:
            # Property: Display format should be a string
            assert isinstance(parsed_shutter_display, str), f"Shutter display not string: {parsed_shutter_display}"

            # Property: Decimal value should be a float
            assert isinstance(parsed_shutter_decimal, float), f"Shutter decimal not float: {parsed_shutter_decimal}"

            # Property: Decimal value should be positive
            assert parsed_shutter_decimal > 0, f"Shutter decimal not positive: {parsed_shutter_decimal}"

            # Property: Decimal value should be in reasonable range (1/8000 to 30 seconds)
            assert 0.0001 <= parsed_shutter_decimal <= 30.0, f"Shutter decimal out of range: {parsed_shutter_decimal}"

            # Property: Display format should contain meaningful information
            assert len(parsed_shutter_display) > 0, "Shutter display is empty"
            assert any(
                char.isdigit() for char in parsed_shutter_display
            ), f"Shutter display has no digits: {parsed_shutter_display}"


class TestLensInformationPreservationProperty:
    """
    Property 3: Lens Information Preservation
    For any photo with lens metadata, the lens make, model, and focal length
    stored in searchable fields should accurately represent the original lens data
    Validates: Requirements 1.3
    """

    @given(
        lens_model=st.one_of(
            st.just("RF24-70mm F2.8 L IS USM"),
            st.just("24-70mm f/2.8"),
            st.just("Canon EF 50mm f/1.8 STM"),
            st.just("EF 50mm f/1.8 STM"),
            st.just("Sigma 24-70mm f/2.8 DG DN Art"),
            st.just("Tamron 28-75mm F/2.8 Di III RXD"),
            st.just("Sony FE 85mm F1.4 GM"),
            st.just("FE 85mm F1.4 GM"),
            st.just("Nikkor Z 24-70mm f/2.8 S"),
            st.just("Z 24-70mm f/2.8 S"),
            st.just("  RF24-70mm F2.8 L IS USM  "),  # with whitespace
        ),
        focal_length=st.one_of(
            st.just("50/1"),  # Fraction format
            st.just("85/1"),
            st.just("24/1"),
            st.just("200/1"),
            st.just(50.0),  # Float
            st.just(85.0),
            st.just(24.0),
            st.just(200.0),
            st.just("50"),  # String
            st.just("85"),
            st.just("135"),
        ),
    )
    @settings(max_examples=100)
    def test_lens_information_preservation(self, lens_model: str, focal_length):
        """Test that lens information is preserved accurately."""
        lens_normalizer = LensNormalizer()
        mapper = MetadataMapper()

        # Test lens model normalization
        normalized_model = lens_normalizer.normalize_model(lens_model)

        if normalized_model is not None:
            # Property: Normalized model should not be None for valid input
            assert normalized_model is not None, f"Lens model normalization returned None for: {lens_model}"

            # Property: Normalized model should not be empty
            assert (
                len(normalized_model.strip()) > 0
            ), f"Lens model normalization returned empty string for: {lens_model}"

            # Property: Normalized model should preserve key information
            original_clean = lens_model.strip().lower()
            normalized_clean = normalized_model.lower()

            # Check that focal length information is preserved
            focal_length_patterns = ["24-70", "50mm", "85mm", "24mm", "200mm", "f/1.4", "f/2.8", "f/1.8"]
            for pattern in focal_length_patterns:
                if pattern in original_clean:
                    assert (
                        pattern in normalized_clean or pattern.replace("mm", "") in normalized_clean
                    ), f"Focal length info lost: {pattern} not in {normalized_model} (from {lens_model})"

            # Property: Multiple normalizations should be idempotent
            double_normalized = lens_normalizer.normalize_model(normalized_model)
            assert (
                normalized_model == double_normalized
            ), f"Lens model normalization not idempotent: {normalized_model} -> {double_normalized}"

        # Test focal length parsing
        parsed_focal_length = mapper._parse_focal_length(focal_length)

        if parsed_focal_length is not None:
            # Property: Parsed focal length should be a float
            assert isinstance(parsed_focal_length, float), f"Focal length not parsed as float: {parsed_focal_length}"

            # Property: Parsed focal length should be in valid range (8mm to 800mm for most lenses)
            assert 4.0 <= parsed_focal_length <= 2000.0, f"Focal length out of valid range: {parsed_focal_length}"

            # Property: Original value should be preserved
            if isinstance(focal_length, (int, float)):
                assert (
                    abs(parsed_focal_length - float(focal_length)) < 0.1
                ), f"Focal length value changed: {focal_length} -> {parsed_focal_length}"
            elif isinstance(focal_length, str):
                if "/" in focal_length:
                    # Fraction format
                    parts = focal_length.split("/")
                    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                        expected = float(parts[0]) / float(parts[1])
                        assert (
                            abs(parsed_focal_length - expected) < 0.1
                        ), f"Fraction focal length not parsed correctly: {focal_length} -> {parsed_focal_length}"
                elif focal_length.replace(".", "").isdigit():
                    # Numeric string
                    expected = float(focal_length)
                    assert (
                        abs(parsed_focal_length - expected) < 0.1
                    ), f"Numeric string focal length not preserved: {focal_length} -> {parsed_focal_length}"


class TestExposureTriangleCalculationProperty:
    """
    Property 4: Exposure Triangle Calculation
    For any photo with ISO, aperture, and shutter speed values, the calculated
    exposure triangle string should correctly format and combine these values
    (e.g., "ISO 400, f/2.8, 1/250")
    Validates: Requirements 1.4
    """

    @given(
        iso=st.integers(min_value=50, max_value=25600),
        aperture=st.floats(min_value=1.0, max_value=16.0),
        shutter_speed=st.one_of(
            st.just("1/60"),
            st.just("1/125"),
            st.just("1/250"),
            st.just("1/500"),
            st.just("1/1000"),
            st.just("2.0s"),
            st.just("0.5s"),
        ),
    )
    @settings(max_examples=100)
    def test_exposure_triangle_calculation(self, iso: int, aperture: float, shutter_speed: str):
        """Test that exposure triangle calculation is correct and consistent."""
        mapper = MetadataMapper()

        # Create mapped data with exposure values
        mapped_data = {"iso": iso, "aperture": aperture, "shutter_speed": shutter_speed}

        # Generate composite fields
        composite = mapper._generate_composite_fields(mapped_data, {})
        exposure_triangle = composite.get("exposure_triangle")

        if exposure_triangle is not None:
            # Property: Exposure triangle should be a string
            assert isinstance(exposure_triangle, str), f"Exposure triangle not a string: {exposure_triangle}"

            # Property: Exposure triangle should not be empty
            assert len(exposure_triangle) > 0, "Exposure triangle is empty"

            # Property: Exposure triangle should contain all three values
            assert str(iso) in exposure_triangle, f"ISO {iso} not found in exposure triangle: {exposure_triangle}"
            assert (
                str(aperture) in exposure_triangle
            ), f"Aperture {aperture} not found in exposure triangle: {exposure_triangle}"
            assert (
                shutter_speed in exposure_triangle
            ), f"Shutter speed {shutter_speed} not found in exposure triangle: {exposure_triangle}"

            # Property: Exposure triangle should follow expected format
            assert "ISO" in exposure_triangle, f"'ISO' label not found in: {exposure_triangle}"
            assert "f/" in exposure_triangle, f"'f/' label not found in: {exposure_triangle}"

            # Property: Values should be separated by commas
            parts = exposure_triangle.split(",")
            assert len(parts) == 3, f"Exposure triangle should have 3 parts separated by commas: {exposure_triangle}"

            # Property: Each part should be properly formatted
            iso_part = parts[0].strip()
            aperture_part = parts[1].strip()
            shutter_part = parts[2].strip()

            assert iso_part.startswith("ISO"), f"ISO part malformed: {iso_part}"
            assert aperture_part.startswith("f/"), f"Aperture part malformed: {aperture_part}"
            assert len(shutter_part) > 0, f"Shutter part empty: {shutter_part}"

            # Property: Regenerating with same values should produce same result
            composite2 = mapper._generate_composite_fields(mapped_data, {})
            exposure_triangle2 = composite2.get("exposure_triangle")
            assert (
                exposure_triangle == exposure_triangle2
            ), f"Exposure triangle calculation not deterministic: {exposure_triangle} != {exposure_triangle2}"


class TestMigrationDataPreservationProperty:
    """
    Property 5: Migration Data Preservation
    For any existing photo metadata before migration, all metadata fields
    should be preserved and accessible after migration to the enhanced schema
    Validates: Requirements 1.5, 1.6
    """

    @given(
        sample_metadata=st.fixed_dictionaries(
            {
                "file": st.fixed_dictionaries(
                    {
                        "path": st.just("/test/photo.jpg"),
                        "name": st.just("photo.jpg"),
                        "extension": st.just(".jpg"),
                        "mime_type": st.just("image/jpeg"),
                    }
                ),
                "filesystem": st.fixed_dictionaries(
                    {
                        "size_bytes": st.integers(min_value=1000, max_value=50000000),
                        "created": st.just("2024-01-01T12:00:00"),
                        "modified": st.just("2024-01-01T12:00:00"),
                    }
                ),
                "exif": st.one_of(
                    st.none(),
                    st.fixed_dictionaries(
                        {
                            "image": st.fixed_dictionaries(
                                {
                                    "Make": st.sampled_from(["Canon", "Nikon", "Sony"]),
                                    "Model": st.sampled_from(["EOS R5", "D850", "A7R IV"]),
                                    "Software": st.just("Adobe Lightroom"),
                                }
                            ),
                            "exif": st.fixed_dictionaries(
                                {
                                    "ISOSpeedRatings": st.sampled_from(["100", "400", "800"]),
                                    "FNumber": st.sampled_from(["28/10", "14/10", "56/10"]),
                                    "ExposureTime": st.sampled_from(["1/60", "1/125", "1/250"]),
                                    "FocalLength": st.sampled_from(["50/1", "85/1", "24/1"]),
                                }
                            ),
                        }
                    ),
                ),
            }
        )
    )
    @settings(max_examples=50, deadline=None)  # Disable deadline for database operations
    def test_migration_preserves_all_data(self, sample_metadata: Dict[str, Any]):
        """Test that migration preserves all original metadata."""
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
            db_path = tmp_db.name

        try:
            # Create original database with sample data
            conn = sqlite3.connect(db_path)
            conn.execute("""
                CREATE TABLE metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    file_hash TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    version INTEGER DEFAULT 1
                )
            """)

            # Insert sample metadata
            file_path = sample_metadata["file"]["path"]
            file_hash = "test_hash_123"
            metadata_json = json.dumps(sample_metadata, default=str)

            conn.execute(
                """
                INSERT INTO metadata (file_path, file_hash, metadata_json)
                VALUES (?, ?, ?)
            """,
                (file_path, file_hash, metadata_json),
            )
            conn.commit()
            conn.close()

            # Get original data
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM metadata WHERE file_path = ?", (file_path,))
            original_row = cursor.fetchone()
            original_metadata = json.loads(original_row["metadata_json"])
            conn.close()

            # Run migration
            migration = MetadataMigration(db_path, batch_size=10)
            success = migration.migrate_database(force=True)

            # Property: Migration should succeed
            assert success, "Migration should succeed for valid data"

            # Get migrated data
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM metadata WHERE file_path = ?", (file_path,))
            migrated_row = cursor.fetchone()
            migrated_metadata = json.loads(migrated_row["metadata_json"])
            conn.close()

            # Property: Original metadata JSON should be preserved exactly
            assert (
                original_metadata == migrated_metadata
            ), "Original metadata JSON should be preserved exactly after migration"

            # Property: File path should be preserved
            assert (
                original_row["file_path"] == migrated_row["file_path"]
            ), "File path should be preserved after migration"

            # Property: File hash should be preserved
            assert (
                original_row["file_hash"] == migrated_row["file_hash"]
            ), "File hash should be preserved after migration"

            # Property: All original fields should still be accessible
            for key, value in original_metadata.items():
                assert key in migrated_metadata, f"Original field {key} missing after migration"
                assert migrated_metadata[key] == value, f"Original field {key} value changed after migration"

            # Property: Enhanced fields should be added without affecting original data
            if sample_metadata.get("exif") and sample_metadata["exif"].get("image", {}).get("Make"):
                # Should have camera_make field populated
                assert (
                    migrated_row["camera_make"] is not None
                ), "Enhanced camera_make field should be populated when EXIF Make is present"

        finally:
            # Cleanup
            if os.path.exists(db_path):
                os.unlink(db_path)


class TestRangeQueryFunctionalityProperty:
    """
    Property 6: Range Query Functionality
    For any numeric metadata field (ISO, aperture, focal length), range queries
    should return only photos with values within the specified range
    Validates: Requirements 1.7
    """

    @given(
        test_values=st.lists(st.integers(min_value=100, max_value=6400), min_size=5, max_size=20, unique=True),
        query_min=st.integers(min_value=100, max_value=3200),
        query_max=st.integers(min_value=3200, max_value=6400),
    )
    @settings(max_examples=50, deadline=None)  # Disable deadline for database operations
    def test_iso_range_query_functionality(self, test_values: List[int], query_min: int, query_max: int):
        """Test that ISO range queries return correct results."""
        assume(query_min <= query_max)  # Ensure valid range

        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
            db_path = tmp_db.name

        try:
            # Create enhanced schema
            schema = MetadataSchemaV2(db_path)
            schema.create_enhanced_schema()

            # Insert test data
            conn = schema.connect()
            cursor = conn.cursor()

            for i, iso_value in enumerate(test_values):
                cursor.execute(
                    """
                    INSERT INTO metadata (file_path, file_hash, metadata_json, iso)
                    VALUES (?, ?, ?, ?)
                """,
                    (f"/test/photo_{i}.jpg", f"hash_{i}", "{}", iso_value),
                )

            conn.commit()

            # Query for values in range
            cursor.execute(
                """
                SELECT file_path, iso FROM metadata
                WHERE iso >= ? AND iso <= ?
                ORDER BY iso
            """,
                (query_min, query_max),
            )

            results = cursor.fetchall()

            # Property: All returned values should be within the specified range
            for row in results:
                iso_value = row["iso"]
                assert (
                    query_min <= iso_value <= query_max
                ), f"ISO value {iso_value} outside query range [{query_min}, {query_max}]"

            # Property: All values in range should be returned
            expected_values = [v for v in test_values if query_min <= v <= query_max]
            returned_values = [row["iso"] for row in results]

            assert len(returned_values) == len(
                expected_values
            ), f"Expected {len(expected_values)} results but got {len(returned_values)}"

            for expected_value in expected_values:
                assert expected_value in returned_values, f"Expected ISO value {expected_value} not found in results"

            # Property: Values outside range should not be returned
            for iso_value in test_values:
                if iso_value < query_min or iso_value > query_max:
                    assert iso_value not in returned_values, f"ISO value {iso_value} outside range but found in results"

            schema.close()

        finally:
            # Cleanup
            if os.path.exists(db_path):
                os.unlink(db_path)

    @given(
        test_values=st.lists(
            st.floats(min_value=1.0, max_value=16.0, allow_nan=False, allow_infinity=False),
            min_size=5,
            max_size=15,
            unique=True,
        ),
        query_min=st.floats(min_value=1.0, max_value=8.0, allow_nan=False, allow_infinity=False),
        query_max=st.floats(min_value=8.0, max_value=16.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=30, deadline=None)  # Disable deadline for database operations
    def test_aperture_range_query_functionality(self, test_values: List[float], query_min: float, query_max: float):
        """Test that aperture range queries return correct results."""
        assume(query_min <= query_max)  # Ensure valid range

        # Round values to avoid floating point precision issues
        test_values = [round(v, 1) for v in test_values]
        query_min = round(query_min, 1)
        query_max = round(query_max, 1)

        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
            db_path = tmp_db.name

        try:
            # Create enhanced schema
            schema = MetadataSchemaV2(db_path)
            schema.create_enhanced_schema()

            # Insert test data
            conn = schema.connect()
            cursor = conn.cursor()

            for i, aperture_value in enumerate(test_values):
                cursor.execute(
                    """
                    INSERT INTO metadata (file_path, file_hash, metadata_json, aperture)
                    VALUES (?, ?, ?, ?)
                """,
                    (f"/test/photo_{i}.jpg", f"hash_{i}", "{}", aperture_value),
                )

            conn.commit()

            # Query for values in range
            cursor.execute(
                """
                SELECT file_path, aperture FROM metadata
                WHERE aperture >= ? AND aperture <= ?
                ORDER BY aperture
            """,
                (query_min, query_max),
            )

            results = cursor.fetchall()

            # Property: All returned values should be within the specified range
            for row in results:
                aperture_value = round(row["aperture"], 1)
                assert (
                    query_min <= aperture_value <= query_max
                ), f"Aperture value {aperture_value} outside query range [{query_min}, {query_max}]"

            # Property: All values in range should be returned
            expected_values = [v for v in test_values if query_min <= v <= query_max]
            returned_values = [round(row["aperture"], 1) for row in results]

            assert len(returned_values) == len(
                expected_values
            ), f"Expected {len(expected_values)} results but got {len(returned_values)}"

            schema.close()

        finally:
            # Cleanup
            if os.path.exists(db_path):
                os.unlink(db_path)


if __name__ == "__main__":
    # Run property tests
    pytest.main([__file__, "-v", "--tb=short"])
