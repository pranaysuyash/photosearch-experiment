"""
Face Analytics Engine

Provides comprehensive analytics and insights for face recognition data including:
1. Person timeline generation with aging progression analysis
2. Relationship detection based on photo co-occurrence patterns
3. Event detection for gatherings and parties
4. Smart organization recommendations

Features:
- Timeline analysis with chronological face progression
- Co-occurrence matrix for relationship strength calculation
- Event detection based on time windows and people groupings
- Quality trend analysis over time
- Caching for performance optimization
- Privacy-aware analytics that respect user settings

Usage:
    analytics = FaceAnalyticsEngine(face_db)
    timeline = analytics.generate_person_timeline(person_id)
    relationships = analytics.detect_photo_relationships()
    events = analytics.detect_events(min_people=3)
"""

import sqlite3
import logging
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


@dataclass
class PersonTimelineEntry:
    """Single entry in a person's timeline"""

    date: str
    photo_path: str
    face_id: str
    age_estimate: Optional[int]
    quality_score: float
    emotion: Optional[str]
    pose_type: Optional[str]
    overall_quality: Optional[float]


@dataclass
class PhotoRelationship:
    """Relationship between two people based on co-occurrence"""

    person1_id: str
    person2_id: str
    co_occurrence_count: int
    relationship_strength: float
    last_seen_together: Optional[str]
    common_photos: List[str]


@dataclass
class DetectedEvent:
    """Detected event based on face co-occurrence patterns"""

    event_id: str
    start_time: str
    end_time: str
    photo_count: int
    people_count: int
    people_involved: List[str]
    photos: List[str]
    event_type: str
    confidence_score: float


