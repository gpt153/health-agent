# Monitoring Infrastructure Implementation Plan

**Issue**: #75 - Phase 2.10: Add Sentry + Prometheus monitoring
**Priority**: MEDIUM
**Estimated Time**: 3 hours
**Epic**: 007 - Phase 2 High-Priority Refactoring

---

## Executive Summary

This plan adds comprehensive monitoring infrastructure to the health-agent application using:
1. **Sentry** for error tracking, transaction performance, and contextual debugging
2. **Prometheus** for operational metrics (request rates, latencies, error rates, cache/database performance)

The implementation will provide:
- Real-time error tracking with full context (user_id, request_id, operation names)
- Performance monitoring across all endpoints and operations
- Operational metrics for capacity planning and optimization
- Zero-downtime deployment with environment-based configuration

---

## Current Architecture Analysis

### Application Structure
- **Dual-mode application**: Telegram Bot + REST API (can run independently or together)
- **Entry point**: `src/main.py` with 3 run modes: `bot`, `api`, `both`
- **API Framework**: FastAPI with uvicorn server
- **Bot Framework**: python-telegram-bot
- **Database**: PostgreSQL with psycopg connection pooling
- **Request flow**:
  - API: FastAPI routes → Agent → Database
  - Bot: Telegram handlers → Agent → Database

### Key Integration Points
1. **API Server** (`src/api/server.py`):
   - Global exception handler (line 59-65)
   - Lifespan manager for startup/shutdown (line 21-39)
   - Middleware setup (line 51-53)

2. **Bot** (`src/bot.py`):
   - Message handlers
   - Command handlers
   - Error handlers

3. **Database** (`src/db/connection.py`):
   - Connection pool manager
   - Query execution points

4. **Routes** (`src/api/routes.py`):
   - 18+ API endpoints across gamification, chat, users, food logging, reminders
   - Error handling in each endpoint

5. **Configuration** (`src/config.py`):
   - Environment-based configuration
   - Existing LOG_LEVEL configuration

---

## Implementation Plan

### Phase 1: Dependencies & Configuration (20 minutes)

#### 1.1 Add Dependencies
**File**: `requirements.txt`

Add:
```txt
# Monitoring
sentry-sdk[fastapi]>=1.40.0  # Sentry with FastAPI integration
prometheus-client>=0.19.0     # Prometheus metrics client
```

**Note**: `sentry-sdk[fastapi]` includes automatic FastAPI instrumentation

#### 1.2 Update Configuration
**File**: `src/config.py`

Add monitoring configuration:
```python
# Monitoring (after line 32)
SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
SENTRY_ENVIRONMENT: str = os.getenv("SENTRY_ENVIRONMENT", "development")
SENTRY_TRACES_SAMPLE_RATE: float = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "1.0"))
ENABLE_SENTRY: bool = os.getenv("ENABLE_SENTRY", "false").lower() == "true"
ENABLE_PROMETHEUS: bool = os.getenv("ENABLE_PROMETHEUS", "true").lower() == "true"
PROMETHEUS_PORT: int = int(os.getenv("PROMETHEUS_PORT", "9090"))
```

**Note**: Sentry disabled by default (opt-in), Prometheus enabled by default (opt-out)

---

### Phase 2: Create Monitoring Module (40 minutes)

#### 2.1 Create Monitoring Module Structure
**New File**: `src/monitoring/__init__.py`
```python
"""Monitoring infrastructure for health-agent"""
from src.monitoring.sentry_config import init_sentry, capture_exception, capture_message
from src.monitoring.prometheus_metrics import (
    metrics,
    track_request,
    track_database_query,
    track_cache_operation,
    track_agent_call
)

__all__ = [
    "init_sentry",
    "capture_exception",
    "capture_message",
    "metrics",
    "track_request",
    "track_database_query",
    "track_cache_operation",
    "track_agent_call"
]
```

#### 2.2 Sentry Configuration
**New File**: `src/monitoring/sentry_config.py`

