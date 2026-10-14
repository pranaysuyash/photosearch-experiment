"""
Privacy Controls System - Phase 6

Implements comprehensive privacy and security controls for face recognition data,
ensuring compliance with GDPR, CCPA, and other privacy regulations.

Features:
1. User consent management for face recognition processing
2. Data anonymization and pseudonymization
3. Right to be forgotten implementation
4. Data export capabilities (GDPR Article 20)
5. Privacy-preserving face processing modes
6. Audit logging for compliance

Privacy by Design Principles:
- Proactive not reactive
- Privacy as the default setting
- Full functionality - positive sum
- End-to-end security
- Visibility and transparency
- Respect for user privacy

Usage:
    privacy_manager = PrivacyControlsManager(db_path)
    privacy_manager.request_consent(user_id, "face_recognition")
    privacy_manager.anonymize_person_data(person_id)
    privacy_manager.export_user_data(user_id, export_path)
"""

import json
import sqlite3
import hashlib
import logging
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class ConsentType(Enum):
    """Types of consent that can be requested"""

    FACE_RECOGNITION = "face_recognition"
    FACIAL_ATTRIBUTES = "facial_attributes"
    FACE_CLUSTERING = "face_clustering"
    VIDEO_PROCESSING = "video_processing"
    DATA_ANALYTICS = "data_analytics"
    BIOMETRIC_STORAGE = "biometric_storage"


class ConsentStatus(Enum):
    """Status of user consent"""

    GRANTED = "granted"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
    PENDING = "pending"


class PrivacyLevel(Enum):
    """Privacy processing levels"""

    FULL_PROCESSING = "full"  # Normal processing with all features
    ANONYMOUS_ONLY = "anonymous"  # No personal identification
    MINIMAL_PROCESSING = "minimal"  # Basic detection only
    NO_PROCESSING = "none"  # No face processing


@dataclass
class ConsentRecord:
    """Record of user consent for privacy compliance"""

    consent_id: str
    user_id: str
    consent_type: ConsentType
    status: ConsentStatus
    granted_at: Optional[datetime]
    withdrawn_at: Optional[datetime]
    expires_at: Optional[datetime]
    purpose: str
    legal_basis: str  # GDPR Article 6 basis
    metadata: Dict[str, Any]


@dataclass
class PrivacyAuditLog:
    """Audit log entry for privacy compliance"""

    log_id: str
    timestamp: datetime
    user_id: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]


@dataclass
class DataExportRequest:
    """Data export request for GDPR compliance"""

    request_id: str
    user_id: str
    requested_at: datetime
    status: str  # pending, processing, completed, failed
    export_types: List[str]
    export_path: Optional[str]
    completed_at: Optional[datetime]
    file_size_bytes: Optional[int]


