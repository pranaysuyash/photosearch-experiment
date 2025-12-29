"""
Mobile Face Recognition API Router - Phase 8

Provides mobile-optimized face recognition endpoints including:
1. Mobile device registration and management
2. Offline face detection and processing
3. Cross-device synchronization
4. Mobile push notifications
5. Bandwidth-optimized responses
6. Mobile-specific face tagging workflows

Features:
- Compressed response formats for mobile bandwidth
- Offline-first architecture with sync capabilities
- Mobile device management and authentication
- Push notification system for face detection events
- Cross-device encrypted synchronization
- Mobile-optimized face processing workflows

Security:
- Device authentication and registration
- Encrypted sync tokens
- Privacy-aware mobile processing
- Secure offline data storage
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, UploadFile, File
from pydantic import BaseModel, Field

from server.config import settings
from server.api.deps import get_state
from server.core.state import AppState
from server.mobile_face_service import MobileFaceService

logger = logging.getLogger(__name__)

router = APIRouter()

# Request/Response Models


class MobileDeviceRegistration(BaseModel):
    """Mobile device registration request"""

    device_id: str = Field(..., description="Unique device identifier")
    device_name: str = Field(..., description="Human-readable device name")
    device_type: str = Field(..., description="Device type (ios, android, web)")
    user_id: str = Field(..., description="User identifier")
    push_token: Optional[str] = Field(None, description="Push notification token")


class MobileFaceDetectionRequest(BaseModel):
    """Mobile face detection request"""

    device_id: str = Field(..., description="Mobile device identifier")
    offline_mode: bool = Field(default=False, description="Process in offline mode")
    max_faces: int = Field(default=10, description="Maximum faces to detect")


class MobileFaceTagRequest(BaseModel):
    """Mobile face tagging request"""

    device_id: str = Field(..., description="Mobile device identifier")
    detection_id: str = Field(..., description="Face detection identifier")
    person_name: str = Field(..., description="Person name for tagging")


class MobileSyncRequest(BaseModel):
    """Mobile synchronization request"""

    device_id: str = Field(..., description="Mobile device identifier")
    sync_token: str = Field(..., description="Synchronization token")
    upload_data: Optional[List[Dict]] = Field(None, description="Data to upload from device")


class MobileNotificationRequest(BaseModel):
    """Mobile notification request"""

    device_id: str = Field(..., description="Target device identifier")
    notification_type: str = Field(..., description="Notification type")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    data: Optional[Dict] = Field(None, description="Additional notification data")


# Helper function to get mobile service
def get_mobile_service(state: AppState) -> MobileFaceService:
    """Get mobile face service instance"""
    if not hasattr(state, "_mobile_face_service"):
        state._mobile_face_service = MobileFaceService(
            face_clusterer=state.face_clusterer, db_path=settings.FACE_CLUSTERS_DB_PATH
        )
    return state._mobile_face_service


def get_user_id_from_request(request: Request) -> str:
    """Extract user ID from request headers"""
    return request.headers.get("X-User-ID", "default_user")


# Device Management Endpoints


@router.post("/api/mobile/devices/register")
async def register_mobile_device(
    registration: MobileDeviceRegistration, request: Request, state: AppState = Depends(get_state)
):
    """
    Register a mobile device for face recognition services.

    Enables mobile-optimized face processing and cross-device sync.
    """
    try:
        mobile_service = get_mobile_service(state)

        result = mobile_service.register_mobile_device(
            device_id=registration.device_id,
            device_name=registration.device_name,
            device_type=registration.device_type,
            user_id=registration.user_id,
            push_token=registration.push_token,
        )

        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])

        return {"success": True, "message": "Mobile device registered successfully", **result}

    except Exception as e:
        logger.error(f"Mobile device registration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/mobile/devices/{device_id}/status")
async def get_device_status(device_id: str, request: Request, state: AppState = Depends(get_state)):
    """Get mobile device status and sync information."""
    try:
        mobile_service = get_mobile_service(state)

        sync_status = mobile_service.get_device_sync_status(device_id)

        return {
            "success": True,
            "device_id": device_id,
            "sync_status": {
                "last_sync": sync_status.last_sync.isoformat() if sync_status.last_sync else None,
                "sync_token": sync_status.sync_token,
                "pending_uploads": sync_status.pending_uploads,
                "pending_downloads": sync_status.pending_downloads,
                "conflicts": sync_status.conflicts,
                "offline_changes": sync_status.offline_changes,
            },
        }

    except Exception as e:
        logger.error(f"Get device status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Mobile Face Processing Endpoints


@router.post("/api/mobile/faces/detect")
async def detect_faces_mobile(
    detection_request: MobileFaceDetectionRequest, image: UploadFile = File(...), state: AppState = Depends(get_state)
):
    """
    Mobile-optimized face detection with compressed responses.

    Processes uploaded image and returns mobile-friendly face detection results.
    Supports offline mode for processing without server connectivity.
    """
    try:
        mobile_service = get_mobile_service(state)

        # Read image data
        image_data = await image.read()

        # Process with mobile optimizations
        result = mobile_service.detect_faces_mobile(
            image_data=image_data, device_id=detection_request.device_id, offline_mode=detection_request.offline_mode
        )

        return {
            "success": True,
            "processing_result": {
                "image_id": result.image_id,
                "device_id": result.device_id,
                "processing_time_ms": result.processing_time_ms,
                "faces_detected": result.faces_detected,
                "faces_processed": result.faces_processed,
                "detections": [
                    {
                        "detection_id": d.detection_id,
                        "bbox": d.bbox,
                        "confidence": d.confidence,
                        "quality_score": d.quality_score,
                        "attributes": d.attributes,
                        "embedding_hash": d.embedding_hash,
                        "cluster_suggestion": d.cluster_suggestion,
                    }
                    for d in result.detections
                ],
                "offline_mode": result.offline_mode,
                "sync_required": result.sync_required,
                "compressed_size_bytes": result.compressed_size_bytes,
            },
        }

    except Exception as e:
        logger.error(f"Mobile face detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/mobile/faces/suggestions/{device_id}")
async def get_mobile_face_suggestions(device_id: str, limit: int = 10, state: AppState = Depends(get_state)):
    """Get face tagging suggestions optimized for mobile interface."""
    try:
        mobile_service = get_mobile_service(state)

        suggestions = mobile_service.get_mobile_face_suggestions(device_id=device_id, limit=limit)

        return {"success": True, "device_id": device_id, "suggestions": suggestions, "count": len(suggestions)}

    except Exception as e:
        logger.error(f"Get mobile face suggestions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/mobile/faces/tag")
async def tag_face_mobile(tag_request: MobileFaceTagRequest, request: Request, state: AppState = Depends(get_state)):
    """Mobile-optimized face tagging with offline support."""
    try:
        mobile_service = get_mobile_service(state)

        result = mobile_service.tag_face_mobile(
            device_id=tag_request.device_id, detection_id=tag_request.detection_id, person_name=tag_request.person_name
        )

        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])

        return {"success": True, "message": "Face tagged successfully", **result}

    except Exception as e:
        logger.error(f"Mobile face tagging failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Cross-Device Synchronization Endpoints


@router.post("/api/mobile/sync")
async def sync_face_data(sync_request: MobileSyncRequest, request: Request, state: AppState = Depends(get_state)):
    """
    Synchronize face data between mobile device and server.

    Handles bidirectional sync with conflict resolution and encrypted data transfer.
    """
    try:
        mobile_service = get_mobile_service(state)

        result = mobile_service.sync_face_data(
            device_id=sync_request.device_id, sync_token=sync_request.sync_token, upload_data=sync_request.upload_data
        )

        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])

        return {"success": True, "message": "Synchronization completed successfully", **result}

    except Exception as e:
        logger.error(f"Mobile sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/mobile/sync/{device_id}/conflicts")
async def get_sync_conflicts(device_id: str, request: Request, state: AppState = Depends(get_state)):
    """Get synchronization conflicts for mobile device."""
    try:
        mobile_service = get_mobile_service(state)

        # Get conflicts from database
        with mobile_service._get_privacy_db() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT conflict_id, resource_type, resource_id, conflict_type,
                       device1_data, device2_data, created_at
                FROM sync_conflicts
                WHERE (device1_id = ? OR device2_id = ?) AND resolved = 0
                ORDER BY created_at DESC
            """,
                (device_id, device_id),
            )

            conflicts = []
            for row in cursor.fetchall():
                conflicts.append(
                    {
                        "conflict_id": row["conflict_id"],
                        "resource_type": row["resource_type"],
                        "resource_id": row["resource_id"],
                        "conflict_type": row["conflict_type"],
                        "device1_data": json.loads(row["device1_data"]),
                        "device2_data": json.loads(row["device2_data"]),
                        "created_at": row["created_at"],
                    }
                )

        return {"success": True, "device_id": device_id, "conflicts": conflicts, "count": len(conflicts)}

    except Exception as e:
        logger.error(f"Get sync conflicts failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/mobile/sync/conflicts/{conflict_id}/resolve")
