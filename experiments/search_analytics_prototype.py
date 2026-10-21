#!/usr/bin/env python3
"""
Search Analytics Prototype - User Behavior Learning System
Experimental implementation for capturing and analyzing search patterns
"""

import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import re


@dataclass
class SearchInteraction:
    """Individual user interaction with search result"""

    type: str  # 'click', 'hover', 'select', 'export', 'skip'
    photo_path: str
    result_position: int  # 1-based position in results
    timestamp: float
    dwell_time: Optional[float] = None
    original_score: float = 0.0


@dataclass
class SearchEvent:
    """Complete search session with user interactions"""

    query: str
    search_mode: str  # 'metadata', 'semantic', 'hybrid'
    timestamp: float
    session_id: str
    collection_size: int
    result_count: int
    search_duration: float
    interactions: List[SearchInteraction]
    previous_query: Optional[str] = None
    query_source: str = "manual"  # 'manual', 'timeline', 'suggestion'


class QueryAnalyzer:
    """Analyzes search queries to extract features for ML models"""

    def __init__(self):
        # Photography-specific term patterns
        self.technical_patterns = {
            "focal_length": r"\d+mm",
            "aperture": r"f/\d+\.?\d*",
            "iso": r"ISO\s*\d+",
            "shutter_speed": r"\d+/\d+",
            "camera_brands": r"(Canon|Sony|Nikon|Fuji|Olympus|Panasonic|Leica)",
            "lens_types": r"(macro|telephoto|wide.?angle|prime|zoom)",
        }

        self.emotional_words = {
            "positive": ["beautiful", "stunning", "amazing", "gorgeous", "peaceful", "happy", "joyful"],
            "dramatic": ["dramatic", "moody", "dark", "stormy", "intense", "powerful"],
            "soft": ["soft", "gentle", "warm", "cozy", "intimate", "tender"],
        }

        self.color_words = [
            "red",
            "blue",
            "green",
            "yellow",
            "orange",
            "purple",
            "pink",
            "black",
            "white",
            "golden",
            "silver",
            "vibrant",
            "colorful",
            "monochrome",
        ]

        self.object_categories = {
            "people": ["person", "people", "portrait", "face", "child", "family", "wedding"],
            "nature": ["landscape", "mountain", "tree", "flower", "sunset", "ocean", "beach"],
            "animals": ["dog", "cat", "bird", "wildlife", "pet"],
            "architecture": ["building", "house", "bridge", "city", "urban", "street"],
        }

    def analyze_query(self, query: str) -> Dict[str, Any]:
        """Extract comprehensive features from search query"""
        query_lower = query.lower()
        words = query_lower.split()

        features = {
            # Basic properties
            "length_words": len(words),
            "length_chars": len(query),
            "has_quotes": '"' in query or "'" in query,
            "has_sql_operators": any(op in query.upper() for op in ["AND", "OR", "=", ">", "<", "LIKE"]),
            # Technical content
            "technical_terms_count": self._count_technical_terms(query),
            "has_focal_length": bool(re.search(self.technical_patterns["focal_length"], query)),
            "has_aperture": bool(re.search(self.technical_patterns["aperture"], query)),
            "has_iso": bool(re.search(self.technical_patterns["iso"], query)),
            "has_camera_brand": bool(re.search(self.technical_patterns["camera_brands"], query, re.IGNORECASE)),
            # Content analysis
            "emotional_score": self._calculate_emotional_score(query_lower),
            "color_mentions": self._count_color_mentions(query_lower),
            "object_categories": self._identify_object_categories(query_lower),
            # Query complexity
            "complexity_score": self._calculate_complexity(query),
            "likely_intent": self._classify_intent(query_lower),
            # Temporal indicators
            "has_date_terms": self._has_date_terms(query_lower),
            "has_time_terms": self._has_time_terms(query_lower),
        }

        return features

    def _count_technical_terms(self, query: str) -> int:
        """Count technical photography terms in query"""
        count = 0
        for pattern in self.technical_patterns.values():
            count += len(re.findall(pattern, query, re.IGNORECASE))
        return count

    def _calculate_emotional_score(self, query: str) -> float:
        """Calculate emotional content score (0-1)"""
        words = query.split()
        emotional_count = 0

        for category, emotion_words in self.emotional_words.items():
            for word in emotion_words:
                if word in query:
                    emotional_count += 1

        return min(emotional_count / len(words), 1.0) if words else 0.0

    def _count_color_mentions(self, query: str) -> int:
        """Count color-related words"""
        return sum(1 for color in self.color_words if color in query)

    def _identify_object_categories(self, query: str) -> List[str]:
        """Identify main object categories mentioned"""
        categories = []
        for category, objects in self.object_categories.items():
            if any(obj in query for obj in objects):
                categories.append(category)
        return categories

    def _calculate_complexity(self, query: str) -> float:
        """Calculate query complexity score (0-1)"""
        factors = [
            len(query.split()) / 10,  # Word count factor
            len(re.findall(r"[AND|OR]", query.upper())) / 3,  # Logical operators
            len(re.findall(r"[=<>]", query)) / 3,  # Comparison operators
            self._count_technical_terms(query) / 5,  # Technical terms
        ]
        return min(sum(factors) / len(factors), 1.0)

    def _classify_intent(self, query: str) -> str:
        """Classify search intent based on query content"""
        if any(op in query.upper() for op in ["=", ">", "<", "AND", "OR"]):
            return "technical"
        elif any(word in query for word in ["beautiful", "stunning", "dramatic", "mood"]):
            return "creative"
        elif self._has_date_terms(query) or self._has_time_terms(query):
            return "temporal"
        elif any(word in query for word in ["city", "location", "place", "where"]):
            return "spatial"
        else:
            return "content"

    def _has_date_terms(self, query: str) -> bool:
        """Check for date-related terms"""
        date_terms = [
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
            "today",
            "yesterday",
            "week",
            "month",
            "year",
            "2023",
            "2024",
        ]
        return any(term in query for term in date_terms)

    def _has_time_terms(self, query: str) -> bool:
        """Check for time-related terms"""
        time_terms = [
            "morning",
            "afternoon",
            "evening",
            "night",
            "sunrise",
            "sunset",
            "golden hour",
            "blue hour",
            "dawn",
            "dusk",
        ]
        return any(term in query for term in time_terms)


