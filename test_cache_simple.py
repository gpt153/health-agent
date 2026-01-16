#!/usr/bin/env python3
"""
Simple test script for cache functionality
Run with: python3 test_cache_simple.py
"""
import asyncio
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils.cache import (
    cache_with_ttl,
    invalidate_cache,
    invalidate_user_cache,
    get_cache_stats,
    reset_cache_stats,
    CacheConfig,
    _cache
)


async def test_basic_caching():
    """Test basic caching functionality"""
    print("Test 1: Basic caching...")
    reset_cache_stats()
    _cache.clear()

    call_count = 0

    @cache_with_ttl(ttl=300, key_prefix="test")
    async def expensive_function(user_id: str):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.01)
        return {"user_id": user_id, "data": "expensive"}

    # First call - should execute
    result1 = await expensive_function("user123")
    assert call_count == 1, f"Expected 1 call, got {call_count}"
    assert result1["user_id"] == "user123"

    # Second call - should use cache
    result2 = await expensive_function("user123")
    assert call_count == 1, f"Expected 1 call (cached), got {call_count}"

    stats = get_cache_stats()
    assert stats["hits"] == 1, f"Expected 1 hit, got {stats['hits']}"
    assert stats["misses"] == 1, f"Expected 1 miss, got {stats['misses']}"

    print("✅ Basic caching works")


async def test_ttl_expiration():
    """Test TTL expiration"""
    print("\nTest 2: TTL expiration...")
    reset_cache_stats()
    _cache.clear()

    call_count = 0

    @cache_with_ttl(ttl=1, key_prefix="test_ttl")
    async def cached_function(user_id: str):
        nonlocal call_count
        call_count += 1
        return {"count": call_count}

    # First call
    result1 = await cached_function("user123")
    assert result1["count"] == 1

    # Second call - should use cache
    result2 = await cached_function("user123")
    assert result2["count"] == 1

    # Wait for expiration
    await asyncio.sleep(1.1)

    # Should execute again
    result3 = await cached_function("user123")
    assert result3["count"] == 2, f"Expected count 2 after expiration, got {result3['count']}"

    print("✅ TTL expiration works")


async def test_cache_invalidation():
    """Test cache invalidation"""
    print("\nTest 3: Cache invalidation...")
    reset_cache_stats()
    _cache.clear()

    @cache_with_ttl(ttl=300, key_prefix="user_data")
    async def get_user_data(user_id: str, data_type: str):
        return {"user_id": user_id, "type": data_type}

    # Create cache entries
    await get_user_data("user123", "profile")
    await get_user_data("user123", "preferences")
    await get_user_data("user456", "profile")

    assert len(_cache) == 3, f"Expected 3 cache entries, got {len(_cache)}"

    # Invalidate user123
    count = invalidate_user_cache("user123")
    assert count == 2, f"Expected 2 invalidations, got {count}"
    assert len(_cache) == 1, f"Expected 1 remaining entry, got {len(_cache)}"

    print("✅ Cache invalidation works")


async def test_cache_statistics():
    """Test cache statistics"""
    print("\nTest 4: Cache statistics...")
    reset_cache_stats()
    _cache.clear()

    @cache_with_ttl(ttl=300, key_prefix="test")
    async def cached_func(value: str):
        return value

    # Create some hits and misses
    await cached_func("a")  # miss
    await cached_func("a")  # hit
    await cached_func("a")  # hit
    await cached_func("b")  # miss

    stats = get_cache_stats()
    assert stats["hits"] == 2, f"Expected 2 hits, got {stats['hits']}"
    assert stats["misses"] == 2, f"Expected 2 misses, got {stats['misses']}"
    assert stats["total_queries"] == 4, f"Expected 4 queries, got {stats['total_queries']}"
    assert stats["hit_rate_percent"] == 50.0, f"Expected 50% hit rate, got {stats['hit_rate_percent']}"
    assert stats["load_reduction_percent"] == 50.0

    print("✅ Cache statistics work")


