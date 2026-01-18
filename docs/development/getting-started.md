# Getting Started - Developer Quick Start

Fast-track guide to setting up the Health Agent development environment.

---

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 14+ (via Docker or native)
- Git

---

## Quick Setup (5 Minutes)

### 1. Clone Repository

```bash
git clone https://github.com/gpt153/health-agent.git
cd health-agent
```

### 2. Environment Configuration

```bash
cp .env.example .env
```

Edit `.env` with your keys:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
ALLOWED_TELEGRAM_IDS=your_telegram_id
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql://postgres:password@localhost:5436/health_agent
```

### 3. Start PostgreSQL

```bash
docker compose up -d postgres
```

### 4. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 5. Run Migrations

Migrations auto-run on Docker startup. For native PostgreSQL:
```bash
psql -h localhost -p 5436 -U postgres -d health_agent < migrations/*.sql
```

### 6. Start Development

**Bot mode**:
```bash
export RUN_MODE=bot
python main.py
```

**API mode** (recommended for development):
```bash
export RUN_MODE=api
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8080
```

### 7. Test

```bash
# Unit tests
pytest tests/unit/

# API test
curl http://localhost:8080/health
```

---

## Development Modes

| Mode | Use Case | Command |
|------|----------|---------|
| **Bot** | Manual testing via Telegram | `export RUN_MODE=bot && python main.py` |
| **API** | Fast iteration, automated testing | `export RUN_MODE=api && uvicorn src.api.app:app --reload` |
| **Both** | Special testing scenarios | `export RUN_MODE=both && python main.py` |

---

## Next Steps

- 📖 **Full Guide**: See [DEVELOPMENT.md](../../DEVELOPMENT.md) for comprehensive documentation
- 🧪 **Testing**: [testing.md](testing.md) - Running tests
- 🎨 **Code Style**: [code-style.md](code-style.md) - Style guide
- 🔧 **Adding Features**: [adding-features.md](adding-features.md) - Step-by-step feature development

---

## Common Issues

**Port 5436 already in use**:
```bash
docker compose down
docker compose up -d postgres
```

**Missing API keys**:
Check `.env` file has all required keys (see `.env.example`)

**Database connection refused**:
```bash
docker ps  # Check postgres container is running
docker logs health-agent-db  # Check postgres logs
```

For more troubleshooting: [/docs/troubleshooting/](../troubleshooting/)
