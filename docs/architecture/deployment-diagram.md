# Deployment Architecture

This document describes the Health Agent's deployment architecture, including Docker setup, environment configuration, and production deployment strategies.

---

## Production Deployment Architecture

```mermaid
graph TB
    subgraph GITHUB["GitHub"]
        REPO[gpt153/health-agent<br/>Repository]
        GHCR[GitHub Container Registry<br/>ghcr.io/gpt153/health-agent]
        ACTIONS[GitHub Actions CI/CD]
    end

    subgraph PROD["Production Server"]
        direction TB

        subgraph DOCKER["Docker Compose Services"]
            BOT[health-agent-bot<br/>RUN_MODE=bot<br/>Port: N/A]
            DB[PostgreSQL 14<br/>Port: 5436<br/>+ pgvector extension]
        end

        subgraph STORAGE["Persistent Storage"]
            VOL_DB[Volume: postgres_data]
            VOL_DATA[Volume: production/data<br/>Markdown files]
            VOL_PHOTOS[Volume: production/photos<br/>Food images]
            VOL_LOGS[Volume: production/logs]
        end

        DOCKER --> STORAGE
    end

    subgraph EXTERNAL["External Services"]
        TELEGRAM[Telegram Bot API<br/>api.telegram.org]
        OPENAI[OpenAI API<br/>GPT-4o, Embeddings]
        ANTHROPIC[Anthropic API<br/>Claude 3.5 Sonnet]
        USDA[USDA FoodData Central<br/>api.nal.usda.gov]
    end

    REPO --> ACTIONS
    ACTIONS -->|Build & Push| GHCR
    GHCR -->|Pull Image| BOT

    BOT <--> DB
    BOT <-->|Polling| TELEGRAM
    BOT -->|API Calls| OPENAI
    BOT -->|API Calls| ANTHROPIC
    BOT -->|API Calls| USDA

    style BOT fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    style DB fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    style GHCR fill:#fff3e0,stroke:#e65100,stroke-width:2px
```

---

## Docker Compose Configuration

### Services Overview

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: pgvector/pgvector:pg14
    container_name: health-agent-db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: health_agent
    ports:
      - "5436:5432"  # External:Internal
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./migrations:/docker-entrypoint-initdb.d  # Auto-run migrations
    restart: unless-stopped

  # Telegram Bot (Production Mode)
  health-agent-bot:
    image: ghcr.io/gpt153/health-agent:latest
    container_name: health-agent-bot
    environment:
      RUN_MODE: bot  # Bot mode only
      DATABASE_URL: postgresql://postgres:${DB_PASSWORD}@postgres:5432/health_agent
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
      ALLOWED_TELEGRAM_IDS: ${ALLOWED_TELEGRAM_IDS}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      USDA_API_KEY: ${USDA_API_KEY}
      ENABLE_MEM0: "true"
      LOG_LEVEL: INFO
    volumes:
      - ./production/data:/app/production/data        # Markdown files
      - ./production/photos:/app/production/photos    # Food photos
      - ./production/logs:/app/production/logs        # Application logs
    depends_on:
      - postgres
    restart: unless-stopped

volumes:
  postgres_data:  # Persistent database storage
```

### Network Topology

```mermaid
graph LR
    subgraph DOCKER_NETWORK["Docker Bridge Network"]
        BOT[health-agent-bot<br/>Container]
        DB[postgres<br/>Container]
    end

    subgraph HOST["Host Machine"]
        PORT_5436[Port 5436<br/>PostgreSQL]
        FILES[File System<br/>./production/]
    end

    INTERNET[Internet]

    BOT -->|Internal DNS:<br/>postgres:5432| DB
    DB -->|Port Mapping| PORT_5436
    BOT -->|Volume Mount| FILES
    BOT <-->|Polling| INTERNET

    style DOCKER_NETWORK fill:#e1f5ff,stroke:#01579b,stroke-width:2px
```

**Key Points**:
- Bot and DB communicate via Docker internal network (fast)
- PostgreSQL exposed on port 5436 for external tools (psql, pgAdmin)
- Volume mounts for persistent data and logs
- Internet access for Telegram polling and API calls

---

## Development Deployment Architecture

```mermaid
graph TB
    subgraph DEV["Development Environment"]
        direction TB

        subgraph NATIVE["Native Python"]
            BOT_DEV[bot.py<br/>RUN_MODE=bot<br/>Hot Reload: N/A]
            API_DEV[api/app.py<br/>RUN_MODE=api<br/>uvicorn --reload]
        end

        subgraph DOCKER_DEV["Docker Compose"]
            DB_DEV[PostgreSQL<br/>Port: 5436]
        end

        NATIVE --> DOCKER_DEV
    end

    subgraph TESTING["Testing Tools"]
        SCAR[SCAR<br/>Automated Tests]
        PYTEST[pytest<br/>Unit + Integration Tests]
    end

    API_DEV <--> SCAR
    NATIVE --> PYTEST

    style API_DEV fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style SCAR fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
