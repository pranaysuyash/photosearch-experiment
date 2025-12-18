"""
Trash DB

App-level Trash/Restore for media items.

- For local folder sources: moves the original file into an app-managed trash folder.
- For cloud sources (Drive/S3): moves the mirrored local copy into trash; does NOT delete remote originals.
"""

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class TrashItem:
    id: str
    original_path: str
    trashed_path: str
    status: str  # trashed | restored | deleted
    source_id: Optional[str]
    remote_id: Optional[str]
    created_at: str
    updated_at: str
    restored_at: Optional[str]
    deleted_at: Optional[str]


class TrashDB:
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
                CREATE TABLE IF NOT EXISTS trash_items (
                  id TEXT PRIMARY KEY,
                  original_path TEXT NOT NULL,
                  trashed_path TEXT NOT NULL,
                  status TEXT NOT NULL,
                  source_id TEXT,
                  remote_id TEXT,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  restored_at TEXT,
                  deleted_at TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_trash_status ON trash_items(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_trash_source ON trash_items(source_id)")

    def create(
        self,
        *,
        item_id: Optional[str] = None,
        original_path: str,
        trashed_path: str,
        source_id: Optional[str],
        remote_id: Optional[str],
    ) -> TrashItem:
        item_id = item_id or str(uuid.uuid4())
        now = _utc_now_iso()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO trash_items
                (id, original_path, trashed_path, status, source_id, remote_id, created_at, updated_at, restored_at, deleted_at)
                VALUES
                (?, ?, ?, 'trashed', ?, ?, ?, ?, NULL, NULL)
                """,
                (item_id, original_path, trashed_path, source_id, remote_id, now, now),
            )
        return self.get(item_id)

    def get(self, item_id: str) -> TrashItem:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM trash_items WHERE id = ?", (item_id,)).fetchone()
        if not row:
            raise KeyError("trash item not found")
        return TrashItem(
            id=row["id"],
            original_path=row["original_path"],
            trashed_path=row["trashed_path"],
            status=row["status"],
            source_id=row["source_id"],
            remote_id=row["remote_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            restored_at=row["restored_at"],
            deleted_at=row["deleted_at"],
        )

    def list(self, status: str = "trashed", limit: int = 200, offset: int = 0) -> List[TrashItem]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM trash_items
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (status, limit, offset),
            ).fetchall()
        return [
            TrashItem(
                id=r["id"],
                original_path=r["original_path"],
                trashed_path=r["trashed_path"],
                status=r["status"],
                source_id=r["source_id"],
                remote_id=r["remote_id"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                restored_at=r["restored_at"],
                deleted_at=r["deleted_at"],
            )
            for r in rows
        ]

    def mark_restored(self, item_id: str) -> None:
        now = _utc_now_iso()
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE trash_items
                SET status = 'restored', restored_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (now, now, item_id),
            )

    def mark_deleted(self, item_id: str) -> None:
        now = _utc_now_iso()
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE trash_items
                SET status = 'deleted', deleted_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (now, now, item_id),
            )
