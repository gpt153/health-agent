# Circuit Breaker and Resilience Pattern Implementation Plan

**Issue**: #80
**Epic**: Phase 3 Long-Term Architecture
**Estimated Time**: 8 hours
**Priority**: MEDIUM

## Executive Summary

This plan implements the Circuit Breaker pattern to protect the health-agent bot from cascading failures when external APIs (OpenAI, Anthropic, USDA) experience outages or timeouts. The implementation ensures graceful degradation and maintains service availability even when dependencies fail.

---

## 1. Current State Analysis

### 1.1 External API Dependencies

The codebase currently makes direct API calls to three external services:

| API | Usage Location | Purpose | Current Error Handling |
|-----|----------------|---------|----------------------|
| **OpenAI** | `src/utils/vision.py` | Vision analysis (GPT-4o-mini) | Try-catch with mock fallback |
| **Anthropic** | `src/utils/vision.py` | Vision analysis (Claude 3.5 Sonnet) | Try-catch with mock fallback |
| **Anthropic** | `src/bot.py`, `src/agent/nutrition_consensus.py`, `src/utils/food_text_parser.py` | Text generation (PydanticAI) | Basic exception handling |
| **USDA** | `src/utils/nutrition_search.py` | Nutrition database lookup | 5s timeout + try-catch |
| **Web Search** | `src/utils/web_nutrition_search.py` | Fallback nutrition data | Try-catch per source |

### 1.2 Current Resilience Mechanisms

**Strengths:**
- USDA API has 5-second timeout (`API_TIMEOUT = 5.0`)
- 24-hour in-memory caching for USDA and web search
- Vision AI falls back to mock data on failure
- Web nutrition search tries multiple sources (Nutritionix, MyFitnessPal, AI)

**Gaps (to be addressed):**
- ❌ No circuit breaker - repeated failures cause delays
- ❌ No retry logic - transient failures aren't retried
- ❌ No exponential backoff - retry storms possible
- ❌ No metrics/monitoring - failures are invisible
- ❌ OpenAI/Anthropic client creation not reused - potential connection leaks
- ❌ USDA fallback strategy limited - only falls back to web search

---

## 2. Architecture Design

### 2.1 Circuit Breaker Pattern

We'll implement a **per-API circuit breaker** using the state machine:

```
┌─────────┐
│ CLOSED  │ ◄─── Normal operation (requests pass through)
└────┬────┘
     │ 5 consecutive failures
     ▼
┌─────────┐
│  OPEN   │ ◄─── Fail fast (reject requests immediately)
└────┬────┘
     │ After 60s timeout
     ▼
┌──────────┐
│HALF_OPEN │ ◄─── Test recovery (allow 1 request)
└────┬─────┘
     │
     ├─ Success → CLOSED
     └─ Failure → OPEN
```

**Configuration per API:**
- **Failure Threshold**: 5 consecutive failures
- **Open Timeout**: 60 seconds
- **Half-Open Test**: 1 request

### 2.2 Library Selection

**Option 1: `pybreaker` (Recommended)**
- Mature, well-tested library
- Supports async operations
- Built-in metrics and listeners
- Configuration: `pip install pybreaker`

**Option 2: Custom Implementation**
- Full control over behavior
- No external dependency
- More development time

**Decision**: Use `pybreaker` for reliability and speed of implementation.

### 2.3 Retry Logic with Exponential Backoff

**Strategy**: Retry transient errors before marking as failure

```python
# Retry configuration
MAX_RETRIES = 3
BASE_DELAY = 1.0  # seconds
MAX_DELAY = 30.0  # seconds
JITTER = 0.1  # 10% random jitter

# Exponential backoff schedule:
# Attempt 1: fail immediately
# Attempt 2: wait 1s + jitter
# Attempt 3: wait 2s + jitter
# Attempt 4: wait 4s + jitter
# Total max delay: ~7s before circuit breaker sees failure
```

**Jitter**: Prevents thundering herd problem when many requests retry simultaneously.

**Transient vs Permanent Errors**:
- **Retry**: Timeouts, 429 (rate limit), 500/502/503 (server errors)
- **Don't Retry**: 400/401/403 (client errors), invalid API keys

### 2.4 Fallback Strategies

#### 2.4.1 Vision AI (OpenAI/Anthropic)

**Current**: Try OpenAI → fallback to mock
**Enhanced**:

```
1. Try primary vision model (from config)
   ├─ Success → return result
   └─ Circuit OPEN or failure
       └─ Try alternative vision model
           ├─ Success → return result
           └─ Circuit OPEN or failure
               └─ Return mock result + notify user
```

