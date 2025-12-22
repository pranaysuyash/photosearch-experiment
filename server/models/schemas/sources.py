from typing import Dict, Optional

from pydantic import BaseModel


class SourceOut(BaseModel):
    id: str
    type: str
    name: str
    status: str
    created_at: str
    updated_at: str
    last_sync_at: Optional[str] = None
    last_error: Optional[str] = None
    config: Dict[str, object] = {}


class LocalFolderSourceCreate(BaseModel):
    name: Optional[str] = None
    path: str
    force: bool = False


class S3SourceCreate(BaseModel):
    name: str
    endpoint_url: str
    region: str
    bucket: str
    prefix: Optional[str] = None
    access_key_id: str
    secret_access_key: str


class GoogleDriveSourceCreate(BaseModel):
    name: str
    client_id: str
    client_secret: str
