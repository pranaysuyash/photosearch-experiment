"""
Performance-Optimized Face Service

Implements high-performance face similarity search using FAISS.
According to .kiro/specs/advanced-face-features/design.md, this service provides:
- FAISS-based similarity search with <100ms performance for 10K+ faces
- Incremental index updates without full rebuild
- Caching layer for frequent queries

Part of Phase 1: High-Performance Foundation implementation.
"""

import logging
from typing import List, Dict, Optional
import numpy as np

from server.face_embedding_index import (
    FAISSIndex,
)
from server.face_clustering_db import FaceClusteringDB

logger = logging.getLogger(__name__)


class PerformanceOptimizedFaceService:
    """
    Face service with FAISS integration for high-performance similarity search.

    Provides:
    - Fast similarity search (<100ms for 10K+ faces)
    - Incremental index updates
    - Caching for frequent queries
    - Automatic index initialization from database
    """

    def __init__(self, db: FaceClusteringDB, index_type: str = "auto", use_cache: bool = True):
        """
        Initialize the performance-optimized face service.

        Args:
            db: FaceClusteringDB instance for database access
            index_type: "auto", "IndexFlatIP", or "IndexIVFFlat"
            use_cache: Enable caching for frequent queries
        """
        self.db = db
        self.index_type = index_type
        self.use_cache = use_cache
        self.cache: Dict[str, List[Dict]] = {}  # Simple in-memory cache

        # Create FAISS index
        # Determine index type based on collection size
        if index_type == "auto":
            # Use IndexIVFFlat for large collections, IndexFlatIP for smaller ones
            num_clusters = self.db.get_cluster_count()
            if num_clusters > 10000:
                logger.info(f"Auto-selecting IndexIVFFlat for {num_clusters} clusters")
                self.faiss_index = FAISSIndex(index_type="IndexIVFFlat", nlist=100)
            else:
                logger.info(f"Auto-selecting IndexFlatIP for {num_clusters} clusters")
                self.faiss_index = FAISSIndex(index_type="IndexFlatIP")
        elif index_type == "IndexFlatIP":
            self.faiss_index = FAISSIndex(index_type="IndexFlatIP")
        elif index_type == "IndexIVFFlat":
            self.faiss_index = FAISSIndex(index_type="IndexIVFFlat", nlist=100)
        else:
            raise ValueError(f"Unknown index_type: {index_type}")

    def initialize_index(self) -> None:
        """
        Initialize FAISS index from existing embeddings in database.

        Loads all cluster prototype embeddings and builds the FAISS index.
        Should be called once at startup or after major database changes.
        """
        logger.info("Initializing FAISS index from database...")

        # Get all cluster prototypes from database
        prototypes = self.db.get_all_cluster_prototypes()

        if not prototypes:
            logger.warning("No cluster prototypes found in database")
            return

        logger.info(f"Loading {len(prototypes)} cluster prototypes into FAISS index...")

        # Prepare embeddings for bulk load
        embeddings_dict = {}
        for cluster_id, prototype_data in prototypes.items():
            embedding = prototype_data.get("embedding")
            label = prototype_data.get("label")

            if embedding is None:
                logger.warning(f"Cluster {cluster_id} has no prototype embedding, skipping")
                continue

            # Embedding is already a numpy array from get_all_cluster_prototypes
            if not isinstance(embedding, np.ndarray):
                # Fallback: try to convert
                if isinstance(embedding, list):
                    embedding = np.array(embedding, dtype=np.float32)
                else:
                    logger.warning(f"Invalid embedding type for cluster {cluster_id}, skipping")
                    continue

            embeddings_dict[cluster_id] = (embedding, label)

        # Bulk load into FAISS index
        if embeddings_dict:
            self.faiss_index.bulk_load(embeddings_dict)
            logger.info(f"FAISS index initialized with {self.faiss_index.count()} prototypes")
        else:
            logger.warning("No valid embeddings found for index initialization")

    def find_similar_faces(
        self, face_id: str, threshold: float = 0.7, limit: int = 10, exclude_self: bool = True
    ) -> List[Dict]:
        """
        Find similar faces using FAISS index.

        Args:
            face_id: Face detection ID to find similar faces for
            threshold: Minimum similarity threshold (0-1)
            limit: Maximum number of results to return
            exclude_self: Exclude the query face from results

        Returns:
            List of similar face dictionaries with metadata
        """
        # Check cache first
        cache_key = f"{face_id}_{threshold}_{limit}"
        if self.use_cache and cache_key in self.cache:
            logger.debug(f"Cache hit for face {face_id}")
            return self.cache[cache_key]

        # Get face embedding from database
        face_detection = self.db.get_face_detection(face_id)
        if not face_detection or not face_detection.embedding:
            logger.warning(f"Face {face_id} not found or has no embedding")
            return []

        # Convert embedding to numpy array (embedding is stored as list in FaceDetection)
        embedding = np.array(face_detection.embedding, dtype=np.float32)

        # Search FAISS index
        similar_faces = self.faiss_index.search(embedding, k=limit, threshold=threshold)

        # Enrich with metadata
        results = []
        for result in similar_faces:
            # Exclude self if requested
            if exclude_self:
                # Get face detection for this cluster to check if it's the same face
                cluster_faces = self.db.get_faces_for_cluster(result.cluster_id)
                if any(f.detection_id == face_id for f in cluster_faces):
                    continue

            # Get face detection data for this cluster
            cluster_faces = self.db.get_faces_for_cluster(result.cluster_id)
            if not cluster_faces:
                continue

            # Get best quality face from cluster
            best_face = max(cluster_faces, key=lambda f: f.quality_score or 0.0)

            results.append(
                {
                    "face_id": best_face.detection_id,
                    "cluster_id": result.cluster_id,
                    "similarity_score": result.similarity,
                    "photo_path": best_face.photo_path,
                    "quality_score": best_face.quality_score,
                    "cluster_label": result.cluster_label,
                }
            )

        # Cache results
        if self.use_cache:
            self.cache[cache_key] = results

        return results

    def find_similar_faces_by_embedding(
        self, embedding: np.ndarray, threshold: float = 0.7, limit: int = 10
    ) -> List[Dict]:
        """
        Find similar faces using a raw embedding vector.

        Args:
            embedding: Face embedding vector (numpy array)
            threshold: Minimum similarity threshold (0-1)
            limit: Maximum number of results to return

        Returns:
            List of similar face dictionaries with metadata
        """
        # Search FAISS index
        similar_faces = self.faiss_index.search(embedding, k=limit, threshold=threshold)

        # Enrich with metadata
        results = []
        for result in similar_faces:
            # Get face detection data for this cluster
            cluster_faces = self.db.get_faces_for_cluster(result.cluster_id)
            if not cluster_faces:
                continue

            # Get best quality face from cluster
            best_face = max(cluster_faces, key=lambda f: f.quality_score or 0.0)

            results.append(
                {
                    "face_id": best_face.detection_id,
                    "cluster_id": result.cluster_id,
                    "similarity_score": result.similarity,
                    "photo_path": best_face.photo_path,
                    "quality_score": best_face.quality_score,
                    "cluster_label": result.cluster_label,
                }
            )

        return results

    def add_face_to_index(self, cluster_id: str, embedding: np.ndarray, label: Optional[str] = None) -> None:
        """
        Add a face embedding to the FAISS index incrementally.

        Args:
            cluster_id: Cluster ID for this face
            embedding: Face embedding vector
            label: Optional cluster label
        """
        self.faiss_index.add_prototype(cluster_id, embedding, label)

        # Clear cache for this cluster
        if self.use_cache:
            # Clear all cache entries (simple invalidation strategy)
            self.cache.clear()

    def remove_face_from_index(self, cluster_id: str) -> bool:
        """
        Remove a face from the FAISS index.

        Args:
            cluster_id: Cluster ID to remove

        Returns:
            True if removed, False if not found
        """
        removed = self.faiss_index.remove_prototype(cluster_id)

        # Clear cache
        if self.use_cache:
            self.cache.clear()

        return removed

    def get_index_stats(self) -> Dict:
        """Get statistics about the FAISS index."""
        stats = self.faiss_index.get_stats()
        stats["cache_size"] = len(self.cache) if self.use_cache else 0
        return stats

    def clear_cache(self) -> None:
        """Clear the query cache."""
        self.cache.clear()
        logger.info("Face service cache cleared")