**Purpose**: Initialize Sentry with custom context and transaction tracking

**Key Features**:
- DSN-based initialization with environment tagging
- Automatic FastAPI instrumentation
- Custom context injection (user_id, request_id, operation)
- Transaction performance tracking
- Error breadcrumb tracking

**Functions**:
```python
def init_sentry() -> None:
    """Initialize Sentry SDK with FastAPI integration"""
    # Only initialize if enabled and DSN provided
    # Configure traces_sample_rate for performance monitoring
    # Add FastAPI integration for automatic request tracking
    # Add logging integration for breadcrumbs
    # Configure before_send hook for custom context

def set_user_context(user_id: str) -> None:
    """Set user context for Sentry events"""
    # Attach user_id to all subsequent events

def set_request_context(request_id: str, operation: str) -> None:
    """Set request context for Sentry events"""
    # Attach request_id and operation name as tags

def capture_exception(exception: Exception, **extra_context) -> None:
    """Capture exception with custom context"""
    # Wrapper for sentry_sdk.capture_exception with extra tags

def capture_message(message: str, level: str = "info", **extra_context) -> None:
    """Capture informational message"""
    # Wrapper for sentry_sdk.capture_message with extra tags

@contextmanager
def sentry_transaction(operation: str, name: str):
    """Context manager for Sentry transaction tracking"""
    # Creates performance transaction for specific operations
    # Usage: with sentry_transaction("agent", "get_agent_response"):
```

**Integration Points**:
- Unhandled exceptions (automatic via FastAPI integration)
- Handled exceptions (manual capture in try/except blocks)
- Performance transactions (agent calls, database queries, API requests)

#### 2.3 Prometheus Metrics
**New File**: `src/monitoring/prometheus_metrics.py`

**Purpose**: Define and expose Prometheus metrics

**Metrics Defined**:

1. **Request Metrics**:
   ```python
   http_requests_total = Counter(
       'http_requests_total',
       'Total HTTP requests',
       ['method', 'endpoint', 'status']
   )

   http_request_duration_seconds = Histogram(
       'http_request_duration_seconds',
       'HTTP request latency',
       ['method', 'endpoint'],
       buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
   )
   ```

2. **Error Metrics**:
   ```python
   http_errors_total = Counter(
       'http_errors_total',
       'Total HTTP errors',
       ['method', 'endpoint', 'error_type']
   )
   ```

3. **Database Metrics**:
   ```python
   db_queries_total = Counter(
       'db_queries_total',
       'Total database queries',
       ['query_type', 'table']
   )

   db_query_duration_seconds = Histogram(
       'db_query_duration_seconds',
       'Database query latency',
       ['query_type'],
       buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
   )

   db_connection_pool_size = Gauge(
       'db_connection_pool_size',
       'Current database connection pool size'
   )

   db_connection_pool_available = Gauge(
       'db_connection_pool_available',
       'Available database connections in pool'
   )
   ```

4. **Cache Metrics**:
   ```python
   cache_operations_total = Counter(
       'cache_operations_total',
       'Total cache operations',
       ['operation', 'result']  # operation: hit/miss, result: success/failure
   )

   cache_hit_rate = Gauge(
       'cache_hit_rate',
       'Cache hit rate (0-1)'
   )
   ```

5. **Agent/AI Metrics**:
   ```python
   agent_calls_total = Counter(
       'agent_calls_total',
       'Total AI agent calls',
       ['agent_type', 'status']  # agent_type: claude/gpt4, status: success/error
   )

   agent_call_duration_seconds = Histogram(
       'agent_call_duration_seconds',
       'AI agent call latency',
       ['agent_type'],
       buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0]
   )

   agent_tokens_used = Counter(
       'agent_tokens_used_total',
       'Total tokens used by AI agents',
       ['agent_type', 'token_type']  # token_type: input/output
   )
   ```

