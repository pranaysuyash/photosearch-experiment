from typing import Any, Dict, Optional

from pydantic import BaseModel


class SmartCollectionCreateRequest(BaseModel):
    name: str
    description: str
    rule_definition: Dict[str, Any]  # JSON definition of inclusion criteria
    auto_update: bool = True
    privacy_level: str = "private"  # public, shared, private


class SmartCollectionUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    rule_definition: Optional[Dict[str, Any]] = None
    auto_update: Optional[bool] = None
    privacy_level: Optional[str] = None
    is_favorite: Optional[bool] = None
