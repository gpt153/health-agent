# Production Deployment Guide

**Last Updated**: 2026-01-18
**Prerequisites**: All optimization phases (1-5) implemented
**Target**: Production-ready deployment with monitoring

---

## Pre-Deployment Checklist

### Code Requirements

- [x] Phase 1: Profiling infrastructure
- [x] Phase 2: Redis caching implemented
- [x] Phase 3: Database indexes created
- [x] Phase 4: Load testing validated
- [x] Phase 5: Monitoring endpoints active

### Infrastructure Requirements

- [ ] PostgreSQL 14+ with pgvector extension
- [ ] Redis 7+ running
- [ ] Docker/Docker Compose installed
- [ ] SSL certificates (production)
- [ ] Domain configured
- [ ] Monitoring tools (Prometheus/Grafana)

---

## Deployment Steps

### 1. Database Setup

```bash
# Apply all migrations
./run_migrations.sh

# Apply performance indexes
psql $DATABASE_URL -f migrations/017_performance_indexes.sql

# Verify indexes
psql $DATABASE_URL -c "\d conversation_history"

# Create production database backup schedule
# Add to cron: 0 2 * * * pg_dump $DATABASE_URL > backup.sql
```

### 2. Redis Configuration

**Production redis.conf**:
```conf
# Memory
maxmemory 512mb
maxmemory-policy allkeys-lru

# Persistence
appendonly yes
appendfsync everysec

# Security
requirepass ${REDIS_PASSWORD}
bind 0.0.0.0
protected-mode yes

# Performance
tcp-backlog 511
timeout 300
```

### 3. Environment Configuration

**.env.production**:
```bash
# Database
DATABASE_URL=postgres://user:pass@prod-db:5432/health_agent

# Redis
REDIS_URL=redis://:password@prod-redis:6379/0
ENABLE_CACHE=true

# API
RUN_MODE=api
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# LLM
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Security
API_KEY_SECRET=your-secret-key-here
CORS_ORIGINS=https://yourdomain.com

# Monitoring
ENABLE_METRICS=true
SLOW_REQUEST_THRESHOLD_MS=3000
```

### 4. Docker Deployment

```bash
# Build production image
docker build -t health-agent-api:v1.0.0 .

# Tag for registry
docker tag health-agent-api:v1.0.0 registry.example.com/health-agent-api:v1.0.0

# Push to registry
docker push registry.example.com/health-agent-api:v1.0.0

# Deploy with docker-compose
docker-compose -f docker-compose.prod.yml up -d

# Verify services
docker-compose ps
docker-compose logs -f api
```

### 5. Load Balancer Setup

**nginx.conf** (production):
```nginx
upstream api_backend {
    least_conn;
    server api-1:8000 max_fails=3 fail_timeout=30s;
    server api-2:8000 max_fails=3 fail_timeout=30s;
    server api-3:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    location /api/ {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/v1/metrics {
        auth_basic "Restricted";
        auth_basic_user_file /etc/nginx/.htpasswd;
        proxy_pass http://api_backend;
    }
}
```

### 6. Monitoring Setup

**Prometheus configuration**:
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'health-agent-api'
    static_configs:
      - targets: ['api-1:8000', 'api-2:8000', 'api-3:8000']
    metrics_path: '/api/v1/metrics'
```

**Alert rules**:
```yaml
# alerts.yml
groups:
  - name: health-agent
    rules:
      - alert: HighCPU
        expr: health_agent_cpu_percent > 80
        for: 10m
        annotations:
          summary: "High CPU usage detected"

      - alert: DatabasePoolExhausted
        expr: health_agent_db_pool_active / health_agent_db_pool_size >= 0.9
        for: 5m
        annotations:
          summary: "Database pool near capacity"

      - alert: LowCacheHitRate
        expr: health_agent_cache_hit_rate_percent < 30
        for: 20m
        annotations:
          summary: "Cache performance degraded"
```

---

## Post-Deployment Validation

### Health Checks

```bash
# API health
curl https://api.yourdomain.com/api/health

# Expected response:
# {"status":"healthy","database":"connected","timestamp":"..."}

# Metrics endpoint
curl https://api.yourdomain.com/api/v1/metrics | jq '.'

# Check specific metrics
curl -s https://api.yourdomain.com/api/v1/metrics | jq '.cache.hit_rate_percent'
curl -s https://api.yourdomain.com/api/v1/metrics | jq '.database.pool_utilization_percent'
```

### Performance Validation

```bash
# Run load test (from load_tests/)
./run_load_tests.sh steady

# Monitor during test
python monitor.py --host https://api.yourdomain.com --interval 5

# Verify success criteria
# - P95 < 3s ✓
# - Error rate < 1% ✓
# - Cache hit rate > 60% ✓
```

### Database Validation

```sql
-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

-- Should see high idx_scan for performance indexes

-- Check connection pool
SELECT count(*) as active_connections
FROM pg_stat_activity
WHERE state = 'active';

-- Should be < 80% of max_connections
```

### Cache Validation

```bash
# Redis stats
redis-cli INFO stats

# Check hit rate
redis-cli INFO stats | grep keyspace_hits
redis-cli INFO stats | grep keyspace_misses