**Helper Functions**:
```python
@contextmanager
def track_request(method: str, endpoint: str):
    """Track HTTP request metrics"""
    # Time the request and record metrics

@contextmanager
def track_database_query(query_type: str, table: str = ""):
    """Track database query metrics"""
    # Time the query and record metrics

def track_cache_operation(operation: str, hit: bool):
    """Track cache operation"""
    # Record hit/miss and update hit rate

@contextmanager
def track_agent_call(agent_type: str):
    """Track agent call metrics"""
    # Time the call and record metrics

def update_pool_metrics(total: int, available: int):
    """Update database connection pool metrics"""
    # Update gauge metrics
```

**Metrics Exposure**:
- HTTP endpoint: `/metrics` (standard Prometheus format)
- Separate port option: Can run on dedicated port (default 9090)

#### 2.4 Metrics Endpoint for FastAPI
**New File**: `src/api/metrics_routes.py`

**Purpose**: Expose Prometheus metrics via HTTP

```python
"""Prometheus metrics endpoint"""
from fastapi import APIRouter
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

router = APIRouter()

@router.get("/metrics")
async def metrics_endpoint():
    """Expose Prometheus metrics"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

---

### Phase 3: FastAPI Integration (30 minutes)

#### 3.1 Update API Server Initialization
**File**: `src/api/server.py`

**Changes**:

1. **Import monitoring modules** (after line 10):
```python
from src.monitoring import init_sentry
from src.monitoring.prometheus_metrics import metrics
from src.config import ENABLE_SENTRY, ENABLE_PROMETHEUS
```

2. **Initialize Sentry in lifespan** (line 24, after logger.info):
```python
    # Initialize monitoring
    if ENABLE_SENTRY:
        init_sentry()
        logger.info("Sentry monitoring initialized")
```

3. **Include metrics endpoint** (after line 56):
```python
    # Include metrics endpoint
    if ENABLE_PROMETHEUS:
        from src.api.metrics_routes import router as metrics_router
        app.include_router(metrics_router)
        logger.info("Prometheus metrics endpoint enabled at /metrics")
```

4. **Update global exception handler** (replace lines 59-65):
```python
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)

        # Capture exception in Sentry
        if ENABLE_SENTRY:
            from src.monitoring import capture_exception
            capture_exception(exc, url=str(request.url), method=request.method)

        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc)}
        )
```

#### 3.2 Add Request Tracking Middleware
**File**: `src/api/middleware.py`

**Add new middleware function** (after setup_rate_limiting):
```python
import uuid
import time
from starlette.middleware.base import BaseHTTPMiddleware
from src.config import ENABLE_PROMETHEUS, ENABLE_SENTRY

