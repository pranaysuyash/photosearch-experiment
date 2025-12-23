"""
Face Intelligence Schema Migrations

Provides versioned schema migrations for the face clustering database.
Each migration is idempotent and runs within a transaction.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Current schema version
CURRENT_SCHEMA_VERSION = 3


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Get the current schema version from the database."""
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """)
        row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        return row[0] if row[0] is not None else 0
    except Exception:
        return 0


def set_schema_version(conn: sqlite3.Connection, version: int, description: str):
    """Record a schema version as applied."""
    conn.execute(
        "INSERT INTO schema_version (version, description) VALUES (?, ?)",
        (version, description),
    )


def migration_v1_base_schema(conn: sqlite3.Connection):
    """
    Version 1: Base schema (already exists in most databases).
    This migration ensures the base tables exist with correct structure.
    """
    # Face detections table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS face_detections (
            detection_id TEXT PRIMARY KEY,
            photo_path TEXT NOT NULL,
            bounding_box TEXT NOT NULL,
            embedding BLOB,
            quality_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Face clusters table (people)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS face_clusters (
            cluster_id TEXT PRIMARY KEY,
            label TEXT,
            face_count INTEGER DEFAULT 0,
            photo_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Photo-person associations
    conn.execute("""
        CREATE TABLE IF NOT EXISTS photo_person_associations (
            photo_path TEXT NOT NULL,
            cluster_id TEXT NOT NULL,
            detection_id TEXT NOT NULL,
            confidence REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (photo_path, cluster_id, detection_id),
            FOREIGN KEY (detection_id) REFERENCES face_detections(detection_id),
            FOREIGN KEY (cluster_id) REFERENCES face_clusters(cluster_id)
        )
    """)

    # Base indexes
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_face_detections_photo ON face_detections(photo_path)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_photo_person_photo ON photo_person_associations(photo_path)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_photo_person_cluster ON photo_person_associations(cluster_id)"
    )


def migration_v2_reversibility_and_trust(conn: sqlite3.Connection):
    """
    Version 2: Add reversibility and trust infrastructure.

    Changes:
    - Add assignment_state to photo_person_associations
    - Add hidden, prototype fields to face_clusters
    - Create face_rejections table (normalized, not JSON)
    - Create person_operations_log table for undo
    """

    # === Add columns to photo_person_associations ===
    existing_cols = {
        r[1]
        for r in conn.execute("PRAGMA table_info(photo_person_associations)").fetchall()
    }

    if "assignment_state" not in existing_cols:
        conn.execute("""
            ALTER TABLE photo_person_associations
            ADD COLUMN assignment_state TEXT DEFAULT 'auto'
        """)
        logger.info("Added assignment_state column to photo_person_associations")

    # === Add columns to face_clusters ===
    cluster_cols = {
        r[1] for r in conn.execute("PRAGMA table_info(face_clusters)").fetchall()
    }

    if "hidden" not in cluster_cols:
        conn.execute("ALTER TABLE face_clusters ADD COLUMN hidden INTEGER DEFAULT 0")
        logger.info("Added hidden column to face_clusters")

    if "prototype_embedding" not in cluster_cols:
        conn.execute("ALTER TABLE face_clusters ADD COLUMN prototype_embedding BLOB")
        logger.info("Added prototype_embedding column to face_clusters")

    if "prototype_updated_at" not in cluster_cols:
        conn.execute(
            "ALTER TABLE face_clusters ADD COLUMN prototype_updated_at TIMESTAMP"
        )
        logger.info("Added prototype_updated_at column to face_clusters")

    if "prototype_count" not in cluster_cols:
        conn.execute(
            "ALTER TABLE face_clusters ADD COLUMN prototype_count INTEGER DEFAULT 0"
        )
        logger.info("Added prototype_count column to face_clusters")

    # === Create face_rejections table ===
    # Normalized table for "this face should never be in this cluster"
    conn.execute("""
        CREATE TABLE IF NOT EXISTS face_rejections (
            detection_id TEXT NOT NULL,
            cluster_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (detection_id, cluster_id),
            FOREIGN KEY (detection_id) REFERENCES face_detections(detection_id),
            FOREIGN KEY (cluster_id) REFERENCES face_clusters(cluster_id)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_rejections_detection ON face_rejections(detection_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_rejections_cluster ON face_rejections(cluster_id)"
    )
    logger.info("Created face_rejections table")

    # === Create person_operations_log table ===
    # Stores full reversible snapshots for undo functionality
    conn.execute("""
        CREATE TABLE IF NOT EXISTS person_operations_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_type TEXT NOT NULL,
            operation_data TEXT NOT NULL,
            performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            undone INTEGER DEFAULT 0,
            undone_at TIMESTAMP
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_operations_performed ON person_operations_log(performed_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_operations_undone ON person_operations_log(undone)"
    )
    logger.info("Created person_operations_log table")


def migration_v3_review_queue_and_representative(conn: sqlite3.Connection):
    """
    Version 3: Add review queue table and representative face.

    Changes:
    - Create face_review_queue table for pending face assignments
    - Add representative_detection_id to face_clusters
    """

    # === Create face_review_queue table ===
    conn.execute("""
        CREATE TABLE IF NOT EXISTS face_review_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            detection_id TEXT NOT NULL,
            candidate_cluster_id TEXT NOT NULL,
            similarity REAL NOT NULL,
            reason TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP NULL,
            FOREIGN KEY (detection_id) REFERENCES face_detections(detection_id),
            FOREIGN KEY (candidate_cluster_id) REFERENCES face_clusters(cluster_id)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_review_queue_status ON face_review_queue(status)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_review_queue_detection ON face_review_queue(detection_id)"
    )
    logger.info("Created face_review_queue table")

    # === Add representative_detection_id to face_clusters ===
    cluster_cols = {
        r[1] for r in conn.execute("PRAGMA table_info(face_clusters)").fetchall()
    }

    if "representative_detection_id" not in cluster_cols:
        conn.execute(
            "ALTER TABLE face_clusters ADD COLUMN representative_detection_id TEXT"
        )
        logger.info("Added representative_detection_id column to face_clusters")

    if "representative_updated_at" not in cluster_cols:
        conn.execute(
            "ALTER TABLE face_clusters ADD COLUMN representative_updated_at TIMESTAMP"
        )
        logger.info("Added representative_updated_at column to face_clusters")


# Migration registry: version -> (migration_function, description)
MIGRATIONS = {
    1: (migration_v1_base_schema, "Base schema for face clustering"),
    2: (
        migration_v2_reversibility_and_trust,
        "Add reversibility and trust infrastructure",
    ),
    3: (
        migration_v3_review_queue_and_representative,
        "Add review queue table and representative face",
    ),
}


def run_migrations(db_path: Path, target_version: Optional[int] = None) -> int:
    """
    Run all pending migrations up to target_version.

    Args:
        db_path: Path to the SQLite database
        target_version: Version to migrate to (default: CURRENT_SCHEMA_VERSION)

    Returns:
        Number of migrations applied
    """
    if target_version is None:
        target_version = CURRENT_SCHEMA_VERSION

    migrations_applied = 0

    with sqlite3.connect(str(db_path)) as conn:
        current_version = get_schema_version(conn)

        if current_version >= target_version:
            logger.info(
                f"Schema already at version {current_version}, no migrations needed"
            )
            return 0

        logger.info(
            f"Migrating schema from version {current_version} to {target_version}"
        )

        for version in range(current_version + 1, target_version + 1):
            if version not in MIGRATIONS:
                raise ValueError(f"Missing migration for version {version}")

            migration_fn, description = MIGRATIONS[version]

            logger.info(f"Applying migration v{version}: {description}")

            try:
                # Run migration in a savepoint for partial rollback capability
                conn.execute("SAVEPOINT migration")
                migration_fn(conn)
                set_schema_version(conn, version, description)
                conn.execute("RELEASE SAVEPOINT migration")

                migrations_applied += 1
                logger.info(f"Successfully applied migration v{version}")

            except Exception as e:
                conn.execute("ROLLBACK TO SAVEPOINT migration")
                logger.error(f"Migration v{version} failed: {e}")
                raise

        conn.commit()

    logger.info(
        f"Applied {migrations_applied} migration(s), now at version {target_version}"
    )
    return migrations_applied


def ensure_schema(db_path: Path) -> int:
    """
    Ensure the database schema is up to date.
    Call this on application startup.

    Args:
        db_path: Path to the SQLite database

    Returns:
        Current schema version after migrations
    """
    return run_migrations(db_path)


if __name__ == "__main__":
    # CLI for running migrations manually
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python face_schema_migrations.py <db_path> [target_version]")
        sys.exit(1)

    db_path = Path(sys.argv[1])
    target = int(sys.argv[2]) if len(sys.argv) > 2 else None

    run_migrations(db_path, target)
