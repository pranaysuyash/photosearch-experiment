"""
Face Crop Caching System

Provides persistent caching for face crop images to improve UI responsiveness.
Implements smart cache invalidation and size management.
"""

import os
import hashlib
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any
import json
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Metadata for a cached face crop."""

    face_id: str
    size: int
    file_path: str
    created_at: float
    last_accessed: float
    file_size_bytes: int
    source_photo_mtime: Optional[float] = None  # For invalidation


class FaceCropCache:
    """
    Persistent cache for face crop images.

    Features:
    - Size-based cache keys (different sizes cached separately)
    - LRU eviction when cache size limit exceeded
    - Automatic invalidation when source photos change
    - Cache statistics and monitoring
    """

    def __init__(self, cache_dir: Path, max_size_mb: int = 500, max_age_days: int = 30):
        """
        Initialize face crop cache.

        Args:
            cache_dir: Directory to store cached crops
            max_size_mb: Maximum cache size in MB
            max_age_days: Maximum age for cache entries
        """
        self.cache_dir = Path(cache_dir)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_age_seconds = max_age_days * 24 * 3600

        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Metadata file for cache entries
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        self.metadata: Dict[str, CacheEntry] = {}

        # Load existing metadata
        self._load_metadata()

        # Clean up on initialization
        self._cleanup_expired()

    def _get_cache_key(self, face_id: str, size: int) -> str:
        """Generate cache key for face crop."""
        return f"{face_id}_{size}"

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get file path for cached crop."""
        # Use first 2 chars of hash for subdirectory (better file system performance)
        hash_prefix = hashlib.md5(cache_key.encode()).hexdigest()[:2]
        subdir = self.cache_dir / hash_prefix
        subdir.mkdir(exist_ok=True)
        return subdir / f"{cache_key}.jpg"

    def _load_metadata(self) -> None:
        """Load cache metadata from disk."""
        if not self.metadata_file.exists():
            return

        try:
            with open(self.metadata_file, "r") as f:
                data = json.load(f)

            # Convert dict back to CacheEntry objects
            for key, entry_dict in data.items():
                self.metadata[key] = CacheEntry(**entry_dict)

        except Exception as e:
            logger.warning(f"Failed to load cache metadata: {e}")
            self.metadata = {}

    def _save_metadata(self) -> None:
        """Save cache metadata to disk."""
        try:
            # Convert CacheEntry objects to dicts
            data = {key: asdict(entry) for key, entry in self.metadata.items()}

            with open(self.metadata_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save cache metadata: {e}")

    def _cleanup_expired(self) -> None:
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = []

        for key, entry in self.metadata.items():
            # Check if entry is too old
            if current_time - entry.created_at > self.max_age_seconds:
                expired_keys.append(key)
                continue

            # Check if cached file still exists
            cache_path = Path(entry.file_path)
            if not cache_path.exists():
                expired_keys.append(key)
                continue

        # Remove expired entries
        for key in expired_keys:
            self._remove_cache_entry(key)

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

    def _remove_cache_entry(self, cache_key: str) -> None:
        """Remove a cache entry and its file."""
        if cache_key in self.metadata:
            entry = self.metadata[cache_key]

            # Remove file if it exists
            cache_path = Path(entry.file_path)
            if cache_path.exists():
                try:
                    cache_path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to remove cache file {cache_path}: {e}")

            # Remove from metadata
            del self.metadata[cache_key]

    def _enforce_size_limit(self) -> None:
        """Enforce cache size limit using LRU eviction."""
        # Calculate current cache size
        total_size = sum(entry.file_size_bytes for entry in self.metadata.values())

        if total_size <= self.max_size_bytes:
            return

        # Sort entries by last access time (LRU first)
        entries_by_access = sorted(self.metadata.items(), key=lambda x: x[1].last_accessed)

        # Remove entries until under size limit
        removed_count = 0
        for key, entry in entries_by_access:
            if total_size <= self.max_size_bytes:
                break

            total_size -= entry.file_size_bytes
            self._remove_cache_entry(key)
            removed_count += 1

        if removed_count > 0:
            logger.info(f"Evicted {removed_count} cache entries to enforce size limit")

    def get_cached_crop(self, face_id: str, size: int = 150) -> Optional[bytes]:
        """
        Get cached face crop if available.

        Args:
            face_id: Face detection ID
            size: Crop size in pixels

        Returns:
            Cached crop data or None if not cached
        """
        cache_key = self._get_cache_key(face_id, size)

        if cache_key not in self.metadata:
            return None

        entry = self.metadata[cache_key]
        cache_path = Path(entry.file_path)

        # Check if file exists
        if not cache_path.exists():
            self._remove_cache_entry(cache_key)
            return None

        try:
            # Update access time
            entry.last_accessed = time.time()

            # Read cached data
            with open(cache_path, "rb") as f:
                data = f.read()

            logger.debug(f"Cache hit for {face_id} size {size}")
            return data

        except Exception as e:
            logger.warning(f"Failed to read cache file {cache_path}: {e}")
            self._remove_cache_entry(cache_key)
            return None

    def cache_crop(
        self,
        face_id: str,
        crop_data: bytes,
        size: int = 150,
        source_photo_path: Optional[str] = None,
    ) -> bool:
        """
        Cache a face crop.

        Args:
            face_id: Face detection ID
            crop_data: JPEG crop data
            size: Crop size in pixels
            source_photo_path: Path to source photo (for invalidation)

        Returns:
            True if cached successfully
        """
        cache_key = self._get_cache_key(face_id, size)
        cache_path = self._get_cache_path(cache_key)

        try:
            # Write crop data to file
            with open(cache_path, "wb") as f:
                f.write(crop_data)

            # Get source photo modification time for invalidation
            source_mtime = None
            if source_photo_path and os.path.exists(source_photo_path):
                source_mtime = os.path.getmtime(source_photo_path)

            # Create cache entry
            current_time = time.time()
            entry = CacheEntry(
                face_id=face_id,
                size=size,
                file_path=str(cache_path),
                created_at=current_time,
                last_accessed=current_time,
                file_size_bytes=len(crop_data),
                source_photo_mtime=source_mtime,
            )

            # Remove existing entry if present
            if cache_key in self.metadata:
                self._remove_cache_entry(cache_key)

            # Add new entry
            self.metadata[cache_key] = entry

            # Enforce size limit
            self._enforce_size_limit()

            # Save metadata
            self._save_metadata()

            logger.debug(f"Cached crop for {face_id} size {size}")
            return True

        except Exception as e:
            logger.error(f"Failed to cache crop for {face_id}: {e}")
            return False

    def invalidate_face(self, face_id: str) -> None:
        """Invalidate all cached crops for a face."""
        keys_to_remove = [key for key, entry in self.metadata.items() if entry.face_id == face_id]

        for key in keys_to_remove:
            self._remove_cache_entry(key)

        if keys_to_remove:
            self._save_metadata()
            logger.debug(f"Invalidated {len(keys_to_remove)} cache entries for face {face_id}")

    def invalidate_by_source_photo(self, photo_path: str) -> None:
        """Invalidate cached crops when source photo changes."""
        if not os.path.exists(photo_path):
            return

        current_mtime = os.path.getmtime(photo_path)
        keys_to_remove = []

        for key, entry in self.metadata.items():
            if entry.source_photo_mtime is not None and entry.source_photo_mtime < current_mtime:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            self._remove_cache_entry(key)

        if keys_to_remove:
            self._save_metadata()
            logger.debug(f"Invalidated {len(keys_to_remove)} cache entries for updated photo {photo_path}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_size = sum(entry.file_size_bytes for entry in self.metadata.values())
        total_files = len(self.metadata)

        # Calculate hit rate (would need to track misses for accurate rate)
        return {
            "total_entries": total_files,
            "total_size_mb": total_size / (1024 * 1024),
            "max_size_mb": self.max_size_bytes / (1024 * 1024),
            "utilization_percent": (total_size / self.max_size_bytes) * 100,
            "cache_dir": str(self.cache_dir),
            "oldest_entry": min((entry.created_at for entry in self.metadata.values()), default=None),
            "newest_entry": max((entry.created_at for entry in self.metadata.values()), default=None),
        }

    def clear_cache(self) -> None:
        """Clear all cached crops."""
        keys_to_remove = list(self.metadata.keys())

        for key in keys_to_remove:
            self._remove_cache_entry(key)

        self._save_metadata()
        logger.info(f"Cleared {len(keys_to_remove)} cache entries")


# Global cache instance
_global_cache: Optional[FaceCropCache] = None


def get_global_cache() -> FaceCropCache:
    """Get the global face crop cache instance."""
    global _global_cache
    if _global_cache is None:
        cache_dir = Path("cache/face_crops")
        _global_cache = FaceCropCache(cache_dir)
    return _global_cache


def reset_global_cache(cache_dir: Optional[Path] = None, **kwargs) -> None:
    """Reset the global cache (useful for testing or reconfiguration)."""
    global _global_cache
    if cache_dir is None:
        cache_dir = Path("cache/face_crops")
    _global_cache = FaceCropCache(cache_dir, **kwargs)