# Calculate hit rate
# hit_rate = hits / (hits + misses)
# Should be > 60% after warmup
```

---

## Monitoring Dashboard

### Key Metrics to Track

**System**:
- CPU usage (alert: > 80%)
- Memory usage (alert: > 85%)
- Disk I/O

**Database**:
- Pool utilization (alert: > 80%)
- Query latency (P95 < 50ms)
- Active connections

**Cache**:
- Hit rate (alert: < 30%)
- Memory usage
- Evictions

**API**:
- Request rate
- P95 latency (alert: > 3s)
- Error rate (alert: > 1%)

### Grafana Dashboard (JSON template)

```json
{
  "dashboard": {
    "title": "Health Agent API",
    "panels": [
      {
        "title": "API Latency (P95)",
        "targets": [{
          "expr": "histogram_quantile(0.95, health_agent_request_duration_ms)"
        }]
      },
      {
        "title": "Cache Hit Rate",
        "targets": [{
          "expr": "health_agent_cache_hit_rate_percent"
        }]
      },
      {
        "title": "Database Pool Utilization",
        "targets": [{
          "expr": "(health_agent_db_pool_active / health_agent_db_pool_size) * 100"
        }]
      }
    ]
  }
}
```

---

## Troubleshooting

### High Error Rate

**Symptoms**: > 1% error rate

**Diagnosis**:
```bash
# Check logs
docker-compose logs api | grep ERROR

# Check database
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';"

# Check Redis
redis-cli PING
```

**Solutions**:
- Increase database pool size
- Restart Redis if unresponsive
- Check LLM API quota

### Slow Responses

**Symptoms**: P95 > 3s

**Diagnosis**:
```bash
# Check slow requests
docker-compose logs api | grep "SLOW REQUEST"

# Check cache hit rate
curl -s http://localhost/api/v1/metrics | jq '.cache.hit_rate_percent'

# Profile database
psql $DATABASE_URL -c "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
```

**Solutions**:
- Warm up cache
- Add missing indexes
- Increase Redis memory
- Optimize slow queries

### Database Connection Errors

**Symptoms**: "pool exhausted" errors

**Diagnosis**:
```bash
# Check pool stats
curl -s http://localhost/api/v1/metrics | jq '.database'

# Check PostgreSQL connections
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"
```

**Solutions**:
- Increase `max_size` in connection pool
- Add PgBouncer connection pooler
- Scale database vertically

---

## Security Hardening

### API Security

```python
# Require API key for production
# src/api/auth.py

async def verify_api_key(api_key: str = Header(None)):
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    if api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key
```

### Database Security

```bash
# Create read-only user for replicas
psql $DATABASE_URL <<EOF
CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD 'secure-password';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO replicator;
EOF

# Restrict network access
# pg_hba.conf:
# host    all    all    10.0.0.0/8    md5
```

### Redis Security

```bash
# Require password
redis-cli CONFIG SET requirepass "your-strong-password"

# Disable dangerous commands
redis-cli CONFIG SET rename-command FLUSHDB ""
redis-cli CONFIG SET rename-command FLUSHALL ""
```

---

## Backup & Recovery

### Database Backups

```bash
# Daily automated backups
0 2 * * * pg_dump $DATABASE_URL | gzip > /backups/db_$(date +\%Y\%m\%d).sql.gz

# Retention: 7 daily, 4 weekly, 12 monthly
# Restore:
gunzip -c backup.sql.gz | psql $DATABASE_URL
```

### Redis Backups

```bash
# Manual backup
redis-cli SAVE

# Automated (AOF already enabled)
# File: /data/appendonly.aof

# Restore: Copy .aof file to data directory, restart Redis
```

### Configuration Backups

```bash
# Version control all configs
git add .env.production docker-compose.prod.yml nginx.conf
git commit -m "Production configuration snapshot"
git tag production-$(date +%Y%m%d)
```

---

## Scaling Procedure

### When to Scale

Monitor these thresholds (from SCALING_GUIDE.md):
- CPU > 80% for 10min → Add API instances
- Memory > 85% for 5min → Scale vertically
- DB Pool > 80% for 5min → Add read replicas
- Cache hit < 30% for 20min → Increase Redis memory

### Horizontal Scaling (Add API Instances)

```bash
# Docker Compose
docker-compose up -d --scale api=5

# Kubernetes
kubectl scale deployment health-agent-api --replicas=10

# Update nginx upstream
# Add new instances to nginx.conf, reload:
nginx -s reload
```

### Database Scaling (Add Read Replica)

```bash
# Create replica
# (Cloud provider specific, e.g., AWS RDS read replica)

# Update connection strings
DATABASE_URL_REPLICA=postgres://user:pass@replica:5432/db

# Route read queries to replica in code
```

---

## Rollback Plan

### Rollback Trigger

If any of these occur within 1 hour of deployment:
- Error rate > 5%
- P95 latency > 10s
- Database connection failures
- Cache completely unavailable

### Rollback Steps

```bash
# 1. Switch to previous version
docker-compose down
docker-compose -f docker-compose.previous.yml up -d

# 2. Verify health
curl http://localhost/api/health

# 3. Rollback database migrations (if any)
psql $DATABASE_URL -f migrations/rollbacks/017_performance_indexes_rollback.sql

# 4. Monitor for 30 minutes
python load_tests/monitor.py --duration 1800

# 5. If stable, investigate deployment issues
```

---

## Quick Reference

### Essential Commands

```bash
# Health check
curl https://api.yourdomain.com/api/health

# Metrics
curl https://api.yourdomain.com/api/v1/metrics | jq '.'

# Logs
docker-compose logs -f --tail=100 api

# Restart services
docker-compose restart api

# Database connection test
psql $DATABASE_URL -c "SELECT 1;"

# Redis connection test
redis-cli -h prod-redis PING

# Load test
./load_tests/run_load_tests.sh steady
```

### Support Contacts

- **On-Call Engineer**: alerts@yourdomain.com
- **Database Admin**: dba@yourdomain.com
- **Infrastructure**: infra@yourdomain.com
- **Monitoring**: https://grafana.yourdomain.com

---

**Deployment Date**: _____________________
**Deployed By**: _____________________
**Version**: v1.0.0 (with performance optimizations)
**Status**: ⬜ Deployed  ⬜ Validated  ⬜ Monitoring Active

