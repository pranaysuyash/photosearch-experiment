"""
Locations Database Module

Provides functionality for location correction, geocoding, and place clustering with SQLite backend.
"""

import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any


class LocationRecord:
    id: str
    photo_path: str
    latitude: float
    longitude: float
    original_place_name: Optional[str]
    corrected_place_name: Optional[str]
    country: Optional[str]
    region: Optional[str]
    city: Optional[str]
    accuracy: float  # GPS accuracy in meters
    created_at: str
    updated_at: str


class LocationsDB:
    """Database interface for location data and place correction"""

    def __init__(self, db_path: Path):
        """
        Initialize the locations database.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize tables
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS photo_locations (
                    id TEXT PRIMARY KEY,
                    photo_path TEXT NOT NULL UNIQUE,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    original_place_name TEXT,
                    corrected_place_name TEXT,
                    country TEXT,
                    region TEXT,
                    city TEXT,
                    accuracy REAL DEFAULT 100.0,  -- GPS accuracy in meters
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_coords ON photo_locations(latitude, longitude)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_place_name ON photo_locations(corrected_place_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_photo_path ON photo_locations(photo_path)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_country ON photo_locations(country)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_region ON photo_locations(region)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_city ON photo_locations(city)")

    def add_photo_location(
        self,
        photo_path: str,
        latitude: float,
        longitude: float,
        original_place_name: Optional[str] = None,
        corrected_place_name: Optional[str] = None,
        country: Optional[str] = None,
        region: Optional[str] = None,
        city: Optional[str] = None,
        accuracy: float = 100.0,
    ) -> str:
        """
        Add or update location information for a photo.

        Args:
            photo_path: Path to the photo
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            original_place_name: Original place name from GPS/EXIF
            corrected_place_name: Corrected human-readable place name
            country: Country name
            region: Region name
            city: City name
            accuracy: GPS accuracy in meters

        Returns:
            ID of the location record
        """
        import uuid

        location_id = str(uuid.uuid4())

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO photo_locations
                    (id, photo_path, latitude, longitude, original_place_name, corrected_place_name, country, region, city, accuracy)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(photo_path) DO UPDATE SET
                        latitude = excluded.latitude,
                        longitude = excluded.longitude,
                        original_place_name = excluded.original_place_name,
                        corrected_place_name = excluded.corrected_place_name,
                        country = excluded.country,
                        region = excluded.region,
                        city = excluded.city,
                        accuracy = excluded.accuracy,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        location_id,
                        photo_path,
                        latitude,
                        longitude,
                        original_place_name,
                        corrected_place_name,
                        country,
                        region,
                        city,
                        accuracy,
                    ),
                )
                return location_id
        except Exception as e:
            print(f"Error adding photo location: {e}")
            return ""

    def get_photo_location(self, photo_path: str) -> Optional[Dict[str, Any]]:
        """
        Get location information for a specific photo.

        Args:
            photo_path: Path to the photo

        Returns:
            Location record if found, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                result = conn.execute("SELECT * FROM photo_locations WHERE photo_path = ?", (photo_path,)).fetchone()
                return dict(result) if result else None
        except Exception:
            return None

    def update_place_name(self, photo_path: str, corrected_place_name: str) -> bool:
        """
        Update the corrected place name for a photo.

        Args:
            photo_path: Path to the photo
            corrected_place_name: New corrected place name

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    UPDATE photo_locations
                    SET corrected_place_name = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE photo_path = ?
                    """,
                    (corrected_place_name, photo_path),
                )
                return cursor.rowcount > 0
        except Exception:
            return False

    def get_photos_by_place(self, place_name: str) -> List[Dict[str, Any]]:
        """
        Get all photos associated with a specific place name.

        Args:
            place_name: Place name to search for

        Returns:
            List of photo records associated with the place
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT * FROM photo_locations
                    WHERE corrected_place_name LIKE ? OR original_place_name LIKE ?
                    ORDER BY created_at DESC
                    """,
                    (f"%{place_name}%", f"%{place_name}%"),
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception:
            return []

    def get_nearby_locations(self, latitude: float, longitude: float, radius_km: float = 1.0) -> List[Dict[str, Any]]:
        """
        Get photos within a certain radius of a location.

        Args:
            latitude: Latitude of center point
            longitude: Longitude of center point
            radius_km: Radius in kilometers

        Returns:
            List of nearby photo locations
        """
        try:
            # Use Haversine formula to find locations within radius
            # This is a simplified version using Euclidean approximation for small distances
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT *,
                           (6371 * acos(cos(radians(?)) * cos(radians(latitude)) *
                           cos(radians(longitude) - radians(?)) +
                           sin(radians(?)) * sin(radians(latitude)))) AS distance
                    FROM photo_locations
                    WHERE (6371 * acos(cos(radians(?)) * cos(radians(latitude)) *
                           cos(radians(longitude) - radians(?)) +
                           sin(radians(?)) * sin(radians(latitude)))) <= ?
                    ORDER BY distance
                    """,
                    (
                        latitude,
                        longitude,
                        latitude,
                        latitude,
                        longitude,
                        latitude,
                        radius_km,
                    ),
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception:
            return []

    def get_place_clusters(self, min_photos: int = 2) -> List[Dict[str, Any]]:
        """
        Get clusters of photos by location (places with multiple photos).

        Args:
            min_photos: Minimum number of photos to form a cluster

        Returns:
            List of place clusters with location and photo count
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                # Group by corrected place name first, then by geocoded city/region
                cursor = conn.execute(
                    """
                    SELECT
                        corrected_place_name,
                        city,
                        region,
                        country,
                        COUNT(*) as photo_count,
                        AVG(latitude) as avg_latitude,
                        AVG(longitude) as avg_longitude,
                        MIN(latitude) as min_latitude,
                        MAX(latitude) as max_latitude,
                        MIN(longitude) as min_longitude,
                        MAX(longitude) as max_longitude
                    FROM photo_locations
                    GROUP BY COALESCE(corrected_place_name, city, region, country)
                    HAVING COUNT(*) >= ?
                    ORDER BY photo_count DESC
                    """,
                    (min_photos,),
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception:
            return []

    def get_location_stats(self) -> Dict[str, int]:
        """
        Get statistics about location data.

        Returns:
            Dictionary with location statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute("SELECT COUNT(*) as total FROM photo_locations").fetchone()
                total_locations = result["total"] if result else 0

                result = conn.execute(
                    "SELECT COUNT(DISTINCT city) as unique_cities FROM photo_locations WHERE city IS NOT NULL"
                ).fetchone()
                unique_cities = result["unique_cities"] if result else 0

                result = conn.execute(
                    "SELECT COUNT(DISTINCT region) as unique_regions FROM photo_locations WHERE region IS NOT NULL"
                ).fetchone()
                unique_regions = result["unique_regions"] if result else 0

                result = conn.execute(
                    "SELECT COUNT(DISTINCT country) as unique_countries FROM photo_locations WHERE country IS NOT NULL"
                ).fetchone()
                unique_countries = result["unique_countries"] if result else 0

                return {
                    "total_locations": total_locations,
                    "unique_cities": unique_cities,
                    "unique_regions": unique_regions,
                    "unique_countries": unique_countries,
                }
        except Exception:
            return {
                "total_locations": 0,
                "unique_cities": 0,
                "unique_regions": 0,
                "unique_countries": 0,
            }


def get_locations_db(db_path: Path) -> LocationsDB:
    """Get locations database instance."""
    return LocationsDB(db_path)
