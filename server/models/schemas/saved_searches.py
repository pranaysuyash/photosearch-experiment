from typing import Dict, Optional

from pydantic import BaseModel


class SaveSearchRequest(BaseModel):
    query: str
    mode: str = "metadata"
    results_count: int = 0
    intent: str = "generic"
    is_favorite: bool = False
    notes: str = ""
    metadata: Optional[Dict] = None


class UpdateSearchRequest(BaseModel):
    is_favorite: Optional[bool] = None
    notes: Optional[str] = None
