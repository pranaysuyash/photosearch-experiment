"""
Place Correction and Location Clustering

Provides functionality for correcting location names, clustering nearby locations,
and managing place associations in photos.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
import uuid
from dataclasses import dataclass
import math


@dataclass
class LocationCluster:
    id: str
    center_lat: float
    center_lng: float
    name: str
    description: str
    photo_count: int
    min_lat: float
    max_lat: float
    min_lng: float
    max_lng: float
    created_at: str
    updated_at: str


@dataclass
class PhotoLocation:
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


class LocationClustersDB:
    """Database interface for location clustering and correction"""

    def __init__(self, db_path: Path):
        """
        Initialize the location clustering database.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize tables
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS photo_locations (
                    photo_path TEXT PRIMARY KEY,
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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS location_clusters (
                    id TEXT PRIMARY KEY,
                    center_lat REAL NOT NULL,
                    center_lng REAL NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    photo_count INTEGER DEFAULT 0,
                    min_lat REAL NOT NULL,
                    max_lat REAL NOT NULL,
                    min_lng REAL NOT NULL,
                    max_lng REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cluster_photos (
                    cluster_id TEXT NOT NULL,
                    photo_path TEXT NOT NULL,
                    distance_to_center REAL,  -- Distance in meters from cluster center
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (cluster_id, photo_path),
                    FOREIGN KEY (cluster_id) REFERENCES location_clusters(id),
                    FOREIGN KEY (photo_path) REFERENCES photo_locations(photo_path)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_coords ON photo_locations(latitude, longitude)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_corrected_place ON photo_locations(corrected_place_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_photo_path ON photo_locations(photo_path)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_center_coords ON location_clusters(center_lat, center_lng)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_name ON location_clusters(name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_photo_count ON location_clusters(photo_count)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cluster_id ON cluster_photos(cluster_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cluster_photo_path ON cluster_photos(photo_path)")

    def add_photo_location(self, 
                          photo_path: str,
                          latitude: float, 
                          longitude: float,
                          original_place_name: Optional[str] = None,
                          corrected_place_name: Optional[str] = None,
                          country: Optional[str] = None,
                          region: Optional[str] = None,
                          city: Optional[str] = None,
                          accuracy: float = 100.0) -> bool:
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
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO photo_locations 
                    (photo_path, latitude, longitude, original_place_name, corrected_place_name, country, region, city, accuracy)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (photo_path, latitude, longitude, original_place_name, corrected_place_name, country, region, city, accuracy)
                )
                
                # Update cluster associations if the photo is near a known cluster
                self._update_cluster_associations(conn, photo_path, latitude, longitude)
                
                return True
        except sqlite3.Error:
            return False

    def get_photo_location(self, photo_path: str) -> Optional[PhotoLocation]:
        """
        Get location information for a specific photo.
        
        Args:
            photo_path: Path to the photo
            
        Returns:
            PhotoLocation if found, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                result = conn.execute(
                    "SELECT * FROM photo_locations WHERE photo_path = ?",
                    (photo_path,)
                ).fetchone()
                
                if result:
                    return PhotoLocation(
                        photo_path=result['photo_path'],
                        latitude=result['latitude'],
                        longitude=result['longitude'],
                        original_place_name=result['original_place_name'],
                        corrected_place_name=result['corrected_place_name'],
                        country=result['country'],
                        region=result['region'],
                        city=result['city'],
                        accuracy=result['accuracy'],
                        created_at=result['created_at'],
                        updated_at=result['updated_at']
                    )
                return None
        except Exception:
            return None

    def get_photos_by_location(self, 
                              latitude: float, 
                              longitude: float, 
                              radius_km: float = 1.0) -> List[PhotoLocation]:
        """
        Get photos within a certain radius of a location.
        
        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_km: Radius in kilometers
            
        Returns:
            List of photos within the specified radius
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Calculate bounds using a simplified approach
                lat_delta = radius_km / 111.0  # Rough conversion: 1 deg latitude ~ 111 km
                lng_delta = radius_km / (111.0 * abs(math.cos(math.radians(latitude))))  # Adjust for longitude
                
                cursor = conn.execute(
                    """
                    SELECT * FROM photo_locations 
                    WHERE latitude BETWEEN ? AND ? 
                    AND longitude BETWEEN ? AND ?
                    """,
                    (latitude - lat_delta, latitude + lat_delta, 
                     longitude - lng_delta, longitude + lng_delta)
                )
                rows = cursor.fetchall()
                
                # Filter by actual distance
                photos = []
                for row in rows:
                    dist = self._calculate_distance(
                        latitude, longitude, 
                        row['latitude'], row['longitude']
                    )
                    if dist <= radius_km * 1000:  # Convert km to meters
                        photos.append(PhotoLocation(
                            photo_path=row['photo_path'],
                            latitude=row['latitude'],
                            longitude=row['longitude'],
                            original_place_name=row['original_place_name'],
                            corrected_place_name=row['corrected_place_name'],
                            country=row['country'],
                            region=row['region'],
                            city=row['city'],
                            accuracy=row['accuracy'],
                            created_at=row['created_at'],
                            updated_at=row['updated_at']
                        ))
                
                return photos
        except Exception:
            return []

    def update_place_name(self, 
                         photo_path: str, 
                         corrected_place_name: Optional[str] = None,
                         country: Optional[str] = None,
                         region: Optional[str] = None,
                         city: Optional[str] = None) -> bool:
        """
        Update the corrected place name for a photo.
        
        Args:
            photo_path: Path to the photo
            corrected_place_name: New corrected place name
            country: New country
            region: New region
            city: New city
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                update_fields = []
                params = []
                
                if corrected_place_name is not None:
                    update_fields.append("corrected_place_name = ?")
                    params.append(corrected_place_name)
                    
                if country is not None:
                    update_fields.append("country = ?")
                    params.append(country)
                    
                if region is not None:
                    update_fields.append("region = ?")
                    params.append(region)
                    
                if city is not None:
                    update_fields.append("city = ?")
                    params.append(city)
                
                if update_fields:
                    update_fields.append("updated_at = CURRENT_TIMESTAMP")
                    params.append(photo_path)
                    
                    sql = f"UPDATE photo_locations SET {', '.join(update_fields)} WHERE photo_path = ?"
                    
                    cursor = conn.execute(sql, params)
                    return cursor.rowcount > 0
                
                return True  # Nothing to update, but operation is successful
        except sqlite3.Error:
            return False

    def get_photos_by_place(self, place_name: str) -> List[PhotoLocation]:
        """
        Get all photos associated with a specific place name.
        
        Args:
            place_name: Place name to search for
            
        Returns:
            List of photos with the specified place name
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT * FROM photo_locations 
                    WHERE corrected_place_name LIKE ? OR original_place_name LIKE ?
                    """,
                    (f'%{place_name}%', f'%{place_name}%')
                )
                rows = cursor.fetchall()
                
                return [PhotoLocation(
                    photo_path=row['photo_path'],
                    latitude=row['latitude'],
                    longitude=row['longitude'],
                    original_place_name=row['original_place_name'],
                    corrected_place_name=row['corrected_place_name'],
                    country=row['country'],
                    region=row['region'],
                    city=row['city'],
                    accuracy=row['accuracy'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                ) for row in rows]
        except Exception:
            return []

    def cluster_locations(self, min_photos: int = 2, max_distance_meters: float = 100.0) -> List[LocationCluster]:
        """
        Cluster nearby locations into named places.
        
        Args:
            min_photos: Minimum number of photos to form a cluster
            max_distance_meters: Maximum distance between photos to be considered part of same cluster
            
        Returns:
            List of location clusters
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT photo_path, latitude, longitude FROM photo_locations"
                )
                all_locations = cursor.fetchall()
                
                # Group locations that are near each other
                clusters = []
                processed = set()
                
                for location in all_locations:
                    if location['photo_path'] in processed:
                        continue
                    
                    # Find nearby locations
                    nearby = []
                    for other_loc in all_locations:
                        if other_loc['photo_path'] in processed:
                            continue
                            
                        dist = self._calculate_distance(
                            location['latitude'], location['longitude'],
                            other_loc['latitude'], other_loc['longitude']
                        )
                        
                        if dist <= max_distance_meters:
                            nearby.append(other_loc)
                    
                    # Only create cluster if we have enough photos
                    if len(nearby) >= min_photos:
                        # Calculate cluster center
                        center_lat = sum(loc['latitude'] for loc in nearby) / len(nearby)
                        center_lng = sum(loc['longitude'] for loc in nearby) / len(nearby)
                        
                        # Calculate bounding box
                        min_lat = min(loc['latitude'] for loc in nearby)
                        max_lat = max(loc['latitude'] for loc in nearby)
                        min_lng = min(loc['longitude'] for loc in nearby)
                        max_lng = max(loc['longitude'] for loc in nearby)
                        
                        cluster_id = str(uuid.uuid4())
                        
                        # Create cluster entry
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO location_clusters
                            (id, center_lat, center_lng, name, description, photo_count, min_lat, max_lat, min_lng, max_lng)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                cluster_id, center_lat, center_lng,
                                self._generate_cluster_name(center_lat, center_lng, nearby[:5]),
                                f"Cluster of {len(nearby)} photos",
                                len(nearby), min_lat, max_lat, min_lng, max_lng
                            )
                        )
                        
                        # Create cluster-photo associations
                        for loc in nearby:
                            conn.execute(
                                """
                                INSERT OR REPLACE INTO cluster_photos
                                (cluster_id, photo_path, distance_to_center)
                                VALUES (?, ?, ?)
                                """,
                                (
                                    cluster_id,
                                    loc['photo_path'],
                                    self._calculate_distance(
                                        center_lat, center_lng,
                                        loc['latitude'], loc['longitude']
                                    )
                                )
                            )
                            processed.add(loc['photo_path'])
                        
                        clusters.append(LocationCluster(
                            id=cluster_id,
                            center_lat=center_lat,
                            center_lng=center_lng,
                            name=self._generate_cluster_name(center_lat, center_lng, nearby[:5]),
                            description=f"Cluster of {len(nearby)} photos",
                            photo_count=len(nearby),
                            min_lat=min_lat,
                            max_lat=max_lat,
                            min_lng=min_lng,
                            max_lng=max_lng,
                            created_at=datetime.now().isoformat(),
                            updated_at=datetime.now().isoformat()
                        ))
                    else:
                        # Mark unclustered photos as processed
                        for loc in nearby:
                            processed.add(loc['photo_path'])
                
                return clusters
        except Exception as e:
            print(f"Error clustering locations: {e}")
            return []

    def get_location_clusters(self, min_photos: int = 2) -> List[LocationCluster]:
        """
        Get existing location clusters.
        
        Args:
            min_photos: Minimum number of photos in a cluster to return
            
        Returns:
            List of location clusters
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT * FROM location_clusters 
                    WHERE photo_count >= ?
                    ORDER BY photo_count DESC
                    """,
                    (min_photos,)
                )
                rows = cursor.fetchall()
                
                return [LocationCluster(
                    id=row['id'],
                    center_lat=row['center_lat'],
                    center_lng=row['center_lng'],
                    name=row['name'],
                    description=row['description'],
                    photo_count=row['photo_count'],
                    min_lat=row['min_lat'],
                    max_lat=row['max_lat'],
                    min_lng=row['min_lng'],
                    max_lng=row['max_lng'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                ) for row in rows]
        except Exception:
            return []

    def get_photos_in_cluster(self, cluster_id: str) -> List[PhotoLocation]:
        """
        Get all photos in a specific cluster.
        
        Args:
            cluster_id: ID of the cluster
            
        Returns:
            List of photos in the cluster
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT pl.* FROM photo_locations pl
                    JOIN cluster_photos cp ON pl.photo_path = cp.photo_path
                    WHERE cp.cluster_id = ?
                    ORDER BY cp.distance_to_center ASC
                    """,
                    (cluster_id,)
                )
                rows = cursor.fetchall()
                
                return [PhotoLocation(
                    photo_path=row['photo_path'],
                    latitude=row['latitude'],
                    longitude=row['longitude'],
                    original_place_name=row['original_place_name'],
                    corrected_place_name=row['corrected_place_name'],
                    country=row['country'],
                    region=row['region'],
                    city=row['city'],
                    accuracy=row['accuracy'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                ) for row in rows]
        except Exception:
            return []

    def get_photo_cluster(self, photo_path: str) -> Optional[LocationCluster]:
        """
        Get the cluster a photo belongs to.
        
        Args:
            photo_path: Path to the photo
            
        Returns:
            LocationCluster if the photo is in a cluster, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT lc.* FROM location_clusters lc
                    JOIN cluster_photos cp ON lc.id = cp.cluster_id
                    WHERE cp.photo_path = ?
                    """,
                    (photo_path,)
                )
                row = cursor.fetchone()
                
                if row:
                    return LocationCluster(
                        id=row['id'],
                        center_lat=row['center_lat'],
                        center_lng=row['center_lng'],
                        name=row['name'],
                        description=row['description'],
                        photo_count=row['photo_count'],
                        min_lat=row['min_lat'],
                        max_lat=row['max_lat'],
                        min_lng=row['min_lng'],
                        max_lng=row['max_lng'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at']
                    )
                return None
        except Exception:
            return None

    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate distance between two points in meters using Haversine formula.
        
        Args:
            lat1, lng1: Coordinates of first point
            lat2, lng2: Coordinates of second point
            
        Returns:
            Distance in meters
        """
        R = 6371000  # Earth's radius in meters
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c

    def _update_cluster_associations(self, conn: sqlite3.Connection, photo_path: str, lat: float, lng: float):
        """Update cluster associations for a new photo."""
        # Find existing clusters this photo should belong to
        cursor = conn.execute(
            """
            SELECT id, center_lat, center_lng FROM location_clusters
            WHERE ? BETWEEN min_lat AND max_lat
            AND ? BETWEEN min_lng AND max_lng
            """,
            (lat, lng)
        )
        
        for row in cursor.fetchall():
            cluster_id = row['id']
            center_lat = row['center_lat']
            center_lng = row['center_lng']
            
            # Check if this photo is actually close enough to the cluster center
            distance = self._calculate_distance(lat, lng, center_lat, center_lng)
            
            # If within max distance, add to cluster
            if distance <= 100.0:  # Within 100m of cluster center
                conn.execute(
                    """
                    INSERT OR REPLACE INTO cluster_photos
                    (cluster_id, photo_path, distance_to_center)
                    VALUES (?, ?, ?)
                    """,
                    (cluster_id, photo_path, distance)
                )
                
                # Update photo count in cluster
                conn.execute(
                    """
                    UPDATE location_clusters 
                    SET photo_count = (
                        SELECT COUNT(*) FROM cluster_photos WHERE cluster_id = ?
                    ), updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (cluster_id, cluster_id)
                )

    def _generate_cluster_name(self, center_lat: float, center_lng: float, sample_photos: List[sqlite3.Row]) -> str:
        """Generate a name for a location cluster based on common place names in the cluster."""
        # Get place names from sample photos
        place_names = [p['corrected_place_name'] or p['original_place_name'] for p in sample_photos if p]
        place_names = [name for name in place_names if name]  # Remove None values
        
        # If we have common place names, use one
        if place_names:
            from collections import Counter
            name_counts = Counter(place_names)
            most_common = name_counts.most_common(1)
            if most_common:
                return most_common[0][0]
        
        # If no place names, use coordinates
        return f"Location ({center_lat:.4f}, {center_lng:.4f})"

    def get_location_stats(self) -> Dict[str, Any]:
        """
        Get statistics about location data.
        
        Returns:
            Dictionary with location statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Total photos with location data
                total_with_location = conn.execute(
                    "SELECT COUNT(*) FROM photo_locations"
                ).fetchone()[0]
                
                # Total clusters
                total_clusters = conn.execute(
                    "SELECT COUNT(*) FROM location_clusters"
                ).fetchone()[0]
                
                # Photos without corrected names
                without_correction = conn.execute(
                    "SELECT COUNT(*) FROM photo_locations WHERE corrected_place_name IS NULL OR corrected_place_name = ''"
                ).fetchone()[0]
                
                # Top locations
                top_locations = conn.execute(
                    """
                    SELECT corrected_place_name, COUNT(*) as count
                    FROM photo_locations 
                    WHERE corrected_place_name IS NOT NULL AND corrected_place_name != ''
                    GROUP BY corrected_place_name
                    ORDER BY count DESC
                    LIMIT 10
                    """
                ).fetchall()
                
                return {
                    'total_with_location': total_with_location,
                    'total_clusters': total_clusters,
                    'without_correction': without_correction,
                    'with_correction': total_with_location - without_correction,
                    'top_locations': [{'name': row[0], 'count': row[1]} for row in top_locations]
                }
        except Exception:
            return {
                'total_with_location': 0,
                'total_clusters': 0,
                'without_correction': 0,
                'with_correction': 0,
                'top_locations': []
            }

    def correct_place_name_bulk(self, photo_paths: List[str], corrected_name: str) -> bool:
        """
        Bulk correct the place name for multiple photos.
        
        Args:
            photo_paths: List of photo paths to update
            corrected_name: Corrected place name to apply to all
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                for path in photo_paths:
                    conn.execute(
                        """
                        UPDATE photo_locations 
                        SET corrected_place_name = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE photo_path = ?
                        """,
                        (corrected_name, path)
                    )
                return True
        except Exception:
            return False


def get_location_clusters_db(db_path: Path) -> LocationClustersDB:
    """Get location clusters database instance."""
    return LocationClustersDB(db_path)
