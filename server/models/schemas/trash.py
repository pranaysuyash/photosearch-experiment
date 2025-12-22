from typing import List, Optional

from pydantic import BaseModel


class TrashMoveRequest(BaseModel):
    file_paths: List[str]


class TrashRestoreRequest(BaseModel):
    item_ids: List[str]


class TrashEmptyRequest(BaseModel):
    item_ids: Optional[List[str]] = None
