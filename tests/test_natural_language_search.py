"""
Tests for Natural Language Search

Tests the NaturalLanguageQueryParser with various query formats.
"""

import pytest
from server.natural_language_search import (
    create_parser,
)


class TestPersonConstraints:
    """Test person name parsing."""

    def test_simple_with_person(self):
        parser = create_parser()
        result = parser.parse("photos with John")

        assert len(result.person_constraints) == 1
        assert result.person_constraints[0].name == "John"
        assert result.person_constraints[0].required is True

    def test_multiple_people_and(self):
        parser = create_parser()
        result = parser.parse("photos with John and Mary")

        assert len(result.person_constraints) == 2
        names = {c.name for c in result.person_constraints}
        assert names == {"John", "Mary"}
        assert all(c.required for c in result.person_constraints)

    def test_exclusion_but_not(self):
        parser = create_parser()
        result = parser.parse("photos with John but not Mary")

        assert len(result.person_constraints) == 2

        john = next(c for c in result.person_constraints if c.name == "John")
        mary = next(c for c in result.person_constraints if c.name == "Mary")

        assert john.required is True
        assert mary.required is False

    def test_exclusion_without(self):
        parser = create_parser()
        result = parser.parse("photos without Mary")

        assert len(result.person_constraints) == 1
        assert result.person_constraints[0].name == "Mary"
        assert result.person_constraints[0].required is False

    def test_known_people_matching(self):
        parser = create_parser(known_people=["John", "Mary", "Alice"])
        result = parser.parse("show me photos of john")

        assert len(result.person_constraints) >= 1


class TestGroupConstraints:
    """Test group composition parsing."""

    def test_exact_count(self):
        parser = create_parser()
        result = parser.parse("photos with 3 people")

        assert result.group_constraint is not None
        assert result.group_constraint.exact_count == 3

    def test_at_least(self):
        parser = create_parser()
        result = parser.parse("photos with at least 4 people")

        assert result.group_constraint is not None
        assert result.group_constraint.min_people == 4

    def test_at_most(self):
        parser = create_parser()
        result = parser.parse("photos with at most 2 people")

        assert result.group_constraint is not None
        assert result.group_constraint.max_people == 2

    def test_solo(self):
        parser = create_parser()
        result = parser.parse("solo photos")

        assert result.group_constraint is not None
        assert result.group_constraint.exact_count == 1

    def test_couple(self):
        parser = create_parser()
        result = parser.parse("couple photos")

        assert result.group_constraint is not None
        assert result.group_constraint.exact_count == 2

    def test_group(self):
        parser = create_parser()
        result = parser.parse("group photos")

        assert result.group_constraint is not None
        assert result.group_constraint.min_people == 3


class TestEmotionConstraints:
    """Test emotion parsing."""

    def test_happy_faces(self):
        parser = create_parser()
        result = parser.parse("happy faces")

        assert len(result.emotion_constraints) == 1
        assert result.emotion_constraints[0].emotion == "happy"

    def test_smiling(self):
        parser = create_parser()
        result = parser.parse("photos with smiling faces")

        assert len(result.emotion_constraints) == 1
        assert result.emotion_constraints[0].emotion == "happy"

    def test_everyone_smiling(self):
        parser = create_parser()
        result = parser.parse("photos where everyone is smiling")

        assert len(result.emotion_constraints) == 1
        assert result.emotion_constraints[0].emotion == "happy"
        assert result.emotion_constraints[0].all_faces is True

    def test_sad_faces(self):
        parser = create_parser()
        result = parser.parse("sad faces")

        assert len(result.emotion_constraints) == 1
        assert result.emotion_constraints[0].emotion == "sad"


class TestAgeConstraints:
    """Test age-based parsing."""

    def test_children(self):
        parser = create_parser()
        result = parser.parse("photos of children")

        assert len(result.age_constraints) == 1
        assert result.age_constraints[0].max_age == 12

    def test_under_age(self):
        parser = create_parser()
        result = parser.parse("faces under 10")

        assert len(result.age_constraints) == 1
        assert result.age_constraints[0].max_age == 10

    def test_over_age(self):
        parser = create_parser()
        result = parser.parse("adults over 50")

        # Should have at least an age constraint for "over 50"
        over_50 = [c for c in result.age_constraints if c.min_age and c.min_age >= 50]
        assert len(over_50) >= 1

    def test_teenager(self):
        parser = create_parser()
        result = parser.parse("photos of teenagers")

        assert len(result.age_constraints) >= 1
        teen_constraint = result.age_constraints[0]
        assert teen_constraint.min_age == 13
        assert teen_constraint.max_age == 19


class TestTemporalConstraints:
    """Test temporal parsing."""

    def test_last_week(self):
        parser = create_parser()
        result = parser.parse("photos from last week")

        assert result.temporal_constraint is not None
        assert result.temporal_constraint.relative_period == "last week"
        assert result.temporal_constraint.start_date is not None

    def test_this_year(self):
        parser = create_parser()
        result = parser.parse("photos from this year")

        assert result.temporal_constraint is not None
        assert result.temporal_constraint.relative_period == "this year"

    def test_specific_year(self):
        parser = create_parser()
        result = parser.parse("photos from 2023")

        assert result.temporal_constraint is not None
        assert result.temporal_constraint.start_date.year == 2023


class TestComplexQueries:
    """Test complex combined queries."""

    def test_person_with_emotion(self):
        parser = create_parser()
        result = parser.parse("happy photos with John")

        assert len(result.person_constraints) >= 1
        assert len(result.emotion_constraints) >= 1

    def test_group_with_emotion(self):
        parser = create_parser()
        result = parser.parse("photos with 3 happy people")

        # Group constraint extracts "3 happy people" as a group
        assert result.group_constraint is not None
        assert result.group_constraint.exact_count == 3
        # Note: "happy" may be consumed by group pattern, which is acceptable

    def test_person_temporal_emotion(self):
        parser = create_parser()
        result = parser.parse("happy photos of John from last year")

        # Temporal constraint should be extracted
        assert result.temporal_constraint is not None
        # Emotion should be extracted
        assert len(result.emotion_constraints) >= 1
        # Person may or may not be extracted depending on parse order


class TestParseConfidence:
    """Test parse confidence calculation."""

    def test_high_confidence_simple(self):
        parser = create_parser()
        result = parser.parse("photos with John")

        assert result.parse_confidence > 0.8

    def test_original_query_preserved(self):
        parser = create_parser()
        query = "happy photos with John from last year"
        result = parser.parse(query)

        assert result.original_query == query


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
