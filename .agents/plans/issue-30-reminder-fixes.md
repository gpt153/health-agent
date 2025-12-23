# Implementation Plan: Fix Reminder System (Issue #30)

**Issue**: Triple reminders, wrong day scheduling, can't clean duplicates, no conversational management
**RCA Document**: `/docs/rca/issue-30-triple-reminders.md`
**Priority**: HIGH (Critical user-facing bug)
**Estimated Effort**: 3-4 hours

---

## Overview

This plan addresses four critical issues with the reminder system:
1. Users receive 3 duplicate reminders with different wording
2. Reminders fire on wrong day but correct time
3. Bot cannot clean duplicate reminders
4. Users cannot add/change/remove reminders conversationally

**Root causes identified**:
- Database contains duplicate reminder entries
- Job names don't include reminder_id causing collisions
- Days-of-week field is ignored during scheduling
- No DELETE or UPDATE agent tools exist for reminders

---

## Implementation Phases

### Phase 1: Emergency Cleanup & Prevention (Critical - Do First)
**Goal**: Stop the bleeding - remove duplicates and prevent new ones

### Phase 2: Job Queue Fixes (Critical)
**Goal**: Fix scheduling to prevent collisions and respect day filters

### Phase 3: Conversational Management (High Priority)
**Goal**: Add agent tools for delete, update, and cleanup

### Phase 4: Verification & Testing (Required)
**Goal**: Ensure all issues are resolved

---

## Phase 1: Emergency Cleanup & Prevention

### 1.1 Create Database Cleanup Function

**File**: `src/db/queries.py`

**Add new function**:
```python
async def find_duplicate_reminders(user_id: Optional[str] = None) -> list[dict]:
    """
    Find duplicate reminders (same user, message, time, timezone)

    Args:
        user_id: Optional user filter, or None for all users

    Returns:
        List of dicts with duplicate info and reminder IDs to keep/remove
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            query = """
            WITH reminder_groups AS (
                SELECT
                    user_id,
                    message,
                    schedule->>'time' as time,
                    schedule->>'timezone' as timezone,
                    ARRAY_AGG(id ORDER BY created_at ASC) as reminder_ids,
                    ARRAY_AGG(created_at ORDER BY created_at ASC) as created_dates,
                    COUNT(*) as count
                FROM reminders
                WHERE active = true
            """

            if user_id:
                query += " AND user_id = %s"
                params = (user_id,)
            else:
                params = ()

            query += """
                GROUP BY user_id, message, schedule->>'time', schedule->>'timezone'
                HAVING COUNT(*) > 1
            )
            SELECT
                user_id,
                message,
                time,
                timezone,
                reminder_ids[1] as keep_id,
                reminder_ids[2:] as remove_ids,
                count as duplicate_count
            FROM reminder_groups
            ORDER BY user_id, count DESC
            """

            await cur.execute(query, params)
            return await cur.fetchall()


async def deactivate_duplicate_reminders(user_id: Optional[str] = None) -> dict:
    """
    Deactivate duplicate reminders, keeping the oldest one

    Args:
        user_id: Optional user filter, or None for all users

    Returns:
        Dict with counts of reminders checked and deactivated
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Find duplicates
            duplicates = await find_duplicate_reminders(user_id)

            if not duplicates:
                return {"checked": 0, "deactivated": 0, "groups": 0}

            # Deactivate all duplicates (except the one to keep)
            deactivated_count = 0
            for dup in duplicates:
                remove_ids = dup["remove_ids"]
                if remove_ids:
                    # Convert list to tuple for SQL IN clause
                    await cur.execute(
                        """
                        UPDATE reminders
                        SET active = false
                        WHERE id = ANY(%s)
                        """,
                        (remove_ids,)
                    )
                    deactivated_count += len(remove_ids)

            await conn.commit()

            logger.info(
                f"Deactivated {deactivated_count} duplicate reminders "
                f"across {len(duplicates)} groups"
            )

            return {
                "checked": sum(d["duplicate_count"] for d in duplicates),
                "deactivated": deactivated_count,
                "groups": len(duplicates)
            }
```

**Why**: Provides both detection and cleanup of duplicates

### 1.2 Run Emergency Cleanup

**File**: Create `scripts/cleanup_duplicate_reminders.py`

