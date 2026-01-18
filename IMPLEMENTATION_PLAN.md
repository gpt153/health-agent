# Implementation Plan: API Integration Tests (Issue #73)

## Overview
Add comprehensive integration tests for all API endpoints to ensure proper request/response handling, authentication, error paths, and edge cases.

**Priority:** MEDIUM
**Estimated Time:** 4 hours
**Epic:** 007 - Phase 2 High-Priority Refactoring

## Analysis

### Current State
- **API Endpoints Identified:** 23 endpoints across 4 categories
  - Chat: 1 endpoint
  - User Profile: 8 endpoints
  - Food Tracking: 2 endpoints
  - Reminders: 4 endpoints
  - Gamification: 3 endpoints
  - Health Check: 1 endpoint
- **Existing Test Structure:**
  - `/tests/api/` exists with 4 test files (chat, reminders, memory, gamification)
  - `/tests/integration/` exists with 9 workflow tests
  - `pytest.ini` configured with `asyncio_mode = auto`
  - Existing tests use `httpx.AsyncClient` for API testing
- **Testing Framework:** pytest with pytest-asyncio
- **Authentication:** API key-based via `Authorization: Bearer <token>` header

### API Routes to Test

#### 1. Chat Endpoint (`/api/v1/chat`)
- **Method:** POST
- **Auth:** Required
- **Success Cases:**
  - Basic message handling
  - Message with history
  - New user creation
  - Conversation persistence
- **Error Cases:**
  - Missing authentication
  - Invalid API key
  - Missing required fields
  - Empty message
  - Malformed request body

#### 2. User Profile Endpoints
- **POST** `/api/v1/users` - Create user
- **GET** `/api/v1/users/{user_id}` - Get user profile
- **DELETE** `/api/v1/users/{user_id}` - Delete user
- **GET** `/api/v1/users/{user_id}/profile` - Get profile
- **PATCH** `/api/v1/users/{user_id}/profile` - Update profile field
- **GET** `/api/v1/users/{user_id}/preferences` - Get preferences
- **PATCH** `/api/v1/users/{user_id}/preferences` - Update preferences
- **DELETE** `/api/v1/users/{user_id}/conversation` - Clear conversation

**Success Cases:**
- CRUD operations for users
- Profile field updates
- Preference management
- Data persistence

**Error Cases:**
- User not found (404)
- Duplicate user creation (400)
- Invalid user_id format
- Missing authentication
- Unauthorized access

#### 3. Food Tracking Endpoints
- **POST** `/api/v1/users/{user_id}/food` - Log food entry
- **GET** `/api/v1/users/{user_id}/food` - Get food summary

**Success Cases:**
- Food logging with description
- Food logging with timestamp
- Retrieve food summary by date
- Default to current date
- Calculate totals (calories, macros)

**Error Cases:**
- User not found
- Invalid date format
- Missing description
- Empty food entries

#### 4. Reminder Endpoints
- **POST** `/api/v1/users/{user_id}/reminders` - Create reminder
- **GET** `/api/v1/users/{user_id}/reminders` - List reminders
- **GET** `/api/v1/users/{user_id}/reminders/{reminder_id}/status` - Get reminder status

**Success Cases:**
- Create daily reminder
- Create one-time reminder
- List active reminders
- Check reminder status
- Timezone handling

**Error Cases:**
- Invalid reminder type
- Missing time configuration
- Invalid reminder_id
- Reminder not found
- User mismatch

#### 5. Gamification Endpoints
- **GET** `/api/v1/users/{user_id}/xp` - Get XP and level
- **GET** `/api/v1/users/{user_id}/streaks` - Get streaks
- **GET** `/api/v1/users/{user_id}/achievements` - Get achievements

**Success Cases:**
- Retrieve XP and level info
- Retrieve active streaks
- List unlocked/locked achievements

**Error Cases:**
- User not found
- No gamification data

#### 6. Health Check Endpoint
- **GET** `/api/health` - Health check

**Success Cases:**
- Service healthy
- Database connected

**Error Cases:**
- Database disconnected (degraded status)

## Implementation Strategy

### Phase 1: Test Infrastructure Setup
**Time:** 30 minutes

1. **Create test fixtures file:** `tests/integration/conftest.py`
   - Shared fixtures for API testing
   - Test API client with authentication
   - Test user management (create/cleanup)
   - Database connection fixture
   - Mock services where needed