class SearchAnalyticsDB:
    """Database for storing and analyzing search behavior"""

    def __init__(self, db_path: str = "experiments/search_analytics.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Search events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                search_mode TEXT NOT NULL,
                timestamp REAL NOT NULL,
                session_id TEXT NOT NULL,
                collection_size INTEGER,
                result_count INTEGER,
                search_duration REAL,
                previous_query TEXT,
                query_source TEXT,
                query_features TEXT  -- JSON blob of analyzed features
            )
        """)

        # Interactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_event_id INTEGER,
                interaction_type TEXT NOT NULL,
                photo_path TEXT NOT NULL,
                result_position INTEGER NOT NULL,
                timestamp REAL NOT NULL,
                dwell_time REAL,
                original_score REAL,
                FOREIGN KEY (search_event_id) REFERENCES search_events (id)
            )
        """)

        # User sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                start_time REAL NOT NULL,
                end_time REAL,
                total_searches INTEGER DEFAULT 0,
                successful_searches INTEGER DEFAULT 0,
                user_type TEXT  -- 'professional', 'casual', 'unknown'
            )
        """)

        conn.commit()
        conn.close()

    def store_search_event(self, event: SearchEvent, query_features: Dict[str, Any]):
        """Store search event and interactions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Insert search event
        cursor.execute(
            """
            INSERT INTO search_events
            (query, search_mode, timestamp, session_id, collection_size,
             result_count, search_duration, previous_query, query_source, query_features)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                event.query,
                event.search_mode,
                event.timestamp,
                event.session_id,
                event.collection_size,
                event.result_count,
                event.search_duration,
                event.previous_query,
                event.query_source,
                json.dumps(query_features),
            ),
        )

        search_event_id = cursor.lastrowid

        # Insert interactions
        for interaction in event.interactions:
            cursor.execute(
                """
                INSERT INTO search_interactions
                (search_event_id, interaction_type, photo_path, result_position,
                 timestamp, dwell_time, original_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    search_event_id,
                    interaction.type,
                    interaction.photo_path,
                    interaction.result_position,
                    interaction.timestamp,
                    interaction.dwell_time,
                    interaction.original_score,
                ),
            )

        conn.commit()
        conn.close()

        return search_event_id


