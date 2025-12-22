import os
from typing import Dict

from fastapi import APIRouter, HTTPException, Depends

from server.config import settings
from server.models.schemas.tags import TagCreate, TagPhotosRequest
from server.tags_db import get_tags_db
from server.api.deps import get_state
from server.core.state import AppState

router = APIRouter()


@router.get("/tags")
async def list_tags(limit: int = 200, offset: int = 0):
    tags_db = get_tags_db(settings.BASE_DIR / "tags.db")
    tags = tags_db.list_tags(limit=limit, offset=offset)
    return {"tags": [t.__dict__ for t in tags]}


@router.post("/tags")
async def create_tag(req: TagCreate):
    name = (req.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    if len(name) > 80:
        raise HTTPException(status_code=400, detail="name too long")
    tags_db = get_tags_db(settings.BASE_DIR / "tags.db")
    tags_db.create_tag(name)
    return {"ok": True}


@router.delete("/tags/{tag_name}")
async def delete_tag(tag_name: str):
    tags_db = get_tags_db(settings.BASE_DIR / "tags.db")
    ok = tags_db.delete_tag(tag_name)
    if not ok:
        raise HTTPException(status_code=404, detail="Tag not found")
    return {"ok": True}


@router.get("/tags/{tag_name}")
async def get_tag(tag_name: str, include_photos: bool = True, state: AppState = Depends(get_state)):
    tags_db = get_tags_db(settings.BASE_DIR / "tags.db")
    if not tags_db.has_tag(tag_name):
        raise HTTPException(status_code=404, detail="Tag not found")
    out: Dict[str, object] = {"tag": tag_name}
    if include_photos:

        paths = tags_db.get_tag_paths(tag_name)
        photos = []
        for path in paths:
            metadata = state.photo_search_engine.db.get_metadata(path)
            if metadata:
                photos.append(
                    {
                        "path": path,
                        "filename": os.path.basename(path),
                        "metadata": metadata,
                    }
                )
        out["photos"] = photos
        out["photo_count"] = len(paths)
    return out


@router.post("/tags/{tag_name}/photos")
async def add_photos_to_tag(tag_name: str, req: TagPhotosRequest):
    tags_db = get_tags_db(settings.BASE_DIR / "tags.db")
    added = tags_db.add_photos(tag_name, req.photo_paths or [])
    return {"added": added, "total": len(req.photo_paths or [])}


@router.delete("/tags/{tag_name}/photos")
async def remove_photos_from_tag(tag_name: str, req: TagPhotosRequest):
    tags_db = get_tags_db(settings.BASE_DIR / "tags.db")
    removed = tags_db.remove_photos(tag_name, req.photo_paths or [])
    return {"removed": removed}


@router.get("/photos/{path:path}/tags")
async def get_photo_tags(path: str):
    tags_db = get_tags_db(settings.BASE_DIR / "tags.db")
    tags = tags_db.get_photo_tags(path)
    return {"tags": tags}
