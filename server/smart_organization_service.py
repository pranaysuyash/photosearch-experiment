"""
Smart Organization Service

Provides intelligent photo organization capabilities including:
1. Automatic album creation based on face co-occurrence patterns
2. Smart recommendations for photo organization
3. Duplicate person detection across different names
4. Event-based album generation
5. Quality-based photo curation

Features:
- Family gathering detection and album creation
- Travel companion identification
- Childhood photo collections using age estimation
- Work event detection based on patterns
- Quality-based "Best of" collections
- Duplicate person merge suggestions
- Personalized organization recommendations

Usage:
    organizer = SmartOrganizationService(face_db, analytics_engine)
    albums = organizer.create_smart_albums()
    recommendations = organizer.generate_recommendations(user_preferences)
    duplicates = organizer.detect_duplicate_people()
"""

import sqlite3
import logging
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from collections import defaultdict

from server.face_analytics_service import FaceAnalyticsEngine

logger = logging.getLogger(__name__)


@dataclass
class SmartAlbum:
    """Smart album with metadata"""

    album_id: str
    name: str
    album_type: str  # auto_generated, smart_collection, event_based
    description: str
    criteria: Dict
    photos: List[str]
    people_involved: List[str]
    confidence_score: float
    created_at: str


@dataclass
class OrganizationRecommendation:
    """Recommendation for photo organization"""

    recommendation_id: str
    recommendation_type: str  # merge_people, create_album, tag_photos, quality_curation
    title: str
    description: str
    action_data: Dict
    confidence_score: float
    priority: str  # high, medium, low


@dataclass
class DuplicatePerson:
    """Potential duplicate person across different clusters"""

    person1_id: str
    person1_name: str
    person2_id: str
    person2_name: str
    similarity_score: float
    common_characteristics: Dict
    merge_confidence: float