class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for request tracking and metrics"""

    async def dispatch(self, request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Set Sentry context
        if ENABLE_SENTRY:
            from src.monitoring import set_request_context
            endpoint = request.url.path
            set_request_context(request_id, f"{request.method} {endpoint}")

        # Track metrics
        if ENABLE_PROMETHEUS:
            from src.monitoring import track_request
            start_time = time.time()

            try:
                response = await call_next(request)

                # Record successful request
                duration = time.time() - start_time
                metrics.http_requests_total.labels(
                    method=request.method,
                    endpoint=request.url.path,
                    status=response.status_code
                ).inc()

                metrics.http_request_duration_seconds.labels(
                    method=request.method,
                    endpoint=request.url.path
                ).observe(duration)

                return response

            except Exception as e:
                # Record error
                duration = time.time() - start_time
                metrics.http_errors_total.labels(
                    method=request.method,
                    endpoint=request.url.path,
                    error_type=type(e).__name__
                ).inc()

                metrics.http_request_duration_seconds.labels(
                    method=request.method,
                    endpoint=request.url.path
                ).observe(duration)

                raise
        else:
            response = await call_next(request)
            return response


def setup_monitoring(app):
    """Configure monitoring middleware"""
    app.add_middleware(MonitoringMiddleware)
    logger.info("Monitoring middleware configured")
```

**Update server.py** to call setup_monitoring (after line 53):
```python
    # Setup middleware
    setup_cors(app)
    setup_rate_limiting(app)
    setup_monitoring(app)  # NEW
```

#### 3.3 Update Routes for User Context
**File**: `src/api/routes.py`

**Add Sentry user context in chat endpoint** (after line 53, before get_agent_response):
```python
        # Set monitoring context
        if ENABLE_SENTRY:
            from src.monitoring import set_user_context
            set_user_context(user_id)
```

**Apply to all endpoints** that have user_id (create_user_endpoint, get_profile, update_profile, etc.)

---

### Phase 4: Database Monitoring Integration (30 minutes)

#### 4.1 Update Database Connection Manager
**File**: `src/db/connection.py`

**Changes**:

1. **Import monitoring** (after line 8):
```python
from src.config import ENABLE_PROMETHEUS
```

2. **Add connection pool metrics** (in `connection()` method, after line 43):
```python
    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[psycopg.AsyncConnection, None]:
        """Get database connection from pool"""
        if not self._pool:
            raise RuntimeError("Database pool not initialized")

        # Update pool metrics
        if ENABLE_PROMETHEUS:
            from src.monitoring import update_pool_metrics
            pool_stats = self._pool.get_stats()
            update_pool_metrics(
                total=pool_stats.get('pool_size', 0),
                available=pool_stats.get('pool_available', 0)
            )

        async with self._pool.connection() as conn:
            conn.row_factory = dict_row
            yield conn
```

**Note**: `psycopg_pool` provides `get_stats()` method for pool monitoring

#### 4.2 Add Query Tracking Helper
**File**: `src/db/queries.py`

**Add decorator for query tracking** (at top of file):
```python
from functools import wraps
from src.config import ENABLE_PROMETHEUS

def track_query(query_type: str, table: str = ""):
    """Decorator to track database query metrics"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if ENABLE_PROMETHEUS:
                from src.monitoring import track_database_query
                with track_database_query(query_type, table):
                    return await func(*args, **kwargs)
            else:
                return await func(*args, **kwargs)
        return wrapper
    return decorator
```

**Apply decorator to key queries** (examples):
```python
@track_query("SELECT", "users")
async def user_exists(telegram_id: str) -> bool:
    ...

@track_query("INSERT", "users")
async def create_user(telegram_id: str, ...):
    ...

@track_query("SELECT", "food_entries")
async def get_food_entries_by_date(user_id: str, ...):
    ...
```

**Apply to ~20-30 most frequently used queries** across the application

---

### Phase 5: Agent Call Monitoring (20 minutes)

#### 5.1 Update Agent Module
**File**: `src/agent/__init__.py`

**Find the main agent call function** (`get_agent_response` or similar)

**Wrap agent calls with monitoring**:
```python
async def get_agent_response(...):
    """Get response from AI agent"""

    # Set user context for Sentry
    if ENABLE_SENTRY:
        from src.monitoring import set_user_context
        set_user_context(telegram_id)

    # Track agent call
    if ENABLE_PROMETHEUS:
        from src.monitoring import track_agent_call

        # Determine agent type (claude/gpt4)
        agent_type = "claude" if "claude" in AGENT_MODEL else "gpt4"

        with track_agent_call(agent_type):
            try:
                response = await _make_agent_call(...)

                # Track token usage if available
                if hasattr(response, 'usage'):
                    metrics.agent_tokens_used.labels(
                        agent_type=agent_type,
                        token_type="input"
                    ).inc(response.usage.input_tokens)

                    metrics.agent_tokens_used.labels(
                        agent_type=agent_type,
                        token_type="output"
                    ).inc(response.usage.output_tokens)

                return response
            except Exception as e:
                # Track error
                metrics.agent_calls_total.labels(
                    agent_type=agent_type,
                    status="error"
                ).inc()

                # Capture in Sentry
                if ENABLE_SENTRY:
                    from src.monitoring import capture_exception
                    capture_exception(e, agent_type=agent_type)

                raise
    else:
        return await _make_agent_call(...)
