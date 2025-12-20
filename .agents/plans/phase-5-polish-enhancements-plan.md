# Phase 5: Polish & Enhancements - Implementation Plan

**Issue**: #11 - Gamification and Motivation System
**Phase**: 5 of 5 (Final Phase)
**Timeline**: 2 weeks (Weeks 10-11)
**Estimated Effort**: 19-27 hours
**Status**: Ready for Implementation

---

## Executive Summary

Phase 5 completes the comprehensive gamification and motivation system by adding:
1. **Completion Notes** - Context and templates for health tracking
2. **Achievement System** - Badges and milestones for motivation
3. **Data Export** - User data ownership and portability
4. **Avatar Customization** - Personal profile and badge display
5. **UI Polish** - Enhanced visual experience across all features
6. **Comprehensive Testing** - Quality assurance and optimization

This phase builds on the solid foundation of Phases 1-4 (already implemented) which includes:
- ✅ Completion tracking with Done/Skip/Snooze buttons
- ✅ Streak calculation and motivation
- ✅ Comprehensive analytics and statistics
- ✅ Day-of-week pattern analysis
- ✅ Multi-reminder comparison dashboard

---

## Current Implementation Status

### ✅ COMPLETED (Phases 1-4)

**Database Tables:**
- `reminder_completions` (with notes field)
- `reminder_skips` (with reason field)
- `reminders` (with tracking preferences)

**Core Features:**
- Interactive completion buttons (Done/Skip/Snooze)
- Streak tracking (current + best streak)
- Completion rate analytics
- Day-of-week pattern analysis
- Multi-reminder comparison
- Skip reason tracking

**Agent Tools:**
- `schedule_reminder` - Smart tracking detection
- `get_reminder_statistics` - Single reminder analytics
- `compare_all_reminders` - Multi-reminder dashboard

### ❌ MISSING (Phase 5 Scope)

**Features to Build:**
1. Completion notes UI and templates
2. Achievement/badge system
3. Data export functionality
4. Avatar/profile customization
5. Enhanced visual formatting
6. Comprehensive testing

---

## Phase 5 Implementation Plan

### 🎯 Component 1: Completion Notes & Templates

**Priority**: HIGH (quick win, improves analytics immediately)
**Effort**: 2-3 hours
**Files to Modify**:
- `src/handlers/reminders.py` - Add note entry flow
- `src/db/queries.py` - Note retrieval functions
- `src/utils/reminder_formatters.py` - Display notes in stats

#### Implementation Steps

**1.1 Enhanced Completion Flow**

Update `handle_reminder_completion()` to offer note option:

```python
# src/handlers/reminders.py

async def handle_reminder_completion(update, context):
    """Handle Done button with optional note entry"""
    query = update.callback_query
    await query.answer()

    # Parse callback data
    _, reminder_id, scheduled_time_str = query.data.split(":")

    # Save completion
    completion_id = await save_reminder_completion(
        user_id=str(update.effective_user.id),
        reminder_id=reminder_id,
        scheduled_time=scheduled_time_str
    )

    # Get reminder details for context
    reminder = await get_reminder_by_id(reminder_id)

    # Calculate streak
    current_streak, best_streak = await calculate_current_streak(
        str(update.effective_user.id),
        reminder_id
    )

    # Build completion message
    message = format_completion_message(reminder, current_streak, best_streak)

    # Add note option
    keyboard = [
        [
            InlineKeyboardButton("📝 Add Note", callback_data=f"add_note:{completion_id}"),
            InlineKeyboardButton("📊 View Stats", callback_data=f"stats:{reminder_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode="Markdown")
```

**1.2 Note Entry Conversation**

Add conversation handler for note input:

```python
# src/handlers/reminders.py

async def handle_add_note_button(update, context):
    """User clicked 'Add Note' button"""
    query = update.callback_query
    await query.answer()

    _, completion_id = query.data.split(":")

    # Store completion_id in user_data
    context.user_data['pending_note_completion_id'] = completion_id

    # Get reminder details to show context-specific templates
    completion = await get_completion_by_id(completion_id)
    reminder = await get_reminder_by_id(completion['reminder_id'])

    # Show quick templates based on reminder type
    templates = get_note_templates(reminder)

    keyboard = []
    for template in templates:
        keyboard.append([InlineKeyboardButton(template, callback_data=f"note_template:{template}")])
    keyboard.append([InlineKeyboardButton("✍️ Write Custom Note", callback_data="note_custom")])
    keyboard.append([InlineKeyboardButton("⏭️ Skip Note", callback_data="note_skip")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"📝 Add a note to this completion?\n\n{reminder['message']}\n\nQuick templates:",
        reply_markup=reply_markup
    )

async def handle_note_template(update, context):
    """User selected a template"""
    query = update.callback_query
    await query.answer()

    _, template_text = query.data.split(":", 1)
    completion_id = context.user_data.get('pending_note_completion_id')

    # Save note
    await update_completion_note(completion_id, template_text)

    await query.edit_message_text(
        f"✅ Note saved!\n\n📝 \"{template_text}\"\n\nThis will help track patterns over time."
    )

    # Clean up
    context.user_data.pop('pending_note_completion_id', None)

async def handle_note_custom(update, context):
    """User wants to write custom note"""
    query = update.callback_query
    await query.answer()

    context.user_data['awaiting_custom_note'] = True

    await query.edit_message_text(
        "✍️ Type your note below:\n\n(Keep it short - max 200 characters)\n\nOr send /cancel to skip."
    )

async def handle_custom_note_text(update, context):
    """User typed a custom note"""
    if not context.user_data.get('awaiting_custom_note'):
        return

    note_text = update.message.text[:200]  # Limit to 200 chars
    completion_id = context.user_data.get('pending_note_completion_id')

    # Save note
    await update_completion_note(completion_id, note_text)

    await update.message.reply_text(
        f"✅ Note saved!\n\n📝 \"{note_text}\"\n\nThis will help track patterns over time."
    )

    # Clean up
    context.user_data.pop('pending_note_completion_id', None)
    context.user_data.pop('awaiting_custom_note', None)
```

