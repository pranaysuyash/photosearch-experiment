"""Face detection backend abstraction.

This module is intentionally dependency-light at import time.
Optional backends are imported lazily so the server can start without them.

Backends currently focus on *detection* (bounding boxes + confidence).
Only the InsightFace backend provides embeddings (required for clustering).

Returned detection format (dict):
- bounding_box: [x, y, w, h]
- confidence: float
- embedding: Optional[np.ndarray]
- embedding_version: Optional[str]
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class FaceBackendConfig:
    models_dir: Path

    # Comma-separated preference list, e.g. "insightface,mediapipe,yolo"
    preferred_backends: Sequence[str]

    # Ultralytics backend options
    yolo_weights_path: Optional[Path] = None


class FaceBackend:
    """Base interface for a face detection backend."""

    name: str = "base"

    def is_available(self) -> bool:
        raise NotImplementedError

    def load(self) -> None:
        """Load models/resources. Should be safe to call multiple times."""
        return

    def detect_bgr(self, img_bgr: np.ndarray) -> List[Dict]:
        """Detect faces in an OpenCV BGR image."""
        raise NotImplementedError


class InsightFaceBackend(FaceBackend):
    name = "insightface"

    def __init__(self, models_dir: Path, providers: Optional[List[str]] = None):
        self._models_dir = models_dir
        self._providers = providers
        self._analyzer = None

    def is_available(self) -> bool:
        try:
            import insightface  # noqa: F401
            import cv2  # noqa: F401
        except Exception:
            return False
        return True

    def load(self) -> None:
        if self._analyzer is not None:
            return

        from insightface.app import FaceAnalysis

        self._models_dir.mkdir(parents=True, exist_ok=True)

        # buffalo_l includes detection + recognition (embeddings)
        self._analyzer = FaceAnalysis(
            name="buffalo_l",
            root=str(self._models_dir),
            providers=self._providers or ["CPUExecutionProvider"],
        )
        # ctx_id=-1 => first available device
        self._analyzer.prepare(ctx_id=-1, det_thresh=0.5)

    def detect_bgr(self, img_bgr: np.ndarray) -> List[Dict]:
        if self._analyzer is None:
            self.load()

        faces = self._analyzer.get(img_bgr)
        results: List[Dict] = []
        for face in faces:
            x1, y1, x2, y2 = face.bbox
            results.append(
                {
                    "bounding_box": [int(x1), int(y1), int(x2 - x1), int(y2 - y1)],
                    "confidence": float(face.det_score),
                    "embedding": getattr(face, "embedding", None),
                    "embedding_version": "buffalo_l",
                }
            )
        return results


class MediaPipeBackend(FaceBackend):
    name = "mediapipe"

    def __init__(self):
        self._detector = None

    def is_available(self) -> bool:
        try:
            import mediapipe as mp  # noqa: F401
        except Exception:
            return False
        return True

    def load(self) -> None:
        if self._detector is not None:
            return

        import mediapipe as mp

        # model_selection=1 generally favors more accurate model
        self._detector = mp.solutions.face_detection.FaceDetection(
            model_selection=1, min_detection_confidence=0.5
        )

    def detect_bgr(self, img_bgr: np.ndarray) -> List[Dict]:
        if self._detector is None:
            self.load()

        # MediaPipe expects RGB
        img_rgb = img_bgr[:, :, ::-1]
        h, w = img_rgb.shape[:2]

        res = self._detector.process(img_rgb)
        if not res.detections:
            return []

        out: List[Dict] = []
        for det in res.detections:
            bb = det.location_data.relative_bounding_box
            x = int(bb.xmin * w)
            y = int(bb.ymin * h)
            bw = int(bb.width * w)
            bh = int(bb.height * h)
            out.append(
                {
                    "bounding_box": [x, y, bw, bh],
                    "confidence": float(det.score[0]) if det.score else 0.0,
                    "embedding": None,
                    "embedding_version": None,
                }
            )
        return out


class UltralyticsYoloBackend(FaceBackend):
    name = "yolo"

    def __init__(self, weights_path: Path):
        self._weights_path = weights_path
        self._model = None

    def is_available(self) -> bool:
        try:
            import ultralytics  # noqa: F401
        except Exception:
            return False
        return self._weights_path.exists()

    def load(self) -> None:
        if self._model is not None:
            return

        from ultralytics import YOLO

        self._model = YOLO(str(self._weights_path))

    def detect_bgr(self, img_bgr: np.ndarray) -> List[Dict]:
        if self._model is None:
            self.load()

        # Ultralytics can accept numpy arrays (BGR is typically fine)
        preds = self._model.predict(img_bgr, verbose=False)
        if not preds:
            return []

        p0 = preds[0]
        if getattr(p0, "boxes", None) is None or p0.boxes is None:
            return []

        boxes = p0.boxes
        xyxy = boxes.xyxy.cpu().numpy() if hasattr(boxes.xyxy, "cpu") else boxes.xyxy
        conf = boxes.conf.cpu().numpy() if hasattr(boxes.conf, "cpu") else boxes.conf

        out: List[Dict] = []
        for (x1, y1, x2, y2), c in zip(xyxy, conf):
            out.append(
                {
                    "bounding_box": [int(x1), int(y1), int(x2 - x1), int(y2 - y1)],
                    "confidence": float(c),
                    "embedding": None,
                    "embedding_version": None,
                }
            )
        return out


def load_face_backend(config: FaceBackendConfig, insightface_providers: Optional[List[str]] = None) -> Optional[FaceBackend]:
    """Pick the first available backend from the preference list."""
    for name in config.preferred_backends:
        n = name.strip().lower()
        if not n:
            continue

        if n == "insightface":
            backend: FaceBackend = InsightFaceBackend(
                models_dir=config.models_dir, providers=insightface_providers
            )
        elif n == "mediapipe":
            backend = MediaPipeBackend()
        elif n in {"yolo", "ultralytics"}:
            if not config.yolo_weights_path:
                logger.info("YOLO backend requested but FACE_YOLO_WEIGHTS is not set")
                continue
            backend = UltralyticsYoloBackend(weights_path=config.yolo_weights_path)
        else:
            logger.warning("Unknown face backend '%s'", n)
            continue

        if backend.is_available():
            try:
                backend.load()
                logger.info("Loaded face backend: %s", backend.name)
                return backend
            except Exception as e:
                logger.warning("Failed to load backend %s: %s", backend.name, e)
                continue

    return None


def env_preferred_backends(default: str = "insightface") -> List[str]:
    raw = os.environ.get("FACE_BACKENDS", default)
    return [p.strip() for p in raw.split(",") if p.strip()]
