# Performance Monitoring Guide

Comprehensive guide to monitoring the Health Agent API performance in production and during load testing.

## Overview

The Health Agent API includes built-in performance monitoring capabilities:
- **Metrics API endpoint** (`/api/v1/metrics`) for real-time stats
- **Performance middleware** for automatic request tracking
- **Slow request logging** for identifying bottlenecks
- **Integration with profiling utilities** from Phase 1

---

## Metrics Endpoint

### `/api/v1/metrics`

**Purpose**: Real-time performance metrics for monitoring tools and load testing.

**Authentication**: None required (consider adding for production)

**Response Format**:
```json
{
  "timestamp": "2026-01-18T14:23:45.123456",
  "system": {
    "cpu_percent": 45.2,
    "memory_mb": 1024.5,
    "memory_percent": 62.3,
    "memory_available_mb": 625.7,
    "disk_read_mb": 123.4,
    "disk_write_mb": 45.6
  },
  "database": {
    "pool_size": 13,
    "pool_available": 8,
    "pool_active": 5,
    "pool_min_size": 4,
    "pool_max_size": 13,
    "pool_utilization_percent": 38.46
  },
  "cache": {
    "enabled": true,
    "hits": 1234,
    "misses": 456,
    "sets": 789,
    "deletes": 12,
    "errors": 0,
    "total_reads": 1690,
    "hit_rate_percent": 73.02
  }
}
```

### Usage Examples

#### cURL
```bash
# Get current metrics
curl http://localhost:8000/api/v1/metrics

# Pretty print with jq
curl -s http://localhost:8000/api/v1/metrics | jq '.'

# Extract specific metric
curl -s http://localhost:8000/api/v1/metrics | jq '.database.pool_active'
```

#### Python
```python
import httpx
import asyncio

async def monitor_metrics():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/api/v1/metrics")
        metrics = response.json()

        print(f"CPU: {metrics['system']['cpu_percent']}%")
        print(f"Memory: {metrics['system']['memory_mb']:.0f} MB")
        print(f"DB Pool: {metrics['database']['pool_active']}/{metrics['database']['pool_size']}")
        print(f"Cache Hit Rate: {metrics['cache']['hit_rate_percent']:.1f}%")

asyncio.run(monitor_metrics())
```

#### Load Test Monitoring
```bash
# Use the monitoring script from Phase 4
python load_tests/monitor.py \
  --host http://localhost:8000 \
  --interval 5 \
  --output metrics.csv
```

---

## Performance Middleware

### Automatic Request Tracking

The `PerformanceMonitoringMiddleware` automatically tracks all API requests:

**Features**:
- ✅ **Request timing**: Measures duration of every request
- ✅ **Slow request logging**: Logs requests > 3 seconds (configurable)
- ✅ **Response headers**: Adds `X-Response-Time` and `X-Request-ID` headers
- ✅ **Debug logging**: Detailed request logs at debug level

### Response Headers

Every API response includes performance headers:

```bash
$ curl -I http://localhost:8000/api/v1/chat

HTTP/1.1 200 OK
X-Response-Time: 234.56ms
X-Request-ID: 12345
```

**Headers**:
- `X-Response-Time`: Request duration in milliseconds
- `X-Request-ID`: Sequential request counter (useful for correlation)

### Slow Request Logging

Requests exceeding the threshold (default: 3000ms) are automatically logged:

```
2026-01-18 14:23:45 - WARNING - SLOW REQUEST: POST /api/v1/chat took 3456ms (threshold: 3000ms)
```

**Configuration**:
Edit `src/api/middleware.py` to adjust the threshold:
```python
slow_request_threshold_ms = 5000  # Change to 5 seconds
```

---

## Monitored Metrics

### System Metrics

| Metric | Description | Source |
|--------|-------------|--------|
| `cpu_percent` | CPU usage (%) | psutil |
| `memory_mb` | Memory used (MB) | psutil |
| `memory_percent` | Memory usage (%) | psutil |
| `memory_available_mb` | Available memory (MB) | psutil |
| `disk_read_mb` | Cumulative disk reads (MB) | psutil |
| `disk_write_mb` | Cumulative disk writes (MB) | psutil |

**Notes**:
- CPU measurement uses 0.1s interval for accuracy
- Disk I/O values are cumulative (since system boot)
- Calculate disk I/O rate by comparing consecutive readings

### Database Metrics

| Metric | Description | Phase |
|--------|-------------|-------|
| `pool_size` | Current pool size | Phase 3 |
| `pool_available` | Available connections | Phase 3 |
| `pool_active` | Active connections | Phase 3 |
| `pool_min_size` | Minimum pool size (config) | Phase 3 |
| `pool_max_size` | Maximum pool size (config) | Phase 3 |
| `pool_utilization_percent` | Active / Size * 100 | Phase 5 |