**Configuration**:
```python
VISION_MODEL_PRIMARY = "openai:gpt-4o-mini"
VISION_MODEL_FALLBACK = "anthropic:claude-3-5-sonnet-latest"
```

#### 2.4.2 Text Generation (Anthropic via PydanticAI)

**Current**: Direct PydanticAI calls to Anthropic
**Enhanced**:

```
1. Try Anthropic (Claude)
   ├─ Success → return result
   └─ Circuit OPEN or failure
       └─ Try OpenAI (GPT-4o)
           ├─ Success → return result
           └─ Circuit OPEN or failure
               └─ Return cached response (if available)
                   └─ Otherwise: user-friendly error message
```

**Note**: PydanticAI abstracts the LLM layer, so we'll wrap the agent calls.

#### 2.4.3 USDA Nutrition Database

**Current**: Try USDA → fallback to web search → fallback to AI estimate
**Enhanced**: Add local nutrition database cache

```
1. Try USDA API
   ├─ Success → cache + return
   └─ Circuit OPEN or failure
       └─ Check local nutrition database (SQLite)
           ├─ Found → return cached data
           └─ Not found → Try web search
               ├─ Found → cache + return
               └─ Not found → Use AI estimate
```

**Local Database**: Pre-populated SQLite database with top 500 common foods from USDA.

---

## 3. Implementation Plan

### 3.1 File Structure

```
src/
├── resilience/
│   ├── __init__.py
│   ├── circuit_breaker.py      # Circuit breaker wrapper
│   ├── retry.py                 # Retry logic with backoff
│   ├── fallback.py              # Fallback orchestration
│   ├── metrics.py               # Metrics collection
│   └── config.py                # Resilience configuration
├── db/
│   └── nutrition_cache.py       # Local nutrition database
└── (existing files to modify)
```

### 3.2 Implementation Steps

#### Step 1: Install Dependencies
**File**: `requirements.txt`

```diff
+ pybreaker>=1.0.0
+ prometheus-client>=0.20.0  # For metrics
```

#### Step 2: Create Circuit Breaker Module
**File**: `src/resilience/circuit_breaker.py`

```python
"""Circuit breaker implementation for external APIs"""
import pybreaker
import logging
from typing import Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)

# Circuit breaker configurations
OPENAI_BREAKER = pybreaker.CircuitBreaker(
    fail_max=5,
    timeout_duration=60,
    name="openai_api",
    listeners=[CircuitBreakerListener()]
)

ANTHROPIC_BREAKER = pybreaker.CircuitBreaker(
    fail_max=5,
    timeout_duration=60,
    name="anthropic_api",
    listeners=[CircuitBreakerListener()]
)

USDA_BREAKER = pybreaker.CircuitBreaker(
    fail_max=5,
    timeout_duration=60,
    name="usda_api",
    listeners=[CircuitBreakerListener()]
)

class CircuitBreakerListener(pybreaker.CircuitBreakerListener):
    """Listener to log circuit breaker state changes"""

    def state_change(self, cb, old_state, new_state):
        logger.warning(f"Circuit breaker {cb.name}: {old_state.name} -> {new_state.name}")
        # Emit metrics (see Step 5)

    def failure(self, cb, exc):
        logger.error(f"Circuit breaker {cb.name} recorded failure: {exc}")

    def success(self, cb):
        logger.debug(f"Circuit breaker {cb.name} recorded success")

def with_circuit_breaker(breaker: pybreaker.CircuitBreaker):
    """Decorator to wrap async functions with circuit breaker"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await breaker.call_async(func, *args, **kwargs)
            except pybreaker.CircuitBreakerError as e:
                logger.warning(f"Circuit breaker {breaker.name} is OPEN")
                raise
        return wrapper
    return decorator
```

#### Step 3: Create Retry Logic Module
**File**: `src/resilience/retry.py`

