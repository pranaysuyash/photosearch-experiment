from fastapi import APIRouter, HTTPException

from server.config import settings
from server.models.schemas.privacy import PrivacyControlRequest, PrivacyUpdateRequest
from server.privacy_controls_db import get_privacy_controls_db


router = APIRouter()


@router.post("/privacy/control/{photo_path:path}")
async def set_photo_privacy(photo_path: str, request: PrivacyControlRequest):
    """Set privacy controls for a photo."""
    try:
        privacy_db = get_privacy_controls_db(settings.BASE_DIR / "privacy.db")

        privacy_id = privacy_db.set_photo_privacy(
            photo_path=photo_path,
            owner_id=request.owner_id,
            visibility=request.visibility,
            share_permissions=request.share_permissions,
            encryption_enabled=request.encryption_enabled,
            encryption_key_hash=request.encryption_key_hash,
            allowed_users=request.allowed_users,
            allowed_groups=request.allowed_groups,
        )

        if not privacy_id:
            raise HTTPException(status_code=400, detail="Failed to set privacy controls")

        return {"success": True, "privacy_id": privacy_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/privacy/control/{photo_path:path}")
async def get_photo_privacy(photo_path: str):
    """Get privacy settings for a photo."""
    try:
        privacy_db = get_privacy_controls_db(settings.BASE_DIR / "privacy.db")
        privacy = privacy_db.get_photo_privacy(photo_path)

        if not privacy:
            raise HTTPException(status_code=404, detail="Privacy settings not found for photo")

        return {"privacy": privacy}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/privacy/control/{photo_path:path}")
async def update_photo_privacy(photo_path: str, request: PrivacyUpdateRequest):
    """Update privacy settings for a photo."""
    try:
        privacy_db = get_privacy_controls_db(settings.BASE_DIR / "privacy.db")

        success = privacy_db.update_photo_privacy(
            photo_path=photo_path,
            visibility=request.visibility,
            share_permissions=request.share_permissions,
            encryption_enabled=request.encryption_enabled,
            encryption_key_hash=request.encryption_key_hash,
            allowed_users=request.allowed_users,
            allowed_groups=request.allowed_groups,
        )

        if not success:
            raise HTTPException(status_code=404, detail="Privacy settings not found for photo")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/privacy/visible/{visibility}/{owner_id}")
async def get_photos_by_visibility(visibility: str, owner_id: str, limit: int = 50, offset: int = 0):
    """Get photos with specific visibility for an owner."""
    try:
        privacy_db = get_privacy_controls_db(settings.BASE_DIR / "privacy.db")
        photos = privacy_db.get_photos_by_visibility(visibility, owner_id, limit, offset)
        return {"photos": photos, "count": len(photos)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/privacy/access/{user_id}")
async def get_photos_accessible_to_user(user_id: str, limit: int = 50, offset: int = 0):
    """Get photos that a user has access to based on privacy settings."""
    try:
        privacy_db = get_privacy_controls_db(settings.BASE_DIR / "privacy.db")
        photos = privacy_db.get_photos_for_user(user_id, limit, offset)
        return {"photos": photos, "count": len(photos)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/privacy/check-access/{photo_path:path}/{user_id}")
async def check_photo_access(photo_path: str, user_id: str):
    """Check if a user has permission to access a photo."""
    try:
        privacy_db = get_privacy_controls_db(settings.BASE_DIR / "privacy.db")
        has_access = privacy_db.check_access_permission(photo_path, user_id)
        return {"has_access": has_access}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/privacy/encrypted/{owner_id}")
async def get_encrypted_photos(owner_id: str):
    """Get all photos with encryption enabled for an owner."""
    try:
        privacy_db = get_privacy_controls_db(settings.BASE_DIR / "privacy.db")
        encrypted_photos = privacy_db.get_encrypted_photos(owner_id)
        return {"encrypted_photos": encrypted_photos, "count": len(encrypted_photos)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/privacy/stats/{owner_id}")
async def get_privacy_stats(owner_id: str):
    """Get statistics about privacy settings for an owner."""
    try:
        privacy_db = get_privacy_controls_db(settings.BASE_DIR / "privacy.db")
        stats = privacy_db.get_privacy_stats(owner_id)
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/privacy/revoke-access/{photo_path:path}/{user_id}")
async def revoke_user_access(photo_path: str, user_id: str):
    """Revoke access for a specific user to a photo."""
    try:
        privacy_db = get_privacy_controls_db(settings.BASE_DIR / "privacy.db")
        success = privacy_db.revoke_user_access(photo_path, user_id)

        if not success:
            raise HTTPException(status_code=400, detail="Failed to revoke access")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
