from typing import Dict, List, Optional

from pydantic import BaseModel


class PrivacyControlRequest(BaseModel):
    owner_id: str
    visibility: str = "private"  # public, shared, private, friends_only
    share_permissions: Optional[Dict[str, bool]] = None
    encryption_enabled: bool = False
    encryption_key_hash: Optional[str] = None
    allowed_users: Optional[List[str]] = None
    allowed_groups: Optional[List[str]] = None


class PrivacyUpdateRequest(BaseModel):
    visibility: Optional[str] = None
    share_permissions: Optional[Dict[str, bool]] = None
    encryption_enabled: Optional[bool] = None
    encryption_key_hash: Optional[str] = None
    allowed_users: Optional[List[str]] = None
    allowed_groups: Optional[List[str]] = None