async def test_realistic_scenario():
    """Test realistic API usage scenario"""
    print("\nTest 5: Realistic scenario (targeting 30% load reduction)...")
    reset_cache_stats()
    _cache.clear()

    db_queries = 0

    @cache_with_ttl(ttl=300, key_prefix="user_profile")
    async def load_user_profile(user_id: str):
        nonlocal db_queries
        db_queries += 1
        await asyncio.sleep(0.001)  # Simulate DB query
        return {"user_id": user_id, "name": "Test User"}

    # Simulate realistic usage: multiple API endpoints reading same user data
    user_id = "user123"

    # Dashboard loads profile 3 times (different API calls)
    await load_user_profile(user_id)
    await load_user_profile(user_id)
    await load_user_profile(user_id)

    # Only 1 DB query should have been made
    assert db_queries == 1, f"Expected 1 DB query, got {db_queries}"

    # User updates profile - invalidate cache
    invalidate_user_cache(user_id)

    # More API calls after update
    await load_user_profile(user_id)
    await load_user_profile(user_id)

    # Should have made 2 total DB queries
    assert db_queries == 2, f"Expected 2 DB queries after invalidation, got {db_queries}"

    stats = get_cache_stats()
    print(f"   Total queries: {stats['total_queries']}")
    print(f"   DB queries: {db_queries}")
    print(f"   Cache hits: {stats['hits']}")
    print(f"   Cache misses: {stats['misses']}")
    print(f"   Load reduction: {stats['load_reduction_percent']}%")

    # 3 hits out of 5 queries = 60% reduction
    assert stats["load_reduction_percent"] == 60.0, \
        f"Expected 60% load reduction, got {stats['load_reduction_percent']}%"

    print("✅ Realistic scenario works - achieved 60% load reduction (exceeds 30% target)")


async def test_gamification_caching():
    """Test gamification data caching scenario"""
    print("\nTest 6: Gamification data caching...")
    reset_cache_stats()
    _cache.clear()

    xp_queries = 0
    streak_queries = 0
    achievement_queries = 0

    @cache_with_ttl(ttl=300, key_prefix="user_xp")
    async def get_user_xp(user_id: str):
        nonlocal xp_queries
        xp_queries += 1
        return {"xp": 1000, "level": 10}

    @cache_with_ttl(ttl=300, key_prefix="user_streaks")
    async def get_user_streaks(user_id: str):
        nonlocal streak_queries
        streak_queries += 1
        return [{"type": "daily", "count": 7}]

    @cache_with_ttl(ttl=300, key_prefix="user_achievements")
    async def get_user_achievements(user_id: str):
        nonlocal achievement_queries
        achievement_queries += 1
        return [{"id": "first_entry"}]

    user_id = "user123"

    # Dashboard load - reads all gamification data
    await get_user_xp(user_id)
    await get_user_streaks(user_id)
    await get_user_achievements(user_id)

    # Multiple API calls read same data
    await get_user_xp(user_id)
    await get_user_streaks(user_id)
    await get_user_achievements(user_id)

    # Should only query once per data type
    assert xp_queries == 1, f"Expected 1 XP query, got {xp_queries}"
    assert streak_queries == 1, f"Expected 1 streak query, got {streak_queries}"
    assert achievement_queries == 1, f"Expected 1 achievement query, got {achievement_queries}"

    stats = get_cache_stats()
    assert stats["load_reduction_percent"] == 50.0, \
        f"Expected 50% load reduction, got {stats['load_reduction_percent']}%"

    print("✅ Gamification caching works - 50% load reduction")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing API Result Caching System")
    print("=" * 60)

    try:
        await test_basic_caching()
        await test_ttl_expiration()
        await test_cache_invalidation()
        await test_cache_statistics()
        await test_realistic_scenario()
        await test_gamification_caching()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nSummary:")
        print("- Cache decorator works correctly")
        print("- TTL expiration functions properly")
        print("- Cache invalidation works as expected")
        print("- Statistics tracking is accurate")
        print("- Realistic scenarios achieve >30% load reduction")
        print("- Gamification caching reduces DB load by 50%+")
        return 0

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
