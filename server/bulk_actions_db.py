"""
Bulk Actions Service with Undo Functionality

Provides safe bulk operations with undo capability for photo management operations.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import uuid
from dataclasses import dataclass


@dataclass
class BulkAction:
    """Represents a bulk action that can be undone"""

    id: str
    action_type: str  # 'delete', 'favorite', 'tag_add', 'tag_remove', 'album_add', 'album_remove', 'move', 'copy'
    user_id: str
    affected_paths: List[str]
    operation_data: Dict[str, Any]  # Additional data needed for undo
    status: str  # 'completed', 'failed', 'undone'
    created_at: str
    undone_at: Optional[str]


class BulkActionsDB:
    """Database interface for managing bulk actions with undo capability"""

    def __init__(self, db_path: Path):
        """
        Initialize the bulk actions database.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize tables
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bulk_actions (
                    id TEXT PRIMARY KEY,
                    action_type TEXT NOT NULL, -- delete, favorite, tag_add, tag_remove, etc.
                    user_id TEXT NOT NULL,
                    affected_paths TEXT NOT NULL, -- JSON list of affected file paths
                    operation_data TEXT, -- JSON data needed to undo the operation
                    status TEXT DEFAULT 'completed', -- completed, failed, undone
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    undone_at TIMESTAMP NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bulk_action_history (
                    id TEXT PRIMARY KEY,
                    bulk_action_id TEXT NOT NULL,
                    operation_type TEXT NOT NULL, -- 'execute' or 'undo'
                    result TEXT, -- JSON result of the operation
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (bulk_action_id) REFERENCES bulk_actions(id)
                )
            """)

            # Indexes must be created separately in SQLite.
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_bulk_actions_user_id ON bulk_actions(user_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_bulk_actions_action_type ON bulk_actions(action_type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_bulk_actions_created_at ON bulk_actions(created_at)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_bulk_actions_status ON bulk_actions(status)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_bulk_action_history_bulk_action_id ON bulk_action_history(bulk_action_id)"
            )

    def record_bulk_action(
        self,
        action_type: str,
        user_id: str,
        affected_paths: List[str],
        operation_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Record a bulk action that may need to be undone.

        Args:
            action_type: Type of action (delete, favorite, tag_add, etc.)
            user_id: ID of the user performing the action
            affected_paths: List of file paths affected by the action
            operation_data: Additional data needed to undo the action

        Returns:
            ID of the recorded bulk action
        """
        action_id = str(uuid.uuid4())

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO bulk_actions
                    (id, action_type, user_id, affected_paths, operation_data)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        action_id,
                        action_type,
                        user_id,
                        json.dumps(affected_paths),
                        json.dumps(operation_data) if operation_data else "{}",
                    ),
                )
                return action_id
        except sqlite3.Error:
            return ""

    def get_action_history(
        self,
        user_id: str,
        action_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[BulkAction]:
        """
        Get bulk action history for a user.

        Args:
            user_id: ID of the user
            action_type: Optional specific action type to filter by
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of bulk actions
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                query = "SELECT * FROM bulk_actions WHERE user_id = ?"
                params = [user_id]

                if action_type:
                    query += " AND action_type = ?"
                    params.append(action_type)

                query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                return [
                    BulkAction(
                        id=row["id"],
                        action_type=row["action_type"],
                        user_id=row["user_id"],
                        affected_paths=json.loads(row["affected_paths"]),
                        operation_data=json.loads(row["operation_data"]),
                        status=row["status"],
                        created_at=row["created_at"],
                        undone_at=row["undone_at"],
                    )
                    for row in rows
                ]
        except Exception:
            return []

    def get_bulk_action(self, action_id: str) -> Optional[BulkAction]:
        """Get a single bulk action by ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT * FROM bulk_actions WHERE id = ?",
                    (action_id,),
                ).fetchone()
                if not row:
                    return None
                return BulkAction(
                    id=row["id"],
                    action_type=row["action_type"],
                    user_id=row["user_id"],
                    affected_paths=json.loads(row["affected_paths"])
                    if row["affected_paths"]
                    else [],
                    operation_data=json.loads(row["operation_data"])
                    if row["operation_data"]
                    else {},
                    status=row["status"],
                    created_at=row["created_at"],
                    undone_at=row["undone_at"],
                )
        except Exception:
            return None

    def can_undo_action(self, action_id: str) -> bool:
        """
        Check if a bulk action can be undone.

        Args:
            action_id: ID of the action

        Returns:
            True if the action can be undone, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                result = conn.execute(
                    "SELECT status FROM bulk_actions WHERE id = ?", (action_id,)
                ).fetchone()

                return result and result["status"] == "completed"
        except Exception:
            return False

    def mark_action_undone(self, action_id: str) -> bool:
        """
        Mark a bulk action as undone.

        Args:
            action_id: ID of the action to mark as undone

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    UPDATE bulk_actions
                    SET status = 'undone', undone_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (action_id,),
                )
                return cursor.rowcount > 0
        except Exception:
            return False

    def get_undone_actions_count(self, user_id: str) -> int:
        """
        Get the count of undone actions for a user.

        Args:
            user_id: ID of the user

        Returns:
            Number of undone actions
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute(
                    "SELECT COUNT(*) FROM bulk_actions WHERE user_id = ? AND status = 'undone'",
                    (user_id,),
                ).fetchone()
                return result[0] if result else 0
        except Exception:
            return 0

    def get_recent_actions(self, user_id: str, minutes: int = 10) -> List[BulkAction]:
        """
        Get recent bulk actions for a user.

        Args:
            user_id: ID of the user
            minutes: Number of minutes to look back

        Returns:
            List of recent bulk actions
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT * FROM bulk_actions
                    WHERE user_id = ?
                    AND created_at >= datetime('now', '-{} minutes')
                    ORDER BY created_at DESC
                    """.format(minutes),
                    (user_id,),
                )
                rows = cursor.fetchall()

                return [
                    BulkAction(
                        id=row["id"],
                        action_type=row["action_type"],
                        user_id=row["user_id"],
                        affected_paths=json.loads(row["affected_paths"]),
                        operation_data=json.loads(row["operation_data"]),
                        status=row["status"],
                        created_at=row["created_at"],
                        undone_at=row["undone_at"],
                    )
                    for row in rows
                ]
        except Exception:
            return []


def get_bulk_actions_db(db_path: Path) -> BulkActionsDB:
    """Get bulk actions database instance."""
    return BulkActionsDB(db_path)
