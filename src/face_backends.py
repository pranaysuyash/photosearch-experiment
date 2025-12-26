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
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import requests

from src.insightface_compat import patch_insightface_deprecations

logger = logging.getLogger(__name__)


@dataclass
class FaceBackendConfig:
    models_dir: Path

    # Comma-separated preference list, e.g. "insightface,mediapipe,yolo"
    preferred_backends: Sequence[str]

    # Ultralytics backend options
    yolo_weights_path: Optional[Path] = None

    # Remote API backend options
    remote_detect_url: Optional[str] = None
    remote_detect_api_key: Optional[str] = None
    remote_detect_timeout: float = 10.0
    remote_detect_embeddings: bool = False


class FaceBackend:
    """Base interface for a face detection backend."""

    name: str = "base"
    supports_embeddings: bool = False

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
    supports_embeddings = True

    def __init__(self, models_dir: Path, providers: Optional[List[str]] = None):
        self._models_dir = models_dir
        self._providers = providers
        self._analyzer: Optional[Any] = None

    def is_available(self) -> bool:
        try:
            import cv2  # noqa: F401
        except Exception:
            return False
        return True

    def load(self) -> None:
        if self._analyzer is not None:
            return

        from insightface.app import FaceAnalysis  # type: ignore[import-untyped]

        patch_insightface_deprecations()

        self._models_dir.mkdir(parents=True, exist_ok=True)

        # buffalo_l includes detection + recognition (embeddings)
        analyzer = FaceAnalysis(
            name="buffalo_l",
            root=str(self._models_dir),
            providers=self._providers or ["CPUExecutionProvider"],
        )
        # ctx_id=-1 => first available device
        analyzer.prepare(ctx_id=-1, det_thresh=0.5)
        self._analyzer = analyzer

    def detect_bgr(self, img_bgr: np.ndarray) -> List[Dict]:
        if self._analyzer is None:
            self.load()

        analyzer = self._analyzer
        if analyzer is None:
            raise RuntimeError("InsightFace backend failed to initialize")

        faces = analyzer.get(img_bgr)
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
        self._detector: Optional[Any] = None

    def is_available(self) -> bool:
        try:
            pass  # type: ignore[import-not-found]
        except Exception:
            return False
        return True

    def load(self) -> None:
        if self._detector is not None:
            return

        import mediapipe as mp  # type: ignore[import-not-found]

        # model_selection=1 generally favors more accurate model
        self._detector = mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)

    def detect_bgr(self, img_bgr: np.ndarray) -> List[Dict]:
        if self._detector is None:
            self.load()

        detector = self._detector
        if detector is None:
            raise RuntimeError("MediaPipe backend failed to initialize")

        # MediaPipe expects RGB
        img_rgb = img_bgr[:, :, ::-1]
        h, w = img_rgb.shape[:2]

        res = detector.process(img_rgb)
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
        self._model: Optional[Any] = None

    def is_available(self) -> bool:
        try:
            pass  # type: ignore[import-not-found]
        except Exception:
            return False
        return self._weights_path.exists()

    def load(self) -> None:
        if self._model is not None:
            return

        from ultralytics import YOLO  # type: ignore[import-not-found]

        self._model = YOLO(str(self._weights_path))

    def detect_bgr(self, img_bgr: np.ndarray) -> List[Dict]:
        if self._model is None:
            self.load()

        model = self._model
        if model is None:
            raise RuntimeError("YOLO backend failed to initialize")

        # Ultralytics can accept numpy arrays (BGR is typically fine)
        preds = model.predict(img_bgr, verbose=False)
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


class RemoteApiBackend(FaceBackend):
    name = "remote"

    def __init__(
        self,
        url: str,
        api_key: Optional[str] = None,
        timeout: float = 10.0,
        provides_embeddings: bool = False,
    ):
        self._url = url
        self._api_key = api_key
        self._timeout = timeout
        self.supports_embeddings = provides_embeddings

    def is_available(self) -> bool:
        return bool(self._url)

    def detect_bgr(self, img_bgr: np.ndarray) -> List[Dict]:
        if not self._url:
            return []

        from PIL import Image
        import base64
        import io

        image = Image.fromarray(img_bgr[:, :, ::-1])
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=95)
        payload = {"image_b64": base64.b64encode(buffer.getvalue()).decode("ascii")}

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        response = requests.post(
            self._url,
            json=payload,
            headers=headers,
            timeout=self._timeout,
        )
        response.raise_for_status()
        data = response.json()
        faces = data.get("faces", [])
        if not isinstance(faces, list):
            return []

        results: List[Dict] = []
        for face in faces:
            if not isinstance(face, dict):
                continue
            bbox = face.get("bounding_box")
            if not isinstance(bbox, list) or len(bbox) != 4:
                continue
            results.append(
                {
                    "bounding_box": bbox,
                    "confidence": float(face.get("confidence", 0.0)),
                    "embedding": face.get("embedding"),
                    "embedding_version": face.get("embedding_version"),
                }
            )
        return results


def load_face_backend(
    config: FaceBackendConfig, insightface_providers: Optional[List[str]] = None
) -> Optional[FaceBackend]:
    """Pick the first available backend from the preference list."""
    for name in config.preferred_backends:
        n = name.strip().lower()
        if not n:
            continue

        if n == "insightface":
            backend: FaceBackend = InsightFaceBackend(models_dir=config.models_dir, providers=insightface_providers)
        elif n == "mediapipe":
            backend = MediaPipeBackend()
        elif n in {"yolo", "ultralytics"}:
            if not config.yolo_weights_path:
                logger.info("YOLO backend requested but FACE_YOLO_WEIGHTS is not set")
                continue
            backend = UltralyticsYoloBackend(weights_path=config.yolo_weights_path)
        elif n in {"remote", "api", "http"}:
            if not config.remote_detect_url:
                logger.info("Remote backend requested but FACE_REMOTE_DETECT_URL is not set")
                continue
            backend = RemoteApiBackend(
                url=config.remote_detect_url,
                api_key=config.remote_detect_api_key,
                timeout=config.remote_detect_timeout,
                provides_embeddings=config.remote_detect_embeddings,
            )
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
