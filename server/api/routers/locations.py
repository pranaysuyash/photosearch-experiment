from fastapi import APIRouter, HTTPException, Query

from server.config import settings
from server.location_clusters_db import get_location_clusters_db
from server.locations_db import get_locations_db
from server.models.schemas.locations import (
    LocationCorrectionRequest,
    LocationCreateRequest,
    LocationUpdateRequest,
)


router = APIRouter()


@router.post("/locations-legacy")
async def add_photo_location_legacy(request: LocationCreateRequest):
    """Add or update location information for a photo."""
    try:
        locations_db = get_locations_db(settings.BASE_DIR / "locations.db")

        normalized_path = "/" + request.photo_path.lstrip("/")

        location_id = locations_db.add_photo_location(
            photo_path=normalized_path,
            latitude=request.latitude,
            longitude=request.longitude,
            original_place_name=request.original_place_name,
            corrected_place_name=request.corrected_place_name,
            country=request.country,
            region=request.region,
            city=request.city,
            accuracy=request.accuracy,
        )

        return {"success": True, "location_id": location_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/locations-legacy/photo/{photo_path:path}")
async def get_photo_location_legacy(photo_path: str):
    """Get location information for a specific photo."""
    try:
        locations_db = get_locations_db(settings.BASE_DIR / "locations.db")
        normalized_path = "/" + photo_path.lstrip("/")
        location = locations_db.get_photo_location(normalized_path)

        if not location:
            raise HTTPException(status_code=404, detail="Location not found for photo")

        return {"location": location}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/locations-legacy/photo/{photo_path:path}")
async def update_photo_location_legacy(photo_path: str, request: LocationUpdateRequest):
    """Update location information for a photo."""
    try:
        locations_db = get_locations_db(settings.BASE_DIR / "locations.db")
        normalized_path = "/" + photo_path.lstrip("/")

        if request.corrected_place_name:
            success = locations_db.update_place_name(normalized_path, request.corrected_place_name)
        else:
            success = True  # Skip update if no corrected name provided

        if not success:
            raise HTTPException(status_code=404, detail="Photo location not found")

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/locations/places/{place_name}")
async def get_photos_by_place(place_name: str):
    """Get all photos associated with a specific place name."""
    try:
        locations_db = get_locations_db(settings.BASE_DIR / "locations.db")
        photos = locations_db.get_photos_by_place(place_name)
        return {"place_name": place_name, "photos": photos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/locations/nearby")
async def get_nearby_locations(
    latitude: float,
    longitude: float,
    radius_km: float = Query(1.0, ge=0.1, le=50.0),  # Between 0.1 and 50 km
):
    """Get photos within a certain radius of a location."""
    try:
        locations_db = get_locations_db(settings.BASE_DIR / "locations.db")
        nearby = locations_db.get_nearby_locations(latitude, longitude, radius_km)
        return {"center": {"lat": latitude, "lng": longitude}, "radius_km": radius_km, "photos": nearby}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/locations/clusters")
async def get_place_clusters(min_photos: int = Query(2, ge=1)):
    """Get clusters of photos by location."""
    try:
        locations_db = get_locations_db(settings.BASE_DIR / "locations.db")
        clusters = locations_db.get_place_clusters(min_photos)
        return {"clusters": clusters}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/locations-legacy/stats")
async def get_location_stats_legacy():
    """Get statistics about location data."""
    try:
        locations_db = get_locations_db(settings.BASE_DIR / "locations.db")
        stats = locations_db.get_location_stats()
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/locations/correct/{photo_path:path}")
async def correct_photo_location(photo_path: str, request: LocationCorrectionRequest):
    """Correct location information for a photo."""
    try:
        locations_db = get_location_clusters_db(settings.BASE_DIR / "locations.db")

        success = locations_db.update_place_name(
            photo_path=photo_path,
            corrected_place_name=request.corrected_place_name,
            country=request.country,
            region=request.region,
            city=request.city,
        )

        if not success:
            raise HTTPException(status_code=404, detail="Photo location not found")

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/locations/photo/{photo_path:path}")
async def get_photo_location(photo_path: str):
    """Get location information for a specific photo."""
    try:
        locations_db = get_location_clusters_db(settings.BASE_DIR / "locations.db")
        location = locations_db.get_photo_location(photo_path)

        if not location:
            raise HTTPException(status_code=404, detail="Location not found for photo")

        return {"location": location}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/locations/nearby")
async def get_photos_near_location(
    latitude: float,
    longitude: float,
    radius_km: float = Query(1.0, ge=0.1, le=50.0),
):
    """Get photos within a certain radius of a location."""
    try:
        locations_db = get_location_clusters_db(settings.BASE_DIR / "locations.db")
        photos = locations_db.get_photos_by_location(latitude, longitude, radius_km)

        return {
            "photos": photos,
            "count": len(photos),
            "center": {"lat": latitude, "lng": longitude},
            "radius_km": radius_km,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/locations/clusters")
async def get_location_clusters(min_photos: int = Query(2, ge=1)):
    """Get all location clusters."""
    try:
        locations_db = get_location_clusters_db(settings.BASE_DIR / "locations.db")
        clusters = locations_db.get_location_clusters(min_photos)

        return {
            "clusters": clusters,
            "count": len(clusters),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/locations/clusters/{cluster_id}/photos")
async def get_photos_in_cluster(cluster_id: str, limit: int = 50, offset: int = 0):
    """Get all photos in a specific cluster."""
    try:
        locations_db = get_location_clusters_db(settings.BASE_DIR / "locations.db")
        photos = locations_db.get_photos_in_cluster(cluster_id)

        return {
            "photos": photos[offset : offset + limit],
            "count": len(photos),
            "total_in_cluster": len(photos),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/locations/photo/{photo_path:path}/cluster")
async def get_photo_cluster(photo_path: str):
    """Get the cluster a photo belongs to."""
    try:
        locations_db = get_location_clusters_db(settings.BASE_DIR / "locations.db")
        cluster = locations_db.get_photo_cluster(photo_path)

        if not cluster:
            return {"cluster": None}

        return {"cluster": cluster}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/locations/clusterize")
async def create_location_clusters(
    min_photos: int = Query(2, ge=1),
    max_distance_meters: float = Query(100.0, ge=10.0, le=1000.0),
):
    """Create location clusters based on proximity of photos."""
    try:
        locations_db = get_location_clusters_db(settings.BASE_DIR / "locations.db")
        clusters = locations_db.cluster_locations(min_photos, max_distance_meters)

        return {
            "clusters": clusters,
            "count": len(clusters),
            "params": {
                "min_photos": min_photos,
                "max_distance_meters": max_distance_meters,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/locations/stats")
async def get_location_stats():
    """Get statistics about location data."""
    try:
        locations_db = get_location_clusters_db(settings.BASE_DIR / "locations.db")
        stats = locations_db.get_location_stats()

        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/locations/correct-bulk")
async def bulk_correct_place_names(payload: dict):
    """Bulk correct place names for multiple photos."""
    try:
        photo_paths = payload.get("photo_paths", [])
        corrected_name = payload.get("corrected_name", "")

        if not photo_paths or not corrected_name:
            raise HTTPException(status_code=400, detail="photo_paths and corrected_name are required")

        locations_db = get_location_clusters_db(settings.BASE_DIR / "locations.db")
        success = locations_db.correct_place_name_bulk(photo_paths, corrected_name)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update place names")

        return {"success": True, "updated_count": len(photo_paths)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