```python
"""Retry logic with exponential backoff and jitter"""
import asyncio
import random
import logging
from typing import Callable, Any, Type
from functools import wraps
import httpx

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BASE_DELAY = 1.0
MAX_DELAY = 30.0
JITTER = 0.1

# Errors that should trigger retry
RETRYABLE_ERRORS = (
    httpx.TimeoutException,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.HTTPStatusError,  # Will check status code
)

def is_retryable_error(exc: Exception) -> bool:
    """Determine if error is transient and should be retried"""
    if isinstance(exc, httpx.HTTPStatusError):
        # Retry on rate limits and server errors
        return exc.response.status_code in [429, 500, 502, 503, 504]

    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectTimeout, httpx.ReadTimeout)):
        return True

    # OpenAI/Anthropic specific errors
    if hasattr(exc, '__class__'):
        class_name = exc.__class__.__name__
        if class_name in ['RateLimitError', 'APITimeoutError', 'InternalServerError']:
            return True

    return False

def calculate_backoff(attempt: int) -> float:
    """Calculate exponential backoff with jitter"""
    delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
    jitter = random.uniform(-JITTER * delay, JITTER * delay)
    return delay + jitter

async def retry_with_backoff(
    func: Callable,
    *args,
    max_retries: int = MAX_RETRIES,
    **kwargs
) -> Any:
    """
    Retry async function with exponential backoff.

    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        *args, **kwargs: Arguments to pass to func

    Returns:
        Result from func

    Raises:
        Last exception if all retries exhausted
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)

        except Exception as e:
            last_exception = e

            if attempt == max_retries:
                logger.error(f"All {max_retries} retries exhausted for {func.__name__}")
                raise

            if not is_retryable_error(e):
                logger.warning(f"Non-retryable error for {func.__name__}: {e}")
                raise

            backoff = calculate_backoff(attempt)
            logger.info(f"Retry {attempt + 1}/{max_retries} for {func.__name__} after {backoff:.2f}s")
            await asyncio.sleep(backoff)

    # Should never reach here
    raise last_exception

def with_retry(max_retries: int = MAX_RETRIES):
    """Decorator to add retry logic to async functions"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            return await retry_with_backoff(func, *args, max_retries=max_retries, **kwargs)
        return wrapper
    return decorator
```

#### Step 4: Create Fallback Orchestration Module
**File**: `src/resilience/fallback.py`

```python
"""Fallback strategies for API failures"""
import logging
from typing import Optional, Any, Callable, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class FallbackStrategy:
    """Define a fallback strategy"""
    name: str
    handler: Callable
    priority: int  # Lower = higher priority

async def execute_with_fallbacks(
    strategies: List[FallbackStrategy],
    *args,
    **kwargs
) -> Any:
    """
    Execute strategies in order until one succeeds.

    Args:
        strategies: List of FallbackStrategy in priority order
        *args, **kwargs: Arguments to pass to handlers

    Returns:
        Result from first successful strategy

    Raises:
        Exception if all strategies fail
    """
    strategies = sorted(strategies, key=lambda s: s.priority)

    last_exception = None

    for strategy in strategies:
        try:
            logger.info(f"Trying fallback strategy: {strategy.name}")
            result = await strategy.handler(*args, **kwargs)
            logger.info(f"Fallback strategy '{strategy.name}' succeeded")
            return result

        except Exception as e:
            logger.warning(f"Fallback strategy '{strategy.name}' failed: {e}")
            last_exception = e
            continue

    logger.error("All fallback strategies exhausted")
    raise last_exception or Exception("All fallback strategies failed")
```

#### Step 5: Create Metrics Module
**File**: `src/resilience/metrics.py`

```python
"""Prometheus metrics for resilience patterns"""
from prometheus_client import Counter, Histogram, Gauge, Enum

# Circuit breaker state
circuit_breaker_state = Enum(
    'circuit_breaker_state',
    'Current state of circuit breaker',
    ['api'],
    states=['closed', 'open', 'half_open']
)

# API call metrics
api_calls_total = Counter(
    'api_calls_total',
    'Total number of API calls',
    ['api', 'status']  # status: success, failure, circuit_open
)

api_call_duration = Histogram(
    'api_call_duration_seconds',
    'Duration of API calls',
    ['api']
)

api_failures_total = Counter(
    'api_failures_total',
    'Total number of API failures',
    ['api', 'error_type']
)

api_retries_total = Counter(
    'api_retries_total',
    'Total number of retry attempts',
    ['api']
)

# Fallback metrics
fallback_executions_total = Counter(
    'fallback_executions_total',
    'Total number of fallback executions',
    ['primary_api', 'fallback_strategy', 'status']
)

def record_circuit_breaker_state(api: str, state: str):
    """Record circuit breaker state change"""
    circuit_breaker_state.labels(api=api).state(state)

def record_api_call(api: str, success: bool, duration: float):
    """Record API call metrics"""
    status = 'success' if success else 'failure'
    api_calls_total.labels(api=api, status=status).inc()
    api_call_duration.labels(api=api).observe(duration)

def record_api_failure(api: str, error_type: str):
    """Record API failure"""
    api_failures_total.labels(api=api, error_type=error_type).inc()

def record_retry(api: str):
    """Record retry attempt"""
    api_retries_total.labels(api=api).inc()

def record_fallback(primary_api: str, fallback: str, success: bool):
    """Record fallback execution"""
    status = 'success' if success else 'failure'
    fallback_executions_total.labels(
        primary_api=primary_api,
        fallback_strategy=fallback,
        status=status
    ).inc()
```

