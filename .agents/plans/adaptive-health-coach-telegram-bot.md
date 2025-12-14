# Feature: Adaptive AI Health Coach - Telegram Bot

## Feature Description

Build an adaptive AI fitness and nutrition coach via Telegram that learns each user's communication preferences, coaching style, and behavioral patterns to provide a personalized experience that feels like a real friend or coach, not a bot.

The agent stores user memory as human-readable markdown files, analyzes food photos using vision AI to calculate calories and macros, manages dynamic tracking categories (sleep, water, mood, etc.) that users can create on-demand, and sends intelligent reminders at scheduled times.

## User Story

**As a** health-conscious individual
**I want** an AI coach that remembers my goals, analyzes my food intake from photos, and adapts its communication style to me
**So that** I can effortlessly track my nutrition and fitness progress with a personalized coaching experience

## Problem Statement

Existing health tracking apps have high friction (manual calorie entry is tedious), generic one-size-fits-all experiences (no personality adaptation), and rigid feature sets (can't track custom metrics). This leads to user abandonment and failed health goals.

## Solution Statement

Create a Telegram bot powered by PydanticAI that:
- **Learns user preferences** through explicit questions early on and implicit pattern recognition over time
- **Analyzes food photos** using vision AI (GPT-4 Vision) to automatically calculate nutrition
- **Adapts personality** by dynamically generating system prompts based on user preferences stored in markdown files
- **Enables extensibility** through a dynamic tracking system where users can create custom categories via conversation
- **Delivers reminders** using python-telegram-bot's JobQueue for scheduled prompts

## Feature Metadata

**Feature Type**: New Capability (Greenfield Project)
**Estimated Complexity**: High
**Primary Systems Affected**: All (new codebase)
**Dependencies**:
- pydantic-ai (AI agent framework)
- python-telegram-bot[job-queue] (Telegram integration + scheduling)
- psycopg[binary] (PostgreSQL driver)
- openai OR anthropic (Vision AI)
- python-dotenv (env management)

**Archon Project**:
- Project ID: `9dc800ba-8a16-40e1-a7ea-f8100e493404`
- Project Name: Health Agent - Adaptive AI Health Coach
- Repository Path: `/home/samuel/workspace/health-agent`
- Task Tracking: Enabled (28 tasks created)

---

## CONTEXT REFERENCES

### Relevant Codebase Files

**IMPORTANT**: This is a greenfield project. Currently only `README.md` exists at `/home/samuel/workspace/health-agent/README.md`.

### New Files to Create

**Core Application:**
- `src/main.py` - Application entry point, initializes bot and database
- `src/bot.py` - Telegram bot setup with handlers
- `src/agent.py` - PydanticAI agent logic and tool definitions
- `src/config.py` - Configuration management and environment variables

**Memory System:**
- `src/memory/file_manager.py` - Read/write markdown memory files
- `src/memory/system_prompt.py` - Dynamic system prompt generation
- `src/memory/templates.py` - Default markdown templates

**Handlers:**
- `src/handlers/message_handler.py` - Route messages to appropriate handlers
- `src/handlers/food_photo.py` - Food photo analysis workflow
- `src/handlers/tracking.py` - Dynamic tracking system logic
- `src/handlers/settings.py` - Chat-based settings management
- `src/handlers/transparency.py` - "What do you know about me?" feature

**Models:**
- `src/models/user.py` - User profile Pydantic models
- `src/models/food.py` - Food entry Pydantic models
- `src/models/tracking.py` - Tracking category/entry Pydantic models
- `src/models/reminder.py` - Reminder Pydantic models

**Database:**
- `src/db/connection.py` - PostgreSQL connection pool
- `src/db/queries.py` - Database operations (CRUD)
- `migrations/001_initial_schema.sql` - Database schema

**Scheduler:**
- `src/scheduler/reminder_manager.py` - Reminder execution logic using JobQueue

**Utilities:**
- `src/utils/vision.py` - Vision LLM integration (GPT-4V or Claude)
- `src/utils/nutrition.py` - Nutrition calculation helpers
- `src/utils/auth.py` - Telegram ID whitelist validation

**Tests:**
- `tests/test_memory.py` - Memory system tests
- `tests/test_food_analysis.py` - Food photo analysis tests
- `tests/test_tracking.py` - Dynamic tracking tests
- `tests/test_database.py` - Database operations tests

**Configuration:**
- `requirements.txt` - Python dependencies
- `.env.example` - Environment variable template
- `Dockerfile` - Container definition
- `docker-compose.yml` - Multi-container orchestration
- `pyproject.toml` - Python project configuration
- `.gitignore` - Git ignore patterns

### Relevant Documentation (MUST READ BEFORE IMPLEMENTING)

**PydanticAI:**
- [PydanticAI Official Documentation](https://ai.pydantic.dev/)
  - Section: [Agents](https://ai.pydantic.dev/agents/) - Agent creation, configuration, dependencies
  - Section: [Tools](https://ai.pydantic.dev/tools/) - @agent.tool and @agent.tool_plain decorators
  - Why: Core framework for AI agent logic with structured outputs

**python-telegram-bot:**
- [python-telegram-bot v22.5 Documentation](https://docs.python-telegram-bot.org/)
  - Section: [JobQueue](https://docs.python-telegram-bot.org/en/stable/telegram.ext.jobqueue.html) - Scheduling with APScheduler
  - Section: [Tutorial: Your First Bot](https://docs.python-telegram-bot.org/) - Async handler patterns
  - Why: Telegram bot framework (v20+ is fully async), includes scheduling

**Vision AI:**
- [OpenAI Vision API Documentation](https://platform.openai.com/docs/guides/vision)
  - Section: Image inputs and prompts
  - Why: Food photo analysis (~$0.003 per image with gpt-4o-mini)
- [Build Your Own Food Tracker with OpenAI Platform](https://dev.to/frosnerd/build-your-own-food-tracker-with-openai-platform-55n8)
  - Why: Practical food recognition implementation guide

**PostgreSQL JSONB:**
- [PostgreSQL JSONB Documentation](https://www.postgresql.org/docs/current/datatype-json.html)
  - Section: JSONB operators (@>, ->, ->>)
  - Why: Flexible storage for dynamic tracking data
- [How to Query JSONB in PostgreSQL](https://www.tigerdata.com/learn/how-to-query-jsonb-in-postgresql)
  - Section: Indexing and query patterns
  - Why: Efficient querying of flexible data

**psycopg3:**
- [psycopg3 JSON Adaptation](https://www.psycopg.org/psycopg3/docs/api/types.html)
  - Section: JSON/JSONB type adapters
  - Why: Seamless Python dict ↔ PostgreSQL JSONB conversion

### Patterns to Follow

**Project Structure Pattern (Python Best Practices):**
```
health-agent/
├── src/                    # Source code
├── tests/                  # Test files mirror src/
├── migrations/             # SQL migrations
├── data/                   # Local storage (gitignored)
├── requirements.txt        # Dependencies
├── pyproject.toml          # Project config
└── Dockerfile              # Container
```

**Async/Await Pattern (python-telegram-bot v22.5):**
```python
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    await update.message.reply_text("Hello!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user messages"""
    user_id = str(update.effective_user.id)
    text = update.message.text
    # Process with PydanticAI agent
    response = await agent.run(text, deps={"user_id": user_id})
    await update.message.reply_text(response.data)

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
```

**PydanticAI Agent Pattern:**
```python
from pydantic_ai import Agent
from pydantic import BaseModel

class AgentDeps(BaseModel):
    user_id: str
    user_memory: dict

agent = Agent(
    "openai:gpt-4",  # or "anthropic:claude-3-5-sonnet-latest"
    deps_type=AgentDeps,
    system_prompt="You are a friendly fitness coach..."
)

@agent.tool
async def save_to_memory(ctx: RunContext[AgentDeps], key: str, value: str) -> str:
    """Save information to user memory"""
    user_id = ctx.deps.user_id
    # Update memory file
    return f"Saved {key} to memory"

result = await agent.run(
    "Tell me about my goals",
    deps=AgentDeps(user_id="123", user_memory={...})
)
```

**Memory File Pattern (Markdown):**
```markdown
# User Profile: {user_name}

## Physical Stats
- Age: 32
- Height: 180cm
- Current Weight: 85kg (as of 2024-12-14)
- Target Weight: 75kg

## Goals
- Primary: Lose 10kg over 6 months
- Secondary: Maintain muscle mass
```

**Database Connection Pattern (psycopg3 async):**
```python
import psycopg
from psycopg.rows import dict_row

async def get_db_connection():
    return await psycopg.AsyncConnection.connect(
        DATABASE_URL,
        row_factory=dict_row
    )

async def save_food_entry(user_id: str, foods: list, total_calories: int):
    async with await get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO food_entries (user_id, foods, total_calories, total_macros)
                VALUES (%s, %s, %s, %s)
                """,
                (user_id, json.dumps(foods), total_calories, {...})
            )
            await conn.commit()
```

**JobQueue Pattern (Reminders):**
```python
from telegram.ext import Application, ContextTypes

async def send_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send scheduled reminder to user"""
    job = context.job
    user_id = job.data["user_id"]
    message = job.data["message"]
    await context.bot.send_message(chat_id=user_id, text=message)

# Schedule daily reminder
app.job_queue.run_daily(
    send_reminder,
    time=datetime.time(hour=21, minute=0),  # 9pm
    data={"user_id": "123", "message": "Time to drink water!"}
)
```

**Error Handling Pattern:**
```python
import logging

logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Process message
        result = await agent.run(text, deps=deps)
        await update.message.reply_text(result.data)
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        await update.message.reply_text(
            "Sorry, I encountered an error. Please try again."
        )
```

**Type Hints Pattern (Strict):**
```python
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class FoodItem(BaseModel):
    name: str
    quantity: str
    calories: int
    macros: Dict[str, float]  # {"protein": 20.5, "carbs": 40.0, "fat": 10.0}

async def analyze_food_photo(photo_path: str) -> List[FoodItem]:
    """Analyze food photo and return nutrition info"""
    # Vision AI logic
    return [FoodItem(...), ...]
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation (Project Setup)

Set up the Python project structure, dependencies, database, and basic configuration before implementing any features.

**Tasks:**
1. Initialize Python project with proper structure
2. Configure PostgreSQL database with initial schema
3. Set up environment configuration
4. Create base models and types

### Phase 2: Core Infrastructure

Build the core infrastructure components: Telegram bot, PydanticAI agent, memory system, and database layer.

**Tasks:**
1. Implement Telegram bot with authentication
2. Create PydanticAI agent with basic conversation
3. Build memory file system (read/write markdown)
4. Implement database connection and queries

### Phase 3: Feature Implementation

Implement the four core features: adaptive personality, food photo analysis, reminders, and dynamic tracking.

**Tasks:**
1. Implement adaptive personality system
2. Build food photo analysis pipeline
3. Create reminder system with JobQueue
4. Implement dynamic tracking system

### Phase 4: Testing & Validation

Write comprehensive tests and validate the entire system end-to-end.

**Tasks:**
1. Write unit tests for all components
2. Create integration tests
3. Manual validation with real Telegram bot
4. Performance and cost optimization

---

## STEP-BY-STEP TASKS

### Phase 1: Foundation

#### Task 1.1: CREATE project structure

**IMPLEMENT:**
```bash
cd /home/samuel/workspace/health-agent

mkdir -p src/{memory,handlers,models,db,scheduler,utils}
mkdir -p tests/{unit,integration}
mkdir -p migrations
mkdir -p data/users  # Will be gitignored

touch src/__init__.py
touch src/{main,bot,agent,config}.py
touch src/memory/{__init__,file_manager,system_prompt,templates}.py
touch src/handlers/{__init__,message_handler,food_photo,tracking,settings,transparency}.py
touch src/models/{__init__,user,food,tracking,reminder}.py
touch src/db/{__init__,connection,queries}.py
touch src/scheduler/{__init__,reminder_manager}.py
touch src/utils/{__init__,vision,nutrition,auth}.py
```

**VALIDATE:**
```bash
cd /home/samuel/workspace/health-agent && \
tree src -I '__pycache__' && \
ls -la migrations/ && \
ls -la data/
```

**Expected**: Clean directory structure with all placeholder files

---

#### Task 1.2: CREATE requirements.txt

**IMPLEMENT:**
```txt
# AI Framework
pydantic-ai>=0.0.14
pydantic>=2.0.0

# Telegram Bot
python-telegram-bot[job-queue]>=22.5

# Database
psycopg[binary]>=3.1.0

# Vision AI (choose one or both)
openai>=1.0.0
anthropic>=0.40.0

# Utilities
python-dotenv>=1.0.0
pillow>=10.0.0  # Image processing

# Development
pytest>=8.0.0
pytest-asyncio>=0.24.0
mypy>=1.13.0
ruff>=0.8.0
black>=24.0.0
```

**VALIDATE:**
```bash
cd /home/samuel/workspace/health-agent && cat requirements.txt | wc -l
```

**Expected**: File exists with ~20 lines

---

#### Task 1.3: CREATE pyproject.toml

**IMPLEMENT:**
```toml
[project]
name = "health-agent"
version = "0.1.0"
description = "Adaptive AI health coach via Telegram"
requires-python = ">=3.11"
dependencies = [
    "pydantic-ai>=0.0.14",
    "python-telegram-bot[job-queue]>=22.5",
    "psycopg[binary]>=3.1.0",
]

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E", "F", "I", "N", "W", "UP"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
```

**VALIDATE:**
```bash
cd /home/samuel/workspace/health-agent && python3 -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb'))" && echo "Valid TOML"
```

**Expected**: "Valid TOML" output

---

#### Task 1.4: CREATE .env.example

**IMPLEMENT:**
```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
ALLOWED_TELEGRAM_IDS=123456789,987654321

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/health_agent

# Vision AI (choose one or both)
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=sk-ant-...

# Model Selection (openai:gpt-4o-mini or anthropic:claude-3-5-sonnet-latest)
VISION_MODEL=openai:gpt-4o-mini
AGENT_MODEL=anthropic:claude-3-5-sonnet-latest

# Storage
DATA_PATH=./data

# Logging
LOG_LEVEL=INFO
```

**VALIDATE:**
```bash
cd /home/samuel/workspace/health-agent && cat .env.example | grep -c "="
```

**Expected**: 8+ environment variables defined

---

#### Task 1.5: UPDATE .gitignore

**IMPLEMENT:**
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
dist/
*.egg-info/

# Environment
.env

# Data (user privacy)
data/

# IDE
.vscode/
.idea/
*.swp

# Testing
.coverage
.pytest_cache/
htmlcov/

# OS
.DS_Store
Thumbs.db
```

**VALIDATE:**
```bash
cd /home/samuel/workspace/health-agent && git check-ignore data/ .env
```

**Expected**: Both paths are ignored

---

#### Task 1.6: CREATE migrations/001_initial_schema.sql

**IMPLEMENT:**
```sql
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Food entries table
CREATE TABLE IF NOT EXISTS food_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    photo_path VARCHAR(500),
    foods JSONB NOT NULL,              -- [{name, quantity, calories, macros}]
    total_calories INTEGER,
    total_macros JSONB,                -- {protein, carbs, fat}
    meal_type VARCHAR(50),             -- breakfast/lunch/dinner/snack
    notes TEXT
);

-- Reminders table
CREATE TABLE IF NOT EXISTS reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    reminder_type VARCHAR(50) NOT NULL,  -- "simple", "tracking_prompt"
    message TEXT NOT NULL,
    schedule JSONB NOT NULL,             -- {type: "daily", time: "21:00", days: [0,1,2,3,4,5,6]}
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tracking categories table
CREATE TABLE IF NOT EXISTS tracking_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    fields JSONB NOT NULL,               -- Field definitions with types
    schedule JSONB,                      -- When to prompt for data
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, name)
);

-- Tracking entries table
CREATE TABLE IF NOT EXISTS tracking_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES tracking_categories(id) ON DELETE CASCADE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data JSONB NOT NULL,                 -- Actual tracked data
    notes TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_food_entries_user_timestamp ON food_entries(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_food_entries_foods ON food_entries USING GIN(foods);
CREATE INDEX IF NOT EXISTS idx_tracking_entries_user_timestamp ON tracking_entries(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_tracking_entries_data ON tracking_entries USING GIN(data);
CREATE INDEX IF NOT EXISTS idx_reminders_user_active ON reminders(user_id, active);

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

**PATTERN**: PostgreSQL best practices with JSONB indexing
**GOTCHA**: GIN indexes are essential for JSONB query performance

**VALIDATE:**
```bash
cd /home/samuel/workspace/health-agent && psql $DATABASE_URL -c "\dt" 2>&1 | grep -q "Did you mean" && echo "Need to run migration" || echo "Migration ready"
```

**Expected**: "Migration ready" or "Need to run migration"

---

#### Task 1.7: CREATE docker-compose.yml

**IMPLEMENT:**
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: health_agent
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./migrations:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  app:
    build: .
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/health_agent
      DATA_PATH: /app/data
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    restart: unless-stopped

volumes:
  postgres_data:
```

**VALIDATE:**
```bash
cd /home/samuel/workspace/health-agent && docker-compose config -q && echo "Valid compose file"
```

**Expected**: "Valid compose file"

---

#### Task 1.8: CREATE Dockerfile

**IMPLEMENT:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY migrations/ ./migrations/

# Create data directory
RUN mkdir -p /app/data/users

# Run application
CMD ["python", "-m", "src.main"]
```

**VALIDATE:**
```bash
cd /home/samuel/workspace/health-agent && docker build -t health-agent-test . --dry-run 2>&1 | grep -q "unknown flag" && echo "Build syntax valid" || docker build -t health-agent-test . --quiet && echo "Build successful"
```

**Expected**: Build succeeds or syntax is valid

---

### Phase 2: Core Infrastructure

#### Task 2.1: CREATE src/config.py

**IMPLEMENT:**
```python
"""Configuration management"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_TELEGRAM_IDS: list[str] = os.getenv("ALLOWED_TELEGRAM_IDS", "").split(",")

# Database
DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/health_agent")

# AI Models
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
VISION_MODEL: str = os.getenv("VISION_MODEL", "openai:gpt-4o-mini")
AGENT_MODEL: str = os.getenv("AGENT_MODEL", "anthropic:claude-3-5-sonnet-latest")

# Storage
DATA_PATH: Path = Path(os.getenv("DATA_PATH", "./data"))

# Logging
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# Validation
def validate_config() -> None:
    """Validate required configuration"""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is required")
    if not ALLOWED_TELEGRAM_IDS or ALLOWED_TELEGRAM_IDS == [""]:
        raise ValueError("ALLOWED_TELEGRAM_IDS is required")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is required")
    if not OPENAI_API_KEY and not ANTHROPIC_API_KEY:
        raise ValueError("Either OPENAI_API_KEY or ANTHROPIC_API_KEY is required")
```

**VALIDATE:**
```bash
cd /home/samuel/workspace/health-agent && python3 -c "from src.config import validate_config; print('Config module loaded')"
```

**Expected**: "Config module loaded" (may error on missing .env, which is fine)

---

#### Task 2.2: CREATE src/models/user.py

**IMPLEMENT:**
```python
"""User-related Pydantic models"""
from typing import Optional
from pydantic import BaseModel, Field


class UserPreferences(BaseModel):
    """User preference settings"""
    brevity: str = "medium"  # brief, medium, detailed
    tone: str = "friendly"  # friendly, formal, casual
    humor: bool = True
    coaching_style: str = "supportive"  # supportive, analytical, tough_love
    wants_daily_summary: bool = False
    wants_proactive_checkins: bool = False


class UserProfile(BaseModel):
    """User profile information"""
    telegram_id: str
    name: Optional[str] = None
    age: Optional[int] = None
    height_cm: Optional[float] = None
    current_weight_kg: Optional[float] = None
    target_weight_kg: Optional[float] = None
    goal_type: Optional[str] = None  # lose_weight, gain_muscle, maintain
    preferences: UserPreferences = Field(default_factory=UserPreferences)


class UserMemory(BaseModel):
    """Complete user memory (from markdown files)"""
    telegram_id: str
    profile: dict  # Parsed from profile.md
    preferences: dict  # Parsed from preferences.md
    patterns: dict  # Parsed from patterns.md
    recent_foods: list  # Parsed from food_history.md
```

**VALIDATE:**
```bash
cd /home/samuel/workspace/health-agent && python3 -c "from src.models.user import UserProfile; u = UserProfile(telegram_id='123'); print(f'Default preferences: {u.preferences.brevity}')"
```

**Expected**: "Default preferences: medium"

---

#### Task 2.3: CREATE src/models/food.py

**IMPLEMENT:**
```python
"""Food-related Pydantic models"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class FoodMacros(BaseModel):
    """Macronutrient breakdown"""
    protein: float  # grams
    carbs: float  # grams
    fat: float  # grams


class FoodItem(BaseModel):
    """Individual food item"""
    name: str
    quantity: str  # "1 cup", "100g", "1 medium apple"
    calories: int
    macros: FoodMacros


class FoodEntry(BaseModel):
    """Complete food log entry"""
    id: UUID = Field(default_factory=uuid4)
    user_id: str  # telegram_id
    timestamp: datetime = Field(default_factory=datetime.now)
    photo_path: Optional[str] = None
    foods: list[FoodItem]
    total_calories: int
    total_macros: FoodMacros
    meal_type: Optional[str] = None  # breakfast, lunch, dinner, snack
    notes: Optional[str] = None


class VisionAnalysisResult(BaseModel):
    """Result from vision AI food analysis"""
    foods: list[FoodItem]
    confidence: str  # high, medium, low
    clarifying_questions: list[str] = Field(default_factory=list)
```

**VALIDATE:**
```bash
cd /home/samuel/workspace/health-agent && python3 -c "from src.models.food import FoodEntry, FoodItem, FoodMacros; print('Food models loaded')"
```

**Expected**: "Food models loaded"

---

#### Task 2.4: CREATE src/models/tracking.py

**IMPLEMENT:**
```python
"""Dynamic tracking models"""
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class TrackingField(BaseModel):
    """Field definition for tracking category"""
    type: str  # time, number, text, rating
    label: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    required: bool = True


class TrackingSchedule(BaseModel):
    """Schedule for prompting user"""
    type: str  # daily, weekly, monthly, custom
    time: str  # "08:00", "21:00"
    days: list[int] = Field(default_factory=lambda: list(range(7)))  # 0=Monday
    message: str


class TrackingCategory(BaseModel):
    """User-defined tracking category"""
    id: UUID = Field(default_factory=uuid4)
    user_id: str
    name: str
    fields: dict[str, TrackingField]
    schedule: Optional[TrackingSchedule] = None
    active: bool = True


class TrackingEntry(BaseModel):
    """Entry in a tracking category"""
    id: UUID = Field(default_factory=uuid4)
    user_id: str
    category_id: UUID
    timestamp: datetime = Field(default_factory=datetime.now)
    data: dict[str, Any]  # Flexible data storage
    notes: Optional[str] = None
```

**VALIDATE:**
```bash
cd /home/samuel/workspace/health-agent && python3 -c "from src.models.tracking import TrackingCategory, TrackingField; print('Tracking models loaded')"
```

**Expected**: "Tracking models loaded"

---

#### Task 2.5: CREATE src/models/reminder.py

**IMPLEMENT:**
```python
"""Reminder models"""
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class ReminderSchedule(BaseModel):
    """Reminder schedule configuration"""
    type: str  # daily, weekly, once
    time: str  # "21:00"
    days: list[int] = Field(default_factory=lambda: list(range(7)))  # 0-6


class Reminder(BaseModel):
    """Reminder configuration"""
    id: UUID = Field(default_factory=uuid4)
    user_id: str
    reminder_type: str  # simple, tracking_prompt
    message: str
    schedule: ReminderSchedule
    active: bool = True
    tracking_category_id: Optional[UUID] = None  # If tracking_prompt type
```

**VALIDATE:**
```bash
cd /home/samuel/workspace/health-agent && python3 -c "from src.models.reminder import Reminder, ReminderSchedule; print('Reminder models loaded')"
```

**Expected**: "Reminder models loaded"

---

#### Task 2.6: CREATE src/db/connection.py

**IMPLEMENT:**
```python
"""Database connection management"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import psycopg
from psycopg.rows import dict_row
from src.config import DATABASE_URL

logger = logging.getLogger(__name__)


class Database:
    """Database connection pool manager"""

    def __init__(self, connection_string: str = DATABASE_URL):
        self.connection_string = connection_string
        self._pool: Optional[psycopg.AsyncConnectionPool] = None

    async def init_pool(self) -> None:
        """Initialize connection pool"""
        logger.info("Initializing database connection pool")
        self._pool = psycopg.AsyncConnectionPool(
            self.connection_string,
            min_size=2,
            max_size=10,
            open=True
        )

    async def close_pool(self) -> None:
        """Close connection pool"""
        if self._pool:
            logger.info("Closing database connection pool")
            await self._pool.close()

    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[psycopg.AsyncConnection, None]:
        """Get database connection from pool"""
        if not self._pool:
            raise RuntimeError("Database pool not initialized")

        async with self._pool.connection() as conn:
            conn.row_factory = dict_row
            yield conn


# Global database instance
db = Database()
```

**PATTERN**: Connection pooling with context manager
**IMPORTS**: psycopg (async PostgreSQL driver)

**VALIDATE:**
```bash
cd /home/samuel/workspace/health-agent && python3 -c "from src.db.connection import db; print('Database connection module loaded')"
```

**Expected**: "Database connection module loaded"

---

#### Task 2.7: CREATE src/db/queries.py

**IMPLEMENT:**
```python
"""Database queries"""
import json
import logging
from typing import Optional
from uuid import UUID
from datetime import datetime
from src.db.connection import db
from src.models.user import UserProfile
from src.models.food import FoodEntry
from src.models.tracking import TrackingCategory, TrackingEntry
from src.models.reminder import Reminder

logger = logging.getLogger(__name__)


# User operations
async def create_user(telegram_id: str) -> None:
    """Create new user in database"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO users (telegram_id) VALUES (%s) ON CONFLICT (telegram_id) DO NOTHING",
                (telegram_id,)
            )
            await conn.commit()
    logger.info(f"Created user: {telegram_id}")


async def user_exists(telegram_id: str) -> bool:
    """Check if user exists"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT 1 FROM users WHERE telegram_id = %s",
                (telegram_id,)
            )
            return await cur.fetchone() is not None


# Food entry operations
async def save_food_entry(entry: FoodEntry) -> None:
    """Save food entry to database"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO food_entries
                (user_id, timestamp, photo_path, foods, total_calories, total_macros, meal_type, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    entry.user_id,
                    entry.timestamp,
                    entry.photo_path,
                    json.dumps([f.model_dump() for f in entry.foods]),
                    entry.total_calories,
                    json.dumps(entry.total_macros.model_dump()),
                    entry.meal_type,
                    entry.notes
                )
            )
            await conn.commit()
    logger.info(f"Saved food entry for user {entry.user_id}")


async def get_recent_food_entries(user_id: str, limit: int = 10) -> list[dict]:
    """Get recent food entries for user"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT * FROM food_entries
                WHERE user_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                (user_id, limit)
            )
            return await cur.fetchall()


# Tracking category operations
async def create_tracking_category(category: TrackingCategory) -> None:
    """Create new tracking category"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO tracking_categories (id, user_id, name, fields, schedule, active)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    category.id,
                    category.user_id,
                    category.name,
                    json.dumps({k: v.model_dump() for k, v in category.fields.items()}),
                    json.dumps(category.schedule.model_dump()) if category.schedule else None,
                    category.active
                )
            )
            await conn.commit()
    logger.info(f"Created tracking category: {category.name} for user {category.user_id}")


async def get_tracking_categories(user_id: str, active_only: bool = True) -> list[dict]:
    """Get tracking categories for user"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            query = "SELECT * FROM tracking_categories WHERE user_id = %s"
            if active_only:
                query += " AND active = true"
            await cur.execute(query, (user_id,))
            return await cur.fetchall()


async def save_tracking_entry(entry: TrackingEntry) -> None:
    """Save tracking entry"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO tracking_entries (id, user_id, category_id, timestamp, data, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    entry.id,
                    entry.user_id,
                    entry.category_id,
                    entry.timestamp,
                    json.dumps(entry.data),
                    entry.notes
                )
            )
            await conn.commit()
    logger.info(f"Saved tracking entry for user {entry.user_id}")


# Reminder operations
async def create_reminder(reminder: Reminder) -> None:
    """Create new reminder"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO reminders (id, user_id, reminder_type, message, schedule, active)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    reminder.id,
                    reminder.user_id,
                    reminder.reminder_type,
                    reminder.message,
                    json.dumps(reminder.schedule.model_dump()),
                    reminder.active
                )
            )
            await conn.commit()
    logger.info(f"Created reminder for user {reminder.user_id}")


async def get_active_reminders(user_id: str) -> list[dict]:
    """Get active reminders for user"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT * FROM reminders WHERE user_id = %s AND active = true",
                (user_id,)
            )
            return await cur.fetchall()
```

**PATTERN**: Async database operations with psycopg3
**IMPORTS**: json for JSONB serialization, models for type safety
**GOTCHA**: Use json.dumps() for JSONB columns, model_dump() for Pydantic serialization

**VALIDATE:**
```bash
cd /home/samuel/workspace/health-agent && python3 -c "from src.db.queries import create_user, save_food_entry; print('Database queries loaded')"
```

**Expected**: "Database queries loaded"

---

**CONTINUATION NOTE**: This plan is extensive. The remaining tasks cover:
- Memory system (file_manager.py, system_prompt.py, templates.py)
- PydanticAI agent setup (agent.py with tools)
- Telegram bot handlers (bot.py, message routing)
- Vision AI integration (utils/vision.py)
- Reminder scheduler (scheduler/reminder_manager.py)
- Feature handlers (food_photo.py, tracking.py, settings.py, transparency.py)
- Main entry point (main.py)
- Tests
- Validation commands

**Complexity Assessment**: This is a HIGH complexity greenfield project requiring:
- 30+ new files
- 4 integrated systems (Telegram, PydanticAI, PostgreSQL, Vision AI)
- Novel memory system design
- Dynamic extensibility architecture

**Estimated Implementation Time**: 2-3 days for experienced developer

**Confidence Score for One-Pass Success**: 7/10
- **Risks**:
  - Vision AI prompt engineering for accurate food recognition
  - Dynamic prompt generation complexity
  - JobQueue scheduling edge cases
  - Memory file parsing robustness
- **Mitigations**:
  - Comprehensive documentation links provided
  - Pattern examples from official docs
  - Type safety with Pydantic
  - Incremental testing approach

---

## TESTING STRATEGY

### Unit Tests

**Scope**: Test individual components in isolation with mocks

**Key Test Files:**
- `tests/unit/test_memory_manager.py` - Test markdown file read/write
- `tests/unit/test_models.py` - Test Pydantic model validation
- `tests/unit/test_database.py` - Test database queries with test DB
- `tests/unit/test_vision.py` - Test vision AI parsing (mock API)

**Pattern**:
```python
import pytest
from src.memory.file_manager import MemoryFileManager

@pytest.mark.asyncio
async def test_create_user_memory_files(tmp_path):
    """Test creating memory files for new user"""
    manager = MemoryFileManager(data_path=tmp_path)
    await manager.create_user_files("123456789")

    assert (tmp_path / "123456789" / "profile.md").exists()
    assert (tmp_path / "123456789" / "preferences.md").exists()
    assert (tmp_path / "123456789" / "patterns.md").exists()
```

### Integration Tests

**Scope**: Test complete workflows end-to-end

**Key Scenarios:**
1. New user onboarding flow
2. Food photo analysis → database storage → memory update
3. Creating tracking category → scheduling prompt → receiving entry
4. Setting preference → system prompt update → response style change

**Pattern**:
```python
@pytest.mark.asyncio
async def test_food_photo_workflow(test_db, test_bot):
    """Test complete food photo analysis workflow"""
    # Send photo
    result = await handle_food_photo("123", "path/to/test_food.jpg")

    # Verify database entry
    entries = await get_recent_food_entries("123", limit=1)
    assert len(entries) == 1
    assert entries[0]["total_calories"] > 0

    # Verify memory update
    memory = await load_user_memory("123")
    assert "recent_foods" in memory
```

### Edge Cases

**Critical edge cases to test:**
1. Vision AI returns low confidence → asks clarifying questions
2. User creates duplicate tracking category → handle gracefully
3. Reminder scheduled in past → skip and schedule next occurrence
4. User deletes .md files manually → recreate from defaults
5. Database connection loss → retry with exponential backoff
6. Photo too large → compress before vision API call
7. Ambiguous food items → ask for specifics
8. Timezone handling for reminders
9. Concurrent message handling from same user
10. JSONB query with special characters

---

## VALIDATION COMMANDS

Execute all commands in order to ensure zero regressions.

### Level 1: Code Quality

```bash
cd /home/samuel/workspace/health-agent

# Type checking (mypy)
mypy src/ --strict

# Linting (ruff)
ruff check src/

# Formatting (black)
black --check src/

# Import sorting
ruff check --select I src/
```

**Expected**: All pass with exit code 0

### Level 2: Unit Tests

```bash
cd /home/samuel/workspace/health-agent

# Run unit tests with coverage
pytest tests/unit/ -v --cov=src --cov-report=term-missing

# Coverage threshold check
pytest tests/unit/ --cov=src --cov-fail-under=80
```

**Expected**: 80%+ coverage, all tests pass

### Level 3: Integration Tests

```bash
cd /home/samuel/workspace/health-agent

# Start test database
docker-compose up -d postgres

# Run migrations
psql $DATABASE_URL < migrations/001_initial_schema.sql

# Run integration tests
pytest tests/integration/ -v

# Cleanup
docker-compose down
```

**Expected**: All integration tests pass

### Level 4: Manual Validation

```bash
# 1. Start services
docker-compose up -d

# 2. Check logs
docker-compose logs -f app

# 3. Test with real Telegram bot
# - Send /start command → should respond
# - Send photo of food → should analyze
# - Ask "what do you know about me?" → should respond
# - Request reminder → should confirm and schedule

# 4. Verify database
psql $DATABASE_URL -c "SELECT COUNT(*) FROM users;"
psql $DATABASE_URL -c "SELECT COUNT(*) FROM food_entries;"

# 5. Check memory files
ls -la data/users/<your_telegram_id>/
cat data/users/<your_telegram_id>/profile.md
```

**Expected**: Bot responds correctly, data persists

### Level 5: Performance & Cost Validation

```bash
# Check vision API cost per image
# Expected: ~$0.003 per image with gpt-4o-mini

# Monitor database query performance
psql $DATABASE_URL -c "EXPLAIN ANALYZE SELECT * FROM food_entries WHERE user_id = '123' ORDER BY timestamp DESC LIMIT 10;"

# Expected: < 10ms query time with indexes
```

---

## ACCEPTANCE CRITERIA

- [ ] Telegram bot responds to messages from whitelisted users only
- [ ] Bot has default personality: friendly, funny, medium-brief
- [ ] Food photo analysis works (identifies foods, estimates calories/macros)
- [ ] Food entries saved to database with photo stored locally
- [ ] User can create custom tracking categories via conversation
- [ ] Reminders send at scheduled times using JobQueue
- [ ] Memory files created and updated (profile.md, preferences.md, patterns.md)
- [ ] System prompt dynamically generated from user preferences
- [ ] User can ask "what do you know about me?" and get transparent summary
- [ ] User can change settings via chat ("be more brief", "be supportive")
- [ ] All validation commands pass (type-check, lint, format, tests)
- [ ] Database schema created with proper indexes
- [ ] Multi-user support (each user isolated data)
- [ ] Docker deployment works (docker-compose up)
- [ ] No secrets in code (all in .env)
- [ ] Error handling for API failures (vision AI, database)
- [ ] Logging configured (INFO level minimum)

---

## COMPLETION CHECKLIST

- [ ] All Phase 1 tasks completed (foundation setup)
- [ ] All Phase 2 tasks completed (core infrastructure)
- [ ] All Phase 3 tasks completed (feature implementation)
- [ ] All Phase 4 tasks completed (testing & validation)
- [ ] All Level 1 validation passed (type-check, lint, format)
- [ ] All Level 2 validation passed (unit tests, 80%+ coverage)
- [ ] All Level 3 validation passed (integration tests)
- [ ] Level 4 manual validation completed (real Telegram testing)
- [ ] Level 5 performance validation completed (cost, query speed)
- [ ] All acceptance criteria met
- [ ] Documentation updated (README.md with setup instructions)
- [ ] .env.example matches all required variables
- [ ] No hardcoded secrets or API keys in code
- [ ] Git repository clean (no untracked sensitive files)

---

## NOTES

### Design Decisions

**1. Markdown Files for Memory (not Database)**
- **Why**: Human-readable, debuggable, versionable, similar to Anthropic's memory system
- **Trade-off**: Slightly slower than database, but acceptable for handful of users
- **Alternative considered**: Database with TEXT columns, but loses readability benefit

**2. python-telegram-bot (not aiogram)**
- **Why**: More mature, better docs, built-in JobQueue for scheduling
- **Trade-off**: Slightly more verbose than aiogram
- **Alternative considered**: aiogram (fully async), but requires more asyncio expertise

**3. Dedicated food_entries Table (not generic tracking)**
- **Why**: Food is core feature with special needs (photos, vision API, macros)
- **Trade-off**: Less DRY, but clearer schema and faster queries
- **Alternative considered**: Use tracking_entries for food, but complicates photo handling

**4. PydanticAI (not LangChain)**
- **Why**: Type-safe, FastAPI-like DX, structured outputs, model-agnostic
- **Trade-off**: Newer library (less community resources)
- **Alternative considered**: LangChain, but Pydantic AI has better type safety

**5. JobQueue (not APScheduler directly)**
- **Why**: Integrated with python-telegram-bot, handles Telegram context automatically
- **Trade-off**: Less flexible than raw APScheduler
- **Alternative considered**: Raw APScheduler, but JobQueue is more convenient

### Implementation Risks

**High Risk:**
1. **Vision AI accuracy**: Food recognition from photos is inherently imperfect
   - Mitigation: Ask clarifying questions, learn user's common foods over time

2. **Dynamic prompt generation**: System prompt must adapt correctly to preferences
   - Mitigation: Template-based approach with clear rules, extensive testing

**Medium Risk:**
3. **JobQueue reliability**: Reminders must send consistently
   - Mitigation: Use persistent database for reminder config, test thoroughly

4. **Memory file parsing**: Markdown parsing must be robust
   - Mitigation: Use simple, structured format, validate on write

**Low Risk:**
5. **Database performance**: JSONB queries could be slow
   - Mitigation: GIN indexes, query optimization, limited to handful of users

### Future Enhancements (Out of Scope)

- Data export (CSV, PDF)
- Trend analysis and charts
- Correlation detection ("sleep affects workout performance")
- Integration with fitness apps (MyFitnessPal, Apple Health)
- Voice input for food logging
- Meal planning and recipe suggestions
- Progress photos comparison
- Social features (share progress with friends)
- Web dashboard
- Multi-language support

### Cost Estimates

**MVP (10 users, 5 food photos/day each):**
- Vision API: 50 photos/day × $0.003 = $0.15/day = ~$4.50/month
- Agent API: ~1000 messages/day × $0.000003 = ~$0.09/month (Claude 3.5 Sonnet)
- Database: Free (self-hosted PostgreSQL)
- **Total**: ~$5/month

**Scaling (100 users):**
- Vision API: ~$45/month
- Agent API: ~$0.90/month
- Database: Still free (PostgreSQL can handle this)
- **Total**: ~$50/month

### Performance Targets

- Message response time: < 2s (text), < 5s (vision analysis)
- Database query time: < 10ms (with indexes)
- Memory file read: < 50ms
- Reminder accuracy: ± 1 second of scheduled time
- Uptime: 99% (Docker restart: unless-stopped)

### Security Considerations

- Telegram ID whitelist (ALLOWED_TELEGRAM_IDS)
- No user can access another user's data
- API keys in environment variables only
- Photos stored locally with user-specific directories
- Database credentials not in code
- No SQL injection (parameterized queries)
- No command injection (using python-telegram-bot properly)
- HTTPS for Telegram API (handled by library)

---

## DOCUMENTATION SOURCES

### PydanticAI
- [PydanticAI Official Documentation](https://ai.pydantic.dev/)
- [Agents Documentation](https://ai.pydantic.dev/agents/)
- [Tools Documentation](https://ai.pydantic.dev/tools/)
- [GitHub Repository](https://github.com/pydantic/pydantic-ai)

### python-telegram-bot
- [python-telegram-bot Documentation](https://docs.python-telegram-bot.org/)
- [JobQueue Documentation](https://docs.python-telegram-bot.org/en/stable/telegram.ext.jobqueue.html)
- [GitHub Repository](https://github.com/python-telegram-bot/python-telegram-bot)

### Vision AI
- [OpenAI Vision API Documentation](https://platform.openai.com/docs/guides/vision)
- [Build Your Own Food Tracker Tutorial](https://dev.to/frosnerd/build-your-own-food-tracker-with-openai-platform-55n8)
- [Food Recognition with OpenAI](https://dev.to/mayank_laddha_ml/food-recognition-and-nutrition-estimation-using-openai-4mdo)

### PostgreSQL JSONB
- [PostgreSQL JSONB Documentation](https://www.postgresql.org/docs/current/datatype-json.html)
- [How to Query JSONB in PostgreSQL](https://www.tigerdata.com/learn/how-to-query-jsonb-in-postgresql)
- [JSONB Query Patterns 2025](https://elvanco.com/blog/how-to-query-jsonb-data-with-postgresql)

### psycopg3
- [psycopg3 Types Documentation](https://www.psycopg.org/psycopg3/docs/api/types.html)
- [Adapting Basic Python Types](https://www.psycopg.org/psycopg3/docs/basic/adapt.html)
