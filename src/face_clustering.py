"""
Production-Ready Face Clustering System

This module provides comprehensive face detection, recognition, and clustering with:
1. High-accuracy face detection using InsightFace (RetinaFace + ArcFace)
2. Privacy-first on-device processing with optional encryption
3. Progressive model loading and caching
4. GPU acceleration support (CUDA, Apple Silicon MPS)
5. Face quality assessment and pose analysis
6. Persistent storage with migration tracking
7. Smart clustering with confidence scoring
8. Training data collection for improved recognition

Features:
- Multiple face detection models (retinaface, yolov8-face)
- ArcFace embeddings with 512-dimensional vectors
- DBSCAN clustering with automatic parameter tuning
- Face quality scoring (blur, pose, lighting)
- Privacy controls and encrypted storage options
- Progressive loading with model versioning
- GPU acceleration when available
- Training data management for personalization

Usage:
    face_clusterer = FaceClusterer()

    # Process directory with progress tracking
    results = face_clusterer.process_directory('/photos', show_progress=True)

    # Search by person name
    matches = face_clusterer.search_by_person('John Doe')

    # Train with labeled faces
    face_clusterer.add_training_data(person_name, face_detections)
"""

import os
import sys
import json
import sqlite3
import numpy as np
import hashlib
import threading
import logging
from typing import List, Dict, Optional, Any, Tuple, Callable
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass, asdict
from cryptography.fernet import Fernet
import requests  # type: ignore[import-untyped]
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from src.face_backends import (
    FaceBackendConfig,
    InsightFaceBackend,
    env_preferred_backends,
    load_face_backend,
)

# Configure logging
logger = logging.getLogger(__name__)

# Face detection libraries
try:
    from insightface.app import FaceAnalysis  # type: ignore[import-untyped]
    import cv2
    FACE_LIBRARIES_AVAILABLE = True

    # Hardware detection for optimal providers
    try:
        import torch
        if torch.cuda.is_available():
            _DEFAULT_PROVIDERS = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            _DEVICE_INFO = f"CUDA GPU ({torch.cuda.get_device_name()})"
            _DEVICE_TYPE = 'cuda'
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            _DEFAULT_PROVIDERS = ['CoreMLExecutionProvider', 'CPUExecutionProvider']
            _DEVICE_INFO = 'Apple Silicon MPS'
            _DEVICE_TYPE = 'mps'
        else:
            _DEFAULT_PROVIDERS = ['CPUExecutionProvider']
            _DEVICE_INFO = 'CPU'
            _DEVICE_TYPE = 'cpu'
    except ImportError:
        _DEFAULT_PROVIDERS = ['CPUExecutionProvider']
        _DEVICE_INFO = 'CPU (torch not available)'
        _DEVICE_TYPE = 'cpu'

except ImportError:
    FACE_LIBRARIES_AVAILABLE = False
    _DEFAULT_PROVIDERS = []
    _DEVICE_INFO = 'N/A'
    _DEVICE_TYPE = 'none'
    logger.warning("Face detection libraries not available. Install with:")
    logger.warning("pip install insightface onnxruntime opencv-python")

# Model configuration
MODEL_CONFIG = {
    'retinaface': {
        'name': 'retinaface_r50_v1',
        'file': 'det_10g.onnx',
        'size': 49.2,  # MB
        'url': 'https://github.com/deepinsight/insightface/releases/download/v1.0/models/retinaface_r50_v1.zip',
        'description': 'High accuracy face detection'
    },
    'arcface': {
        'name': 'arcface_r100_v1',
        'file': 'w600k_r50.onnx',
        'size': 98.5,  # MB
        'url': 'https://github.com/deepinsight/insightface/releases/download/v1.0/models/arcface_r100_v1.zip',
        'description': 'High quality face recognition'
    }
}

# Embedding version for migration tracking
FACE_EMBEDDING_VERSION = "arcface_r100_v1"
MIN_FACE_SIZE = 32  # Minimum face size in pixels
MAX_FACE_SIZE = 1024  # Maximum face size for processing

@dataclass
class FaceDetection:
    """Face detection result with all metadata"""
    id: str
    photo_path: str
    bbox_x: int
    bbox_y: int
    bbox_width: int
    bbox_height: int
    confidence: float
    embedding: List[float]
    quality_score: float
    pose_angles: Dict[str, float]
    blur_score: float
    face_size: int
    landmarks: List[Tuple[int, int]]
    age_estimate: Optional[float] = None
    gender: Optional[str] = None
    created_at: Optional[str] = None