**1.3 Note Templates**

Create template system:

```python
# src/utils/reminder_formatters.py

def get_note_templates(reminder: dict) -> list[str]:
    """Get context-aware note templates based on reminder type"""

    message_lower = reminder['message'].lower()

    # Medication/supplements
    if any(kw in message_lower for kw in ['medication', 'medicine', 'pill', 'supplement', 'vitamin']):
        return [
            "✅ No issues",
            "😵 Felt dizzy",
            "🤢 Nauseous",
            "😴 Drowsy",
            "⚡ Energized",
            "💊 Side effects noted"
        ]

    # Blood pressure
    if 'blood pressure' in message_lower or 'bp' in message_lower:
        return [
            "120/80 - Normal",
            "130/85 - Slightly elevated",
            "140/90 - High",
            "110/70 - Low",
            "📊 Recorded in log"
        ]

    # Exercise/fitness
    if any(kw in message_lower for kw in ['exercise', 'workout', 'walk', 'run', 'gym', 'yoga']):
        return [
            "💪 Great workout!",
            "😊 Easy session",
            "😅 Tough but finished",
            "🤕 Modified - injury",
            "⏱️ 30 min",
            "⏱️ 60 min"
        ]

    # Water/hydration
    if any(kw in message_lower for kw in ['water', 'hydrat', 'drink']):
        return [
            "💧 8 glasses",
            "💧 4 glasses",
            "💧 2 glasses",
            "☕ Coffee counted",
            "🥤 With electrolytes"
        ]

    # Sleep
    if 'sleep' in message_lower:
        return [
            "😴 7-8 hours",
            "😴 6-7 hours",
            "😴 5-6 hours",
            "😴 <5 hours",
            "😊 Well rested",
            "😫 Poor quality"
        ]

    # Generic templates
    return [
        "✅ Completed as planned",
        "⏰ Did it early",
        "⏰ Did it late",
        "💯 Felt great",
        "😊 Good enough"
    ]
```

**1.4 Display Notes in Statistics**

Update statistics formatter:

```python
# src/utils/reminder_formatters.py

async def format_reminder_statistics(
    stats: dict,
    reminder: dict,
    include_notes: bool = True
) -> str:
    """Format reminder statistics with optional note display"""

    # ... existing stats formatting ...

    if include_notes and stats.get('recent_completions_with_notes'):
        message += "\n\n📝 **Recent Completions with Notes**\n"

        for completion in stats['recent_completions_with_notes'][:5]:
            date_str = completion['completed_at'].strftime("%b %d, %I:%M %p")
            delay = completion.get('delay_minutes', 0)

            status_emoji = "✅"
            if delay < -5:
                status_emoji = "⚡"  # Early
            elif delay > 30:
                status_emoji = "🕐"  # Late

            message += f"\n{status_emoji} {date_str}"
            if delay != 0:
                message += f" ({abs(delay)} min {'early' if delay < 0 else 'late'})"

            if completion.get('notes'):
                message += f"\n   📝 \"{completion['notes']}\""

            message += "\n"

    # Note pattern analysis (if enough notes exist)
    if stats.get('note_patterns'):
        message += "\n\n🔍 **Note Patterns**\n"
        for pattern, count in stats['note_patterns'].items():
            message += f"• {pattern}: {count} times\n"

    return message
```

**1.5 Database Functions**

Add note retrieval:

```python
# src/db/queries.py

async def get_completion_by_id(completion_id: str) -> dict:
    """Get completion details by ID"""
    async with get_db_connection() as conn:
        result = await conn.fetchrow(
            """
            SELECT c.*, r.message, r.reminder_type
            FROM reminder_completions c
            JOIN reminders r ON c.reminder_id = r.id
            WHERE c.id = $1
            """,
            completion_id
        )
        return dict(result) if result else None

async def update_completion_note(completion_id: str, note: str):
    """Add or update note for a completion"""
    async with get_db_connection() as conn:
        await conn.execute(
            """
            UPDATE reminder_completions
            SET notes = $1
            WHERE id = $2
            """,
            note,
            completion_id
        )

async def get_recent_completions_with_notes(
    user_id: str,
    reminder_id: str,
    limit: int = 10
) -> list[dict]:
    """Get recent completions that have notes"""
    async with get_db_connection() as conn:
        results = await conn.fetch(
            """
            SELECT
                id,
                completed_at,
                scheduled_time,
                notes,
                EXTRACT(EPOCH FROM (completed_at - scheduled_time))/60 as delay_minutes
            FROM reminder_completions
            WHERE user_id = $1 AND reminder_id = $2 AND notes IS NOT NULL
            ORDER BY completed_at DESC
            LIMIT $3
            """,
            user_id,
            reminder_id,
            limit
        )
        return [dict(r) for r in results]

async def analyze_note_patterns(
    user_id: str,
    reminder_id: str,
    days: int = 30
) -> dict[str, int]:
    """Analyze frequently mentioned keywords in notes"""
    async with get_db_connection() as conn:
        results = await conn.fetch(
            """
            SELECT notes
            FROM reminder_completions
            WHERE user_id = $1
            AND reminder_id = $2
            AND notes IS NOT NULL
            AND completed_at > NOW() - INTERVAL '1 day' * $3
            """,
            user_id,
            reminder_id,
            days
        )

        # Simple keyword extraction
        keywords = {}
        common_patterns = [
            'dizzy', 'nauseous', 'tired', 'energized', 'pain',
            'side effects', 'good', 'great', 'poor', 'difficult',
            'early', 'late', 'rushed'
        ]

        for row in results:
            note_lower = row['notes'].lower()
            for pattern in common_patterns:
                if pattern in note_lower:
                    keywords[pattern] = keywords.get(pattern, 0) + 1

        return dict(sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:5])
```

