"""Simple people tagging DB (name tags per photo).

This supports legacy/feature tests that expect free-form people tags independent of
face recognition clusters.

Schema:
- photo_people(photo_path, person_name)

Design goals:
- tiny, deterministic, no heavy ML dependencies
- safe to use in PHOTOSEARCH_TEST_MODE with PHOTOSEARCH_BASE_DIR isolation
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, List


class PeopleTagsDB:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS photo_people (
                    photo_path TEXT NOT NULL,
                    person_name TEXT NOT NULL,
                    UNIQUE(photo_path, person_name)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_photo_people_path ON photo_people(photo_path)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_photo_people_name ON photo_people(person_name)"
            )

    def add_people(self, photo_path: str, people: Iterable[str]) -> int:
        cleaned = [p.strip() for p in people if isinstance(p, str) and p.strip()]
        if not photo_path or not cleaned:
            return 0

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            for name in cleaned:
                cur.execute(
                    "INSERT OR IGNORE INTO photo_people(photo_path, person_name) VALUES (?, ?)",
                    (photo_path, name),
                )
            return cur.rowcount

    def get_people(self, photo_path: str) -> List[str]:
        if not photo_path:
            return []
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT person_name FROM photo_people WHERE photo_path = ? ORDER BY person_name ASC",
                (photo_path,),
            ).fetchall()
        return [r[0] for r in rows]

    def search_photos_by_person(self, person_name: str) -> List[str]:
        q = (person_name or "").strip()
        if not q:
            return []
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT photo_path
                FROM photo_people
                WHERE LOWER(person_name) LIKE LOWER(?)
                ORDER BY photo_path ASC
                """,
                (f"%{q}%",),
            ).fetchall()
        return [r[0] for r in rows]


_people_db_singletons: dict[str, PeopleTagsDB] = {}


def get_people_tags_db(db_path: Path) -> PeopleTagsDB:
    key = str(Path(db_path).resolve())
    db = _people_db_singletons.get(key)
    if db is None:
        db = PeopleTagsDB(Path(db_path))
        _people_db_singletons[key] = db
    return db
