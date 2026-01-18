# Code Style Guide

Python coding standards and conventions for the Health Agent project.

---

## Style Standards

- **PEP 8** - Python style guide baseline
- **Black** - Auto-formatter (line length: 100)
- **Ruff** - Fast linter
- **mypy** - Type checking

---

## Formatting

### Auto-Format with Black

```bash
black src/ tests/
```

### Check Formatting

```bash
black --check src/
```

### Line Length

```python
# Good
def process_food_entry(
    user_id: str, foods: list[dict], calories: int
) -> dict:
    ...

# Bad (too long)
def process_food_entry(user_id: str, foods: list[dict], calories: int, protein: float, carbs: float, fat: float) -> dict:
    ...
```

---

## Naming Conventions

### Files
- `snake_case.py`
- Example: `memory_file_manager.py`, `multi_agent_consensus.py`

### Classes
- `PascalCase`
- Example: `MemoryFileManager`, `AgentDeps`, `FoodEntry`

### Functions/Methods
- `snake_case()`
- Example: `save_food_entry()`, `calculate_level()`, `award_xp()`

### Constants
- `UPPER_CASE`
- Example: `TELEGRAM_BOT_TOKEN`, `MAX_XP_LEVEL`, `API_PORT`

### Private Methods
- `_snake_case()` (leading underscore)
- Example: `_generate_embedding()`, `_validate_nutrition_data()`

---

## Type Hints

### Always Use Type Hints

```python
# Good
async def save_food_entry(
    user_id: str,
    foods: list[dict],
    calories: int
) -> str:
    return entry_id

# Bad (no type hints)
async def save_food_entry(user_id, foods, calories):
    return entry_id
```

### Optional Types

```python
from typing import Optional

def get_profile(user_id: str) -> Optional[dict]:
    # May return None
    ...
```

### Generic Types

```python
from typing import TypedDict, Any

class FoodEntry(TypedDict):
    name: str
    calories: int
    protein: float

def process_foods(entries: list[FoodEntry]) -> dict[str, Any]:
    ...
```

---

## Docstrings

### Google Style Docstrings

```python
async def award_xp(user_id: str, activity_type: str, quality_bonus: int = 0) -> dict:
    """Award XP for completing a health activity.

    Args:
        user_id: User's Telegram ID
        activity_type: Type of activity (e.g., "food_log_photo")
        quality_bonus: Additional XP for quality (0-50)

    Returns:
        Dictionary containing:
            - xp_gained: XP awarded for this activity
            - total_xp: User's total XP after award
            - level: Current level
            - level_up: Whether user leveled up

    Raises:
        ValueError: If activity_type is invalid
    """
    ...
```

### Module Docstrings

```python
"""Multi-agent nutrition consensus system.

This module implements a 3-agent + moderator system for accurate food photo analysis.
Reduces hallucination by 30% compared to single-model analysis.

Example:
    result = await analyze_food_photo("path/to/photo.jpg")
    print(result["calories"])  # 450
"""
```

---

## Import Order

```python
# 1. Standard library
import os
import logging
from datetime import datetime

# 2. Third-party libraries
from pydantic import BaseModel
from pydantic_ai import Agent
import httpx

# 3. Local modules
from src.config import DATABASE_URL
from src.db.queries import save_food_entry
from src.memory.file_manager import MemoryFileManager
```

### Use Absolute Imports

```python
# Good
from src.agent.tools import save_food_entry

# Bad (relative imports)
from ..tools import save_food_entry
```

---

## Error Handling

### Specific Exceptions

```python
# Good
try:
    entry_id = await save_food_entry(...)
except psycopg.IntegrityError as e:
    logger.error(f"Database constraint violation: {e}")
    return {"success": False, "error": "Duplicate entry"}
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    return {"success": False, "error": "Internal error"}

# Bad (bare except)
try:
    entry_id = await save_food_entry(...)
except:
    return {"success": False}
```

### Logging Exceptions

```python
# Good
logger.exception("Failed to save food entry")  # Includes stack trace

# Okay
logger.error(f"Error: {str(e)}")

# Bad (no logging)
pass
```