---

### 🏆 Component 2: Achievement System

**Priority**: HIGH (high engagement value)
**Effort**: 4-6 hours
**Files to Create/Modify**:
- `migrations/008_achievements_system.sql` - New tables
- `src/models/achievement.py` - Achievement models
- `src/db/queries.py` - Achievement functions
- `src/handlers/achievements.py` - Achievement handlers
- `src/utils/achievement_checker.py` - Unlock detection

#### Implementation Steps

**2.1 Database Schema**

```sql
-- migrations/008_achievements_system.sql

-- Achievement definitions table
CREATE TABLE IF NOT EXISTS achievements (
    id VARCHAR(50) PRIMARY KEY,  -- e.g., 'first_completion', 'week_warrior'
    name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    icon VARCHAR(10),  -- emoji
    category VARCHAR(50),  -- 'consistency', 'milestones', 'recovery', 'social'
    criteria JSONB NOT NULL,  -- {type: 'streak', value: 7}
    tier VARCHAR(20),  -- 'bronze', 'silver', 'gold', 'platinum'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User achievements (unlocked badges)
CREATE TABLE IF NOT EXISTS user_achievements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    achievement_id VARCHAR(50) NOT NULL REFERENCES achievements(id),
    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,  -- {reminder_id: '...', streak: 30}
    UNIQUE(user_id, achievement_id)
);

CREATE INDEX idx_user_achievements_user ON user_achievements(user_id, unlocked_at DESC);

COMMENT ON TABLE achievements IS 'Achievement definitions for gamification';
COMMENT ON TABLE user_achievements IS 'Tracks which achievements each user has unlocked';
```

**2.2 Achievement Definitions**

```python
# src/models/achievement.py

from enum import Enum
from pydantic import BaseModel
from typing import Optional, Any

class AchievementCategory(str, Enum):
    CONSISTENCY = "consistency"
    MILESTONES = "milestones"
    RECOVERY = "recovery"
    SOCIAL = "social"
    EXPLORATION = "exploration"

class AchievementTier(str, Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"

class Achievement(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    category: AchievementCategory
    criteria: dict[str, Any]
    tier: AchievementTier

class UserAchievement(BaseModel):
    user_id: str
    achievement_id: str
    unlocked_at: str
    metadata: Optional[dict] = None

# Pre-defined achievements
ACHIEVEMENT_DEFINITIONS = [
    Achievement(
        id="first_steps",
        name="First Steps",
        description="Completed your first tracked reminder",
        icon="👣",
        category=AchievementCategory.MILESTONES,
        criteria={"type": "total_completions", "value": 1},
        tier=AchievementTier.BRONZE
    ),
    Achievement(
        id="week_warrior",
        name="Week Warrior",
        description="Maintained a 7-day streak",
        icon="🔥",
        category=AchievementCategory.CONSISTENCY,
        criteria={"type": "streak", "value": 7},
        tier=AchievementTier.SILVER
    ),
    Achievement(
        id="perfect_month",
        name="Perfect Month",
        description="100% completion rate for 30 days",
        icon="💯",
        category=AchievementCategory.CONSISTENCY,
        criteria={"type": "perfect_days", "value": 30},
        tier=AchievementTier.GOLD
    ),
    Achievement(
        id="century_club",
        name="Century Club",
        description="Completed 100 tracked tasks",
        icon="💯",
        category=AchievementCategory.MILESTONES,
        criteria={"type": "total_completions", "value": 100},
        tier=AchievementTier.GOLD
    ),
    Achievement(
        id="early_bird",
        name="Early Bird",
        description="Completed 10 reminders early (before scheduled time)",
        icon="🌅",
        category=AchievementCategory.CONSISTENCY,
        criteria={"type": "early_completions", "value": 10},
        tier=AchievementTier.SILVER
    ),
    Achievement(
        id="comeback_kid",
        name="Comeback Kid",
        description="Returned to 80%+ completion rate after a difficult week",
        icon="💪",
        category=AchievementCategory.RECOVERY,
        criteria={"type": "recovery", "threshold": 0.8},
        tier=AchievementTier.GOLD
    ),
    Achievement(
        id="multi_tasker",
        name="Multi-Tasker",
        description="Actively tracking 3+ health habits",
        icon="⚡",
        category=AchievementCategory.MILESTONES,
        criteria={"type": "active_reminders", "value": 3},
        tier=AchievementTier.SILVER
    ),
    Achievement(
        id="data_enthusiast",
        name="Data Enthusiast",
        description="Checked statistics 10+ times",
        icon="📊",
        category=AchievementCategory.EXPLORATION,
        criteria={"type": "stats_views", "value": 10},
        tier=AchievementTier.BRONZE
    ),
    Achievement(
        id="streak_legend",
        name="Streak Legend",
        description="Achieved a 30-day streak",
        icon="🏆",
        category=AchievementCategory.CONSISTENCY,
        criteria={"type": "streak", "value": 30},
        tier=AchievementTier.PLATINUM
    ),
    Achievement(
        id="hundred_day_hero",
        name="100-Day Hero",
        description="Maintained a 100-day streak",
        icon="💎",
        category=AchievementCategory.CONSISTENCY,
        criteria={"type": "streak", "value": 100},
        tier=AchievementTier.PLATINUM
    ),
]
```

**2.3 Achievement Detection**

