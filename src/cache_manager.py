"""
Advanced Caching System for Photo Search Application

This module provides:
1. Multi-level caching (memory, disk)
2. Cache invalidation strategies
3. Performance monitoring for cache operations
4. Cache statistics and analytics
5. Integration with existing search operations
"""

import time
import json
import pickle
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from pathlib import Path
import sqlite3
import threading
from functools import wraps


class CacheEntry:
    """Represents a cached entry with metadata."""

    def __init__(self, key: str, value: Any, ttl_seconds: int = 3600):
        self.key = key
        self.value = value
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(seconds=ttl_seconds)
        self.access_count = 1
        self.last_accessed = self.created_at

    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return datetime.now() >= self.expires_at

    def is_valid(self) -> bool:
        """Check if the cache entry is still valid."""
        return not self.is_expired()

    def update_access(self):
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = datetime.now()


class MemoryCache:
    """In-memory cache implementation."""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if entry.is_valid():
                    entry.update_access()
                    return entry.value
                else:
                    # Remove expired entry
                    del self._cache[key]
            return None

    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        """Set a value in the cache."""
        with self._lock:
            # Check if we need to evict items
            if len(self._cache) >= self.max_size:
                # Simple eviction - remove oldest entry
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
                del self._cache[oldest_key]

            self._cache[key] = CacheEntry(key, value, ttl_seconds)
            return True

    def delete(self, key: str) -> bool:
        """Delete a key from the cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self):
        """Clear all entries from the cache."""
        with self._lock:
            self._cache.clear()

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            valid_entries = [entry for entry in self._cache.values() if entry.is_valid()]
            expired_entries = [entry for entry in self._cache.values() if entry.is_expired()]

            total_accesses = sum(entry.access_count for entry in self._cache.values())

            return {
                'total_entries': len(self._cache),
                'valid_entries': len(valid_entries),
                'expired_entries': len(expired_entries),
                'max_size': self.max_size,
                'total_accesses': total_accesses,
                'utilization_percent': (len(self._cache) / self.max_size) * 100 if self.max_size > 0 else 0
            }


class DiskCache:
    """Disk-based cache implementation using SQLite."""

    def __init__(self, db_path: str = "cache.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        """Initialize the cache database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Create cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                access_count INTEGER DEFAULT 1,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON cache(expires_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_last_accessed ON cache(last_accessed)")

        conn.commit()
        conn.close()

    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT value, access_count
                FROM cache
                WHERE key = ? AND expires_at > ?
            """, (key, datetime.now().isoformat()))

            row = cursor.fetchone()
            if row:
                # Update access count and last accessed time
                cursor.execute("""
                    UPDATE cache
                    SET access_count = access_count + 1,
                        last_accessed = ?
                    WHERE key = ?
                """, (datetime.now().isoformat(), key))

                conn.commit()

                # Deserialize the value
                try:
                    return pickle.loads(row['value'])
                except Exception:
                    return None
        finally:
            conn.close()

        return None

    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        """Set a value in the cache."""
        try:
            # Serialize the value
            serialized_value = pickle.dumps(value)
        except Exception:
            return False  # Cannot serialize the value

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            expires_at = (datetime.now() + timedelta(seconds=ttl_seconds)).isoformat()

            cursor.execute("""
                INSERT OR REPLACE INTO cache
                (key, value, expires_at)
                VALUES (?, ?, ?)
            """, (key, serialized_value, expires_at))

            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    def delete(self, key: str) -> bool:
        """Delete a key from the cache."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM cache WHERE key = ?", (key,))
        rows_affected = cursor.rowcount

        conn.commit()
        conn.close()

        return rows_affected > 0

    def clear(self):
        """Clear all entries from the cache."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM cache")
        conn.commit()
        conn.close()

    def cleanup_expired(self) -> int:
        """Remove expired entries and return count of removed entries."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM cache WHERE expires_at <= ?", (datetime.now().isoformat(),))
        removed_count = cursor.rowcount

        conn.commit()
        conn.close()

        return removed_count

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Count total entries
        cursor.execute("SELECT COUNT(*) as count FROM cache")
        total_entries = cursor.fetchone()['count']

        # Count expired entries
        cursor.execute("SELECT COUNT(*) as count FROM cache WHERE expires_at <= ?", (datetime.now().isoformat(),))
        expired_entries = cursor.fetchone()['count']

        # Count valid entries
        valid_entries = total_entries - expired_entries

        # Get total access count
        cursor.execute("SELECT SUM(access_count) as total FROM cache")
        result = cursor.fetchone()
        total_accesses = result['total'] or 0

        conn.close()

        return {
            'total_entries': total_entries,
            'valid_entries': valid_entries,
            'expired_entries': expired_entries,
            'total_accesses': total_accesses
        }


