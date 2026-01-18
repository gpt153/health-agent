# Observability Stack

This document describes the observability stack for the Health Agent application, including error tracking, metrics collection, distributed tracing, and visualization.

## Table of Contents

- [Overview](#overview)
- [Components](#components)
- [Getting Started](#getting-started)
- [Error Tracking with Sentry](#error-tracking-with-sentry)
- [Metrics with Prometheus](#metrics-with-prometheus)
- [Distributed Tracing with OpenTelemetry](#distributed-tracing-with-opentelemetry)
- [Visualization with Grafana](#visualization-with-grafana)
- [Configuration](#configuration)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

The Health Agent observability stack provides comprehensive monitoring and debugging capabilities through three complementary layers:

1. **Error Tracking (Sentry)** - Capture and analyze application errors with full context
2. **Metrics (Prometheus)** - Collect and query time-series metrics for performance monitoring
3. **Distributed Tracing (OpenTelemetry + Jaeger)** - Track requests across services and identify bottlenecks
4. **Visualization (Grafana)** - Create dashboards and alerts for operational insights

### Architecture

```
┌─────────────────┐
│  Health Agent   │
│   Application   │
└────────┬────────┘
         │
         ├─────────────► Sentry (Error Tracking)
         │
         ├─────────────► Prometheus (Metrics via /metrics endpoint)
         │
         └─────────────► Jaeger (Traces via OTLP)
                               │
                               │
                         ┌─────▼──────┐
                         │  Grafana   │
                         │ Dashboards │
                         └────────────┘
```

## Components

### 1. Sentry (Error Tracking)

- **Purpose**: Capture unhandled exceptions, log errors, and performance issues
- **Integration**: FastAPI, Python logging
- **Features**:
  - Error grouping and deduplication
  - User context (user ID, username)
  - Breadcrumbs (navigation trail)
  - Release tracking (git commit SHA)
  - Environment tagging (dev/staging/prod)

### 2. Prometheus (Metrics)

- **Purpose**: Time-series metrics collection and querying
- **Integration**: Custom metrics middleware, background collector
- **Features**:
  - 30+ custom metrics across 10 categories
  - Automatic HTTP request instrumentation
  - Database connection pool monitoring
  - AI token usage tracking
  - User activity metrics

### 3. OpenTelemetry + Jaeger (Distributed Tracing)

- **Purpose**: Track request flow and identify performance bottlenecks
- **Integration**: FastAPI auto-instrumentation, PostgreSQL instrumentation
- **Features**:
  - Automatic HTTP request tracing
  - Database query tracing
  - Custom span creation
  - Trace context propagation
  - OTLP export to Jaeger

### 4. Grafana (Visualization)

- **Purpose**: Create dashboards and visualize metrics
- **Integration**: Prometheus datasource, Jaeger datasource
- **Features**:
  - 5 pre-built dashboards
  - Real-time metric updates
  - Alert rules (future)
  - Custom queries and panels

## Getting Started

### Prerequisites

- Docker and Docker Compose installed
- Health Agent application configured with environment variables
- (Optional) Sentry account and DSN

### Step 1: Start the Observability Stack

```bash
# Start Prometheus, Grafana, and Jaeger
docker-compose -f docker-compose.observability.yml up -d

# Verify services are running
docker-compose -f docker-compose.observability.yml ps
```

This will start:
- Prometheus on http://localhost:9090
- Grafana on http://localhost:3000 (admin/admin)
- Jaeger UI on http://localhost:16686

### Step 2: Configure Environment Variables

Create or update your `.env` file:

```bash
# Sentry (optional - for production error tracking)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
SENTRY_ENVIRONMENT=development
SENTRY_TRACES_SAMPLE_RATE=0.1
ENABLE_SENTRY=true

# Metrics
ENABLE_METRICS=true

# Tracing
ENABLE_TRACING=true
OTEL_SERVICE_NAME=health-agent
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
```

### Step 3: Start the Health Agent

```bash
# Start in API mode (exposes /metrics endpoint)
RUN_MODE=api python -m src.main

# Or start in bot mode
RUN_MODE=bot python -m src.main

# Or start both
RUN_MODE=both python -m src.main
```

### Step 4: Access the Dashboards

1. **Grafana**: http://localhost:3000
   - Login: admin / admin
   - Navigate to "Dashboards" → "Health Agent" folder
   - Available dashboards:
     - Main Overview
     - Telegram Bot
     - AI Agent
     - Database
     - Food Tracking

2. **Prometheus**: http://localhost:9090
   - Query metrics directly
   - Example: `rate(http_requests_total[5m])`

3. **Jaeger**: http://localhost:16686
   - Search for traces by service name
   - View trace timelines and spans

## Error Tracking with Sentry

### Initialization

Sentry is automatically initialized on application startup in `src/main.py`:

```python
from src.observability.sentry_config import init_sentry

# Initialize Sentry
init_sentry()
```

### Setting User Context

```python
from src.observability.context import set_user_context

# In your handler
set_user_context(
    user_id=str(telegram_user.id),
    username=telegram_user.username,
    metadata={"first_name": telegram_user.first_name}
)
```

### Adding Breadcrumbs

```python
from src.observability.context import add_breadcrumb

# Track user actions
add_breadcrumb(
    category="user_action",
    message="User sent photo for analysis",
    level="info",
    data={"photo_size": photo.file_size}
)
```

### Capturing Exceptions

```python
from src.observability.context import capture_exception_with_context

try:
    result = process_photo(photo)
except Exception as e:
    capture_exception_with_context(
        error=e,
        context={"photo_id": photo.file_id},
        level="error"
    )
    raise
```

### Features

- **Automatic Error Capture**: Unhandled exceptions are automatically sent to Sentry
- **Performance Monitoring**: Sample rate configurable via `SENTRY_TRACES_SAMPLE_RATE`
- **Release Tracking**: Git commit SHA is automatically tagged
- **Environment Separation**: Dev/staging/prod environments are separated

## Metrics with Prometheus

### Available Metrics

See [METRICS_CATALOG.md](./METRICS_CATALOG.md) for a complete list of available metrics.

### Accessing Metrics

**Metrics Endpoint**: http://localhost:8080/metrics

```bash
# View raw metrics
curl http://localhost:8080/metrics

# Query in Prometheus UI
# Navigate to http://localhost:9090
# Example query: rate(http_requests_total[5m])
```

### Creating Custom Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Define metric
my_counter = Counter(
    'my_operation_total',
    'Total number of my operations',
    ['operation_type', 'status']
)

# Increment metric
my_counter.labels(operation_type='foo', status='success').inc()
```

### Querying Metrics

Common Prometheus queries:

```promql
# HTTP request rate (requests per second)
rate(http_requests_total[5m])

# 95th percentile response time
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(errors_total[5m])

# Active users
active_users_total{time_period="last_hour"}

# Database connection pool utilization
db_pool_size{state="in_use"} / db_pool_size{state="total"}
```

### Metrics Collection

- **HTTP Middleware**: Automatically instruments all API requests
- **Background Collector**: Runs every 60 seconds to collect gauge metrics
- **Manual Instrumentation**: Add metrics in your code where needed

## Distributed Tracing with OpenTelemetry

### Auto-Instrumentation

FastAPI and PostgreSQL are automatically instrumented:

```python
from src.observability.tracing import init_tracing, auto_instrument_fastapi, auto_instrument_psycopg

# In main.py
init_tracing()
auto_instrument_fastapi(app)
auto_instrument_psycopg()
```

### Creating Custom Spans

```python
from src.observability.tracing import trace_span

# Context manager
with trace_span("process_photo", {"photo_id": photo_id}) as span:
    result = analyze_photo(photo)
    span.set_attribute("confidence", result.confidence)
```

### Using the Decorator

```python
from src.observability.tracing import trace_function

@trace_function(span_name="agent.generate_response")
async def generate_response(user_id: str, message: str):
    return await agent.generate(message)
```

### Adding Span Events

```python
from src.observability.tracing import get_current_span, add_span_event

span = get_current_span()
add_span_event(span, "analysis_started")
# ... do work ...
add_span_event(span, "analysis_complete", {"items_found": len(items)})
```

### Viewing Traces

1. Navigate to Jaeger UI: http://localhost:16686
2. Select "health-agent" service
3. Click "Find Traces"
4. Click on a trace to view the timeline

Traces show:
- Request flow through the application
- Database queries and their duration
- External API calls
- Custom spans you've created

## Visualization with Grafana

### Pre-built Dashboards

#### 1. Main Overview
- HTTP request rate and duration
- Active users
- Error rate
- Database connections
- AI token usage

#### 2. Telegram Bot
- Message rate by type
- Message processing duration
- Command usage
- Active users
- Error rate

#### 3. AI Agent
- Request rate by model
- Response duration
- Token usage
- Success rate
- Memory search rate

#### 4. Database
- Query rate and duration
- Connection pool status
- Query type distribution
- Success rate
- Error rate

#### 5. Food Tracking
- Entry creation rate
- Photo analysis rate
- Processing duration
- Confidence distribution
- Gamification metrics

### Creating Custom Dashboards

1. Navigate to Grafana: http://localhost:3000
2. Click "+" → "Dashboard"
3. Add a new panel
4. Select Prometheus datasource
5. Enter a PromQL query
6. Configure visualization options
7. Save the dashboard

### Setting Up Alerts (Future)

Grafana supports alerting based on metric thresholds:

```yaml
# Example alert rule (not yet configured)
alert: HighErrorRate
expr: rate(errors_total[5m]) > 0.1
for: 5m
labels:
  severity: warning
annotations:
  summary: High error rate detected
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENABLE_SENTRY` | Enable Sentry error tracking | `true` | No |
| `SENTRY_DSN` | Sentry project DSN | - | Yes (if Sentry enabled) |
| `SENTRY_ENVIRONMENT` | Environment name | `development` | No |
| `SENTRY_TRACES_SAMPLE_RATE` | Sampling rate (0.0-1.0) | `0.1` | No |
| `ENABLE_METRICS` | Enable Prometheus metrics | `true` | No |
| `ENABLE_TRACING` | Enable OpenTelemetry tracing | `true` | No |
| `OTEL_SERVICE_NAME` | Service name for traces | `health-agent` | No |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP endpoint URL | - | Yes (if tracing enabled) |

### Feature Flags

You can disable individual observability components:

```bash
# Disable Sentry
ENABLE_SENTRY=false

# Disable metrics
ENABLE_METRICS=false

# Disable tracing
ENABLE_TRACING=false
```

### Docker Compose Configuration

Customize `docker-compose.observability.yml`:

```yaml
# Change Prometheus retention period
services:
  prometheus:
    command:
      - '--storage.tsdb.retention.time=90d'  # Default: 30d

# Add Grafana plugins
services:
  grafana:
    environment:
      - GF_INSTALL_PLUGINS=grafana-piechart-panel,grafana-clock-panel
```

## Best Practices

### Error Tracking

1. **Set User Context Early**: Call `set_user_context()` at the start of request handling
2. **Add Breadcrumbs**: Track important user actions before errors occur
3. **Capture Context**: Include relevant data when capturing exceptions
4. **Use Appropriate Levels**: `error` for exceptions, `warning` for issues, `info` for context

### Metrics

1. **Avoid High Cardinality**: Don't use unbounded values in labels (e.g., user IDs)
2. **Use Consistent Labels**: Stick to a naming convention for labels
3. **Choose the Right Metric Type**:
   - Counter: Monotonically increasing values (requests, errors)
   - Gauge: Values that go up and down (active users, queue size)
   - Histogram: Distributions (duration, sizes)
4. **Normalize Paths**: Use path normalization to reduce cardinality

### Tracing

1. **Sample Appropriately**: Use sampling in production (e.g., 10% of traces)
2. **Add Meaningful Attributes**: Include data that helps debug issues
3. **Create Spans for Important Operations**: Don't over-instrument trivial operations
4. **Propagate Context**: Ensure trace context is passed across async boundaries

### Dashboards

1. **Use Time Ranges Appropriately**: Default to 1 hour, but allow customization
2. **Include Multiple Percentiles**: p50, p95, p99 for latency metrics
3. **Show Both Rate and Count**: Help understand both trends and absolute values
4. **Set Meaningful Thresholds**: Use color coding to highlight issues

## Troubleshooting

### Metrics Not Showing in Prometheus

**Problem**: Prometheus isn't scraping metrics from the application.

**Solution**:
1. Verify the application is running in API mode: `RUN_MODE=api`
2. Check metrics endpoint is accessible: `curl http://localhost:8080/metrics`
3. Verify Prometheus configuration targets the correct host
4. For Docker: Use `host.docker.internal:8080` instead of `localhost:8080`
5. Check Prometheus targets status: http://localhost:9090/targets

### Traces Not Appearing in Jaeger

**Problem**: No traces showing up in Jaeger UI.

**Solution**:
1. Verify `ENABLE_TRACING=true` in environment
2. Check `OTEL_EXPORTER_OTLP_ENDPOINT` is set correctly
3. Verify Jaeger is running: `docker-compose ps jaeger`
4. Check application logs for OTLP export errors
5. Ensure port 4318 is accessible from the application

### Grafana Dashboards Not Loading

**Problem**: Dashboards are empty or not showing data.

**Solution**:
1. Verify Prometheus datasource is configured correctly
2. Test Prometheus connection in Grafana datasources page
3. Check that the application is generating metrics
4. Verify dashboard time range matches data availability
5. Check browser console for errors

### High Memory Usage

**Problem**: Observability components using too much memory.

**Solution**:
1. **Prometheus**: Reduce retention time or decrease scrape frequency
2. **Jaeger**: Use memory storage only for development (default)
3. **Application**: Reduce sampling rates for traces
4. **Metrics**: Review metric cardinality, remove unused metrics

### Sentry Quota Exceeded

**Problem**: Sentry rate limit or quota exceeded.

**Solution**:
1. Adjust `SENTRY_TRACES_SAMPLE_RATE` to lower value (e.g., 0.01 = 1%)
2. Filter errors before sending (use `before_send` callback)
3. Upgrade Sentry plan or request quota increase
4. Temporarily disable Sentry: `ENABLE_SENTRY=false`

## Performance Impact

The observability stack is designed to have minimal performance impact:

- **Metrics Collection**: <1% CPU overhead
- **Tracing**: <2% overhead at 10% sampling rate
- **Sentry**: <1% overhead
- **Total**: <5% overhead in production with recommended settings

## Next Steps

- Review the [Metrics Catalog](./METRICS_CATALOG.md) for all available metrics
- Explore the [Runbook](./RUNBOOK.md) for operational procedures
- Set up alerting rules in Grafana
- Configure long-term storage for metrics (e.g., Thanos, Cortex)
- Integrate with on-call system (e.g., PagerDuty, Opsgenie)

## Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Sentry Documentation](https://docs.sentry.io/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
