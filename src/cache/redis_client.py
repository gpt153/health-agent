"""
Redis caching client for performance optimization.

Provides async Redis operations with:
- Automatic serialization/deserialization
- TTL-based caching
- Graceful degradation on Redis failures
- Connection pooling
- Cache statistics
"""

import json
import logging
from typing import Any, Optional
import asyncio
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

# Try to import redis
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis not available - caching will be disabled")


class RedisCache:
    """
    Async Redis cache client with graceful degradation.

    Features:
    - Automatic JSON serialization
    - TTL support
    - Cache statistics
    - Connection pooling
    - Fallback to no-cache on failures
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0", enabled: bool = True):
        """
        Initialize Redis cache client.

        Args:
            redis_url: Redis connection URL
            enabled: Whether caching is enabled (allows runtime disable)
        """
        self.redis_url = redis_url
        self.enabled = enabled and REDIS_AVAILABLE
        self._client: Optional[Any] = None
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
        }

        if not REDIS_AVAILABLE:
            logger.warning("Redis library not installed - caching disabled")
            self.enabled = False

    async def connect(self):
        """Establish Redis connection."""
        if not self.enabled:
            return

        try:
            self._client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10,
            )
            # Test connection
            await self._client.ping()
            logger.info(f"✅ Redis connected: {self.redis_url}")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            logger.warning("Caching disabled - falling back to direct queries")
            self.enabled = False
            self._client = None

    async def close(self):
        """Close Redis connection."""
        if self._client:
            try:
                await self._client.aclose()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value (deserialized from JSON) or None if not found
        """
        if not self.enabled or not self._client:
            self._stats["misses"] += 1
            return None

        try:
            value = await self._client.get(key)
            if value is None:
                self._stats["misses"] += 1
                logger.debug(f"Cache MISS: {key}")
                return None

            self._stats["hits"] += 1
            logger.debug(f"Cache HIT: {key}")

            # Deserialize JSON
            return json.loads(value)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for key '{key}': {e}")
            self._stats["errors"] += 1
            return None
        except Exception as e:
            logger.error(f"Redis GET error for key '{key}': {e}")
            self._stats["errors"] += 1
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (None = no expiration)

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self._client:
            return False

        try:
            # Serialize to JSON
            serialized = json.dumps(value)

            if ttl:
                await self._client.setex(key, ttl, serialized)
            else:
                await self._client.set(key, serialized)

            self._stats["sets"] += 1
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True
        except (TypeError, ValueError) as e:
            logger.error(f"JSON encode error for key '{key}': {e}")
            self._stats["errors"] += 1
            return False
        except Exception as e:
            logger.error(f"Redis SET error for key '{key}': {e}")
            self._stats["errors"] += 1
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if key was deleted, False otherwise
        """
        if not self.enabled or not self._client:
            return False

        try:
            result = await self._client.delete(key)
            self._stats["deletes"] += 1
            logger.debug(f"Cache DELETE: {key}")
            return result > 0
        except Exception as e:
            logger.error(f"Redis DELETE error for key '{key}': {e}")
            self._stats["errors"] += 1
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Redis key pattern (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        if not self.enabled or not self._client:
            return 0

        try:
            keys = []
            async for key in self._client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await self._client.delete(*keys)
                self._stats["deletes"] += deleted
                logger.debug(f"Cache DELETE pattern '{pattern}': {deleted} keys")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Redis DELETE pattern error for '{pattern}': {e}")
            self._stats["errors"] += 1
            return 0

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        if not self.enabled or not self._client:
            return False

        try:
            return await self._client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error for key '{key}': {e}")
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration time for existing key.

        Args:
            key: Cache key
            ttl: Time to live in seconds

        Returns:
            True if expiration was set, False otherwise
        """
        if not self.enabled or not self._client:
            return False

        try:
            return await self._client.expire(key, ttl)
        except Exception as e:
            logger.error(f"Redis EXPIRE error for key '{key}': {e}")
            return False

    async def ttl(self, key: str) -> int:
        """
        Get remaining TTL for a key.

        Args:
            key: Cache key

        Returns:
            TTL in seconds, -1 if no expiration, -2 if key doesn't exist
        """
        if not self.enabled or not self._client:
            return -2

        try:
            return await self._client.ttl(key)
        except Exception as e:
            logger.error(f"Redis TTL error for key '{key}': {e}")
            return -2

    async def clear_all(self) -> bool:
        """
        Clear all keys in the current database.

        WARNING: This deletes ALL cached data.

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self._client:
            return False

        try:
            await self._client.flushdb()
            logger.warning("🗑️  Redis cache cleared (FLUSHDB)")
            return True
        except Exception as e:
            logger.error(f"Redis FLUSHDB error: {e}")
            return False

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with hits, misses, hit rate, etc.
        """
        total_reads = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total_reads * 100) if total_reads > 0 else 0.0

        return {
            "enabled": self.enabled,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate_percent": round(hit_rate, 2),
            "sets": self._stats["sets"],
            "deletes": self._stats["deletes"],
            "errors": self._stats["errors"],
            "total_reads": total_reads,
        }

    def reset_stats(self):
        """Reset cache statistics."""
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
        }
        logger.info("Cache statistics reset")

    @asynccontextmanager
    async def pipeline(self):
        """
        Context manager for pipelined operations.

        Example:
            async with cache.pipeline() as pipe:
                await pipe.set("key1", "value1")
                await pipe.set("key2", "value2")
                await pipe.execute()
        """
        if not self.enabled or not self._client:
            yield None
            return

        pipe = self._client.pipeline()
        try:
            yield pipe
        finally:
            pass


# Global cache instance (initialized by config)
cache: Optional[RedisCache] = None


async def init_cache(redis_url: str, enabled: bool = True) -> RedisCache:
    """
    Initialize global Redis cache instance.

    Args:
        redis_url: Redis connection URL
        enabled: Whether caching is enabled

    Returns:
        Initialized RedisCache instance
    """
    global cache

    cache = RedisCache(redis_url=redis_url, enabled=enabled)
    await cache.connect()

    return cache


async def close_cache():
    """Close global cache connection."""
    global cache

    if cache:
        await cache.close()
        cache = None


def get_cache() -> Optional[RedisCache]:
    """
    Get global cache instance.

    Returns:
        RedisCache instance or None if not initialized
    """
    return cache
