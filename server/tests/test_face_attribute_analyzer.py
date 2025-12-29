import numpy as np

from server.face_attribute_analyzer import (
    AdvancedFaceQualityAssessor,
    FaceAttributeAnalyzer,
    QualityScores,
)


def test_attribute_analyzer_deterministic_age_and_cache():
    face_crop = np.full((64, 64, 3), 120, dtype=np.uint8)
    analyzer = FaceAttributeAnalyzer(backend_preference=("heuristic",), cache_size=8)

    first = analyzer.analyze_attributes(face_crop)
    second = analyzer.analyze_attributes(face_crop)

    assert first == second  # cache hit, deterministic outputs
    assert first["age_estimate"] == second["age_estimate"]
    assert first["age_confidence"] == second["age_confidence"]
    assert 5 <= first["age_estimate"] <= 80
    assert 0.0 <= first["age_confidence"] <= 1.0


def test_quality_assessor_returns_qualityscores():
    face_crop = np.full((64, 64, 3), 150, dtype=np.uint8)
    assessor = AdvancedFaceQualityAssessor(cache_size=8)

    scores = assessor.assess(face_crop)
    assert isinstance(scores, QualityScores)
    assert 0.0 <= scores.blur_score <= 1.0
    assert 0.0 <= scores.overall_quality <= 1.0
