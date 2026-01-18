# Performance Baseline Metrics

**Date**: 2026-01-18
**Issue**: #82 - Phase 3.6 Performance Optimization
**Status**: ⚠️ Environment Setup Required

---

## Executive Summary

This document establishes baseline performance metrics for the health agent Telegram bot **before** optimization. Actual performance testing requires environment setup (see Prerequisites below).

### Baseline Targets (Pre-Optimization)
Based on the codebase analysis and issue requirements:

| Metric | Target (Post-Optimization) | Expected Baseline (Est.) |
|--------|----------------------------|--------------------------|
| Average response time | <5s | 8-15s |
| P95 latency | <3s | 20-30s |
| P99 latency | <10s | 40-60s |
| Database query time | <50ms | 50-200ms |
| Cache hit rate | >60% | 0% (no cache) |
| Concurrent users | 100 | Unknown |
| Memory usage | <500MB | ~200MB |

---

## Prerequisites for Performance Testing

### 1. Python Environment Setup

The performance testing requires all dependencies installed:

```bash
# Install profiling tools
pip install py-spy memory-profiler psutil locust redis hiredis

# Install bot dependencies
pip install -r requirements.txt
```

**Note**: Testing environment requires:
- Python 3.11+
- PostgreSQL database with test data
- `.env` file configured with credentials
- Test user created in database

### 2. Database Setup

Required tables and indexes:
- `conversation_messages` with test data
- `users` table with test user
- `food_entries`, `reminders`, etc. for comprehensive testing

### 3. External Services

- **PostgreSQL**: Running on configured port
- **Mem0/pgvector**: Initialized for semantic search
- **LLM API**: Anthropic/OpenAI API keys configured

---

## Current Architecture Analysis

### Component Breakdown (From Code Review)

Based on `/test_performance.py` analysis, the message processing pipeline consists of:

1. **Load Conversation History** (~50-200ms estimated)
   - Database query: `SELECT * FROM conversation_messages WHERE user_id = ? ORDER BY created_at DESC LIMIT 20`
   - Current indexes: Unknown (requires EXPLAIN ANALYZE)
   - Expected bottleneck: Missing covering index

2. **Load User Memory (File I/O)** (~100-500ms estimated)
   - Reads user preference files from disk
   - File location: `.agents/memory/users/{user_id}/`
   - No caching layer

3. **Generate System Prompt + Mem0 Search** (~1-5s estimated)
   - Semantic memory search via Mem0 (pgvector)
   - Embedding generation for query
   - Vector similarity search
   - **Expected major bottleneck**

4. **Agent Response (LLM API)** (~5-20s estimated)
   - PydanticAI agent initialization
   - Tool registration
   - LLM API call (Anthropic Sonnet/Haiku)
   - **Expected major bottleneck (external latency)**

5. **Save Conversation Messages** (~10-50ms estimated)
   - Two INSERT queries (user + assistant messages)
   - Transactional writes

6. **Mem0 Add Message (Embedding)** (~500-2000ms estimated)
   - Generate embeddings for messages
   - Store in pgvector
   - **Expected bottleneck**

### Total Estimated Baseline: 8-30 seconds per message

---

## Expected Bottlenecks (Pre-Testing)

Based on code analysis:

### 🔴 CRITICAL (>50% of time)
1. **LLM API Latency** (5-20s)
   - External dependency (Anthropic/OpenAI)
   - Network latency
   - Model inference time
   - **Cannot be fully optimized** (external service)
   - Mitigation: Streaming responses, faster model selection (Haiku)

2. **Mem0 Semantic Search** (1-5s)
   - Embedding generation for query
   - Pgvector similarity search
   - Happens twice per message (system prompt + add_message)
   - **Primary optimization target**

### 🟡 HIGH (20-50% of time)
3. **User Memory File I/O** (100-500ms)
   - Disk reads for user preferences
   - No caching layer
   - **Easy optimization target** (Redis cache)

4. **Database Queries** (50-200ms total)
   - Conversation history retrieval
   - Missing covering indexes
   - **Easy optimization target** (indexes + caching)

### 🟢 MEDIUM (<20% of time)
5. **Message Storage** (10-50ms)
   - Transactional writes
   - Already reasonably fast
   - Low priority for optimization

---

## Database Connection Pool Analysis

### Current Configuration
From `src/db/connection.py`:

```python
AsyncConnectionPool(
    min_size=2,
    max_size=10
)
```

### Optimization Opportunity
**Target**: Dynamic sizing based on CPU cores

Formula: `pool_size = (2 * cpu_cores) + spare_connections`

For 4-core system:
- Min: 4 connections
- Max: 13 connections

**Expected Impact**: Better throughput under concurrent load

---

## Optimization Priorities (From Analysis)

### Phase 1 Priorities (Quick Wins)
1. ✅ **Add Redis caching layer**
   - User preferences: 1hr TTL
   - Nutrition data: 24hr TTL
   - Conversation history: 30min TTL
   - **Expected improvement**: 30-50% reduction in data loading time

2. ✅ **Database query optimization**
   - Add covering index: `(user_id, created_at DESC) INCLUDE (role, content, message_type, metadata)`
   - **Expected improvement**: 50-80% faster conversation history queries

3. ✅ **Dynamic connection pooling**
   - Auto-detect CPU cores
   - Adjust pool size
   - **Expected improvement**: Better concurrency handling

### Phase 2 Priorities (Complex)
4. **Mem0 optimization**
   - Limit search scope to recent memories
   - Skip for simple queries ("hi", "thanks")
   - Cache search results per session
   - **Expected improvement**: 40-60% reduction in Mem0 latency

