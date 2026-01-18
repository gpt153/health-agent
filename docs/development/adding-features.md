# Adding Features - Step-by-Step Guide

How to add new features to the Health Agent system.

---

## Feature Development Workflow

```
1. Plan → 2. Create Branch → 3. Implement → 4. Test → 5. Document → 6. PR → 7. Deploy
```

---

## Example: Adding a New Tracking Category

### Step 1: Plan the Feature

**Goal**: Add sleep quality tracking

**Requirements**:
- User can log sleep duration (hours)
- User can rate sleep quality (1-10)
- Daily reminder to log sleep
- XP reward for consistent logging

---

### Step 2: Create Feature Branch

```bash
git checkout main
git pull origin main
git checkout -b feature/sleep-tracking
```

---

### Step 3: Database Migration

Create `/migrations/023_sleep_tracking.sql`:

```sql
-- Sleep tracking category (using existing tracking_categories table)
INSERT INTO tracking_categories (id, user_id, name, fields, schedule)
VALUES (
    gen_random_uuid(),
    'system',  -- System-wide category
    'Sleep Quality',
    '[
        {"name": "duration_hours", "type": "number", "required": true, "min": 0, "max": 24},
        {"name": "quality_rating", "type": "number", "required": true, "min": 1, "max": 10},
        {"name": "notes", "type": "text", "required": false}
    ]'::jsonb,
    '{"type": "daily", "time": "08:00"}'::jsonb
) ON CONFLICT DO NOTHING;
```

Apply migration:
```bash
psql -h localhost -p 5436 -U postgres -d health_agent < migrations/023_sleep_tracking.sql
```

---

### Step 4: Add Agent Tool

Edit `src/agent/__init__.py`:

```python
@claude_agent.tool()
@gpt_agent.tool()
async def log_sleep(
    ctx: RunContext[AgentDeps],
    duration_hours: float,
    quality_rating: int,
    notes: Optional[str] = None
) -> TrackingEntryResult:
    """Log sleep quality data.

    Args:
        ctx: Agent runtime context
        duration_hours: Hours of sleep (0-24)
        quality_rating: Sleep quality rating (1-10)
        notes: Optional notes about sleep

    Returns:
        TrackingEntryResult with success status and message
    """
    telegram_id = ctx.deps.telegram_id

    # Validate inputs
    if not (0 <= duration_hours <= 24):
        return TrackingEntryResult(
            success=False,
            message="Sleep duration must be between 0 and 24 hours",
            category="Sleep Quality",
            data={}
        )

    if not (1 <= quality_rating <= 10):
        return TrackingEntryResult(
            success=False,
            message="Quality rating must be between 1 and 10",
            category="Sleep Quality",
            data={}
        )

    # Save to database
    entry_data = {
        "duration_hours": duration_hours,
        "quality_rating": quality_rating,
        "notes": notes
    }

    await log_tracking_entry(
        telegram_id=telegram_id,
        category_name="Sleep Quality",
        data=entry_data
    )

    # Award XP
    await award_xp(telegram_id, "sleep_log", quality_bonus=0)

    return TrackingEntryResult(
        success=True,
        message=f"Sleep logged: {duration_hours}h, quality {quality_rating}/10",
        category="Sleep Quality",
        data=entry_data
    )
```

---

### Step 5: Update System Prompt

Edit `src/memory/system_prompt.py`:

```python
SYSTEM_PROMPT = f"""
...
## Available Tools

### Sleep Tracking
- **log_sleep**: Log sleep duration and quality
  - duration_hours: Hours of sleep (0-24)
  - quality_rating: Quality rating (1-10)
  - notes: Optional notes

  Example: "I slept 7.5 hours last night, quality was 8/10"
...
"""
```

---

### Step 6: Add API Endpoint (Optional)

Edit `src/api/routes.py`:

```python
@app.post("/sleep", response_model=TrackingEntryResult)
async def log_sleep_endpoint(
    request: SleepLogRequest,
    api_key: str = Depends(verify_api_key)
):
    """Log sleep quality data via API"""
    result = await log_sleep(
        ctx=build_context(request.user_id),
        duration_hours=request.duration_hours,
        quality_rating=request.quality_rating,
        notes=request.notes
    )
    return result
```

Add Pydantic model in `src/api/models.py`:

```python
class SleepLogRequest(BaseModel):
    user_id: str
    duration_hours: float = Field(ge=0, le=24)
    quality_rating: int = Field(ge=1, le=10)
    notes: Optional[str] = None
```

---

### Step 7: Write Tests

Create `tests/unit/test_sleep_tracking.py`:

```python
import pytest
from src.agent import log_sleep
from src.agent import AgentDeps
from tests.mocks import MockMemoryManager

@pytest.mark.asyncio
async def test_log_sleep_valid():
    """Test logging valid sleep data"""
    ctx = build_mock_context(user_id="test_user")

    result = await log_sleep(
        ctx=ctx,
        duration_hours=7.5,
        quality_rating=8,
        notes="Felt rested"
    )

    assert result.success == True
    assert "7.5h" in result.message
    assert result.category == "Sleep Quality"

@pytest.mark.asyncio
async def test_log_sleep_invalid_duration():
    """Test logging invalid sleep duration"""
    ctx = build_mock_context(user_id="test_user")

    result = await log_sleep(
        ctx=ctx,
        duration_hours=25,  # Invalid
        quality_rating=8
    )

    assert result.success == False
    assert "between 0 and 24" in result.message
```

Run tests:
```bash
pytest tests/unit/test_sleep_tracking.py -v
```

---

### Step 8: Update Documentation

Add to `/docs/api/agent-interface.md`:

```markdown
### `log_sleep`

Log sleep duration and quality.

**Parameters**:
- `duration_hours` (float): Hours of sleep (0-24)
- `quality_rating` (int): Sleep quality rating (1-10)
- `notes` (str, optional): Additional notes

**Example**:
- "I slept 7.5 hours, quality was 8/10"
```

---

### Step 9: Commit and Push

```bash
git add migrations/023_sleep_tracking.sql src/agent/__init__.py tests/
git commit -m "feat: Add sleep quality tracking

- Created sleep tracking category with duration and quality rating
- Added log_sleep agent tool with validation
- Implemented XP rewards for sleep logging
- Added unit tests for sleep tracking

Closes #145"

git push -u origin feature/sleep-tracking
```

---

### Step 10: Create Pull Request

```bash
gh pr create --title "Add sleep quality tracking" --body "
## Description
Adds sleep quality tracking feature with duration and quality rating.

## Changes
- Database migration for sleep tracking category
- log_sleep agent tool with input validation
- API endpoint for programmatic sleep logging
- Unit tests with 95% coverage

## Testing
- Unit tests pass: pytest tests/unit/test_sleep_tracking.py
- Manual testing via Telegram: 'I slept 7.5 hours, quality 8/10'
- API testing: POST /sleep endpoint

## Closes
#145
"
```

---

## Common Feature Types

### Adding a New Agent Tool

1. Define tool function in `src/agent/__init__.py`
2. Register on both agents (`@claude_agent.tool()`, `@gpt_agent.tool()`)
3. Add to system prompt
4. Write tests
5. Update documentation

### Adding a Database Table

1. Create migration SQL file (`NNN_description.sql`)
2. Test migration on dev database
3. Add query functions in `src/db/queries.py`
4. Update schema documentation

### Adding an API Endpoint

1. Define Pydantic request/response models in `src/api/models.py`
2. Add route in `src/api/routes.py`
3. Add authentication (`verify_api_key` dependency)
4. Write API tests (`tests/api/`)
5. Update API_README.md

### Adding a Service

1. Create service module in `src/services/`
2. Define service class with methods
3. Inject service into AgentDeps
4. Use in agent tools
5. Write unit tests for service

---

## Feature Checklist

Before submitting PR:

- [ ] **Code**
  - [ ] Feature implemented and working
  - [ ] Code formatted with Black
  - [ ] Type hints on all functions
  - [ ] Docstrings added
  - [ ] No linting errors (ruff check)

- [ ] **Tests**
  - [ ] Unit tests written
  - [ ] Integration tests (if needed)
  - [ ] Tests pass locally (pytest)
  - [ ] Coverage >80%

- [ ] **Database**
  - [ ] Migration file created (if needed)
  - [ ] Migration tested
  - [ ] Indexes added for performance

- [ ] **Documentation**
  - [ ] Agent tool documented
  - [ ] API endpoint documented (if added)
  - [ ] README updated (if needed)
  - [ ] Docstrings complete

- [ ] **Review**
  - [ ] Self-review of changes
  - [ ] No debug code left in
  - [ ] No secrets committed
  - [ ] Commit messages clear

---

## Related Documentation

- **Git Workflow**: [git-workflow.md](git-workflow.md) - Branching and commits
- **Testing**: [testing.md](testing.md) - Writing tests
- **Code Style**: [code-style.md](code-style.md) - Style guidelines
- **Agent Interface**: [/docs/api/agent-interface.md](../api/agent-interface.md) - Tool reference
- **Database Schema**: [/docs/api/database-schema.md](../api/database-schema.md) - Schema reference

## Revision History

- 2025-01-18: Initial feature development guide created for Phase 3.7
