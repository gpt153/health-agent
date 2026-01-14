# Feature: Smart Conditional Reminders (Issue #41)

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Implement conditional reminder checks to prevent reminders from firing when the user has already completed the intended action. This makes reminders "smart" by checking user state before sending notifications, reducing notification spam and improving UX.

**Example**: User sets "Remind me to eat lunch if I haven't logged food by 12:00" → User logs food at 11:50 → Reminder checks condition at 12:00 → Condition met (food logged) → Skip reminder ✅

## User Story

As a health-conscious user
I want reminders to check if I've already completed the action
So that I don't receive unnecessary notifications when I've already done the task

## Problem Statement

Reminders currently fire at scheduled times regardless of whether the user has already completed the intended action. This causes notification spam and trains users to ignore reminders. The reminder system and food logging system are completely independent with no integration between the `reminders` and `food_entries` tables.

## Solution Statement

Implement a hybrid conditional checking system that evaluates TWO conditions before firing each reminder:

1. **Food Log Check**: Has user logged food in the last N hours? (configurable per reminder)
2. **Completion Check**: Has user marked reminder "Done" today? (existing completion tracking)

If EITHER condition is true → Skip reminder

This is achieved by:
- Adding a `check_condition` JSONB field to the `reminders` table
- Updating `_send_custom_reminder()` to query `food_entries` and `reminder_completions` before sending
- Maintaining backward compatibility (existing reminders without conditions work unchanged)

## Feature Metadata

**Feature Type**: Enhancement
**Estimated Complexity**: Medium
**Primary Systems Affected**: Scheduler (reminder_manager), Database (queries), Models (reminder)
**Dependencies**: None (uses existing tables)

---

## CONTEXT REFERENCES

### Relevant Codebase Files - IMPORTANT: YOU MUST READ THESE BEFORE IMPLEMENTING!

**Scheduler & Reminders:**
- `src/scheduler/reminder_manager.py` (367-453) - `_send_custom_reminder()` callback (add condition checks here)
- `src/scheduler/reminder_manager.py` (103-198) - `schedule_custom_reminder()` (understand scheduling)

**Database Queries:**
- `src/db/queries.py` (42-65, 187-201, 616-660) - Food entry queries (save, get_recent, get_by_date)
- `src/db/queries.py` (1441-1520) - Reminder completion queries (save, get_completions, calculate_streak)

**Models & Schema:**
- `src/models/reminder.py` (7-27) - Reminder/ReminderSchedule models
- `src/models/food.py` (38-49) - FoodEntry model
- `migrations/001_initial_schema.sql` (10-31) - food_entries & reminders tables

### New Files to Create

- `/worktrees/health-agent/issue-41/migrations/015_reminder_conditions.sql` - Add `check_condition` JSONB field to reminders table
- `/worktrees/health-agent/issue-41/tests/integration/test_conditional_reminders.py` - Integration tests for conditional reminder logic

### Relevant Documentation

