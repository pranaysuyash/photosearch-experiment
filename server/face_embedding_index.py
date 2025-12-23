"""
Face Embedding Index Module

Provides an abstraction layer for face embedding similarity search.
Supports both linear search (for small collections) and FAISS (for scale).

Phase 3 Feature: Speed & Scale
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


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
    def add_prototype(
        self, cluster_id: str, embedding: np.ndarray, label: Optional[str] = None
    ) -> None:
        """Add or update a cluster prototype embedding."""
        pass

    @abstractmethod
    def remove_prototype(self, cluster_id: str) -> bool:
        """Remove a cluster prototype. Returns True if found and removed."""
        pass

    @abstractmethod
    def search(
        self, query_embedding: np.ndarray, k: int = 5, threshold: float = 0.0
    ) -> List[SearchResult]:
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

    def add_prototype(
        self, cluster_id: str, embedding: np.ndarray, label: Optional[str] = None
    ) -> None:
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

    def search(
        self, query_embedding: np.ndarray, k: int = 5, threshold: float = 0.0
    ) -> List[SearchResult]:
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

    def bulk_load(
        self, prototypes: Dict[str, Tuple[np.ndarray, Optional[str]]]
    ) -> None:
        """
        Efficiently load multiple prototypes at once.

        Args:
            prototypes: Dict of cluster_id -> (embedding, label)
        """
        for cluster_id, (embedding, label) in prototypes.items():
            self.add_prototype(cluster_id, embedding, label)


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

    def batch_assign(
        self, embeddings: List[Tuple[str, np.ndarray]]
    ) -> Dict[str, Dict[str, Any]]:
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
def create_embedding_index(backend: str = "linear") -> EmbeddingIndex:
    """
    Create an embedding index with the specified backend.

    Args:
        backend: 'linear' (default) or 'faiss' (future)

    Returns:
        EmbeddingIndex instance
    """
    if backend == "linear":
        return LinearIndex()
    elif backend == "faiss":
        # Future: return FaissIndex()
        raise NotImplementedError(
            "FAISS backend not yet implemented. Use 'linear' for now."
        )
    else:
        raise ValueError(f"Unknown backend: {backend}. Use 'linear' or 'faiss'.")