```python
# src/utils/achievement_checker.py

from src.models.achievement import ACHIEVEMENT_DEFINITIONS
from src.db.queries import (
    get_user_achievements,
    unlock_achievement,
    get_reminder_analytics,
    count_user_completions,
    count_early_completions,
    count_active_reminders
)

async def check_and_unlock_achievements(
    user_id: str,
    reminder_id: str = None,
    event_type: str = "completion"
) -> list[str]:
    """
    Check if user has unlocked any new achievements

    Args:
        user_id: User's Telegram ID
        reminder_id: Optional reminder ID for context
        event_type: 'completion', 'stats_view', 'reminder_created'

    Returns:
        List of newly unlocked achievement IDs
    """

    # Get already unlocked achievements
    unlocked = await get_user_achievements(user_id)
    unlocked_ids = {a['achievement_id'] for a in unlocked}

    newly_unlocked = []

    for achievement in ACHIEVEMENT_DEFINITIONS:
        # Skip if already unlocked
        if achievement.id in unlocked_ids:
            continue

        # Check criteria
        unlocked = await check_achievement_criteria(user_id, achievement, reminder_id)

        if unlocked:
            # Unlock achievement
            await unlock_achievement(user_id, achievement.id, {"reminder_id": reminder_id})
            newly_unlocked.append(achievement.id)

    return newly_unlocked

async def check_achievement_criteria(
    user_id: str,
    achievement: Achievement,
    reminder_id: str = None
) -> bool:
    """Check if user meets achievement criteria"""

    criteria_type = achievement.criteria.get("type")
    criteria_value = achievement.criteria.get("value")

    # Total completions
    if criteria_type == "total_completions":
        total = await count_user_completions(user_id)
        return total >= criteria_value

    # Streak achievement
    if criteria_type == "streak":
        if not reminder_id:
            # Check best streak across all reminders
            reminders = await get_user_reminders(user_id)
            for r in reminders:
                _, best_streak = await calculate_current_streak(user_id, r['id'])
                if best_streak >= criteria_value:
                    return True
            return False
        else:
            current_streak, best_streak = await calculate_current_streak(user_id, reminder_id)
            return current_streak >= criteria_value or best_streak >= criteria_value

    # Perfect days (100% completion)
    if criteria_type == "perfect_days":
        # Count consecutive days with 100% completion
        perfect_days = await count_perfect_completion_days(user_id)
        return perfect_days >= criteria_value

    # Early completions
    if criteria_type == "early_completions":
        count = await count_early_completions(user_id)
        return count >= criteria_value

    # Active reminders
    if criteria_type == "active_reminders":
        count = await count_active_reminders(user_id, tracking_enabled=True)
        return count >= criteria_value

    # Recovery (comeback)
    if criteria_type == "recovery":
        # Check if user had low week (<60%) then recovered to >80%
        return await check_recovery_pattern(user_id, achievement.criteria['threshold'])

    # Stats views
    if criteria_type == "stats_views":
        count = await count_stats_views(user_id)
        return count >= criteria_value

    return False
```

**2.4 Achievement Display**

```python
# src/utils/reminder_formatters.py

def format_achievement_unlock(achievement: Achievement) -> str:
    """Format achievement unlock notification"""

    tier_emoji = {
        "bronze": "🥉",
        "silver": "🥈",
        "gold": "🥇",
        "platinum": "💎"
    }

    return f"""
🎉 **ACHIEVEMENT UNLOCKED!** 🎉

{achievement.icon} **{achievement.name}** {tier_emoji.get(achievement.tier, '')}

{achievement.description}

Keep up the great work! 💪
"""

async def format_user_achievements(user_id: str) -> str:
    """Display all user achievements"""

    unlocked = await get_user_achievements(user_id)
    total_achievements = len(ACHIEVEMENT_DEFINITIONS)

    message = f"🏆 **Your Achievements** ({len(unlocked)}/{total_achievements})\n\n"

    # Group by category
    by_category = {}
    for achievement_data in unlocked:
        achievement = next(a for a in ACHIEVEMENT_DEFINITIONS if a.id == achievement_data['achievement_id'])
        category = achievement.category.value
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(achievement)

    # Display by category
    for category, achievements in by_category.items():
        message += f"**{category.title()}** ({len(achievements)})\n"
        for achievement in achievements:
            message += f"{achievement.icon} {achievement.name}\n"
        message += "\n"

    # Show locked achievements (teaser)
    locked_ids = {a.id for a in ACHIEVEMENT_DEFINITIONS} - {a['achievement_id'] for a in unlocked}
    if locked_ids:
        message += "🔒 **Locked** (Keep going!)\n"
        for achievement in ACHIEVEMENT_DEFINITIONS:
            if achievement.id in locked_ids:
                message += f"❓ {achievement.name}\n"
                break  # Show just one teaser
        message += f"\n...and {len(locked_ids) - 1} more to unlock!\n"

    return message
```

**2.5 Integration with Completion Flow**

Update completion handler to check achievements:

```python
# src/handlers/reminders.py

from src.utils.achievement_checker import check_and_unlock_achievements
from src.utils.reminder_formatters import format_achievement_unlock
from src.models.achievement import ACHIEVEMENT_DEFINITIONS

async def handle_reminder_completion(update, context):
    """Handle Done button with achievement checking"""

    # ... existing completion logic ...

    # Check for newly unlocked achievements
    new_achievements = await check_and_unlock_achievements(
        user_id=str(update.effective_user.id),
        reminder_id=reminder_id,
        event_type="completion"
    )

    # Send achievement notifications
    for achievement_id in new_achievements:
        achievement = next(a for a in ACHIEVEMENT_DEFINITIONS if a.id == achievement_id)
        achievement_message = format_achievement_unlock(achievement)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=achievement_message,
            parse_mode="Markdown"
        )
```

---

### 📦 Component 3: Data Export

**Priority**: MEDIUM
**Effort**: 3-4 hours
**Files to Create/Modify**:
- `src/agent/__init__.py` - New export agent tool
- `src/utils/data_export.py` - Export formatters
- `src/handlers/export.py` - Export handlers

#### Implementation Steps

**3.1 Export Agent Tool**

