"""
Natural language parsing for face attribute searches.

Converts simple phrases like "happy kids under 10" into structured filters.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple, Optional


EMOTION_ALIASES = {
    "happy": ["happy", "smile", "smiling", "joy", "cheerful"],
    "sad": ["sad", "tearful", "down"],
    "angry": ["angry", "mad", "furious"],
    "surprised": ["surprised", "surprise", "shocked"],
    "fearful": ["fearful", "afraid", "scared"],
    "disgusted": ["disgusted", "disgust", "grossed"],
    "neutral": ["neutral", "calm", "plain"],
}

GENDER_ALIASES = {
    "male": ["male", "man", "men", "boy", "guy"],
    "female": ["female", "woman", "women", "girl", "lady"],
}

POSE_ALIASES = {
    "frontal": ["frontal", "front", "forward", "straight on"],
    "three_quarter": ["three quarter", "three-quarter", "three quarter view", "3/4"],
    "profile": ["profile", "side profile", "side view"],
}

QUALITY_ALIASES = {
    "high": ["high quality", "best quality", "sharp", "crisp", "clear"],
    "low": ["low quality", "blurry", "blurred", "soft focus"],
}


def _bounded_age(value: int) -> Optional[int]:
    if 0 <= value <= 120:
        return value
    return None


def _set_min_max(filters: Dict[str, int], min_age: Optional[int], max_age: Optional[int]) -> None:
    if min_age is not None:
        filters["min_age"] = min_age
    if max_age is not None:
        filters["max_age"] = max_age
    if "min_age" in filters and "max_age" in filters:
        if filters["min_age"] > filters["max_age"]:
            filters["min_age"], filters["max_age"] = filters["max_age"], filters["min_age"]


def _first_match(text: str, phrases: List[str]) -> Optional[int]:
    best_idx: Optional[int] = None
    for phrase in phrases:
        match = re.search(rf"\b{re.escape(phrase)}\b", text)
        if match:
            if best_idx is None or match.start() < best_idx:
                best_idx = match.start()
    return best_idx


def parse_face_attribute_query(query: str) -> Tuple[Dict[str, object], List[str]]:
    """
    Parse a natural language query into face attribute filters.

    Returns (filters, warnings).
    """
    text = query.strip().lower()
    filters: Dict[str, object] = {}
    warnings: List[str] = []

    # Age ranges
    range_patterns = [
        r"between\s+(\d{1,3})\s+and\s+(\d{1,3})",
        r"(\d{1,3})\s*(?:-|to)\s*(\d{1,3})\s*(?:years?|yrs?)",
        r"age\s*(\d{1,3})\s*(?:-|to)\s*(\d{1,3})",
    ]
    for pattern in range_patterns:
        match = re.search(pattern, text)
        if match:
            min_age = _bounded_age(int(match.group(1)))
            max_age = _bounded_age(int(match.group(2)))
            _set_min_max(filters, min_age, max_age)
            break

    if "min_age" not in filters and "max_age" not in filters:
        exact_match = re.search(r"\b(?:age|aged)\s*(\d{1,3})\b", text)
        if exact_match:
            value = _bounded_age(int(exact_match.group(1)))
            if value is not None:
                _set_min_max(filters, value, value)

    min_patterns = [
        r"\b(?:over|older than|at least|greater than)\s*(\d{1,3})\b",
        r"\bage\s*>=\s*(\d{1,3})\b",
    ]
    for pattern in min_patterns:
        match = re.search(pattern, text)
        if match:
            value = _bounded_age(int(match.group(1)))
            if value is not None:
                _set_min_max(filters, value, filters.get("max_age"))
            break

    max_patterns = [
        r"\b(?:under|younger than|at most|less than)\s*(\d{1,3})\b",
        r"\bage\s*<=\s*(\d{1,3})\b",
    ]
    for pattern in max_patterns:
        match = re.search(pattern, text)
        if match:
            value = _bounded_age(int(match.group(1)))
            if value is not None:
                _set_min_max(filters, filters.get("min_age"), value)
            break

    # Age keywords
    if re.search(r"\b(child|kid|kids|children)\b", text):
        current_max = filters.get("max_age")
        suggested = 12
        if current_max is None or suggested < current_max:
            _set_min_max(filters, filters.get("min_age"), suggested)
    if re.search(r"\b(teen|teenager|teens)\b", text):
        _set_min_max(filters, 13, 19)
    if re.search(r"\b(adult|adults)\b", text):
        _set_min_max(filters, 20, filters.get("max_age"))
    if re.search(r"\b(senior|elderly)\b", text):
        _set_min_max(filters, 60, filters.get("max_age"))

    # Emotion parsing
    emotions: List[str] = []
    for emotion, aliases in EMOTION_ALIASES.items():
        if _first_match(text, aliases) is not None:
            emotions.append(emotion)
    if emotions:
        filters["emotions"] = sorted(set(emotions))

    # Gender parsing
    gender_hits = []
    for gender, aliases in GENDER_ALIASES.items():
        if _first_match(text, aliases) is not None:
            gender_hits.append(gender)
    if len(gender_hits) == 1:
        filters["gender"] = gender_hits[0]
    elif len(gender_hits) > 1:
        warnings.append("Multiple gender terms found; gender filter skipped.")

    # Pose parsing (use earliest match)
    pose_matches = []
    for pose, aliases in POSE_ALIASES.items():
        idx = _first_match(text, aliases)
        if idx is not None:
            pose_matches.append((idx, pose))
    if pose_matches:
        pose_matches.sort(key=lambda item: item[0])
        filters["pose_type"] = pose_matches[0][1]

    # Quality hints
    if _first_match(text, QUALITY_ALIASES["high"]) is not None:
        filters["min_quality"] = 0.8
    if _first_match(text, QUALITY_ALIASES["low"]) is not None:
        warnings.append("Low-quality filters are not supported yet.")

    return filters, warnings
