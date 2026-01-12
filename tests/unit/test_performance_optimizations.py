"""Unit tests for performance optimization utilities"""
import pytest
from src.utils.response_cache import ResponseCache
from src.utils.query_router import QueryRouter


class TestResponseCache:
    """Test response caching functionality"""

    def test_cache_hit_greeting(self):
        """Test that simple greetings are cached"""
        cache = ResponseCache()

        # Test various greetings
        greetings = ["hi", "hello", "hey", "Hi!", "HELLO"]
        for greeting in greetings:
            result = cache.get_cached_response(greeting)
            assert result is not None, f"Should cache greeting: {greeting}"
            assert isinstance(result, str)
            assert len(result) > 0

    def test_cache_hit_thanks(self):
        """Test that thanks messages are cached"""
        cache = ResponseCache()

        thanks_messages = ["thanks", "thank you", "thx"]
        for msg in thanks_messages:
            result = cache.get_cached_response(msg)
            assert result is not None, f"Should cache thanks: {msg}"

    def test_cache_miss_complex(self):
        """Test that complex messages are not cached"""
        cache = ResponseCache()

        complex_messages = [
            "what did I eat yesterday?",
            "show me my progress this week",
            "how can I improve my nutrition?",
        ]
        for msg in complex_messages:
            result = cache.get_cached_response(msg)
            assert result is None, f"Should NOT cache complex message: {msg}"

    def test_cache_stats(self):
        """Test cache statistics tracking"""
        cache = ResponseCache()

        # Generate some hits and misses
        cache.get_cached_response("hi")  # hit
        cache.get_cached_response("thanks")  # hit
        cache.get_cached_response("what's my XP?")  # miss

        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["total"] == 3
        assert stats["hit_rate"] == pytest.approx(66.67, rel=0.01)


class TestQueryRouter:
    """Test query routing functionality"""

    def test_simple_xp_query(self):
        """Test that XP queries route to Haiku"""
        router = QueryRouter()

        simple_queries = [
            "what's my XP?",
            "show my level",
            "my progress",
            "get my achievements",
        ]

        for query in simple_queries:
            model, reason = router.route_query(query)
            assert model == "haiku", f"Should route '{query}' to Haiku, got {model} ({reason})"

    def test_simple_reminder_query(self):
        """Test that reminder queries route to Haiku"""
        router = QueryRouter()

        reminder_queries = [
            "show my reminders",
            "list reminders",
            "what are my reminders?",
        ]

        for query in reminder_queries:
            model, reason = router.route_query(query)
            assert model == "haiku", f"Should route '{query}' to Haiku"

    def test_complex_why_query(self):
        """Test that 'why' questions route to Sonnet"""
        router = QueryRouter()

        complex_queries = [
            "why am I not losing weight?",
            "how can I improve my sleep?",
            "what should I eat for better energy?",
        ]

        for query in complex_queries:
            model, reason = router.route_query(query)
            assert model == "sonnet", f"Should route '{query}' to Sonnet, got {model} ({reason})"

    def test_complex_analysis_query(self):
        """Test that analysis requests route to Sonnet"""
        router = QueryRouter()

        analysis_queries = [
            "analyze my nutrition trends",
            "compare my progress to last month",
            "suggest a better workout plan",
        ]

        for query in analysis_queries:
            model, reason = router.route_query(query)
            assert model == "sonnet", f"Should route '{query}' to Sonnet"

    def test_short_query_routes_to_haiku(self):
        """Test that very short queries route to Haiku"""
        router = QueryRouter()

        short_queries = ["XP", "stats", "level", "ok"]

        for query in short_queries:
            model, reason = router.route_query(query)
            assert model == "haiku", f"Should route short query '{query}' to Haiku"

    def test_long_query_routes_to_sonnet(self):
        """Test that long queries route to Sonnet"""
        router = QueryRouter()

        long_query = "I've been tracking my food for a week now and I'm wondering if you can help me understand what patterns you've noticed and what I should focus on improving"
        model, reason = router.route_query(long_query)
        assert model == "sonnet", "Long queries should route to Sonnet"

    def test_router_stats(self):
        """Test router statistics tracking"""
        router = QueryRouter()

        # Route some queries
        router.route_query("what's my XP?")  # haiku
        router.route_query("show my level")  # haiku
        router.route_query("why am I not making progress?")  # sonnet

        stats = router.get_stats()
        assert stats["haiku_routed"] == 2
        assert stats["sonnet_routed"] == 1
        assert stats["total"] == 3
        assert stats["haiku_rate"] == pytest.approx(66.67, rel=0.01)


class TestPersistentTypingIndicator:
    """Test persistent typing indicator (integration would require Telegram mock)"""

    def test_typing_indicator_imports(self):
        """Test that typing indicator module imports correctly"""
        from src.utils.typing_indicator import PersistentTypingIndicator

        # Just verify the class exists and can be instantiated (without Chat object)
        assert PersistentTypingIndicator is not None