```

**Development Workflow**:
1. Docker Compose runs PostgreSQL only
2. Native Python runs bot or API (hot reload enabled)
3. SCAR tests via API mode
4. pytest runs unit and integration tests

---

## Environment Variables

### Required Variables

```bash
# Telegram Configuration
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz  # From @BotFather
ALLOWED_TELEGRAM_IDS=123456789,987654321  # Comma-separated Telegram user IDs

# Database Configuration
DATABASE_URL=postgresql://postgres:password@localhost:5436/health_agent

# LLM API Keys
OPENAI_API_KEY=sk-proj-...  # For GPT-4o and embeddings
ANTHROPIC_API_KEY=sk-ant-...  # For Claude 3.5 Sonnet

# Optional: Nutrition Data
USDA_API_KEY=abc123...  # USDA FoodData Central API key (optional)
```

### Optional Variables

```bash
# Run Mode
RUN_MODE=bot  # Options: bot, api, both

# API Configuration (if RUN_MODE includes api)
API_HOST=0.0.0.0
API_PORT=8080
API_KEYS=test_key_123,prod_key_456  # Comma-separated API keys

# Feature Flags
ENABLE_MEM0=true  # Enable semantic memory (requires OPENAI_API_KEY)

# Logging
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR
```

### Environment Files

**Production** (`.env.production`):
```bash
RUN_MODE=bot
DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@postgres:5432/health_agent
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
ALLOWED_TELEGRAM_IDS=${ALLOWED_TELEGRAM_IDS}
ENABLE_MEM0=true
LOG_LEVEL=INFO
```

**Development** (`.env.development`):
```bash
RUN_MODE=api
DATABASE_URL=postgresql://postgres:devpassword@localhost:5436/health_agent
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
OPENAI_API_KEY=${OPENAI_API_KEY}
ENABLE_MEM0=false  # Disable for faster dev iteration
LOG_LEVEL=DEBUG
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

```mermaid
flowchart LR
    PUSH[Push to main<br/>branch]

    subgraph BUILD["Build Stage"]
        CHECKOUT[Checkout Code]
        LOGIN[Login to<br/>GitHub Container Registry]
        META[Extract Metadata<br/>tags, labels]
        BUILD_IMG[Build Docker Image]
        PUSH_IMG[Push to<br/>ghcr.io]
    end

    subgraph DEPLOY["Deploy Stage (Manual)"]
        SSH[SSH to<br/>Production Server]
        PULL[Pull Latest Image]
        RESTART[Restart Containers<br/>docker compose up -d]
    end

    PUSH --> CHECKOUT
    CHECKOUT --> LOGIN
    LOGIN --> META
    META --> BUILD_IMG
    BUILD_IMG --> PUSH_IMG

    PUSH_IMG -.Manual Trigger.-> SSH
    SSH --> PULL
    PULL --> RESTART

    style BUILD fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    style DEPLOY fill:#fff3e0,stroke:#e65100,stroke-width:2px
```

### Workflow File

`.github/workflows/docker-build-deploy.yml`:
```yaml
name: Build and Deploy Docker Image

on:
  push:
    branches: [main]
  workflow_dispatch:  # Manual trigger

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Login to GitHub Container Registry
        uses: docker/login-action@v2
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: ghcr.io/gpt153/health-agent
          tags: |
            type=ref,event=branch
            type=sha,prefix={{branch}}-

      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
```

**Image Tags**:
- `ghcr.io/gpt153/health-agent:main` - Latest from main branch
- `ghcr.io/gpt153/health-agent:main-abc1234` - Specific commit SHA

---

## Scaling Considerations

### Current Architecture (Single Instance)

**Limitations**:
- Single bot instance (Telegram polling)
- Single database instance
- No load balancing

**Suitable for**:
- 1-10 users
- <1000 messages/day
- <100 concurrent conversations

### Scaling Strategy (Future)

