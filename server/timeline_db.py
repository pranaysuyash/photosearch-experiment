"""
Timeline & Story Creation Tools

Provides functionality for automatically generating photo timelines and story narratives
from photo collections based on dates, locations, and content.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
import uuid
from dataclasses import dataclass


@dataclass
class TimelineEntry:
    """Represents a single entry in a photo timeline"""
    id: str
    story_id: str
    photo_path: str
    date: str
    location: Optional[str]
    caption: Optional[str]
    narrative_order: int
    created_at: str
    updated_at: str


@dataclass
class StoryNarrative:
    """Represents a story narrative created from multiple photos"""
    id: str
    title: str
    description: str
    owner_id: str
    created_at: str
    updated_at: str
    is_published: bool
    metadata: Optional[Dict[str, Any]]
    timeline_entries: List[TimelineEntry]


class TimelineDB:
    """Database interface for timeline and story creation"""

    def __init__(self, db_path: Path):
        """
        Initialize the timeline database.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize tables
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stories (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    owner_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_published BOOLEAN DEFAULT FALSE,
                    metadata TEXT, -- JSON metadata about the story
                    INDEX idx_owner_id (owner_id),
                    INDEX idx_is_published (is_published),
                    INDEX idx_created_at (created_at)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS timeline_entries (
                    id TEXT PRIMARY KEY,
                    story_id TEXT NOT NULL,
                    photo_path TEXT NOT NULL,
                    date TIMESTAMP NOT NULL,
                    location TEXT,
                    caption TEXT,
                    narrative_order INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (story_id) REFERENCES stories(id),
                    INDEX idx_story_id (story_id),
                    INDEX idx_date (date),
                    INDEX idx_narrative_order (narrative_order)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS story_tags (
                    id TEXT PRIMARY KEY,
                    story_id TEXT NOT NULL,
                    tag TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (story_id) REFERENCES stories(id),
                    UNIQUE(story_id, tag),
                    INDEX idx_story_tag (story_id, tag)
                )
            """)

    def create_story(self, 
                     title: str, 
                     description: str, 
                     owner_id: str, 
                     metadata: Optional[Dict[str, Any]] = None,
                     is_published: bool = False) -> str:
        """
        Create a new story narrative.
        
        Args:
            title: Title of the story
            description: Description of the story
            owner_id: ID of the story owner
            metadata: Additional metadata about the story
            is_published: Whether the story is published
            
        Returns:
            ID of the created story
        """
        story_id = str(uuid.uuid4())
        metadata_json = json.dumps(metadata) if metadata else '{}'
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO stories 
                    (id, title, description, owner_id, is_published, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (story_id, title, description, owner_id, is_published, metadata_json)
                )
                return story_id
        except sqlite3.IntegrityError:
            return ""

    def get_story(self, story_id: str) -> Optional[StoryNarrative]:
        """
        Get a story narrative by ID.
        
        Args:
            story_id: ID of the story
            
        Returns:
            StoryNarrative if found, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                story_row = conn.execute(
                    "SELECT * FROM stories WHERE id = ?",
                    (story_id,)
                ).fetchone()
                
                if not story_row:
                    return None

                # Get timeline entries for this story
                entries_cursor = conn.execute(
                    """
                    SELECT * FROM timeline_entries 
                    WHERE story_id = ? 
                    ORDER BY narrative_order ASC
                    """,
                    (story_id,)
                )
                entry_rows = entries_cursor.fetchall()

                timeline_entries = [
                    TimelineEntry(
                        id=row['id'],
                        story_id=row['story_id'],
                        photo_path=row['photo_path'],
                        date=row['date'],
                        location=row['location'],
                        caption=row['caption'],
                        narrative_order=row['narrative_order'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at']
                    ) for row in entry_rows
                ]

                return StoryNarrative(
                    id=story_row['id'],
                    title=story_row['title'],
                    description=story_row['description'],
                    owner_id=story_row['owner_id'],
                    created_at=story_row['created_at'],
                    updated_at=story_row['updated_at'],
                    is_published=bool(story_row['is_published']),
                    metadata=json.loads(row['metadata']) if row['metadata'] else {},
                    timeline_entries=timeline_entries
                )
        except Exception:
            return None

    def add_photo_to_timeline(self, 
                              story_id: str, 
                              photo_path: str, 
                              date: str, 
                              location: Optional[str] = None, 
                              caption: Optional[str] = None) -> str:
        """
        Add a photo to a story's timeline.
        
        Args:
            story_id: ID of the story
            photo_path: Path to the photo
            date: Date of the photo
            location: Optional location for the photo
            caption: Optional caption for the photo
            
        Returns:
            ID of the created timeline entry
        """
        entry_id = str(uuid.uuid4())
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get the next narrative order position for this story
                next_order = conn.execute(
                    "SELECT COALESCE(MAX(narrative_order), 0) + 1 FROM timeline_entries WHERE story_id = ?",
                    (story_id,)
                ).fetchone()[0]
                
                conn.execute(
                    """
                    INSERT INTO timeline_entries 
                    (id, story_id, photo_path, date, location, caption, narrative_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (entry_id, story_id, photo_path, date, location, caption, next_order)
                )
                return entry_id
        except sqlite3.IntegrityError:
            return ""

    def update_timeline_entry_order(self, entry_id: str, new_order: int) -> bool:
        """
        Update the narrative order of a timeline entry.
        
        Args:
            entry_id: ID of the timeline entry
            new_order: New narrative order position
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    UPDATE timeline_entries 
                    SET narrative_order = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (new_order, entry_id)
                )
                return cursor.rowcount > 0
        except Exception:
            return False

    def remove_photo_from_timeline(self, entry_id: str) -> bool:
        """
        Remove a photo from a story's timeline.
        
        Args:
            entry_id: ID of the timeline entry to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM timeline_entries WHERE id = ?",
                    (entry_id,)
                )
                return cursor.rowcount > 0
        except Exception:
            return False

    def get_stories_by_owner(self, 
                           owner_id: str, 
                           include_unpublished: bool = False, 
                           limit: int = 50, 
                           offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get all stories for an owner.
        
        Args:
            owner_id: ID of the owner
            include_unpublished: Whether to include unpublished stories
            limit: Maximum number of stories to return
            offset: Number of stories to skip
            
        Returns:
            List of stories for the owner
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                where_clause = "WHERE owner_id = ?"
                params = [owner_id]
                
                if not include_unpublished:
                    where_clause += " AND is_published = 1"
                
                cursor = conn.execute(
                    f"""
                    SELECT * FROM stories 
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (*params, limit, offset)
                )
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
        except Exception:
            return []

    def get_stories_by_date_range(self, 
                                 start_date: str, 
                                 end_date: str, 
                                 limit: int = 50, 
                                 offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get all stories with photos in a given date range.
        
        Args:
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            limit: Maximum number of stories to return
            offset: Number of stories to skip
            
        Returns:
            List of stories with photos in the date range
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT DISTINCT s.*, COUNT(te.id) as photo_count
                    FROM stories s
                    JOIN timeline_entries te ON s.id = te.story_id
                    WHERE te.date BETWEEN ? AND ?
                    GROUP BY s.id
                    ORDER BY s.created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (start_date, end_date, limit, offset)
                )
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
        except Exception:
            return []

    def get_timeline_for_story(self, story_id: str) -> List[Dict[str, Any]]:
        """
        Get the full timeline for a story.
        
        Args:
            story_id: ID of the story
            
        Returns:
            List of timeline entries ordered by narrative_order
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT * FROM timeline_entries 
                    WHERE story_id = ? 
                    ORDER BY narrative_order ASC
                    """,
                    (story_id,)
                )
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
        except Exception:
            return []

    def add_tag_to_story(self, story_id: str, tag: str) -> bool:
        """
        Add a tag to a story.
        
        Args:
            story_id: ID of the story
            tag: Tag to add
            
        Returns:
            True if successful, False otherwise
        """
        tag_id = str(uuid.uuid4())
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO story_tags 
                    (id, story_id, tag)
                    VALUES (?, ?, ?)
                    """,
                    (tag_id, story_id, tag)
                )
                return True
        except Exception:
            return False

    def get_tags_for_story(self, story_id: str) -> List[str]:
        """
        Get all tags for a story.
        
        Args:
            story_id: ID of the story
            
        Returns:
            List of tags associated with the story
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT tag FROM story_tags WHERE story_id = ?",
                    (story_id,)
                )
                rows = cursor.fetchall()
                
                return [row[0] for row in rows]
        except Exception:
            return []

    def get_stories_by_tag(self, 
                          tag: str, 
                          limit: int = 50, 
                          offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get stories with a specific tag.
        
        Args:
            tag: Tag to search for
            limit: Maximum number of stories to return
            offset: Number of stories to skip
            
        Returns:
            List of stories with the specified tag
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT DISTINCT s.* FROM stories s
                    JOIN story_tags st ON s.id = st.story_id
                    WHERE st.tag = ?
                    ORDER BY s.created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (tag, limit, offset)
                )
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
        except Exception:
            return []

    def publish_story(self, story_id: str, is_published: bool = True) -> bool:
        """
        Set the publication status of a story.
        
        Args:
            story_id: ID of the story
            is_published: Whether to publish (True) or unpublish (False) the story
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    UPDATE stories 
                    SET is_published = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (is_published, story_id)
                )
                return cursor.rowcount > 0
        except Exception:
            return False

    def get_story_stats(self, owner_id: str) -> Dict[str, int]:
        """
        Get statistics about a user's stories.
        
        Args:
            owner_id: ID of the owner
            
        Returns:
            Dictionary with story statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Total stories
                total_stories = conn.execute(
                    "SELECT COUNT(*) FROM stories WHERE owner_id = ?",
                    (owner_id,)
                ).fetchone()[0]
                
                # Published stories
                published_stories = conn.execute(
                    "SELECT COUNT(*) FROM stories WHERE owner_id = ? AND is_published = 1",
                    (owner_id,)
                ).fetchone()[0]
                
                # Total photos across all stories
                total_photos = conn.execute(
                    """
                    SELECT COUNT(*) FROM timeline_entries te
                    JOIN stories s ON te.story_id = s.id
                    WHERE s.owner_id = ?
                    """,
                    (owner_id,)
                ).fetchone()[0]
                
                # Stories by date range (last 30 days)
                last_month_stories = conn.execute(
                    """
                    SELECT COUNT(*) FROM stories 
                    WHERE owner_id = ? AND created_at >= datetime('now', '-30 days')
                    """,
                    (owner_id,)
                ).fetchone()[0]
                
                return {
                    'total_stories': total_stories,
                    'published_stories': published_stories,
                    'total_photos_in_stories': total_photos,
                    'stories_last_30_days': last_month_stories
                }
        except Exception:
            return {
                'total_stories': 0,
                'published_stories': 0,
                'total_photos_in_stories': 0,
                'stories_last_30_days': 0
            }


def get_timeline_db(db_path: Path) -> TimelineDB:
    """Get timeline database instance."""
    return TimelineDB(db_path)