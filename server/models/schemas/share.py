from typing import List, Optional

from pydantic import BaseModel


class ShareRequest(BaseModel):
    paths: List[str]
    expiration_hours: int = 24  # Default 24 hours
    password: Optional[str] = None  # Optional password protection


class ShareResponse(BaseModel):
    share_id: str
    share_url: str
    expiration: str
    download_count: int = 0
