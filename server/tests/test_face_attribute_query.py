"""
Tests for natural language parsing of face attribute queries.
"""

from server.face_attribute_query import parse_face_attribute_query


def test_parse_age_and_emotion():
    filters, warnings = parse_face_attribute_query("happy kids under 10")
    assert filters["max_age"] == 10
    assert "happy" in filters.get("emotions", [])
    assert warnings == []


def test_parse_gender_and_pose():
    filters, warnings = parse_face_attribute_query("female profile portraits")
    assert filters["gender"] == "female"
    assert filters["pose_type"] == "profile"
    assert warnings == []


def test_parse_age_range():
    filters, warnings = parse_face_attribute_query("age 20-30")
    assert filters["min_age"] == 20
    assert filters["max_age"] == 30
    assert warnings == []
