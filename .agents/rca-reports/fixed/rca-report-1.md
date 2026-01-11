# Root Cause Analysis: Issue #36

**Issue**: Agent cannot create one-time reminders, only recurring daily reminders
**Root Cause**: `schedule_reminder` agent tool hardcodes `reminder_type="daily"` and lacks parameters for one-time scheduling
**Severity**: High (Production bug affecting user experience)
**Confidence**: High (Code inspection, git history, and cross-reference with working one-time reminder code confirms diagnosis)

---

## Evidence Chain

### The Path from Symptom to Cause

**SYMPTOM**: Users report: "Agent says 'I can only set recurring reminders, not one-time reminders'"

**WHY 1**: Why does the agent say it can only set recurring reminders?
↓ **BECAUSE**: The `schedule_reminder` tool docstring states "Schedule a **daily** reminder at a specific time"

**Evidence**: `src/agent/__init__.py:499`
```python
async def schedule_reminder(
    ctx, reminder_time: str, message: str
) -> ReminderScheduleResult:
    """
    Schedule a daily reminder at a specific time

    Args:
        reminder_time: Time in "HH:MM" format (24-hour, user's local time)
        message: Reminder message to send
```

The LLM reads this docstring and correctly informs users of the tool's limitation.

---

**WHY 2**: Why does the tool only support daily reminders?
↓ **BECAUSE**: The tool signature lacks parameters for one-time reminders (no `reminder_type`, `reminder_date`, or `trigger_time` parameters)

**Evidence**: `src/agent/__init__.py:495-496`
```python
async def schedule_reminder(
    ctx, reminder_time: str, message: str  # <-- Only accepts time and message
) -> ReminderScheduleResult:
```

**Comparison**: The API endpoint (which DOES support one-time reminders) accepts:
```python
# From tests/api/test_reminders.py:72-77
{
    "type": "one_time",           # ❌ Agent tool doesn't accept this
    "message": "Check something",  # ✅ Agent tool has this
    "trigger_time": trigger_time,  # ❌ Agent tool doesn't accept this
    "timezone": "UTC"              # ✅ Agent tool gets this from user preferences
}
```

---

**WHY 3**: Why does the tool implementation not support one-time reminders?
↓ **BECAUSE**: The `Reminder` object is hardcoded with `reminder_type="daily"` and `schedule.type="daily"`

**Evidence**: `src/agent/__init__.py:575-584`
```python
reminder_obj = Reminder(
    id=reminder_id,
    user_id=deps.telegram_id,
    reminder_type="daily",  # <-- HARDCODED
    message=message,
    schedule=ReminderSchedule(
        type="daily",  # <-- HARDCODED
        time=reminder_time,
        timezone=user_timezone
    ),
    active=True,
```

---

**WHY 4**: Why does the scheduling call not support one-time reminders?
↓ **BECAUSE**: The `schedule_custom_reminder` call is hardcoded with `reminder_type="daily"`

**Evidence**: `src/agent/__init__.py:598-605`
```python
await deps.reminder_manager.schedule_custom_reminder(
    user_id=deps.telegram_id,
    reminder_time=reminder_time,
    message=message,
    reminder_type="daily",  # <-- HARDCODED
    user_timezone=user_timezone,
    reminder_id=reminder_id
)
```

---

**WHY 5**: Why doesn't the ReminderManager execute one-time reminders?
↓ **ROOT CAUSE**: `ReminderManager.schedule_custom_reminder` only implements `run_daily`, not `run_once`

**Evidence**: `src/scheduler/reminder_manager.py:137-154`
```python
# Schedule based on type
if reminder_type == "daily":
    self.job_queue.run_daily(  # <-- Only daily scheduling implemented
        callback=self._send_custom_reminder,
        time=scheduled_time,
        data={...},
        name=f"custom_reminder_{reminder_id}",
    )
else:
    logger.warning(f"Reminder type {reminder_type} not implemented yet")  # <-- One-time reminders fall here
```

**Proof that one-time scheduling is possible**: `src/handlers/reminders.py:330-340` (snooze feature) successfully uses `run_once`:
```python
context.application.job_queue.run_once(
    callback=_send_snoozed_reminder,
    when=snooze_time,  # <-- datetime object
    data={
        'user_id': user_id,
        'message': message,
        'reminder_id': reminder_id,
        'scheduled_time': scheduled_time
    },
    name=f"snooze_{reminder_id}_{user_id}"
)
```

---

### Alternative Hypotheses Considered

