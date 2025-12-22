from typing import List

from fastapi import APIRouter, HTTPException, Depends

from server.pricing import PricingTier, UsageStats, pricing_manager
from server.api.deps import get_state
from server.core.state import AppState


router = APIRouter()


@router.get("/pricing", response_model=List[PricingTier])
async def get_pricing_tiers():
    """
    Get all available pricing tiers.
    """
    return pricing_manager.get_all_tiers()


@router.get("/pricing/{tier_name}", response_model=PricingTier)
async def get_pricing_tier(tier_name: str):
    """
    Get details for a specific pricing tier.
    """
    tier = pricing_manager.get_tier(tier_name)
    if not tier:
        raise HTTPException(status_code=404, detail="Pricing tier not found")
    return tier


@router.get("/pricing/recommend", response_model=PricingTier)
async def recommend_pricing_tier(image_count: int):
    """
    Recommend a pricing tier based on image count.
    """
    if image_count < 0:
        raise HTTPException(status_code=400, detail="Image count must be positive")

    return pricing_manager.get_tier_by_image_count(image_count)


@router.get("/usage/{user_id}", response_model=UsageStats)
async def get_usage_stats(user_id: str, state: AppState = Depends(get_state)):
    """
    Get current usage statistics for a user.
    """

    # Get current image count from database
    try:
        cursor = state.photo_search_engine.db.conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM metadata")
        result = cursor.fetchone()
        image_count = result["count"] if result else 0
    except Exception as e:
        print(f"Error getting image count: {e}")
        image_count = 0

    # Track usage and return stats
    return pricing_manager.track_usage(user_id, image_count)


@router.get("/usage/check/{user_id}")
async def check_usage_limit(user_id: str, additional_images: int = 0):
    """
    Check if user can add more images without exceeding their limit.
    """
    if additional_images < 0:
        raise HTTPException(status_code=400, detail="Additional images must be positive")

    can_add = pricing_manager.check_limit(user_id, additional_images)

    return {
        "can_add": can_add,
        "message": "User can add images" if can_add else "User would exceed their image limit",
    }


@router.post("/usage/upgrade/{user_id}")
async def upgrade_user_tier(user_id: str, new_tier: str):
    """
    Upgrade a user to a new pricing tier.
    """
    success = pricing_manager.upgrade_tier(user_id, new_tier)

    if not success:
        raise HTTPException(status_code=400, detail="Invalid tier or user not found")

    return {
        "success": True,
        "message": f"User {user_id} upgraded to {new_tier} tier",
        "new_tier": new_tier,
    }


@router.get("/usage/history/{user_id}")
async def get_user_usage_history(user_id: str, days: int = 30):
    """
    Get usage history for a specific user.

    Args:
        user_id: ID of the user
        days: Number of days to retrieve history for (default: 30)

    Returns:
        List of usage records
    """
    try:
        history = pricing_manager.get_usage_history(user_id, days)
        return {
            "user_id": user_id,
            "days": days,
            "history": history,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/usage/growth/{user_id}")
async def get_user_growth_rate(user_id: str, days: int = 30):
    """
    Get user growth rate over time.

    Args:
        user_id: ID of the user
        days: Number of days to calculate growth over (default: 30)

    Returns:
        Growth rate statistics
    """
    try:
        growth = pricing_manager.get_user_growth_rate(user_id, days)
        return growth
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/usage/tier-averages")
async def get_tier_usage_averages():
    """
    Get average usage statistics per pricing tier.

    Returns:
        Dictionary with average usage per tier
    """
    try:
        averages = pricing_manager.get_tier_averages()
        return averages
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/usage/company-analytics")
async def get_company_usage_analytics():
    """
    Get comprehensive usage analytics for the company.

    Returns:
        Company-wide usage statistics
    """
    try:
        analytics = pricing_manager.get_company_usage_analytics()
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