2. **Create shared utilities:** `tests/integration/api_helpers.py`
   - Helper functions for common operations
   - Assertion utilities
   - Test data generators
   - Response validation helpers

### Phase 2: Chat Endpoint Tests
**Time:** 45 minutes

**File:** `tests/integration/test_api_chat.py`

**Tests to implement:**
- `test_chat_basic_message()` - Simple message/response
- `test_chat_with_message_history()` - Context preservation
- `test_chat_creates_new_user()` - Auto user creation
- `test_chat_saves_conversation()` - Persistence check
- `test_chat_without_auth()` - 403 response
- `test_chat_invalid_api_key()` - 401 response
- `test_chat_empty_message()` - 400 response
- `test_chat_malformed_request()` - 422 response
- `test_chat_missing_user_id()` - 422 response

**Target:** 9+ tests

### Phase 3: User Profile Tests
**Time:** 60 minutes

**File:** `tests/integration/test_api_users.py`

**Tests to implement:**
- `test_create_user()` - User creation
- `test_create_duplicate_user()` - 400 error
- `test_get_user()` - Retrieve profile and preferences
- `test_get_nonexistent_user()` - 404 error
- `test_delete_user()` - User deletion
- `test_delete_nonexistent_user()` - 404 error
- `test_get_user_profile()` - Profile retrieval
- `test_update_profile_field()` - Field update
- `test_update_multiple_profile_fields()` - Multiple updates
- `test_get_user_preferences()` - Preferences retrieval
- `test_update_preferences()` - Preference update
- `test_clear_conversation()` - Conversation history clear
- `test_user_without_auth()` - Auth required
- `test_profile_persistence()` - Data persists

**Target:** 14+ tests

### Phase 4: Food Tracking Tests
**Time:** 45 minutes

**File:** `tests/integration/test_api_food.py`

**Tests to implement:**
- `test_log_food_basic()` - Simple food logging
- `test_log_food_with_timestamp()` - Custom timestamp
- `test_log_food_creates_entry()` - Entry persisted
- `test_get_food_summary_today()` - Current day summary
- `test_get_food_summary_specific_date()` - Date parameter
- `test_get_food_summary_empty()` - No entries case
- `test_food_summary_calculations()` - Totals accuracy
- `test_food_nonexistent_user()` - 404 error
- `test_food_invalid_date_format()` - 400 error
- `test_food_without_auth()` - Auth required

**Target:** 10+ tests

### Phase 5: Reminder Tests
**Time:** 45 minutes

**File:** `tests/integration/test_api_reminders.py`

**Tests to implement:**
- `test_create_daily_reminder()` - Daily reminder
- `test_create_onetime_reminder()` - One-time reminder
- `test_create_reminder_with_timezone()` - Timezone handling
- `test_list_reminders()` - List all reminders
- `test_list_reminders_empty()` - No reminders case
- `test_get_reminder_status()` - Status check
- `test_get_reminder_status_not_found()` - 404 error
- `test_create_reminder_invalid_type()` - 400 error
- `test_create_reminder_missing_time()` - 400 error
- `test_reminder_user_mismatch()` - Security check
- `test_reminders_without_auth()` - Auth required

**Target:** 11+ tests

### Phase 6: Gamification Tests
**Time:** 30 minutes

**File:** `tests/integration/test_api_gamification.py`

**Tests to implement:**
- `test_get_xp_basic()` - XP retrieval
- `test_get_xp_new_user()` - Default XP values
- `test_get_xp_nonexistent_user()` - 404 error
- `test_get_streaks()` - Streaks retrieval
- `test_get_streaks_empty()` - No streaks case
- `test_get_achievements()` - Achievements list
- `test_achievements_locked_unlocked()` - Both states
- `test_gamification_without_auth()` - Auth required

**Target:** 8+ tests

### Phase 7: Health Check Tests
**Time:** 15 minutes

**File:** `tests/integration/test_api_health.py`

**Tests to implement:**
- `test_health_check_healthy()` - All systems operational
- `test_health_check_no_auth_required()` - Public endpoint
- `test_health_check_structure()` - Response format

**Target:** 3+ tests

### Phase 8: Edge Cases & Integration
**Time:** 15 minutes

**Add to existing test files:**
- Rate limiting tests
- CORS validation
- Concurrent request handling
- Large payload handling
- Timeout scenarios

**Target:** 5+ tests