```python
"""Emergency cleanup script for duplicate reminders"""
import asyncio
import logging
from src.db.connection import db
from src.db.queries import find_duplicate_reminders, deactivate_duplicate_reminders

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Run duplicate cleanup"""
    try:
        # Initialize database
        await db.init_pool()

        # Find duplicates
        logger.info("Searching for duplicate reminders...")
        duplicates = await find_duplicate_reminders()

        if not duplicates:
            logger.info("No duplicates found!")
            return

        # Show duplicates
        logger.info(f"\nFound {len(duplicates)} groups of duplicates:\n")
        for dup in duplicates:
            logger.info(
                f"User {dup['user_id']}: "
                f"{dup['duplicate_count']}x '{dup['message']}' "
                f"@ {dup['time']} {dup['timezone']}"
            )

        # Confirm
        response = input("\nDeactivate duplicates? (yes/no): ")
        if response.lower() != "yes":
            logger.info("Cancelled")
            return

        # Clean up
        result = await deactivate_duplicate_reminders()
        logger.info(
            f"\n✅ Cleanup complete:\n"
            f"   - Checked: {result['checked']} reminders\n"
            f"   - Deactivated: {result['deactivated']} duplicates\n"
            f"   - Groups: {result['groups']}"
        )

        logger.info("\n⚠️ Remember to restart the bot to reload job queue!")

    finally:
        await db.close_pool()


if __name__ == "__main__":
    asyncio.run(main())
```

**Action**: Run this script immediately to clean up existing duplicates

### 1.3 Add Duplicate Detection to schedule_reminder

**File**: `src/agent/__init__.py`

**Modify `schedule_reminder` function** (around line 462):

```python
@agent.tool
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
    deps: AgentDeps = ctx.deps

    try:
        # Check if reminder_manager is available
        if not deps.reminder_manager:
            return ReminderScheduleResult(
                success=False,
                message="Reminder system not available",
                reminder_time=reminder_time,
                reminder_message=message,
            )

        # Get user's timezone from memory
        user_timezone = "UTC"
        if deps.mem0_user_id:
            memories = deps.mem0_client.search(
                query="timezone location preference",
                user_id=deps.mem0_user_id,
                limit=5
            )
            for mem in memories:
                if "timezone" in mem["memory"].lower():
                    parts = mem["memory"].split()
                    for i, word in enumerate(parts):
                        if word.lower() in ["timezone", "tz"]:
                            if i + 1 < len(parts):
                                user_timezone = parts[i + 1].strip()
                                break

        # ⭐ NEW: Check for duplicate reminders before creating
        from src.db.queries import get_active_reminders
        existing_reminders = await get_active_reminders(deps.telegram_id)

        for existing in existing_reminders:
            existing_schedule = existing.get("schedule", {})
            if isinstance(existing_schedule, str):
                import json
                existing_schedule = json.loads(existing_schedule)

            existing_time = existing_schedule.get("time")
            existing_tz = existing_schedule.get("timezone", "UTC")
            existing_msg = existing.get("message", "")

            # Check for exact duplicate
            if (existing_msg == message and
                existing_time == reminder_time and
                existing_tz == user_timezone):

                return ReminderScheduleResult(
                    success=False,
                    message=(
                        f"⚠️ You already have this reminder scheduled!\n\n"
                        f"📝 Message: {message}\n"
                        f"⏰ Time: {reminder_time} {user_timezone}\n\n"
                        f"If you want to modify it, ask me to delete it first, "
                        f"then create a new one."
                    ),
                    reminder_time=reminder_time,
                    reminder_message=message,
                )

        # Rest of existing implementation...
        # (Continue with reminder creation as before)
```

**Why**: Prevents creating duplicates in the future

---

## Phase 2: Job Queue Fixes

### 2.1 Fix Job Naming to Include reminder_id

**File**: `src/scheduler/reminder_manager.py`

**Change line 135** from:
```python
name=f"custom_reminder_{user_id}_{hour}{minute}",
```

To:
```python
name=f"custom_reminder_{reminder_id}",  # Use UUID for uniqueness
```

**Why**: Ensures each reminder has a unique job, prevents collisions

### 2.2 Implement Days-of-Week Filtering

**File**: `src/scheduler/reminder_manager.py`

**Modify `schedule_custom_reminder`** to pass days to data:

```python
async def schedule_custom_reminder(
    self,
    user_id: str,
    reminder_time: str,
    message: str,
    reminder_type: str = "daily",
    user_timezone: str = "UTC",
    reminder_id: str = None,
    days: list[int] = None  # ⭐ NEW parameter
) -> None:
    """
    Schedule a custom reminder

    Args:
        user_id: Telegram user ID
        reminder_time: Time in "HH:MM" format (user's local time)
        message: Reminder message to send
        reminder_type: "daily", "weekly", or "custom"
        user_timezone: IANA timezone string (e.g., "America/New_York")
        reminder_id: UUID of reminder in database (optional, for completion tracking)
        days: List of weekday integers (0=Monday, 6=Sunday). None = all days.
    """
    try:
        # Parse time and apply user's timezone
        hour, minute = map(int, reminder_time.split(":"))

        # Create timezone-aware time
        tz = ZoneInfo(user_timezone)
        scheduled_time = time(hour=hour, minute=minute, tzinfo=tz)

        # Default to all days if not specified
        if days is None:
            days = list(range(7))

        # Schedule based on type
        if reminder_type == "daily":
            self.job_queue.run_daily(
                callback=self._send_custom_reminder,
                time=scheduled_time,
                data={
                    "user_id": user_id,
                    "message": message,
                    "reminder_id": reminder_id,
                    "scheduled_time": reminder_time,
                    "timezone": user_timezone,
                    "days": days  # ⭐ NEW: Pass days to callback
                },
                name=f"custom_reminder_{reminder_id}",  # ⭐ CHANGED: Use reminder_id
            )
        else:
            logger.warning(f"Reminder type {reminder_type} not implemented yet")

        logger.info(
            f"Scheduled {reminder_type} reminder for {user_id} "
            f"at {reminder_time} {user_timezone} (days: {days})"
        )

    except Exception as e:
        logger.error(f"Failed to schedule custom reminder: {e}", exc_info=True)
```

**Modify `_send_custom_reminder`** to check days:

```python
async def _send_custom_reminder(self, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a custom reminder to user with completion tracking buttons"""
    data = context.job.data
    user_id = data["user_id"]
    message = data["message"]
    reminder_id = data.get("reminder_id")
    scheduled_time = data.get("scheduled_time", "")
    timezone_str = data.get("timezone", "UTC")
    scheduled_days = data.get("days", list(range(7)))  # ⭐ NEW: Get days filter

    try:
        # ⭐ NEW: Check if today is a scheduled day
        from zoneinfo import ZoneInfo
        user_tz = ZoneInfo(timezone_str)
        now_user = datetime.now(user_tz)
        current_weekday = now_user.weekday()  # 0=Monday, 6=Sunday

        if current_weekday not in scheduled_days:
            logger.debug(
                f"Skipping reminder {reminder_id} for {user_id}: "
                f"Today ({current_weekday}) not in scheduled days {scheduled_days}"
            )
            return  # Don't send reminder today

        # Rest of existing implementation...
        # (Continue with reminder sending as before)
```

**Why**: Ensures reminders only fire on intended days

### 2.3 Update load_reminders to pass days

**File**: `src/scheduler/reminder_manager.py`

**Modify `load_reminders`** (around line 45):

```python
# Parse schedule JSON
schedule = json.loads(reminder["schedule"]) if isinstance(reminder["schedule"], str) else reminder["schedule"]
reminder_time = schedule.get("time", "09:00")
timezone = schedule.get("timezone", "UTC")
days = schedule.get("days", list(range(7)))  # ⭐ NEW: Extract days

# Schedule the reminder with reminder_id and days
await self.schedule_custom_reminder(
    user_id=user_id,
    reminder_time=reminder_time,
    message=message,
    reminder_type=reminder_type,
    user_timezone=timezone,
    reminder_id=reminder_id,
    days=days  # ⭐ NEW: Pass days
)
```

**Why**: Ensures days filter is applied on bot restart

---

## Phase 3: Conversational Management

### 3.1 Add Database Query for Deletion

**File**: `src/db/queries.py`

