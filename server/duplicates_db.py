"""
Duplicate Detection and Management System
Provides functionality to detect exact and perceptual duplicates with SQLite backend.
"""

import sqlite3
import hashlib
import os
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime


@dataclass
class DuplicateGroup:
    id: str
    hash_type: str  # 'md5' for exact, 'perceptual' for similar
    files: List[str]  # List of file paths
    similarity_score: Optional[float] = None  # For perceptual duplicates
    created_at: str = None


@dataclass
class DuplicateFile:
    file_path: str
    file_hash: str
    file_size: int
    created_at: str
    group_id: str


class DuplicatesDB:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize the duplicates database."""
        with sqlite3.connect(str(self.db_path)) as conn:
            # Groups table for duplicate sets
            conn.execute("""
                CREATE TABLE IF NOT EXISTS duplicate_groups (
                    id TEXT PRIMARY KEY,
                    hash_type TEXT NOT NULL,
                    similarity_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP,
                    resolution TEXT
                )
            """)

            # Files table linking to groups
            conn.execute("""
                CREATE TABLE IF NOT EXISTS duplicate_files (
                    file_path TEXT PRIMARY KEY,
                    file_hash TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    group_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (group_id) REFERENCES duplicate_groups (id)
                )
            """)

            # Indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_duplicate_groups_hash_type ON duplicate_groups(hash_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_duplicate_files_group_id ON duplicate_files(group_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_duplicate_files_hash ON duplicate_files(file_hash)")

    def add_duplicate_group(self, hash_type: str, files: List[str], similarity_score: Optional[float] = None) -> str:
        """Add a group of duplicate files."""
        group_id = f"grp_{hash_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(files)}"

        with sqlite3.connect(str(self.db_path)) as conn:
            # Add group
            conn.execute(
                """
                INSERT INTO duplicate_groups (id, hash_type, similarity_score)
                VALUES (?, ?, ?)
            """,
                (group_id, hash_type, similarity_score),
            )

            # Add files to group
            for file_path in files:
                file_hash = self._calculate_file_hash(file_path)
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

                conn.execute(
                    """
                    INSERT OR REPLACE INTO duplicate_files (file_path, file_hash, file_size, group_id)
                    VALUES (?, ?, ?, ?)
                """,
                    (file_path, file_hash, file_size, group_id),
                )

        return group_id

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate MD5 hash of a file."""
        if not os.path.exists(file_path):
            return f"missing_{hashlib.md5(file_path.encode()).hexdigest()}"

        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except (IOError, OSError):
            return f"error_{hashlib.md5(file_path.encode()).hexdigest()}"

    def get_duplicate_groups(
        self, hash_type: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[DuplicateGroup]:
        """Get duplicate groups."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            query = "SELECT * FROM duplicate_groups WHERE resolved_at IS NULL"
            params = []

            if hash_type:
                query += " AND hash_type = ?"
                params.append(hash_type)

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            rows = conn.execute(query, params).fetchall()

            groups = []
            for row in rows:
                # Get files for this group
                file_rows = conn.execute(
                    "SELECT file_path, file_hash, file_size FROM duplicate_files WHERE group_id = ?",
                    (row["id"],),
                ).fetchall()

                files = [f["file_path"] for f in file_rows]

                groups.append(
                    DuplicateGroup(
                        id=row["id"],
                        hash_type=row["hash_type"],
                        files=files,
                        similarity_score=row["similarity_score"],
                        created_at=row["created_at"],
                    )
                )

            return groups

    def get_duplicate_stats(self) -> Dict:
        """Get statistics about duplicates."""
        with sqlite3.connect(str(self.db_path)) as conn:
            stats = {}

            # Total groups
            stats["total_groups"] = conn.execute(
                "SELECT COUNT(*) FROM duplicate_groups WHERE resolved_at IS NULL"
            ).fetchone()[0]

            # Groups by type
            for hash_type in ["md5", "perceptual"]:
                count = conn.execute(
                    "SELECT COUNT(*) FROM duplicate_groups WHERE hash_type = ? AND resolved_at IS NULL",
                    (hash_type,),
                ).fetchone()[0]
                stats[f"{hash_type}_groups"] = count

            # Total duplicate files
            stats["total_duplicate_files"] = conn.execute("""
                SELECT COUNT(*) FROM duplicate_files df
                JOIN duplicate_groups dg ON df.group_id = dg.id
                WHERE dg.resolved_at IS NULL
            """).fetchone()[0]

            # Potential space saved (sum of duplicates - keep one per group)
            stats["potential_space_saved"] = (
                conn.execute("""
                SELECT SUM(df.file_size) - (
                    SELECT MAX(file_size)
                    FROM duplicate_files df2
                    WHERE df2.group_id = df.group_id
                )
                FROM duplicate_files df
                JOIN duplicate_groups dg ON df.group_id = dg.id
                WHERE dg.resolved_at IS NULL
            """).fetchone()[0]
                or 0
            )

            return stats

    def resolve_duplicates(self, group_id: str, resolution: str, keep_files: List[str] = None) -> bool:
        """Mark a duplicate group as resolved."""
        with sqlite3.connect(str(self.db_path)) as conn:
            if resolution == "keep_selected" and keep_files:
                # Move non-selected files to trash or mark for deletion
                group_files = conn.execute(
                    "SELECT file_path FROM duplicate_files WHERE group_id = ?",
                    (group_id,),
                ).fetchall()

                all_files = [f[0] for f in group_files]
                files_to_remove = [f for f in all_files if f not in keep_files]

                # Here you could implement actual file deletion or trash moving
                # For now, just mark the group as resolved
                resolution_info = f"keep_{len(keep_files)}_remove_{len(files_to_remove)}"
            else:
                resolution_info = resolution

            conn.execute(
                """
                UPDATE duplicate_groups
                SET resolved_at = CURRENT_TIMESTAMP, resolution = ?
                WHERE id = ?
            """,
                (resolution_info, group_id),
            )

            return True

    def delete_group(self, group_id: str) -> bool:
        """Delete a duplicate group completely."""
        with sqlite3.connect(str(self.db_path)) as conn:
            # Delete files first (foreign key constraint)
            conn.execute("DELETE FROM duplicate_files WHERE group_id = ?", (group_id,))
            # Delete group
            conn.execute("DELETE FROM duplicate_groups WHERE id = ?", (group_id,))
            return True

    def find_exact_duplicates(self, file_paths: List[str]) -> List[DuplicateGroup]:
        """Find exact duplicate files by MD5 hash."""
        hash_to_files = {}

        # Calculate hashes for all files
        for file_path in file_paths:
            if not os.path.exists(file_path):
                continue

            file_hash = self._calculate_file_hash(file_path)
            if file_hash not in hash_to_files:
                hash_to_files[file_hash] = []
            hash_to_files[file_hash].append(file_path)

        # Create groups for duplicates (2+ files with same hash)
        groups = []
        for file_hash, files in hash_to_files.items():
            if len(files) > 1:
                group_id = self.add_duplicate_group("md5", files)
                groups.append(DuplicateGroup(id=group_id, hash_type="md5", files=files, similarity_score=1.0))

        return groups

    def cleanup_missing_files(self) -> int:
        """Remove entries for files that no longer exist."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("SELECT file_path FROM duplicate_files")
            all_files = [row[0] for row in cursor.fetchall()]

            missing_files = [f for f in all_files if not os.path.exists(f)]

            for file_path in missing_files:
                conn.execute("DELETE FROM duplicate_files WHERE file_path = ?", (file_path,))

            return len(missing_files)


def get_duplicates_db(db_path: Path) -> DuplicatesDB:
    """Get duplicates database instance."""
    return DuplicatesDB(db_path)
