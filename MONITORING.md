# Monitoring Infrastructure

This document describes the monitoring infrastructure for the health-agent application.

## Overview

The application includes comprehensive monitoring using:
- **Sentry** for error tracking, transaction performance, and contextual debugging
- **Prometheus** for operational metrics (request rates, latencies, error rates, cache/database performance)

## Configuration

### Environment Variables

```bash
# Sentry Configuration
ENABLE_SENTRY=false                    # Enable/disable Sentry (default: false)
SENTRY_DSN=                            # Your Sentry DSN from sentry.io
SENTRY_ENVIRONMENT=development         # Environment name (development/staging/production)
SENTRY_TRACES_SAMPLE_RATE=1.0          # Trace sampling rate 0.0-1.0 (1.0 = 100%)

# Prometheus Configuration
ENABLE_PROMETHEUS=true                 # Enable/disable Prometheus (default: true)
PROMETHEUS_PORT=9090                   # Port for Prometheus metrics (if separate)
```

### Recommended Settings by Environment

**Development:**
```bash
ENABLE_SENTRY=false
ENABLE_PROMETHEUS=true
SENTRY_TRACES_SAMPLE_RATE=1.0
```

**Staging:**
```bash
ENABLE_SENTRY=true
ENABLE_PROMETHEUS=true
SENTRY_ENVIRONMENT=staging
SENTRY_TRACES_SAMPLE_RATE=1.0
```

**Production:**
```bash
ENABLE_SENTRY=true
ENABLE_PROMETHEUS=true
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1  # 10% sampling to reduce overhead
```

## Sentry Error Tracking

### Setup

1. Create a Sentry project at https://sentry.io
2. Copy your DSN from project settings
3. Set environment variables:
   ```bash
   ENABLE_SENTRY=true
   SENTRY_DSN=https://your-dsn@sentry.io/project-id
   SENTRY_ENVIRONMENT=production
   ```

### Features

- **Automatic Exception Capture**: All unhandled exceptions are automatically captured
- **User Context**: Every error includes the user_id for easy debugging
- **Request Context**: Each error includes request_id and operation name
- **Transaction Performance**: Tracks API endpoint performance
- **Custom Tags**: Additional context like model name, endpoint, method

### What Gets Tracked

- Unhandled exceptions in API endpoints
- Unhandled exceptions in Telegram bot
- Agent/AI model errors
- Database errors (when not handled)
- Custom captured exceptions

### Viewing Errors

1. Log into Sentry dashboard
2. Navigate to Issues
3. Filter by:
   - Environment
   - User ID
   - Request ID
   - Error type

## Prometheus Metrics

### Accessing Metrics

Metrics are exposed at: `http://your-api-host:8080/metrics`

### Available Metrics

#### HTTP Request Metrics

- `http_requests_total{method, endpoint, status}` - Total HTTP requests
- `http_request_duration_seconds{method, endpoint}` - Request latency histogram
- `http_errors_total{method, endpoint, error_type}` - Total errors by type

#### Database Metrics

- `db_queries_total{query_type, table}` - Total database queries
- `db_query_duration_seconds{query_type}` - Query latency histogram
- `db_connection_pool_size` - Current connection pool size
- `db_connection_pool_available` - Available connections in pool

#### Agent/AI Metrics

- `agent_calls_total{agent_type, status}` - Total AI agent calls
- `agent_call_duration_seconds{agent_type}` - Agent call latency
- `agent_tokens_used_total{agent_type, token_type}` - Token usage (input/output)

#### Cache Metrics

- `cache_operations_total{operation, result}` - Cache operations (hit/miss)
- `cache_hit_rate` - Current cache hit rate

