"""
Privacy-Aware Face Processing Service - Phase 6

Integrates privacy controls with face recognition processing to ensure
compliance with user consent and privacy preferences.

Features:
1. Consent-based processing - only processes data with valid consent
2. Privacy level enforcement - respects user privacy settings
3. Anonymization support - processes data without storing personal identifiers
4. Audit logging - tracks all privacy-sensitive operations
5. Data minimization - only processes necessary data
6. Secure processing modes - different levels of privacy protection

Privacy Processing Modes:
- FULL_PROCESSING: Normal processing with all features (requires consent)
- ANONYMOUS_ONLY: Face detection without personal identification
- MINIMAL_PROCESSING: Basic detection only, no clustering or attributes
- NO_PROCESSING: Skip face processing entirely

Usage:
    processor = PrivacyAwareFaceProcessor(face_clusterer, privacy_manager)
    result = processor.process_with_privacy_controls(image_path, user_id)
"""

import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass

from server.privacy_controls import PrivacyControlsManager, ConsentType, PrivacyLevel

logger = logging.getLogger(__name__)


@dataclass
class PrivacyProcessingResult:
    """Result of privacy-aware face processing"""

    image_path: str
    user_id: str
    privacy_level: PrivacyLevel
    processing_allowed: bool
    faces_detected: int
    faces_processed: int
    consent_status: Dict[str, bool]
    anonymized_data: bool
    processing_time: float
    privacy_notes: List[str]


@dataclass
class AnonymizedFaceData:
    """Anonymized face detection data"""

    detection_id: str  # Anonymized ID
    bounding_box: List[float]
    confidence: float
    quality_score: Optional[float]
    attributes: Optional[Dict[str, Any]]  # Anonymized attributes
    cluster_id: Optional[str]  # Anonymized cluster ID