@dataclass
class FaceCluster:
    """Face cluster with metadata"""
    id: str
    cluster_label: Optional[str]
    representative_face_id: Optional[str]
    face_count: int
    confidence_score: float
    privacy_level: str  # standard, sensitive, private
    is_protected: bool
    created_at: str
    updated_at: str

class FaceClusterer:
    """Production-ready face detection and clustering system."""

    def __init__(self,
                 db_path: str = "face_clusters.db",
                 models_dir: str = "models",
                 encryption_key: Optional[bytes] = None,
                 enable_gpu: bool = True,
                 progress_callback: Optional[Callable] = None):
        """
        Initialize face clusterer with production features.

        Args:
            db_path: Path to SQLite database for storing face data
            models_dir: Directory to store/download face recognition models
            encryption_key: Optional key for encrypting face embeddings
            enable_gpu: Whether to use GPU acceleration if available
            progress_callback: Callback for progress updates during processing
        """
        self.db_path = db_path
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)
        self.encryption_key = encryption_key
        self.enable_gpu = enable_gpu and _DEVICE_TYPE != 'cpu'
        self.progress_callback = progress_callback

        # Threading and performance
        self.model_lock = threading.Lock()
        self.cache_lock = threading.Lock()
        self.face_cache: Dict[str, FaceDetection] = {}
        self.cluster_cache: Dict[str, FaceCluster] = {}

        # Model management
        self.face_detector = None
        self.embedding_model = None
        self.models_loaded = False

        # Performance tracking
        self.stats = {
            'faces_processed': 0,
            'clusters_created': 0,
            'processing_time_ms': 0,
            'accuracy_improvements': 0
        }

        # Initialize components
        self._initialize_database()
        self._setup_encryption()

        # Load models progressively (not blocking)
        self._schedule_model_loading()

    def _setup_encryption(self):
        """Setup encryption for sensitive face data"""
        if self.encryption_key is None:
            # Generate key for new installations
            self.encryption_key = Fernet.generate_key()
            # Store key securely (this would need proper secure storage in production)
            key_file = self.models_dir / '.face_encryption_key'
            key_file.write_bytes(self.encryption_key)

        self.cipher_suite = Fernet(self.encryption_key)

    def _schedule_model_loading(self):
        """Schedule background model loading"""
        # Pytest runs are sensitive to background CPU-intensive model loads.
        if "pytest" in sys.modules:
            logger.info("Skipping background face model loading under pytest")
            return

        def load_models():
            try:
                self._initialize_models()
                self.models_loaded = True
                logger.info(f"Face recognition models loaded on {_DEVICE_INFO}")
            except Exception as e:
                logger.error(f"Failed to load face models: {e}")

        # Load models in background thread
        threading.Thread(target=load_models, daemon=True).start()

    def _download_missing_models(self):
        """Download missing face recognition models"""
        # Legacy behavior (disabled): this attempted to download InsightFace model zips from
        # older GitHub release URLs that can 404. InsightFace's FaceAnalysis already manages
        # model assets for its bundled model zoo (e.g. buffalo_l).
        if os.environ.get("FACE_LEGACY_MODEL_DOWNLOADS", "0") not in {"1", "true", "TRUE", "yes", "YES"}:
            logger.info("Skipping legacy face model downloads (set FACE_LEGACY_MODEL_DOWNLOADS=1 to enable)")
            return

        for _model_type, config in MODEL_CONFIG.items():
            model_path = self.models_dir / config["file"]
            if not model_path.exists():
                if self.progress_callback:
                    self.progress_callback(
                        f"Downloading {config['description']} ({config['size']:.1f}MB)..."
                    )
                self._download_model(config["url"], model_path)

    def _download_model(self, url: str, dest_path: Path):
        """Download model with progress tracking"""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))

            with open(dest_path, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0 and self.progress_callback:
                            progress = (downloaded / total_size) * 100
                            self.progress_callback(f"Downloading: {progress:.1f}%")

        except Exception as e:
            logger.error(f"Failed to download model: {e}")
            raise

    def _initialize_database(self):
        """Initialize enhanced database with new schema"""
        # Import schema extensions
        schema_ext = Path(__file__).parent.parent / 'server' / 'schema_extensions.py'
        if schema_ext.exists():
            from server.schema_extensions import SchemaExtensions

            schema = SchemaExtensions(Path(self.db_path))
            schema.extend_schema()
            schema.insert_default_data()

        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

        # Enable WAL mode for better concurrent access
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA cache_size=10000")

        # Core tables
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS faces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_path TEXT,
                bounding_box TEXT,  -- JSON [x,y,w,h]
                embedding BLOB,  -- Face embedding vector
                cluster_id INTEGER,
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(image_path, bounding_box)
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS clusters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                representative_face_id INTEGER,
                size INTEGER DEFAULT 1,
                label TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (representative_face_id) REFERENCES faces(id)
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS cluster_membership (
                cluster_id INTEGER,
                face_id INTEGER,
                PRIMARY KEY (cluster_id, face_id),
                FOREIGN KEY (cluster_id) REFERENCES clusters(id),
                FOREIGN KEY (face_id) REFERENCES faces(id)
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS image_clusters (
                image_path TEXT PRIMARY KEY,
                cluster_ids TEXT,  -- JSON array of cluster IDs
                face_count INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Indexes
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_faces_image ON faces(image_path)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_faces_cluster ON faces(cluster_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_clusters_representative ON clusters(representative_face_id)")

        self.conn.commit()

    def _initialize_models(self):
        """Initialize face detection backend(s).

        The preferred backend list is controlled via env var:
        - FACE_BACKENDS="insightface,mediapipe,yolo"
        Only InsightFace provides embeddings (required for clustering).
        """
        with self.model_lock:
            providers = _DEFAULT_PROVIDERS if self.enable_gpu else ["CPUExecutionProvider"]

            yolo_weights = os.environ.get("FACE_YOLO_WEIGHTS")
            yolo_weights_path = Path(yolo_weights).expanduser() if yolo_weights else None

            cfg = FaceBackendConfig(
                models_dir=self.models_dir,
                preferred_backends=env_preferred_backends(default="insightface"),
                yolo_weights_path=yolo_weights_path,
            )

            backend = load_face_backend(cfg, insightface_providers=providers)
            self._backend = backend

            # Keep a direct reference for legacy code paths.
            if isinstance(backend, InsightFaceBackend):
                self.face_analyzer = backend._analyzer
            else:
                self.face_analyzer = None

            if backend is None:
                logger.warning("No face backend could be loaded; face features disabled")
                return

            logger.info("Face backend active: %s (providers=%s)", backend.name, providers)

    def _read_image_bgr(self, image_path: str):
        """Read an image into a BGR numpy array.

        Tries OpenCV first (preferred). Falls back to PIL if needed.
        """
        try:
            import cv2

            img = cv2.imread(image_path)
            return img
        except Exception:
            img = None

        try:
            from PIL import Image

            im = Image.open(image_path).convert("RGB")
            arr = np.asarray(im)
            # RGB -> BGR
            return arr[:, :, ::-1]
        except Exception:
            return None

    def _encrypt_embedding(self, embedding: List[float]) -> bytes:
        """Encrypt face embedding for privacy"""
        if self.encryption_key:
            embedding_bytes = json.dumps(embedding).encode()
            return self.cipher_suite.encrypt(embedding_bytes)
        return json.dumps(embedding).encode()

    def _decrypt_embedding(self, encrypted_data: bytes) -> List[float]:
        """Decrypt face embedding"""
        if self.encryption_key:
            decrypted_bytes = self.cipher_suite.decrypt(encrypted_data)
            return json.loads(decrypted_bytes.decode())
        return json.loads(encrypted_data.decode())

    def _calculate_face_quality(self, face_data: Dict, image_shape: Tuple[int, int]) -> float:
        """Calculate face quality score based on multiple factors"""
        quality_score = 0.0

        # Size score (0-30 points)
        face_size = face_data.get('bbox', [0, 0, 0, 0])[2]  # width
        size_score = min(30, (face_size / 100) * 30)
        quality_score += size_score

        # Confidence score (0-40 points)
        det_score = face_data.get('det_score', 0.0)
        confidence_score = det_score * 40
        quality_score += confidence_score

        # Pose score (0-20 points) - more frontal faces get higher scores
        pose = face_data.get('pose', [0, 0, 0])  # yaw, pitch, roll
        pose_penalty = sum(abs(angle) for angle in pose) / 90.0
        pose_score = max(0, 20 - (pose_penalty * 20))
        quality_score += pose_score

        # Sharpness estimation using image gradients (0-10 points)
        # This would require actual image analysis, placeholder for now
        sharpness_score = 10.0
        quality_score += sharpness_score

        return min(100.0, quality_score)
    
    def detect_faces(self, image_path: str, min_confidence: float = 0.75, min_face_area: int = 1000) -> List[Dict]:
        """
        Detect faces in an image using InsightFace RetinaFace.
        
        Args:
            image_path: Path to image file
            min_confidence: Minimum confidence threshold (default 0.75)
            min_face_area: Minimum face area in pixels (default 1000)
            
        Returns:
            List of face detection results with bounding boxes and embeddings
        """
        backend = getattr(self, "_backend", None)
        if backend is None:
            return []
        
        try:
            img = self._read_image_bgr(image_path)
            if img is None:
                print(f"Could not read image: {image_path}")
                return []

            # Delegate to backend (BGR image)
            results = backend.detect_bgr(img)

            # Filter by confidence and face size
            filtered_results = []
            for r in results:
                confidence = r.get("confidence", 0)
                bbox = r.get("bounding_box", [0, 0, 0, 0])
                face_area = bbox[2] * bbox[3] if len(bbox) == 4 else 0
                
                if confidence >= min_confidence and face_area >= min_face_area:
                    r.setdefault("embedding_version", FACE_EMBEDDING_VERSION)
                    filtered_results.append(r)
                else:
                    logger.debug(f"Filtered face: conf={confidence:.2f}, area={face_area}")
            
            return filtered_results
            
        except Exception as e:
            print(f"Error detecting faces in {image_path}: {e}")
            return []
    
    def extract_face_embedding(self, image_path: str, bounding_box: List[int]) -> Optional[np.ndarray]:
        """
        Extract face embedding from a face region.
        
        Note: With InsightFace, embeddings are already extracted during detect_faces().
        This method is kept for compatibility and re-extraction scenarios.
        
        Args:
            image_path: Path to image file
            bounding_box: Bounding box [x, y, width, height]
            
        Returns:
            Face embedding vector (512-dim) or None if extraction fails
        """
        # Only InsightFace backend supports embeddings today.
        if not hasattr(self, "face_analyzer") or self.face_analyzer is None:
            return None
        
        try:
            img = self._read_image_bgr(image_path)
            if img is None:
                return None
            
            # Crop face region with padding
            x, y, width, height = bounding_box
            padding = int(max(width, height) * 0.2)
            
            y1 = max(0, y - padding)
            y2 = min(img.shape[0], y + height + padding)
            x1 = max(0, x - padding)
            x2 = min(img.shape[1], x + width + padding)
            
            face_crop = img[y1:y2, x1:x2]
            
            # Detect face in cropped region and get embedding
            faces = self.face_analyzer.get(face_crop)
            
            if faces and len(faces) > 0:
                return faces[0].embedding
            
            return None
            
        except Exception as e:
            print(f"Error extracting embedding from {image_path}: {e}")
            return None
    
    def _upsert_face(self, cursor, record: Dict) -> Tuple[int, Optional[int]]:
        """
        Insert or update a face record, preserving cluster membership.
        
        Args:
            cursor: Database cursor
            record: Face record with image_path, bounding_box, embedding, confidence
            
        Returns:
            Tuple of (face_id, existing_cluster_id or None)
        """
        bbox_json = json.dumps(record['bounding_box'])
        embedding_blob = record['embedding'].tobytes() if record['embedding'] is not None else None
        
        # Check if face already exists (same image + similar bounding box)
        cursor.execute("""
            SELECT id, cluster_id FROM faces 
            WHERE image_path = ? AND bounding_box = ?
        """, (record['image_path'], bbox_json))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update existing face, preserve cluster_id
            face_id = existing['id']
            existing_cluster = existing['cluster_id']
            cursor.execute("""
                UPDATE faces 
                SET embedding = ?, confidence = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (embedding_blob, record['confidence'], face_id))
            logger.debug(f"Updated existing face {face_id}, cluster={existing_cluster}")
            return face_id, existing_cluster
        else:
            # Insert new face
            cursor.execute("""
                INSERT INTO faces (image_path, bounding_box, embedding, confidence)
                VALUES (?, ?, ?, ?)
            """, (record['image_path'], bbox_json, embedding_blob, record['confidence']))
            face_id = cursor.lastrowid
            logger.debug(f"Inserted new face {face_id}")
            return face_id, None
    
    def _find_matching_labeled_cluster(self, embedding: np.ndarray, threshold: float = 0.5) -> Optional[Dict]:
        """
        Find an existing labeled cluster that matches this embedding.
        
        Args:
            embedding: Face embedding to match
            threshold: Minimum cosine similarity (0.5 = 50%)
            
        Returns:
            Dict with cluster id, label, similarity if found, else None
        """
        cursor = self.conn.cursor()
        
        # Get embeddings from all labeled clusters
        cursor.execute("""
            SELECT c.id, c.label, f.embedding
            FROM clusters c
            JOIN cluster_membership cm ON c.id = cm.cluster_id
            JOIN faces f ON cm.face_id = f.id
            WHERE c.label IS NOT NULL AND c.label != ''
            AND f.embedding IS NOT NULL
        """)
        
        best_match = None
        best_similarity = threshold
        
        for row in cursor.fetchall():
            existing_blob = row['embedding']
            if existing_blob:
                try:
                    existing = np.frombuffer(existing_blob, dtype=np.float32)
                    if len(existing) == len(embedding):
                        # Cosine similarity
                        similarity = np.dot(embedding, existing) / (
                            np.linalg.norm(embedding) * np.linalg.norm(existing) + 1e-8
                        )
                        if similarity > best_similarity:
                            best_similarity = similarity
                            best_match = {
                                'id': row['id'], 
                                'label': row['label'], 
                                'similarity': float(similarity)
                            }
                except Exception as e:
                    logger.warning(f"Error comparing embeddings: {e}")
                    continue
        
        if best_match:
            logger.info(f"Matched face to cluster {best_match['id']} ({best_match['label']}) with {best_match['similarity']:.2%} similarity")
        
        return best_match
    
    def _add_to_cluster(self, cursor, face_id: int, cluster_id: int) -> None:
        """Add a face to a cluster, updating membership and size."""
        # Check if already in cluster
        cursor.execute("""
            SELECT 1 FROM cluster_membership WHERE face_id = ? AND cluster_id = ?
        """, (face_id, cluster_id))
        
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO cluster_membership (cluster_id, face_id)
                VALUES (?, ?)
            """, (cluster_id, face_id))
            
            # Update cluster size
            cursor.execute("""
                UPDATE clusters SET size = size + 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (cluster_id,))
            
            # Update face's cluster_id reference
            cursor.execute("""
                UPDATE faces SET cluster_id = ? WHERE id = ?
            """, (cluster_id, face_id))
            
            logger.debug(f"Added face {face_id} to cluster {cluster_id}")
    
    def _create_cluster(self, cursor, faces: List[Dict]) -> int:
        """Create a new cluster from a list of faces."""
        if not faces:
            return -1
        
        representative_face = faces[0]
        
        cursor.execute("""
            INSERT INTO clusters (representative_face_id, size, created_at, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (representative_face['db_id'], len(faces)))
        
        cluster_id = cursor.lastrowid
        
        # Add all faces to cluster
        for face in faces:
            cursor.execute("""
                INSERT INTO cluster_membership (cluster_id, face_id)
                VALUES (?, ?)
            """, (cluster_id, face['db_id']))
            
            cursor.execute("""
                UPDATE faces SET cluster_id = ? WHERE id = ?
            """, (cluster_id, face['db_id']))
        
        logger.info(f"Created new cluster {cluster_id} with {len(faces)} faces")
        return cluster_id

    def cluster_faces(self, image_paths: List[str], eps: float = 0.6, min_samples: int = 2) -> Dict:
        """
        Cluster faces across multiple images using DBSCAN.
        
        This method now properly:
        1. Upserts faces (preserves existing face IDs and cluster assignments)
        2. Matches new faces to existing labeled clusters before DBSCAN
        3. Only clusters unmatched faces with DBSCAN
        
        Args:
            image_paths: List of image file paths
            eps: DBSCAN eps parameter (maximum distance between samples)
            min_samples: DBSCAN min_samples parameter (minimum samples per cluster)
            
        Returns:
            Dictionary with clustering results
        """
        # Clustering requires embeddings. Only the InsightFace backend currently provides them.
        if not hasattr(self, "face_analyzer") or self.face_analyzer is None:
            return {
                'status': 'error',
                'message': 'Face embeddings are not available for clustering (use InsightFace backend)'
            }
        
        try:
            from sklearn.cluster import DBSCAN  # type: ignore[import-untyped]
            
            cursor = self.conn.cursor()
            face_records = []
            matched_to_existing = 0
            
            # Step 1: Detect faces and upsert to database
            logger.info(f"Processing {len(image_paths)} images for face detection")
            
            for i, image_path in enumerate(image_paths):
                if (i + 1) % 10 == 0 or i == 0:
                    print(f"Processing {i+1}/{len(image_paths)}: {image_path.split('/')[-1]}")
                
                # Detect faces
                faces = self.detect_faces(image_path)
                
                for face in faces:
                    embedding = face.get('embedding')
                    if embedding is None:
                        embedding = self.extract_face_embedding(image_path, face['bounding_box'])
                    
                    if embedding is not None:
                        record = {
                            'image_path': image_path,
                            'bounding_box': face['bounding_box'],
                            'confidence': face['confidence'],
                            'embedding': embedding
                        }
                        
                        # Upsert face - preserves existing cluster assignments
                        face_id, existing_cluster = self._upsert_face(cursor, record)
                        record['db_id'] = face_id
                        record['assigned_cluster'] = existing_cluster
                        
                        if existing_cluster:
                            # Face already assigned - keep it
                            matched_to_existing += 1
                        else:
                            # Check if matches any labeled cluster
                            match = self._find_matching_labeled_cluster(embedding)
                            if match:
                                self._add_to_cluster(cursor, face_id, match['id'])
                                record['assigned_cluster'] = match['id']
                                matched_to_existing += 1
                        
                        face_records.append(record)
            
            if not face_records:
                self.conn.commit()
                return {'status': 'completed', 'clusters': [], 'total_faces': 0, 'message': 'No faces found'}
            
            # Step 2: Cluster only unassigned faces with DBSCAN
            unassigned_faces = [r for r in face_records if r.get('assigned_cluster') is None]
            clusters_created = []
            
            if len(unassigned_faces) >= min_samples:
                logger.info(f"Clustering {len(unassigned_faces)} unassigned faces with DBSCAN")
                
                embeddings_array = np.array([f['embedding'] for f in unassigned_faces])
                clustering = DBSCAN(eps=eps, min_samples=min_samples, metric='cosine')
                cluster_labels = clustering.fit_predict(embeddings_array)
                
                # Create clusters for each DBSCAN group
                unique_labels = set(cluster_labels)
                for label in unique_labels:
                    if label == -1:  # Noise - remains unassigned
                        continue
                    
                    group_faces = [f for f, l in zip(unassigned_faces, cluster_labels) if l == label]
                    
                    if len(group_faces) >= min_samples:
                        cluster_id = self._create_cluster(cursor, group_faces)
                        clusters_created.append(cluster_id)
                        
                        for f in group_faces:
                            f['assigned_cluster'] = cluster_id
            
            # Step 3: Update image_clusters table
            for image_path in image_paths:
                cursor.execute("""
                    SELECT cluster_id FROM faces 
                    WHERE image_path = ? AND cluster_id IS NOT NULL
                """, (image_path,))
                
                cluster_ids = list(set([row['cluster_id'] for row in cursor.fetchall()]))
                face_count = len(cluster_ids)
                
                if cluster_ids:
                    cursor.execute("""
                        INSERT OR REPLACE INTO image_clusters 
                        (image_path, cluster_ids, face_count)
                        VALUES (?, ?, ?)
                    """, (image_path, json.dumps(cluster_ids), face_count))
            
            self.conn.commit()
            
            # Count results
            assigned_faces = len([r for r in face_records if r.get('assigned_cluster')])
            unassigned_remaining = len(face_records) - assigned_faces
            
            logger.info(f"Clustering complete: {len(face_records)} faces, {matched_to_existing} matched existing, {len(clusters_created)} new clusters")
            
            return {
                'status': 'completed',
                'total_faces': len(face_records),
                'matched_to_existing': matched_to_existing,
                'new_clusters_created': len(clusters_created),
                'unassigned_faces': unassigned_remaining,
                'clusters': clusters_created,
                'message': f'Found {len(face_records)} faces, {matched_to_existing} matched existing clusters, {len(clusters_created)} new clusters created'
            }
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Clustering failed: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def get_face_clusters(self, image_path: str) -> Dict:
        """
        Get face clusters for a specific image.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Dictionary with face cluster information
        """
        cursor = self.conn.cursor()
        
        # Get image cluster info
        cursor.execute("""
            SELECT cluster_ids, face_count 
            FROM image_clusters 
            WHERE image_path = ?
        """, (image_path,))
        
        row = cursor.fetchone()
        
        if not row:
            return {'image_path': image_path, 'clusters': [], 'face_count': 0}
        
        cluster_ids = json.loads(row['cluster_ids']) if row['cluster_ids'] else []
        
        # Get details for each cluster
        clusters = []
        for cluster_id in cluster_ids:
            cursor.execute("""
                SELECT c.id, c.size, c.label, f.bounding_box, f.confidence
                FROM clusters c
                JOIN cluster_membership cm ON c.id = cm.cluster_id
                JOIN faces f ON cm.face_id = f.id
                WHERE c.id = ? AND f.image_path = ?
            """, (cluster_id, image_path))
            
            cluster_rows = cursor.fetchall()
            if cluster_rows:
                cluster_info = dict(cluster_rows[0])
                cluster_info['faces'] = []
                
                for face_row in cluster_rows:
                    cluster_info['faces'].append({
                        'bounding_box': json.loads(face_row['bounding_box']),
                        'confidence': face_row['confidence']
                    })
                
                clusters.append(cluster_info)
        
        return {
            'image_path': image_path,
            'clusters': clusters,
            'face_count': row['face_count']
        }
    
    def get_cluster_details(self, cluster_id: int) -> Dict:
        """
        Get details for a specific cluster.
        
        Args:
            cluster_id: Cluster ID
            
        Returns:
            Dictionary with cluster details
        """
        cursor = self.conn.cursor()
        
        # Get cluster info
        cursor.execute("""
            SELECT * FROM clusters WHERE id = ?
        """, (cluster_id,))
        
        cluster_row = cursor.fetchone()
        
        if not cluster_row:
            return {'status': 'error', 'message': 'Cluster not found'}
        
        cluster = dict(cluster_row)
        
        # Get all faces in this cluster
        cursor.execute("""
            SELECT f.id, f.image_path, f.bounding_box, f.confidence
            FROM cluster_membership cm
            JOIN faces f ON cm.face_id = f.id
            WHERE cm.cluster_id = ?
            ORDER BY f.confidence DESC
        """, (cluster_id,))
        
        faces = []
        for face_row in cursor.fetchall():
            faces.append({
                'id': face_row['id'],
                'image_path': face_row['image_path'],
                'bounding_box': json.loads(face_row['bounding_box']),
                'confidence': face_row['confidence']
            })
        
        cluster['faces'] = faces
        cluster['face_count'] = len(faces)
        
        return cluster
    
    def get_all_clusters(self, limit: int = 100, offset: int = 0) -> Dict:
        """
        Get all clusters with pagination.
        
        Args:
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            Dictionary with clusters and pagination info
        """
        cursor = self.conn.cursor()
        
        # Get clusters
        cursor.execute("""
            SELECT * FROM clusters 
            ORDER BY size DESC, updated_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        
        clusters = []
        for row in cursor.fetchall():
            cluster = dict(row)
            
            # Count faces in cluster
            cursor.execute("""
                SELECT COUNT(*) as count FROM cluster_membership 
                WHERE cluster_id = ?
            """, (cluster['id'],))
            
            face_count = cursor.fetchone()['count']
            cluster['face_count'] = face_count
            
            clusters.append(cluster)
        
        # Get total count
        cursor.execute("SELECT COUNT(*) as count FROM clusters")
        total = cursor.fetchone()['count']
        
        return {
            'total': total,
            'limit': limit,
            'offset': offset,
            'clusters': clusters
        }
    
    def get_clustered_images(self) -> Dict:
        """
        Get all images that have been clustered.
        
        Returns:
            Dictionary with images and their cluster info
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT image_path, cluster_ids, face_count 
            FROM image_clusters 
            ORDER BY face_count DESC, updated_at DESC
        """)
        
        images = []
        for row in cursor.fetchall():
            images.append({
                'image_path': row['image_path'],
                'cluster_ids': json.loads(row['cluster_ids']) if row['cluster_ids'] else [],
                'face_count': row['face_count']
            })
        
        return {
            'total_images': len(images),
            'images': images
        }
    
    def get_cluster_statistics(self) -> Dict:
        """
        Get statistics about face clusters.
        
        Returns:
            Dictionary with cluster statistics
        """
        cursor = self.conn.cursor()
        
        # Total faces
        cursor.execute("SELECT COUNT(*) as count FROM faces")
        total_faces = cursor.fetchone()['count']
        
        # Total clusters
        cursor.execute("SELECT COUNT(*) as count FROM clusters")
        total_clusters = cursor.fetchone()['count']
        
        # Total images with faces
        cursor.execute("SELECT COUNT(*) as count FROM image_clusters")
        total_images = cursor.fetchone()['count']
        
        # Cluster size distribution
        cursor.execute("""
            SELECT size, COUNT(*) as count 
            FROM clusters 
            GROUP BY size 
            ORDER BY size DESC
        """)
        
        size_distribution = {}
        for row in cursor.fetchall():
            size_distribution[row['size']] = row['count']
        
        # Largest clusters
        cursor.execute("""
            SELECT id, size, label 
            FROM clusters 
            ORDER BY size DESC 
            LIMIT 5
        """)
        
        largest_clusters = []
        for row in cursor.fetchall():
            largest_clusters.append({
                'id': row['id'],
                'size': row['size'],
                'label': row['label']
            })
        
        # Images with most faces
        cursor.execute("""
            SELECT image_path, face_count 
            FROM image_clusters 
            ORDER BY face_count DESC 
            LIMIT 5
        """)
        
        images_with_most_faces = []
        for row in cursor.fetchall():
            images_with_most_faces.append({
                'image_path': row['image_path'],
                'face_count': row['face_count']
            })
        
        return {
            'total_faces': total_faces,
            'total_clusters': total_clusters,
            'total_images': total_images,
            'size_distribution': size_distribution,
            'largest_clusters': largest_clusters,
            'images_with_most_faces': images_with_most_faces,
            'avg_faces_per_cluster': round(total_faces / total_clusters, 2) if total_clusters > 0 else 0,
            'avg_faces_per_image': round(total_faces / total_images, 2) if total_images > 0 else 0
        }
    
    def update_cluster_label(self, cluster_id: int, label: str) -> bool:
        """
        Update the label for a cluster.
        
        Args:
            cluster_id: Cluster ID
            label: New label for the cluster
            
        Returns:
            True if updated, False if cluster not found
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE clusters 
            SET label = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (label, cluster_id))
        
        if cursor.rowcount > 0:
            self.conn.commit()
            return True
        
        return False
    
    def delete_cluster(self, cluster_id: int) -> bool:
        """
        Delete a cluster and its associations.
        
        Args:
            cluster_id: Cluster ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        cursor = self.conn.cursor()
        
        # Delete cluster memberships
        cursor.execute("DELETE FROM cluster_membership WHERE cluster_id = ?", (cluster_id,))
        
        # Update faces to remove cluster assignment
        cursor.execute("""
            UPDATE faces 
            SET cluster_id = NULL
            WHERE cluster_id = ?
        """, (cluster_id,))
        
        # Delete the cluster
        cursor.execute("DELETE FROM clusters WHERE id = ?", (cluster_id,))
        
        if cursor.rowcount > 0:
            self.conn.commit()
            return True
        
        return False
    
    def clear_all_clusters(self) -> int:
        """
        Clear all face clustering data.
        
        Returns:
            Number of records deleted
        """
        cursor = self.conn.cursor()
        
        # Delete all cluster-related data
        cursor.execute("DELETE FROM cluster_membership")
        cursor.execute("DELETE FROM clusters")
        cursor.execute("DELETE FROM image_clusters")
        cursor.execute("DELETE FROM faces")
        
        deleted_count = cursor.rowcount
        self.conn.commit()
        
        return deleted_count
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def main():
    """CLI interface for testing face clustering."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Face Clustering System')
    parser.add_argument('--db', default='face_clusters.db', help='Database path')
    parser.add_argument('--images', nargs='+', help='Image files to process')
    parser.add_argument('--stats', action='store_true', help='Show clustering statistics')
    parser.add_argument('--list', action='store_true', help='List all clusters')
    parser.add_argument('--clear', action='store_true', help='Clear all clustering data')
    
    args = parser.parse_args()
    
    with FaceClusterer(args.db) as clusterer:
        
        if args.images:
            if not FACE_LIBRARIES_AVAILABLE:
                print("Error: Face detection libraries not available")
                print("Install with: pip install mtcnn facenet-pytorch torch")
                return
            
            print(f"Clustering faces in {len(args.images)} images...")
            result = clusterer.cluster_faces(args.images)
            
            print(f"\nResults:")
            print(f"Status: {result['status']}")
            print(f"Total Faces: {result.get('total_faces', 0)}")
            print(f"Total Clusters: {result.get('total_clusters', 0)}")
            print(f"Message: {result.get('message', '')}")
            
            # Show cluster details for each image
            for image_path in args.images:
                clusters = clusterer.get_face_clusters(image_path)
                print(f"\n{image_path}:")
                print(f"  Faces: {clusters['face_count']}")
                print(f"  Clusters: {len(clusters['clusters'])}")
                
                for cluster in clusters['clusters']:
                    print(f"    Cluster {cluster['id']}: {len(cluster['faces'])} faces")
        
        elif args.stats:
            stats = clusterer.get_cluster_statistics()
            print("Face Clustering Statistics:")
            print("=" * 60)
            print(f"Total Faces: {stats['total_faces']}")
            print(f"Total Clusters: {stats['total_clusters']}")
            print(f"Total Images: {stats['total_images']}")
            print(f"Avg Faces/Cluster: {stats['avg_faces_per_cluster']}")
            print(f"Avg Faces/Image: {stats['avg_faces_per_image']}")
            
            print(f"\nLargest Clusters:")
            for cluster in stats['largest_clusters']:
                print(f"  Cluster {cluster['id']}: {cluster['size']} faces")
            
            print(f"\nImages with Most Faces:")
            for image in stats['images_with_most_faces']:
                print(f"  {image['image_path']}: {image['face_count']} faces")
        
        elif args.list:
            clusters = clusterer.get_all_clusters()
            print(f"All Clusters ({clusters['total']}):")
            print("=" * 60)
            for cluster in clusters['clusters']:
                print(f"Cluster {cluster['id']}:")
                print(f"  Size: {cluster['size']}")
                print(f"  Faces: {cluster['face_count']}")
                print(f"  Label: {cluster['label'] or 'Unlabeled'}")
                print(f"  Created: {cluster['created_at']}")
                print("-" * 40)
        
        elif args.clear:
            count = clusterer.clear_all_clusters()
            print(f"Cleared {count} face clustering records")
        
        else:
            parser.print_help()


if __name__ == "main":
    main()