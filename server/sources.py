import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redact_config(source_type: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    redacted = dict(cfg or {})
    if source_type == "s3":
        if "access_key_id" in redacted:
            redacted["access_key_id"] = (
                str(redacted["access_key_id"])[0:4] + "…" if redacted["access_key_id"] else None
            )
        if "secret_access_key" in redacted:
            redacted["secret_access_key"] = "••••••••"
    if source_type == "google_drive":
        for k in ("client_id", "client_secret", "access_token", "refresh_token", "state_nonce"):
            if k in redacted:
                redacted[k] = "••••••••"
    if source_type == "local_folder":
        # Keep path visible for desktop users, but allow UI to hide it by default.
        # The server returns it as-is to support re-scan.
        pass
    return redacted


@dataclass(frozen=True)
class SourceRecord:
    id: str
    type: str
    name: str
    status: str
    created_at: str
    updated_at: str
    last_sync_at: Optional[str]
    last_error: Optional[str]
    config: Dict[str, Any]


class SourceStore:
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
                CREATE TABLE IF NOT EXISTS sources (
                  id TEXT PRIMARY KEY,
                  type TEXT NOT NULL,
                  name TEXT NOT NULL,
                  status TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  last_sync_at TEXT,
                  last_error TEXT,
                  config_json TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sources_type ON sources(type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sources_status ON sources(status)")

    def create_source(
        self,
        source_type: str,
        name: str,
        config: Optional[Dict[str, Any]] = None,
        status: str = "pending",
    ) -> SourceRecord:
        source_id = str(uuid.uuid4())
        now = _utc_now_iso()
        cfg_json = json.dumps(config or {})
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO sources (id, type, name, status, created_at, updated_at, last_sync_at, last_error, config_json)
                VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, ?)
                """,
                (source_id, source_type, name, status, now, now, cfg_json),
            )
        return self.get_source(source_id, redact=False)

    def get_source(self, source_id: str, redact: bool = True) -> SourceRecord:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
        if not row:
            raise KeyError(f"source not found: {source_id}")
        cfg = json.loads(row["config_json"] or "{}")
        if redact:
            cfg = _redact_config(row["type"], cfg)
        return SourceRecord(
            id=row["id"],
            type=row["type"],
            name=row["name"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_sync_at=row["last_sync_at"],
            last_error=row["last_error"],
            config=cfg,
        )

    def list_sources(self, redact: bool = True) -> List[SourceRecord]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM sources ORDER BY created_at DESC").fetchall()
        out: List[SourceRecord] = []
        for r in rows:
            cfg = json.loads(r["config_json"] or "{}")
            if redact:
                cfg = _redact_config(r["type"], cfg)
            out.append(
                SourceRecord(
                    id=r["id"],
                    type=r["type"],
                    name=r["name"],
                    status=r["status"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                    last_sync_at=r["last_sync_at"],
                    last_error=r["last_error"],
                    config=cfg,
                )
            )
        return out

    def update_source(
        self,
        source_id: str,
        *,
        name: Optional[str] = None,
        status: Optional[str] = None,
        last_sync_at: Optional[str] = None,
        last_error: Optional[str] = None,
        config_patch: Optional[Dict[str, Any]] = None,
    ) -> SourceRecord:
        existing = self.get_source(source_id, redact=False)
        next_cfg = dict(existing.config or {})
        if config_patch:
            next_cfg.update(config_patch)
        updates: List[Tuple[str, Any]] = []
        if name is not None:
            updates.append(("name", name))
        if status is not None:
            updates.append(("status", status))
        if last_sync_at is not None:
            updates.append(("last_sync_at", last_sync_at))
        if last_error is not None:
            updates.append(("last_error", last_error))
        updates.append(("config_json", json.dumps(next_cfg)))
        updates.append(("updated_at", _utc_now_iso()))

        set_clause = ", ".join([f"{k} = ?" for k, _ in updates])
        values = [v for _, v in updates] + [source_id]

        with self._conn() as conn:
            conn.execute(f"UPDATE sources SET {set_clause} WHERE id = ?", values)

        return self.get_source(source_id, redact=False)

    def delete_source(self, source_id: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM sources WHERE id = ?", (source_id,))