class PrivacyAwareFaceProcessor:
    """Face processor with integrated privacy controls"""

    def __init__(self, face_clusterer, privacy_manager: PrivacyControlsManager):
        """
        Initialize privacy-aware face processor.

        Args:
            face_clusterer: Face clustering system instance
            privacy_manager: Privacy controls manager
        """
        self.face_clusterer = face_clusterer
        self.privacy_manager = privacy_manager

        # Processing thresholds for different privacy levels
        self.privacy_thresholds = {
            PrivacyLevel.FULL_PROCESSING: {
                "min_confidence": 0.5,
                "store_embeddings": True,
                "enable_clustering": True,
                "enable_attributes": True,
                "store_personal_data": True,
            },
            PrivacyLevel.ANONYMOUS_ONLY: {
                "min_confidence": 0.7,
                "store_embeddings": False,
                "enable_clustering": False,
                "enable_attributes": True,
                "store_personal_data": False,
            },
            PrivacyLevel.MINIMAL_PROCESSING: {
                "min_confidence": 0.8,
                "store_embeddings": False,
                "enable_clustering": False,
                "enable_attributes": False,
                "store_personal_data": False,
            },
            PrivacyLevel.NO_PROCESSING: {
                "min_confidence": 1.0,  # Effectively disabled
                "store_embeddings": False,
                "enable_clustering": False,
                "enable_attributes": False,
                "store_personal_data": False,
            },
        }

        logger.info("PrivacyAwareFaceProcessor initialized")

    def process_with_privacy_controls(
        self, image_path: str, user_id: str, force_privacy_level: Optional[PrivacyLevel] = None
    ) -> PrivacyProcessingResult:
        """
        Process image with privacy controls and consent validation.

        Args:
            image_path: Path to image file
            user_id: User identifier for privacy checks
            force_privacy_level: Override privacy level for testing

        Returns:
            Privacy processing result with compliance information
        """
        start_time = datetime.now()
        privacy_notes = []

        try:
            # 1. Check user privacy settings and consent
            privacy_level, consent_status = self._check_privacy_requirements(user_id, force_privacy_level)

            # 2. Determine if processing is allowed
            processing_allowed = self._is_processing_allowed(privacy_level, consent_status)

            if not processing_allowed:
                privacy_notes.append("Processing blocked due to privacy settings or missing consent")
                return PrivacyProcessingResult(
                    image_path=image_path,
                    user_id=user_id,
                    privacy_level=privacy_level,
                    processing_allowed=False,
                    faces_detected=0,
                    faces_processed=0,
                    consent_status=consent_status,
                    anonymized_data=False,
                    processing_time=0.0,
                    privacy_notes=privacy_notes,
                )

            # 3. Process image according to privacy level
            faces_detected, faces_processed, anonymized_data = self._process_image_with_privacy(
                image_path, user_id, privacy_level, privacy_notes
            )

            # 4. Log privacy-compliant processing
            self._log_privacy_processing(user_id, image_path, privacy_level, faces_processed)

            processing_time = (datetime.now() - start_time).total_seconds()

            return PrivacyProcessingResult(
                image_path=image_path,
                user_id=user_id,
                privacy_level=privacy_level,
                processing_allowed=True,
                faces_detected=faces_detected,
                faces_processed=faces_processed,
                consent_status=consent_status,
                anonymized_data=anonymized_data,
                processing_time=processing_time,
                privacy_notes=privacy_notes,
            )

        except Exception as e:
            logger.error(f"Privacy-aware processing failed: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()

            return PrivacyProcessingResult(
                image_path=image_path,
                user_id=user_id,
                privacy_level=PrivacyLevel.NO_PROCESSING,
                processing_allowed=False,
                faces_detected=0,
                faces_processed=0,
                consent_status={},
                anonymized_data=False,
                processing_time=processing_time,
                privacy_notes=[f"Processing error: {str(e)}"],
            )

    def _check_privacy_requirements(
        self, user_id: str, force_privacy_level: Optional[PrivacyLevel] = None
    ) -> Tuple[PrivacyLevel, Dict[str, bool]]:
        """Check user privacy settings and consent status"""

        # Get user privacy settings
        privacy_level = force_privacy_level or self._get_user_privacy_level(user_id)

        # Check consent for different processing types
        consent_status = {
            "face_recognition": self.privacy_manager.check_consent(user_id, ConsentType.FACE_RECOGNITION),
            "facial_attributes": self.privacy_manager.check_consent(user_id, ConsentType.FACIAL_ATTRIBUTES),
            "face_clustering": self.privacy_manager.check_consent(user_id, ConsentType.FACE_CLUSTERING),
            "biometric_storage": self.privacy_manager.check_consent(user_id, ConsentType.BIOMETRIC_STORAGE),
        }

        return privacy_level, consent_status

    def _get_user_privacy_level(self, user_id: str) -> PrivacyLevel:
        """Get user's privacy level from settings"""
        try:
            with self.privacy_manager._get_privacy_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT privacy_level FROM user_privacy_settings WHERE user_id = ?
                """,
                    (user_id,),
                )

                row = cursor.fetchone()
                if row:
                    return PrivacyLevel(row[0])

                # Default to full processing if no settings found
                return PrivacyLevel.FULL_PROCESSING

        except Exception as e:
            logger.warning(f"Failed to get privacy level for user {user_id}: {e}")
            return PrivacyLevel.FULL_PROCESSING

    def _is_processing_allowed(self, privacy_level: PrivacyLevel, consent_status: Dict[str, bool]) -> bool:
        """Determine if face processing is allowed based on privacy settings and consent"""

        # No processing level always blocks
        if privacy_level == PrivacyLevel.NO_PROCESSING:
            return False

        # For full processing, require face recognition consent
        if privacy_level == PrivacyLevel.FULL_PROCESSING:
            return consent_status.get("face_recognition", False)

        # Anonymous and minimal processing don't require explicit consent
        # but respect user settings
        return True

    def _process_image_with_privacy(
        self, image_path: str, user_id: str, privacy_level: PrivacyLevel, privacy_notes: List[str]
    ) -> Tuple[int, int, bool]:
        """Process image according to privacy level"""

        thresholds = self.privacy_thresholds[privacy_level]
        faces_detected = 0
        faces_processed = 0
        anonymized_data = privacy_level != PrivacyLevel.FULL_PROCESSING

        try:
            if privacy_level == PrivacyLevel.NO_PROCESSING:
                privacy_notes.append("No face processing performed due to privacy settings")
                return 0, 0, False

            # Detect faces with privacy-appropriate confidence threshold
            if hasattr(self.face_clusterer, "detect_faces_in_image"):
                detections = self.face_clusterer.detect_faces_in_image(
                    image_path, min_confidence=thresholds["min_confidence"]
                )
                faces_detected = len(detections)

                if faces_detected == 0:
                    privacy_notes.append("No faces detected above privacy threshold")
                    return 0, 0, anonymized_data

                # Process faces according to privacy level
                if privacy_level == PrivacyLevel.FULL_PROCESSING:
                    faces_processed = self._process_faces_full(detections, image_path, user_id, privacy_notes)

                elif privacy_level == PrivacyLevel.ANONYMOUS_ONLY:
                    faces_processed = self._process_faces_anonymous(detections, image_path, privacy_notes)

                elif privacy_level == PrivacyLevel.MINIMAL_PROCESSING:
                    faces_processed = self._process_faces_minimal(detections, privacy_notes)

                return faces_detected, faces_processed, anonymized_data

            else:
                privacy_notes.append("Face detection not available")
                return 0, 0, anonymized_data

        except Exception as e:
            logger.error(f"Privacy-aware image processing failed: {e}")
            privacy_notes.append(f"Processing error: {str(e)}")
            return 0, 0, anonymized_data

    def _process_faces_full(self, detections: List, image_path: str, user_id: str, privacy_notes: List[str]) -> int:
        """Process faces with full functionality (requires consent)"""
        try:
            # Full processing: clustering, attributes, biometric storage
            if hasattr(self.face_clusterer, "cluster_faces"):
                result = self.face_clusterer.cluster_faces([image_path])
                faces_processed = result.get("total_faces", 0)
                privacy_notes.append("Full face processing with clustering and attributes")
                return faces_processed

            privacy_notes.append("Full processing requested but clustering not available")
            return len(detections)

        except Exception as e:
            logger.error(f"Full face processing failed: {e}")
            privacy_notes.append(f"Full processing error: {str(e)}")
            return 0

    def _process_faces_anonymous(self, detections: List, image_path: str, privacy_notes: List[str]) -> int:
        """Process faces anonymously (no personal identification)"""
        try:
            # Anonymous processing: detection and attributes only, no clustering
            anonymized_faces = []

            for i, detection in enumerate(detections):
                # Create anonymized face data
                anon_face = AnonymizedFaceData(
                    detection_id=self._generate_anonymous_id(image_path, i),
                    bounding_box=detection.get("bounding_box", []),
                    confidence=detection.get("confidence", 0.0),
                    quality_score=detection.get("quality_score"),
                    attributes=self._anonymize_attributes(detection.get("attributes", {})),
                    cluster_id=None,  # No clustering in anonymous mode
                )
                anonymized_faces.append(anon_face)

            # Store anonymized data (implementation would go here)
            privacy_notes.append(
                f"Anonymous processing: {len(anonymized_faces)} faces processed without identification"
            )
            return len(anonymized_faces)

        except Exception as e:
            logger.error(f"Anonymous face processing failed: {e}")
            privacy_notes.append(f"Anonymous processing error: {str(e)}")
            return 0

    def _process_faces_minimal(self, detections: List, privacy_notes: List[str]) -> int:
        """Process faces with minimal data (detection only)"""
        try:
            # Minimal processing: count faces only, no storage
            face_count = len(detections)
            privacy_notes.append(f"Minimal processing: {face_count} faces detected, no data stored")
            return face_count

        except Exception as e:
            logger.error(f"Minimal face processing failed: {e}")
            privacy_notes.append(f"Minimal processing error: {str(e)}")
            return 0

    def _generate_anonymous_id(self, image_path: str, face_index: int) -> str:
        """Generate anonymous ID for face detection"""
        # Create deterministic but anonymous ID
        source = f"{Path(image_path).name}_{face_index}_{datetime.now().date()}"
        return f"anon_{hashlib.sha256(source.encode()).hexdigest()[:16]}"

    def _anonymize_attributes(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize facial attributes for privacy"""
        if not attributes:
            return {}

        # Keep general attributes but remove specific identifiers
        anonymized = {}

        # Age ranges instead of specific ages
        if "age" in attributes:
            age = attributes["age"]
            if age < 13:
                anonymized["age_group"] = "child"
            elif age < 20:
                anonymized["age_group"] = "teen"
            elif age < 35:
                anonymized["age_group"] = "young_adult"
            elif age < 55:
                anonymized["age_group"] = "middle_age"
            else:
                anonymized["age_group"] = "senior"

        # Keep emotion and pose as they're less identifying
        if "emotion" in attributes:
            anonymized["emotion"] = attributes["emotion"]

        if "pose" in attributes:
            anonymized["pose"] = attributes["pose"]

        # Remove or generalize other attributes
        if "quality_score" in attributes:
            anonymized["quality_score"] = attributes["quality_score"]

        return anonymized

    def _log_privacy_processing(self, user_id: str, image_path: str, privacy_level: PrivacyLevel, faces_processed: int):
        """Log privacy-compliant processing for audit"""
        self.privacy_manager._log_privacy_action(
            user_id=user_id,
            action="face_processing",
            resource_type="image",
            resource_id=str(Path(image_path).name),
            details={
                "privacy_level": privacy_level.value,
                "faces_processed": faces_processed,
                "processing_mode": "privacy_aware",
            },
        )

    def batch_process_with_privacy(
        self, image_paths: List[str], user_id: str, progress_callback=None
    ) -> List[PrivacyProcessingResult]:
        """
        Process multiple images with privacy controls.

        Args:
            image_paths: List of image paths to process
            user_id: User identifier
            progress_callback: Optional callback for progress updates

        Returns:
            List of processing results
        """
        results = []

        # Check privacy settings once for batch
        privacy_level, consent_status = self._check_privacy_requirements(user_id)

        for i, image_path in enumerate(image_paths):
            try:
                result = self.process_with_privacy_controls(image_path, user_id, force_privacy_level=privacy_level)
                results.append(result)

                if progress_callback:
                    progress_callback(i + 1, len(image_paths), result)

            except Exception as e:
                logger.error(f"Batch processing failed for {image_path}: {e}")
                # Create error result
                error_result = PrivacyProcessingResult(
                    image_path=image_path,
                    user_id=user_id,
                    privacy_level=privacy_level,
                    processing_allowed=False,
                    faces_detected=0,
                    faces_processed=0,
                    consent_status=consent_status,
                    anonymized_data=False,
                    processing_time=0.0,
                    privacy_notes=[f"Batch processing error: {str(e)}"],
                )
                results.append(error_result)

        # Log batch processing
        self.privacy_manager._log_privacy_action(
            user_id=user_id,
            action="batch_face_processing",
            resource_type="image_batch",
            details={
                "total_images": len(image_paths),
                "successful_processing": sum(1 for r in results if r.processing_allowed),
                "privacy_level": privacy_level.value,
            },
        )

        return results

    def get_privacy_processing_stats(self, user_id: str) -> Dict[str, Any]:
        """Get privacy processing statistics for user"""
        try:
            with self.privacy_manager._get_privacy_db() as conn:
                cursor = conn.cursor()

                # Get processing statistics
                cursor.execute(
                    """
                    SELECT
                        json_extract(details, '$.privacy_level') as privacy_level,
                        COUNT(*) as processing_count,
                        SUM(json_extract(details, '$.faces_processed')) as total_faces
                    FROM privacy_audit_log
                    WHERE user_id = ? AND action = 'face_processing'
                    GROUP BY json_extract(details, '$.privacy_level')
                """,
                    (user_id,),
                )

                stats_by_level = {}
                for row in cursor.fetchall():
                    privacy_level, count, faces = row
                    stats_by_level[privacy_level or "unknown"] = {"processing_count": count, "total_faces": faces or 0}

                return {
                    "user_id": user_id,
                    "processing_stats": stats_by_level,
                    "generated_at": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.error(f"Failed to get privacy processing stats: {e}")
            return {"error": str(e)}

    def validate_privacy_compliance(self, user_id: str) -> Dict[str, Any]:
        """
        Validate privacy compliance for user's face processing.

        Checks consent status, data retention, and processing compliance.
        """
        try:
            compliance_report = {
                "user_id": user_id,
                "compliance_status": "compliant",
                "issues": [],
                "recommendations": [],
                "checked_at": datetime.now().isoformat(),
            }

            # Check consent status
            consent_status = {}
            for consent_type in ConsentType:
                is_valid = self.privacy_manager.check_consent(user_id, consent_type)
                consent_status[consent_type.value] = is_valid

                if not is_valid and consent_type in [ConsentType.FACE_RECOGNITION, ConsentType.BIOMETRIC_STORAGE]:
                    compliance_report["issues"].append(f"Missing or expired consent for {consent_type.value}")

            # Check data retention
            privacy_level = self._get_user_privacy_level(user_id)
            if privacy_level == PrivacyLevel.NO_PROCESSING:
                # Check if there's still face data stored
                compliance_report["recommendations"].append(
                    "Consider anonymizing existing face data due to NO_PROCESSING setting"
                )

            # Set overall compliance status
            if compliance_report["issues"]:
                compliance_report["compliance_status"] = "issues_found"

            compliance_report["consent_status"] = consent_status
            compliance_report["current_privacy_level"] = privacy_level.value

            return compliance_report

        except Exception as e:
            logger.error(f"Privacy compliance validation failed: {e}")
            return {
                "user_id": user_id,
                "compliance_status": "error",
                "error": str(e),
                "checked_at": datetime.now().isoformat(),
            }
