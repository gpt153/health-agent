# Phase 3.2: Test Coverage Enhancement Plan

## Executive Summary

This plan outlines the strategy to increase test coverage from 38% to 80% for the health-agent project. The codebase consists of:
- **Source code**: 83 Python files, ~24,867 lines of code
- **Current tests**: 38 test files, ~6,752 lines, 215 test cases
- **Coverage target**: 80% overall, with 85% per critical file
- **Estimated effort**: 300-400 new test cases across 5 phases

The plan focuses on:
1. Setting up comprehensive coverage infrastructure
2. Adding unit tests for untested business logic
3. Expanding integration test coverage
4. Implementing error injection and edge case testing
5. Establishing continuous coverage monitoring

---

## Current State Analysis

### Test Distribution
```
tests/
├── api/               (4 files)  - API endpoint tests
├── integration/       (10 files) - Integration and workflow tests
├── unit/             (17 files) - Unit tests for utilities and models
└── root/             (7 files)  - Gamification and memory architecture tests
```

### Coverage Gaps Identified

**High-Priority Untested Modules** (0% coverage):
- `/worktrees/health-agent/issue-78/src/handlers/message_handler.py` (0 lines - empty stub)
- `/worktrees/health-agent/issue-78/src/handlers/food_photo.py` (0 lines - empty stub)
- `/worktrees/health-agent/issue-78/src/handlers/settings.py` (0 lines - empty stub)
- `/worktrees/health-agent/issue-78/src/handlers/tracking.py` (0 lines - empty stub)
- `/worktrees/health-agent/issue-78/src/handlers/transparency.py` (0 lines - empty stub)

**Medium-Priority Partially Tested** (estimated <50% coverage):
- `/worktrees/health-agent/issue-78/src/db/queries.py` (3,270 lines, ~90 functions)
- `/worktrees/health-agent/issue-78/src/bot.py` (1,398 lines)
- `/worktrees/health-agent/issue-78/src/agent/__init__.py` (2,876 lines)
- `/worktrees/health-agent/issue-78/src/api/routes.py` (757 lines)
- `/worktrees/health-agent/issue-78/src/scheduler/reminder_manager.py` (514 lines)

**Gamification Modules** (partial coverage from phase 1/2 tests):
- Achievement system (501 lines)
- Challenges (640 lines)
- Dashboards (491 lines)
- Integrations (595 lines)
- Motivation profiles (453 lines)
- Streak system (278 lines)
- XP system (268 lines)

**Memory System** (basic tests exist):
- Answer extractor (59 lines)
- File manager (160 lines)
- Habit extractor (309 lines)
- Mem0 manager (199 lines)
- Retrieval (101 lines)
- System prompt (382 lines)

**Utilities** (partial coverage):
- Achievement checker (238 lines)
- Datetime helpers (420 lines)
- Estimate comparison (297 lines)
- Nutrition search (457 lines)
- Nutrition validation (418 lines)
- Query router (137 lines)
- Reminder formatters (357 lines)
- Timezone helper (122 lines)
- Typing indicator (82 lines)
- Vision (395 lines)
- Voice (41 lines)

---

## Phase 1: Setup & Infrastructure (Week 1)

### Task 1.1: Install Coverage Tooling
**Files to modify**: `/worktrees/health-agent/issue-78/requirements.txt`, `/worktrees/health-agent/issue-78/pytest.ini`

**Actions**:
1. Add to requirements.txt:
   ```
   pytest-cov>=5.0.0
   coverage[toml]>=7.4.0
   pytest-mock>=3.12.0
   pytest-xdist>=3.5.0  # Parallel test execution
   ```

2. Update pytest.ini:
   ```ini
   [pytest]
   testpaths = tests
   python_files = test_*.py
   python_classes = Test*
   python_functions = test_*
   asyncio_mode = auto
   addopts = -v --tb=short --cov=src --cov-report=html --cov-report=term --cov-report=json
   ```

3. Create `.coveragerc`:
   ```ini
   [run]
   source = src
   omit =
       */tests/*
       */migrations/*
       */__init__.py
       */config.py

   [report]
   exclude_lines =
       pragma: no cover
       def __repr__
       raise AssertionError
       raise NotImplementedError
       if __name__ == .__main__.:
       if TYPE_CHECKING:
       @abstract
   ```

