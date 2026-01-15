# Plan: Telegram Response Perception Optimization

## Summary

Implement four optimizations to reduce perceived Telegram response time from "60+ seconds" to <10 seconds. Actual response time is already 8 seconds, but users perceive it as much longer due to lack of feedback. This plan implements: (1) persistent typing indicator during LLM processing, (2) background Mem0 embedding generation, (3) response caching for simple greetings, and (4) query routing to Claude Haiku for simple requests.

## Intent

Users currently experience no feedback during 6-8 second LLM API calls, making the 8-second actual response time feel like 60+ seconds. By adding continuous typing indicators, moving non-critical operations to background tasks, caching common responses, and routing simple queries to faster models, we can dramatically improve perceived responsiveness without sacrificing response quality.

## Persona

**Primary**: All Telegram bot users (currently 4 authorized users: 7376426503, 7538670249, 8191393299, 8288122596)
**Secondary**: Future users experiencing the health coaching bot

These users send varied messages ranging from simple greetings ("hi", "thanks") to complex health queries ("what did I eat yesterday?", "show my progress"). They currently wait 8-10 seconds with no feedback and assume the bot is broken.

## UX

### Before (Current State)
```
User: "Hi"
      |
      v
[No feedback for 8 seconds - user thinks bot crashed]
      |
      v
Bot: "Hey! How can I help you today?"
```

**User perception**: "Why did it take so long? Is the bot working?"

### After (Optimized)
```
User: "Hi"
      |
      v
Bot: [typing...]  ← Appears immediately
      |           ← Persists throughout processing
      v           ← Updates every 4 seconds
[0.1s] Bot: "Hey! How can I help you today?"  ← Instant (cached)

User: "Show my reminders"
      |
      v
Bot: [typing...]  ← Appears immediately
      |
[3s] Bot: [Response]  ← Haiku (fast model)

User: "What should I eat for optimal protein intake based on my training today?"
      |
      v
Bot: [typing...]  ← Appears immediately
      |           ← Persists for 6-8 seconds
[8s] Bot: [Detailed response]  ← Sonnet (quality model)
```

**User perception**: "Bot is responsive and working, just thinking"

## External Research

### Documentation