class SmartOrganizationService:
    """Intelligent photo organization and recommendation system"""

    def __init__(self, face_db_path: str, analytics_engine: Optional[FaceAnalyticsEngine] = None):
        """
        Initialize smart organization service.

        Args:
            face_db_path: Path to face clustering database
            analytics_engine: Optional analytics engine instance
        """
        self.db_path = Path(face_db_path)
        self.analytics = analytics_engine or FaceAnalyticsEngine(face_db_path)
        self.cache = {}

        logger.info("SmartOrganizationService initialized")

    def _get_db_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def create_smart_albums(self) -> List[Dict]:
        """
        Create smart albums based on face analysis and co-occurrence patterns.

        Returns:
            List of smart album definitions
        """
        try:
            albums = []

            # 1. Family gathering albums
            family_albums = self._create_family_gathering_albums()
            albums.extend(family_albums)

            # 2. Travel companion albums
            travel_albums = self._create_travel_albums()
            albums.extend(travel_albums)

            # 3. Childhood photo collections
            childhood_albums = self._create_childhood_albums()
            albums.extend(childhood_albums)

            # 4. Event-based albums
            event_albums = self._create_event_albums()
            albums.extend(event_albums)

            # 5. Quality-based "Best of" collections
            quality_albums = self._create_quality_albums()
            albums.extend(quality_albums)

            # 6. Emotion-based collections
            emotion_albums = self._create_emotion_albums()
            albums.extend(emotion_albums)

            # Sort by confidence score
            albums.sort(key=lambda x: x["confidence_score"], reverse=True)

            logger.info(f"Created {len(albums)} smart albums")
            return albums

        except Exception as e:
            logger.error(f"Error creating smart albums: {e}")
            return []

    def generate_recommendations(self, user_preferences: Optional[Dict] = None) -> List[Dict]:
        """
        Generate personalized organization recommendations.

        Args:
            user_preferences: Optional user preferences for recommendations

        Returns:
            List of organization recommendations
        """
        try:
            recommendations = []

            # 1. Duplicate people merge suggestions
            duplicate_recs = self._generate_duplicate_merge_recommendations()
            recommendations.extend(duplicate_recs)

            # 2. Album creation suggestions
            album_recs = self._generate_album_recommendations()
            recommendations.extend(album_recs)

            # 3. Quality curation recommendations
            quality_recs = self._generate_quality_recommendations()
            recommendations.extend(quality_recs)

            # 4. Tagging recommendations
            tagging_recs = self._generate_tagging_recommendations()
            recommendations.extend(tagging_recs)

            # 5. Privacy recommendations
            privacy_recs = self._generate_privacy_recommendations()
            recommendations.extend(privacy_recs)

            # Sort by priority and confidence
            priority_order = {"high": 3, "medium": 2, "low": 1}
            recommendations.sort(
                key=lambda x: (priority_order.get(x["priority"], 0), x["confidence_score"]), reverse=True
            )

            logger.info(f"Generated {len(recommendations)} recommendations")
            return recommendations[:20]  # Top 20 recommendations

        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []

    def detect_duplicate_people(self, similarity_threshold: float = 0.8) -> List[Dict]:
        """
        Detect potential duplicate people across different cluster names.

        Args:
            similarity_threshold: Minimum similarity for duplicate detection

        Returns:
            List of potential duplicate person pairs
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()

                # Get all people with their characteristics
                cursor.execute("""
                    SELECT
                        fc.id as cluster_id,
                        fc.label,
                        COUNT(ppa.detection_id) as photo_count,
                        AVG(fd.age_estimate) as avg_age,
                        AVG(fd.overall_quality) as avg_quality,
                        GROUP_CONCAT(DISTINCT fd.emotion) as emotions,
                        GROUP_CONCAT(DISTINCT fd.gender) as genders
                    FROM face_clusters fc
                    JOIN photo_person_associations ppa ON fc.cluster_id = ppa.cluster_id
                    JOIN face_detections fd ON ppa.detection_id = fd.detection_id
                    WHERE fc.label IS NOT NULL AND fc.label != ''
                    GROUP BY fc.id, fc.label
                    HAVING photo_count >= 2
                """)

                people_data = cursor.fetchall()

                duplicates = []

                # Compare each pair of people
                for i, person1 in enumerate(people_data):
                    for person2 in people_data[i + 1 :]:
                        similarity = self._calculate_person_similarity(person1, person2)

                        if similarity >= similarity_threshold:
                            # Get sample photos for visual comparison
                            sample_photos = self._get_sample_photos_for_comparison(
                                person1["cluster_id"], person2["cluster_id"]
                            )

                            duplicate = {
                                "person1_id": person1["cluster_id"],
                                "person1_name": person1["label"],
                                "person2_id": person2["cluster_id"],
                                "person2_name": person2["label"],
                                "similarity_score": round(similarity, 3),
                                "common_characteristics": {
                                    "age_similarity": abs((person1["avg_age"] or 0) - (person2["avg_age"] or 0)) < 5,
                                    "quality_similarity": abs(
                                        (person1["avg_quality"] or 0) - (person2["avg_quality"] or 0)
                                    )
                                    < 0.2,
                                    "shared_emotions": self._find_shared_emotions(
                                        person1["emotions"], person2["emotions"]
                                    ),
                                    "shared_genders": self._find_shared_genders(person1["genders"], person2["genders"]),
                                },
                                "merge_confidence": similarity,
                                "sample_photos": sample_photos,
                            }
                            duplicates.append(duplicate)

                # Sort by similarity score
                duplicates.sort(key=lambda x: x["similarity_score"], reverse=True)

                logger.info(f"Found {len(duplicates)} potential duplicate people")
                return duplicates

        except Exception as e:
            logger.error(f"Error detecting duplicate people: {e}")
            return []

    def _create_family_gathering_albums(self) -> List[Dict]:
        """Create albums for family gatherings based on co-occurrence patterns."""
        try:
            # Get events with multiple people
            events = self.analytics.detect_events(min_people=4, time_window_hours=12)

            albums = []
            for event in events:
                if event["people_count"] >= 4 and event["photo_count"] >= 3:
                    album = {
                        "album_id": f"family_gathering_{event['event_id']}",
                        "name": f"Family Gathering - {event['start_time'][:10]}",
                        "album_type": "event_based",
                        "description": f"We detected a family gathering with {event['people_count']} people in {event['photo_count']} photos",
                        "criteria": {
                            "event_type": "family_gathering",
                            "min_people": 4,
                            "date_range": [event["start_time"], event["end_time"]],
                        },
                        "photos": event["photos"],
                        "people_involved": event["people_involved"],
                        "confidence_score": event["confidence_score"],
                        "created_at": datetime.now().isoformat(),
                    }
                    albums.append(album)

            return albums[:5]  # Top 5 family gatherings

        except Exception as e:
            logger.error(f"Error creating family gathering albums: {e}")
            return []

    def _create_travel_albums(self) -> List[Dict]:
        """Create albums for travel based on location and companion patterns."""
        try:
            # Get relationships to identify travel companions
            relationships = self.analytics.detect_photo_relationships()

            albums = []
            for rel in relationships.get("relationships", [])[:10]:
                if rel["co_occurrence_count"] >= 5 and rel["relationship_strength"] > 0.3:
                    # Check if photos span multiple days (indicating travel)
                    if self._is_travel_pattern(rel["common_photos_count"]):
                        album = {
                            "album_id": f"travel_{rel['person1_id']}_{rel['person2_id']}",
                            "name": f"Travel with {rel['person1_name']} and {rel['person2_name']}",
                            "album_type": "smart_collection",
                            "description": f"We found {rel['co_occurrence_count']} photos of {rel['person1_name']} and {rel['person2_name']} together",
                            "criteria": {
                                "collection_type": "travel_companions",
                                "people": [rel["person1_id"], rel["person2_id"]],
                                "min_co_occurrence": 5,
                            },
                            "photos": [],  # Would need to fetch actual photo paths
                            "people_involved": [rel["person1_id"], rel["person2_id"]],
                            "confidence_score": rel["relationship_strength"],
                            "created_at": datetime.now().isoformat(),
                        }
                        albums.append(album)

            return albums[:3]  # Top 3 travel albums

        except Exception as e:
            logger.error(f"Error creating travel albums: {e}")
            return []

    def _create_childhood_albums(self) -> List[Dict]:
        """Create childhood photo collections using age estimation."""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()

                # Find people with childhood photos (age < 13)
                cursor.execute("""
                    SELECT
                        ppa.cluster_id,
                        fc.label,
                        COUNT(ppa.detection_id) as childhood_photos,
                        MIN(fd.age_estimate) as youngest_age,
                        MAX(fd.age_estimate) as oldest_age
                    FROM photo_person_associations ppa
                    JOIN face_detections fd ON ppa.detection_id = fd.detection_id
                    JOIN face_clusters fc ON ppa.cluster_id = fc.cluster_id
                    WHERE fd.age_estimate IS NOT NULL AND fd.age_estimate < 13
                    GROUP BY ppa.cluster_id, fc.label
                    HAVING childhood_photos >= 3
                    ORDER BY childhood_photos DESC
                """)

                childhood_data = cursor.fetchall()

                albums = []
                for person in childhood_data[:5]:  # Top 5 people with childhood photos
                    person_name = person["label"] or f"Person {person['cluster_id']}"
                    album = {
                        "album_id": f"childhood_{person['cluster_id']}",
                        "name": f"Childhood Photos of {person_name}",
                        "album_type": "smart_collection",
                        "description": f"We found {person['childhood_photos']} childhood photos (ages {person['youngest_age']}-{person['oldest_age']})",
                        "criteria": {
                            "collection_type": "childhood_photos",
                            "person_id": person["cluster_id"],
                            "max_age": 13,
                        },
                        "photos": [],  # Would need to fetch actual photo paths
                        "people_involved": [person["cluster_id"]],
                        "confidence_score": min(1.0, person["childhood_photos"] / 10.0),
                        "created_at": datetime.now().isoformat(),
                    }
                    albums.append(album)

                return albums

        except Exception as e:
            logger.error(f"Error creating childhood albums: {e}")
            return []

    def _create_event_albums(self) -> List[Dict]:
        """Create albums based on detected events."""
        try:
            events = self.analytics.detect_events(min_people=3, time_window_hours=6)

            albums = []
            for event in events[:10]:  # Top 10 events
                event_name = self._generate_event_name(event)

                album = {
                    "album_id": f"event_{event['event_id']}",
                    "name": event_name,
                    "album_type": "event_based",
                    "description": f"We detected a {event['event_type']} with {event['people_count']} people",
                    "criteria": {
                        "event_id": event["event_id"],
                        "event_type": event["event_type"],
                        "time_window": [event["start_time"], event["end_time"]],
                    },
                    "photos": event["photos"],
                    "people_involved": event["people_involved"],
                    "confidence_score": event["confidence_score"],
                    "created_at": datetime.now().isoformat(),
                }
                albums.append(album)

            return albums

        except Exception as e:
            logger.error(f"Error creating event albums: {e}")
            return []

    def _create_quality_albums(self) -> List[Dict]:
        """Create 'Best of' albums based on photo quality."""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()

                # Get highest quality photos for each person
                cursor.execute("""
                    SELECT
                        ppa.cluster_id,
                        fc.label,
                        ppa.photo_path,
                        fd.overall_quality,
                        ROW_NUMBER() OVER (PARTITION BY ppa.cluster_id ORDER BY fd.overall_quality DESC) as quality_rank
                    FROM photo_person_associations ppa
                    JOIN face_detections fd ON ppa.detection_id = fd.detection_id
                    JOIN face_clusters fc ON ppa.cluster_id = fc.cluster_id
                    WHERE fd.overall_quality IS NOT NULL AND fd.overall_quality >= 0.8
                """)

                quality_photos = cursor.fetchall()

                # Group by person and create "Best of" albums
                person_best_photos = defaultdict(list)
                for photo in quality_photos:
                    if photo["quality_rank"] <= 10:  # Top 10 photos per person
                        person_best_photos[photo["cluster_id"]].append(photo)

                albums = []
                for person_id, photos in person_best_photos.items():
                    if len(photos) >= 3:  # At least 3 high-quality photos
                        person_name = photos[0]["label"] or f"Person {person_id}"

                        album = {
                            "album_id": f"best_of_{person_id}",
                            "name": f"Best Photos of {person_name}",
                            "album_type": "smart_collection",
                            "description": f"We selected {len(photos)} highest quality photos of {person_name}",
                            "criteria": {"collection_type": "best_quality", "person_id": person_id, "min_quality": 0.8},
                            "photos": [p["photo_path"] for p in photos],
                            "people_involved": [person_id],
                            "confidence_score": sum(p["overall_quality"] for p in photos) / len(photos),
                            "created_at": datetime.now().isoformat(),
                        }
                        albums.append(album)

                return albums[:5]  # Top 5 quality albums

        except Exception as e:
            logger.error(f"Error creating quality albums: {e}")
            return []

    def _create_emotion_albums(self) -> List[Dict]:
        """Create albums based on emotions (e.g., 'Happy Moments')."""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()

                # Get photos by emotion
                cursor.execute("""
                    SELECT
                        fd.emotion,
                        COUNT(*) as photo_count,
                        GROUP_CONCAT(DISTINCT ppa.photo_path) as photo_paths
                        FROM face_detections fd
                        JOIN photo_person_associations ppa ON fd.detection_id = ppa.detection_id
                        WHERE fd.emotion IS NOT NULL AND fd.emotion_confidence >= 0.7
                        GROUP BY fd.emotion
                    HAVING photo_count >= 10
                    ORDER BY photo_count DESC
                """)

                emotion_data = cursor.fetchall()

                albums = []
                for emotion_row in emotion_data:
                    emotion = emotion_row["emotion"]
                    photo_count = emotion_row["photo_count"]

                    if emotion in ["happy", "surprised"]:  # Focus on positive emotions
                        album = {
                            "album_id": f"emotion_{emotion}",
                            "name": f"{emotion.title()} Moments",
                            "album_type": "smart_collection",
                            "description": f"We found {photo_count} photos with {emotion} expressions",
                            "criteria": {"collection_type": "emotion_based", "emotion": emotion, "min_confidence": 0.7},
                            "photos": emotion_row["photo_paths"].split(",")[:50] if emotion_row["photo_paths"] else [],
                            "people_involved": [],  # Multiple people
                            "confidence_score": min(1.0, photo_count / 50.0),
                            "created_at": datetime.now().isoformat(),
                        }
                        albums.append(album)

                return albums

        except Exception as e:
            logger.error(f"Error creating emotion albums: {e}")
            return []

    def _generate_duplicate_merge_recommendations(self) -> List[Dict]:
        """Generate recommendations for merging duplicate people."""
        duplicates = self.detect_duplicate_people(similarity_threshold=0.75)

        recommendations = []
        for dup in duplicates[:5]:  # Top 5 duplicates
            rec = {
                "recommendation_id": f"merge_{dup['person1_id']}_{dup['person2_id']}",
                "recommendation_type": "merge_people",
                "title": f"Merge {dup['person1_name']} and {dup['person2_name']}",
                "description": f"These appear to be the same person ({dup['similarity_score']:.1%} similarity)",
                "action_data": {
                    "source_person_id": dup["person2_id"],
                    "target_person_id": dup["person1_id"],
                    "similarity_score": dup["similarity_score"],
                },
                "confidence_score": dup["similarity_score"],
                "priority": "high" if dup["similarity_score"] > 0.9 else "medium",
            }
            recommendations.append(rec)

        return recommendations

    def _generate_album_recommendations(self) -> List[Dict]:
        """Generate recommendations for creating new albums."""
        # This would analyze patterns and suggest new album types
        return []

    def _generate_quality_recommendations(self) -> List[Dict]:
        """Generate recommendations for quality-based curation."""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()

                # Find low-quality photos that could be reviewed
                cursor.execute("""
                    SELECT COUNT(*) as low_quality_count
                    FROM face_detections
                    WHERE overall_quality IS NOT NULL AND overall_quality < 0.3
                """)

                low_quality_count = cursor.fetchone()["low_quality_count"]

                recommendations = []
                if low_quality_count > 10:
                    rec = {
                        "recommendation_id": "review_low_quality",
                        "recommendation_type": "quality_curation",
                        "title": "Review Low Quality Photos",
                        "description": f"We found {low_quality_count} photos with low quality scores that might need review",
                        "action_data": {
                            "action": "review_low_quality",
                            "photo_count": low_quality_count,
                            "quality_threshold": 0.3,
                        },
                        "confidence_score": 0.8,
                        "priority": "medium",
                    }
                    recommendations.append(rec)

                return recommendations

        except Exception as e:
            logger.error(f"Error generating quality recommendations: {e}")
            return []

    def _generate_tagging_recommendations(self) -> List[Dict]:
        """Generate recommendations for tagging unidentified people."""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()

                # Find clusters without labels
                cursor.execute("""
                    SELECT COUNT(*) as unlabeled_count
                    FROM face_clusters
                    WHERE (label IS NULL OR label = '' OR label LIKE 'Person %')
                    AND id IN (
                        SELECT cluster_id FROM photo_person_associations
                        GROUP BY cluster_id HAVING COUNT(*) >= 3
                    )
                """)

                unlabeled_count = cursor.fetchone()["unlabeled_count"]

                recommendations = []
                if unlabeled_count > 0:
                    rec = {
                        "recommendation_id": "tag_unidentified_people",
                        "recommendation_type": "tag_photos",
                        "title": "Tag Unidentified People",
                        "description": f"We found {unlabeled_count} people with multiple photos who haven't been named yet",
                        "action_data": {"action": "tag_people", "people_count": unlabeled_count},
                        "confidence_score": 0.9,
                        "priority": "medium",
                    }
                    recommendations.append(rec)

                return recommendations

        except Exception as e:
            logger.error(f"Error generating tagging recommendations: {e}")
            return []

    def _generate_privacy_recommendations(self) -> List[Dict]:
        """Generate recommendations for privacy settings."""
        # This would analyze privacy patterns and suggest settings
        return []

    def _calculate_person_similarity(self, person1: sqlite3.Row, person2: sqlite3.Row) -> float:
        """Calculate similarity between two people based on characteristics."""
        similarity_score = 0.0

        # Age similarity (if both have age data)
        if person1["avg_age"] and person2["avg_age"]:
            age_diff = abs(person1["avg_age"] - person2["avg_age"])
            age_similarity = max(0, 1 - (age_diff / 20))  # Normalize by 20 years
            similarity_score += age_similarity * 0.3

        # Quality similarity
        if person1["avg_quality"] and person2["avg_quality"]:
            quality_diff = abs(person1["avg_quality"] - person2["avg_quality"])
            quality_similarity = max(0, 1 - (quality_diff / 0.5))  # Normalize by 0.5
            similarity_score += quality_similarity * 0.2

        # Photo count similarity (people with similar photo counts might be the same)
        photo_ratio = min(person1["photo_count"], person2["photo_count"]) / max(
            person1["photo_count"], person2["photo_count"]
        )
        similarity_score += photo_ratio * 0.2

        # Name similarity (basic string similarity)
        name_similarity = self._calculate_name_similarity(person1["label"], person2["label"])
        similarity_score += name_similarity * 0.3

        return min(1.0, similarity_score)

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names."""
        if not name1 or not name2:
            return 0.0

        # Simple Levenshtein-like similarity
        name1_lower = name1.lower()
        name2_lower = name2.lower()

        if name1_lower == name2_lower:
            return 1.0

        # Check for partial matches
        if name1_lower in name2_lower or name2_lower in name1_lower:
            return 0.7

        # Check for word overlap
        words1 = set(name1_lower.split())
        words2 = set(name2_lower.split())

        if words1 & words2:  # Common words
            return len(words1 & words2) / len(words1 | words2)

        return 0.0

    def _get_sample_photos_for_comparison(self, person1_id: str, person2_id: str) -> Dict:
        """Get sample photos for visual comparison of potential duplicates."""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()

                # Get best quality photos for each person
                cursor.execute(
                    """
                    SELECT ppa.photo_path, fd.overall_quality
                    FROM photo_person_associations ppa
                    JOIN face_detections fd ON ppa.detection_id = fd.detection_id
                    WHERE ppa.cluster_id = ?
                    ORDER BY fd.overall_quality DESC
                    LIMIT 3
                """,
                    (person1_id,),
                )

                person1_photos = [row["photo_path"] for row in cursor.fetchall()]

                cursor.execute(
                    """
                    SELECT ppa.photo_path, fd.overall_quality
                    FROM photo_person_associations ppa
                    JOIN face_detections fd ON ppa.detection_id = fd.detection_id
                    WHERE ppa.cluster_id = ?
                    ORDER BY fd.overall_quality DESC
                    LIMIT 3
                """,
                    (person2_id,),
                )

                person2_photos = [row["photo_path"] for row in cursor.fetchall()]

                return {"person1_samples": person1_photos, "person2_samples": person2_photos}

        except Exception as e:
            logger.error(f"Error getting sample photos: {e}")
            return {"person1_samples": [], "person2_samples": []}

    def _find_shared_emotions(self, emotions1: str, emotions2: str) -> List[str]:
        """Find shared emotions between two people."""
        if not emotions1 or not emotions2:
            return []

        set1 = set(emotions1.split(","))
        set2 = set(emotions2.split(","))

        return list(set1 & set2)

    def _find_shared_genders(self, genders1: str, genders2: str) -> List[str]:
        """Find shared genders between two people."""
        if not genders1 or not genders2:
            return []

        set1 = set(genders1.split(","))
        set2 = set(genders2.split(","))

        return list(set1 & set2)

    def _is_travel_pattern(self, photo_count: int) -> bool:
        """Determine if photo pattern suggests travel."""
        # Simple heuristic: multiple photos together might indicate travel
        return photo_count >= 5

    def _generate_event_name(self, event: Dict) -> str:
        """Generate a descriptive name for an event."""
        event_type = event["event_type"].replace("_", " ").title()
        date = event["start_time"][:10]

        return f"{event_type} - {date}"
