"""
Face Clustering Database Module

Provides database operations for face detection, clustering, and person management.
This module connects the face clustering system with individual photos.
"""

import sqlite3
import hashlib
import os
import logging
from pathlib import Path
from typing import Any, Optional, List, Dict, Tuple, cast
from dataclasses import dataclass
from datetime import datetime
import json
import numpy as np

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class FaceDetection:
    """Represents a detected face in a photo."""

    detection_id: str
    photo_path: str
    bounding_box: Dict[str, float]  # {x, y, width, height}
    embedding: Optional[List[float]] = None  # Face embedding vector
    quality_score: Optional[float] = None  # 0-1 quality score
    age_estimate: Optional[float] = None
    age_confidence: Optional[float] = None
    emotion: Optional[str] = None
    emotion_confidence: Optional[float] = None
    pose_type: Optional[str] = None
    pose_confidence: Optional[float] = None
    gender: Optional[str] = None
    gender_confidence: Optional[float] = None
    lighting_score: Optional[float] = None
    occlusion_score: Optional[float] = None
    resolution_score: Optional[float] = None
    overall_quality: Optional[float] = None
    created_at: Optional[str] = None


@dataclass
class FaceCluster:
    """Represents a cluster of similar faces (a person)."""

    cluster_id: str
    label: Optional[str] = None  # User-provided name
    face_count: int = 0
    photo_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    indexing_disabled: bool = False


@dataclass
class PhotoPersonAssociation:
    """Represents the association between a photo and a person."""

    photo_path: str
    cluster_id: str
    detection_id: str
    confidence: float  # Confidence that this face belongs to the cluster
    assignment_state: Optional[str] = None  # 'auto', 'user_confirmed', 'user_rejected'
    created_at: Optional[str] = None


