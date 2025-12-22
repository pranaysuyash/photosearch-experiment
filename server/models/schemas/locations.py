from typing import Optional

from pydantic import BaseModel


class LocationCreateRequest(BaseModel):
    photo_path: str
    latitude: float
    longitude: float
    original_place_name: Optional[str] = None
    corrected_place_name: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    accuracy: float = 100.0


class LocationUpdateRequest(BaseModel):
    corrected_place_name: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None


class LocationCorrectionRequest(BaseModel):
    original_place_name: Optional[str] = None
    corrected_place_name: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None


class LocationClusterCreateRequest(BaseModel):
    name: str
    center_lat: float
    center_lng: float
    description: Optional[str] = None
    min_photos: int = 2
