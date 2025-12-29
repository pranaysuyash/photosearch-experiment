"""
Face Embedding Index Module

Provides an abstraction layer for face embedding similarity search.
Supports both linear search (for small collections) and FAISS (for scale).

Phase 3 Feature: Speed & Scale - Now with FAISS implementation
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Try to import FAISS, fall back gracefully if not available
try:
    import faiss

    FAISS_AVAILABLE = True
    logger.info("FAISS available for high-performance similarity search")
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS not available. Install with: pip install faiss-cpu")


@dataclass
class SearchResult:
    """Result from an embedding similarity search."""

    cluster_id: str
    similarity: float
    cluster_label: Optional[str] = None


class EmbeddingIndex(ABC):
    """
    Abstract interface for face embedding similarity search.

    Implementations:
    - LinearIndex: Simple in-memory search, O(n) per query
    - FaissIndex: Optimized for 10K+ vectors (future)
    """

    @abstractmethod
    def add_prototype(self, cluster_id: str, embedding: np.ndarray, label: Optional[str] = None) -> None:
        """Add or update a cluster prototype embedding."""
        pass

    @abstractmethod
    def remove_prototype(self, cluster_id: str) -> bool:
        """Remove a cluster prototype. Returns True if found and removed."""
        pass

    @abstractmethod
    def search(self, query_embedding: np.ndarray, k: int = 5, threshold: float = 0.0) -> List[SearchResult]:
        """
        Find k most similar cluster prototypes.

        Args:
            query_embedding: The face embedding to search for
            k: Maximum number of results to return
            threshold: Minimum similarity threshold (0-1)

        Returns:
            List of SearchResult sorted by similarity (highest first)
        """
        pass

    @abstractmethod
    def get_prototype(self, cluster_id: str) -> Optional[np.ndarray]:
        """Get the prototype embedding for a cluster."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Return number of prototypes in the index."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all prototypes from the index."""
        pass


class LinearIndex(EmbeddingIndex):
    """
    Simple linear search index for face embeddings.

    Suitable for collections up to ~10K faces.
    Uses cosine similarity (embeddings assumed to be L2-normalized).
    """

    def __init__(self):
        self._prototypes: Dict[str, np.ndarray] = {}
        self._labels: Dict[str, Optional[str]] = {}

    def add_prototype(self, cluster_id: str, embedding: np.ndarray, label: Optional[str] = None) -> None:
        """Add or update a cluster prototype embedding."""
        # Ensure L2 normalization
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        self._prototypes[cluster_id] = embedding.astype(np.float32)
        self._labels[cluster_id] = label

    def remove_prototype(self, cluster_id: str) -> bool:
        """Remove a cluster prototype."""
        if cluster_id in self._prototypes:
            del self._prototypes[cluster_id]
            del self._labels[cluster_id]
            return True
        return False

    def search(self, query_embedding: np.ndarray, k: int = 5, threshold: float = 0.0) -> List[SearchResult]:
        """Find k most similar cluster prototypes using cosine similarity."""
        if not self._prototypes:
            return []

        # Normalize query
        query = query_embedding.astype(np.float32)
        norm = np.linalg.norm(query)
        if norm > 0:
            query = query / norm

        # Calculate similarities (cosine similarity via dot product for normalized vectors)
        results = []
        for cluster_id, prototype in self._prototypes.items():
            similarity = float(np.dot(query, prototype))

            if similarity >= threshold:
                results.append(
                    SearchResult(
                        cluster_id=cluster_id,
                        similarity=similarity,
                        cluster_label=self._labels.get(cluster_id),
                    )
                )

        # Sort by similarity (highest first) and limit to k
        results.sort(key=lambda x: x.similarity, reverse=True)
        return results[:k]

    def get_prototype(self, cluster_id: str) -> Optional[np.ndarray]:
        """Get the prototype embedding for a cluster."""
        return self._prototypes.get(cluster_id)

    def count(self) -> int:
        """Return number of prototypes in the index."""
        return len(self._prototypes)

    def clear(self) -> None:
        """Clear all prototypes from the index."""
        self._prototypes.clear()
        self._labels.clear()

    def bulk_load(self, prototypes: Dict[str, Tuple[np.ndarray, Optional[str]]]) -> None:
        """
        Efficiently load multiple prototypes at once.

        Args:
            prototypes: Dict of cluster_id -> (embedding, label)
        """
        for cluster_id, (embedding, label) in prototypes.items():
            self.add_prototype(cluster_id, embedding, label)

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        return {
            "index_type": "linear",
            "num_prototypes": len(self._prototypes),
            "memory_usage_mb": sum(p.nbytes for p in self._prototypes.values()) / (1024 * 1024),
        }


class FAISSIndex(EmbeddingIndex):
    """
    FAISS-based similarity search for large face collections (10K+ faces).

    Supports both IndexFlatIP (exact search) and IndexIVFFlat (approximate, faster for very large collections).
    Provides O(log n) search performance vs O(n) for LinearIndex.

    According to .kiro/specs/advanced-face-features/design.md:
    - IndexFlatIP: Exact inner product for cosine similarity (default)
    - IndexIVFFlat: Approximate search with inverted file index for 100K+ faces
    """

    def __init__(self, dimension: int = 512, index_type: str = "IndexFlatIP", nlist: int = 100):
        """
        Initialize FAISS index.

        Args:
            dimension: Embedding dimension (default 512 for InsightFace)
            index_type: "IndexFlatIP" (exact) or "IndexIVFFlat" (approximate, faster)
            nlist: Number of clusters for IndexIVFFlat (default 100)
        """
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS not available. Install with: pip install faiss-cpu")

        self.dimension = dimension
        self.index_type = index_type
        self.nlist = nlist
        self._is_trained = False

        # Canonical in-memory store for rebuilds/removals.
        # NOTE: Prototypes are relatively small (one per cluster), so keeping
        # these in memory is acceptable and makes removal/rebuild deterministic.
        self.cluster_ids: List[str] = []  # index -> cluster_id
        self.id_to_index: Dict[str, int] = {}  # cluster_id -> index
        self.labels: Dict[str, Optional[str]] = {}  # cluster_id -> label
        self._embeddings: List[np.ndarray] = []  # index-aligned, float32 unit vectors

        # Create index based on type. For IndexIVFFlat, we start with an IndexFlatIP
        # fallback until we have enough vectors to train the IVF index.
        self._active_index_type: str = "IndexFlatIP"
        self.index = faiss.IndexFlatIP(dimension)

        if index_type == "IndexFlatIP":
            self._active_index_type = "IndexFlatIP"
        elif index_type == "IndexIVFFlat":
            # Start in flat fallback mode; upgrade once we have enough vectors.
            self._active_index_type = "IndexFlatIP"
        else:
            raise ValueError(f"Unknown index_type: {index_type}. Use 'IndexFlatIP' or 'IndexIVFFlat'")

    def _maybe_upgrade_to_ivf(self) -> None:
        """Upgrade from FlatIP fallback to IVFFlat when enough vectors exist."""
        if self.index_type != "IndexIVFFlat":
            return
        if self._active_index_type == "IndexIVFFlat":
            return
        if len(self._embeddings) < self.nlist:
            return

        embeddings_array = np.vstack(self._embeddings).astype("float32")
        quantizer = faiss.IndexFlatIP(self.dimension)
        ivf = faiss.IndexIVFFlat(quantizer, self.dimension, self.nlist)
        ivf.train(embeddings_array)
        ivf.add(embeddings_array)

        self.index = ivf
        self._active_index_type = "IndexIVFFlat"
        self._is_trained = True

    def _rebuild_index(self) -> None:
        """Rebuild the underlying FAISS index from canonical embeddings."""
        if not self._embeddings:
            self.index = faiss.IndexFlatIP(self.dimension)
            self._active_index_type = "IndexFlatIP"
            self._is_trained = False
            return

        embeddings_array = np.vstack(self._embeddings).astype("float32")

        if self.index_type == "IndexIVFFlat" and len(self._embeddings) >= self.nlist:
            quantizer = faiss.IndexFlatIP(self.dimension)
            ivf = faiss.IndexIVFFlat(quantizer, self.dimension, self.nlist)
            ivf.train(embeddings_array)
            ivf.add(embeddings_array)
            self.index = ivf
            self._active_index_type = "IndexIVFFlat"
            self._is_trained = True
        else:
            # Flat fallback (exact) for small collections or when IVF can't be trained yet.
            flat = faiss.IndexFlatIP(self.dimension)
            flat.add(embeddings_array)
            self.index = flat
            self._active_index_type = "IndexFlatIP"
            self._is_trained = False

    def add_prototype(self, cluster_id: str, embedding: np.ndarray, label: Optional[str] = None) -> None:
        """
        Add or update a cluster prototype embedding.

        For IndexIVFFlat, ensures index is trained before adding vectors.
        """
        # Remove existing prototype if it exists
        if cluster_id in self.id_to_index:
            self.remove_prototype(cluster_id)

        # Ensure L2 normalization for cosine similarity
        emb = embedding.astype(np.float32)
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm

        # Update canonical stores
        self.cluster_ids.append(cluster_id)
        self.id_to_index[cluster_id] = len(self.cluster_ids) - 1
        self.labels[cluster_id] = label
        self._embeddings.append(emb)

        # Add to current active index. If IVF was requested but not yet trained,
        # we'll be in FlatIP fallback mode until we can upgrade.
        self.index.add(emb.reshape(1, -1))
        self._maybe_upgrade_to_ivf()

    def remove_prototype(self, cluster_id: str) -> bool:
        """Remove a cluster prototype."""
        if cluster_id not in self.id_to_index:
            return False

        remove_idx = self.id_to_index[cluster_id]

        # Remove from canonical stores
        del self.cluster_ids[remove_idx]
        del self._embeddings[remove_idx]
        if cluster_id in self.labels:
            del self.labels[cluster_id]

        # Rebuild id mapping
        self.id_to_index = {cid: i for i, cid in enumerate(self.cluster_ids)}

        # Rebuild the underlying index based on requested type + available vectors
        self._rebuild_index()
        return True

    def search(self, query_embedding: np.ndarray, k: int = 5, threshold: float = 0.0) -> List[SearchResult]:
        """
        Find k most similar cluster prototypes using FAISS.

        For IndexIVFFlat, uses nprobe parameter for search quality vs speed tradeoff.
        """
        if self.index.ntotal == 0:
            return []

        # Normalize query embedding
        query = query_embedding.astype(np.float32)
        norm = np.linalg.norm(query)
        if norm > 0:
            query = query / norm

        # For IndexIVFFlat, set nprobe (number of clusters to search)
        # Higher nprobe = better accuracy but slower
        if self._active_index_type == "IndexIVFFlat" and hasattr(self.index, "nprobe"):
            # Default nprobe: search 10% of clusters or at least 10
            nprobe = max(10, min(self.nlist // 10, 50))
            self.index.nprobe = nprobe

        # Search FAISS index
        k = min(k, self.index.ntotal)  # Don't search for more than available
        scores, indices = self.index.search(query.reshape(1, -1), k)

        # Convert results and apply threshold
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1 and score >= threshold:  # Valid result above threshold
                if idx < len(self.cluster_ids):
                    cluster_id = self.cluster_ids[idx]
                    results.append(
                        SearchResult(
                            cluster_id=cluster_id, similarity=float(score), cluster_label=self.labels.get(cluster_id)
                        )
                    )

        return results

    def get_prototype(self, cluster_id: str) -> Optional[np.ndarray]:
        """Get the prototype embedding for a cluster."""
        if cluster_id not in self.id_to_index:
            return None

        idx = self.id_to_index[cluster_id]
        try:
            return self.index.reconstruct(idx)
        except Exception:
            # Reconstruct may not be available for some index configurations; fall back to canonical copy.
            if 0 <= idx < len(self._embeddings):
                return self._embeddings[idx]
            return None

    def count(self) -> int:
        """Return number of prototypes in the index."""
        return self.index.ntotal

    def clear(self) -> None:
        """Clear all prototypes from the index."""
        self.cluster_ids.clear()
        self.id_to_index.clear()
        self.labels.clear()
        self._embeddings.clear()
        self.index = faiss.IndexFlatIP(self.dimension)
        self._active_index_type = "IndexFlatIP"
        self._is_trained = False

    def bulk_load(self, prototypes: Dict[str, Tuple[np.ndarray, Optional[str]]]) -> None:
        """
        Efficiently load multiple prototypes at once.

        Args:
            prototypes: Dict of cluster_id -> (embedding, label)
        """
        if not prototypes:
            return

        # Clear existing data
        self.clear()

        # Prepare data
        for cluster_id, (embedding, label) in prototypes.items():
            emb = embedding.astype(np.float32)
            norm = np.linalg.norm(emb)
            if norm > 0:
                emb = emb / norm
            self.cluster_ids.append(cluster_id)
            self.id_to_index[cluster_id] = len(self.cluster_ids) - 1
            self.labels[cluster_id] = label
            self._embeddings.append(emb)

        # Rebuild underlying index once
        self._rebuild_index()

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        stats = {
            "index_type": f"faiss_{self.index_type}",
            "active_index_type": f"faiss_{self._active_index_type}",
            "num_prototypes": self.index.ntotal,
            "dimension": self.dimension,
            "memory_usage_mb": self.index.ntotal * self.dimension * 4 / (1024 * 1024),  # float32
        }
        if self._active_index_type == "IndexIVFFlat":
            stats["nlist"] = self.nlist
            stats["is_trained"] = self._is_trained
            if hasattr(self.index, "nprobe"):
                stats["nprobe"] = self.index.nprobe
        return stats


class PrototypeAssigner:
    """
    Assigns new face embeddings to existing clusters using prototype matching.

    Thresholds:
    - auto_assign_min (0.55): Above this, auto-assign to cluster
    - review_min (0.50): Above this but below auto_assign, add to review queue
    - Below review_min: Mark as unassigned (unknown)
    """

    def __init__(
        self,
        index: EmbeddingIndex,
        auto_assign_min: float = 0.55,
        review_min: float = 0.50,
    ):
        self.index = index
        self.auto_assign_min = auto_assign_min
        self.review_min = review_min

    def assign_face(self, embedding: np.ndarray) -> Dict[str, Any]:
        """
        Determine assignment for a new face embedding.

        Returns:
            {
                'action': 'auto_assign' | 'review' | 'unknown',
                'cluster_id': str | None,
                'cluster_label': str | None,
                'similarity': float,
                'candidates': List[SearchResult]  # Top matches for review
            }
        """
        # Find best matches
        results = self.index.search(embedding, k=5, threshold=self.review_min)

        if not results:
            return {
                "action": "unknown",
                "cluster_id": None,
                "cluster_label": None,
                "similarity": 0.0,
                "candidates": [],
            }

        best = results[0]

        if best.similarity >= self.auto_assign_min:
            return {
                "action": "auto_assign",
                "cluster_id": best.cluster_id,
                "cluster_label": best.cluster_label,
                "similarity": best.similarity,
                "candidates": results,
            }
        elif best.similarity >= self.review_min:
            return {
                "action": "review",
                "cluster_id": best.cluster_id,
                "cluster_label": best.cluster_label,
                "similarity": best.similarity,
                "candidates": results,
            }
        else:
            return {
                "action": "unknown",
                "cluster_id": None,
                "cluster_label": None,
                "similarity": best.similarity,
                "candidates": results,
            }

    def batch_assign(self, embeddings: List[Tuple[str, np.ndarray]]) -> Dict[str, Dict[str, Any]]:
        """
        Assign multiple face embeddings.

        Args:
            embeddings: List of (detection_id, embedding) tuples

        Returns:
            Dict of detection_id -> assignment result
        """
        results = {}
        for detection_id, embedding in embeddings:
            results[detection_id] = self.assign_face(embedding)
        return results


# Factory function
def create_embedding_index(backend: str = "auto", num_prototypes_hint: int = 1000) -> EmbeddingIndex:
    """
    Create an embedding index with the specified backend.

    Args:
        backend: 'auto' (default), 'linear', or 'faiss'
        num_prototypes_hint: Expected number of prototypes (for auto selection)

    Returns:
        EmbeddingIndex instance
    """
    if backend == "auto":
        # Automatically choose based on expected size and FAISS availability
        if FAISS_AVAILABLE and num_prototypes_hint > 1000:
            logger.info(f"Auto-selecting FAISS index for {num_prototypes_hint} prototypes")
            return FAISSIndex()
        else:
            logger.info(f"Auto-selecting Linear index for {num_prototypes_hint} prototypes")
            return LinearIndex()
    elif backend == "linear":
        return LinearIndex()
    elif backend == "faiss":
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS not available. Install with: pip install faiss-cpu")
        return FAISSIndex()
    else:
        raise ValueError(f"Unknown backend: {backend}. Use 'auto', 'linear', or 'faiss'.")


# Global instances for singleton pattern
_global_index: Optional[EmbeddingIndex] = None
_global_assigner: Optional[PrototypeAssigner] = None


def get_global_index() -> EmbeddingIndex:
    """Get the global embedding index instance."""
    global _global_index
    if _global_index is None:
        _global_index = create_embedding_index()
    return _global_index


def get_global_assigner() -> PrototypeAssigner:
    """Get the global prototype assigner instance."""
    global _global_assigner
    if _global_assigner is None:
        _global_assigner = PrototypeAssigner(get_global_index())
    return _global_assigner


def reset_global_index(backend: str = "auto", num_prototypes_hint: int = 1000) -> None:
    """Reset the global index (useful for testing or reconfiguration)."""
    global _global_index, _global_assigner
    _global_index = create_embedding_index(backend, num_prototypes_hint)
    _global_assigner = PrototypeAssigner(_global_index)