## Test Fixtures Design

### `conftest.py` fixtures:

```python
@pytest.fixture
async def api_client():
    """Async HTTP client with base configuration"""

@pytest.fixture
async def auth_headers():
    """Valid authentication headers"""

@pytest.fixture
async def test_user():
    """Create test user, yield user_id, cleanup after"""

@pytest.fixture
async def test_users():
    """Create multiple test users"""

@pytest.fixture
async def db_connection():
    """Database connection for direct validation"""

@pytest.fixture
async def cleanup_user():
    """Cleanup helper for user deletion"""
```

## Success Metrics

- **Total Tests:** 60+ integration tests
- **Coverage:** >80% of API endpoint code paths
- **Test Categories:**
  - Success paths: ~35 tests
  - Error paths: ~20 tests
  - Edge cases: ~5 tests
- **All tests pass:** ✅
- **Execution time:** <2 minutes for full suite
- **No flaky tests:** All deterministic

## Technical Considerations

### Authentication
- Use valid test API key in fixtures
- Test both valid and invalid keys
- Ensure public endpoints don't require auth

### Database State
- Each test should be isolated
- Use fixtures for setup/teardown
- Consider transaction rollback for fast cleanup

### Async Testing
- All API calls are async
- Use `pytest.mark.asyncio` decorator
- Leverage `asyncio_mode = auto` from pytest.ini

### Test Data
- Use unique user IDs per test to avoid collisions
- Consider parameterized tests for variations
- Mock external dependencies (LLM API, etc.)

### Error Simulation
- Test database disconnection
- Test timeout scenarios
- Test malformed requests

## Files to Create/Modify

### New Files
1. `tests/integration/conftest.py` - Shared fixtures
2. `tests/integration/api_helpers.py` - Utility functions
3. `tests/integration/test_api_chat.py` - Chat endpoint tests
4. `tests/integration/test_api_users.py` - User profile tests
5. `tests/integration/test_api_food.py` - Food tracking tests
6. `tests/integration/test_api_reminders.py` - Reminder tests
7. `tests/integration/test_api_gamification.py` - Gamification tests
8. `tests/integration/test_api_health.py` - Health check tests

### Modified Files
- None (purely additive)

## Testing the Tests

1. **Run full suite:** `pytest tests/integration/test_api_*.py -v`
2. **Run specific category:** `pytest tests/integration/test_api_chat.py -v`
3. **Run with coverage:** `pytest tests/integration/test_api_*.py --cov=src/api --cov-report=html`
4. **Check for slow tests:** `pytest tests/integration/test_api_*.py --durations=10`

## Dependencies

- `pytest` ✅ (already installed)
- `pytest-asyncio` ✅ (already configured)
- `httpx` ✅ (already used in existing tests)
- `psycopg` ✅ (database driver)

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Tests affect production data | HIGH | Use test-specific user IDs, cleanup fixtures |
| Flaky tests due to async timing | MEDIUM | Use proper awaits, timeouts, retries |
| Database state pollution | MEDIUM | Isolated test data, transaction rollback |
| API server not running | HIGH | Document startup requirements, add health check |
| Slow test execution | LOW | Optimize fixtures, parallel execution |

## Execution Order

1. ✅ Phase 1: Test Infrastructure (conftest.py, helpers)
2. ✅ Phase 2: Chat Endpoint Tests
3. ✅ Phase 3: User Profile Tests
4. ✅ Phase 4: Food Tracking Tests
5. ✅ Phase 5: Reminder Tests
6. ✅ Phase 6: Gamification Tests
7. ✅ Phase 7: Health Check Tests
8. ✅ Phase 8: Edge Cases & Integration
9. ✅ Run full test suite and validate coverage
10. ✅ Document results and update issue

## Completion Checklist

- [ ] All 8 test files created
- [ ] Fixtures and helpers implemented
- [ ] 60+ tests written
- [ ] All tests pass locally
- [ ] Coverage >80% of API routes
- [ ] No flaky tests
- [ ] Tests run in <2 minutes
- [ ] Documentation updated
- [ ] PR ready for review

## Next Steps After Implementation

1. Run test suite: `pytest tests/integration/test_api_*.py -v`
2. Generate coverage report: `pytest --cov=src/api --cov-report=html`
3. Review coverage gaps
4. Add any missing edge cases
5. Update epic-007 tracker
6. Create PR with test results