```python
# src/agent/__init__.py

@agent.tool
async def export_user_data(
    ctx: AgentDeps,
    format: str = "json",  # json, csv, markdown
    include_achievements: bool = True,
    include_statistics: bool = True,
    days: int = 90
) -> ExportDataResult:
    """
    Export user's health data

    Args:
        format: Export format (json, csv, markdown)
        include_achievements: Include achievement data
        include_statistics: Include computed statistics
        days: Number of days of completion history to export

    Returns detailed export of all user data
    """
    user_id = str(ctx.deps.user_id)

    # Gather all data
    reminders = await get_user_reminders(user_id)
    completions = await get_all_user_completions(user_id, days=days)
    skips = await get_all_user_skips(user_id, days=days)

    achievements_data = None
    if include_achievements:
        achievements_data = await get_user_achievements(user_id)

    stats_data = None
    if include_statistics:
        stats_data = {}
        for reminder in reminders:
            stats = await get_reminder_analytics(user_id, reminder['id'], days=days)
            stats_data[reminder['id']] = stats

    # Format and export
    export_content = await format_export_data(
        format=format,
        reminders=reminders,
        completions=completions,
        skips=skips,
        achievements=achievements_data,
        statistics=stats_data
    )

    # Save to file and send
    file_path = await save_export_file(user_id, export_content, format)

    return ExportDataResult(
        success=True,
        file_path=file_path,
        format=format,
        record_count=len(completions),
        message=f"Exported {len(completions)} completions, {len(reminders)} reminders"
    )
```

**3.2 Export Formatters**

```python
# src/utils/data_export.py

import json
import csv
from io import StringIO
from datetime import datetime

async def format_export_data(
    format: str,
    reminders: list,
    completions: list,
    skips: list,
    achievements: list = None,
    statistics: dict = None
) -> str:
    """Format user data for export"""

    if format == "json":
        return format_json_export(reminders, completions, skips, achievements, statistics)
    elif format == "csv":
        return format_csv_export(completions, skips)
    elif format == "markdown":
        return format_markdown_export(reminders, completions, skips, achievements, statistics)
    else:
        raise ValueError(f"Unsupported format: {format}")

def format_json_export(reminders, completions, skips, achievements, statistics) -> str:
    """Export as JSON"""
    data = {
        "export_date": datetime.now().isoformat(),
        "reminders": reminders,
        "completions": [
            {
                "reminder_id": str(c['reminder_id']),
                "scheduled_time": c['scheduled_time'].isoformat(),
                "completed_at": c['completed_at'].isoformat(),
                "notes": c.get('notes')
            }
            for c in completions
        ],
        "skips": [
            {
                "reminder_id": str(s['reminder_id']),
                "scheduled_time": s['scheduled_time'].isoformat(),
                "skipped_at": s['skipped_at'].isoformat(),
                "reason": s.get('reason'),
                "notes": s.get('notes')
            }
            for s in skips
        ]
    }

    if achievements:
        data["achievements"] = achievements

    if statistics:
        data["statistics"] = statistics

    return json.dumps(data, indent=2)

def format_csv_export(completions, skips) -> str:
    """Export as CSV"""
    output = StringIO()
    writer = csv.writer(output)

    # Write completions
    writer.writerow(["Type", "Reminder ID", "Scheduled Time", "Actual Time", "Delay (min)", "Notes"])

    for c in completions:
        delay = (c['completed_at'] - c['scheduled_time']).total_seconds() / 60
        writer.writerow([
            "Completion",
            str(c['reminder_id']),
            c['scheduled_time'].isoformat(),
            c['completed_at'].isoformat(),
            f"{delay:.0f}",
            c.get('notes', '')
        ])

    for s in skips:
        writer.writerow([
            "Skip",
            str(s['reminder_id']),
            s['scheduled_time'].isoformat(),
            s['skipped_at'].isoformat(),
            "",
            f"Reason: {s.get('reason', 'N/A')}"
        ])

    return output.getvalue()

def format_markdown_export(reminders, completions, skips, achievements, statistics) -> str:
    """Export as Markdown report"""

    report = f"""# Health Agent Data Export

**Export Date**: {datetime.now().strftime("%B %d, %Y")}

## Summary

- **Active Reminders**: {len(reminders)}
- **Total Completions**: {len(completions)}
- **Total Skips**: {len(skips)}
"""

    if achievements:
        report += f"- **Achievements Unlocked**: {len(achievements)}\n"

    report += "\n## Reminders\n\n"
    for reminder in reminders:
        report += f"### {reminder['message']}\n"
        report += f"- Schedule: {reminder['schedule']}\n"
        report += f"- Tracking: {'✅ Enabled' if reminder.get('enable_completion_tracking') else '❌ Disabled'}\n"

        if statistics and str(reminder['id']) in statistics:
            stats = statistics[str(reminder['id'])]
            report += f"- Completion Rate: {stats.get('completion_rate', 0)*100:.1f}%\n"
            report += f"- Current Streak: {stats.get('current_streak', 0)} days\n"

        report += "\n"

    if achievements:
        report += "## Achievements\n\n"
        for achievement in achievements:
            unlocked_date = datetime.fromisoformat(achievement['unlocked_at']).strftime("%B %d, %Y")
            report += f"- **{achievement['achievement_id']}** - Unlocked: {unlocked_date}\n"
        report += "\n"

    report += "## Recent Completions\n\n"
    for c in completions[:20]:
        delay = (c['completed_at'] - c['scheduled_time']).total_seconds() / 60
        report += f"- {c['completed_at'].strftime('%b %d, %I:%M %p')} "
        report += f"({delay:+.0f} min)"
        if c.get('notes'):
            report += f" - *{c['notes']}*"
        report += "\n"

    return report

async def save_export_file(user_id: str, content: str, format: str) -> str:
    """Save export to temporary file"""
    import tempfile
    import os

    file_extension = {"json": "json", "csv": "csv", "markdown": "md"}[format]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    file_path = os.path.join(
        tempfile.gettempdir(),
        f"health_agent_export_{user_id}_{timestamp}.{file_extension}"
    )

    with open(file_path, 'w') as f:
        f.write(content)

    return file_path
```

