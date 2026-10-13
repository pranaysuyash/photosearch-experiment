"""
Enhanced Metadata Database Schema V2 - Searchable metadata columns

This module provides the enhanced database schema that transforms PhotoSearch's
metadata extraction capabilities into a professional-grade searchable interface.
Building on the existing metadata.db structure, this adds structured columns
for camera settings, lens information, and technical data.

Key Features:
- Searchable columns for camera make/model, exposure settings, lens data
- Backward compatibility with existing metadata table
- Database indexes for performance optimization
- Migration support for existing photo libraries

Author: PhotoSearch Metadata Completion System
Date: 2025-12-29
"""

import sqlite3
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class MetadataSchemaV2:
    """
    Enhanced metadata database schema with searchable columns.
    Extends existing metadata table with structured fields for professional photography workflows.
    """

    # Define searchable columns with their SQLite types
    SEARCHABLE_COLUMNS = {
        # Camera Information
        "camera_make": "TEXT",
        "camera_model": "TEXT",
        "camera_serial": "TEXT",
        # Lens Information
        "lens_make": "TEXT",
        "lens_model": "TEXT",
        "lens_serial": "TEXT",
        # Exposure Settings
        "iso": "INTEGER",
        "aperture": "REAL",  # f-number (e.g., 2.8)
        "shutter_speed": "TEXT",  # display format (e.g., "1/250")
        "shutter_speed_decimal": "REAL",  # for range queries
        "exposure_compensation": "REAL",
        "exposure_mode": "TEXT",
        "metering_mode": "TEXT",
        # Focal Length
        "focal_length": "REAL",  # in mm
        "focal_length_35mm": "INTEGER",  # 35mm equivalent
        # Flash
        "flash_used": "BOOLEAN",
        "flash_mode": "TEXT",
        # White Balance
        "white_balance": "TEXT",
        "color_temperature": "INTEGER",
        # Image Quality
        "image_quality": "TEXT",  # RAW, JPEG, etc.
        "color_space": "TEXT",  # sRGB, AdobeRGB, etc.
        "bit_depth": "INTEGER",
        # Software
        "software": "TEXT",
        "edit_software": "TEXT",
        # Copyright & Attribution
        "copyright": "TEXT",
        "creator": "TEXT",
        "creator_tool": "TEXT",
        # IPTC/XMP Content & Rights
        "title": "TEXT",
        "headline": "TEXT",
        "description": "TEXT",
        "keywords": "TEXT",
        "credit_line": "TEXT",
        "source": "TEXT",
        "instructions": "TEXT",
        "rights_usage_terms": "TEXT",
        "intellectual_genre": "TEXT",
        # IPTC/XMP Location & Events
        "location_city": "TEXT",
        "location_state": "TEXT",
        "location_country": "TEXT",
        "location_country_code": "TEXT",
        "location_sublocation": "TEXT",
        "event": "TEXT",
        "subject_code": "TEXT",
        "scene_code": "TEXT",
        # Composite Fields
        "exposure_triangle": "TEXT",  # "ISO 400, f/2.8, 1/250"
        "searchable_text": "TEXT",  # Full-text search index
    }

    # Indexes for performance optimization
    INDEXES = [
        ("idx_metadata_enhanced_camera_make", "camera_make"),
        ("idx_metadata_enhanced_camera_model", "camera_model"),
        ("idx_metadata_enhanced_lens_model", "lens_model"),
        ("idx_metadata_enhanced_iso", "iso"),
        ("idx_metadata_enhanced_aperture", "aperture"),
        ("idx_metadata_enhanced_focal_length", "focal_length"),
        ("idx_metadata_enhanced_exposure_triangle", "exposure_triangle"),
        ("idx_metadata_enhanced_searchable_text", "searchable_text"),
        ("idx_metadata_enhanced_copyright", "copyright"),
        ("idx_metadata_enhanced_creator", "creator"),
        ("idx_metadata_enhanced_keywords", "keywords"),
        ("idx_metadata_enhanced_title", "title"),
        ("idx_metadata_enhanced_location_city", "location_city"),
        ("idx_metadata_enhanced_event", "event"),
    ]

    def __init__(self, db_path: str):
        """
        Initialize enhanced metadata schema.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """Establish database connection with optimized settings."""
        if self.conn is None:
            self.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0,
                isolation_level=None,  # Autocommit mode
            )
            self.conn.row_factory = sqlite3.Row

            # Enable performance optimizations
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")
            self.conn.execute("PRAGMA cache_size=10000")
            self.conn.execute("PRAGMA temp_store=memory")

        return self.conn

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def table_exists(self, table_name: str) -> bool:
        """Check if table exists in database."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name=?
        """,
            (table_name,),
        )
        return cursor.fetchone() is not None

    def column_exists(self, table_name: str, column_name: str) -> bool:
        """Check if column exists in table."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        return column_name in columns

    def get_schema_version(self) -> int:
        """Get current schema version from database."""
        conn = self.connect()
        cursor = conn.cursor()

        # Check if schema_version table exists
        if not self.table_exists("schema_version"):
            return 1  # Original schema

        cursor.execute("SELECT version FROM schema_version ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else 1

    def set_schema_version(self, version: int):
        """Set schema version in database."""
        conn = self.connect()
        cursor = conn.cursor()

        # Create schema_version table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
        conn.commit()
        logger.info(f"Schema version set to {version}")

    def create_enhanced_schema(self) -> bool:
        """
        Create enhanced metadata schema with searchable columns.

        Returns:
            True if schema created successfully
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Check if we need to add columns to existing metadata table
            if self.table_exists("metadata"):
                logger.info("Enhancing existing metadata table with searchable columns")
                self._add_searchable_columns_to_existing_table(cursor)
            else:
                logger.info("Creating new enhanced metadata table")
                self._create_new_enhanced_table(cursor)

            # Create indexes for performance
            self._create_indexes(cursor)

            # Set schema version
            self.set_schema_version(2)

            conn.commit()
            logger.info("Enhanced metadata schema created successfully")
            return True

        except Exception as e:
            logger.error(f"Error creating enhanced schema: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    def _add_searchable_columns_to_existing_table(self, cursor: sqlite3.Cursor):
        """Add searchable columns to existing metadata table."""
        for column_name, column_type in self.SEARCHABLE_COLUMNS.items():
            if not self.column_exists("metadata", column_name):
                try:
                    cursor.execute(f"ALTER TABLE metadata ADD COLUMN {column_name} {column_type}")
                    logger.debug(f"Added column {column_name} to metadata table")
                except Exception as e:
                    logger.warning(f"Could not add column {column_name}: {e}")

    def _create_new_enhanced_table(self, cursor: sqlite3.Cursor):
        """Create new enhanced metadata table from scratch."""
        # Build column definitions
        columns = [
            "id INTEGER PRIMARY KEY AUTOINCREMENT",
            "file_path TEXT UNIQUE NOT NULL",
            "file_hash TEXT NOT NULL",
            "metadata_json TEXT NOT NULL",
            "extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "version INTEGER DEFAULT 1",
            "deleted_at TIMESTAMP",
        ]

        # Add searchable columns
        for column_name, column_type in self.SEARCHABLE_COLUMNS.items():
            columns.append(f"{column_name} {column_type}")

        # Create table
        cursor.execute(f"""
            CREATE TABLE metadata (
                {', '.join(columns)}
            )
        """)

        logger.info("Created new enhanced metadata table")

    def _create_indexes(self, cursor: sqlite3.Cursor):
        """Create database indexes for performance optimization."""
        # Create indexes for existing columns
        existing_indexes = [
            ("idx_metadata_file_hash", "file_hash"),
            ("idx_metadata_extracted_at", "extracted_at"),
            ("idx_metadata_file_path", "file_path"),
        ]

        all_indexes = existing_indexes + self.INDEXES

        for index_name, column_name in all_indexes:
            try:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON metadata({column_name})")
                logger.debug(f"Created index {index_name}")
            except Exception as e:
                logger.warning(f"Could not create index {index_name}: {e}")

    def validate_schema(self) -> Dict[str, Any]:
        """
        Validate that the enhanced schema is properly implemented.

        Returns:
            Dictionary with validation results
        """
        results = {"valid": True, "errors": [], "warnings": [], "missing_columns": [], "missing_indexes": []}

        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Check if metadata table exists
            if not self.table_exists("metadata"):
                results["valid"] = False
                results["errors"].append("metadata table does not exist")
                return results

            # Check for required columns
            cursor.execute("PRAGMA table_info(metadata)")
            existing_columns = {row[1]: row[2] for row in cursor.fetchall()}

            for column_name, expected_type in self.SEARCHABLE_COLUMNS.items():
                if column_name not in existing_columns:
                    results["missing_columns"].append(column_name)
                    results["warnings"].append(f"Missing searchable column: {column_name}")

            # Check for indexes
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            existing_indexes = {row[0] for row in cursor.fetchall()}

            for index_name, _ in self.INDEXES:
                if index_name not in existing_indexes:
                    results["missing_indexes"].append(index_name)
                    results["warnings"].append(f"Missing index: {index_name}")

            # Check schema version
            schema_version = self.get_schema_version()
            if schema_version < 2:
                results["warnings"].append(f"Schema version is {schema_version}, expected 2")

            logger.info(
                f"Schema validation completed: {len(results['errors'])} errors, {len(results['warnings'])} warnings"
            )

        except Exception as e:
            results["valid"] = False
            results["errors"].append(f"Validation error: {e}")
            logger.error(f"Schema validation failed: {e}")

        return results

    def get_table_stats(self) -> Dict[str, Any]:
        """Get statistics about the enhanced metadata table."""
        try:
            conn = self.connect()
            cursor = conn.cursor()

            # Get row count
            cursor.execute("SELECT COUNT(*) FROM metadata")
            total_rows = cursor.fetchone()[0]

            # Get rows with enhanced data
            enhanced_conditions = []
            for column_name in ["camera_make", "lens_model", "iso", "aperture"]:
                enhanced_conditions.append(f"{column_name} IS NOT NULL")

            cursor.execute(f"""
                SELECT COUNT(*) FROM metadata
                WHERE {' OR '.join(enhanced_conditions)}
            """)
            enhanced_rows = cursor.fetchone()[0]

            # Get column statistics for key fields
            stats = {
                "total_rows": total_rows,
                "enhanced_rows": enhanced_rows,
                "enhancement_percentage": (enhanced_rows / total_rows * 100) if total_rows > 0 else 0,
                "column_stats": {},
            }

            # Get statistics for key columns
            key_columns = ["camera_make", "camera_model", "lens_model", "iso", "aperture", "focal_length"]
            for column in key_columns:
                if self.column_exists("metadata", column):
                    cursor.execute(f"SELECT COUNT(*) FROM metadata WHERE {column} IS NOT NULL")
                    non_null_count = cursor.fetchone()[0]
                    stats["column_stats"][column] = {
                        "non_null_count": non_null_count,
                        "percentage": (non_null_count / total_rows * 100) if total_rows > 0 else 0,
                    }

            return stats

        except Exception as e:
            logger.error(f"Error getting table stats: {e}")
            return {"error": str(e)}


def create_enhanced_metadata_schema(db_path: str) -> bool:
    """
    Convenience function to create enhanced metadata schema.

    Args:
        db_path: Path to SQLite database file

    Returns:
        True if schema created successfully
    """
    schema = MetadataSchemaV2(db_path)
    try:
        return schema.create_enhanced_schema()
    finally:
        schema.close()


def validate_enhanced_schema(db_path: str) -> Dict[str, Any]:
    """
    Convenience function to validate enhanced metadata schema.

    Args:
        db_path: Path to SQLite database file

    Returns:
        Validation results dictionary
    """
    schema = MetadataSchemaV2(db_path)
    try:
        return schema.validate_schema()
    finally:
        schema.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Enhanced Metadata Schema Management")
    parser.add_argument("--db", default="metadata.db", help="Database file path")
    parser.add_argument("--create", action="store_true", help="Create enhanced schema")
    parser.add_argument("--validate", action="store_true", help="Validate schema")
    parser.add_argument("--stats", action="store_true", help="Show table statistics")

    args = parser.parse_args()

    if args.create:
        success = create_enhanced_metadata_schema(args.db)
        print(f"Schema creation: {'SUCCESS' if success else 'FAILED'}")

    if args.validate:
        results = validate_enhanced_schema(args.db)
        print(f"Schema validation: {'VALID' if results['valid'] else 'INVALID'}")
        if results["errors"]:
            print("Errors:")
            for error in results["errors"]:
                print(f"  - {error}")
        if results["warnings"]:
            print("Warnings:")
            for warning in results["warnings"]:
                print(f"  - {warning}")

    if args.stats:
        schema = MetadataSchemaV2(args.db)
        try:
            stats = schema.get_table_stats()
            if "error" not in stats:
                print(f"Total rows: {stats['total_rows']}")
                print(f"Enhanced rows: {stats['enhanced_rows']} ({stats['enhancement_percentage']:.1f}%)")
                print("Column statistics:")
                for column, column_stats in stats["column_stats"].items():
                    print(f"  {column}: {column_stats['non_null_count']} ({column_stats['percentage']:.1f}%)")
            else:
                print(f"Error: {stats['error']}")
        finally:
            schema.close()