```mermaid
graph TB
    subgraph LOAD_BALANCER["Load Balancer (nginx)"]
        LB[nginx]
    end

    subgraph BOT_INSTANCES["Bot Instances (Horizontal Scaling)"]
        BOT1[health-agent-bot-1]
        BOT2[health-agent-bot-2]
        BOT3[health-agent-bot-3]
    end

    subgraph DATABASE["Database (Read Replicas)"]
        DB_PRIMARY[(PostgreSQL<br/>Primary)]
        DB_REPLICA1[(PostgreSQL<br/>Replica 1)]
        DB_REPLICA2[(PostgreSQL<br/>Replica 2)]
    end

    subgraph CACHE["Caching Layer"]
        REDIS[(Redis)]
    end

    LB --> BOT1
    LB --> BOT2
    LB --> BOT3

    BOT1 --> DB_PRIMARY
    BOT1 -.Read.-> DB_REPLICA1
    BOT2 --> DB_PRIMARY
    BOT2 -.Read.-> DB_REPLICA2
    BOT3 --> DB_PRIMARY

    BOT1 --> REDIS
    BOT2 --> REDIS
    BOT3 --> REDIS

    DB_PRIMARY -.Replication.-> DB_REPLICA1
    DB_PRIMARY -.Replication.-> DB_REPLICA2

    style DB_PRIMARY fill:#e8f5e9,stroke:#1b5e20,stroke-width:3px
```

**Scaling Triggers**:
- \>50 active users
- \>5000 messages/day
- Response time >5 seconds

**See**: `/docs/deployment/scaling.md` for detailed scaling guide

---

## Monitoring and Observability

### Logging

**Log Locations**:
- **Docker**: `docker compose logs -f health-agent-bot`
- **Native**: `./production/logs/health_agent.log`

**Log Format**:
```
2025-01-18 12:34:56,789 - INFO - src.bot - User 123456 sent message
2025-01-18 12:34:57,123 - INFO - src.agent - Tool call: save_food_entry
2025-01-18 12:34:58,456 - INFO - src.vision - Multi-agent consensus: 450 cal
```

### Health Checks

**Database Health**:
```bash
# Check if PostgreSQL is accepting connections
psql -h localhost -p 5436 -U postgres -d health_agent -c "SELECT 1;"
```

**Bot Health**:
```bash
# Check if bot container is running
docker ps | grep health-agent-bot

# Check recent logs
docker logs health-agent-bot --tail 50
```

**API Health** (if running API mode):
```bash
curl http://localhost:8080/health
# Response: {"status": "healthy", "database": "connected"}
```

---

## Backup and Recovery

### Automated Backups

```bash
# Daily database backup (cron job)
0 2 * * * docker exec health-agent-db pg_dump -U postgres health_agent > /backups/health_agent_$(date +\%Y\%m\%d).sql
```

### Backup Locations

```
/backups/
├── health_agent_20250118.sql  # Daily DB dump
├── health_agent_20250117.sql
└── ...

./production/
├── data/      # User markdown files (version controlled)
└── photos/    # Food photos (synced to cloud storage)
```

### Recovery Procedure

1. **Database Recovery**:
   ```bash
   docker exec -i health-agent-db psql -U postgres health_agent < /backups/health_agent_20250118.sql
   ```

2. **File Recovery**:
   - Markdown files: Restore from Git or backup
   - Photos: Restore from cloud storage (S3, Dropbox, etc.)

---

## Security Considerations

### Network Security
- ✅ PostgreSQL not exposed to internet (only localhost:5436)
- ✅ No SSH access required (Docker Compose handles deployment)
- ✅ API key authentication for API mode
- ✅ Telegram ID whitelist (only authorized users)

### Secrets Management
- ✅ Environment variables (not hardcoded)
- ✅ `.env` files in `.gitignore` (not committed)
- ✅ GitHub Secrets for CI/CD
- ✅ Docker secrets (for sensitive files)

### Data Encryption
- ✅ PostgreSQL encryption at rest (optional)
- ✅ HTTPS for all API calls (Telegram, OpenAI, Anthropic)
- ✅ No sensitive data in logs

---

## Related Documentation

- **Docker Deployment Guide**: `/docs/deployment/docker.md` - Step-by-step Docker setup
- **Environment Setup**: `/docs/deployment/environment-setup.md` - Complete environment variable reference
- **CI/CD Pipeline**: `/docs/deployment/ci-cd.md` - GitHub Actions configuration
- **Scaling Guide**: `/docs/deployment/scaling.md` - Horizontal and vertical scaling strategies
- **Database Migrations**: `/docs/deployment/database-migrations.md` - Schema management

## Revision History

- 2025-01-18: Initial deployment architecture diagram created for Phase 3.7 documentation