class SearchBehaviorAnalyzer:
    """Analyzes user search behavior patterns"""

    def __init__(self, db: SearchAnalyticsDB):
        self.db = db
        self.query_analyzer = QueryAnalyzer()

    def analyze_mode_effectiveness(self) -> Dict[str, Any]:
        """Analyze which search modes work best for different query types"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        # Get search events with interactions
        cursor.execute("""
            SELECT se.search_mode, se.query_features, se.result_count,
                   COUNT(si.id) as interaction_count,
                   AVG(si.result_position) as avg_click_position,
                   COUNT(CASE WHEN si.interaction_type = 'click' THEN 1 END) as click_count
            FROM search_events se
            LEFT JOIN search_interactions si ON se.id = si.search_event_id
            GROUP BY se.id
        """)

        results = cursor.fetchall()
        conn.close()

        mode_stats = defaultdict(
            lambda: {
                "total_searches": 0,
                "searches_with_clicks": 0,
                "avg_clicks_per_search": 0,
                "avg_click_position": 0,
                "click_through_rate": 0,
            }
        )

        for row in results:
            mode = row[0]
            click_count = row[5]

            stats = mode_stats[mode]
            stats["total_searches"] += 1

            if click_count > 0:
                stats["searches_with_clicks"] += 1
                stats["avg_clicks_per_search"] += click_count
                stats["avg_click_position"] += row[4] or 0

        # Calculate final averages
        for mode, stats in mode_stats.items():
            if stats["total_searches"] > 0:
                stats["click_through_rate"] = stats["searches_with_clicks"] / stats["total_searches"]
                if stats["searches_with_clicks"] > 0:
                    stats["avg_clicks_per_search"] /= stats["searches_with_clicks"]
                    stats["avg_click_position"] /= stats["searches_with_clicks"]

        return dict(mode_stats)

    def identify_query_patterns(self) -> Dict[str, Any]:
        """Identify patterns in successful vs unsuccessful queries"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT se.query, se.search_mode, se.query_features,
                   COUNT(CASE WHEN si.interaction_type = 'click' THEN 1 END) as clicks,
                   COUNT(CASE WHEN si.interaction_type = 'export' THEN 1 END) as exports
            FROM search_events se
            LEFT JOIN search_interactions si ON se.id = si.search_event_id
            GROUP BY se.id
        """)

        results = cursor.fetchall()
        conn.close()

        successful_queries = []  # Queries with clicks or exports
        unsuccessful_queries = []  # Queries with no interactions

        for row in results:
            query_features = json.loads(row[2]) if row[2] else {}
            clicks = row[3]
            exports = row[4]

            query_data = {
                "query": row[0],
                "mode": row[1],
                "features": query_features,
                "clicks": clicks,
                "exports": exports,
            }

            if clicks > 0 or exports > 0:
                successful_queries.append(query_data)
            else:
                unsuccessful_queries.append(query_data)

        return {
            "successful_queries": successful_queries,
            "unsuccessful_queries": unsuccessful_queries,
            "success_rate": len(successful_queries) / (len(successful_queries) + len(unsuccessful_queries))
            if (successful_queries or unsuccessful_queries)
            else 0,
        }

    def analyze_position_bias(self) -> Dict[int, float]:
        """Analyze click probability by result position"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT result_position,
                   COUNT(*) as total_at_position,
                   COUNT(CASE WHEN interaction_type = 'click' THEN 1 END) as clicks_at_position
            FROM search_interactions
            WHERE result_position <= 20  -- Focus on first 20 results
            GROUP BY result_position
            ORDER BY result_position
        """)

        results = cursor.fetchall()
        conn.close()

        position_ctr = {}
        for position, total, clicks in results:
            position_ctr[position] = clicks / total if total > 0 else 0

        return position_ctr


class SearchModePredictor:
    """Machine learning model to predict optimal search mode"""

    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.feature_names = []
        self.is_trained = False

    def prepare_training_data(self, db: SearchAnalyticsDB) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data from search analytics"""
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()

        # Get search events with success metrics
        cursor.execute("""
            SELECT se.search_mode, se.query_features,
                   COUNT(CASE WHEN si.interaction_type = 'click' THEN 1 END) as clicks,
                   COUNT(CASE WHEN si.interaction_type = 'export' THEN 1 END) as exports,
                   AVG(si.result_position) as avg_click_position
            FROM search_events se
            LEFT JOIN search_interactions si ON se.id = si.search_event_id
            GROUP BY se.id
            HAVING se.query_features IS NOT NULL
        """)

        results = cursor.fetchall()
        conn.close()

        if not results:
            raise ValueError("No training data available")

        features = []
        labels = []

        for row in results:
            mode = row[0]
            query_features = json.loads(row[1])

            # Convert features to numeric array
            feature_vector = self._extract_feature_vector(query_features)
            features.append(feature_vector)
            labels.append(mode)

        return np.array(features), np.array(labels)

    def _extract_feature_vector(self, query_features: Dict[str, Any]) -> List[float]:
        """Convert query features to numeric vector"""
        # Define feature extraction order (must be consistent)
        if not self.feature_names:
            self.feature_names = [
                "length_words",
                "length_chars",
                "has_quotes",
                "has_sql_operators",
                "technical_terms_count",
                "has_focal_length",
                "has_aperture",
                "has_iso",
                "has_camera_brand",
                "emotional_score",
                "color_mentions",
                "complexity_score",
                "has_date_terms",
                "has_time_terms",
                "object_category_count",
            ]

        vector = []
        for feature_name in self.feature_names:
            if feature_name == "object_category_count":
                # Count of object categories
                value = len(query_features.get("object_categories", []))
            else:
                value = query_features.get(feature_name, 0)

            # Convert boolean to int
            if isinstance(value, bool):
                value = int(value)

            vector.append(float(value))

        return vector

    def train(self, db: SearchAnalyticsDB):
        """Train the mode prediction model"""
        X, y = self.prepare_training_data(db)

        if len(X) < 10:
            raise ValueError("Insufficient training data (need at least 10 samples)")

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Train model
        self.model.fit(X_train, y_train)
        self.is_trained = True

        # Evaluate
        y_pred = self.model.predict(X_test)
        accuracy = (y_pred == y_test).mean()

        print(f"Model trained with accuracy: {accuracy:.3f}")
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred))

        return accuracy

    def predict_optimal_mode(self, query: str) -> Dict[str, float]:
        """Predict optimal search mode for a query"""
        if not self.is_trained:
            raise ValueError("Model not trained yet")

        # Analyze query
        analyzer = QueryAnalyzer()
        query_features = analyzer.analyze_query(query)

        # Extract feature vector
        feature_vector = self._extract_feature_vector(query_features)

        # Predict probabilities
        probabilities = self.model.predict_proba([feature_vector])[0]
        classes = self.model.classes_

        # Return as dictionary
        predictions = {}
        for i, class_name in enumerate(classes):
            predictions[class_name] = float(probabilities[i])

        return predictions


