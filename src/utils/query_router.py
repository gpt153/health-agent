"""Query routing to optimize model selection for simple vs complex queries"""
import logging
import re
from typing import Tuple

logger = logging.getLogger(__name__)


class QueryRouter:
    """
    Routes queries to appropriate AI model based on complexity.

    Simple queries (< 8 words, factual lookups) → Claude Haiku (2-3s)
    Complex queries (analysis, reasoning) → Claude Sonnet (6-8s)
    """

    # Patterns that indicate simple queries
    SIMPLE_QUERY_PATTERNS = [
        # Direct questions about data
        r"^(what('s| is) my|show my|get my|my)\s+(xp|level|progress|streaks?|stats?|achievements?)",
        r"^(how (much|many)|what('s| is))\s+(xp|calories|protein|carbs|fat|macros)",

        # Reminder queries
        r"^(show|list|get|what are) (my )?reminders?",
        r"^(do i have|what('s| is) my) (reminders?|schedule)",

        # Simple status checks
        r"^(am i|what('s| is) my)\s+(level|rank|tier|streak)",

        # Food summary queries
        r"^(what did i eat|show (my )?food|calories today|today('s| 's) (food|calories|macros))",

        # Short factual questions (< 8 words)
        r"^.{1,50}$",  # Very short messages are usually simple
    ]

    # Keywords that indicate complexity (override simple detection)
    COMPLEX_INDICATORS = [
        # Analysis and reasoning
        r"\b(why|how (do|does|can|could|should|would)|explain|analyze|compare)\b",
        r"\b(suggest|recommend|advice|should i|what if)\b",

        # Planning and strategy
        r"\b(plan|strategy|approach|best way|optimize)\b",

        # Context-heavy requests
        r"\b(based on|considering|taking into account)\b",

        # Multi-part questions
        r"\?.*\?",  # Multiple question marks
        r"\band\b.*\b(what|how|why|when)",  # Compound questions
    ]

    def __init__(self):
        """Initialize query router"""
        self._simple_count = 0
        self._complex_count = 0

    def route_query(self, message: str) -> Tuple[str, str]:
        """
        Determine which model to use for this query.

        Args:
            message: User's message

        Returns:
            Tuple of (model_name, reason)
            - model_name: "haiku" or "sonnet"
            - reason: Explanation for the routing decision
        """
        # Normalize for analysis
        normalized = message.lower().strip()
        word_count = len(normalized.split())

        # Check for complex indicators first (high priority)
        for pattern in self.COMPLEX_INDICATORS:
            if re.search(pattern, normalized, re.IGNORECASE):
                self._complex_count += 1
                reason = f"Complex query detected (pattern: {pattern})"
                logger.info(f"[ROUTER] → Sonnet: {reason}")
                return ("sonnet", reason)

        # Check for simple query patterns
        for pattern in self.SIMPLE_QUERY_PATTERNS:
            if re.search(pattern, normalized, re.IGNORECASE):
                # Additional validation: if message is very long, it's probably complex
                if word_count > 15:
                    self._complex_count += 1
                    reason = f"Long message ({word_count} words) overrides simple pattern"
                    logger.info(f"[ROUTER] → Sonnet: {reason}")
                    return ("sonnet", reason)

                self._simple_count += 1
                reason = f"Simple query pattern matched: {pattern[:50]}"
                logger.info(f"[ROUTER] → Haiku: {reason}")
                return ("haiku", reason)

        # Default: very short queries are simple, longer ones are complex
        if word_count <= 5:
            self._simple_count += 1
            reason = f"Short query ({word_count} words)"
            logger.info(f"[ROUTER] → Haiku: {reason}")
            return ("haiku", reason)
        else:
            self._complex_count += 1
            reason = f"Default to complex ({word_count} words)"
            logger.info(f"[ROUTER] → Sonnet: {reason}")
            return ("sonnet", reason)

    def should_use_haiku(self, message: str) -> bool:
        """
        Quick check if message should use Haiku.

        Args:
            message: User's message

        Returns:
            True if Haiku should be used, False for Sonnet
        """
        model, _ = self.route_query(message)
        return model == "haiku"

    def get_stats(self) -> dict:
        """Get routing statistics"""
        total = self._simple_count + self._complex_count
        haiku_rate = (self._simple_count / total * 100) if total > 0 else 0

        return {
            "haiku_routed": self._simple_count,
            "sonnet_routed": self._complex_count,
            "total": total,
            "haiku_rate": haiku_rate,
        }


# Global router instance
query_router = QueryRouter()
