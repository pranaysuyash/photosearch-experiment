from typing import Optional

from pydantic import BaseModel


class CollaborativeSpaceCreateRequest(BaseModel):
    name: str
    description: str
    privacy_level: str = "private"  # public, shared, private
    max_members: int = 10


class CollaborativeSpaceUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    privacy_level: Optional[str] = None
    max_members: Optional[int] = None


class AddMemberRequest(BaseModel):
    user_id: str
    role: str = "contributor"  # owner, admin, contributor, viewer


class SpacePhotoCreateRequest(BaseModel):
    photo_path: str
    caption: Optional[str] = None


class SpaceCommentCreateRequest(BaseModel):
    comment: str