**Pool Utilization Interpretation**:
- `< 50%`: Pool is underutilized (consider reducing size)
- `50-80%`: Healthy utilization
- `> 80%`: Pool is under pressure (consider increasing size)
- `100%`: Pool exhausted (requests may timeout)

**Dynamic Pool Sizing** (from Phase 3):
- Formula: `max_size = (2 * cpu_cores) + 5`
- Example (4-core): min=4, max=13

### Cache Metrics

| Metric | Description | Phase |
|--------|-------------|-------|
| `enabled` | Cache enabled status | Phase 2 |
| `hits` | Successful cache lookups | Phase 2 |
| `misses` | Failed cache lookups | Phase 2 |
| `sets` | Cache write operations | Phase 2 |
| `deletes` | Cache delete operations | Phase 2 |
| `errors` | Cache errors | Phase 2 |
| `total_reads` | hits + misses | Phase 5 |
| `hit_rate_percent` | hits / total_reads * 100 | Phase 5 |

**Hit Rate Interpretation**:
- `< 30%`: Cache is not effective (check TTLs, access patterns)
- `30-60%`: Moderate benefit (room for improvement)
- `60-80%`: Good cache performance
- `> 80%`: Excellent cache performance

**Expected Cache Performance** (from Phase 2):
- Cold start: 10-20%
- After 5 minutes: 50-60%
- Steady state: 70-80%

---

## Monitoring Integrations

### Prometheus

Export metrics to Prometheus for long-term storage and alerting:

```python
# Install prometheus_client
# pip install prometheus-client

from prometheus_client import Gauge, Counter, Histogram, generate_latest
import httpx

# Define metrics
cpu_usage = Gauge('health_agent_cpu_percent', 'CPU usage percentage')
memory_usage = Gauge('health_agent_memory_mb', 'Memory usage in MB')
db_pool_active = Gauge('health_agent_db_pool_active', 'Active DB connections')
cache_hit_rate = Gauge('health_agent_cache_hit_rate_percent', 'Cache hit rate')

# Scrape metrics endpoint
async def collect_metrics():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/api/v1/metrics")
        data = response.json()

        cpu_usage.set(data['system']['cpu_percent'])
        memory_usage.set(data['system']['memory_mb'])
        db_pool_active.set(data['database']['pool_active'])
        cache_hit_rate.set(data['cache']['hit_rate_percent'])

# Expose Prometheus endpoint
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

app = FastAPI()

@app.get("/metrics")
async def metrics():
    await collect_metrics()
    return PlainTextResponse(generate_latest())
```

**Prometheus scrape config** (`prometheus.yml`):
```yaml
scrape_configs:
  - job_name: 'health-agent-api'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
```

### Grafana

Create dashboards to visualize metrics:

**Dashboard Panels**:
1. **System Health**:
   - CPU usage (line chart)
   - Memory usage (line chart)
   - Disk I/O rate (line chart)

2. **Database**:
   - Pool utilization (gauge)
   - Active connections (line chart)
   - Pool size (stat)

3. **Cache**:
   - Hit rate (gauge)
   - Hits vs misses (time series)
   - Cache operations (bar chart)

4. **API Performance**:
   - Request rate (graph)
   - Response time distribution (heatmap)
   - Error rate (stat)

**Example Grafana Query** (Prometheus datasource):
```promql
# CPU usage over time
health_agent_cpu_percent

# Database pool utilization rate
health_agent_db_pool_active / health_agent_db_pool_size * 100

# Cache hit rate
health_agent_cache_hit_rate_percent
```

### CloudWatch (AWS)

Send metrics to CloudWatch for AWS-hosted deployments:

```python
import boto3
from datetime import datetime

cloudwatch = boto3.client('cloudwatch')

async def send_metrics_to_cloudwatch():
    response = await httpx.get("http://localhost:8000/api/v1/metrics")
    data = response.json()

    cloudwatch.put_metric_data(
        Namespace='HealthAgent',
        MetricData=[
            {
                'MetricName': 'CPUUtilization',
                'Value': data['system']['cpu_percent'],
                'Unit': 'Percent',
                'Timestamp': datetime.now()
            },
            {
                'MetricName': 'MemoryUsage',
                'Value': data['system']['memory_mb'],
                'Unit': 'Megabytes',
                'Timestamp': datetime.now()
            },
            {
                'MetricName': 'DatabasePoolUtilization',
                'Value': data['database']['pool_utilization_percent'],
                'Unit': 'Percent',
                'Timestamp': datetime.now()
            },
            {
                'MetricName': 'CacheHitRate',
                'Value': data['cache']['hit_rate_percent'],
                'Unit': 'Percent',
                'Timestamp': datetime.now()
            }
        ]
    )
```

---

## Alerting

### Alert Rules

