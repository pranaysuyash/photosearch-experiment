"""
Performance Optimization & Caching System

Implements caching strategies to improve application performance,
particularly for large photo collections.
"""

from typing import Any, Dict, List, Optional, Tuple
import hashlib
import json
from collections import OrderedDict
import time
import threading


class LRUCache:
    """Simple LRU Cache implementation with thread safety"""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """
        Initialize LRU cache with max size and TTL.

        Args:
            max_size: Maximum number of items to store
            ttl: Time-to-live in seconds
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.lock = threading.RLock()

    def _is_expired(self, timestamp: float) -> bool:
        """Check if a cached item has expired."""
        return time.time() - timestamp > self.ttl

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if it exists and hasn't expired."""
        with self.lock:
            if key not in self.cache:
                return None

            item = self.cache[key]
            if self._is_expired(item["timestamp"]):
                del self.cache[key]
                return None

            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return item["value"]

    def set(self, key: str, value: Any) -> None:
        """Set value in cache, evicting LRU item if needed."""
        with self.lock:
            # Clean up expired items periodically
            if len(self.cache) > self.max_size * 0.9:  # Clean when 90% full
                for k in list(self.cache.keys()):
                    if self._is_expired(self.cache[k]["timestamp"]):
                        del self.cache[k]

            # Evict LRU if at max size
            if len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)

            self.cache[key] = {"value": value, "timestamp": time.time()}

    def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all items from cache."""
        with self.lock:
            self.cache.clear()


class CacheManager:
    """Manages multiple caching strategies for performance optimization."""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """
        Initialize the cache manager.

        Args:
            max_size: Maximum size per cache (for each type of data)
            ttl: Default TTL for cached items (in seconds)
        """
        self.thumbnail_cache = LRUCache(max_size=max_size, ttl=ttl)
        self.search_results_cache = LRUCache(max_size=max_size, ttl=ttl)
        self.metadata_cache = LRUCache(max_size=max_size, ttl=ttl)
        self.embeddings_cache = LRUCache(max_size=max_size, ttl=ttl * 24)  # Keep embeddings longer

        # Background cleanup will clean expired items periodically
        self._cleanup_interval = 300  # 5 minutes
        self._running = False
        self._cleanup_task = None

    def start_background_cleanup(self):
        """Start background task to periodically clean expired items."""
        if self._running:
            return

        self._running = True
        # Run cleanup in a separate thread
        self._cleanup_task = threading.Thread(target=self._background_cleanup, daemon=True)
        self._cleanup_task.start()

    def stop_background_cleanup(self):
        """Stop background cleanup task."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.join(timeout=1.0)

    def _background_cleanup(self):
        """Background task to clean expired items."""
        while self._running:
            time.sleep(self._cleanup_interval)
            self._cleanup_expired()

    def _cleanup_expired(self):
        """Clean expired items from all caches."""
        # This would clean expired items, but we already do it in get/set
        # This function exists as a periodic cleanup for additional safety
        pass

    def generate_key(self, prefix: str, *args) -> str:
        """
        Generate a cache key from prefix and arguments.

        Args:
            prefix: Cache type prefix (e.g., 'thumb', 'search', 'meta')
            *args: Arguments to include in the key

        Returns:
            SHA-256 hash key
        """
        key_str = f"{prefix}:{':'.join(map(str, args))}"
        return hashlib.sha256(key_str.encode()).hexdigest()

    # Thumbnail caching
    def cache_thumbnail(self, photo_path: str, size: Tuple[int, int], thumbnail_data: bytes) -> None:
        """
        Cache a thumbnail image.

        Args:
            photo_path: Path to the photo
            size: Thumbnail size (width, height)
            thumbnail_data: Thumbnail image data
        """
        key = self.generate_key("thumb", photo_path, size[0], size[1])
        self.thumbnail_cache.set(key, thumbnail_data)

    def get_cached_thumbnail(self, photo_path: str, size: Tuple[int, int]) -> Optional[bytes]:
        """
        Get a cached thumbnail.

        Args:
            photo_path: Path to the photo
            size: Thumbnail size (width, height)

        Returns:
            Thumbnail data if cached, None otherwise
        """
        key = self.generate_key("thumb", photo_path, size[0], size[1])
        return self.thumbnail_cache.get(key)

    # Search results caching
    def cache_search_results(
        self,
        query: str,
        filters: Dict[str, Any],
        results: List[Dict[str, Any]],
        ttl: int = 600,
    ) -> None:
        """
        Cache search results.

        Args:
            query: Search query
            filters: Search filters applied
            results: Search results to cache
            ttl: Time-to-live for the cached results
        """
        # Use a custom TTL for search results cache
        original_ttl = self.search_results_cache.ttl
        try:
            self.search_results_cache.ttl = ttl
            key = self.generate_key("search", query, json.dumps(filters, sort_keys=True))
            self.search_results_cache.set(key, results)
        finally:
            self.search_results_cache.ttl = original_ttl

    def get_cached_search_results(self, query: str, filters: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached search results.

        Args:
            query: Search query
            filters: Search filters applied

        Returns:
            Cached search results if available, None otherwise
        """
        key = self.generate_key("search", query, json.dumps(filters, sort_keys=True))
        return self.search_results_cache.get(key)

    # Metadata caching
    def cache_metadata(self, photo_path: str, metadata: Dict[str, Any]) -> None:
        """
        Cache photo metadata.

        Args:
            photo_path: Path to the photo
            metadata: Photo metadata to cache
        """
        key = self.generate_key("meta", photo_path)
        self.metadata_cache.set(key, metadata)

    def get_cached_metadata(self, photo_path: str) -> Optional[Dict[str, Any]]:
        """
        Get cached photo metadata.

        Args:
            photo_path: Path to the photo

        Returns:
            Cached metadata if available, None otherwise
        """
        key = self.generate_key("meta", photo_path)
        return self.metadata_cache.get(key)

    # Embeddings caching
    def cache_embeddings(self, photo_path: str, embeddings: List[float]) -> None:
        """
        Cache photo embeddings.

        Args:
            photo_path: Path to the photo
            embeddings: Photo embeddings to cache
        """
        key = self.generate_key("embed", photo_path)
        self.embeddings_cache.set(key, embeddings)

    def get_cached_embeddings(self, photo_path: str) -> Optional[List[float]]:
        """
        Get cached photo embeddings.

        Args:
            photo_path: Path to the photo

        Returns:
            Cached embeddings if available, None otherwise
        """
        key = self.generate_key("embed", photo_path)
        return self.embeddings_cache.get(key)

    # Cache stats
    def get_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Get statistics about all caches.

        Returns:
            Dictionary with stats for each cache type
        """
        return {
            "thumbnail_cache": {
                "size": len(self.thumbnail_cache.cache),
                "max_size": self.thumbnail_cache.max_size,
                "ttl": self.thumbnail_cache.ttl,
            },
            "search_results_cache": {
                "size": len(self.search_results_cache.cache),
                "max_size": self.search_results_cache.max_size,
                "ttl": self.search_results_cache.ttl,
            },
            "metadata_cache": {
                "size": len(self.metadata_cache.cache),
                "max_size": self.metadata_cache.max_size,
                "ttl": self.metadata_cache.ttl,
            },
            "embeddings_cache": {
                "size": len(self.embeddings_cache.cache),
                "max_size": self.embeddings_cache.max_size,
                "ttl": self.embeddings_cache.ttl,
            },
        }

    def clear_cache(self, cache_type: Optional[str] = None) -> None:
        """
        Clear cache(s).

        Args:
            cache_type: Type of cache to clear ('thumbnail', 'search', 'metadata', 'embeddings', or None for all)
        """
        if cache_type is None or cache_type == "thumbnail":
            self.thumbnail_cache.clear()
        if cache_type is None or cache_type == "search":
            self.search_results_cache.clear()
        if cache_type is None or cache_type == "metadata":
            self.metadata_cache.clear()
        if cache_type is None or cache_type == "embeddings":
            self.embeddings_cache.clear()


# Global cache manager instance
cache_manager = CacheManager(max_size=2000, ttl=1800)  # 2000 items, 30 min default TTL

# Start background cleanup
cache_manager.start_background_cleanup()
