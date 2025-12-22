from typing import Any, Dict, Optional

from pydantic import BaseModel


class LegacyVersionCreateRequest(BaseModel):
    original_path: str
    version_path: str
    version_type: str = "edited"  # 'original', 'edited', 'variant'
    version_name: Optional[str] = None
    version_description: Optional[str] = None
    editing_instructions: Optional[Dict[str, Any]] = None
    parent_version_id: Optional[str] = None


class LegacyVersionUpdateRequest(BaseModel):
    version_name: Optional[str] = None
    version_description: Optional[str] = None


class VersionCreateRequest(BaseModel):
    original_path: str
    version_path: str
    version_type: str = "edit"  # 'original', 'edit', 'variant', 'derivative'
    version_name: Optional[str] = None
    version_description: Optional[str] = None
    edit_instructions: Optional[Dict[str, Any]] = None
    parent_version_id: Optional[str] = None


class VersionUpdateRequest(BaseModel):
    version_name: Optional[str] = None
    version_description: Optional[str] = None
