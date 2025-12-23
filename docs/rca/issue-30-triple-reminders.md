# Root Cause Analysis: Issue #30 - Triple Reminders

**Issue**: User receives 3 copies of reminders (differently worded), reminders are for wrong day but correct time, bot acknowledges duplicates but can't clean them, and users can't manage reminders conversationally.

**Date**: 2024
**Analyzed by**: Remote Agent
**Status**: Root causes identified, implementation plan needed

---

## Problem Statement

Users are experiencing multiple critical issues with the reminder system:

1. **Triple Reminders**: Each reminder triggers 3 separate notifications with different wording
2. **Wrong Day**: Reminders fire on incorrect days despite having the correct time (e.g., morning reminder for Friday fires on Tuesday)
3. **Bot Can't Clean**: Bot detects duplicates in database but has no ability to remove them
4. **No Conversational Management**: Users cannot add, change, or remove reminders by talking to the bot

---

## Investigation Summary

### Key Files Analyzed

1. `/src/scheduler/reminder_manager.py` - Reminder scheduling and job queue management
2. `/src/agent/__init__.py` - Agent tools including `schedule_reminder()`
3. `/src/handlers/reminders.py` - Reminder completion handlers
4. `/src/models/reminder.py` - Reminder data models
5. `/src/db/queries.py` - Database operations
6. `/src/main.py` - Bot initialization and reminder loading

### Timeline of Execution

1. **Bot Startup** (`main.py:35`): Calls `reminder_manager.load_reminders()`
2. **Load Reminders** (`reminder_manager.py:20`): Fetches ALL active reminders from database
3. **Schedule Each** (`reminder_manager.py:45`): Calls `schedule_custom_reminder()` for each database entry
4. **Job Queue Registration** (`reminder_manager.py:125`): Registers job with `run_daily()`

---

## Root Cause #1: Triple Reminders

### Primary Cause: Database Duplicates + Job Name Collisions

**Evidence**:
```python
# reminder_manager.py:135
name=f"custom_reminder_{user_id}_{hour}{minute}"
```

**Problem**:
- Job names do NOT include the `reminder_id` (UUID)
- Multiple reminders at the same time create jobs with identical names
- If database contains 3 duplicate reminders at 08:00, `load_reminders()` calls `schedule_custom_reminder()` 3 times
- Depending on Telegram JobQueue behavior:
  - If it allows duplicate names: 3 jobs are created → 3 notifications
  - If it replaces by name: Only last job survives, but user still has 3 DB entries

**How Duplicates Get Into Database**:

1. **User asks agent to create reminder** → `schedule_reminder()` tool is called
2. **Agent calls `create_reminder()`** → Writes to database
3. **Agent calls `schedule_custom_reminder()`** → Adds to job queue
4. **If conversation fails/retries** → Agent might call `schedule_reminder()` again
5. **Database now has 2+ identical reminders**
6. **Bot restarts** → `load_reminders()` schedules all duplicates

**Why Different Wording**:
Each reminder notification goes through the completion tracking system which may add different streak messages:

```python
# reminder_manager.py:328-330
if enable_tracking and streak_count > 0:
    fire_emoji = "🔥" * min(streak_count, 3)
    reminder_text += f"\n\n{fire_emoji} {streak_count}-day streak! Keep it going 💪"
```

If the reminders have different `reminder_id` values, they have different streak counts, leading to different messages.

### Contributing Factors

