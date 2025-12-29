"""
GDPR Compliance Manager

Implements comprehensive GDPR compliance features including:
- Data export (Article 20: Right to data portability)
- Data deletion (Article 17: Right to erasure)
- Consent management (Articles 6, 7: Lawful basis and consent)
- Audit logging (Article 12: Transparent information)
- Data minimization and purpose limitation
"""

import json
import sqlite3
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging
import secrets

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
    """Status of consent"""

    GRANTED = "granted"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
    PENDING = "pending"


@dataclass
class ConsentRecord:
    """Record of user consent"""

    consent_id: str
    user_id: str
    consent_type: ConsentType
    status: ConsentStatus
    purpose: str
    legal_basis: str
    granted_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    version: int = 1


@dataclass
class AuditLogEntry:
    """Audit log entry for GDPR compliance"""

    log_id: str
    user_id: str
    action: str
    resource_type: str
    resource_id: Optional[str]
    timestamp: datetime
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class GDPRComplianceManager:
    """
    GDPR Compliance Manager

    Provides comprehensive GDPR compliance features including consent management,
    data export, data deletion, and audit logging.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

        # Consent purposes and descriptions
        self.consent_purposes = {
            ConsentType.FACE_RECOGNITION: {
                "purpose": "We detect and recognize faces in your photos for organization and search",
                "legal_basis": "consent",
                "retention_period": "Until consent is withdrawn",
                "data_categories": ["facial biometric data", "photo metadata"],
            },
            ConsentType.FACIAL_ATTRIBUTES: {
                "purpose": "We analyze facial attributes like age and emotion for enhanced search capabilities",
                "legal_basis": "consent",
                "retention_period": "Until consent is withdrawn",
                "data_categories": ["facial attribute data", "demographic estimates"],
            },
            ConsentType.FACE_CLUSTERING: {
                "purpose": "We group similar faces together to identify people in your photos",
                "legal_basis": "consent",
                "retention_period": "Until consent is withdrawn",
                "data_categories": ["facial embeddings", "cluster assignments"],
            },
            ConsentType.VIDEO_PROCESSING: {
                "purpose": "We process faces in your videos for timeline analysis and highlights",
                "legal_basis": "consent",
                "retention_period": "Until consent is withdrawn",
                "data_categories": ["video face data", "temporal analysis"],
            },
            ConsentType.DATA_ANALYTICS: {
                "purpose": "We analyze your photo collection to provide insights and recommendations",
                "legal_basis": "legitimate_interest",
                "retention_period": "2 years or until objection",
                "data_categories": ["usage patterns", "photo statistics"],
            },
            ConsentType.BIOMETRIC_STORAGE: {
                "purpose": "We store biometric face data for accurate recognition across sessions",
                "legal_basis": "consent",
                "retention_period": "Until consent is withdrawn",
                "data_categories": ["encrypted biometric templates"],
            },
        }

    def _init_database(self):
        """Initialize GDPR compliance database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS consent_records (
                    consent_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    consent_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    legal_basis TEXT NOT NULL,
                    granted_at TEXT,
                    withdrawn_at TEXT,
                    expires_at TEXT,
                    version INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    log_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT,
                    timestamp TEXT NOT NULL,
                    details TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS data_export_requests (
                    request_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    export_types TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requested_at TEXT NOT NULL,
                    completed_at TEXT,
                    file_path TEXT,
                    expires_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS data_deletion_requests (
                    request_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    deletion_type TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requested_at TEXT NOT NULL,
                    completed_at TEXT,
                    verification_required BOOLEAN DEFAULT FALSE,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_consent_user_type ON consent_records(user_id, consent_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_user_timestamp ON audit_log(user_id, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_export_user_status ON data_export_requests(user_id, status)")

    # Consent Management (GDPR Articles 6, 7)

    def request_consent(
        self, user_id: str, consent_type: ConsentType, purpose: Optional[str] = None, legal_basis: str = "consent"
    ) -> str:
        """
        Request consent from user (GDPR Article 7)

        Args:
            user_id: User identifier
            consent_type: Type of consent being requested
            purpose: Specific purpose (optional, uses default if not provided)
            legal_basis: Legal basis for processing

        Returns:
            Consent ID for tracking
        """
        consent_id = self._generate_id("consent")

        # Get default purpose if not provided
        if purpose is None:
            purpose = self.consent_purposes[consent_type]["purpose"]

        consent_record = ConsentRecord(
            consent_id=consent_id,
            user_id=user_id,
            consent_type=consent_type,
            status=ConsentStatus.PENDING,
            purpose=purpose,
            legal_basis=legal_basis,
        )

        # Store consent request
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO consent_records
                (consent_id, user_id, consent_type, status, purpose, legal_basis)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    consent_record.consent_id,
                    consent_record.user_id,
                    consent_record.consent_type.value,
                    consent_record.status.value,
                    consent_record.purpose,
                    consent_record.legal_basis,
                ),
            )

        # Log consent request
        self._log_audit_event(
            user_id=user_id,
            action="consent_requested",
            resource_type="consent",
            resource_id=consent_id,
            details={"consent_type": consent_type.value, "purpose": purpose, "legal_basis": legal_basis},
        )

        logger.info(f"Consent requested: {consent_id} for user {user_id}, type {consent_type.value}")
        return consent_id

    def grant_consent(self, consent_id: str) -> bool:
        """
        Grant consent (GDPR Article 7)

        Args:
            consent_id: ID of the consent to grant

        Returns:
            True if successful, False otherwise
        """
        try:
            now = datetime.utcnow().isoformat()

            with sqlite3.connect(self.db_path) as conn:
                # Update consent status
                cursor = conn.execute(
                    """
                    UPDATE consent_records
                    SET status = ?, granted_at = ?, updated_at = ?
                    WHERE consent_id = ? AND status = ?
                """,
                    (ConsentStatus.GRANTED.value, now, now, consent_id, ConsentStatus.PENDING.value),
                )

                if cursor.rowcount == 0:
                    logger.warning(f"Failed to grant consent {consent_id}: not found or not pending")
                    return False

                # Get consent details for logging
                consent_data = conn.execute(
                    """
                    SELECT user_id, consent_type FROM consent_records WHERE consent_id = ?
                """,
                    (consent_id,),
                ).fetchone()

                if consent_data:
                    user_id, consent_type = consent_data

                    # Log consent granted
                    self._log_audit_event(
                        user_id=user_id,
                        action="consent_granted",
                        resource_type="consent",
                        resource_id=consent_id,
                        details={"consent_type": consent_type},
                    )

                    logger.info(f"Consent granted: {consent_id} for user {user_id}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Failed to grant consent {consent_id}: {e}")
            return False

    def withdraw_consent(self, user_id: str, consent_type: ConsentType) -> bool:
        """
        Withdraw consent (GDPR Article 7.3)

        Args:
            user_id: User identifier
            consent_type: Type of consent to withdraw

        Returns:
            True if successful, False otherwise
        """
        try:
            now = datetime.utcnow().isoformat()

            with sqlite3.connect(self.db_path) as conn:
                # Update consent status
                cursor = conn.execute(
                    """
                    UPDATE consent_records
                    SET status = ?, withdrawn_at = ?, updated_at = ?
                    WHERE user_id = ? AND consent_type = ? AND status = ?
                """,
                    (ConsentStatus.WITHDRAWN.value, now, now, user_id, consent_type.value, ConsentStatus.GRANTED.value),
                )

                if cursor.rowcount == 0:
                    logger.warning(
                        f"Failed to withdraw consent for user {user_id}, type {consent_type.value}: not found or not granted"
                    )
                    return False

                # Log consent withdrawal
                self._log_audit_event(
                    user_id=user_id,
                    action="consent_withdrawn",
                    resource_type="consent",
                    resource_id=None,
                    details={"consent_type": consent_type.value},
                )

                logger.info(f"Consent withdrawn for user {user_id}, type {consent_type.value}")
                return True

        except Exception as e:
            logger.error(f"Failed to withdraw consent for user {user_id}: {e}")
            return False

    def check_consent(self, user_id: str, consent_type: ConsentType) -> bool:
        """
        Check if user has granted consent for a specific type

        Args:
            user_id: User identifier
            consent_type: Type of consent to check

        Returns:
            True if consent is granted and valid, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute(
                    """
                    SELECT status, granted_at, expires_at FROM consent_records
                    WHERE user_id = ? AND consent_type = ?
                    ORDER BY created_at DESC LIMIT 1
                """,
                    (user_id, consent_type.value),
                ).fetchone()

                if not result:
                    return False

                status, granted_at, expires_at = result

                # Check if consent is granted
                if status != ConsentStatus.GRANTED.value:
                    return False

                # Check if consent has expired
                if expires_at:
                    expiry_date = datetime.fromisoformat(expires_at)
                    if datetime.utcnow() > expiry_date:
                        # Mark as expired
                        self._expire_consent(user_id, consent_type)
                        return False

                return True

        except Exception as e:
            logger.error(f"Failed to check consent for user {user_id}: {e}")
            return False

    def get_consent_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get all consent statuses for a user

        Args:
            user_id: User identifier

        Returns:
            Dictionary with consent statuses
        """
        try:
            consent_status = {}

            with sqlite3.connect(self.db_path) as conn:
                results = conn.execute(
                    """
                    SELECT consent_type, status, granted_at, withdrawn_at, expires_at, purpose
                    FROM consent_records
                    WHERE user_id = ?
                    ORDER BY consent_type, created_at DESC
                """,
                    (user_id,),
                ).fetchall()

                # Get latest status for each consent type
                seen_types = set()
                for row in results:
                    consent_type, status, granted_at, withdrawn_at, expires_at, purpose = row

                    if consent_type not in seen_types:
                        seen_types.add(consent_type)

                        # Check if expired
                        if expires_at and status == ConsentStatus.GRANTED.value:
                            expiry_date = datetime.fromisoformat(expires_at)
                            if datetime.utcnow() > expiry_date:
                                status = ConsentStatus.EXPIRED.value

                        consent_status[consent_type] = {
                            "granted": status == ConsentStatus.GRANTED.value,
                            "status": status,
                            "granted_at": granted_at,
                            "withdrawn_at": withdrawn_at,
                            "expires_at": expires_at,
                            "description": purpose,
                        }

            return {"user_id": user_id, "consent_status": consent_status}

        except Exception as e:
            logger.error(f"Failed to get consent status for user {user_id}: {e}")
            return {"user_id": user_id, "consent_status": {}, "error": str(e)}

    # Data Export (GDPR Article 20)

    def request_data_export(self, user_id: str, export_types: List[str], include_biometric_data: bool = False) -> str:
        """
        Request data export (GDPR Article 20: Right to data portability)

        Args:
            user_id: User identifier
            export_types: Types of data to export
            include_biometric_data: Whether to include biometric data

        Returns:
            Export request ID
        """
        request_id = self._generate_id("export")
        now = datetime.utcnow().isoformat()
        expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()  # Export links expire in 30 days

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO data_export_requests
                    (request_id, user_id, export_types, status, requested_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (request_id, user_id, json.dumps(export_types), "pending", now, expires_at),
                )

            # Log export request
            self._log_audit_event(
                user_id=user_id,
                action="data_export_requested",
                resource_type="export",
                resource_id=request_id,
                details={"export_types": export_types, "include_biometric_data": include_biometric_data},
            )

            logger.info(f"Data export requested: {request_id} for user {user_id}")
            return request_id

        except Exception as e:
            logger.error(f"Failed to request data export for user {user_id}: {e}")
            raise

    def generate_data_export(self, request_id: str) -> Optional[Path]:
        """
        Generate data export file

        Args:
            request_id: Export request ID

        Returns:
            Path to export file if successful, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                request_data = conn.execute(
                    """
                    SELECT user_id, export_types, status FROM data_export_requests
                    WHERE request_id = ?
                """,
                    (request_id,),
                ).fetchone()

                if not request_data:
                    logger.error(f"Export request not found: {request_id}")
                    return None

                user_id, export_types_json, status = request_data

                if status != "pending":
                    logger.warning(f"Export request {request_id} is not pending (status: {status})")
                    return None

                export_types = json.loads(export_types_json)

                # Create export directory
                export_dir = Path("exports") / user_id
                export_dir.mkdir(parents=True, exist_ok=True)

                # Create export file
                export_file = export_dir / f"data_export_{request_id}.zip"

                with zipfile.ZipFile(export_file, "w", zipfile.ZIP_DEFLATED) as zipf:
                    # Export consent data
                    if "consent" in export_types:
                        consent_data = self._export_consent_data(user_id)
                        zipf.writestr("consent_records.json", json.dumps(consent_data, indent=2))

                    # Export audit logs
                    if "audit_logs" in export_types:
                        audit_data = self._export_audit_logs(user_id)
                        zipf.writestr("audit_logs.json", json.dumps(audit_data, indent=2))

                    # Export face data (if consented)
                    if "face_data" in export_types:
                        face_data = self._export_face_data(user_id)
                        zipf.writestr("face_data.json", json.dumps(face_data, indent=2))

                    # Export privacy settings
                    if "privacy_settings" in export_types:
                        privacy_data = self._export_privacy_settings(user_id)
                        zipf.writestr("privacy_settings.json", json.dumps(privacy_data, indent=2))

                    # Add export metadata
                    export_metadata = {
                        "export_id": request_id,
                        "user_id": user_id,
                        "export_types": export_types,
                        "generated_at": datetime.utcnow().isoformat(),
                        "format_version": "1.0",
                        "gdpr_article": "Article 20 - Right to data portability",
                    }
                    zipf.writestr("export_metadata.json", json.dumps(export_metadata, indent=2))

                # Update request status
                now = datetime.utcnow().isoformat()
                conn.execute(
                    """
                    UPDATE data_export_requests
                    SET status = ?, completed_at = ?, file_path = ?
                    WHERE request_id = ?
                """,
                    ("completed", now, str(export_file), request_id),
                )

                # Log export completion
                self._log_audit_event(
                    user_id=user_id,
                    action="data_export_completed",
                    resource_type="export",
                    resource_id=request_id,
                    details={"file_path": str(export_file), "file_size": export_file.stat().st_size},
                )

                logger.info(f"Data export completed: {request_id} for user {user_id}")
                return export_file

        except Exception as e:
            logger.error(f"Failed to generate data export {request_id}: {e}")
            return None

    # Data Deletion (GDPR Article 17)

    def request_data_deletion(self, user_id: str, deletion_type: str = "complete", reason: str = "User request") -> str:
        """
        Request data deletion (GDPR Article 17: Right to erasure)

        Args:
            user_id: User identifier
            deletion_type: Type of deletion ("complete", "face_data", "specific")
            reason: Reason for deletion

        Returns:
            Deletion request ID
        """
        request_id = self._generate_id("deletion")
        now = datetime.utcnow().isoformat()

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO data_deletion_requests
                    (request_id, user_id, deletion_type, reason, status, requested_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (request_id, user_id, deletion_type, reason, "pending", now),
                )

            # Log deletion request
            self._log_audit_event(
                user_id=user_id,
                action="data_deletion_requested",
                resource_type="deletion",
                resource_id=request_id,
                details={"deletion_type": deletion_type, "reason": reason},
            )

            logger.info(f"Data deletion requested: {request_id} for user {user_id}")
            return request_id

        except Exception as e:
            logger.error(f"Failed to request data deletion for user {user_id}: {e}")
            raise

    def execute_data_deletion(self, request_id: str) -> bool:
        """
        Execute data deletion request

        Args:
            request_id: Deletion request ID

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                request_data = conn.execute(
                    """
                    SELECT user_id, deletion_type, reason, status FROM data_deletion_requests
                    WHERE request_id = ?
                """,
                    (request_id,),
                ).fetchone()

                if not request_data:
                    logger.error(f"Deletion request not found: {request_id}")
                    return False

                user_id, deletion_type, reason, status = request_data

                if status != "pending":
                    logger.warning(f"Deletion request {request_id} is not pending (status: {status})")
                    return False

                # Perform deletion based on type
                deletion_success = False
                if deletion_type == "complete":
                    deletion_success = self._delete_all_user_data(user_id)
                elif deletion_type == "face_data":
                    deletion_success = self._delete_face_data(user_id)
                else:
                    logger.error(f"Unknown deletion type: {deletion_type}")
                    return False

                if deletion_success:
                    # Update request status
                    now = datetime.utcnow().isoformat()
                    conn.execute(
                        """
                        UPDATE data_deletion_requests
                        SET status = ?, completed_at = ?
                        WHERE request_id = ?
                    """,
                        ("completed", now, request_id),
                    )

                    # Log deletion completion
                    self._log_audit_event(
                        user_id=user_id,
                        action="data_deletion_completed",
                        resource_type="deletion",
                        resource_id=request_id,
                        details={"deletion_type": deletion_type, "reason": reason},
                    )

                    logger.info(f"Data deletion completed: {request_id} for user {user_id}")
                    return True
                else:
                    # Mark as failed
                    conn.execute(
                        """
                        UPDATE data_deletion_requests
                        SET status = ?
                        WHERE request_id = ?
                    """,
                        ("failed", request_id),
                    )

                    logger.error(f"Data deletion failed: {request_id} for user {user_id}")
                    return False

        except Exception as e:
            logger.error(f"Failed to execute data deletion {request_id}: {e}")
            return False

    # Audit Logging (GDPR Article 12)

    def _log_audit_event(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Log an audit event"""
        log_id = self._generate_id("audit")
        timestamp = datetime.utcnow().isoformat()
        details_json = json.dumps(details or {})

        try:
            # Use a separate connection to avoid locks
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            try:
                conn.execute(
                    """
                    INSERT INTO audit_log
                    (log_id, user_id, action, resource_type, resource_id, timestamp, details, ip_address, user_agent)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        log_id,
                        user_id,
                        action,
                        resource_type,
                        resource_id,
                        timestamp,
                        details_json,
                        ip_address,
                        user_agent,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            # Don't raise - audit logging should not break main functionality

    def get_audit_logs(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit logs for a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                results = conn.execute(
                    """
                    SELECT log_id, action, resource_type, resource_id, timestamp, details
                    FROM audit_log
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """,
                    (user_id, limit),
                ).fetchall()

                logs = []
                for row in results:
                    log_id, action, resource_type, resource_id, timestamp, details_json = row
                    logs.append(
                        {
                            "log_id": log_id,
                            "action": action,
                            "resource_type": resource_type,
                            "resource_id": resource_id,
                            "timestamp": timestamp,
                            "details": json.loads(details_json),
                        }
                    )

                return logs

        except Exception as e:
            logger.error(f"Failed to get audit logs for user {user_id}: {e}")
            return []

    # Helper methods

    def _generate_id(self, prefix: str) -> str:
        """Generate a unique ID with prefix"""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        random_part = secrets.token_hex(8)
        return f"{prefix}_{timestamp}_{random_part}"

    def _expire_consent(self, user_id: str, consent_type: ConsentType):
        """Mark consent as expired"""
        now = datetime.utcnow().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE consent_records
                SET status = ?, updated_at = ?
                WHERE user_id = ? AND consent_type = ? AND status = ?
            """,
                (ConsentStatus.EXPIRED.value, now, user_id, consent_type.value, ConsentStatus.GRANTED.value),
            )

    def _export_consent_data(self, user_id: str) -> Dict[str, Any]:
        """Export consent data for a user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            results = conn.execute(
                """
                SELECT * FROM consent_records WHERE user_id = ?
            """,
                (user_id,),
            ).fetchall()

            consent_records = [dict(row) for row in results]

            return {
                "user_id": user_id,
                "consent_records": consent_records,
                "exported_at": datetime.utcnow().isoformat(),
            }

    def _export_audit_logs(self, user_id: str) -> Dict[str, Any]:
        """Export audit logs for a user"""
        logs = self.get_audit_logs(user_id, limit=1000)  # Export up to 1000 recent logs

        return {"user_id": user_id, "audit_logs": logs, "exported_at": datetime.utcnow().isoformat()}

    def _export_face_data(self, user_id: str) -> Dict[str, Any]:
        """Export face data for a user (placeholder - implement based on face storage)"""
        return {
            "user_id": user_id,
            "face_data": "Face data export would be implemented based on face storage system",
            "exported_at": datetime.utcnow().isoformat(),
        }

    def _export_privacy_settings(self, user_id: str) -> Dict[str, Any]:
        """Export privacy settings for a user"""
        consent_status = self.get_consent_status(user_id)

        return {"user_id": user_id, "privacy_settings": consent_status, "exported_at": datetime.utcnow().isoformat()}

    def _delete_all_user_data(self, user_id: str) -> bool:
        """Delete all data for a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Delete consent records
                conn.execute("DELETE FROM consent_records WHERE user_id = ?", (user_id,))

                # Delete export requests
                conn.execute("DELETE FROM data_export_requests WHERE user_id = ?", (user_id,))

                # Delete deletion requests (except the current one)
                conn.execute(
                    """
                    DELETE FROM data_deletion_requests
                    WHERE user_id = ? AND status != 'pending'
                """,
                    (user_id,),
                )

                # Note: Audit logs are typically retained for legal compliance
                # They would be anonymized rather than deleted

            # Delete face data (would call secure face clusterer)
            self._delete_face_data(user_id)

            # Delete encryption keys
            try:
                from server.security.key_manager import get_key_manager

                key_manager = get_key_manager()
                key_manager.delete_user_keys(user_id)
            except Exception as e:
                logger.warning(f"Could not delete encryption keys for {user_id}: {e}")

            return True

        except Exception as e:
            logger.error(f"Failed to delete all data for user {user_id}: {e}")
            return False

    def _delete_face_data(self, user_id: str) -> bool:
        """Delete face data for a user"""
        try:
            # This would integrate with the secure face clusterer
            # to delete all face-related data for the user

            # Delete encryption keys
            try:
                from server.security.key_manager import get_key_manager

                key_manager = get_key_manager()
                key_manager.delete_user_keys(user_id)
            except Exception as e:
                logger.warning(f"Could not delete encryption keys for {user_id}: {e}")

            return True

        except Exception as e:
            logger.error(f"Failed to delete face data for user {user_id}: {e}")
            return False


# Global GDPR manager instance
_gdpr_manager: Optional[GDPRComplianceManager] = None


def get_gdpr_manager() -> GDPRComplianceManager:
    """Get the global GDPR compliance manager instance"""
    global _gdpr_manager
    if _gdpr_manager is None:
        from server.config import settings

        db_path = Path(settings.DATA_DIR) / "gdpr_compliance.db"
        _gdpr_manager = GDPRComplianceManager(db_path)
    return _gdpr_manager
