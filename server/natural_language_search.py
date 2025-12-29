"""
Natural Language Search for Face Recognition

Parses natural language queries into structured face search parameters.
Supports:
- Person name queries ("photos with John")
- Group composition ("photos with 3 people")
- Emotion-based search ("happy faces", "everyone smiling")
- Age-based search ("children", "adults over 50")
- Exclusion queries ("photos with John but not Mary")
- Temporal constraints ("photos of John from last summer")
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class PersonConstraint:
    """Constraint on a person's presence in the photo."""

    name: str
    required: bool = True  # True = must be present, False = must NOT be present


@dataclass
class GroupConstraint:
    """Constraint on group composition."""

    min_people: Optional[int] = None
    max_people: Optional[int] = None
    exact_count: Optional[int] = None


@dataclass
class EmotionConstraint:
    """Constraint on facial emotions."""

    emotion: str  # happy, sad, surprised, neutral, etc.
    all_faces: bool = False  # True = "everyone smiling", False = "any smiling face"


@dataclass
class AgeConstraint:
    """Constraint on estimated age."""

    min_age: Optional[int] = None
    max_age: Optional[int] = None
    category: Optional[str] = None  # child, teenager, adult, elderly


@dataclass
class TemporalConstraint:
    """Constraint on photo date."""

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    relative_period: Optional[str] = None  # "last week", "this year", etc.


@dataclass
class ParsedFaceQuery:
    """Result of parsing a natural language face query."""

    # Person constraints
    person_constraints: List[PersonConstraint] = field(default_factory=list)

    # Group constraints
    group_constraint: Optional[GroupConstraint] = None

    # Emotion constraints
    emotion_constraints: List[EmotionConstraint] = field(default_factory=list)

    # Age constraints
    age_constraints: List[AgeConstraint] = field(default_factory=list)

    # Temporal constraints
    temporal_constraint: Optional[TemporalConstraint] = None

    # Original query for reference
    original_query: str = ""

    # Any unrecognized parts of the query
    unparsed_parts: List[str] = field(default_factory=list)

    # Confidence in the parse (0-1)
    parse_confidence: float = 1.0


