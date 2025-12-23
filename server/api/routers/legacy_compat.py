"""Legacy compatibility endpoints.

A small set of endpoints that earlier tests and scripts expect. These map onto
current DB modules and keep behavior lightweight.

Intent: keep backward-compat without forcing the whole app to carry old route
shapes forever.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from server.core.paths import _runtime_base_dir
from server.notes_db import get_notes_db
from server.tags_db import get_tags_db
from server.smart_collections_db import get_smart_collections_db
from server.people_tags_db import get_people_tags_db
from server.locations_db import get_locations_db


router = APIRouter()


# -------------------------------
# Notes (legacy: /notes/{path})
# Current API: /api/photos/{path}/notes
# -------------------------------


@router.get("/notes/{photo_path:path}")
async def legacy_get_note(photo_path: str):
    try:
        base_dir = _runtime_base_dir()
        notes_db = get_notes_db(base_dir / "notes.db")
        note = notes_db.get_note(photo_path)
        if note is None:
            raise HTTPException(status_code=404, detail="Note not found")
        return {"note": note}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notes/{photo_path:path}")
async def legacy_set_note(photo_path: str, payload: dict[str, Any]):
    try:
        base_dir = _runtime_base_dir()
        notes_db = get_notes_db(base_dir / "notes.db")
        note = payload.get("note")
        if not isinstance(note, str):
            raise HTTPException(status_code=400, detail="note is required")
        ok = notes_db.set_note(photo_path, note)
        if not ok:
            raise HTTPException(status_code=500, detail="Failed to set note")
        return {"success": True, "note": note}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/notes/{photo_path:path}")
async def legacy_delete_note(photo_path: str):
    try:
        base_dir = _runtime_base_dir()
        notes_db = get_notes_db(base_dir / "notes.db")
        ok = notes_db.delete_note(photo_path)
        if not ok:
            raise HTTPException(status_code=404, detail="Note not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------
# Tags (legacy: /tags/add, /tags/photo/{path}, /tags/photos/{tag})
# Current API: /tags/{tag}/photos, /photos/{path}/tags
# -------------------------------


@router.post("/tags/add")
async def legacy_tags_add(payload: dict[str, Any]):
    try:
        base_dir = _runtime_base_dir()
        tags_db = get_tags_db(base_dir / "tags.db")

        paths = payload.get("paths") or []
        tags = payload.get("tags") or []
        if not isinstance(paths, list) or not isinstance(tags, list):
            raise HTTPException(status_code=400, detail="paths and tags must be lists")

        # Ensure tags exist and associate.
        for t in tags:
            if not isinstance(t, str) or not t.strip():
                continue
            tag_name = t.strip()
            if not tags_db.has_tag(tag_name):
                tags_db.create_tag(tag_name)
            tags_db.add_photos(tag_name, [p for p in paths if isinstance(p, str)])

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tags/photo/{photo_path:path}")
async def legacy_get_tags_for_photo(photo_path: str):
    try:
        base_dir = _runtime_base_dir()
        tags_db = get_tags_db(base_dir / "tags.db")
        tags = tags_db.get_photo_tags(photo_path)
        return {"photo_path": photo_path, "tags": [{"name": t} for t in tags]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tags/photos/{tag_name}")
async def legacy_get_photos_for_tag(tag_name: str):
    try:
        base_dir = _runtime_base_dir()
        tags_db = get_tags_db(base_dir / "tags.db")
        paths = tags_db.get_tag_paths(tag_name)
        return {
            "tag": tag_name,
            "photos": [{"path": p} for p in paths],
            "count": len(paths),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tags/multi-filter")
async def legacy_multi_tag_filter(payload: dict[str, Any]):
    """A minimal multi-tag filter endpoint expected by tests.

    Payload shape (from tests): {photo_paths: [...], tags: [...], operator: 'AND'|'OR'}
    """
    try:
        base_dir = _runtime_base_dir()
        tags_db = get_tags_db(base_dir / "tags.db")

        tags = payload.get("tags") or []
        operator = str(payload.get("operator") or "OR").upper()

        tag_sets = []
        for t in tags:
            if not isinstance(t, str) or not t.strip():
                continue
            tag_sets.append(set(tags_db.get_tag_paths(t.strip())))

        if not tag_sets:
            paths = []
        elif operator == "AND":
            paths = sorted(set.intersection(*tag_sets))
        else:
            paths = sorted(set.union(*tag_sets))

        return {"photos": [{"path": p} for p in paths], "count": len(paths)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------
# People tags (legacy: /people/{path})
# Independent from face recognition clusters
# -------------------------------


@router.post("/people/{photo_path:path}")
async def legacy_people_tag(photo_path: str, payload: dict[str, Any]):
    try:
        base_dir = _runtime_base_dir()
        people_db = get_people_tags_db(base_dir / "people_tags.db")
        people = payload.get("people")
        if not isinstance(people, list):
            raise HTTPException(status_code=400, detail="people must be a list")
        people_db.add_people(photo_path, people)
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/people/{photo_path:path}")
async def legacy_people_get(photo_path: str):
    try:
        base_dir = _runtime_base_dir()
        people_db = get_people_tags_db(base_dir / "people_tags.db")
        names = people_db.get_people(photo_path)
        return {"photo_path": photo_path, "people": [{"name": n} for n in names]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------
# Locations (legacy: /locations/{path})
# Current APIs live under /locations/*; tests expect the simpler legacy shape.
# -------------------------------


@router.post("/locations/{photo_path:path}")
async def legacy_set_location(photo_path: str, payload: dict[str, Any]):
    try:
        base_dir = _runtime_base_dir()
        locations_db = get_locations_db(base_dir / "locations.db")

        lat = payload.get("latitude")
        lng = payload.get("longitude")
        if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
            raise HTTPException(
                status_code=400, detail="latitude and longitude are required"
            )

        location_id = locations_db.add_photo_location(
            photo_path=photo_path,
            latitude=float(lat),
            longitude=float(lng),
            original_place_name=payload.get("original_place_name"),
            corrected_place_name=payload.get("corrected_place_name"),
            country=payload.get("country"),
            region=payload.get("region"),
            city=payload.get("city"),
            accuracy=payload.get("accuracy"),
        )

        if not location_id:
            raise HTTPException(status_code=500, detail="Failed to add location")

        return {"success": True, "location_id": location_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------
# Smart collections (legacy: /smart-collections)
# Current API: /collections/smart
# -------------------------------


@router.post("/smart-collections")
async def legacy_create_smart_collection(payload: dict[str, Any]):
    try:
        base_dir = _runtime_base_dir()
        collections_db = get_smart_collections_db(base_dir / "collections.db")

        name = payload.get("name")
        if not isinstance(name, str) or not name.strip():
            raise HTTPException(status_code=400, detail="name is required")

        rule_definition = payload.get("rule_definition")
        if not isinstance(rule_definition, dict):
            raise HTTPException(
                status_code=400, detail="rule_definition must be an object"
            )

        description = payload.get("description")
        if description is None:
            description = ""
        if not isinstance(description, str):
            raise HTTPException(status_code=400, detail="description must be a string")

        collection_id = collections_db.create_smart_collection(
            name=name,
            description=description,
            rule_definition=rule_definition,
            auto_update=bool(payload.get("auto_update", True)),
            privacy_level=payload.get("privacy_level", "private"),
        )

        if not collection_id:
            raise HTTPException(
                status_code=400, detail="Collection name already exists"
            )

        return {"collection_id": collection_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/smart-collections/{collection_id}/photos")
async def legacy_get_collection_photos(collection_id: str):
    try:
        base_dir = _runtime_base_dir()
        collections_db = get_smart_collections_db(base_dir / "collections.db")
        photo_paths = collections_db.get_photos_for_collection(collection_id)
        return {"photos": photo_paths, "count": len(photo_paths)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
