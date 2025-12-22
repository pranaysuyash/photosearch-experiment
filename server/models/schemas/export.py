from typing import List, Optional

from pydantic import BaseModel


class ExportOptions(BaseModel):
    format: str = "zip"  # zip, pdf, json (for metadata)
    include_metadata: bool = True
    include_thumbnails: bool = False
    max_resolution: Optional[int] = None  # Max width/height in pixels
    rename_pattern: Optional[str] = None  # Pattern for renaming files
    password_protect: bool = False
    password: Optional[str] = None


class ExportRequest(BaseModel):
    paths: List[str]
    options: ExportOptions = ExportOptions()