**Add new function**:
```python
async def delete_reminder(reminder_id: str, user_id: str) -> bool:
    """
    Delete (deactivate) a reminder

    Args:
        reminder_id: UUID of reminder
        user_id: User ID for security check

    Returns:
        True if deleted, False if not found or unauthorized
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE reminders
                SET active = false
                WHERE id = %s AND user_id = %s AND active = true
                RETURNING id
                """,
                (reminder_id, user_id)
            )
            result = await cur.fetchone()
            await conn.commit()

            if result:
                logger.info(f"Deleted reminder {reminder_id} for user {user_id}")
                return True
            else:
                logger.warning(f"Reminder {reminder_id} not found for user {user_id}")
                return False


async def update_reminder(
    reminder_id: str,
    user_id: str,
    new_time: Optional[str] = None,
    new_message: Optional[str] = None,
    new_timezone: Optional[str] = None,
    new_days: Optional[list[int]] = None
) -> Optional[dict]:
    """
    Update a reminder's properties

    Args:
        reminder_id: UUID of reminder
        user_id: User ID for security check
        new_time: New time in "HH:MM" format (optional)
        new_message: New message text (optional)
        new_timezone: New timezone (optional)
        new_days: New days list (optional)

    Returns:
        Updated reminder dict or None if not found
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Get current reminder
            await cur.execute(
                """
                SELECT id, message, schedule
                FROM reminders
                WHERE id = %s AND user_id = %s AND active = true
                """,
                (reminder_id, user_id)
            )
            current = await cur.fetchone()

            if not current:
                return None

            # Parse current schedule
            current_schedule = current["schedule"]
            if isinstance(current_schedule, str):
                current_schedule = json.loads(current_schedule)

            # Build updated values
            updated_message = new_message if new_message is not None else current["message"]
            updated_schedule = current_schedule.copy()

            if new_time is not None:
                updated_schedule["time"] = new_time
            if new_timezone is not None:
                updated_schedule["timezone"] = new_timezone
            if new_days is not None:
                updated_schedule["days"] = new_days

            # Update database
            await cur.execute(
                """
                UPDATE reminders
                SET message = %s, schedule = %s
                WHERE id = %s AND user_id = %s
                RETURNING id, message, schedule
                """,
                (updated_message, json.dumps(updated_schedule), reminder_id, user_id)
            )
            result = await cur.fetchone()
            await conn.commit()

            if result:
                logger.info(f"Updated reminder {reminder_id} for user {user_id}")
                return result

            return None


async def get_reminder_by_id(reminder_id: str) -> Optional[dict]:
    """Get a single reminder by ID (already exists, but ensure it's complete)"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT * FROM reminders WHERE id = %s",
                (reminder_id,)
            )
            return await cur.fetchone()
```

### 3.2 Add Job Queue Cancel Method

**File**: `src/scheduler/reminder_manager.py`

**Add new method**:
```python
async def cancel_reminder_by_id(self, reminder_id: str) -> bool:
    """
    Cancel a scheduled reminder by its reminder_id

    Args:
        reminder_id: UUID of the reminder

    Returns:
        True if cancelled, False if not found
    """
    job_name = f"custom_reminder_{reminder_id}"
    return await self.cancel_reminder(job_name)
```

**Why**: Provides clean interface to cancel jobs by reminder UUID

### 3.3 Add Agent Tool: delete_reminder

**File**: `src/agent/__init__.py`

**Add result model** (around line 90):
```python
class ReminderOperationResult(BaseModel):
    """Result of reminder delete/update operation"""
    success: bool
    message: str
    reminder_id: Optional[str] = None
```

**Add tool** (after `get_user_reminders`):
```python
@agent.tool
async def delete_reminder(ctx, reminder_id: str) -> ReminderOperationResult:
    """
    Delete a reminder by its ID

    Args:
        reminder_id: The UUID of the reminder to delete

    Returns:
        ReminderOperationResult with success status
    """
    deps: AgentDeps = ctx.deps

    try:
        from src.db.queries import delete_reminder as db_delete_reminder
        from src.db.queries import get_reminder_by_id

        # Get reminder details for confirmation message
        reminder = await get_reminder_by_id(reminder_id)

        if not reminder:
            return ReminderOperationResult(
                success=False,
                message=f"❌ Reminder not found: {reminder_id}",
                reminder_id=reminder_id
            )

        # Security: Verify it belongs to this user
        if reminder["user_id"] != deps.telegram_id:
            return ReminderOperationResult(
                success=False,
                message="❌ You can only delete your own reminders",
                reminder_id=reminder_id
            )

        # Delete from database
        deleted = await db_delete_reminder(reminder_id, deps.telegram_id)

        if not deleted:
            return ReminderOperationResult(
                success=False,
                message=f"❌ Failed to delete reminder {reminder_id}",
                reminder_id=reminder_id
            )

        # Cancel from job queue
        if deps.reminder_manager:
            await deps.reminder_manager.cancel_reminder_by_id(reminder_id)

        # Format confirmation
        schedule = reminder.get("schedule", {})
        if isinstance(schedule, str):
            import json
            schedule = json.loads(schedule)

        message_text = reminder.get("message", "")
        time_str = schedule.get("time", "")
        tz_str = schedule.get("timezone", "UTC")

        return ReminderOperationResult(
            success=True,
            message=(
                f"✅ Deleted reminder:\n\n"
                f"📝 {message_text}\n"
                f"⏰ {time_str} {tz_str}"
            ),
            reminder_id=reminder_id
        )

    except Exception as e:
        logger.error(f"Error deleting reminder: {e}", exc_info=True)
        return ReminderOperationResult(
            success=False,
            message=f"❌ Error: {str(e)}",
            reminder_id=reminder_id
        )
```

**Register tool** in `create_dynamic_agent` (around line 2131):
```python
dynamic_agent.tool(delete_reminder)  # Add this line
```

### 3.4 Add Agent Tool: update_reminder

**File**: `src/agent/__init__.py`

