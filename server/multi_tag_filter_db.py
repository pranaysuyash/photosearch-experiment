"""
Multi-tag Filtering with AND/OR Logic

Provides advanced tag filtering capabilities allowing users to combine multiple tags
with logical operators (AND/OR) for more precise photo searches.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
import json
import uuid


class TagFilter:
    """Represents a tag filter with logical operator"""
    id: str
    name: str
    tag_expressions: List[Dict[str, Any]]  # List of tag conditions with operators
    operator: str  # 'AND' or 'OR' - how to combine the expressions
    created_at: str
    updated_at: str


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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS photo_tags (
                    id INTEGER PRIMARY KEY,
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
                CREATE TABLE IF NOT EXISTS saved_tag_searches (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    tag_filter_id TEXT NOT NULL,  -- References tag_filters.id
                    owner_id TEXT NOT NULL,
                    is_favorite BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tag_filter_id) REFERENCES tag_filters(id),
                    INDEX idx_owner_id (owner_id),
                    INDEX idx_is_favorite (is_favorite),
                    INDEX idx_created_at (created_at)
                )
            """)

    def create_tag_filter(self, 
                         name: str, 
                         tag_expressions: List[Dict[str, Any]], 
                         combination_operator: str = 'AND') -> str:
        """
        Create a new tag filter with expressions and operator.
        
        Args:
            name: Name of the filter
            tag_expressions: List of tag expressions (e.g., [{"tag": "beach", "operator": "has"}, {"tag": "sunset", "operator": "not_has"}])
            combination_operator: How to combine expressions ('AND' or 'OR')
            
        Returns:
            ID of the created tag filter
        """
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

    def get_tag_filter(self, filter_id: str) -> Optional[TagFilter]:
        """
        Get a tag filter by ID.
        
        Args:
            filter_id: ID of the filter
            
        Returns:
            TagFilter if found, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                result = conn.execute(
                    "SELECT * FROM tag_filters WHERE id = ?",
                    (filter_id,)
                ).fetchone()
                
                if result:
                    return TagFilter(
                        id=result['id'],
                        name=result['name'],
                        tag_expressions=json.loads(result['tag_expressions']),
                        combination_operator=result['combination_operator'],
                        created_at=result['created_at'],
                        updated_at=result['updated_at']
                    )
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
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Build the query based on the combination operator
                if combination_operator.upper() == 'AND':
                    # All tags must be present (intersection)
                    query_parts = []
                    params = []
                    
                    for expr in tag_expressions:
                        tag = expr.get('tag')
                        op = expr.get('operator', 'has')  # 'has', 'not_has', 'maybe_has'
                        
                        if op == 'not_has':
                            # Exclude photos with this tag
                            query_parts.append(f"NOT EXISTS (SELECT 1 FROM photo_tags pt{i} WHERE pt{i}.photo_path = p.photo_path AND pt{i}.tag = ?)")
                            params.append(tag)
                        else:
                            # Include photos with this tag
                            query_parts.append(f"EXISTS (SELECT 1 FROM photo_tags pt{i} WHERE pt{i}.photo_path = p.photo_path AND pt{i}.tag = ?)")
                            params.append(tag)
                    
                    query = f"""
                    SELECT DISTINCT p.photo_path
                    FROM (
                        SELECT DISTINCT photo_path FROM photo_tags
                    ) p
                    WHERE {' AND '.join(query_parts)}
                    """
                else:  # OR operator
                    # Any of the tags can be present (union)
                    all_tags = set()
                    include_tags = []
                    exclude_tags = []
                    
                    for expr in tag_expressions:
                        tag = expr.get('tag')
                        op = expr.get('operator', 'has')
                        
                        if op == 'not_has':
                            exclude_tags.append(tag)
                        else:
                            include_tags.append(tag)
                        all_tags.add(tag)
                    
                    query = """
                    SELECT DISTINCT photo_path
                    FROM photo_tags
                    WHERE tag IN ({})
                    """.format(','.join(['?' for _ in include_tags]))
                    
                    params = include_tags
                    
                    if exclude_tags:
                        # Exclude photos that have any of the excluded tags
                        exclude_clause = "AND photo_path NOT IN (SELECT DISTINCT photo_path FROM photo_tags WHERE tag IN ({}))"
                        query += " " + exclude_clause.format(','.join(['?' for _ in exclude_tags]))
                        params.extend(exclude_tags)
                
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                return [row['photo_path'] for row in rows]
        except Exception as e:
            print(f"Error applying tag filter: {e}")
            return []

    def get_photos_by_tags(self, 
                          tags: List[str], 
                          operator: Literal['AND', 'OR'] = 'OR',
                          include_negations: Optional[List[str]] = None) -> List[str]:
        """
        Get photos that match specified tags with AND/OR logic.
        
        Args:
            tags: List of tags to match
            operator: How to combine tags ('AND' or 'OR')
            include_negations: Tags that must NOT be present
            
        Returns:
            List of photo paths that match the criteria
        """
        if not tags:
            return []
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                if operator.upper() == 'AND':
                    # All tags must be present in the photo
                    placeholders = ','.join(['?' for _ in tags])
                    base_query = f"""
                    SELECT photo_path
                    FROM photo_tags
                    WHERE tag IN ({placeholders})
                    GROUP BY photo_path
                    HAVING COUNT(DISTINCT tag) = ?
                    """
                    params = tags + [len(tags)]
                else:  # OR operator
                    # Any of the tags can be present
                    placeholders = ','.join(['?' for _ in tags])
                    base_query = f"""
                    SELECT DISTINCT photo_path
                    FROM photo_tags
                    WHERE tag IN ({placeholders})
                    """
                    params = tags
                
                # Add negation filter if specified
                if include_negations:
                    neg_placeholders = ','.join(['?' for _ in include_negations])
                    base_query += f"""
                    AND photo_path NOT IN (
                        SELECT DISTINCT photo_path 
                        FROM photo_tags 
                        WHERE tag IN ({neg_placeholders})
                    )
                    """
                    params.extend(include_negations)
                
                cursor = conn.execute(base_query, params)
                rows = cursor.fetchall()
                
                return [row['photo_path'] for row in rows]
        except Exception:
            return []

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

    def get_photos_by_single_tag(self, tag: str) -> List[str]:
        """
        Get all photos with a specific tag.
        
        Args:
            tag: Tag to search for
            
        Returns:
            List of photo paths with the tag
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT DISTINCT photo_path FROM photo_tags WHERE tag = ?",
                    (tag,)
                )
                rows = cursor.fetchall()
                return [row['photo_path'] for row in rows]
        except Exception:
            return []

    def get_common_tags(self, photo_paths: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get common tags across multiple photos.
        
        Args:
            photo_paths: List of photo paths
            limit: Maximum number of tags to return
            
        Returns:
            List of common tags with counts
        """
        if not photo_paths:
            return []
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                placeholders = ','.join(['?' for _ in photo_paths])
                
                query = f"""
                SELECT tag, COUNT(*) as count
                FROM photo_tags
                WHERE photo_path IN ({placeholders})
                GROUP BY tag
                ORDER BY count DESC
                LIMIT ?
                """
                params = photo_paths + [limit]
                
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                return [{'tag': row['tag'], 'count': row['count']} for row in rows]
        except Exception:
            return []

    def get_tag_stats(self) -> Dict[str, Any]:
        """
        Get statistics about tags in the system.
        
        Returns:
            Dictionary with tag statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Total number of tags
                total_tags = conn.execute("SELECT COUNT(*) FROM photo_tags").fetchone()[0]
                
                # Total number of distinct tags
                distinct_tags = conn.execute("SELECT COUNT(DISTINCT tag) FROM photo_tags").fetchone()[0]
                
                # Total number of photos with tags
                photos_with_tags = conn.execute("SELECT COUNT(DISTINCT photo_path) FROM photo_tags").fetchone()[0]
                
                # Most common tags
                cursor = conn.execute("""
                    SELECT tag, COUNT(*) as count
                    FROM photo_tags
                    GROUP BY tag
                    ORDER BY count DESC
                    LIMIT 10
                """)
                rows = cursor.fetchall()
                most_common = [{'tag': row['tag'], 'count': row['count']} for row in rows]
                
                return {
                    'total_tag_assignments': total_tags,
                    'distinct_tags': distinct_tags,
                    'photos_with_tags': photos_with_tags,
                    'most_common_tags': most_common
                }
        except Exception:
            return {
                'total_tag_assignments': 0,
                'distinct_tags': 0,
                'photos_with_tags': 0,
                'most_common_tags': []
            }

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


def get_multi_tag_filter_db(db_path: Path) -> MultiTagFilterDB:
    """Get multi-tag filter database instance."""
    return MultiTagFilterDB(db_path)