**3.3 Export Handler**

```python
# src/handlers/export.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.utils.data_export import format_export_data, save_export_file
from src.db.queries import (
    get_user_reminders,
    get_all_user_completions,
    get_all_user_skips,
    get_user_achievements
)

async def handle_export_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show export options"""

    keyboard = [
        [
            InlineKeyboardButton("📊 JSON", callback_data="export:json"),
            InlineKeyboardButton("📈 CSV", callback_data="export:csv")
        ],
        [InlineKeyboardButton("📝 Markdown Report", callback_data="export:markdown")],
        [InlineKeyboardButton("❌ Cancel", callback_data="export:cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📦 **Export Your Data**\n\nChoose a format:\n\n"
        "• **JSON** - Complete data, machine-readable\n"
        "• **CSV** - Spreadsheet-friendly\n"
        "• **Markdown** - Human-readable report",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_export_format_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle export format selection"""
    query = update.callback_query
    await query.answer()

    _, format_type = query.data.split(":")

    if format_type == "cancel":
        await query.edit_message_text("Export cancelled.")
        return

    await query.edit_message_text(f"🔄 Preparing your {format_type.upper()} export...")

    user_id = str(update.effective_user.id)

    try:
        # Gather data
        reminders = await get_user_reminders(user_id)
        completions = await get_all_user_completions(user_id, days=90)
        skips = await get_all_user_skips(user_id, days=90)
        achievements = await get_user_achievements(user_id)

        # Format export
        content = await format_export_data(
            format=format_type,
            reminders=reminders,
            completions=completions,
            skips=skips,
            achievements=achievements
        )

        # Save to file
        file_path = await save_export_file(user_id, content, format_type)

        # Send file
        with open(file_path, 'rb') as f:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=f,
                filename=os.path.basename(file_path),
                caption=f"✅ Your health data export ({len(completions)} records)"
            )

        # Clean up temp file
        os.remove(file_path)

        await query.message.reply_text(
            "✅ Export complete!\n\nYour data has been sent as a file above."
        )

    except Exception as e:
        await query.message.reply_text(f"❌ Export failed: {str(e)}")
```

---

### 👤 Component 4: Avatar & Profile Customization

**Priority**: LOW (nice-to-have)
**Effort**: 4-6 hours
**Files to Create/Modify**:
- `migrations/009_user_profiles.sql` - Profile table
- `src/models/user.py` - Extended user model
- `src/handlers/profile.py` - Profile management

#### Implementation Steps

**4.1 Database Schema**

```sql
-- migrations/009_user_profiles.sql

ALTER TABLE users
ADD COLUMN IF NOT EXISTS display_name VARCHAR(100),
ADD COLUMN IF NOT EXISTS avatar_emoji VARCHAR(10) DEFAULT '👤',
ADD COLUMN IF NOT EXISTS profile_color VARCHAR(20) DEFAULT 'blue',
ADD COLUMN IF NOT EXISTS show_badges BOOLEAN DEFAULT true,
ADD COLUMN IF NOT EXISTS motivation_style VARCHAR(50) DEFAULT 'balanced',  -- 'competitive', 'supportive', 'minimal', 'balanced'
ADD COLUMN IF NOT EXISTS profile_customized_at TIMESTAMP;

COMMENT ON COLUMN users.avatar_emoji IS 'User selected emoji for avatar (e.g., 💪, 🏃, 🧘)';
COMMENT ON COLUMN users.motivation_style IS 'Preferred motivation messaging style';
```

**4.2 Profile Customization Handler**

```python
# src/handlers/profile.py

AVATAR_EMOJI_OPTIONS = [
    "💪", "🏃", "🧘", "🚴", "🏋️", "🤸",
    "❤️", "🔥", "⚡", "🌟", "✨", "🎯",
    "🦸", "🧠", "💚", "🌈", "🎨", "📚"
]

async def handle_profile_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show profile customization menu"""

    keyboard = [
        [InlineKeyboardButton("👤 Change Avatar", callback_data="profile:avatar")],
        [InlineKeyboardButton("💬 Motivation Style", callback_data="profile:motivation")],
        [InlineKeyboardButton("🏆 Badge Display", callback_data="profile:badges")],
        [InlineKeyboardButton("✅ Done", callback_data="profile:done")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    user_profile = await get_user_profile(str(update.effective_user.id))

    await update.message.reply_text(
        f"⚙️ **Profile Settings**\n\n"
        f"Avatar: {user_profile.get('avatar_emoji', '👤')}\n"
        f"Motivation Style: {user_profile.get('motivation_style', 'balanced').title()}\n"
        f"Badges: {'Visible' if user_profile.get('show_badges', True) else 'Hidden'}\n\n"
        f"What would you like to customize?",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_avatar_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show avatar emoji picker"""
    query = update.callback_query
    await query.answer()

    # Create grid of emoji options
    keyboard = []
    row = []
    for i, emoji in enumerate(AVATAR_EMOJI_OPTIONS):
        row.append(InlineKeyboardButton(emoji, callback_data=f"avatar_set:{emoji}"))
        if (i + 1) % 6 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="profile:back")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "👤 **Choose Your Avatar**\n\nSelect an emoji that represents you:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_set_avatar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set user's avatar emoji"""
    query = update.callback_query
    await query.answer()

    _, emoji = query.data.split(":")
    user_id = str(update.effective_user.id)

    await update_user_profile(user_id, avatar_emoji=emoji)

    await query.edit_message_text(
        f"✅ Avatar updated to {emoji}!\n\nThis will appear in your stats and achievements."
    )
```

---

### 🎨 Component 5: UI Enhancements

**Priority**: MEDIUM
**Effort**: 3-4 hours
**Files to Modify**:
- `src/utils/reminder_formatters.py` - Enhanced formatting

#### Implementation Steps

**5.1 Progress Bars**