**Success criteria**: Coverage reports generated successfully

### Task 1.2: Create Test Fixtures & Utilities
**New file**: `/worktrees/health-agent/issue-78/tests/conftest.py`

**Content**:
```python
"""Global test fixtures and utilities"""
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, date
from pathlib import Path
import tempfile

# Database fixtures
@pytest.fixture
async def mock_db_connection():
    """Mock database connection"""
    # Implementation

@pytest.fixture
async def test_user_id():
    """Standard test user ID"""
    return "test_user_123"

@pytest.fixture
def mock_telegram_update():
    """Mock Telegram Update object"""
    # Implementation

@pytest.fixture
def mock_telegram_context():
    """Mock Telegram Context object"""
    # Implementation

@pytest.fixture
async def mock_openai_client():
    """Mock OpenAI client"""
    # Implementation

@pytest.fixture
async def mock_anthropic_client():
    """Mock Anthropic client"""
    # Implementation

@pytest.fixture
def temp_data_dir():
    """Temporary data directory"""
    # Implementation

@pytest.fixture
def freeze_time():
    """Freeze time for testing"""
    # Implementation
```

**Estimated effort**: 2-3 days, ~500 lines of fixture code

### Task 1.3: CI/CD Integration
**File**: `/worktrees/health-agent/issue-78/.github/workflows/test.yml` (create if not exists)

**Actions**:
1. Add coverage step to CI workflow
2. Generate coverage badge
3. Upload coverage reports to artifacts
4. Add coverage PR comments

**Success criteria**: Coverage reports appear in PR checks

---

## Phase 2: Unit Test Expansion (Weeks 2-4)

### Module 2.1: Database Queries (`/worktrees/health-agent/issue-78/src/db/queries.py`)

**New file**: `/worktrees/health-agent/issue-78/tests/unit/test_db_queries.py`

**Coverage target**: 85% (90 functions to test)

**Test categories**:
1. **User operations** (3 functions):
   - test_create_user_new
   - test_create_user_existing
   - test_user_exists_true
   - test_user_exists_false

2. **Food entry operations** (5 functions):
   - test_save_food_entry_success
   - test_save_food_entry_invalid_macros
   - test_update_food_entry_success
   - test_update_food_entry_not_found
   - test_update_food_entry_wrong_user
   - test_get_recent_food_entries
   - test_get_food_entries_by_date

3. **Reminder operations** (10 functions):
   - test_create_reminder_basic
   - test_create_reminder_with_schedule
   - test_get_active_reminders
   - test_update_reminder_time
   - test_delete_reminder_success
   - test_delete_reminder_wrong_user
   - test_find_duplicate_reminders
   - test_deactivate_duplicate_reminders
   - test_calculate_current_streak
   - test_calculate_best_streak

4. **Gamification queries** (15 functions):
   - test_get_user_xp_data
   - test_update_user_xp
   - test_add_xp_transaction
   - test_get_user_streak
   - test_update_user_streak
   - test_get_all_achievements
   - test_unlock_achievement
   - test_has_user_unlocked_achievement
   - (continue for all gamification functions)

5. **Analytics queries** (12 functions):
   - test_get_reminder_analytics
   - test_analyze_day_of_week_patterns
   - test_detect_timing_patterns
   - test_detect_difficult_days
   - test_generate_adaptive_suggestions

**Estimated effort**: 150-200 test cases, ~2,000 lines

### Module 2.2: Gamification System

**Files to create**:
- `/worktrees/health-agent/issue-78/tests/unit/test_xp_system.py`
- `/worktrees/health-agent/issue-78/tests/unit/test_streak_system.py`
- `/worktrees/health-agent/issue-78/tests/unit/test_achievement_system.py`
- `/worktrees/health-agent/issue-78/tests/unit/test_challenges.py`
- `/worktrees/health-agent/issue-78/tests/unit/test_dashboards.py`
- `/worktrees/health-agent/issue-78/tests/unit/test_motivation_profiles.py`

**XP System tests** (~25 tests):
- Level calculation edge cases (0 XP, max level, boundary values)
- XP award with different sources
- Level up detection
- XP transaction logging
- Concurrent XP updates

**Streak System tests** (~30 tests):
- Streak increment
- Streak freeze usage
- Streak reset conditions
- Multi-day gap handling
- Timezone edge cases

