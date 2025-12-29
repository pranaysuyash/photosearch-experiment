import numpy as np
import pytest

from src.enhanced_face_clustering import EnhancedFaceClusterer


def test_quality_weighting_penalizes_low_quality(tmp_path):
    clusterer = EnhancedFaceClusterer(db_path=str(tmp_path / "faces.db"), auto_load_models=False)

    base = np.array([[0.0, 0.2], [0.2, 0.0]], dtype=float)
    qualities = [0.95, 0.4]

    weighted = clusterer._apply_quality_weight(base, qualities, weight=0.2)

    # Factor = 1 + weight * (1 - min(0.95, 0.4)) = 1 + 0.2 * 0.6 = 1.12
    expected = 0.2 * 1.12

    assert weighted[0, 1] > base[0, 1]
    assert weighted[1, 0] > base[1, 0]
    assert weighted[0, 1] == pytest.approx(expected, rel=1e-3)