```python
# src/utils/reminder_formatters.py

def create_progress_bar(percentage: float, width: int = 10, filled: str = "█", empty: str = "░") -> str:
    """Create text-based progress bar"""
    filled_count = int(percentage * width)
    empty_count = width - filled_count
    return filled * filled_count + empty * empty_count

def format_percentage_with_bar(value: float, label: str = "") -> str:
    """Format percentage with visual bar"""
    bar = create_progress_bar(value)
    percentage_str = f"{value*100:.0f}%"
    return f"{label}{bar} {percentage_str}"

# Usage in statistics
def format_completion_rate(rate: float) -> str:
    """Format completion rate with visual bar"""
    emoji = "🔥" if rate >= 0.8 else "✅" if rate >= 0.6 else "📈"
    bar = create_progress_bar(rate)
    return f"{emoji} {bar} {rate*100:.0f}%"
```

**5.2 Enhanced Statistics Display**

```python
# Update format_reminder_statistics to use progress bars

async def format_reminder_statistics(stats: dict, reminder: dict) -> str:
    """Enhanced statistics with visual elements"""

    message = f"📊 **{reminder['message']}**\n\n"

    # Overview with progress bar
    message += "**📈 OVERVIEW**\n"
    completion_rate = stats.get('completion_rate', 0)
    message += format_completion_rate(completion_rate) + "\n"
    message += f"✅ Completed: {stats['completed_days']}/{stats['total_days']} days\n"

    # Streaks with visual emphasis
    current_streak = stats.get('current_streak', 0)
    best_streak = stats.get('best_streak', 0)

    if current_streak > 0:
        fire_emoji = "🔥" * min(current_streak // 3, 5)  # Scale fire emoji
        message += f"\n{fire_emoji} **Current Streak**: {current_streak} days\n"

    if best_streak > current_streak:
        message += f"🏆 Best Streak: {best_streak} days\n"

    # Timing with clock emojis
    avg_delay = stats.get('average_delay_minutes', 0)
    if avg_delay != 0:
        message += f"\n**⏰ TIMING**\n"
        delay_str = f"{abs(avg_delay):.0f} min {'early' if avg_delay < 0 else 'late'}"
        emoji = "⚡" if avg_delay < 0 else "🕐" if avg_delay > 30 else "✅"
        message += f"{emoji} Average: {delay_str}\n"

    # Day of week with color coding
    if stats.get('day_of_week_breakdown'):
        message += "\n**📅 BY DAY OF WEEK**\n"
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        for day, data in stats['day_of_week_breakdown'].items():
            rate = data.get('completion_rate', 0)
            emoji = "🟢" if rate >= 0.8 else "🟡" if rate >= 0.5 else "🔴"
            bar = create_progress_bar(rate, width=5)
            message += f"{emoji} {days[day]}: {bar} {rate*100:.0f}%\n"

    return message
```

---

### 🧪 Component 6: Testing & Validation

**Priority**: HIGH
**Effort**: 3-4 hours
**Files to Create**:
- `tests/unit/test_achievements.py`
- `tests/unit/test_export.py`
- `tests/integration/test_phase5_flow.py`

#### Test Coverage

**6.1 Achievement Tests**

```python
# tests/unit/test_achievements.py

import pytest
from src.utils.achievement_checker import check_achievement_criteria
from src.models.achievement import Achievement, AchievementTier, AchievementCategory

@pytest.mark.asyncio
async def test_first_completion_achievement(db_connection, sample_user):
    """Test 'First Steps' achievement unlocks on first completion"""

    achievement = Achievement(
        id="first_steps",
        name="First Steps",
        description="First completion",
        icon="👣",
        category=AchievementCategory.MILESTONES,
        criteria={"type": "total_completions", "value": 1},
        tier=AchievementTier.BRONZE
    )

    # Before any completions
    result = await check_achievement_criteria(sample_user.telegram_id, achievement)
    assert result == False

    # After first completion
    await save_reminder_completion(sample_user.telegram_id, sample_reminder.id, datetime.now())

    result = await check_achievement_criteria(sample_user.telegram_id, achievement)
    assert result == True

@pytest.mark.asyncio
async def test_streak_achievement(db_connection, sample_user, sample_reminder):
    """Test streak-based achievement"""

    achievement = Achievement(
        id="week_warrior",
        name="Week Warrior",
        description="7-day streak",
        icon="🔥",
        category=AchievementCategory.CONSISTENCY,
        criteria={"type": "streak", "value": 7},
        tier=AchievementTier.SILVER
    )

    # Create 7-day streak
    for i in range(7):
        completion_date = datetime.now() - timedelta(days=6-i)
        await save_reminder_completion(
            sample_user.telegram_id,
            sample_reminder.id,
            completion_date
        )

    result = await check_achievement_criteria(
        sample_user.telegram_id,
        achievement,
        reminder_id=sample_reminder.id
    )
    assert result == True
```

**6.2 Export Tests**

```python
# tests/unit/test_export.py

import pytest
import json
from src.utils.data_export import format_json_export, format_csv_export

def test_json_export_format(sample_completions, sample_reminders):
    """Test JSON export formatting"""

    result = format_json_export(
        reminders=sample_reminders,
        completions=sample_completions,
        skips=[],
        achievements=None,
        statistics=None
    )

    data = json.loads(result)

    assert 'export_date' in data
    assert 'reminders' in data
    assert 'completions' in data
    assert len(data['completions']) == len(sample_completions)

def test_csv_export_format(sample_completions):
    """Test CSV export formatting"""

    result = format_csv_export(completions=sample_completions, skips=[])

    lines = result.strip().split('\n')
    assert len(lines) == len(sample_completions) + 1  # +1 for header
    assert 'Type,Reminder ID,Scheduled Time' in lines[0]
```

**6.3 Integration Tests**

