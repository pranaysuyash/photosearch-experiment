from pydantic import BaseModel


class ScanRequest(BaseModel):
    path: str


class SearchRequest(BaseModel):
    query: str
    limit: int = 1000
    offset: int = 0


class SearchCountRequest(BaseModel):
    query: str
    mode: str = "metadata"
