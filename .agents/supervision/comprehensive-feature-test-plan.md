# Comprehensive Feature Test Plan
**Created**: 2026-01-11
**Status**: Ready for Execution
**Delegated To**: Testing Subagent

## Test Environment

- **API Endpoint**: http://localhost:8080
- **Database**: PostgreSQL on localhost:5436
- **Bot**: Running in Docker (health-agent-bot)
- **API**: Running in Docker (health-agent-api)

## Mock User Details

**Test User ID**: `test_user_999888777`
**Purpose**: Comprehensive feature testing
**API Key**: `test_key_123` (from .env)

## Test Categories

### 1. System Health & Infrastructure

**Test 1.1: API Health Check**
- Endpoint: `GET /api/health`
- Expected: `{"status": "healthy", "database": "connected", "timestamp": "..."}`
- Validates: API is running, database connected

**Test 1.2: Database Connectivity**
- Direct PostgreSQL connection test
- Verify all tables exist: users, reminders, food_entries, user_xp, user_streaks, achievements, etc.
- Expected: All tables from migrations are present

### 2. User Management

**Test 2.1: Create Mock User**
- Endpoint: `POST /api/user`
- Payload: `{"telegram_id": "test_user_999888777", "username": "test_bot_user", "first_name": "Test", "language": "en"}`
- Expected: User created with initial XP record (level 1, 0 XP)
- Store: User details for subsequent tests

**Test 2.2: Retrieve User Data**
- Endpoint: `GET /api/user/test_user_999888777`
- Expected: User object with all fields
- Validates: User persistence

**Test 2.3: User Memory Storage**
- Check if user memory directory created: `data/test_user_999888777/`
- Expected: Directory exists

### 3. Reminder System (CRITICAL: No Duplicates)

**Test 3.1: Create Reminder**
- Endpoint: `POST /api/reminders`
- Payload: `{"user_id": "test_user_999888777", "message": "Test Medication", "schedule": "09:00", "enabled": true, "streak_motivation": true}`
- Expected: Reminder created with UUID
- Store: Reminder ID for subsequent tests

**Test 3.2: List User Reminders**
- Endpoint: `GET /api/reminders/test_user_999888777`
- Expected: Array with 1 reminder (the one just created)
- Validates: No duplicates

**Test 3.3: Complete Reminder**
- Endpoint: `POST /api/reminders/{reminder_id}/complete`
- Payload: `{"user_id": "test_user_999888777", "completed_at": "2026-01-11T09:15:00Z"}`
- Expected: Completion recorded
- Check: XP awarded (should see xp_transactions entry)
- Check: Streak updated (user_streaks table)

**Test 3.4: Verify No Duplicate Reminders**
- List reminders again
- Expected: Still only 1 reminder
- Validates: Critical bug fix - no duplicate reminder creation

**Test 3.5: Skip Reminder**
- Endpoint: `POST /api/reminders/{reminder_id}/skip`
- Payload: `{"user_id": "test_user_999888777", "reason": "Forgot", "skipped_at": "2026-01-11T09:30:00Z"}`
- Expected: Skip recorded, streak protection might apply

**Test 3.6: Snooze Reminder**
- Endpoint: `POST /api/reminders/{reminder_id}/snooze`
- Payload: `{"user_id": "test_user_999888777", "snooze_until": "2026-01-11T10:00:00Z"}`
- Expected: Snooze recorded

### 4. Food Logging & Nutrition

**Test 4.1: Log Food Entry (Text)**
- Endpoint: `POST /api/food`
- Payload: `{"user_id": "test_user_999888777", "description": "Chicken salad with avocado", "meal_type": "lunch", "logged_at": "2026-01-11T12:30:00Z"}`
- Expected: Food entry created
- Check: XP awarded for nutrition domain
- Check: Nutrition streak updated

**Test 4.2: Log Food Entry (Photo Analysis)**
- Note: Requires vision AI integration test
- Endpoint: `POST /api/food/photo`
- Payload: Image file + user_id
- Expected: Food entry with AI-analyzed nutrition data
- Skip if: API keys not configured

**Test 4.3: List User Food Entries**
- Endpoint: `GET /api/food/test_user_999888777`
- Expected: Array with food entries (at least 1 from Test 4.1)

### 5. Sleep Tracking

**Test 5.1: Log Sleep Entry**
- Endpoint: `POST /api/sleep`
- Payload: `{"user_id": "test_user_999888777", "sleep_time": "2026-01-10T22:00:00Z", "wake_time": "2026-01-11T06:30:00Z", "quality": "good"}`
- Expected: Sleep entry created
- Check: XP awarded for sleep domain
- Check: Sleep streak updated

**Test 5.2: Sleep Quiz Completion**
- Endpoint: `POST /api/sleep/quiz`
- Payload: Quiz answers (simplified test)
- Expected: Quiz completed, preferences stored

### 6. Gamification System

**Test 6.1: Check Initial XP**
- Endpoint: `GET /api/gamification/xp/test_user_999888777`
- Expected: XP record exists (level 1, some XP from previous tests)

**Test 6.2: Verify XP Transactions**
- Query: `SELECT * FROM xp_transactions WHERE user_id = 'test_user_999888777' ORDER BY awarded_at DESC`
- Expected: Multiple entries (reminder completion, food entry, sleep entry)
- Validates: XP is being awarded correctly

