"""EmbeddingGemma 2 image+text embeddings via Apple MLX.

The fast path of the image-embedding fallback chain:

    eg2_mlx (default, ~160 img/s on Apple Silicon) → CLIP via sentence-transformers

Rationale (experiments/eg2_mlx_benchmark_2026-10-20.md and
experiments/caption_to_image_retrieval_2026-10-20.md): EG2 has the best
measured top-1 precision of the candidate image embedders, and the MLX
runtime removes the throughput blocker of the transformers path (1.6-3 img/s
→ ~155-166 img/s, embeddings verified identical: wolf cosine 0.759 MLX vs
0.758 ST). Dependencies are optional by design: `pip install mlx mlx-vlm`
plus torchvision; when anything is missing, callers fall back to CLIP.

Query prompt follows the model card ("task: search result | query: ...") so
text queries and image embeddings live in the same space as the
sentence-transformers path produces for documents.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, List, Optional

from server.config import settings

logger = logging.getLogger(__name__)

QUERY_PREFIX = "task: search result | query: "
_DIM = 768


class Eg2MlxBackend:
    """EmbeddingGemma 2 (bf16 MLX conversion) image+text embedder."""

    def __init__(self, model_id: Optional[str] = None):
        self.model_id = model_id or settings.EG2_MLX_MODEL
        # Stamp name shown in vector-store model stamps and logs.
        self.model_name = "embeddinggemma-2@mlx-bf16"
        self._lock = threading.Lock()
        self._model: Any = None
        self._processor: Any = None
        self._tokenizer: Any = None

    @staticmethod
    def available() -> bool:
        """True when mlx and mlx_vlm are importable (weights download lazily)."""
        try:
            import mlx.core  # noqa: F401
            import mlx_vlm  # noqa: F401

            return True
        except ImportError:
            return False

    def _ensure(self):
        if self._model is None:
            from mlx_vlm import load
            from transformers import AutoTokenizer

            logger.info("Loading EG2-MLX embedder: %s", self.model_id)
            self._model, self._processor = load(self.model_id)
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        return self._model

    def _normalize(self, embeds) -> List[List[float]]:
        import mlx.core as mx

        embeds = embeds / mx.linalg.norm(embeds, axis=-1, keepdims=True)
        return embeds.astype(mx.float32).tolist()

    def encode_images(self, images: List[Any]) -> List[List[float]]:
        """Embed PIL images; one normalized 768-d vector per image.

        Per-image calls only: the model's processor JOINTS a multi-image
        batch into a single embedding (verified: 4 images → text_embeds
        (1, 768)), so batching here would silently produce one vector for N
        photos. Per-image throughput measured ~112 img/s on M-series (MLX
        forward ~9 ms) — batching is unnecessary.
        """
        model = self._ensure()
        out: List[List[float]] = []
        with self._lock:
            for image in images:
                inputs = self._processor(images=[image], return_tensors="np")
                result = model(**{k: mx_array(v) for k, v in inputs.items()})
                out.extend(self._normalize(result.text_embeds))
        return out

    def embed_query(self, text: str) -> List[float]:
        """Embed a search query with the model card's query task prefix."""
        model = self._ensure()
        inputs = self._tokenizer([QUERY_PREFIX + text], padding=True, return_tensors="np")
        with self._lock:
            result = model(**{k: mx_array(v) for k, v in inputs.items()})
        return self._normalize(result.text_embeds)[0]

    @property
    def dimension(self) -> int:
        return _DIM


def mx_array(value):
    import mlx.core as mx

    return mx.array(value)
