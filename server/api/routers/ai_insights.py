from typing import List

from fastapi import APIRouter, Body, HTTPException

from server.ai_insights_db import get_ai_insights_db
from server.config import settings
from server.models.schemas.ai_insights import AIInsightCreateRequest, AIInsightUpdateRequest


router = APIRouter()


@router.post("/ai/insights")
async def create_ai_insight(request: AIInsightCreateRequest):
    """Create a new AI-generated insight for a photo."""
    try:
        insights_db = get_ai_insights_db(settings.BASE_DIR / "insights.db")

        insight_id = insights_db.add_insight(
            photo_path=request.photo_path,
            insight_type=request.insight_type,
            insight_data=request.insight_data,
            confidence=request.confidence,
        )

        if not insight_id:
            raise HTTPException(status_code=400, detail="Failed to create insight")

        return {"success": True, "insight_id": insight_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai/insights/photo/{photo_path:path}")
async def get_insights_for_photo(photo_path: str):
    """Get all AI insights for a specific photo."""
    try:
        insights_db = get_ai_insights_db(settings.BASE_DIR / "insights.db")
        insights = insights_db.get_insights_for_photo(photo_path)
        return {"insights": insights, "count": len(insights)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai/insights/type/{insight_type}")
async def get_insights_by_type(insight_type: str, limit: int = 50):
    """Get AI insights of a specific type."""
    try:
        insights_db = get_ai_insights_db(settings.BASE_DIR / "insights.db")
        insights = insights_db.get_insights_by_type(insight_type, limit)
        return {"insights": insights, "count": len(insights)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai/insights")
async def get_all_insights(limit: int = 100, offset: int = 0):
    """Get all AI insights with pagination."""
    try:
        insights_db = get_ai_insights_db(settings.BASE_DIR / "insights.db")
        insights = insights_db.get_all_insights(limit, offset)
        return {"insights": insights, "count": len(insights)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/ai/insights/{insight_id}")
async def update_insight_applied_status(insight_id: str, request: AIInsightUpdateRequest):
    """Update the applied status of an insight."""
    try:
        insights_db = get_ai_insights_db(settings.BASE_DIR / "insights.db")

        if request.is_applied is None:
            raise HTTPException(status_code=400, detail="is_applied status must be provided")

        success = insights_db.mark_insight_applied(insight_id, request.is_applied)

        if not success:
            raise HTTPException(status_code=404, detail="Insight not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/ai/insights/{insight_id}")
async def delete_insight(insight_id: str):
    """Delete an AI insight."""
    try:
        insights_db = get_ai_insights_db(settings.BASE_DIR / "insights.db")
        success = insights_db.delete_insight(insight_id)

        if not success:
            raise HTTPException(status_code=404, detail="Insight not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai/insights/stats")
async def get_insights_stats():
    """Get statistics about AI insights."""
    try:
        insights_db = get_ai_insights_db(settings.BASE_DIR / "insights.db")
        stats = insights_db.get_insights_stats()
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/analytics/patterns")
async def analyze_photographer_patterns(photo_paths: List[str] = Body(...)):
    """Analyze photographer patterns across multiple photos."""
    try:
        insights_db = get_ai_insights_db(settings.BASE_DIR / "insights.db")
        patterns = insights_db.get_photographer_patterns(photo_paths)
        return {"patterns": patterns}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