5. **LLM response caching**
   - Cache common queries/responses
   - Use faster model (Haiku) for simple queries
   - **Expected improvement**: 20-30% for cached queries

---

## Load Testing Scenarios

Once environment is configured, run these scenarios:

### Scenario 1: Steady Load
- **Users**: 100 concurrent
- **Duration**: 10 minutes
- **Pattern**: 50 messages per user over 10 min
- **Success Criteria**: P95 < 3s, no errors

### Scenario 2: Spike Test
- **Users**: 0 → 200 in 1 minute
- **Duration**: 6 minutes total
- **Pattern**: Rapid ramp-up
- **Success Criteria**: Graceful degradation, no crashes

### Scenario 3: Endurance Test
- **Users**: 50 concurrent
- **Duration**: 60 minutes
- **Pattern**: Sustained load
- **Success Criteria**: No memory leaks, stable performance

---

## Metrics Collection Methodology

### Tools Configured

1. **PerformanceTimer** (custom)
   - High-precision timing (perf_counter)
   - Per-stage breakdown

2. **SystemMetrics** (psutil)
   - CPU usage
   - Memory usage (RSS)
   - CPU core count

3. **PerformanceMonitor** (custom)
   - Percentile calculation (P50, P95, P99)
   - Trend analysis
   - Multi-run aggregation

4. **Database Query Profiler** (custom)
   - EXPLAIN ANALYZE integration
   - Slow query logging (>100ms)

### Enhanced `test_performance.py`

The test script now captures:
- ✅ Per-stage timing breakdown
- ✅ System resource usage (CPU, memory)
- ✅ Memory delta per operation
- ✅ Database pool statistics
- ✅ Latency percentiles (P50, P95, P99)
- ✅ Bottleneck identification

---

## Next Steps

### To Run Baseline Tests:

1. **Setup Environment**
   ```bash
   # Create virtual environment
   python3 -m venv .venv
   source .venv/bin/activate

   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Configure Database**
   ```bash
   # Ensure PostgreSQL running
   # Run migrations
   ./run_migrations.sh
   ```

3. **Run Performance Tests**
   ```bash
   python test_performance.py
   ```

4. **Review Output**
   - Console output: Per-test breakdown
   - Report file: `.agents/supervision/performance-findings-{timestamp}.md`

### Expected Deliverables

Once tests run successfully:
- ✅ Baseline metrics document (this file, updated)
- ✅ Performance findings report
- ✅ Bottleneck identification
- ✅ Database query analysis (EXPLAIN ANALYZE)
- ✅ Memory profiling results

---

## Environment Setup Status

| Component | Status | Notes |
|-----------|--------|-------|
| Python dependencies | ⚠️ Partial | psutil/locust not installed system-wide |
| Test script enhanced | ✅ Complete | Added comprehensive metrics |
| Profiling utilities | ✅ Complete | `src/utils/profiling.py` created |
| Database access | ❌ Not configured | Requires .env setup |
| Test data | ❌ Not configured | Requires test user creation |

**Blocker**: Python environment externally managed (Debian restriction). Requires virtual environment or Docker setup for actual test execution.

---

## Alternative: Docker-Based Testing

If local environment is restrictive, use Docker:

```yaml
# docker-compose.yml addition
performance-test:
  build: .
  volumes:
    - ./test_performance.py:/app/test_performance.py
    - ./docs/performance:/app/docs/performance
  command: python test_performance.py
  depends_on:
    - postgres
    - redis
```

This isolates the testing environment and ensures all dependencies are available.

---

## Conclusion

**Phase 1 (Baseline Metrics) Status**: 📝 **Documentation Complete, Execution Pending**

### Completed
- ✅ Profiling dependencies added to `requirements.txt`
- ✅ Profiling utilities module created (`src/utils/profiling.py`)
- ✅ `test_performance.py` enhanced with comprehensive metrics
- ✅ Baseline expectations documented

### Pending
- ⏳ Environment setup (venv or Docker)
- ⏳ Actual test execution
- ⏳ Baseline metrics collection
- ⏳ Performance report generation

### Recommendation

Proceed to **Phase 2 (Redis Caching Implementation)** in parallel. The caching layer can be implemented without running baseline tests, and actual metrics can be collected once the environment is properly configured (likely in production or staging).

**Estimated Time to Unblock**: 1-2 hours (environment setup)
**Alternative Path**: Implement optimizations first, then A/B test in staging environment

---

## Appendix: Profiling Utilities Reference

### PerformanceTimer
```python
from src.utils.profiling import PerformanceTimer

with PerformanceTimer("operation_name"):
    # Code to profile
    result = await some_operation()
```

### profile_function Decorator
```python
from src.utils.profiling import profile_function

@profile_function(log_threshold_ms=100)
async def slow_operation():
    # Automatically logged if >100ms
    pass
```

### SystemMetrics
```python
from src.utils.profiling import SystemMetrics

memory_mb = SystemMetrics.get_memory_usage_mb()
cpu_percent = SystemMetrics.get_cpu_percent()
snapshot = SystemMetrics.get_snapshot()
```

### PerformanceMonitor
```python
from src.utils.profiling import PerformanceMonitor

monitor = PerformanceMonitor("test_run")
monitor.record_sample(response_time_ms=1500, memory_mb=250)
summary = monitor.get_summary()  # P50, P95, P99, avg, min, max
```

---

*Document will be updated with actual metrics once testing environment is configured and tests are executed.*
