from typing import List

from pydantic import BaseModel


class OCRSearchRequest(BaseModel):
    query: str
    limit: int = 100
    offset: int = 0


class OCRImageRequest(BaseModel):
    image_paths: List[str]
