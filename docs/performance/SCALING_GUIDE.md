# Scaling Guide - Health Agent API

**Last Updated**: 2026-01-18
**Target Audience**: DevOps, SREs, System Architects
**Prerequisites**: Performance optimizations from Phases 1-5 implemented

---

## Table of Contents

1. [Current Capacity](#current-capacity)
2. [Scaling Thresholds](#scaling-thresholds)
3. [Horizontal Scaling](#horizontal-scaling)
4. [Database Scaling](#database-scaling)
5. [Cache Scaling](#cache-scaling)
6. [Load Balancing](#load-balancing)
7. [Cost Analysis](#cost-analysis)
8. [Scaling Checklist](#scaling-checklist)

---

## Current Capacity

### Single-Instance Performance

**Hardware Configuration** (baseline):
- CPU: 4 cores
- Memory: 2GB
- Disk: SSD (50GB)
- Network: 1 Gbps

**Performance Metrics** (post-optimization):
- **Concurrent users**: 100+
- **P95 latency**: 2-3s
- **Throughput**: ~500-600 requests/minute
- **CPU usage**: 50-60% at full load
- **Memory usage**: ~250MB
- **Database pool**: 13 connections (40-60% utilization)

**Bottlenecks** (single instance):
- LLM API latency (external, 5-20s)
- Database connection pool (max 13 connections)
- Redis cache (256MB, single-threaded)

### Capacity Limits

| Resource | Limit | Symptoms of Exhaustion |
|----------|-------|------------------------|
| **CPU** | 85% sustained | Slow responses, request queuing |
| **Memory** | 1.5GB | OOM kills, swap thrashing |
| **DB Pool** | 13 connections | "Pool exhausted" errors |
| **Redis** | 256MB | Cache evictions, low hit rate |
| **Network** | 100 Mbps | Timeout errors, slow downloads |

**Scale Trigger**: When any resource hits **80% utilization** for **10+ minutes**.

---

## Scaling Thresholds

### Monitoring-Based Triggers

Use `/api/v1/metrics` endpoint and Prometheus alerts to trigger scaling:

#### Scale Up Triggers (Add Capacity)

| Metric | Threshold | Action | Urgency |
|--------|-----------|--------|---------|
| CPU > 80% | 10 min sustained | Scale horizontally | High |
| Memory > 85% | 5 min sustained | Scale vertically | Critical |
| DB Pool > 80% | 5 min sustained | Increase pool or scale DB | High |
| Cache Hit Rate < 30% | 20 min sustained | Increase Redis memory | Medium |
| API Errors > 5% | 5 min | Investigate, then scale | Critical |
| P95 Latency > 5s | 10 min | Scale horizontally | High |

#### Scale Down Triggers (Reduce Cost)

| Metric | Threshold | Action | Savings |
|--------|-----------|--------|---------|
| CPU < 30% | 30 min sustained | Scale down instances | 50% cost |
| Memory < 50% | 60 min sustained | Reduce instance size | 30% cost |
| DB Pool < 30% | 60 min sustained | Reduce pool size | 20% DB cost |

### User-Based Triggers

| Concurrent Users | Recommended Configuration | Notes |
|------------------|---------------------------|-------|
| **0-100** | 1 instance (4-core, 2GB) | Single instance sufficient |
| **100-300** | 2-3 instances (4-core, 2GB each) | Horizontal scaling begins |
| **300-500** | 3-5 instances (4-core, 2GB each) | Load balancer required |
| **500-1000** | 5-10 instances (4-core, 2GB each) | Database scaling needed |
| **1000+** | 10+ instances + DB replicas | Full distributed setup |

---

## Horizontal Scaling

### Architecture Overview

```
                          ┌─────────────┐
                          │   Clients   │
                          └──────┬──────┘
                                 │
                          ┌──────▼──────┐
                          │     Load    │
                          │   Balancer  │
                          │  (nginx)    │
                          └──────┬──────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
   ┌────▼────┐             ┌────▼────┐             ┌────▼────┐
   │ API     │             │ API     │             │ API     │
   │ Instance│             │ Instance│             │ Instance│
   │ 1       │             │ 2       │             │ N       │
   └────┬────┘             └────┬────┘             └────┬────┘
        │                        │                        │
        └────────────────────────┼────────────────────────┘
                                 │
                   ┌─────────────┴─────────────┐
                   │                           │
              ┌────▼────┐                 ┌───▼────┐
              │ Redis   │                 │ Postgres│
              │ Cache   │                 │   DB    │
              │(Shared) │                 │(Shared) │
              └─────────┘                 └─────────┘
```

### Implementation Steps

#### 1. Containerization

**Dockerfile** (already exists):
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run API server
CMD ["python", "-m", "uvicorn", "src.api.server:create_api_application", "--host", "0.0.0.0", "--port", "8000"]
```

**Build and run**:
```bash
# Build image
docker build -t health-agent-api:latest .

# Run multiple instances
docker run -d -p 8001:8000 --name api-1 health-agent-api:latest
docker run -d -p 8002:8000 --name api-2 health-agent-api:latest
docker run -d -p 8003:8000 --name api-3 health-agent-api:latest
```

#### 2. Docker Compose (Multiple Instances)

**docker-compose.yml** (enhanced):
```yaml
version: '3.8'

services:
  # API instances (scale as needed)
  api-1:
    build: .
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379/0
      - RUN_MODE=api
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  api-2:
    build: .
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379/0
      - RUN_MODE=api
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  api-3:
    build: .
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379/0
      - RUN_MODE=api
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  # Load balancer
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - api-1
      - api-2
      - api-3
    restart: unless-stopped

  # Shared services
  postgres:
    image: ankane/pgvector:latest
    environment:
      POSTGRES_DB: health_agent
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

**Scale with Docker Compose**:
```bash
# Scale to 5 instances
docker-compose up -d --scale api=5

# Scale down to 2 instances
docker-compose up -d --scale api=2
```

#### 3. Kubernetes Deployment

**deployment.yaml**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: health-agent-api
spec:
  replicas: 3  # Start with 3 instances
  selector:
    matchLabels:
      app: health-agent-api
  template:
    metadata:
      labels:
        app: health-agent-api
    spec:
      containers:
      - name: api
        image: health-agent-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: REDIS_URL
          value: "redis://redis-service:6379/0"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /api/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: health-agent-api
spec:
  selector:
    app: health-agent-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

**Horizontal Pod Autoscaler**:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: health-agent-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: health-agent-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

**Deploy to Kubernetes**:
```bash
kubectl apply -f deployment.yaml
kubectl apply -f hpa.yaml

# Check autoscaling
kubectl get hpa
kubectl describe hpa health-agent-api-hpa
```

### Session Handling

**Stateless Design** (current):
- No server-side sessions
- All state in database/Redis
- Any instance can handle any request
- **No sticky sessions required** ✅

**Benefits**:
- Simple load balancing (round-robin)
- No session migration needed
- Instance failures don't lose sessions

---

## Database Scaling

### Current Configuration

**Single PostgreSQL Instance**:
- Connection pool: Dynamic (4-13 connections for 4-core)
- Indexes: 6 strategic indexes (Phase 3)
- Query time: 2-10ms (optimized)

**Capacity**: ~100-300 concurrent users per instance

### Scaling Strategies

#### Strategy 1: Vertical Scaling (Short-Term)

**When to use**: < 500 concurrent users

**Upgrade path**:
```
Current: 4 CPU, 4GB RAM
     ↓
Step 1:  8 CPU, 8GB RAM    (supports ~500 users)
     ↓
Step 2: 16 CPU, 16GB RAM   (supports ~1000 users)
```

**Connection pool adjustment** (automatic with dynamic sizing):
```python
# 8-core system
min_size = 8
max_size = (2 * 8) + 5 = 21 connections

# 16-core system
min_size = 16
max_size = (2 * 16) + 5 = 37 connections
```

**Pros**:
- Simple (no architecture changes)
- No replication lag
- Consistent reads/writes

**Cons**:
- Expensive at scale
- Downtime for upgrades
- Single point of failure

---

#### Strategy 2: Read Replicas (Medium-Term)

**When to use**: > 500 concurrent users, read-heavy workload

**Architecture**:
```
                    ┌──────────────┐
                    │   Primary    │
                    │  (Writes)    │
                    └──────┬───────┘
                           │
              Async Replication
                           │
           ┌───────────────┼───────────────┐
           │               │               │
      ┌────▼────┐     ┌────▼────┐     ┌───▼─────┐
      │Replica 1│     │Replica 2│     │Replica N│
      │ (Reads) │     │ (Reads) │     │ (Reads) │
      └─────────┘     └─────────┘     └─────────┘
```

**Implementation** (with PgBouncer):
```bash
# Primary (write) connection
DATABASE_URL_PRIMARY=postgres://user:pass@primary:5432/db

# Replica (read) connection
DATABASE_URL_REPLICA=postgres://user:pass@replica:5432/db
```

**Code changes** (`src/db/queries.py`):
```python
# Read queries → Replica
async def get_conversation_history(user_id: str):
    async with db_replica.connection() as conn:
        # Read from replica
        pass

# Write queries → Primary
async def save_conversation_message(user_id: str, ...):
    async with db_primary.connection() as conn:
        # Write to primary
        pass
```

**Read/Write Split**:
- **Reads** (90% of queries):
  - `get_conversation_history`
  - `get_food_entries`
  - `get_active_reminders`
  - `get_user_xp_level`

- **Writes** (10% of queries):
  - `save_conversation_message`
  - `create_food_entry`
  - `update_user_profile`

**Replication Lag**:
- Expected: 10-100ms
- Acceptable for most queries
- Use primary for time-sensitive reads (just-created data)

**Pros**:
- Scales read capacity linearly
- No application downtime
- Better read performance

**Cons**:
- Replication lag
- Application changes required
- More complex setup

---

#### Strategy 3: Connection Pooling (PgBouncer)

**When to use**: Connection pool exhaustion (>80% utilization)

**Setup** (Docker):
```yaml
# docker-compose.yml
pgbouncer:
  image: pgbouncer/pgbouncer:latest
  environment:
    - DATABASES_HOST=postgres
    - DATABASES_PORT=5432
    - DATABASES_DBNAME=health_agent
    - POOL_MODE=transaction
    - MAX_CLIENT_CONN=1000
    - DEFAULT_POOL_SIZE=25
  ports:
    - "6432:6432"
  depends_on:
    - postgres
```

**Configuration** (`pgbouncer.ini`):
```ini
[databases]
health_agent = host=postgres port=5432 dbname=health_agent

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt

# Pool configuration
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
min_pool_size = 5
reserve_pool_size = 5
```

**Application changes**:
```python
# Change database URL to PgBouncer
DATABASE_URL = "postgres://user:pass@pgbouncer:6432/health_agent"
```

**Benefits**:
- 1000 client connections → 25 database connections
- Reduces database load
- Connection reuse

**Pros**:
- Dramatically increases capacity
- Minimal application changes
- Lower database resource usage

**Cons**:
- Transaction pooling limits (no prepared statements across requests)
- Additional component to maintain

---

#### Strategy 4: Database Partitioning (Long-Term)

**When to use**: > 1 million messages, slow queries despite indexes

**Partition Strategy** (conversation_history):
```sql
-- Partition by date (monthly)
CREATE TABLE conversation_history_2026_01 PARTITION OF conversation_history
FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE conversation_history_2026_02 PARTITION OF conversation_history
FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

-- Old partitions can be archived or dropped
DROP TABLE conversation_history_2025_01;
```

**Benefits**:
- Queries only scan relevant partitions
- Easy archival of old data
- Better query performance

**Maintenance**:
```bash
# Automate partition creation (monthly cron)
0 0 1 * * psql $DATABASE_URL -c "CALL create_next_month_partition();"
```

**Pros**:
- Maintains query performance at massive scale
- Easy data lifecycle management
- Can archive cold data

**Cons**:
- Complex setup
- Partition maintenance overhead
- Application may need awareness

---

## Cache Scaling

### Current Configuration

**Single Redis Instance**:
- Memory: 256MB
- Eviction policy: allkeys-lru
- Persistence: AOF
- Expected capacity: ~100-300 users

### Scaling Strategies

#### Strategy 1: Increase Memory (Vertical)

**When to use**: Cache hit rate < 30%, frequent evictions

**Upgrade path**:
```
Current: 256MB   (100-300 users)
     ↓
Step 1:  512MB   (300-500 users)
     ↓
Step 2:  1GB     (500-1000 users)
     ↓
Step 3:  2GB+    (1000+ users)
```

**Monitor evictions**:
```bash
# Check evicted keys
redis-cli INFO stats | grep evicted_keys

# If evicted_keys growing rapidly → increase memory
```

**Docker configuration**:
```yaml
redis:
  image: redis:7-alpine
  command: redis-server --maxmemory 1gb --maxmemory-policy allkeys-lru
```

**Pros**:
- Simple (no architecture changes)
- No code changes
- Better hit rate

**Cons**:
- Limited by single-instance memory
- Vertical scaling limits

---

#### Strategy 2: Redis Cluster (Horizontal)

**When to use**: > 1GB cache data, high throughput

**Architecture**:
```
                    ┌──────────────┐
                    │   Clients    │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
         ┌────▼────┐  ┌───▼─────┐  ┌──▼──────┐
         │ Master 1│  │Master 2 │  │Master 3 │
         │  (Shard)│  │ (Shard) │  │ (Shard) │
         └────┬────┘  └───┬─────┘  └──┬──────┘
              │            │            │
         ┌────▼────┐  ┌───▼─────┐  ┌──▼──────┐
         │Replica 1│  │Replica 2│  │Replica 3│
         └─────────┘  └─────────┘  └─────────┘
```

**Setup** (docker-compose.yml):
```yaml
redis-cluster:
  image: redis:7-alpine
  command: redis-cli --cluster create redis1:6379 redis2:6379 redis3:6379 --cluster-replicas 1
```

**Client changes** (`src/cache/redis_client.py`):
```python
from redis.cluster import RedisCluster

# Create cluster client
redis_client = RedisCluster(
    startup_nodes=[
        {"host": "redis1", "port": 6379},
        {"host": "redis2", "port": 6379},
        {"host": "redis3", "port": 6379},
    ],
    decode_responses=True
)
```

**Data distribution**:
- Hash slot-based sharding
- 16384 slots distributed across masters
- Automatic failover

**Pros**:
- Horizontal scaling (memory, throughput)
- High availability (automatic failover)
- Linear scalability

**Cons**:
- Complex setup
- Code changes required
- Multi-key operations limited

---

#### Strategy 3: Redis Sentinel (High Availability)

**When to use**: Need HA, not necessarily more capacity

**Architecture**:
```
    ┌─────────┐      ┌─────────┐      ┌─────────┐
    │Sentinel │      │Sentinel │      │Sentinel │
    │   1     │      │   2     │      │   3     │
    └────┬────┘      └────┬────┘      └────┬────┘
         └───────────────┬┼──────────────┘
                         ││
              ┌──────────┼┴───────────┐
              │                       │
         ┌────▼────┐             ┌───▼─────┐
         │ Master  │─────────────│ Replica │
         │ (Write) │ Replication │ (Read)  │
         └─────────┘             └─────────┘
```

**Benefits**:
- Automatic failover (30-60 seconds)
- Master election
- No manual intervention

**Code changes**: None (Sentinel handles failover transparently)

**Pros**:
- High availability
- Automatic failover
- Minimal code changes

**Cons**:
- Doesn't increase capacity
- Failover downtime (seconds)
- Complex setup

---

## Load Balancing

### nginx Configuration

**nginx.conf**:
```nginx
upstream api_backend {
    least_conn;  # Route to least busy server

    server api-1:8000 max_fails=3 fail_timeout=30s;
    server api-2:8000 max_fails=3 fail_timeout=30s;
    server api-3:8000 max_fails=3 fail_timeout=30s;

    keepalive 32;  # Persistent connections
}

server {
    listen 80;
    server_name api.healthagent.com;

    # Health check
    location /health {
        proxy_pass http://api_backend/api/health;
        proxy_connect_timeout 5s;
        proxy_read_timeout 10s;
    }

    # API endpoints
    location /api/ {
        proxy_pass http://api_backend;

        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 10s;
        proxy_send_timeout 30s;
        proxy_read_timeout 60s;

        # Buffering
        proxy_buffering off;  # For streaming responses
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/m;
    limit_req zone=api_limit burst=20 nodelay;
}
```

### Load Balancing Algorithms

| Algorithm | Use Case | Pros | Cons |
|-----------|----------|------|------|
| **Round Robin** | Equal instances | Simple, fair | Ignores load |
| **Least Connections** | Varied request times | Load-aware | More complex |
| **IP Hash** | Need sticky sessions | Consistent routing | Uneven distribution |
| **Weighted** | Mixed instance sizes | Flexible | Manual tuning |

**Recommendation**: **Least Connections** (handles varied LLM response times well)

---

## Cost Analysis

### Single Instance vs Scaled (AWS Example)

#### Single Instance (100 users)

| Service | Instance Type | Cost/Month |
|---------|---------------|------------|
| API Server | t3.medium (4-core, 2GB) | $30 |
| PostgreSQL | db.t3.small (2-core, 2GB) | $25 |
| Redis | t3.micro (2-core, 1GB) | $7 |
| **Total** | | **$62/month** |

**Cost per user**: $0.62/month

---

#### Scaled (500 users)

| Service | Instance Type | Quantity | Cost/Month |
|---------|---------------|----------|------------|
| API Server | t3.medium (4-core, 2GB) | 5× | $150 |
| Load Balancer | ALB | 1× | $20 |
| PostgreSQL | db.m5.large (8-core, 8GB) | 1× | $140 |
| Redis | t3.small (2-core, 2GB) | 1× | $15 |
| **Total** | | | **$325/month** |

**Cost per user**: $0.65/month

**Cost efficiency**: Nearly linear scaling (3% increase per user)

---

#### Highly Scaled (2000 users)

| Service | Instance Type | Quantity | Cost/Month |
|---------|---------------|----------|------------|
| API Server | t3.medium | 15× | $450 |
| Load Balancer | ALB | 1× | $20 |
| PostgreSQL Primary | db.m5.2xlarge (32-core, 32GB) | 1× | $540 |
| PostgreSQL Replica | db.m5.xlarge (16-core, 16GB) | 2× | $540 |
| Redis Cluster | t3.medium | 6× | $180 |
| **Total** | | | **$1,730/month** |

**Cost per user**: $0.87/month

**Cost increase**: 40% per user (economies of scale diminish)

### Cost Optimization Tips

1. **Reserved Instances**: 40-60% savings for predictable workloads
2. **Spot Instances**: 70-90% savings for API servers (auto-healing)
3. **Autoscaling**: Scale down during off-peak hours (50% savings)
4. **Database Optimization**: Smaller instance + read replicas cheaper than large primary
5. **Cache Optimization**: Higher hit rate → Lower database costs

---

## Scaling Checklist

### Pre-Scaling Checklist

- [ ] Monitor metrics for 7+ days
- [ ] Identify which resource is bottleneck (CPU, memory, DB, cache)
- [ ] Review current utilization (should be >70% before scaling)
- [ ] Check error rates (should be <1%)
- [ ] Validate optimizations are working (cache hit rate >60%)
- [ ] Estimate target user count
- [ ] Calculate cost impact
- [ ] Plan rollback strategy

### During Scaling

- [ ] Enable maintenance mode (optional)
- [ ] Take database backup
- [ ] Deploy new infrastructure
- [ ] Run smoke tests
- [ ] Gradually shift traffic (10% → 50% → 100%)
- [ ] Monitor metrics continuously
- [ ] Check for errors
- [ ] Validate performance improvements

### Post-Scaling Validation

- [ ] P95 latency < 3s (target)
- [ ] Error rate < 1%
- [ ] Database pool utilization < 80%
- [ ] Cache hit rate > 60%
- [ ] CPU usage < 70%
- [ ] Memory usage < 80%
- [ ] No errors in logs
- [ ] All health checks passing

### Rollback Plan

If scaling fails:
1. Shift traffic back to old infrastructure (load balancer)
2. Keep new infrastructure running (for debugging)
3. Investigate issues
4. Fix and retry

---

## Quick Reference

### Scaling Decision Tree

```
How many concurrent users?
│
├─ 0-100 users
│  └─ Single instance (4-core, 2GB)
│     Cost: ~$60/month
│
├─ 100-300 users
│  ├─ 2-3 API instances
│  └─ Single DB + Redis
│     Cost: ~$150-200/month
│
├─ 300-500 users
│  ├─ 3-5 API instances
│  ├─ Vertical DB scaling (8-core)
│  └─ Increased Redis memory (512MB-1GB)
│     Cost: ~$300-400/month
│
├─ 500-1000 users
│  ├─ 5-10 API instances
│  ├─ DB read replicas
│  ├─ PgBouncer connection pooling
│  └─ Redis Sentinel (HA)
│     Cost: ~$700-1000/month
│
└─ 1000+ users
   ├─ 10+ API instances (autoscaling)
   ├─ Primary + 2-3 read replicas
   ├─ Redis Cluster (sharded)
   └─ Multi-region (optional)
      Cost: ~$1500+/month
```

### Scaling Commands

```bash
# Docker Compose (scale API)
docker-compose up -d --scale api=5

# Kubernetes (scale deployment)
kubectl scale deployment health-agent-api --replicas=10

# Check autoscaler
kubectl get hpa

# Monitor metrics
curl http://localhost/api/v1/metrics | jq '.database.pool_utilization_percent'

# Redis memory check
redis-cli INFO memory | grep used_memory_human
```

---

**Last Updated**: 2026-01-18
**Next Review**: Quarterly or when approaching capacity thresholds

