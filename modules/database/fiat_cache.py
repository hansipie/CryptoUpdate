"""File-based cache manager for fiat currency API data.

This module provides a persistent caching system for MarketRaccoon API responses
to reduce redundant network calls. The cache uses JSON storage with atomic writes,
automatic corruption recovery, and TTL-based expiration.
"""

import json
import logging
import os
import shutil
import tempfile
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class FiatCacheManager:
    """File-based cache manager for fiat currency exchange rate data.

    Features:
    - TTL-based expiration (default: 1 hour)
    - Atomic file writes to prevent corruption
    - Automatic recovery from corrupted cache files
    - LRU eviction when cache grows too large
    - Fallback to expired cache when API fails

    Attributes:
        cache_file (str): Path to JSON cache file
        ttl_seconds (int): Time-to-live for cache entries in seconds
        max_entries (int): Maximum number of cache entries before LRU eviction
    """

    # Maximum number of entries before LRU eviction
    MAX_CACHE_ENTRIES = 100

    def __init__(self, cache_file: str, ttl_seconds: int = 3600):
        """Initialize cache manager.

        Args:
            cache_file: Path to JSON cache file (will be created if doesn't exist)
            ttl_seconds: Time-to-live for cache entries in seconds (default: 3600 = 1 hour)
        """
        self.cache_file = cache_file
        self.ttl_seconds = ttl_seconds
        self.max_entries = self.MAX_CACHE_ENTRIES

        # Ensure cache directory exists
        cache_dir = os.path.dirname(cache_file)
        if cache_dir and not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)
            logger.info(f"Created cache directory: {cache_dir}")

    def get(self, key: str) -> Optional[dict]:
        """Get cached value if it exists and is not expired.

        Args:
            key: Cache key

        Returns:
            Cached data dict if found and not expired, None otherwise
        """
        cache_data = self._load_cache()

        if key not in cache_data:
            logger.debug(f"Cache MISS for key: {key} (not found)")
            return None

        entry = cache_data[key]
        current_time = int(time.time())

        if current_time >= entry["expiry"]:
            logger.debug(f"Cache MISS for key: {key} (expired)")
            return None

        logger.debug(f"Cache HIT for key: {key}")
        return entry["data"]

    def set(self, key: str, value: dict, ttl_override: Optional[int] = None):
        """Set cache value with optional TTL override.

        Args:
            key: Cache key
            value: Data to cache (must be JSON-serializable dict)
            ttl_override: Optional TTL in seconds, overrides default
        """
        cache_data = self._load_cache()

        current_time = int(time.time())
        ttl = ttl_override if ttl_override is not None else self.ttl_seconds

        cache_data[key] = {
            "timestamp": current_time,
            "expiry": current_time + ttl,
            "data": value,
        }

        logger.debug(f"Cache SET for key: {key} (TTL: {ttl}s)")

        # Cleanup expired entries before saving
        cache_data = self._cleanup_expired_entries(cache_data)

        # LRU eviction if cache too large
        if len(cache_data) > self.max_entries:
            cache_data = self._evict_oldest(cache_data)

        self._save_cache(cache_data)

    def is_expired(self, key: str) -> bool:
        """Check if cache entry exists and is expired.

        Args:
            key: Cache key

        Returns:
            True if entry exists and is expired, False otherwise
        """
        cache_data = self._load_cache()

        if key not in cache_data:
            return False

        current_time = int(time.time())
        return current_time >= cache_data[key]["expiry"]

    def get_or_fetch(
        self,
        key: str,
        fetch_func: Callable[[], Optional[dict]],
        allow_expired_fallback: bool = True,
    ) -> Optional[dict]:
        """Get from cache or fetch from source with fallback to expired cache.

        This is the main method for cache-aware data retrieval. It implements
        the following strategy:
        1. Try to get fresh data from cache (within TTL)
        2. If cache miss, try to fetch from source
        3. If fetch fails and allow_expired_fallback=True, use expired cache

        Args:
            key: Cache key
            fetch_func: Callable that fetches fresh data (should return dict or None)
            allow_expired_fallback: If True, use expired cache when fetch fails

        Returns:
            Cached or fetched data, or None if all strategies fail
        """
        # Strategy 1: Try fresh cache
        cached = self.get(key)
        if cached is not None:
            logger.debug(f"Using fresh cache for key: {key}")
            return cached

        # Strategy 2: Try to fetch fresh data
        try:
            logger.debug(f"Cache miss for key: {key}, fetching from source")
            fresh_data = fetch_func()

            if fresh_data is not None:
                self.set(key, fresh_data)
                logger.info(f"Fetched and cached fresh data for key: {key}")
                return fresh_data
            else:
                logger.warning(f"Fetch returned None for key: {key}")
        except Exception as e:
            logger.error(f"Failed to fetch data for key {key}: {e}")

        # Strategy 3: Fallback to expired cache if allowed
        if allow_expired_fallback:
            expired_data = self._get_expired(key)
            if expired_data is not None:
                logger.warning(
                    f"Using EXPIRED cache for key: {key} due to fetch failure"
                )
                return expired_data

        logger.error(f"All strategies failed for key: {key}")
        return None

    def cleanup_expired(self):
        """Remove all expired entries from cache file.

        This can be called periodically to keep cache file small.
        """
        cache_data = self._load_cache()
        original_size = len(cache_data)

        cache_data = self._cleanup_expired_entries(cache_data)
        cleaned_count = original_size - len(cache_data)

        if cleaned_count > 0:
            self._save_cache(cache_data)
            logger.info(f"Cleaned {cleaned_count} expired entries from cache")
        else:
            logger.debug("No expired entries to clean")

    def _get_expired(self, key: str) -> Optional[dict]:
        """Get cache entry even if expired (for fallback).

        Args:
            key: Cache key

        Returns:
            Cached data even if expired, or None if not found
        """
        cache_data = self._load_cache()

        if key not in cache_data:
            return None

        return cache_data[key]["data"]

    def _load_cache(self) -> dict:
        """Load cache from file with corruption recovery.

        Returns:
            Cache data dict, or empty dict if file doesn't exist or is corrupted
        """
        if not os.path.exists(self.cache_file):
            logger.debug(f"Cache file does not exist: {self.cache_file}")
            return {}

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            logger.debug(f"Loaded cache with {len(cache_data)} entries")
            return cache_data
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Cache file corrupted: {e}, resetting cache")

            # Backup corrupted file for debugging
            timestamp = int(time.time())
            backup_file = f"{self.cache_file}.corrupted.{timestamp}"
            try:
                shutil.copy(self.cache_file, backup_file)
                logger.info(f"Corrupted cache backed up to: {backup_file}")
            except Exception as backup_error:
                logger.error(f"Failed to backup corrupted cache: {backup_error}")

            return {}

    def _save_cache(self, cache_data: dict):
        """Save cache to file with atomic write.

        Uses atomic write (temp file + rename) to prevent corruption
        from partial writes or crashes during save.

        Args:
            cache_data: Cache data dict to save
        """
        cache_dir = os.path.dirname(self.cache_file)

        # Create temp file in same directory for atomic rename
        try:
            temp_fd, temp_path = tempfile.mkstemp(
                dir=cache_dir, prefix=".cache_tmp_", suffix=".json"
            )

            # Write to temp file
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)

            # Atomic rename (OS-level atomic operation)
            shutil.move(temp_path, self.cache_file)
            logger.debug(f"Saved cache with {len(cache_data)} entries")

        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
            # Cleanup temp file if it exists
            if "temp_path" in locals() and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
            raise

    def _cleanup_expired_entries(self, cache_data: dict) -> dict:
        """Remove expired entries from cache data dict.

        Args:
            cache_data: Cache data dict

        Returns:
            Cleaned cache data dict without expired entries
        """
        current_time = int(time.time())

        cleaned = {
            key: value
            for key, value in cache_data.items()
            if current_time < value["expiry"]
        }

        removed_count = len(cache_data) - len(cleaned)
        if removed_count > 0:
            logger.debug(f"Cleaned {removed_count} expired entries")

        return cleaned

    def _evict_oldest(self, cache_data: dict) -> dict:
        """Evict oldest entries using LRU strategy.

        Args:
            cache_data: Cache data dict

        Returns:
            Cache data dict with oldest entries removed to fit max_entries
        """
        if len(cache_data) <= self.max_entries:
            return cache_data

        # Sort by timestamp (oldest first)
        sorted_items = sorted(cache_data.items(), key=lambda item: item[1]["timestamp"])

        # Keep only the newest max_entries
        evict_count = len(cache_data) - self.max_entries
        kept_items = sorted_items[evict_count:]

        logger.warning(f"Evicted {evict_count} oldest entries (LRU)")

        return dict(kept_items)