### Setting Up Prometheus Scraper

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'health-agent'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8080']
```

### Example Prometheus Queries

**Request rate by endpoint:**
```promql
rate(http_requests_total[5m])
```

**P95 latency:**
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

**Error rate:**
```promql
rate(http_errors_total[5m])
```

**Database connection pool usage:**
```promql
db_connection_pool_size - db_connection_pool_available
```

**Agent token usage per hour:**
```promql
rate(agent_tokens_used_total[1h]) * 3600
```

## Grafana Dashboard

### Importing the Dashboard

1. Open Grafana
2. Go to Dashboards → Import
3. Upload `dashboards/health-agent-metrics.json` (if available)
4. Select your Prometheus data source
5. Click Import

### Dashboard Panels

1. **Request Rate** - HTTP requests per second by endpoint
2. **Response Time (p50, p95, p99)** - Latency percentiles
3. **Error Rate** - Errors per second by type
4. **Database Query Performance** - Query latency histogram
5. **Database Connection Pool** - Pool size and availability
6. **Agent Call Performance** - AI agent call duration
7. **Agent Token Usage** - Token consumption over time
8. **Cache Hit Rate** - Cache effectiveness

## Performance Impact

The monitoring infrastructure is designed for minimal performance impact:

- **Sentry**: <1% overhead with 10% sampling (0.1 sample rate)
- **Prometheus**: <0.5% overhead (metrics are in-memory counters)
- **Total**: <1.5% overall impact on request latency

### Optimization Strategies

1. **Reduce Sentry sampling** for high-traffic production:
   ```bash
   SENTRY_TRACES_SAMPLE_RATE=0.01  # 1% sampling
   ```

2. **Disable monitoring** in development if needed:
   ```bash
   ENABLE_SENTRY=false
   ENABLE_PROMETHEUS=false
   ```

3. **Lazy imports**: Monitoring modules are only imported when enabled

## Troubleshooting

### Sentry Not Capturing Errors

1. Check `ENABLE_SENTRY=true`
2. Verify `SENTRY_DSN` is set correctly
3. Check logs for "Sentry initialized" message
4. Test with: `capture_exception(Exception("test"))`

### Prometheus Metrics Not Appearing

1. Check `ENABLE_PROMETHEUS=true`
2. Access `/metrics` endpoint directly
3. Check logs for "Prometheus metrics initialized"
4. Verify Prometheus scraper configuration

### High Memory Usage

1. Reduce Sentry sample rate
2. Check for high-cardinality metrics
3. Limit metric labels (don't use user IDs as labels)

## Monitoring Best Practices

### For Developers

1. **Add context to errors**:
   ```python
   from src.monitoring import capture_exception
   capture_exception(error, user_id=user_id, operation="process_food")
   ```

2. **Track custom metrics** (if needed):
   ```python
   from src.monitoring.prometheus_metrics import metrics
   metrics.custom_counter.labels(type="important").inc()
   ```

3. **Use database query tracking**:
   ```python
   @track_query("SELECT", "users")
   async def get_user(user_id: str):
       # query implementation
   ```

### For DevOps

1. **Set up alerts** for:
   - Error rate > threshold
   - P95 latency > threshold
   - Database pool exhaustion
   - High token usage

2. **Monitor trends**:
   - Request rate over time
   - Error rate by endpoint
   - Agent performance degradation

3. **Set retention policies**:
   - Prometheus: 15-30 days
   - Sentry: 30-90 days
   - Grafana: based on Prometheus retention

## Architecture

### Monitoring Flow

```
Request → Middleware → Track Metrics → Handler → Response
                    ↓
                  Sentry (if error)
                    ↓
                Prometheus (metrics)
```

### Key Components

1. **src/monitoring/__init__.py** - Main exports
2. **src/monitoring/sentry_config.py** - Sentry initialization and helpers
3. **src/monitoring/prometheus_metrics.py** - Metric definitions
4. **src/api/metrics_routes.py** - Metrics endpoint
5. **src/api/middleware.py** - Request tracking middleware

### Integration Points

- **API Server**: Middleware tracks all requests
- **Database**: Connection pool and query tracking
- **Agent**: AI call tracking and error capture
- **Bot**: Error handler for Telegram bot
- **Main**: Early Sentry init for startup errors

## Cost Considerations

### Sentry

- Free tier: 5,000 errors/month
- Paid tier: ~$26/month for 50K errors
- Recommended: Use 10% sampling in production

### Prometheus + Grafana

- Self-hosted: Free (infrastructure cost only)
- Grafana Cloud: Free tier available
- Recommended: Self-host for production

## Security

### Sensitive Data

- **DO NOT** log passwords, API keys, or tokens
- **DO NOT** include PII in metric labels
- **DO** sanitize error messages before capturing
- **DO** use user IDs (not emails) for context

### Access Control

- Restrict `/metrics` endpoint to internal networks
- Use firewall rules or authentication
- Sentry project permissions for team members

## Future Enhancements

1. **Custom Dashboards** - User-specific metrics
2. **Alerting** - PagerDuty/Slack integration
3. **APM** - Full distributed tracing
4. **Logging** - Structured logging with correlation IDs
5. **Cost Tracking** - Monitor AI API costs

## Support

For issues or questions:
1. Check logs for initialization messages
2. Verify environment variables
3. Test with minimal configuration
4. Review this documentation

## References

- Sentry Documentation: https://docs.sentry.io
- Prometheus Documentation: https://prometheus.io/docs
- Grafana Documentation: https://grafana.com/docs