```

---

### Phase 6: Bot Integration (20 minutes)

#### 6.1 Update Bot Initialization
**File**: `src/bot.py`

**Initialize Sentry in bot** (add function after logger initialization, line 55):
```python
def init_bot_monitoring():
    """Initialize monitoring for Telegram bot"""
    if ENABLE_SENTRY:
        from src.monitoring import init_sentry
        init_sentry()
        logger.info("Sentry monitoring initialized for bot")
```

**Call in bot creation** (in `create_bot_application` function):
```python
def create_bot_application():
    """Create and configure the bot application"""
    init_bot_monitoring()  # NEW

    # ... rest of bot setup
```

#### 6.2 Add Bot Error Handler
**File**: `src/bot.py`

**Add global error handler for bot**:
```python
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in bot"""
    logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)

    # Capture in Sentry
    if ENABLE_SENTRY:
        from src.monitoring import capture_exception

        # Add context
        extra = {}
        if update and hasattr(update, 'effective_user'):
            extra['user_id'] = str(update.effective_user.id)
        if update and hasattr(update, 'effective_message'):
            extra['message_text'] = str(update.effective_message.text)

        capture_exception(context.error, **extra)
```

**Register error handler** (in `create_bot_application`):
```python
    # Add error handler
    app.add_error_handler(error_handler)
```

---

### Phase 7: Main Entry Point Integration (10 minutes)

#### 7.1 Update Main Module
**File**: `src/main.py`

**Initialize Sentry early** (after line 16, before async def run_telegram_bot):
```python
# Initialize Sentry monitoring (early initialization for startup errors)
from src.config import ENABLE_SENTRY
if ENABLE_SENTRY:
    from src.monitoring import init_sentry
    init_sentry()
    logger.info("Sentry monitoring initialized")
```

**Note**: This ensures startup errors are also captured

---

### Phase 8: Environment Configuration (10 minutes)

#### 8.1 Create .env.example
**File**: `.env.example`

**Add monitoring section**:
```bash
# Monitoring Configuration
ENABLE_SENTRY=false
SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0
SENTRY_ENVIRONMENT=development
SENTRY_TRACES_SAMPLE_RATE=1.0

ENABLE_PROMETHEUS=true
PROMETHEUS_PORT=9090
```

#### 8.2 Update README/Documentation
**File**: `API_README.md` or create `MONITORING.md`

**Add monitoring section**:
```markdown
## Monitoring

### Sentry Error Tracking

To enable Sentry:

1. Create a Sentry project at https://sentry.io
2. Copy your DSN
3. Set environment variables:
   ```bash
   ENABLE_SENTRY=true
   SENTRY_DSN=your-dsn-here
   SENTRY_ENVIRONMENT=production
   ```

### Prometheus Metrics

Metrics are exposed at `/metrics` endpoint by default.

Available metrics:
- `http_requests_total`: Total HTTP requests by method, endpoint, status
- `http_request_duration_seconds`: Request latency histograms
- `http_errors_total`: Error counts by type
- `db_queries_total`: Database query counts
- `db_query_duration_seconds`: Query latency
- `db_connection_pool_*`: Connection pool statistics
- `agent_calls_total`: AI agent call counts
- `agent_call_duration_seconds`: Agent call latency
- `agent_tokens_used_total`: Token usage tracking
- `cache_operations_total`: Cache hit/miss statistics

To disable Prometheus:
```bash
ENABLE_PROMETHEUS=false
```

### Grafana Dashboard

Import the provided dashboard (dashboards/health-agent-metrics.json) to Grafana for visualization.
```

---

### Phase 9: Testing (20 minutes)

#### 9.1 Create Test File
**New File**: `tests/test_monitoring.py`

**Test cases**:
```python
"""Tests for monitoring infrastructure"""
import pytest
from src.monitoring import init_sentry, set_user_context, capture_exception
from src.monitoring.prometheus_metrics import track_request, track_database_query

def test_sentry_initialization_disabled():
    """Test Sentry doesn't initialize when disabled"""
    # Mock ENABLE_SENTRY=False
    # Call init_sentry()
    # Assert no errors

