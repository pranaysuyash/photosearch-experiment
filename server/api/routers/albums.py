import json
import os
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Depends

from server.albums_db import get_albums_db
from server.models.schemas.albums import AlbumCreate, AlbumPhotosRequest, AlbumUpdate
from server.smart_albums import initialize_predefined_smart_albums, populate_smart_album
from server.api.deps import get_state
from server.core.state import AppState


router = APIRouter()


@router.post("/albums")
async def create_album(req: AlbumCreate):
    """Create a new album."""
    albums_db = get_albums_db()
    album_id = str(uuid.uuid4())

    album = albums_db.create_album(
        album_id=album_id,
        name=req.name,
        description=req.description,
    )

    return {"album": album}


@router.get("/albums")
async def list_albums(include_smart: bool = True):
    """List all albums."""
    albums_db = get_albums_db()

    # Initialize predefined smart albums if not exists
    initialize_predefined_smart_albums(albums_db)

    albums = albums_db.list_albums(include_smart=include_smart)
    return {"albums": albums}


@router.get("/albums/{album_id}")
async def get_album(album_id: str, include_photos: bool = True, state: AppState = Depends(get_state)):
    """Get album details."""
    albums_db = get_albums_db()
    album = albums_db.get_album(album_id)

    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    result: dict[str, Any] = {"album": album}

    if include_photos:

        photo_paths = albums_db.get_album_photos(album_id)
        # Get metadata for photos
        photos = []
        for path in photo_paths:
            metadata = state.photo_search_engine.db.get_metadata(path)
            if metadata:
                photos.append(
                    {
                        "path": path,
                        "filename": os.path.basename(path),
                        "metadata": metadata,
                    }
                )
        result["photos"] = photos

    return result


@router.put("/albums/{album_id}")
async def update_album(album_id: str, req: AlbumUpdate):
    """Update album details."""
    albums_db = get_albums_db()

    album = albums_db.update_album(
        album_id=album_id,
        name=req.name,
        description=req.description,
        cover_photo_path=req.cover_photo_path,
    )

    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    return {"album": album}


@router.delete("/albums/{album_id}")
async def delete_album(album_id: str):
    """Delete an album."""
    albums_db = get_albums_db()

    # Don't allow deleting smart albums
    album = albums_db.get_album(album_id)
    if album and album.is_smart:
        raise HTTPException(status_code=400, detail="Cannot delete smart albums")

    success = albums_db.delete_album(album_id)

    if not success:
        raise HTTPException(status_code=404, detail="Album not found")

    return {"ok": True}


@router.post("/albums/{album_id}/photos")
async def add_photos_to_album(album_id: str, req: AlbumPhotosRequest):
    """Add photos to album."""
    albums_db = get_albums_db()

    # Check album exists
    album = albums_db.get_album(album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    # Don't allow adding to smart albums
    if album.is_smart:
        raise HTTPException(status_code=400, detail="Cannot manually add photos to smart albums")

    added = albums_db.add_photos_to_album(album_id, req.photo_paths)

    return {"added": added, "total": len(req.photo_paths)}


@router.delete("/albums/{album_id}/photos")
async def remove_photos_from_album(album_id: str, req: AlbumPhotosRequest):
    """Remove photos from album."""
    albums_db = get_albums_db()

    # Check album exists
    album = albums_db.get_album(album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    # Don't allow removing from smart albums
    if album.is_smart:
        raise HTTPException(status_code=400, detail="Cannot manually remove photos from smart albums")

    removed = albums_db.remove_photos_from_album(album_id, req.photo_paths)

    return {"removed": removed}


@router.post("/albums/{album_id}/refresh")
async def refresh_smart_album(album_id: str, state: AppState = Depends(get_state)):
    """Refresh a smart album (recompute matches)."""

    albums_db = get_albums_db()

    album = albums_db.get_album(album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    if not album.is_smart:
        raise HTTPException(status_code=400, detail="Only smart albums can be refreshed")

    # Get all photos with metadata
    cursor = state.photo_search_engine.db.conn.cursor()
    cursor.execute("SELECT file_path, metadata_json FROM metadata WHERE deleted_at IS NULL")

    photos_with_metadata = []
    for row in cursor.fetchall():
        metadata = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
        photos_with_metadata.append((row["file_path"], metadata))

    # Populate smart album
    populate_smart_album(albums_db, album_id, photos_with_metadata)

    # Return updated album
    album = albums_db.get_album(album_id)
    return {"album": album}


@router.get("/photos/{path:path}/albums")
async def get_photo_albums(path: str):
    """Get all albums containing a specific photo."""
    albums_db = get_albums_db()
    albums = albums_db.get_photo_albums(path)
    return {"albums": albums}