**Test 6.3: Check Streaks**
- Endpoint: `GET /api/gamification/streaks/test_user_999888777`
- Expected: Streaks for domains where activities completed (medication, nutrition, sleep)
- Each streak: current_streak = 1 (first day)

**Test 6.4: Verify Achievement Unlocks**
- Endpoint: `GET /api/gamification/achievements/test_user_999888777`
- Expected: "First Steps" achievement unlocked (first tracked activity)
- Check: Achievement XP bonus awarded

**Test 6.5: Level Progression Check**
- Calculate total XP from all activities
- Verify: User level matches expected progression
- Expected: If XP > 100, user should be level 2

**Test 6.6: Multi-Day Streak Simulation**
- Create activities for multiple consecutive days (simulate 7 days)
- Expected: "Week Warrior" achievement unlocked (7-day streak)
- Expected: Streak count = 7 for relevant domains

### 7. Tracking Categories

**Test 7.1: List Tracking Categories**
- Endpoint: `GET /api/tracking/categories/test_user_999888777`
- Expected: Default categories or user-specific categories

**Test 7.2: Create Custom Tracking Entry**
- Endpoint: `POST /api/tracking/entry`
- Payload: `{"user_id": "test_user_999888777", "category": "hydration", "value": "2000ml", "tracked_at": "2026-01-11T14:00:00Z"}`
- Expected: Entry created
- Check: XP awarded if category is gamified

### 8. Settings & Preferences

**Test 8.1: Get User Settings**
- Endpoint: `GET /api/settings/test_user_999888777`
- Expected: User preferences object

**Test 8.2: Update User Settings**
- Endpoint: `PUT /api/settings/test_user_999888777`
- Payload: `{"language": "en", "timezone": "America/New_York", "adaptive_timing": true}`
- Expected: Settings updated

**Test 8.3: Transparency (Data Export)**
- Endpoint: `GET /api/transparency/test_user_999888777`
- Expected: Complete data export (user info, reminders, food entries, XP, streaks, achievements)
- Validates: GDPR-like data access

### 9. Conversation History & Memory

**Test 9.1: Store Conversation Message**
- Endpoint: `POST /api/conversation`
- Payload: `{"user_id": "test_user_999888777", "message": "Test conversation", "role": "user"}`
- Expected: Message stored

**Test 9.2: Retrieve Conversation History**
- Endpoint: `GET /api/conversation/test_user_999888777`
- Expected: Array with conversation messages

**Test 9.3: Clear Conversation History**
- Endpoint: `DELETE /api/conversation/test_user_999888777`
- Expected: History cleared

### 10. Edge Cases & Error Handling

**Test 10.1: Duplicate User Creation**
- Attempt to create user with same telegram_id
- Expected: Error or idempotent success (user already exists)

**Test 10.2: Invalid API Key**
- Request without API key header
- Expected: 401 Unauthorized

**Test 10.3: Non-existent User**
- Request data for user_id that doesn't exist
- Expected: 404 Not Found

**Test 10.4: Invalid Data Formats**
- Submit malformed JSON
- Expected: 400 Bad Request with validation errors

## Success Criteria

### Critical Tests (Must Pass)
- ✅ API health check passes
- ✅ User creation and retrieval works
- ✅ Reminders: NO DUPLICATES (Test 3.4)
- ✅ XP is awarded for activities
- ✅ Streaks are tracked correctly
- ✅ At least one achievement unlocks

### Important Tests (Should Pass)
- Food logging works (text entry)
- Sleep tracking works
- Settings can be read/updated
- Conversation history persists

### Nice-to-Have Tests (Can Skip if Time-Limited)
- Photo analysis (requires API keys)
- Multi-day streak simulation
- All edge cases

## Reporting Format

For each test:
```json
{
  "test_id": "3.4",
  "name": "Verify No Duplicate Reminders",
  "status": "PASS | FAIL | SKIP",
  "result": "Description of what happened",
  "expected": "What was expected",
  "actual": "What actually occurred",
  "error": "Error message if failed",
  "evidence": "API response or database query result"
}
```

## Final Report Structure

```markdown
# Test Execution Report
**Date**: [timestamp]
**Total Tests**: X
**Passed**: X
**Failed**: X
**Skipped**: X

## Critical Issues Found
- [List any critical bugs]

## Summary by Category
- System Health: X/X passed
- User Management: X/X passed
- Reminder System: X/X passed (CRITICAL: duplicates check)
- Food Logging: X/X passed
- Sleep Tracking: X/X passed
- Gamification: X/X passed
- Settings: X/X passed

## Detailed Results
[Full test results for each test]

## Recommendations
[Next steps, fixes needed, etc.]
```

## Execution Notes

1. **Run tests sequentially** - Many tests depend on previous test data
2. **Store IDs** - Keep reminder_id, food_entry_id, etc. for dependent tests
3. **Database verification** - For critical tests, verify in database directly
4. **No cleanup between tests** - Keep mock user data to test retrieval
5. **Final cleanup** - Delete test user at end: `DELETE FROM users WHERE telegram_id = 'test_user_999888777'`

## Subagent Instructions

1. Execute each test category in order
2. Record all results in structured format
3. For failed tests, capture full error details
4. Take database snapshots for critical validations
5. Generate final report with recommendations
6. Store report in `.agents/supervision/test-execution-report-[timestamp].md`
