"""
Photo Rating System
Provides 1-5 star rating functionality for photos with SQLite backend.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class PhotoRating:
    photo_path: str
    rating: int
    created_at: str
    updated_at: str


class RatingsDB:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize the ratings database."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS photo_ratings (
                    photo_path TEXT PRIMARY KEY,
                    rating INTEGER NOT NULL CHECK (rating >= 0 AND rating <= 5),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rating ON photo_ratings(rating)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_updated ON photo_ratings(updated_at)")

    def set_rating(self, photo_path: str, rating: int) -> bool:
        """Set rating for a photo (0-5 stars, 0 = unrated)."""
        if not (0 <= rating <= 5):
            return False

        with sqlite3.connect(str(self.db_path)) as conn:
            if rating == 0:
                # Remove rating if set to 0
                conn.execute("DELETE FROM photo_ratings WHERE photo_path = ?", (photo_path,))
            else:
                # Insert or update rating
                conn.execute(
                    """
                    INSERT OR REPLACE INTO photo_ratings (photo_path, rating, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """,
                    (photo_path, rating),
                )
        return True

    def get_rating(self, photo_path: str) -> int:
        """Get rating for a photo (0 if unrated)."""
        with sqlite3.connect(str(self.db_path)) as conn:
            result = conn.execute("SELECT rating FROM photo_ratings WHERE photo_path = ?", (photo_path,)).fetchone()
            return result[0] if result else 0

    def get_photos_by_rating(self, rating: int, limit: int = 100, offset: int = 0) -> List[str]:
        """Get photo paths with specific rating."""
        if not (1 <= rating <= 5):
            return []

        with sqlite3.connect(str(self.db_path)) as conn:
            results = conn.execute(
                """
                SELECT photo_path FROM photo_ratings
                WHERE rating = ?
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
            """,
                (rating, limit, offset),
            ).fetchall()
            return [r[0] for r in results]

    def get_all_ratings(self, limit: int = 1000, offset: int = 0) -> List[PhotoRating]:
        """Get all photo ratings."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            results = conn.execute(
                """
                SELECT * FROM photo_ratings
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
            """,
                (limit, offset),
            ).fetchall()

            return [
                PhotoRating(
                    photo_path=r["photo_path"],
                    rating=r["rating"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                )
                for r in results
            ]

    def get_rating_stats(self) -> Dict[int, int]:
        """Get count of photos for each rating."""
        with sqlite3.connect(str(self.db_path)) as conn:
            results = conn.execute("""
                SELECT rating, COUNT(*) as count
                FROM photo_ratings
                GROUP BY rating
                ORDER BY rating
            """).fetchall()
            return {r[0]: r[1] for r in results}

    def remove_rating(self, photo_path: str) -> bool:
        """Remove rating for a photo."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("DELETE FROM photo_ratings WHERE photo_path = ?", (photo_path,))
            return cursor.rowcount > 0

    def bulk_set_ratings(self, ratings: List[tuple]) -> int:
        """Bulk set ratings. ratings = [(path, rating), ...]"""
        count = 0
        with sqlite3.connect(str(self.db_path)) as conn:
            for photo_path, rating in ratings:
                if 0 <= rating <= 5:
                    if rating == 0:
                        conn.execute(
                            "DELETE FROM photo_ratings WHERE photo_path = ?",
                            (photo_path,),
                        )
                    else:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO photo_ratings (photo_path, rating, updated_at)
                            VALUES (?, ?, CURRENT_TIMESTAMP)
                        """,
                            (photo_path, rating),
                        )
                    count += 1
        return count


def get_ratings_db(db_path: Path) -> RatingsDB:
    """Get ratings database instance."""
    return RatingsDB(db_path)
