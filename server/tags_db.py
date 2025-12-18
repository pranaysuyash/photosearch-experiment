import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class TagSummary:
    name: str
    photo_count: int
    created_at: str
    updated_at: str


class TagsDB:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tags (
                  name TEXT PRIMARY KEY,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tag_photos (
                  tag_name TEXT NOT NULL,
                  photo_path TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  PRIMARY KEY (tag_name, photo_path),
                  FOREIGN KEY (tag_name) REFERENCES tags(name) ON DELETE CASCADE
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tag_photos_tag ON tag_photos(tag_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tag_photos_path ON tag_photos(photo_path)")

    def _ensure_tag(self, name: str) -> None:
        now = _utc_now_iso()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO tags (name, created_at, updated_at)
                VALUES (?, ?, ?)
                """,
                (name, now, now),
            )
            conn.execute(
                """
                UPDATE tags SET updated_at = ? WHERE name = ?
                """,
                (now, name),
            )

    def create_tag(self, name: str) -> None:
        self._ensure_tag(name)

    def list_tags(self, limit: int = 200, offset: int = 0) -> List[TagSummary]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT
                  t.name,
                  t.created_at,
                  t.updated_at,
                  (SELECT COUNT(*) FROM tag_photos tp WHERE tp.tag_name = t.name) AS photo_count
                FROM tags t
                ORDER BY photo_count DESC, t.updated_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [
            TagSummary(
                name=r["name"],
                photo_count=int(r["photo_count"] or 0),
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    def delete_tag(self, name: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM tags WHERE name = ?", (name,))
            return cur.rowcount > 0

    def add_photos(self, tag_name: str, photo_paths: List[str]) -> int:
        self._ensure_tag(tag_name)
        now = _utc_now_iso()
        with self._conn() as conn:
            added = 0
            for p in photo_paths:
                try:
                    cur = conn.execute(
                        """
                        INSERT OR IGNORE INTO tag_photos (tag_name, photo_path, created_at)
                        VALUES (?, ?, ?)
                        """,
                        (tag_name, p, now),
                    )
                    try:
                        if cur.rowcount and cur.rowcount > 0:
                            added += 1
                    except Exception:
                        pass
                except Exception:
                    continue
            conn.execute("UPDATE tags SET updated_at = ? WHERE name = ?", (now, tag_name))
        return added

    def remove_photos(self, tag_name: str, photo_paths: List[str]) -> int:
        with self._conn() as conn:
            removed = 0
            for p in photo_paths:
                cur = conn.execute(
                    "DELETE FROM tag_photos WHERE tag_name = ? AND photo_path = ?",
                    (tag_name, p),
                )
                removed += int(cur.rowcount or 0)
            conn.execute("UPDATE tags SET updated_at = ? WHERE name = ?", (_utc_now_iso(), tag_name))
        return removed

    def get_tag_paths(self, tag_name: str) -> List[str]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT photo_path FROM tag_photos
                WHERE tag_name = ?
                ORDER BY created_at DESC
                """,
                (tag_name,),
            ).fetchall()
        return [r["photo_path"] for r in rows]

    def get_photo_tags(self, photo_path: str) -> List[str]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT tag_name FROM tag_photos
                WHERE photo_path = ?
                ORDER BY created_at DESC
                """,
                (photo_path,),
            ).fetchall()
        return [r["tag_name"] for r in rows]

    def has_tag(self, tag_name: str) -> bool:
        with self._conn() as conn:
            row = conn.execute("SELECT 1 FROM tags WHERE name = ? LIMIT 1", (tag_name,)).fetchone()
        return bool(row)


_tags_db_singleton: Optional[TagsDB] = None


def get_tags_db(db_path: Optional[Path] = None) -> TagsDB:
    global _tags_db_singleton
    if _tags_db_singleton is None:
        if db_path is None:
            # Default next to other app DBs.
            db_path = Path(__file__).resolve().parent.parent / "tags.db"
        _tags_db_singleton = TagsDB(db_path)
    return _tags_db_singleton
