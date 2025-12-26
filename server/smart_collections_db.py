"""
Smart Collections Database Module

Provides functionality for creating and managing smart collections with
automatic photo inclusion based on rules and machine learning.
"""

import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import uuid


class SmartCollection:
    """Represents a smart collection with auto-inclusion rules"""

    id: str
    name: str
    description: str
    rule_definition: Dict[str, Any]  # JSON definition of automatic inclusion criteria
    auto_update: bool
    photo_count: int
    last_updated: str
    created_at: str
    is_favorite: bool
    privacy_level: str  # public, shared, private


class SmartCollectionsDB:
    """Database interface for smart collections"""

    def __init__(self, db_path: Path):
        """
        Initialize the smart collections database.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize tables
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS smart_collections (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    rule_definition TEXT NOT NULL,  -- JSON definition of inclusion criteria
                    auto_update BOOLEAN DEFAULT TRUE,
                    photo_count INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_favorite BOOLEAN DEFAULT FALSE,
                    privacy_level TEXT DEFAULT 'private'  -- public, shared, private
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_smart_collections_name ON smart_collections(name)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_smart_collections_auto_update ON smart_collections(auto_update)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_smart_collections_privacy ON smart_collections(privacy_level)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_smart_collections_created_at ON smart_collections(created_at)")

    def create_smart_collection(
        self,
        name: str,
        description: str,
        rule_definition: Dict[str, Any],
        auto_update: bool = True,
        privacy_level: str = "private",
    ) -> str:
        """
        Create a new smart collection.

        Args:
            name: Name of the collection
            description: Description of the collection
            rule_definition: Dictionary defining inclusion criteria
            auto_update: Whether to automatically update the collection
            privacy_level: Privacy setting (public, shared, private)

        Returns:
            ID of the created collection
        """
        collection_id = str(uuid.uuid4())

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO smart_collections
                    (id, name, description, rule_definition, auto_update, privacy_level)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (collection_id, name, description, json.dumps(rule_definition), auto_update, privacy_level),
                )
                return collection_id
        except sqlite3.IntegrityError:
            # Handle name collision - in a real app we might add a number suffix
            return ""

    def get_smart_collection(self, collection_id: str) -> Optional[SmartCollection]:
        """
        Get a smart collection by ID.

        Args:
            collection_id: ID of the collection

        Returns:
            SmartCollection if found, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                result = conn.execute("SELECT * FROM smart_collections WHERE id = ?", (collection_id,)).fetchone()
                return SmartCollection(**dict(result)) if result else None
        except Exception:
            return None

    def get_smart_collections(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get all smart collections.

        Args:
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of smart collections
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT * FROM smart_collections
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception:
            return []

    def update_smart_collection(
        self,
        collection_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        rule_definition: Optional[Dict[str, Any]] = None,
        auto_update: Optional[bool] = None,
        privacy_level: Optional[str] = None,
        is_favorite: Optional[bool] = None,
    ) -> bool:
        """
        Update a smart collection.

        Args:
            collection_id: ID of the collection to update
            name: New name (optional)
            description: New description (optional)
            rule_definition: New rule definition (optional)
            auto_update: New auto-update setting (optional)
            privacy_level: New privacy level (optional)
            is_favorite: New favorite status (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "UPDATE smart_collections SET last_updated = CURRENT_TIMESTAMP"
                params = []

                if name is not None:
                    query += ", name = ?"
                    params.append(name)

                if description is not None:
                    query += ", description = ?"
                    params.append(description)

                if rule_definition is not None:
                    query += ", rule_definition = ?"
                    params.append(json.dumps(rule_definition))

                if auto_update is not None:
                    query += ", auto_update = ?"
                    params.append(auto_update)

                if privacy_level is not None:
                    query += ", privacy_level = ?"
                    params.append(privacy_level)

                if is_favorite is not None:
                    query += ", is_favorite = ?"
                    params.append(is_favorite)

                query += " WHERE id = ?"
                params.append(collection_id)

                cursor = conn.execute(query, params)
                return cursor.rowcount > 0
        except Exception:
            return False

    def delete_smart_collection(self, collection_id: str) -> bool:
        """
        Delete a smart collection.

        Args:
            collection_id: ID of the collection to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM smart_collections WHERE id = ?", (collection_id,))
                return cursor.rowcount > 0
        except Exception:
            return False

    def get_photos_for_collection(self, collection_id: str) -> List[str]:
        """
        Get photo paths that match the collection's rules.

        Args:
            collection_id: ID of the collection

        Returns:
            List of photo paths that match the collection's rules
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                result = conn.execute(
                    "SELECT rule_definition FROM smart_collections WHERE id = ?", (collection_id,)
                ).fetchone()

                if not result:
                    return []

                json.loads(result["rule_definition"])

                # In a real implementation, this would evaluate the rule against
                # the photo database to find matching photos
                # For this example, we'll return an empty list since we don't
                # have access to the main photo database here
                return []
        except Exception:
            return []

    def get_collections_by_rule_type(self, rule_type: str) -> List[Dict[str, Any]]:
        """
        Get collections that use a specific type of rule.

        Args:
            rule_type: Type of rule (e.g., 'date', 'location', 'people', 'event')

        Returns:
            List of collections that use the specified rule type
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                # Find collections where rule definition contains the specified type
                cursor = conn.execute(
                    """
                    SELECT * FROM smart_collections
                    WHERE rule_definition LIKE ?
                    ORDER BY created_at DESC
                    """,
                    (f"%{rule_type}%",),
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception:
            return []

    def get_collections_stats(self) -> Dict[str, int]:
        """
        Get statistics about smart collections.

        Returns:
            Dictionary with collection statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute("SELECT COUNT(*) as total FROM smart_collections").fetchone()
                total_collections = result["total"] if result else 0

                result = conn.execute(
                    "SELECT COUNT(*) as auto_update FROM smart_collections WHERE auto_update = 1"
                ).fetchone()
                auto_update_count = result["auto_update"] if result else 0

                return {
                    "total_collections": total_collections,
                    "auto_update_collections": auto_update_count,
                    "manual_collections": total_collections - auto_update_count,
                }
        except Exception:
            return {"total_collections": 0, "auto_update_collections": 0, "manual_collections": 0}


def get_smart_collections_db(db_path: Path) -> SmartCollectionsDB:
    """Get smart collections database instance."""
    return SmartCollectionsDB(db_path)
