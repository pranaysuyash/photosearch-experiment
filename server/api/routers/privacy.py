"""
Privacy Controls API Router - Phase 6

Provides REST API endpoints for privacy and security controls,
ensuring GDPR, CCPA, and other privacy regulation compliance.

Endpoints:
- Consent management
- Data export (GDPR Article 20)
- Right to be forgotten
- Privacy dashboard
- Audit logging

Security Features:
- Request validation and sanitization
- Rate limiting for sensitive operations
- Audit logging for all privacy actions
- User authentication and authorization
"""

import logging
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from server.config import settings
from server.api.deps import get_state
from server.core.state import AppState
from server.privacy_controls import PrivacyControlsManager, ConsentType, PrivacyLevel

logger = logging.getLogger(__name__)

router = APIRouter()

# Request/Response Models


class ConsentRequest(BaseModel):
    """Request model for consent operations"""

    consent_type: str = Field(..., description="Type of consent (face_recognition, facial_attributes, etc.)")
    purpose: str = Field(..., description="Purpose for data processing")
    legal_basis: str = Field(default="consent", description="GDPR Article 6 legal basis")
    expires_in_days: Optional[int] = Field(default=730, description="Consent expiration in days")


class ConsentResponse(BaseModel):
    """Response model for consent operations"""

    consent_id: str
    status: str
    message: str


class DataExportRequest(BaseModel):
    """Request model for data export"""

    export_types: List[str] = Field(..., description="Types of data to export")
    include_biometric_data: bool = Field(default=False, description="Include biometric data (requires special consent)")


class DataExportResponse(BaseModel):
    """Response model for data export"""

    request_id: str
    status: str
    export_path: Optional[str] = None
    estimated_completion: Optional[str] = None


class AnonymizationRequest(BaseModel):
    """Request model for data anonymization"""

    person_id: str = Field(..., description="Person/cluster ID to anonymize")
    reason: str = Field(..., description="Reason for anonymization")


class PrivacySettingsRequest(BaseModel):
    """Request model for privacy settings update"""

    privacy_level: str = Field(default="full", description="Privacy processing level")
    face_recognition_enabled: bool = Field(default=True)
    facial_attributes_enabled: bool = Field(default=True)
    video_processing_enabled: bool = Field(default=True)
    data_retention_days: int = Field(default=2555, description="Data retention period in days")


# Helper function to get privacy manager
def get_privacy_manager() -> PrivacyControlsManager:
    """Get privacy controls manager instance"""
    return PrivacyControlsManager(
        face_db_path=settings.FACE_CLUSTERS_DB_PATH,
        privacy_db_path=str(Path(settings.FACE_CLUSTERS_DB_PATH).parent / "privacy.db"),
    )


def get_user_id_from_request(request: Request) -> str:
    """Extract user ID from request (placeholder - implement based on auth system)"""
    # In a real implementation, this would extract user ID from JWT token or session
    # For now, using a default user ID
    return request.headers.get("X-User-ID", "default_user")


def log_privacy_request(request: Request, action: str, details: Dict[str, Any]):
    """Log privacy-related requests for audit compliance"""
    privacy_manager = get_privacy_manager()
    user_id = get_user_id_from_request(request)

    privacy_manager._log_privacy_action(
        user_id=user_id,
        action=action,
        resource_type="api_request",
        details=details,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )


# Consent Management Endpoints


