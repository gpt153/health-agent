# ADR-003: Dual-Mode Bot + API Architecture

**Status**: Accepted

**Date**: 2024-11-01

**Deciders**: Health Agent Development Team

---

## Context

The Health Agent needs to serve two distinct use cases:

1. **Production**: Telegram bot for real users tracking health and nutrition
2. **Development/Testing**: REST API for automated testing (SCAR), programmatic access, and future integrations

Key requirements:
- Single codebase (avoid duplication of agent logic)
- Production-ready Telegram bot with Docker deployment
- Developer-friendly API for rapid iteration and testing
- Hot reload for fast development cycles
- Isolated environments (bot and API shouldn't interfere)
- Flexibility to run both modes simultaneously (rare, but useful for testing)

## Decision

Implement a **dual-mode architecture** with a single `RUN_MODE` environment variable that controls which services start:

- **`RUN_MODE=bot`** - Telegram bot only (production)
- **`RUN_MODE=api`** - REST API only (development/testing)
- **`RUN_MODE=both`** - Both services (rare, for special testing scenarios)

Both modes share the same:
- Agent core (PydanticAI agents)
- Database layer (PostgreSQL)
- Memory system (Markdown, Mem0)
- Service layer (vision AI, gamification, reminders)
- Business logic

## Rationale

### Why Dual-Mode?

1. **Avoid Code Duplication**
   - Agent tools defined once, work in both modes
   - Database queries shared across bot and API
   - Vision AI, nutrition consensus, gamification logic unified
   - Bug fixes apply to both modes automatically

2. **Developer Experience**
   - API mode enables fast iteration without Telegram
   - Hot reload in API mode (uvicorn --reload) for instant feedback
   - SCAR (remote coding agent) can test via API
   - Easier to write automated tests (pytest against API)

3. **Production Deployment**
   - Docker runs in `bot` mode for clean production environment
   - No API attack surface in production (security benefit)
   - Simpler resource management (only bot process running)

4. **Flexibility**
   - Can run API locally while bot runs in Docker
   - Future integrations (mobile app, web dashboard) use API mode
   - Testing can spin up API instance without affecting production bot

### Implementation Strategy

**Single entry point with mode detection**:

```python
# main.py
import os
from src.bot import run_bot
from src.api.app import run_api

async def main():
    run_mode = os.getenv("RUN_MODE", "bot")

    if run_mode == "bot":
        await run_bot()
    elif run_mode == "api":
        await run_api()
    elif run_mode == "both":
        # Run both concurrently (rare)
        await asyncio.gather(run_bot(), run_api())
    else:
        raise ValueError(f"Invalid RUN_MODE: {run_mode}")

if __name__ == "__main__":
    asyncio.run(main())
```

**Docker Compose configuration**:

```yaml
services:
  health-agent-bot:
    image: ghcr.io/gpt153/health-agent:latest
    environment:
      RUN_MODE: bot  # Production runs bot only
      DATABASE_URL: postgresql://...
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
    depends_on:
      - postgres

  health-agent-api:
    image: ghcr.io/gpt153/health-agent:latest
    environment:
      RUN_MODE: api  # Development API instance
      DATABASE_URL: postgresql://...
    ports:
      - "8080:8080"
    depends_on:
      - postgres
```

**Local development (native Python)**:

```bash
# Terminal 1: Run bot
export RUN_MODE=bot
python main.py

# Terminal 2: Run API with hot reload
export RUN_MODE=api
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8080
```

## Alternatives Considered

### Alternative 1: Separate Codebases (bot repo + api repo)

**Rejected because**:
- ❌ Code duplication (agent logic, tools, database queries)
- ❌ Bug fixes need to be applied twice
- ❌ Schema changes require coordinating two repositories
- ❌ Shared library approach adds complexity (versioning, publishing)
- ❌ Development velocity decreases (context switching between repos)

**Considered pros**:
- ✅ Clear separation of concerns
- ✅ Independent deployment cycles
- ✅ Easier to scale teams (bot team vs API team)

### Alternative 2: Bot-Only with Programmatic Testing via Telegram

**Rejected because**:
- ❌ Slow iteration (need to interact via Telegram UI)
- ❌ Hard to automate tests (Telegram test clients are clunky)
- ❌ SCAR integration requires Telegram API rate limits
- ❌ Difficult to test concurrency (multiple users)
- ❌ No programmatic access for future integrations

**Considered pros**:
- ✅ Simpler architecture (one interface)
- ✅ Production environment matches testing environment exactly

### Alternative 3: API-Only with Telegram as a Client

**Rejected because**:
- ❌ Telegram bot becomes a thin client (adds latency)
- ❌ More complex deployment (bot client + API server)
- ❌ Network calls between bot and API introduce failure points
- ❌ Harder to debug (distributed system)
- ❌ Overkill for single-user bot (no need for separate API server)

**Considered pros**:
- ✅ API-first design (easier to add more clients later)
- ✅ Bot and API independently scalable
- ✅ Clear separation of presentation and logic

### Alternative 4: Always Run Both (No RUN_MODE)

**Rejected because**:
- ❌ Production bot doesn't need API (attack surface)
- ❌ Wastes resources (API server running but unused)
- ❌ Port conflicts if both try to bind same port
- ❌ Confusing logs (bot and API logs interleaved)

**Considered pros**:
- ✅ Simpler configuration (no mode switching)
- ✅ Maximum flexibility

## Implementation Details

### Shared Agent Core

```python
# src/agent/__init__.py
from pydantic_ai import Agent

# Agents defined once, used by both bot and API
claude_agent = Agent(
    model="claude-3-5-sonnet-20241022",
    system_prompt=SYSTEM_PROMPT,
    deps_type=AgentDeps,
    retries=2
)

gpt_agent = Agent(
    model="openai:gpt-4o",
    system_prompt=SYSTEM_PROMPT,
    deps_type=AgentDeps,
    retries=2
)

# Tools registered on both agents
@claude_agent.tool()
@gpt_agent.tool()
async def save_food_entry(ctx: RunContext[AgentDeps], ...) -> str:
    # Business logic here (shared across bot and API)
    ...
```

### Bot Implementation

```python
# src/bot.py
from telegram.ext import Application, MessageHandler, filters
from src.agent import claude_agent, gpt_agent

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming Telegram messages."""
    user_message = update.message.text
    user_id = str(update.effective_user.id)

    # Use shared agent
    result = await claude_agent.run_sync(
        user_message,
        deps={
            "user_id": user_id,
            "db_manager": db_manager,
            # ... other services
        }
    )

    await update.message.reply_text(result.data)

async def run_bot():
    """Start Telegram bot."""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    await app.run_polling()
```

### API Implementation

```python
# src/api/app.py
from fastapi import FastAPI, HTTPException
from src.agent import claude_agent, gpt_agent

app = FastAPI(title="Health Agent API")

@app.post("/chat")
async def chat(request: ChatRequest):
    """Chat endpoint - mirrors Telegram bot functionality."""
    result = await claude_agent.run_sync(
        request.message,
        deps={
            "user_id": request.user_id,
            "db_manager": db_manager,
            # ... same services as bot
        }
    )

    return {"response": result.data}

async def run_api():
    """Start FastAPI server."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

### Mode Detection in Configuration

```python
# src/config.py
import os

RUN_MODE = os.getenv("RUN_MODE", "bot")

# Validate mode
if RUN_MODE not in ["bot", "api", "both"]:
    raise ValueError(f"Invalid RUN_MODE: {RUN_MODE}. Must be 'bot', 'api', or 'both'")

# Mode-specific configuration
if RUN_MODE in ["bot", "both"]:
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        raise ValueError("TELEGRAM_BOT_TOKEN required for bot mode")

if RUN_MODE in ["api", "both"]:
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", 8080))
```

## Consequences

### Positive

✅ **Single Codebase** - Agent logic, tools, business logic shared across modes
✅ **Fast Development** - API mode with hot reload enables rapid iteration
✅ **Easy Testing** - SCAR and pytest use API for automated testing
✅ **Production-Ready** - Docker runs bot mode for clean deployment
✅ **Future-Proof** - API ready for mobile app, web dashboard integrations
✅ **Developer Experience** - Choose mode based on workflow (bot for manual testing, API for automation)
✅ **Security** - Production bot doesn't expose API endpoints

### Negative

⚠️ **Configuration Complexity** - Need to set RUN_MODE correctly for each environment
⚠️ **Mode Awareness** - Developers need to understand which mode to use when
⚠️ **Testing Gap** - API tests might not catch Telegram-specific issues (e.g., message formatting)
⚠️ **Deployment Variants** - Two deployment configurations (bot vs API) to maintain

### Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Forgot to set RUN_MODE in production | Defaults to "bot" mode (safe default) |
| API exposed in production by mistake | Docker Compose only runs bot mode, doesn't expose API port |
| Telegram-specific bugs missed in API testing | Manual Telegram testing before releases |
| Mode switching breaks one mode | CI/CD tests both modes independently |

## Development Workflow

### Local Development with SCAR

1. SCAR runs `RUN_MODE=api` for testing
2. Makes HTTP requests to `http://localhost:8080/chat`
3. Validates responses programmatically
4. No need to interact with Telegram

**Example SCAR test**:
```python
# scripts/scar_test_agent.py
async def test_food_logging():
    response = await client.post("/chat", json={
        "user_id": "test_user",
        "message": "I ate 200g chicken breast and 150g rice"
    })
    assert "saved" in response.json()["response"].lower()
```

### Manual Testing

1. Developer sets `RUN_MODE=bot`
2. Runs bot locally
3. Tests via real Telegram messages
4. Sees real-time responses in Telegram app

### Production Deployment

1. Docker Compose sets `RUN_MODE=bot`
2. Only bot process starts
3. No API endpoints exposed
4. Telegram webhook or polling handles messages

## Performance Characteristics

| Aspect | Bot Mode | API Mode | Both Mode |
|--------|----------|----------|-----------|
| Startup time | ~3s | ~2s | ~4s |
| Memory usage | ~150MB | ~120MB | ~250MB |
| Response latency | 1-3s | 1-3s | 1-3s (concurrent) |
| Concurrent users | High (Telegram async) | Medium (FastAPI async) | Divided |

## Related Decisions

- **ADR-001**: PydanticAI agents work identically in both modes
- **ADR-002**: Three-tier memory accessed the same way in both modes
- See **API_README.md** for detailed API documentation

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [python-telegram-bot Documentation](https://python-telegram-bot.org/)
- Health Agent Implementation: `/src/bot.py`, `/src/api/app.py`

## Revision History

- 2024-10-01: Initial bot-only implementation
- 2024-11-01: API mode added for SCAR testing
- 2024-12-01: RUN_MODE environment variable introduced
- 2025-01-18: Documentation created for Phase 3.7
