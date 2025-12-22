from typing import Any, Dict, Optional

from pydantic import BaseModel


class StoryCreateRequest(BaseModel):
    title: str
    description: str
    owner_id: str
    metadata: Optional[Dict[str, Any]] = None
    is_published: bool = False


class StoryUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_published: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class TimelineEntryCreateRequest(BaseModel):
    photo_path: str
    date: str
    location: Optional[str] = None
    caption: Optional[str] = None


class TimelineEntryUpdateRequest(BaseModel):
    date: Optional[str] = None
    location: Optional[str] = None
    caption: Optional[str] = None
    narrative_order: Optional[int] = None