**Add tool** (after `delete_reminder`):
```python
@agent.tool
async def update_reminder(
    ctx,
    reminder_id: str,
    new_time: Optional[str] = None,
    new_message: Optional[str] = None
) -> ReminderOperationResult:
    """
    Update an existing reminder's time or message

    Args:
        reminder_id: The UUID of the reminder to update
        new_time: New time in "HH:MM" format (optional)
        new_message: New reminder message (optional)

    Returns:
        ReminderOperationResult with success status
    """
    deps: AgentDeps = ctx.deps

    try:
        from src.db.queries import (
            update_reminder as db_update_reminder,
            get_reminder_by_id
        )

        # Validate at least one field to update
        if new_time is None and new_message is None:
            return ReminderOperationResult(
                success=False,
                message="❌ Please specify what to update (time or message)",
                reminder_id=reminder_id
            )

        # Get current reminder
        reminder = await get_reminder_by_id(reminder_id)

        if not reminder:
            return ReminderOperationResult(
                success=False,
                message=f"❌ Reminder not found: {reminder_id}",
                reminder_id=reminder_id
            )

        # Security check
        if reminder["user_id"] != deps.telegram_id:
            return ReminderOperationResult(
                success=False,
                message="❌ You can only update your own reminders",
                reminder_id=reminder_id
            )

        # Update in database
        updated = await db_update_reminder(
            reminder_id=reminder_id,
            user_id=deps.telegram_id,
            new_time=new_time,
            new_message=new_message
        )

        if not updated:
            return ReminderOperationResult(
                success=False,
                message=f"❌ Failed to update reminder {reminder_id}",
                reminder_id=reminder_id
            )

        # Reschedule in job queue
        if deps.reminder_manager:
            # Cancel old job
            await deps.reminder_manager.cancel_reminder_by_id(reminder_id)

            # Parse updated schedule
            updated_schedule = updated["schedule"]
            if isinstance(updated_schedule, str):
                import json
                updated_schedule = json.loads(updated_schedule)

            # Schedule new job
            await deps.reminder_manager.schedule_custom_reminder(
                user_id=deps.telegram_id,
                reminder_time=updated_schedule.get("time"),
                message=updated["message"],
                reminder_type="daily",
                user_timezone=updated_schedule.get("timezone", "UTC"),
                reminder_id=reminder_id,
                days=updated_schedule.get("days", list(range(7)))
            )

        # Format confirmation
        changes = []
        if new_time:
            changes.append(f"⏰ Time: {new_time}")
        if new_message:
            changes.append(f"📝 Message: {new_message}")

        return ReminderOperationResult(
            success=True,
            message=(
                f"✅ Updated reminder:\n\n"
                + "\n".join(changes)
            ),
            reminder_id=reminder_id
        )

    except Exception as e:
        logger.error(f"Error updating reminder: {e}", exc_info=True)
        return ReminderOperationResult(
            success=False,
            message=f"❌ Error: {str(e)}",
            reminder_id=reminder_id
        )
```

**Register tool** in `create_dynamic_agent` (around line 2131):
```python
dynamic_agent.tool(update_reminder)  # Add this line
```

### 3.5 Add Agent Tool: cleanup_duplicate_reminders

**File**: `src/agent/__init__.py`

**Add result model**:
```python
class CleanupResult(BaseModel):
    """Result of cleanup operation"""
    success: bool
    message: str
    checked: int = 0
    deactivated: int = 0
    groups: int = 0
```

**Add tool**:
```python
@agent.tool
async def cleanup_duplicate_reminders(ctx) -> CleanupResult:
    """
    Find and remove duplicate reminders for the current user

    Keeps the oldest reminder when duplicates are found (same message, time, timezone).

    Returns:
        CleanupResult with counts of duplicates found and removed
    """
    deps: AgentDeps = ctx.deps

    try:
        from src.db.queries import (
            find_duplicate_reminders,
            deactivate_duplicate_reminders
        )

        # Find duplicates for this user
        duplicates = await find_duplicate_reminders(user_id=deps.telegram_id)

        if not duplicates:
            return CleanupResult(
                success=True,
                message="✅ No duplicate reminders found! Your reminders are clean.",
                checked=0,
                deactivated=0,
                groups=0
            )

        # Deactivate duplicates
        result = await deactivate_duplicate_reminders(user_id=deps.telegram_id)

        # Cancel jobs for deactivated reminders
        if deps.reminder_manager:
            for dup in duplicates:
                # Get the remove_ids and cancel their jobs
                remove_ids = dup.get("remove_ids", [])
                for rid in remove_ids:
                    await deps.reminder_manager.cancel_reminder_by_id(str(rid))

        # Format result message
        message = (
            f"✅ **Cleanup Complete**\n\n"
            f"📊 Found {result['groups']} groups with duplicates\n"
            f"🗑️ Removed {result['deactivated']} duplicate reminders\n"
            f"✅ Kept {result['groups']} original reminders\n\n"
            f"Your reminders are now clean! "
            f"You should only receive one notification per reminder."
        )

        return CleanupResult(
            success=True,
            message=message,
            checked=result["checked"],
            deactivated=result["deactivated"],
            groups=result["groups"]
        )

    except Exception as e:
        logger.error(f"Error cleaning up duplicates: {e}", exc_info=True)
        return CleanupResult(
            success=False,
            message=f"❌ Error during cleanup: {str(e)}",
            checked=0,
            deactivated=0,
            groups=0
        )
```

