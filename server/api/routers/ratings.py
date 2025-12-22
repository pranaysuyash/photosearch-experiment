from fastapi import APIRouter, HTTPException

from server.config import settings
from server.models.schemas.ratings import RatingCreate
from server.ratings_db import get_ratings_db


router = APIRouter()


@router.get("/api/photos/{file_path:path}/rating")
async def get_photo_rating(file_path: str):
    """Get rating for a photo."""
    try:
        ratings_db = get_ratings_db(settings.BASE_DIR / "ratings.db")
        rating = ratings_db.get_rating(file_path)
        return {"rating": rating}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/photos/{file_path:path}/rating")
async def set_photo_rating(file_path: str, rating_req: RatingCreate):
    """Set rating for a photo (1-5 stars, 0 = unrated)."""
    try:
        if not (0 <= rating_req.rating <= 5):
            raise HTTPException(status_code=400, detail="Rating must be between 0 and 5")

        ratings_db = get_ratings_db(settings.BASE_DIR / "ratings.db")
        success = ratings_db.set_rating(file_path, rating_req.rating)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to set rating")

        return {"success": True, "rating": rating_req.rating}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/ratings/photos/{rating}")
async def get_photos_by_rating(rating: int, limit: int = 100, offset: int = 0):
    """Get photos with specific rating."""
    try:
        if not (1 <= rating <= 5):
            raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

        ratings_db = get_ratings_db(settings.BASE_DIR / "ratings.db")
        photo_paths = ratings_db.get_photos_by_rating(rating, limit, offset)

        from server import main as main_module

        # Get full metadata for each photo
        photos = []
        for path in photo_paths:
            metadata = main_module.photo_search_engine.db.get_metadata(path)
            if metadata:
                photos.append(
                    {
                        "path": path,
                        "metadata": metadata,
                        "rating": rating,
                    }
                )

        return {"count": len(photos), "results": photos}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/ratings/stats")
async def get_rating_stats():
    """Get rating statistics."""
    try:
        ratings_db = get_ratings_db(settings.BASE_DIR / "ratings.db")
        stats = ratings_db.get_rating_stats()
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