**Achievement System tests** (~40 tests):
- Each achievement type unlocking
- Progress tracking
- Duplicate unlock prevention
- Achievement dependencies
- XP reward distribution

**Estimated effort**: 95 test cases, ~1,200 lines

### Module 2.3: Handlers

**Files to create**:
- `/worktrees/health-agent/issue-78/tests/unit/test_onboarding_handlers.py`
- `/worktrees/health-agent/issue-78/tests/unit/test_reminder_handlers.py`
- `/worktrees/health-agent/issue-78/tests/unit/test_sleep_quiz_handlers.py`
- `/worktrees/health-agent/issue-78/tests/unit/test_sleep_settings_handlers.py`

**Onboarding handler tests** (~20 tests):
- Path selection (Quick Start, Full Tour, Just Chat)
- Timezone setup
- Focus selection
- Language selection
- State transitions
- Completion flow

**Reminder handler tests** (~25 tests):
- Completion handling
- Skip with reason
- Snooze functionality
- Note addition
- Template selection
- Custom notes

**Sleep quiz tests** (~20 tests):
- Question progression
- Answer validation
- Score calculation
- Settings update
- Schedule management

**Estimated effort**: 65 test cases, ~800 lines

### Module 2.4: Agent & AI Integration

**Files to create**:
- `/worktrees/health-agent/issue-78/tests/unit/test_agent_init.py`
- `/worktrees/health-agent/issue-78/tests/unit/test_dynamic_tools.py`
- `/worktrees/health-agent/issue-78/tests/unit/test_gamification_tools.py`
- `/worktrees/health-agent/issue-78/tests/unit/test_nutrition_agents.py`

**Agent initialization tests** (~15 tests):
- get_agent_response basic flow
- Tool loading
- Memory integration
- Context building
- Error handling

**Dynamic tools tests** (~20 tests):
- Tool registration
- Tool execution
- Tool approval workflow
- Tool versioning
- Tool disabling/enabling

**Nutrition agent tests** (~25 tests):
- Consensus system
- Debate mechanism
- Validator logic
- Moderator decisions
- Multi-agent coordination

**Estimated effort**: 60 test cases, ~750 lines

### Module 2.5: Utilities

**Files to create**:
- `/worktrees/health-agent/issue-78/tests/unit/test_datetime_helpers.py`
- `/worktrees/health-agent/issue-78/tests/unit/test_reminder_formatters.py`
- `/worktrees/health-agent/issue-78/tests/unit/test_achievement_checker.py`
- `/worktrees/health-agent/issue-78/tests/unit/test_query_router.py`
- `/worktrees/health-agent/issue-78/tests/unit/test_typing_indicator.py`
- `/worktrees/health-agent/issue-78/tests/unit/test_voice.py`

**Datetime helpers tests** (~30 tests):
- UTC conversions
- User timezone handling
- Date parsing
- Time comparison
- DST transitions
- Leap year handling

**Reminder formatters tests** (~15 tests):
- Time formatting
- Completion message formatting
- Analytics display
- Streak display

**Achievement checker tests** (~20 tests):
- Achievement criteria evaluation
- Progress calculation
- Multi-condition checks

**Estimated effort**: 65 test cases, ~800 lines

### Module 2.6: Memory System

**Files to enhance**:
- `/worktrees/health-agent/issue-78/tests/unit/test_memory.py` (expand existing)
- New: `/worktrees/health-agent/issue-78/tests/unit/test_habit_extractor.py`
- New: `/worktrees/health-agent/issue-78/tests/unit/test_answer_extractor.py`
- New: `/worktrees/health-agent/issue-78/tests/unit/test_file_manager.py`

**Habit extractor tests** (~15 tests):
- Pattern detection
- Frequency analysis
- Habit extraction from conversations
- Edge cases (no habits, multiple habits)

**Answer extractor tests** (~10 tests):
- Answer parsing
- Context extraction
- Multi-turn conversations

**File manager tests** (~15 tests):
- File creation
- File reading
- File updates
- Directory management
- Error handling

**Estimated effort**: 40 test cases, ~500 lines

---

## Phase 3: Integration Tests (Week 5)

### Integration 3.1: End-to-End Bot Workflows