**Register tool**:
```python
dynamic_agent.tool(cleanup_duplicate_reminders)  # Add this line
```

### 3.6 Improve list_reminders to show IDs

**File**: `src/agent/__init__.py`

**Modify `get_user_reminders`** to include formatted list with IDs:

```python
@agent.tool
async def get_user_reminders(ctx) -> RemindersListResult:
    """
    Get all active reminders for the current user

    Returns:
        RemindersListResult with list of active reminders (including IDs)
    """
    deps: AgentDeps = ctx.deps

    try:
        from src.db.queries import get_active_reminders

        reminders = await get_active_reminders(deps.telegram_id)

        if not reminders:
            return RemindersListResult(
                success=True,
                message="You have no active reminders",
                reminders=[]
            )

        # Format reminders for display
        reminder_list = []
        formatted_lines = []

        for i, r in enumerate(reminders, 1):
            schedule = r.get('schedule', {})
            if isinstance(schedule, str):
                import json
                schedule = json.loads(schedule)

            reminder_id = str(r.get('id'))
            message = r.get('message', '')
            time_str = schedule.get('time', '')
            tz = schedule.get('timezone', 'UTC')
            days = schedule.get('days', list(range(7)))

            # Format days
            if len(days) == 7:
                days_str = "Every day"
            elif len(days) == 5 and days == [0,1,2,3,4]:
                days_str = "Weekdays"
            elif len(days) == 2 and days == [5,6]:
                days_str = "Weekends"
            else:
                day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                days_str = ", ".join(day_names[d] for d in sorted(days))

            # Add to formatted display
            formatted_lines.append(
                f"{i}. **{message}**\n"
                f"   ⏰ {time_str} {tz} • {days_str}\n"
                f"   🆔 `{reminder_id[:8]}...`"
            )

            # Add to data list
            reminder_list.append({
                'id': reminder_id,
                'message': message,
                'time': time_str,
                'type': r.get('reminder_type'),
                'timezone': tz,
                'days': days
            })

        count = len(reminders)
        formatted_message = (
            f"📋 **Your Reminders** ({count})\n\n" +
            "\n\n".join(formatted_lines) +
            "\n\n💡 To delete: \"delete reminder [message or ID]\""
            "\n💡 To update: \"change [reminder] to [new time]\""
        )

        return RemindersListResult(
            success=True,
            message=formatted_message,
            reminders=reminder_list
        )

    except Exception as e:
        logger.error(f"Error getting reminders: {e}", exc_info=True)
        return RemindersListResult(
            success=False,
            message=f"Error: {str(e)}",
            reminders=[]
        )
```

**Why**: Shows users their reminder IDs so they can reference them for deletion/updates

---

## Phase 4: Verification & Testing

### 4.1 Manual Testing Checklist

**Test duplicate prevention**:
- [ ] Create a reminder: "Morning vitamins at 08:00"
- [ ] Try to create the same reminder again
- [ ] Verify: Bot says "You already have this reminder" ✅
- [ ] Check DB: Only 1 entry exists ✅

**Test duplicate cleanup**:
- [ ] Manually create duplicate in DB (for testing)
- [ ] Ask bot: "Clean up my duplicate reminders"
- [ ] Verify: Bot finds and removes duplicates ✅
- [ ] Check DB: Only oldest reminder remains active ✅
- [ ] Restart bot
- [ ] Verify: Only 1 notification received ✅

**Test days filtering**:
- [ ] Create reminder: "Weekday standup at 09:00" (Mon-Fri only)
- [ ] Wait for Saturday
- [ ] Verify: No reminder fires on Saturday ✅
- [ ] Wait for Monday
- [ ] Verify: Reminder fires on Monday ✅

**Test deletion**:
- [ ] Create reminder: "Test reminder at 14:00"
- [ ] Ask bot: "Delete my test reminder"
- [ ] Verify: Bot confirms deletion ✅
- [ ] List reminders
- [ ] Verify: Test reminder not in list ✅
- [ ] Wait for 14:00
- [ ] Verify: No notification received ✅

