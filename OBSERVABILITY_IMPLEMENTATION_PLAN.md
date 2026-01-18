# Comprehensive Observability Stack Implementation Plan

## Executive Summary

This plan details the implementation of a full observability stack for the health-agent application, including Sentry error tracking, Prometheus metrics, OpenTelemetry distributed tracing, and Grafana dashboards. The implementation is designed to work with the existing Python 3.11 + PostgreSQL + FastAPI + python-telegram-bot architecture while maintaining backward compatibility and supporting both development and production environments.

---

## Phase 1: Foundation & Sentry Error Tracking

**Goal:** Establish error tracking infrastructure and integrate Sentry SDK

### 1.1 Dependencies & Configuration

**Files to Create:**
- `src/observability/__init__.py`
- `src/observability/sentry_config.py`
- `src/observability/context.py`

**Files to Modify:**
- `requirements.txt` - Add:
  ```
  sentry-sdk[fastapi]>=1.40.0
  prometheus-client>=0.19.0
  opentelemetry-api>=1.22.0
  opentelemetry-sdk>=1.22.0
  opentelemetry-instrumentation-fastapi>=0.43b0
  opentelemetry-instrumentation-psycopg>=0.43b0
  opentelemetry-instrumentation-requests>=0.43b0
  opentelemetry-exporter-otlp>=1.22.0
  ```

- `.env.example` - Add:
  ```bash
  # Observability
  SENTRY_DSN=https://...@sentry.io/...
  SENTRY_ENVIRONMENT=development  # development, staging, production
  SENTRY_TRACES_SAMPLE_RATE=0.1  # 10% sampling for dev, 1.0 for prod
  ENABLE_SENTRY=true
  ENABLE_METRICS=true
  ENABLE_TRACING=true

  # OpenTelemetry
  OTEL_SERVICE_NAME=health-agent
  OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
  OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
  ```

- `src/config.py` - Add observability settings:
  ```python
  # Observability
  SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
  SENTRY_ENVIRONMENT: str = os.getenv("SENTRY_ENVIRONMENT", "development")
  SENTRY_TRACES_SAMPLE_RATE: float = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
  ENABLE_SENTRY: bool = os.getenv("ENABLE_SENTRY", "true").lower() == "true"
  ENABLE_METRICS: bool = os.getenv("ENABLE_METRICS", "true").lower() == "true"
  ENABLE_TRACING: bool = os.getenv("ENABLE_TRACING", "true").lower() == "true"
  OTEL_SERVICE_NAME: str = os.getenv("OTEL_SERVICE_NAME", "health-agent")
  OTEL_EXPORTER_OTLP_ENDPOINT: str = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
  ```

### 1.2 Sentry Integration

**Implementation in `src/observability/sentry_config.py`:**
- Initialize Sentry SDK with FastAPI and psycopg integrations
- Configure error sampling and performance monitoring
- Set up release tracking (use git commit SHA from environment)
- Configure breadcrumbs for better debugging context

**Implementation in `src/observability/context.py`:**
- Create context manager for attaching user context to errors
- Function to set user context: `set_user_context(user_id: str, username: str = None)`
- Function to set tags: `set_tag(key: str, value: str)`
- Function to add breadcrumb: `add_breadcrumb(category: str, message: str, data: dict = None)`

**Files to Modify:**
- `src/main.py` - Initialize Sentry before app startup:
  ```python
  from src.observability.sentry_config import init_sentry

  async def main():
      # Initialize observability first
      init_sentry()

      # Rest of startup...
  ```

- `src/api/server.py` - Integrate Sentry with FastAPI:
  ```python
  import sentry_sdk
  from sentry_sdk.integrations.fastapi import FastApiIntegration

  # Sentry is initialized in main.py but we need to ensure it's working
  ```

- `src/bot.py` - Add user context to all handler functions:
  ```python
  from src.observability.context import set_user_context, add_breadcrumb

  async def handle_message(update, context):
      user_id = str(update.effective_user.id)
      set_user_context(user_id, update.effective_user.username)
      add_breadcrumb("telegram", "message_received", {"text_length": len(text)})
      # ... rest of handler
  ```

### 1.3 Testing Sentry Integration

**Files to Create:**
- `tests/test_observability.py` - Unit tests for observability functions
- `scripts/test_sentry.py` - Script to trigger test errors