**Files to create**:
- `/worktrees/health-agent/issue-78/tests/integration/test_bot_message_flow.py`
- `/worktrees/health-agent/issue-78/tests/integration/test_photo_upload_flow.py`
- `/worktrees/health-agent/issue-78/tests/integration/test_voice_message_flow.py`

**Bot message flow tests** (~10 tests):
- New user message handling
- Existing user conversation
- Topic filtering
- Authorization checks
- Message history retrieval

**Photo upload flow tests** (~8 tests):
- Photo reception
- Vision analysis
- Food entry creation
- Gamification trigger
- Correction workflow

**Voice message flow tests** (~5 tests):
- Voice transcription
- Message processing
- Response generation

**Estimated effort**: 23 test cases, ~600 lines

### Integration 3.2: API + Database Integration

**Files to create**:
- `/worktrees/health-agent/issue-78/tests/integration/test_api_routes.py`
- `/worktrees/health-agent/issue-78/tests/integration/test_api_auth.py`

**API routes tests** (~20 tests):
- Chat endpoint with DB
- User profile CRUD
- Food log retrieval
- Reminder management
- Gamification endpoints
- Error responses

**API auth tests** (~8 tests):
- Valid API key
- Invalid API key
- Missing API key
- Rate limiting

**Estimated effort**: 28 test cases, ~700 lines

### Integration 3.3: Scheduler Integration

**File to create**: `/worktrees/health-agent/issue-78/tests/integration/test_reminder_scheduler.py`

**Tests** (~15 tests):
- Reminder scheduling
- Reminder execution
- Reminder rescheduling
- Sleep quiz scheduling
- Concurrent reminder handling

**Estimated effort**: 15 test cases, ~400 lines

---

## Phase 4: Error Injection & Edge Cases (Week 6)

### Error 4.1: Database Failure Scenarios

**File to create**: `/worktrees/health-agent/issue-78/tests/error_injection/test_db_failures.py`

**Tests** (~20 tests):
- Connection pool exhaustion
- Query timeout
- Deadlock detection
- Transaction rollback
- Connection failure mid-operation
- NULL constraint violations
- Foreign key violations
- Unique constraint violations

**Estimated effort**: 20 test cases, ~500 lines

### Error 4.2: External API Failures

**Files to create**:
- `/worktrees/health-agent/issue-78/tests/error_injection/test_openai_failures.py`
- `/worktrees/health-agent/issue-78/tests/error_injection/test_usda_api_failures.py`
- `/worktrees/health-agent/issue-78/tests/error_injection/test_telegram_api_failures.py`

**OpenAI failure tests** (~10 tests):
- Rate limiting (429)
- Timeout
- Invalid response
- Model unavailable
- Token limit exceeded

**USDA API tests** (~8 tests):
- API key invalid
- Rate limiting
- Malformed response
- No results found

**Telegram API tests** (~10 tests):
- Send message failure
- Upload photo failure
- Webhook failure
- User blocked bot

**Estimated effort**: 28 test cases, ~700 lines

### Error 4.3: Edge Cases & Boundary Conditions

**Files to create**:
- `/worktrees/health-agent/issue-78/tests/edge_cases/test_timezone_edge_cases.py`
- `/worktrees/health-agent/issue-78/tests/edge_cases/test_unicode_handling.py`
- `/worktrees/health-agent/issue-78/tests/edge_cases/test_concurrent_requests.py`
- `/worktrees/health-agent/issue-78/tests/edge_cases/test_data_limits.py`

**Timezone edge cases** (~15 tests):
- DST transitions
- Leap year dates
- Year boundaries (Dec 31 -> Jan 1)
- Cross-timezone reminders
- Invalid timezone strings

**Unicode handling** (~10 tests):
- Emoji in food names
- Multi-byte characters
- RTL languages
- Zero-width characters
- Surrogate pairs

**Concurrent requests** (~12 tests):
- Simultaneous XP updates
- Parallel food logging
- Race conditions in streaks
- Concurrent reminder completions

**Data limits** (~10 tests):
- Maximum food entries
- Very long messages
- Large file uploads
- Extremely high XP values
- Deep conversation history

**Estimated effort**: 47 test cases, ~1,200 lines

---

## Phase 5: Coverage Analysis & Documentation (Week 7)

### Task 5.1: Generate Coverage Reports

