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


@dataclass
class PhotoPersonAssociation:
    """Represents the association between a photo and a person."""
    photo_path: str
    cluster_id: str
    detection_id: str
    confidence: float  # Confidence that this face belongs to the cluster
    created_at: Optional[str] = None


class FaceClusteringDB:
    """Database for managing face detections, clusters, and photo-person associations."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

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
        """Initialize the face clustering database."""
        with sqlite3.connect(str(self.db_path)) as conn:
            # Face detections table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS face_detections (
                    detection_id TEXT PRIMARY KEY,
                    photo_path TEXT NOT NULL,
                    bounding_box TEXT NOT NULL,  -- JSON: {x, y, width, height}
                    embedding BLOB,  -- Face embedding vector
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

            # --- Lightweight migrations for older DBs ---
            # Some earlier versions created face_clusters without a `label` column.
            try:
                cols = [r[1] for r in conn.execute("PRAGMA table_info(face_clusters)").fetchall()]
                if "label" not in cols:
                    conn.execute("ALTER TABLE face_clusters ADD COLUMN label TEXT")
            except Exception:
                # If migration fails, later queries may still work without label.
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

    def add_face_detection(self, photo_path: str, bounding_box: Dict[str, float], 
                          embedding: Optional[List[float]] = None, 
                          quality_score: Optional[float] = None) -> str:
        """Add a face detection to the database."""
        detection_id = f"face_{hashlib.md5(f'{photo_path}_{json.dumps(bounding_box)}'.encode()).hexdigest()}"

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT INTO face_detections (detection_id, photo_path, bounding_box, embedding, quality_score)
                VALUES (?, ?, ?, ?, ?)
            """, (
                detection_id,
                photo_path,
                json.dumps(bounding_box),
                json.dumps(embedding) if embedding else None,
                quality_score
            ))
        
        return detection_id

    def add_face_cluster(self, label: Optional[str] = None) -> str:
        """Add a new face cluster (person)."""
        cluster_id = f"cluster_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]}"

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT INTO face_clusters (cluster_id, label)
                VALUES (?, ?)
            """, (cluster_id, label))
        
        return cluster_id

    def associate_person_with_photo(self, photo_path: str, cluster_id: str, detection_id: str, confidence: float):
        """Associate a person (cluster) with a photo."""
        with sqlite3.connect(str(self.db_path)) as conn:
            # Check if cluster exists
            cluster = conn.execute(
                "SELECT cluster_id FROM face_clusters WHERE cluster_id = ?",
                (cluster_id,)
            ).fetchone()
            
            if not cluster:
                raise ValueError(f"Cluster {cluster_id} does not exist")
            
            # Check if detection exists
            detection = conn.execute(
                "SELECT detection_id FROM face_detections WHERE detection_id = ?",
                (detection_id,)
            ).fetchone()
            
            if not detection:
                raise ValueError(f"Detection {detection_id} does not exist")
            
            # Add association
            conn.execute("""
                INSERT INTO photo_person_associations (photo_path, cluster_id, detection_id, confidence)
                VALUES (?, ?, ?, ?)
            """, (photo_path, cluster_id, detection_id, confidence))
            
            # Update cluster counts
            conn.execute("""
                UPDATE face_clusters
                SET face_count = face_count + 1,
                    photo_count = photo_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE cluster_id = ?
            """, (cluster_id,))

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
                SELECT ppa.photo_path, ppa.cluster_id, ppa.detection_id, ppa.confidence, ppa.created_at,
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
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    def add_person_to_photo(self, photo_path: str, cluster_id: str, detection_id: str, confidence: float = 0.9):
        """Add a person association to a photo."""
        # First check if this detection already has associations
        existing = self.get_people_in_photo(photo_path)
        existing_cluster_ids = [assoc.cluster_id for assoc in existing]
        
        if cluster_id in existing_cluster_ids:
            # Already associated, update confidence
            with sqlite3.connect(str(self.db_path)) as conn:
                cur = conn.execute("""
                    UPDATE photo_person_associations
                    SET confidence = ?
                    WHERE photo_path = ? AND cluster_id = ? AND detection_id = ?
                """, (confidence, photo_path, cluster_id, detection_id))

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
            conn.execute("""
                DELETE FROM photo_person_associations
                WHERE photo_path = ? AND cluster_id = ? AND detection_id = ?
            """, (photo_path, cluster_id, detection_id))
            
            # Update cluster counts
            remaining_faces = conn.execute("""
                SELECT COUNT(*) FROM photo_person_associations
                WHERE cluster_id = ?
            """, (cluster_id,)).fetchone()[0]
            
            remaining_photos = conn.execute("""
                SELECT COUNT(DISTINCT photo_path) FROM photo_person_associations
                WHERE cluster_id = ?
            """, (cluster_id,)).fetchone()[0]
            
            conn.execute("""
                UPDATE face_clusters
                SET face_count = ?,
                    photo_count = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE cluster_id = ?
            """, (remaining_faces, remaining_photos, cluster_id))

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
                SELECT cluster_id, label, face_count, photo_count, created_at, updated_at
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
                conn.execute("DELETE FROM photo_person_associations WHERE photo_path = ?", (photo_path,))
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
                    quality_score=face.quality_score
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
                row = conn.execute("""
                    SELECT photo_path, bounding_box
                    FROM face_detections
                    WHERE detection_id = ?
                """, (detection_id,)).fetchone()
                
                if not row:
                    return None
                
                # Create a DetectedFace object
                from server.face_detection_service import DetectedFace
                face = DetectedFace(
                    detection_id=detection_id,
                    photo_path=row['photo_path'],
                    bounding_box=json.loads(row['bounding_box'])
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
            
            clustering = DBSCAN(
                eps=distance_threshold,
                min_samples=min_samples,
                metric='cosine'
            )
            
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
                            'cluster_id': cluster_id,
                            'detection_ids': cast(List[str], []),
                        }
                    
                    cast(List[str], clusters[label]['detection_ids']).append(detection_id)
            
            # Associate faces with their clusters
            for cluster_label, cluster_data in clusters.items():
                cluster_id = cast(str, cluster_data['cluster_id'])
                
                for detection_id in cast(List[str], cluster_data['detection_ids']):
                    # Get the photo path for this detection
                    with sqlite3.connect(str(self.db_path)) as conn:
                        row = conn.execute("""
                            SELECT photo_path FROM face_detections
                            WHERE detection_id = ?
                        """, (detection_id,)).fetchone()
                        
                        if row:
                            photo_path = row[0]
                            
                            # Associate the face with the cluster
                            self.associate_person_with_photo(
                                photo_path=photo_path,
                                cluster_id=cluster_id,
                                detection_id=detection_id,
                                confidence=0.95
                            )
            
            # Return clustering results
            result: Dict[str, List[str]] = {}
            for cluster_label, cluster_data in clusters.items():
                cid = cast(str, cluster_data['cluster_id'])
                result[cid] = cast(List[str], cluster_data['detection_ids'])
            
            logger.info(f"Created {len(clusters)} clusters from {len(detection_ids)} faces")
            logger.info(f"Noise detections (not clustered): {len(noise_detections)}")
            
            return result
            
        except ImportError:
            logger.warning("scikit-learn not available for clustering")
            return {}
        except Exception as e:
            logger.error(f"Error during face clustering: {e}")
            return {}

    def find_similar_faces(self, detection_id: str, threshold: float = 0.7) -> List[Dict]:
        """Find faces similar to a given face detection."""
        try:
            # Get the reference face embedding
            with sqlite3.connect(str(self.db_path)) as conn:
                row = conn.execute("""
                    SELECT embedding, photo_path
                    FROM face_detections
                    WHERE detection_id = ?
                """, (detection_id,)).fetchone()
                
                if not row or not row[0]:
                    return []
                
                ref_embedding = json.loads(row[0])
                ref_photo_path = row[1]
            
            # Get all other face embeddings
            detection_ids, embeddings = self._get_face_embeddings()
            
            # Calculate similarities
            similarities = []
            
            for det_id, embedding in zip(detection_ids, embeddings):
                if det_id == detection_id:
                    continue  # Skip self-comparison
                
                similarity = self._calculate_cosine_similarity(ref_embedding, embedding)
                
                if similarity >= threshold:
                    # Get photo path for this detection
                    with sqlite3.connect(str(self.db_path)) as conn:
                        photo_row = conn.execute("""
                            SELECT photo_path FROM face_detections
                            WHERE detection_id = ?
                        """, (det_id,)).fetchone()
                        
                        if photo_row:
                            similarities.append({
                                'detection_id': det_id,
                                'photo_path': photo_row[0],
                                'similarity': similarity
                            })
            
            # Sort by similarity (highest first)
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            
            return similarities
            
        except Exception as e:
            logger.error(f"Error finding similar faces: {e}")
            return []

    def get_cluster_quality(self, cluster_id: str) -> Dict:
        """Analyze the quality of a face cluster."""
        try:
            # Get all faces in the cluster
            with sqlite3.connect(str(self.db_path)) as conn:
                rows = conn.execute("""
                    SELECT ppa.detection_id, ppa.confidence,
                           fd.quality_score, fd.embedding
                    FROM photo_person_associations ppa
                    JOIN face_detections fd ON ppa.detection_id = fd.detection_id
                    WHERE ppa.cluster_id = ?
                """, (cluster_id,)).fetchall()
                
                if not rows:
                    return {'error': 'Cluster not found or empty'}
            
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
                'cluster_id': cluster_id,
                'face_count': len(rows),
                'avg_confidence': avg_confidence,
                'avg_quality_score': avg_quality,
                'coherence_score': coherence_score,
                'quality_rating': self._calculate_quality_rating(avg_quality, coherence_score)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing cluster quality: {e}")
            return {'error': str(e)}

    def _calculate_quality_rating(self, avg_quality: float, coherence: float) -> str:
        """Calculate a quality rating for a cluster."""
        score = (avg_quality + coherence) / 2
        
        if score >= 0.9:
            return 'Excellent'
        elif score >= 0.8:
            return 'Good'
        elif score >= 0.7:
            return 'Fair'
        elif score >= 0.6:
            return 'Poor'
        else:
            return 'Low'


def get_face_clustering_db(db_path: Path) -> FaceClusteringDB:
    """Get face clustering database instance."""
    return FaceClusteringDB(db_path)
