from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class BulkActionRequest(BaseModel):
    action_type: str  # 'delete', 'favorite', 'tag_add', 'tag_remove', 'move', 'copy'
    paths: List[str]
    operation_data: Optional[Dict[str, Any]] = None  # Additional data for the operation


class BulkActionUndoRequest(BaseModel):
    action_id: str