**Actions**:
1. Run full test suite with coverage
2. Generate HTML report
3. Identify remaining gaps
4. Document intentional exclusions

**Commands**:
```bash
pytest --cov=src --cov-report=html --cov-report=term-missing
coverage json
coverage report --show-missing
```

**Deliverables**:
- HTML coverage report
- JSON coverage data
- Gap analysis document

### Task 5.2: Add Coverage Badge

**File to update**: `/worktrees/health-agent/issue-78/README.md`

**Actions**:
1. Add shields.io badge
2. Link to coverage report
3. Document coverage targets

### Task 5.3: Create Testing Documentation

**File to create**: `/worktrees/health-agent/issue-78/docs/TESTING.md`

**Content**:
- How to run tests
- How to add new tests
- Fixture usage guide
- Mocking strategies
- Coverage requirements
- CI/CD integration

### Task 5.4: Document Intentional Exclusions

**File to create**: `/worktrees/health-agent/issue-78/docs/COVERAGE_EXCLUSIONS.md`

**Document**:
- Config file (no logic to test)
- __init__.py files (imports only)
- Migration scripts
- Development utilities
- Deprecated code paths

---

## File-by-File Coverage Targets

### Critical Files (85% target)

| File | Current Est. | Target | Priority | Test File |
|------|-------------|--------|----------|-----------|
| `src/db/queries.py` | 30% | 85% | Critical | `tests/unit/test_db_queries.py` |
| `src/agent/__init__.py` | 40% | 85% | Critical | `tests/unit/test_agent_init.py` |
| `src/bot.py` | 35% | 85% | Critical | `tests/integration/test_bot_message_flow.py` |
| `src/gamification/xp_system.py` | 60% | 85% | High | `tests/unit/test_xp_system.py` |
| `src/gamification/streak_system.py` | 55% | 85% | High | `tests/unit/test_streak_system.py` |
| `src/gamification/achievement_system.py` | 50% | 85% | High | `tests/unit/test_achievement_system.py` |
| `src/scheduler/reminder_manager.py` | 30% | 85% | High | `tests/integration/test_reminder_scheduler.py` |
| `src/api/routes.py` | 40% | 85% | High | `tests/integration/test_api_routes.py` |
| `src/utils/datetime_helpers.py` | 45% | 85% | High | `tests/unit/test_datetime_helpers.py` |
| `src/utils/nutrition_search.py` | 65% | 85% | Medium | Enhance existing |
| `src/utils/nutrition_validation.py` | 70% | 85% | Medium | Enhance existing |

### Important Files (75% target)

| File | Current Est. | Target | Priority | Test File |
|------|-------------|--------|----------|-----------|
| `src/handlers/onboarding.py` | 50% | 75% | Medium | Enhance `test_onboarding_flow.py` |
| `src/handlers/reminders.py` | 45% | 75% | Medium | `tests/unit/test_reminder_handlers.py` |
| `src/handlers/sleep_quiz.py` | 50% | 75% | Medium | Enhance existing |
| `src/memory/habit_extractor.py` | 30% | 75% | Medium | `tests/unit/test_habit_extractor.py` |
| `src/memory/file_manager.py` | 40% | 75% | Medium | `tests/unit/test_file_manager.py` |
| `src/gamification/challenges.py` | 35% | 75% | Medium | `tests/unit/test_challenges.py` |
| `src/gamification/dashboards.py` | 30% | 75% | Medium | `tests/unit/test_dashboards.py` |

### Supporting Files (70% target)

All other utility files, models, and supporting modules should reach 70% coverage minimum.

---

## Testing Patterns & Utilities

### Pattern 1: Database Test Pattern

```python
@pytest.fixture
async def mock_db_cursor():
    """Mock database cursor with standard query results"""
    cursor = AsyncMock()
    cursor.fetchone = AsyncMock(return_value={"id": 1, "user_id": "123"})
    cursor.fetchall = AsyncMock(return_value=[])
    return cursor

async def test_database_query(mock_db_cursor):
    """Test pattern for database queries"""
    with patch('src.db.connection.db.connection') as mock_conn:
        mock_conn.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value = mock_db_cursor
        # Test implementation
```

### Pattern 2: Telegram Handler Test Pattern

