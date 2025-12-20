"""
Multi-tag Filtering Database Module

Provides functionality for complex tag filtering with AND/OR logic.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal, cast
from datetime import datetime
import json


class MultiTagFilterDB:
    """Database interface for multi-tag filtering operations"""

    def __init__(self, db_path: Path):
        """
        Initialize the multi-tag filter database.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize tables
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS photo_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    photo_path TEXT NOT NULL,
                    tag TEXT NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_photo_path (photo_path),
                    INDEX idx_tag (tag),
                    INDEX idx_photo_tag (photo_path, tag),
                    UNIQUE(photo_path, tag)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tag_filters (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    tag_expressions TEXT NOT NULL,  -- JSON array of tag expressions
                    combination_operator TEXT DEFAULT 'AND',  -- 'AND' or 'OR'
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_created_at (created_at)
                )
            """)

    def add_tag_to_photo(self, photo_path: str, tag: str) -> bool:
        """
        Add a tag to a photo.
        
        Args:
            photo_path: Path to the photo
            tag: Tag to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO photo_tags (photo_path, tag) VALUES (?, ?)",
                    (photo_path, tag)
                )
                return True
        except sqlite3.IntegrityError:
            return False  # Tag already exists for this photo
        except Exception:
            return False

    def remove_tag_from_photo(self, photo_path: str, tag: str) -> bool:
        """
        Remove a tag from a photo.
        
        Args:
            photo_path: Path to the photo
            tag: Tag to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM photo_tags WHERE photo_path = ? AND tag = ?",
                    (photo_path, tag)
                )
                return cursor.rowcount > 0
        except Exception:
            return False

    def get_tags_for_photo(self, photo_path: str) -> List[str]:
        """
        Get all tags for a photo.
        
        Args:
            photo_path: Path to the photo
            
        Returns:
            List of tags for the photo
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT tag FROM photo_tags WHERE photo_path = ? ORDER BY tag",
                    (photo_path,)
                )
                rows = cursor.fetchall()
                return [row['tag'] for row in rows]
        except Exception:
            return []

    def get_photos_by_tags(self, 
                          tags: List[str], 
                          operator: Literal['AND', 'OR'] = 'OR',
                          exclude_tags: Optional[List[str]] = None) -> List[str]:
        """
        Get photos by multiple tags with AND/OR logic.
        
        Args:
            tags: List of tags to search for
            operator: How to combine tags ('AND' or 'OR')
            exclude_tags: List of tags to exclude from results
            
        Returns:
            List of photo paths matching the criteria
        """
        if not tags:
            return []
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                params: list[str | int] = []
                
                if operator.upper() == 'AND':
                    # All tags must be present (intersection)
                    # This requires counting that all tags are associated with each photo
                    placeholders = ','.join(['?' for _ in tags])
                    
                    # Count how many of our target tags each photo has
                    query = f"""
                    SELECT photo_path, COUNT(tag) as tag_count
                    FROM photo_tags
                    WHERE tag IN ({placeholders})
                    GROUP BY photo_path
                    HAVING tag_count = ?
                    """
                    params.extend(tags)
                    params.append(len(tags))
                    
                    cursor = conn.execute(query, params)
                    matching_photos = [row['photo_path'] for row in cursor.fetchall()]
                    
                    # Apply exclusions if specified
                    if exclude_tags:
                        matching_photos = self._apply_exclude_tags(conn, matching_photos, exclude_tags)
                        
                elif operator.upper() == 'OR':
                    # Any of the tags can be present (union)
                    placeholders = ','.join(['?' for _ in tags])
                    query = f"""
                    SELECT DISTINCT photo_path
                    FROM photo_tags
                    WHERE tag IN ({placeholders})
                    """
                    params.extend(tags)
                    
                    cursor = conn.execute(query, params)
                    matching_photos = [row['photo_path'] for row in cursor.fetchall()]
                    
                    # Apply exclusions if specified
                    if exclude_tags:
                        matching_photos = self._apply_exclude_tags(conn, matching_photos, exclude_tags)
                else:
                    raise ValueError("Operator must be 'AND' or 'OR'")
                
                return matching_photos
        except Exception as e:
            print(f"Error in get_photos_by_tags: {e}")
            return []

    def _apply_exclude_tags(self, conn: sqlite3.Connection, photo_paths: List[str], exclude_tags: List[str]) -> List[str]:
        """Helper method to filter out photos that have excluded tags."""
        if not exclude_tags:
            return photo_paths
            
        placeholders = ','.join(['?' for _ in exclude_tags])
        exclude_query = f"""
        SELECT DISTINCT photo_path
        FROM photo_tags
        WHERE tag IN ({placeholders})
        """
        
        cursor = conn.execute(exclude_query, exclude_tags)
        excluded_photos = set(row['photo_path'] for row in cursor.fetchall())
        
        # Return only photos that don't have excluded tags
        return [path for path in photo_paths if path not in excluded_photos]

    def create_tag_filter(self, 
                         name: str, 
                         tag_expressions: List[Dict[str, Any]], 
                         combination_operator: str = 'AND') -> str:
        """
        Create a saved tag filter with expressions and operator.
        
        Args:
            name: Name of the filter
            tag_expressions: List of tag expressions (e.g., [{"tag": "beach", "operator": "has"}, {"tag": "sunset", "operator": "not_has"}])
            combination_operator: How to combine expressions ('AND' or 'OR')
            
        Returns:
            ID of the created tag filter
        """
        import uuid
        filter_id = str(uuid.uuid4())
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO tag_filters 
                    (id, name, tag_expressions, combination_operator)
                    VALUES (?, ?, ?, ?)
                    """,
                    (filter_id, name, json.dumps(tag_expressions), combination_operator)
                )
                return filter_id
        except sqlite3.Error:
            return ""

    def get_tag_filter(self, filter_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a tag filter by ID.
        
        Args:
            filter_id: ID of the filter
            
        Returns:
            Tag filter data if found, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                result = conn.execute(
                    "SELECT * FROM tag_filters WHERE id = ?",
                    (filter_id,)
                ).fetchone()
                
                if result:
                    return {
                        'id': result['id'],
                        'name': result['name'],
                        'tag_expressions': json.loads(result['tag_expressions']),
                        'combination_operator': result['combination_operator'],
                        'created_at': result['created_at'],
                        'updated_at': result['updated_at']
                    }
                return None
        except Exception:
            return None

    def apply_tag_filter(self, 
                        tag_expressions: List[Dict[str, Any]], 
                        combination_operator: str = 'AND') -> List[str]:
        """
        Apply a tag filter to find matching photos.
        
        Args:
            tag_expressions: List of tag expressions to match
            combination_operator: How to combine expressions ('AND' or 'OR')
            
        Returns:
            List of photo paths that match the filter
        """
        try:
            # Parse tag expressions to determine include/exclude tags
            include_tags: list[str] = []
            exclude_tags: list[str] = []
            
            for expr in tag_expressions:
                tag = expr.get('tag')
                op = expr.get('operator', 'has')  # 'has', 'not_has'

                if not isinstance(tag, str) or not tag:
                    continue
                
                if op == 'not_has':
                    exclude_tags.append(tag)
                else:
                    include_tags.append(tag)
            
            # Get photos by include tags
            if include_tags:
                op_upper = combination_operator.upper()
                if op_upper not in ('AND', 'OR'):
                    op_upper = 'AND'
                operator_lit = cast(Literal['AND', 'OR'], op_upper)
                return self.get_photos_by_tags(include_tags, operator_lit, exclude_tags or None)
            else:
                # If only exclude tags are specified, we'd need to return all photos except excluded ones
                # For now, return empty list - a more complex implementation would handle this case
                return []
        except Exception as e:
            print(f"Error applying tag filter: {e}")
            return []

    def get_common_tags(self, photo_paths: List[str], limit: int = 10) -> List[str]:
        """Get tags that appear on all provided photos."""
        if not photo_paths:
            return []

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                placeholders = ','.join(['?' for _ in photo_paths])
                query = f"""
                SELECT tag
                FROM photo_tags
                WHERE photo_path IN ({placeholders})
                GROUP BY tag
                HAVING COUNT(DISTINCT photo_path) = ?
                ORDER BY tag
                LIMIT ?
                """
                params: list[str | int] = []
                params.extend(photo_paths)
                params.append(len(photo_paths))
                params.append(limit)
                rows = conn.execute(query, params).fetchall()
                return [row['tag'] for row in rows]
        except Exception:
            return []

    def get_tag_stats(self) -> Dict[str, Any]:
        """Get basic statistics about tags and tagging activity."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                total_tag_rows = conn.execute("SELECT COUNT(*) AS c FROM photo_tags").fetchone()
                total_tag_assignments = int(total_tag_rows['c']) if total_tag_rows else 0

                unique_tag_rows = conn.execute("SELECT COUNT(DISTINCT tag) AS c FROM photo_tags").fetchone()
                unique_tags = int(unique_tag_rows['c']) if unique_tag_rows else 0

                tagged_photo_rows = conn.execute("SELECT COUNT(DISTINCT photo_path) AS c FROM photo_tags").fetchone()
                tagged_photos = int(tagged_photo_rows['c']) if tagged_photo_rows else 0

                top_tags = self.get_photo_tags_with_counts()[:20]

                return {
                    "total_tag_assignments": total_tag_assignments,
                    "unique_tags": unique_tags,
                    "tagged_photos": tagged_photos,
                    "top_tags": top_tags,
                }
        except Exception:
            return {
                "total_tag_assignments": 0,
                "unique_tags": 0,
                "tagged_photos": 0,
                "top_tags": [],
            }

    def get_all_tag_filters(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get all tag filters with pagination.
        
        Args:
            limit: Maximum number of filters to return
            offset: Number of filters to skip
            
        Returns:
            List of tag filters
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT * FROM tag_filters
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset)
                )
                rows = cursor.fetchall()
                
                return [{
                    'id': row['id'],
                    'name': row['name'],
                    'tag_expressions': json.loads(row['tag_expressions']),
                    'combination_operator': row['combination_operator'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                } for row in rows]
        except Exception:
            return []

    def delete_tag_filter(self, filter_id: str) -> bool:
        """
        Delete a tag filter.
        
        Args:
            filter_id: ID of the filter to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM tag_filters WHERE id = ?",
                    (filter_id,)
                )
                return cursor.rowcount > 0
        except Exception:
            return False

    def get_photo_tags_with_counts(self) -> List[Dict[str, Any]]:
        """
        Get all tags with their photo counts.
        
        Returns:
            List of tags with photo counts
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT tag, COUNT(DISTINCT photo_path) as photo_count
                    FROM photo_tags
                    GROUP BY tag
                    ORDER BY photo_count DESC
                    """
                )
                rows = cursor.fetchall()
                
                return [{
                    'tag': row['tag'],
                    'photo_count': row['photo_count']
                } for row in rows]
        except Exception:
            return []

    def search_tags(self, query: str, limit: int = 20) -> List[str]:
        """
        Search for tags by name.
        
        Args:
            query: Search query
            limit: Maximum number of results to return
            
        Returns:
            List of matching tags
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT DISTINCT tag
                    FROM photo_tags
                    WHERE tag LIKE ?
                    ORDER BY tag
                    LIMIT ?
                    """,
                    (f'%{query}%', limit)
                )
                rows = cursor.fetchall()
                
                return [row['tag'] for row in rows]
        except Exception:
            return []


def get_multi_tag_filter_db(db_path: Path) -> MultiTagFilterDB:
    """Get multi-tag filter database instance."""
    return MultiTagFilterDB(db_path)