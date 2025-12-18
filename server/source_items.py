import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class SourceItem:
    source_id: str
    remote_id: str
    remote_path: str
    etag: Optional[str]
    modified_at: Optional[str]
    size_bytes: Optional[int]
    mime_type: Optional[str]
    name: Optional[str]
    local_path: Optional[str]
    status: str  # active | deleted | trashed | removed
    last_seen_at: str
    created_at: str
    updated_at: str


class SourceItemStore:
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
                CREATE TABLE IF NOT EXISTS source_items (
                  source_id TEXT NOT NULL,
                  remote_id TEXT NOT NULL,
                  remote_path TEXT NOT NULL,
                  etag TEXT,
                  modified_at TEXT,
                  size_bytes INTEGER,
                  mime_type TEXT,
                  name TEXT,
                  local_path TEXT,
                  status TEXT NOT NULL DEFAULT 'active',
                  last_seen_at TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  PRIMARY KEY (source_id, remote_id)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_source_items_source ON source_items(source_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_source_items_status ON source_items(status)"
            )

    def upsert_seen(
        self,
        *,
        source_id: str,
        remote_id: str,
        remote_path: str,
        etag: Optional[str],
        modified_at: Optional[str],
        size_bytes: Optional[int],
        mime_type: Optional[str],
        name: Optional[str],
    ) -> SourceItem:
        now = _utc_now_iso()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM source_items WHERE source_id = ? AND remote_id = ?",
                (source_id, remote_id),
            ).fetchone()
            if row:
                # Preserve user-driven states (don't flip back to active on sync).
                # - trashed: in Recently Deleted (restorable)
                # - removed: removed from library (do not re-download on sync)
                next_status = row["status"] if row["status"] in ("trashed", "removed") else "active"
                conn.execute(
                    """
                    UPDATE source_items
                    SET remote_path = ?, etag = ?, modified_at = ?, size_bytes = ?, mime_type = ?, name = ?,
                        status = ?, last_seen_at = ?, updated_at = ?
                    WHERE source_id = ? AND remote_id = ?
                    """,
                    (
                        remote_path,
                        etag,
                        modified_at,
                        size_bytes,
                        mime_type,
                        name,
                        next_status,
                        now,
                        now,
                        source_id,
                        remote_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO source_items
                    (source_id, remote_id, remote_path, etag, modified_at, size_bytes, mime_type, name, local_path, status, last_seen_at, created_at, updated_at)
                    VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, NULL, 'active', ?, ?, ?)
                    """,
                    (
                        source_id,
                        remote_id,
                        remote_path,
                        etag,
                        modified_at,
                        size_bytes,
                        mime_type,
                        name,
                        now,
                        now,
                        now,
                    ),
                )
        return self.get(source_id, remote_id)

    def set_status(self, source_id: str, remote_id: str, status: str) -> None:
        now = _utc_now_iso()
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE source_items
                SET status = ?, updated_at = ?
                WHERE source_id = ? AND remote_id = ?
                """,
                (status, now, source_id, remote_id),
            )

    def set_local_path(self, source_id: str, remote_id: str, local_path: str) -> None:
        now = _utc_now_iso()
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE source_items
                SET local_path = ?, updated_at = ?
                WHERE source_id = ? AND remote_id = ?
                """,
                (local_path, now, source_id, remote_id),
            )

    def mark_missing_as_deleted(self, source_id: str, seen_at: str) -> List[SourceItem]:
        """
        Mark items not seen at `seen_at` as deleted.
        Returns list of items transitioned to deleted.
        """
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM source_items
                WHERE source_id = ? AND status = 'active' AND last_seen_at < ?
                """,
                (source_id, seen_at),
            ).fetchall()
            conn.execute(
                """
                UPDATE source_items
                SET status = 'deleted', updated_at = ?
                WHERE source_id = ? AND status = 'active' AND last_seen_at < ?
                """,
                (_utc_now_iso(), source_id, seen_at),
            )
        return [self._row_to_item(r) for r in rows]

    def list_by_source(self, source_id: str) -> List[SourceItem]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM source_items WHERE source_id = ? ORDER BY created_at DESC",
                (source_id,),
            ).fetchall()
        return [self._row_to_item(r) for r in rows]

    def find_by_local_path(self, local_path: str) -> Optional[SourceItem]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM source_items WHERE local_path = ? LIMIT 1",
                (local_path,),
            ).fetchone()
        if not row:
            return None
        return self._row_to_item(row)

    def get(self, source_id: str, remote_id: str) -> SourceItem:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM source_items WHERE source_id = ? AND remote_id = ?",
                (source_id, remote_id),
            ).fetchone()
        if not row:
            raise KeyError("source item not found")
        return self._row_to_item(row)

    def _row_to_item(self, row: sqlite3.Row) -> SourceItem:
        return SourceItem(
            source_id=row["source_id"],
            remote_id=row["remote_id"],
            remote_path=row["remote_path"],
            etag=row["etag"],
            modified_at=row["modified_at"],
            size_bytes=row["size_bytes"],
            mime_type=row["mime_type"],
            name=row["name"],
            local_path=row["local_path"],
            status=row["status"],
            last_seen_at=row["last_seen_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
