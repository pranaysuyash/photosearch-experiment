"""Background image-quality space (EG2) + idle-gated builder.

Architecture (operator-directed, 2026-10-20): the INTERACTIVE image space
stays fast (CLIP, ~276 img/s); a second LanceDB table (`photos_quality`)
holds EmbeddingGemma-2 image embeddings — the best measured top-1 precision
(experiments/caption_to_image_retrieval_2026-10-20.md) but only ~3-5 img/s
on this Mac (vision-tower bound; MLX and sentence-transformers runtimes are
equally slow once MLX's lazy evaluation is forced). A background builder
fills the quality space only while the app is idle (no API activity for
IMAGE_QUALITY_IDLE_SECONDS); /search/semantic reranks its candidates through
the quality space once coverage is complete.

Honest-measurement notes baked into this module's history: MLX is lazy —
any benchmark must force evaluation (mx.eval / tolist) or it times graph
construction (the source of a bogus 160 img/s claim); and the model's
processor JOINS a multi-image batch into one embedding (4 images →
text_embeds (1, 768)), so image encoding is per-image by necessity.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, List, Optional

from server.config import settings
from server.lancedb_store import LanceDBStore

logger = logging.getLogger(__name__)


class QualityEmbedder:
    """EG2 image+query embedder; resolves eg2_mlx → eg2_st (one space)."""

    def __init__(self, backend: Optional[str] = None):
        self._backend_name = backend or settings.IMAGE_QUALITY_BACKEND
        self._mlx: Optional[Any] = None
        self._st: Optional[Any] = None
        self._resolved = False
        self.model_name = "unresolved"
        self.dimension = 768

    def available(self) -> bool:
        if self._backend_name == "off":
            return False
        self._resolve()
        return self.model_name != "unresolved"

    def _resolve(self):
        if self._resolved:
            return
        self._resolved = True

        if self._backend_name in ("auto", "eg2_mlx"):
            try:
                from server.eg2_mlx_backend import Eg2MlxBackend

                if Eg2MlxBackend.available():
                    self._mlx = Eg2MlxBackend(settings.EG2_MLX_MODEL)
                    self.model_name = self._mlx.model_name
                    self.dimension = self._mlx.dimension
                    return
            except Exception as e:
                logger.warning("EG2-MLX quality backend unavailable: %s", e)

        if self._backend_name in ("auto", "eg2_st"):
            try:
                from sentence_transformers import SentenceTransformer

                self._st = SentenceTransformer(settings.IMAGE_QUALITY_MODEL_ST)
                self.model_name = settings.IMAGE_QUALITY_MODEL_ST
                self.dimension = int(self._st.get_sentence_embedding_dimension())
            except Exception as e:
                logger.warning("EG2-ST quality backend unavailable: %s", e)

    def encode_images(self, images) -> List[List[float]]:
        self._resolve()
        if self._mlx is not None:
            return self._mlx.encode_images(images)
        if self._st is not None:
            return self._st.encode(images, normalize_embeddings=True).tolist()
        raise RuntimeError("no quality embedder available")

    def embed_query(self, text: str) -> List[float]:
        self._resolve()
        if self._mlx is not None:
            return self._mlx.embed_query(text)
        if self._st is not None:
            prompts = getattr(self._st, "prompts", None) or {}
            if "query" in prompts:
                return self._st.encode([text], prompt_name="query", normalize_embeddings=True)[0].tolist()
            return self._st.encode([text], normalize_embeddings=True)[0].tolist()
        raise RuntimeError("no quality embedder available")


class PhotoQualityIndex(LanceDBStore):
    """EG2 image vectors for photos already indexed in the fast space."""

    def __init__(self, embedder: Optional[QualityEmbedder] = None):
        super().__init__(table_name="photos_quality")
        self.embedder = embedder or QualityEmbedder()

    def index_images(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Embed and store {path, image} records. Returns {indexed, errors}."""
        if not records or not self.embedder.available():
            return {"indexed": 0, "errors": 0}
        indexed = errors = 0
        for record in records:
            path = record["path"]
            try:
                vector = self.embedder.encode_images([record["image"]])[0]
                self.delete([path])
                self.add(
                    path,
                    vector,
                    {
                        "path": path,
                        "filename": record.get("filename", ""),
                        "embedding_model": self.embedder.model_name,
                        "dim": len(vector),
                        "indexed_at": time.time(),
                    },
                )
                indexed += 1
            except Exception as e:
                logger.warning("Quality index failed for %s: %s", path, e)
                errors += 1
        try:
            self.set_index_model(self.embedder.model_name, self.embedder.dimension)
        except Exception as e:
            logger.warning(f"Quality index stamp failed: {e}")
        return {"indexed": indexed, "errors": errors}

    def stored_paths(self) -> set:
        return self.get_all_ids()

    def pending(self, fast_ids: set) -> List[str]:
        """Fast-space ids not yet in the quality space."""
        return sorted(fast_ids - self.stored_paths())

    def coverage(self, paths: List[str]) -> float:
        if not paths:
            return 1.0
        stored = self.stored_paths()
        return sum(1 for p in paths if p in stored) / len(paths)

    def rerank(self, query_vector: List[float], paths: List[str]) -> Dict[str, float]:
        """EG2 similarity for each stored candidate path; missing → absent."""
        if not paths or self.table is None:
            return {}
        try:
            rows = self.table.search().limit(1_000_000).to_list()
        except Exception as e:
            logger.warning(f"Quality rerank fetch failed: {e}")
            return {}
        wanted = set(paths)
        by_path = {r["id"]: r["vector"] for r in rows if r["id"] in wanted}

        def cosine(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            na = sum(x * x for x in a) ** 0.5 or 1.0
            nb = sum(x * x for x in b) ** 0.5 or 1.0
            return dot / (na * nb)

        return {p: cosine(query_vector, v) for p, v in by_path.items()}


class QualityIndexBuilder:
    """Idle-gated background loop filling the quality space."""

    def __init__(self, quality_index: PhotoQualityIndex, vector_store, image_loader):
        self.quality_index = quality_index
        self.vector_store = vector_store
        self.image_loader = image_loader  # callable path → PIL image
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.last_batch_stats: Dict[str, Any] = {}
        self.running = False

    def status(self) -> Dict[str, Any]:
        try:
            fast_count = len(self.vector_store.get_all_ids())
            done = self.quality_index.get_count()
            return {
                "running": self.running,
                "backend": self.quality_index.embedder.model_name,
                "available": self.quality_index.embedder.available(),
                "fast_space_images": fast_count,
                "quality_space_images": done,
                "pending": max(fast_count - done, 0),
                "last_batch": self.last_batch_stats,
                "idle_seconds": settings.IMAGE_QUALITY_IDLE_SECONDS,
            }
        except Exception as e:
            return {"running": self.running, "error": str(e)[:160]}

    def _idle(self) -> bool:
        from server.core.state import activity_clock

        return activity_clock.seconds_since_activity() >= settings.IMAGE_QUALITY_IDLE_SECONDS

    def build_batch(self, batch_size: Optional[int] = None) -> Dict[str, Any]:
        """Embed one batch of pending images. Public for tests and manual runs."""
        batch_size = batch_size or settings.IMAGE_QUALITY_BATCH_SIZE
        fast_ids = self.vector_store.get_all_ids()
        pending = self.quality_index.pending(fast_ids)[:batch_size]
        records = []
        for path in pending:
            try:
                records.append({"path": path, "image": self.image_loader(path), "filename": path.rsplit("/", 1)[-1]})
            except Exception as e:
                logger.warning("Quality builder skipped %s: %s", path, e)
        stats = self.quality_index.index_images(records)
        self.last_batch_stats = {**stats, "at": time.time()}
        return self.last_batch_stats

    def run_loop(self):
        self.running = True
        try:
            while not self.stop_event.is_set():
                if self._idle():
                    stats = self.build_batch()
                    # Yield quickly when idle work remains; sleep when idle
                    # with nothing pending, or when the user came back.
                    if stats.get("indexed", 0) == 0 and not self._idle():
                        continue
                    self.stop_event.wait(2.0 if stats.get("indexed") else 15.0)
                else:
                    self.stop_event.wait(5.0)
        finally:
            self.running = False

    def start(self):
        if self.running:
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self.run_loop, daemon=True, name="quality-index-builder")
        self.thread.start()

    def stop(self):
        self.stop_event.set()
