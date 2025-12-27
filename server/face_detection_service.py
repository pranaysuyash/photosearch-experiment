"""
Face Detection Service

Provides face detection capabilities using the enhanced face clustering module.
This service bridges the gap between the database layer and actual face detection.
"""

import os
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
import numpy as np

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class DetectedFace:
    """Represents a detected face with all relevant information."""

    detection_id: str
    photo_path: str
    bounding_box: Dict[str, float]  # {x, y, width, height}
    embedding: Optional[List[float]] = None
    quality_score: Optional[float] = None
    confidence: Optional[float] = None
    landmarks: Optional[Dict] = None
    pose: Optional[Dict] = None  # {yaw, pitch, roll}
    age_estimate: Optional[float] = None
    age_confidence: Optional[float] = None
    gender: Optional[str] = None
    gender_confidence: Optional[float] = None
    emotion: Optional[str] = None
    emotion_confidence: Optional[float] = None
    pose_type: Optional[str] = None
    pose_confidence: Optional[float] = None
    lighting_score: Optional[float] = None
    occlusion_score: Optional[float] = None
    resolution_score: Optional[float] = None
    pose_quality_score: Optional[float] = None
    overall_quality: Optional[float] = None


@dataclass
class FaceDetectionResult:
    """Result of face detection for a single photo."""

    photo_path: str
    faces: List[DetectedFace]
    processing_time: float
    success: bool
    error: Optional[str] = None