Recommended alert thresholds:

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| High CPU | `cpu_percent > 80%` for 5 min | Warning | Investigate load |
| Critical CPU | `cpu_percent > 95%` for 2 min | Critical | Scale up |
| High Memory | `memory_percent > 85%` for 5 min | Warning | Check for leaks |
| Critical Memory | `memory_percent > 95%` | Critical | Restart service |
| DB Pool Exhausted | `pool_utilization_percent >= 100%` | Critical | Increase pool size |
| DB Pool High | `pool_utilization_percent > 80%` for 5 min | Warning | Monitor closely |
| Low Cache Hit Rate | `hit_rate_percent < 30%` for 10 min | Warning | Check cache config |
| Cache Errors | `cache.errors > 0` | Warning | Check Redis connection |
| Slow Requests | Logged slow requests | Info | Investigate endpoint |

### Prometheus Alert Rules

**Example** (`alerts.yml`):
```yaml
groups:
  - name: health-agent
    interval: 30s
    rules:
      - alert: HighCPUUsage
        expr: health_agent_cpu_percent > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage detected"
          description: "CPU usage is {{ $value }}%"

      - alert: DatabasePoolExhausted
        expr: health_agent_db_pool_active / health_agent_db_pool_size >= 1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database pool exhausted"
          description: "All {{ $value }} connections are in use"

      - alert: LowCacheHitRate
        expr: health_agent_cache_hit_rate_percent < 30
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Cache hit rate is low"
          description: "Hit rate is only {{ $value }}%"
```

### Log-based Alerts

Monitor logs for slow requests:

```bash
# Find slow requests in logs
grep "SLOW REQUEST" /var/log/health-agent/api.log

# Count slow requests in last hour
grep "SLOW REQUEST" /var/log/health-agent/api.log | tail -n 1000 | wc -l

# Alert if > 10 slow requests in 5 minutes
count=$(grep "SLOW REQUEST" /var/log/health-agent/api.log | tail -n 100 | wc -l)
if [ $count -gt 10 ]; then
    echo "ALERT: $count slow requests detected" | mail -s "Health Agent Alert" ops@example.com
fi
```

---

## Monitoring During Load Tests

### Real-Time Monitoring

Use the monitoring script from Phase 4:

```bash
# Terminal 1: Start monitoring
python load_tests/monitor.py \
  --host http://localhost:8000 \
  --interval 5 \
  --output load_test_metrics_$(date +%Y%m%d_%H%M%S).csv

# Terminal 2: Run load test
./load_tests/run_load_tests.sh steady
```

**Output**:
```
Time       | CPU%   | Mem%   | Mem(MB)  | API(ms) | DB Pool  | Redis Hit% | Status
----------------------------------------------------------------------------------
14:23:05   |  45.2% |  62.3% |     1024 |      85 | 5/13     | 72.5%      | ✅ 200
14:23:10   |  48.7% |  63.1% |     1037 |      92 | 6/13     | 74.2%      | ✅ 200
14:23:15   |  51.3% |  64.0% |     1052 |      88 | 7/13     | 75.8%      | ✅ 200
```

### Post-Test Analysis

Analyze CSV metrics:

```python
import pandas as pd
import matplotlib.pyplot as plt

# Load metrics
df = pd.read_csv('load_test_metrics.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')

# Plot CPU usage over time
plt.figure(figsize=(12, 6))
plt.plot(df['timestamp'], df['cpu_percent'])
plt.xlabel('Time')
plt.ylabel('CPU %')
plt.title('CPU Usage During Load Test')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('cpu_usage.png')

# Plot database pool utilization
df['pool_utilization'] = (df['db_pool_active'] / df['db_pool_size']) * 100
plt.figure(figsize=(12, 6))
plt.plot(df['timestamp'], df['pool_utilization'])
plt.axhline(y=80, color='r', linestyle='--', label='Warning threshold')
plt.xlabel('Time')
plt.ylabel('Pool Utilization %')
plt.title('Database Pool Utilization')
plt.legend()
plt.tight_layout()
plt.savefig('db_pool_utilization.png')

# Calculate statistics
print("\n=== Load Test Metrics Summary ===")
print(f"Duration: {(df['timestamp'].max() - df['timestamp'].min()).total_seconds():.0f}s")
print(f"\nCPU Usage:")
print(f"  Average: {df['cpu_percent'].mean():.1f}%")
print(f"  Max: {df['cpu_percent'].max():.1f}%")
print(f"\nDatabase Pool:")
print(f"  Average active: {df['db_pool_active'].mean():.1f}")
print(f"  Peak active: {df['db_pool_active'].max()}")
print(f"  Average utilization: {df['pool_utilization'].mean():.1f}%")
print(f"\nCache Performance:")
print(f"  Average hit rate: {df['redis_hit_rate'].mean():.1f}%")
```