**Test updating**:
- [ ] Create reminder: "Exercise at 17:00"
- [ ] Ask bot: "Change my exercise reminder to 18:00"
- [ ] Verify: Bot confirms update ✅
- [ ] List reminders
- [ ] Verify: Shows new time 18:00 ✅
- [ ] Wait for 18:00
- [ ] Verify: Receives reminder at new time ✅

**Test job queue uniqueness**:
- [ ] Create 2 reminders at same time: "Med A at 08:00" and "Med B at 08:00"
- [ ] Check logs: Verify 2 separate jobs created ✅
- [ ] Wait for 08:00
- [ ] Verify: Receive 2 notifications (one for each) ✅
- [ ] Restart bot
- [ ] Wait for 08:00 next day
- [ ] Verify: Still receive exactly 2 notifications ✅

### 4.2 Database Verification Queries

**Check for duplicates**:
```sql
SELECT
  user_id,
  message,
  schedule->>'time' as time,
  schedule->>'timezone' as tz,
  COUNT(*) as count
FROM reminders
WHERE active = true
GROUP BY user_id, message, schedule->>'time', schedule->>'timezone'
HAVING COUNT(*) > 1;
```

**Expected**: No results (0 duplicates)

**Check job names in logs**:
```bash
grep "Scheduled.*reminder" bot.log | tail -20
```

**Expected**: Each reminder has unique job name with UUID

### 4.3 Integration Test

Create automated test script:

**File**: `tests/integration/test_reminder_fixes.py`

```python
"""Integration tests for reminder system fixes"""
import pytest
from src.db.queries import (
    create_reminder,
    find_duplicate_reminders,
    delete_reminder,
    update_reminder,
    get_active_reminders
)
from src.models.reminder import Reminder, ReminderSchedule
from uuid import uuid4


@pytest.mark.asyncio
async def test_no_duplicates_created():
    """Test that duplicate detection works"""
    user_id = "test_user_123"

    # Create first reminder
    r1 = Reminder(
        id=uuid4(),
        user_id=user_id,
        reminder_type="daily",
        message="Test reminder",
        schedule=ReminderSchedule(
            type="daily",
            time="08:00",
            timezone="UTC",
            days=list(range(7))
        )
    )
    await create_reminder(r1)

    # Check for duplicates (should be none yet)
    dups = await find_duplicate_reminders(user_id)
    assert len(dups) == 0

    # Try to create duplicate
    r2 = Reminder(
        id=uuid4(),
        user_id=user_id,
        reminder_type="daily",
        message="Test reminder",  # Same message
        schedule=ReminderSchedule(
            type="daily",
            time="08:00",  # Same time
            timezone="UTC",  # Same timezone
            days=list(range(7))
        )
    )

    # In real app, this should be blocked by agent tool
    # But if it gets through, cleanup should find it
    await create_reminder(r2)

    # Now find duplicates
    dups = await find_duplicate_reminders(user_id)
    assert len(dups) == 1
    assert dups[0]["duplicate_count"] == 2

    # Cleanup
    await delete_reminder(str(r1.id), user_id)
    await delete_reminder(str(r2.id), user_id)


@pytest.mark.asyncio
async def test_delete_reminder():
    """Test reminder deletion"""
    user_id = "test_user_456"

    # Create reminder
    r = Reminder(
        id=uuid4(),
        user_id=user_id,
        reminder_type="daily",
        message="Delete me",
        schedule=ReminderSchedule(
            type="daily",
            time="10:00",
            timezone="UTC"
        )
    )
    await create_reminder(r)

    # Verify it exists
    reminders = await get_active_reminders(user_id)
    assert len(reminders) == 1

    # Delete it
    deleted = await delete_reminder(str(r.id), user_id)
    assert deleted is True

    # Verify it's gone
    reminders = await get_active_reminders(user_id)
    assert len(reminders) == 0


@pytest.mark.asyncio
async def test_update_reminder():
    """Test reminder updates"""
    user_id = "test_user_789"

    # Create reminder
    r = Reminder(
        id=uuid4(),
        user_id=user_id,
        reminder_type="daily",
        message="Original message",
        schedule=ReminderSchedule(
            type="daily",
            time="09:00",
            timezone="UTC"
        )
    )
    await create_reminder(r)

    # Update it
    updated = await update_reminder(
        reminder_id=str(r.id),
        user_id=user_id,
        new_time="10:00",
        new_message="Updated message"
    )
    assert updated is not None
    assert updated["message"] == "Updated message"

    schedule = updated["schedule"]
    if isinstance(schedule, str):
        import json
        schedule = json.loads(schedule)
    assert schedule["time"] == "10:00"

    # Cleanup
    await delete_reminder(str(r.id), user_id)
```