---

## Async Patterns

### Always Use await

```python
# Good
result = await async_function()

# Bad (blocks event loop)
result = async_function()  # Forgot await
```

### Parallel Async Operations

```python
import asyncio

# Good (parallel)
results = await asyncio.gather(
    conservative_agent.run_sync(photo),
    moderate_agent.run_sync(photo),
    optimistic_agent.run_sync(photo)
)

# Bad (sequential - slower)
conservative = await conservative_agent.run_sync(photo)
moderate = await moderate_agent.run_sync(photo)
optimistic = await optimistic_agent.run_sync(photo)
```

---

## Logging

### Log Levels

```python
logger.debug("Detailed debugging info")      # DEBUG
logger.info("Normal operations")             # INFO
logger.warning("Potential issue")            # WARNING
logger.error("Error occurred")               # ERROR
logger.exception("Error with stack trace")   # ERROR + traceback
```

### Structured Logging

```python
# Good
logger.info(f"Food entry saved: user={user_id}, calories={calories}")

# Bad (unstructured)
logger.info("Saved food")
```

---

## Configuration

### Environment Variables

```python
import os

# Good
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable required")

# Bad (hardcoded)
DATABASE_URL = "postgresql://localhost/db"
```

---

## Code Organization

### File Structure

```python
"""Module docstring"""

# Imports
import os
from src.config import SETTING

# Constants
MAX_VALUE = 100

# Type definitions
class MyModel(BaseModel):
    ...

# Functions
async def my_function():
    ...

# Main execution
if __name__ == "__main__":
    ...
```

---

## Testing Code Style

### Test Function Names

```python
# Good (descriptive)
def test_award_xp_food_log_photo():
    ...

def test_calculate_level_at_boundary():
    ...

# Bad (vague)
def test1():
    ...

def test_xp():
    ...
```

### Arrange-Act-Assert Pattern

```python
def test_award_xp():
    # Arrange
    user_id = "test_user"
    activity_type = "food_log_photo"

    # Act
    result = award_xp(user_id, activity_type)

    # Assert
    assert result["xp_gained"] == 75
    assert result["success"] == True
```

---

## Linting

### Ruff Configuration

```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]  # Line length handled by Black
```

### Run Linter

```bash
ruff check src/
ruff check --fix src/  # Auto-fix issues
```

---

## Type Checking

### mypy Configuration

```ini
# mypy.ini
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
```

### Run Type Checker

```bash
mypy src/
```

---

## Pre-commit Hooks

### Setup

```bash
pip install pre-commit
pre-commit install
```

### .pre-commit-config.yaml

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.1.0
    hooks:
      - id: black
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
```

---

## Common Patterns

### Dependency Injection (Agent Tools)

```python
@claude_agent.tool()
async def my_tool(ctx: RunContext[AgentDeps], param: str) -> str:
    # Access dependencies
    user_id = ctx.deps.telegram_id
    memory_manager = ctx.deps.memory_manager

    # Use dependencies
    await memory_manager.update_profile(user_id, {"field": param})
    return "Success"
```

### Service Layer Pattern

```python
class MyService:
    """Service for business logic"""

    def __init__(self, db_pool):
        self.db_pool = db_pool

    async def do_operation(self, param: str) -> dict:
        """Perform business operation"""
        async with self.db_pool.connection() as conn:
            result = await conn.fetch_one(query, {"param": param})
            return result
```

---

## Summary

**Quick Checklist**:
- ✅ Type hints on all functions
- ✅ Google-style docstrings
- ✅ Black formatting (line length 100)
- ✅ Async/await for I/O operations
- ✅ Specific exception handling
- ✅ Structured logging
- ✅ Environment variables for config
- ✅ Descriptive test names

---

## Related Documentation

- **Testing**: [testing.md](testing.md) - Test conventions
- **Adding Features**: [adding-features.md](adding-features.md) - Development workflow
- **DEVELOPMENT.md**: [../../DEVELOPMENT.md](../../DEVELOPMENT.md) - Full development guide

## Revision History

- 2025-01-18: Initial code style guide created for Phase 3.7