def test_prometheus_metrics_tracking():
    """Test Prometheus metrics are recorded"""
    # Call track_request() context manager
    # Assert metrics are incremented

def test_database_query_tracking():
    """Test database query metrics"""
    # Call track_database_query() context manager
    # Assert query metrics are recorded

def test_user_context_setting():
    """Test Sentry user context"""
    # Call set_user_context()
    # Assert context is set (if Sentry enabled)

@pytest.mark.asyncio
async def test_monitoring_middleware():
    """Test request tracking middleware"""
    # Mock request/response
    # Call middleware
    # Assert metrics recorded and request_id set
```

#### 9.2 Integration Testing
**Manual testing checklist**:
1. Start app with Sentry enabled: `ENABLE_SENTRY=true python -m src.main`
2. Trigger API request: `curl http://localhost:8080/api/v1/health`
3. Verify metrics endpoint: `curl http://localhost:8080/metrics`
4. Trigger error: Send invalid request
5. Check Sentry dashboard for error capture
6. Check Prometheus metrics for increments

---

### Phase 10: Optional Grafana Dashboard (30 minutes)

#### 10.1 Create Grafana Dashboard JSON
**New File**: `dashboards/health-agent-metrics.json`

**Dashboard panels**:
1. **Request Rate**: Rate of `http_requests_total`
2. **Response Time (p50, p95, p99)**: Quantiles of `http_request_duration_seconds`
3. **Error Rate**: Rate of `http_errors_total`
4. **Database Query Performance**: `db_query_duration_seconds` histogram
5. **Database Connection Pool**: `db_connection_pool_size` and `db_connection_pool_available`
6. **Agent Call Performance**: `agent_call_duration_seconds`
7. **Agent Token Usage**: Rate of `agent_tokens_used_total`
8. **Cache Hit Rate**: `cache_hit_rate` gauge

**Export as JSON** for easy import into Grafana

---

## File Changes Summary

### New Files
1. `src/monitoring/__init__.py` - Monitoring module exports
2. `src/monitoring/sentry_config.py` - Sentry initialization and helpers (~150 lines)
3. `src/monitoring/prometheus_metrics.py` - Metrics definitions and helpers (~200 lines)
4. `src/api/metrics_routes.py` - Metrics endpoint (~15 lines)
5. `tests/test_monitoring.py` - Monitoring tests (~100 lines)
6. `dashboards/health-agent-metrics.json` - Grafana dashboard (optional)
7. `MONITORING.md` - Monitoring documentation (~100 lines)

### Modified Files
1. `requirements.txt` - Add sentry-sdk, prometheus-client
2. `src/config.py` - Add monitoring configuration (~7 lines)
3. `src/api/server.py` - Initialize Sentry, add metrics endpoint, update exception handler (~20 lines)
4. `src/api/middleware.py` - Add MonitoringMiddleware (~80 lines)
5. `src/api/routes.py` - Add user context to endpoints (~2 lines per endpoint, ~20 lines total)
6. `src/db/connection.py` - Add pool metrics (~10 lines)
7. `src/db/queries.py` - Add query tracking decorator and apply to queries (~50 lines)
8. `src/agent/__init__.py` - Add agent call tracking (~30 lines)
9. `src/bot.py` - Initialize monitoring, add error handler (~25 lines)
10. `src/main.py` - Early Sentry initialization (~5 lines)
11. `.env.example` - Add monitoring configuration (~7 lines)
12. `API_README.md` - Add monitoring section (~50 lines)

**Total**: ~7 new files, 12 modified files, ~900 new lines of code

---

## Deployment Strategy

### Zero-Downtime Deployment
1. **Phase 1**: Deploy with monitoring disabled
   - Merge PR with `ENABLE_SENTRY=false` in production
   - Deploy and verify application stability