---

## Troubleshooting

### High CPU Usage

**Symptoms**:
- `cpu_percent > 80%` consistently
- Slow response times

**Diagnosis**:
```bash
# Check top CPU consumers
htop

# Profile Python code
py-spy record -o profile.svg --pid $(pgrep -f "uvicorn")

# Check for CPU-intensive queries
docker-compose logs health-agent-api | grep "SLOW REQUEST"
```

**Solutions**:
- Scale horizontally (add more API instances)
- Optimize CPU-intensive operations (LLM calls, image processing)
- Enable caching (if not already enabled)

### High Memory Usage

**Symptoms**:
- `memory_percent > 85%` consistently
- Out of memory errors

**Diagnosis**:
```bash
# Check memory usage by process
ps aux --sort=-%mem | head -n 10

# Profile memory
memory_profiler -o memory_profile.txt src/main.py

# Check for memory leaks
docker stats
```

**Solutions**:
- Increase server memory
- Check for memory leaks in agent code
- Reduce conversation history limit
- Clear old cache entries

### Database Pool Exhaustion

**Symptoms**:
- `pool_utilization_percent >= 100%`
- "Connection pool exhausted" errors
- Requests timing out

**Diagnosis**:
```bash
# Check active connections
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"

# Check pool stats
curl -s http://localhost:8000/api/v1/metrics | jq '.database'

# Check for long-running queries
psql $DATABASE_URL -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query FROM pg_stat_activity WHERE state = 'active';"
```

**Solutions**:
- Increase pool size in `src/db/connection.py`
- Optimize slow queries (add indexes)
- Check for connection leaks (unclosed connections)
- Scale database server

### Low Cache Hit Rate

**Symptoms**:
- `hit_rate_percent < 30%` after warmup
- Slow response times despite caching

**Diagnosis**:
```bash
# Check cache stats
curl -s http://localhost:8000/api/v1/metrics | jq '.cache'

# Check Redis memory usage
redis-cli INFO memory

# Check cache keys
redis-cli KEYS "*" | head -n 20
```

**Solutions**:
- Increase TTLs (if data doesn't change frequently)
- Warm up cache before load tests
- Check cache key patterns (ensure they're being reused)
- Increase Redis memory (if eviction is happening)

---

## Best Practices

### Monitoring in Production

1. **Continuous Monitoring**: Poll `/api/v1/metrics` every 15-30 seconds
2. **Alert on Trends**: Alert on sustained high usage, not spikes
3. **Log Slow Requests**: Review slow request logs weekly
4. **Dashboard**: Create Grafana dashboard for at-a-glance health
5. **Capacity Planning**: Monitor trends to predict scaling needs

### Monitoring During Development

1. **Profile Changes**: Run profiler before/after optimizations
2. **Load Test**: Run load tests after significant changes
3. **Monitor Tests**: Watch metrics during test runs
4. **Compare Baselines**: Compare metrics against Phase 1 baseline

### Security Considerations

1. **Protect Metrics Endpoint**: Add authentication in production
2. **Rate Limit**: Prevent metrics endpoint abuse
3. **Sanitize Logs**: Don't log sensitive data in slow requests
4. **Access Control**: Restrict monitoring dashboard access

---

## Performance Targets

From Issue #82 and baseline analysis:

| Metric | Baseline | Target | Current |
|--------|----------|--------|---------|
| **API Response Time (P95)** | 15-45s | < 3s | 2-3s |
| **Database Pool Utilization** | N/A | < 80% | ~40% (100 users) |
| **Cache Hit Rate** | 0% | > 70% | 70-80% (steady state) |
| **CPU Usage** | N/A | < 70% | ~50% (100 users) |
| **Memory Usage** | N/A | < 80% | ~60% (100 users) |

---

## References

- **Phase 1**: [Baseline Metrics](./baseline_metrics.md)
- **Phase 2**: [Redis Caching](./PHASE2_COMPLETION.md)
- **Phase 3**: [Database Optimization](./PHASE3_COMPLETION.md)
- **Phase 4**: [Load Testing](../load_tests/README.md)
- **Profiling Utilities**: [src/utils/profiling.py](../../src/utils/profiling.py)

---

## Quick Reference

### Metrics Endpoint
```bash
curl http://localhost:8000/api/v1/metrics | jq '.'
```

### Monitor During Load Test
```bash
python load_tests/monitor.py --interval 5 --output metrics.csv
```

### Check Slow Requests
```bash
grep "SLOW REQUEST" /var/log/health-agent/api.log
```

### Prometheus Scrape Target
```
http://localhost:8000/api/v1/metrics
```

### Alert Thresholds
- CPU > 80% for 5min
- Memory > 85% for 5min
- DB Pool >= 100%
- Cache hit rate < 30% for 10min
