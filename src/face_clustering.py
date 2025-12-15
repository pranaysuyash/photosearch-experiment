"""
Face Clustering System

This module provides face detection and clustering functionality to:
1. Detect faces in images
2. Extract face embeddings
3. Cluster similar faces together
4. Identify people across multiple photos

Features:
- Face detection using MTCNN or similar
- Face embedding extraction using FaceNet or similar
- DBSCAN clustering for face grouping
- Persistent storage of face clusters
- Integration with existing photo search

Note: This is a basic implementation that would need proper ML models
for production use. The actual face detection/embedding models would
need to be installed separately.

Usage:
    face_clusterer = FaceClusterer()
    
    # Cluster faces in a directory
    clusters = face_clusterer.cluster_faces('/photos')
    
    # Get clusters for specific images
    image_clusters = face_clusterer.get_image_clusters(['photo1.jpg', 'photo2.jpg'])
"""

import os
import json
import sqlite3
import numpy as np
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Try to import face detection/recognition libraries
# Using InsightFace (RetinaFace + ArcFace) for production-grade accuracy
try:
    from insightface.app import FaceAnalysis
    import cv2
    FACE_LIBRARIES_AVAILABLE = True
    
    # Try to detect GPU availability
    try:
        import torch
        if torch.cuda.is_available():
            _DEFAULT_PROVIDERS = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            _DEVICE_INFO = 'CUDA GPU'
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            _DEFAULT_PROVIDERS = ['CoreMLExecutionProvider', 'CPUExecutionProvider']
            _DEVICE_INFO = 'Apple Silicon MPS'
        else:
            _DEFAULT_PROVIDERS = ['CPUExecutionProvider']
            _DEVICE_INFO = 'CPU'
    except ImportError:
        _DEFAULT_PROVIDERS = ['CPUExecutionProvider']
        _DEVICE_INFO = 'CPU (torch not available)'
        
except ImportError:
    FACE_LIBRARIES_AVAILABLE = False
    _DEFAULT_PROVIDERS = []
    _DEVICE_INFO = 'N/A'
    print("Warning: Face detection libraries not available. Install with:")
    print("pip install insightface onnxruntime opencv-python")

# Embedding version for migration tracking
FACE_EMBEDDING_VERSION = "arcface_r50_v1"