#### Step 6: Create Local Nutrition Database
**File**: `src/db/nutrition_cache.py`

```python
"""Local SQLite cache for common foods"""
import sqlite3
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "nutrition_cache.db"

def init_nutrition_cache():
    """Initialize SQLite database with common foods"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nutrition (
            food_name TEXT PRIMARY KEY,
            description TEXT,
            calories_per_100g REAL,
            protein_per_100g REAL,
            carbs_per_100g REAL,
            fat_per_100g REAL,
            fiber_per_100g REAL,
            sodium_per_100g REAL,
            source TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Pre-populate with top 100 common foods from USDA
    common_foods = [
        ("chicken breast", "Chicken, broilers or fryers, breast, meat only, cooked, roasted",
         165, 31.0, 0.0, 3.6, 0.0, 74, "USDA"),
        ("egg", "Egg, whole, cooked, hard-boiled",
         155, 12.6, 1.1, 10.6, 0.0, 124, "USDA"),
        ("rice", "Rice, white, long-grain, regular, cooked",
         130, 2.7, 28.2, 0.3, 0.4, 1, "USDA"),
        # ... (add top 100 common foods)
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO nutrition
        (food_name, description, calories_per_100g, protein_per_100g,
         carbs_per_100g, fat_per_100g, fiber_per_100g, sodium_per_100g, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, common_foods)

    conn.commit()
    conn.close()
    logger.info(f"Nutrition cache initialized at {DB_PATH}")

async def get_from_cache(food_name: str) -> Optional[Dict[str, Any]]:
    """Retrieve food from local cache"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM nutrition WHERE food_name = ? COLLATE NOCASE
    """, (food_name.lower(),))

    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "food_name": row[0],
            "description": row[1],
            "calories_per_100g": row[2],
            "protein_per_100g": row[3],
            "carbs_per_100g": row[4],
            "fat_per_100g": row[5],
            "fiber_per_100g": row[6],
            "sodium_per_100g": row[7],
            "source": row[8]
        }

    return None

async def add_to_cache(food_name: str, nutrition_data: Dict[str, Any]):
    """Add food to local cache"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO nutrition
        (food_name, description, calories_per_100g, protein_per_100g,
         carbs_per_100g, fat_per_100g, fiber_per_100g, sodium_per_100g, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        food_name.lower(),
        nutrition_data.get("description", ""),
        nutrition_data.get("calories_per_100g", 0),
        nutrition_data.get("protein_per_100g", 0),
        nutrition_data.get("carbs_per_100g", 0),
        nutrition_data.get("fat_per_100g", 0),
        nutrition_data.get("fiber_per_100g", 0),
        nutrition_data.get("sodium_per_100g", 0),
        nutrition_data.get("source", "unknown")
    ))

    conn.commit()
    conn.close()
```

#### Step 7: Update Vision AI Module
**File**: `src/utils/vision.py`

**Changes**:
1. Wrap OpenAI/Anthropic calls with circuit breaker + retry
2. Implement fallback to alternative vision model
3. Add metrics collection

```python
# Add imports
from src.resilience.circuit_breaker import with_circuit_breaker, OPENAI_BREAKER, ANTHROPIC_BREAKER
from src.resilience.retry import with_retry
from src.resilience.fallback import execute_with_fallbacks, FallbackStrategy
from src.resilience.metrics import record_api_call, record_fallback
import time

# Modify analyze_food_photo
async def analyze_food_photo(...) -> VisionAnalysisResult:
    """Enhanced with circuit breaker and fallback"""

    # Define fallback strategies
    strategies = [
        FallbackStrategy(
            name="primary_vision_model",
            handler=_analyze_primary_vision,
            priority=1
        ),
        FallbackStrategy(
            name="fallback_vision_model",
            handler=_analyze_fallback_vision,
            priority=2
        ),
        FallbackStrategy(
            name="mock_fallback",
            handler=_get_mock_result_async,
            priority=3
        )
    ]

    return await execute_with_fallbacks(
        strategies,
        image_data=image_data,
        photo_path=photo_path,
        caption=caption,
        # ... other args
    )

async def _analyze_primary_vision(...):
    """Try primary vision model with circuit breaker"""
    if VISION_MODEL.startswith("openai:"):
        return await _analyze_openai_protected(...)
    elif VISION_MODEL.startswith("anthropic:"):
        return await _analyze_anthropic_protected(...)

async def _analyze_fallback_vision(...):
    """Try fallback vision model"""
    # Switch to alternate model
    if VISION_MODEL.startswith("openai:"):
        return await _analyze_anthropic_protected(...)
    else:
        return await _analyze_openai_protected(...)

@with_circuit_breaker(OPENAI_BREAKER)
@with_retry(max_retries=3)
async def _analyze_openai_protected(...):
    """OpenAI call protected by circuit breaker and retry"""
    start_time = time.time()
    try:
        result = await analyze_with_openai(...)
        record_api_call("openai", success=True, duration=time.time() - start_time)
        return result
    except Exception as e:
        record_api_call("openai", success=False, duration=time.time() - start_time)
        raise

# Similar for Anthropic
```