- [Telegram Bot API - sendChatAction](https://core.telegram.org/bots/api#sendchataction) - Official API for typing indicators
  - Key finding: Typing status lasts **only 5 seconds**, must be refreshed for longer operations
  - Recommendation: Re-send every 4-5 seconds during long operations

- [Python asyncio - Coroutines and Tasks](https://docs.python.org/3/library/asyncio-task.html) - Official Python async documentation
  - Key sections: `asyncio.create_task()` for fire-and-forget background tasks
  - Critical pattern: Maintain strong references to prevent garbage collection
  - Updated: January 10, 2026

- [Claude Haiku 4.5 vs Sonnet 4.5 Comparison](https://www.creolestudios.com/claude-haiku-4-5-vs-sonnet-4-5-comparison/)
  - **Speed**: Haiku is 4-5x faster (0.36s TTFT vs 0.64s for Sonnet)
  - **Throughput**: Similar (52.54 vs 50.88 tokens/sec)
  - **Quality**: Haiku achieves 90% of Sonnet's performance
  - **Pricing**: Haiku is $1/$5 per million tokens vs Sonnet's $3/$15

### Gotchas & Best Practices

**Telegram Typing Indicator**:
- ⚠️ **5-second timeout**: Status automatically clears after 5 seconds
- ✅ **Solution**: Implement loop that re-sends `send_action("typing")` every 4 seconds
- ✅ **Cleanup**: Cancel loop when response is sent

**Python asyncio Background Tasks**:
- ⚠️ **Garbage collection**: Tasks created with `create_task()` can be GC'd if no reference kept
- ✅ **Solution**: Store tasks in a set and remove on completion:
  ```python
  background_tasks = set()
  task = asyncio.create_task(coro())
  background_tasks.add(task)
  task.add_done_callback(background_tasks.discard)
  ```
- ⚠️ **Exception handling**: Background tasks swallow exceptions by default
- ✅ **Solution**: Wrap in try/except and log errors

**Claude Model Selection**:
- ✅ **Haiku for simple queries**: "show reminders", "what's my XP", greetings
- ✅ **Sonnet for complex queries**: Multi-step reasoning, nutrition analysis, personalized coaching
- ⚠️ **Context switching overhead**: Don't route if query classification takes >500ms

## Patterns to Mirror

### Pattern 1: Typing Indicator (Current Usage)

**FROM**: `src/bot.py:829-830`
```python
# Send typing indicator
await update.message.chat.send_action("typing")
```

**Current behavior**: Sent once at start, clears after 5 seconds (before LLM responds)

**What we'll mirror**: The `update.message.chat.send_action("typing")` call pattern, but in a loop

### Pattern 2: Simple In-Memory Caching

**FROM**: `src/utils/nutrition_search.py:12-14`
```python
# Simple in-memory cache with expiration
_cache: Dict[str, Tuple[Dict[Any, Any], datetime]] = {}
CACHE_DURATION = timedelta(hours=24)  # Cache for 24 hours
```

**Pattern to mirror**: Dict-based cache with TTL, check before expensive operation

### Pattern 3: Configuration Pattern

**FROM**: `src/config.py:26`
```python
AGENT_MODEL: str = os.getenv("AGENT_MODEL", "anthropic:claude-3-5-sonnet-latest")
```

**Pattern to mirror**: Use environment variables with sensible defaults for configuration

### Pattern 4: Async Database Operations

**FROM**: `src/bot.py:842-844`
```python
# Save user message and assistant response to database
await save_conversation_message(user_id, "user", text, message_type="text")
await save_conversation_message(user_id, "assistant", response, message_type="text")
```

**Pattern to mirror**: Sequential `await` for operations that must complete

**Contrast**: Mem0 operations (lines 847-848) DON'T need to block response:
```python
# Add to Mem0 for semantic memory and automatic fact extraction
mem0_manager.add_message(user_id, text, role="user", metadata={"message_type": "text"})
mem0_manager.add_message(user_id, response, role="assistant", metadata={"message_type": "text"})
```
**These should be fire-and-forget background tasks**

### Pattern 5: Test Structure

**FROM**: `tests/test_gamification_phase1.py` (example test file)
```python
# Test files in tests/ directory
# Naming convention: test_*.py
# Uses pytest framework
```

**Pattern to mirror**: Create `tests/test_performance_optimizations.py` for new functionality

## Files to Change

| File | Action | Justification |
|------|--------|---------------|
| `src/bot.py` | **UPDATE** | Add persistent typing indicator loop, move Mem0 to background, implement response caching |
| `src/config.py` | **UPDATE** | Add configuration for Haiku model and caching settings |
| `src/utils/response_cache.py` | **CREATE** | Simple response cache for common greetings (mirrors nutrition_search.py pattern) |
| `src/utils/query_classifier.py` | **CREATE** | Classify queries as simple/complex for model routing |
| `src/utils/async_helpers.py` | **CREATE** | Background task helpers (fire-and-forget pattern) |
| `tests/test_performance_optimizations.py` | **CREATE** | Unit tests for new performance features |
| `tests/integration/test_typing_indicator.py` | **CREATE** | Integration test for typing indicator behavior |
| `.env.example` | **UPDATE** | Add new environment variables for Haiku model and cache settings |
| `DEVELOPMENT.md` | **UPDATE** | Document new performance features and configuration |

## NOT Building

- ❌ **Response streaming**: Telegram doesn't support well, adds complexity
- ❌ **Redis caching**: In-memory cache sufficient for 4 users, avoid new dependency
- ❌ **Advanced query classification ML**: Simple heuristics sufficient for v1
- ❌ **User-specific model preferences**: All users get same routing logic for now
- ❌ **Metrics/monitoring dashboard**: Just log timings, don't build observability UI
- ❌ **A/B testing framework**: Deploy optimizations to all users
- ❌ **Database caching layer**: Current DB performance is excellent (10ms), not a bottleneck

## Minimal Viable Implementation

**Smallest change that delivers the feature**:

1. Add typing indicator loop (30 lines)
2. Wrap Mem0 calls in `create_task()` (5 lines)
3. Add dict-based greeting cache (20 lines)
4. Add simple query classifier (40 lines)
5. Route simple queries to Haiku (10 lines)

**Total new code**: ~105 lines
**Modified code**: ~20 lines
**Total effort**: 4-5 hours

## Tasks

### Task 1: CREATE `src/utils/async_helpers.py` - Background Task Helpers

**Why**: Need reusable pattern for fire-and-forget background tasks to move Mem0 operations off critical path

**Mirror**: Python asyncio best practices from [official docs](https://docs.python.org/3/library/asyncio-task.html)

**Do**:
```python
"""Async helper utilities for background tasks"""
import asyncio
import logging
from typing import Coroutine, Any, Set

logger = logging.getLogger(__name__)

# Global set to hold strong references to background tasks
_background_tasks: Set[asyncio.Task] = set()


def fire_and_forget(coro: Coroutine[Any, Any, None]) -> None:
    """
    Execute coroutine in background without blocking.

    Maintains strong reference to prevent garbage collection.
    Logs exceptions if task fails.

    Args:
        coro: Coroutine to execute

    Example:
        fire_and_forget(mem0_manager.add_message(user_id, text))
    """
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    task.add_done_callback(_log_task_exception)


def _log_task_exception(task: asyncio.Task) -> None:
    """Log exception if background task failed"""
    try:
        task.result()  # Raise exception if task failed
    except Exception as e:
        logger.error(f"Background task failed: {e}", exc_info=True)
```

**Don't**:
- Don't make this overly complex with task management, priorities, etc.
- Don't add async context managers or cleanup - keep it simple
- Don't add timeout handling - let tasks run to completion

**Verify**:
```bash
python -c "from src.utils.async_helpers import fire_and_forget; print('✓ Import successful')"
```

---

### Task 2: CREATE `src/utils/response_cache.py` - Simple Response Cache

**Why**: Eliminate 8-second LLM call for common greetings that don't need personalization

**Mirror**: `src/utils/nutrition_search.py:12-14` (simple dict cache with TTL)

**Do**:
```python
"""Simple in-memory response cache for common messages"""
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Cache configuration
CACHE_DURATION = timedelta(hours=24)  # Refresh daily to allow response variations
_cache: Dict[str, tuple[str, datetime]] = {}

# Pre-cached common responses (case-insensitive matching)
CACHED_RESPONSES: Dict[str, str] = {
    "hi": "Hey! How can I help you today?",
    "hello": "Hello! What can I do for you?",
    "hey": "Hey there! What's up?",
    "thanks": "You're welcome! 😊",
    "thank you": "Happy to help!",
    "thx": "No problem!",
    "bye": "Take care! See you later! 👋",
    "goodbye": "Goodbye! Talk to you soon!",
}


def get_cached_response(message: str) -> Optional[str]:
    """
    Get cached response for common messages.

    Args:
        message: User message (will be normalized to lowercase, stripped)

    Returns:
        Cached response if found and not expired, None otherwise
    """
    # Normalize message
    normalized = message.strip().lower()

    # Check if message is in cache
    if normalized not in CACHED_RESPONSES:
        return None

    # Return cached response
    cached_response = CACHED_RESPONSES[normalized]
    logger.info(f"Cache HIT for message: '{message}' -> using cached response")

    return cached_response


def is_cacheable(message: str) -> bool:
    """Check if message is a simple greeting/thanks that can be cached"""
    normalized = message.strip().lower()
    return normalized in CACHED_RESPONSES
```

**Don't**:
- Don't add dynamic caching (learning which responses to cache) - just static list
- Don't add per-user caching - same response for all users keeps it simple
- Don't add cache warming, preloading, or other complexity
- Don't use LRU cache decorator - we want explicit control

**Verify**:
```bash
python -c "from src.utils.response_cache import get_cached_response; assert get_cached_response('hi') == 'Hey! How can I help you today!'; print('✓ Cache working')"
```

---

### Task 3: CREATE `src/utils/query_classifier.py` - Simple Query Classifier

**Why**: Route simple queries to Haiku (fast) and complex queries to Sonnet (quality)

**Mirror**: None - this is new logic, but keep it simple (heuristic-based, not ML)

**Do**:
```python
"""Classify user queries as simple or complex for model routing"""
import logging
import re
from typing import Literal

logger = logging.getLogger(__name__)

QueryComplexity = Literal["simple", "complex"]

# Simple query patterns (case-insensitive)
SIMPLE_PATTERNS = [
    # Direct tool/data requests
    r"^show (my )?reminders?$",
    r"^list (my )?reminders?$",
    r"^what are my reminders?$",
    r"^(show|get|what'?s) (my )?xp$",
    r"^(show|get|what'?s) (my )?level$",
    r"^(show|get|what'?s) (my )?streaks?$",
    r"^(show|get|list) (my )?achievements?$",
    r"^daily dashboard$",
    r"^weekly dashboard$",
    r"^monthly dashboard$",
    r"^progress summary$",
    r"^(show|get) (my )?stats$",

    # Simple questions (short, no reasoning)
    r"^how much xp (do i have|have i earned)\??$",
    r"^am i (on a )?streak\??$",
    r"^what level am i\??$",
]

# Complex query indicators (presence of these suggests complex query)
COMPLEX_INDICATORS = [
    "why", "how should", "what should", "recommend", "advice", "help me",
    "explain", "analyze", "compare", "optimal", "best", "strategy",
    "yesterday", "last week", "this month", "trend", "pattern",
    "based on", "considering", "given that", "what if"
]


def classify_query(message: str) -> QueryComplexity:
    """
    Classify query as simple or complex for model routing.

    Simple queries: Direct data requests, simple lookups, tool invocations
    Complex queries: Reasoning, analysis, personalized advice, multi-step

    Args:
        message: User message

    Returns:
        "simple" for fast queries (use Haiku), "complex" for quality queries (use Sonnet)
    """
    normalized = message.strip().lower()

    # Very short messages are likely simple
    if len(normalized.split()) <= 3:
        logger.info(f"Query classified as SIMPLE (short): {message[:50]}")
        return "simple"

    # Check against simple patterns
    for pattern in SIMPLE_PATTERNS:
        if re.match(pattern, normalized):
            logger.info(f"Query classified as SIMPLE (pattern match): {message[:50]}")
            return "simple"

    # Check for complex indicators
    for indicator in COMPLEX_INDICATORS:
        if indicator in normalized:
            logger.info(f"Query classified as COMPLEX (contains '{indicator}'): {message[:50]}")
            return "complex"

    # Default to complex for safety (better quality)
    logger.info(f"Query classified as COMPLEX (default): {message[:50]}")
    return "complex"


def should_use_haiku(message: str) -> bool:
    """Convenience function: Returns True if query should use Haiku model"""
    return classify_query(message) == "simple"
```

**Don't**:
- Don't use ML/embeddings for classification - simple heuristics are fast and transparent
- Don't add confidence scores - binary decision is sufficient
- Don't add user-specific learning - same rules for all users
- Don't make it overly conservative - it's okay to occasionally use Haiku for borderline cases

**Verify**:
```bash
python -c "from src.utils.query_classifier import classify_query; assert classify_query('show my reminders') == 'simple'; assert classify_query('what should I eat today based on my goals?') == 'complex'; print('✓ Classifier working')"
```

---

### Task 4: UPDATE `src/config.py` - Add Haiku Model Configuration

**Why**: Need to configure Haiku model for fast query routing

**Mirror**: `src/config.py:26` (AGENT_MODEL pattern)

**Do**:
Add these lines after line 26:
```python
# Performance optimizations
AGENT_MODEL_FAST: str = os.getenv("AGENT_MODEL_FAST", "anthropic:claude-haiku-4-5-20251001")  # Fast model for simple queries
ENABLE_QUERY_ROUTING: bool = os.getenv("ENABLE_QUERY_ROUTING", "true").lower() == "true"  # Route simple queries to fast model
ENABLE_RESPONSE_CACHE: bool = os.getenv("ENABLE_RESPONSE_CACHE", "true").lower() == "true"  # Cache common greetings
```

**Don't**:
- Don't add complex configuration classes or validation logic
- Don't add per-user model preferences - keep it global
- Don't add model version management - just use latest

**Verify**:
```bash
python -c "from src.config import AGENT_MODEL_FAST, ENABLE_QUERY_ROUTING; print(f'✓ AGENT_MODEL_FAST={AGENT_MODEL_FAST}'); print(f'✓ ENABLE_QUERY_ROUTING={ENABLE_QUERY_ROUTING}')"
```

---

### Task 5: UPDATE `src/bot.py` - Implement Persistent Typing Indicator

**Why**: Current typing indicator expires after 5 seconds, but LLM takes 6-8 seconds

**Mirror**: `src/bot.py:829-830` (existing send_action call)

**Do**:

**Step 5a**: Add helper function after imports (around line 50):
```python
async def keep_typing_alive(update: Update, context: ContextTypes.DEFAULT_TYPE, stop_event: asyncio.Event) -> None:
    """
    Maintain typing indicator throughout long operations.

    Telegram's typing indicator expires after 5 seconds, but LLM calls take 6-10 seconds.
    This function refreshes the indicator every 4 seconds until stopped.

    Args:
        update: Telegram update object
        context: Telegram context
        stop_event: Event to signal when to stop sending typing indicators
    """
    try:
        while not stop_event.is_set():
            await update.message.chat.send_action("typing")
            await asyncio.sleep(4)  # Refresh every 4 seconds (before 5s timeout)
    except Exception as e:
        logger.error(f"Error in keep_typing_alive: {e}", exc_info=True)
```

**Step 5b**: Modify `handle_message` function (around line 829-838):

**REPLACE**:
```python
    # Send typing indicator
    await update.message.chat.send_action("typing")

    # Load conversation history from database (auto-filters unhelpful "I don't know" responses)
    message_history = await get_conversation_history(user_id, limit=20)

    # Get agent response with conversation history
    # Pass context.application for approval notifications
    response = await get_agent_response(
        user_id, text, memory_manager, reminder_manager, message_history,
        bot_application=context.application
    )
```

**WITH**:
```python
    # Start persistent typing indicator
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(keep_typing_alive(update, context, stop_typing))

    try:
        # Load conversation history from database (auto-filters unhelpful "I don't know" responses)
        message_history = await get_conversation_history(user_id, limit=20)

        # Get agent response with conversation history
        # Pass context.application for approval notifications
        response = await get_agent_response(
            user_id, text, memory_manager, reminder_manager, message_history,
            bot_application=context.application
        )
    finally:
        # Stop typing indicator
        stop_typing.set()
        await typing_task  # Wait for cleanup
```

**Don't**:
- Don't use threading - stick with asyncio
- Don't make typing interval configurable - 4 seconds is optimal
- Don't add retry logic - if typing fails, it's not critical

**Verify**: Manual test - send message and observe typing indicator persists throughout processing

---

### Task 6: UPDATE `src/bot.py` - Add Response Caching

**Why**: Eliminate 8-second LLM call for simple greetings

**Mirror**: Cache check pattern from nutrition_search.py

**Do**:

**Step 6a**: Add imports at top of file (around line 10):
```python
from src.utils.response_cache import get_cached_response, is_cacheable
from src.config import ENABLE_RESPONSE_CACHE
```

**Step 6b**: Add cache check in `handle_message` BEFORE typing indicator (around line 827):
```python
    # Check authorization (for active users)
    if not await is_authorized(user_id):
        return

    # NEW: Check cache for simple greetings (if enabled)
    if ENABLE_RESPONSE_CACHE and is_cacheable(text):
        cached_response = get_cached_response(text)
        if cached_response:
            await update.message.reply_text(cached_response)
            # Still save to conversation history
            await save_conversation_message(user_id, "user", text, message_type="text")
            await save_conversation_message(user_id, "assistant", cached_response, message_type="text")
            logger.info(f"Served cached response for: {text}")
            return

    # Start persistent typing indicator
    stop_typing = asyncio.Event()
    # ... (rest of handler)
```

**Don't**:
- Don't cache complex responses - only simple greetings
- Don't add cache invalidation logic - static responses don't need it
- Don't add metrics/analytics - just log cache hits

**Verify**:
```bash
# Send "hi" via Telegram
# Should respond instantly (<1s) with cached greeting
```

---

### Task 7: UPDATE `src/bot.py` - Move Mem0 to Background Tasks

**Why**: Mem0 embedding generation takes 0.7-1.5s and doesn't need to block response delivery

**Mirror**: Fire-and-forget pattern from async_helpers.py

**Do**:

**Step 7a**: Add import at top:
```python
from src.utils.async_helpers import fire_and_forget
```

**Step 7b**: Modify Mem0 calls (around line 847-848):

**REPLACE**:
```python
    # Add to Mem0 for semantic memory and automatic fact extraction
    mem0_manager.add_message(user_id, text, role="user", metadata={"message_type": "text"})
    mem0_manager.add_message(user_id, response, role="assistant", metadata={"message_type": "text"})
```

**WITH**:
```python
    # Add to Mem0 for semantic memory (background task - don't block response)
    async def save_to_mem0():
        """Save messages to Mem0 in background"""
        try:
            mem0_manager.add_message(user_id, text, role="user", metadata={"message_type": "text"})
            mem0_manager.add_message(user_id, response, role="assistant", metadata={"message_type": "text"})
            logger.info(f"Saved messages to Mem0 for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to save to Mem0: {e}", exc_info=True)

    fire_and_forget(save_to_mem0())
```

**Don't**:
- Don't await the task - defeats the purpose
- Don't add complex error recovery - just log and move on
- Don't make mem0 operations synchronous fallback - background only

**Verify**: Response should be 0.7-1.5s faster (check logs for timing)

---

### Task 8: UPDATE `src/agent/__init__.py` - Add Query Routing to Haiku

**Why**: Simple queries can use Haiku (2-3s) instead of Sonnet (6-8s) for 2-3x speedup

**Mirror**: Existing model selection pattern (lines 2665-2669)

**Do**:

**Step 8a**: Add imports at top:
```python
from src.utils.query_classifier import should_use_haiku
from src.config import AGENT_MODEL_FAST, ENABLE_QUERY_ROUTING
```

**Step 8b**: Modify `get_agent_response` function (around line 2659-2669):

**REPLACE**:
```python
    # Try with primary model (Claude) first
    try:
        logger.info(f"Attempting with primary model: {AGENT_MODEL}")
        # ... rest of try block

        dynamic_agent = Agent(
            model=AGENT_MODEL,
            system_prompt=system_prompt,
            deps_type=AgentDeps,
        )
```

**WITH**:
```python
    # Select model based on query complexity (if routing enabled)
    selected_model = AGENT_MODEL
    if ENABLE_QUERY_ROUTING and should_use_haiku(user_message):
        selected_model = AGENT_MODEL_FAST
        logger.info(f"Routing to fast model: {selected_model} for simple query")

    # Try with selected model first
    try:
        logger.info(f"Attempting with model: {selected_model}")
        # ... rest of try block

        dynamic_agent = Agent(
            model=selected_model,
            system_prompt=system_prompt,
            deps_type=AgentDeps,
        )
```

**Don't**:
- Don't add automatic fallback to Sonnet if Haiku fails - let existing fallback logic handle it
- Don't log full query text - only first 50 chars for privacy
- Don't add per-user routing preferences - global routing for now

**Verify**:
```bash
# Send "show my reminders" via Telegram
# Check logs - should say "Routing to fast model: anthropic:claude-haiku-4-5"
# Response should be 2-3x faster than usual
```

---

### Task 9: UPDATE `.env.example` - Document New Configuration

**Why**: New environment variables need to be documented for deployment

**Mirror**: Existing .env.example format

**Do**:

Add these lines after the `AGENT_MODEL` entry:
```bash
# Performance Optimizations
AGENT_MODEL_FAST=anthropic:claude-haiku-4-5-20251001  # Fast model for simple queries
ENABLE_QUERY_ROUTING=true  # Route simple queries to fast model (true/false)
ENABLE_RESPONSE_CACHE=true  # Cache common greetings for instant responses (true/false)
```

**Don't**:
- Don't add sensitive values - this is just an example file
- Don't add extensive comments - keep it brief
- Don't add optional/advanced settings - just the essentials

**Verify**: Check that `.env.example` can be copied to `.env` and works

---

### Task 10: CREATE `tests/test_performance_optimizations.py` - Unit Tests

**Why**: Validate new utilities work correctly

**Mirror**: Existing test file structure in `tests/test_memory_architecture.py`

**Do**:
```python
"""Tests for performance optimization utilities"""
import pytest
import asyncio
from src.utils.response_cache import get_cached_response, is_cacheable
from src.utils.query_classifier import classify_query, should_use_haiku
from src.utils.async_helpers import fire_and_forget


class TestResponseCache:
    """Test response caching functionality"""

    def test_cacheable_greetings(self):
        """Test that common greetings are cached"""
        assert is_cacheable("hi")
        assert is_cacheable("HI")  # Case insensitive
        assert is_cacheable("  hello  ")  # Whitespace handling
        assert is_cacheable("thanks")
        assert is_cacheable("bye")

    def test_non_cacheable_messages(self):
        """Test that complex messages are not cached"""
        assert not is_cacheable("what should I eat today?")
        assert not is_cacheable("show my reminders")
        assert not is_cacheable("help me with my nutrition plan")

    def test_cached_response_retrieval(self):
        """Test retrieving cached responses"""
        response = get_cached_response("hi")
        assert response is not None
        assert "help" in response.lower() or "hey" in response.lower()

        # Non-cached message returns None
        assert get_cached_response("random message") is None


class TestQueryClassifier:
    """Test query classification for model routing"""

    def test_simple_queries(self):
        """Test that simple queries are classified correctly"""
        assert classify_query("show my reminders") == "simple"
        assert classify_query("what's my xp") == "simple"
        assert classify_query("list my achievements") == "simple"
        assert classify_query("daily dashboard") == "simple"

    def test_complex_queries(self):
        """Test that complex queries are classified correctly"""
        assert classify_query("what should I eat today based on my goals?") == "complex"
        assert classify_query("why am I not making progress?") == "complex"
        assert classify_query("help me optimize my nutrition") == "complex"
        assert classify_query("analyze my food from yesterday") == "complex"

    def test_should_use_haiku(self):
        """Test convenience function for Haiku routing"""
        assert should_use_haiku("show reminders") is True
        assert should_use_haiku("what should I eat?") is False


class TestAsyncHelpers:
    """Test background task helpers"""

    @pytest.mark.asyncio
    async def test_fire_and_forget(self):
        """Test that fire_and_forget executes tasks without blocking"""
        result = []

        async def background_task():
            await asyncio.sleep(0.1)
            result.append("done")

        # Fire and forget - should not block
        fire_and_forget(background_task())

        # Task hasn't completed yet (no blocking)
        assert len(result) == 0

        # Wait for task to complete
        await asyncio.sleep(0.2)
        assert result == ["done"]

    @pytest.mark.asyncio
    async def test_fire_and_forget_exception_handling(self):
        """Test that exceptions in background tasks are logged, not raised"""
        async def failing_task():
            raise ValueError("Test error")

        # Should not raise - exceptions are logged
        fire_and_forget(failing_task())
        await asyncio.sleep(0.1)  # Let task fail
```

**Don't**:
- Don't test integration with Telegram API - that's for integration tests
- Don't test LLM models - too slow and non-deterministic
- Don't mock everything - test real logic where possible

**Verify**:
```bash
pytest tests/test_performance_optimizations.py -v
```

---

### Task 11: CREATE `tests/integration/test_typing_indicator.py` - Integration Test

**Why**: Validate typing indicator behavior with actual bot

**Mirror**: Existing integration test structure

**Do**:
```python
"""Integration tests for typing indicator behavior"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


class TestTypingIndicator:
    """Test typing indicator persistence during long operations"""

    @pytest.mark.asyncio
    async def test_typing_indicator_refreshes_during_long_operation(self):
        """Test that typing indicator is refreshed every 4 seconds"""
        # Mock update and context objects
        update = MagicMock()
        update.message.chat.send_action = AsyncMock()
        context = MagicMock()

        stop_event = asyncio.Event()

        # Import the function
        from src.bot import keep_typing_alive

        # Start typing indicator
        task = asyncio.create_task(keep_typing_alive(update, context, stop_event))

        # Let it run for 10 seconds (should send 2-3 times)
        await asyncio.sleep(10)

        # Stop it
        stop_event.set()
        await task

        # Verify send_action was called multiple times (at least 2)
        assert update.message.chat.send_action.call_count >= 2

        # Verify all calls were with "typing"
        for call in update.message.chat.send_action.call_args_list:
            assert call[0][0] == "typing"

    @pytest.mark.asyncio
    async def test_typing_indicator_stops_on_event(self):
        """Test that typing indicator stops when event is set"""
        update = MagicMock()
        update.message.chat.send_action = AsyncMock()
        context = MagicMock()

        stop_event = asyncio.Event()

        from src.bot import keep_typing_alive

        # Start typing indicator
        task = asyncio.create_task(keep_typing_alive(update, context, stop_event))

        # Let it send once
        await asyncio.sleep(1)

        # Stop immediately
        stop_event.set()
        await task

        # Should have sent only 1-2 times (initial + maybe one refresh)
        assert update.message.chat.send_action.call_count <= 2
```

**Don't**:
- Don't test with real Telegram API - use mocks
- Don't add sleep times >10 seconds - tests should be fast
- Don't test error recovery extensively - basic coverage is enough

**Verify**:
```bash
pytest tests/integration/test_typing_indicator.py -v
```

---

### Task 12: UPDATE `DEVELOPMENT.md` - Document Performance Features

**Why**: Developers need to understand new performance optimizations

**Mirror**: Existing DEVELOPMENT.md documentation style

**Do**:

Add new section after deployment sections:
```markdown
## Performance Optimizations

### Response Time Improvements

The bot implements several optimizations to improve perceived response time:

1. **Persistent Typing Indicator**: Telegram's typing indicator expires after 5 seconds, but LLM calls take 6-10 seconds. The bot refreshes the indicator every 4 seconds to maintain user feedback.

2. **Response Caching**: Common greetings ("hi", "thanks", etc.) are cached and served instantly without calling the LLM. This reduces response time from 8s to <0.1s for ~20% of messages.

3. **Background Tasks**: Mem0 embedding generation (0.7-1.5s) is moved to background tasks using `asyncio.create_task()`, reducing perceived response time.

4. **Query Routing**: Simple queries ("show reminders", "what's my XP") are routed to Claude Haiku (2-3s) instead of Sonnet (6-8s) for 2-3x faster responses.

### Configuration

Configure performance features in `.env`:

```bash
# Fast model for simple queries
AGENT_MODEL_FAST=anthropic:claude-haiku-4-5-20251001

# Enable/disable query routing
ENABLE_QUERY_ROUTING=true

# Enable/disable response caching
ENABLE_RESPONSE_CACHE=true
```

### Metrics

Measured improvements:
- **Cached responses**: 8s → 0.1s (80x faster)
- **Simple queries with Haiku**: 8s → 3s (2.7x faster)
- **Background Mem0**: -0.7-1.5s perceived latency
- **Typing indicator**: Dramatically improves user perception

### Debugging

To debug performance:

1. Check logs for query routing:
   ```
   Routing to fast model: anthropic:claude-haiku-4-5 for simple query
   ```

2. Check logs for cache hits:
   ```
   Cache HIT for message: 'hi' -> using cached response
   ```

3. Check logs for background task completion:
   ```
   Saved messages to Mem0 for user 7376426503
   ```
```

**Don't**:
- Don't add extensive architecture diagrams - keep it practical
- Don't document internal implementation details - just user-facing behavior
- Don't add performance benchmarking instructions - just basic metrics

**Verify**: Read through documentation to ensure clarity

---

## Validation Strategy

### Automated Checks

- [ ] `python -m py_compile src/bot.py` - Python syntax valid
- [ ] `python -m py_compile src/utils/*.py` - All new utilities compile
- [ ] `pytest tests/test_performance_optimizations.py -v` - Unit tests pass
- [ ] `pytest tests/integration/test_typing_indicator.py -v` - Integration tests pass
- [ ] `grep -r "import asyncio" src/` - Verify asyncio used correctly
- [ ] `grep -r "mem0_manager.add_message" src/bot.py` - Verify wrapped in fire_and_forget

### New Tests to Write

| Test File | Test Case | What It Validates |
|-----------|-----------|-------------------|
| `test_performance_optimizations.py` | `test_cacheable_greetings` | Greeting detection works |
| `test_performance_optimizations.py` | `test_cached_response_retrieval` | Cache returns correct responses |
| `test_performance_optimizations.py` | `test_simple_queries` | Query classifier detects simple queries |
| `test_performance_optimizations.py` | `test_complex_queries` | Query classifier detects complex queries |
| `test_performance_optimizations.py` | `test_fire_and_forget` | Background tasks execute without blocking |
| `test_typing_indicator.py` | `test_typing_indicator_refreshes` | Typing indicator persists >5 seconds |
| `test_typing_indicator.py` | `test_typing_indicator_stops` | Typing stops when response sent |

### Manual/E2E Validation

**Test 1: Cached Response Speed**
```bash
# Via Telegram:
1. Send message: "hi"
2. Measure response time (should be <0.5s)
3. Check logs for "Cache HIT"
4. Verify response is a greeting

Expected: Instant response (<0.5s), log shows cache hit
```

**Test 2: Typing Indicator Persistence**
```bash
# Via Telegram:
1. Send complex query: "What should I eat today based on my training goals?"
2. Observe typing indicator
3. Verify it persists throughout 6-8s wait
4. Verify it disappears when response arrives

Expected: Typing indicator visible continuously, no gaps
```

**Test 3: Query Routing to Haiku**
```bash
# Via Telegram:
1. Send simple query: "show my reminders"
2. Check logs for "Routing to fast model: anthropic:claude-haiku-4-5"
3. Measure response time (should be 2-4s, not 6-8s)
4. Verify response quality is acceptable

Expected: Faster response, log shows Haiku routing, correct data returned
```

**Test 4: Background Mem0 (Non-Blocking)**
```bash
# Via Telegram:
1. Send message: "I ate chicken and rice for lunch"
2. Verify you receive response quickly
3. Check logs after response - should see "Saved messages to Mem0" AFTER response
4. Query Mem0: "What did I eat?" - should retrieve the saved memory

Expected: Response not delayed by Mem0, memory still saved correctly
```

**Test 5: Complex Query Still Uses Sonnet**
```bash
# Via Telegram:
1. Send complex query: "Analyze my nutrition from yesterday and suggest improvements"
2. Check logs - should NOT see "Routing to fast model"
3. Should use default Sonnet model
4. Verify response quality is high (detailed analysis)

Expected: Uses Sonnet (high quality), takes 6-8s but with typing indicator
```

### Edge Cases to Test

- [ ] **Very long message (>500 chars)**: Should classify as complex, use Sonnet
- [ ] **Mixed case greeting**: "HeLLo" should still cache-hit
- [ ] **Greeting with typo**: "helo" should NOT cache-hit (spell check out of scope)
- [ ] **Concurrent messages**: Send 2 messages rapidly, both should get typing indicators
- [ ] **Mem0 failure**: If Mem0 throws exception, response should still be sent
- [ ] **Haiku unavailable**: Should fallback to OpenAI (existing fallback logic)
- [ ] **Cache disabled**: `ENABLE_RESPONSE_CACHE=false` should bypass cache
- [ ] **Routing disabled**: `ENABLE_QUERY_ROUTING=false` should use Sonnet for all
- [ ] **Empty message**: Should not crash cache or classifier
- [ ] **Special characters in message**: e.g., "hi! 😊" should still cache-hit (after normalization)

### Regression Check

- [ ] Existing simple messages still work: Send "show my reminders", verify response
- [ ] Existing complex queries still work: Send "what did I eat yesterday?", verify analysis
- [ ] Tool calling still works: Verify reminders, XP, streaks, achievements
- [ ] Conversation history still persists: Send multiple messages, verify context maintained
- [ ] Photo analysis still works: Send food photo, verify calorie estimation
- [ ] Error handling still works: Send invalid command, verify graceful error message

### Performance Benchmarking

**Before Optimizations** (baseline):
```
Simple greeting: 8.2s
Simple query: 8.5s
Complex query: 9.1s
Mem0 blocking: 0.9s
```

**After Optimizations** (target):
```
Simple greeting (cached): <0.5s (16x faster)
Simple query (Haiku): 3.0s (2.8x faster)
Complex query (Sonnet): 7.2s (1.3x faster, saved Mem0 time)
Mem0 non-blocking: 0s perceived (moved to background)
```

**Measurement approach**:
```python
import time

start = time.time()
# Send message via Telegram
# Wait for response
end = time.time()

print(f"Response time: {end - start:.1f}s")
```

## Risks

**Risk 1: Typing Indicator Spam**
- **What**: Sending `send_action("typing")` every 4 seconds could trigger rate limits
- **Likelihood**: Low (Telegram rate limits are generous for bot actions)
- **Mitigation**: Monitor logs for rate limit errors, increase interval to 5s if needed

**Risk 2: Haiku Quality Degradation**
- **What**: Users notice lower quality responses for simple queries
- **Likelihood**: Medium (Haiku is 90% of Sonnet quality)
- **Mitigation**: Conservative classification (default to complex), easy to disable via env var

**Risk 3: Background Task Memory Leak**
- **What**: Background tasks accumulate and consume memory
- **Likelihood**: Low (tasks are short-lived, removed on completion)
- **Mitigation**: Strong reference management with `add_done_callback(set.discard)`

**Risk 4: Cache Staleness**
- **What**: Cached greetings become stale or inappropriate
- **Likelihood**: Very Low (greetings are timeless)
- **Mitigation**: Static cache with manual updates, can add TTL if needed

**Risk 5: Query Misclassification**
- **What**: Complex query routed to Haiku, produces poor response
- **Likelihood**: Medium initially, decreases with pattern tuning
- **Mitigation**: Log all classifications, monitor user feedback, adjust patterns

---

## Success Metrics

**Primary KPIs**:
- Cached response time: <0.5s (from 8s)
- Simple query response time: <4s (from 8s)
- User perception: "Fast and responsive" (from "slow and broken")

**Secondary KPIs**:
- Cache hit rate: >15% of messages (greetings are ~20% of traffic)
- Haiku routing rate: >30% of non-cached messages
- Background task success rate: >99% (Mem0 saves)

**Qualitative**:
- No user complaints about "bot not responding"
- Positive feedback on responsiveness
- No degradation in response quality for complex queries

---

## Implementation Checklist

**Phase 1: Core Infrastructure** (1-2 hours)
- [ ] Create `src/utils/async_helpers.py` with fire_and_forget pattern
- [ ] Create `src/utils/response_cache.py` with static greeting cache
- [ ] Create `src/utils/query_classifier.py` with heuristic classifier
- [ ] Update `src/config.py` with new env vars
- [ ] Update `.env.example` with documentation

**Phase 2: Bot Integration** (2-3 hours)
- [ ] Implement persistent typing indicator in `src/bot.py`
- [ ] Add response caching check in `handle_message`
- [ ] Wrap Mem0 calls in fire_and_forget
- [ ] Add query routing to Haiku in `src/agent/__init__.py`

**Phase 3: Testing** (1 hour)
- [ ] Write unit tests in `tests/test_performance_optimizations.py`
- [ ] Write integration test in `tests/integration/test_typing_indicator.py`
- [ ] Run all tests and verify passing
- [ ] Manual E2E testing via Telegram

**Phase 4: Documentation** (30 min)
- [ ] Update `DEVELOPMENT.md` with performance features
- [ ] Update `.env.example` with clear descriptions
- [ ] Add inline code comments for complex logic

**Phase 5: Deployment** (30 min)
- [ ] Deploy to production environment
- [ ] Monitor logs for errors
- [ ] Collect initial performance metrics
- [ ] Verify user experience improvement

**Total estimated time**: 4-5 hours

---

## Sources

- [Telegram Bot API - sendChatAction](https://core.telegram.org/bots/api#sendchataction)
- [Python asyncio - Coroutines and Tasks](https://docs.python.org/3/library/asyncio-task.html)
- [Claude Haiku 4.5 vs Sonnet 4.5 Comparison](https://www.creolestudios.com/claude-haiku-4-5-vs-sonnet-4-5-comparison/)
- [Telegram API Best Practices - Typing Indicators](https://community.latenode.com/t/how-to-simulate-bot-typing-in-telegram-chats/16193)
- [Python Background Tasks with asyncio](https://www.backendmesh.com/asyncio-and-background-tasks-in-python/)
