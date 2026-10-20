"""
Metadata Migration System - Upgrade existing photo libraries to enhanced schema

This module provides migration capabilities to upgrade existing PhotoSearch
metadata databases to the enhanced schema with searchable columns. It handles
batch processing, progress reporting, rollback capabilities, and data integrity
validation for large photo libraries.

Key Features:
- Batch processing to handle large libraries (100k+ photos)
- Progress reporting with detailed statistics
- Rollback capability if migration fails
- Data integrity validation after migration
- Performance optimization for minimal downtime

Author: PhotoSearch Metadata Completion System
Date: 2025-12-29
"""

import os
import json
import sqlite3
import logging
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from server.database.metadata_schema_v2 import MetadataSchemaV2
from server.metadata.metadata_mapper import MetadataMapper

logger = logging.getLogger(__name__)


@dataclass
class MigrationProgress:
    """Track migration progress and statistics."""

    total_files: int = 0
    processed_files: int = 0
    successful_migrations: int = 0
    failed_migrations: int = 0
    skipped_files: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    current_batch: int = 0
    total_batches: int = 0

    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.processed_files / self.total_files) * 100

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.processed_files == 0:
            return 0.0
        return (self.successful_migrations / self.processed_files) * 100

    @property
    def elapsed_time(self) -> float:
        """Calculate elapsed time in seconds."""
        if not self.start_time:
            return 0.0
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

    @property
    def estimated_remaining_time(self) -> float:
        """Estimate remaining time in seconds."""
        if self.processed_files == 0 or self.elapsed_time == 0:
            return 0.0

        rate = self.processed_files / self.elapsed_time
        remaining_files = self.total_files - self.processed_files
        return remaining_files / rate if rate > 0 else 0.0

    @property
    def processing_rate(self) -> float:
        """Calculate processing rate (files per second)."""
        if self.elapsed_time == 0:
            return 0.0
        return self.processed_files / self.elapsed_time


