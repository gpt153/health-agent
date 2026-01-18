"""
Caching utilities for API endpoints

Implements TTL-based in-memory caching with user-specific cache keys.
Designed to reduce database load by caching frequently accessed data.

Target: 30% load reduction on user preferences, profiles, and gamification data.
"""
import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Tuple, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Cache storage: {cache_key: (value, expiry_timestamp)}
_cache: Dict[str, Tuple[Any, float]] = {}

# Cache statistics for monitoring
_cache_stats = {
    "hits": 0,
    "misses": 0,
    "invalidations": 0,
    "total_queries": 0
}


class CacheConfig:
    """Cache configuration constants"""
    DEFAULT_TTL = 300  # 5 minutes in seconds
    USER_PREFERENCES_TTL = 300  # 5 minutes
    USER_PROFILE_TTL = 300  # 5 minutes
    GAMIFICATION_TTL = 300  # 5 minutes (XP, streaks, achievements)

    # Enable/disable caching globally (useful for testing)
    ENABLED = True


def cache_with_ttl(
    ttl: int = CacheConfig.DEFAULT_TTL,
    key_prefix: str = "",
    include_args: bool = True
):
    """
    Decorator to cache function results with TTL (Time To Live).

    Args:
        ttl: Time to live in seconds (default: 5 minutes)
        key_prefix: Prefix for cache key (helps organize cache entries)
        include_args: Whether to include function arguments in cache key

    Usage:
        @cache_with_ttl(ttl=300, key_prefix="user_profile")
        async def get_user_profile(user_id: str) -> dict:
            # expensive database operation
            return profile_data
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            global _cache_stats
            _cache_stats["total_queries"] += 1

            # Check if caching is enabled
            if not CacheConfig.ENABLED:
                return await func(*args, **kwargs)

            # Build cache key
            if include_args:
                # Convert args and kwargs to a hashable key
                args_key = "_".join(str(arg) for arg in args)
                kwargs_key = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = f"{key_prefix}:{func.__name__}:{args_key}:{kwargs_key}"
            else:
                cache_key = f"{key_prefix}:{func.__name__}"

            # Check if value exists in cache and is not expired
            current_time = time.time()
            if cache_key in _cache:
                cached_value, expiry = _cache[cache_key]
                if current_time < expiry:
                    _cache_stats["hits"] += 1
                    logger.debug(
                        f"Cache HIT: {cache_key} "
                        f"(expires in {int(expiry - current_time)}s)"
                    )
                    return cached_value
                else:
                    # Expired entry, remove it
                    del _cache[cache_key]
                    logger.debug(f"Cache EXPIRED: {cache_key}")

            # Cache miss - execute function
            _cache_stats["misses"] += 1
            logger.debug(f"Cache MISS: {cache_key}")

            result = await func(*args, **kwargs)

            # Store in cache with expiry timestamp
            _cache[cache_key] = (result, current_time + ttl)
            logger.debug(f"Cache STORED: {cache_key} (TTL: {ttl}s)")

            return result

        return wrapper
    return decorator


def invalidate_cache(pattern: Optional[str] = None, user_id: Optional[str] = None) -> int:
    """
    Invalidate cache entries matching a pattern or user_id.

    Args:
        pattern: String pattern to match in cache keys (e.g., "user_profile")
        user_id: User ID to invalidate all cache entries for

    Returns:
        Number of cache entries invalidated

    Examples:
        invalidate_cache(user_id="123456")  # Invalidate all cache for user
        invalidate_cache(pattern="user_profile")  # Invalidate all profile caches
        invalidate_cache(pattern="user_profile", user_id="123456")  # Specific user's profile
    """
    global _cache_stats

    if not pattern and not user_id:
        # Clear entire cache
        count = len(_cache)
        _cache.clear()
        _cache_stats["invalidations"] += count
        logger.info(f"Cleared entire cache ({count} entries)")
        return count

    # Find matching keys
    keys_to_delete = []
    for key in _cache.keys():
        match = True
        if pattern and pattern not in key:
            match = False
        if user_id and user_id not in key:
            match = False
        if match:
            keys_to_delete.append(key)

    # Delete matching keys
    for key in keys_to_delete:
        del _cache[key]

    count = len(keys_to_delete)
    _cache_stats["invalidations"] += count

    if count > 0:
        logger.info(
            f"Invalidated {count} cache entries "
            f"(pattern='{pattern}', user_id='{user_id}')"
        )

    return count


def invalidate_user_cache(user_id: str) -> int:
    """
    Invalidate all cache entries for a specific user.

    This should be called when user data is updated:
    - Profile updates
    - Preference changes
    - XP/level changes
    - Achievement unlocks
    - Streak updates
    """
    return invalidate_cache(user_id=user_id)


def get_cache_stats() -> dict:
    """
    Get cache performance statistics.

    Returns:
        dict with hits, misses, hit_rate, invalidations, total_queries
    """
    hits = _cache_stats["hits"]
    total = _cache_stats["total_queries"]

    hit_rate = (hits / total * 100) if total > 0 else 0

    return {
        "hits": hits,
        "misses": _cache_stats["misses"],
        "hit_rate_percent": round(hit_rate, 2),
        "invalidations": _cache_stats["invalidations"],
        "total_queries": total,
        "cache_size": len(_cache),
        "load_reduction_percent": round(hit_rate, 2)  # Hit rate = load reduction
    }


def reset_cache_stats():
    """Reset cache statistics (useful for testing)"""
    global _cache_stats
    _cache_stats = {
        "hits": 0,
        "misses": 0,
        "invalidations": 0,
        "total_queries": 0
    }
    logger.info("Cache statistics reset")


def clear_expired_entries() -> int:
    """
    Manually clear expired cache entries.

    This is automatically done on cache access, but can be called
    explicitly for cleanup.

    Returns:
        Number of expired entries removed
    """
    current_time = time.time()
    expired_keys = [
        key for key, (_, expiry) in _cache.items()
        if current_time >= expiry
    ]

    for key in expired_keys:
        del _cache[key]

    if expired_keys:
        logger.info(f"Cleared {len(expired_keys)} expired cache entries")

    return len(expired_keys)


def warm_user_cache(user_id: str, data: Dict[str, Any]) -> None:
    """
    Pre-populate cache with user data (cache warming).

    Called on user login to preload frequently accessed data.

    Args:
        user_id: User ID to warm cache for
        data: Dict containing cache entries to pre-populate
              Keys should be cache key prefixes (e.g., 'user_profile', 'user_preferences')
    """
    current_time = time.time()
    count = 0

    for key_suffix, value in data.items():
        # Determine TTL based on data type
        if "profile" in key_suffix.lower():
            ttl = CacheConfig.USER_PROFILE_TTL
        elif "preference" in key_suffix.lower():
            ttl = CacheConfig.USER_PREFERENCES_TTL
        elif any(x in key_suffix.lower() for x in ["xp", "streak", "achievement", "gamification"]):
            ttl = CacheConfig.GAMIFICATION_TTL
        else:
            ttl = CacheConfig.DEFAULT_TTL

        cache_key = f"{key_suffix}:{user_id}"
        _cache[cache_key] = (value, current_time + ttl)
        count += 1

    logger.info(f"Warmed cache for user {user_id} with {count} entries")