```python
@pytest.fixture
def telegram_update_factory():
    """Factory for creating mock Telegram updates"""
    def _create(text="", user_id="123", chat_type="private"):
        update = Mock()
        update.effective_user.id = int(user_id)
        update.message.text = text
        update.message.chat.type = chat_type
        update.message.reply_text = AsyncMock()
        return update
    return _create
```

### Pattern 3: Time-Based Test Pattern

```python
@pytest.fixture
def frozen_time():
    """Freeze time for deterministic testing"""
    frozen = datetime(2024, 1, 15, 12, 0, 0, tzinfo=ZoneInfo("UTC"))
    with patch('src.utils.datetime_helpers.now_utc', return_value=frozen):
        yield frozen
```

### Pattern 4: Error Injection Pattern

```python
async def test_database_connection_failure():
    """Test handling of database connection failures"""
    with patch('src.db.connection.db.connection', side_effect=psycopg.OperationalError("Connection failed")):
        with pytest.raises(DatabaseError):
            await some_function()
```

---

## Risk Assessment

### High Risks

1. **Database Connection Pool Management**
   - Risk: Tests may exhaust connection pool
   - Mitigation: Use fixtures to properly close connections, implement connection mocking

2. **Async Test Complexity**
   - Risk: Race conditions in async tests
   - Mitigation: Use pytest-asyncio properly, avoid real concurrency where possible

3. **External API Dependencies**
   - Risk: Tests calling real APIs
   - Mitigation: Mock all external API calls, use environment variable checks

4. **Test Execution Time**
   - Risk: >300 tests may take too long
   - Mitigation: Use pytest-xdist for parallelization, optimize slow tests

### Medium Risks

1. **Test Data Cleanup**
   - Risk: Tests leaving data in database
   - Mitigation: Use transactions with rollback, implement cleanup fixtures

2. **Timezone Handling in Tests**
   - Risk: Tests failing in different timezones
   - Mitigation: Always use UTC in tests, freeze time for determinism

3. **Coverage Gaming**
   - Risk: Tests that improve coverage without testing behavior
   - Mitigation: Code review focus on test quality, not just coverage percentage

---

## Success Criteria

### Quantitative Metrics
- [ ] Overall test coverage ≥ 80%
- [ ] Critical files coverage ≥ 85%
- [ ] Important files coverage ≥ 75%
- [ ] Supporting files coverage ≥ 70%
- [ ] Total test count ≥ 500 tests
- [ ] All tests pass in CI/CD
- [ ] Test execution time < 5 minutes

### Qualitative Metrics
- [ ] All database operations have error handling tests
- [ ] All external API calls are mocked
- [ ] All handlers have integration tests
- [ ] Edge cases documented and tested
- [ ] Testing documentation complete
- [ ] Coverage report accessible in CI

### Phase Completion Criteria

**Phase 1 Complete**:
- pytest-cov installed and configured
- conftest.py with core fixtures
- CI/CD running coverage reports

**Phase 2 Complete**:
- All critical modules ≥ 85% coverage
- All database functions tested
- All gamification modules tested

**Phase 3 Complete**:
- End-to-end workflows tested
- API integration tests complete
- Scheduler integration verified

**Phase 4 Complete**:
- Error injection tests for all external dependencies
- Edge cases documented and tested
- Concurrent operation tests implemented

**Phase 5 Complete**:
- Coverage reports generated
- Documentation updated
- Exclusions documented

---

## Implementation Sequence

### Week 1: Infrastructure
1. Install coverage tools
2. Create conftest.py
3. Set up CI/CD
4. Create test utilities

### Week 2: Database & Core
1. Test db/queries.py (150 tests)
2. Test bot.py integration (20 tests)
3. Test agent/__init__.py (15 tests)

### Week 3: Gamification
1. Test XP system (25 tests)
2. Test streak system (30 tests)
3. Test achievement system (40 tests)
4. Test challenges (20 tests)

### Week 4: Handlers & Utilities
1. Test all handlers (65 tests)
2. Test datetime helpers (30 tests)
3. Test other utilities (50 tests)
4. Test memory system (40 tests)

### Week 5: Integration
1. Bot workflow tests (23 tests)
2. API integration tests (28 tests)
3. Scheduler tests (15 tests)