**Hypothesis A**: "The database doesn't support one-time reminders"
**Status**: ❌ REFUTED

**Evidence**: `src/models/reminder.py:9`
```python
class ReminderSchedule(BaseModel):
    """Reminder schedule configuration"""
    type: str  # daily, weekly, once  <-- "once" type is defined
```

The model explicitly supports `type="once"`.

---

**Hypothesis B**: "JobQueue doesn't support one-time reminders"
**Status**: ❌ REFUTED

**Evidence**:
1. Snooze feature uses `run_once` successfully (src/handlers/reminders.py:330)
2. Web search confirms `JobQueue.run_once` exists and accepts datetime: [python-telegram-bot documentation](https://docs.python-telegram-bot.org/en/stable/telegram.ext.jobqueue.html)

---

**Hypothesis C**: "This is a deliberate design choice"
**Status**: ❌ REFUTED

**Evidence**:
1. API already supports one-time reminders with tests (`tests/api/test_reminders.py:54`)
2. Issue #36 explicitly states this is a bug, not intended behavior
3. Users expect one-time reminders as basic functionality

---

### Git History Context

**Introduced**: Commit `8b49ed5` - "Add reminder completion tracking with inline keyboard buttons"
**Author**: gpt153
**Date**: 2025-12-18
**Recent changes**:
- 2025-12-23: `2adf28c` - "Fix reminder system: eliminate duplicates, add management tools, implement day filtering"
- 2025-12-18: `f8d54bd` - "feat: Add reminder statistics and analytics (Week 2)"
- 2025-12-18: `8b49ed5` - "Add reminder completion tracking with inline keyboard buttons" (introduced hardcoding)

**Implication**: This is an **original limitation** from the initial implementation. The tool was designed with only daily reminders in mind. Subsequent work (duplicate fixes, analytics, day filtering) all built on this daily-only foundation. The one-time reminder capability exists in the API but was never connected to the agent tool.

---

## Fix Specification

### What Needs to Change

The fix requires changes at **three layers** to connect the agent tool to existing one-time reminder infrastructure:

1. **Agent Tool Layer** (`src/agent/__init__.py`):
   - Add parameters: `reminder_type: str = "daily"`, `reminder_date: Optional[str] = None`
   - Update docstring to document both daily and one-time reminders
   - Add validation: require `reminder_date` when `reminder_type="once"`
   - Pass dynamic `reminder_type` to Reminder object and scheduling call

2. **Scheduler Layer** (`src/scheduler/reminder_manager.py`):
   - Implement `run_once` path in `schedule_custom_reminder`
   - Parse date + time into full datetime for one-time reminders
   - Create timezone-aware datetime for scheduling

3. **Reminder Management** (existing code already supports this):
   - Database model already supports `type="once"` ✅
   - JobQueue already supports `run_once` ✅
   - Just need to wire it up ✅

---

### Implementation Guidance

#### Layer 1: Agent Tool (`src/agent/__init__.py`)

**Current problematic pattern (lines 495-507)**:
```python
async def schedule_reminder(
    ctx, reminder_time: str, message: str
) -> ReminderScheduleResult:
    """
    Schedule a daily reminder at a specific time

    Args:
        reminder_time: Time in "HH:MM" format (24-hour, user's local time)
        message: Reminder message to send

    Returns:
        ReminderScheduleResult with success status
    """
```

**Required pattern**:
```python
async def schedule_reminder(
    ctx,
    reminder_time: str,
    message: str,
    reminder_type: str = "daily",  # NEW: "daily", "weekly", or "once"
    reminder_date: Optional[str] = None  # NEW: Required for reminder_type="once", format: "YYYY-MM-DD"
) -> ReminderScheduleResult:
    """
    Schedule a reminder (daily, weekly, or one-time)

    Args:
        reminder_time: Time in "HH:MM" format (24-hour, user's local time)
        message: Reminder message to send
        reminder_type: Type of reminder - "daily" (default), "weekly", or "once"
        reminder_date: Date for one-time reminders (YYYY-MM-DD format). Required when reminder_type="once"

    Examples:
        Daily: reminder_type="daily", reminder_time="09:00"
        One-time: reminder_type="once", reminder_time="15:00", reminder_date="2025-01-15"

    Returns:
        ReminderScheduleResult with success status
    """
```

**Add validation after line 507**:
```python
# Validate parameters based on reminder_type
if reminder_type == "once" and not reminder_date:
    return ReminderScheduleResult(
        success=False,
        message="One-time reminders require a date. Please provide reminder_date in YYYY-MM-DD format.",
        reminder_time=reminder_time,
        reminder_message=message,
    )

# Validate date format if provided
if reminder_date:
    try:
        from datetime import date
        date.fromisoformat(reminder_date)
    except ValueError:
        return ReminderScheduleResult(
            success=False,
            message=f"Invalid date format '{reminder_date}'. Please use YYYY-MM-DD format.",
            reminder_time=reminder_time,
            reminder_message=message,
        )
```

**Change lines 575-584** from hardcoded "daily" to dynamic:
```python
reminder_obj = Reminder(
    id=reminder_id,
    user_id=deps.telegram_id,
    reminder_type=reminder_type,  # CHANGED: use parameter instead of hardcoded "daily"
    message=message,
    schedule=ReminderSchedule(
        type=reminder_type,  # CHANGED: use parameter instead of hardcoded "daily"
        time=reminder_time,
        timezone=user_timezone,
        date=reminder_date if reminder_type == "once" else None  # NEW: add date for one-time
    ),
    active=True,
    enable_completion_tracking=enable_tracking,
    streak_motivation=enable_tracking
)
```

**Change lines 598-605** to pass dynamic reminder_type:
```python
await deps.reminder_manager.schedule_custom_reminder(
    user_id=deps.telegram_id,
    reminder_time=reminder_time,
    message=message,
    reminder_type=reminder_type,  # CHANGED: use parameter instead of hardcoded "daily"
    user_timezone=user_timezone,
    reminder_id=reminder_id,
    reminder_date=reminder_date  # NEW: pass date for one-time reminders
)
```

---

#### Layer 2: Scheduler (`src/scheduler/reminder_manager.py`)

**Current problematic pattern (lines 103-161)**:
```python
async def schedule_custom_reminder(
    self,
    user_id: str,
    reminder_time: str,
    message: str,
    reminder_type: str = "daily",
    user_timezone: str = "UTC",
    reminder_id: str = None,
    days: list[int] = None
) -> None:
    """..."""
    # Parse time and apply user's timezone
    hour, minute = map(int, reminder_time.split(":"))
    tz = ZoneInfo(user_timezone)
    scheduled_time = time(hour=hour, minute=minute, tzinfo=tz)

    # Schedule based on type
    if reminder_type == "daily":
        self.job_queue.run_daily(...)
    else:
        logger.warning(f"Reminder type {reminder_type} not implemented yet")
```

**Required pattern**:
```python
async def schedule_custom_reminder(
    self,
    user_id: str,
    reminder_time: str,
    message: str,
    reminder_type: str = "daily",
    user_timezone: str = "UTC",
    reminder_id: str = None,
    days: list[int] = None,
    reminder_date: Optional[str] = None  # NEW: Date for one-time reminders
) -> None:
    """
    Schedule a custom reminder

    Args:
        user_id: Telegram user ID
        reminder_time: Time in "HH:MM" format (user's local time)
        message: Reminder message to send
        reminder_type: "daily", "weekly", or "once"
        user_timezone: IANA timezone string (e.g., "America/New_York")
        reminder_id: UUID of reminder in database (optional, for completion tracking)
        days: List of weekday integers (0=Monday, 6=Sunday). None = all days.
        reminder_date: Date string in YYYY-MM-DD format (required for reminder_type="once")
    """
    try:
        # Parse time and apply user's timezone
        hour, minute = map(int, reminder_time.split(":"))
        tz = ZoneInfo(user_timezone)

        # Schedule based on type
        if reminder_type == "daily":
            scheduled_time = time(hour=hour, minute=minute, tzinfo=tz)
            if days is None:
                days = list(range(7))

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

        elif reminder_type == "once":  # NEW: Implement one-time reminders
            # Parse date and time into full datetime
            from datetime import datetime, date
            reminder_date_obj = date.fromisoformat(reminder_date)

            # Create timezone-aware datetime
            reminder_datetime = datetime.combine(
                reminder_date_obj,
                time(hour, minute),
                tzinfo=tz
            )

            # Schedule one-time job
            self.job_queue.run_once(
                callback=self._send_custom_reminder,
                when=reminder_datetime,
                data={
                    "user_id": user_id,
                    "message": message,
                    "reminder_id": reminder_id,
                    "scheduled_time": reminder_time,
                    "timezone": user_timezone,
                    "days": None  # Not applicable for one-time reminders
                },
                name=f"custom_reminder_{reminder_id}",
            )

            logger.info(
                f"Scheduled one-time reminder for {user_id} "
                f"at {reminder_datetime.isoformat()}"
            )

        else:
            logger.warning(f"Reminder type {reminder_type} not implemented yet")

    except Exception as e:
        logger.error(f"Failed to schedule custom reminder: {e}", exc_info=True)
```

---

### Key Considerations for Implementation

**Edge Cases**:
1. **Past dates**: Validate that `reminder_date` is not in the past (should fail gracefully)
2. **Timezone handling**: Ensure datetime is created in user's timezone, not UTC
3. **Duplicate detection**: Existing duplicate check (lines 538-567) may need adjustment for one-time reminders
4. **Reminder deactivation**: One-time reminders should auto-deactivate after delivery (update `_send_custom_reminder`)

**Testing approach**:
1. Test daily reminder creation (existing functionality - regression test)
2. Test one-time reminder creation with date tomorrow
3. Test validation: one-time reminder without date should fail
4. Test validation: invalid date format should fail
5. Test validation: past date should fail
6. Verify one-time reminder appears in database with correct type
7. Verify one-time reminder auto-deactivates after delivery

**Related code that might need updates**:
- `src/agent/__init__.py` line 1092: Update reminder also hardcodes "daily" - should support updating to/from one-time
- `src/models/reminder.py`: May need to add `date` field to `ReminderSchedule` model
- `src/db/queries.py`: Verify reminder queries handle one-time reminders correctly

---

### Files to Examine

Primary changes:
- `src/agent/__init__.py:495-605` - Add parameters, update tool logic
- `src/scheduler/reminder_manager.py:103-161` - Implement `run_once` path

Potential secondary changes:
- `src/models/reminder.py:7-13` - May need to add `date` field to `ReminderSchedule`
- `src/agent/__init__.py:1090-1099` - Update reminder tool also hardcodes "daily"
- `src/scheduler/reminder_manager.py:328-413` - `_send_custom_reminder` may need one-time deactivation logic

Reference implementations (do NOT modify, use as examples):
- `src/handlers/reminders.py:330-340` - Working `run_once` example (snooze feature)
- `tests/api/test_reminders.py:54-93` - Expected one-time reminder API format

---

## Verification

### How to confirm the fix works:

**1. Functional Test - Create One-Time Reminder**:
```
User: "Remind me tomorrow at 2pm to call mom"
Expected: Agent creates one-time reminder for tomorrow at 14:00
Verify: Check database - reminder_type should be "once", schedule.type should be "once"
```

**2. Functional Test - Create Daily Reminder (Regression)**:
```
User: "Remind me daily at 9am to take vitamins"
Expected: Agent creates daily recurring reminder at 09:00
Verify: Existing functionality still works
```

**3. Validation Test - One-Time Without Date**:
```
Tool call: schedule_reminder(reminder_type="once", reminder_time="14:00", message="test")
Expected: Returns error "One-time reminders require a date"
```

**4. Delivery Test - One-Time Reminder Fires Once**:
```
Create one-time reminder for 2 minutes from now
Wait for delivery
Verify:
  - Reminder fires at correct time
  - Reminder auto-deactivates (active=False in database)
  - Reminder does NOT fire again the next day
```

**5. Database Verification**:
```sql
SELECT id, user_id, reminder_type, schedule, active
FROM reminders
WHERE reminder_type = 'once';
```
Expected: Shows one-time reminders with proper schedule structure

**6. Agent Behavior Verification**:
```
User: "Set a reminder for January 15th at 3pm to submit report"
Expected: Agent responds with success, NOT "I can only set recurring reminders"
```

---

## Summary

The root cause is a **three-layer limitation** where the agent tool was designed only for daily reminders:

1. **Tool signature** lacks `reminder_type` and `reminder_date` parameters
2. **Tool implementation** hardcodes `reminder_type="daily"` when creating Reminder objects
3. **Scheduler** only implements `run_daily`, not `run_once`

The infrastructure to support one-time reminders **already exists**:
- ✅ Database model supports `type="once"`
- ✅ JobQueue supports `run_once` (proven by snooze feature)
- ✅ API endpoints support one-time reminders
- ❌ Agent tool just needs to be wired up

**Fix complexity**: Medium - requires coordinated changes across 3 layers but no new infrastructure needed.

**User impact**: High - basic reminder functionality is expected to include one-time reminders.

**Risk**: Low - one-time reminder infrastructure already works (API, snooze), just extending agent access.