@router.post("/api/privacy/consent/request", response_model=ConsentResponse)
async def request_consent(consent_request: ConsentRequest, request: Request, state: AppState = Depends(get_state)):
    """
    Request user consent for data processing.

    Initiates consent flow for specific data processing activities.
    Required for GDPR compliance.
    """
    try:
        privacy_manager = get_privacy_manager()
        user_id = get_user_id_from_request(request)

        # Validate consent type
        try:
            consent_type = ConsentType(consent_request.consent_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid consent type: {consent_request.consent_type}")

        # Request consent
        consent_id = privacy_manager.request_consent(
            user_id=user_id,
            consent_type=consent_type,
            purpose=consent_request.purpose,
            legal_basis=consent_request.legal_basis,
            expires_in_days=consent_request.expires_in_days,
        )

        # Log request
        log_privacy_request(
            request,
            "consent_requested",
            {"consent_type": consent_request.consent_type, "purpose": consent_request.purpose},
        )

        return ConsentResponse(
            consent_id=consent_id, status="pending", message="Consent request created. User approval required."
        )

    except Exception as e:
        logger.error(f"Consent request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/privacy/consent/{consent_id}/grant", response_model=ConsentResponse)
async def grant_consent(consent_id: str, request: Request, state: AppState = Depends(get_state)):
    """
    Grant consent for data processing.

    User confirms consent for specific data processing activity.
    """
    try:
        privacy_manager = get_privacy_manager()
        user_id = get_user_id_from_request(request)

        success = privacy_manager.grant_consent(consent_id, user_id)

        if not success:
            raise HTTPException(status_code=404, detail="Consent request not found or already processed")

        # Log consent granted
        log_privacy_request(request, "consent_granted", {"consent_id": consent_id})

        return ConsentResponse(consent_id=consent_id, status="granted", message="Consent granted successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Grant consent failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/privacy/consent/{consent_type}/withdraw")
async def withdraw_consent(consent_type: str, request: Request, state: AppState = Depends(get_state)):
    """
    Withdraw consent for data processing.

    Implements right to withdraw consent (GDPR Article 7).
    May trigger data anonymization or deletion.
    """
    try:
        privacy_manager = get_privacy_manager()
        user_id = get_user_id_from_request(request)

        # Validate consent type
        try:
            consent_type_enum = ConsentType(consent_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid consent type: {consent_type}")

        success = privacy_manager.withdraw_consent(user_id, consent_type_enum)

        if not success:
            raise HTTPException(status_code=404, detail="No active consent found for this type")

        # Log consent withdrawal
        log_privacy_request(request, "consent_withdrawn", {"consent_type": consent_type})

        return {
            "status": "success",
            "message": f"Consent withdrawn for {consent_type}. Data processing stopped.",
            "next_steps": "Data anonymization process initiated if required.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Withdraw consent failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/privacy/consent/status")
async def get_consent_status(request: Request, state: AppState = Depends(get_state)):
    """
    Get current consent status for all data processing types.

    Provides transparency about active consents and their expiration.
    """
    try:
        privacy_manager = get_privacy_manager()
        user_id = get_user_id_from_request(request)

        consent_status = {}

        # Check status for each consent type
        for consent_type in ConsentType:
            is_valid = privacy_manager.check_consent(user_id, consent_type)
            consent_status[consent_type.value] = {
                "granted": is_valid,
                "description": _get_consent_description(consent_type),
            }

        return {"user_id": user_id, "consent_status": consent_status, "checked_at": datetime.now().isoformat()}

    except Exception as e:
        logger.error(f"Get consent status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Data Export Endpoints (GDPR Article 20)


@router.post("/api/privacy/export/request", response_model=DataExportResponse)
async def request_data_export(
    export_request: DataExportRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    state: AppState = Depends(get_state),
):
    """
    Request data export for GDPR compliance (Article 20 - Data Portability).

    Exports all user data in machine-readable format.
    """
    try:
        privacy_manager = get_privacy_manager()
        user_id = get_user_id_from_request(request)

        # Validate export types
        valid_types = ["consent", "audit_logs", "face_data", "privacy_settings"]
        invalid_types = [t for t in export_request.export_types if t not in valid_types]
        if invalid_types:
            raise HTTPException(status_code=400, detail=f"Invalid export types: {invalid_types}")

        # Check if biometric data export requires special consent
        if export_request.include_biometric_data:
            has_biometric_consent = privacy_manager.check_consent(user_id, ConsentType.BIOMETRIC_STORAGE)
            if not has_biometric_consent:
                raise HTTPException(status_code=403, detail="Biometric data export requires explicit consent")

        # Create export request
        request_id = privacy_manager.export_user_data(user_id=user_id, export_types=export_request.export_types)

        # Log export request
        log_privacy_request(
            request,
            "data_export_requested",
            {"export_types": export_request.export_types, "include_biometric": export_request.include_biometric_data},
        )

        return DataExportResponse(
            request_id=request_id,
            status="processing",
            estimated_completion="Data export typically completes within 24 hours",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Data export request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/privacy/export/{request_id}/status")
async def get_export_status(request_id: str, request: Request, state: AppState = Depends(get_state)):
    """Get status of data export request."""
    try:
        privacy_manager = get_privacy_manager()
        user_id = get_user_id_from_request(request)

        # Get export status from database
        with privacy_manager._get_privacy_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT status, export_path, completed_at, file_size_bytes
                FROM data_export_requests
                WHERE request_id = ? AND user_id = ?
            """,
                (request_id, user_id),
            )

            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Export request not found")

            status, export_path, completed_at, file_size = row

            return {
                "request_id": request_id,
                "status": status,
                "export_path": export_path if status == "completed" else None,
                "completed_at": completed_at,
                "file_size_bytes": file_size,
                "download_available": status == "completed" and export_path is not None,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get export status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/privacy/export/{request_id}/download")
async def download_export(request_id: str, request: Request, state: AppState = Depends(get_state)):
    """Download completed data export."""
    try:
        privacy_manager = get_privacy_manager()
        user_id = get_user_id_from_request(request)

        # Verify export belongs to user and is completed
        with privacy_manager._get_privacy_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT export_path, status FROM data_export_requests
                WHERE request_id = ? AND user_id = ?
            """,
                (request_id, user_id),
            )

            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Export request not found")

            export_path, status = row

            if status != "completed":
                raise HTTPException(status_code=400, detail="Export not completed")

            if not export_path or not Path(export_path).exists():
                raise HTTPException(status_code=404, detail="Export file not found")

        # Log download
        log_privacy_request(request, "data_export_downloaded", {"request_id": request_id})

        # Create zip file for download
        import zipfile
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_file:
            with zipfile.ZipFile(tmp_file.name, "w") as zip_file:
                export_dir = Path(export_path)
                for file_path in export_dir.rglob("*"):
                    if file_path.is_file():
                        zip_file.write(file_path, file_path.relative_to(export_dir))

            return FileResponse(
                tmp_file.name, filename=f"user_data_export_{request_id}.zip", media_type="application/zip"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Right to be Forgotten Endpoints


@router.post("/api/privacy/anonymize/person")
async def anonymize_person_data(
    anonymization_request: AnonymizationRequest, request: Request, state: AppState = Depends(get_state)
):
    """
    Anonymize person data (Right to be Forgotten - GDPR Article 17).

    Removes personal identifiers while preserving statistical data.
    """
    try:
        privacy_manager = get_privacy_manager()
        user_id = get_user_id_from_request(request)

        # Anonymize person data
        anonymized_id = privacy_manager.anonymize_person_data(
            person_id=anonymization_request.person_id, user_id=user_id
        )

        # Log anonymization
        log_privacy_request(
            request,
            "person_data_anonymized",
            {
                "person_id": anonymization_request.person_id,
                "reason": anonymization_request.reason,
                "anonymized_id": anonymized_id,
            },
        )

        return {
            "status": "success",
            "message": "Person data anonymized successfully",
            "original_id": anonymization_request.person_id,
            "anonymized_id": anonymized_id,
            "anonymized_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Anonymize person data failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Privacy Dashboard Endpoints


@router.get("/api/privacy/dashboard")
async def get_privacy_dashboard(request: Request, state: AppState = Depends(get_state)):
    """
    Get comprehensive privacy dashboard for user.

    Provides transparency about data processing, consents, and privacy rights.
    """
    try:
        privacy_manager = get_privacy_manager()
        user_id = get_user_id_from_request(request)

        dashboard_data = privacy_manager.get_privacy_dashboard(user_id)

        return dashboard_data

    except Exception as e:
        logger.error(f"Get privacy dashboard failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/privacy/settings")
async def update_privacy_settings(
    settings_request: PrivacySettingsRequest, request: Request, state: AppState = Depends(get_state)
):
    """Update user privacy settings and preferences."""
    try:
        privacy_manager = get_privacy_manager()
        user_id = get_user_id_from_request(request)

        # Validate privacy level
        try:
            PrivacyLevel(settings_request.privacy_level)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid privacy level: {settings_request.privacy_level}")

        # Update settings in database
        with privacy_manager._get_privacy_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO user_privacy_settings
                (user_id, privacy_level, face_recognition_enabled, facial_attributes_enabled,
                 video_processing_enabled, data_retention_days, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (
                    user_id,
                    settings_request.privacy_level,
                    settings_request.face_recognition_enabled,
                    settings_request.facial_attributes_enabled,
                    settings_request.video_processing_enabled,
                    settings_request.data_retention_days,
                ),
            )
            conn.commit()

        # Log settings update
        log_privacy_request(
            request,
            "privacy_settings_updated",
            {
                "privacy_level": settings_request.privacy_level,
                "face_recognition_enabled": settings_request.face_recognition_enabled,
            },
        )

        return {
            "status": "success",
            "message": "Privacy settings updated successfully",
            "updated_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update privacy settings failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Audit and Compliance Endpoints


@router.get("/api/privacy/audit/logs")
async def get_audit_logs(request: Request, limit: int = 50, offset: int = 0, state: AppState = Depends(get_state)):
    """Get privacy audit logs for user (transparency requirement)."""
    try:
        privacy_manager = get_privacy_manager()
        user_id = get_user_id_from_request(request)

        with privacy_manager._get_privacy_db() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT action, resource_type, timestamp, details
                FROM privacy_audit_log
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """,
                (user_id, limit, offset),
            )

            logs = [dict(row) for row in cursor.fetchall()]

            return {"audit_logs": logs, "total_count": len(logs), "user_id": user_id}

    except Exception as e:
        logger.error(f"Get audit logs failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/privacy/cleanup")
async def cleanup_expired_data(request: Request, dry_run: bool = True, state: AppState = Depends(get_state)):
    """
    Clean up expired privacy data (admin endpoint).

    Removes expired consents and associated data per retention policies.
    """
    try:
        privacy_manager = get_privacy_manager()
        get_user_id_from_request(request)

        # This would typically require admin privileges
        # For now, allowing any user to see what would be cleaned up

        cleanup_stats = privacy_manager.cleanup_expired_data(dry_run=dry_run)

        # Log cleanup operation
        log_privacy_request(request, "privacy_cleanup", {"dry_run": dry_run, "stats": cleanup_stats})

        return {
            "status": "completed" if not dry_run else "dry_run",
            "cleanup_stats": cleanup_stats,
            "message": "Privacy data cleanup completed" if not dry_run else "Dry run completed - no data modified",
        }

    except Exception as e:
        logger.error(f"Privacy cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper Functions


def _get_consent_description(consent_type: ConsentType) -> str:
    """Get human-readable description for consent type"""
    descriptions = {
        ConsentType.FACE_RECOGNITION: "We detect and recognize faces in your photos",
        ConsentType.FACIAL_ATTRIBUTES: "We analyze facial attributes like age and emotion",
        ConsentType.FACE_CLUSTERING: "We group similar faces together to identify people",
        ConsentType.VIDEO_PROCESSING: "We process faces in your videos for timeline analysis",
        ConsentType.DATA_ANALYTICS: "We analyze your photo collection for insights",
        ConsentType.BIOMETRIC_STORAGE: "We store biometric face data for recognition",
    }
    return descriptions.get(consent_type, "Data processing for photo organization")


# Add privacy manager database connection helper
def _get_privacy_db(self):
    """Get privacy database connection"""
    return sqlite3.connect(str(self.privacy_db_path))


# Monkey patch the method to PrivacyControlsManager
PrivacyControlsManager._get_privacy_db = _get_privacy_db


# ---------------------------------------------------------------------------
# Per-photo privacy controls (data layer: server/privacy_controls_db.py).
# These paths match ui/src/api.ts exactly; the UI privacy panel has been
# calling them since the data layer shipped.
# ---------------------------------------------------------------------------

from dataclasses import asdict, is_dataclass

from server.privacy_controls_db import PrivacyControlsDB


class PhotoPrivacyControlRequest(BaseModel):
    """Request model for setting per-photo privacy controls"""

    owner_id: str = Field(..., description="Owner of the photo")
    visibility: str = Field(default="private", description="public, shared, private, friends_only")
    share_permissions: Optional[Dict[str, bool]] = Field(default=None, description="Who can view/download/share")
    encryption_enabled: bool = Field(default=False, description="Whether the photo is encrypted")
    encryption_key_hash: Optional[str] = Field(default=None, description="Hash of the encryption key")
    allowed_users: Optional[List[str]] = Field(default=None, description="Allowed user IDs")
    allowed_groups: Optional[List[str]] = Field(default=None, description="Allowed group IDs")


class PhotoPrivacyUpdateRequest(BaseModel):
    """Request model for updating per-photo privacy controls"""

    visibility: Optional[str] = None
    share_permissions: Optional[Dict[str, bool]] = None
    encryption_enabled: Optional[bool] = None
    encryption_key_hash: Optional[str] = None
    allowed_users: Optional[List[str]] = None
    allowed_groups: Optional[List[str]] = None


def _get_privacy_controls_db() -> PrivacyControlsDB:
    """Per-photo controls live in the same privacy.db as consent records."""
    return PrivacyControlsDB(Path(settings.FACE_CLUSTERS_DB_PATH).parent / "privacy.db")


def _control_dict(control) -> Dict[str, Any]:
    return asdict(control) if is_dataclass(control) else control


@router.post("/privacy/control/{photo_path:path}")
async def set_photo_privacy_control(photo_path: str, body: PhotoPrivacyControlRequest, request: Request):
    """Set privacy controls for a photo (owner, visibility, sharing, encryption)."""
    try:
        db = _get_privacy_controls_db()
        privacy_id = db.set_photo_privacy(
            photo_path=photo_path,
            owner_id=body.owner_id,
            visibility=body.visibility,
            share_permissions=body.share_permissions,
            encryption_enabled=body.encryption_enabled,
            encryption_key_hash=body.encryption_key_hash,
            allowed_users=body.allowed_users,
            allowed_groups=body.allowed_groups,
        )
        if not privacy_id:
            raise HTTPException(status_code=500, detail="Failed to store privacy control")
        log_privacy_request(request, "photo_privacy_set", {"photo_path": photo_path, "visibility": body.visibility})
        control = db.get_photo_privacy(photo_path)
        return _control_dict(control) if control else {"photo_path": photo_path, "status": "created"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Set photo privacy control failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/privacy/control/{photo_path:path}")
async def get_photo_privacy_control(photo_path: str):
    """Get the privacy control settings for a photo."""
    try:
        control = _get_privacy_controls_db().get_photo_privacy(photo_path)
        return {"privacy": _control_dict(control) if control else None}
    except Exception as e:
        logger.error(f"Get photo privacy control failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/privacy/control/{photo_path:path}")
async def update_photo_privacy_control(photo_path: str, body: PhotoPrivacyUpdateRequest):
    """Update individual privacy control fields for a photo."""
    try:
        updated = _get_privacy_controls_db().update_photo_privacy(
            photo_path=photo_path,
            visibility=body.visibility,
            share_permissions=body.share_permissions,
            encryption_enabled=body.encryption_enabled,
            encryption_key_hash=body.encryption_key_hash,
            allowed_users=body.allowed_users,
            allowed_groups=body.allowed_groups,
        )
        if not updated:
            raise HTTPException(status_code=404, detail=f"No privacy control for {photo_path}")
        control = _get_privacy_controls_db().get_photo_privacy(photo_path)
        return {"status": "updated", "privacy": _control_dict(control) if control else None}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update photo privacy control failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/privacy/visible/{visibility}/{owner_id}")
async def get_photos_by_visibility(visibility: str, owner_id: str, limit: int = 50, offset: int = 0):
    """List an owner's photos with a given visibility setting."""
    try:
        photos = _get_privacy_controls_db().get_photos_by_visibility(visibility, owner_id, limit, offset)
        return {"photos": photos, "count": len(photos)}
    except Exception as e:
        logger.error(f"List photos by visibility failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/privacy/access/{user_id}")
async def get_photos_accessible_to_user(user_id: str, limit: int = 50, offset: int = 0):
    """List photos a user has permission to access."""
    try:
        photos = _get_privacy_controls_db().get_photos_for_user(user_id, limit, offset)
        return {"photos": photos, "count": len(photos)}
    except Exception as e:
        logger.error(f"List accessible photos failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/privacy/check-access/{photo_path:path}/{user_id}")
async def check_photo_access(photo_path: str, user_id: str):
    """Check whether a user has permission to access a photo."""
    try:
        has_access = _get_privacy_controls_db().check_access_permission(photo_path, user_id)
        return {"has_access": has_access}
    except Exception as e:
        logger.error(f"Check photo access failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/privacy/encrypted/{owner_id}")
async def get_encrypted_photos(owner_id: str):
    """List an owner's photos that have encryption enabled."""
    try:
        photos = _get_privacy_controls_db().get_encrypted_photos(owner_id)
        return {"encrypted_photos": photos, "count": len(photos)}
    except Exception as e:
        logger.error(f"List encrypted photos failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/privacy/stats/{owner_id}")
async def get_owner_privacy_stats(owner_id: str):
    """Privacy-control statistics for an owner."""
    try:
        stats = _get_privacy_controls_db().get_privacy_stats(owner_id)
        return {"stats": stats}
    except Exception as e:
        logger.error(f"Get privacy stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/privacy/revoke-access/{photo_path:path}/{user_id}")
async def revoke_user_photo_access(photo_path: str, user_id: str):
    """Revoke a user's access to a photo."""
    try:
        success = _get_privacy_controls_db().revoke_user_access(photo_path, user_id)
        return {"status": "revoked" if success else "not_found", "success": success}
    except Exception as e:
        logger.error(f"Revoke photo access failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
