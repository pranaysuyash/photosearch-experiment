"""Tests for src/intent_recognition.py — regression coverage for the
word-boundary, no-signal, and date-pattern fixes (2026-10-13).

Root causes fixed (each was verified by direct behavioral check before the fix):
- substring keyword match ("parking" hit the "park" location keyword)
- all-zero scores fell through to "camera" (first dict key) instead of "generic"
- bare years and month names were invisible to the date intent
"""

import pytest

from src.intent_recognition import IntentDetector


@pytest.fixture(scope="module")
def detector() -> IntentDetector:
    return IntentDetector()


class TestNoSignalFallback:
    def test_unmatched_query_is_generic_not_camera(self, detector):
        # Before the fix this returned "camera" via first-dict-key bias in max().
        result = detector.detect_intent("zzz qwerty florb")
        assert result["primary_intent"] == "generic"
        assert result["confidence"] == 0.0

    def test_no_signal_badges_still_render(self, detector):
        result = detector.detect_intent("zzz qwerty florb")
        assert result["badges"][0]["intent"] == "generic"


class TestWordBoundaryMatching:
    def test_parking_is_not_location(self, detector):
        # "parking" contains "park"; word-boundary matching must not fire.
        result = detector.detect_intent("parking garage")
        assert result["primary_intent"] == "generic"

    def test_word_within_larger_word_does_not_score(self, detector):
        # "son" (people keyword) must not match inside "Madison".
        result = detector.detect_intent("Madison avenue shops")
        assert result["primary_intent"] != "people"

    def test_clear_people_query_still_matches(self, detector):
        result = detector.detect_intent("family portrait at the park")
        assert result["primary_intent"] == "people"


class TestDatePatterns:
    def test_bare_year_is_date(self, detector):
        # Before the fix this fell into the no-signal camera fallback.
        result = detector.detect_intent("summer 2023")
        assert result["primary_intent"] == "date"

    def test_month_name_is_date(self, detector):
        result = detector.detect_intent("photos from December 2023")
        assert result["primary_intent"] == "date"

    def test_model_number_is_not_date(self, detector):
        # "15" must not satisfy the bare-year pattern.
        result = detector.detect_intent("photos taken with iPhone 15 Pro at night")
        assert result["primary_intent"] == "camera"


class TestFamilyRelationKeywords:
    @pytest.mark.parametrize(
        "query",
        [
            "photos of my daughter at school",
            "grandma smiling for the portrait",
            "wife and husband at dinner",
        ],
    )
    def test_relation_words_route_to_people(self, detector, query):
        result = detector.detect_intent(query)
        assert result["primary_intent"] == "people"

    def test_camera_double_count_removed(self, detector):
        # The camera intent's pattern list duplicated its keywords, scoring the
        # word "camera" at 2.75 and biasing camera over everything. "grandma
        # smiling at the camera" is now a 1.25/1.25 tie instead of a camera
        # rout; the tie remains deterministic first-key behavior, documented
        # here so the residual limit is visible.
        result = detector.detect_intent("grandma smiling at the camera")
        assert result["primary_intent"] in {"camera", "people"}
        assert result["confidence"] == pytest.approx(0.5)


class TestExistingBehaviorPreserved:
    def test_docstring_example(self, detector):
        result = detector.detect_intent("Canon camera beach vacation")
        assert result["primary_intent"] == "camera"
        assert "location" in result["secondary_intents"]

    def test_public_delegates_match_private(self, detector):
        assert detector.generate_suggestions("camera", "canon shots") == detector._generate_suggestions(
            "camera", "canon shots"
        )
        assert detector.generate_badges("people", ["event"]) == detector._generate_badges("people", ["event"])

    def test_empty_query_shape(self, detector):
        result = detector.detect_intent("")
        assert result["primary_intent"] == "generic"
        assert result["confidence"] == 0.0