class FaceDetectionService:
    """Service for detecting faces in photos using enhanced face clustering."""

    def __init__(self):
        """Initialize the face detection service."""
        try:
            # Import the enhanced face clusterer
            from src.enhanced_face_clustering import EnhancedFaceClusterer

            self.clusterer = EnhancedFaceClusterer()
            self.initialized = True
            logger.info("Face detection service initialized successfully")
        except ImportError as e:
            logger.error(f"Failed to import EnhancedFaceClusterer: {e}")
            self.initialized = False
            self.clusterer = None
        except Exception as e:
            logger.error(f"Failed to initialize face detection service: {e}")
            self.initialized = False
            self.clusterer = None

    def is_available(self) -> bool:
        """Check if face detection is available."""
        return self.initialized and self.clusterer is not None

    @staticmethod
    def _to_bbox_dict(detection) -> Dict[str, float]:
        """Normalize bounding box structure from detection outputs."""
        if hasattr(detection, "bbox_x"):
            return {
                "x": getattr(detection, "bbox_x", 0.0),
                "y": getattr(detection, "bbox_y", 0.0),
                "width": getattr(detection, "bbox_width", 0.0),
                "height": getattr(detection, "bbox_height", 0.0),
            }

        bbox = getattr(detection, "bbox", None)
        if bbox and len(bbox) >= 4:
            return {
                "x": bbox[0],
                "y": bbox[1],
                "width": bbox[2] - bbox[0],
                "height": bbox[3] - bbox[1],
            }

        return {"x": 0.0, "y": 0.0, "width": 0.0, "height": 0.0}

    def detect_faces(self, photo_path: str) -> FaceDetectionResult:
        """Detect faces in a single photo."""
        if not self.is_available():
            return FaceDetectionResult(
                photo_path=photo_path,
                faces=[],
                processing_time=0.0,
                success=False,
                error="Face detection service not available",
            )

        if not os.path.exists(photo_path):
            return FaceDetectionResult(
                photo_path=photo_path,
                faces=[],
                processing_time=0.0,
                success=False,
                error="Photo file not found",
            )

        try:
            import time

            start_time = time.time()

            # Use the enhanced face clusterer to detect faces
            detection_results = self.clusterer.detect_faces(
                photo_path,
                include_embeddings=True,
                include_landmarks=True,
                include_pose=True,
            )

            processing_time = time.time() - start_time

            # Convert to our standard format
            faces = []
            for i, detection in enumerate(detection_results):
                pose_data = getattr(detection, "pose_angles", None) or getattr(detection, "pose", None)
                pose_dict = None
                if isinstance(pose_data, dict):
                    pose_dict = {
                        "yaw": pose_data.get("yaw"),
                        "pitch": pose_data.get("pitch"),
                        "roll": pose_data.get("roll"),
                    }
                elif isinstance(pose_data, (list, tuple)) and len(pose_data) >= 3:
                    pose_dict = {"yaw": pose_data[0], "pitch": pose_data[1], "roll": pose_data[2]}

                face = DetectedFace(
                    detection_id=f"face_{os.path.basename(photo_path)}_{i}",
                    photo_path=photo_path,
                    bounding_box=self._to_bbox_dict(detection),
                    embedding=detection.embedding.tolist() if detection.embedding is not None else None,
                    quality_score=getattr(detection, "quality_score", getattr(detection, "quality", None)),
                    confidence=getattr(detection, "confidence", None),
                    landmarks=getattr(detection, "landmarks", None),
                    pose=pose_dict,
                    age_estimate=getattr(detection, "age_estimate", None),
                    age_confidence=getattr(detection, "age_confidence", None),
                    gender=getattr(detection, "gender", None),
                    gender_confidence=getattr(detection, "gender_confidence", None),
                    emotion=getattr(detection, "emotion", None),
                    emotion_confidence=getattr(detection, "emotion_confidence", None),
                    pose_type=getattr(detection, "pose_type", None),
                    pose_confidence=getattr(detection, "pose_confidence", None),
                    lighting_score=getattr(detection, "lighting_score", None),
                    occlusion_score=getattr(detection, "occlusion_score", None),
                    resolution_score=getattr(detection, "resolution_score", None),
                    pose_quality_score=getattr(detection, "pose_quality_score", None),
                    overall_quality=getattr(detection, "overall_quality", None),
                )
                faces.append(face)

            return FaceDetectionResult(
                photo_path=photo_path,
                faces=faces,
                processing_time=processing_time,
                success=True,
            )

        except Exception as e:
            logger.error(f"Error detecting faces in {photo_path}: {e}")
            return FaceDetectionResult(
                photo_path=photo_path,
                faces=[],
                processing_time=0.0,
                success=False,
                error=str(e),
            )

    def detect_faces_from_array(self, image_array: np.ndarray, source_id: str = "array") -> FaceDetectionResult:
        """
        Detect faces in an image provided as a numpy array.

        This method is used for video frame processing where we have
        the frame already in memory as a numpy array.

        Args:
            image_array: RGB image as numpy array (H, W, 3)
            source_id: Identifier for the source (useful for logging)

        Returns:
            FaceDetectionResult with detected faces
        """
        if not self.is_available():
            return FaceDetectionResult(
                photo_path=source_id,
                faces=[],
                processing_time=0.0,
                success=False,
                error="Face detection service not available",
            )

        try:
            import time

            start_time = time.time()

            # Use the enhanced face clusterer to detect faces from array
            # The clusterer should support detect_faces_from_array or we use detect_from_image
            if hasattr(self.clusterer, "detect_faces_from_array"):
                detection_results = self.clusterer.detect_faces_from_array(
                    image_array,
                    include_embeddings=True,
                    include_landmarks=True,
                    include_pose=True,
                )
            elif hasattr(self.clusterer, "detect_from_image"):
                detection_results = self.clusterer.detect_from_image(
                    image_array,
                    include_embeddings=True,
                    include_landmarks=True,
                    include_pose=True,
                )
            else:
                # Fallback: save to temp file and detect
                import tempfile
                import cv2

                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                    # Convert RGB to BGR for cv2
                    bgr_image = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
                    cv2.imwrite(tmp.name, bgr_image)
                    detection_results = self.clusterer.detect_faces(
                        tmp.name,
                        include_embeddings=True,
                        include_landmarks=True,
                        include_pose=True,
                    )
                    os.unlink(tmp.name)

            processing_time = time.time() - start_time

            # Convert to our standard format
            faces = []
            for i, detection in enumerate(detection_results):
                pose_data = getattr(detection, "pose_angles", None) or getattr(detection, "pose", None)
                pose_dict = None
                if isinstance(pose_data, dict):
                    pose_dict = {
                        "yaw": pose_data.get("yaw"),
                        "pitch": pose_data.get("pitch"),
                        "roll": pose_data.get("roll"),
                    }
                elif isinstance(pose_data, (list, tuple)) and len(pose_data) >= 3:
                    pose_dict = {"yaw": pose_data[0], "pitch": pose_data[1], "roll": pose_data[2]}

                face = DetectedFace(
                    detection_id=f"face_{source_id}_{i}",
                    photo_path=source_id,
                    bounding_box=self._to_bbox_dict(detection),
                    embedding=detection.embedding.tolist() if detection.embedding is not None else None,
                    quality_score=getattr(detection, "quality_score", getattr(detection, "quality", None)),
                    confidence=getattr(detection, "confidence", None),
                    landmarks=getattr(detection, "landmarks", None),
                    pose=pose_dict,
                    age_estimate=getattr(detection, "age_estimate", None),
                    age_confidence=getattr(detection, "age_confidence", None),
                    gender=getattr(detection, "gender", None),
                    gender_confidence=getattr(detection, "gender_confidence", None),
                    emotion=getattr(detection, "emotion", None),
                    emotion_confidence=getattr(detection, "emotion_confidence", None),
                    pose_type=getattr(detection, "pose_type", None),
                    pose_confidence=getattr(detection, "pose_confidence", None),
                    lighting_score=getattr(detection, "lighting_score", None),
                    occlusion_score=getattr(detection, "occlusion_score", None),
                    resolution_score=getattr(detection, "resolution_score", None),
                    pose_quality_score=getattr(detection, "pose_quality_score", None),
                    overall_quality=getattr(detection, "overall_quality", None),
                )
                faces.append(face)

            return FaceDetectionResult(
                photo_path=source_id,
                faces=faces,
                processing_time=processing_time,
                success=True,
            )

        except Exception as e:
            logger.error(f"Error detecting faces from array ({source_id}): {e}")
            return FaceDetectionResult(
                photo_path=source_id,
                faces=[],
                processing_time=0.0,
                success=False,
                error=str(e),
            )

    def detect_faces_batch(self, photo_paths: List[str], batch_size: int = 10) -> List[FaceDetectionResult]:
        """Detect faces in multiple photos with batch processing."""
        results = []

        for i in range(0, len(photo_paths), batch_size):
            batch = photo_paths[i : i + batch_size]
            batch_results = []

            for photo_path in batch:
                result = self.detect_faces(photo_path)
                batch_results.append(result)

            results.extend(batch_results)

            # Log progress
            progress = min((i + len(batch)) / len(photo_paths), 1.0)
            logger.info(f"Processed {i + len(batch)}/{len(photo_paths)} photos ({progress:.1%})")

        return results

    def get_face_thumbnail(self, photo_path: str, face: DetectedFace) -> Optional[str]:
        """Extract a thumbnail of a specific face from a photo."""
        if not self.is_available():
            return None

        try:
            # Use the clusterer to extract face thumbnail
            thumbnail_data = self.clusterer.extract_face_thumbnail(photo_path, face.bounding_box)

            if thumbnail_data:
                # Convert to base64 for easy transmission
                import base64

                return f"data:image/jpeg;base64,{base64.b64encode(thumbnail_data).decode('utf-8')}"

        except Exception as e:
            logger.error(f"Error extracting face thumbnail: {e}")

        return None

    def analyze_face_quality(self, face: DetectedFace) -> Dict:
        """Analyze the quality of a detected face."""
        if not self.is_available() or face.embedding is None:
            return {
                "quality_score": face.quality_score or 0.5,
                "issues": ["Face detection service not available"],
            }

        try:
            # Use the clusterer to analyze face quality
            quality_analysis = self.clusterer.analyze_face_quality(face.embedding, face.landmarks, face.pose)

            return {
                "quality_score": quality_analysis.score,
                "issues": quality_analysis.issues,
                "recommendations": quality_analysis.recommendations,
            }

        except Exception as e:
            logger.error(f"Error analyzing face quality: {e}")
            return {"quality_score": face.quality_score or 0.5, "issues": [str(e)]}


def get_face_detection_service() -> FaceDetectionService:
    """Get the face detection service instance."""
    return FaceDetectionService()