#### Step 8: Update USDA Nutrition Search
**File**: `src/utils/nutrition_search.py`

**Changes**:
1. Wrap USDA API calls with circuit breaker + retry
2. Add local database fallback
3. Add metrics

```python
from src.resilience.circuit_breaker import with_circuit_breaker, USDA_BREAKER
from src.resilience.retry import with_retry
from src.db.nutrition_cache import get_from_cache, add_to_cache
from src.resilience.metrics import record_api_call, record_fallback

@with_circuit_breaker(USDA_BREAKER)
@with_retry(max_retries=3)
async def search_usda(food_name: str, max_results: int = 3) -> Optional[Dict[str, Any]]:
    """Enhanced USDA search with resilience"""
    # Existing implementation...

async def verify_food_items(food_items: List[FoodItem]) -> List[FoodItem]:
    """Enhanced with local database fallback"""

    for item in food_items:
        normalized_name = normalize_food_name(item.name)

        try:
            # Try USDA API
            usda_results = await search_usda(normalized_name)

            if usda_results:
                # Cache to local DB
                await add_to_cache(normalized_name, usda_results['foods'][0])
                # ... existing logic

        except Exception as e:
            logger.warning(f"USDA failed for '{item.name}': {e}")

            # Try local database
            cached_data = await get_from_cache(normalized_name)
            if cached_data:
                logger.info(f"Using cached nutrition data for '{item.name}'")
                record_fallback("usda", "local_cache", success=True)
                # ... use cached data
                continue

            # Existing fallback to web search...
```

#### Step 9: Update Bot Main Module
**File**: `src/bot.py`

**Changes**:
1. Initialize resilience components
2. Expose Prometheus metrics endpoint

```python
from src.resilience.circuit_breaker import OPENAI_BREAKER, ANTHROPIC_BREAKER, USDA_BREAKER
from src.db.nutrition_cache import init_nutrition_cache
from prometheus_client import start_http_server

async def main():
    """Initialize bot with resilience components"""

    # Initialize nutrition cache
    init_nutrition_cache()

    # Start Prometheus metrics server (port 8000)
    start_http_server(8000)
    logger.info("Prometheus metrics exposed on :8000/metrics")

    # Existing bot initialization...
```

#### Step 10: Add Configuration
**File**: `src/config.py`

```python
# Circuit Breaker Configuration
CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5"))
CIRCUIT_BREAKER_TIMEOUT: int = int(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "60"))

# Retry Configuration
API_RETRY_MAX: int = int(os.getenv("API_RETRY_MAX", "3"))
API_RETRY_BASE_DELAY: float = float(os.getenv("API_RETRY_BASE_DELAY", "1.0"))

# Fallback Configuration
VISION_MODEL_FALLBACK: str = os.getenv("VISION_MODEL_FALLBACK", "anthropic:claude-3-5-sonnet-latest")

# Metrics
METRICS_PORT: int = int(os.getenv("METRICS_PORT", "8000"))
```

**File**: `.env.example`

```bash
# Circuit Breaker Configuration
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT=60

# Retry Configuration
API_RETRY_MAX=3
API_RETRY_BASE_DELAY=1.0

# Fallback Configuration
VISION_MODEL_FALLBACK=anthropic:claude-3-5-sonnet-latest

# Metrics
METRICS_PORT=8000
```

---

## 4. Testing Strategy

### 4.1 Unit Tests

**File**: `tests/unit/test_circuit_breaker.py`

