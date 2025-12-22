from typing import List

from pydantic import BaseModel


class LibraryRemoveRequest(BaseModel):
    file_paths: List[str]