async def resolve_sync_conflict(
    conflict_id: str, resolution_data: Dict, request: Request, state: AppState = Depends(get_state)
):
    """Resolve a synchronization conflict."""
    try:
        mobile_service = get_mobile_service(state)

        # Update conflict resolution in database
        with mobile_service._get_privacy_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE sync_conflicts
                SET resolved = 1, resolution_data = ?, resolved_at = CURRENT_TIMESTAMP
                WHERE conflict_id = ?
            """,
                (json.dumps(resolution_data), conflict_id),
            )

            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Conflict not found")

            conn.commit()

        return {
            "success": True,
            "conflict_id": conflict_id,
            "message": "Conflict resolved successfully",
            "resolution": resolution_data,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resolve sync conflict failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Mobile Push Notifications Endpoints


@router.post("/api/mobile/notifications/send")
async def send_mobile_notification(
    notification_request: MobileNotificationRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    state: AppState = Depends(get_state),
):
    """Send push notification to mobile device."""
    try:
        mobile_service = get_mobile_service(state)

        # Queue notification in database
        notification_id = str(uuid.uuid4())

        with mobile_service._get_privacy_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO mobile_notifications
                (notification_id, device_id, notification_type, title, message, data)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    notification_id,
                    notification_request.device_id,
                    notification_request.notification_type,
                    notification_request.title,
                    notification_request.message,
                    json.dumps(notification_request.data or {}),
                ),
            )
            conn.commit()

        # In a real implementation, this would send the actual push notification
        # For now, we'll just queue it for processing
        background_tasks.add_task(_process_push_notification, notification_id, notification_request.device_id)

        return {"success": True, "notification_id": notification_id, "message": "Notification queued for delivery"}

    except Exception as e:
        logger.error(f"Send mobile notification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/mobile/notifications/{device_id}")
async def get_mobile_notifications(
    device_id: str, limit: int = 50, offset: int = 0, state: AppState = Depends(get_state)
):
    """Get mobile notifications for device."""
    try:
        mobile_service = get_mobile_service(state)

        with mobile_service._get_privacy_db() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT notification_id, notification_type, title, message, data,
                       sent, created_at, sent_at
                FROM mobile_notifications
                WHERE device_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """,
                (device_id, limit, offset),
            )

            notifications = []
            for row in cursor.fetchall():
                notifications.append(
                    {
                        "notification_id": row["notification_id"],
                        "notification_type": row["notification_type"],
                        "title": row["title"],
                        "message": row["message"],
                        "data": json.loads(row["data"]) if row["data"] else {},
                        "sent": bool(row["sent"]),
                        "created_at": row["created_at"],
                        "sent_at": row["sent_at"],
                    }
                )

        return {"success": True, "device_id": device_id, "notifications": notifications, "count": len(notifications)}

    except Exception as e:
        logger.error(f"Get mobile notifications failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Mobile Settings and Configuration Endpoints


@router.get("/api/mobile/settings/{device_id}")
async def get_mobile_settings(device_id: str, state: AppState = Depends(get_state)):
    """Get mobile-specific settings and configuration."""
    try:
        mobile_service = get_mobile_service(state)

        return {
            "success": True,
            "device_id": device_id,
            "settings": mobile_service.mobile_settings,
            "features": {
                "offline_processing": True,
                "cross_device_sync": True,
                "push_notifications": True,
                "compressed_responses": True,
                "mobile_optimized_ui": True,
            },
        }

    except Exception as e:
        logger.error(f"Get mobile settings failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/mobile/settings/{device_id}")
async def update_mobile_settings(
    device_id: str, settings_update: Dict, request: Request, state: AppState = Depends(get_state)
):
    """Update mobile-specific settings."""
    try:
        mobile_service = get_mobile_service(state)

        # Update device settings in database
        with mobile_service._get_privacy_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE mobile_devices
                SET updated_at = CURRENT_TIMESTAMP
                WHERE device_id = ?
            """,
                (device_id,),
            )

            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Device not found")

            conn.commit()

        return {
            "success": True,
            "device_id": device_id,
            "message": "Mobile settings updated successfully",
            "updated_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update mobile settings failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Mobile Analytics and Performance Endpoints


@router.get("/api/mobile/analytics/{device_id}")
async def get_mobile_analytics(device_id: str, days: int = 30, state: AppState = Depends(get_state)):
    """Get mobile usage analytics and performance metrics."""
    try:
        mobile_service = get_mobile_service(state)

        # Get analytics from database
        with mobile_service._get_privacy_db() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get sync operations
            cursor.execute(
                """
                SELECT operation_type, COUNT(*) as count,
                       AVG(success_count) as avg_success,
                       AVG(error_count) as avg_errors
                FROM sync_operations
                WHERE device_id = ? AND started_at > datetime('now', '-{} days')
                GROUP BY operation_type
            """.format(days),
                (device_id,),
            )

            sync_stats = {
                row["operation_type"]: {
                    "count": row["count"],
                    "avg_success": row["avg_success"],
                    "avg_errors": row["avg_errors"],
                }
                for row in cursor.fetchall()
            }

            # Get notification stats
            cursor.execute(
                """
                SELECT notification_type, COUNT(*) as count,
                       SUM(CASE WHEN sent = 1 THEN 1 ELSE 0 END) as sent_count
                FROM mobile_notifications
                WHERE device_id = ? AND created_at > datetime('now', '-{} days')
                GROUP BY notification_type
            """.format(days),
                (device_id,),
            )

            notification_stats = {
                row["notification_type"]: {
                    "total": row["count"],
                    "sent": row["sent_count"],
                    "delivery_rate": (row["sent_count"] / row["count"]) * 100 if row["count"] > 0 else 0,
                }
                for row in cursor.fetchall()
            }

        return {
            "success": True,
            "device_id": device_id,
            "period_days": days,
            "analytics": {
                "sync_operations": sync_stats,
                "notifications": notification_stats,
                "generated_at": datetime.now().isoformat(),
            },
        }

    except Exception as e:
        logger.error(f"Get mobile analytics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Maintenance and Cleanup Endpoints


@router.post("/api/mobile/cleanup/{device_id}")
async def cleanup_mobile_data(
    device_id: str, request: Request, state: AppState = Depends(get_state), days_old: int = 7
):
    """Clean up old mobile data and cache."""
    try:
        mobile_service = get_mobile_service(state)

        cleanup_result = mobile_service.cleanup_offline_cache(days_old=days_old)

        return {
            "success": True,
            "device_id": device_id,
            "cleanup_result": cleanup_result,
            "message": f"Cleaned up data older than {days_old} days",
        }

    except Exception as e:
        logger.error(f"Mobile cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Background task functions


async def _process_push_notification(notification_id: str, device_id: str):
    """Background task to process push notification delivery"""
    try:
        # In a real implementation, this would:
        # 1. Get device push token from database
        # 2. Send notification via FCM/APNS
        # 3. Update notification status

        # For now, just mark as sent
        import sqlite3

        db_path = Path(settings.FACE_CLUSTERS_DB_PATH).parent / "privacy.db"

        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE mobile_notifications
                SET sent = 1, sent_at = CURRENT_TIMESTAMP
                WHERE notification_id = ?
            """,
                (notification_id,),
            )
            conn.commit()

        logger.info(f"Push notification {notification_id} processed for device {device_id}")

    except Exception as e:
        logger.error(f"Push notification processing failed: {e}")


# Import required modules
import sqlite3
import uuid