```python
import pytest
from src.resilience.circuit_breaker import OPENAI_BREAKER, with_circuit_breaker
import pybreaker

@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures():
    """Test circuit breaker opens after threshold failures"""

    @with_circuit_breaker(OPENAI_BREAKER)
    async def failing_function():
        raise Exception("Simulated failure")

    # Trigger 5 failures
    for i in range(5):
        with pytest.raises(Exception):
            await failing_function()

    # 6th call should be rejected by circuit breaker
    with pytest.raises(pybreaker.CircuitBreakerError):
        await failing_function()

@pytest.mark.asyncio
async def test_circuit_breaker_half_open_recovery():
    """Test circuit breaker recovers via HALF_OPEN state"""
    # ... test implementation
```

**File**: `tests/unit/test_retry.py`

```python
import pytest
from src.resilience.retry import retry_with_backoff, is_retryable_error
import httpx

@pytest.mark.asyncio
async def test_retry_with_transient_error():
    """Test retry succeeds after transient error"""

    attempt_count = 0

    async def flaky_function():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise httpx.TimeoutException("Timeout")
        return "success"

    result = await retry_with_backoff(flaky_function, max_retries=3)
    assert result == "success"
    assert attempt_count == 3

@pytest.mark.asyncio
async def test_no_retry_on_permanent_error():
    """Test no retry for permanent errors (e.g., 401)"""

    async def auth_error_function():
        response = httpx.Response(401)
        raise httpx.HTTPStatusError("Unauthorized", request=None, response=response)

    with pytest.raises(httpx.HTTPStatusError):
        await retry_with_backoff(auth_error_function, max_retries=3)
```

### 4.2 Integration Tests

**File**: `tests/integration/test_resilience_integration.py`

```python
import pytest
from unittest.mock import patch, AsyncMock
from src.utils.vision import analyze_food_photo
from src.utils.nutrition_search import verify_food_items

@pytest.mark.asyncio
async def test_vision_fallback_to_alternative_model():
    """Test vision AI falls back to alternative model when primary fails"""

    with patch('src.utils.vision.analyze_with_openai', side_effect=Exception("OpenAI down")):
        with patch('src.utils.vision.analyze_with_anthropic', return_value=mock_result()):
            result = await analyze_food_photo("test.jpg", caption="apple")
            assert result.foods[0].name == "apple"

@pytest.mark.asyncio
async def test_usda_fallback_to_local_cache():
    """Test USDA falls back to local cache when API fails"""

    # Pre-populate cache
    await add_to_cache("chicken breast", mock_nutrition_data())

    with patch('src.utils.nutrition_search.search_usda', side_effect=Exception("USDA down")):
        result = await verify_food_items([mock_food_item()])
        assert result[0].verification_source == "local_cache"
```

### 4.3 Load Tests

**File**: `tests/load/test_circuit_breaker_load.py`

```python
import pytest
import asyncio
from src.resilience.circuit_breaker import USDA_BREAKER

@pytest.mark.asyncio
async def test_circuit_breaker_under_load():
    """Test circuit breaker behavior under heavy load"""

    # Simulate 100 concurrent requests with 50% failure rate
    async def load_test():
        tasks = [make_api_call() for _ in range(100)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify circuit breaker opened after failures
        assert USDA_BREAKER.current_state == pybreaker.STATE_OPEN

    await load_test()
```

### 4.4 Chaos Testing

**File**: `tests/chaos/test_api_failures.py`

```python
import pytest
from unittest.mock import patch
import random

@pytest.mark.asyncio
async def test_random_api_failures():
    """Inject random failures to test resilience"""

    def random_failure(*args, **kwargs):
        if random.random() < 0.3:  # 30% failure rate
            raise Exception("Random failure")
        return mock_success()

    with patch('httpx.AsyncClient.get', side_effect=random_failure):
        # Run 100 requests and verify system stays responsive
        for _ in range(100):
            try:
                result = await search_usda("chicken")
                assert result is not None
            except Exception:
                pass  # Expected failures
```

---

## 5. Monitoring and Alerting

### 5.1 Prometheus Metrics

**Exposed on**: `http://localhost:8000/metrics`

Key metrics:
- `circuit_breaker_state{api="openai|anthropic|usda"}` - Current state
- `api_calls_total{api, status}` - Total calls by status
- `api_failures_total{api, error_type}` - Failures by type
- `api_retries_total{api}` - Retry attempts
- `fallback_executions_total{primary_api, fallback_strategy, status}` - Fallback usage

### 5.2 Alert Rules (Prometheus/Grafana)

