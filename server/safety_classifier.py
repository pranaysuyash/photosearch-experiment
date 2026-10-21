"""Sensitive-content (NSFW) image classification.

Local ViT binary classifier (default Falconsai/nsfw_image_detection, Apache-2.0,
runs via the already-required transformers dependency). Stateless by design:
:class:`SafetyClassifier` answers "is this image likely sensitive?" on demand;
persisting flags and wiring them into the privacy surface is deliberately a
separate, owner-approved step (see
docs/OSS_MODEL_INTEGRATION_IMPLEMENTATION_2026-10-19.md).

The classifier only ever returns a label and score — it never hides, blocks,
or deletes media.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from server.config import settings

logger = logging.getLogger(__name__)

NSFW_LABEL = "nsfw"
NORMAL_LABEL = "normal"
# Falconsai's model was trained/evaluated at 224x224; higher input sizes add
# latency without accuracy.
_MAX_EDGE = 1024


class SafetyClassifier:
    """On-demand sensitive-content classifier with lazy model load."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.NSFW_MODEL
        self._pipeline = None

    @property
    def enabled(self) -> bool:
        return settings.NSFW_DETECTION_ENABLED

    def is_available(self) -> bool:
        return self.enabled

    def _ensure_model(self):
        if self._pipeline is None:
            from transformers import pipeline as hf_pipeline

            logger.info("Loading safety classifier %s", self.model_name)
            self._pipeline = hf_pipeline(
                "image-classification",
                model=self.model_name,
            )
        return self._pipeline

    def classify(self, image_path: str) -> Dict[str, Any]:
        """Classify one image.

        Returns {"path", "label", "score", "is_sensitive", "model"} or an
        error dict. Never raises to the caller.
        """
        if not self.enabled:
            return {
                "error": "NSFW detection is disabled (NSFW_DETECTION_ENABLED=false)",
                "path": image_path,
            }
        try:
            from PIL import Image

            image = Image.open(image_path)
            image.thumbnail((_MAX_EDGE, _MAX_EDGE))
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")

            pipe = self._ensure_model()
            predictions = pipe(image)
            best = max(predictions, key=lambda p: p.get("score", 0.0))
            label = str(best.get("label", "")).lower()
            return {
                "path": image_path,
                "label": label,
                "score": round(float(best.get("score", 0.0)), 4),
                "is_sensitive": label == NSFW_LABEL,
                "model": self.model_name,
                "all_scores": [
                    {"label": str(p.get("label", "")), "score": round(float(p.get("score", 0.0)), 4)}
                    for p in predictions
                ],
            }
        except Exception as e:
            logger.error("Safety classification failed for %s: %s", image_path, e)
            return {"error": "Classification failed: " + str(e), "path": image_path}

    def classify_batch(self, image_paths, limit: int = 50):
        """Classify up to `limit` images, returning per-path results.

        Errors (unreadable files, model failures) are reported separately and
        do not count as classified.
        """
        results = []
        errors = []
        for i, path in enumerate(image_paths):
            if i >= limit:
                break
            result = self.classify(path)
            if result.get("error"):
                errors.append({"path": path, "error": result["error"]})
            else:
                results.append(result)
        sensitive = [r["path"] for r in results if r.get("is_sensitive")]
        return {
            "classified": len(results),
            "error_count": len(errors),
            "errors": errors[:10],
            "sensitive_count": len(sensitive),
            "results": results,
        }


_safety_classifier = None


def get_safety_classifier() -> SafetyClassifier:
    global _safety_classifier
    if _safety_classifier is None:
        _safety_classifier = SafetyClassifier()
    return _safety_classifier
