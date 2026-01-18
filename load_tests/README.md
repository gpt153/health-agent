# Load Testing Infrastructure

Comprehensive load testing suite for the Health Agent API using Locust.

## Overview

This directory contains all load testing infrastructure:
- **Locust configuration** (`locustfile.py`)
- **Test scenarios** (`scenarios/`)
- **Test runner script** (`run_load_tests.sh`)
- **Performance monitoring** (`monitor.py`)

## Quick Start

### 1. Install Dependencies

```bash
# From project root
pip install -r requirements.txt
```

### 2. Start the API

```bash
# Start all services
docker-compose up -d

# Verify API is running
curl http://localhost:8000/health
```

### 3. Run Load Tests

```bash
# Run all scenarios
./load_tests/run_load_tests.sh

# Run specific scenario
./load_tests/run_load_tests.sh steady
./load_tests/run_load_tests.sh spike
./load_tests/run_load_tests.sh endurance
```

### 4. View Results

Reports are generated in `load_tests/results/`:
- `*_report.html` - Interactive HTML report
- `*_stats.csv` - Request statistics
- `*.log` - Console output

## Test Scenarios

### 1. Steady Load (`steady_load.py`)

**Purpose**: Simulate normal production load

**Configuration**:
- Users: 100 concurrent
- Spawn rate: 10 users/sec
- Duration: 10 minutes

**Success Criteria**:
- P95 latency < 3 seconds
- Error rate < 1%

**Usage**:
```bash
./load_tests/run_load_tests.sh steady
```

---

### 2. Spike Test (`spike_test.py`)

**Purpose**: Test system resilience under sudden traffic spike

**Configuration**:
- Users: 0 → 200 (instant spike)
- Spawn rate: 200 users/sec
- Duration: 5 minutes

**Success Criteria**:
- P95 latency < 5 seconds (more lenient)
- Error rate < 5% (allow some failures during spike)

**Usage**:
```bash
./load_tests/run_load_tests.sh spike
```

---

### 3. Endurance Test (`endurance_test.py`)

**Purpose**: Test system stability over extended period (detect memory leaks, connection pool exhaustion)

**Configuration**:
- Users: 50 concurrent
- Spawn rate: 5 users/sec
- Duration: 60 minutes

**Success Criteria**:
- P95 latency < 3 seconds
- Error rate < 1%
- No performance degradation over time

**Usage**:
```bash
./load_tests/run_load_tests.sh endurance
```

## Performance Monitoring

Real-time monitoring during load tests:

```bash
# Start monitoring (in separate terminal)
python load_tests/monitor.py --host http://localhost:8000 --interval 5

# Save metrics to CSV
python load_tests/monitor.py --output load_tests/results/monitoring.csv

# Monitor for specific duration
python load_tests/monitor.py --duration 600  # 10 minutes
```

**Monitored Metrics**:
- CPU usage (%)
- Memory usage (MB, %)
- API latency (ms)
- Database connection pool (active/total)
- Redis cache hit rate (%)
- API error rate

**Output Example**:
```
Time       | CPU%   | Mem%   | Mem(MB)  | API(ms) | DB Pool  | Redis Hit% | Status
---------------------------------------------------------------------------------
14:23:05   |  45.2% |  62.3% |     1024 |      85 | 5/13     | 72.5%      | ✅ 200
14:23:10   |  48.7% |  63.1% |     1037 |      92 | 6/13     | 74.2%      | ✅ 200
```

## User Simulation

The `locustfile.py` simulates realistic user behavior:

**Task Distribution**:
- Text messages (50%): Common user queries
- Food logging (20%): Log food entries
- Reminders (20%): Check active reminders
- Gamification (10%): Check XP and achievements

**Behavior**:
- Wait 5-15 seconds between requests (human-like)
- Each user makes 50 requests max (10-minute session)
- Unique user IDs for each virtual user

## Configuration

### Environment Variables

```bash
# API host (default: http://localhost:8000)
export LOAD_TEST_HOST=http://localhost:8000

# Skip health check (useful for debugging)
export SKIP_HEALTH_CHECK=true
```

### Customizing Scenarios

Edit scenario files in `scenarios/`:

```python
# scenarios/steady_load.py

USERS = 100           # Number of concurrent users
SPAWN_RATE = 10       # Users spawned per second
RUN_TIME = "10m"      # Duration (e.g., "10m", "1h")

MAX_P95_MS = 3000     # P95 latency threshold (ms)
MAX_FAILURE_RATE = 1.0  # Error rate threshold (%)
```

## Results Analysis

### Success Criteria

Load tests automatically check success criteria:

```
🎯 SUCCESS CRITERIA:
  P95 < 3s: ✅ PASS (2.34s)
  Errors < 1%: ✅ PASS (0.12%)
```

### HTML Reports

Interactive reports include:
- Response time charts
- Request distribution
- Failure analysis
- Percentile breakdowns (P50, P90, P95, P99)

Open in browser:
```bash
open load_tests/results/steady_load_report.html
```

### CSV Statistics

Raw statistics for analysis:

```bash
# View aggregate statistics
cat load_tests/results/steady_load_stats.csv | column -t -s,

# Extract P95 latency
awk -F',' 'NR==2 {print "P95:", $17, "ms"}' load_tests/results/steady_load_stats.csv
```

## Troubleshooting

### API Not Responding

```bash
# Check if API is running
docker-compose ps

# Check API logs
docker-compose logs health-agent-api

# Restart API
docker-compose restart health-agent-api
```

### Locust Command Not Found

```bash
# Install Locust
pip install locust

# Verify installation
locust --version
```

### Connection Refused Errors

```bash
# Check API is listening on correct port
curl http://localhost:8000/health

# If using different host, set environment variable
export LOAD_TEST_HOST=http://your-api-host:8000
```

### High Error Rates

If error rate > 1%, check:
1. **Database connection pool**: May be exhausted
   - Increase pool size in `src/db/connection.py`
   - Monitor pool stats during test
2. **Redis cache**: May be unavailable
   - Check Redis logs: `docker-compose logs redis`
   - Verify cache is enabled: `ENABLE_CACHE=true`
3. **API rate limiting**: May be hitting rate limits
   - Adjust Locust spawn rate
   - Increase API capacity

## Advanced Usage

### Custom Load Pattern

Run Locust with custom parameters:

```bash
locust \
  -f load_tests/locustfile.py \
  --host http://localhost:8000 \
  --users 150 \
  --spawn-rate 15 \
  --run-time 15m \
  --headless \
  --html load_tests/results/custom_report.html
```

### Interactive Web UI

```bash
# Start Locust web UI
locust -f load_tests/locustfile.py --host http://localhost:8000

# Open browser to http://localhost:8089
# Configure users and spawn rate in UI
```

### Distributed Load Testing

Run Locust across multiple machines:

```bash
# Master node
locust -f load_tests/locustfile.py --master --host http://localhost:8000

# Worker nodes (run on separate machines)
locust -f load_tests/locustfile.py --worker --master-host=<master-ip>
```

## Performance Targets

From Issue #82 requirements:

| Metric | Target | Current (Expected) |
|--------|--------|-------------------|
| **Concurrent Users** | 100 | ✅ Supported |
| **P95 Latency** | < 3s | 2-3s (optimized) |
| **Error Rate** | < 1% | < 0.5% |
| **Throughput** | 50 msg/10min/user | ✅ Supported |

## Next Steps

After running load tests:

1. **Analyze Results**: Review HTML reports and CSV statistics
2. **Identify Bottlenecks**: Check monitoring data for resource constraints
3. **Optimize**: Based on findings (database, cache, API)
4. **Re-test**: Validate improvements with new load test run
5. **Document**: Update performance benchmarks in `docs/performance/`

## Files Overview

```
load_tests/
├── locustfile.py              # Main Locust configuration
├── scenarios/                 # Test scenario definitions
│   ├── __init__.py
│   ├── steady_load.py         # Normal production load
│   ├── spike_test.py          # Sudden traffic spike
│   └── endurance_test.py      # Extended duration test
├── run_load_tests.sh          # Test runner script
├── monitor.py                 # Real-time monitoring utility
├── results/                   # Test results (generated)
│   ├── *_report.html          # Interactive HTML reports
│   ├── *_stats.csv            # Request statistics
│   └── *.log                  # Console output
└── README.md                  # This file
```

## References

- [Locust Documentation](https://docs.locust.io/)
- [Performance Optimization Plan](/docs/performance/IMPLEMENTATION_PLAN.md)
- [Issue #82](https://github.com/your-repo/health-agent/issues/82)
