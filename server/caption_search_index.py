"""Caption search index.

Bridges the orphaned ``photo_captions`` SQLite table into semantic search:
caption text is embedded with the same model used for image embeddings and
stored in a dedicated LanceDB table so text↔text matches (brands, book
titles, situational context that pure image embeddings miss) become
searchable. See docs/OSS_MODEL_INTEGRATION_EXPLORATION_2026-10-19.md P0.1.

Every row carries the embedding model stamp; rows stamped with a different
model than the active generator are re-embedded lazily, so switching
EMBEDDING_MODEL never silently mixes vector spaces.
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional

from server.config import settings
from server.lancedb_store import LanceDBStore

logger = logging.getLogger(__name__)


class CaptionSearchIndex(LanceDBStore):
    """LanceDB-backed vector index over photo captions (table "captions").

    Query↔caption embeddings come from a dedicated text embedder
    (settings.CAPTION_EMBEDDING_MODEL, default EmbeddingGemma-300m — measured
    at 2.2× CLIP-text MRR on real captions) with prompt-aware query/document
    encoding. When that model is unavailable (gated, no token, download
    failure) or explicitly disabled (""), the index falls back to the caller
    supplied embedding generator (CLIP) for BOTH sides — the two sides always
    share one space, whichever is active.
    """

    def __init__(self):
        super().__init__(table_name="captions")
        self._text_model = None
        self._text_model_name: Optional[str] = None
        self._text_model_failed = False

    # ------------------------------------------------------------------
    # Embedding resolution (single space guarantee)
    # ------------------------------------------------------------------

    def _resolve_text_model(self):
        """Lazy-load the dedicated caption embedder; None = use fallback."""
        if self._text_model is not None or self._text_model_failed:
            return self._text_model
        model_name = getattr(settings, "CAPTION_EMBEDDING_MODEL", "")
        if not model_name:
            self._text_model_failed = True
            return None
        try:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading caption text embedder: %s", model_name)
            self._text_model = SentenceTransformer(model_name)
            self._text_model_name = model_name
        except Exception as e:
            logger.warning(
                "Caption embedder %s unavailable (%s); falling back to the "
                "app embedding generator for the caption index.",
                model_name,
                str(e)[:120],
            )
            self._text_model_failed = True
        return self._text_model

    def _embed_documents(self, texts, embedding_generator):
        model = self._resolve_text_model()
        if model is not None:
            try:
                return model.encode(texts, prompt_name="document", normalize_embeddings=True).tolist()
            except TypeError:
                return model.encode(texts, normalize_embeddings=True).tolist()
        return [embedding_generator.generate_text_embedding(t) for t in texts]

    def embed_query(self, text: str, embedding_generator=None):
        """Embed a search query in the index's active space."""
        model = self._resolve_text_model()
        if model is not None:
            try:
                return model.encode(text, prompt_name="query", normalize_embeddings=True).tolist()
            except TypeError:
                return model.encode(text, normalize_embeddings=True).tolist()
        if embedding_generator is None:
            raise RuntimeError("caption index has no text model and no fallback generator")
        return embedding_generator.generate_text_embedding(text)

    def _active_model_name(self, embedding_generator) -> str:
        """Name of whichever embedder is actually in use (dedicated wins)."""
        if self._resolve_text_model() is not None:
            return self._text_model_name or "dedicated-text-model"
        return getattr(embedding_generator, "model_name", "unknown")

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def index_caption(
        self,
        photo_path: str,
        caption: str,
        embedding_generator: Any,
        caption_updated_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Embed and upsert a single caption.

        Returns a small status dict; never raises for missing caption text.
        """
        caption = (caption or "").strip()
        if not caption:
            return {"indexed": False, "reason": "empty caption"}
        if embedding_generator is None and self._resolve_text_model() is None:
            return {"indexed": False, "reason": "no text embedder available"}

        try:
            vector = self._embed_documents([caption], embedding_generator)[0]
        except Exception as e:
            logger.error(f"Failed to embed caption for {photo_path}: {e}")
            return {"indexed": False, "reason": f"embedding failed: {e}"}

        # Upsert: LanceDB has no native upsert, so delete-then-add by id.
        try:
            self.delete([photo_path])
        except Exception as e:
            logger.warning(f"Caption index delete-before-add failed for {photo_path}: {e}")

        metadata = {
            "path": photo_path,
            "filename": os.path.basename(photo_path),
            "caption": caption,
            "embedding_model": self._active_model_name(embedding_generator),
            "dim": len(vector),
            "caption_updated_at": caption_updated_at or "",
            "indexed_at": time.time(),
        }
        self.add(photo_path, vector, metadata)

        # Stamp on every write so the dimension guard is active even when
        # captions trickle in one at a time (idempotent meta-row upsert).
        try:
            self.set_index_model(self._active_model_name(embedding_generator), len(vector))
        except Exception as e:
            logger.warning(f"Caption index model stamp failed: {e}")
        return {"indexed": True, "path": photo_path, "dim": len(vector)}

    def drop(self, photo_path: str) -> None:
        """Remove a photo's caption vector (caption deleted or emptied)."""
        try:
            self.delete([photo_path])
        except Exception as e:
            logger.warning(f"Caption index drop failed for {photo_path}: {e}")

    def ensure_indexed(
        self,
        caption_rows: List[Dict[str, Any]],
        embedding_generator: Any,
        model_stamp: Optional[str] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Backfill/re-embed caption vectors from ``get_all_captions()`` rows.

        A row is (re)indexed when it is missing from the vector table, was
        embedded by a different model, or ``force`` is set. Caption edits are
        detected via ``caption_updated_at`` when available.
        """
        if embedding_generator is None and self._resolve_text_model() is None:
            return {"indexed": 0, "skipped": len(caption_rows), "reason": "no text embedder available"}

        active_model = model_stamp or self._active_model_name(embedding_generator)

        try:
            existing = self.get_all_records(limit=1_000_000)
        except Exception:
            existing = []
        by_path = {r.get("path"): r for r in existing}

        stats = {"indexed": 0, "skipped": 0, "errors": 0}
        for row in caption_rows:
            path = row.get("photo_path")
            caption = (row.get("caption") or "").strip()
            if not path or not caption:
                stats["skipped"] += 1
                continue

            # VLMCaptionService.get_all_captions() exposes the edit timestamp
            # as ``updated_at``; accept both spellings so caption edits are
            # detected regardless of the caller.
            row_updated = row.get("caption_updated_at") or row.get("updated_at")

            current = by_path.get(path)
            needs_index = (
                force
                or current is None
                or current.get("embedding_model") != active_model
                or (
                    row_updated
                    and current.get("caption_updated_at")
                    and str(row_updated) != str(current["caption_updated_at"])
                )
            )
            if not needs_index:
                stats["skipped"] += 1
                continue

            result = self.index_caption(path, caption, embedding_generator, caption_updated_at=row_updated)
            if result.get("indexed"):
                stats["indexed"] += 1
            else:
                stats["errors"] += 1

        try:
            if self._resolve_text_model() is not None:
                dim = len(self.embed_query("dim-probe"))
            else:
                dim = embedding_generator.embedding_dimension
            self.set_index_model(active_model, dim)
        except Exception as e:  # stamping is diagnostics, never load-bearing
            logger.warning(f"Caption index model stamp failed: {e}")
        return stats

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query_embedding: List[float],
        limit: int = 50,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Return caption matches as [{path, score, caption, embedding_model}]."""
        try:
            results = super().search(query_embedding, limit=limit)
        except Exception as e:
            logger.error(f"Caption index search failed: {e}")
            return []

        out = []
        for r in results:
            meta = r.get("metadata", {})
            if r.get("score", 0.0) < min_score:
                continue
            out.append(
                {
                    "path": meta.get("path", r.get("id")),
                    "score": r.get("score", 0.0),
                    "caption": meta.get("caption", ""),
                    "embedding_model": meta.get("embedding_model", "unknown"),
                }
            )
        return out

    def get_stats(self) -> Dict[str, Any]:
        return {
            "captions_indexed": self.get_count(),
            "index_model": self.get_index_model(),
        }


# Singleton following the lancedb_store.py convention.
_caption_index = None


def get_caption_index() -> CaptionSearchIndex:
    global _caption_index
    if _caption_index is None:
        _caption_index = CaptionSearchIndex()
    return _caption_index
