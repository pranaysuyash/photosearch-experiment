"""
Albums Database Manager

SQLite database for albums and smart albums functionality.
Separate from vector store for clean separation of concerns.
"""

import sqlite3
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class Album:
    id: str
    name: str
    description: Optional[str] = None
    cover_photo_path: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    is_smart: bool = False
    smart_rules: Optional[Dict[str, Any]] = None
    photo_count: int = 0


@dataclass
class AlbumPhoto:
    album_id: str
    photo_path: str
    added_at: Optional[str] = None
    sort_order: int = 0


class AlbumsDB:
    def __init__(self, db_path: str = "albums.db"):
        self.db_path = db_path
        self.conn = None
        self._initialize_db()

    def _initialize_db(self):
        """Create database and tables if they don't exist."""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        cursor = self.conn.cursor()

        # Albums table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS albums (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                cover_photo_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_smart BOOLEAN DEFAULT FALSE,
                smart_rules TEXT  -- JSON string
            )
        """)

        # Album photos junction table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS album_photos (
                album_id TEXT NOT NULL,
                photo_path TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sort_order INTEGER DEFAULT 0,
                PRIMARY KEY (album_id, photo_path),
                FOREIGN KEY (album_id) REFERENCES albums(id) ON DELETE CASCADE
            )
        """)

        # Indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_album_photos_album_id
            ON album_photos(album_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_album_photos_photo_path
            ON album_photos(photo_path)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_albums_is_smart
            ON albums(is_smart)
        """)

        self.conn.commit()

    def create_album(
        self,
        album_id: str,
        name: str,
        description: Optional[str] = None,
        is_smart: bool = False,
        smart_rules: Optional[Dict] = None,
    ) -> Album:
        """Create a new album."""
        cursor = self.conn.cursor()

        smart_rules_json = json.dumps(smart_rules) if smart_rules else None

        cursor.execute(
            """
            INSERT INTO albums (id, name, description, is_smart, smart_rules)
            VALUES (?, ?, ?, ?, ?)
        """,
            (album_id, name, description, is_smart, smart_rules_json),
        )

        self.conn.commit()
        return self.get_album(album_id)

    def get_album(self, album_id: str) -> Optional[Album]:
        """Get album by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM albums WHERE id = ?", (album_id,))
        row = cursor.fetchone()

        if not row:
            return None

        # Get photo count
        cursor.execute(
            """
            SELECT COUNT(*) as count FROM album_photos WHERE album_id = ?
        """,
            (album_id,),
        )
        photo_count = cursor.fetchone()["count"]

        return Album(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            cover_photo_path=row["cover_photo_path"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            is_smart=bool(row["is_smart"]),
            smart_rules=json.loads(row["smart_rules"]) if row["smart_rules"] else None,
            photo_count=photo_count,
        )

    def list_albums(self, include_smart: bool = True) -> List[Album]:
        """List all albums."""
        cursor = self.conn.cursor()

        if include_smart:
            cursor.execute("SELECT * FROM albums ORDER BY created_at DESC")
        else:
            cursor.execute("""
                SELECT * FROM albums WHERE is_smart = FALSE
                ORDER BY created_at DESC
            """)

        albums = []
        for row in cursor.fetchall():
            album_id = row["id"]

            # Get photo count
            cursor.execute(
                """
                SELECT COUNT(*) as count FROM album_photos WHERE album_id = ?
            """,
                (album_id,),
            )
            photo_count = cursor.fetchone()["count"]

            albums.append(
                Album(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    cover_photo_path=row["cover_photo_path"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    is_smart=bool(row["is_smart"]),
                    smart_rules=json.loads(row["smart_rules"]) if row["smart_rules"] else None,
                    photo_count=photo_count,
                )
            )

        return albums

    def update_album(
        self,
        album_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        cover_photo_path: Optional[str] = None,
    ) -> Optional[Album]:
        """Update album details."""
        cursor = self.conn.cursor()

        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)

        if description is not None:
            updates.append("description = ?")
            params.append(description)

        if cover_photo_path is not None:
            updates.append("cover_photo_path = ?")
            params.append(cover_photo_path)

        if not updates:
            return self.get_album(album_id)

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(album_id)

        query = f"UPDATE albums SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        self.conn.commit()

        return self.get_album(album_id)

    def delete_album(self, album_id: str) -> bool:
        """Delete album and all photo associations."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM albums WHERE id = ?", (album_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def add_photos_to_album(self, album_id: str, photo_paths: List[str]) -> int:
        """Add photos to album. Returns count of added photos."""
        cursor = self.conn.cursor()
        added = 0

        for photo_path in photo_paths:
            try:
                cursor.execute(
                    """
                    INSERT INTO album_photos (album_id, photo_path)
                    VALUES (?, ?)
                """,
                    (album_id, photo_path),
                )
                added += 1
            except sqlite3.IntegrityError:
                # Photo already in album
                pass

        # Update album timestamp
        cursor.execute(
            """
            UPDATE albums SET updated_at = CURRENT_TIMESTAMP WHERE id = ?
        """,
            (album_id,),
        )

        self.conn.commit()
        return added

    def remove_photos_from_album(self, album_id: str, photo_paths: List[str]) -> int:
        """Remove photos from album. Returns count of removed photos."""
        cursor = self.conn.cursor()

        placeholders = ",".join("?" * len(photo_paths))
        cursor.execute(
            f"""
            DELETE FROM album_photos
            WHERE album_id = ? AND photo_path IN ({placeholders})
        """,
            [album_id] + photo_paths,
        )

        removed = cursor.rowcount

        # Update album timestamp
        cursor.execute(
            """
            UPDATE albums SET updated_at = CURRENT_TIMESTAMP WHERE id = ?
        """,
            (album_id,),
        )

        self.conn.commit()
        return removed

    def get_album_photos(self, album_id: str, limit: int = 1000, offset: int = 0) -> List[str]:
        """Get photo paths in album."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT photo_path FROM album_photos
            WHERE album_id = ?
            ORDER BY sort_order, added_at DESC
            LIMIT ? OFFSET ?
        """,
            (album_id, limit, offset),
        )

        return [row["photo_path"] for row in cursor.fetchall()]

    def get_photo_albums(self, photo_path: str) -> List[Album]:
        """Get all albums containing a specific photo."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT a.* FROM albums a
            JOIN album_photos ap ON a.id = ap.album_id
            WHERE ap.photo_path = ?
            ORDER BY a.name
        """,
            (photo_path,),
        )

        albums = []
        for row in cursor.fetchall():
            albums.append(
                Album(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    cover_photo_path=row["cover_photo_path"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    is_smart=bool(row["is_smart"]),
                    smart_rules=json.loads(row["smart_rules"]) if row["smart_rules"] else None,
                    photo_count=0,  # Not needed for this query
                )
            )

        return albums

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


# Singleton instance
_albums_db: Optional[AlbumsDB] = None


def get_albums_db() -> AlbumsDB:
    """Get or create albums database singleton."""
    global _albums_db
    if _albums_db is None:
        _albums_db = AlbumsDB()
    return _albums_db