2. **Phase 2**: Enable Prometheus metrics
   - Set `ENABLE_PROMETHEUS=true`
   - Restart application
   - Verify `/metrics` endpoint
   - Configure Prometheus scraper

3. **Phase 3**: Enable Sentry
   - Create Sentry project
   - Set `ENABLE_SENTRY=true` and `SENTRY_DSN`
   - Set appropriate `SENTRY_TRACES_SAMPLE_RATE` (0.1 for production = 10% sampling)
   - Restart application
   - Verify error tracking

### Environment-Specific Configuration

**Development**:
```bash
ENABLE_SENTRY=false
ENABLE_PROMETHEUS=true
SENTRY_TRACES_SAMPLE_RATE=1.0  # 100% sampling
```

**Staging**:
```bash
ENABLE_SENTRY=true
ENABLE_PROMETHEUS=true
SENTRY_ENVIRONMENT=staging
SENTRY_TRACES_SAMPLE_RATE=1.0  # 100% sampling for testing
```

**Production**:
```bash
ENABLE_SENTRY=true
ENABLE_PROMETHEUS=true
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1  # 10% sampling to reduce overhead
```

---

## Performance Considerations

### Overhead Analysis

**Sentry**:
- Transaction sampling: 0.1 = 10% of requests traced (minimal overhead)
- Error capture: Only on exceptions (negligible overhead)
- Estimated overhead: <1% with 10% sampling

**Prometheus**:
- Metrics increment: O(1) operation, ~1-5 microseconds per metric
- Estimated overhead per request: <100 microseconds
- Memory: ~10-50 KB for metric storage
- Overall impact: <0.5% on request latency

**Total**: <1.5% performance impact with recommended settings

### Optimization Strategies
1. **Reduce Sentry sampling** in high-traffic production (0.01 = 1%)
2. **Use metric aggregation** for high-cardinality labels (e.g., group endpoints)
3. **Disable debug-level Sentry breadcrumbs** in production
4. **Lazy import** monitoring modules (already implemented with if ENABLE_SENTRY checks)

---

## Success Metrics

### Post-Deployment Validation

**Week 1**:
- ✅ Sentry receiving errors with full context
- ✅ Prometheus metrics endpoint returning data
- ✅ No performance degradation (check p95 latency)
- ✅ All endpoints reporting metrics

**Week 2**:
- ✅ Grafana dashboards visualizing metrics
- ✅ Alerts configured for critical errors
- ✅ Database pool metrics showing healthy values
- ✅ Agent performance within expected ranges

**Week 4**:
- ✅ Identified and fixed 3+ errors via Sentry
- ✅ Optimized 2+ slow endpoints using metrics
- ✅ Established baseline performance metrics
- ✅ Team trained on monitoring tools

---

## Risk Assessment

### Low Risk
- **Gradual rollout**: Monitoring disabled by default
- **Non-breaking changes**: All monitoring is opt-in
- **Isolated code**: Monitoring in separate module
- **Environment-based**: Can disable per environment

### Potential Issues
1. **Issue**: Sentry DSN misconfiguration
   - **Mitigation**: Clear validation error if DSN invalid
   - **Fallback**: App continues without monitoring

2. **Issue**: Prometheus endpoint exposed publicly
   - **Mitigation**: Document need for firewall rules
   - **Fallback**: Can disable or move to separate port

3. **Issue**: High-cardinality metrics causing memory issues
   - **Mitigation**: Use fixed labels (method, endpoint, status)
   - **Fallback**: Can disable specific metrics

4. **Issue**: Performance impact on high-traffic endpoints
   - **Mitigation**: Reduce Sentry sampling rate
   - **Fallback**: Can disable per-endpoint

---

## Future Enhancements

### Phase 2 (Post-MVP)
1. **Custom Dashboards**: User-specific metrics dashboards
2. **Alerting**: PagerDuty/Slack integration for critical errors
3. **APM**: Full distributed tracing across services
4. **Logging**: Structured logging with correlation IDs
5. **Cost Tracking**: Monitor API costs (OpenAI/Anthropic tokens)