- [PostgreSQL JSONB](https://www.postgresql.org/docs/current/datatype-json.html#JSON-CONTAINMENT) - JSONB operators/indexing for `check_condition`
- [Python timedelta](https://docs.python.org/3/library/datetime.html#datetime.timedelta) - Time window calculations
- [Pydantic Optional](https://docs.pydantic.dev/latest/concepts/models/#basic-model-usage) - Optional field patterns

### Key Patterns to Follow

**JSONB**: `json.dumps(obj.model_dump())` for write, `json.loads(col)` for read (see queries.py:261-292)
**Async Query**: `async with db.connection() as conn: async with conn.cursor() as cur: ...`
**DateTime**: Use `now_utc()` for storage, `to_user_timezone()` for display (src/utils/datetime_helpers.py)
**Logging**: `logger = logging.getLogger(__name__)` then `logger.info/debug/warning/error`
**Error Handling**: Try/except with `logger.error(..., exc_info=True)`, don't re-raise in callbacks
**Optional Fields**: `field: Optional[Type] = None` (Pydantic pattern)

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation - Database Schema

Add the `check_condition` JSONB field to store conditional logic configuration.

**Tasks:**
- Create migration to add `check_condition` column to `reminders` table
- Update `Reminder` model with new optional field

### Phase 2: Core Implementation - Condition Checking Logic

Implement the condition evaluation logic that queries food logs and completions.

**Tasks:**
- Add query function to check if food was logged in time window
- Add query function to check if reminder was completed today
- Update `_send_custom_reminder()` to evaluate conditions before sending

### Phase 3: Integration - Model Updates

Ensure the Reminder model properly handles the new field.

**Tasks:**
- Update Reminder Pydantic model with `check_condition` field
- Ensure backward compatibility (None = no conditions)

### Phase 4: Testing & Validation

Comprehensive testing of all condition types and edge cases.

**Tasks:**
- Create integration tests for food log conditions
- Create integration tests for completion conditions
- Test backward compatibility with existing reminders
- Manual validation with real reminder scenarios

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### CREATE migration file: `migrations/015_reminder_conditions.sql`

- **IMPLEMENT**: Add `check_condition` JSONB column to `reminders` table
- **PATTERN**: Follow JSONB column pattern from `schedule` field (001_initial_schema.sql:28)
- **IMPORTS**: None (SQL migration)
- **GOTCHA**: Use `ALTER TABLE ... ADD COLUMN ... DEFAULT NULL` to avoid updating existing rows
- **VALIDATE**: `psql $DATABASE_URL -c "\d reminders"` (check column exists)

**SQL**: `ALTER TABLE reminders ADD COLUMN check_condition JSONB DEFAULT NULL;` + comment describing structure

### UPDATE model: `src/models/reminder.py`

- **IMPLEMENT**: Add `check_condition: Optional[dict] = None` field to `Reminder` model
- **PATTERN**: Follow optional field pattern from `tracking_category_id` (reminder.py:24)
- **IMPORTS**: None (already imports Optional from typing)
- **GOTCHA**: Keep default as `None` for backward compatibility with existing reminders
- **VALIDATE**: `uv run python -c "from src.models.reminder import Reminder; print(Reminder.model_fields.keys())"` (check field exists)

**Code**: Add field `check_condition: Optional[dict] = None` after `streak_motivation` (line 26)

### CREATE query function: `src/db/queries.py` - `has_logged_food_in_window()`

- **IMPLEMENT**: Query function to check if user logged food within time window
- **PATTERN**: Mirror async query pattern from `get_food_entries_by_date()` (queries.py:616-660)
- **IMPORTS**: `from datetime import datetime, timedelta`, `from src.utils.datetime_helpers import now_utc`
- **GOTCHA**: Must use UTC for all timestamp comparisons (food_entries.timestamp is in UTC)
- **VALIDATE**: `uv run python -c "import asyncio; from src.db.queries import has_logged_food_in_window; asyncio.run(has_logged_food_in_window('test_user', 2))"` (test import)

**Logic**: Query `SELECT COUNT(*) FROM food_entries WHERE user_id=%s AND timestamp >= cutoff_time [AND meal_type=%s]`. Calculate `cutoff_time = now_utc() - timedelta(hours=window_hours)`. Return `count > 0`.

### CREATE query function: `src/db/queries.py` - `has_completed_reminder_today()`

- **IMPLEMENT**: Query function to check if user completed specific reminder today
- **PATTERN**: Mirror pattern from `get_reminder_completions()` (queries.py:1483-1520)
- **IMPORTS**: Already available (datetime imported above)
- **GOTCHA**: Must check for today in user's timezone, not UTC (use datetime_helpers)
- **VALIDATE**: `uv run python -c "import asyncio; from src.db.queries import has_completed_reminder_today; asyncio.run(has_completed_reminder_today('test_user', 'reminder_id'))"` (test import)

**Logic**: Query `SELECT COUNT(*) FROM reminder_completions WHERE user_id=%s AND reminder_id=%s AND completed_at >= today_start`. Calculate `today_start = (await now_user_timezone(user_id)).replace(hour=0,...)`. Return `count > 0`.

### UPDATE callback: `src/scheduler/reminder_manager.py` - `_send_custom_reminder()`

- **IMPLEMENT**: Add condition evaluation logic at start of callback (after day-of-week check)
- **PATTERN**: Follow error handling pattern from existing callback (lines 451-453)
- **IMPORTS**: `from src.db.queries import has_logged_food_in_window, has_completed_reminder_today`
- **GOTCHA**: Must check conditions AFTER day-of-week filter but BEFORE fetching reminder data
- **CRITICAL**: Preserve import order for side-effect imports (use `# ruff: noqa: I001` if needed)
- **VALIDATE**: Read the file and verify logic is correct before running tests

**Logic**: After line 390, fetch reminder_data and check `check_condition` field. If type=="food_logged", call `has_logged_food_in_window()` and return early if true. Also check `has_completed_reminder_today()` if tracking enabled. Log skip reason.

### REFACTOR callback: `src/scheduler/reminder_manager.py` - `_send_custom_reminder()`

- **IMPLEMENT**: Consolidate the two `get_reminder_by_id()` calls into one
- **PATTERN**: Move condition checks to use the same `reminder_data` as tracking logic
- **IMPORTS**: None (already imported above)
- **GOTCHA**: Ensure condition checks happen before building message text
- **VALIDATE**: Read file and confirm only ONE call to `get_reminder_by_id()` exists

**Refactor**: Consolidate to single `get_reminder_by_id()` call. Structure: (1) day-of-week check, (2) fetch reminder_data, (3) check conditions + return early if met, (4) calculate streak, (5) build message, (6) send with buttons.

### CREATE integration test: `tests/integration/test_conditional_reminders.py`

- **IMPLEMENT**: Comprehensive integration tests for all condition types
- **PATTERN**: Follow test structure from `test_food_correction.py` (tests/integration/test_food_correction.py:10-81)
- **IMPORTS**: `pytest`, `from src.db.queries import save_food_entry, create_reminder, has_logged_food_in_window, has_completed_reminder_today, save_reminder_completion`
- **GOTCHA**: Use unique user IDs with UUID to avoid test collisions
- **VALIDATE**: `uv run pytest tests/integration/test_conditional_reminders.py -v` (all tests pass)

**Test Cases** (8 tests total):
1. `test_food_logged_condition_met()` - Food logged 1h ago, 2h window → True
2. `test_food_logged_condition_not_met()` - Food logged 5h ago, 2h window → False
3. `test_food_logged_with_meal_type_filter()` - Breakfast logged, check lunch → False
4. `test_completion_condition_met()` - Reminder completed today → True
5. `test_completion_condition_not_met()` - No completion → False
6. `test_reminder_with_check_condition_stored()` - JSONB persists correctly
7. `test_backward_compatibility_no_condition()` - Reminder without condition → check_condition=None

**Pattern**: Follow `test_food_correction.py` structure - use `f"test_user_{uuid4()}"` for isolation, `await db.init_pool()` fixture, assert on query results.

---

## TESTING STRATEGY

Testing follows the project's pytest + pytest-asyncio framework with `asyncio_mode = auto`.

### Unit Tests

**Scope**: Individual query functions in isolation

- Test `has_logged_food_in_window()` with various time windows
- Test `has_completed_reminder_today()` with different completion states
- Test boundary conditions (exactly at window edge)

### Integration Tests

**Scope**: End-to-end conditional reminder workflows (see test file above)

**Key Test Cases**:
1. ✅ Food logged within window → Condition met
2. ✅ Food logged outside window → Condition not met
3. ✅ Food logged with meal type filter
4. ✅ Reminder completed today → Condition met
5. ✅ Reminder not completed today → Condition not met
6. ✅ Reminder with check_condition persists correctly
7. ✅ Backward compatibility: Reminders without conditions work unchanged

### Edge Cases

**Critical edge cases to test**:
- Time window exactly at boundary (2.000 hours vs 2.001 hours)
- Multiple food logs in window (should still return True)
- User in different timezone (Stockholm vs UTC)
- Invalid check_condition format (should gracefully skip condition check)
- Reminder without reminder_id (should work as before)
- Database query failures (should log error but not crash bot)

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Import Validation (CRITICAL)

**Verify all imports resolve before running tests:**

```bash
uv run python -c "from src.scheduler.reminder_manager import ReminderManager; from src.db.queries import has_logged_food_in_window, has_completed_reminder_today; print('✓ All imports valid')"
```

**Expected:** "✓ All imports valid" (no ModuleNotFoundError or ImportError)

**Why:** Catches incorrect imports immediately. If this fails, fix imports before proceeding.

### Level 2: Database Migration

**Apply migration and verify schema:**

```bash
psql $DATABASE_URL -f migrations/015_reminder_conditions.sql
psql $DATABASE_URL -c "\d reminders" | grep check_condition
```

**Expected:** Output shows `check_condition | jsonb |` column

### Level 3: Model Validation

**Verify Pydantic model accepts new field:**

```bash
uv run python -c "
from src.models.reminder import Reminder, ReminderSchedule
r = Reminder(
    user_id='test',
    reminder_type='simple',
    message='Test',
    schedule=ReminderSchedule(type='daily', time='12:00'),
    check_condition={'type': 'food_logged', 'window_hours': 2}
)
print(f'✓ Model validation passed: {r.check_condition}')
"
```

**Expected:** "✓ Model validation passed: {'type': 'food_logged', 'window_hours': 2}"

### Level 4: Unit Tests

**Run integration tests for conditional reminder logic:**

```bash
uv run pytest tests/integration/test_conditional_reminders.py -v
```

**Expected:** All 8 tests pass

### Level 5: Full Test Suite

**Ensure no regressions in existing tests:**

```bash
uv run pytest tests/ -v --tb=short
```

**Expected:** All tests pass (including new conditional reminder tests)

### Level 6: Manual Validation

**End-to-end test:** Insert conditional reminder via SQL → Log food within window → Verify no reminder fires (check logs for "Skipping reminder") → Next day without food log → Reminder fires

---

## ACCEPTANCE CRITERIA

- [x] Migration adds `check_condition` JSONB field to reminders table
- [x] Reminder model accepts optional `check_condition` field
- [x] `has_logged_food_in_window()` correctly queries food_entries within time window
- [x] `has_completed_reminder_today()` correctly checks reminder_completions for today
- [x] `_send_custom_reminder()` evaluates conditions and skips when met
- [x] Food log condition with meal type filter works correctly
- [x] Completion condition checked for all tracking-enabled reminders
- [x] Backward compatible: Existing reminders without conditions work unchanged
- [x] All validation commands pass with zero errors
- [x] Integration tests cover all condition types and edge cases
- [x] No regressions in existing reminder functionality
- [x] Logging provides clear debugging information for condition checks

---

## COMPLETION CHECKLIST

- [ ] Migration file created and applied successfully
- [ ] Reminder model updated with check_condition field
- [ ] Query functions implemented: has_logged_food_in_window, has_completed_reminder_today
- [ ] _send_custom_reminder callback updated with condition logic
- [ ] Integration tests created and passing (8 tests)
- [ ] Import validation passes
- [ ] Model validation passes
- [ ] Full test suite passes (no regressions)
- [ ] Manual testing confirms conditional reminders work
- [ ] Logging messages provide clear debugging information
- [ ] Code reviewed for quality and maintainability

---

## NOTES

**Design Decisions:**
- JSONB allows flexibility for future condition types without schema changes
- Conditions checked at fire time (not schedule time) since user state changes
- Completions checked separately (applies to all reminders, not just food)

**Future Enhancements:** exercise_logged, water_consumed, weight_recorded, natural language condition setting, analytics

**Performance:** Adds 1-2 indexed DB queries per conditional reminder at fire time only. Negligible impact.

**Security:** None - user_id scoped queries, no external APIs, no user input in check_condition
