# Deployment Documentation

Comprehensive deployment guides for the Health Agent system.

---

## Quick Links

1. [Environment Setup](#environment-setup)
2. [Database Migrations](#database-migrations)
3. [Docker Deployment](#docker-deployment)
4. [CI/CD Pipeline](#cicd-pipeline)
5. [Scaling Strategies](#scaling-strategies)

---

## Environment Setup

### Required Environment Variables

```bash
# Telegram
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
ALLOWED_TELEGRAM_IDS=123456789,987654321

# Database
DATABASE_URL=postgresql://postgres:password@localhost:5436/health_agent

# LLM APIs
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...

# Optional
USDA_API_KEY=...  # USDA FoodData Central
```

### Optional Configuration

```bash
# Run Mode
RUN_MODE=bot  # bot | api | both

# API Settings (if RUN_MODE=api or both)
API_HOST=0.0.0.0
API_PORT=8080
API_KEYS=key1,key2

# Features
ENABLE_MEM0=true  # Semantic memory

# Logging
LOG_LEVEL=INFO  # DEBUG | INFO | WARNING | ERROR
```

### Environment Files

**Production** (`.env.production`):
```bash
RUN_MODE=bot
DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@postgres:5432/health_agent
ENABLE_MEM0=true
LOG_LEVEL=INFO
```

**Development** (`.env.development`):
```bash
RUN_MODE=api
DATABASE_URL=postgresql://postgres:devpass@localhost:5436/health_agent
ENABLE_MEM0=false
LOG_LEVEL=DEBUG
```

---

## Database Migrations

### Migration System

**Location**: `/migrations/`
**Format**: `NNN_description.sql`
**Execution**: Auto-run on Docker startup

### Creating Migrations

1. **Create file**: `023_add_sleep_tracking.sql`

```sql
-- Use IF NOT EXISTS for idempotence
CREATE TABLE IF NOT EXISTS sleep_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id),
    duration_hours NUMERIC(4,2),
    quality_rating INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sleep_user_date
ON sleep_entries(user_id, DATE(created_at));
```

2. **Test locally**:
```bash
psql -h localhost -p 5436 -U postgres -d health_agent < migrations/023_add_sleep_tracking.sql
```

3. **Commit**: Migrations run automatically on next Docker restart

### Running Migrations Manually

```bash
# Docker
docker exec -i health-agent-db psql -U postgres health_agent < migrations/023_add_sleep_tracking.sql

# Native PostgreSQL
psql -h localhost -p 5436 -U postgres -d health_agent -f migrations/023_add_sleep_tracking.sql
```

### Migration Best Practices

- ✅ Use `IF NOT EXISTS` for idempotence
- ✅ Add indexes for frequently queried columns
- ✅ Include `ON DELETE CASCADE` for foreign keys
- ✅ Test on dev database first
- ✅ Keep migrations small and focused

---

## Docker Deployment

### Docker Compose Setup

**File**: `docker-compose.yml`

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg14
    container_name: health-agent-db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: health_agent
    ports:
      - "5436:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./migrations:/docker-entrypoint-initdb.d
    restart: unless-stopped

  health-agent-bot:
    image: ghcr.io/gpt153/health-agent:latest
    container_name: health-agent-bot
    environment:
      RUN_MODE: bot
      DATABASE_URL: postgresql://postgres:${DB_PASSWORD}@postgres:5432/health_agent
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
      ALLOWED_TELEGRAM_IDS: ${ALLOWED_TELEGRAM_IDS}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      ENABLE_MEM0: "true"
      LOG_LEVEL: INFO
    volumes:
      - ./production/data:/app/production/data
      - ./production/photos:/app/production/photos
      - ./production/logs:/app/production/logs
    depends_on:
      - postgres
    restart: unless-stopped

volumes:
  postgres_data:
```

### Deployment Commands

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f health-agent-bot

# Restart bot
docker compose restart health-agent-bot

# Stop all services
docker compose down

# Update to latest image
docker compose pull
docker compose up -d
```

### Building Custom Image

```bash
# Build image
docker build -t ghcr.io/gpt153/health-agent:latest .

# Push to registry
docker push ghcr.io/gpt153/health-agent:latest
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

**File**: `.github/workflows/docker-build-deploy.yml`

```yaml
name: Build and Deploy

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Login to GHCR
        uses: docker/login-action@v2
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: |
            ghcr.io/gpt153/health-agent:latest
            ghcr.io/gpt153/health-agent:${{ github.sha }}
```

### Automated Testing

```yaml
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest --cov=src
```

### Deployment Trigger

```bash
# Manual deployment
git push origin main  # Auto-triggers build

# Or manual trigger
gh workflow run docker-build-deploy.yml
```

---

## Scaling Strategies

### Current Architecture

**Suitable for**:
- 1-10 users
- <1000 messages/day
- Single server

**Limitations**:
- Single bot instance (Telegram polling)
- Single database instance
- No load balancing

### Horizontal Scaling (100+ Users)

#### 1. Multiple Bot Instances

```yaml
# docker-compose-scaled.yml
services:
  health-agent-bot-1:
    image: ghcr.io/gpt153/health-agent:latest
    environment:
      RUN_MODE: both  # Bot + API
      INSTANCE_ID: "1"
    ...

  health-agent-bot-2:
    image: ghcr.io/gpt153/health-agent:latest
    environment:
      RUN_MODE: both
      INSTANCE_ID: "2"
    ...

  nginx:
    image: nginx:latest
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - health-agent-bot-1
      - health-agent-bot-2
```

#### 2. Database Read Replicas

```yaml
  postgres-primary:
    image: pgvector/pgvector:pg14
    environment:
      POSTGRES_REPLICATION_MODE: master
    ...

  postgres-replica:
    image: pgvector/pgvector:pg14
    environment:
      POSTGRES_REPLICATION_MODE: slave
      POSTGRES_MASTER_HOST: postgres-primary
    ...
```

#### 3. Redis Caching

```yaml
  redis:
    image: redis:latest
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
```

**Cache Strategy**:
- User profiles (TTL: 1 hour)
- Conversation history (TTL: 30 minutes)
- XP/streak data (TTL: 5 minutes)

### Vertical Scaling

**Database**:
```yaml
postgres:
  deploy:
    resources:
      limits:
        cpus: '4.0'
        memory: 8G
      reservations:
        cpus: '2.0'
        memory: 4G
```

**Bot**:
```yaml
health-agent-bot:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 4G
```

### Performance Monitoring

```bash
# Database connection pool
psql -c "SELECT * FROM pg_stat_activity;"

# Docker resource usage
docker stats

# Application metrics (Prometheus format)
curl http://localhost:8080/metrics
```

---

## Backup and Recovery

### Automated Backups

```bash
# Daily database backup (cron)
0 2 * * * docker exec health-agent-db pg_dump -U postgres health_agent > /backups/health_agent_$(date +\%Y\%m\%d).sql
```

### Manual Backup

```bash
# Database
docker exec health-agent-db pg_dump -U postgres health_agent > backup.sql

# User data (markdown + photos)
tar -czf user_data_backup.tar.gz production/data production/photos
```

### Restore

```bash
# Database
docker exec -i health-agent-db psql -U postgres health_agent < backup.sql

# User data
tar -xzf user_data_backup.tar.gz
```

---

## Security

### Secrets Management

- ✅ Use environment variables
- ✅ Never commit `.env` to git
- ✅ Use GitHub Secrets for CI/CD
- ✅ Rotate API keys quarterly

### Network Security

- ✅ PostgreSQL not exposed to internet
- ✅ API requires authentication
- ✅ HTTPS for all external APIs
- ✅ Firewall rules for Docker ports

### Data Encryption

- ✅ PostgreSQL encryption at rest (optional)
- ✅ TLS for database connections
- ✅ No sensitive data in logs

---

## Monitoring

### Health Checks

```bash
# Database
psql -h localhost -p 5436 -U postgres -d health_agent -c "SELECT 1;"

# Bot (check logs)
docker logs health-agent-bot --tail 50

# API (if running)
curl http://localhost:8080/health
```

### Metrics to Track

- Message processing time
- Database query latency
- API call latency (OpenAI, Anthropic)
- XP award frequency
- Active users per day
- Database size growth

---

## Troubleshooting

### Bot Not Responding

```bash
# Check logs
docker logs health-agent-bot --tail 100

# Restart bot
docker compose restart health-agent-bot

# Check Telegram token
echo $TELEGRAM_BOT_TOKEN
```

### Database Connection Issues

```bash
# Check postgres running
docker ps | grep postgres

# Check connection
psql -h localhost -p 5436 -U postgres -d health_agent

# Check logs
docker logs health-agent-db
```

### Out of Disk Space

```bash
# Check disk usage
df -h

# Clean Docker
docker system prune -a

# Clean old photos (>30 days)
find production/photos -mtime +30 -delete
```

---

## Related Documentation

- **Deployment Architecture**: [/docs/architecture/deployment-diagram.md](../architecture/deployment-diagram.md)
- **Environment Setup**: [/docs/development/getting-started.md](../development/getting-started.md)
- **Troubleshooting**: [/docs/troubleshooting/](../troubleshooting/)

## Revision History

- 2025-01-18: Initial deployment documentation created for Phase 3.7
