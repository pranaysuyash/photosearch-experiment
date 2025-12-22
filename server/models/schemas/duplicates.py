from typing import List, Optional

from pydantic import BaseModel


class DuplicateResolution(BaseModel):
    resolution: str  # 'keep_all', 'keep_selected', 'delete_all'
    keep_files: Optional[List[str]] = None