class CacheManager:
    """Main cache manager with performance monitoring."""

    def __init__(self, memory_size: int = 1000, disk_path: str = "cache.db"):
        self.memory_cache = MemoryCache(max_size=memory_size)
        self.disk_cache = DiskCache(db_path=disk_path)
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache with statistics tracking."""
        # First try memory cache
        value = self.memory_cache.get(key)
        if value is not None:
            with self._lock:
                self._stats['hits'] += 1
            return value

        # If not in memory, try disk cache
        value = self.disk_cache.get(key)
        if value is not None:
            # Promote to memory cache
            ttl_seconds = 3600  # Default TTL
            self.memory_cache.set(key, value, ttl_seconds)
            with self._lock:
                self._stats['hits'] += 1
            return value

        with self._lock:
            self._stats['misses'] += 1
        return None

    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        """Set a value in both cache levels with statistics tracking."""
        success = self.memory_cache.set(key, value, ttl_seconds) and \
                  self.disk_cache.set(key, value, ttl_seconds)

        if success:
            with self._lock:
                self._stats['sets'] += 1

        return success

    def delete(self, key: str) -> bool:
        """Delete a key from both cache levels with statistics tracking."""
        mem_success = self.memory_cache.delete(key)
        disk_success = self.disk_cache.delete(key)
        success = mem_success or disk_success

        if success:
            with self._lock:
                self._stats['deletes'] += 1

        return success

    def clear(self):
        """Clear all cache entries."""
        self.memory_cache.clear()
        self.disk_cache.clear()

        with self._lock:
            self._stats['hits'] = 0
            self._stats['misses'] = 0
            self._stats['sets'] = 0
            self._stats['deletes'] = 0

    def get_cache_key(self, *args, **kwargs) -> str:
        """Generate a cache key from function arguments."""
        # Create a string representation of args and kwargs
        key_str = f"{args}_{sorted(kwargs.items())}"
        # Hash it to create a consistent key
        return hashlib.md5(key_str.encode()).hexdigest()

    def cached_method(self, ttl_seconds: int = 3600):
        """Decorator to cache method results."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Create a key from the function name and arguments
                key_parts = [func.__name__] + list(args)
                key_str = "_".join(str(part) for part in key_parts) + str(sorted(kwargs.items()))
                key = hashlib.md5(key_str.encode()).hexdigest()

                # Try to get from cache
                cached_result = self.get(key)
                if cached_result is not None:
                    return cached_result

                # Execute the function and cache the result
                result = func(*args, **kwargs)
                self.set(key, result, ttl_seconds)

                return result
            return wrapper
        return decorator

    def stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        with self._lock:
            memory_stats = self.memory_cache.stats()
            disk_stats = self.disk_cache.stats()

            return {
                'memory': memory_stats,
                'disk': disk_stats,
                'operation_stats': dict(self._stats),
                'hit_rate': self._stats['hits'] / (self._stats['hits'] + self._stats['misses']) if (self._stats['hits'] + self._stats['misses']) > 0 else 0,
                'hit_count': self._stats['hits'],
                'miss_count': self._stats['misses']
            }

    def cleanup(self) -> int:
        """Clean up expired entries from disk cache."""
        removed_count = self.disk_cache.cleanup_expired()
        return removed_count


# Global cache instance
cache_manager = CacheManager()
