"""
Version Stacks for Photo Edits

Manages photo version stacks showing the relationship between original photos and edited versions.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import uuid
from dataclasses import dataclass, asdict, field


@dataclass
class PhotoVersion:
    """Represents a single version of a photo in a version stack."""

    id: str
    original_path: str  # Path to the original photo
    version_path: str  # Path to this specific version
    version_type: str  # 'original', 'edit', 'variant', 'derivative'
    version_name: Optional[str] = None  # User-friendly name for this version
    version_description: Optional[str] = None  # Description of changes made
    edit_instructions: Optional[Dict[str, Any]] = None  # Edit operations applied
    parent_version_id: Optional[str] = None  # ID of parent version in the stack
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if d.get("edit_instructions") is None:
            d["edit_instructions"] = {}
        return d


@dataclass
class VersionStack:
    """Represents a complete version stack with original and all derived versions."""

    id: str
    original_path: str
    version_count: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    versions: List[PhotoVersion] = field(default_factory=list)

    def dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "original_path": self.original_path,
            "version_count": self.version_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "versions": [v.dict() for v in (self.versions or [])],
        }


class PhotoVersionsDB:
    """Database interface for photo version management"""

    def _init_schema(self, conn: sqlite3.Connection) -> None:
        """Create tables and indexes if they don't exist."""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS photo_versions (
                id TEXT PRIMARY KEY,
                original_path TEXT NOT NULL,  -- Path to original photo
                version_path TEXT NOT NULL UNIQUE,  -- Path to this version
                version_type TEXT DEFAULT 'edit',  -- 'original', 'edit', 'variant', 'derivative'
                version_name TEXT,  -- User-friendly name for the version
                version_description TEXT,  -- Description of changes
                edit_instructions TEXT,  -- JSON of edit operations applied
                parent_version_id TEXT,  -- ID of parent version (for edit chains)
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_version_id) REFERENCES photo_versions(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS version_stacks (
                id TEXT PRIMARY KEY,
                original_path TEXT NOT NULL UNIQUE,
                version_count INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Lightweight migrations for older databases.
        cols = {
            row[1]
            for row in conn.execute("PRAGMA table_info(photo_versions)").fetchall()
        }
        if "edit_instructions" not in cols:
            conn.execute("ALTER TABLE photo_versions ADD COLUMN edit_instructions TEXT")
            cols.add("edit_instructions")

        # Some older code used 'editing_instructions'. If present, opportunistically
        # backfill into the canonical 'edit_instructions' column.
        if "editing_instructions" in cols and "edit_instructions" in cols:
            conn.execute(
                """
                UPDATE photo_versions
                SET edit_instructions = editing_instructions
                WHERE (edit_instructions IS NULL OR edit_instructions = '')
                  AND editing_instructions IS NOT NULL
                  AND editing_instructions != ''
                """
            )

        # Indexes must be created separately in SQLite.
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_photo_versions_original_path ON photo_versions(original_path)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_photo_versions_version_path ON photo_versions(version_path)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_photo_versions_parent_version ON photo_versions(parent_version_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_version_stacks_created_at ON version_stacks(created_at)"
        )

    def __init__(self, db_path: Path):
        """
        Initialize the photo versions database.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize tables
        with sqlite3.connect(self.db_path) as conn:
            self._init_schema(conn)

    def create_version(
        self,
        original_path: str,
        version_path: str,
        version_type: str = "edit",
        version_name: Optional[str] = None,
        version_description: Optional[str] = None,
        edit_instructions: Optional[Dict[str, Any]] = None,
        # Backwards-compatible alias used by older endpoint code.
        editing_instructions: Optional[Dict[str, Any]] = None,
        parent_version_id: Optional[str] = None,
    ) -> str:
        """
        Create a new photo version record.

        Args:
            original_path: Path to the original photo
            version_path: Path to this specific version
            version_type: Type of version ('original', 'edit', 'variant', 'derivative')
            version_name: User-friendly name for this version
            version_description: Description of changes made
            edit_instructions: Dictionary of edit operations applied
            parent_version_id: ID of parent version in the stack

        Returns:
            ID of the created version record
        """
        version_id = str(uuid.uuid4())
        effective_instructions = (
            edit_instructions if edit_instructions is not None else editing_instructions
        )
        instructions_json = (
            json.dumps(effective_instructions) if effective_instructions else None
        )

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Create the version record
                conn.execute(
                    """
                    INSERT INTO photo_versions
                    (id, original_path, version_path, version_type, version_name, version_description, edit_instructions, parent_version_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        version_id,
                        original_path,
                        version_path,
                        version_type,
                        version_name,
                        version_description,
                        instructions_json,
                        parent_version_id,
                    ),
                )

                # Update or create the version stack
                stack_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT OR REPLACE INTO version_stacks
                    (id, original_path, version_count)
                    SELECT
                        COALESCE((SELECT id FROM version_stacks WHERE original_path = ?), ?),
                        ?,
                        (SELECT COUNT(*) FROM photo_versions WHERE original_path = ?)
                    """,
                    (original_path, stack_id, original_path, original_path),
                )

                return version_id
        except sqlite3.IntegrityError:
            return ""  # Version already exists

    def get_versions_for_original(self, original_path: str) -> List[Dict[str, Any]]:
        """Return all versions for a given original photo (as dicts)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT * FROM photo_versions
                    WHERE original_path = ?
                    ORDER BY created_at ASC
                    """,
                    (original_path,),
                ).fetchall()

                versions: List[Dict[str, Any]] = []
                for row in rows:
                    d = dict(row)
                    d["edit_instructions"] = (
                        json.loads(d["edit_instructions"])
                        if d.get("edit_instructions")
                        else {}
                    )
                    versions.append(d)
                return versions
        except Exception:
            return []

    def get_version_stack_list(self, photo_path: str) -> List[Dict[str, Any]]:
        """Legacy helper: return the full stack for a photo path (original or version) as a list of dicts."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                result = conn.execute(
                    """
                    SELECT original_path FROM photo_versions
                    WHERE version_path = ? OR original_path = ?
                    """,
                    (photo_path, photo_path),
                ).fetchone()
                if not result:
                    return []

                return self.get_versions_for_original(result["original_path"])
        except Exception:
            return []

    def get_version_stack(self, photo_path: str) -> List[Dict[str, Any]]:
        """Return the full version stack for a photo path (original or version).

        Note: This is a legacy helper used by older code/tests and returns a list
        of dicts (not a VersionStack object).
        """

        return self.get_version_stack_list(photo_path)

    def get_version_stack_for_original(
        self, original_path: str
    ) -> Optional[VersionStack]:
        """Return the complete version stack for an original photo (as a VersionStack)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                stack_info = conn.execute(
                    "SELECT * FROM version_stacks WHERE original_path = ?",
                    (original_path,),
                ).fetchone()
                if not stack_info:
                    return None

                version_rows = conn.execute(
                    """
                    SELECT * FROM photo_versions
                    WHERE original_path = ?
                    ORDER BY created_at ASC
                    """,
                    (original_path,),
                ).fetchall()

                versions = [
                    PhotoVersion(
                        id=row["id"],
                        original_path=row["original_path"],
                        version_path=row["version_path"],
                        version_type=row["version_type"],
                        version_name=row["version_name"],
                        version_description=row["version_description"],
                        edit_instructions=json.loads(row["edit_instructions"])
                        if row["edit_instructions"]
                        else {},
                        parent_version_id=row["parent_version_id"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                    for row in version_rows
                ]

                return VersionStack(
                    id=stack_info["id"],
                    original_path=stack_info["original_path"],
                    version_count=stack_info["version_count"],
                    created_at=stack_info["created_at"],
                    updated_at=stack_info["updated_at"],
                    versions=versions,
                )
        except Exception:
            return None

    def get_version_stack_for_photo(self, photo_path: str) -> Optional[VersionStack]:
        """Resolve a version stack for any photo path (original or version)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                result = conn.execute(
                    """
                    SELECT original_path FROM photo_versions
                    WHERE version_path = ? OR original_path = ?
                    """,
                    (photo_path, photo_path),
                ).fetchone()
                if not result:
                    return None

                return self.get_version_stack_for_original(result["original_path"])
        except Exception:
            return None

    def get_photo_versions(self, photo_path: str) -> List[PhotoVersion]:
        """
        Get all versions for a specific photo (either original or version).

        Args:
            photo_path: Path to the photo (could be original or any version)

        Returns:
            List of all versions in the stack
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # First, find the original path for this photo
                result = conn.execute(
                    """
                    SELECT original_path FROM photo_versions
                    WHERE version_path = ? OR original_path = ?
                    """,
                    (photo_path, photo_path),
                ).fetchone()

                if not result:
                    return []

                original_path = result["original_path"]

                # Get all versions for this original
                cursor = conn.execute(
                    """
                    SELECT * FROM photo_versions
                    WHERE original_path = ?
                    ORDER BY created_at ASC
                    """,
                    (original_path,),
                )
                rows = cursor.fetchall()

                return [
                    PhotoVersion(
                        id=row["id"],
                        original_path=row["original_path"],
                        version_path=row["version_path"],
                        version_type=row["version_type"],
                        version_name=row["version_name"],
                        version_description=row["version_description"],
                        edit_instructions=json.loads(row["edit_instructions"])
                        if row["edit_instructions"]
                        else {},
                        parent_version_id=row["parent_version_id"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                    for row in rows
                ]
        except Exception:
            return []

    def get_original_photo(self, version_path: str) -> Optional[str]:
        """
        Get the original photo path for a version.

        Args:
            version_path: Path to the version

        Returns:
            Path to the original photo, or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                result = conn.execute(
                    "SELECT original_path FROM photo_versions WHERE version_path = ?",
                    (version_path,),
                ).fetchone()
                return result["original_path"] if result else None
        except Exception:
            return None

    def update_version_metadata(
        self,
        version_path: str,
        version_name: Optional[str] = None,
        version_description: Optional[str] = None,
    ) -> bool:
        """
        Update metadata for a specific version.

        Args:
            version_path: Path to the version to update
            version_name: New name for the version
            version_description: New description for the version

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                update_fields = []
                params = []

                if version_name is not None:
                    update_fields.append("version_name = ?")
                    params.append(version_name)

                if version_description is not None:
                    update_fields.append("version_description = ?")
                    params.append(version_description)

                if update_fields:
                    update_fields.append("updated_at = CURRENT_TIMESTAMP")
                    params.append(version_path)

                    sql = f"UPDATE photo_versions SET {', '.join(update_fields)} WHERE version_path = ?"

                    cursor = conn.execute(sql, params)
                    return cursor.rowcount > 0

                return True  # Nothing to update but operation succeeded
        except Exception:
            return False

    def delete_version(self, version_id: str) -> bool:
        """
        Delete a specific version (but not the original unless it's the only version).

        Args:
            version_id: ID of the version to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                # Check if this is the original and only version
                version_info = conn.execute(
                    """
                    SELECT pv.original_path, vs.version_count
                    FROM photo_versions pv
                    JOIN version_stacks vs ON pv.original_path = vs.original_path
                    WHERE pv.id = ?
                    """,
                    (version_id,),
                ).fetchone()

                if not version_info:
                    return False

                original_path = version_info["original_path"]
                version_count = version_info["version_count"]

                # If this is the original and only version, don't allow deletion
                if version_count <= 1:
                    # Check if this is the original version
                    result = conn.execute(
                        "SELECT version_type FROM photo_versions WHERE id = ?",
                        (version_id,),
                    ).fetchone()
                    if result and result["version_type"] == "original":
                        return False  # Can't delete the only version

                cursor = conn.execute(
                    "DELETE FROM photo_versions WHERE id = ?", (version_id,)
                )

                if cursor.rowcount > 0:
                    # Update version count
                    remaining_count = conn.execute(
                        "SELECT COUNT(*) FROM photo_versions WHERE original_path = ?",
                        (original_path,),
                    ).fetchone()[0]

                    conn.execute(
                        """
                        UPDATE version_stacks
                        SET version_count = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE original_path = ?
                        """,
                        (remaining_count, original_path),
                    )

                    return True

                return False
        except Exception:
            return False

    def get_all_stacks(self, limit: int = 50, offset: int = 0) -> List[VersionStack]:
        """
        Get all version stacks with pagination.

        Args:
            limit: Maximum number of stacks to return
            offset: Number of stacks to skip

        Returns:
            List of version stacks
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                cursor = conn.execute(
                    """
                    SELECT * FROM version_stacks
                    ORDER BY updated_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                )
                stack_rows = cursor.fetchall()

                stacks = []
                for stack_row in stack_rows:
                    # Get versions for each stack
                    versions_cursor = conn.execute(
                        """
                        SELECT * FROM photo_versions
                        WHERE original_path = ?
                        ORDER BY created_at ASC
                        """,
                        (stack_row["original_path"],),
                    )
                    version_rows = versions_cursor.fetchall()

                    versions = [
                        PhotoVersion(
                            id=row["id"],
                            original_path=row["original_path"],
                            version_path=row["version_path"],
                            version_type=row["version_type"],
                            version_name=row["version_name"],
                            version_description=row["version_description"],
                            edit_instructions=json.loads(row["edit_instructions"])
                            if row["edit_instructions"]
                            else {},
                            parent_version_id=row["parent_version_id"],
                            created_at=row["created_at"],
                            updated_at=row["updated_at"],
                        )
                        for row in version_rows
                    ]

                    stacks.append(
                        VersionStack(
                            id=stack_row["id"],
                            original_path=stack_row["original_path"],
                            version_count=stack_row["version_count"],
                            created_at=stack_row["created_at"],
                            updated_at=stack_row["updated_at"],
                            versions=versions,
                        )
                    )

                return stacks
        except Exception:
            return []

    def get_version_stats(self) -> Dict[str, int]:
        """
        Get statistics about photo versions.

        Returns:
            Dictionary with version statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Total number of versions
                total_versions = conn.execute(
                    "SELECT COUNT(*) FROM photo_versions"
                ).fetchone()[0]

                # Total number of version stacks (original photos with versions)
                total_stacks = conn.execute(
                    "SELECT COUNT(*) FROM version_stacks"
                ).fetchone()[0]

                # Count of originals vs edits
                original_count = conn.execute(
                    "SELECT COUNT(*) FROM photo_versions WHERE version_type = 'original'"
                ).fetchone()[0]

                edit_count = conn.execute(
                    "SELECT COUNT(*) FROM photo_versions WHERE version_type = 'edit'"
                ).fetchone()[0]

                variant_count = conn.execute(
                    "SELECT COUNT(*) FROM photo_versions WHERE version_type = 'variant'"
                ).fetchone()[0]

                return {
                    "total_versions": total_versions,
                    "total_stacks": total_stacks,
                    "original_count": original_count,
                    "edit_count": edit_count,
                    "variant_count": variant_count,
                    "average_versions_per_stack": total_versions / total_stacks
                    if total_stacks > 0
                    else 0,
                }
        except Exception:
            return {
                "total_versions": 0,
                "total_stacks": 0,
                "original_count": 0,
                "edit_count": 0,
                "variant_count": 0,
                "average_versions_per_stack": 0,
            }

    def merge_version_stacks(self, stack1_path: str, stack2_path: str) -> bool:
        """
        Merge two version stacks into one (useful when determining two paths refer to same photo).

        Args:
            stack1_path: Original path of first stack
            stack2_path: Original path of second stack

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if both exist
                count1 = conn.execute(
                    "SELECT COUNT(*) FROM version_stacks WHERE original_path = ?",
                    (stack1_path,),
                ).fetchone()[0]

                count2 = conn.execute(
                    "SELECT COUNT(*) FROM version_stacks WHERE original_path = ?",
                    (stack2_path,),
                ).fetchone()[0]

                if count1 == 0 or count2 == 0:
                    return False

                # Update all versions from stack2 to point to stack1's original
                conn.execute(
                    """
                    UPDATE photo_versions
                    SET original_path = ?
                    WHERE original_path = ?
                    """,
                    (stack1_path, stack2_path),
                )

                # Update version counts
                new_version_count = conn.execute(
                    "SELECT COUNT(*) FROM photo_versions WHERE original_path = ?",
                    (stack1_path,),
                ).fetchone()[0]

                conn.execute(
                    """
                    UPDATE version_stacks
                    SET version_count = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE original_path = ?
                    """,
                    (new_version_count, stack1_path),
                )

                # Remove the old stack
                conn.execute(
                    "DELETE FROM version_stacks WHERE original_path = ?", (stack2_path,)
                )

                return True
        except Exception:
            return False


def get_photo_versions_db(db_path: Path) -> PhotoVersionsDB:
    """Get photo versions database instance."""
    return PhotoVersionsDB(db_path)