1. **No uniqueness constraint** in database schema on `(user_id, message, schedule->time)`
2. **No duplicate detection** before inserting new reminders
3. **Job name collision** makes debugging harder (can't tell which reminder_id is which job)

---

## Root Cause #2: Wrong Day, Correct Time

### Primary Cause: Timezone Conversion or Day Field Ignored

**Evidence**:
```python
# reminder_manager.py:120-136
tz = ZoneInfo(user_timezone)
scheduled_time = time(hour=hour, minute=minute, tzinfo=tz)

if reminder_type == "daily":
    self.job_queue.run_daily(
        callback=self._send_custom_reminder,
        time=scheduled_time,
        data={...},
        name=f"custom_reminder_{user_id}_{hour}{minute}",
    )
```

**Problem**:
- The `schedule` object has a `days` field (days of week: 0-6) defined in the model:
  ```python
  # reminder.py:12
  days: list[int] = Field(default_factory=lambda: list(range(7)))  # 0-6
  ```
- But this `days` field is **NEVER USED** when scheduling jobs!
- `run_daily()` runs every day, ignoring the `days` constraint
- If timezone conversion is wrong, a reminder at 23:00 in one timezone might become 01:00 the next day in UTC

**Why Wrong Day**:

**Hypothesis 1**: Timezone boundary crossing
- User in Europe/Stockholm (UTC+1 or UTC+2 depending on DST)
- Morning reminder at 08:00 local time
- If bot stores/interprets as UTC incorrectly: 08:00 CET = 07:00 UTC
- But if calculation is off by a day cycle, it triggers on wrong day

**Hypothesis 2**: Days field defaults to all days but user expects specific days
- Model defaults `days` to `[0,1,2,3,4,5,6]` (all days)
- User might create reminder saying "Friday morning"
- Agent creates reminder with default all-days schedule
- Reminder fires every day, user only notices when it fires on wrong day

**Most Likely**: Combination of both - timezone handling AND days field not being used

---

## Root Cause #3: Bot Can't Clean Duplicates

### Primary Cause: Missing Agent Tools for Reminder Management

**Evidence**:
```python
# agent/__init__.py - Available reminder tools:
- schedule_reminder()          # CREATE only
- get_user_reminders()          # LIST only
- get_reminder_statistics()     # READ only
- compare_all_reminders()       # READ only
- suggest_reminder_optimizations() # READ only
```

**Problem**:
- **No `delete_reminder()` tool**
- **No `update_reminder()` tool**
- **No `cleanup_duplicate_reminders()` tool**
- Agent can detect duplicates in conversation but has no tool to fix them

**Why Bot Says It Can't Clean**:
When user asks bot to clean duplicates, the agent:
1. Calls `get_user_reminders()` to list them
2. Sees duplicates (same message, time, timezone)
3. Wants to delete them but realizes no tool exists
4. Responds: "I can see duplicates but I can't remove them"

---

## Root Cause #4: No Conversational Reminder Management

### Primary Cause: Missing CRUD Tools for Reminders

**Problem**:
Current agent tools support:
- ✅ CREATE (schedule_reminder)
- ✅ READ (get_user_reminders, get_reminder_statistics)
- ❌ UPDATE (no tool)
- ❌ DELETE (no tool)

Users cannot:
- "Remove my morning reminder"
- "Change my vitamin reminder from 8am to 9am"
- "Cancel all my reminders"
- "Clean up duplicate reminders"

---

## Impact Assessment

### User Experience
- **Severity**: HIGH - Core feature is broken and annoying
- **Frequency**: Every time reminder fires (multiple times daily)
- **Frustration**: High - User can't fix it themselves

### Data Impact
- Database likely has duplicate reminder entries
- Completion tracking data may be split across duplicate reminder_ids
- Streak calculations may be wrong due to duplicates

### System Impact
- Unnecessary job queue overhead (multiple jobs for same reminder)
- Logs polluted with duplicate reminder sends
- Agent can't fulfill user requests to manage reminders

---

## Proposed Solution Components

### Fix #1: Prevent Duplicate Reminders

**Database Layer**:
1. Add unique constraint: `UNIQUE(user_id, message, (schedule->>'time'), (schedule->>'timezone'))`
2. Or add deduplication logic before INSERT

**Application Layer**:
1. Before creating reminder, check if identical one exists:
   ```python
   existing = await check_duplicate_reminder(user_id, message, time, timezone)
   if existing:
       return "You already have this reminder scheduled"
   ```

**Job Queue Layer**:
1. Include `reminder_id` in job name:
   ```python
   name=f"custom_reminder_{user_id}_{reminder_id}"
   ```

### Fix #2: Correct Day Scheduling

**Implement Days Filter**:
1. Parse `days` from schedule JSON
2. Create custom callback that checks day-of-week before sending
3. Or use `run_daily()` with day filter parameter if available
4. Example:
   ```python
   async def _send_custom_reminder(context):
       schedule_days = context.job.data.get('days', list(range(7)))
       current_day = datetime.now(tz).weekday()
       if current_day not in schedule_days:
           logger.debug(f"Skipping reminder - not scheduled for {current_day}")
           return
       # ... send reminder
   ```

**Fix Timezone Handling**:
1. Verify timezone conversion is correct
2. Add extensive logging to debug wrong-day issues
3. Store scheduled_date along with scheduled_time to track expectations

### Fix #3: Add Reminder Management Tools

**New Agent Tools Needed**:

1. **`delete_reminder(reminder_id)`**
   - Remove from database
   - Cancel job queue entry
   - Return success message

2. **`update_reminder(reminder_id, new_time=None, new_message=None)`**
   - Update database
   - Cancel old job
   - Schedule new job
   - Return success message

3. **`cleanup_duplicate_reminders()`**
   - Find duplicates (same user, message, time, timezone)
   - Keep oldest, mark others inactive
   - Cancel duplicate jobs
   - Return cleanup summary

4. **`list_reminders_detailed()`**
   - Show reminders with IDs so user can reference them
   - Format: "1. [ID: abc-123] Morning vitamins @ 08:00 CET"

**Database Queries Needed**:
```python
async def find_duplicate_reminders(user_id: str) -> list[dict]
async def delete_reminder(reminder_id: str, user_id: str) -> bool
async def update_reminder(reminder_id: str, user_id: str, **updates) -> bool
```

**Job Queue Manager Methods**:
```python
async def cancel_reminder_by_id(self, reminder_id: str) -> bool:
    """Cancel job by reminder_id"""
    # Find job with reminder_id in data or name
    # Call job.schedule_removal()
```

### Fix #4: Immediate Cleanup for Current User

**Manual Cleanup Script**:
```sql
-- Find duplicates
WITH duplicates AS (
  SELECT
    user_id,
    message,
    schedule->>'time' as time,
    schedule->>'timezone' as tz,
    COUNT(*) as count,
    MIN(created_at) as first_created
  FROM reminders
  WHERE active = true
  GROUP BY user_id, message, schedule->>'time', schedule->>'timezone'
  HAVING COUNT(*) > 1
)
-- Deactivate all but oldest
UPDATE reminders r
SET active = false
FROM duplicates d
WHERE r.user_id = d.user_id
  AND r.message = d.message
  AND r.schedule->>'time' = d.time
  AND r.schedule->>'timezone' = d.tz
  AND r.created_at > d.first_created
RETURNING r.id, r.message;
```

---

## Verification Steps

After fixes are implemented:

1. **No Duplicates Created**:
   - Create reminder conversationally
   - Check database: should be exactly 1 entry
   - Restart bot
   - Check job queue: should be exactly 1 job

2. **Correct Days**:
   - Create "weekday only" reminder
   - Verify it doesn't fire on weekend
   - Check logs for day-filtering

3. **Can Delete**:
   - Ask bot "delete my morning reminder"
   - Verify removed from DB and job queue
   - Should not receive reminder

4. **Can Update**:
   - Ask bot "change my vitamin reminder to 9am"
   - Verify DB updated, old job cancelled, new job scheduled
   - Receive reminder at new time

---

## Recommendations

### Immediate Actions (Critical)
1. ✅ **Run cleanup script** to deactivate duplicate reminders in database
2. ✅ **Restart bot** to reload clean reminder list
3. ✅ **Add `delete_reminder` tool** so bot can help users manage reminders

### Short-term (This Sprint)
1. ✅ **Implement days-of-week filtering** in reminder scheduling
2. ✅ **Add reminder_id to job names** to prevent collisions
3. ✅ **Add duplicate detection** before creating new reminders
4. ✅ **Add update_reminder tool** for conversational editing

### Medium-term (Next Sprint)
1. ⚠️ **Add database unique constraint** on reminders
2. ⚠️ **Add comprehensive reminder management UI** (list with IDs, delete buttons)
3. ⚠️ **Improve timezone handling** with extensive logging
4. ⚠️ **Add reminder validation** to prevent ambiguous schedules

### Long-term (Backlog)
1. 📋 **Reminder analytics** - "Which reminders do you skip most?"
2. 📋 **Smart scheduling** - "You usually complete this late, want to move it?"
3. 📋 **Reminder templates** - "Take medication" with common times
4. 📋 **Bulk operations** - "Pause all reminders for this week"

---

## Related Issues

- None found yet

---

## Lessons Learned

1. **Job names must be unique**: Include entity IDs in scheduled job names
2. **CRUD completeness**: If you can CREATE, you must support DELETE and UPDATE
3. **Duplicate prevention**: Add uniqueness constraints or detection logic
4. **Field usage**: Don't define model fields (like `days`) that aren't used in scheduling
5. **Restart testing**: Test what happens when bot restarts with existing DB state

---

## Appendix: Code References

### Job Naming Issue
File: `src/scheduler/reminder_manager.py:135`
```python
name=f"custom_reminder_{user_id}_{hour}{minute}",  # ❌ Missing reminder_id
```

Should be:
```python
name=f"custom_reminder_{user_id}_{reminder_id}",  # ✅ Unique per reminder
```

### Days Field Not Used
File: `src/scheduler/reminder_manager.py:124-136`
```python
if reminder_type == "daily":
    self.job_queue.run_daily(
        callback=self._send_custom_reminder,
        time=scheduled_time,
        data={...},
        name=f"custom_reminder_{user_id}_{hour}{minute}",
    )
    # ❌ schedule.days is never checked
```

Should check:
```python
data = {
    "user_id": user_id,
    "message": message,
    "reminder_id": reminder_id,
    "scheduled_time": reminder_time,
    "timezone": user_timezone,
    "days": schedule.get("days", list(range(7)))  # ✅ Include days
}
```

### Missing Tools
File: `src/agent/__init__.py`

Missing:
```python
@agent.tool
async def delete_reminder(ctx, reminder_id: str) -> ReminderOperationResult:
    """Delete a reminder by ID"""
    # Implementation needed

@agent.tool
async def update_reminder(
    ctx,
    reminder_id: str,
    new_time: Optional[str] = None,
    new_message: Optional[str] = None
) -> ReminderOperationResult:
    """Update an existing reminder"""
    # Implementation needed

@agent.tool
async def cleanup_duplicate_reminders(ctx) -> CleanupResult:
    """Find and remove duplicate reminders"""
    # Implementation needed
```
