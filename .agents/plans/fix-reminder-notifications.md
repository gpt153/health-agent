# Feature: Fix Reminder Notifications Not Being Sent

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

The reminder notification system has stopped working - users are not receiving scheduled reminder notifications despite active reminders existing in the database. This requires a root cause analysis (RCA) to identify whether the issue is in the scheduler initialization, database queries, Telegram API delivery, or job queue configuration, followed by implementing the necessary fix.

## User Story

As a user of the health-agent bot
I want to receive my scheduled reminder notifications at the configured times
So that I can stay on track with my health goals and medication schedules

## Problem Statement

The reminder system has completely stopped sending notifications to users. Despite having active reminders configured in the database, no reminder notifications are being delivered via Telegram. This is a critical bug affecting core functionality - users are missing medication reminders, food tracking prompts, sleep reminders, and custom tracking notifications.

## Solution Statement

Conduct a systematic root cause analysis to identify why the reminder scheduler is not triggering notifications, then implement a fix to restore reminder functionality. The investigation will examine:
1. Scheduler initialization during bot startup
2. JobQueue configuration and job registration
3. Database query execution and reminder loading
4. Telegram API delivery and error handling
5. Timezone and timing calculations

## Feature Metadata

**Feature Type**: Bug Fix
**Estimated Complexity**: Medium
**Primary Systems Affected**:
- Scheduler system (`src/scheduler/reminder_manager.py`)
- Bot initialization (`src/main.py`, `src/bot.py`)
- Database queries (`src/db/queries/reminders.py`)
- Telegram notification delivery

**Dependencies**:
- python-telegram-bot[job-queue]
- psycopg[binary]
- zoneinfo (stdlib)

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `src/scheduler/reminder_manager.py` (lines 1-515) - Core reminder scheduling logic, ReminderManager class
- `src/main.py` (lines 25-64) - Bot startup and reminder loading sequence
- `src/bot.py` (lines 1526-1599) - Bot application creation, ReminderManager initialization
- `src/db/queries/reminders.py` (lines 17-58, 393-425) - Reminder database operations
- `src/handlers/reminders.py` - Reminder callback handlers (completion, skip, snooze)
- `src/models/reminder.py` (lines 1-110) - Reminder data models and validation
- `tests/integration/test_conditional_reminders.py` - Test patterns for reminder functionality

### New Files to Create

