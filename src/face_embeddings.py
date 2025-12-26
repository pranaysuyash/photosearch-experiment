from __future__ import annotations

import base64
import io
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

import numpy as np
import requests
from PIL import Image

from src.insightface_compat import patch_insightface_deprecations


@dataclass
class FaceEmbeddingBackendConfig:
    models_dir: Path
    preferred_backends: Sequence[str]
    insightface_providers: Optional[List[str]] = None
    remote_url: Optional[str] = None
    remote_api_key: Optional[str] = None
    remote_timeout: float = 10.0
    clip_model: str = "clip-ViT-B-32"


class FaceEmbeddingBackend:
    name: str = "base"
    embedding_version: Optional[str] = None

    def is_available(self) -> bool:
        raise NotImplementedError

    def load(self) -> None:
        return

    def embed_bgr(self, img_bgr: np.ndarray, bbox: Optional[List[int]]) -> Optional[np.ndarray]:
        raise NotImplementedError


def _crop_face_bgr(img_bgr: np.ndarray, bbox: Optional[List[int]], padding_ratio: float = 0.2) -> Optional[np.ndarray]:
    if bbox is None or len(bbox) != 4:
        return img_bgr

    x, y, w, h = bbox
    if w <= 0 or h <= 0:
        return None

    pad = int(max(w, h) * padding_ratio)
    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(img_bgr.shape[1], x + w + pad)
    y2 = min(img_bgr.shape[0], y + h + pad)

    if x2 <= x1 or y2 <= y1:
        return None

    return img_bgr[y1:y2, x1:x2]


class InsightFaceEmbeddingBackend(FaceEmbeddingBackend):
    name = "insightface"

    def __init__(
        self,
        models_dir: Path,
        providers: Optional[List[str]] = None,
        analyzer: Optional[object] = None,
    ):
        self._models_dir = models_dir
        self._providers = providers or ["CPUExecutionProvider"]
        self._analyzer = analyzer
        self.embedding_version = "insightface-buffalo_l"

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

        from insightface.app import FaceAnalysis  # type: ignore[import-untyped]

        patch_insightface_deprecations()
        self._models_dir.mkdir(parents=True, exist_ok=True)
        analyzer = FaceAnalysis(
            name="buffalo_l",
            root=str(self._models_dir),
            providers=self._providers,
        )
        analyzer.prepare(ctx_id=-1, det_thresh=0.5)
        self._analyzer = analyzer

    def embed_bgr(self, img_bgr: np.ndarray, bbox: Optional[List[int]]) -> Optional[np.ndarray]:
        if self._analyzer is None:
            self.load()

        analyzer = self._analyzer
        if analyzer is None:
            return None

        face_crop = _crop_face_bgr(img_bgr, bbox)
        if face_crop is None:
            return None

        faces = analyzer.get(face_crop)
        if not faces:
            return None

        return faces[0].embedding


class ClipEmbeddingBackend(FaceEmbeddingBackend):
    name = "clip"

    def __init__(self, model_name: str):
        self._model_name = model_name
        self._model = None
        self.embedding_version = model_name

    def is_available(self) -> bool:
        try:
            import sentence_transformers  # noqa: F401
        except Exception:
            return False
        return True

    def load(self) -> None:
        if self._model is not None:
            return
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(self._model_name)

    def embed_bgr(self, img_bgr: np.ndarray, bbox: Optional[List[int]]) -> Optional[np.ndarray]:
        if self._model is None:
            self.load()

        model = self._model
        if model is None:
            return None

        face_crop = _crop_face_bgr(img_bgr, bbox)
        if face_crop is None:
            return None

        face_rgb = face_crop[:, :, ::-1]
        image = Image.fromarray(face_rgb)
        embedding = model.encode([image], convert_to_numpy=True, normalize_embeddings=True)[0]
        return embedding.astype(np.float32)


class RemoteEmbeddingBackend(FaceEmbeddingBackend):
    name = "remote"

    def __init__(self, url: str, api_key: Optional[str], timeout: float):
        self._url = url
        self._api_key = api_key
        self._timeout = timeout
        self.embedding_version = "remote"

    def is_available(self) -> bool:
        return bool(self._url)

    def embed_bgr(self, img_bgr: np.ndarray, bbox: Optional[List[int]]) -> Optional[np.ndarray]:
        if not self._url:
            return None

        face_crop = _crop_face_bgr(img_bgr, bbox)
        if face_crop is None:
            return None

        face_rgb = face_crop[:, :, ::-1]
        image = Image.fromarray(face_rgb)
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
        embedding = data.get("embedding")
        if embedding is None:
            return None

        version = data.get("embedding_version")
        if isinstance(version, str) and version:
            self.embedding_version = version

        return np.asarray(embedding, dtype=np.float32)


def load_embedding_backend(
    config: FaceEmbeddingBackendConfig,
    analyzer: Optional[object] = None,
) -> Optional[FaceEmbeddingBackend]:
    for name in config.preferred_backends:
        key = name.strip().lower()
        if not key:
            continue

        if key == "insightface":
            backend: FaceEmbeddingBackend = InsightFaceEmbeddingBackend(
                models_dir=config.models_dir,
                providers=config.insightface_providers,
                analyzer=analyzer,
            )
        elif key in {"clip", "sentence-transformers"}:
            backend = ClipEmbeddingBackend(config.clip_model)
        elif key in {"remote", "http"}:
            backend = RemoteEmbeddingBackend(
                url=config.remote_url or "",
                api_key=config.remote_api_key,
                timeout=config.remote_timeout,
            )
        elif key in {"none", "off", "disabled"}:
            return None
        else:
            continue

        if backend.is_available():
            try:
                backend.load()
                return backend
            except Exception:
                continue

    return None


def env_preferred_embedding_backends(default: str = "insightface,clip,remote") -> List[str]:
    raw = os.environ.get("FACE_EMBEDDING_BACKENDS", default)
    return [p.strip() for p in raw.split(",") if p.strip()]
