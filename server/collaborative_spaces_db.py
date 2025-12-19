"""
Collaborative Photo Spaces & Sharing

Provides functionality for creating collaborative photo spaces with shared albums, 
permissions, and real-time synchronization.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
import uuid


class CollaborativeSpace:
    """Represents a collaborative photo space"""
    id: str
    name: str
    description: str
    owner_id: str
    created_at: str
    updated_at: str
    privacy_level: str  # public, shared, private
    max_members: int
    current_members: int


class SpaceMember:
    """Represents a member of a collaborative space"""
    space_id: str
    user_id: str
    role: str  # owner, admin, contributor, viewer
    joined_at: str
    permissions: Dict[str, bool]  # specific permissions for this user
    is_active: bool


class CollaborativeSpacesDB:
    """Database interface for collaborative photo spaces"""

    def __init__(self, db_path: Path):
        """
        Initialize the collaborative spaces database.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize tables
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS collaborative_spaces (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    owner_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    privacy_level TEXT DEFAULT 'private',  -- public, shared, private
                    max_members INTEGER DEFAULT 10,
                    current_members INTEGER DEFAULT 1,
                    INDEX idx_owner_id (owner_id),
                    INDEX idx_privacy_level (privacy_level),
                    INDEX idx_created_at (created_at)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS space_members (
                    space_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    role TEXT DEFAULT 'viewer',  -- owner, admin, contributor, viewer
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    permissions TEXT,  -- JSON string with specific permissions
                    is_active BOOLEAN DEFAULT TRUE,
                    PRIMARY KEY (space_id, user_id),
                    FOREIGN KEY (space_id) REFERENCES collaborative_spaces(id),
                    INDEX idx_space_id (space_id),
                    INDEX idx_user_id (user_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS space_photos (
                    space_id TEXT NOT NULL,
                    photo_path TEXT NOT NULL,
                    added_by TEXT NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    caption TEXT,
                    permissions TEXT,  -- JSON string with access permissions
                    PRIMARY KEY (space_id, photo_path),
                    FOREIGN KEY (space_id) REFERENCES collaborative_spaces(id),
                    INDEX idx_space_photos (space_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS space_comments (
                    id TEXT PRIMARY KEY,
                    space_id TEXT NOT NULL,
                    photo_path TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    comment TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_edited BOOLEAN DEFAULT FALSE,
                    edited_at TIMESTAMP,
                    FOREIGN KEY (space_id) REFERENCES collaborative_spaces(id),
                    INDEX idx_space_photo (space_id, photo_path),
                    INDEX idx_created_at (created_at)
                )
            """)

    def create_collaborative_space(self, 
                                 name: str, 
                                 description: str, 
                                 owner_id: str, 
                                 privacy_level: str = 'private',
                                 max_members: int = 10) -> str:
        """
        Create a new collaborative space.
        
        Args:
            name: Name of the space
            description: Description of the space
            owner_id: ID of the user creating the space
            privacy_level: Privacy level (public, shared, private)
            max_members: Maximum number of members allowed
            
        Returns:
            ID of the created space
        """
        space_id = str(uuid.uuid4())
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Create the space
                conn.execute(
                    """
                    INSERT INTO collaborative_spaces 
                    (id, name, description, owner_id, privacy_level, max_members, current_members)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                    """,
                    (space_id, name, description, owner_id, privacy_level, max_members)
                )
                
                # Add the owner as a member with admin privileges
                default_permissions = {
                    'add_photos': True,
                    'remove_photos': True,
                    'add_comments': True,
                    'remove_comments': True,
                    'manage_members': True,
                    'change_settings': True
                }
                
                conn.execute(
                    """
                    INSERT INTO space_members 
                    (space_id, user_id, role, permissions)
                    VALUES (?, ?, ?, ?)
                    """,
                    (space_id, owner_id, 'owner', json.dumps(default_permissions))
                )
                
                return space_id
        except sqlite3.IntegrityError:
            return ""

    def get_collaborative_space(self, space_id: str) -> Optional[CollaborativeSpace]:
        """
        Get a collaborative space by ID.
        
        Args:
            space_id: ID of the space
            
        Returns:
            CollaborativeSpace if found, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                result = conn.execute(
                    "SELECT * FROM collaborative_spaces WHERE id = ?",
                    (space_id,)
                ).fetchone()
                return CollaborativeSpace(**dict(result)) if result else None
        except Exception:
            return None

    def get_user_spaces(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get all collaborative spaces a user belongs to.
        
        Args:
            user_id: ID of the user
            limit: Maximum number of results to return
            offset: Number of results to skip
            
        Returns:
            List of collaborative spaces the user belongs to
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                # Join to get spaces where user is a member
                cursor = conn.execute(
                    """
                    SELECT cs.*, sm.role
                    FROM collaborative_spaces cs
                    JOIN space_members sm ON cs.id = sm.space_id
                    WHERE sm.user_id = ? AND sm.is_active = 1
                    ORDER BY cs.updated_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (user_id, limit, offset)
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception:
            return []

    def add_member_to_space(self, space_id: str, user_id: str, role: str = 'contributor') -> bool:
        """
        Add a member to a collaborative space.
        
        Args:
            space_id: ID of the space
            user_id: ID of the user to add
            role: Role for the new member (admin, contributor, viewer)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Determine permissions based on role
            permissions = self._get_role_permissions(role)
            
            with sqlite3.connect(self.db_path) as conn:
                # Check if space exists and has room for more members
                space = conn.execute(
                    "SELECT current_members, max_members FROM collaborative_spaces WHERE id = ?",
                    (space_id,)
                ).fetchone()
                
                if not space or space[0] >= space[1]:
                    return False  # No more room
                
                # Add the member
                conn.execute(
                    """
                    INSERT INTO space_members 
                    (space_id, user_id, role, permissions)
                    VALUES (?, ?, ?, ?)
                    """,
                    (space_id, user_id, role, json.dumps(permissions))
                )
                
                # Update member count
                conn.execute(
                    """
                    UPDATE collaborative_spaces 
                    SET current_members = current_members + 1, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (space_id,)
                )
                
                return True
        except sqlite3.IntegrityError:
            # Member already exists
            return False
        except Exception:
            return False

    def remove_member_from_space(self, space_id: str, user_id: str) -> bool:
        """
        Remove a member from a collaborative space.
        
        Args:
            space_id: ID of the space
            user_id: ID of the user to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Don't allow removing the owner
                owner_check = conn.execute(
                    "SELECT owner_id FROM collaborative_spaces WHERE id = ?",
                    (space_id,)
                ).fetchone()
                
                if owner_check and owner_check[0] == user_id:
                    return False  # Cannot remove owner
                
                cursor = conn.execute(
                    "DELETE FROM space_members WHERE space_id = ? AND user_id = ?",
                    (space_id, user_id)
                )
                
                if cursor.rowcount > 0:
                    # Update member count
                    conn.execute(
                        """
                        UPDATE collaborative_spaces 
                        SET current_members = current_members - 1, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (space_id,)
                    )
                    return True
                
                return False
        except Exception:
            return False

    def add_photo_to_space(self, space_id: str, photo_path: str, added_by_user_id: str, caption: str = "") -> bool:
        """
        Add a photo to a collaborative space.
        
        Args:
            space_id: ID of the space
            photo_path: Path to the photo
            added_by_user_id: ID of the user adding the photo
            caption: Optional caption for the photo
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO space_photos 
                    (space_id, photo_path, added_by, caption)
                    VALUES (?, ?, ?, ?)
                    """,
                    (space_id, photo_path, added_by_user_id, caption)
                )
                return True
        except sqlite3.IntegrityError:
            # Photo already exists in this space
            return False
        except Exception:
            return False

    def remove_photo_from_space(self, space_id: str, photo_path: str) -> bool:
        """
        Remove a photo from a collaborative space.
        
        Args:
            space_id: ID of the space
            photo_path: Path to the photo
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM space_photos WHERE space_id = ? AND photo_path = ?",
                    (space_id, photo_path)
                )
                return cursor.rowcount > 0
        except Exception:
            return False

    def add_comment_to_space_photo(self, space_id: str, photo_path: str, user_id: str, comment: str) -> str:
        """
        Add a comment to a photo in a collaborative space.
        
        Args:
            space_id: ID of the space
            photo_path: Path to the photo
            user_id: ID of the user making the comment
            comment: Comment text
            
        Returns:
            ID of the created comment
        """
        comment_id = str(uuid.uuid4())
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO space_comments 
                    (id, space_id, photo_path, user_id, comment)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (comment_id, space_id, photo_path, user_id, comment)
                )
                return comment_id
        except Exception:
            return ""

    def get_space_photos(self, space_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get all photos in a collaborative space.
        
        Args:
            space_id: ID of the space
            limit: Maximum number of results to return
            offset: Number of results to skip
            
        Returns:
            List of photos in the space
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT sp.*, u.username as added_by_username
                    FROM space_photos sp
                    LEFT JOIN users u ON sp.added_by = u.id
                    WHERE sp.space_id = ?
                    ORDER BY sp.added_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (space_id, limit, offset)
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception:
            return []

    def get_photo_comments(self, space_id: str, photo_path: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get all comments for a photo in a collaborative space.
        
        Args:
            space_id: ID of the space
            photo_path: Path to the photo
            limit: Maximum number of results to return
            offset: Number of results to skip
            
        Returns:
            List of comments for the photo
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT sc.*, u.username as author_username
                    FROM space_comments sc
                    LEFT JOIN users u ON sc.user_id = u.id
                    WHERE sc.space_id = ? AND sc.photo_path = ?
                    ORDER BY sc.created_at ASC
                    LIMIT ? OFFSET ?
                    """,
                    (space_id, photo_path, limit, offset)
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception:
            return []

    def update_space_permissions(self, space_id: str, user_id: str, permissions: Dict[str, bool]) -> bool:
        """
        Update permissions for a user in a collaborative space.
        
        Args:
            space_id: ID of the space
            user_id: ID of the user
            permissions: Dictionary of permissions to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    UPDATE space_members 
                    SET permissions = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE space_id = ? AND user_id = ?
                    """,
                    (json.dumps(permissions), space_id, user_id)
                )
                return cursor.rowcount > 0
        except Exception:
            return False

    def get_space_members(self, space_id: str, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """
        Get all members of a collaborative space.
        
        Args:
            space_id: ID of the space
            include_inactive: Whether to include inactive members
            
        Returns:
            List of members in the space
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                where_clause = "WHERE space_id = ?" if not include_inactive else "WHERE space_id = ? AND is_active = 1"
                
                cursor = conn.execute(
                    f"""
                    SELECT sm.*, u.username as user_username
                    FROM space_members sm
                    LEFT JOIN users u ON sm.user_id = u.id
                    {where_clause}
                    ORDER BY sm.joined_at
                    """,
                    (space_id,)
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception:
            return []

    def get_space_stats(self, space_id: str) -> Dict[str, int]:
        """
        Get statistics about a collaborative space.
        
        Args:
            space_id: ID of the space
            
        Returns:
            Dictionary with space statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get space details
                space_info = conn.execute(
                    """
                    SELECT current_members, max_members FROM collaborative_spaces 
                    WHERE id = ?
                    """,
                    (space_id,)
                ).fetchone()
                
                # Count photos in space
                total_photos = conn.execute(
                    "SELECT COUNT(*) FROM space_photos WHERE space_id = ?",
                    (space_id,)
                ).fetchone()[0]
                
                # Count comments in space
                total_comments = conn.execute(
                    "SELECT COUNT(*) FROM space_comments WHERE space_id = ?",
                    (space_id,)
                ).fetchone()[0]
                
                return {
                    'total_members': space_info[0] if space_info else 0,
                    'max_members': space_info[1] if space_info else 0,
                    'total_photos': total_photos,
                    'total_comments': total_comments,
                    'member_utilization': space_info[0] / space_info[1] if space_info and space_info[1] > 0 else 0
                }
        except Exception:
            return {
                'total_members': 0,
                'max_members': 0,
                'total_photos': 0,
                'total_comments': 0,
                'member_utilization': 0
            }

    def _get_role_permissions(self, role: str) -> Dict[str, bool]:
        """Get default permissions for a role."""
        permissions_map = {
            'owner': {
                'add_photos': True,
                'remove_photos': True,
                'add_comments': True,
                'remove_comments': True,
                'manage_members': True,
                'change_settings': True
            },
            'admin': {
                'add_photos': True,
                'remove_photos': True,
                'add_comments': True,
                'remove_comments': True,
                'manage_members': True,
                'change_settings': True
            },
            'contributor': {
                'add_photos': True,
                'remove_photos': False,
                'add_comments': True,
                'remove_comments': False,  # Can only remove their own
                'manage_members': False,
                'change_settings': False
            },
            'viewer': {
                'add_photos': False,
                'remove_photos': False,
                'add_comments': True,
                'remove_comments': False,
                'manage_members': False,
                'change_settings': False
            }
        }
        return permissions_map.get(role, permissions_map['viewer'])


def get_collaborative_spaces_db(db_path: Path) -> CollaborativeSpacesDB:
    """Get collaborative spaces database instance."""
    return CollaborativeSpacesDB(db_path)