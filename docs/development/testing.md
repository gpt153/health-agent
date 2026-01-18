# Testing Guide

Comprehensive guide to testing the Health Agent system.

---

## Test Structure

```
tests/
├── unit/           # Fast, isolated unit tests
│   ├── test_agent.py
│   ├── test_gamification.py
│   └── test_memory.py
├── integration/    # Database and service integration tests
│   ├── test_food_logging.py
│   └── test_reminders.py
└── api/            # API endpoint tests
    └── test_endpoints.py
```

---

## Running Tests

### All Tests
```bash
pytest
```

### Specific Test File
```bash
pytest tests/unit/test_gamification.py
```

### Specific Test Function
```bash
pytest tests/unit/test_gamification.py::test_xp_award
```

### With Coverage
```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### Verbose Output
```bash
pytest -v -s  # -s shows print statements
```

---

## Writing Tests

### Unit Test Example

```python
# tests/unit/test_xp_system.py
import pytest
from src.gamification.xp_system import award_xp, calculate_level

@pytest.mark.asyncio
async def test_award_xp_food_log():
    """Test XP award for food logging"""
    result = await award_xp(
        user_id="test_user",
        activity_type="food_log_photo",
        quality_bonus=10
    )

    assert result["success"] == True
    assert result["xp_gained"] == 85  # 75 base + 10 bonus
    assert result["level"] >= 1

def test_calculate_level():
    """Test level calculation from XP"""
    level, tier = calculate_level(xp=450)
    assert level == 3
    assert tier == "Bronze"
```

### Integration Test Example

```python
# tests/integration/test_food_logging.py
import pytest
from src.db.queries import save_food_entry, get_food_entries_by_date
from src.db.connection import get_db_pool

@pytest.mark.asyncio
async def test_food_entry_crud():
    """Test food entry create and retrieve"""
    pool = await get_db_pool()

    # Create
    entry_id = await save_food_entry(
        user_id="test_user",
        foods=[{"name": "chicken", "amount": "200g"}],
        calories=220
    )

    assert entry_id is not None

    # Retrieve
    entries = await get_food_entries_by_date(
        user_id="test_user",
        date="2025-01-18"
    )

    assert len(entries) > 0
    assert entries[0]["calories"] == 220
```

### API Test Example

```python
# tests/api/test_endpoints.py
import pytest
from fastapi.testclient import TestClient
from src.api.app import app

client = TestClient(app)

def test_health_endpoint():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_chat_endpoint():
    """Test chat endpoint"""
    response = client.post(
        "/chat",
        headers={"X-API-Key": "test_key_123"},
        json={
            "user_id": "test_user",
            "message": "What is my XP?"
        }
    )

    assert response.status_code == 200
    assert "response" in response.json()
```

---

## Test Fixtures

### Database Fixture

```python
# tests/conftest.py
import pytest
from src.db.connection import get_db_pool

@pytest.fixture
async def db_pool():
    """Provide database pool for tests"""
    pool = await get_db_pool()
    yield pool
    # Cleanup
    async with pool.connection() as conn:
        await conn.execute("DELETE FROM test_users")
```

### Mock Agent Fixture

```python
@pytest.fixture
def mock_agent_deps():
    """Mock agent dependencies"""
    return AgentDeps(
        telegram_id="test_user",
        memory_manager=MockMemoryManager(),
        user_memory={"profile": {}, "preferences": {}},
        reminder_manager=MockReminderManager()
    )
```

---

## Manual Testing

### API Testing Script

```bash
# scripts/test_api.py
python scripts/test_api.py
```

**Tests**:
- Health check
- User creation
- Food logging
- XP retrieval
- Reminder scheduling

### SCAR Test Suite

```bash
# scripts/scar_test_agent.py
python scripts/scar_test_agent.py
```

**Tests**:
- Full conversation flows
- Multi-turn interactions
- Tool calling validation
- Error handling

---

## Test Configuration

### pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (requires database)
    api: API endpoint tests
    slow: Slow-running tests
```

### Running by Marker

```bash
pytest -m unit        # Only unit tests
pytest -m integration # Only integration tests
pytest -m "not slow"  # Skip slow tests
```

---

## Mocking External APIs

### Mock OpenAI

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
@patch("src.vision.multi_agent_consensus.openai_client")
async def test_food_analysis(mock_openai):
    """Test food photo analysis with mocked OpenAI"""
    mock_openai.chat.completions.create = AsyncMock(
        return_value={"choices": [{"message": {"content": "220 calories"}}]}
    )

    result = await analyze_food_photo("test_photo.jpg")
    assert result["calories"] == 220
```

### Mock USDA API

```python
@patch("src.nutrition.usda_client.httpx.AsyncClient")
async def test_usda_search(mock_httpx):
    """Test USDA food search with mocked HTTP client"""
    mock_httpx.get.return_value.json = lambda: {
        "foods": [{"fdcId": 12345, "description": "Chicken breast"}]
    }

    results = await usda_client.search_food("chicken")
    assert len(results) > 0
```

---

## Continuous Integration

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v3
```

---

## Coverage Goals

- **Overall**: >80%
- **Critical Paths**: >90% (agent tools, gamification, food logging)
- **Edge Cases**: >70%

---

## Debugging Tests

### Print Debug Info

```bash
pytest -v -s  # Show print() output
```

### Drop into Debugger on Failure

```bash
pytest --pdb  # Python debugger
pytest --pdbcls=IPython.terminal.debugger:Pdb  # IPython debugger
```

### Specific Test with Verbose

```python
pytest tests/unit/test_agent.py::test_save_food_entry -v -s
```

---

## Performance Testing

### Load Testing API

```bash
# Using locust
locust -f tests/load/locustfile.py --host=http://localhost:8080
```

### Database Query Performance

```python
import time

start = time.time()
results = await db.fetch_all(query)
elapsed = time.time() - start

assert elapsed < 0.1  # Query should complete in <100ms
```

---

## Test Data Management

### Test Data Fixtures

```python
# tests/fixtures/food_data.py
SAMPLE_FOOD_ENTRY = {
    "foods": [
        {"name": "chicken breast", "amount": "200g", "calories": 220}
    ],
    "total_calories": 220,
    "total_macros": {"protein": 46, "carbs": 0, "fat": 2.5}
}
```

### Database Cleanup

```python
@pytest.fixture(autouse=True)
async def cleanup_test_data():
    """Auto-cleanup after each test"""
    yield
    async with db_pool.connection() as conn:
        await conn.execute("DELETE FROM food_entries WHERE user_id LIKE 'test_%'")
```

---

## Related Documentation

- **Getting Started**: [getting-started.md](getting-started.md) - Development setup
- **CI/CD**: [/docs/deployment/ci-cd.md](../deployment/ci-cd.md) - Automated testing pipeline
- **API Reference**: [/docs/api/](../api/) - Endpoint specifications for API tests

## Revision History

- 2025-01-18: Initial testing guide created for Phase 3.7
