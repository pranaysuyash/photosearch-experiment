from fastapi import APIRouter, HTTPException

from server.collaborative_spaces_db import get_collaborative_spaces_db
from server.config import settings
from server.models.schemas.collaborative_spaces import (
    AddMemberRequest,
    CollaborativeSpaceCreateRequest,
    CollaborativeSpaceUpdateRequest,
    SpaceCommentCreateRequest,
    SpacePhotoCreateRequest,
)


router = APIRouter()


@router.post("/collaborative/spaces")
async def create_collaborative_space(request: CollaborativeSpaceCreateRequest, user_id: str = "default_user"):
    """Create a new collaborative photo space."""
    try:
        spaces_db = get_collaborative_spaces_db(settings.BASE_DIR / "collaborative_spaces.db")

        space_id = spaces_db.create_collaborative_space(
            name=request.name,
            description=request.description,
            owner_id=user_id,  # In a real app, this would come from auth
            privacy_level=request.privacy_level,
            max_members=request.max_members,
        )

        if not space_id:
            raise HTTPException(status_code=400, detail="Failed to create space")

        return {"success": True, "space_id": space_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collaborative/spaces/{space_id}")
async def get_collaborative_space(space_id: str):
    """Get details about a specific collaborative space."""
    try:
        spaces_db = get_collaborative_spaces_db(settings.BASE_DIR / "collaborative_spaces.db")
        space = spaces_db.get_collaborative_space(space_id)

        if not space:
            raise HTTPException(status_code=404, detail="Space not found")

        return {"space": space}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collaborative/spaces/user/{user_id}")
async def get_user_spaces(user_id: str, limit: int = 50, offset: int = 0):
    """Get all collaborative spaces a user belongs to."""
    try:
        spaces_db = get_collaborative_spaces_db(settings.BASE_DIR / "collaborative_spaces.db")
        user_spaces = spaces_db.get_user_spaces(user_id, limit, offset)
        return {"spaces": user_spaces, "count": len(user_spaces)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collaborative/spaces/{space_id}/members")
async def add_member_to_space(space_id: str, request: AddMemberRequest):
    """Add a member to a collaborative space."""
    try:
        spaces_db = get_collaborative_spaces_db(settings.BASE_DIR / "collaborative_spaces.db")

        success = spaces_db.add_member_to_space(
            space_id=space_id,
            user_id=request.user_id,
            role=request.role,
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to add member")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/collaborative/spaces/{space_id}/members/{user_id}")
async def remove_member_from_space(space_id: str, user_id: str):
    """Remove a member from a collaborative space."""
    try:
        spaces_db = get_collaborative_spaces_db(settings.BASE_DIR / "collaborative_spaces.db")

        success = spaces_db.remove_member_from_space(space_id, user_id)

        if not success:
            raise HTTPException(status_code=400, detail="Failed to remove member")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collaborative/spaces/{space_id}/members")
async def get_space_members(space_id: str):
    """Get all members of a collaborative space."""
    try:
        spaces_db = get_collaborative_spaces_db(settings.BASE_DIR / "collaborative_spaces.db")
        members = spaces_db.get_space_members(space_id)
        return {"members": members, "count": len(members)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collaborative/spaces/{space_id}/photos")
async def add_photo_to_space(space_id: str, request: SpacePhotoCreateRequest, user_id: str = "default_user"):
    """Add a photo to a collaborative space."""
    try:
        spaces_db = get_collaborative_spaces_db(settings.BASE_DIR / "collaborative_spaces.db")

        success = spaces_db.add_photo_to_space(
            space_id=space_id,
            photo_path=request.photo_path,
            added_by_user_id=user_id,  # In a real app, this would come from auth
            caption=request.caption or "",
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to add photo to space")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/collaborative/spaces/{space_id}/photos/{photo_path:path}")
async def remove_photo_from_space(space_id: str, photo_path: str):
    """Remove a photo from a collaborative space."""
    try:
        spaces_db = get_collaborative_spaces_db(settings.BASE_DIR / "collaborative_spaces.db")

        success = spaces_db.remove_photo_from_space(space_id, photo_path)

        if not success:
            raise HTTPException(status_code=400, detail="Failed to remove photo from space")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collaborative/spaces/{space_id}/photos")
async def get_space_photos(space_id: str, limit: int = 50, offset: int = 0):
    """Get all photos in a collaborative space."""
    try:
        spaces_db = get_collaborative_spaces_db(settings.BASE_DIR / "collaborative_spaces.db")
        photos = spaces_db.get_space_photos(space_id, limit, offset)
        return {"photos": photos, "count": len(photos)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collaborative/spaces/{space_id}/photos/{photo_path:path}/comments")
async def add_comment_to_space_photo(
    space_id: str,
    photo_path: str,
    request: SpaceCommentCreateRequest,
    user_id: str = "default_user",
):
    """Add a comment to a photo in a collaborative space."""
    try:
        spaces_db = get_collaborative_spaces_db(settings.BASE_DIR / "collaborative_spaces.db")

        comment_id = spaces_db.add_comment_to_space_photo(
            space_id=space_id,
            photo_path=photo_path,
            user_id=user_id,  # In a real app, this would come from auth
            comment=request.comment,
        )

        if not comment_id:
            raise HTTPException(status_code=400, detail="Failed to add comment")

        return {"success": True, "comment_id": comment_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collaborative/spaces/{space_id}/photos/{photo_path:path}/comments")
async def get_photo_comments(space_id: str, photo_path: str, limit: int = 50, offset: int = 0):
    """Get all comments for a photo in a collaborative space."""
    try:
        spaces_db = get_collaborative_spaces_db(settings.BASE_DIR / "collaborative_spaces.db")
        comments = spaces_db.get_photo_comments(space_id, photo_path, limit, offset)
        return {"comments": comments, "count": len(comments)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collaborative/spaces/{space_id}/stats")
async def get_space_stats(space_id: str):
    """Get statistics about a collaborative space."""
    try:
        spaces_db = get_collaborative_spaces_db(settings.BASE_DIR / "collaborative_spaces.db")
        stats = spaces_db.get_space_stats(space_id)
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