class FaceClusteringDB:
    """Database for managing face detections, clusters, and photo-person associations."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        # Provide a convenience connection for legacy callers (routers) that
        # expect a `.conn` attribute similar to the older FaceClusterer API.
        # Callers doing ad-hoc queries should still prefer context-managed
        # connections, but exposing this keeps existing endpoints working.
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row

    @staticmethod
    def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
        try:
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        except sqlite3.OperationalError:
            return set()
        return {row[1] for row in rows}

    @classmethod
    def _is_legacy_schema(cls, conn: sqlite3.Connection) -> bool:
        face_clusters_cols = cls._table_columns(conn, "face_clusters")
        if "cluster_id" in face_clusters_cols:
            return False
        legacy_cols = cls._table_columns(conn, "clusters")
        return "id" in face_clusters_cols or bool(legacy_cols)

    def _init_db(self):
        """Initialize the face clustering database with versioned migrations."""
        # Run versioned migrations first
        try:
            # Try relative import first (when running from server directory or tests)
            try:
                from face_schema_migrations import run_migrations, get_schema_version
            except ImportError:
                # Try absolute import (when running from project root)
                from server.face_schema_migrations import (
                    run_migrations,
                    get_schema_version,
                )

            run_migrations(self.db_path)

            # Verify schema version
            with sqlite3.connect(str(self.db_path)) as conn:
                version = get_schema_version(conn)
                logger.info(f"Face clustering DB initialized at schema version {version}")
        except Exception as e:
            logger.warning(f"Migration failed, falling back to legacy init: {e}")
            self._init_db_legacy()

    def _init_db_legacy(self):
        """Legacy database initialization (fallback if migrations fail)."""
        with sqlite3.connect(str(self.db_path)) as conn:
            # Face detections table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS face_detections (
                    detection_id TEXT PRIMARY KEY,
                    photo_path TEXT NOT NULL,
                    bounding_box TEXT NOT NULL,
                    embedding BLOB,
                    quality_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Face clusters table (people)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS face_clusters (
                    cluster_id TEXT PRIMARY KEY,
                    label TEXT,
                    face_count INTEGER DEFAULT 0,
                    photo_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Photo-person associations
            conn.execute("""
                CREATE TABLE IF NOT EXISTS photo_person_associations (
                    photo_path TEXT NOT NULL,
                    cluster_id TEXT NOT NULL,
                    detection_id TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    assignment_state TEXT DEFAULT 'auto',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (photo_path, cluster_id, detection_id),
                    FOREIGN KEY (detection_id) REFERENCES face_detections(detection_id),
                    FOREIGN KEY (cluster_id) REFERENCES face_clusters(cluster_id)
                )
            """)

            # Indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_face_detections_photo ON face_detections(photo_path)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_photo_person_photo ON photo_person_associations(photo_path)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_photo_person_cluster ON photo_person_associations(cluster_id)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_photo_person_photo_cluster ON photo_person_associations(photo_path, cluster_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_photo_person_assignment_state ON photo_person_associations(assignment_state)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_photo_person_created_at ON photo_person_associations(created_at)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_face_detections_created_at ON face_detections(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_face_clusters_label ON face_clusters(label)")

            # Lightweight migrations for older DBs
            try:
                cols = [r[1] for r in conn.execute("PRAGMA table_info(face_clusters)").fetchall()]
                if "label" not in cols:
                    conn.execute("ALTER TABLE face_clusters ADD COLUMN label TEXT")
            except Exception:
                pass

    def ensure_face_cluster(self, cluster_id: str, label: Optional[str] = None) -> None:
        """Ensure a face cluster exists.

        This is useful for manual associations where the UI (or tests) provides a stable
        person_id/cluster_id without first creating a cluster record.
        """
        if not cluster_id:
            return
        with sqlite3.connect(str(self.db_path)) as conn:
            if self._is_legacy_schema(conn):
                try:
                    cluster_id_int = int(cluster_id)
                except (TypeError, ValueError):
                    return
                conn.execute(
                    """
                    INSERT OR IGNORE INTO clusters (id, label, size)
                    VALUES (?, ?, 0)
                    """,
                    (cluster_id_int, label),
                )
                return

            conn.execute(
                """
                INSERT OR IGNORE INTO face_clusters (cluster_id, label)
                VALUES (?, ?)
                """,
                (cluster_id, label),
            )

    def ensure_face_detection(
        self,
        detection_id: str,
        photo_path: str,
        bounding_box: Optional[Dict[str, float]] = None,
    ) -> None:
        """Ensure a face detection exists.

        For manual associations (or when face detection is unavailable), callers may
        want to attach a person to a photo without a real detection region.
        """
        if not detection_id or not photo_path:
            return

        if bounding_box is None:
            bounding_box = {"x": 0.0, "y": 0.0, "width": 0.0, "height": 0.0}

        with sqlite3.connect(str(self.db_path)) as conn:
            if self._is_legacy_schema(conn):
                return
            conn.execute(
                """
                INSERT OR IGNORE INTO face_detections (detection_id, photo_path, bounding_box, embedding, quality_score)
                VALUES (?, ?, ?, NULL, NULL)
                """,
                (detection_id, photo_path, json.dumps(bounding_box)),
            )

    def add_face_detection(
        self,
        photo_path: str,
        bounding_box: Dict[str, float],
        embedding: Optional[List[float]] = None,
        quality_score: Optional[float] = None,
        age_estimate: Optional[float] = None,
        age_confidence: Optional[float] = None,
        emotion: Optional[str] = None,
        emotion_confidence: Optional[float] = None,
        pose_type: Optional[str] = None,
        pose_confidence: Optional[float] = None,
        gender: Optional[str] = None,
        gender_confidence: Optional[float] = None,
        lighting_score: Optional[float] = None,
        occlusion_score: Optional[float] = None,
        resolution_score: Optional[float] = None,
        overall_quality: Optional[float] = None,
    ) -> str:
        """Add a face detection to the database."""
        detection_id = f"face_{hashlib.md5(f'{photo_path}_{json.dumps(bounding_box)}'.encode()).hexdigest()}"

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT INTO face_detections (
                    detection_id,
                    photo_path,
                    bounding_box,
                    embedding,
                    quality_score,
                    age_estimate,
                    age_confidence,
                    emotion,
                    emotion_confidence,
                    pose_type,
                    pose_confidence,
                    gender,
                    gender_confidence,
                    lighting_score,
                    occlusion_score,
                    resolution_score,
                    overall_quality
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    detection_id,
                    photo_path,
                    json.dumps(bounding_box),
                    json.dumps(embedding) if embedding else None,
                    quality_score,
                    age_estimate,
                    age_confidence,
                    emotion,
                    emotion_confidence,
                    pose_type,
                    pose_confidence,
                    gender,
                    gender_confidence,
                    lighting_score,
                    occlusion_score,
                    resolution_score,
                    overall_quality if overall_quality is not None else quality_score,
                ),
            )

        return detection_id

    def add_face_cluster(self, label: Optional[str] = None) -> str:
        """Add a new face cluster (person)."""
        cluster_id = f"cluster_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]}"

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT INTO face_clusters (cluster_id, label)
                VALUES (?, ?)
            """,
                (cluster_id, label),
            )

        return cluster_id

    def associate_person_with_photo(self, photo_path: str, cluster_id: str, detection_id: str, confidence: float):
        """Associate a person (cluster) with a photo."""
        with sqlite3.connect(str(self.db_path)) as conn:
            # Check if cluster exists
            cluster = conn.execute(
                "SELECT cluster_id FROM face_clusters WHERE cluster_id = ?",
                (cluster_id,),
            ).fetchone()

            if not cluster:
                raise ValueError(f"Cluster {cluster_id} does not exist")

            # Check if detection exists
            detection = conn.execute(
                "SELECT detection_id FROM face_detections WHERE detection_id = ?",
                (detection_id,),
            ).fetchone()

            if not detection:
                raise ValueError(f"Detection {detection_id} does not exist")

            # Add association
            conn.execute(
                """
                INSERT INTO photo_person_associations (photo_path, cluster_id, detection_id, confidence)
                VALUES (?, ?, ?, ?)
            """,
                (photo_path, cluster_id, detection_id, confidence),
            )

            # Update cluster counts
            conn.execute(
                """
                UPDATE face_clusters
                SET face_count = face_count + 1,
                    photo_count = photo_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE cluster_id = ?
            """,
                (cluster_id,),
            )

    def get_people_in_photo(self, photo_path: str) -> List[PhotoPersonAssociation]:
        """Get all people associated with a specific photo."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            if self._is_legacy_schema(conn):
                rows = conn.execute(
                    """
                    SELECT f.image_path as photo_path, f.cluster_id, f.id as detection_id,
                           f.confidence, f.created_at
                    FROM faces f
                    WHERE f.image_path = ? AND f.cluster_id IS NOT NULL
                    ORDER BY f.confidence DESC
                    """,
                    (photo_path,),
                ).fetchall()

                return [
                    PhotoPersonAssociation(
                        photo_path=row["photo_path"],
                        cluster_id=str(row["cluster_id"]),
                        detection_id=str(row["detection_id"]),
                        confidence=row["confidence"] or 0.0,
                        created_at=row["created_at"],
                    )
                    for row in rows
                ]

            rows = conn.execute(
                """
                  SELECT ppa.photo_path, ppa.cluster_id, ppa.detection_id, ppa.confidence,
                      ppa.assignment_state, ppa.created_at,
                      fc.label as cluster_label
                  FROM photo_person_associations ppa
                  JOIN face_clusters fc ON ppa.cluster_id = fc.cluster_id
                WHERE ppa.photo_path = ?
                ORDER BY ppa.confidence DESC
                """,
                (photo_path,),
            ).fetchall()

            return [
                PhotoPersonAssociation(
                    photo_path=row["photo_path"],
                    cluster_id=row["cluster_id"],
                    detection_id=row["detection_id"],
                    confidence=row["confidence"],
                    assignment_state=row["assignment_state"] or "auto",
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    def add_person_to_photo(
        self,
        photo_path: str,
        cluster_id: str,
        detection_id: str,
        confidence: float = 0.9,
    ):
        """Add a person association to a photo."""
        # First check if this detection already has associations
        existing = self.get_people_in_photo(photo_path)
        existing_cluster_ids = [assoc.cluster_id for assoc in existing]

        if cluster_id in existing_cluster_ids:
            # Already associated, update confidence
            with sqlite3.connect(str(self.db_path)) as conn:
                cur = conn.execute(
                    """
                    UPDATE photo_person_associations
                    SET confidence = ?
                    WHERE photo_path = ? AND cluster_id = ? AND detection_id = ?
                """,
                    (confidence, photo_path, cluster_id, detection_id),
                )

                # If there was an existing association for the cluster but not for this specific
                # detection_id, create a new association row.
                if cur.rowcount == 0:
                    self.associate_person_with_photo(photo_path, cluster_id, detection_id, confidence)
        else:
            # New association
            self.associate_person_with_photo(photo_path, cluster_id, detection_id, confidence)

    def remove_person_from_photo(self, photo_path: str, cluster_id: str, detection_id: str):
        """Remove a person association from a photo."""
        with sqlite3.connect(str(self.db_path)) as conn:
            # Remove association
            conn.execute(
                """
                DELETE FROM photo_person_associations
                WHERE photo_path = ? AND cluster_id = ? AND detection_id = ?
            """,
                (photo_path, cluster_id, detection_id),
            )

            # Update cluster counts
            remaining_faces = conn.execute(
                """
                SELECT COUNT(*) FROM photo_person_associations
                WHERE cluster_id = ?
            """,
                (cluster_id,),
            ).fetchone()[0]

            remaining_photos = conn.execute(
                """
                SELECT COUNT(DISTINCT photo_path) FROM photo_person_associations
                WHERE cluster_id = ?
            """,
                (cluster_id,),
            ).fetchone()[0]

            conn.execute(
                """
                UPDATE face_clusters
                SET face_count = ?,
                    photo_count = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE cluster_id = ?
            """,
                (remaining_faces, remaining_photos, cluster_id),
            )

    def get_all_clusters(self) -> List[FaceCluster]:
        """Get all face clusters (people)."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            if self._is_legacy_schema(conn):
                rows = conn.execute(
                    """
                    SELECT id, label, size, created_at, updated_at
                    FROM clusters
                    ORDER BY label COLLATE NOCASE, created_at DESC
                    """
                ).fetchall()

                return [
                    FaceCluster(
                        cluster_id=str(row["id"]),
                        label=row["label"],
                        face_count=row["size"] or 0,
                        photo_count=row["size"] or 0,
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                    for row in rows
                ]

            rows = conn.execute(
                """
                SELECT cluster_id, label, face_count, photo_count, created_at, updated_at, indexing_disabled
                FROM face_clusters
                ORDER BY label COLLATE NOCASE, created_at DESC
                """
            ).fetchall()

            return [
                FaceCluster(
                    cluster_id=row["cluster_id"],
                    label=row["label"],
                    face_count=row["face_count"],
                    photo_count=row["photo_count"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    indexing_disabled=row["indexing_disabled"] == 1,
                )
                for row in rows
            ]

    def get_photos_for_cluster(self, cluster_id: str) -> List[str]:
        """Get all photos associated with a cluster."""
        with sqlite3.connect(str(self.db_path)) as conn:
            if self._is_legacy_schema(conn):
                rows = conn.execute(
                    """
                    SELECT DISTINCT image_path
                    FROM faces
                    WHERE cluster_id = ?
                    ORDER BY image_path
                    """,
                    (cluster_id,),
                ).fetchall()
                return [row[0] for row in rows]

            rows = conn.execute(
                """
                SELECT DISTINCT photo_path
                FROM photo_person_associations
                WHERE cluster_id = ?
                ORDER BY photo_path
                """,
                (cluster_id,),
            ).fetchall()

            return [row[0] for row in rows]

    def update_cluster_label(self, cluster_id: str, label: str):
        """Update the label (name) of a cluster."""
        with sqlite3.connect(str(self.db_path)) as conn:
            if self._is_legacy_schema(conn):
                conn.execute(
                    """
                    UPDATE clusters
                    SET label = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (label, cluster_id),
                )
                return

            conn.execute(
                """
                UPDATE face_clusters
                SET label = ?, updated_at = CURRENT_TIMESTAMP
                WHERE cluster_id = ?
                """,
                (label, cluster_id),
            )

    def cleanup_missing_photos(self) -> int:
        """Remove associations for photos that no longer exist."""
        with sqlite3.connect(str(self.db_path)) as conn:
            # Get all unique photo paths
            cursor = conn.execute("SELECT DISTINCT photo_path FROM photo_person_associations")
            all_photos = [row[0] for row in cursor.fetchall()]

            missing_photos = [f for f in all_photos if not os.path.exists(f)]

            for photo_path in missing_photos:
                # Remove associations
                conn.execute(
                    "DELETE FROM photo_person_associations WHERE photo_path = ?",
                    (photo_path,),
                )
                # Remove detections
                conn.execute("DELETE FROM face_detections WHERE photo_path = ?", (photo_path,))

            return len(missing_photos)

    def detect_and_store_faces(self, photo_path: str) -> List[str]:
        """Detect faces in a photo and store them in the database."""
        try:
            from server.face_detection_service import get_face_detection_service

            # Get face detection service
            detection_service = get_face_detection_service()

            if not detection_service.is_available():
                logger.warning("Face detection service not available, using fallback")
                return []

            # Detect faces
            result = detection_service.detect_faces(photo_path)

            if not result.success:
                logger.error(f"Face detection failed for {photo_path}: {result.error}")
                return []

            # Store detected faces in database
            detection_ids = []
            for face in result.faces:
                detection_id = self.add_face_detection(
                    photo_path=face.photo_path,
                    bounding_box=face.bounding_box,
                    embedding=face.embedding,
                    quality_score=face.quality_score,
                    age_estimate=face.age_estimate,
                    age_confidence=face.age_confidence,
                    emotion=face.emotion,
                    emotion_confidence=face.emotion_confidence,
                    pose_type=face.pose_type,
                    pose_confidence=face.pose_confidence,
                    gender=face.gender,
                    gender_confidence=face.gender_confidence,
                    lighting_score=face.lighting_score,
                    occlusion_score=face.occlusion_score,
                    resolution_score=face.resolution_score,
                    overall_quality=face.overall_quality,
                )
                detection_ids.append(detection_id)

            logger.info(f"Detected and stored {len(detection_ids)} faces in {photo_path}")
            return detection_ids

        except ImportError:
            logger.warning("Face detection service not available, using fallback")
            return []
        except Exception as e:
            logger.error(f"Error detecting and storing faces for {photo_path}: {e}")
            return []

    def process_photo_with_faces(self, photo_path: str) -> bool:
        """Complete workflow: detect faces, store them, and suggest associations."""
        try:
            # Step 1: Detect and store faces
            detection_ids = self.detect_and_store_faces(photo_path)

            if not detection_ids:
                logger.info(f"No faces detected in {photo_path}")
                return False

            # Step 2: For now, we'll just store the detections
            # Future: Add automatic clustering and association

            logger.info(f"Processed {photo_path} with {len(detection_ids)} faces")
            return True

        except Exception as e:
            logger.error(f"Error processing photo {photo_path}: {e}")
            return False

    def get_face_thumbnail(self, detection_id: str) -> Optional[str]:
        """Get a thumbnail for a specific face detection."""
        try:
            from server.face_detection_service import get_face_detection_service

            # Get the detection details
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    """
                    SELECT photo_path, bounding_box
                    FROM face_detections
                    WHERE detection_id = ?
                """,
                    (detection_id,),
                ).fetchone()

                if not row:
                    return None

                # Create a DetectedFace object
                from server.face_detection_service import DetectedFace

                face = DetectedFace(
                    detection_id=detection_id,
                    photo_path=row["photo_path"],
                    bounding_box=json.loads(row["bounding_box"]),
                )

            # Get thumbnail using detection service
            detection_service = get_face_detection_service()
            if detection_service.is_available():
                return detection_service.get_face_thumbnail(face.photo_path, face)

        except Exception as e:
            logger.error(f"Error getting face thumbnail: {e}")

        return None

    def _calculate_cosine_similarity(self, emb1: List[float], emb2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings."""
        try:
            vec1 = np.array(emb1)
            vec2 = np.array(emb2)

            # Normalize vectors
            vec1_norm = vec1 / np.linalg.norm(vec1)
            vec2_norm = vec2 / np.linalg.norm(vec2)

            # Calculate cosine similarity
            similarity = np.dot(vec1_norm, vec2_norm)
            return float(similarity)

        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0

    def _get_face_embeddings(self) -> Tuple[List[str], List[List[float]]]:
        """Get all face embeddings from the database."""
        detection_ids = []
        embeddings = []

        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute("""
                SELECT detection_id, embedding
                FROM face_detections
                WHERE embedding IS NOT NULL
            """).fetchall()

            for row in rows:
                detection_ids.append(row[0])
                embeddings.append(json.loads(row[1]))

        return detection_ids, embeddings

    def cluster_faces(self, similarity_threshold: float = 0.6, min_samples: int = 2) -> Dict[str, List[str]]:
        """Automatically cluster similar faces using DBSCAN."""
        try:
            # Get all face embeddings
            detection_ids, embeddings = self._get_face_embeddings()

            if not embeddings or len(embeddings) < min_samples:
                logger.info("Not enough faces for clustering")
                return {}

            # Convert to numpy array
            embedding_array = np.array(embeddings)

            # Use DBSCAN for clustering
            # eps = similarity_threshold (1 - cosine similarity)
            # min_samples = minimum number of faces to form a cluster
            from sklearn.cluster import DBSCAN  # type: ignore[import-untyped]

            # DBSCAN uses distance, so we convert similarity threshold
            # Cosine similarity of 0.6 ≈ distance of 0.894 (1 - 0.6^2, but simplified)
            distance_threshold = 1.0 - similarity_threshold

            clustering = DBSCAN(eps=distance_threshold, min_samples=min_samples, metric="cosine")

            # Fit the clustering
            labels = clustering.fit_predict(embedding_array)

            # Create clusters
            clusters: Dict[int, Dict[str, Any]] = {}  # label -> {'cluster_id': str, 'detection_ids': List[str]}
            noise_detections = []  # Detections not in any cluster

            for detection_id, label in zip(detection_ids, labels):
                if label == -1:
                    noise_detections.append(detection_id)
                else:
                    if label not in clusters:
                        # Create a new cluster
                        cluster_id = self.add_face_cluster(label=f"Auto Cluster {label}")
                        clusters[label] = {
                            "cluster_id": cluster_id,
                            "detection_ids": cast(List[str], []),
                        }

                    cast(List[str], clusters[label]["detection_ids"]).append(detection_id)

            # Associate faces with their clusters
            for cluster_label, cluster_data in clusters.items():
                cluster_id = cast(str, cluster_data["cluster_id"])

                for detection_id in cast(List[str], cluster_data["detection_ids"]):
                    # Get the photo path for this detection
                    with sqlite3.connect(str(self.db_path)) as conn:
                        row = conn.execute(
                            """
                            SELECT photo_path FROM face_detections
                            WHERE detection_id = ?
                        """,
                            (detection_id,),
                        ).fetchone()

                        if row:
                            photo_path = row[0]

                            # Associate the face with the cluster
                            self.associate_person_with_photo(
                                photo_path=photo_path,
                                cluster_id=cluster_id,
                                detection_id=detection_id,
                                confidence=0.95,
                            )

            # Return clustering results
            result: Dict[str, List[str]] = {}
            for cluster_label, cluster_data in clusters.items():
                cid = cast(str, cluster_data["cluster_id"])
                result[cid] = cast(List[str], cluster_data["detection_ids"])

            logger.info(f"Created {len(clusters)} clusters from {len(detection_ids)} faces")
            logger.info(f"Noise detections (not clustered): {len(noise_detections)}")

            return result

        except ImportError:
            logger.warning("scikit-learn not available for clustering")
            return {}
        except Exception as e:
            logger.error(f"Error during face clustering: {e}")
            return {}

    def get_cluster_quality(self, cluster_id: str) -> Dict:
        """Analyze the quality of a face cluster."""
        try:
            # Get all faces in the cluster
            with sqlite3.connect(str(self.db_path)) as conn:
                rows = conn.execute(
                    """
                          SELECT ppa.detection_id, ppa.confidence,
                              fd.quality_score, fd.embedding
                          FROM photo_person_associations ppa
                          JOIN face_detections fd ON ppa.detection_id = fd.detection_id
                    WHERE ppa.cluster_id = ?
                """,
                    (cluster_id,),
                ).fetchall()

                if not rows:
                    return {"error": "Cluster not found or empty"}

            # Calculate quality metrics
            confidences = [row[1] for row in rows]
            quality_scores = [row[2] for row in rows]
            embeddings = [json.loads(row[3]) for row in rows if row[3]]

            # Calculate statistics
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

            # Calculate cluster coherence (how similar faces are to each other)
            coherence_score = 1.0
            if len(embeddings) > 1:
                similarities = []
                for i in range(len(embeddings)):
                    for j in range(i + 1, len(embeddings)):
                        sim = self._calculate_cosine_similarity(embeddings[i], embeddings[j])
                        similarities.append(sim)

                if similarities:
                    coherence_score = sum(similarities) / len(similarities)

            return {
                "cluster_id": cluster_id,
                "face_count": len(rows),
                "avg_confidence": avg_confidence,
                "avg_quality_score": avg_quality,
                "coherence_score": coherence_score,
                "quality_rating": self._calculate_quality_rating(avg_quality, coherence_score),
            }

        except Exception as e:
            logger.error(f"Error analyzing cluster quality: {e}")
            return {"error": str(e)}

    def _calculate_quality_rating(self, avg_quality: float, coherence: float) -> str:
        """Calculate a quality rating for a cluster."""
        score = (avg_quality + coherence) / 2

        if score >= 0.9:
            return "Excellent"
        elif score >= 0.8:
            return "Good"
        elif score >= 0.7:
            return "Fair"
        elif score >= 0.6:
            return "Poor"
        else:
            return "Low"

    # ===================================================================
    # Phase 0: Assignment State Management
    # ===================================================================

    def update_assignment_state(self, detection_id: str, cluster_id: str, state: str) -> bool:
        """
        Update the assignment state of a face-to-cluster association.

        Args:
            detection_id: The face detection ID
            cluster_id: The cluster/person ID
            state: One of 'auto', 'user_confirmed', 'user_rejected'

        Returns:
            True if update succeeded
        """
        valid_states = {"auto", "user_confirmed", "user_rejected"}
        if state not in valid_states:
            raise ValueError(f"Invalid state: {state}. Must be one of {valid_states}")

        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                """
                UPDATE photo_person_associations
                SET assignment_state = ?
                WHERE detection_id = ? AND cluster_id = ?
            """,
                (state, detection_id, cluster_id),
            )

            return cursor.rowcount > 0

    def confirm_face_assignment(self, detection_id: str, cluster_id: str) -> bool:
        """User confirms a face assignment - prevents auto-reassignment."""
        return self.update_assignment_state(detection_id, cluster_id, "user_confirmed")

    def reject_face_from_cluster(self, detection_id: str, cluster_id: str) -> bool:
        """
        User rejects a face from a cluster.
        This removes the association and records the rejection to prevent re-assignment.
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            # Log the operation for undo
            self._log_operation(
                conn,
                "reject",
                {
                    "detection_id": detection_id,
                    "cluster_id": cluster_id,
                    "previous_state": self._get_association_snapshot(conn, detection_id, cluster_id),
                },
            )

            # Add to rejections table
            conn.execute(
                """
                INSERT OR IGNORE INTO face_rejections (detection_id, cluster_id)
                VALUES (?, ?)
            """,
                (detection_id, cluster_id),
            )

            # Remove the association
            conn.execute(
                """
                DELETE FROM photo_person_associations
                WHERE detection_id = ? AND cluster_id = ?
            """,
                (detection_id, cluster_id),
            )

            # Update cluster counts
            self._update_cluster_counts_conn(conn, cluster_id)

            return True

    def is_face_rejected_from_cluster(self, detection_id: str, cluster_id: str) -> bool:
        """Check if a face was explicitly rejected from a cluster."""
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute(
                """
                SELECT 1 FROM face_rejections
                WHERE detection_id = ? AND cluster_id = ?
            """,
                (detection_id, cluster_id),
            ).fetchone()
            return row is not None

    def get_rejected_clusters_for_face(self, detection_id: str) -> List[str]:
        """Get all clusters this face has been rejected from."""
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute(
                """
                SELECT cluster_id FROM face_rejections
                WHERE detection_id = ?
            """,
                (detection_id,),
            ).fetchall()
            return [row[0] for row in rows]

    # ===================================================================
    # Phase 0: Hide/Unhide Person
    # ===================================================================

    def set_cluster_hidden(self, cluster_id: str, hidden: bool = True) -> bool:
        """Hide or unhide a person cluster from the main gallery."""
        with sqlite3.connect(str(self.db_path)) as conn:
            # Log for undo
            current_state = conn.execute(
                "SELECT hidden FROM face_clusters WHERE cluster_id = ?", (cluster_id,)
            ).fetchone()

            if current_state:
                self._log_operation(
                    conn,
                    "hide",
                    {"cluster_id": cluster_id, "previous_hidden": current_state[0]},
                )

            cursor = conn.execute(
                """
                UPDATE face_clusters
                SET hidden = ?, updated_at = CURRENT_TIMESTAMP
                WHERE cluster_id = ?
            """,
                (1 if hidden else 0, cluster_id),
            )

            return cursor.rowcount > 0

    def get_visible_clusters(self) -> List[FaceCluster]:
        """Get only non-hidden clusters."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT cluster_id, label, face_count, photo_count, created_at, updated_at
                FROM face_clusters
                WHERE hidden = 0 OR hidden IS NULL
                ORDER BY label COLLATE NOCASE, created_at DESC
            """).fetchall()

            return [
                FaceCluster(
                    cluster_id=row["cluster_id"],
                    label=row["label"],
                    face_count=row["face_count"],
                    photo_count=row["photo_count"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]

    def get_hidden_clusters(self) -> List[FaceCluster]:
        """Get all hidden clusters."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT cluster_id, label, face_count, photo_count, created_at, updated_at
                FROM face_clusters
                WHERE hidden = 1
                ORDER BY label COLLATE NOCASE, created_at DESC
            """).fetchall()

            return [
                FaceCluster(
                    cluster_id=row["cluster_id"],
                    label=row["label"],
                    face_count=row["face_count"],
                    photo_count=row["photo_count"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]

    # ===================================================================
    # Phase 0: Undo System (Full Reversible Snapshots)
    # ===================================================================

    def _log_operation(self, conn: sqlite3.Connection, operation_type: str, operation_data: dict):
        """Log an operation for potential undo. Call within an existing transaction."""
        conn.execute(
            """
            INSERT INTO person_operations_log (operation_type, operation_data)
            VALUES (?, ?)
        """,
            (operation_type, json.dumps(operation_data)),
        )

    def _get_association_snapshot(self, conn: sqlite3.Connection, detection_id: str, cluster_id: str) -> Optional[dict]:
        """Get current state of an association for undo purposes."""
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT photo_path, cluster_id, detection_id, confidence, assignment_state, created_at
            FROM photo_person_associations
            WHERE detection_id = ? AND cluster_id = ?
        """,
            (detection_id, cluster_id),
        ).fetchone()

        if row:
            return dict(row)
        return None

    def _get_cluster_snapshot(self, conn: sqlite3.Connection, cluster_id: str) -> Optional[dict]:
        """Get current state of a cluster for undo purposes."""
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT cluster_id, label, face_count, photo_count, hidden,
                   prototype_embedding, prototype_updated_at, prototype_count,
                   created_at, updated_at
            FROM face_clusters
            WHERE cluster_id = ?
        """,
            (cluster_id,),
        ).fetchone()

        if row:
            result = dict(row)
            # Convert blob to base64 for JSON serialization
            if result.get("prototype_embedding"):
                import base64

                result["prototype_embedding"] = base64.b64encode(result["prototype_embedding"]).decode()
            return result
        return None

    def undo_last_operation(self) -> Optional[dict]:
        """
        Undo the most recent operation.

        Returns:
            Dict with operation_type and status, or None if nothing to undo
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT id, operation_type, operation_data
                FROM person_operations_log
                WHERE undone = 0
                ORDER BY performed_at DESC
                LIMIT 1
            """).fetchone()

            if not row:
                return None

            op_id = row["id"]
            op_type = row["operation_type"]
            op_data = json.loads(row["operation_data"])

            try:
                # Execute undo based on operation type
                if op_type == "merge":
                    self._undo_merge(conn, op_data)
                elif op_type == "split":
                    self._undo_split(conn, op_data)
                elif op_type == "move":
                    self._undo_move(conn, op_data)
                elif op_type == "hide":
                    self._undo_hide(conn, op_data)
                elif op_type == "reject":
                    self._undo_reject(conn, op_data)
                elif op_type == "delete_person":
                    self._undo_delete_person(conn, op_data)
                elif op_type == "rename":
                    self._undo_rename(conn, op_data)
                elif op_type == "review_confirm":
                    self._undo_review_confirm(conn, op_data)
                elif op_type == "review_reject":
                    self._undo_review_reject(conn, op_data)

                # Mark as undone
                conn.execute(
                    """
                    UPDATE person_operations_log
                    SET undone = 1, undone_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """,
                    (op_id,),
                )

                return {"operation_type": op_type, "undone": True}

            except Exception as e:
                logger.error(f"Failed to undo {op_type}: {e}")
                return {"operation_type": op_type, "undone": False, "error": str(e)}

    def get_undo_status(self) -> dict:
        """Return whether there is an outstanding operation that can be undone.

        Provides lightweight metadata for UI polling without mutating state.
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT id, operation_type, performed_at
                FROM person_operations_log
                WHERE undone = 0
                ORDER BY performed_at DESC
                LIMIT 1
                """
            ).fetchone()

            if not row:
                return {"can_undo": False}

            return {
                "can_undo": True,
                "operation_type": row["operation_type"],
                "performed_at": row["performed_at"],
            }

    def _undo_review_confirm(self, conn: sqlite3.Connection, op_data: dict):
        """Undo a review confirm - reset association and queue status."""
        detection_id = op_data["detection_id"]
        # cluster_id = op_data["cluster_id"]

        # Reset association to 'auto' or delete if it didn't exist?
        # For simplicity, we just set it back to what review queue implies (usually 'auto' if it existed)
        # But if it was a new face, we might want to keep it but reset status?
        # Safest is to reset assignment_state to NULL (pending) or remove if no confidence?
        # Actually, review queue items come from inference.
        # We should reset assignment_state to 'auto' or 'predicted' if we track that?
        # Current schema defaults to 'auto'.
        # But wait, before confirm it was likely just a detection without association OR an 'auto' association.

        # Strategy: Set assignment_state back to 'auto'
        conn.execute(
            """
            UPDATE photo_person_associations
            SET assignment_state = 'auto'
            WHERE detection_id = ?
            """,
            (detection_id,),
        )

        # Reset review queue status to pending
        conn.execute(
            """
            UPDATE face_review_queue
            SET status = 'pending', resolved_at = NULL
            WHERE detection_id = ?
            """,
            (detection_id,),
        )

    def _undo_review_reject(self, conn: sqlite3.Connection, op_data: dict):
        """Undo a review reject - remove from rejections and reset queue status."""
        detection_id = op_data["detection_id"]
        cluster_id = op_data["cluster_id"]

        # Remove from rejections
        conn.execute(
            """
            DELETE FROM face_rejections
            WHERE detection_id = ? AND cluster_id = ?
            """,
            (detection_id, cluster_id),
        )

        # Restore association (it was deleted on reject)
        # We need to re-insert it. But we don't have the original confidence in op_data for reject?
        # We should probably have stored it.
        # However, for now, we can try to restore it if we can find the embedding?
        # Or better - just reset the review queue.
        # The next scan/assign might pick it up?
        # No, that's slow.
        # Ideally `resolve_review_item` should store full context for reject undo.
        # For now, let's just reset the review queue status. The user will see it again.
        # But the association GONE means they can't see the face in the cluster anymore (which is correct for pending).
        # Wait, pending items usually SHOW UP in the review queue.
        # So we just need to reset the queue status.

        conn.execute(
            """
            UPDATE face_review_queue
            SET status = 'pending', resolved_at = NULL
            WHERE detection_id = ?
            """,
            (detection_id,),
        )

        # If we really want to restore the association causing the suggestion, we might need to rely on the
        # background process or store more data.
        # But typically, the review queue item itself contains candidate_cluster_id.
        # So just making it pending again makes it appear in the queue.

    def _undo_hide(self, conn: sqlite3.Connection, op_data: dict):
        """Undo a hide operation."""
        cluster_id = op_data["cluster_id"]
        previous_hidden = op_data.get("previous_hidden", 0)
        conn.execute(
            """
            UPDATE face_clusters SET hidden = ? WHERE cluster_id = ?
        """,
            (previous_hidden, cluster_id),
        )

    def _undo_reject(self, conn: sqlite3.Connection, op_data: dict):
        """Undo a reject operation - restore association and remove rejection."""
        detection_id = op_data["detection_id"]
        cluster_id = op_data["cluster_id"]
        previous_state = op_data.get("previous_state")

        # Remove from rejections
        conn.execute(
            """
            DELETE FROM face_rejections
            WHERE detection_id = ? AND cluster_id = ?
        """,
            (detection_id, cluster_id),
        )

        # Restore association if we have the snapshot
        if previous_state:
            conn.execute(
                """
                INSERT OR REPLACE INTO photo_person_associations
                (photo_path, cluster_id, detection_id, confidence, assignment_state, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    previous_state["photo_path"],
                    previous_state["cluster_id"],
                    previous_state["detection_id"],
                    previous_state["confidence"],
                    previous_state.get("assignment_state", "auto"),
                    previous_state["created_at"],
                ),
            )
            self._update_cluster_counts_conn(conn, cluster_id)

    def _undo_rename(self, conn: sqlite3.Connection, op_data: dict):
        """Undo a rename operation."""
        cluster_id = op_data["cluster_id"]
        previous_label = op_data.get("previous_label")
        conn.execute(
            """
            UPDATE face_clusters SET label = ? WHERE cluster_id = ?
        """,
            (previous_label, cluster_id),
        )

    def _undo_merge(self, conn: sqlite3.Connection, op_data: dict):
        """Undo a merge operation - restore original clusters."""
        # Restore the deleted cluster
        deleted_cluster = op_data.get("deleted_cluster")
        if deleted_cluster:
            import base64

            prototype = None
            if deleted_cluster.get("prototype_embedding"):
                prototype = base64.b64decode(deleted_cluster["prototype_embedding"])

            conn.execute(
                """
                INSERT INTO face_clusters
                (cluster_id, label, face_count, photo_count, hidden,
                 prototype_embedding, prototype_updated_at, prototype_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    deleted_cluster["cluster_id"],
                    deleted_cluster.get("label"),
                    deleted_cluster.get("face_count", 0),
                    deleted_cluster.get("photo_count", 0),
                    deleted_cluster.get("hidden", 0),
                    prototype,
                    deleted_cluster.get("prototype_updated_at"),
                    deleted_cluster.get("prototype_count", 0),
                ),
            )

        # Restore original associations
        moved_faces = op_data.get("moved_faces", [])
        for face in moved_faces:
            # Remove from target cluster
            conn.execute(
                """
                DELETE FROM photo_person_associations
                WHERE detection_id = ? AND cluster_id = ?
            """,
                (face["detection_id"], op_data["target_cluster_id"]),
            )

            # Re-add to original cluster
            conn.execute(
                """
                INSERT INTO photo_person_associations
                (photo_path, cluster_id, detection_id, confidence, assignment_state)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    face["photo_path"],
                    face["original_cluster_id"],
                    face["detection_id"],
                    face["confidence"],
                    face.get("assignment_state", "auto"),
                ),
            )

        # Update counts
        self._update_cluster_counts_conn(conn, op_data["target_cluster_id"])
        if deleted_cluster:
            self._update_cluster_counts_conn(conn, deleted_cluster["cluster_id"])

    def _undo_split(self, conn: sqlite3.Connection, op_data: dict):
        """Undo a split operation - move faces back and delete new cluster."""
        new_cluster_id = op_data["new_cluster_id"]
        original_mappings = op_data.get("original_mappings", {})

        # Move faces back to original clusters
        for detection_id, original_cluster_id in original_mappings.items():
            # Get photo path
            row = conn.execute(
                """
                SELECT photo_path, confidence, assignment_state
                FROM photo_person_associations
                WHERE detection_id = ? AND cluster_id = ?
            """,
                (detection_id, new_cluster_id),
            ).fetchone()

            if row:
                conn.execute(
                    """
                    DELETE FROM photo_person_associations
                    WHERE detection_id = ? AND cluster_id = ?
                """,
                    (detection_id, new_cluster_id),
                )

                conn.execute(
                    """
                    INSERT INTO photo_person_associations
                    (photo_path, cluster_id, detection_id, confidence, assignment_state)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (row[0], original_cluster_id, detection_id, row[1], row[2]),
                )

                self._update_cluster_counts_conn(conn, original_cluster_id)

        # Delete the new cluster
        conn.execute("DELETE FROM face_clusters WHERE cluster_id = ?", (new_cluster_id,))

    def _undo_move(self, conn: sqlite3.Connection, op_data: dict):
        """Undo a move operation."""
        detection_id = op_data["detection_id"]
        from_cluster = op_data["from_cluster_id"]
        to_cluster = op_data["to_cluster_id"]
        original_state = op_data.get("original_state")

        # Remove from target
        conn.execute(
            """
            DELETE FROM photo_person_associations
            WHERE detection_id = ? AND cluster_id = ?
        """,
            (detection_id, to_cluster),
        )

        # Restore to original
        if original_state:
            conn.execute(
                """
                INSERT INTO photo_person_associations
                (photo_path, cluster_id, detection_id, confidence, assignment_state)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    original_state["photo_path"],
                    original_state["cluster_id"],
                    original_state["detection_id"],
                    original_state["confidence"],
                    original_state.get("assignment_state", "auto"),
                ),
            )

        self._update_cluster_counts_conn(conn, from_cluster)
        self._update_cluster_counts_conn(conn, to_cluster)

    def _update_cluster_counts_conn(self, conn: sqlite3.Connection, cluster_id: str):
        """Update face and photo counts for a cluster using an existing connection."""
        face_count = conn.execute(
            """
            SELECT COUNT(*) FROM photo_person_associations WHERE cluster_id = ?
        """,
            (cluster_id,),
        ).fetchone()[0]

        photo_count = conn.execute(
            """
            SELECT COUNT(DISTINCT photo_path) FROM photo_person_associations WHERE cluster_id = ?
        """,
            (cluster_id,),
        ).fetchone()[0]

        conn.execute(
            """
            UPDATE face_clusters
            SET face_count = ?, photo_count = ?, updated_at = CURRENT_TIMESTAMP
            WHERE cluster_id = ?
        """,
            (face_count, photo_count, cluster_id),
        )

    # ===================================================================
    # Phase 0: Split Flow (Move Faces to New Person)
    # ===================================================================

    def split_faces_to_new_person(self, detection_ids: List[str], new_label: Optional[str] = None) -> str:
        """
        Move selected faces from their current clusters to a new person.

        Args:
            detection_ids: List of face detection IDs to move
            new_label: Optional name for the new person

        Returns:
            The new cluster_id
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            # Gather original mappings for undo
            original_mappings = {}
            face_details = []

            for det_id in detection_ids:
                row = conn.execute(
                    """
                    SELECT photo_path, cluster_id, detection_id, confidence, assignment_state
                    FROM photo_person_associations
                    WHERE detection_id = ?
                """,
                    (det_id,),
                ).fetchone()

                if row:
                    original_mappings[det_id] = row["cluster_id"]
                    face_details.append(dict(row))

            if not face_details:
                raise ValueError("No valid faces found for the provided detection_ids")

            # Create new cluster
            new_cluster_id = self.add_face_cluster(label=new_label)

            # Log for undo
            self._log_operation(
                conn,
                "split",
                {
                    "new_cluster_id": new_cluster_id,
                    "detection_ids": detection_ids,
                    "original_mappings": original_mappings,
                },
            )

            # Move faces to new cluster
            for face in face_details:
                # Remove from old cluster
                conn.execute(
                    """
                    DELETE FROM photo_person_associations
                    WHERE detection_id = ? AND cluster_id = ?
                """,
                    (face["detection_id"], face["cluster_id"]),
                )

                # Add to new cluster
                conn.execute(
                    """
                    INSERT INTO photo_person_associations
                    (photo_path, cluster_id, detection_id, confidence, assignment_state)
                    VALUES (?, ?, ?, ?, 'user_confirmed')
                """,
                    (
                        face["photo_path"],
                        new_cluster_id,
                        face["detection_id"],
                        face["confidence"],
                    ),
                )

                # Update counts on old cluster
                self._update_cluster_counts_conn(conn, face["cluster_id"])

            # Update counts on new cluster
            self._update_cluster_counts_conn(conn, new_cluster_id)

            logger.info(f"Split {len(detection_ids)} faces to new cluster {new_cluster_id}")
            return new_cluster_id

    def move_face_to_cluster(self, detection_id: str, to_cluster_id: str) -> bool:
        """
        Move a single face to a different cluster.

        Args:
            detection_id: The face to move
            to_cluster_id: Target cluster

        Returns:
            True if successful
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            # Get current association
            row = conn.execute(
                """
                SELECT photo_path, cluster_id, detection_id, confidence, assignment_state
                FROM photo_person_associations
                WHERE detection_id = ?
            """,
                (detection_id,),
            ).fetchone()

            if not row:
                raise ValueError(f"No association found for detection {detection_id}")

            from_cluster_id = row["cluster_id"]

            if from_cluster_id == to_cluster_id:
                return True  # Already in target cluster

            # Log for undo
            self._log_operation(
                conn,
                "move",
                {
                    "detection_id": detection_id,
                    "from_cluster_id": from_cluster_id,
                    "to_cluster_id": to_cluster_id,
                    "original_state": dict(row),
                },
            )

            # Remove from old cluster
            conn.execute(
                """
                DELETE FROM photo_person_associations
                WHERE detection_id = ? AND cluster_id = ?
            """,
                (detection_id, from_cluster_id),
            )

            # Add to new cluster
            conn.execute(
                """
                INSERT INTO photo_person_associations
                (photo_path, cluster_id, detection_id, confidence, assignment_state)
                VALUES (?, ?, ?, ?, 'user_confirmed')
            """,
                (row["photo_path"], to_cluster_id, detection_id, row["confidence"]),
            )

            # Update counts
            self._update_cluster_counts_conn(conn, from_cluster_id)
            self._update_cluster_counts_conn(conn, to_cluster_id)

            return True

    # ===================================================================
    # Phase 0: Enhanced Merge with Undo Support
    # ===================================================================

    def merge_clusters_with_undo(self, source_cluster_id: str, target_cluster_id: str) -> bool:
        """
        Merge source cluster into target cluster with full undo support.

        Args:
            source_cluster_id: Cluster to be merged (will be deleted)
            target_cluster_id: Cluster to merge into (will be kept)

        Returns:
            True if successful
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            # Capture source cluster state for undo
            source_cluster = self._get_cluster_snapshot(conn, source_cluster_id)
            if not source_cluster:
                raise ValueError(f"Source cluster {source_cluster_id} not found")

            # Get all faces being moved
            moved_faces = []
            rows = conn.execute(
                """
                SELECT photo_path, cluster_id, detection_id, confidence, assignment_state
                FROM photo_person_associations
                WHERE cluster_id = ?
            """,
                (source_cluster_id,),
            ).fetchall()

            for row in rows:
                moved_faces.append(
                    {
                        "detection_id": row["detection_id"],
                        "photo_path": row["photo_path"],
                        "original_cluster_id": source_cluster_id,
                        "confidence": row["confidence"],
                        "assignment_state": row["assignment_state"],
                    }
                )

            # Log for undo
            self._log_operation(
                conn,
                "merge",
                {
                    "source_cluster_id": source_cluster_id,
                    "target_cluster_id": target_cluster_id,
                    "deleted_cluster": source_cluster,
                    "moved_faces": moved_faces,
                },
            )

            # Move all faces to target cluster
            for face in moved_faces:
                conn.execute(
                    """
                    UPDATE photo_person_associations
                    SET cluster_id = ?
                    WHERE detection_id = ? AND cluster_id = ?
                """,
                    (target_cluster_id, face["detection_id"], source_cluster_id),
                )

            # Delete source cluster
            conn.execute("DELETE FROM face_clusters WHERE cluster_id = ?", (source_cluster_id,))

            # Update target cluster counts
            self._update_cluster_counts_conn(conn, target_cluster_id)

            # Recompute prototype for target cluster
            self._recompute_prototype(conn, target_cluster_id)

            logger.info(f"Merged cluster {source_cluster_id} into {target_cluster_id}")
            return True

    # ===================================================================
    # Phase 0: Prototype Embedding Management
    # ===================================================================

    def _recompute_prototype(self, conn: sqlite3.Connection, cluster_id: str):
        """
        Recompute prototype embedding for a cluster.
        Uses centroid of confirmed faces only, excluding low-quality faces.
        """
        # Get embeddings from confirmed, high-quality faces
        rows = conn.execute(
            """
            SELECT fd.embedding
            FROM photo_person_associations ppa
            JOIN face_detections fd ON ppa.detection_id = fd.detection_id
            WHERE ppa.cluster_id = ?
            AND (ppa.assignment_state = 'user_confirmed' OR ppa.assignment_state IS NULL)
            AND fd.embedding IS NOT NULL
            AND (fd.quality_score IS NULL OR fd.quality_score >= 0.5)
        """,
            (cluster_id,),
        ).fetchall()

        if not rows:
            # Fallback: use all faces with embeddings
            rows = conn.execute(
                """
                SELECT fd.embedding
                FROM photo_person_associations ppa
                JOIN face_detections fd ON ppa.detection_id = fd.detection_id
                WHERE ppa.cluster_id = ?
                AND fd.embedding IS NOT NULL
            """,
                (cluster_id,),
            ).fetchall()

        if not rows:
            return

        # Compute centroid
        embeddings = []
        for row in rows:
            if row[0]:
                try:
                    emb = json.loads(row[0]) if isinstance(row[0], str) else np.frombuffer(row[0], dtype=np.float32)
                    embeddings.append(np.array(emb, dtype=np.float32))
                except Exception:
                    continue

        if not embeddings:
            return

        centroid = np.mean(embeddings, axis=0)
        # L2 normalize
        centroid = centroid / (np.linalg.norm(centroid) + 1e-8)

        # Store
        conn.execute(
            """
            UPDATE face_clusters
            SET prototype_embedding = ?,
                prototype_updated_at = CURRENT_TIMESTAMP,
                prototype_count = ?
            WHERE cluster_id = ?
        """,
            (centroid.tobytes(), len(embeddings), cluster_id),
        )

    def recompute_all_prototypes(self):
        """Recompute prototypes for all clusters."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cluster_ids = [row[0] for row in conn.execute("SELECT cluster_id FROM face_clusters").fetchall()]

            for cluster_id in cluster_ids:
                self._recompute_prototype(conn, cluster_id)
                self._compute_representative_face(conn, cluster_id)

            logger.info(f"Recomputed prototypes for {len(cluster_ids)} clusters")

    def _compute_representative_face(self, conn: sqlite3.Connection, cluster_id: str) -> str | None:
        """
        Select the best representative face for a cluster using a deterministic algorithm.

        Scoring criteria (Phase 5.3):
        1. User-confirmed faces get priority (weight: +0.5)
        2. Quality score (weight: 0.4 * quality_score)
        3. Small recency bonus (weight: 0.1 * recency_factor)
        4. Exclude low quality faces (quality < 0.3)

        Returns:
            detection_id of the selected representative, or None if cluster is empty
        """
        rows = conn.execute(
            """
            SELECT
                fd.detection_id,
                fd.quality_score,
                ppa.assignment_state,
                ppa.created_at
            FROM photo_person_associations ppa
            JOIN face_detections fd ON ppa.detection_id = fd.detection_id
            WHERE ppa.cluster_id = ?
            AND (fd.quality_score IS NULL OR fd.quality_score >= 0.3)
            ORDER BY ppa.created_at DESC
        """,
            (cluster_id,),
        ).fetchall()

        if not rows:
            return None

        # Find most recent timestamp for recency normalization
        from datetime import datetime

        scores = []
        for row in rows:
            detection_id = row[0]
            quality = row[1] if row[1] is not None else 0.5  # Default quality
            assignment_state = row[2]
            created_at_str = row[3]

            score = 0.0

            # 1. Confirmed bonus (+0.5)
            if assignment_state == "user_confirmed":
                score += 0.5

            # 2. Quality component (40% weight)
            score += 0.4 * quality

            # 3. Recency bonus (10% weight) - newer is better
            try:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                # Recency bonus: faces added in last 30 days get up to 0.1 bonus
                age_days = (datetime.now() - created_at.replace(tzinfo=None)).days
                recency_factor = max(0.0, 1.0 - (age_days / 30.0))
                score += 0.1 * recency_factor
            except Exception:
                pass  # No recency bonus if date parsing fails

            scores.append((detection_id, score))

        # Sort by score descending, then by detection_id for determinism
        scores.sort(key=lambda x: (-x[1], x[0]))
        best_detection_id = scores[0][0]

        # Update the cluster's representative
        conn.execute(
            """
            UPDATE face_clusters
            SET representative_detection_id = ?,
                representative_updated_at = CURRENT_TIMESTAMP
            WHERE cluster_id = ?
        """,
            (best_detection_id, cluster_id),
        )

        return best_detection_id

    def get_representative_face(self, cluster_id: str) -> dict | None:
        """
        Get the representative face for a cluster.

        Returns dict with detection_id, photo_path, bounding_box, quality_score
        or None if no representative is set.
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            row = conn.execute(
                """
                SELECT
                    fc.representative_detection_id,
                    fd.photo_path,
                    fd.bounding_box,
                    fd.quality_score
                FROM face_clusters fc
                LEFT JOIN face_detections fd
                    ON fc.representative_detection_id = fd.detection_id
                WHERE fc.cluster_id = ?
            """,
                (cluster_id,),
            ).fetchone()

            if not row or not row["representative_detection_id"]:
                return None

            return {
                "detection_id": row["representative_detection_id"],
                "photo_path": row["photo_path"],
                "bounding_box": row["bounding_box"],
                "quality_score": row["quality_score"],
            }

    def recompute_representative_face(self, cluster_id: str) -> str | None:
        """Recompute and return the representative face for a specific cluster."""
        with sqlite3.connect(str(self.db_path)) as conn:
            return self._compute_representative_face(conn, cluster_id)

    # ===================================================================
    # Phase 5.4: Merge Suggestions
    # ===================================================================

    def get_merge_suggestions(
        self, similarity_threshold: float = 0.62, max_suggestions: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find cluster pairs that might be the same person based on prototype similarity.

        Conservative criteria:
        1. Prototype similarity >= threshold (default 0.62)
        2. NO co-occurrence conflict (both clusters appearing in same photo = HARD BLOCK)

        Returns:
            List of merge suggestion dicts with:
            - cluster_a_id, cluster_a_label, cluster_a_face_count
            - cluster_b_id, cluster_b_label, cluster_b_face_count
            - similarity: prototype similarity score
            - representative_a: {photo_path, detection_id}
            - representative_b: {photo_path, detection_id}
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            # Get all clusters with their prototype embeddings
            clusters = conn.execute(
                """
                SELECT
                    cluster_id,
                    label,
                    prototype_embedding,
                    representative_detection_id
                FROM face_clusters
                WHERE prototype_embedding IS NOT NULL
            """
            ).fetchall()

            if len(clusters) < 2:
                return []

            # Get face counts for each cluster
            face_counts = {}
            for row in conn.execute(
                """
                SELECT cluster_id, COUNT(*) as cnt
                FROM photo_person_associations
                GROUP BY cluster_id
            """
            ).fetchall():
                face_counts[row["cluster_id"]] = row["cnt"]

            # Build co-occurrence map: clusters that share any photo
            # This is a HARD BLOCK for merge suggestions
            co_occurring = set()
            photo_clusters = conn.execute(
                """
                SELECT photo_path, GROUP_CONCAT(DISTINCT cluster_id) as clusters
                FROM photo_person_associations
                GROUP BY photo_path
                HAVING COUNT(DISTINCT cluster_id) > 1
            """
            ).fetchall()

            for row in photo_clusters:
                cluster_ids = row["clusters"].split(",")
                # Add all pairs that co-occur
                for i in range(len(cluster_ids)):
                    for j in range(i + 1, len(cluster_ids)):
                        pair = tuple(sorted([cluster_ids[i], cluster_ids[j]]))
                        co_occurring.add(pair)

            # Get representative face info
            rep_info = {}
            for row in conn.execute(
                """
                SELECT fc.cluster_id, fd.photo_path, fd.detection_id
                FROM face_clusters fc
                JOIN face_detections fd ON fc.representative_detection_id = fd.detection_id
                WHERE fc.representative_detection_id IS NOT NULL
            """
            ).fetchall():
                rep_info[row["cluster_id"]] = {
                    "photo_path": row["photo_path"],
                    "detection_id": row["detection_id"],
                }

            # Compare prototype embeddings pairwise
            suggestions = []
            cluster_list = list(clusters)

            for i in range(len(cluster_list)):
                for j in range(i + 1, len(cluster_list)):
                    c1 = cluster_list[i]
                    c2 = cluster_list[j]
                    cluster_a_id = c1["cluster_id"]
                    cluster_b_id = c2["cluster_id"]

                    # Check co-occurrence (HARD BLOCK)
                    pair = tuple(sorted([cluster_a_id, cluster_b_id]))
                    if pair in co_occurring:
                        continue  # Skip - they appear in the same photo

                    # Compare prototype embeddings
                    try:
                        emb1 = np.frombuffer(c1["prototype_embedding"], dtype=np.float32)
                        emb2 = np.frombuffer(c2["prototype_embedding"], dtype=np.float32)

                        # Cosine similarity (embeddings should be L2-normalized)
                        similarity = float(np.dot(emb1, emb2))

                        if similarity >= similarity_threshold:
                            suggestions.append(
                                {
                                    "cluster_a_id": cluster_a_id,
                                    "cluster_a_label": c1["label"] or f"Person {cluster_a_id}",
                                    "cluster_a_face_count": face_counts.get(cluster_a_id, 0),
                                    "cluster_b_id": cluster_b_id,
                                    "cluster_b_label": c2["label"] or f"Person {cluster_b_id}",
                                    "cluster_b_face_count": face_counts.get(cluster_b_id, 0),
                                    "similarity": round(similarity, 3),
                                    "representative_a": rep_info.get(cluster_a_id),
                                    "representative_b": rep_info.get(cluster_b_id),
                                }
                            )
                    except Exception as e:
                        logger.warning(f"Error comparing clusters {cluster_a_id} and {cluster_b_id}: {e}")

            # Sort by similarity (highest first) and limit
            suggestions.sort(key=lambda x: x["similarity"], reverse=True)
            return suggestions[:max_suggestions]

    def dismiss_merge_suggestion(self, cluster_a_id: str, cluster_b_id: str) -> bool:
        """
        Dismiss a merge suggestion so it won't appear again.
        Stores in a dismissals table.
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            # Create table if not exists
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS merge_dismissals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cluster_a_id TEXT NOT NULL,
                    cluster_b_id TEXT NOT NULL,
                    dismissed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(cluster_a_id, cluster_b_id)
                )
            """
            )

            # Normalize order
            pair = tuple(sorted([cluster_a_id, cluster_b_id]))
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO merge_dismissals (cluster_a_id, cluster_b_id)
                    VALUES (?, ?)
                """,
                    pair,
                )
                return True
            except Exception as e:
                logger.error(f"Error dismissing merge suggestion: {e}")
                return False

    # ===================================================================
    # Phase 6: Privacy Controls
    # ===================================================================

    def set_person_indexing_enabled(self, cluster_id: str, enabled: bool, reason: str | None = None) -> bool:
        """
        Enable or disable auto-assignment to a specific person cluster.

        When disabled, PrototypeAssigner will skip this cluster when
        finding candidates for new face detections.
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            try:
                conn.execute(
                    """
                    UPDATE face_clusters
                    SET indexing_disabled = ?,
                        indexing_disabled_at = CASE WHEN ? = 0 THEN NULL ELSE CURRENT_TIMESTAMP END,
                        indexing_disabled_reason = ?
                    WHERE cluster_id = ?
                """,
                    (0 if enabled else 1, 0 if enabled else 1, reason, cluster_id),
                )
                return True
            except Exception as e:
                logger.error(f"Error setting indexing toggle: {e}")
                return False

    def get_person_indexing_status(self, cluster_id: str) -> dict:
        """Get the indexing status for a specific person cluster."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT indexing_disabled, indexing_disabled_at, indexing_disabled_reason
                FROM face_clusters
                WHERE id = ?
            """,
                (cluster_id,),
            ).fetchone()

            if not row:
                return {"error": "Cluster not found"}

            return {
                "enabled": row["indexing_disabled"] != 1,
                "disabled_at": row["indexing_disabled_at"],
                "reason": row["indexing_disabled_reason"],
            }

    def get_indexing_enabled_cluster_ids(self) -> List[str]:
        """Get list of cluster IDs that have indexing enabled (not disabled)."""
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute(
                """
                SELECT cluster_id FROM face_clusters
                WHERE indexing_disabled = 0 OR indexing_disabled IS NULL
            """
            ).fetchall()
            return [row[0] for row in rows]

    # Global settings methods
    def get_app_setting(self, key: str, default: str | None = None) -> str | None:
        """Get an app setting value."""
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
            return row[0] if row else default

    def set_app_setting(self, key: str, value: str) -> bool:
        """Set an app setting value."""
        with sqlite3.connect(str(self.db_path)) as conn:
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO app_settings (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """,
                    (key, value),
                )
                return True
            except Exception as e:
                logger.error(f"Error setting app setting {key}: {e}")
                return False

    def is_face_indexing_paused(self) -> bool:
        """Check if global face indexing is paused."""
        return self.get_app_setting("faces_indexing_paused", "false") == "true"

    def set_face_indexing_paused(self, paused: bool) -> bool:
        """Pause or resume global face indexing."""
        return self.set_app_setting("faces_indexing_paused", "true" if paused else "false")

    # ===================================================================
    # Phase 0: Unknown Bucket (Unassigned Faces)
    # ===================================================================

    def get_unassigned_faces(self, limit: int = 100, offset: int = 0) -> List[dict]:
        """
        Get faces that are not assigned to any cluster.
        These are faces detected but not yet associated with a person.
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT fd.detection_id, fd.photo_path, fd.bounding_box, fd.quality_score, fd.created_at
                FROM face_detections fd
                LEFT JOIN photo_person_associations ppa ON fd.detection_id = ppa.detection_id
                WHERE ppa.detection_id IS NULL
                ORDER BY fd.created_at DESC
                LIMIT ? OFFSET ?
            """,
                (limit, offset),
            ).fetchall()

            return [dict(row) for row in rows]

    def get_unassigned_face_count(self) -> int:
        """Get count of unassigned faces."""
        with sqlite3.connect(str(self.db_path)) as conn:
            return conn.execute("""
                SELECT COUNT(*)
                FROM face_detections fd
                LEFT JOIN photo_person_associations ppa ON fd.detection_id = ppa.detection_id
                WHERE ppa.detection_id IS NULL
            """).fetchone()[0]

    # ===================================================================
    # Enhanced Rename with Undo
    # ===================================================================

    def rename_cluster_with_undo(self, cluster_id: str, new_label: str) -> bool:
        """Rename a cluster with undo support."""
        with sqlite3.connect(str(self.db_path)) as conn:
            # Get current label
            row = conn.execute("SELECT label FROM face_clusters WHERE cluster_id = ?", (cluster_id,)).fetchone()

            if not row:
                raise ValueError(f"Cluster {cluster_id} not found")

            previous_label = row[0]

            # Log for undo
            self._log_operation(
                conn,
                "rename",
                {
                    "cluster_id": cluster_id,
                    "previous_label": previous_label,
                    "new_label": new_label,
                },
            )

            # Update
            conn.execute(
                """
                UPDATE face_clusters
                SET label = ?, updated_at = CURRENT_TIMESTAMP
                WHERE cluster_id = ?
            """,
                (new_label, cluster_id),
            )

            return True

    # ===================================================================
    # Phase 2: Mixed Cluster Detection & Review Queue
    # ===================================================================

    def get_cluster_coherence(self, cluster_id: str) -> Dict[str, Any]:
        """
        Analyze cluster coherence to detect mixed clusters.

        Returns:
            - coherence_score: 0-1 (higher = more coherent/single person)
            - variance: embedding variance (higher = more diverse faces)
            - low_quality_ratio: fraction of low quality faces
            - is_mixed_suspected: bool if we suspect multiple people
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            # Get all faces in cluster with embeddings and quality
            rows = conn.execute(
                """
                SELECT
                    fd.embedding,
                    fd.quality_score,
                    ppa.confidence,
                    ppa.assignment_state
                FROM photo_person_associations ppa
                JOIN face_detections fd ON ppa.detection_id = fd.detection_id
                WHERE ppa.cluster_id = ?
            """,
                (cluster_id,),
            ).fetchall()

            if not rows:
                return {
                    "coherence_score": 1.0,
                    "variance": 0.0,
                    "low_quality_ratio": 0.0,
                    "is_mixed_suspected": False,
                    "face_count": 0,
                }

            embeddings = []
            quality_scores = []
            confidences = []

            for row in rows:
                if row["embedding"]:
                    try:
                        emb = np.frombuffer(row["embedding"], dtype=np.float32)
                        embeddings.append(emb)
                    except Exception:
                        pass

                if row["quality_score"] is not None:
                    quality_scores.append(row["quality_score"])
                if row["confidence"] is not None:
                    confidences.append(row["confidence"])

            face_count = len(rows)

            # Calculate metrics
            if len(embeddings) < 2:
                variance = 0.0
                coherence_score = 1.0
            else:
                # Calculate pairwise distances
                emb_array = np.array(embeddings)
                centroid = np.mean(emb_array, axis=0)
                distances = [np.linalg.norm(e - centroid) for e in emb_array]
                variance = float(np.var(distances))

                # Coherence is inverse of variance, normalized
                coherence_score = max(0.0, 1.0 - min(variance * 5, 1.0))

            # Low quality ratio
            low_quality_count = sum(1 for q in quality_scores if q < 0.5)
            low_quality_ratio = low_quality_count / len(quality_scores) if quality_scores else 0.0

            # Mixed cluster heuristic:
            # - High variance (> 0.15) OR
            # - Low coherence (< 0.5) AND high low-quality ratio (> 0.4)
            is_mixed_suspected = variance > 0.15 or (coherence_score < 0.5 and low_quality_ratio > 0.4)

            return {
                "coherence_score": coherence_score,
                "variance": variance,
                "low_quality_ratio": low_quality_ratio,
                "is_mixed_suspected": is_mixed_suspected,
                "face_count": face_count,
                "avg_confidence": sum(confidences) / len(confidences) if confidences else 0.0,
            }

    def get_gray_zone_faces(
        self,
        similarity_min: float = 0.50,
        similarity_max: float = 0.55,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get faces in the gray-zone that need human review.


        These are faces with confidence between similarity_min and similarity_max,
        which are uncertain assignments that should be reviewed by the user.
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            rows = conn.execute(
                """
                SELECT
                    ppa.detection_id,
                    ppa.photo_path,
                    ppa.cluster_id,
                    ppa.confidence,
                    ppa.assignment_state,
                    fc.label as cluster_label,
                    fd.quality_score
                FROM photo_person_associations ppa
                JOIN face_clusters fc ON ppa.cluster_id = fc.cluster_id
                JOIN face_detections fd ON ppa.detection_id = fd.detection_id
                WHERE ppa.confidence >= ? AND ppa.confidence <= ?
                AND ppa.assignment_state = 'auto'
                ORDER BY ppa.confidence ASC
                LIMIT ?
            """,
                (similarity_min, similarity_max, limit),
            ).fetchall()

            return [
                {
                    "detection_id": row["detection_id"],
                    "photo_path": row["photo_path"],
                    "cluster_id": row["cluster_id"],
                    "cluster_label": row["cluster_label"],
                    "confidence": row["confidence"],
                    "quality_score": row["quality_score"],
                    "assignment_state": row["assignment_state"],
                }
                for row in rows
            ]

    def get_mixed_clusters(self, threshold: float = 0.5) -> List[Dict[str, Any]]:
        """
        Get all clusters that are suspected to contain multiple people.

        Args:
            threshold: Coherence score below which a cluster is suspicious

        Returns:
            List of cluster info with coherence analysis
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            # Get all visible clusters
            rows = conn.execute("""
                SELECT cluster_id, label, face_count
                FROM face_clusters
                WHERE hidden = 0
            """).fetchall()

            mixed_clusters = []
            for row in rows:
                if row["face_count"] < 3:
                    continue  # Need at least 3 faces to detect mixing

                coherence = self.get_cluster_coherence(row["cluster_id"])

                if coherence["is_mixed_suspected"] or coherence["coherence_score"] < threshold:
                    mixed_clusters.append(
                        {
                            "cluster_id": row["cluster_id"],
                            "label": row["label"],
                            "face_count": row["face_count"],
                            **coherence,
                        }
                    )

            # Sort by coherence (worst first)
            mixed_clusters.sort(key=lambda x: x["coherence_score"])

            return mixed_clusters

    # ===================================================================
    # Phase 3: Speed & Scale - Prototype-based Assignment
    # ===================================================================

    def build_embedding_index(self, backend: str = "auto"):
        """
        Build an embedding index from all cluster prototypes.

        Args:
            backend: 'auto' (default), 'linear', or 'faiss'
                    'auto' chooses based on cluster count (FAISS for 1000+)

        Returns:
            EmbeddingIndex populated with all cluster prototypes
        """
        from server.face_embedding_index import create_embedding_index

        # Count clusters to determine optimal backend
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM face_clusters
                WHERE hidden = 0
                AND (indexing_disabled = 0 OR indexing_disabled IS NULL)
                AND prototype_embedding IS NOT NULL
            """)
            cluster_count = cursor.fetchone()[0]

        # Create index with appropriate backend
        index = create_embedding_index(backend, num_prototypes_hint=cluster_count)

        # Load all prototypes efficiently
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            rows = conn.execute("""
                SELECT cluster_id, label, prototype_embedding
                FROM face_clusters
                WHERE hidden = 0
                AND (indexing_disabled = 0 OR indexing_disabled IS NULL)
                AND prototype_embedding IS NOT NULL
            """).fetchall()

            # Prepare for bulk loading if supported
            prototypes = {}
            for row in rows:
                try:
                    embedding = np.frombuffer(row["prototype_embedding"], dtype=np.float32)
                    prototypes[row["cluster_id"]] = (embedding, row["label"])
                except Exception as e:
                    logger.warning(f"Failed to load prototype for {row['cluster_id']}: {e}")

            # Use bulk loading if available (FAISS), otherwise add individually
            if hasattr(index, "bulk_load"):
                index.bulk_load(prototypes)
            else:
                for cluster_id, (embedding, label) in prototypes.items():
                    index.add_prototype(cluster_id, embedding, label)

            backend_type = getattr(index, "get_stats", lambda: {}).get("index_type", "unknown")
            logger.info(f"Built {backend_type} embedding index with {index.count()} prototypes")

        return index

    def assign_new_face(
        self,
        detection_id: str,
        embedding: np.ndarray,
        auto_assign_min: float = 0.55,
        review_min: float = 0.50,
        index=None,
    ) -> Dict[str, Any]:
        """
        Assign a new face to an existing cluster using prototype matching.

        Args:
            detection_id: Face detection ID
            embedding: Face embedding vector
            auto_assign_min: Threshold for automatic assignment (default 0.55)
            review_min: Threshold for review queue (default 0.50)
            index: Optional pre-built EmbeddingIndex (builds one if not provided)

        Returns:
            {
                'action': 'auto_assign' | 'review' | 'unknown',
                'cluster_id': str | None,
                'cluster_label': str | None,
                'similarity': float,
                'detection_id': str
            }
        """
        from server.face_embedding_index import PrototypeAssigner

        # Build index if not provided
        if index is None:
            index = self.build_embedding_index()

        # Create assigner with thresholds
        assigner = PrototypeAssigner(index=index, auto_assign_min=auto_assign_min, review_min=review_min)

        # Get assignment
        result = assigner.assign_face(embedding)
        result["detection_id"] = detection_id

        # If auto-assign, create the association
        if result["action"] == "auto_assign" and result["cluster_id"]:
            with sqlite3.connect(str(self.db_path)) as conn:
                # Get photo path for this detection
                row = conn.execute(
                    "SELECT photo_path FROM face_detections WHERE detection_id = ?",
                    (detection_id,),
                ).fetchone()

                if row:
                    # Check if not rejected
                    rejected = conn.execute(
                        """
                        SELECT 1 FROM face_rejections
                        WHERE detection_id = ? AND cluster_id = ?
                    """,
                        (detection_id, result["cluster_id"]),
                    ).fetchone()

                    if not rejected:
                        # Create association
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO photo_person_associations
                            (photo_path, cluster_id, detection_id, confidence, assignment_state)
                            VALUES (?, ?, ?, ?, 'auto')
                        """,
                            (
                                row[0],
                                result["cluster_id"],
                                detection_id,
                                result["similarity"],
                            ),
                        )

                        # Update cluster counts
                        self._update_cluster_counts_conn(conn, result["cluster_id"])

                        result["assigned"] = True
                    else:
                        # Was rejected, don't auto-assign
                        result["action"] = "unknown"
                        result["assigned"] = False
                        result["reason"] = "Previously rejected"

        # If review action, add to review queue
        elif result["action"] == "review" and result["cluster_id"]:
            self.add_to_review_queue(
                detection_id=detection_id,
                candidate_cluster_id=result["cluster_id"],
                similarity=result["similarity"],
                reason="gray_zone",
            )
            result["added_to_review"] = True

        return result

    def batch_assign_new_faces(
        self,
        faces: List[Tuple[str, np.ndarray]],
        auto_assign_min: float = 0.55,
        review_min: float = 0.50,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Assign multiple new faces to clusters efficiently.

        Args:
            faces: List of (detection_id, embedding) tuples
            auto_assign_min: Threshold for automatic assignment
            review_min: Threshold for review queue

        Returns:
            Dict of detection_id -> assignment result
        """
        # Build index once for all faces
        index = self.build_embedding_index()

        results = {}
        for detection_id, embedding in faces:
            results[detection_id] = self.assign_new_face(
                detection_id=detection_id,
                embedding=embedding,
                auto_assign_min=auto_assign_min,
                review_min=review_min,
                index=index,
            )

        # Summary
        auto_count = sum(1 for r in results.values() if r["action"] == "auto_assign")
        review_count = sum(1 for r in results.values() if r["action"] == "review")
        unknown_count = sum(1 for r in results.values() if r["action"] == "unknown")

        logger.info(f"Batch assignment: {auto_count} auto, {review_count} review, {unknown_count} unknown")

        return results

    # ===================================================================
    # Phase 4: Search & Retrieval
    # ===================================================================

    def find_similar_faces(
        self,
        detection_id: str,
        limit: int = 20,
        threshold: float = 0.5,
        include_same_cluster: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Find faces similar to a given face detection with extended options.

        "Find more like this face" - useful for:
        - Discovering unclustered similar faces
        - Finding potential merge candidates
        - Quality control (checking for misclassified faces)

        Args:
            detection_id: The reference face to find similar ones
            limit: Maximum number of results
            threshold: Minimum similarity threshold (0-1)
            include_same_cluster: If False, exclude faces from same cluster

        Returns:
            List of similar faces with similarity scores and cluster info
        """

        def _embedding_to_unit_vec(raw: Any) -> Optional[np.ndarray]:
            """Decode an embedding value from SQLite into a unit-normalized float32 vector.

            Historical note: embeddings have been stored both as JSON strings (via json.dumps)
            and as bytes-like blobs. SQLite doesn't enforce column types, so we must handle both.
            """
            if raw is None:
                return None

            try:
                if isinstance(raw, (bytes, bytearray, memoryview)):
                    vec = np.frombuffer(raw, dtype=np.float32)
                elif isinstance(raw, str):
                    vec = np.asarray(json.loads(raw), dtype=np.float32)
                elif isinstance(raw, (list, tuple)):
                    vec = np.asarray(raw, dtype=np.float32)
                else:
                    # Best-effort fallback for other buffer-protocol objects.
                    try:
                        vec = np.frombuffer(raw, dtype=np.float32)  # type: ignore[arg-type]
                    except Exception:
                        vec = np.asarray(raw, dtype=np.float32)
            except Exception as e:
                logger.warning(f"Failed to decode embedding: {e}")
                return None

            if vec.size == 0:
                return None

            return vec / (np.linalg.norm(vec) + 1e-8)

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            # Get the reference face embedding
            ref_row = conn.execute(
                """
                SELECT fd.embedding, fd.photo_path, ppa.cluster_id
                FROM face_detections fd
                LEFT JOIN photo_person_associations ppa ON fd.detection_id = ppa.detection_id
                WHERE fd.detection_id = ?
            """,
                (detection_id,),
            ).fetchone()

            if not ref_row or not ref_row["embedding"]:
                return []

            ref_embedding = _embedding_to_unit_vec(ref_row["embedding"])
            if ref_embedding is None:
                return []
            ref_cluster = ref_row["cluster_id"]

            # Get all other face embeddings
            rows = conn.execute(
                """
                SELECT
                    fd.detection_id,
                    fd.photo_path,
                    fd.embedding,
                    fd.quality_score,
                    ppa.cluster_id,
                    fc.label as cluster_label
                FROM face_detections fd
                LEFT JOIN photo_person_associations ppa ON fd.detection_id = ppa.detection_id
                LEFT JOIN face_clusters fc ON ppa.cluster_id = fc.cluster_id
                WHERE fd.detection_id != ? AND fd.embedding IS NOT NULL
            """,
                (detection_id,),
            ).fetchall()

            results = []
            for row in rows:
                # Skip same cluster if requested
                if not include_same_cluster and ref_cluster is not None and row["cluster_id"] == ref_cluster:
                    continue

                try:
                    embedding = _embedding_to_unit_vec(row["embedding"])
                    if embedding is None:
                        continue

                    # Cosine similarity
                    similarity = float(np.dot(ref_embedding, embedding))

                    if similarity >= threshold:
                        results.append(
                            {
                                "detection_id": row["detection_id"],
                                "photo_path": row["photo_path"],
                                "similarity": similarity,
                                "quality_score": row["quality_score"],
                                "cluster_id": row["cluster_id"],
                                "cluster_label": row["cluster_label"],
                            }
                        )
                except Exception as e:
                    logger.warning(f"Error comparing face {row['detection_id']}: {e}")

            # Sort by similarity (highest first)
            results.sort(key=lambda x: x["similarity"], reverse=True)

            return results[:limit]

    def get_photos_with_people(
        self,
        include_people: List[str],
        exclude_people: Optional[List[str]] = None,
        require_all: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Find photos based on co-occurrence of people.

        Examples:
        - Photos with Alice AND Bob: include_people=['alice_id', 'bob_id'], require_all=True
        - Photos with Alice OR Bob: include_people=['alice_id', 'bob_id'], require_all=False
        - Photos with Alice but NOT Bob: include_people=['alice_id'], exclude_people=['bob_id']

        Args:
            include_people: List of cluster_ids that must appear
            exclude_people: List of cluster_ids that must NOT appear
            require_all: If True, all include_people must be in photo (AND)
                        If False, any of include_people can be in photo (OR)
            limit: Maximum results
            offset: Pagination offset

        Returns:
            {
                'photos': List of photo paths with matched people,
                'total': Total count,
                'limit': limit,
                'offset': offset
            }
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            if not include_people:
                return {"photos": [], "total": 0, "limit": limit, "offset": offset}

            exclude_people = exclude_people or []

            if require_all:
                # All people must be in the photo (AND logic)
                # Get photos that have ALL of the included people
                placeholders = ",".join("?" * len(include_people))

                query = f"""
                    SELECT photo_path, COUNT(DISTINCT cluster_id) as match_count
                    FROM photo_person_associations
                    WHERE cluster_id IN ({placeholders})
                    GROUP BY photo_path
                    HAVING match_count = ?
                """
                params = include_people + [len(include_people)]

            else:
                # Any person can be in the photo (OR logic)
                placeholders = ",".join("?" * len(include_people))

                query = f"""
                    SELECT DISTINCT photo_path
                    FROM photo_person_associations
                    WHERE cluster_id IN ({placeholders})
                """
                params = include_people

            # Get all matching photos first (for count)
            all_photos = conn.execute(query, params).fetchall()
            photo_paths = [row["photo_path"] for row in all_photos]

            # Apply exclusion filter
            if exclude_people and photo_paths:
                exclude_placeholders = ",".join("?" * len(exclude_people))
                path_placeholders = ",".join("?" * len(photo_paths))

                exclude_query = f"""
                    SELECT DISTINCT photo_path
                    FROM photo_person_associations
                    WHERE cluster_id IN ({exclude_placeholders})
                    AND photo_path IN ({path_placeholders})
                """
                excluded = conn.execute(exclude_query, exclude_people + photo_paths).fetchall()
                excluded_paths = {row["photo_path"] for row in excluded}

                photo_paths = [p for p in photo_paths if p not in excluded_paths]

            total = len(photo_paths)

            # Apply pagination
            paginated = photo_paths[offset : offset + limit]

            # Get additional info for each photo
            results = []
            for path in paginated:
                # Get all people in this photo
                people = conn.execute(
                    """
                    SELECT ppa.cluster_id, fc.label
                    FROM photo_person_associations ppa
                    JOIN face_clusters fc ON ppa.cluster_id = fc.cluster_id
                    WHERE ppa.photo_path = ?
                """,
                    (path,),
                ).fetchall()

                results.append(
                    {
                        "photo_path": path,
                        "people": [{"cluster_id": p["cluster_id"], "label": p["label"]} for p in people],
                    }
                )

            return {"photos": results, "total": total, "limit": limit, "offset": offset}

    def get_faces_in_photo(self, photo_path: str) -> List[Dict[str, Any]]:
        """
        Get all faces detected in a photo with full detection details.

        Unlike get_people_in_photo which returns associations, this returns
        detailed face detection info including bounding boxes and quality scores.
        Useful for trust signals (Phase 2).

        Args:
            photo_path: Path to the photo

        Returns:
            List of faces with cluster info, bounding boxes, quality scores
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            rows = conn.execute(
                """
                SELECT
                    ppa.cluster_id,
                    ppa.detection_id,
                    ppa.confidence,
                    ppa.assignment_state,
                    fc.label,
                    fd.bounding_box,
                    fd.quality_score
                FROM photo_person_associations ppa
                JOIN face_clusters fc ON ppa.cluster_id = fc.cluster_id
                JOIN face_detections fd ON ppa.detection_id = fd.detection_id
                WHERE ppa.photo_path = ?
            """,
                (photo_path,),
            ).fetchall()

            return [
                {
                    "cluster_id": row["cluster_id"],
                    "detection_id": row["detection_id"],
                    "label": row["label"],
                    "confidence": row["confidence"],
                    "assignment_state": row["assignment_state"],
                    "bounding_box": json.loads(row["bounding_box"]) if row["bounding_box"] else None,
                    "quality_score": row["quality_score"],
                }
                for row in rows
            ]

    def search_photos_by_face_attributes(
        self,
        min_age: Optional[int] = None,
        max_age: Optional[int] = None,
        emotions: Optional[List[str]] = None,
        gender: Optional[str] = None,
        pose_type: Optional[str] = None,
        min_quality: Optional[float] = None,
        min_confidence: Optional[float] = None,
        min_age_confidence: Optional[float] = None,
        min_emotion_confidence: Optional[float] = None,
        min_pose_confidence: Optional[float] = None,
        min_gender_confidence: Optional[float] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Search photos by face attributes (age, emotion, pose, gender, quality).

        Returns photos with matching face detections and the matched faces.
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            conditions: List[str] = []
            params: List[Any] = []

            if min_age is not None:
                conditions.append("fd.age_estimate >= ?")
                params.append(min_age)
            if max_age is not None:
                conditions.append("fd.age_estimate <= ?")
                params.append(max_age)
            if emotions:
                placeholders = ",".join("?" * len(emotions))
                conditions.append(f"fd.emotion IN ({placeholders})")
                params.extend(emotions)
            if gender:
                conditions.append("fd.gender = ?")
                params.append(gender)
            if pose_type:
                conditions.append("fd.pose_type = ?")
                params.append(pose_type)
            if min_quality is not None:
                conditions.append("COALESCE(fd.overall_quality, fd.quality_score, 0) >= ?")
                params.append(min_quality)
            if min_confidence is not None:
                conditions.append("COALESCE(ppa.confidence, 1.0) >= ?")
                params.append(min_confidence)
            if min_age_confidence is not None:
                conditions.append("fd.age_confidence >= ?")
                params.append(min_age_confidence)
            if min_emotion_confidence is not None:
                conditions.append("fd.emotion_confidence >= ?")
                params.append(min_emotion_confidence)
            if min_pose_confidence is not None:
                conditions.append("fd.pose_confidence >= ?")
                params.append(min_pose_confidence)
            if min_gender_confidence is not None:
                conditions.append("fd.gender_confidence >= ?")
                params.append(min_gender_confidence)

            conditions.append("(fc.hidden = 0 OR ppa.cluster_id IS NULL)")
            where_clause = " AND ".join(conditions) if conditions else "1=1"

            total_row = conn.execute(
                f"""
                SELECT COUNT(DISTINCT fd.photo_path) AS total
                FROM face_detections fd
                LEFT JOIN photo_person_associations ppa ON fd.detection_id = ppa.detection_id
                LEFT JOIN face_clusters fc ON ppa.cluster_id = fc.cluster_id
                WHERE {where_clause}
            """,
                params,
            ).fetchone()

            total = total_row["total"] if total_row else 0

            photo_rows = conn.execute(
                f"""
                SELECT DISTINCT fd.photo_path
                FROM face_detections fd
                LEFT JOIN photo_person_associations ppa ON fd.detection_id = ppa.detection_id
                LEFT JOIN face_clusters fc ON ppa.cluster_id = fc.cluster_id
                WHERE {where_clause}
                ORDER BY fd.photo_path
                LIMIT ? OFFSET ?
            """,
                params + [limit, offset],
            ).fetchall()

            photo_paths = [row["photo_path"] for row in photo_rows]
            if not photo_paths:
                return {"photos": [], "total": total, "limit": limit, "offset": offset}

            placeholders = ",".join("?" * len(photo_paths))
            detail_rows = conn.execute(
                f"""
                SELECT
                    fd.detection_id,
                    fd.photo_path,
                    fd.bounding_box,
                    ppa.cluster_id,
                    ppa.confidence,
                    fd.quality_score,
                    fd.overall_quality,
                    fd.age_estimate,
                    fd.age_confidence,
                    fd.emotion,
                    fd.emotion_confidence,
                    fd.pose_type,
                    fd.pose_confidence,
                    fd.gender,
                    fd.gender_confidence,
                    fd.lighting_score,
                    fd.occlusion_score,
                    fd.resolution_score,
                    fc.label
                FROM face_detections fd
                LEFT JOIN photo_person_associations ppa ON fd.detection_id = ppa.detection_id
                LEFT JOIN face_clusters fc ON ppa.cluster_id = fc.cluster_id
                WHERE {where_clause}
                AND fd.photo_path IN ({placeholders})
                ORDER BY fd.photo_path
            """,
                params + photo_paths,
            ).fetchall()

            grouped: Dict[str, List[Dict[str, Any]]] = {}
            for row in detail_rows:
                grouped.setdefault(row["photo_path"], []).append(
                    {
                        "detection_id": row["detection_id"],
                        "photo_path": row["photo_path"],
                        "bounding_box": json.loads(row["bounding_box"]) if row["bounding_box"] else None,
                        "cluster_id": row["cluster_id"],
                        "label": row["label"],
                        "confidence": row["confidence"],
                        "quality_score": row["quality_score"],
                        "overall_quality": row["overall_quality"],
                        "age_estimate": row["age_estimate"],
                        "age_confidence": row["age_confidence"],
                        "emotion": row["emotion"],
                        "emotion_confidence": row["emotion_confidence"],
                        "pose_type": row["pose_type"],
                        "pose_confidence": row["pose_confidence"],
                        "gender": row["gender"],
                        "gender_confidence": row["gender_confidence"],
                        "lighting_score": row["lighting_score"],
                        "occlusion_score": row["occlusion_score"],
                        "resolution_score": row["resolution_score"],
                    }
                )

            photos = [
                {"photo_path": path, "faces": grouped.get(path, []), "match_count": len(grouped.get(path, []))}
                for path in photo_paths
            ]

            return {"photos": photos, "total": total, "limit": limit, "offset": offset}

    def search_photos_by_people(
        self, query: str, mode: str = "and", limit: int = 100, offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search photos by people names with natural language-like queries.

        Supports queries like:
        - "Alice" - Photos with Alice
        - "Alice Bob" - Photos with Alice AND Bob (mode='and')
        - "Alice Bob" - Photos with Alice OR Bob (mode='or')
        - "Alice !Bob" or "Alice -Bob" - Photos with Alice but NOT Bob

        Args:
            query: Space-separated names, prefix with ! or - to exclude
            mode: 'and' (default) or 'or' for include names
            limit: Maximum results
            offset: Pagination offset
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            # Parse query
            terms = query.split()
            include_names = []
            exclude_names = []

            for term in terms:
                if term.startswith("!") or term.startswith("-"):
                    exclude_names.append(term[1:])
                else:
                    include_names.append(term)

            if not include_names:
                return {"photos": [], "total": 0, "limit": limit, "offset": offset}

            # Find cluster IDs for names
            include_clusters = []
            for name in include_names:
                rows = conn.execute(
                    """
                    SELECT cluster_id FROM face_clusters
                    WHERE label LIKE ? AND hidden = 0
                """,
                    (f"%{name}%",),
                ).fetchall()
                include_clusters.extend([r["cluster_id"] for r in rows])

            exclude_clusters = []
            for name in exclude_names:
                rows = conn.execute(
                    """
                    SELECT cluster_id FROM face_clusters
                    WHERE label LIKE ? AND hidden = 0
                """,
                    (f"%{name}%",),
                ).fetchall()
                exclude_clusters.extend([r["cluster_id"] for r in rows])

            if not include_clusters:
                return {"photos": [], "total": 0, "limit": limit, "offset": offset}

            # Use co-occurrence filter
            return self.get_photos_with_people(
                include_people=include_clusters,
                exclude_people=exclude_clusters if exclude_clusters else None,
                require_all=(mode == "and"),
                limit=limit,
                offset=offset,
            )

    # =========================================================================
    # Review Queue Methods
    # =========================================================================

    def get_review_queue(
        self,
        limit: int = 20,
        offset: int = 0,
        sort: str = "similarity_desc",
    ) -> List[Dict[str, Any]]:
        """
        Get pending items from the review queue.

        Args:
            limit: Maximum number of items to return
            offset: Number of items to skip
            sort: Sort order (similarity_desc, similarity_asc, created_at_desc)

        Returns:
            List of review queue items with face details and candidate info
        """
        order_by = {
            "similarity_desc": "rq.similarity DESC",
            "similarity_asc": "rq.similarity ASC",
            "created_at_desc": "rq.created_at DESC",
        }.get(sort, "rq.similarity DESC")

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"""
                SELECT
                    rq.id,
                    rq.detection_id,
                    rq.candidate_cluster_id,
                    rq.similarity,
                    rq.reason,
                    rq.status,
                    rq.created_at,
                    fd.photo_path,
                    fd.bounding_box,
                    fd.quality_score,
                    fc.label as candidate_label,
                    fc.face_count as candidate_face_count
                FROM face_review_queue rq
                JOIN face_detections fd ON rq.detection_id = fd.detection_id
                LEFT JOIN face_clusters fc ON rq.candidate_cluster_id = fc.cluster_id
                WHERE rq.status = 'pending'
                ORDER BY {order_by}
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()

            return [
                {
                    "id": row["id"],
                    "detection_id": row["detection_id"],
                    "candidate_cluster_id": row["candidate_cluster_id"],
                    "similarity": row["similarity"],
                    "reason": row["reason"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                    "photo_path": row["photo_path"],
                    "bounding_box": json.loads(row["bounding_box"]) if row["bounding_box"] else None,
                    "quality_score": row["quality_score"],
                    "candidate_label": row["candidate_label"],
                    "candidate_face_count": row["candidate_face_count"],
                }
                for row in rows
            ]

    def get_review_queue_count(self) -> int:
        """Get count of pending items in review queue."""
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute("SELECT COUNT(*) FROM face_review_queue WHERE status = 'pending'").fetchone()
            return row[0] if row else 0

    def add_to_review_queue(
        self,
        detection_id: str,
        candidate_cluster_id: str,
        similarity: float,
        reason: str = "gray_zone",
    ) -> int:
        """
        Add a face detection to the review queue.

        Args:
            detection_id: ID of the face detection
            candidate_cluster_id: Best matching cluster ID
            similarity: Similarity score to the candidate
            reason: Why this face needs review ('gray_zone', 'low_confidence', 'ambiguous')

        Returns:
            ID of the created review queue item
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                """
                INSERT INTO face_review_queue
                (detection_id, candidate_cluster_id, similarity, reason)
                VALUES (?, ?, ?, ?)
                """,
                (detection_id, candidate_cluster_id, similarity, reason),
            )
            return cursor.lastrowid or 0

    def resolve_review_item(
        self,
        detection_id: str,
        action: str,
        cluster_id: Optional[str] = None,
    ) -> bool:
        """
        Resolve a review queue item.

        Args:
            detection_id: ID of the face detection
            action: 'confirm', 'reject', or 'skip'
            cluster_id: Cluster to assign to (required for confirm)

        Returns:
            True if successful
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            # Get the review queue item
            item = conn.execute(
                """
                SELECT * FROM face_review_queue
                WHERE detection_id = ? AND status = 'pending'
                """,
                (detection_id,),
            ).fetchone()

            if not item:
                return False

            target_cluster = cluster_id or item["candidate_cluster_id"]

            if action == "confirm":
                # Update assignment state to confirmed
                conn.execute(
                    """
                    UPDATE photo_person_associations
                    SET assignment_state = 'user_confirmed'
                    WHERE detection_id = ? AND cluster_id = ?
                    """,
                    (detection_id, target_cluster),
                )

                # If no association exists, create one
                if conn.total_changes == 0:
                    # Get photo_path from detection
                    det = conn.execute(
                        "SELECT photo_path FROM face_detections WHERE detection_id = ?",
                        (detection_id,),
                    ).fetchone()
                    if det:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO photo_person_associations
                            (photo_path, cluster_id, detection_id, confidence, assignment_state)
                            VALUES (?, ?, ?, ?, 'user_confirmed')
                            """,
                            (
                                det["photo_path"],
                                target_cluster,
                                detection_id,
                                item["similarity"],
                            ),
                        )

                # Log for undo
                self._log_operation(
                    conn,
                    "review_confirm",
                    {
                        "detection_id": detection_id,
                        "cluster_id": target_cluster,
                        "similarity": item["similarity"],
                    },
                )

            elif action == "reject":
                # Add to rejections
                conn.execute(
                    """
                    INSERT OR IGNORE INTO face_rejections (detection_id, cluster_id)
                    VALUES (?, ?)
                    """,
                    (detection_id, target_cluster),
                )

                # Remove association if exists
                conn.execute(
                    """
                    DELETE FROM photo_person_associations
                    WHERE detection_id = ? AND cluster_id = ?
                    """,
                    (detection_id, target_cluster),
                )

                # Log for undo
                self._log_operation(
                    conn,
                    "review_reject",
                    {
                        "detection_id": detection_id,
                        "cluster_id": target_cluster,
                    },
                )

            # Update review queue status
            status = "confirmed" if action == "confirm" else action + "ed"
            if action == "skip":
                status = "skipped"

            conn.execute(
                """
                UPDATE face_review_queue
                SET status = ?, resolved_at = CURRENT_TIMESTAMP
                WHERE detection_id = ? AND status = 'pending'
                """,
                (status, detection_id),
            )

            return True

    def _undo_delete_person(self, conn: sqlite3.Connection, op_data: dict):
        """Undo a delete person operation."""
        cluster_row = op_data["cluster"]
        associations = op_data.get("associations", [])
        review_items = op_data.get("review_items", [])
        rejections = op_data.get("rejections", [])

        # Restore cluster
        keys = list(cluster_row.keys())
        placeholders = ",".join(["?"] * len(keys))
        columns = ",".join(keys)
        conn.execute(
            f"INSERT INTO face_clusters ({columns}) VALUES ({placeholders})",
            list(cluster_row.values()),
        )

        # Restore associations
        if associations:
            conn.executemany(
                """
                INSERT INTO photo_person_associations
                (photo_path, cluster_id, detection_id, confidence, assignment_state)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        a["photo_path"],
                        a["cluster_id"],
                        a["detection_id"],
                        a["confidence"],
                        a.get("assignment_state"),
                    )
                    for a in associations
                ],
            )

        # Restore review queue items
        if review_items:
            conn.executemany(
                """
                INSERT INTO face_review_queue
                (detection_id, candidate_cluster_id, similarity, reason, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        r["detection_id"],
                        r["candidate_cluster_id"],
                        r["similarity"],
                        r["reason"],
                        r["status"],
                        r["created_at"],
                    )
                    for r in review_items
                ],
            )

        # Restore rejections
        if rejections:
            conn.executemany(
                """
                INSERT INTO face_rejections (detection_id, cluster_id, created_at)
                VALUES (?, ?, ?)
                """,
                [(r["detection_id"], r["cluster_id"], r["created_at"]) for r in rejections],
            )

    def delete_face_cluster(self, cluster_id: str) -> bool:
        """
        Delete a face cluster (person) and all its data.
        Features robust undo support.

        Args:
            cluster_id: ID of the cluster to delete

        Returns:
            True if successful
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            # 1. Fetch data for undo
            # Cluster info
            cluster_row = conn.execute("SELECT * FROM face_clusters WHERE cluster_id = ?", (cluster_id,)).fetchone()
            if not cluster_row:
                return False  # Already deleted?

            # Associations
            associations = [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM photo_person_associations WHERE cluster_id = ?",
                    (cluster_id,),
                ).fetchall()
            ]

            # Review queue items
            review_items = [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM face_review_queue WHERE candidate_cluster_id = ?",
                    (cluster_id,),
                ).fetchall()
            ]

            # Rejections
            rejections = [
                dict(row)
                for row in conn.execute("SELECT * FROM face_rejections WHERE cluster_id = ?", (cluster_id,)).fetchall()
            ]

            # Log for undo
            self._log_operation(
                conn,
                "delete_person",
                {
                    "cluster": dict(cluster_row),
                    "associations": associations,
                    "review_items": review_items,
                    "rejections": rejections,
                },
            )

            # 2. Delete everything
            conn.execute(
                "DELETE FROM photo_person_associations WHERE cluster_id = ?",
                (cluster_id,),
            )
            conn.execute(
                "DELETE FROM face_review_queue WHERE candidate_cluster_id = ?",
                (cluster_id,),
            )
            conn.execute("DELETE FROM face_rejections WHERE cluster_id = ?", (cluster_id,))
            conn.execute("DELETE FROM face_clusters WHERE cluster_id = ?", (cluster_id,))

            logger.info(f"Deleted person {cluster_id}")
            return True

    def get_face_cluster_export_data(self, cluster_id: str) -> Optional[dict]:
        """Get all data for a cluster for export."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            # Cluster info
            cluster = conn.execute("SELECT * FROM face_clusters WHERE cluster_id = ?", (cluster_id,)).fetchone()
            if not cluster:
                return None

            cluster_dict = dict(cluster)

            # Faces with details
            faces = [
                dict(row)
                for row in conn.execute(
                    """
                SELECT
                    a.detection_id, a.photo_path, a.confidence, a.assignment_state,
                    d.bounding_box, d.quality_score, d.created_at as detected_at
                FROM photo_person_associations a
                LEFT JOIN face_detections d ON a.detection_id = d.detection_id
                WHERE a.cluster_id = ?
            """,
                    (cluster_id,),
                ).fetchall()
            ]

            # Rejections
            rejections = [
                dict(row)
                for row in conn.execute(
                    """
                SELECT detection_id, created_at
                FROM face_rejections
                WHERE cluster_id = ?
            """,
                    (cluster_id,),
                ).fetchall()
            ]

            return {
                "cluster": cluster_dict,
                "faces": faces,
                "rejections": rejections,
                "exported_at": datetime.now().isoformat(),
            }

    def delete_all_face_data(self) -> dict:
        """
        Delete ALL face data from the system.
        Irreversible. Wipes clusters, detections, associations, logs.
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            # Stats
            stats = {}
            try:
                stats["associations"] = conn.execute("SELECT COUNT(*) FROM photo_person_associations").fetchone()[0]
                stats["clusters"] = conn.execute("SELECT COUNT(*) FROM face_clusters").fetchone()[0]
                stats["detections"] = conn.execute("SELECT COUNT(*) FROM face_detections").fetchone()[0]
            except sqlite3.OperationalError:
                stats = {"error": "Could not fetch stats"}

            # Delete in order
            try:
                conn.execute("DELETE FROM photo_person_associations")
                conn.execute("DELETE FROM face_review_queue")
                conn.execute("DELETE FROM face_rejections")
                conn.execute("DELETE FROM face_clusters")
                conn.execute("DELETE FROM face_detections")
                conn.execute("DELETE FROM person_operations_log")
            except sqlite3.OperationalError as e:
                logger.warning(f"Error deleting tables: {e}")

            logger.warning(f"Deleted ALL face data: {stats}")
            return stats

    # ===================================================================
    # Phase 1: Performance-Optimized Face Service Support Methods
    # ===================================================================

    def get_all_cluster_prototypes(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all cluster prototypes with embeddings for FAISS index initialization.

        Returns:
            Dict mapping cluster_id to {"embedding": np.ndarray, "label": str}
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            # Check if using legacy schema
            if self._is_legacy_schema(conn):
                # Legacy schema doesn't have prototypes, return empty
                logger.warning("Legacy schema detected, no prototypes available")
                return {}

            rows = conn.execute(
                """
                SELECT cluster_id, label, prototype_embedding
                FROM face_clusters
                WHERE (hidden = 0 OR hidden IS NULL)
                AND (indexing_disabled = 0 OR indexing_disabled IS NULL)
                AND prototype_embedding IS NOT NULL
                """
            ).fetchall()

            prototypes = {}
            for row in rows:
                try:
                    # Convert BLOB to numpy array
                    embedding = np.frombuffer(row["prototype_embedding"], dtype=np.float32)
                    prototypes[row["cluster_id"]] = {
                        "embedding": embedding,
                        "label": row["label"],
                    }
                except Exception as e:
                    logger.warning(f"Failed to load prototype for {row['cluster_id']}: {e}")

            return prototypes

    def get_face_detection(self, detection_id: str) -> Optional[FaceDetection]:
        """
        Get face detection by ID.

        Args:
            detection_id: Face detection ID

        Returns:
            FaceDetection object or None if not found
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            # Check if using legacy schema
            if self._is_legacy_schema(conn):
                logger.warning("Legacy schema detected, face detection retrieval not supported")
                return None

            row = conn.execute(
                """
                SELECT detection_id, photo_path, bounding_box, embedding, quality_score, created_at
                FROM face_detections
                WHERE detection_id = ?
                """,
                (detection_id,),
            ).fetchone()

            if not row:
                return None

            # Parse embedding if present
            embedding = None
            if row["embedding"]:
                try:
                    if isinstance(row["embedding"], bytes):
                        embedding = np.frombuffer(row["embedding"], dtype=np.float32).tolist()
                    elif isinstance(row["embedding"], str):
                        embedding = json.loads(row["embedding"])
                    else:
                        embedding = list(row["embedding"])
                except Exception as e:
                    logger.warning(f"Failed to parse embedding for {detection_id}: {e}")

            # Parse bounding box
            bounding_box = {}
            if row["bounding_box"]:
                try:
                    bounding_box = (
                        json.loads(row["bounding_box"]) if isinstance(row["bounding_box"], str) else row["bounding_box"]
                    )
                except Exception:
                    bounding_box = {}

            return FaceDetection(
                detection_id=row["detection_id"],
                photo_path=row["photo_path"],
                bounding_box=bounding_box,
                embedding=embedding,
                quality_score=row["quality_score"],
                created_at=row["created_at"],
            )

    def get_faces_for_cluster(self, cluster_id: str) -> List[FaceDetection]:
        """
        Get all face detections for a cluster.

        Args:
            cluster_id: Cluster ID

        Returns:
            List of FaceDetection objects
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            # Check if using legacy schema
            if self._is_legacy_schema(conn):
                logger.warning("Legacy schema detected, face retrieval not supported")
                return []

            rows = conn.execute(
                """
                SELECT fd.detection_id, fd.photo_path, fd.bounding_box, fd.embedding, fd.quality_score, fd.created_at
                FROM face_detections fd
                JOIN photo_person_associations ppa ON fd.detection_id = ppa.detection_id
                WHERE ppa.cluster_id = ?
                """,
                (cluster_id,),
            ).fetchall()

            faces = []
            for row in rows:
                # Parse embedding if present
                embedding = None
                if row["embedding"]:
                    try:
                        if isinstance(row["embedding"], bytes):
                            embedding = np.frombuffer(row["embedding"], dtype=np.float32).tolist()
                        elif isinstance(row["embedding"], str):
                            embedding = json.loads(row["embedding"])
                        else:
                            embedding = list(row["embedding"])
                    except Exception as e:
                        logger.warning(f"Failed to parse embedding for {row['detection_id']}: {e}")

                # Parse bounding box
                bounding_box = {}
                if row["bounding_box"]:
                    try:
                        bounding_box = (
                            json.loads(row["bounding_box"])
                            if isinstance(row["bounding_box"], str)
                            else row["bounding_box"]
                        )
                    except Exception:
                        bounding_box = {}

                faces.append(
                    FaceDetection(
                        detection_id=row["detection_id"],
                        photo_path=row["photo_path"],
                        bounding_box=bounding_box,
                        embedding=embedding,
                        quality_score=row["quality_score"],
                        created_at=row["created_at"],
                    )
                )

            return faces

    def get_cluster_count(self) -> int:
        """
        Get total number of clusters.

        Returns:
            Number of clusters (excluding hidden ones)
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            # Check if using legacy schema
            if self._is_legacy_schema(conn):
                # Use legacy clusters table
                result = conn.execute("SELECT COUNT(*) as count FROM clusters").fetchone()
                return result[0] if result else 0

            result = conn.execute(
                """
                SELECT COUNT(*) as count
                FROM face_clusters
                WHERE (hidden = 0 OR hidden IS NULL)
                AND (indexing_disabled = 0 OR indexing_disabled IS NULL)
                """
            ).fetchone()

            return result[0] if result else 0


def get_face_clustering_db(db_path: Path) -> FaceClusteringDB:
    """Get face clustering database instance."""
    return FaceClusteringDB(db_path)
