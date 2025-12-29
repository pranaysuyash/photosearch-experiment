"""
Secure Face Clustering Wrapper

Wraps the existing face clustering system with enhanced security features:
- Per-user encryption for face embeddings
- Input validation and sanitization
- Secure file handling
- Privacy-compliant processing
"""

import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from server.security.key_manager import get_key_manager, encrypt_face_embedding, decrypt_face_embedding
from server.security.input_validator import validate_file_upload, sanitize_user_input, ValidationError
from src.enhanced_face_clustering import EnhancedFaceClusterer, FaceDetection

logger = logging.getLogger(__name__)


class SecureFaceClusterer:
    """
    Secure wrapper for face clustering with enhanced security features.

    Features:
    - Per-user encryption of face embeddings
    - Input validation for all file operations
    - Secure storage of face data
    - Privacy-compliant processing
    - Audit logging for security events
    """

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.key_manager = get_key_manager()
        self.base_clusterer = EnhancedFaceClusterer()

        logger.info(f"Initialized SecureFaceClusterer for user: {user_id}")

    def process_image_secure(self, image_path: Path, validate_input: bool = True) -> Dict[str, Any]:
        """
        Process an image with security validation and encrypted storage.

        Args:
            image_path: Path to the image file
            validate_input: Whether to validate the input file

        Returns:
            Processing result with encrypted face data

        Raises:
            ValidationError: If file validation fails
        """
        try:
            # Validate input file if requested
            if validate_input:
                validation_result = validate_file_upload(image_path, "image")
                if not validation_result.get("valid", False):
                    raise ValidationError(f"File validation failed: {validation_result}")

                # Check for security issues in validation
                content_validation = validation_result.get("content_validation", {})
                if not content_validation.get("safe", True):
                    issues = content_validation.get("issues", [])
                    raise ValidationError(f"Security issues detected: {', '.join(issues)}")

            # Process image using base clusterer
            detections = self.base_clusterer.detect_faces(str(image_path))

            # Encrypt face embeddings
            secure_detections = []
            for detection in detections:
                secure_detection = self._encrypt_face_detection(detection)
                secure_detections.append(secure_detection)

            # Log security event
            logger.info(
                f"Processed image securely: {image_path}, found {len(detections)} faces for user {self.user_id}"
            )

            return {
                "image_path": str(image_path),
                "face_count": len(detections),
                "detections": secure_detections,
                "user_id": self.user_id,
                "encrypted": True,
            }

        except Exception as e:
            logger.error(f"Secure image processing failed for {image_path}: {e}")
            raise

    def process_directory_secure(
        self, directory_path: Path, validate_files: bool = True, progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Process a directory of images with security validation.

        Args:
            directory_path: Path to the directory
            validate_files: Whether to validate each file
            progress_callback: Optional callback for progress updates

        Returns:
            Processing results with encrypted face data
        """
        try:
            # Validate directory path
            if not directory_path.exists() or not directory_path.is_dir():
                raise ValidationError(f"Invalid directory path: {directory_path}")

            # Discover image files
            image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".heic", ".heif"}
            image_files = []

            for file_path in directory_path.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                    image_files.append(file_path)

            logger.info(f"Found {len(image_files)} image files in {directory_path}")

            # Process files securely
            results = []
            processed_count = 0

            for image_file in image_files:
                try:
                    result = self.process_image_secure(image_file, validate_files)
                    results.append(result)
                    processed_count += 1

                    # Call progress callback if provided
                    if progress_callback:
                        progress_callback(processed_count, len(image_files), str(image_file))

                except Exception as e:
                    logger.warning(f"Failed to process {image_file}: {e}")
                    results.append({"image_path": str(image_file), "error": str(e), "user_id": self.user_id})

            # Perform secure clustering
            clustering_result = self._perform_secure_clustering(results)

            return {
                "directory": str(directory_path),
                "total_files": len(image_files),
                "processed_files": processed_count,
                "failed_files": len(image_files) - processed_count,
                "results": results,
                "clustering": clustering_result,
                "user_id": self.user_id,
            }

        except Exception as e:
            logger.error(f"Secure directory processing failed for {directory_path}: {e}")
            raise

    def search_faces_secure(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Search for faces with input validation and decryption.

        Args:
            query: Search query (person name or description)
            max_results: Maximum number of results to return

        Returns:
            List of matching faces with decrypted data
        """
        try:
            # Sanitize search query
            sanitized_query = sanitize_user_input(query, max_length=200)

            if not sanitized_query.strip():
                return []

            # Search using base clusterer
            raw_results = self.base_clusterer.search_by_person(sanitized_query)

            # Decrypt and return results
            secure_results = []
            for result in raw_results[:max_results]:
                try:
                    decrypted_result = self._decrypt_search_result(result)
                    secure_results.append(decrypted_result)
                except Exception as e:
                    logger.warning(f"Failed to decrypt search result: {e}")

            logger.info(
                f"Secure face search for '{sanitized_query}' returned {len(secure_results)} results for user {self.user_id}"
            )

            return secure_results

        except Exception as e:
            logger.error(f"Secure face search failed: {e}")
            raise

    def get_person_clusters_secure(self) -> List[Dict[str, Any]]:
        """
        Get all person clusters with decrypted data.

        Returns:
            List of person clusters with decrypted face data
        """
        try:
            # Get clusters from base clusterer
            raw_clusters = self.base_clusterer.get_all_clusters()

            # Decrypt cluster data
            secure_clusters = []
            for cluster in raw_clusters:
                try:
                    decrypted_cluster = self._decrypt_cluster_data(cluster)
                    secure_clusters.append(decrypted_cluster)
                except Exception as e:
                    logger.warning(f"Failed to decrypt cluster data: {e}")

            logger.info(f"Retrieved {len(secure_clusters)} person clusters for user {self.user_id}")

            return secure_clusters

        except Exception as e:
            logger.error(f"Failed to get person clusters: {e}")
            raise

    def add_person_label_secure(self, cluster_id: str, person_name: str) -> bool:
        """
        Add a person label to a cluster with input validation.

        Args:
            cluster_id: ID of the cluster to label
            person_name: Name of the person

        Returns:
            True if successful, False otherwise
        """
        try:
            # Sanitize inputs
            sanitized_cluster_id = sanitize_user_input(cluster_id, max_length=100)
            sanitized_person_name = sanitize_user_input(person_name, max_length=200)

            if not sanitized_cluster_id or not sanitized_person_name:
                raise ValidationError("Cluster ID and person name cannot be empty")

            # Update label using base clusterer
            success = self.base_clusterer.update_cluster_label(sanitized_cluster_id, sanitized_person_name)

            if success:
                logger.info(
                    f"Added person label '{sanitized_person_name}' to cluster {sanitized_cluster_id} for user {self.user_id}"
                )

            return success

        except Exception as e:
            logger.error(f"Failed to add person label: {e}")
            return False

    def delete_person_data_secure(self, person_id: str, reason: str = "User request") -> bool:
        """
        Securely delete all data for a person (GDPR compliance).

        Args:
            person_id: ID of the person to delete
            reason: Reason for deletion (for audit log)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Sanitize inputs
            sanitized_person_id = sanitize_user_input(person_id, max_length=100)
            sanitized_reason = sanitize_user_input(reason, max_length=500)

            if not sanitized_person_id:
                raise ValidationError("Person ID cannot be empty")

            # Delete from base clusterer
            success = self.base_clusterer.delete_cluster(sanitized_person_id)

            if success:
                # Log deletion for audit
                logger.info(
                    f"Deleted person data for {sanitized_person_id}, reason: {sanitized_reason}, user: {self.user_id}"
                )

                # Also delete any user-specific encryption keys if needed
                # (This would be implemented based on specific requirements)

            return success

        except Exception as e:
            logger.error(f"Failed to delete person data: {e}")
            return False

    def _encrypt_face_detection(self, detection: FaceDetection) -> Dict[str, Any]:
        """Encrypt face detection data"""
        try:
            # Convert embedding to bytes
            embedding_bytes = detection.embedding.tobytes()

            # Encrypt embedding
            encrypted_embedding = encrypt_face_embedding(embedding_bytes, self.user_id)

            # Return detection with encrypted embedding
            return {
                "bbox": detection.bbox.tolist() if hasattr(detection.bbox, "tolist") else detection.bbox,
                "confidence": float(detection.confidence),
                "encrypted_embedding": encrypted_embedding.hex(),  # Store as hex string
                "embedding_shape": detection.embedding.shape,
                "embedding_dtype": str(detection.embedding.dtype),
                "quality_score": getattr(detection, "quality_score", 0.0),
                "encrypted": True,
            }

        except Exception as e:
            logger.error(f"Failed to encrypt face detection: {e}")
            raise

    def _decrypt_face_detection(self, encrypted_detection: Dict[str, Any]) -> FaceDetection:
        """Decrypt face detection data"""
        try:
            # Decrypt embedding
            encrypted_embedding = bytes.fromhex(encrypted_detection["encrypted_embedding"])
            embedding_bytes = decrypt_face_embedding(encrypted_embedding, self.user_id)

            # Reconstruct embedding array
            embedding_shape = tuple(encrypted_detection["embedding_shape"])
            embedding_dtype = np.dtype(encrypted_detection["embedding_dtype"])
            embedding = np.frombuffer(embedding_bytes, dtype=embedding_dtype).reshape(embedding_shape)

            # Create FaceDetection object
            detection = FaceDetection(
                bbox=np.array(encrypted_detection["bbox"]),
                confidence=encrypted_detection["confidence"],
                embedding=embedding,
            )

            # Add quality score if available
            if "quality_score" in encrypted_detection:
                detection.quality_score = encrypted_detection["quality_score"]

            return detection

        except Exception as e:
            logger.error(f"Failed to decrypt face detection: {e}")
            raise

    def _perform_secure_clustering(self, detection_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform clustering on encrypted face data"""
        try:
            # Decrypt embeddings for clustering
            all_embeddings = []
            detection_map = {}

            for i, result in enumerate(detection_results):
                if "detections" in result and result["detections"]:
                    for j, encrypted_detection in enumerate(result["detections"]):
                        if encrypted_detection.get("encrypted"):
                            try:
                                detection = self._decrypt_face_detection(encrypted_detection)
                                all_embeddings.append(detection.embedding)
                                detection_map[len(all_embeddings) - 1] = (i, j)
                            except Exception as e:
                                logger.warning(f"Failed to decrypt detection for clustering: {e}")

            if not all_embeddings:
                return {"clusters": [], "total_faces": 0}

            # Perform clustering using base clusterer's clustering logic
            embeddings_array = np.array(all_embeddings)

            # Use the base clusterer's update clustering method
            # This is a simplified clustering approach for the secure wrapper
            cluster_labels = []
            for i, embedding in enumerate(embeddings_array):
                # Simple similarity-based clustering (placeholder)
                cluster_labels.append(i % 10)  # Simplified clustering for demo

            # Group results by cluster
            clusters = {}
            for embedding_idx, cluster_label in enumerate(cluster_labels):
                if cluster_label not in clusters:
                    clusters[cluster_label] = []

                result_idx, detection_idx = detection_map[embedding_idx]
                clusters[cluster_label].append(
                    {
                        "result_index": result_idx,
                        "detection_index": detection_idx,
                        "image_path": detection_results[result_idx]["image_path"],
                    }
                )

            # Convert to list format
            cluster_list = []
            for cluster_id, faces in clusters.items():
                cluster_list.append({"cluster_id": f"cluster_{cluster_id}", "face_count": len(faces), "faces": faces})

            return {"clusters": cluster_list, "total_faces": len(all_embeddings), "total_clusters": len(clusters)}

        except Exception as e:
            logger.error(f"Secure clustering failed: {e}")
            return {"clusters": [], "total_faces": 0, "error": str(e)}

    def _decrypt_search_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt search result data"""
        # This would decrypt any encrypted fields in search results
        # Implementation depends on the structure of search results
        return result

    def _decrypt_cluster_data(self, cluster: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt cluster data"""
        # This would decrypt any encrypted fields in cluster data
        # Implementation depends on the structure of cluster data
        return cluster

    def get_security_info(self) -> Dict[str, Any]:
        """
        Get information about the security configuration.

        Returns:
            Dictionary with security information
        """
        key_info = self.key_manager.get_key_info()

        return {
            "user_id": self.user_id,
            "encryption_enabled": True,
            "key_management": key_info,
            "input_validation_enabled": True,
            "audit_logging_enabled": True,
        }


# Convenience functions
def create_secure_clusterer(user_id: str = "default") -> SecureFaceClusterer:
    """Create a secure face clusterer for a specific user"""
    return SecureFaceClusterer(user_id)


def process_image_with_security(image_path: Path, user_id: str = "default") -> Dict[str, Any]:
    """Process a single image with full security features"""
    clusterer = SecureFaceClusterer(user_id)
    return clusterer.process_image_secure(image_path)


def search_faces_with_security(query: str, user_id: str = "default") -> List[Dict[str, Any]]:
    """Search faces with full security features"""
    clusterer = SecureFaceClusterer(user_id)
    return clusterer.search_faces_secure(query)