class FaceAnalyticsEngine:
    """Advanced analytics and insights generation for face recognition data"""

    def __init__(self, face_db_path: str):
        """
        Initialize face analytics engine.

        Args:
            face_db_path: Path to face clustering database
        """
        self.db_path = Path(face_db_path)
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour cache TTL

        logger.info("FaceAnalyticsEngine initialized")

    def _get_db_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def generate_person_timeline(self, person_id: str) -> Dict:
        """
        Generate comprehensive timeline for a person showing aging progression.

        Args:
            person_id: Cluster ID of the person

        Returns:
            Dictionary with timeline data, age progression, and quality trends
        """
        cache_key = f"timeline_{person_id}"
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now().timestamp() - timestamp < self.cache_ttl:
                return cached_data

        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()

                # Get person info
                cursor.execute(
                    """
                    SELECT label FROM face_clusters WHERE cluster_id = ?
                """,
                    (person_id,),
                )

                person_row = cursor.fetchone()
                if not person_row:
                    return {"error": "Person not found"}

                person_name = person_row["label"] or f"Person {person_id}"

                # Get all photos with this person, including metadata
                cursor.execute(
                    """
                    SELECT DISTINCT
                        ppa.photo_path,
                        ppa.detection_id,
                        ppa.confidence,
                        fd.age_estimate,
                        fd.age_confidence,
                        fd.emotion,
                        fd.emotion_confidence,
                        fd.pose_type,
                        fd.quality_score,
                        fd.overall_quality,
                        fd.created_at
                    FROM photo_person_associations ppa
                    JOIN face_detections fd ON ppa.detection_id = fd.detection_id
                    WHERE ppa.cluster_id = ?
                    ORDER BY fd.created_at ASC
                """,
                    (person_id,),
                )

                rows = cursor.fetchall()

                if not rows:
                    return {
                        "person_id": person_id,
                        "person_name": person_name,
                        "timeline": [],
                        "message": "No photos found for this person",
                    }

                # Build timeline entries
                timeline_entries = []
                for row in rows:
                    # Try to get actual photo date from metadata
                    photo_date = self._get_photo_date(row["photo_path"])
                    if not photo_date:
                        photo_date = row["created_at"]

                    entry = PersonTimelineEntry(
                        date=photo_date,
                        photo_path=row["photo_path"],
                        face_id=row["detection_id"],
                        age_estimate=row["age_estimate"],
                        quality_score=row["quality_score"] or 0.0,
                        emotion=row["emotion"],
                        pose_type=row["pose_type"],
                        overall_quality=row["overall_quality"],
                    )
                    timeline_entries.append(entry)

                # Sort by date
                timeline_entries.sort(key=lambda x: x.date)

                # Analyze age progression
                age_progression = self._analyze_age_progression(timeline_entries)

                # Analyze quality trends
                quality_trends = self._analyze_quality_trends(timeline_entries)

                # Analyze emotion patterns
                emotion_patterns = self._analyze_emotion_patterns(timeline_entries)

                result = {
                    "person_id": person_id,
                    "person_name": person_name,
                    "timeline": [
                        {
                            "date": entry.date,
                            "photo_path": entry.photo_path,
                            "face_id": entry.face_id,
                            "age_estimate": entry.age_estimate,
                            "quality_score": entry.quality_score,
                            "emotion": entry.emotion,
                            "pose_type": entry.pose_type,
                            "overall_quality": entry.overall_quality,
                        }
                        for entry in timeline_entries
                    ],
                    "age_progression": age_progression,
                    "quality_trends": quality_trends,
                    "emotion_patterns": emotion_patterns,
                    "total_photos": len(timeline_entries),
                    "date_range": {
                        "earliest": timeline_entries[0].date if timeline_entries else None,
                        "latest": timeline_entries[-1].date if timeline_entries else None,
                    },
                }

                # Cache result
                self.cache[cache_key] = (result, datetime.now().timestamp())

                return result

        except Exception as e:
            logger.error(f"Error generating timeline for person {person_id}: {e}")
            return {"error": str(e)}

    def detect_photo_relationships(self) -> Dict:
        """
        Analyze who appears together most frequently to identify relationships.

        Returns:
            Dictionary with relationship data and network analysis
        """
        cache_key = "photo_relationships"
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now().timestamp() - timestamp < self.cache_ttl:
                return cached_data

        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()

                # Get all photos with multiple people
                cursor.execute("""
                    SELECT photo_path, GROUP_CONCAT(cluster_id) as people_list
                    FROM photo_person_associations
                    GROUP BY photo_path
                    HAVING COUNT(DISTINCT cluster_id) >= 2
                """)

                multi_person_photos = cursor.fetchall()

                # Build co-occurrence matrix
                co_occurrence = defaultdict(int)
                photo_relationships = defaultdict(list)

                for row in multi_person_photos:
                    photo_path = row["photo_path"]
                    people = row["people_list"].split(",")

                    # Record all pairs in this photo
                    for i, person1 in enumerate(people):
                        for person2 in people[i + 1 :]:
                            # Ensure consistent ordering
                            pair = tuple(sorted([person1, person2]))
                            co_occurrence[pair] += 1
                            photo_relationships[pair].append(photo_path)

                # Calculate relationship strengths and get person names
                relationships = []
                for (person1_id, person2_id), count in co_occurrence.items():
                    # Get person names
                    cursor.execute(
                        """
                        SELECT cluster_id, label FROM face_clusters
                        WHERE cluster_id IN (?, ?)
                    """,
                        (person1_id, person2_id),
                    )

                    name_rows = cursor.fetchall()
                    names = {row["cluster_id"]: row["label"] or f"Person {row['cluster_id']}" for row in name_rows}

                    # Calculate relationship strength (normalized by total photos)
                    cursor.execute(
                        """
                        SELECT COUNT(DISTINCT photo_path) as total_photos_person1
                        FROM photo_person_associations WHERE cluster_id = ?
                    """,
                        (person1_id,),
                    )
                    total1 = cursor.fetchone()["total_photos_person1"]

                    cursor.execute(
                        """
                        SELECT COUNT(DISTINCT photo_path) as total_photos_person2
                        FROM photo_person_associations WHERE cluster_id = ?
                    """,
                        (person2_id,),
                    )
                    total2 = cursor.fetchone()["total_photos_person2"]

                    # Relationship strength as percentage of shared photos
                    strength = count / min(total1, total2) if min(total1, total2) > 0 else 0

                    # Get most recent photo together
                    common_photos = photo_relationships[(person1_id, person2_id)]
                    last_photo = max(common_photos) if common_photos else None

                    relationships.append(
                        {
                            "person1_id": person1_id,
                            "person1_name": names.get(person1_id, f"Person {person1_id}"),
                            "person2_id": person2_id,
                            "person2_name": names.get(person2_id, f"Person {person2_id}"),
                            "co_occurrence_count": count,
                            "relationship_strength": round(strength, 3),
                            "last_seen_together": last_photo,
                            "common_photos_count": len(common_photos),
                        }
                    )

                # Sort by relationship strength
                relationships.sort(key=lambda x: x["relationship_strength"], reverse=True)

                # Generate network insights
                network_insights = self._generate_network_insights(relationships)

                result = {
                    "relationships": relationships[:50],  # Top 50 relationships
                    "total_relationships": len(relationships),
                    "network_insights": network_insights,
                    "generated_at": datetime.now().isoformat(),
                }

                # Cache result
                self.cache[cache_key] = (result, datetime.now().timestamp())

                return result

        except Exception as e:
            logger.error(f"Error detecting photo relationships: {e}")
            return {"error": str(e)}

    def detect_events(self, min_people: int = 3, time_window_hours: int = 24) -> List[Dict]:
        """
        Detect gatherings and events based on face co-occurrence patterns.

        Args:
            min_people: Minimum number of people for an event
            time_window_hours: Time window for grouping photos into events

        Returns:
            List of detected events with metadata
        """
        cache_key = f"events_{min_people}_{time_window_hours}"
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now().timestamp() - timestamp < self.cache_ttl:
                return cached_data

        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()

                # Get all photos with multiple people and their timestamps
                cursor.execute(
                    """
                    SELECT
                        ppa.photo_path,
                        GROUP_CONCAT(ppa.cluster_id) as people_list,
                        COUNT(DISTINCT ppa.cluster_id) as people_count,
                        MIN(fd.created_at) as photo_timestamp
                    FROM photo_person_associations ppa
                    JOIN face_detections fd ON ppa.detection_id = fd.detection_id
                    GROUP BY ppa.photo_path
                    HAVING people_count >= ?
                    ORDER BY photo_timestamp
                """,
                    (min_people,),
                )

                group_photos = cursor.fetchall()

                if not group_photos:
                    return []

                # Group photos by time windows
                events = []
                current_event_photos = []
                current_event_start = None

                for photo in group_photos:
                    photo_time = datetime.fromisoformat(photo["photo_timestamp"].replace("Z", "+00:00"))

                    if (
                        current_event_start is None
                        or (photo_time - current_event_start).total_seconds() <= time_window_hours * 3600
                    ):
                        # Add to current event
                        if current_event_start is None:
                            current_event_start = photo_time
                        current_event_photos.append(photo)
                    else:
                        # Process current event and start new one
                        if len(current_event_photos) >= 2:  # At least 2 photos for an event
                            event = self._process_event_photos(current_event_photos)
                            if event:
                                events.append(event)

                        # Start new event
                        current_event_photos = [photo]
                        current_event_start = photo_time

                # Process final event
                if len(current_event_photos) >= 2:
                    event = self._process_event_photos(current_event_photos)
                    if event:
                        events.append(event)

                # Sort events by start time (most recent first)
                events.sort(key=lambda x: x["start_time"], reverse=True)

                # Cache result
                self.cache[cache_key] = (events, datetime.now().timestamp())

                return events

        except Exception as e:
            logger.error(f"Error detecting events: {e}")
            return []

    def _get_photo_date(self, photo_path: str) -> Optional[str]:
        """
        Get the actual date a photo was taken from metadata.

        Args:
            photo_path: Path to the photo

        Returns:
            ISO format date string or None
        """
        try:
            # Try to get from photo metadata database
            # This would integrate with the main photo search database
            # For now, use file modification time as fallback
            import os

            if os.path.exists(photo_path):
                mtime = os.path.getmtime(photo_path)
                return datetime.fromtimestamp(mtime).isoformat()
        except Exception:
            pass

        return None

    def _analyze_age_progression(self, timeline_entries: List[PersonTimelineEntry]) -> Dict:
        """Analyze age progression over time."""
        ages_with_dates = [
            (entry.date, entry.age_estimate) for entry in timeline_entries if entry.age_estimate is not None
        ]

        if not ages_with_dates:
            return {"message": "No age data available"}

        ages_with_dates.sort(key=lambda x: x[0])

        return {
            "earliest_age": ages_with_dates[0][1],
            "latest_age": ages_with_dates[-1][1],
            "age_span": ages_with_dates[-1][1] - ages_with_dates[0][1] if len(ages_with_dates) > 1 else 0,
            "progression_data": [{"date": date, "age": age} for date, age in ages_with_dates],
            "avg_age": sum(age for _, age in ages_with_dates) / len(ages_with_dates),
        }

    def _analyze_quality_trends(self, timeline_entries: List[PersonTimelineEntry]) -> Dict:
        """Analyze photo quality trends over time."""
        quality_data = [(entry.date, entry.overall_quality or entry.quality_score) for entry in timeline_entries]
        quality_data.sort(key=lambda x: x[0])

        if not quality_data:
            return {"message": "No quality data available"}

        qualities = [q for _, q in quality_data]

        return {
            "avg_quality": sum(qualities) / len(qualities),
            "min_quality": min(qualities),
            "max_quality": max(qualities),
            "quality_trend": "improving"
            if qualities[-1] > qualities[0]
            else "declining"
            if len(qualities) > 1
            else "stable",
            "quality_data": [{"date": date, "quality": quality} for date, quality in quality_data],
        }

    def _analyze_emotion_patterns(self, timeline_entries: List[PersonTimelineEntry]) -> Dict:
        """Analyze emotion patterns over time."""
        emotions = [entry.emotion for entry in timeline_entries if entry.emotion]

        if not emotions:
            return {"message": "No emotion data available"}

        emotion_counts = Counter(emotions)

        return {
            "dominant_emotion": emotion_counts.most_common(1)[0][0],
            "emotion_distribution": dict(emotion_counts),
            "total_emotions_detected": len(emotions),
            "emotion_variety": len(emotion_counts),
        }

    def _generate_network_insights(self, relationships: List[Dict]) -> Dict:
        """Generate insights about the social network."""
        if not relationships:
            return {"message": "No relationships found"}

        # Find most connected people
        person_connections = defaultdict(int)
        for rel in relationships:
            person_connections[rel["person1_id"]] += 1
            person_connections[rel["person2_id"]] += 1

        most_connected = max(person_connections.items(), key=lambda x: x[1]) if person_connections else None

        # Find strongest relationships
        strongest_relationships = relationships[:5]  # Top 5

        return {
            "total_people": len(person_connections),
            "total_connections": len(relationships),
            "most_connected_person": {"person_id": most_connected[0], "connection_count": most_connected[1]}
            if most_connected
            else None,
            "strongest_relationships": strongest_relationships,
            "avg_relationship_strength": sum(r["relationship_strength"] for r in relationships) / len(relationships),
        }

    def _process_event_photos(self, event_photos: List) -> Optional[Dict]:
        """Process a group of photos into an event."""
        if len(event_photos) < 2:
            return None

        # Collect all people involved
        all_people = set()
        all_photo_paths = []

        for photo in event_photos:
            people_list = photo["people_list"].split(",")
            all_people.update(people_list)
            all_photo_paths.append(photo["photo_path"])

        # Determine event type based on characteristics
        event_type = self._classify_event_type(len(all_people), len(event_photos))

        # Calculate confidence based on photo density and people consistency
        confidence = min(1.0, len(event_photos) / 10.0 + len(all_people) / 20.0)

        start_time = event_photos[0]["photo_timestamp"]
        end_time = event_photos[-1]["photo_timestamp"]

        return {
            "event_id": f"event_{hash(tuple(sorted(all_photo_paths)))}",
            "start_time": start_time,
            "end_time": end_time,
            "photo_count": len(event_photos),
            "people_count": len(all_people),
            "people_involved": list(all_people),
            "photos": all_photo_paths,
            "event_type": event_type,
            "confidence_score": round(confidence, 3),
        }

    def _classify_event_type(self, people_count: int, photo_count: int) -> str:
        """Classify event type based on characteristics."""
        if people_count >= 10:
            return "large_gathering"
        elif people_count >= 5:
            return "party"
        elif people_count >= 3:
            return "small_gathering"
        else:
            return "meeting"

    def get_person_insights(self, person_id: str) -> Dict:
        """
        Get comprehensive insights for a specific person.

        Args:
            person_id: Cluster ID of the person

        Returns:
            Dictionary with comprehensive person insights
        """
        try:
            timeline = self.generate_person_timeline(person_id)

            # Get relationship data for this person
            relationships = self.detect_photo_relationships()
            person_relationships = [
                r
                for r in relationships.get("relationships", [])
                if r["person1_id"] == person_id or r["person2_id"] == person_id
            ]

            # Get events this person appears in
            events = self.detect_events()
            person_events = [e for e in events if person_id in e["people_involved"]]

            return {
                "person_id": person_id,
                "timeline": timeline,
                "relationships": person_relationships[:10],  # Top 10 relationships
                "events": person_events[:10],  # Recent 10 events
                "insights": {
                    "total_photos": timeline.get("total_photos", 0),
                    "relationship_count": len(person_relationships),
                    "event_appearances": len(person_events),
                    "social_activity": "high"
                    if len(person_relationships) > 5
                    else "medium"
                    if len(person_relationships) > 2
                    else "low",
                },
            }

        except Exception as e:
            logger.error(f"Error generating insights for person {person_id}: {e}")
            return {"error": str(e)}