def generate_synthetic_data(db: SearchAnalyticsDB, num_events: int = 100):
    """Generate synthetic search data for testing"""
    import random

    # Sample queries for different modes
    metadata_queries = [
        "camera.make = 'Canon'",
        "lens.focal_length >= 85",
        "date.taken >= '2023-01-01'",
        "iso >= 1600",
        "file.size > 5000000",
    ]

    semantic_queries = [
        "sunset over ocean",
        "happy family portrait",
        "dramatic mountain landscape",
        "colorful street art",
        "cozy indoor scene",
        "wedding ceremony outdoor",
        "children playing park",
    ]

    hybrid_queries = [
        "Canon portrait photography",
        "Sony street photography",
        "macro flower photography",
        "wedding 85mm lens",
        "landscape wide angle",
    ]

    analyzer = QueryAnalyzer()

    for i in range(num_events):
        # Random query selection
        mode_choice = random.choice(["metadata", "semantic", "hybrid"])

        if mode_choice == "metadata":
            query = random.choice(metadata_queries)
        elif mode_choice == "semantic":
            query = random.choice(semantic_queries)
        else:
            query = random.choice(hybrid_queries)

        # Generate synthetic event
        event = SearchEvent(
            query=query,
            search_mode=mode_choice,
            timestamp=datetime.now().timestamp() - random.randint(0, 86400 * 30),  # Last 30 days
            session_id=f"session_{random.randint(1, 20)}",
            collection_size=random.randint(100, 10000),
            result_count=random.randint(5, 100),
            search_duration=random.uniform(0.1, 2.0),
            interactions=[],
        )

        # Generate synthetic interactions
        num_interactions = random.randint(0, 5)
        for j in range(num_interactions):
            interaction = SearchInteraction(
                type=random.choice(["click", "hover", "select"]),
                photo_path=f"/photos/photo_{random.randint(1, 1000)}.jpg",
                result_position=random.randint(1, min(20, event.result_count)),
                timestamp=event.timestamp + random.uniform(1, 30),
                dwell_time=random.uniform(0.5, 10.0),
                original_score=random.uniform(0.1, 1.0),
            )
            event.interactions.append(interaction)

        # Analyze query and store
        query_features = analyzer.analyze_query(query)
        db.store_search_event(event, query_features)


