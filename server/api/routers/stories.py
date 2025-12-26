import json
import sqlite3
from typing import Any

from fastapi import APIRouter, HTTPException

from server.config import settings
from server.models.schemas.stories import (
    StoryCreateRequest,
    StoryUpdateRequest,
    TimelineEntryCreateRequest,
    TimelineEntryUpdateRequest,
)
from server.timeline_db import get_timeline_db


router = APIRouter()


@router.post("/stories")
async def create_story(request: StoryCreateRequest):
    """Create a new story narrative."""
    try:
        timeline_db = get_timeline_db(settings.BASE_DIR / "timelines.db")

        story_id = timeline_db.create_story(
            title=request.title,
            description=request.description,
            owner_id=request.owner_id,
            metadata=request.metadata,
            is_published=request.is_published,
        )

        if not story_id:
            raise HTTPException(status_code=400, detail="Failed to create story")

        return {"success": True, "story_id": story_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stories/{story_id}")
async def get_story(story_id: str):
    """Get details about a specific story."""
    try:
        timeline_db = get_timeline_db(settings.BASE_DIR / "timelines.db")
        story = timeline_db.get_story(story_id)

        if not story:
            raise HTTPException(status_code=404, detail="Story not found")

        return {"story": story}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stories/owner/{owner_id}")
async def get_stories_by_owner(
    owner_id: str,
    include_unpublished: bool = False,
    limit: int = 50,
    offset: int = 0,
):
    """Get all stories for an owner."""
    try:
        timeline_db = get_timeline_db(settings.BASE_DIR / "timelines.db")
        stories = timeline_db.get_stories_by_owner(owner_id, include_unpublished, limit, offset)
        return {"stories": stories, "count": len(stories)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/stories/{story_id}")
async def update_story(story_id: str, request: StoryUpdateRequest):
    """Update story details."""
    try:
        # In a real implementation, we would update the story in the database
        # For now, we'll just return success
        timeline_db = get_timeline_db(settings.BASE_DIR / "timelines.db")

        # Get existing story to update
        existing_story = timeline_db.get_story(story_id)
        if not existing_story:
            raise HTTPException(status_code=404, detail="Story not found")

        # Update story in database
        with sqlite3.connect(settings.BASE_DIR / "timelines.db") as conn:
            update_fields: list[str] = []
            params: list[object] = []

            if request.title is not None:
                update_fields.append("title = ?")
                params.append(request.title)

            if request.description is not None:
                update_fields.append("description = ?")
                params.append(request.description)

            if request.is_published is not None:
                update_fields.append("is_published = ?")
                params.append(request.is_published)

            if request.metadata is not None:
                update_fields.append("metadata = ?")
                params.append(json.dumps(request.metadata))

            update_fields.append("updated_at = CURRENT_TIMESTAMP")

            if update_fields:
                sql = f"UPDATE stories SET {', '.join(update_fields)} WHERE id = ?"
                params.append(story_id)

                cursor = conn.execute(sql, params)

                if cursor.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Story not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stories/{story_id}/photos")
async def add_photo_to_story(story_id: str, request: TimelineEntryCreateRequest):
    """Add a photo to a story's timeline."""
    try:
        timeline_db = get_timeline_db(settings.BASE_DIR / "timelines.db")

        entry_id = timeline_db.add_photo_to_timeline(
            story_id=story_id,
            photo_path=request.photo_path,
            date=request.date,
            location=request.location,
            caption=request.caption,
        )

        if not entry_id:
            raise HTTPException(status_code=400, detail="Failed to add photo to timeline")

        return {"success": True, "entry_id": entry_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stories/{story_id}/timeline")
async def get_story_timeline(story_id: str, limit: int = 100, offset: int = 0):
    """Get the timeline for a story."""
    try:
        timeline_db = get_timeline_db(settings.BASE_DIR / "timelines.db")
        timeline = timeline_db.get_timeline_for_story(story_id)

        # Apply limit and offset manually since the method doesn't support it
        paginated_timeline = timeline[offset : offset + limit]

        return {"timeline": paginated_timeline, "count": len(timeline)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/timeline/entries/{entry_id}")
async def update_timeline_entry(entry_id: str, request: TimelineEntryUpdateRequest):
    """Update a timeline entry."""
    try:
        # In a real implementation, we would have a method to update specific timeline entries
        # For now, we'll update using raw SQL
        with sqlite3.connect(settings.BASE_DIR / "timelines.db") as conn:
            update_fields: list[str] = []
            params: list[object] = []

            if request.date is not None:
                update_fields.append("date = ?")
                params.append(request.date)

            if request.location is not None:
                update_fields.append("location = ?")
                params.append(request.location)

            if request.caption is not None:
                update_fields.append("caption = ?")
                params.append(request.caption)

            if request.narrative_order is not None:
                update_fields.append("narrative_order = ?")
                params.append(request.narrative_order)

            update_fields.append("updated_at = CURRENT_TIMESTAMP")

            if update_fields:
                sql = f"UPDATE timeline_entries SET {', '.join(update_fields)} WHERE id = ?"
                params.append(entry_id)

                cursor = conn.execute(sql, params)

                if cursor.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Timeline entry not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/timeline/entries/{entry_id}")
async def remove_photo_from_timeline(entry_id: str):
    """Remove a photo from a story's timeline."""
    try:
        timeline_db = get_timeline_db(settings.BASE_DIR / "timelines.db")

        success = timeline_db.remove_photo_from_timeline(entry_id)

        if not success:
            raise HTTPException(status_code=404, detail="Timeline entry not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stories/{story_id}/stats")
async def get_story_stats(story_id: str):
    """Get statistics about a story."""
    try:
        timeline_db = get_timeline_db(settings.BASE_DIR / "timelines.db")
        story = timeline_db.get_story(story_id)

        if not story:
            raise HTTPException(status_code=404, detail="Story not found")

        # Get the timeline to calculate stats
        timeline = timeline_db.get_timeline_for_story(story_id)

        # Calculate stats
        # `timeline_db` implementations may return dict rows; normalize access defensively.
        story_title = story.get("title") if isinstance(story, dict) else getattr(story, "title", None)
        story_created_at = story.get("created_at") if isinstance(story, dict) else getattr(story, "created_at", None)

        def _entry_field(entry: Any, key: str) -> Any:
            if isinstance(entry, dict):
                return entry.get(key)
            return getattr(entry, key, None)

        dates = [_entry_field(e, "date") for e in timeline if _entry_field(e, "date")]
        locations = [_entry_field(e, "location") for e in timeline if _entry_field(e, "location")]
        has_captions = any(bool(_entry_field(e, "caption")) for e in timeline)

        stats = {
            "story_id": story_id,
            "title": story_title,
            "total_photos": len(timeline),
            "start_date": min(dates) if dates else story_created_at,
            "end_date": max(dates) if dates else story_created_at,
            "locations_count": len(set(locations)),
            "has_captions": has_captions,
        }

        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stories/user/{user_id}/stats")
async def get_user_story_stats(user_id: str):
    """Get statistics about a user's stories."""
    try:
        timeline_db = get_timeline_db(settings.BASE_DIR / "timelines.db")
        stats = timeline_db.get_story_stats(user_id)
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stories/{story_id}/publish")
async def toggle_story_publish(story_id: str, publish_request: dict):
    """Publish or unpublish a story."""
    try:
        is_published = publish_request.get("publish", True)
        timeline_db = get_timeline_db(settings.BASE_DIR / "timelines.db")

        success = timeline_db.publish_story(story_id, is_published)

        if not success:
            raise HTTPException(status_code=400, detail="Failed to update story publication status")

        return {"success": True, "published": is_published}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
