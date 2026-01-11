"""Simple response cache for common greetings and quick replies"""
import logging
from typing import Optional
import re

logger = logging.getLogger(__name__)


class ResponseCache:
    """
    Cache for instant responses to common messages.

    Handles greetings, thanks, and other simple interactions
    without requiring LLM processing.
    """

    # Predefined responses for common patterns
    CACHED_RESPONSES = {
        # Greetings
        r"^(hi|hey|hello|sup|yo|hola)[\s!.]*$": [
            "Hey! 👋 How can I help you today?",
            "Hi there! 👋 What's up?",
            "Hello! 👋 Ready to crush your health goals?",
        ],

        # Thanks
        r"^(thanks|thank you|thx|ty)[\s!.]*$": [
            "You're welcome! 😊",
            "Anytime! 💪",
            "Happy to help! 🙌",
        ],

        # Good morning/night
        r"^(good morning|morning)[\s!.]*$": [
            "Good morning! ☀️ Ready to make today count?",
            "Morning! ☀️ Let's have a great day!",
        ],

        r"^(good night|goodnight|night)[\s!.]*$": [
            "Good night! 🌙 Sleep well!",
            "Night! 🌙 Rest up and recover!",
        ],

        # OK/Alright
        r"^(ok|okay|alright|k|kk)[\s!.]*$": [
            "👍",
            "Got it! 👍",
        ],

        # Yes/No (single word)
        r"^(yes|yeah|yep|yup)[\s!.]*$": [
            "Great! 👍",
            "Awesome! 🎉",
        ],

        r"^(no|nope|nah)[\s!.]*$": [
            "No worries! 👍",
            "All good! 👍",
        ],
    }

    def __init__(self):
        """Initialize response cache"""
        self._cache_hits = 0
        self._cache_misses = 0

    def get_cached_response(self, message: str) -> Optional[str]:
        """
        Check if message matches a cached pattern and return instant response.

        Args:
            message: User's message (cleaned)

        Returns:
            Cached response string if match found, None otherwise
        """
        # Normalize message for matching
        normalized = message.lower().strip()

        # Check each pattern
        for pattern, responses in self.CACHED_RESPONSES.items():
            if re.match(pattern, normalized, re.IGNORECASE):
                self._cache_hits += 1
                # Rotate through responses to add variety
                import random
                response = random.choice(responses)
                logger.info(f"[CACHE_HIT] Matched pattern '{pattern}' for message '{normalized}'")
                return response

        # No match found
        self._cache_misses += 1
        return None

    def get_stats(self) -> dict:
        """Get cache statistics"""
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total > 0 else 0

        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "total": total,
            "hit_rate": hit_rate,
        }


# Global cache instance
response_cache = ResponseCache()
