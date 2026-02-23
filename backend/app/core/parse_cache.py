"""
Redis-based cache for URL parsing results.
Reduces repeated requests to the same URLs and persists across restarts.
"""

import json
import logging
import hashlib
from typing import Optional, Dict, Any
from datetime import timedelta

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger("wishshare.parse_cache")

# Default TTL: 24 hours (in seconds)
DEFAULT_TTL = 24 * 60 * 60


class ParseCache:
    """Redis-based cache for product parsing results with TTL support."""

    def __init__(self, redis_dsn: str = None, default_ttl: int = DEFAULT_TTL):
        self._redis_dsn = redis_dsn or settings.redis_dsn
        self._default_ttl = default_ttl
        self._redis: Optional[redis.Redis] = None
        self._hits = 0
        self._misses = 0

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            try:
                self._redis = redis.from_url(
                    self._redis_dsn,
                    encoding="utf-8",
                    decode_responses=True
                )
                # Test connection
                await self._redis.ping()
                logger.info("ParseCache: Connected to Redis at %s", self._redis_dsn)
            except Exception as e:
                logger.warning("ParseCache: Failed to connect to Redis: %s. Cache will be disabled.", e)
                self._redis = None
        return self._redis

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for consistent caching."""
        import re
        # Remove trailing slashes
        url = url.rstrip("/")
        # Remove common tracking parameters
        tracking_params = ["utm_source", "utm_medium", "utm_campaign", "utm_term", 
                          "utm_content", "at", "__rr", "_openstat", "from", "ref"]
        for param in tracking_params:
            url = re.sub(rf"[?&]{param}=[^&]*", "", url)
        # Clean up leading ? or & after param removal
        url = re.sub(r"[?&]$", "", url)
        url = re.sub(r"\?&", "?", url)
        return url

    def _get_key(self, url: str) -> str:
        """Generate Redis cache key from URL."""
        normalized = self._normalize_url(url)
        url_hash = hashlib.md5(normalized.encode()).hexdigest()
        return f"parse:{url_hash}"

    async def get(self, url: str) -> Optional[Dict[str, Any]]:
        """Get cached result if exists and not expired."""
        try:
            client = await self._get_redis()
            if client is None:
                self._misses += 1
                return None

            key = self._get_key(url)
            data = await client.get(key)

            if data is None:
                self._misses += 1
                logger.debug("ParseCache: MISS for %s (key: %s)", url[:50], key)
                return None

            self._hits += 1
            logger.info("ParseCache: HIT for %s (key: %s)", url[:50], key)
            return json.loads(data)

        except Exception as e:
            logger.warning("ParseCache: Error getting cached data for %s: %s", url[:50], e)
            self._misses += 1
            return None

    async def set(self, url: str, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Cache result with optional custom TTL."""
        try:
            client = await self._get_redis()
            if client is None:
                return False

            key = self._get_key(url)
            ttl_value = ttl or self._default_ttl

            # Add timestamp for debugging
            data_to_store = {
                **data,
                "_cached_at": int(__import__("time").time())
            }

            await client.setex(
                key,
                timedelta(seconds=ttl_value),
                json.dumps(data_to_store, ensure_ascii=False)
            )
            logger.info(
                "ParseCache: Cached result for %s (key: %s, TTL: %ds)",
                url[:50], key, ttl_value
            )
            return True

        except Exception as e:
            logger.warning("ParseCache: Error caching data for %s: %s", url[:50], e)
            return False

    async def delete(self, url: str) -> bool:
        """Delete cached result for a specific URL."""
        try:
            client = await self._get_redis()
            if client is None:
                return False

            key = self._get_key(url)
            result = await client.delete(key)
            if result > 0:
                logger.info("ParseCache: Deleted cache for %s (key: %s)", url[:50], key)
                return True
            return False

        except Exception as e:
            logger.warning("ParseCache: Error deleting cache for %s: %s", url[:50], e)
            return False

    async def clear_all(self) -> int:
        """Clear all parse cache entries. Returns number of keys deleted."""
        try:
            client = await self._get_redis()
            if client is None:
                return 0

            # Find all parse:* keys
            keys = []
            async for key in client.scan_iter(match="parse:*"):
                keys.append(key)

            if keys:
                deleted = await client.delete(*keys)
                logger.info("ParseCache: Cleared %d cache entries", deleted)
                return deleted
            return 0

        except Exception as e:
            logger.warning("ParseCache: Error clearing cache: %s", e)
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            client = await self._get_redis()
            
            stats = {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / (self._hits + self._misses) * 100, 2) 
                           if (self._hits + self._misses) > 0 else 0,
                "redis_connected": client is not None,
                "enabled": client is not None,
                "default_ttl": self._default_ttl,
                "total_keys": 0,
            }

            if client is not None:
                # Count parse:* keys
                key_count = 0
                async for _ in client.scan_iter(match="parse:*"):
                    key_count += 1
                stats["total_keys"] = key_count
                stats["cached_entries"] = key_count

            return stats

        except Exception as e:
            logger.warning("ParseCache: Error getting stats: %s", e)
            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": 0,
                "redis_connected": False,
                "enabled": False,
                "total_keys": 0,
                "error": str(e)
            }

    async def close(self):
        """Close Redis connection."""
        if self._redis is not None:
            try:
                await self._redis.close()
                logger.info("ParseCache: Redis connection closed")
            except Exception as e:
                logger.warning("ParseCache: Error closing Redis connection: %s", e)
            finally:
                self._redis = None


# Global cache instance
parse_cache = ParseCache()