```yaml
groups:
  - name: resilience_alerts
    rules:
      - alert: CircuitBreakerOpen
        expr: circuit_breaker_state == 1  # OPEN
        for: 2m
        annotations:
          summary: "Circuit breaker {{ $labels.api }} is OPEN"
          description: "API {{ $labels.api }} has been failing for 2 minutes"

      - alert: HighAPIFailureRate
        expr: rate(api_failures_total[5m]) > 0.1
        annotations:
          summary: "High failure rate for {{ $labels.api }}"
          description: "API {{ $labels.api }} failure rate is {{ $value }}"

      - alert: FrequentFallbacks
        expr: rate(fallback_executions_total[5m]) > 0.5
        annotations:
          summary: "Frequent fallback usage for {{ $labels.primary_api }}"
```

### 5.3 Logging

Enhanced logging for debugging:

```python
# Log circuit breaker state changes
logger.warning(f"[CIRCUIT_BREAKER] {api} state: {old_state} -> {new_state}")

# Log retry attempts
logger.info(f"[RETRY] Attempt {n}/{max} for {api} after {delay}s")

# Log fallback execution
logger.warning(f"[FALLBACK] {primary_api} failed, trying {fallback_strategy}")

# Log metrics
logger.info(f"[METRICS] {api} - calls: {total}, failures: {failures}, success_rate: {rate}%")
```

---

## 6. Deployment Plan

### 6.1 Rollout Strategy

**Phase 1: Non-Production** (Days 1-2)
- Deploy to staging environment
- Run integration tests
- Monitor metrics for 24 hours
- Validate circuit breaker behavior

**Phase 2: Canary** (Days 3-4)
- Deploy to 10% of production traffic
- Monitor error rates and latency
- Gradually increase to 50%

**Phase 3: Full Rollout** (Day 5)
- Deploy to 100% of production
- Monitor for 48 hours
- Document any issues

### 6.2 Rollback Plan

**Trigger**: Circuit breaker causing more harm than good (e.g., false positives)

**Steps**:
1. Disable circuit breaker via config: `CIRCUIT_BREAKER_ENABLED=false`
2. Restart service
3. Monitor for 1 hour
4. Investigate root cause
5. Fix and redeploy

### 6.3 Configuration Tuning

**Adjustable via Environment Variables**:
- `CIRCUIT_BREAKER_FAILURE_THRESHOLD` - Default: 5
- `CIRCUIT_BREAKER_TIMEOUT` - Default: 60s
- `API_RETRY_MAX` - Default: 3
- `API_RETRY_BASE_DELAY` - Default: 1.0s

**Tuning Guidelines**:
- If too many false positives → Increase failure threshold
- If recovery too slow → Decrease timeout
- If too many retries → Decrease max retries

---

## 7. Success Criteria

### 7.1 Functional Requirements

- ✅ Circuit breaker implemented for all 3 external APIs (OpenAI, Anthropic, USDA)
- ✅ Retry logic with exponential backoff (1s, 2s, 4s, max 30s)
- ✅ Fallback strategies for each API
- ✅ Local nutrition database for USDA fallback
- ✅ All API calls protected by circuit breaker + retry
- ✅ Metrics exposed via Prometheus

### 7.2 Performance Requirements

- ✅ P95 latency increase < 100ms (due to retry overhead)
- ✅ Circuit breaker opens within 5 failures
- ✅ Circuit breaker recovers within 60s of service restoration
- ✅ Fallback strategies execute < 1s

### 7.3 Reliability Requirements

- ✅ System remains responsive when all external APIs fail (returns fallback/cached data)
- ✅ No cascading failures (circuit breaker prevents retry storms)
- ✅ 99.9% of requests receive a response (even if degraded)

### 7.4 Testing Requirements

- ✅ Unit tests: 90%+ coverage for resilience modules
- ✅ Integration tests: All fallback paths tested
- ✅ Load tests: System stable under 100 concurrent requests with 50% API failures
- ✅ Chaos tests: Random failures don't crash system

---

## 8. Documentation

### 8.1 Code Documentation

- All modules have docstrings
- Complex logic has inline comments
- Configuration options documented in `.env.example`

### 8.2 Operations Documentation

**File**: `docs/operations/circuit-breaker.md`

```markdown
# Circuit Breaker Operations Guide

## Monitoring
- View metrics: http://localhost:8000/metrics
- Grafana dashboard: [link]

## Common Issues
### Circuit Breaker Stuck Open
- Check external API status
- View logs: `grep "CIRCUIT_BREAKER" app.log`
- Manually close: (not recommended, let it auto-recover)

### High Failure Rate
- Check API keys are valid
- Verify network connectivity
- Review error logs for root cause

## Configuration Tuning
See section 6.3 in implementation plan
```