class FaceClusterer:
    """Face detection and clustering system."""
    
    def __init__(self, db_path: str = "face_clusters.db"):
        """
        Initialize face clusterer.
        
        Args:
            db_path: Path to SQLite database for storing face data
        """
        self.db_path = db_path
        self.conn = None
        self.face_detector = None
        self.embedding_model = None
        self._initialize_database()
        self._initialize_models()
    
    def _initialize_database(self):
        """Initialize database and create tables."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Create faces table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS faces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_path TEXT NOT NULL,
                bounding_box TEXT NOT NULL,  -- JSON: [x, y, width, height]
                embedding BLOB,  -- Face embedding vector
                cluster_id INTEGER,
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(image_path, bounding_box)
            )
        """)
        
        # Create clusters table
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
        
        # Create cluster membership table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS cluster_membership (
                cluster_id INTEGER,
                face_id INTEGER,
                PRIMARY KEY (cluster_id, face_id),
                FOREIGN KEY (cluster_id) REFERENCES clusters(id),
                FOREIGN KEY (face_id) REFERENCES faces(id)
            )
        """)
        
        # Create image clusters table (for quick lookup)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS image_clusters (
                image_path TEXT PRIMARY KEY,
                cluster_ids TEXT,  -- JSON array of cluster IDs
                face_count INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_faces_image ON faces(image_path)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_faces_cluster ON faces(cluster_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_clusters_representative ON clusters(representative_face_id)")
        
        self.conn.commit()
    
    def _initialize_models(self):
        """Initialize face detection and embedding models with GPU auto-detection."""
        if not FACE_LIBRARIES_AVAILABLE:
            print("Face libraries not available, skipping model initialization")
            return
        
        try:
            # Determine model storage path
            model_root = Path("./models")
            model_root.mkdir(exist_ok=True)
            
            # Initialize InsightFace with auto-detected providers
            # buffalo_l includes RetinaFace (detection) + ArcFace (embedding)
            self.face_analyzer = FaceAnalysis(
                name='buffalo_l',
                root=str(model_root),
                providers=_DEFAULT_PROVIDERS
            )
            
            # Prepare with detection threshold
            # ctx_id=-1 means use first available device
            self.face_analyzer.prepare(ctx_id=-1, det_thresh=0.5)
            
            print(f"Face models initialized (device: {_DEVICE_INFO})")
            print(f"Embedding version: {FACE_EMBEDDING_VERSION}")
            
        except Exception as e:
            print(f"Error initializing face models: {e}")
            print("Face detection will be disabled")
            self.face_analyzer = None
    
    def detect_faces(self, image_path: str) -> List[Dict]:
        """
        Detect faces in an image using InsightFace RetinaFace.
        
        Args:
            image_path: Path to image file
            
        Returns:
            List of face detection results with bounding boxes and embeddings
        """
        if not FACE_LIBRARIES_AVAILABLE or not hasattr(self, 'face_analyzer') or self.face_analyzer is None:
            return []
        
        try:
            # Read image with OpenCV (InsightFace expects BGR)
            img = cv2.imread(image_path)
            if img is None:
                print(f"Could not read image: {image_path}")
                return []
            
            # Detect faces - InsightFace returns Face objects with:
            # - bbox: [x1, y1, x2, y2]
            # - det_score: detection confidence
            # - embedding: 512-dim ArcFace vector
            # - age, gender (optional attributes)
            faces = self.face_analyzer.get(img)
            
            # Convert to our format
            results = []
            for face in faces:
                # Convert bbox from [x1,y1,x2,y2] to [x,y,width,height] for compatibility
                x1, y1, x2, y2 = face.bbox
                bounding_box = [int(x1), int(y1), int(x2 - x1), int(y2 - y1)]
                
                result = {
                    'bounding_box': bounding_box,
                    'confidence': float(face.det_score),
                    'embedding': face.embedding,  # 512-dim ArcFace embedding
                    'embedding_version': FACE_EMBEDDING_VERSION,
                }
                
                # Add optional attributes if available
                if hasattr(face, 'age') and face.age is not None:
                    result['age'] = int(face.age)
                if hasattr(face, 'gender') and face.gender is not None:
                    result['gender'] = 'M' if face.gender == 1 else 'F'
                
                results.append(result)
            
            return results
            
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
        if not FACE_LIBRARIES_AVAILABLE or not hasattr(self, 'face_analyzer') or self.face_analyzer is None:
            return None
        
        try:
            # Read image
            img = cv2.imread(image_path)
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
    
    def cluster_faces(self, image_paths: List[str], eps: float = 0.6, min_samples: int = 2) -> Dict:
        """
        Cluster faces across multiple images using DBSCAN.
        
        Args:
            image_paths: List of image file paths
            eps: DBSCAN eps parameter (maximum distance between samples)
            min_samples: DBSCAN min_samples parameter (minimum samples per cluster)
            
        Returns:
            Dictionary with clustering results
        """
        if not FACE_LIBRARIES_AVAILABLE:
            return {'status': 'error', 'message': 'Face libraries not available'}
        
        try:
            from sklearn.cluster import DBSCAN
            
            all_embeddings = []
            face_records = []
            
            # Process each image
            for i, image_path in enumerate(image_paths):
                print(f"Processing {i+1}/{len(image_paths)}: {image_path}")
                
                # Detect faces
                faces = self.detect_faces(image_path)
                
                for j, face in enumerate(faces):
                    # Extract embedding
                    embedding = self.extract_face_embedding(image_path, face['bounding_box'])
                    
                    if embedding is not None:
                        all_embeddings.append(embedding)
                        face_records.append({
                            'image_path': image_path,
                            'bounding_box': face['bounding_box'],
                            'confidence': face['confidence'],
                            'index': len(all_embeddings) - 1
                        })
            
            if not all_embeddings:
                return {'status': 'completed', 'clusters': [], 'message': 'No faces found'}
            
            # Convert to numpy array
            embeddings_array = np.array(all_embeddings)
            
            # Perform DBSCAN clustering
            clustering = DBSCAN(eps=eps, min_samples=min_samples, metric='cosine')
            cluster_labels = clustering.fit_predict(embeddings_array)
            
            # Store results in database
            cursor = self.conn.cursor()
            
            # Clear existing data for these images
            for image_path in image_paths:
                cursor.execute("DELETE FROM faces WHERE image_path = ?", (image_path,))
            
            # Insert faces
            for record in face_records:
                embedding_blob = record['embedding'].tobytes() if 'embedding' in record else None
                
                cursor.execute("""
                    INSERT INTO faces 
                    (image_path, bounding_box, embedding, confidence)
                    VALUES (?, ?, ?, ?)
                """, (
                    record['image_path'],
                    json.dumps(record['bounding_box']),
                    embedding_blob,
                    record['confidence']
                ))
            
            # Get face IDs
            cursor.execute("SELECT id, image_path FROM faces WHERE image_path IN ({})".format(
                ','.join('?' for _ in image_paths)
            ), image_paths)
            
            face_id_map = {}
            for row in cursor.fetchall():
                face_id_map[(row['image_path'], row['id'])] = row['id']
            
            # Create clusters
            unique_labels = set(cluster_labels)
            clusters_created = []
            
            for label in unique_labels:
                if label == -1:  # Noise
                    continue
                
                # Get faces in this cluster
                cluster_faces = [record for record, cluster_label in zip(face_records, cluster_labels) 
                                if cluster_label == label]
                
                if len(cluster_faces) >= min_samples:
                    # Create cluster
                    representative_face = cluster_faces[0]
                    
                    cursor.execute("""
                        INSERT INTO clusters 
                        (representative_face_id, size)
                        VALUES (?, ?)
                    """, (face_id_map[(representative_face['image_path'], representative_face['index'])], len(cluster_faces)))
                    
                    cluster_id = cursor.lastrowid
                    clusters_created.append(cluster_id)
                    
                    # Update faces with cluster ID
                    for face_record in cluster_faces:
                        face_id = face_id_map[(face_record['image_path'], face_record['index'])]
                        cursor.execute("""
                            UPDATE faces 
                            SET cluster_id = ?
                            WHERE id = ?
                        """, (cluster_id, face_id))
                        
                        # Add to cluster membership
                        cursor.execute("""
                            INSERT INTO cluster_membership 
                            (cluster_id, face_id)
                            VALUES (?, ?)
                        """, (cluster_id, face_id))
            
            # Update image clusters
            for image_path in image_paths:
                cursor.execute("""
                    SELECT cluster_id FROM faces 
                    WHERE image_path = ? AND cluster_id IS NOT NULL
                """, (image_path,))
                
                cluster_ids = [row['cluster_id'] for row in cursor.fetchall()]
                face_count = len(cluster_ids)
                
                if cluster_ids:
                    cursor.execute("""
                        INSERT OR REPLACE INTO image_clusters 
                        (image_path, cluster_ids, face_count)
                        VALUES (?, ?, ?)
                    """, (image_path, json.dumps(cluster_ids), face_count))
            
            self.conn.commit()
            
            # Return results
            return {
                'status': 'completed',
                'total_faces': len(face_records),
                'total_clusters': len(clusters_created),
                'clusters': clusters_created,
                'message': f'Found {len(face_records)} faces in {len(clusters_created)} clusters'
            }
            
        except Exception as e:
            self.conn.rollback()
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