- `.agents/rca/reminder-notification-failure.md` - Root cause analysis document
- `tests/integration/test_reminder_scheduler.py` - Integration tests for scheduler initialization and job execution

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [python-telegram-bot JobQueue Documentation](https://docs.python-telegram-bot.org/en/stable/telegram.ext.jobqueue.html)
  - Specific section: JobQueue scheduling and callback execution
  - Why: Understanding job scheduling patterns and potential failure points
- [python-telegram-bot Application Lifecycle](https://docs.python-telegram-bot.org/en/stable/telegram.ext.application.html#application-lifecycle)
  - Specific section: Application initialization sequence
  - Why: Ensures reminder loading happens at correct lifecycle stage

### Patterns to Follow

**Scheduler Initialization Pattern:**
```python
# From src/main.py (lines 38-45)
# Load reminders from database (after bot is started)
from src.bot import reminder_manager
if reminder_manager:
    logger.info("Loading reminders from database...")
    await reminder_manager.load_reminders()

    # Load sleep quiz schedules
    logger.info("Loading sleep quiz schedules...")
    await reminder_manager.load_sleep_quiz_schedules()
```

**Job Scheduling Pattern:**
```python
# From src/scheduler/reminder_manager.py (lines 144-156)
self.job_queue.run_daily(
    callback=self._send_custom_reminder,
    time=scheduled_time,
    data={
        "user_id": user_id,
        "message": message,
        "reminder_id": reminder_id,
        "scheduled_time": reminder_time,
        "timezone": user_timezone,
        "days": days
    },
    name=f"custom_reminder_{reminder_id}",
)
```

**Error Handling Pattern:**
```python
# From src/scheduler/reminder_manager.py (lines 482-484)
except Exception as e:
    logger.error(f"Failed to send custom reminder: {e}", exc_info=True)
```

**Logging Pattern:**
```python
# From src/scheduler/reminder_manager.py
logger.info(f"Loaded and scheduled {scheduled_count} reminders from database")
logger.error(f"Failed to load reminders: {e}", exc_info=True)
```

**Database Query Pattern:**
```python
# From src/db/queries/reminders.py (lines 50-57)
async def get_active_reminders_all() -> list[dict]:
    """Get all active reminders for all users"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT * FROM reminders WHERE active = true ORDER BY user_id"
            )
            return await cur.fetchall()
```

---

## IMPLEMENTATION PLAN

### Phase 1: Root Cause Analysis

Systematically investigate all potential failure points in the reminder system to identify the root cause.

**Tasks:**

- Verify database state and reminder configuration
- Check scheduler initialization sequence
- Inspect job queue registration
- Review logs for errors and warnings
- Test Telegram API connectivity

### Phase 2: Fix Implementation

Based on RCA findings, implement the necessary fix to restore reminder notifications.

**Tasks:**

- Address identified root cause
- Add defensive error handling
- Improve logging for observability
- Add validation checks

### Phase 3: Testing & Validation

Ensure the fix works correctly and prevent future regressions.

**Tasks:**

- Create integration tests for scheduler
- Test end-to-end reminder delivery
- Verify all reminder types work (daily, once, conditional)
- Validate timezone handling

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Phase 1: Root Cause Analysis

#### Task 1: CREATE RCA Document

- **IMPLEMENT**: Create structured RCA document to track investigation
- **CREATE**: `.agents/rca/reminder-notification-failure.md`
- **PATTERN**: Use systematic investigation methodology
- **STRUCTURE**:
```markdown
# Root Cause Analysis: Reminder Notifications Not Sent

## Investigation Date
[Current date]

## Symptoms
- No reminder notifications delivered
- Active reminders exist in database
- No obvious errors in logs

## Investigation Steps

### 1. Database State Verification
[Findings go here]

### 2. Scheduler Initialization Check
[Findings go here]

### 3. Job Queue Registration
[Findings go here]

### 4. Telegram API Connectivity
[Findings go here]

## Root Cause
[Final determination]

## Fix Implementation
[Solution applied]
```

#### Task 2: INVESTIGATE Database State

- **IMPLEMENT**: Check database for active reminders and verify data integrity
- **RUN**: Database query to count active reminders
- **CHECK**: Reminder schedule JSON is valid
- **CHECK**: User IDs match expected format
- **DOCUMENT**: Findings in RCA under "Database State Verification"
- **VALIDATE**: `echo "SELECT COUNT(*) FROM reminders WHERE active = true;" | psql -d health_agent` (should show count > 0)

#### Task 3: INVESTIGATE Scheduler Initialization

- **IMPLEMENT**: Trace bot startup sequence for reminder loading
- **CHECK**: `src/main.py` lines 38-45 - is `load_reminders()` called?
- **CHECK**: `src/bot.py` lines 1536-1537 - is ReminderManager initialized?
- **CHECK**: Is `reminder_manager` global variable properly set?
- **REVIEW**: Application lifecycle - when does `load_reminders()` execute?
- **ADD**: Debug logging to trace execution flow
- **DOCUMENT**: Findings in RCA under "Scheduler Initialization Check"
- **GOTCHA**: `load_reminders()` must execute AFTER `app.start()` completes (line 35), otherwise job_queue may not be ready

#### Task 4: INVESTIGATE Job Queue State

- **IMPLEMENT**: Verify JobQueue is initialized and jobs are registered
- **CHECK**: `self.job_queue` is not None in ReminderManager.__init__
- **CHECK**: `app.job_queue` exists after application initialization
- **ADD**: Logging to show job count after `load_reminders()`
- **TEST**: Job queue accepts job registration
- **DOCUMENT**: Findings in RCA under "Job Queue Registration"
- **VALIDATE**: Add `logger.info(f"Job queue has {len(self.job_queue.jobs())} jobs")` after load_reminders

#### Task 5: INVESTIGATE Callback Execution

- **IMPLEMENT**: Verify reminder callbacks are being invoked
- **ADD**: Debug logging at start of `_send_custom_reminder()` method
- **CHECK**: Are callbacks registered correctly?
- **CHECK**: Are timezone calculations correct?
- **CHECK**: Are day filters preventing execution?
- **CHECK**: Are conditional checks blocking reminders?
- **DOCUMENT**: Findings in RCA under "Callback Execution"
- **GOTCHA**: Current weekday check (lines 380-392) may silently skip reminders

#### Task 6: INVESTIGATE Telegram API Delivery

- **IMPLEMENT**: Verify Telegram bot can send messages
- **TEST**: Send test message via `context.bot.send_message()`
- **CHECK**: Bot token is valid and active
- **CHECK**: User IDs are valid Telegram chat IDs
- **CHECK**: No rate limiting or API errors
- **DOCUMENT**: Findings in RCA under "Telegram API Connectivity"
- **VALIDATE**: `curl -X POST https://api.telegram.org/bot<TOKEN>/sendMessage -d chat_id=<USER_ID> -d text="Test"`

#### Task 7: ANALYZE Logs for Patterns

- **IMPLEMENT**: Search logs for reminder-related entries
- **RUN**: `grep -i "reminder\|schedule" logs/bot.log | tail -200`
- **LOOK FOR**: "Loading reminders", "Scheduled X reminders", error messages
- **LOOK FOR**: Silent failures (missing expected log entries)
- **CHECK**: Last successful reminder notification timestamp
- **DOCUMENT**: Key log findings in RCA
- **GOTCHA**: Absence of logs is as important as presence of errors

#### Task 8: IDENTIFY Root Cause

- **IMPLEMENT**: Synthesize investigation findings into root cause determination
- **ANALYZE**: All evidence gathered from Tasks 2-7
- **DETERMINE**: Single most likely root cause or combination of factors
- **DOCUMENT**: Complete "Root Cause" section in RCA document
- **EXAMPLE CAUSES**:
  - JobQueue not initialized before `load_reminders()` called
  - Application lifecycle order issue (loading before `app.start()`)
  - Silent exception swallowing in try/except blocks
  - Timezone calculation breaking job scheduling
  - Day filter always evaluating to False

### Phase 2: Fix Implementation

**NOTE**: The following tasks are conditional based on RCA findings. Implement only the tasks relevant to the identified root cause.

#### Task 9A: FIX Scheduler Initialization (If RCA identifies lifecycle issue)

- **IMPLEMENT**: Ensure reminder loading happens at correct application lifecycle stage
- **UPDATE**: `src/main.py` - Move `load_reminders()` to correct position
- **PATTERN**: Must execute after `app.start()` but before `app.updater.start_polling()`
- **ADD**: Validation that job_queue is ready
- **EXAMPLE**:
```python
# After app.start()
await app.start()

# Verify job_queue is ready
if not app.job_queue:
    raise RuntimeError("JobQueue not initialized")

# NOW load reminders
from src.bot import reminder_manager
if reminder_manager:
    await reminder_manager.load_reminders()
```
- **VALIDATE**: `python -c "from src.main import *; import asyncio; asyncio.run(run_telegram_bot())"` (check logs)

#### Task 9B: FIX Job Queue Initialization (If RCA identifies job_queue None)

- **IMPLEMENT**: Ensure ReminderManager receives initialized job_queue
- **UPDATE**: `src/scheduler/reminder_manager.py` __init__ method
- **ADD**: Validation that job_queue is not None
- **EXAMPLE**:
```python
def __init__(self, application: Application):
    self.application = application
    self.job_queue = application.job_queue

    if self.job_queue is None:
        raise RuntimeError("Application job_queue is None - ensure Application is built with job_queue support")

    logger.info(f"ReminderManager initialized with job_queue: {self.job_queue}")
```
- **VALIDATE**: Bot startup logs show "ReminderManager initialized with job_queue: <JobQueue object>"

#### Task 9C: FIX Silent Failures (If RCA identifies swallowed exceptions)

- **IMPLEMENT**: Improve error handling to surface failures
- **UPDATE**: `src/scheduler/reminder_manager.py` `load_reminders()` method
- **REMOVE**: Overly broad try/except blocks that swallow errors
- **ADD**: Specific exception handling with re-raising
- **EXAMPLE**:
```python
try:
    all_reminders = await get_active_reminders_all()
except DatabaseError as e:
    logger.error(f"Database error loading reminders: {e}")
    raise  # Don't swallow - let it fail loudly
except Exception as e:
    logger.error(f"Unexpected error loading reminders: {e}", exc_info=True)
    raise
```
- **VALIDATE**: Introduce intentional error, verify bot crashes instead of silent failure

#### Task 9D: FIX Day Filter Logic (If RCA identifies weekday filter issue)

- **IMPLEMENT**: Fix day filter to correctly evaluate scheduled days
- **UPDATE**: `src/scheduler/reminder_manager.py` `_send_custom_reminder()` lines 380-392
- **FIX**: Ensure default days includes all days (0-6)
- **FIX**: Ensure current_weekday calculation is correct
- **EXAMPLE**:
```python
# Get scheduled days with proper default
scheduled_days = data.get("days", list(range(7)))  # Default: all days

# Calculate current weekday in user's timezone
from zoneinfo import ZoneInfo
from datetime import datetime
user_tz = ZoneInfo(timezone_str)
now_user = datetime.now(user_tz)
current_weekday = now_user.weekday()  # 0=Monday, 6=Sunday

logger.debug(f"Reminder {reminder_id}: current_weekday={current_weekday}, scheduled_days={scheduled_days}")

if current_weekday not in scheduled_days:
    logger.info(f"Skipping reminder {reminder_id}: today ({current_weekday}) not in {scheduled_days}")
    return
```
- **VALIDATE**: Create test reminder for today's weekday, verify it triggers

#### Task 10: ADD Defensive Logging

- **IMPLEMENT**: Add comprehensive logging for observability
- **UPDATE**: `src/scheduler/reminder_manager.py` all key methods
- **ADD**: Log job queue state after loading
- **ADD**: Log each reminder scheduling attempt
- **ADD**: Log callback invocations with context
- **EXAMPLE**:
```python
logger.info(f"Loading reminders from database...")
all_reminders = await get_active_reminders_all()
logger.info(f"Found {len(all_reminders)} active reminders")

for reminder in all_reminders:
    logger.debug(f"Scheduling reminder {reminder['id']} for user {reminder['user_id']}")
    # ... scheduling logic ...

logger.info(f"Scheduled {scheduled_count} reminders. Job queue now has {len(self.job_queue.jobs())} jobs")
```
- **VALIDATE**: Logs show detailed progression through reminder loading

#### Task 11: ADD Validation Checks

- **IMPLEMENT**: Add runtime validation to catch configuration issues
- **UPDATE**: `src/scheduler/reminder_manager.py` methods
- **ADD**: Validate reminder data before scheduling
- **ADD**: Validate time format, timezone, user_id format
- **EXAMPLE**:
```python
# Validate before scheduling
if not user_id or not reminder_time or not message:
    logger.warning(f"Skipping invalid reminder {reminder_id}: missing required fields")
    continue

try:
    hour, minute = map(int, reminder_time.split(":"))
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError(f"Invalid time: {reminder_time}")
except ValueError as e:
    logger.error(f"Skipping reminder {reminder_id}: {e}")
    continue
```
- **VALIDATE**: Introduce invalid reminder data, verify graceful handling

### Phase 3: Testing & Validation

#### Task 12: CREATE Integration Test

- **IMPLEMENT**: Create comprehensive scheduler integration test
- **CREATE**: `tests/integration/test_reminder_scheduler.py`
- **PATTERN**: Mirror existing test structure from `test_conditional_reminders.py`
- **TEST CASES**:
  1. Scheduler initializes with application
  2. Reminders load from database
  3. Jobs registered in job queue
  4. Callbacks execute at scheduled time (use short delay for testing)
  5. Notifications sent via Telegram (mock bot.send_message)
- **EXAMPLE**:
```python
@pytest.mark.asyncio
async def test_scheduler_loads_reminders():
    """Test that ReminderManager loads reminders from database"""
    # Create test reminder in database
    reminder = Reminder(
        user_id="test_user",
        reminder_type="simple",
        message="Test reminder",
        schedule=ReminderSchedule(
            type="daily",
            time="10:00",
            timezone="UTC"
        )
    )
    await create_reminder(reminder)

    # Create application and scheduler
    app = Application.builder().token(TEST_TOKEN).build()
    manager = ReminderManager(app)

    # Load reminders
    await manager.load_reminders()

    # Verify job registered
    jobs = app.job_queue.get_jobs_by_name(f"custom_reminder_{reminder.id}")
    assert len(jobs) == 1
    assert jobs[0].data["user_id"] == "test_user"
```
- **VALIDATE**: `pytest tests/integration/test_reminder_scheduler.py -v`

#### Task 13: TEST End-to-End Delivery

- **IMPLEMENT**: Manual end-to-end test of reminder delivery
- **CREATE**: Test reminder scheduled 2 minutes from now
- **TEST STEPS**:
  1. Start bot with fixed code
  2. Create reminder via database or API
  3. Verify reminder loads (check logs)
  4. Wait for scheduled time
  5. Verify notification received in Telegram
  6. Check database for completion tracking
- **VALIDATE**: Receive actual Telegram notification
- **DOCUMENT**: Test results in RCA document

#### Task 14: TEST All Reminder Types

- **IMPLEMENT**: Verify all reminder types work correctly
- **TEST**: Daily reminder (recurring)
- **TEST**: One-time reminder (specific date/time)
- **TEST**: Conditional reminder (with check_condition)
- **TEST**: Reminder with day filter (specific weekdays)
- **TEST**: Reminder with completion tracking
- **TEST**: Sleep quiz reminder
- **VALIDATE**: Each type delivers notifications as expected

#### Task 15: TEST Timezone Handling

- **IMPLEMENT**: Verify timezone conversions are correct
- **TEST**: Reminder scheduled in non-UTC timezone (e.g., "America/New_York")
- **TEST**: User in different timezone than server
- **TEST**: Daylight saving time transitions (if applicable)
- **VALIDATE**: Notifications arrive at correct local time for user
- **GOTCHA**: Use `ZoneInfo` not `pytz` for timezone handling

#### Task 16: ADD Monitoring & Alerts

- **IMPLEMENT**: Add monitoring for reminder delivery health
- **UPDATE**: `src/scheduler/reminder_manager.py`
- **ADD**: Counter for successful reminder deliveries
- **ADD**: Counter for failed reminder deliveries
- **ADD**: Metrics for scheduler health
- **EXAMPLE**:
```python
# After successful delivery
logger.info(f"✅ Reminder {reminder_id} delivered to {user_id}")

# After failure
logger.error(f"❌ Failed to deliver reminder {reminder_id} to {user_id}: {e}")
```
- **VALIDATE**: Logs clearly show delivery success/failure

---

## TESTING STRATEGY

### Unit Tests

**Scope**: Test individual components in isolation

- `ReminderManager.__init__()` - Verify initialization with job_queue
- `ReminderManager.schedule_custom_reminder()` - Verify job registration
- `ReminderManager._send_custom_reminder()` - Verify callback logic (day filter, conditions)
- `get_active_reminders_all()` - Verify database query

**Pattern**: Use mocks for dependencies (database, Telegram bot)

```python
@pytest.mark.asyncio
async def test_reminder_manager_init():
    """Test ReminderManager initializes correctly"""
    app = Mock(spec=Application)
    app.job_queue = Mock(spec=JobQueue)

    manager = ReminderManager(app)

    assert manager.application == app
    assert manager.job_queue == app.job_queue
```

### Integration Tests

**Scope**: Test complete workflows with real database

- Scheduler initialization and reminder loading
- Job registration in job queue
- Callback execution (with mocked Telegram API)
- Multi-reminder scenarios
- Error handling and recovery

**Pattern**: Use test database with cleanup fixtures

```python
@pytest.fixture
async def test_app():
    """Create test application with job queue"""
    app = Application.builder().token(TEST_TOKEN).build()
    await app.initialize()
    yield app
    await app.shutdown()

@pytest.mark.asyncio
async def test_load_and_schedule_reminders(test_app):
    """Test full reminder loading workflow"""
    # Create reminders in database
    # ...

    # Initialize manager
    manager = ReminderManager(test_app)

    # Load reminders
    await manager.load_reminders()

    # Verify jobs scheduled
    jobs = test_app.job_queue.jobs()
    assert len(jobs) > 0
```

### Manual End-to-End Tests

**Scope**: Verify actual notification delivery

1. **Test Daily Reminder**:
   - Create daily reminder for 2 minutes from now
   - Start bot
   - Wait and verify notification received

2. **Test One-Time Reminder**:
   - Create one-time reminder for specific time
   - Verify notification at exact time
   - Verify job removed after execution

3. **Test Conditional Reminder**:
   - Create reminder with food_logged condition
   - Log food entry
   - Verify reminder skipped (condition met)

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Import Validation (CRITICAL)

**Verify all imports resolve before running tests:**

```bash
python3 -c "from src.scheduler.reminder_manager import ReminderManager; print('✓ ReminderManager imports valid')"
python3 -c "from src.main import run_telegram_bot; print('✓ Main imports valid')"
python3 -c "from src.bot import create_bot_application; print('✓ Bot imports valid')"
```

**Expected:** "✓ ... imports valid" for all (no ModuleNotFoundError or ImportError)

**Why:** Catches import errors before running bot or tests.

### Level 2: Syntax & Style

**Run linter and formatter:**

```bash
ruff check src/scheduler/ src/main.py src/bot.py --fix
black src/scheduler/ src/main.py src/bot.py --check
```

**Expected:** No errors, all files pass style checks

### Level 3: Unit Tests

**Run unit tests for reminder components:**

```bash
pytest tests/unit/test_reminder_manager.py -v
pytest tests/api/test_reminders.py -v
```

**Expected:** All tests pass (0 failures)

### Level 4: Integration Tests

**Run integration tests for full reminder workflow:**

```bash
pytest tests/integration/test_reminder_scheduler.py -v
pytest tests/integration/test_conditional_reminders.py -v
pytest tests/integration/test_api_reminders.py -v
```

**Expected:** All tests pass, reminders loaded and scheduled correctly

### Level 5: Manual Validation

**Test actual reminder delivery:**

```bash
# 1. Start bot in terminal
python -m src.main

# 2. In another terminal, create test reminder
python3 -c "
import asyncio
from src.db.connection import db
from src.db.queries import create_reminder
from src.models.reminder import Reminder, ReminderSchedule
from datetime import datetime, timedelta

async def create_test_reminder():
    await db.init_pool()

    # Schedule for 2 minutes from now
    now = datetime.now()
    future_time = (now + timedelta(minutes=2)).strftime('%H:%M')

    reminder = Reminder(
        user_id='YOUR_TELEGRAM_ID',  # Replace with your ID
        reminder_type='simple',
        message='🧪 Test reminder - notifications working!',
        schedule=ReminderSchedule(
            type='daily',
            time=future_time,
            timezone='UTC'
        )
    )

    await create_reminder(reminder)
    print(f'✓ Created test reminder for {future_time}')
    await db.close_pool()

asyncio.run(create_test_reminder())
"

# 3. Wait 2 minutes and verify you receive the notification
```

**Expected:** Test reminder notification received in Telegram at scheduled time

### Level 6: Database Validation

**Verify database state after fix:**

```bash
# Check active reminders loaded
echo "SELECT COUNT(*) as active_count FROM reminders WHERE active = true;" | psql -d health_agent

# Check recent reminder activity
echo "SELECT COUNT(*) as recent_completions FROM reminder_completions WHERE completed_at > NOW() - INTERVAL '1 day';" | psql -d health_agent

# Check for errors in reminder data
echo "SELECT id, user_id, message FROM reminders WHERE schedule IS NULL OR message = '';" | psql -d health_agent
```

**Expected:**
- Active reminders count > 0
- No NULL schedules or empty messages
- Recent completions increase after fix

### Level 7: Log Validation

**Verify logging shows healthy reminder system:**

```bash
# Check reminder loading logs
grep "Loading reminders" logs/bot.log | tail -5

# Check successful deliveries
grep "Sent custom reminder" logs/bot.log | tail -10

# Check for errors
grep -i "error.*reminder" logs/bot.log | tail -20
```

**Expected:**
- "Loading reminders from database..." appears on bot startup
- "Loaded and scheduled X reminders" shows count > 0
- "Sent custom reminder to ..." appears at scheduled times
- No errors related to reminder scheduling

---

## ACCEPTANCE CRITERIA

- [ ] Root cause of notification failure identified and documented in RCA
- [ ] Fix implemented that addresses root cause
- [ ] All validation commands pass with zero errors
- [ ] Unit tests cover ReminderManager initialization and scheduling
- [ ] Integration tests verify full reminder loading and job registration
- [ ] Manual test confirms reminder notification delivered to Telegram
- [ ] All reminder types work correctly (daily, once, conditional, filtered)
- [ ] Timezone handling works for non-UTC timezones
- [ ] Comprehensive logging added for observability
- [ ] No regressions in existing reminder functionality
- [ ] Database queries execute successfully
- [ ] Job queue properly initialized before reminder loading

---

## COMPLETION CHECKLIST

- [ ] RCA document created and root cause identified
- [ ] All investigation tasks (2-8) completed with findings documented
- [ ] Fix implemented for identified root cause (task 9A/B/C/D as applicable)
- [ ] Defensive logging added (task 10)
- [ ] Validation checks added (task 11)
- [ ] Integration test created (task 12)
- [ ] End-to-end manual test passed (task 13)
- [ ] All reminder types tested and working (task 14)
- [ ] Timezone handling verified (task 15)
- [ ] Monitoring added (task 16)
- [ ] All validation commands executed successfully
- [ ] Test reminder notification received in Telegram
- [ ] Acceptance criteria all met
- [ ] Code reviewed for quality and maintainability

---

## NOTES

### Investigation Hypothesis

Based on the codebase analysis, the most likely root causes (in order of probability):

1. **Lifecycle Ordering Issue**: `load_reminders()` may be called before `app.start()` completes, resulting in job_queue not being fully initialized. The current code in `src/main.py` lines 34-41 calls `load_reminders()` after `app.start()` but the timing may be critical.

2. **Silent Exception Swallowing**: The broad try/except in `load_reminders()` (lines 24-63) catches all exceptions and only logs them, preventing visibility into failures. If database connection fails or job registration fails, reminders simply don't load.

3. **Day Filter Bug**: The weekday filter logic (lines 380-392) may incorrectly calculate the current day or have improper default values, causing all reminders to be silently skipped.

4. **JobQueue Not Initialized**: ReminderManager receives an Application but doesn't validate that job_queue is not None. If Application is created without job_queue support, all scheduling silently fails.

### Design Decisions

- **Fail Loudly**: Remove silent error swallowing - let initialization failures crash the bot during startup rather than running in broken state
- **Defensive Validation**: Add runtime checks for job_queue, reminder data validity, timezone correctness
- **Comprehensive Logging**: Add detailed logging at every step to enable quick diagnosis of future issues
- **Test Coverage**: Add integration tests to prevent regressions in scheduler initialization

### Known Gotchas

- The reminder loading MUST happen after `app.start()` completes but before `app.updater.start_polling()` begins
- The JobQueue requires the Application to be built with `job_queue` support enabled
- Timezone calculations must use `ZoneInfo` not `pytz` for Python 3.11+
- Day filters use 0=Monday, 6=Sunday (ISO weekday standard)
- Conditional reminders can silently skip if conditions are met - this is expected behavior but needs clear logging

### Future Improvements

After fixing the immediate issue, consider:
- Add health check endpoint to verify scheduler is running
- Add Sentry monitoring for failed reminder deliveries
- Create admin command to view scheduled jobs
- Add retry logic for failed Telegram deliveries
- Implement dead letter queue for permanently failed reminders