class NaturalLanguageQueryParser:
    """
    Parses natural language queries into structured face search parameters.

    Examples:
        "photos with John" -> PersonConstraint(name="John", required=True)
        "photos with 3 people" -> GroupConstraint(exact_count=3)
        "happy faces" -> EmotionConstraint(emotion="happy")
        "photos with John but not Mary" -> [PersonConstraint("John", True), PersonConstraint("Mary", False)]
        "children under 10" -> AgeConstraint(max_age=10, category="child")
    """

    # Emotion keywords
    EMOTIONS = {
        "happy": ["happy", "smiling", "smile", "joyful", "cheerful", "laughing"],
        "sad": ["sad", "unhappy", "crying", "upset", "depressed"],
        "surprised": ["surprised", "shocked", "amazed", "startled"],
        "angry": ["angry", "mad", "furious", "annoyed"],
        "fearful": ["fearful", "scared", "afraid", "frightened"],
        "neutral": ["neutral", "calm", "serious", "expressionless"],
        "disgusted": ["disgusted", "grossed out"],
    }

    # Age category keywords
    AGE_CATEGORIES = {
        "baby": (0, 2),
        "toddler": (2, 4),
        "child": (0, 12),
        "children": (0, 12),
        "kid": (0, 12),
        "kids": (0, 12),
        "teenager": (13, 19),
        "teen": (13, 19),
        "teens": (13, 19),
        "young adult": (20, 35),
        "adult": (18, 65),
        "adults": (18, 65),
        "middle-aged": (40, 60),
        "senior": (60, 100),
        "elderly": (65, 100),
        "old": (60, 100),
    }

    # Temporal keywords
    TEMPORAL_KEYWORDS = {
        "today": lambda: (datetime.now().replace(hour=0, minute=0, second=0), datetime.now()),
        "yesterday": lambda: (
            datetime.now().replace(hour=0, minute=0, second=0) - timedelta(days=1),
            datetime.now().replace(hour=0, minute=0, second=0),
        ),
        "last week": lambda: (datetime.now() - timedelta(weeks=1), datetime.now()),
        "this week": lambda: (datetime.now() - timedelta(days=datetime.now().weekday()), datetime.now()),
        "last month": lambda: (datetime.now() - timedelta(days=30), datetime.now()),
        "this month": lambda: (datetime.now().replace(day=1), datetime.now()),
        "last year": lambda: (datetime.now() - timedelta(days=365), datetime.now()),
        "this year": lambda: (datetime.now().replace(month=1, day=1), datetime.now()),
        "last summer": lambda: NaturalLanguageQueryParser._get_last_season("summer"),
        "last winter": lambda: NaturalLanguageQueryParser._get_last_season("winter"),
        "last spring": lambda: NaturalLanguageQueryParser._get_last_season("spring"),
        "last fall": lambda: NaturalLanguageQueryParser._get_last_season("fall"),
    }

    @staticmethod
    def _get_last_season(season: str) -> Tuple[datetime, datetime]:
        """Get date range for last occurrence of a season."""
        now = datetime.now()
        year = now.year

        seasons = {
            "spring": (3, 6),  # March - May
            "summer": (6, 9),  # June - August
            "fall": (9, 12),  # September - November
            "winter": (12, 3),  # December - February
        }

        start_month, end_month = seasons.get(season, (1, 12))

        # If we're past this season this year, use this year, else last year
        if now.month > end_month:
            season_year = year
        else:
            season_year = year - 1

        start = datetime(season_year, start_month, 1)
        end = datetime(season_year, end_month % 12 or 12, 28)  # Approximate end

        return (start, end)

    def __init__(self, known_people: Optional[List[str]] = None):
        """
        Initialize parser.

        Args:
            known_people: List of known person names for better matching
        """
        self.known_people = set(known_people or [])

    def parse(self, query: str) -> ParsedFaceQuery:
        """
        Parse a natural language query into structured parameters.

        Args:
            query: Natural language query string

        Returns:
            ParsedFaceQuery with extracted constraints
        """
        result = ParsedFaceQuery(original_query=query)
        query_lower = query.lower().strip()

        # Track what parts we've parsed
        remaining_query = query_lower

        # IMPORTANT: Parse in this order to avoid conflicts:
        # 1. Temporal (most specific patterns)
        # 2. Group constraints (before person names to handle "with 3 people")
        # 3. Age constraints (before person names to handle "children", "teenagers")
        # 4. Emotion constraints (before person names to handle "smiling faces")
        # 5. Person constraints (last, to catch remaining names)

        # Parse temporal constraints FIRST
        temporal, remaining = self._parse_temporal_constraints(remaining_query)
        if temporal:
            result.temporal_constraint = temporal
        remaining_query = remaining

        # Parse group constraints SECOND (before person to handle "with 3 people")
        group, remaining = self._parse_group_constraint(remaining_query)
        if group:
            result.group_constraint = group
        remaining_query = remaining

        # Parse age constraints THIRD (before person to handle "children", etc)
        ages, remaining = self._parse_age_constraints(remaining_query)
        result.age_constraints = ages
        remaining_query = remaining

        # Parse emotion constraints FOURTH (handle "smiling faces" before person)
        emotions, remaining = self._parse_emotion_constraints(remaining_query)
        result.emotion_constraints = emotions
        remaining_query = remaining

        # Parse person constraints LAST (pick up remaining names)
        persons, remaining = self._parse_person_constraints(remaining_query)
        result.person_constraints = persons
        remaining_query = remaining

        # Store unparsed parts
        unparsed = remaining_query.strip()
        if unparsed:
            # Clean up common words that don't need parsing
            stopwords = {
                "photos",
                "photo",
                "pictures",
                "picture",
                "images",
                "image",
                "find",
                "show",
                "get",
                "with",
                "of",
                "the",
                "a",
                "an",
                "me",
                "my",
                "faces",
                "people",
                "person",
                "persons",
                "is",
                "are",
                "where",
            }
            unparsed_words = [w for w in unparsed.split() if w not in stopwords]
            if unparsed_words:
                result.unparsed_parts = unparsed_words

        # Calculate parse confidence
        result.parse_confidence = self._calculate_confidence(result)

        return result

    def _parse_person_constraints(self, query: str) -> Tuple[List[PersonConstraint], str]:
        """Parse person name constraints including exclusions."""
        constraints = []
        remaining = query

        # Pattern for "with X but not Y" or "with X and Y but not Z"
        exclusion_pattern = r"but\s+not\s+(\w+)"
        exclusions = re.findall(exclusion_pattern, query, re.IGNORECASE)
        for name in exclusions:
            constraints.append(PersonConstraint(name=name.capitalize(), required=False))
        remaining = re.sub(exclusion_pattern, "", remaining, flags=re.IGNORECASE)

        # Pattern for "without X"
        without_pattern = r"without\s+(\w+)"
        withouts = re.findall(without_pattern, remaining, re.IGNORECASE)
        for name in withouts:
            constraints.append(PersonConstraint(name=name.capitalize(), required=False))
        remaining = re.sub(without_pattern, "", remaining, flags=re.IGNORECASE)

        # Pattern for "with X" or "with X and Y"
        with_pattern = r"with\s+(\w+(?:\s+and\s+\w+)*)"
        with_matches = re.findall(with_pattern, remaining, re.IGNORECASE)
        for match in with_matches:
            # Split on "and" to get individual names
            names = re.split(r"\s+and\s+", match, flags=re.IGNORECASE)
            for name in names:
                name = name.strip()
                # Skip if it's a number (for group constraints)
                if name and not name.isdigit() and name not in ["people", "person", "persons"]:
                    # Check if it's a known person
                    if self.known_people and name.capitalize() in self.known_people:
                        constraints.append(PersonConstraint(name=name.capitalize(), required=True))
                    elif name[0].isupper() or (len(name) > 2 and name not in self.EMOTIONS):
                        # Assume capitalized names or non-emotion words are person names
                        constraints.append(PersonConstraint(name=name.capitalize(), required=True))

        remaining = re.sub(with_pattern, "", remaining, flags=re.IGNORECASE)

        # Pattern for "of X" (e.g., "photos of John")
        of_pattern = r"of\s+(\w+)"
        of_matches = re.findall(of_pattern, remaining, re.IGNORECASE)
        for name in of_matches:
            name = name.strip()
            if name and not name.isdigit() and name not in ["people", "person", "the", "my"]:
                if name[0].isupper() or (self.known_people and name.capitalize() in self.known_people):
                    constraints.append(PersonConstraint(name=name.capitalize(), required=True))

        remaining = re.sub(of_pattern, "", remaining, flags=re.IGNORECASE)

        return constraints, remaining.strip()

    def _parse_group_constraint(self, query: str) -> Tuple[Optional[GroupConstraint], str]:
        """Parse group size constraints."""
        remaining = query

        # Special keywords FIRST (before number patterns)
        if "solo" in query or "alone" in query:
            remaining = remaining.replace("solo", "").replace("alone", "")
            return GroupConstraint(exact_count=1), remaining.strip()

        if "couple" in query or "pair" in query:
            remaining = remaining.replace("couple", "").replace("pair", "")
            return GroupConstraint(exact_count=2), remaining.strip()

        if "group" in query and not re.search(r"\d+", query):
            remaining = remaining.replace("group", "")
            return GroupConstraint(min_people=3), remaining.strip()

        # Range patterns BEFORE exact count (longer patterns first)
        range_patterns = [
            (r"at\s+least\s+(\d+)\s+(?:happy\s+)?people", "min"),
            (r"more\s+than\s+(\d+)\s+(?:happy\s+)?people", "min_exclusive"),
            (r"at\s+most\s+(\d+)\s+(?:happy\s+)?people", "max"),
            (r"fewer\s+than\s+(\d+)\s+(?:happy\s+)?people", "max_exclusive"),
            (r"less\s+than\s+(\d+)\s+(?:happy\s+)?people", "max_exclusive"),
            (r"(\d+)\s+or\s+more\s+(?:happy\s+)?people", "min"),
            (r"(\d+)\s+to\s+(\d+)\s+(?:happy\s+)?people", "range"),
        ]

        for pattern, constraint_type in range_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                remaining = re.sub(pattern, "", remaining, flags=re.IGNORECASE)
                if constraint_type == "min":
                    return GroupConstraint(min_people=int(match.group(1))), remaining.strip()
                elif constraint_type == "min_exclusive":
                    return GroupConstraint(min_people=int(match.group(1)) + 1), remaining.strip()
                elif constraint_type == "max":
                    return GroupConstraint(max_people=int(match.group(1))), remaining.strip()
                elif constraint_type == "max_exclusive":
                    return GroupConstraint(max_people=int(match.group(1)) - 1), remaining.strip()
                elif constraint_type == "range":
                    return GroupConstraint(
                        min_people=int(match.group(1)), max_people=int(match.group(2))
                    ), remaining.strip()

        # Exact count patterns (allow optional adjective like "happy")
        exact_patterns = [
            r"(\d+)\s+(?:\w+\s+)?people",
            r"(\d+)\s+(?:\w+\s+)?persons?",
            r"(\d+)\s+(?:\w+\s+)?faces?",
            r"exactly\s+(\d+)",
        ]

        for pattern in exact_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                count = int(match.group(1))
                remaining = re.sub(pattern, "", remaining, flags=re.IGNORECASE)
                return GroupConstraint(exact_count=count), remaining.strip()

        return None, remaining.strip()

    def _parse_emotion_constraints(self, query: str) -> Tuple[List[EmotionConstraint], str]:
        """Parse emotion-based constraints."""
        constraints = []
        remaining = query

        # Check for "everyone" modifier
        everyone = "everyone" in query or "all" in query

        # Search for emotion keywords
        for emotion, keywords in self.EMOTIONS.items():
            for keyword in keywords:
                if keyword in query.lower():
                    constraints.append(EmotionConstraint(emotion=emotion, all_faces=everyone))
                    remaining = remaining.replace(keyword, "")
                    break  # Only match one keyword per emotion

        # Clean up "everyone" and "all" if used
        if everyone:
            remaining = remaining.replace("everyone", "").replace("all", "")

        return constraints, remaining.strip()

    def _parse_age_constraints(self, query: str) -> Tuple[List[AgeConstraint], str]:
        """Parse age-based constraints."""
        constraints = []
        remaining = query
        matched_categories = set()

        # Check for age category keywords (sort by length descending to match longer first)
        sorted_categories = sorted(self.AGE_CATEGORIES.keys(), key=len, reverse=True)
        for category in sorted_categories:
            min_age, max_age = self.AGE_CATEGORIES[category]
            if category in query.lower():
                # Avoid duplicates (e.g., "children" contains "child")
                key = (min_age, max_age)
                if key not in matched_categories:
                    constraints.append(AgeConstraint(min_age=min_age, max_age=max_age, category=category))
                    matched_categories.add(key)
                remaining = remaining.replace(category, "")

        # Check for specific age patterns
        age_patterns = [
            (r"under\s+(\d+)", "max"),
            (r"over\s+(\d+)", "min"),
            (r"(\d+)\s+years?\s+old", "exact"),
            (r"aged?\s+(\d+)", "exact"),
            (r"(\d+)\s*-\s*(\d+)\s+years?", "range"),
        ]

        for pattern, constraint_type in age_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                remaining = re.sub(pattern, "", remaining, flags=re.IGNORECASE)
                if constraint_type == "max":
                    constraints.append(AgeConstraint(max_age=int(match.group(1))))
                elif constraint_type == "min":
                    constraints.append(AgeConstraint(min_age=int(match.group(1))))
                elif constraint_type == "exact":
                    age = int(match.group(1))
                    constraints.append(AgeConstraint(min_age=age - 2, max_age=age + 2))
                elif constraint_type == "range":
                    constraints.append(AgeConstraint(min_age=int(match.group(1)), max_age=int(match.group(2))))

        return constraints, remaining.strip()

    def _parse_temporal_constraints(self, query: str) -> Tuple[Optional[TemporalConstraint], str]:
        """Parse temporal constraints."""
        remaining = query

        # Check for temporal keywords
        for keyword, date_func in self.TEMPORAL_KEYWORDS.items():
            if keyword in query.lower():
                start, end = date_func()
                remaining = remaining.replace(keyword, "")
                return TemporalConstraint(start_date=start, end_date=end, relative_period=keyword), remaining.strip()

        # Check for year patterns
        year_match = re.search(r"from\s+(\d{4})", query, re.IGNORECASE)
        if year_match:
            year = int(year_match.group(1))
            remaining = re.sub(r"from\s+\d{4}", "", remaining, flags=re.IGNORECASE)
            return TemporalConstraint(
                start_date=datetime(year, 1, 1), end_date=datetime(year, 12, 31), relative_period=f"from {year}"
            ), remaining.strip()

        # Check for "in YYYY" pattern
        in_year_match = re.search(r"in\s+(\d{4})", query, re.IGNORECASE)
        if in_year_match:
            year = int(in_year_match.group(1))
            remaining = re.sub(r"in\s+\d{4}", "", remaining, flags=re.IGNORECASE)
            return TemporalConstraint(
                start_date=datetime(year, 1, 1), end_date=datetime(year, 12, 31), relative_period=f"in {year}"
            ), remaining.strip()

        return None, remaining.strip()

    def _calculate_confidence(self, result: ParsedFaceQuery) -> float:
        """Calculate confidence score for the parse."""
        # Start with full confidence
        confidence = 1.0

        # Reduce for unparsed parts
        if result.unparsed_parts:
            confidence -= 0.1 * len(result.unparsed_parts)

        # Increase for successful constraint extraction
        if result.person_constraints:
            confidence += 0.1
        if result.group_constraint:
            confidence += 0.05
        if result.emotion_constraints:
            confidence += 0.05
        if result.temporal_constraint:
            confidence += 0.05

        # Clamp to [0, 1]
        return max(0.0, min(1.0, confidence))


def create_parser(known_people: Optional[List[str]] = None) -> NaturalLanguageQueryParser:
    """Factory function to create a parser instance."""
    return NaturalLanguageQueryParser(known_people=known_people)