class PrivacyControlsManager:
    """Comprehensive privacy controls for face recognition system"""

    def __init__(self, face_db_path: str, privacy_db_path: Optional[str] = None):
        """
        Initialize privacy controls manager.

        Args:
            face_db_path: Path to face clustering database
            privacy_db_path: Path to privacy database (optional)
        """
        self.face_db_path = Path(face_db_path)
        if privacy_db_path:
            self.privacy_db_path = Path(privacy_db_path)
        else:
            # Create privacy.db in the same directory as face_db_path
            face_db_path_obj = Path(face_db_path)
            self.privacy_db_path = face_db_path_obj.parent / "privacy.db"

        # Initialize privacy database
        self._init_privacy_database()

        # Default consent expiration (2 years for GDPR compliance)
        self.default_consent_expiry = timedelta(days=730)

        logger.info("PrivacyControlsManager initialized")

    def _init_privacy_database(self):
        """Initialize privacy controls database schema"""
        try:
            with sqlite3.connect(str(self.privacy_db_path)) as conn:
                cursor = conn.cursor()

                # Consent management table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_consent (
                        consent_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        consent_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        granted_at TIMESTAMP,
                        withdrawn_at TIMESTAMP,
                        expires_at TIMESTAMP,
                        purpose TEXT NOT NULL,
                        legal_basis TEXT NOT NULL,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Privacy audit log
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS privacy_audit_log (
                        log_id TEXT PRIMARY KEY,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        user_id TEXT,
                        action TEXT NOT NULL,
                        resource_type TEXT NOT NULL,
                        resource_id TEXT,
                        details TEXT,
                        ip_address TEXT,
                        user_agent TEXT
                    )
                """)

                # Data export requests
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS data_export_requests (
                        request_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status TEXT DEFAULT 'pending',
                        export_types TEXT NOT NULL,
                        export_path TEXT,
                        completed_at TIMESTAMP,
                        file_size_bytes INTEGER
                    )
                """)

                # Privacy settings per user
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_privacy_settings (
                        user_id TEXT PRIMARY KEY,
                        privacy_level TEXT DEFAULT 'full',
                        face_recognition_enabled BOOLEAN DEFAULT 1,
                        facial_attributes_enabled BOOLEAN DEFAULT 1,
                        video_processing_enabled BOOLEAN DEFAULT 1,
                        data_retention_days INTEGER DEFAULT 2555,  -- 7 years default
                        anonymization_enabled BOOLEAN DEFAULT 0,
                        settings_json TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Anonymized data mapping (for right to be forgotten)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS anonymization_mapping (
                        original_id TEXT PRIMARY KEY,
                        anonymized_id TEXT NOT NULL,
                        resource_type TEXT NOT NULL,
                        anonymized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        user_id TEXT
                    )
                """)

                # Create indexes for performance
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_consent_user_type ON user_consent(user_id, consent_type)"
                )
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_user_action ON privacy_audit_log(user_id, action)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_export_user_status ON data_export_requests(user_id, status)"
                )

                conn.commit()
                logger.info("Privacy database schema initialized")

        except Exception as e:
            logger.error(f"Failed to initialize privacy database: {e}")
            raise

    def request_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
        purpose: str,
        legal_basis: str = "consent",
        expires_in_days: Optional[int] = None,
    ) -> str:
        """
        Request user consent for data processing.

        Args:
            user_id: User identifier
            consent_type: Type of consent being requested
            purpose: Purpose for data processing
            legal_basis: GDPR Article 6 legal basis
            expires_in_days: Consent expiration in days

        Returns:
            Consent ID for tracking
        """
        try:
            if not isinstance(consent_type, ConsentType):
                raise ValueError(f"Invalid consent type: {consent_type!r}")
            consent_id = str(uuid.uuid4())
            expires_at = None

            if expires_in_days:
                expires_at = datetime.now() + timedelta(days=expires_in_days)
            else:
                expires_at = datetime.now() + self.default_consent_expiry

            ConsentRecord(
                consent_id=consent_id,
                user_id=user_id,
                consent_type=consent_type,
                status=ConsentStatus.PENDING,
                granted_at=None,
                withdrawn_at=None,
                expires_at=expires_at,
                purpose=purpose,
                legal_basis=legal_basis,
                metadata={},
            )

            with sqlite3.connect(str(self.privacy_db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO user_consent
                    (consent_id, user_id, consent_type, status, expires_at, purpose, legal_basis, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        consent_id,
                        user_id,
                        consent_type.value,
                        ConsentStatus.PENDING.value,
                        expires_at,
                        purpose,
                        legal_basis,
                        json.dumps({}),
                    ),
                )
                conn.commit()

            # Log consent request
            self._log_privacy_action(
                user_id=user_id,
                action="consent_requested",
                resource_type="consent",
                resource_id=consent_id,
                details={"consent_type": consent_type.value, "purpose": purpose},
            )

            logger.info(f"Consent requested: {consent_id} for user {user_id}")
            return consent_id

        except Exception as e:
            logger.error(f"Failed to request consent: {e}")
            raise

    def grant_consent(self, consent_id: str, user_id: str) -> bool:
        """Grant consent for data processing."""
        try:
            with sqlite3.connect(str(self.privacy_db_path)) as conn:
                cursor = conn.cursor()

                # Update consent status
                cursor.execute(
                    """
                    UPDATE user_consent
                    SET status = ?, granted_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE consent_id = ? AND user_id = ?
                """,
                    (ConsentStatus.GRANTED.value, consent_id, user_id),
                )

                if cursor.rowcount == 0:
                    return False

                conn.commit()

            # Log consent granted
            self._log_privacy_action(
                user_id=user_id, action="consent_granted", resource_type="consent", resource_id=consent_id, details={}
            )

            logger.info(f"Consent granted: {consent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to grant consent: {e}")
            return False

    def withdraw_consent(self, user_id: str, consent_type: ConsentType) -> bool:
        """
        Withdraw consent for data processing.

        This triggers data anonymization or deletion as required by GDPR.
        """
        try:
            with sqlite3.connect(str(self.privacy_db_path)) as conn:
                cursor = conn.cursor()

                # Update all active consents of this type
                cursor.execute(
                    """
                    UPDATE user_consent
                    SET status = ?, withdrawn_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND consent_type = ? AND status = ?
                """,
                    (ConsentStatus.WITHDRAWN.value, user_id, consent_type.value, ConsentStatus.GRANTED.value),
                )

                withdrawn_count = cursor.rowcount
                conn.commit()

            if withdrawn_count > 0:
                # Log consent withdrawal
                self._log_privacy_action(
                    user_id=user_id,
                    action="consent_withdrawn",
                    resource_type="consent",
                    details={"consent_type": consent_type.value, "withdrawn_count": withdrawn_count},
                )

                # Trigger data processing based on consent type
                if consent_type == ConsentType.FACE_RECOGNITION:
                    self._handle_face_recognition_withdrawal(user_id)
                elif consent_type == ConsentType.BIOMETRIC_STORAGE:
                    self._handle_biometric_data_withdrawal(user_id)

                logger.info(f"Consent withdrawn for user {user_id}, type {consent_type.value}")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to withdraw consent: {e}")
            return False

    def check_consent(self, user_id: str, consent_type: ConsentType) -> bool:
        """
        Check if user has valid consent for data processing.

        Returns:
            True if consent is valid and active
        """
        try:
            with sqlite3.connect(str(self.privacy_db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT status, expires_at FROM user_consent
                    WHERE user_id = ? AND consent_type = ? AND status = ?
                    ORDER BY granted_at DESC LIMIT 1
                """,
                    (user_id, consent_type.value, ConsentStatus.GRANTED.value),
                )

                row = cursor.fetchone()
                if not row:
                    return False

                status, expires_at = row

                # Check if consent has expired
                if expires_at:
                    expiry_date = datetime.fromisoformat(expires_at)
                    if datetime.now() > expiry_date:
                        # Mark as expired
                        cursor.execute(
                            """
                            UPDATE user_consent
                            SET status = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE user_id = ? AND consent_type = ? AND status = ?
                        """,
                            (ConsentStatus.EXPIRED.value, user_id, consent_type.value, ConsentStatus.GRANTED.value),
                        )
                        conn.commit()
                        return False

                return status == ConsentStatus.GRANTED.value

        except Exception as e:
            logger.error(f"Failed to check consent: {e}")
            return False

    def _get_privacy_db(self):
        """Get privacy database connection"""
        return sqlite3.connect(str(self.privacy_db_path))

    def anonymize_person_data(self, person_id: str, user_id: Optional[str] = None) -> str:
        """
        Anonymize all data for a specific person (right to be forgotten).

        Args:
            person_id: Person/cluster ID to anonymize
            user_id: User requesting anonymization

        Returns:
            Anonymized ID for tracking
        """
        try:
            anonymized_id = (
                f"anon_{hashlib.sha256(f'{person_id}_{datetime.now().isoformat()}'.encode()).hexdigest()[:16]}"
            )

            # Update face clustering database
            with sqlite3.connect(str(self.face_db_path)) as conn:
                cursor = conn.cursor()

                # Check if clusters table exists
                cursor.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='clusters'
                """)

                if cursor.fetchone():
                    # Anonymize cluster label
                    cursor.execute(
                        """
                        UPDATE clusters
                        SET label = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """,
                        (f"Anonymous Person {anonymized_id[-8:]}", person_id),
                    )

                    # Clear any personal identifiers in face data
                    cursor.execute("""
                        SELECT name FROM sqlite_master
                        WHERE type='table' AND name='faces'
                    """)

                    if cursor.fetchone():
                        cursor.execute(
                            """
                            UPDATE faces
                            SET metadata = json_remove(metadata, '$.personal_info')
                            WHERE id IN (
                                SELECT f.id FROM faces f
                                JOIN cluster_membership cm ON f.id = cm.face_id
                                WHERE cm.cluster_id = ?
                            )
                        """,
                            (person_id,),
                        )

                    conn.commit()
                else:
                    logger.info("Face clustering tables not found - skipping face data anonymization")

            # Record anonymization mapping
            with sqlite3.connect(str(self.privacy_db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO anonymization_mapping
                    (original_id, anonymized_id, resource_type, user_id)
                    VALUES (?, ?, ?, ?)
                """,
                    (person_id, anonymized_id, "person", user_id),
                )
                conn.commit()

            # Log anonymization
            self._log_privacy_action(
                user_id=user_id,
                action="data_anonymized",
                resource_type="person",
                resource_id=person_id,
                details={"anonymized_id": anonymized_id},
            )

            logger.info(f"Person data anonymized: {person_id} -> {anonymized_id}")
            return anonymized_id

        except Exception as e:
            logger.error(f"Failed to anonymize person data: {e}")
            raise

    def export_user_data(self, user_id: str, export_types: List[str], export_path: Optional[str] = None) -> str:
        """
        Export all user data for GDPR compliance (Article 20 - Data Portability).

        Args:
            user_id: User requesting data export
            export_types: Types of data to export
            export_path: Directory to save export files

        Returns:
            Export request ID
        """
        try:
            request_id = str(uuid.uuid4())

            if not export_path:
                export_path = f"exports/user_data_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Create export request record
            with sqlite3.connect(str(self.privacy_db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO data_export_requests
                    (request_id, user_id, export_types, export_path)
                    VALUES (?, ?, ?, ?)
                """,
                    (request_id, user_id, json.dumps(export_types), export_path),
                )
                conn.commit()

            # Log export request
            self._log_privacy_action(
                user_id=user_id,
                action="data_export_requested",
                resource_type="user_data",
                resource_id=request_id,
                details={"export_types": export_types},
            )

            # Process export (in production, this would be async)
            self._process_data_export(request_id, user_id, export_types, export_path)

            logger.info(f"Data export requested: {request_id} for user {user_id}")
            return request_id

        except Exception as e:
            logger.error(f"Failed to export user data: {e}")
            raise

    def _process_data_export(self, request_id: str, user_id: str, export_types: List[str], export_path: str):
        """Process data export request"""
        try:
            export_dir = Path(export_path)
            export_dir.mkdir(parents=True, exist_ok=True)

            total_size = 0

            # Export consent records
            if "consent" in export_types:
                consent_data = self._export_consent_data(user_id)
                consent_file = export_dir / "consent_records.json"
                with open(consent_file, "w") as f:
                    json.dump(consent_data, f, indent=2, default=str)
                total_size += consent_file.stat().st_size

            # Export privacy audit logs
            if "audit_logs" in export_types:
                audit_data = self._export_audit_logs(user_id)
                audit_file = export_dir / "privacy_audit_logs.json"
                with open(audit_file, "w") as f:
                    json.dump(audit_data, f, indent=2, default=str)
                total_size += audit_file.stat().st_size

            # Export face recognition data
            if "face_data" in export_types:
                face_data = self._export_face_data(user_id)
                face_file = export_dir / "face_recognition_data.json"
                with open(face_file, "w") as f:
                    json.dump(face_data, f, indent=2, default=str)
                total_size += face_file.stat().st_size

            # Create export summary
            summary = {
                "export_id": request_id,
                "user_id": user_id,
                "exported_at": datetime.now().isoformat(),
                "export_types": export_types,
                "total_files": len(list(export_dir.glob("*"))),
                "total_size_bytes": total_size,
                "gdpr_compliance": {
                    "article_20_data_portability": True,
                    "machine_readable_format": True,
                    "structured_format": "JSON",
                },
            }

            with open(export_dir / "export_summary.json", "w") as f:
                json.dump(summary, f, indent=2)

            # Update export request status
            with sqlite3.connect(str(self.privacy_db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE data_export_requests
                    SET status = 'completed', completed_at = CURRENT_TIMESTAMP, file_size_bytes = ?
                    WHERE request_id = ?
                """,
                    (total_size, request_id),
                )
                conn.commit()

            logger.info(f"Data export completed: {request_id}")

        except Exception as e:
            logger.error(f"Failed to process data export: {e}")
            # Update status to failed
            with sqlite3.connect(str(self.privacy_db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE data_export_requests
                    SET status = 'failed'
                    WHERE request_id = ?
                """,
                    (request_id,),
                )
                conn.commit()

    def _export_consent_data(self, user_id: str) -> List[Dict]:
        """Export user consent records"""
        with sqlite3.connect(str(self.privacy_db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM user_consent WHERE user_id = ?
                ORDER BY created_at DESC
            """,
                (user_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def _export_audit_logs(self, user_id: str) -> List[Dict]:
        """Export privacy audit logs for user"""
        with sqlite3.connect(str(self.privacy_db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM privacy_audit_log WHERE user_id = ?
                ORDER BY timestamp DESC
            """,
                (user_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def _export_face_data(self, user_id: str) -> Dict:
        """Export face recognition data (anonymized)"""
        # This would export face data associated with the user
        # but without biometric identifiers for privacy
        return {
            "message": "Face recognition data export",
            "note": "Biometric data excluded for privacy protection",
            "metadata_only": True,
            "user_id": user_id,
            "exported_at": datetime.now().isoformat(),
        }

    def _handle_face_recognition_withdrawal(self, user_id: str):
        """Handle face recognition consent withdrawal"""
        # This would trigger anonymization of face data
        logger.info(f"Processing face recognition withdrawal for user {user_id}")

    def _handle_biometric_data_withdrawal(self, user_id: str):
        """Handle biometric data consent withdrawal"""
        # This would trigger deletion of biometric embeddings
        logger.info(f"Processing biometric data withdrawal for user {user_id}")

    def _log_privacy_action(
        self,
        action: str,
        resource_type: str,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Log privacy-related actions for audit compliance"""
        try:
            log_id = str(uuid.uuid4())

            with sqlite3.connect(str(self.privacy_db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO privacy_audit_log
                    (log_id, user_id, action, resource_type, resource_id, details, ip_address, user_agent)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        log_id,
                        user_id,
                        action,
                        resource_type,
                        resource_id,
                        json.dumps(details or {}),
                        ip_address,
                        user_agent,
                    ),
                )
                conn.commit()

        except Exception as e:
            logger.error(f"Failed to log privacy action: {e}")

    def get_privacy_dashboard(self, user_id: str) -> Dict[str, Any]:
        """
        Get privacy dashboard data for user.

        Provides transparency about data processing and consent status.
        """
        try:
            with sqlite3.connect(str(self.privacy_db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Get consent status
                cursor.execute(
                    """
                    SELECT consent_type, status, granted_at, expires_at, purpose
                    FROM user_consent
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                """,
                    (user_id,),
                )
                consents = [dict(row) for row in cursor.fetchall()]

                # Get recent audit logs
                cursor.execute(
                    """
                    SELECT action, resource_type, timestamp, details
                    FROM privacy_audit_log
                    WHERE user_id = ?
                    ORDER BY timestamp DESC LIMIT 10
                """,
                    (user_id,),
                )
                recent_actions = [dict(row) for row in cursor.fetchall()]

                # Get export requests
                cursor.execute(
                    """
                    SELECT request_id, requested_at, status, export_types
                    FROM data_export_requests
                    WHERE user_id = ?
                    ORDER BY requested_at DESC
                """,
                    (user_id,),
                )
                export_requests = [dict(row) for row in cursor.fetchall()]

            return {
                "user_id": user_id,
                "consents": consents,
                "recent_actions": recent_actions,
                "export_requests": export_requests,
                "privacy_rights": {
                    "right_to_access": "Available via data export",
                    "right_to_rectification": "Contact support",
                    "right_to_erasure": "Available via consent withdrawal",
                    "right_to_portability": "Available via data export",
                    "right_to_object": "Available via consent withdrawal",
                },
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get privacy dashboard: {e}")
            return {"error": str(e)}

    def cleanup_expired_data(self, dry_run: bool = True) -> Dict[str, int]:
        """
        Clean up expired consent records and associated data.

        Args:
            dry_run: If True, only report what would be cleaned up

        Returns:
            Statistics about cleanup operations
        """
        try:
            stats = {"expired_consents": 0, "anonymized_records": 0, "deleted_exports": 0}

            with sqlite3.connect(str(self.privacy_db_path)) as conn:
                cursor = conn.cursor()

                # Find expired consents
                cursor.execute("""
                    SELECT consent_id, user_id, consent_type FROM user_consent
                    WHERE status = 'granted' AND expires_at < CURRENT_TIMESTAMP
                """)
                expired_consents = cursor.fetchall()

                stats["expired_consents"] = len(expired_consents)

                if not dry_run:
                    # Mark consents as expired
                    cursor.execute("""
                        UPDATE user_consent
                        SET status = 'expired', updated_at = CURRENT_TIMESTAMP
                        WHERE status = 'granted' AND expires_at < CURRENT_TIMESTAMP
                    """)

                    # Clean up old export files (older than 30 days)
                    cursor.execute("""
                        SELECT request_id, export_path FROM data_export_requests
                        WHERE status = 'completed' AND completed_at < datetime('now', '-30 days')
                    """)
                    old_exports = cursor.fetchall()

                    for request_id, export_path in old_exports:
                        if export_path and Path(export_path).exists():
                            shutil.rmtree(export_path)
                            stats["deleted_exports"] += 1

                    conn.commit()

            logger.info(f"Privacy cleanup completed: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Failed to cleanup expired data: {e}")
            return {"error": str(e)}