def main():
    """Main function to demonstrate the search learning system"""
    print("Search Learning Experiment - Prototype")
    print("=" * 50)

    # Initialize components
    db = SearchAnalyticsDB()
    behavior_analyzer = SearchBehaviorAnalyzer(db)
    predictor = SearchModePredictor()

    # Generate synthetic data for testing
    print("Generating synthetic search data...")
    generate_synthetic_data(db, 200)

    # Analyze search behavior
    print("\nAnalyzing search mode effectiveness...")
    mode_effectiveness = behavior_analyzer.analyze_mode_effectiveness()
    for mode, stats in mode_effectiveness.items():
        print(f"{mode}: CTR={stats['click_through_rate']:.3f}, " f"Avg Clicks={stats['avg_clicks_per_search']:.2f}")

    # Analyze query patterns
    print("\nAnalyzing query patterns...")
    patterns = behavior_analyzer.identify_query_patterns()
    print(f"Overall success rate: {patterns['success_rate']:.3f}")

    # Train prediction model
    print("\nTraining search mode prediction model...")
    try:
        predictor.train(db)  # prints its own accuracy and classification report

        # Test predictions
        test_queries = [
            "camera.make = 'Sony' AND lens.focal_length > 50",
            "beautiful sunset landscape",
            "Canon wedding photography",
        ]

        print("\nTesting mode predictions:")
        for query in test_queries:
            predictions = predictor.predict_optimal_mode(query)
            best_mode = max(predictions, key=predictions.get)
            confidence = predictions[best_mode]
            print(f"Query: '{query}'")
            print(f"Predicted mode: {best_mode} (confidence: {confidence:.3f})")
            print()

    except ValueError as e:
        print(f"Training failed: {e}")

    print("Experiment completed!")


if __name__ == "__main__":
    main()