### Week 6: Error & Edge Cases
1. Database failures (20 tests)
2. External API failures (28 tests)
3. Edge cases (47 tests)

### Week 7: Analysis & Documentation
1. Generate coverage reports
2. Fill remaining gaps
3. Document exclusions
4. Update README and docs

---

## Estimated Total Effort

- **New test files**: ~35 files
- **New test cases**: ~500 tests
- **Lines of test code**: ~10,000 lines
- **Time estimate**: 7 weeks (1 developer full-time)
- **Coverage increase**: 38% → 80%+ (42 percentage point increase)

---

## Maintenance Plan

### Ongoing Requirements
1. **Pre-commit hook**: Run tests before commit
2. **PR requirement**: Maintain coverage (no decrease)
3. **New feature requirement**: 80% coverage for new code
4. **Quarterly review**: Evaluate and update test suite
5. **Refactoring**: Update tests with code changes

### Coverage Monitoring
- Weekly coverage reports
- Alert on coverage decrease >2%
- Monthly review of slow tests
- Quarterly test suite optimization

---

## Notes & Recommendations

### Best Practices
1. **Write tests first** for bug fixes (TDD for bugs)
2. **Mock external dependencies** always
3. **Use fixtures** for common setup
4. **Test behavior**, not implementation
5. **Keep tests fast** (<5 min total)
6. **Document complex tests** with comments
7. **Use descriptive test names** (test_function_scenario_expectedResult)

### Anti-Patterns to Avoid
1. Testing private methods directly
2. Tests depending on execution order
3. Tests with sleep() calls
4. Tests that require manual setup
5. Tests with hardcoded timestamps
6. Overly complex test fixtures
7. Coverage for coverage's sake

### Future Enhancements
1. Property-based testing (hypothesis)
2. Mutation testing (mutmut)
3. Performance benchmarking
4. Load testing for API
5. Contract testing for API
6. Visual regression testing (if applicable)

---

## Appendix: Critical Files for Implementation

### Priority 1: Foundation

1. **tests/conftest.py** - Core test fixtures and utilities (does not exist, must create)
   - Database mocking
   - Telegram API mocking
   - AI client mocking
   - Time freezing utilities
   - Common test data

2. **.coveragerc** - Coverage configuration (must create)
   - Source paths
   - Exclusion rules
   - Report formats

3. **requirements.txt or pyproject.toml** - Add test dependencies
   - pytest-cov
   - pytest-mock
   - pytest-xdist
   - coverage

### Priority 2: Critical Module Tests

4. **tests/unit/test_db_queries.py** - Database query testing (must create)
   - Covers src/db/queries.py (3,270 lines, ~90 functions)
   - 150-200 test cases
   - Highest impact on coverage

5. **tests/unit/test_xp_system.py** - XP and leveling system (must create)
   - Covers src/gamification/xp_system.py
   - 25 test cases
   - Critical gamification logic

6. **tests/unit/test_streak_system.py** - Streak tracking system (must create)
   - Covers src/gamification/streak_system.py
   - 30 test cases
   - Time-sensitive logic

7. **tests/unit/test_achievement_system.py** - Achievement unlocking (must create)
   - Covers src/gamification/achievement_system.py
   - 40 test cases
   - Complex state management

### Priority 3: Integration Coverage

8. **tests/integration/test_bot_message_flow.py** - Bot end-to-end workflows (must create)
   - Covers src/bot.py integration
   - 10 test cases
   - Critical user-facing functionality

9. **tests/integration/test_api_routes.py** - API endpoint integration (must create)
   - Covers src/api/routes.py with database
   - 20 test cases
   - External interface testing

### Priority 4: Error Handling

10. **tests/error_injection/test_db_failures.py** - Database error scenarios (must create)
    - 20 test cases
    - Validates resilience

11. **tests/error_injection/test_openai_failures.py** - AI API error handling (must create)
    - 10 test cases
    - External dependency failures

### Source Files Requiring Most Attention

- **src/db/queries.py** (3,270 lines) - Largest file, most untested
- **src/bot.py** (1,398 lines) - Main bot logic, partially tested
- **src/agent/__init__.py** (2,876 lines) - AI agent core, needs coverage
- **src/api/routes.py** (757 lines) - API endpoints, partially tested
- **src/scheduler/reminder_manager.py** (514 lines) - Scheduler logic, untested