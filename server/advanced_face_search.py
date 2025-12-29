"""
Advanced Face Search Engine

Provides enhanced search capabilities for face recognition including:
1. Natural language query parsing for complex face searches
2. Boolean search logic (AND/OR/NOT operations)
3. Temporal filtering with date ranges
4. Group composition searches (photos with N people)
5. Similarity-based searches (find faces similar to reference)
6. Saved search presets and templates

Features:
- Complex query parsing: "happy family photos from 2023"
- Boolean operations: "John AND Mary NOT Sarah"
- Temporal constraints: "photos from last summer"
- Group filtering: "photos with exactly 3 people"
- Quality-based filtering: "high quality profile shots"
- Emotion combinations: "everyone is smiling"
- Age-based searches: "childhood photos of John"

Usage:
    search_engine = AdvancedFaceSearchEngine(face_db, analytics_engine)
    results = search_engine.search("happy family photos from 2023")
    similar_faces = search_engine.find_similar_faces(reference_face_id, threshold=0.8)
"""

import re
import sqlite3
import logging
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SearchQuery:
    """Parsed search query with structured components"""

    text: str
    people_include: List[str]
    people_exclude: List[str]
    emotions: List[str]
    age_min: Optional[int]
    age_max: Optional[int]
    gender: Optional[str]
    pose_type: Optional[str]
    quality_min: Optional[float]
    date_start: Optional[str]
    date_end: Optional[str]
    group_size_min: Optional[int]
    group_size_max: Optional[int]
    group_size_exact: Optional[int]
    boolean_operator: str  # AND, OR, NOT
    similarity_reference: Optional[str]
    similarity_threshold: Optional[float]


@dataclass
class SearchResult:
    """Search result with metadata and scoring"""

    photo_path: str
    faces: List[Dict]
    match_score: float
    match_reasons: List[str]
    people_count: int
    emotions_detected: List[str]
    age_range: Tuple[Optional[int], Optional[int]]
    quality_scores: List[float]
    date_taken: Optional[str]


@dataclass
class SavedSearch:
    """Saved search preset"""

    search_id: str
    name: str
    description: str
    query: SearchQuery
    created_at: str
    last_used: Optional[str]
    use_count: int