---

## Rollout Plan

### Step 1: Emergency Cleanup (Do Immediately)
1. Run cleanup script on production database
2. Restart bot to reload clean reminder list
3. Verify users stop receiving duplicate notifications

### Step 2: Deploy Prevention (Same Day)
1. Deploy duplicate detection in `schedule_reminder`
2. Deploy job naming fix (include reminder_id)
3. Restart bot
4. Monitor logs for any issues

### Step 3: Deploy Management Tools (Next Day)
1. Deploy delete_reminder tool
2. Deploy update_reminder tool
3. Deploy cleanup_duplicate_reminders tool
4. Update system prompt to mention these capabilities
5. Test with real users

### Step 4: Deploy Days Filter (Next Day)
1. Deploy days-of-week filtering
2. Restart bot
3. Monitor for correct day behavior
4. User testing over a week period

### Step 5: Verification (Ongoing)
1. Monitor user feedback
2. Check logs for errors
3. Run database queries to verify no new duplicates
4. Confirm reminders fire on correct days

---

## Rollback Plan

If issues occur:

**Phase 1 rollback**: Reactivate all reminders, restart bot
```sql
UPDATE reminders SET active = true WHERE user_id = 'affected_user';
```

**Phase 2 rollback**: Revert job naming change, restart bot

**Phase 3 rollback**: Disable new tools in agent registration

**Phase 4 rollback**: Remove days check from callback

---

## Success Metrics

- ✅ Zero duplicate reminders in database
- ✅ Users receive exactly 1 notification per reminder
- ✅ Reminders fire on correct days only
- ✅ Users can delete reminders conversationally
- ✅ Users can update reminders conversationally
- ✅ Bot can clean up duplicates when asked
- ✅ No new duplicates created after fix

---

## Files Modified Summary

### New Files
- `/scripts/cleanup_duplicate_reminders.py` - Emergency cleanup script
- `/tests/integration/test_reminder_fixes.py` - Integration tests
- `/docs/rca/issue-30-triple-reminders.md` - RCA document (already exists)
- `.agents/plans/issue-30-reminder-fixes.md` - This implementation plan

### Modified Files
1. **`src/db/queries.py`**
   - Add `find_duplicate_reminders()`
   - Add `deactivate_duplicate_reminders()`
   - Add `delete_reminder()`
   - Add `update_reminder()`

2. **`src/scheduler/reminder_manager.py`**
   - Update job naming to use reminder_id (line ~135)
   - Add `days` parameter to `schedule_custom_reminder()`
   - Implement days filtering in `_send_custom_reminder()`
   - Update `load_reminders()` to pass days
   - Add `cancel_reminder_by_id()` method

3. **`src/agent/__init__.py`**
   - Add duplicate detection to `schedule_reminder()` (line ~462)
   - Add `ReminderOperationResult` model
   - Add `CleanupResult` model
   - Add `delete_reminder()` tool
   - Add `update_reminder()` tool
   - Add `cleanup_duplicate_reminders()` tool
   - Update `get_user_reminders()` to show IDs
   - Register new tools in `create_dynamic_agent()`

---

## Timeline

- **Immediate (0-1 hour)**: Emergency cleanup script + deployment
- **Day 1 (2-3 hours)**: Prevention fixes (duplicate detection + job naming)
- **Day 2 (3-4 hours)**: Management tools (delete/update/cleanup)
- **Day 3 (1-2 hours)**: Days filtering + testing
- **Day 4-7**: Monitoring and verification

**Total estimated effort**: 8-11 hours across 1 week

---

## Notes

- Keep old duplicates in DB (active=false) for debugging
- Add extensive logging during rollout
- Test with one user before production deployment
- Document new capabilities in user guide
- Consider adding notification: "Reminder system has been fixed! Run /cleanup to remove duplicates"

---

## Questions / Decisions Needed

1. ✅ Should we permanently delete duplicate reminders or just deactivate? **Decision: Deactivate (set active=false) to preserve audit trail**

2. ✅ Should cleanup tool auto-run on bot startup? **Decision: No, manual only to avoid surprises**

3. ✅ How to handle partial day names in user requests? "weekdays", "weekends", "Mon-Fri" **Decision: Agent should parse and convert to day numbers, store in days field**

4. ⚠️ Should we add database unique constraint? **Decision: Yes, but as phase 2 after duplicates are cleaned**

5. ⚠️ Timezone conversion verification needed? **Decision: Add extensive logging first, fix if issues found**