```python
# tests/integration/test_phase5_flow.py

@pytest.mark.asyncio
async def test_complete_note_flow(bot, user, reminder):
    """Test completion with note entry flow"""

    # 1. Complete reminder
    update = create_callback_query_update(user, f"complete:{reminder.id}:2024-01-01T08:00:00")
    await handle_reminder_completion(update, context)

    # Should offer note button
    assert "Add Note" in update.callback_query.message.text

    # 2. Click Add Note
    update = create_callback_query_update(user, f"add_note:{completion_id}")
    await handle_add_note_button(update, context)

    # Should show templates
    assert "Quick templates" in update.callback_query.message.text

    # 3. Select template
    update = create_callback_query_update(user, f"note_template:No issues")
    await handle_note_template(update, context)

    # Verify note saved
    completion = await get_completion_by_id(completion_id)
    assert completion['notes'] == "No issues"

@pytest.mark.asyncio
async def test_achievement_unlock_notification(bot, user, reminder):
    """Test achievement unlock shows notification"""

    # Complete first reminder to trigger 'First Steps' achievement
    update = create_callback_query_update(user, f"complete:{reminder.id}:2024-01-01T08:00:00")
    await handle_reminder_completion(update, context)

    # Check for achievement message
    sent_messages = context.bot.send_message.call_args_list
    achievement_msg = next(m for m in sent_messages if "ACHIEVEMENT UNLOCKED" in m[1]['text'])
    assert "First Steps" in achievement_msg[1]['text']
```

---

## Database Migrations Summary

**New Migrations to Create:**

1. **008_achievements_system.sql**
   - `achievements` table (achievement definitions)
   - `user_achievements` table (unlocked badges)

2. **009_user_profiles.sql**
   - Extend `users` table with:
     - `avatar_emoji`
     - `display_name`
     - `motivation_style`
     - `show_badges`

---

## Implementation Timeline

### Week 10

**Days 1-2: Completion Notes**
- [ ] Add note entry UI to completion flow
- [ ] Create note templates system
- [ ] Update statistics to display notes
- [ ] Test note flow end-to-end

**Days 3-5: Achievement System**
- [ ] Create database migrations (008)
- [ ] Define achievement criteria
- [ ] Implement unlock detection
- [ ] Add achievement notifications
- [ ] Create achievement display UI
- [ ] Test achievement unlocking

### Week 11

**Days 1-2: Data Export**
- [ ] Create export agent tool
- [ ] Implement JSON/CSV/Markdown formatters
- [ ] Add export handlers
- [ ] Test export functionality

**Days 3-4: Profile & UI**
- [ ] Create profile customization (migration 009)
- [ ] Add avatar selection UI
- [ ] Enhance formatters with progress bars
- [ ] Polish visual presentation

**Day 5: Testing & Documentation**
- [ ] Write unit tests for new features
- [ ] Integration tests for workflows
- [ ] Update documentation
- [ ] User acceptance testing
- [ ] Performance optimization

---

## Success Metrics (Phase 5)

### Engagement Metrics
- **Note Usage**: >40% of completions include a note within 4 weeks
- **Achievement Views**: Users check achievements 2+ times per week
- **Export Usage**: 20% of users export data at least once
- **Profile Customization**: 50% of users customize their avatar

### Quality Metrics
- **Test Coverage**: >85% for new Phase 5 code
- **Performance**: Export completes in <5 seconds for 90 days of data
- **Error Rate**: <1% failure rate on new features

### User Satisfaction
- **Feature Usefulness**: 7/10+ rating on note templates
- **Achievement Motivation**: 60% report achievements increase motivation
- **Export Satisfaction**: 8/10+ on data export experience

---

## Risks & Mitigation

### Technical Risks

**Risk**: Achievement detection becomes slow with many users
**Mitigation**: Cache unlock checks, run detection asynchronously, batch process

**Risk**: Export file size too large for Telegram
**Mitigation**: Limit to 90 days, compress files, offer external link option

**Risk**: Note entry interrupts flow
**Mitigation**: Make notes fully optional, allow quick skip, use templates for speed

### UX Risks

**Risk**: Too many achievement notifications feel spammy
**Mitigation**: Batch achievements, allow notification preferences, limit to important milestones

**Risk**: Profile customization adds complexity
**Mitigation**: Keep settings minimal, use smart defaults, make fully optional

---

## Future Enhancements (Post-Phase 5)

After Phase 5 completion, consider:

1. **Social Features**
   - Share achievements with friends
   - Group challenges
   - Accountability partners

2. **Advanced Analytics**
   - Correlation analysis (sleep vs completion rate)
   - Predictive modeling (likelihood to miss)
   - Personalized insights

3. **Integration**
   - Apple Health / Google Fit export
   - Calendar integration
   - Wearable device sync

4. **Gamification 2.0**
   - XP and leveling system
   - Challenge library
   - Leaderboards (opt-in)
   - Reward shop (virtual items)

---

## Definition of Done

Phase 5 is complete when:

- [x] All 6 components implemented and tested
- [x] Database migrations deployed
- [x] Unit test coverage >85%
- [x] Integration tests passing
- [x] User documentation updated
- [x] Code reviewed and approved
- [x] Deployed to production
- [x] Success metrics tracking enabled
- [x] User feedback collected
- [x] Known issues documented

---

## Conclusion

Phase 5 completes the gamification vision by adding the polish and user-facing features that make the system delightful to use. By focusing on:

1. **Contextual notes** for richer data
2. **Achievements** for motivation
3. **Data export** for ownership
4. **Customization** for personalization
5. **Visual polish** for engagement
6. **Comprehensive testing** for quality

We deliver a production-ready, user-loved health motivation platform.

**Estimated Completion**: End of Week 11 (2 weeks from start)
**Total Effort**: 19-27 hours
**Risk Level**: Low (building on solid Phase 1-4 foundation)

Let's ship this! 🚀

---

**Document Version**: 1.0
**Created**: December 20, 2024
**Owner**: Development Team
**Status**: Ready for Implementation
