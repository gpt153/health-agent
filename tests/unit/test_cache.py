"""
Tests for API result caching system

Tests cache functionality, TTL expiration, invalidation, and performance metrics.
"""
import asyncio
import time
import pytest
from src.utils.cache import (
    cache_with_ttl,
    invalidate_cache,
    invalidate_user_cache,
    get_cache_stats,
    reset_cache_stats,
    clear_expired_entries,
    warm_user_cache,
    CacheConfig,
    _cache
)


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset cache and stats before each test"""
    _cache.clear()
    reset_cache_stats()
    CacheConfig.ENABLED = True
    yield
    _cache.clear()
    reset_cache_stats()


class TestCacheDecorator:
    """Test the cache_with_ttl decorator"""

    @pytest.mark.asyncio
    async def test_cache_basic_functionality(self):
        """Test that caching works for basic async functions"""
        call_count = 0

        @cache_with_ttl(ttl=300, key_prefix="test")
        async def expensive_function(user_id: str):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # Simulate expensive operation
            return {"user_id": user_id, "data": "expensive"}

        # First call - should execute function
        result1 = await expensive_function("user123")
        assert call_count == 1
        assert result1 == {"user_id": "user123", "data": "expensive"}

        # Second call with same args - should use cache
        result2 = await expensive_function("user123")
        assert call_count == 1  # Not incremented
        assert result2 == result1

        # Different args - should execute function again
        result3 = await expensive_function("user456")
        assert call_count == 2
        assert result3["user_id"] == "user456"

    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self):
        """Test that cache entries expire after TTL"""
        call_count = 0

        @cache_with_ttl(ttl=1, key_prefix="test_ttl")  # 1 second TTL
        async def cached_function(user_id: str):
            nonlocal call_count
            call_count += 1
            return {"count": call_count}

        # First call
        result1 = await cached_function("user123")
        assert result1["count"] == 1

        # Immediate second call - should use cache
        result2 = await cached_function("user123")
        assert result2["count"] == 1

        # Wait for TTL to expire
        await asyncio.sleep(1.1)

        # Call after expiration - should execute function again
        result3 = await cached_function("user123")
        assert result3["count"] == 2

    @pytest.mark.asyncio
    async def test_cache_disabled(self):
        """Test that caching can be disabled globally"""
        call_count = 0

        @cache_with_ttl(ttl=300, key_prefix="test_disabled")
        async def cached_function(user_id: str):
            nonlocal call_count
            call_count += 1
            return {"count": call_count}

        # Disable caching
        CacheConfig.ENABLED = False

        # Both calls should execute function
        await cached_function("user123")
        await cached_function("user123")
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_cache_with_kwargs(self):
        """Test caching with keyword arguments"""
        call_count = 0

        @cache_with_ttl(ttl=300, key_prefix="test_kwargs")
        async def cached_function(user_id: str, option: str = "default"):
            nonlocal call_count
            call_count += 1
            return {"user_id": user_id, "option": option, "count": call_count}

        # Different combinations should create different cache entries
        result1 = await cached_function("user123", option="A")
        result2 = await cached_function("user123", option="A")  # Should use cache
        result3 = await cached_function("user123", option="B")  # Different option

        assert result1["count"] == 1
        assert result2["count"] == 1  # Same as result1 (cached)
        assert result3["count"] == 2  # New call


class TestCacheInvalidation:
    """Test cache invalidation functions"""

    @pytest.mark.asyncio
    async def test_invalidate_by_user_id(self):
        """Test invalidating all cache entries for a user"""
        @cache_with_ttl(ttl=300, key_prefix="user_data")
        async def get_user_data(user_id: str, data_type: str):
            return {"user_id": user_id, "type": data_type}

        # Create cache entries for multiple users
        await get_user_data("user123", "profile")
        await get_user_data("user123", "preferences")
        await get_user_data("user456", "profile")

        assert len(_cache) == 3

        # Invalidate all entries for user123
        count = invalidate_user_cache("user123")
        assert count == 2
        assert len(_cache) == 1

    @pytest.mark.asyncio
    async def test_invalidate_by_pattern(self):
        """Test invalidating cache entries matching a pattern"""
        @cache_with_ttl(ttl=300, key_prefix="user_profile")
        async def get_profile(user_id: str):
            return {"user_id": user_id}

        @cache_with_ttl(ttl=300, key_prefix="user_xp")
        async def get_xp(user_id: str):
            return {"xp": 100}

        await get_profile("user123")
        await get_xp("user123")

        assert len(_cache) == 2

        # Invalidate only profile entries
        count = invalidate_cache(pattern="user_profile")
        assert count == 1
        assert len(_cache) == 1

    @pytest.mark.asyncio
    async def test_invalidate_all(self):
        """Test clearing entire cache"""
        @cache_with_ttl(ttl=300, key_prefix="test")
        async def cached_func(value: str):
            return value

        await cached_func("a")
        await cached_func("b")
        await cached_func("c")

        assert len(_cache) == 3

        count = invalidate_cache()
        assert count == 3
        assert len(_cache) == 0


class TestCacheStatistics:
    """Test cache performance statistics"""

    @pytest.mark.asyncio
    async def test_cache_hit_miss_counting(self):
        """Test that cache hits and misses are counted correctly"""
        @cache_with_ttl(ttl=300, key_prefix="test")
        async def cached_func(value: str):
            return value

        # First call - miss
        await cached_func("test")
        stats = get_cache_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 1
        assert stats["total_queries"] == 1

        # Second call - hit
        await cached_func("test")
        stats = get_cache_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["total_queries"] == 2
        assert stats["hit_rate_percent"] == 50.0

        # Third call - hit
        await cached_func("test")
        stats = get_cache_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["total_queries"] == 3
        assert stats["hit_rate_percent"] == pytest.approx(66.67, abs=0.1)

    @pytest.mark.asyncio
    async def test_cache_invalidation_counting(self):
        """Test that invalidations are counted"""
        @cache_with_ttl(ttl=300, key_prefix="test")
        async def cached_func(user_id: str):
            return {"user_id": user_id}

        await cached_func("user123")
        await cached_func("user456")

        invalidate_user_cache("user123")
        stats = get_cache_stats()
        assert stats["invalidations"] == 1

        invalidate_cache()
        stats = get_cache_stats()
        assert stats["invalidations"] == 2  # 1 + 1 remaining entry

    @pytest.mark.asyncio
    async def test_load_reduction_metric(self):
        """Test that load_reduction_percent matches hit_rate_percent"""
        @cache_with_ttl(ttl=300, key_prefix="test")
        async def cached_func(value: str):
            return value

        # Create some hits and misses
        await cached_func("a")  # miss
        await cached_func("a")  # hit
        await cached_func("b")  # miss
        await cached_func("a")  # hit
        await cached_func("b")  # hit

        stats = get_cache_stats()
        # 3 hits out of 5 total = 60% reduction
        assert stats["hit_rate_percent"] == 60.0
        assert stats["load_reduction_percent"] == 60.0


class TestCacheWarming:
    """Test cache warming functionality"""

    def test_warm_user_cache(self):
        """Test pre-populating cache with user data"""
        user_data = {
            "user_profile": {"name": "Test User", "age": 30},
            "user_preferences": {"theme": "dark"},
            "user_xp": {"xp": 1000, "level": 10}
        }

        warm_user_cache("user123", user_data)

        # Check that cache was populated
        assert len(_cache) == 3

        # Check that entries have correct TTLs
        for key in _cache:
            value, expiry = _cache[key]
            current_time = time.time()
            ttl_remaining = expiry - current_time

            # Should be around 300 seconds (5 minutes)
            assert 295 < ttl_remaining <= 300


class TestCacheExpiration:
    """Test cache expiration cleanup"""

    def test_clear_expired_entries(self):
        """Test manual cleanup of expired entries"""
        # Manually add expired entries
        current_time = time.time()
        _cache["expired1"] = ("value1", current_time - 10)  # Expired 10s ago
        _cache["expired2"] = ("value2", current_time - 5)   # Expired 5s ago
        _cache["valid"] = ("value3", current_time + 300)    # Valid for 5 mins

        assert len(_cache) == 3

        count = clear_expired_entries()
        assert count == 2
        assert len(_cache) == 1
        assert "valid" in _cache


class TestIntegrationScenarios:
    """Integration tests for realistic usage patterns"""

    @pytest.mark.asyncio
    async def test_user_profile_workflow(self):
        """Test typical user profile caching workflow"""
        profile_loads = 0

        @cache_with_ttl(ttl=300, key_prefix="user_profile")
        async def load_user_profile(user_id: str):
            nonlocal profile_loads
            profile_loads += 1
            await asyncio.sleep(0.01)  # Simulate DB query
            return {"user_id": user_id, "name": "Test User"}

        # Simulate multiple reads (common in API)
        user_id = "user123"
        await load_user_profile(user_id)
        await load_user_profile(user_id)
        await load_user_profile(user_id)

        # Should only load once due to caching
        assert profile_loads == 1

        # Simulate profile update
        invalidate_user_cache(user_id)

        # Next read should reload
        await load_user_profile(user_id)
        assert profile_loads == 2

        # Subsequent reads should use cache again
        await load_user_profile(user_id)
        await load_user_profile(user_id)
        assert profile_loads == 2

    @pytest.mark.asyncio
    async def test_gamification_data_workflow(self):
        """Test gamification data caching (XP, streaks, achievements)"""
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
            return [{"id": "first_entry", "unlocked": True}]

        user_id = "user123"

        # Simulate dashboard load (reads all gamification data)
        await get_user_xp(user_id)
        await get_user_streaks(user_id)
        await get_user_achievements(user_id)

        # Subsequent dashboard loads should use cache
        await get_user_xp(user_id)
        await get_user_streaks(user_id)
        await get_user_achievements(user_id)

        assert xp_queries == 1
        assert streak_queries == 1
        assert achievement_queries == 1

        # Simulate XP update (e.g., user logs food)
        invalidate_user_cache(user_id)

        # Next dashboard load should reload all data
        await get_user_xp(user_id)
        await get_user_streaks(user_id)
        await get_user_achievements(user_id)

        assert xp_queries == 2
        assert streak_queries == 2
        assert achievement_queries == 2

    @pytest.mark.asyncio
    async def test_30_percent_load_reduction_target(self):
        """Test that we can achieve 30%+ load reduction in realistic scenario"""
        db_queries = 0

        @cache_with_ttl(ttl=300, key_prefix="user_data")
        async def expensive_db_query(user_id: str):
            nonlocal db_queries
            db_queries += 1
            await asyncio.sleep(0.01)
            return {"data": "expensive"}

        # Simulate realistic usage: multiple API calls with some repeated reads
        users = ["user1", "user2", "user3"]

        # Simulate 100 API calls
        for _ in range(100):
            # 70% of requests are for existing users (cache hits)
            # 30% are new queries (cache misses)
            import random
            if random.random() < 0.7:
                user_id = random.choice(users)  # Cached user
            else:
                user_id = f"user{random.randint(4, 100)}"  # New user

            await expensive_db_query(user_id)

        stats = get_cache_stats()

        # Should achieve at least 30% load reduction
        assert stats["load_reduction_percent"] >= 30.0

        # DB queries should be significantly less than total queries
        assert db_queries < stats["total_queries"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
