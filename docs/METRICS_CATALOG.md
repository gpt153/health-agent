# Metrics Catalog

This document provides a comprehensive reference of all Prometheus metrics exposed by the Health Agent application.

## Table of Contents

- [Overview](#overview)
- [HTTP Metrics](#http-metrics)
- [Telegram Bot Metrics](#telegram-bot-metrics)
- [AI Agent Metrics](#ai-agent-metrics)
- [Database Metrics](#database-metrics)
- [Food Tracking Metrics](#food-tracking-metrics)
- [User Metrics](#user-metrics)
- [Error Metrics](#error-metrics)
- [External API Metrics](#external-api-metrics)
- [Memory Metrics](#memory-metrics)
- [Gamification Metrics](#gamification-metrics)
- [Query Examples](#query-examples)

## Overview

The Health Agent exposes **30+ metrics** across **10 categories**, accessible at the `/metrics` endpoint.

**Metrics Endpoint**: `http://localhost:8080/metrics`

### Metric Types

- **Counter**: Monotonically increasing value (e.g., total requests, errors)
- **Gauge**: Value that can go up or down (e.g., active users, queue size)
- **Histogram**: Distribution of values (e.g., request duration, sizes)

### Metric Naming Convention

Metrics follow Prometheus naming conventions:
- `<namespace>_<name>_<unit>`
- All lowercase with underscores
- Units: `_total` (counter), `_seconds` (duration), `_bytes` (size)

## HTTP Metrics

Metrics for REST API requests and responses.

### `http_requests_total`

**Type**: Counter
**Description**: Total number of HTTP requests received
**Labels**:
- `method`: HTTP method (GET, POST, PUT, DELETE)
- `endpoint`: Normalized endpoint path
- `status`: HTTP status code (200, 404, 500, etc.)

**Example**:
```promql
# Request rate
rate(http_requests_total[5m])

# Error rate (4xx and 5xx)
rate(http_requests_total{status=~"[45].."}[5m])

# Success rate
rate(http_requests_total{status=~"2.."}[5m]) / rate(http_requests_total[5m])
```

### `http_request_duration_seconds`

**Type**: Histogram
**Description**: HTTP request duration in seconds
**Labels**:
- `method`: HTTP method
- `endpoint`: Normalized endpoint path

**Buckets**: 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0

**Example**:
```promql
# 95th percentile latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Average latency
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])
```

### `http_requests_in_progress`

**Type**: Gauge
**Description**: Number of HTTP requests currently being processed
**Labels**:
- `method`: HTTP method
- `endpoint`: Normalized endpoint path

**Example**:
```promql
# Current in-flight requests
http_requests_in_progress

# Max concurrent requests
max_over_time(http_requests_in_progress[1h])
```

## Telegram Bot Metrics

Metrics for Telegram bot message processing.

### `telegram_messages_total`

**Type**: Counter
**Description**: Total number of Telegram messages processed
**Labels**:
- `message_type`: Type of message (text, photo, voice, document, location)
- `status`: Processing status (success, error)

**Example**:
```promql
# Message rate
rate(telegram_messages_total[5m])

# Photo message rate
rate(telegram_messages_total{message_type="photo"}[5m])

# Error rate
rate(telegram_messages_total{status="error"}[5m])
```

### `telegram_message_duration_seconds`

**Type**: Histogram
**Description**: Time taken to process a Telegram message
**Labels**:
- `message_type`: Type of message

**Buckets**: 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0

**Example**:
```promql
# 95th percentile processing time
histogram_quantile(0.95, rate(telegram_message_duration_seconds_bucket[5m]))

# Average processing time by type
rate(telegram_message_duration_seconds_sum[5m]) / rate(telegram_message_duration_seconds_count[5m])
```

### `telegram_commands_total`

**Type**: Counter
**Description**: Total number of Telegram commands executed
**Labels**:
- `command`: Command name (/start, /help, /stats, etc.)

**Example**:
```promql
# Most popular commands
topk(5, increase(telegram_commands_total[1h]))

# Command rate
rate(telegram_commands_total[5m])
```

## AI Agent Metrics

Metrics for AI agent requests and token usage.

### `agent_requests_total`

**Type**: Counter
**Description**: Total number of AI agent requests
**Labels**:
- `model`: AI model used (haiku, sonnet, opus)
- `status`: Request status (success, error)

**Example**:
```promql
# Request rate by model
rate(agent_requests_total[5m])

# Success rate
rate(agent_requests_total{status="success"}[5m]) / rate(agent_requests_total[5m])
```

### `agent_response_duration_seconds`

**Type**: Histogram
**Description**: Time taken for AI agent to generate response
**Labels**:
- `model`: AI model used
- `complexity`: Query complexity (simple, complex)

**Buckets**: 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0

**Example**:
```promql
# 95th percentile response time
histogram_quantile(0.95, rate(agent_response_duration_seconds_bucket[5m]))

# Average response time by model
rate(agent_response_duration_seconds_sum{model="haiku"}[5m]) / rate(agent_response_duration_seconds_count{model="haiku"}[5m])
```

### `agent_token_usage_total`

**Type**: Counter
**Description**: Total number of AI tokens used
**Labels**:
- `provider`: AI provider (anthropic, openai)
- `model`: Model name
- `token_type`: Type of tokens (input, output)

**Example**:
```promql
# Token usage rate
rate(agent_token_usage_total[5m])

# Input vs output tokens
sum by (token_type) (rate(agent_token_usage_total[1h]))

# Cost estimation (tokens/1000 * price)
rate(agent_token_usage_total{model="haiku", token_type="input"}[1h]) / 1000 * 0.00025
```

## Database Metrics

Metrics for PostgreSQL database queries and connections.

### `db_queries_total`

**Type**: Counter
**Description**: Total number of database queries executed
**Labels**:
- `query_type`: Type of query (select, insert, update, delete)
- `status`: Query status (success, error)

**Example**:
```promql
# Query rate
rate(db_queries_total[5m])

# Write vs read ratio
rate(db_queries_total{query_type=~"insert|update|delete"}[5m]) / rate(db_queries_total{query_type="select"}[5m])
```

### `db_query_duration_seconds`

**Type**: Histogram
**Description**: Database query execution time
**Labels**:
- `query_type`: Type of query

**Buckets**: 0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0

**Example**:
```promql
# 95th percentile query time
histogram_quantile(0.95, rate(db_query_duration_seconds_bucket[5m]))

# Slow queries (>100ms)
histogram_quantile(0.99, rate(db_query_duration_seconds_bucket[5m])) > 0.1
```

### `db_connections_active`

**Type**: Gauge
**Description**: Number of active database connections

**Example**:
```promql
# Current active connections
db_connections_active

# Connection pool utilization
db_connections_active / db_pool_size{state="total"}
```

### `db_pool_size`

**Type**: Gauge
**Description**: Database connection pool size
**Labels**:
- `state`: Pool state (total, available, in_use)

**Example**:
```promql
# Available connections
db_pool_size{state="available"}

# Pool exhaustion risk
db_pool_size{state="available"} < 2
```

## Food Tracking Metrics

Metrics for food entry creation and photo analysis.

### `food_entries_created_total`

**Type**: Counter
**Description**: Total number of food entries created
**Labels**:
- `entry_type`: Entry creation method (photo, manual, voice)

**Example**:
```promql
# Entry creation rate
rate(food_entries_created_total[5m])

# Photo vs manual entries
sum by (entry_type) (increase(food_entries_created_total[1h]))
```

### `food_photos_analyzed_total`

**Type**: Counter
**Description**: Total number of food photos analyzed
**Labels**:
- `confidence_level`: Analysis confidence (high, medium, low)

**Example**:
```promql
# Photo analysis rate
rate(food_photos_analyzed_total[5m])

# High confidence rate
rate(food_photos_analyzed_total{confidence_level="high"}[5m]) / rate(food_photos_analyzed_total[5m])

# Low confidence warnings
increase(food_photos_analyzed_total{confidence_level="low"}[1h]) > 10
```

### `food_photo_processing_duration_seconds`

**Type**: Histogram
**Description**: Time taken to analyze food photo

**Buckets**: 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0

**Example**:
```promql
# 95th percentile processing time
histogram_quantile(0.95, rate(food_photo_processing_duration_seconds_bucket[5m]))

# Average processing time
rate(food_photo_processing_duration_seconds_sum[5m]) / rate(food_photo_processing_duration_seconds_count[5m])
```

## User Metrics

Metrics for user activity and registration.

### `active_users_total`

**Type**: Gauge
**Description**: Number of active users in different time periods
**Labels**:
- `time_period`: Time period (last_hour, last_day, last_week)

**Example**:
```promql
# Active users in last hour
active_users_total{time_period="last_hour"}

# Daily active users trend
active_users_total{time_period="last_day"}
```

### `user_registrations_total`

**Type**: Counter
**Description**: Total number of new user registrations

**Example**:
```promql
# Registration rate
rate(user_registrations_total[1h])

# New users today
increase(user_registrations_total[24h])
```

## Error Metrics

Metrics for application errors and exceptions.

### `errors_total`

**Type**: Counter
**Description**: Total number of errors
**Labels**:
- `error_type`: Type/class of error (ValueError, ConnectionError, etc.)
- `component`: Component where error occurred (bot, api, database, agent)

**Example**:
```promql
# Error rate
rate(errors_total[5m])

# Errors by component
sum by (component) (rate(errors_total[5m]))

# Most common error types
topk(5, increase(errors_total[1h]))
```

## External API Metrics

Metrics for external API calls (OpenAI, USDA, etc.).

### `external_api_calls_total`

**Type**: Counter
**Description**: Total number of external API calls
**Labels**:
- `service`: External service name (openai, usda, etc.)
- `status`: Call status (success, error)

**Example**:
```promql
# API call rate
rate(external_api_calls_total[5m])

# Success rate by service
rate(external_api_calls_total{status="success"}[5m]) / rate(external_api_calls_total[5m])
```

### `external_api_duration_seconds`

**Type**: Histogram
**Description**: External API call duration
**Labels**:
- `service`: External service name

**Buckets**: 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0

**Example**:
```promql
# 95th percentile latency
histogram_quantile(0.95, rate(external_api_duration_seconds_bucket[5m]))

# Slow API calls
histogram_quantile(0.95, rate(external_api_duration_seconds_bucket{service="openai"}[5m])) > 5
```

## Memory Metrics

Metrics for semantic memory search operations.

### `memory_searches_total`

**Type**: Counter
**Description**: Total number of memory searches
**Labels**:
- `search_type`: Type of search (conversation, user_profile, recommendations)
- `status`: Search status (success, error)

**Example**:
```promql
# Search rate
rate(memory_searches_total[5m])

# Search type distribution
sum by (search_type) (increase(memory_searches_total[1h]))
```

## Gamification Metrics

Metrics for gamification features (XP, achievements).

### `gamification_xp_awarded_total`

**Type**: Counter
**Description**: Total XP awarded to users
**Labels**:
- `activity_type`: Type of activity (food_entry, quiz_completion, streak, etc.)

**Example**:
```promql
# XP award rate
rate(gamification_xp_awarded_total[5m])

# XP by activity
sum by (activity_type) (increase(gamification_xp_awarded_total[1h]))
```

### `gamification_achievements_unlocked_total`

**Type**: Counter
**Description**: Total achievements unlocked
**Labels**:
- `achievement_type`: Type of achievement (first_meal, week_streak, etc.)

**Example**:
```promql
# Achievement unlock rate
rate(gamification_achievements_unlocked_total[5m])

# Most common achievements
topk(5, increase(gamification_achievements_unlocked_total[7d]))
```

## Query Examples

### Performance Monitoring

```promql
# Overall request rate (requests/sec)
sum(rate(http_requests_total[5m]))

# Error rate percentage
sum(rate(http_requests_total{status=~"[45].."}[5m])) / sum(rate(http_requests_total[5m])) * 100

# 95th percentile response time
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))

# Requests slower than 1 second
sum(rate(http_request_duration_seconds_bucket{le="1.0"}[5m]))
```

### Capacity Planning

```promql
# Database connection pool utilization
db_pool_size{state="in_use"} / db_pool_size{state="total"} * 100

# Peak concurrent requests
max_over_time(http_requests_in_progress[1h])

# Token usage trend (for cost estimation)
sum(rate(agent_token_usage_total[1h])) * 3600
```

### User Engagement

```promql
# Daily active users
active_users_total{time_period="last_day"}

# Average messages per user
sum(increase(telegram_messages_total[24h])) / active_users_total{time_period="last_day"}

# Feature adoption rate (photo analysis)
rate(food_entries_created_total{entry_type="photo"}[1h]) / rate(food_entries_created_total[1h])
```

### Service Health

```promql
# Service availability (uptime)
up{job="health-agent-api"}

# Error budget (99.9% target)
1 - (sum(rate(http_requests_total{status=~"[45].."}[30d])) / sum(rate(http_requests_total[30d])))

# Database query errors
rate(db_queries_total{status="error"}[5m])
```

### Business Metrics

```promql
# Food entries per hour
sum(increase(food_entries_created_total[1h]))

# Photo analysis confidence quality
sum(rate(food_photos_analyzed_total{confidence_level="high"}[1h])) / sum(rate(food_photos_analyzed_total[1h]))

# User growth rate
rate(user_registrations_total[1d])

# XP economy health
sum(rate(gamification_xp_awarded_total[1h])) by (activity_type)
```

### Alerting Queries

```promql
# High error rate (>1%)
sum(rate(errors_total[5m])) / sum(rate(http_requests_total[5m])) > 0.01

# Slow response time (p95 > 2s)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2

# Database pool exhaustion
db_pool_size{state="available"} < 2

# External API failures
rate(external_api_calls_total{status="error"}[5m]) > 0.1

# Low photo confidence rate (>20% low confidence)
sum(rate(food_photos_analyzed_total{confidence_level="low"}[5m])) / sum(rate(food_photos_analyzed_total[5m])) > 0.2
```

## Helper Functions

The metrics module provides helper functions for categorizing values:

### `get_confidence_level(confidence: float) -> str`

Categorizes confidence scores:
- `high`: confidence >= 0.8
- `medium`: 0.5 <= confidence < 0.8
- `low`: confidence < 0.5

### `get_complexity_level(token_count: int) -> str`

Categorizes query complexity:
- `simple`: token_count < 500
- `complex`: token_count >= 500

## Cardinality Considerations

To prevent metrics explosion, the following strategies are used:

1. **Path Normalization**: API paths with IDs are normalized (e.g., `/api/v1/users/123` → `/api/v1/users/:id`)
2. **Limited Label Values**: Labels have a bounded set of values
3. **No User IDs in Labels**: User-specific data is not used in metric labels
4. **Aggregation**: High-cardinality data is aggregated before creating metrics

## Retention

Metrics are retained according to Prometheus configuration:
- **Default**: 30 days
- **Configurable**: Adjust in `docker-compose.observability.yml`

For long-term storage, consider:
- Thanos
- Cortex
- Grafana Cloud
- AWS Timestream

## Next Steps

- Review [OBSERVABILITY.md](./OBSERVABILITY.md) for setup instructions
- Explore metrics in Prometheus UI: http://localhost:9090
- View pre-built dashboards in Grafana: http://localhost:3000
- Set up alerting rules based on critical metrics
- Create custom dashboards for your use cases
