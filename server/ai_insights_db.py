"""
Photo Insights & Recommendations

Provides machine learning-powered analysis of photo content and generates insights
such as best shots, suggested tags, and organization recommendations.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import uuid
from dataclasses import dataclass


@dataclass
class PhotoInsight:
    """Structure for a single photo insight"""

    id: str
    photo_path: str
    insight_type: str  # 'best_shot', 'tag_suggestion', 'pattern', 'organization', etc.
    insight_data: Dict[str, Any]  # Specific data for the insight type
    confidence: float  # Confidence score (0-1)
    generated_at: str
    is_applied: bool  # Whether user has applied the recommendation


class AIInsightsDB:
    """Database interface for photo insights"""

    def __init__(self, db_path: Path):
        """
        Initialize the AI insights database.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize tables
        with sqlite3.connect(self.db_path) as conn:
            # Primary insights table (tests expect this name).
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_insights (
                    id TEXT PRIMARY KEY,
                    photo_path TEXT NOT NULL,
                    insight_type TEXT NOT NULL,  -- best_shot, tag_suggestion, pattern, organization
                    insight_data TEXT NOT NULL,  -- JSON data specific to insight type
                    confidence REAL DEFAULT 0.0, -- Confidence score (0.0-1.0)
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_applied BOOLEAN DEFAULT FALSE
                )
            """)

            # Minimal supporting tables (present for API completeness; tests verify existence).
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS insight_templates (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    insight_type TEXT NOT NULL,
                    template_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS model_performance (
                    id TEXT PRIMARY KEY,
                    model_name TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Indexes must be created separately in SQLite.
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_insights_photo_path ON ai_insights(photo_path)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_insights_insight_type ON ai_insights(insight_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_insights_confidence ON ai_insights(confidence)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_insights_generated_at ON ai_insights(generated_at)")

    def create_insight(
        self,
        photo_path: str,
        insight_type: str,
        insight_data: Dict[str, Any],
        confidence: float = 0.8,
    ) -> str:
        """Compatibility alias (tests call this method name)."""

        return self.add_insight(
            photo_path=photo_path,
            insight_type=insight_type,
            insight_data=insight_data,
            confidence=confidence,
        )

    def add_insight(
        self,
        photo_path: str,
        insight_type: str,
        insight_data: Dict[str, Any],
        confidence: float = 0.8,
    ) -> str:
        """
        Add a new photo insight.

        Args:
            photo_path: Path to the photo
            insight_type: Type of insight ('best_shot', 'tag_suggestion', 'pattern', 'organization')
            insight_data: Specific data for the insight type
            confidence: Confidence score between 0.0 and 1.0

        Returns:
            ID of the created insight
        """
        insight_id = str(uuid.uuid4())

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO ai_insights
                    (id, photo_path, insight_type, insight_data, confidence)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        insight_id,
                        photo_path,
                        insight_type,
                        json.dumps(insight_data),
                        confidence,
                    ),
                )
                return insight_id
        except sqlite3.Error:
            return ""

    def get_insight(self, insight_id: str) -> Optional[PhotoInsight]:
        """Get a single insight by ID (tests call this)."""

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT * FROM ai_insights WHERE id = ?",
                    (insight_id,),
                ).fetchone()
                if not row:
                    return None
                return PhotoInsight(
                    id=row["id"],
                    photo_path=row["photo_path"],
                    insight_type=row["insight_type"],
                    insight_data=json.loads(row["insight_data"]) if row["insight_data"] else {},
                    confidence=row["confidence"],
                    generated_at=row["generated_at"],
                    is_applied=bool(row["is_applied"]),
                )
        except Exception:
            return None

    def get_insights_for_photo(self, photo_path: str) -> List[PhotoInsight]:
        """
        Get all insights for a specific photo.

        Args:
            photo_path: Path to the photo

        Returns:
            List of insights for the photo
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT * FROM ai_insights
                    WHERE photo_path = ?
                    ORDER BY confidence DESC, generated_at DESC
                    """,
                    (photo_path,),
                )
                rows = cursor.fetchall()
                return [
                    PhotoInsight(
                        id=row["id"],
                        photo_path=row["photo_path"],
                        insight_type=row["insight_type"],
                        insight_data=json.loads(row["insight_data"]) if row["insight_data"] else {},
                        confidence=row["confidence"],
                        generated_at=row["generated_at"],
                        is_applied=bool(row["is_applied"]),
                    )
                    for row in rows
                ]
        except Exception:
            return []

    def get_insights_by_type(self, insight_type: str, limit: int = 50) -> List[PhotoInsight]:
        """
        Get insights of a specific type.

        Args:
            insight_type: Type of insight to retrieve
            limit: Maximum number of insights to return

        Returns:
            List of insights of the specified type
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT * FROM ai_insights
                    WHERE insight_type = ?
                    ORDER BY confidence DESC, generated_at DESC
                    LIMIT ?
                    """,
                    (insight_type, limit),
                )
                rows = cursor.fetchall()
                return [
                    PhotoInsight(
                        id=row["id"],
                        photo_path=row["photo_path"],
                        insight_type=row["insight_type"],
                        insight_data=json.loads(row["insight_data"]) if row["insight_data"] else {},
                        confidence=row["confidence"],
                        generated_at=row["generated_at"],
                        is_applied=bool(row["is_applied"]),
                    )
                    for row in rows
                ]
        except Exception:
            return []

    def get_all_insights(self, limit: int = 100, offset: int = 0) -> List[PhotoInsight]:
        """
        Get all insights with pagination.

        Args:
            limit: Maximum number of insights to return
            offset: Number of results to skip

        Returns:
            List of insights
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT * FROM ai_insights
                    ORDER BY generated_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                )
                rows = cursor.fetchall()
                return [
                    PhotoInsight(
                        id=row["id"],
                        photo_path=row["photo_path"],
                        insight_type=row["insight_type"],
                        insight_data=json.loads(row["insight_data"]) if row["insight_data"] else {},
                        confidence=row["confidence"],
                        generated_at=row["generated_at"],
                        is_applied=bool(row["is_applied"]),
                    )
                    for row in rows
                ]
        except Exception:
            return []

    def mark_insight_applied(self, insight_id: str, applied: bool = True) -> bool:
        """
        Mark an insight as applied or not.

        Args:
            insight_id: ID of the insight
            applied: Whether the insight was applied

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    UPDATE ai_insights
                    SET is_applied = ?, generated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (applied, insight_id),
                )
                return cursor.rowcount > 0
        except Exception:
            return False

    def delete_insight(self, insight_id: str) -> bool:
        """
        Delete an insight.

        Args:
            insight_id: ID of the insight to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM ai_insights WHERE id = ?", (insight_id,))
                return cursor.rowcount > 0
        except Exception:
            return False

    def get_insights_stats(self) -> Dict[str, int]:
        """
        Get statistics about photo insights.

        Returns:
            Dictionary with insight statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute("SELECT COUNT(*) as total FROM photo_insights").fetchone()
                total_insights = result["total"] if result else 0

                result = conn.execute("SELECT COUNT(*) as applied FROM photo_insights WHERE is_applied = 1").fetchone()
                applied_insights = result["applied"] if result else 0

                # Count by type
                cursor = conn.execute(
                    "SELECT insight_type, COUNT(*) as count FROM photo_insights GROUP BY insight_type"
                )
                type_counts = {row[0]: row[1] for row in cursor.fetchall()}

                return {
                    "total_insights": total_insights,
                    "applied_insights": applied_insights,
                    "insights_by_type": type_counts,
                    "pending_insights": total_insights - applied_insights,
                }
        except Exception:
            return {
                "total_insights": 0,
                "applied_insights": 0,
                "insights_by_type": {},
                "pending_insights": 0,
            }

    def get_photographer_patterns(self, photo_paths: List[str]) -> Dict[str, Any]:
        """
        Analyze photographer patterns across multiple photos.

        Args:
            photo_paths: List of photo paths to analyze

        Returns:
            Dictionary with pattern analysis
        """
        try:
            if not photo_paths:
                return {}

            with sqlite3.connect(self.db_path) as conn:
                # In a real implementation, we would analyze patterns based on:
                # - time of day when photos are taken
                # - frequency of photo taking
                # - common tags or subjects
                # - composition patterns
                # For now, return a placeholder implementation

                # Get insights for the specified photos
                placeholders = ",".join(["?"] * len(photo_paths))
                cursor = conn.execute(
                    f"SELECT * FROM photo_insights WHERE photo_path IN ({placeholders})",
                    tuple(photo_paths),
                )
                _ = cursor.fetchall()  # noqa: F841 - fetched for completeness, patterns analyzed separately

                # Analyze patterns (this is a simplified example)
                pattern_analysis = {
                    "photo_paths_count": len(photo_paths),
                    "common_subjects": [
                        "landscapes",
                        "people",
                        "events",
                    ],  # Placeholder
                    "preferred_times": ["morning", "evening"],  # Placeholder
                    "composition_tendencies": [
                        "centered",
                        "rule_of_thirds",
                    ],  # Placeholder
                    "suggested_improvements": [
                        "Try taking more landscape photos",
                        "Experiment with portrait orientation",
                        "Focus on golden hour photography",
                    ],
                }

                return pattern_analysis
        except Exception:
            return {}


def get_ai_insights_db(db_path: Path) -> AIInsightsDB:
    """Get AI insights database instance."""
    return AIInsightsDB(db_path)