**Test Cases:**
- Verify Sentry captures exceptions with user context
- Test breadcrumb attachment
- Verify performance transaction creation
- Test error filtering (don't send HTTPException 404s to Sentry)

---

## Phase 2: Prometheus Metrics

**Goal:** Instrument application with business and technical metrics

### 2.1 Metrics Infrastructure

**Files to Create:**
- `src/observability/metrics.py` - Centralized metrics registry
- `src/observability/metrics_middleware.py` - FastAPI middleware for automatic instrumentation

**Metrics to Define in `metrics.py`:**

```python
from prometheus_client import Counter, Gauge, Histogram, Summary

# Request metrics
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

# Bot metrics
telegram_messages_total = Counter(
    'telegram_messages_total',
    'Total Telegram messages processed',
    ['message_type', 'status']  # text/photo/voice, success/error
)

telegram_message_duration_seconds = Histogram(
    'telegram_message_duration_seconds',
    'Telegram message processing time',
    ['message_type'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# Error metrics
errors_total = Counter(
    'errors_total',
    'Total errors by type',
    ['error_type', 'component']  # bot/api/database
)

# User activity metrics
active_users = Gauge(
    'active_users_total',
    'Number of active users',
    ['time_period']  # last_hour/last_day/last_week
)

# Food tracking metrics
food_photos_analyzed_total = Counter(
    'food_photos_analyzed_total',
    'Total food photos analyzed',
    ['confidence_level']  # high/medium/low
)

food_photo_processing_duration_seconds = Histogram(
    'food_photo_processing_duration_seconds',
    'Food photo analysis time',
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 15.0, 30.0]
)

# Agent metrics
agent_response_duration_seconds = Histogram(
    'agent_response_duration_seconds',
    'Agent response generation time',
    ['model', 'complexity'],  # haiku/sonnet, simple/complex
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0]
)

agent_token_usage_total = Counter(
    'agent_token_usage_total',
    'Total AI tokens used',
    ['provider', 'model', 'type']  # openai/anthropic, gpt-4o/sonnet, input/output
)

# Database metrics
db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query execution time',
    ['query_type'],  # select/insert/update/delete
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

db_connections_active = Gauge(
    'db_connections_active',
    'Active database connections'
)

db_pool_size = Gauge(
    'db_pool_size',
    'Database connection pool size',
    ['state']  # available/in_use
)

# API usage metrics
external_api_calls_total = Counter(
    'external_api_calls_total',
    'External API calls',
    ['service', 'status']  # openai/anthropic/usda, success/error
)

external_api_duration_seconds = Histogram(
    'external_api_duration_seconds',
    'External API call duration',
    ['service'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)
```

### 2.2 Metrics Endpoint

**Files to Modify:**
- `src/api/routes.py` - Add metrics endpoint:
  ```python
  from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
  from fastapi import Response

  @router.get("/metrics")
  async def metrics():
      """Prometheus metrics endpoint"""
      return Response(
          content=generate_latest(),
          media_type=CONTENT_TYPE_LATEST
      )
  ```

### 2.3 Instrumentation Points

**Files to Modify:**

1. **`src/bot.py`:**
   - Wrap `handle_message` with timing decorator
   - Wrap `handle_photo` with timing + counter
   - Wrap `handle_voice` with timing + counter
   - Add error counters to exception handlers

2. **`src/api/routes.py`:**
   - Add middleware for automatic HTTP metrics (in middleware.py)
   - Track endpoint-specific business metrics (e.g., food entries created)

3. **`src/agent/__init__.py`:**
   - Track agent response time by model
   - Track token usage from PydanticAI responses

4. **`src/utils/vision.py`:**
   - Track food photo processing time
   - Track confidence levels

5. **`src/db/connection.py`:**
   - Track connection pool stats
   - Instrument query timing (wrap connection context manager)

### 2.4 Background Metrics Collection

**Files to Create:**
- `src/observability/metrics_collector.py` - Background task to calculate gauge metrics

**Implementation:**
- Run periodic task (every 60 seconds) to calculate:
  - Active users (last hour/day/week from database)
  - Database connection pool stats
  - Memory usage (using psutil)
  - CPU usage (using psutil)

**Files to Modify:**
- `src/main.py` - Start metrics collector task:
  ```python
  from src.observability.metrics_collector import start_metrics_collector

  async def main():
      # ... after db init
      if ENABLE_METRICS:
          asyncio.create_task(start_metrics_collector())
  ```

---

## Phase 3: OpenTelemetry Distributed Tracing

**Goal:** Add distributed tracing for end-to-end request flow visibility

### 3.1 OTEL Infrastructure

**Files to Create:**
- `src/observability/tracing.py` - OpenTelemetry initialization and helpers

**Implementation in `tracing.py`:**
```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
from opentelemetry.sdk.resources import Resource
from src.config import OTEL_SERVICE_NAME, OTEL_EXPORTER_OTLP_ENDPOINT

def init_tracing():
    """Initialize OpenTelemetry tracing"""
    if not ENABLE_TRACING or not OTEL_EXPORTER_OTLP_ENDPOINT:
        logger.info("Tracing disabled or no OTLP endpoint configured")
        return

    resource = Resource.create({"service.name": OTEL_SERVICE_NAME})
    provider = TracerProvider(resource=resource)

    # Export to OTLP endpoint (Jaeger, Tempo, or Grafana Cloud)
    otlp_exporter = OTLPSpanExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT)
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    trace.set_tracer_provider(provider)

    # Auto-instrument FastAPI
    FastAPIInstrumentor.instrument()

    # Auto-instrument psycopg (database)
    PsycopgInstrumentor().instrument()

    logger.info(f"OpenTelemetry tracing initialized, exporting to {OTEL_EXPORTER_OTLP_ENDPOINT}")

def get_tracer():
    """Get tracer for manual instrumentation"""
    return trace.get_tracer(__name__)
```

### 3.2 Manual Span Creation

**Files to Modify:**

1. **`src/bot.py`:**
   - Add span for Telegram message handling
   - Add span for photo analysis
   - Propagate trace context through message processing

2. **`src/utils/vision.py`:**
   - Create span for food photo analysis
   - Add attributes: model, confidence, food_count

3. **`src/agent/__init__.py`:**
   - Create span for agent response generation
   - Add attributes: model, prompt_tokens, completion_tokens

4. **`src/db/queries.py`:**
   - Auto-instrumented by PsycopgInstrumentor, but add custom attributes for query type

**Example Instrumentation Pattern:**
```python
from src.observability.tracing import get_tracer

tracer = get_tracer()

async def handle_photo(update, context):
    with tracer.start_as_current_span("telegram.handle_photo") as span:
        span.set_attribute("user_id", user_id)
        span.set_attribute("photo_size", photo.file_size)

        # Photo analysis
        with tracer.start_as_current_span("vision.analyze_food") as analysis_span:
            analysis = await analyze_food_photo(photo_path)
            analysis_span.set_attribute("confidence", analysis.confidence)
            analysis_span.set_attribute("food_count", len(analysis.foods))
```

### 3.3 Trace Context Propagation

**Challenge:** Telegram bot doesn't have HTTP headers for trace propagation

**Solution:**
- Generate trace ID at message entry point
- Store in context.user_data for the conversation
- Pass through all async function calls

**Implementation:**
- Add trace_id to all major function signatures as optional parameter
- Store in database for long-running operations (reminders)

---

## Phase 4: Infrastructure Setup (Docker Compose)

**Goal:** Deploy observability backend services

### 4.1 Observability Stack Services

**Files to Create:**
- `docker-compose.observability.yml` - Separate compose file for observability stack

**Services to Add:**

```yaml
version: '3.8'

services:
  # Prometheus - Metrics collection
  prometheus:
    image: prom/prometheus:v2.48.0
    ports:
      - "9090:9090"
    volumes:
      - ./observability/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.enable-lifecycle'
    networks:
      - health-agent-network

  # Grafana - Visualization
  grafana:
    image: grafana/grafana:10.2.2
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
      GF_USERS_ALLOW_SIGN_UP: false
      GF_INSTALL_PLUGINS: grafana-piechart-panel
    volumes:
      - ./observability/grafana/provisioning:/etc/grafana/provisioning
      - ./observability/grafana/dashboards:/var/lib/grafana/dashboards
      - grafana_data:/var/lib/grafana
    depends_on:
      - prometheus
    networks:
      - health-agent-network

  # Jaeger - Distributed tracing (all-in-one for dev)
  jaeger:
    image: jaegertracing/all-in-one:1.52
    ports:
      - "16686:16686"  # Jaeger UI
      - "4318:4318"    # OTLP HTTP receiver
      - "4317:4317"    # OTLP gRPC receiver
    environment:
      COLLECTOR_OTLP_ENABLED: true
    networks:
      - health-agent-network

volumes:
  prometheus_data:
  grafana_data:

networks:
  health-agent-network:
    external: true  # Connect to existing health-agent network
```

### 4.2 Prometheus Configuration

**Files to Create:**
- `observability/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'health-agent-api'
    static_configs:
      - targets: ['health-agent-api:8080']
    metrics_path: '/metrics'
```

### 4.3 Update Main Docker Compose

**Files to Modify:**
- `docker-compose.yml` - Add network and expose metrics

```yaml
services:
  health-agent-bot:
    # ... existing config
    environment:
      # ... existing vars
      ENABLE_SENTRY: "true"
      ENABLE_METRICS: "true"
      ENABLE_TRACING: "true"
      OTEL_EXPORTER_OTLP_ENDPOINT: "http://jaeger:4318/v1/traces"
    networks:
      - health-agent-network

  health-agent-api:
    # ... existing config
    environment:
      # ... existing vars
      ENABLE_SENTRY: "true"
      ENABLE_METRICS: "true"
      ENABLE_TRACING: "true"
      OTEL_EXPORTER_OTLP_ENDPOINT: "http://jaeger:4318/v1/traces"
    networks:
      - health-agent-network

networks:
  health-agent-network:
    driver: bridge
```

---

## Phase 5: Grafana Dashboards

**Goal:** Create pre-built dashboards for monitoring

### 5.1 Dashboard Configuration Files

**Files to Create:**

1. **`observability/grafana/provisioning/datasources/datasources.yml`**
```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true

  - name: Jaeger
    type: jaeger
    access: proxy
    url: http://jaeger:16686
```

2. **`observability/grafana/provisioning/dashboards/dashboards.yml`**
```yaml
apiVersion: 1

providers:
  - name: 'Health Agent'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    options:
      path: /var/lib/grafana/dashboards
```

3. **Dashboard JSON files:**
   - `observability/grafana/dashboards/main_dashboard.json` - Main overview dashboard
   - `observability/grafana/dashboards/bot_dashboard.json` - Telegram bot metrics
   - `observability/grafana/dashboards/api_dashboard.json` - REST API metrics
   - `observability/grafana/dashboards/database_dashboard.json` - Database metrics
   - `observability/grafana/dashboards/ai_dashboard.json` - AI usage metrics

### 5.2 Dashboard Panels

**Main Dashboard Panels:**
1. Error Rate (errors/min) - Line chart
2. Request Latency (p50, p95, p99) - Line chart with multiple series
3. Active Users (last hour) - Stat panel
4. Total Requests Today - Stat panel
5. Token Usage (OpenAI + Anthropic) - Bar chart
6. Top Errors (last 24h) - Table
7. Food Photos Processed - Counter
8. Agent Response Time Distribution - Heatmap

**Service Dashboard (Bot):**
1. Messages per Minute - Line chart
2. Message Type Distribution (text/photo/voice) - Pie chart
3. Error Rate by Handler - Line chart
4. Response Time by Message Type - Line chart with percentiles
5. Top Commands Used - Bar chart
6. User Engagement (messages per user) - Histogram

**Database Dashboard:**
1. Query Count (by type) - Stacked area chart
2. Query Latency (p50, p95, p99) - Line chart
3. Connection Pool Usage - Gauge
4. Slow Queries (>100ms) - Table
5. Database Size - Stat panel
6. Active Connections - Time series

### 5.3 Alerting Rules

**Files to Create:**
- `observability/grafana/provisioning/alerting/alerts.yml`

**Alert Rules:**
1. **High Error Rate:** Error rate > 1% for 5 minutes
2. **High Latency:** p95 latency > 3 seconds for 5 minutes
3. **Database Connection Pool Exhausted:** All connections in use for 2 minutes
4. **API Rate Limit Approaching:** External API calls > 80% of limit

---

## Phase 6: Testing & Validation

**Goal:** Verify observability stack works correctly

### 6.1 Integration Tests

**Files to Create:**
- `tests/test_metrics.py` - Test metrics collection
- `tests/test_tracing.py` - Test span creation
- `tests/test_sentry_integration.py` - Test error capture

**Test Scenarios:**
1. Trigger error and verify Sentry captures it
2. Make API call and verify metrics incremented
3. Send Telegram message and verify trace created
4. Analyze food photo and verify all spans present
5. Check database queries are instrumented
6. Verify user context attached to errors

### 6.2 Load Testing

**Files to Create:**
- `scripts/load_test.py` - Generate load for testing

**Test Scenarios:**
1. Simulate 100 concurrent API requests
2. Monitor dashboard during load
3. Verify alerts fire correctly
4. Check trace sampling works
5. Verify metrics don't impact performance (<5% overhead)

---

## Phase 7: Documentation

**Goal:** Document observability for developers and operators

### 7.1 Documentation Files

**Files to Create:**

1. **`docs/OBSERVABILITY.md`** - Main observability guide
   - Architecture overview
   - How to access dashboards
   - Metrics catalog
   - How to add new metrics
   - Tracing best practices
   - Alert runbook

2. **`docs/METRICS_CATALOG.md`** - Complete metrics reference
   - All metrics with descriptions
   - Labels and their meanings
   - Query examples

3. **`docs/RUNBOOK.md`** - Operational runbook
   - Common issues and solutions
   - How to investigate errors
   - Dashboard interpretation guide
   - Alert response procedures

4. **`docs/DEVELOPMENT_OBSERVABILITY.md`** - Development guide
   - How to run observability stack locally
   - How to instrument new code
   - Testing observability features
   - Debugging with traces

---

## Phase 8: Production Rollout

**Goal:** Safely deploy observability to production

### 8.1 Staged Rollout Plan

**Stage 1: Development (Week 1)**
- Deploy full observability stack locally
- Test all features
- Fix any issues
- Optimize performance

**Stage 2: Staging (Week 2)**
- Deploy to staging environment
- Monitor for 3 days
- Verify no performance impact
- Tune sampling rates
- Validate alerts

**Stage 3: Production Canary (Week 3)**
- Enable Sentry only (low risk)
- Enable metrics with high cardinality limits
- Monitor for 2 days
- If stable, enable tracing at 1% sampling

**Stage 4: Production Full (Week 4)**
- Increase trace sampling to 10%
- Enable all dashboards
- Enable alerting
- Train team on using observability tools

### 8.2 Configuration Per Environment

**Development:**
```bash
SENTRY_TRACES_SAMPLE_RATE=1.0  # 100% sampling
ENABLE_SENTRY=true
ENABLE_METRICS=true
ENABLE_TRACING=true
```

**Production:**
```bash
SENTRY_TRACES_SAMPLE_RATE=0.1  # 10% sampling
ENABLE_SENTRY=true
ENABLE_METRICS=true
ENABLE_TRACING=true
OTEL_EXPORTER_OTLP_ENDPOINT=https://tempo.grafana.net:443  # Grafana Cloud
```

---

## Configuration Management

### Environment Variables Summary

| Variable | Development | Production | Purpose |
|----------|------------|------------|---------|
| `SENTRY_DSN` | Test project DSN | Prod project DSN | Sentry error tracking |
| `SENTRY_ENVIRONMENT` | development | production | Environment tagging |
| `SENTRY_TRACES_SAMPLE_RATE` | 1.0 | 0.1 | Trace sampling rate |
| `ENABLE_SENTRY` | true | true | Toggle Sentry |
| `ENABLE_METRICS` | true | true | Toggle Prometheus |
| `ENABLE_TRACING` | true | true | Toggle OpenTelemetry |
| `OTEL_SERVICE_NAME` | health-agent | health-agent | Service identifier |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | http://jaeger:4318 | https://otlp.grafana.net | Trace export destination |

---

## Risks & Mitigations

### Risk 1: Performance Impact
**Impact:** Observability adds latency and CPU overhead
**Mitigation:**
- Use async exporters
- Sample traces in production (10%)
- Benchmark before/after
- Add kill switch (ENABLE_* flags)

### Risk 2: High Cardinality Metrics
**Impact:** Prometheus memory usage explodes with unlimited labels
**Mitigation:**
- Limit user_id labels (use aggregated metrics)
- Restrict endpoint labels to route patterns
- Monitor Prometheus memory usage
- Document cardinality guidelines

### Risk 3: Trace Context Loss
**Impact:** Telegram bot doesn't have HTTP headers for propagation
**Mitigation:**
- Generate trace_id at message entry
- Store in context.user_data
- Pass explicitly through async calls
- Document pattern for developers

### Risk 4: Alert Fatigue
**Impact:** Too many false positive alerts
**Mitigation:**
- Start with conservative thresholds
- Tune based on baseline metrics
- Use time windows (5+ minutes)
- Separate warning vs critical alerts

### Risk 5: Cost (Grafana Cloud)
**Impact:** Metrics/traces storage can be expensive
**Mitigation:**
- Start with self-hosted stack
- Optimize sampling rates
- Set retention policies (30 days)
- Monitor billing dashboards

---

## File Change Summary

### New Files to Create (27 files)

**Observability Core:**
1. `src/observability/__init__.py`
2. `src/observability/sentry_config.py`
3. `src/observability/context.py`
4. `src/observability/metrics.py`
5. `src/observability/metrics_middleware.py`
6. `src/observability/metrics_collector.py`
7. `src/observability/tracing.py`

**Infrastructure:**
8. `docker-compose.observability.yml`
9. `observability/prometheus.yml`
10. `observability/grafana/provisioning/datasources/datasources.yml`
11. `observability/grafana/provisioning/dashboards/dashboards.yml`
12. `observability/grafana/provisioning/alerting/alerts.yml`

**Dashboards:**
13. `observability/grafana/dashboards/main_dashboard.json`
14. `observability/grafana/dashboards/bot_dashboard.json`
15. `observability/grafana/dashboards/api_dashboard.json`
16. `observability/grafana/dashboards/database_dashboard.json`
17. `observability/grafana/dashboards/ai_dashboard.json`

**Tests:**
18. `tests/test_observability.py`
19. `tests/test_metrics.py`
20. `tests/test_tracing.py`
21. `tests/test_sentry_integration.py`
22. `scripts/test_sentry.py`
23. `scripts/load_test.py`

**Documentation:**
24. `docs/OBSERVABILITY.md`
25. `docs/METRICS_CATALOG.md`
26. `docs/RUNBOOK.md`
27. `docs/DEVELOPMENT_OBSERVABILITY.md`

### Files to Modify (11 files)

1. `requirements.txt` - Add observability dependencies
2. `.env.example` - Add observability configuration
3. `src/config.py` - Add observability settings
4. `src/main.py` - Initialize observability
5. `src/bot.py` - Add metrics, tracing, and user context
6. `src/api/server.py` - Integrate Sentry with FastAPI
7. `src/api/routes.py` - Add /metrics endpoint, instrument handlers
8. `src/agent/__init__.py` - Track agent metrics
9. `src/utils/vision.py` - Track food photo analysis
10. `src/db/connection.py` - Track connection pool stats
11. `docker-compose.yml` - Add network and environment variables

---

## Implementation Timeline

### Week 1: Foundation
- Days 1-2: Add dependencies, create observability module structure
- Days 3-4: Implement Sentry integration
- Day 5: Testing and validation

### Week 2: Metrics
- Days 1-2: Implement metrics infrastructure
- Days 3-4: Instrument all key paths
- Day 5: Testing and validation

### Week 3: Tracing
- Days 1-2: Implement OpenTelemetry infrastructure
- Days 3-4: Add manual spans to key operations
- Day 5: Testing and validation

### Week 4: Infrastructure
- Days 1-2: Set up Docker Compose observability stack
- Days 3-4: Configure Prometheus and Grafana
- Day 5: Testing end-to-end

### Week 5: Dashboards & Alerts
- Days 1-3: Create all dashboards
- Day 4: Configure alert rules
- Day 5: Testing and tuning

### Week 6: Documentation & Rollout
- Days 1-2: Write documentation
- Days 3-5: Staged production rollout

**Total Estimated Time:** 6 weeks (30 working days) or ~12 hours of focused implementation time per the issue estimate

---

## Success Criteria

1. ✅ **Error Tracking:** All exceptions captured in Sentry with user context
2. ✅ **Metrics Visibility:** All key metrics exposed and queryable
3. ✅ **Tracing Coverage:** End-to-end traces for all user flows
4. ✅ **Dashboard Usability:** Non-technical users can understand dashboards
5. ✅ **Alert Reliability:** Alerts fire correctly with <5% false positives
6. ✅ **Performance:** <5% latency overhead from observability
7. ✅ **Documentation:** Complete runbooks and guides available

---

## Next Steps

1. **Review this plan** with the team and stakeholders
2. **Set up Sentry account** and obtain DSN for development environment
3. **Begin Phase 1** implementation (Foundation & Sentry)
4. **Create GitHub project board** to track implementation progress
5. **Schedule weekly check-ins** to review progress and adjust timeline