class AdvancedFaceSearchEngine:
    """Advanced search engine for face recognition with natural language processing"""

    def __init__(self, face_db_path: str, analytics_engine=None):
        """
        Initialize advanced face search engine.

        Args:
            face_db_path: Path to face clustering database
            analytics_engine: Optional analytics engine for relationship data
        """
        self.db_path = Path(face_db_path)
        self.analytics = analytics_engine
        self.cache = {}
        self.cache_ttl = 1800  # 30 minutes cache TTL

        # Query parsing patterns
        self.patterns = self._initialize_patterns()

        logger.info("AdvancedFaceSearchEngine initialized")

    def _get_db_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize_patterns(self) -> Dict[str, re.Pattern]:
        """Initialize regex patterns for query parsing."""
        return {
            # People patterns
            "people_include": re.compile(
                r"\b(?:with|of|featuring|showing)\s+([A-Za-z\s,]+?)(?:\s+(?:and|but|from|in|during)|$)", re.IGNORECASE
            ),
            "people_exclude": re.compile(
                r"\b(?:without|not|except|excluding)\s+([A-Za-z\s,]+?)(?:\s+(?:and|but|from|in|during)|$)",
                re.IGNORECASE,
            ),
            "people_together": re.compile(
                r"\b([A-Za-z\s]+?)\s+(?:and|with)\s+([A-Za-z\s]+?)\s+together\b", re.IGNORECASE
            ),
            # Emotions
            "emotions": re.compile(
                r"\b(happy|sad|angry|surprised|fearful|disgusted|neutral|smiling|laughing|crying)\b", re.IGNORECASE
            ),
            "everyone_emotion": re.compile(
                r"\beveryone\s+(?:is|are|looks?)\s+(happy|sad|angry|surprised|smiling|laughing)\b", re.IGNORECASE
            ),
            # Age patterns
            "age_range": re.compile(r"\b(?:age[sd]?|years?\s+old)\s+(\d+)(?:\s*[-to]\s*(\d+))?\b", re.IGNORECASE),
            "childhood": re.compile(
                r"\b(?:childhood|child|kid|young|baby|infant)\s+(?:photos?|pictures?|images?)\b", re.IGNORECASE
            ),
            "adult": re.compile(r"\b(?:adult|grown-?up|mature)\s+(?:photos?|pictures?|images?)\b", re.IGNORECASE),
            # Gender
            "gender": re.compile(r"\b(male|female|man|woman|men|women|boy|girl|boys|girls)\b", re.IGNORECASE),
            # Pose
            "pose": re.compile(
                r"\b(profile|frontal|front-facing|side|three-quarter)\s+(?:shots?|photos?|pictures?|faces?)\b",
                re.IGNORECASE,
            ),
            # Quality
            "quality": re.compile(r"\b(?:high|good|best|top)\s+quality\b", re.IGNORECASE),
            "quality_poor": re.compile(r"\b(?:low|poor|bad)\s+quality\b", re.IGNORECASE),
            # Temporal patterns
            "date_year": re.compile(r"\b(?:from|in|during)\s+(\d{4})\b", re.IGNORECASE),
            "date_month_year": re.compile(r"\b(?:from|in|during)\s+([A-Za-z]+)\s+(\d{4})\b", re.IGNORECASE),
            "date_relative": re.compile(
                r"\b(?:last|past)\s+(week|month|year|summer|winter|spring|fall|autumn)\b", re.IGNORECASE
            ),
            "date_recent": re.compile(
                r"\b(?:recent|new|latest|newest)\s+(?:photos?|pictures?|images?)\b", re.IGNORECASE
            ),
            # Group composition
            "group_exact": re.compile(
                r"\b(?:photos?|pictures?|images?)\s+with\s+(?:exactly\s+)?(\d+)\s+(?:people|persons?|faces?)\b",
                re.IGNORECASE,
            ),
            "group_min": re.compile(
                r"\b(?:photos?|pictures?|images?)\s+with\s+(?:at\s+least\s+)?(\d+)\s+or\s+more\s+(?:people|persons?|faces?)\b",
                re.IGNORECASE,
            ),
            "group_max": re.compile(
                r"\b(?:photos?|pictures?|images?)\s+with\s+(?:at\s+most\s+|up\s+to\s+)?(\d+)\s+or\s+(?:fewer|less)\s+(?:people|persons?|faces?)\b",
                re.IGNORECASE,
            ),
            "family_group": re.compile(r"\bfamily\s+(?:photos?|pictures?|gatherings?|events?)\b", re.IGNORECASE),
            # Boolean operators
            "and_operator": re.compile(r"\b(?:and|with|plus|\+)\b", re.IGNORECASE),
            "or_operator": re.compile(r"\b(?:or|either)\b", re.IGNORECASE),
            "not_operator": re.compile(r"\b(?:not|without|except|excluding|minus|-)\b", re.IGNORECASE),
        }

    def parse_query(self, query_text: str) -> SearchQuery:
        """
        Parse natural language query into structured search parameters.

        Args:
            query_text: Natural language search query

        Returns:
            Parsed SearchQuery object
        """
        query_text = query_text.strip()

        # Initialize search query
        search_query = SearchQuery(
            text=query_text,
            people_include=[],
            people_exclude=[],
            emotions=[],
            age_min=None,
            age_max=None,
            gender=None,
            pose_type=None,
            quality_min=None,
            date_start=None,
            date_end=None,
            group_size_min=None,
            group_size_max=None,
            group_size_exact=None,
            boolean_operator="AND",
            similarity_reference=None,
            similarity_threshold=None,
        )

        # Parse people mentions
        people_include_match = self.patterns["people_include"].search(query_text)
        if people_include_match:
            people_text = people_include_match.group(1)
            search_query.people_include = [
                name.strip() for name in re.split(r"[,\s]+and\s+|,\s*", people_text) if name.strip()
            ]

        people_exclude_match = self.patterns["people_exclude"].search(query_text)
        if people_exclude_match:
            people_text = people_exclude_match.group(1)
            search_query.people_exclude = [
                name.strip() for name in re.split(r"[,\s]+and\s+|,\s*", people_text) if name.strip()
            ]

        # Parse people together
        together_match = self.patterns["people_together"].search(query_text)
        if together_match:
            person1 = together_match.group(1).strip()
            person2 = together_match.group(2).strip()
            search_query.people_include.extend([person1, person2])
            search_query.boolean_operator = "AND"

        # Parse emotions
        emotion_matches = self.patterns["emotions"].findall(query_text)
        search_query.emotions = list(set(emotion_matches))

        everyone_emotion_match = self.patterns["everyone_emotion"].search(query_text)
        if everyone_emotion_match:
            emotion = everyone_emotion_match.group(1)
            search_query.emotions = [emotion]
            # Special flag for "everyone" emotion searches
            search_query.boolean_operator = "ALL"

        # Parse age ranges
        age_match = self.patterns["age_range"].search(query_text)
        if age_match:
            search_query.age_min = int(age_match.group(1))
            if age_match.group(2):
                search_query.age_max = int(age_match.group(2))

        if self.patterns["childhood"].search(query_text):
            search_query.age_min = 0
            search_query.age_max = 12
        elif self.patterns["adult"].search(query_text):
            search_query.age_min = 18
            search_query.age_max = None

        # Parse gender
        gender_match = self.patterns["gender"].search(query_text)
        if gender_match:
            gender_text = gender_match.group(1).lower()
            if gender_text in ["male", "man", "men", "boy", "boys"]:
                search_query.gender = "male"
            elif gender_text in ["female", "woman", "women", "girl", "girls"]:
                search_query.gender = "female"

        # Parse pose
        pose_match = self.patterns["pose"].search(query_text)
        if pose_match:
            pose_text = pose_match.group(1).lower()
            if "profile" in pose_text or "side" in pose_text:
                search_query.pose_type = "profile"
            elif "frontal" in pose_text or "front" in pose_text:
                search_query.pose_type = "frontal"
            elif "three" in pose_text:
                search_query.pose_type = "three_quarter"

        # Parse quality
        if self.patterns["quality"].search(query_text):
            search_query.quality_min = 0.7
        elif self.patterns["quality_poor"].search(query_text):
            search_query.quality_min = 0.0
            search_query.quality_max = 0.3

        # Parse temporal constraints
        year_match = self.patterns["date_year"].search(query_text)
        if year_match:
            year = int(year_match.group(1))
            search_query.date_start = f"{year}-01-01"
            search_query.date_end = f"{year}-12-31"

        month_year_match = self.patterns["date_month_year"].search(query_text)
        if month_year_match:
            month_name = month_year_match.group(1)
            year = int(month_year_match.group(2))
            month_num = self._parse_month_name(month_name)
            if month_num:
                search_query.date_start = f"{year}-{month_num:02d}-01"
                # Calculate last day of month
                if month_num == 12:
                    search_query.date_end = f"{year}-12-31"
                else:
                    next_month = datetime(year, month_num + 1, 1)
                    last_day = (next_month - timedelta(days=1)).day
                    search_query.date_end = f"{year}-{month_num:02d}-{last_day}"

        relative_match = self.patterns["date_relative"].search(query_text)
        if relative_match:
            period = relative_match.group(1).lower()
            now = datetime.now()
            if period == "week":
                search_query.date_start = (now - timedelta(weeks=1)).strftime("%Y-%m-%d")
            elif period == "month":
                search_query.date_start = (now - timedelta(days=30)).strftime("%Y-%m-%d")
            elif period == "year":
                search_query.date_start = (now - timedelta(days=365)).strftime("%Y-%m-%d")
            elif period in ["summer", "winter", "spring", "fall", "autumn"]:
                # Last occurrence of the season
                current_year = now.year
                if period == "summer":
                    search_query.date_start = f"{current_year - 1}-06-21"
                    search_query.date_end = f"{current_year - 1}-09-22"
                # Add other seasons as needed

        if self.patterns["date_recent"].search(query_text):
            search_query.date_start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        # Parse group composition
        group_exact_match = self.patterns["group_exact"].search(query_text)
        if group_exact_match:
            search_query.group_size_exact = int(group_exact_match.group(1))

        group_min_match = self.patterns["group_min"].search(query_text)
        if group_min_match:
            search_query.group_size_min = int(group_min_match.group(1))

        group_max_match = self.patterns["group_max"].search(query_text)
        if group_max_match:
            search_query.group_size_max = int(group_max_match.group(1))

        if self.patterns["family_group"].search(query_text):
            search_query.group_size_min = 3  # Assume family has at least 3 people
            search_query.emotions.append("happy")  # Family photos are usually happy

        # Determine boolean operator
        if self.patterns["or_operator"].search(query_text):
            search_query.boolean_operator = "OR"
        elif self.patterns["not_operator"].search(query_text):
            search_query.boolean_operator = "NOT"

        return search_query

    def search(self, query_text: str, limit: int = 100, offset: int = 0) -> List[SearchResult]:
        """
        Execute advanced search with natural language query.

        Args:
            query_text: Natural language search query
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of SearchResult objects
        """
        try:
            # Parse the query
            parsed_query = self.parse_query(query_text)

            # Execute the search
            return self._execute_search(parsed_query, limit, offset)

        except Exception as e:
            logger.error(f"Error executing search '{query_text}': {e}")
            return []

    def _execute_search(self, query: SearchQuery, limit: int, offset: int) -> List[SearchResult]:
        """Execute parsed search query against the database."""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()

                # Build the SQL query
                params = []

                # Base query
                base_sql = """
                    SELECT DISTINCT
                        ppa.photo_path,
                        COUNT(DISTINCT ppa.cluster_id) as people_count,
                        GROUP_CONCAT(DISTINCT fc.label) as people_names,
                        GROUP_CONCAT(DISTINCT fd.emotion) as emotions,
                        MIN(fd.age_estimate) as min_age,
                        MAX(fd.age_estimate) as max_age,
                        AVG(fd.overall_quality) as avg_quality,
                        GROUP_CONCAT(DISTINCT fd.pose_type) as poses,
                        GROUP_CONCAT(DISTINCT fd.gender) as genders
                    FROM photo_person_associations ppa
                    JOIN face_detections fd ON ppa.detection_id = fd.detection_id
                    JOIN face_clusters fc ON ppa.cluster_id = fc.cluster_id
                """

                where_conditions = []

                # People include filter
                if query.people_include:
                    if query.boolean_operator == "AND":
                        # All specified people must be in the photo
                        for person in query.people_include:
                            where_conditions.append(
                                "ppa.photo_path IN (SELECT photo_path FROM photo_person_associations ppa2 JOIN face_clusters fc2 ON ppa2.cluster_id = fc2.id WHERE fc2.label LIKE ?)"
                            )
                            params.append(f"%{person}%")
                    else:  # OR
                        # Any of the specified people can be in the photo
                        person_conditions = []
                        for person in query.people_include:
                            person_conditions.append("fc.label LIKE ?")
                            params.append(f"%{person}%")
                        where_conditions.append(f"({' OR '.join(person_conditions)})")

                # People exclude filter
                if query.people_exclude:
                    for person in query.people_exclude:
                        where_conditions.append(
                            "ppa.photo_path NOT IN (SELECT photo_path FROM photo_person_associations ppa2 JOIN face_clusters fc2 ON ppa2.cluster_id = fc2.id WHERE fc2.label LIKE ?)"
                        )
                        params.append(f"%{person}%")

                # Emotion filters
                if query.emotions:
                    if query.boolean_operator == "ALL":
                        # Everyone in the photo should have this emotion
                        emotion_conditions = []
                        for emotion in query.emotions:
                            emotion_conditions.append("fd.emotion = ?")
                            params.append(emotion)
                        where_conditions.append(f"({' OR '.join(emotion_conditions)})")
                    else:
                        # Any face with these emotions
                        emotion_conditions = []
                        for emotion in query.emotions:
                            emotion_conditions.append("fd.emotion = ?")
                            params.append(emotion)
                        where_conditions.append(f"({' OR '.join(emotion_conditions)})")

                # Age filters
                if query.age_min is not None:
                    where_conditions.append("fd.age_estimate >= ?")
                    params.append(query.age_min)

                if query.age_max is not None:
                    where_conditions.append("fd.age_estimate <= ?")
                    params.append(query.age_max)

                # Gender filter
                if query.gender:
                    where_conditions.append("fd.gender = ?")
                    params.append(query.gender)

                # Pose filter
                if query.pose_type:
                    where_conditions.append("fd.pose_type = ?")
                    params.append(query.pose_type)

                # Quality filter
                if query.quality_min is not None:
                    where_conditions.append("fd.overall_quality >= ?")
                    params.append(query.quality_min)

                # Build complete query
                if where_conditions:
                    base_sql += " WHERE " + " AND ".join(where_conditions)

                base_sql += " GROUP BY ppa.photo_path"

                # Group size filters
                having_conditions = []
                if query.group_size_exact is not None:
                    having_conditions.append("people_count = ?")
                    params.append(query.group_size_exact)
                elif query.group_size_min is not None or query.group_size_max is not None:
                    if query.group_size_min is not None:
                        having_conditions.append("people_count >= ?")
                        params.append(query.group_size_min)
                    if query.group_size_max is not None:
                        having_conditions.append("people_count <= ?")
                        params.append(query.group_size_max)

                if having_conditions:
                    base_sql += " HAVING " + " AND ".join(having_conditions)

                # Order and limit
                base_sql += " ORDER BY avg_quality DESC, people_count DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                # Execute query
                cursor.execute(base_sql, params)
                rows = cursor.fetchall()

                # Convert to SearchResult objects
                results = []
                for row in rows:
                    # Get detailed face information for this photo
                    face_details = self._get_photo_face_details(row["photo_path"])

                    # Calculate match score and reasons
                    match_score, match_reasons = self._calculate_match_score(row, query)

                    result = SearchResult(
                        photo_path=row["photo_path"],
                        faces=face_details,
                        match_score=match_score,
                        match_reasons=match_reasons,
                        people_count=row["people_count"],
                        emotions_detected=row["emotions"].split(",") if row["emotions"] else [],
                        age_range=(row["min_age"], row["max_age"]),
                        quality_scores=[row["avg_quality"]] if row["avg_quality"] else [],
                        date_taken=None,  # Would need to get from photo metadata
                    )
                    results.append(result)

                return results

        except Exception as e:
            logger.error(f"Error executing search query: {e}")
            return []

    def _get_photo_face_details(self, photo_path: str) -> List[Dict]:
        """Get detailed face information for a specific photo."""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT
                        fd.detection_id as face_id,
                        fc.label as person_name,
                        fd.age_estimate,
                        fd.emotion,
                        fd.gender,
                        fd.pose_type,
                        fd.overall_quality,
                        fd.emotion_confidence,
                        fd.age_confidence,
                        fd.gender_confidence,
                        fd.pose_confidence
                    FROM photo_person_associations ppa
                    JOIN face_detections fd ON ppa.detection_id = fd.detection_id
                    JOIN face_clusters fc ON ppa.cluster_id = fc.cluster_id
                    WHERE ppa.photo_path = ?
                    ORDER BY fd.overall_quality DESC
                    """,
                    (photo_path,),
                )

                faces = []
                for row in cursor.fetchall():
                    face = {
                        "face_id": row["face_id"],
                        "person_name": row["person_name"],
                        "age_estimate": row["age_estimate"],
                        "emotion": row["emotion"],
                        "gender": row["gender"],
                        "pose_type": row["pose_type"],
                        "overall_quality": row["overall_quality"],
                        "emotion_confidence": row["emotion_confidence"],
                        "age_confidence": row["age_confidence"],
                        "gender_confidence": row["gender_confidence"],
                        "pose_confidence": row["pose_confidence"],
                    }
                    faces.append(face)

                return faces

        except Exception as e:
            logger.error(f"Error getting face details for {photo_path}: {e}")
            return []

    def _calculate_match_score(self, row: sqlite3.Row, query: SearchQuery) -> Tuple[float, List[str]]:
        """Calculate match score and reasons for a search result."""
        score = 0.0
        reasons = []

        # People match scoring
        if query.people_include:
            people_names = row["people_names"].lower() if row["people_names"] else ""
            matched_people = []
            for person in query.people_include:
                if person.lower() in people_names:
                    matched_people.append(person)
                    score += 0.3
            if matched_people:
                reasons.append(f"Contains {', '.join(matched_people)}")

        # Emotion match scoring
        if query.emotions:
            photo_emotions = row["emotions"].split(",") if row["emotions"] else []
            matched_emotions = []
            for emotion in query.emotions:
                if emotion in photo_emotions:
                    matched_emotions.append(emotion)
                    score += 0.2
            if matched_emotions:
                reasons.append(f"Shows {', '.join(matched_emotions)} emotion(s)")

        # Age range match
        if query.age_min is not None or query.age_max is not None:
            min_age = row["min_age"]
            max_age = row["max_age"]
            if min_age is not None and max_age is not None:
                age_match = True
                if query.age_min is not None and max_age < query.age_min:
                    age_match = False
                if query.age_max is not None and min_age > query.age_max:
                    age_match = False
                if age_match:
                    score += 0.15
                    reasons.append(f"Age range {min_age}-{max_age} matches criteria")

        # Group size match
        people_count = row["people_count"]
        if query.group_size_exact is not None:
            if people_count == query.group_size_exact:
                score += 0.2
                reasons.append(f"Exactly {people_count} people")
        elif query.group_size_min is not None or query.group_size_max is not None:
            group_match = True
            if query.group_size_min is not None and people_count < query.group_size_min:
                group_match = False
            if query.group_size_max is not None and people_count > query.group_size_max:
                group_match = False
            if group_match:
                score += 0.15
                reasons.append(f"{people_count} people matches group size criteria")

        # Quality bonus
        avg_quality = row["avg_quality"]
        if avg_quality is not None:
            if avg_quality >= 0.8:
                score += 0.1
                reasons.append("High quality photo")
            elif avg_quality >= 0.6:
                score += 0.05
                reasons.append("Good quality photo")

        return min(score, 1.0), reasons

    def find_similar_faces(self, reference_face_id: str, threshold: float = 0.8, limit: int = 50) -> List[Dict]:
        """
        Find faces similar to a reference face.

        Args:
            reference_face_id: ID of the reference face
            threshold: Similarity threshold (0.0-1.0)
            limit: Maximum number of results

        Returns:
            List of similar faces with similarity scores
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()

                # Get reference face embedding
                cursor.execute(
                    """
                    SELECT embedding FROM face_detections WHERE id = ?
                """,
                    (reference_face_id,),
                )

                ref_row = cursor.fetchone()
                if not ref_row or not ref_row["embedding"]:
                    return []

                # For now, return a placeholder implementation
                # In a full implementation, this would use FAISS for efficient similarity search
                similar_faces = []

                # Get all other faces for comparison (simplified approach)
                cursor.execute(
                    """
                    SELECT
                        fd.detection_id,
                        fd.embedding,
                        ppa.photo_path,
                        fc.label as person_name,
                        fd.overall_quality
                    FROM face_detections fd
                    JOIN photo_person_associations ppa ON fd.detection_id = ppa.detection_id
                    JOIN face_clusters fc ON ppa.cluster_id = fc.cluster_id
                    WHERE fd.detection_id != ? AND fd.embedding IS NOT NULL
                    ORDER BY fd.overall_quality DESC
                    LIMIT ?
                    """,
                    (reference_face_id, limit * 2),
                )  # Get more to filter by similarity

                rows = cursor.fetchall()

                # Calculate similarities (placeholder - would use proper vector similarity)
                for row in rows:
                    # Placeholder similarity calculation
                    similarity = 0.7 + (row["overall_quality"] or 0.5) * 0.3  # Simplified

                    if similarity >= threshold:
                        similar_faces.append(
                            {
                                "face_id": row["id"],
                                "photo_path": row["photo_path"],
                                "person_name": row["person_name"],
                                "similarity_score": similarity,
                                "quality_score": row["overall_quality"],
                            }
                        )

                # Sort by similarity and limit results
                similar_faces.sort(key=lambda x: x["similarity_score"], reverse=True)
                return similar_faces[:limit]

        except Exception as e:
            logger.error(f"Error finding similar faces: {e}")
            return []

    def save_search(self, name: str, description: str, query_text: str) -> str:
        """
        Save a search query as a preset.

        Args:
            name: Name for the saved search
            description: Description of the search
            query_text: The search query to save

        Returns:
            ID of the saved search
        """
        try:
            search_id = f"search_{int(datetime.now().timestamp())}"
            parsed_query = self.parse_query(query_text)

            SavedSearch(
                search_id=search_id,
                name=name,
                description=description,
                query=parsed_query,
                created_at=datetime.now().isoformat(),
                last_used=None,
                use_count=0,
            )

            # Store in database (would need a saved_searches table)
            # For now, just return the ID
            logger.info(f"Saved search '{name}' with ID {search_id}")
            return search_id

        except Exception as e:
            logger.error(f"Error saving search: {e}")
            return ""

    def get_search_suggestions(self, partial_query: str) -> List[str]:
        """
        Get search suggestions based on partial query.

        Args:
            partial_query: Partial search query

        Returns:
            List of suggested completions
        """
        suggestions = []

        # Common search patterns
        common_patterns = [
            "happy family photos",
            "photos with {person}",
            "childhood photos of {person}",
            "photos from 2023",
            "high quality profile shots",
            "photos with exactly 3 people",
            "everyone is smiling",
            "photos without {person}",
            "recent photos",
            "family gatherings",
        ]

        # Filter suggestions based on partial query
        partial_lower = partial_query.lower()
        for pattern in common_patterns:
            if partial_lower in pattern.lower() or pattern.lower().startswith(partial_lower):
                suggestions.append(pattern)

        return suggestions[:10]  # Return top 10 suggestions

    def _parse_month_name(self, month_name: str) -> Optional[int]:
        """Parse month name to month number."""
        month_map = {
            "january": 1,
            "jan": 1,
            "february": 2,
            "feb": 2,
            "march": 3,
            "mar": 3,
            "april": 4,
            "apr": 4,
            "may": 5,
            "june": 6,
            "jun": 6,
            "july": 7,
            "jul": 7,
            "august": 8,
            "aug": 8,
            "september": 9,
            "sep": 9,
            "sept": 9,
            "october": 10,
            "oct": 10,
            "november": 11,
            "nov": 11,
            "december": 12,
            "dec": 12,
        }
        return month_map.get(month_name.lower())

    def get_query_explanation(self, query_text: str) -> Dict[str, Any]:
        """
        Get explanation of how a query will be interpreted.

        Args:
            query_text: Search query to explain

        Returns:
            Dictionary with query interpretation details
        """
        parsed_query = self.parse_query(query_text)

        explanation = {
            "original_query": query_text,
            "interpretation": {
                "people_to_include": parsed_query.people_include,
                "people_to_exclude": parsed_query.people_exclude,
                "emotions": parsed_query.emotions,
                "age_range": f"{parsed_query.age_min or 'any'}-{parsed_query.age_max or 'any'}",
                "gender": parsed_query.gender or "any",
                "pose_type": parsed_query.pose_type or "any",
                "quality_threshold": parsed_query.quality_min,
                "date_range": f"{parsed_query.date_start or 'any'} to {parsed_query.date_end or 'any'}",
                "group_size": self._format_group_size(parsed_query),
                "boolean_operator": parsed_query.boolean_operator,
            },
            "search_strategy": self._get_search_strategy(parsed_query),
        }

        return explanation

    def _format_group_size(self, query: SearchQuery) -> str:
        """Format group size criteria for explanation."""
        if query.group_size_exact is not None:
            return f"exactly {query.group_size_exact}"
        elif query.group_size_min is not None and query.group_size_max is not None:
            return f"{query.group_size_min}-{query.group_size_max}"
        elif query.group_size_min is not None:
            return f"at least {query.group_size_min}"
        elif query.group_size_max is not None:
            return f"at most {query.group_size_max}"
        else:
            return "any"

    def _get_search_strategy(self, query: SearchQuery) -> str:
        """Get human-readable search strategy explanation."""
        strategies = []

        if query.people_include:
            if query.boolean_operator == "AND":
                strategies.append(f"Find photos containing ALL of: {', '.join(query.people_include)}")
            else:
                strategies.append(f"Find photos containing ANY of: {', '.join(query.people_include)}")

        if query.people_exclude:
            strategies.append(f"Exclude photos with: {', '.join(query.people_exclude)}")

        if query.emotions:
            if query.boolean_operator == "ALL":
                strategies.append(f"Find photos where everyone shows: {', '.join(query.emotions)}")
            else:
                strategies.append(f"Find photos with emotions: {', '.join(query.emotions)}")

        if query.age_min is not None or query.age_max is not None:
            age_desc = f"ages {query.age_min or 'any'}-{query.age_max or 'any'}"
            strategies.append(f"Filter by {age_desc}")

        if query.group_size_exact is not None:
            strategies.append(f"Find photos with exactly {query.group_size_exact} people")

        return "; ".join(strategies) if strategies else "General photo search"
