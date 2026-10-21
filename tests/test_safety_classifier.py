"""Safety classifier tests (P3.4, stateless NSFW classification)."""

import pytest

from server.config import settings
from server.safety_classifier import SafetyClassifier


@pytest.fixture
def image_file(tmp_path):
    from PIL import Image

    p = tmp_path / "photo.png"
    Image.new("RGB", (4, 4), color=(10, 120, 200)).save(p)
    return str(p)


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setattr(settings, "NSFW_DETECTION_ENABLED", True)
    # Skip the real transformers model load; return a fake pipeline.
    classifier = SafetyClassifier(model_name="fake-nsfw-model")

    def fake_ensure_model(self):
        class FakePipe:
            def __call__(self, image):
                return [
                    {"label": "nsfw", "score": 0.93},
                    {"label": "normal", "score": 0.07},
                ]

        self._pipeline = FakePipe()
        return self._pipeline

    monkeypatch.setattr(SafetyClassifier, "_ensure_model", fake_ensure_model)
    return classifier


class TestSafetyClassifier:
    def test_disabled_by_default_reports_error_not_crash(self, image_file):
        assert settings.NSFW_DETECTION_ENABLED is False
        result = SafetyClassifier().classify(image_file)
        assert "error" in result
        assert "disabled" in result["error"]

    def test_classification_parses_top_label(self, enabled, image_file):
        result = enabled.classify(image_file)
        assert result["label"] == "nsfw"
        assert result["is_sensitive"] is True
        assert result["score"] == 0.93
        assert result["model"] == "fake-nsfw-model"
        assert len(result["all_scores"]) == 2

    def test_normal_label_not_sensitive(self, enabled, image_file, monkeypatch):
        def fake_ensure_model(self):
            class FakePipe:
                def __call__(self, image):
                    return [{"label": "normal", "score": 0.99}]

            self._pipeline = FakePipe()
            return self._pipeline

        monkeypatch.setattr(SafetyClassifier, "_ensure_model", fake_ensure_model)
        result = enabled.classify(image_file)
        assert result["is_sensitive"] is False

    def test_missing_file_returns_error(self, enabled):
        result = enabled.classify("/nonexistent/image.png")
        assert "error" in result

    def test_batch_counts_sensitive(self, enabled, image_file):
        result = enabled.classify_batch([image_file, "/nonexistent.png"], limit=10)
        assert result["classified"] == 1
        assert result["sensitive_count"] == 1