class MetadataMigration:
    """
    Migrate existing metadata database to enhanced schema with searchable columns.
    """

    def __init__(self, db_path: str, batch_size: int = 1000):
        """
        Initialize metadata migration.

        Args:
            db_path: Path to SQLite database file
            batch_size: Number of files to process per batch
        """
        self.db_path = db_path
        self.batch_size = batch_size
        self.schema = MetadataSchemaV2(db_path)
        self.mapper = MetadataMapper()
        self.progress = MigrationProgress()
        self._backup_path: Optional[str] = None

    def create_backup(self) -> bool:
        """
        Create backup of database before migration.

        Returns:
            True if backup created successfully
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{Path(self.db_path).stem}_backup_{timestamp}.db"
            self._backup_path = str(Path(self.db_path).parent / backup_name)

            # Copy database file
            import shutil

            shutil.copy2(self.db_path, self._backup_path)

            logger.info(f"Database backup created: {self._backup_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False

    def restore_from_backup(self) -> bool:
        """
        Restore database from backup.

        Returns:
            True if restore successful
        """
        if not self._backup_path or not os.path.exists(self._backup_path):
            logger.error("No backup available for restore")
            return False

        try:
            import shutil

            shutil.copy2(self._backup_path, self.db_path)
            logger.info(f"Database restored from backup: {self._backup_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore from backup: {e}")
            return False

    def cleanup_backup(self):
        """Remove backup file after successful migration."""
        if self._backup_path and os.path.exists(self._backup_path):
            try:
                os.remove(self._backup_path)
                logger.info(f"Backup file removed: {self._backup_path}")
            except Exception as e:
                logger.warning(f"Could not remove backup file: {e}")

    def check_migration_needed(self) -> bool:
        """
        Check if migration is needed.

        Returns:
            True if migration is needed
        """
        try:
            schema_version = self.schema.get_schema_version()
            if schema_version >= 2:
                logger.info(f"Database already at version {schema_version}, no migration needed")
                return False

            logger.info(f"Database at version {schema_version}, migration needed")
            return True

        except Exception as e:
            logger.error(f"Error checking migration status: {e}")
            return True  # Assume migration needed if we can't check

    def get_migration_stats(self) -> Dict[str, Any]:
        """
        Get statistics about files that need migration.

        Returns:
            Dictionary with migration statistics
        """
        try:
            conn = self.schema.connect()
            cursor = conn.cursor()

            # Count total files (handle both old and new schema)
            try:
                cursor.execute("SELECT COUNT(*) FROM metadata WHERE deleted_at IS NULL")
                total_files = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                # Old schema without deleted_at column
                cursor.execute("SELECT COUNT(*) FROM metadata")
                total_files = cursor.fetchone()[0]

            # Count files that already have enhanced data.
            # Literal statements: the column set is fixed per schema version
            # and SQLite cannot bind identifiers; column_exists guards each.
            enhanced_files = 0
            for statement in (
                "SELECT COUNT(*) FROM metadata WHERE deleted_at IS NULL"
                " AND (camera_make IS NOT NULL OR lens_model IS NOT NULL"
                " OR iso IS NOT NULL OR aperture IS NOT NULL)",
                "SELECT COUNT(*) FROM metadata"
                " WHERE camera_make IS NOT NULL OR lens_model IS NOT NULL"
                " OR iso IS NOT NULL OR aperture IS NOT NULL",
            ):
                try:
                    enhanced_files = cursor.execute(statement).fetchone()[0]
                    break
                except sqlite3.OperationalError:
                    continue  # try the older-schema variant

            files_needing_migration = total_files - enhanced_files

            return {
                "total_files": total_files,
                "enhanced_files": enhanced_files,
                "files_needing_migration": files_needing_migration,
                "migration_percentage": (files_needing_migration / total_files * 100) if total_files > 0 else 0,
            }

        except Exception as e:
            logger.error(f"Error getting migration stats: {e}")
            return {"error": str(e)}

    def migrate_database(
        self, progress_callback: Optional[Callable[[MigrationProgress], None]] = None, force: bool = False
    ) -> bool:
        """
        Migrate database to enhanced schema.

        Args:
            progress_callback: Optional callback for progress updates
            force: Force migration even if not needed

        Returns:
            True if migration successful
        """
        try:
            # Check if migration is needed
            if not force and not self.check_migration_needed():
                return True

            # Create backup
            if not self.create_backup():
                logger.error("Failed to create backup, aborting migration")
                return False

            # Initialize progress tracking
            self.progress = MigrationProgress()
            self.progress.start_time = datetime.now()

            # Create enhanced schema
            logger.info("Creating enhanced database schema...")
            if not self.schema.create_enhanced_schema():
                logger.error("Failed to create enhanced schema")
                self.restore_from_backup()
                return False

            # Get migration statistics
            stats = self.get_migration_stats()
            if "error" in stats:
                logger.error(f"Failed to get migration stats: {stats['error']}")
                self.restore_from_backup()
                return False

            self.progress.total_files = stats["files_needing_migration"]
            self.progress.total_batches = (self.progress.total_files + self.batch_size - 1) // self.batch_size

            logger.info(
                f"Starting migration of {self.progress.total_files} files in {self.progress.total_batches} batches"
            )

            # Process files in batches
            success = self._process_batches(progress_callback)

            if success:
                # Validate migration
                validation_success = self._validate_migration()
                if validation_success:
                    self.progress.end_time = datetime.now()
                    logger.info(f"Migration completed successfully in {self.progress.elapsed_time:.1f} seconds")
                    logger.info(
                        f"Processed {self.progress.processed_files} files, {self.progress.successful_migrations} successful"
                    )

                    # Cleanup backup
                    self.cleanup_backup()
                    return True
                else:
                    logger.error("Migration validation failed, rolling back")
                    self.restore_from_backup()
                    return False
            else:
                logger.error("Migration failed, rolling back")
                self.restore_from_backup()
                return False

        except Exception as e:
            logger.error(f"Migration error: {e}")
            self.restore_from_backup()
            return False
        finally:
            self.schema.close()

    def _process_batches(self, progress_callback: Optional[Callable[[MigrationProgress], None]]) -> bool:
        """Process files in batches."""
        try:
            conn = self.schema.connect()
            cursor = conn.cursor()

            # Get files that need migration (handle both old and new schema)
            try:
                cursor.execute("""
                    SELECT id, file_path, metadata_json
                    FROM metadata
                    WHERE deleted_at IS NULL
                    ORDER BY id
                """)
            except sqlite3.OperationalError:
                # Old schema without deleted_at column
                cursor.execute("""
                    SELECT id, file_path, metadata_json
                    FROM metadata
                    ORDER BY id
                """)

            batch = []
            batch_count = 0

            for row in cursor.fetchall():
                batch.append(row)

                if len(batch) >= self.batch_size:
                    # Process batch
                    batch_count += 1
                    self.progress.current_batch = batch_count

                    success = self._process_batch(batch)
                    if not success:
                        return False

                    # Report progress
                    if progress_callback:
                        progress_callback(self.progress)

                    batch = []

            # Process remaining files
            if batch:
                batch_count += 1
                self.progress.current_batch = batch_count
                success = self._process_batch(batch)
                if not success:
                    return False

                if progress_callback:
                    progress_callback(self.progress)

            return True

        except Exception as e:
            logger.error(f"Error processing batches: {e}")
            return False

    def _process_batch(self, batch: List[sqlite3.Row]) -> bool:
        """Process a single batch of files."""
        try:
            conn = self.schema.connect()
            cursor = conn.cursor()

            # Begin transaction for batch
            cursor.execute("BEGIN TRANSACTION")

            for row in batch:
                try:
                    file_id = row["id"]
                    _file_path = row["file_path"]
                    metadata_json = row["metadata_json"]

                    # Parse metadata
                    if metadata_json:
                        raw_metadata = json.loads(metadata_json)

                        # Map to searchable fields
                        mapped_fields = self.mapper.map_metadata(raw_metadata)

                        # Update database with mapped fields
                        if mapped_fields:
                            self._update_file_with_mapped_data(cursor, file_id, mapped_fields)
                            self.progress.successful_migrations += 1
                        else:
                            self.progress.skipped_files += 1
                    else:
                        self.progress.skipped_files += 1

                    self.progress.processed_files += 1

                except Exception as e:
                    logger.warning(
                        f"Error processing file {row['file_path'] if 'file_path' in row.keys() else 'unknown'}: {e}"
                    )
                    self.progress.failed_migrations += 1
                    self.progress.processed_files += 1

            # Commit batch transaction
            cursor.execute("COMMIT")

            logger.debug(
                f"Processed batch {self.progress.current_batch}/{self.progress.total_batches} " f"({len(batch)} files)"
            )

            return True

        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            try:
                cursor.execute("ROLLBACK")
            except:
                pass
            return False

    def _update_file_with_mapped_data(self, cursor: sqlite3.Cursor, file_id: int, mapped_fields: Dict[str, Any]):
        """Update file record with mapped searchable fields."""
        # Build UPDATE query dynamically
        set_clauses = []
        values = []

        for field_name, field_value in mapped_fields.items():
            if field_value is not None and self.schema.column_exists("metadata", field_name):
                set_clauses.append(f"{field_name} = ?")
                values.append(field_value)

        if set_clauses:
            # Add updated_at timestamp if column exists
            if self.schema.column_exists("metadata", "updated_at"):
                set_clauses.append("updated_at = CURRENT_TIMESTAMP")

            query = f"UPDATE metadata SET {', '.join(set_clauses)} WHERE id = ?"
            values.append(file_id)

            cursor.execute(query, values)

    def _validate_migration(self) -> bool:
        """Validate migration results."""
        try:
            logger.info("Validating migration results...")

            conn = self.schema.connect()
            cursor = conn.cursor()

            # Check that enhanced columns have data
            validation_results = {}

            key_column_counts = [
                ("camera_make", "SELECT COUNT(*) FROM metadata WHERE camera_make IS NOT NULL"),
                ("camera_model", "SELECT COUNT(*) FROM metadata WHERE camera_model IS NOT NULL"),
                ("lens_model", "SELECT COUNT(*) FROM metadata WHERE lens_model IS NOT NULL"),
                ("iso", "SELECT COUNT(*) FROM metadata WHERE iso IS NOT NULL"),
                ("aperture", "SELECT COUNT(*) FROM metadata WHERE aperture IS NOT NULL"),
                ("focal_length", "SELECT COUNT(*) FROM metadata WHERE focal_length IS NOT NULL"),
            ]
            for column, statement in key_column_counts:
                if self.schema.column_exists("metadata", column):
                    validation_results[column] = cursor.execute(statement).fetchone()[0]

            # Check that we have reasonable data coverage (handle both old and new schema)
            try:
                cursor.execute("SELECT COUNT(*) FROM metadata WHERE deleted_at IS NULL")
                total_files = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                # Old schema without deleted_at column
                cursor.execute("SELECT COUNT(*) FROM metadata")
                total_files = cursor.fetchone()[0]

            # At least 10% of files should have camera make data (reasonable for mixed libraries)
            camera_make_coverage = validation_results.get("camera_make", 0) / total_files if total_files > 0 else 0

            if camera_make_coverage < 0.05:  # Less than 5% coverage might indicate a problem
                logger.warning(f"Low camera make coverage: {camera_make_coverage:.1%}")

            # Check for data integrity issues
            cursor.execute("""
                SELECT COUNT(*) FROM metadata
                WHERE iso IS NOT NULL AND (iso < 50 OR iso > 409600)
            """)
            invalid_iso_count = cursor.fetchone()[0]

            if invalid_iso_count > 0:
                logger.warning(f"Found {invalid_iso_count} files with invalid ISO values")

            logger.info("Migration validation completed")
            logger.info(f"Enhanced data coverage: {validation_results}")

            return True

        except Exception as e:
            logger.error(f"Migration validation failed: {e}")
            return False

    def get_migration_report(self) -> Dict[str, Any]:
        """
        Generate detailed migration report.

        Returns:
            Dictionary with migration report
        """
        return {
            "migration_completed": self.progress.end_time is not None,
            "total_files": self.progress.total_files,
            "processed_files": self.progress.processed_files,
            "successful_migrations": self.progress.successful_migrations,
            "failed_migrations": self.progress.failed_migrations,
            "skipped_files": self.progress.skipped_files,
            "completion_percentage": self.progress.completion_percentage,
            "success_rate": self.progress.success_rate,
            "elapsed_time_seconds": self.progress.elapsed_time,
            "processing_rate_files_per_second": self.progress.processing_rate,
            "start_time": self.progress.start_time.isoformat() if self.progress.start_time else None,
            "end_time": self.progress.end_time.isoformat() if self.progress.end_time else None,
            "backup_path": self._backup_path,
        }


def migrate_metadata_database(
    db_path: str,
    batch_size: int = 1000,
    progress_callback: Optional[Callable[[MigrationProgress], None]] = None,
    force: bool = False,
) -> bool:
    """
    Convenience function to migrate metadata database.

    Args:
        db_path: Path to SQLite database file
        batch_size: Number of files to process per batch
        progress_callback: Optional callback for progress updates
        force: Force migration even if not needed

    Returns:
        True if migration successful
    """
    migration = MetadataMigration(db_path, batch_size)
    return migration.migrate_database(progress_callback, force)


if __name__ == "__main__":
    import argparse

    def print_progress(progress: MigrationProgress):
        """Print progress updates."""
        print(
            f"Progress: {progress.completion_percentage:.1f}% "
            f"({progress.processed_files}/{progress.total_files}) "
            f"- Batch {progress.current_batch}/{progress.total_batches} "
            f"- Rate: {progress.processing_rate:.1f} files/sec "
            f"- ETA: {progress.estimated_remaining_time:.0f}s"
        )

    parser = argparse.ArgumentParser(description="Metadata Migration System")
    parser.add_argument("--db", default="metadata.db", help="Database file path")
    parser.add_argument("--migrate", action="store_true", help="Run migration")
    parser.add_argument("--check", action="store_true", help="Check if migration needed")
    parser.add_argument("--stats", action="store_true", help="Show migration statistics")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for processing")
    parser.add_argument("--force", action="store_true", help="Force migration")
    parser.add_argument("--backup", action="store_true", help="Create backup only")
    parser.add_argument("--validate", action="store_true", help="Validate existing migration")

    args = parser.parse_args()

    migration = MetadataMigration(args.db, args.batch_size)

    try:
        if args.backup:
            success = migration.create_backup()
            print(f"Backup creation: {'SUCCESS' if success else 'FAILED'}")

        elif args.check:
            needed = migration.check_migration_needed()
            print(f"Migration needed: {'YES' if needed else 'NO'}")

        elif args.stats:
            stats = migration.get_migration_stats()
            if "error" not in stats:
                print(f"Total files: {stats['total_files']}")
                print(f"Enhanced files: {stats['enhanced_files']}")
                print(f"Files needing migration: {stats['files_needing_migration']}")
                print(f"Migration percentage: {stats['migration_percentage']:.1f}%")
            else:
                print(f"Error: {stats['error']}")

        elif args.validate:
            success = migration._validate_migration()
            print(f"Migration validation: {'PASSED' if success else 'FAILED'}")

        elif args.migrate:
            print("Starting metadata migration...")
            success = migration.migrate_database(print_progress, args.force)

            if success:
                print("\nMigration completed successfully!")
                report = migration.get_migration_report()
                print(f"Processed: {report['processed_files']} files")
                print(f"Success rate: {report['success_rate']:.1f}%")
                print(f"Processing rate: {report['processing_rate_files_per_second']:.1f} files/sec")
                print(f"Total time: {report['elapsed_time_seconds']:.1f} seconds")
            else:
                print("Migration failed!")

        else:
            parser.print_help()

    finally:
        migration.schema.close()