### 8.3 Developer Documentation

**File**: `docs/development/resilience-patterns.md`

```markdown
# Resilience Patterns Guide

## Adding a New External API

1. Create a circuit breaker:
```python
NEW_API_BREAKER = pybreaker.CircuitBreaker(
    fail_max=5,
    timeout_duration=60,
    name="new_api"
)
```

2. Wrap API calls:
```python
@with_circuit_breaker(NEW_API_BREAKER)
@with_retry(max_retries=3)
async def call_new_api():
    ...
```

3. Implement fallback strategy
4. Add metrics
5. Write tests
```

---

## 9. Timeline and Effort Estimation

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| **Phase 1: Setup** | Install dependencies, create file structure | 1 hour |
| **Phase 2: Core Implementation** | Circuit breaker, retry, fallback modules | 3 hours |
| **Phase 3: Integration** | Update vision, USDA, bot modules | 2 hours |
| **Phase 4: Testing** | Unit, integration, load, chaos tests | 4 hours |
| **Phase 5: Monitoring** | Metrics, logging, alerts | 1 hour |
| **Phase 6: Documentation** | Code docs, ops guide, developer guide | 1 hour |
| **Phase 7: Deployment** | Staging, canary, rollout | 2 hours |

**Total: ~14 hours** (with buffer, fits within 8-hour estimate for core implementation, testing can be parallelized)

---

## 10. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Circuit breaker false positives | Service degradation | Medium | Tune thresholds, add manual override |
| Increased latency from retries | Poor UX | Medium | Limit max retries, use aggressive timeouts |
| Local database outdated | Inaccurate nutrition data | Low | Regular sync from USDA, cache expiry |
| Metrics overhead | Performance impact | Low | Use sampling, async metrics collection |
| Fallback strategy fails | No response to user | Low | Always have final fallback (mock/error message) |

---

## 11. Future Enhancements (Out of Scope)

- **Distributed Circuit Breaker**: Share state across multiple bot instances (Redis)
- **Adaptive Timeouts**: Dynamically adjust based on API performance
- **Rate Limiting**: Prevent hitting API rate limits
- **Advanced Caching**: Use Redis for distributed cache
- **Health Checks**: Proactive API health monitoring
- **Bulkhead Pattern**: Isolate API calls to prevent resource exhaustion

---

## 12. References

- [Circuit Breaker Pattern (Martin Fowler)](https://martinfowler.com/bliki/CircuitBreaker.html)
- [pybreaker Documentation](https://pybreaker.readthedocs.io/)
- [Exponential Backoff (AWS)](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)
- [Prometheus Python Client](https://github.com/prometheus/client_python)
- [Phase 3 Epic](https://github.com/gpt153/health-agent-planning/blob/main/.bmad/epic-008-phase3-architecture.md)

---

## Appendix A: Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CIRCUIT_BREAKER_FAILURE_THRESHOLD` | `5` | Failures before circuit opens |
| `CIRCUIT_BREAKER_TIMEOUT` | `60` | Seconds before HALF_OPEN |
| `API_RETRY_MAX` | `3` | Max retry attempts |
| `API_RETRY_BASE_DELAY` | `1.0` | Base delay for backoff (seconds) |
| `VISION_MODEL_FALLBACK` | `anthropic:claude-3-5-sonnet-latest` | Fallback vision model |
| `METRICS_PORT` | `8000` | Prometheus metrics port |

### Circuit Breaker States

| State | Behavior | Next State |
|-------|----------|------------|
| `CLOSED` | Normal operation | `OPEN` (after N failures) |
| `OPEN` | Fail fast, reject requests | `HALF_OPEN` (after timeout) |
| `HALF_OPEN` | Allow 1 test request | `CLOSED` (success) or `OPEN` (failure) |

---

## Appendix B: Common Failure Scenarios

| Scenario | Circuit Breaker | Retry | Fallback | User Impact |
|----------|----------------|-------|----------|-------------|
| Transient timeout | Counts failure | Retries (success) | Not triggered | None (transparent) |
| API rate limit | Counts failure | Retries (success) | Not triggered | Slight delay |
| API complete outage | Opens after 5 failures | No retry (circuit open) | Fallback triggered | Degraded data |
| Network partition | Opens after 5 failures | Retries (all fail) | Fallback triggered | Degraded data |
| Invalid API key | Counts failure | No retry (permanent error) | Fallback triggered | Error message |

---

**End of Implementation Plan**
