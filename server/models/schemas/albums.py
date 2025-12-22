from typing import List, Optional

from pydantic import BaseModel


class AlbumCreate(BaseModel):
    name: str
    description: Optional[str] = None


class AlbumUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cover_photo_path: Optional[str] = None


class AlbumPhotosRequest(BaseModel):
    photo_paths: List[str]
