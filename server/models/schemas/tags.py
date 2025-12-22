from typing import List

from pydantic import BaseModel


class TagCreate(BaseModel):
    name: str


class TagPhotosRequest(BaseModel):
    photo_paths: List[str]
