import sqlite3
from pathlib import Path
from typing import Optional, Any, Dict
import json


class PhotoEditsDB:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS photo_edits (
                    photo_path TEXT PRIMARY KEY,
                    edit_data TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def get_edit(self, photo_path: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT edit_data, updated_at FROM photo_edits WHERE photo_path = ?",
                (photo_path,),
            ).fetchone()
            if not row:
                return None
            try:
                data = json.loads(row["edit_data"]) if row["edit_data"] else None
            except Exception:
                data = None
            return {"edit_data": data, "updated_at": row["updated_at"]}

    def set_edit(self, photo_path: str, edit_data: Dict[str, Any]):
        payload = json.dumps(edit_data or {})
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO photo_edits(photo_path, edit_data, updated_at)
                VALUES(?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(photo_path) DO UPDATE SET edit_data=excluded.edit_data, updated_at=excluded.updated_at
                """,
                (photo_path, payload),
            )


def get_photo_edits_db(db_path: Path) -> PhotoEditsDB:
    return PhotoEditsDB(db_path)