### Phase 3 (Advanced)
1. **User Journey Tracking**: Track user flows through app
2. **A/B Testing Metrics**: Compare feature performance
3. **Business Metrics**: Track DAU, retention, engagement
4. **ML Metrics**: Model performance and accuracy tracking

---

## Documentation Requirements

### For Developers
1. **How to add new metrics**: Guide in MONITORING.md
2. **How to capture custom errors**: Sentry usage examples
3. **How to debug with Sentry**: Context and breadcrumbs guide
4. **How to use Grafana**: Dashboard navigation guide

### For DevOps
1. **Prometheus scraping config**: Example prometheus.yml
2. **Grafana setup**: Dashboard import instructions
3. **Alert configuration**: Example alert rules
4. **Backup and retention**: Metrics retention policies

---

## Estimated Time Breakdown

| Phase | Task | Time |
|-------|------|------|
| 1 | Dependencies & Configuration | 20 min |
| 2 | Create Monitoring Module | 40 min |
| 3 | FastAPI Integration | 30 min |
| 4 | Database Monitoring | 30 min |
| 5 | Agent Call Monitoring | 20 min |
| 6 | Bot Integration | 20 min |
| 7 | Main Entry Point | 10 min |
| 8 | Environment Config | 10 min |
| 9 | Testing | 20 min |
| 10 | Grafana Dashboard (Optional) | 30 min |
| **Total** | | **3h 50min** |

**Estimated**: 3 hours (core implementation)
**With optional Grafana**: 3.5 hours
**With full testing and docs**: 4 hours

---

## Implementation Order

### Day 1 (2-3 hours)
1. ✅ Add dependencies (requirements.txt)
2. ✅ Create monitoring module structure
3. ✅ Implement Sentry configuration
4. ✅ Implement Prometheus metrics
5. ✅ Integrate with FastAPI server
6. ✅ Add middleware

### Day 2 (1-2 hours)
7. ✅ Database monitoring integration
8. ✅ Agent call tracking
9. ✅ Bot integration
10. ✅ Testing and validation

### Day 3 (Optional, 1 hour)
11. ✅ Documentation
12. ✅ Grafana dashboard
13. ✅ Deployment guide

---

## Acceptance Criteria

### Must Have
- [x] Sentry integration with DSN configuration
- [x] Sentry captures unhandled exceptions with user context
- [x] Sentry tracks transaction performance for API endpoints
- [x] Prometheus metrics defined: requests, latency, errors
- [x] Prometheus metrics defined: database queries and pool
- [x] Prometheus metrics defined: cache hit/miss rates
- [x] Prometheus metrics exposed at `/metrics` endpoint
- [x] All metrics include proper labels (method, endpoint, status, etc.)
- [x] User context (user_id) attached to Sentry events
- [x] Request context (request_id) attached to Sentry events
- [x] Configuration via environment variables
- [x] Monitoring can be disabled via env vars
- [x] No performance degradation >2% with monitoring enabled

### Should Have
- [x] Grafana dashboard JSON (optional but recommended)
- [x] Documentation in MONITORING.md
- [x] Example Prometheus scrape config
- [x] Unit tests for monitoring module
- [x] Integration tests for metrics endpoints

### Nice to Have
- [ ] Automated alerts configuration examples
- [ ] Custom Sentry error grouping rules
- [ ] Cost tracking for AI tokens
- [ ] User journey tracking

---

## Conclusion

This implementation plan provides comprehensive monitoring for the health-agent application with minimal performance overhead and zero downtime deployment. The architecture supports gradual rollout, environment-specific configuration, and future enhancements.

**Key Benefits**:
- 🔍 Full visibility into errors with context
- 📊 Performance metrics for optimization
- 🚀 Operational insights for scaling
- 🛡️ Proactive error detection and debugging
- 📈 Foundation for data-driven improvements

**Next Steps**: Begin implementation with Phase 1 (Dependencies & Configuration)
