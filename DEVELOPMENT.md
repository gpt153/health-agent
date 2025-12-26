# Development Guide - Health Agent

Complete guide to setting up and developing the Health Agent project with optimal workflows for both production and development environments.

## 🎯 Quick Reference

| Task | Command |
|------|---------|
| Start production bot | `docker compose up -d health-agent-bot postgres` |
| Start dev API | `RUN_MODE=api python -m src.main` |
| Check PostgreSQL | `docker compose ps postgres` |
| Test API health | `curl http://localhost:8080/api/health` |
| View bot logs | `docker compose logs -f health-agent-bot` |
| Stop all containers | `docker compose down` |

## 📖 Table of Contents

- [Overview: Two-Mode Architecture](#overview-two-mode-architecture)
- [Quick Start for Experienced Developers](#quick-start-for-experienced-developers)
- [Production Mode Setup](#production-mode-setup)
- [Development Mode Setup](#development-mode-setup)
- [SCAR Integration Workflow](#scar-integration-workflow)
- [Docker vs Native: Decision Matrix](#docker-vs-native-decision-matrix)
- [Troubleshooting Common Issues](#troubleshooting-common-issues)
- [FAQ](#faq)

---

## Overview: Two-Mode Architecture

Health Agent uses a **two-mode architecture** that separates production from development to enable fast iteration while maintaining stability.

### Why This Architecture?

This follows the established **SCAR pattern**:
- **Databases run in Docker** - Consistent, isolated, easy to reset
- **Application code runs natively during development** - Hot reload, immediate feedback, no rebuild delays

### Architecture Diagrams

```
Production Mode:              Development Mode:
┌─────────────────────┐      ┌─────────────────────┐
│ Docker Container    │      │ Docker Container    │ (still running)
│ health-agent-bot    │      │ health-agent-bot    │
│ (Telegram Bot)      │      │ (Telegram Bot)      │
│ RUN_MODE=bot        │      │ RUN_MODE=bot        │
└──────────┬──────────┘      └─────────────────────┘
           │
           │ connects to          ┌─────────────────────┐
           │                      │ Native Python       │
           ▼                      │ API Server          │
┌─────────────────────┐      ┌───┤ (Development)       │
│ PostgreSQL          │◄─────┤   │ RUN_MODE=api        │
│ (Docker Container)  │      │   │ localhost:8080      │
│ localhost:5436      │      │   └─────────────────────┘
└─────────────────────┘      │
                             │
                        ┌────▼────────────────────┐
                        │ PostgreSQL              │
                        │ (Docker Container)      │
                        │ localhost:5436          │
                        └─────────────────────────┘
```

### Key Concepts

**Production Mode:**
- Telegram bot runs in Docker (`health-agent-bot` container)
- PostgreSQL runs in Docker (always running)
- Database exposed on `localhost:5436` for native development access
- Used for: Stable production deployment, user-facing bot

**Development Mode:**
- Production bot stays running (prevents Telegram API conflicts)
- Developer runs API server natively: `RUN_MODE=api python -m src.main`
- Code changes are picked up immediately (hot reload)
- Used for: Feature development, SCAR testing, rapid iteration

**Why No Docker for Development API?**
- Docker requires rebuild for every code change (slow)
- Native Python picks up changes instantly (fast)
- SCAR/developers test via REST API, need immediate feedback
- No Telegram bot conflicts (only one bot instance allowed by Telegram)

---

## Quick Start for Experienced Developers

**TL;DR:** Databases in Docker, application native for dev work.

```bash
# 1. Clone and install
git clone <repo-url>
cd health-agent
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env: Add your TELEGRAM_BOT_TOKEN, ALLOWED_TELEGRAM_IDS, API keys

# 3. Start production services (PostgreSQL + Telegram bot)
docker compose up -d postgres health-agent-bot

# 4. Develop natively with hot reload
RUN_MODE=api python -m src.main

# 5. Test your changes
curl http://localhost:8080/api/health
```

**That's it!** Production bot handles Telegram, you develop via REST API.

---

## Production Mode Setup

Production mode runs the Telegram bot in Docker for stable, always-on operation.

### Prerequisites

- Docker and Docker Compose installed
- Telegram bot token (from [@BotFather](https://t.me/botfather))
- Your Telegram user ID (from [@userinfobot](https://t.me/userinfobot))

### Step-by-Step Setup

**1. Configure Environment**

```bash
# Copy example configuration
cp .env.example .env

# Edit .env and set required values:
# - TELEGRAM_BOT_TOKEN=<your_bot_token>
# - ALLOWED_TELEGRAM_IDS=<your_telegram_user_id>
# - OPENAI_API_KEY or ANTHROPIC_API_KEY for vision AI
```

**2. Start Production Services**

```bash
# Start PostgreSQL and Telegram bot
docker compose up -d postgres health-agent-bot

# Verify both services are running
docker compose ps

# Expected output:
# NAME                  STATUS
# postgres              Up (healthy)
# health-agent-bot      Up
```

**3. Verify Bot is Working**

```bash
# Check bot logs
docker compose logs -f health-agent-bot

# Should see:
# "Running in BOT mode (Telegram bot only)"
# "Bot started successfully"

# Test in Telegram
# Send /start to your bot - you should get a response
```

**4. Verify Database Connection**

```bash
# Connect to PostgreSQL from host
PGPASSWORD=postgres psql -h localhost -p 5436 -U postgres -d health_agent -c "\dt"

# Should show tables: users, etc.
```

### Production Mode Configuration

**docker-compose.yml settings:**
- `health-agent-bot` container runs with `RUN_MODE=bot`
- `postgres` container exposes port `5436:5432`
- Data persists in Docker volume `postgres_data`
- Logs and data stored in `./production/` directory

**When to use Production Mode:**
- Deploying to a server
- Running the bot for actual users
- CI/CD testing
- Long-running stable operation

---

## Development Mode Setup

Development mode runs the API server natively for rapid iteration during feature development.

### Prerequisites

- Production mode already running (PostgreSQL + Telegram bot)
- Python 3.11+ with virtual environment
- Dependencies installed (`pip install -r requirements.txt`)

### Step-by-Step Setup

**1. Ensure Production Services are Running**

```bash
# Check PostgreSQL and bot are running
docker compose ps

# If not running, start them:
docker compose up -d postgres health-agent-bot
```

**2. Activate Python Virtual Environment**

```bash
# Linux/Mac
source .venv/bin/activate

# Windows
.venv\Scripts\activate

# Verify Python version
python --version  # Should be 3.11+
```

**3. Run API Server Natively**

```bash
# Start API server in development mode
RUN_MODE=api python -m src.main

# You should see:
# "Running in API mode (REST API only)"
# "API server started on http://0.0.0.0:8080"
```

**4. Test API Endpoints**

```bash
# Health check
curl http://localhost:8080/api/health

# Expected response:
# {"status":"healthy","timestamp":"..."}

# Test authenticated endpoint (requires API key from .env)
curl -H "X-API-Key: test_key_123" http://localhost:8080/api/user/123456789
```

**5. Make Code Changes and Test**

When you modify code in `src/`, the changes are picked up immediately:
- **FastAPI auto-reload:** API server restarts automatically
- **No Docker rebuild needed:** Changes are instant
- **Test immediately:** Make change → save file → test API

### Development Workflow Example

```bash
# 1. Start dev API (if not already running)
RUN_MODE=api python -m src.main

# 2. In another terminal, make changes to code
# Edit src/api/endpoints.py or any source file

# 3. Save the file - API auto-restarts
# Watch the API terminal for "Application startup complete"

# 4. Test your changes immediately
curl -H "X-API-Key: test_key_123" http://localhost:8080/api/your-new-endpoint

# 5. Iterate: Change code → Save → Test → Repeat
```

### Why Native Development?

**Benefits:**
- ✅ **Instant feedback:** Code changes picked up in < 1 second
- ✅ **No rebuild delays:** No `docker build` step (can take 30-60 seconds)
- ✅ **Easy debugging:** Attach debugger directly to Python process
- ✅ **IDE integration:** Full code intelligence, breakpoints, etc.
- ✅ **Hot reload:** FastAPI automatically restarts on file changes

**Compared to Docker:**
- ❌ Docker requires rebuild for every change
- ❌ Docker restart takes 10-30 seconds
- ❌ Docker logs are less convenient
- ❌ Docker debugging requires extra setup

---

## SCAR Integration Workflow

SCAR (Sam's Coding Agent Remote) uses the REST API for testing implementations in isolated GitHub issue worktrees.

### How SCAR Works with Health Agent

**SCAR Development Process:**

1. **GitHub Issue Created:** Developer creates issue describing feature/bug
2. **SCAR Mentions in Issue:** Mention SCAR in GitHub issue comments
3. **Isolated Worktree:** SCAR creates isolated worktree: `~/.archon/worktrees/health-agent-issue-<number>`
4. **Native API Testing:** SCAR runs `RUN_MODE=api python -m src.main` in worktree
5. **Iterative Development:** SCAR makes changes, tests via API, iterates
6. **Pull Request:** Once complete, SCAR creates PR from feature branch

### Why SCAR Needs Native API

SCAR benefits from **hot reload** during iterative development:

```bash
# SCAR's workflow (simplified):
cd ~/.archon/worktrees/health-agent-issue-42

# Start API server
RUN_MODE=api python -m src.main &

# Make code changes
# Edit src/api/endpoints.py - add new feature

# Test immediately (no rebuild needed!)
curl -H "X-API-Key: scar_key_456" http://localhost:8080/api/new-feature

# If test fails, edit code again
# Change is picked up instantly

# Iterate until tests pass, then commit
```

**Without native API (using Docker):**
```bash
# Make change → docker build → docker compose up → test (60+ seconds)
# vs
# Make change → save → test (1 second)
```

### Testing SCAR Implementations

When SCAR creates a PR, test the changes:

```bash
# 1. Checkout the PR branch
git fetch origin
git checkout feature-branch-name

# 2. Start API in development mode
RUN_MODE=api python -m src.main

# 3. Test the new endpoints
curl -H "X-API-Key: test_key_123" http://localhost:8080/api/the-new-feature

# 4. Verify changes work as expected
# Run pytest if tests are included
pytest tests/
```

### SCAR API Key

SCAR uses dedicated API key for authentication:
```bash
# In .env:
API_KEYS=test_key_123,scar_key_456,po_key_789

# SCAR uses: scar_key_456
# You can use: test_key_123
```

---

## Docker vs Native: Decision Matrix

When should you use Docker vs native Python?

### Use Docker When:

| Scenario | Why Docker? |
|----------|-------------|
| **Production deployment** | Isolated, reproducible environment |
| **Running Telegram bot** | Needs to stay running 24/7 |
| **CI/CD pipeline** | Consistent testing environment |
| **Database (PostgreSQL)** | Easy setup, isolated data, easy reset |
| **First-time setup** | Get everything running quickly |

### Use Native Python When:

| Scenario | Why Native? |
|----------|-------------|
| **API development** | Hot reload, instant feedback |
| **SCAR testing** | Rapid iteration on GitHub issues |
| **Debugging** | Direct debugger access |
| **Testing changes** | No rebuild delay |
| **Learning codebase** | Full IDE integration |

### Port Reference Table

| Service | Container Port | Host Port | Connect From Native |
|---------|---------------|-----------|---------------------|
| PostgreSQL | 5432 | 5436 | `localhost:5436` |
| API Server (Docker) | 8080 | 8080 | `localhost:8080` |
| API Server (Native) | 8080 | 8080 | `localhost:8080` |

**Important:**
- Native development connects to PostgreSQL via `localhost:5436`
- Docker containers connect internally via `postgres:5432`
- API server (native or Docker) runs on `localhost:8080`

---

## Troubleshooting Common Issues

### Error: "Conflict: terminated by other getUpdates request"

**Symptom:**
```
telegram.error.Conflict: Conflict: terminated by other getUpdates request
```

**Cause:** Two bot instances running simultaneously (Telegram only allows one)

**Solution:**

```bash
# Check for duplicate bots
docker compose ps | grep health-agent-bot

# Check for native bot process
ps aux | grep "python -m src.main" | grep -v "RUN_MODE=api"

# If duplicate found, stop one:
docker compose stop health-agent-bot
# OR
pkill -f "python -m src.main"

# Then restart the one you want:
docker compose up -d health-agent-bot  # For production
# OR
RUN_MODE=bot python -m src.main  # For development (not recommended)
```

**Prevention:** Always use `RUN_MODE=api` for native development, leave bot in Docker.

### Error: "Connection refused" (Database)

**Symptom:**
```
psycopg.OperationalError: connection refused
```

**Cause:** PostgreSQL container not running

**Solution:**

```bash
# Check if PostgreSQL is running
docker compose ps postgres

# If not running, start it:
docker compose up -d postgres

# Wait for it to be healthy (5-10 seconds)
docker compose ps postgres
# STATUS should show "Up (healthy)"

# Verify connection
PGPASSWORD=postgres psql -h localhost -p 5436 -U postgres -d health_agent -c "SELECT 1;"
```

### Error: "ModuleNotFoundError"

**Symptom:**
```
ModuleNotFoundError: No module named 'pydantic_ai'
```

**Cause:** Virtual environment not activated or dependencies not installed

**Solution:**

```bash
# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
# OR
.venv\Scripts\activate  # Windows

# Verify activation (should show .venv path)
which python

# Install/update dependencies
pip install -r requirements.txt

# Verify key packages
pip list | grep -E "(pydantic|fastapi|python-telegram-bot)"
```

### Error: "Address already in use" (Port 8080)

**Symptom:**
```
OSError: [Errno 48] Address already in use
```

**Cause:** Another process using port 8080

**Solution:**

```bash
# Find what's using port 8080
lsof -i :8080
# OR on Linux:
netstat -tulpn | grep :8080

# Kill the process (replace <PID> with actual PID from above)
kill <PID>

# Or stop the Docker API container if running
docker compose stop health-agent-api

# Then start your native API
RUN_MODE=api python -m src.main
```

### Docker Image Has Outdated Code

**Symptom:** Testing in Docker, but recent code changes not reflected

**Cause:** Docker image not rebuilt after code changes

**Solution:**

```bash
# Rebuild the Docker image
docker compose build health-agent-bot

# Restart the container with new image
docker compose up -d health-agent-bot

# Verify new code is running
docker compose logs health-agent-bot | tail -20
```

**Better solution:** Use native development (no rebuilds needed!)

### API Returns 401 Unauthorized

**Symptom:**
```json
{"detail": "Invalid API key"}
```

**Cause:** Missing or incorrect API key in request

**Solution:**

```bash
# Check API keys in .env
grep "^API_KEYS=" .env

# Use one of the configured keys
curl -H "X-API-Key: test_key_123" http://localhost:8080/api/health

# Add new API key if needed (edit .env):
API_KEYS=test_key_123,scar_key_456,your_new_key
```

### Database Schema Out of Date

**Symptom:** API errors mentioning missing columns/tables

**Cause:** Database schema doesn't match current code

**Solution:**

```bash
# Check current schema
PGPASSWORD=postgres psql -h localhost -p 5436 -U postgres -d health_agent -c "\d users"

# If schema is wrong, recreate database:
docker compose down postgres
docker volume rm health-agent_postgres_data  # WARNING: Deletes all data!
docker compose up -d postgres

# Wait for healthy status
docker compose ps postgres

# Schema will be created from migrations on startup
```

---

## FAQ

### Q: Should I run the Telegram bot natively or in Docker?

**A:** **Always use Docker for the Telegram bot** unless you have a specific reason not to.

**Why:**
- Telegram only allows one bot instance (prevents conflicts)
- Bot needs to run 24/7 (Docker handles restarts)
- Development work uses API, not Telegram
- Production and development should use same bot setup

**Exception:** If you're specifically debugging Telegram message handling, you can temporarily stop Docker bot and run natively with `RUN_MODE=bot`.

### Q: Can I run the API in both Docker and natively at the same time?

**A:** No, they'll conflict on port 8080.

**Solution:**
- For development: Use native API (`RUN_MODE=api python -m src.main`)
- For production: Use Docker API (`docker compose up -d health-agent-api`)
- Never run both simultaneously

### Q: How do I reset the database to clean state?

**A:**

```bash
# WARNING: This deletes all data!
docker compose down postgres
docker volume rm health-agent_postgres_data
docker compose up -d postgres
```

### Q: What's the difference between RUN_MODE=bot, api, and both?

**A:**

| RUN_MODE | What Runs | When to Use |
|----------|-----------|-------------|
| `bot` | Telegram bot only | Production bot in Docker (default) |
| `api` | REST API only | Native development, SCAR testing |
| `both` | Telegram bot + REST API | Rare (testing both together) |

**Recommendation:** Use `bot` for Docker container, `api` for native development.

### Q: How do I connect to PostgreSQL from a native Python script?

**A:**

```python
# In your code or .env:
DATABASE_URL = "postgresql://postgres:postgres@localhost:5436/health_agent"

# Note the port: 5436 (host) not 5432 (container internal)
```

### Q: Why is the Docker API container included if we shouldn't use it for development?

**A:** The `health-agent-api` container is included for:
- CI/CD testing (automated tests in isolated environment)
- Production API deployment (if needed separately from bot)
- Deployment testing (verify Docker build works)

For **development**, always use native API for hot reload.

### Q: How do I add a new Python dependency?

**A:**

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Install package
pip install new-package-name

# 3. Update requirements
pip freeze > requirements.txt

# 4. Rebuild Docker image (for production)
docker compose build health-agent-bot

# 5. Restart Docker container
docker compose up -d health-agent-bot
```

### Q: What's the DATA_PATH for user memory files?

**A:**

- **Docker containers:** `/app/data` (mapped to `./production/data` on host)
- **Native development:** `./data` (configured in `.env` via `DATA_PATH=./data`)

User memory markdown files are stored here. Docker and native use separate directories to avoid conflicts.

### Q: How do I view logs?

**A:**

```bash
# Docker bot logs
docker compose logs -f health-agent-bot

# Docker API logs
docker compose logs -f health-agent-api

# PostgreSQL logs
docker compose logs -f postgres

# Native API logs
# Logs print directly to terminal where you ran:
# RUN_MODE=api python -m src.main
```

### Q: Can SCAR and I both work on features simultaneously?

**A:** Yes! SCAR works in isolated worktrees:

```bash
# Your work (main repo):
cd ~/projects/health-agent
RUN_MODE=api python -m src.main  # Port 8080

# SCAR's work (isolated worktree):
cd ~/.archon/worktrees/health-agent-issue-42
# SCAR runs API on different port, or you coordinate

# No conflicts because:
# - Separate code directories
# - Same Docker PostgreSQL (shared data OK)
# - Can use different ports if needed
```

---

## Additional Resources

- **[README.md](README.md)** - Quick start guide and project overview
- **[API_README.md](API_README.md)** - Detailed REST API documentation
- **[.env.example](.env.example)** - All configuration options explained

---

**Happy coding! 🚀**

For questions or issues, create a GitHub issue or consult the troubleshooting section above.
