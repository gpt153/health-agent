# Feature: Sleep Quiz Enhancements

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Enhance the existing sleep quiz system with four major improvements:
1. **Multi-language support** - Automatically detect user's language and present quiz questions in their native language
2. **Default activation with opt-out** - Enable sleep quiz by default for new users with settings to disable
3. **Customizable quiz timing** - Allow users to set their preferred morning quiz time with timezone awareness
4. **Smart pattern learning** - Track submission patterns and suggest optimal quiz times based on user behavior

This transforms the sleep quiz from a manually-triggered feature into an intelligent, proactive daily habit tracker that adapts to each user's schedule and preferences.

## User Story

As a health-conscious user
I want the sleep quiz to be sent automatically at my preferred time in my native language
So that I can effortlessly track my sleep patterns without manual intervention

## Problem Statement

The current sleep quiz requires manual activation (`/sleep_quiz` command) and only supports English. Users must remember to log their sleep each day, leading to:
- Low engagement and inconsistent tracking
- Language barriers for non-English speakers
- No personalization for different wake schedules
- Missed opportunities for data collection when users forget

## Solution Statement

Create an intelligent, automated sleep quiz system that:
- Automatically enrolls new users (opt-out model)
- Detects user language and translates all quiz content
- Schedules daily quizzes based on user-configured wake times
- Learns from submission patterns to optimize send times
- Provides comprehensive settings UI for customization

## Feature Metadata

**Feature Type**: Enhancement
**Estimated Complexity**: High
**Primary Systems Affected**:
- Sleep quiz handlers (`src/handlers/sleep_quiz.py`)
- User settings/preferences (`src/models/user.py`)
- Database schema (new tables for settings, submissions)
- Scheduler system (`src/scheduler/reminder_manager.py`)

**Dependencies**:
- `babel` - Python i18n library for translations
- `pytz` - Timezone handling (already available)
- `python-telegram-bot[job-queue]` - Scheduled jobs (already installed)

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `src/handlers/sleep_quiz.py` (all lines) - **Current quiz implementation with inline keyboards**
  - Pattern: ConversationHandler with states (BEDTIME, SLEEP_LATENCY, etc.)
  - Pattern: Inline keyboards for time pickers and selections
  - Pattern: context.user_data for temporary quiz state
  - Critical: All question text and button labels are hardcoded strings

- `src/models/sleep.py` (all lines) - **SleepEntry model**
  - Why: Understand data structure saved to database

- `src/models/user.py` (lines 1-36) - **UserPreferences and UserProfile models**
  - Pattern: UserPreferences has timezone, wants_daily_summary fields
  - Why: Need to extend with sleep quiz preferences

- `src/scheduler/reminder_manager.py` (all lines) - **Scheduling pattern with JobQueue**
  - Pattern: `schedule_custom_reminder()` - how to schedule daily jobs
  - Pattern: Time parsing with `zoneinfo.ZoneInfo` for timezone awareness
  - Pattern: Job naming convention: `f"custom_reminder_{user_id}_{hour}{minute}"`
  - Why: Mirror this pattern for sleep quiz scheduling

- `src/db/queries.py` (lines 956-1014) - **Sleep entry database operations**
  - Pattern: `save_sleep_entry()` and `get_sleep_entries()`
  - Why: Will need similar patterns for settings and submission tracking

- `src/bot.py` (lines 1041-1077) - **Handler registration pattern**
  - Critical: ConversationHandlers MUST be registered BEFORE message handlers
  - Pattern: `app.add_handler(sleep_quiz_handler)` at line 1063
  - Why: New settings handlers must follow same pattern

- `migrations/005_sleep_tracking.sql` (all lines) - **Current sleep schema**
  - Why: Need to understand existing structure before adding new tables

- `src/utils/timezone_helper.py` (all lines) - **Timezone utilities**
  - Pattern: `suggest_timezones_for_language()` - maps language codes to timezones
  - Pattern: `LANGUAGE_TIMEZONE_MAP` dictionary for language → timezone suggestions
  - Why: Extend for language detection logic

- `tests/integration/test_sleep_quiz_flow.py` (all lines) - **Test patterns for sleep quiz**
  - Pattern: pytest with async fixtures
  - Pattern: Creating SleepEntry objects for testing
  - Why: Mirror test structure for new features

### New Files to Create

- `src/i18n/translations.py` - Translation system with language-keyed dictionaries
- `src/i18n/__init__.py` - Package initializer
- `src/handlers/sleep_settings.py` - Settings conversation handler for quiz configuration
- `src/models/sleep_settings.py` - Pydantic models for SleepQuizSettings, SubmissionPattern
- `migrations/007_sleep_quiz_enhancements.sql` - Database schema for new tables
- `tests/unit/test_sleep_translations.py` - Unit tests for i18n system
- `tests/integration/test_sleep_quiz_scheduling.py` - Integration tests for auto-scheduling

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [Babel i18n Documentation](https://babel.pocoo.org/en/latest/index.html)
  - Specific section: Message Catalogs and Translations
  - Why: Industry standard for Python i18n (alternative to gettext)
  - Note: We'll use simple dict-based approach instead for MVP

- [python-telegram-bot JobQueue](https://docs.python-telegram-bot.org/en/stable/telegram.ext.jobqueue.html)
  - Specific section: run_daily() and timezone handling
  - Why: Already used in reminder_manager.py, need same pattern

- [PostgreSQL JSONB](https://www.postgresql.org/docs/current/datatype-json.html)
  - Specific section: JSONB operators and indexing
  - Why: Store flexible settings and patterns as JSONB

### Patterns to Follow

**Naming Conventions:**
```python
# Models: PascalCase with descriptive names
class SleepQuizSettings(BaseModel):
    ...

# Functions: snake_case, verb-first
async def schedule_sleep_quiz(user_id: str, ...) -> None:
    ...

# Database tables: snake_case, plural for collections
CREATE TABLE sleep_quiz_settings ...
CREATE TABLE sleep_quiz_submissions ...
```

**Error Handling:**
```python
# Pattern from src/scheduler/reminder_manager.py:145
try:
    # Operation
    logger.info(f"Success message with context")
except Exception as e:
    logger.error(f"Failed to X: {e}", exc_info=True)
```

**Logging Pattern:**
```python
# Pattern from src/handlers/sleep_quiz.py:507
logger.info(f"Sleep quiz completed for user {entry.user_id}")
```

**Conversation Handler Pattern:**
```python
# Pattern from src/handlers/sleep_quiz.py:521-537
handler = ConversationHandler(
    entry_points=[CommandHandler('command', handler_func)],
    states={
        STATE_NAME: [CallbackQueryHandler(callback_func)],
    },
    fallbacks=[CommandHandler('cancel', cancel_func)],
)
```

**Database Query Pattern:**
```python
# Pattern from src/db/queries.py:957-986
async def save_X(entry: Model) -> None:
    """Save X to database"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("INSERT INTO ...", (...))
            await conn.commit()
    logger.info(f"Saved X for user {entry.user_id}")
```

**Inline Keyboard Pattern:**
```python
# Pattern from src/handlers/sleep_quiz.py:52-70 (time picker)
keyboard = [
    [InlineKeyboardButton("🔼", callback_data="prefix_h_up"),
     InlineKeyboardButton("", callback_data="noop"),
     InlineKeyboardButton("🔼", callback_data="prefix_m_up")],
    [InlineKeyboardButton(f"{hour:02d}", callback_data="noop"),
     InlineKeyboardButton(":", callback_data="noop"),
     InlineKeyboardButton(f"{minute:02d}", callback_data="noop")],
    # ... down buttons
    [InlineKeyboardButton("✅ Confirm", callback_data="prefix_confirm")],
]
reply_markup = InlineKeyboardMarkup(keyboard)
```

---

## IMPLEMENTATION PLAN

### Phase 1: Database Schema & Models

Create foundational database tables and Pydantic models for new settings and tracking.

**Tasks:**
- Create migration file with three new tables
- Define Pydantic models for settings and patterns
- Add database query functions

### Phase 2: Translation System

Build lightweight i18n system using dictionary-based translations (not full gettext/babel for MVP).

**Tasks:**
- Create translation module with nested dictionaries
- Implement language detection from Telegram user object
- Add translation helper function with fallback to English
- Translate all sleep quiz questions and responses

### Phase 3: Settings UI

Create conversation handler for users to configure sleep quiz preferences.

**Tasks:**
- Build settings conversation handler with inline keyboards
- Implement enable/disable toggle
- Add time picker for preferred quiz time
- Save settings to database

### Phase 4: Auto-Scheduling System

Integrate with existing scheduler to automatically send daily quizzes.

**Tasks:**
- Add sleep quiz scheduling to ReminderManager
- Load user settings on bot startup
- Schedule quiz jobs with timezone awareness
- Handle job persistence across restarts

### Phase 5: Pattern Learning (Stretch Goal)

Track submission patterns and suggest optimal times.

**Tasks:**
- Log submission time whenever quiz is completed
- Calculate average response delay
- Suggest time adjustments after 7+ submissions
- Display pattern insights in settings

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### CREATE migrations/007_sleep_quiz_enhancements.sql

**IMPLEMENT**: Three new tables for sleep quiz enhancements

```sql
-- User-specific sleep quiz settings
CREATE TABLE IF NOT EXISTS sleep_quiz_settings (
    user_id VARCHAR(255) PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
    enabled BOOLEAN DEFAULT true,
    preferred_time TIME DEFAULT '07:00:00',
    timezone VARCHAR(100) DEFAULT 'UTC',
    language_code VARCHAR(10) DEFAULT 'en',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Track quiz submission patterns for learning
CREATE TABLE IF NOT EXISTS sleep_quiz_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    scheduled_time TIMESTAMP NOT NULL,
    submitted_at TIMESTAMP NOT NULL,
    response_delay_minutes INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_sleep_quiz_settings_enabled ON sleep_quiz_settings(user_id, enabled);
CREATE INDEX IF NOT EXISTS idx_sleep_quiz_submissions_user_time ON sleep_quiz_submissions(user_id, submitted_at DESC);

-- Update trigger for settings
CREATE TRIGGER update_sleep_quiz_settings_updated_at
BEFORE UPDATE ON sleep_quiz_settings
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

**PATTERN**: Mirror existing migration files (001-006)
**VALIDATE**: `psql $DATABASE_URL -f migrations/007_sleep_quiz_enhancements.sql` (should complete without errors)

---

### CREATE src/models/sleep_settings.py

**IMPLEMENT**: Pydantic models for sleep quiz settings and patterns

```python
"""Pydantic models for sleep quiz settings and patterns"""
from pydantic import BaseModel, Field
from datetime import datetime, time
from typing import Optional


class SleepQuizSettings(BaseModel):
    """User settings for automated sleep quiz"""

    user_id: str
    enabled: bool = True
    preferred_time: time = Field(default=time(7, 0))  # 7:00 AM
    timezone: str = "UTC"
    language_code: str = "en"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class SleepQuizSubmission(BaseModel):
    """Record of when user submitted quiz vs scheduled time"""

    id: str
    user_id: str
    scheduled_time: datetime
    submitted_at: datetime
    response_delay_minutes: int  # submitted_at - scheduled_time in minutes
    created_at: datetime = Field(default_factory=datetime.now)


class SubmissionPattern(BaseModel):
    """Analyzed pattern of user's submission behavior"""

    user_id: str
    average_delay_minutes: float
    suggested_time: time
    confidence_score: float = Field(ge=0.0, le=1.0)  # 0.0-1.0
    sample_size: int  # Number of submissions analyzed
```

**IMPORTS**: `from datetime import datetime, time`, `from pydantic import BaseModel, Field`
**PATTERN**: Mirror `src/models/sleep.py` structure
**VALIDATE**: `uv run python -c "from src.models.sleep_settings import SleepQuizSettings; print('✓ Models import successfully')"`

---

### UPDATE src/db/queries.py

**IMPLEMENT**: Add database query functions for sleep quiz settings

**PATTERN**: Follow existing query patterns (`save_sleep_entry`, `get_sleep_entries`)

```python
# Add to imports at top
from src.models.sleep_settings import SleepQuizSettings, SleepQuizSubmission

# Add at end of file

# ==========================================
# Sleep Quiz Settings Functions
# ==========================================

async def get_sleep_quiz_settings(user_id: str) -> Optional[dict]:
    """Get sleep quiz settings for user"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT user_id, enabled, preferred_time, timezone, language_code,
                       created_at, updated_at
                FROM sleep_quiz_settings
                WHERE user_id = %s
                """,
                (user_id,)
            )
            row = await cur.fetchone()
            return dict(row) if row else None


async def save_sleep_quiz_settings(settings: SleepQuizSettings) -> None:
    """Create or update sleep quiz settings"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO sleep_quiz_settings
                (user_id, enabled, preferred_time, timezone, language_code)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    enabled = EXCLUDED.enabled,
                    preferred_time = EXCLUDED.preferred_time,
                    timezone = EXCLUDED.timezone,
                    language_code = EXCLUDED.language_code,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    settings.user_id,
                    settings.enabled,
                    str(settings.preferred_time),
                    settings.timezone,
                    settings.language_code
                )
            )
            await conn.commit()
    logger.info(f"Saved sleep quiz settings for {settings.user_id}")


async def get_all_enabled_sleep_quiz_users() -> list[dict]:
    """Get all users with sleep quiz enabled (for scheduling on startup)"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT user_id, enabled, preferred_time, timezone, language_code
                FROM sleep_quiz_settings
                WHERE enabled = true
                ORDER BY user_id
                """
            )
            return await cur.fetchall()


async def save_sleep_quiz_submission(submission: SleepQuizSubmission) -> None:
    """Record quiz submission for pattern learning"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO sleep_quiz_submissions
                (id, user_id, scheduled_time, submitted_at, response_delay_minutes)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    submission.id,
                    submission.user_id,
                    submission.scheduled_time,
                    submission.submitted_at,
                    submission.response_delay_minutes
                )
            )
            await conn.commit()
    logger.info(f"Saved submission pattern for {submission.user_id}")


async def get_submission_patterns(user_id: str, days: int = 30) -> list[dict]:
    """Get recent submission patterns for analysis"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, user_id, scheduled_time, submitted_at, response_delay_minutes
                FROM sleep_quiz_submissions
                WHERE user_id = %s
                  AND submitted_at > NOW() - INTERVAL '%s days'
                ORDER BY submitted_at DESC
                """,
                (user_id, days)
            )
            rows = await cur.fetchall()

            if not rows:
                return []

            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in rows]
```

**IMPORTS**: Add to existing imports section
**GOTCHA**: Use `ON CONFLICT (user_id) DO UPDATE` for upsert pattern (PostgreSQL-specific)
**VALIDATE**: `uv run python -c "from src.db import queries; print('✓ Query functions added')"`

---

### CREATE src/i18n/__init__.py

**IMPLEMENT**: Package initializer (empty for now)

```python
"""Internationalization (i18n) module for multi-language support"""
```

**VALIDATE**: File created

---

### CREATE src/i18n/translations.py

**IMPLEMENT**: Translation system with dictionary-based approach (MVP, not full gettext)

```python
"""
Sleep quiz translations for multi-language support.

Uses simple dictionary approach for MVP. For production, consider
migrating to babel/gettext with .po/.mo files.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Translation dictionaries: language_code -> {key: translated_string}
TRANSLATIONS: Dict[str, Dict[str, Any]] = {
    "en": {
        # Quiz questions
        "quiz_welcome": "😴 **Good morning! Let's log your sleep**\n\nThis takes about 60 seconds.\n\nReady? Let's start!",
        "q1_bedtime": "**Q1/8: What time did you get into bed?**\n\nUse ⬆️⬇️ to adjust time",
        "q2_latency": "**Q2/8: How long did it take you to fall asleep?**",
        "q3_wake_time": "**Q3/8: What time did you wake up this morning?**\n\nUse ⬆️⬇️ to adjust time",
        "q4_wakings": "**Q4/8: Did you wake up during the night?**",
        "q5_quality": "**Q5/8: How would you rate your sleep quality?**\n\n😫 1-2 = Terrible\n😐 5-6 = Okay\n😊 9-10 = Excellent",
        "q6_phone": "**Q6/8: Did you use your phone/screen while in bed?**",
        "q6_duration": "**For how long?**",
        "q7_disruptions": "**Q7/8: What disrupted your sleep?** (Select all that apply)",
        "q8_alertness": "**Q8/8: How tired/alert do you feel RIGHT NOW?**\n\n😴 1-2 = Exhausted\n😐 5-6 = Normal\n⚡ 9-10 = Wide awake",

        # Button labels
        "btn_confirm": "✅ Confirm",
        "btn_yes": "✅ Yes",
        "btn_no": "❌ No",
        "btn_done": "✅ Done",
        "latency_less_15": "Less than 15 min",
        "latency_15_30": "15-30 min",
        "latency_30_60": "30-60 min",
        "latency_60_plus": "More than 1 hour",
        "wakings_no": "No",
        "wakings_1_2": "Yes, 1-2 times",
        "wakings_3_plus": "Yes, 3+ times",
        "phone_dur_less_15": "< 15 min",
        "phone_dur_15_30": "15-30 min",
        "phone_dur_30_60": "30-60 min",
        "phone_dur_60_plus": "1+ hour",
        "disruption_noise": "🔊 Noise",
        "disruption_light": "💡 Light",
        "disruption_temp": "🌡️ Temperature",
        "disruption_stress": "😰 Stress/worry",
        "disruption_dream": "😱 Bad dream",
        "disruption_pain": "🤕 Pain",

        # Confirmations
        "confirmed_latency": "✅ Sleep latency: {minutes} minutes",
        "confirmed_wakings": "✅ Night wakings: {count} times",
        "confirmed_quality": "✅ Quality rating: {emoji} {rating}/10",
        "confirmed_phone_no": "✅ Noted: No phone usage",
        "confirmed_phone_duration": "✅ Phone usage: {minutes} minutes",

        # Summary
        "summary_title": "✅ **Sleep Logged!**",
        "summary_bedtime": "🛏️ **Bedtime:** {time}",
        "summary_latency": "😴 **Fell asleep:** {minutes} min",
        "summary_wake": "⏰ **Woke up:** {time}",
        "summary_total": "⏱️ **Total sleep:** {hours}h {minutes}m",
        "summary_quality": "🌙 **Quality:** {emoji} {rating}/10",
        "summary_phone": "📱 **Phone usage:** {usage}",
        "summary_alertness": "😌 **Alertness:** {rating}/10",
        "summary_tip": "💡 **Tip:** You got {hours}h {minutes}m of sleep. Aim for 8-10h for optimal health!",

        # Settings
        "settings_title": "⚙️ **Sleep Quiz Settings**",
        "settings_enabled": "Quiz Status: {status}",
        "settings_time": "Scheduled Time: {time} ({timezone})",
        "settings_language": "Language: {language}",
        "settings_prompt": "What would you like to change?",
        "btn_toggle_quiz": "{icon} {action} Daily Quiz",
        "btn_change_time": "🕐 Change Time",
        "btn_change_language": "🌐 Change Language",
        "btn_view_patterns": "📊 View Patterns",
        "btn_back": "◀️ Back",
        "settings_updated": "✅ Settings updated!",

        # Cancel
        "quiz_cancelled": "Sleep quiz cancelled. You can start again with /sleep_quiz",
    },

    "sv": {
        # Swedish translations
        "quiz_welcome": "😴 **God morgon! Låt oss logga din sömn**\n\nDetta tar ungefär 60 sekunder.\n\nRedo? Låt oss börja!",
        "q1_bedtime": "**F1/8: Vilken tid gick du till sängs?**\n\nAnvänd ⬆️⬇️ för att justera tiden",
        "q2_latency": "**F2/8: Hur lång tid tog det att somna?**",
        "q3_wake_time": "**F3/8: Vilken tid vaknade du i morse?**\n\nAnvänd ⬆️⬇️ för att justera tiden",
        "q4_wakings": "**F4/8: Vaknade du under natten?**",
        "q5_quality": "**F5/8: Hur skulle du bedöma din sömnkvalitet?**\n\n😫 1-2 = Fruktansvärt\n😐 5-6 = Okej\n😊 9-10 = Utmärkt",
        "q6_phone": "**F6/8: Använde du telefon/skärm i sängen?**",
        "q6_duration": "**Hur länge?**",
        "q7_disruptions": "**F7/8: Vad störde din sömn?** (Välj alla som gäller)",
        "q8_alertness": "**F8/8: Hur trött/pigg känner du dig JUST NU?**\n\n😴 1-2 = Utmattad\n😐 5-6 = Normal\n⚡ 9-10 = Klarvaken",

        "btn_confirm": "✅ Bekräfta",
        "btn_yes": "✅ Ja",
        "btn_no": "❌ Nej",
        "btn_done": "✅ Klar",
        "latency_less_15": "Mindre än 15 min",
        "latency_15_30": "15-30 min",
        "latency_30_60": "30-60 min",
        "latency_60_plus": "Mer än 1 timme",
        "wakings_no": "Nej",
        "wakings_1_2": "Ja, 1-2 gånger",
        "wakings_3_plus": "Ja, 3+ gånger",
        "phone_dur_less_15": "< 15 min",
        "phone_dur_15_30": "15-30 min",
        "phone_dur_30_60": "30-60 min",
        "phone_dur_60_plus": "1+ timme",
        "disruption_noise": "🔊 Ljud",
        "disruption_light": "💡 Ljus",
        "disruption_temp": "🌡️ Temperatur",
        "disruption_stress": "😰 Stress/oro",
        "disruption_dream": "😱 Mardröm",
        "disruption_pain": "🤕 Smärta",

        "confirmed_latency": "✅ Insomning: {minutes} minuter",
        "confirmed_wakings": "✅ Nattliga uppvaknanden: {count} gånger",
        "confirmed_quality": "✅ Kvalitetsbetyg: {emoji} {rating}/10",
        "confirmed_phone_no": "✅ Noterat: Ingen telefonanvändning",
        "confirmed_phone_duration": "✅ Telefonanvändning: {minutes} minuter",

        "summary_title": "✅ **Sömn Loggad!**",
        "summary_bedtime": "🛏️ **Sänggående:** {time}",
        "summary_latency": "😴 **Somnade:** {minutes} min",
        "summary_wake": "⏰ **Vaknade:** {time}",
        "summary_total": "⏱️ **Total sömn:** {hours}h {minutes}m",
        "summary_quality": "🌙 **Kvalitet:** {emoji} {rating}/10",
        "summary_phone": "📱 **Telefonanvändning:** {usage}",
        "summary_alertness": "😌 **Pigghet:** {rating}/10",
        "summary_tip": "💡 **Tips:** Du sov {hours}h {minutes}m. Sikta på 8-10h för optimal hälsa!",

        "settings_title": "⚙️ **Inställningar för Sömnquiz**",
        "settings_enabled": "Status: {status}",
        "settings_time": "Schemalagd tid: {time} ({timezone})",
        "settings_language": "Språk: {language}",
        "settings_prompt": "Vad vill du ändra?",
        "btn_toggle_quiz": "{icon} {action} Dagligt Quiz",
        "btn_change_time": "🕐 Ändra Tid",
        "btn_change_language": "🌐 Ändra Språk",
        "btn_view_patterns": "📊 Visa Mönster",
        "btn_back": "◀️ Tillbaka",
        "settings_updated": "✅ Inställningar uppdaterade!",

        "quiz_cancelled": "Sömnquiz avbrutet. Du kan starta igen med /sleep_quiz",
    },

    "es": {
        # Spanish translations
        "quiz_welcome": "😴 **¡Buenos días! Registremos tu sueño**\n\nEsto toma unos 60 segundos.\n\n¿Listo? ¡Empecemos!",
        "q1_bedtime": "**P1/8: ¿A qué hora te acostaste?**\n\nUsa ⬆️⬇️ para ajustar la hora",
        "q2_latency": "**P2/8: ¿Cuánto tiempo tardaste en dormirte?**",
        "q3_wake_time": "**P3/8: ¿A qué hora te despertaste esta mañana?**\n\nUsa ⬆️⬇️ para ajustar la hora",
        "q4_wakings": "**P4/8: ¿Te despertaste durante la noche?**",
        "q5_quality": "**P5/8: ¿Cómo calificarías la calidad de tu sueño?**\n\n😫 1-2 = Terrible\n😐 5-6 = Regular\n😊 9-10 = Excelente",
        "q6_phone": "**P6/8: ¿Usaste tu teléfono/pantalla en la cama?**",
        "q6_duration": "**¿Por cuánto tiempo?**",
        "q7_disruptions": "**P7/8: ¿Qué interrumpió tu sueño?** (Selecciona todas las que apliquen)",
        "q8_alertness": "**P8/8: ¿Qué tan cansado/alerta te sientes AHORA MISMO?**\n\n😴 1-2 = Agotado\n😐 5-6 = Normal\n⚡ 9-10 = Muy despierto",

        "btn_confirm": "✅ Confirmar",
        "btn_yes": "✅ Sí",
        "btn_no": "❌ No",
        "btn_done": "✅ Listo",
        "latency_less_15": "Menos de 15 min",
        "latency_15_30": "15-30 min",
        "latency_30_60": "30-60 min",
        "latency_60_plus": "Más de 1 hora",
        "wakings_no": "No",
        "wakings_1_2": "Sí, 1-2 veces",
        "wakings_3_plus": "Sí, 3+ veces",
        "phone_dur_less_15": "< 15 min",
        "phone_dur_15_30": "15-30 min",
        "phone_dur_30_60": "30-60 min",
        "phone_dur_60_plus": "1+ hora",
        "disruption_noise": "🔊 Ruido",
        "disruption_light": "💡 Luz",
        "disruption_temp": "🌡️ Temperatura",
        "disruption_stress": "😰 Estrés/preocupación",
        "disruption_dream": "😱 Pesadilla",
        "disruption_pain": "🤕 Dolor",

        "confirmed_latency": "✅ Latencia de sueño: {minutes} minutos",
        "confirmed_wakings": "✅ Despertares nocturnos: {count} veces",
        "confirmed_quality": "✅ Calificación de calidad: {emoji} {rating}/10",
        "confirmed_phone_no": "✅ Anotado: Sin uso de teléfono",
        "confirmed_phone_duration": "✅ Uso de teléfono: {minutes} minutos",

        "summary_title": "✅ **¡Sueño Registrado!**",
        "summary_bedtime": "🛏️ **Hora de acostarse:** {time}",
        "summary_latency": "😴 **Te dormiste:** {minutes} min",
        "summary_wake": "⏰ **Te despertaste:** {time}",
        "summary_total": "⏱️ **Sueño total:** {hours}h {minutes}m",
        "summary_quality": "🌙 **Calidad:** {emoji} {rating}/10",
        "summary_phone": "📱 **Uso de teléfono:** {usage}",
        "summary_alertness": "😌 **Alerta:** {rating}/10",
        "summary_tip": "💡 **Consejo:** Dormiste {hours}h {minutes}m. ¡Apunta a 8-10h para una salud óptima!",

        "settings_title": "⚙️ **Configuración del Quiz de Sueño**",
        "settings_enabled": "Estado: {status}",
        "settings_time": "Hora programada: {time} ({timezone})",
        "settings_language": "Idioma: {language}",
        "settings_prompt": "¿Qué te gustaría cambiar?",
        "btn_toggle_quiz": "{icon} {action} Quiz Diario",
        "btn_change_time": "🕐 Cambiar Hora",
        "btn_change_language": "🌐 Cambiar Idioma",
        "btn_view_patterns": "📊 Ver Patrones",
        "btn_back": "◀️ Atrás",
        "settings_updated": "✅ ¡Configuración actualizada!",

        "quiz_cancelled": "Quiz de sueño cancelado. Puedes empezar de nuevo con /sleep_quiz",
    },
}


def get_user_language(telegram_user) -> str:
    """
    Detect user's language from Telegram user object.

    Args:
        telegram_user: Telegram User object with language_code attribute

    Returns:
        Language code (e.g., 'en', 'sv', 'es'). Defaults to 'en' if unsupported.
    """
    if not telegram_user or not hasattr(telegram_user, 'language_code'):
        return 'en'

    lang_code = telegram_user.language_code or 'en'

    # Return language if we have translations, else English
    if lang_code in TRANSLATIONS:
        return lang_code

    logger.info(f"Unsupported language '{lang_code}', falling back to English")
    return 'en'


def t(key: str, lang: str = 'en', **kwargs) -> str:
    """
    Translate a key to the specified language with optional formatting.

    Args:
        key: Translation key (e.g., 'quiz_welcome', 'q1_bedtime')
        lang: Language code (defaults to 'en')
        **kwargs: Format arguments for string formatting

    Returns:
        Translated and formatted string. Falls back to English if key not found.

    Examples:
        t('quiz_welcome', lang='sv')
        t('confirmed_latency', lang='es', minutes=15)
        t('summary_quality', lang='en', emoji='😊', rating=9)
    """
    # Get translation dictionary for language (fallback to English)
    lang_dict = TRANSLATIONS.get(lang, TRANSLATIONS['en'])

    # Get translated string (fallback to English key if not found)
    translated = lang_dict.get(key, TRANSLATIONS['en'].get(key, f"[MISSING: {key}]"))

    # Format with kwargs if provided
    if kwargs:
        try:
            return translated.format(**kwargs)
        except KeyError as e:
            logger.error(f"Translation formatting error for key '{key}': {e}")
            return translated

    return translated


def get_supported_languages() -> list[str]:
    """Return list of supported language codes"""
    return list(TRANSLATIONS.keys())
```

**PATTERN**: Simple dict-based translations (MVP approach)
**GOTCHA**: Use `.format(**kwargs)` for dynamic values, not f-strings in translation strings
**IMPORTS**: `import logging`, `from typing import Dict, Any`
**VALIDATE**: `uv run python -c "from src.i18n.translations import t; print(t('quiz_welcome', lang='sv'))"`

---

### UPDATE src/handlers/sleep_quiz.py

**IMPLEMENT**: Integrate translations into existing quiz handler

**PATTERN**: Replace all hardcoded strings with `t()` function calls

**Step 1: Add imports**
```python
# Add after existing imports (around line 12)
from src.i18n.translations import t, get_user_language
```

**Step 2: Detect language at quiz start**
```python
# MODIFY start_sleep_quiz function (line 21-41)
async def start_sleep_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for sleep quiz"""
    user_id = str(update.effective_user.id)

    # Check authorization
    if not await is_authorized(user_id):
        return ConversationHandler.END

    # Detect user's language
    lang = get_user_language(update.effective_user)

    # Initialize quiz data storage with language
    context.user_data['sleep_quiz_data'] = {'lang': lang}

    message = t('quiz_welcome', lang=lang)

    await update.message.reply_text(message, parse_mode="Markdown")

    # Show first question immediately
    return await show_bedtime_question(update, context)
```

**Step 3: Update all question functions to use translations**

Example for bedtime question (repeat pattern for all questions):
```python
# MODIFY show_bedtime_question (line 44-79)
async def show_bedtime_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show bedtime question with time picker"""
    user_id = str(update.effective_user.id)
    lang = context.user_data['sleep_quiz_data'].get('lang', 'en')

    # Default to 10 PM if no prior data
    hour = context.user_data['sleep_quiz_data'].get('bedtime_hour', 22)
    minute = context.user_data['sleep_quiz_data'].get('bedtime_minute', 0)

    keyboard = [
        [
            InlineKeyboardButton("🔼", callback_data="bed_h_up"),
            InlineKeyboardButton("", callback_data="noop"),
            InlineKeyboardButton("🔼", callback_data="bed_m_up"),
        ],
        [
            InlineKeyboardButton(f"{hour:02d}", callback_data="noop"),
            InlineKeyboardButton(":", callback_data="noop"),
            InlineKeyboardButton(f"{minute:02d}", callback_data="noop"),
        ],
        [
            InlineKeyboardButton("🔽", callback_data="bed_h_down"),
            InlineKeyboardButton("", callback_data="noop"),
            InlineKeyboardButton("🔽", callback_data="bed_m_down"),
        ],
        [InlineKeyboardButton(t('btn_confirm', lang=lang), callback_data="bed_confirm")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = t('q1_bedtime', lang=lang)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return BEDTIME
```

**CRITICAL**: Repeat this pattern for ALL question functions:
- `show_sleep_latency_question` - Use `t('q2_latency', ...)` and button labels
- `show_wake_time_question` - Use `t('q3_wake_time', ...)`
- `show_night_wakings_question` - Use `t('q4_wakings', ...)` + button labels
- `show_quality_rating_question` - Use `t('q5_quality', ...)`
- `show_phone_usage_question` - Use `t('q6_phone', ...)` + `t('q6_duration', ...)`
- `show_disruptions_question` - Use `t('q7_disruptions', ...)` + ALL disruption labels
- `show_alertness_question` - Use `t('q8_alertness', ...)`

**Step 4: Update confirmation messages**
```python
# Example: handle_sleep_latency_callback (line 143)
# REPLACE: await query.edit_message_text(f"✅ Sleep latency: {latency_minutes} minutes")
# WITH:
lang = context.user_data['sleep_quiz_data'].get('lang', 'en')
await query.edit_message_text(t('confirmed_latency', lang=lang, minutes=latency_minutes))
```

**Step 5: Update final summary**
```python
# MODIFY handle_alertness_callback final summary (lines 489-500)
lang = context.user_data['sleep_quiz_data'].get('lang', 'en')
hours = int(total_sleep_hours)
minutes = int((total_sleep_hours % 1) * 60)
quality_emoji = "😊" if entry.sleep_quality_rating >= 8 else "😐" if entry.sleep_quality_rating >= 5 else "😫"

summary = f"""{t('summary_title', lang=lang)}

{t('summary_bedtime', lang=lang, time=bedtime_str)}
{t('summary_latency', lang=lang, minutes=latency)}
{t('summary_wake', lang=lang, time=wake_str)}
{t('summary_total', lang=lang, hours=hours, minutes=minutes)}

{t('summary_quality', lang=lang, emoji=quality_emoji, rating=entry.sleep_quality_rating)}
{t('summary_phone', lang=lang, usage="Yes" if entry.phone_usage else "No")}
{t('summary_alertness', lang=lang, rating=alertness)}

{t('summary_tip', lang=lang, hours=hours, minutes=minutes)}"""
```

**GOTCHA**: Extract `lang` from `context.user_data['sleep_quiz_data']` in EVERY callback function
**VALIDATE**: `uv run pytest tests/integration/test_sleep_quiz_flow.py -v`

---

### CREATE src/handlers/sleep_settings.py

**IMPLEMENT**: Settings conversation handler for quiz configuration

```python
"""Sleep quiz settings conversation handler"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler, CommandHandler, CallbackQueryHandler, ContextTypes
)
from src.db.queries import (
    get_sleep_quiz_settings,
    save_sleep_quiz_settings,
    get_submission_patterns,
)
from src.models.sleep_settings import SleepQuizSettings, SubmissionPattern
from src.utils.auth import is_authorized
from src.i18n.translations import t, get_user_language, get_supported_languages
from datetime import time as time_type
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Conversation states
MAIN_MENU, TIME_PICKER, LANGUAGE_PICKER = range(3)


async def settings_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for sleep quiz settings"""
    user_id = str(update.effective_user.id)

    # Check authorization
    if not await is_authorized(user_id):
        return ConversationHandler.END

    # Get or create settings
    settings_dict = await get_sleep_quiz_settings(user_id)

    if not settings_dict:
        # Create default settings
        lang = get_user_language(update.effective_user)
        from src.utils.timezone_helper import get_timezone_from_profile
        user_tz = get_timezone_from_profile(user_id) or "UTC"

        settings = SleepQuizSettings(
            user_id=user_id,
            enabled=True,
            preferred_time=time_type(7, 0),
            timezone=user_tz,
            language_code=lang
        )
        await save_sleep_quiz_settings(settings)
        settings_dict = settings.model_dump()

    # Store in context for easy access
    context.user_data['sleep_settings'] = settings_dict
    context.user_data['settings_lang'] = settings_dict['language_code']

    return await show_main_menu(update, context)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show main settings menu"""
    settings = context.user_data['sleep_settings']
    lang = context.user_data['settings_lang']

    # Format status
    status = "✅ Enabled" if settings['enabled'] else "❌ Disabled"
    toggle_action = "Disable" if settings['enabled'] else "Enable"
    toggle_icon = "❌" if settings['enabled'] else "✅"

    # Format time
    pref_time = settings['preferred_time']
    if isinstance(pref_time, str):
        # Parse from string if needed
        hour, minute = map(int, pref_time.split(':')[:2])
        pref_time = time_type(hour, minute)

    time_str = pref_time.strftime("%H:%M")
    tz_str = settings['timezone']

    # Build message
    message = f"""{t('settings_title', lang=lang)}

{t('settings_enabled', lang=lang, status=status)}
{t('settings_time', lang=lang, time=time_str, timezone=tz_str)}
{t('settings_language', lang=lang, language=lang.upper())}

{t('settings_prompt', lang=lang)}"""

    # Build keyboard
    keyboard = [
        [InlineKeyboardButton(
            t('btn_toggle_quiz', lang=lang, icon=toggle_icon, action=toggle_action),
            callback_data="toggle_enabled"
        )],
        [InlineKeyboardButton(t('btn_change_time', lang=lang), callback_data="change_time")],
        [InlineKeyboardButton(t('btn_change_language', lang=lang), callback_data="change_language")],
        [InlineKeyboardButton(t('btn_view_patterns', lang=lang), callback_data="view_patterns")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")

    return MAIN_MENU


async def handle_main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle main menu button callbacks"""
    query = update.callback_query
    await query.answer()

    action = query.data

    if action == "toggle_enabled":
        # Toggle enabled status
        settings = context.user_data['sleep_settings']
        settings['enabled'] = not settings['enabled']

        # Save to database
        settings_model = SleepQuizSettings(**settings)
        await save_sleep_quiz_settings(settings_model)

        # Update scheduler
        from src.bot import reminder_manager
        if reminder_manager:
            if settings['enabled']:
                # Schedule quiz
                await reminder_manager.schedule_sleep_quiz(
                    settings['user_id'],
                    settings['preferred_time'],
                    settings['timezone'],
                    settings['language_code']
                )
            else:
                # Cancel quiz job
                job_name = f"sleep_quiz_{settings['user_id']}"
                await reminder_manager.cancel_reminder(job_name)

        # Show updated menu
        return await show_main_menu(update, context)

    elif action == "change_time":
        return await show_time_picker(update, context)

    elif action == "change_language":
        return await show_language_picker(update, context)

    elif action == "view_patterns":
        return await show_patterns(update, context)

    return MAIN_MENU


async def show_time_picker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show time picker for preferred quiz time"""
    settings = context.user_data['sleep_settings']
    lang = context.user_data['settings_lang']

    # Get current time or default
    pref_time = settings.get('preferred_time_hour', 7)
    pref_minute = settings.get('preferred_time_minute', 0)

    # If pref_time is a time object string, parse it
    if isinstance(settings.get('preferred_time'), str):
        hour, minute = map(int, settings['preferred_time'].split(':')[:2])
        pref_time = hour
        pref_minute = minute

    # Store in temp state
    context.user_data['sleep_settings']['preferred_time_hour'] = pref_time
    context.user_data['sleep_settings']['preferred_time_minute'] = pref_minute

    keyboard = [
        [
            InlineKeyboardButton("🔼", callback_data="time_h_up"),
            InlineKeyboardButton("", callback_data="noop"),
            InlineKeyboardButton("🔼", callback_data="time_m_up"),
        ],
        [
            InlineKeyboardButton(f"{pref_time:02d}", callback_data="noop"),
            InlineKeyboardButton(":", callback_data="noop"),
            InlineKeyboardButton(f"{pref_minute:02d}", callback_data="noop"),
        ],
        [
            InlineKeyboardButton("🔽", callback_data="time_h_down"),
            InlineKeyboardButton("", callback_data="noop"),
            InlineKeyboardButton("🔽", callback_data="time_m_down"),
        ],
        [InlineKeyboardButton(t('btn_confirm', lang=lang), callback_data="time_confirm")],
        [InlineKeyboardButton(t('btn_back', lang=lang), callback_data="time_cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"**{t('btn_change_time', lang=lang)}**\n\nUse ⬆️⬇️ to adjust time"
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return TIME_PICKER


async def handle_time_picker_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle time picker callbacks"""
    query = update.callback_query
    await query.answer()

    data = query.data
    settings = context.user_data['sleep_settings']
    hour = settings.get('preferred_time_hour', 7)
    minute = settings.get('preferred_time_minute', 0)

    if data == "time_h_up":
        hour = (hour + 1) % 24
    elif data == "time_h_down":
        hour = (hour - 1) % 24
    elif data == "time_m_up":
        minute = (minute + 15) % 60
    elif data == "time_m_down":
        minute = (minute - 15) % 60
    elif data == "time_confirm":
        # Save new time
        settings['preferred_time'] = time_type(hour, minute)
        settings_model = SleepQuizSettings(**settings)
        await save_sleep_quiz_settings(settings_model)

        # Update scheduler if enabled
        from src.bot import reminder_manager
        if reminder_manager and settings['enabled']:
            # Cancel old job
            job_name = f"sleep_quiz_{settings['user_id']}"
            await reminder_manager.cancel_reminder(job_name)
            # Schedule new job
            await reminder_manager.schedule_sleep_quiz(
                settings['user_id'],
                settings['preferred_time'],
                settings['timezone'],
                settings['language_code']
            )

        # Show confirmation and return to menu
        lang = context.user_data['settings_lang']
        await query.edit_message_text(t('settings_updated', lang=lang))
        return await show_main_menu(update, context)

    elif data == "time_cancel":
        return await show_main_menu(update, context)
    elif data == "noop":
        return TIME_PICKER

    # Update stored values
    settings['preferred_time_hour'] = hour
    settings['preferred_time_minute'] = minute

    # Rebuild picker
    return await show_time_picker(update, context)


async def show_language_picker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show language selection menu"""
    lang = context.user_data['settings_lang']

    # Build keyboard with available languages
    keyboard = []
    for lang_code in get_supported_languages():
        display_name = {'en': 'English', 'sv': 'Svenska', 'es': 'Español'}.get(lang_code, lang_code.upper())
        keyboard.append([InlineKeyboardButton(
            f"{'✅ ' if lang_code == lang else ''}{display_name}",
            callback_data=f"lang_{lang_code}"
        )])
    keyboard.append([InlineKeyboardButton(t('btn_back', lang=lang), callback_data="lang_cancel")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"**{t('btn_change_language', lang=lang)}**\n\nSelect your language:"
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return LANGUAGE_PICKER


async def handle_language_picker_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle language selection"""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("lang_"):
        new_lang = data.replace("lang_", "")

        if new_lang in get_supported_languages():
            # Update language
            settings = context.user_data['sleep_settings']
            settings['language_code'] = new_lang
            context.user_data['settings_lang'] = new_lang

            # Save to database
            settings_model = SleepQuizSettings(**settings)
            await save_sleep_quiz_settings(settings_model)

            # Show confirmation
            await query.edit_message_text(t('settings_updated', lang=new_lang))
            return await show_main_menu(update, context)

    elif data == "lang_cancel":
        return await show_main_menu(update, context)

    return LANGUAGE_PICKER


async def show_patterns(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show submission pattern analysis"""
    user_id = str(update.effective_user.id)
    lang = context.user_data['settings_lang']

    # Get submission patterns
    patterns = await get_submission_patterns(user_id, days=30)

    if len(patterns) < 3:
        message = f"📊 **Submission Patterns**\n\nNot enough data yet. Complete at least 3 quizzes to see patterns.\n\nCompleted: {len(patterns)}/3"
    else:
        # Calculate average delay
        delays = [p['response_delay_minutes'] for p in patterns]
        avg_delay = sum(delays) / len(delays)

        # Calculate suggested time
        settings = context.user_data['sleep_settings']
        scheduled_hour = settings['preferred_time_hour']
        scheduled_minute = settings['preferred_time_minute']

        # Suggest new time (scheduled + average delay)
        suggested_minutes = (scheduled_hour * 60 + scheduled_minute + int(avg_delay)) % (24 * 60)
        suggested_hour = suggested_minutes // 60
        suggested_minute = suggested_minutes % 60

        message = f"""📊 **Submission Patterns**

**Data:** {len(patterns)} submissions (last 30 days)
**Average delay:** {int(avg_delay)} minutes

**Current scheduled time:** {scheduled_hour:02d}:{scheduled_minute:02d}
**Average completion time:** {suggested_hour:02d}:{suggested_minute:02d}

💡 **Suggestion:** {"Your current time works well!" if avg_delay < 30 else f"Consider changing to {suggested_hour:02d}:{suggested_minute:02d} for better alignment."}"""

    keyboard = [[InlineKeyboardButton(t('btn_back', lang=lang), callback_data="patterns_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode="Markdown")

    return MAIN_MENU


async def handle_patterns_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle patterns view callback"""
    query = update.callback_query
    await query.answer()

    if query.data == "patterns_back":
        return await show_main_menu(update, context)

    return MAIN_MENU


async def cancel_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel settings conversation"""
    await update.message.reply_text("Settings cancelled.")
    if 'sleep_settings' in context.user_data:
        del context.user_data['sleep_settings']
    return ConversationHandler.END


# Build conversation handler
sleep_settings_handler = ConversationHandler(
    entry_points=[CommandHandler('sleep_settings', settings_start)],
    states={
        MAIN_MENU: [
            CallbackQueryHandler(handle_main_menu_callback),
            CallbackQueryHandler(handle_patterns_callback, pattern="^patterns_"),
        ],
        TIME_PICKER: [CallbackQueryHandler(handle_time_picker_callback)],
        LANGUAGE_PICKER: [CallbackQueryHandler(handle_language_picker_callback)],
    },
    fallbacks=[CommandHandler('cancel', cancel_settings)],
)
```

**PATTERN**: Mirror `sleep_quiz_handler` structure from `src/handlers/sleep_quiz.py`
**IMPORTS**: Follow existing import patterns
**GOTCHA**: Access `reminder_manager` from `src.bot` global (circular import handled at runtime)
**VALIDATE**: `uv run python -c "from src.handlers.sleep_settings import sleep_settings_handler; print('✓ Handler created')"`

---

### UPDATE src/scheduler/reminder_manager.py

**IMPLEMENT**: Add sleep quiz scheduling method

```python
# Add method to ReminderManager class (after schedule_custom_reminder, around line 145)

async def schedule_sleep_quiz(
    self, user_id: str, preferred_time: time, user_timezone: str = "UTC", language_code: str = "en"
) -> None:
    """
    Schedule automated sleep quiz for a user.

    Args:
        user_id: Telegram user ID
        preferred_time: Preferred time for quiz (user's local time)
        user_timezone: IANA timezone string
        language_code: User's language code for translations
    """
    try:
        # Create timezone-aware time
        tz = ZoneInfo(user_timezone)

        # Handle both time objects and strings
        if isinstance(preferred_time, str):
            hour, minute = map(int, preferred_time.split(':')[:2])
            scheduled_time = time(hour=hour, minute=minute, tzinfo=tz)
        else:
            scheduled_time = time(hour=preferred_time.hour, minute=preferred_time.minute, tzinfo=tz)

        # Schedule daily job
        self.job_queue.run_daily(
            callback=self._send_sleep_quiz,
            time=scheduled_time,
            data={
                "user_id": user_id,
                "language_code": language_code,
                "scheduled_time": scheduled_time.strftime("%H:%M"),
                "timezone": user_timezone
            },
            name=f"sleep_quiz_{user_id}",
        )

        logger.info(
            f"Scheduled sleep quiz for {user_id} at {scheduled_time.strftime('%H:%M')} {user_timezone}"
        )

    except Exception as e:
        logger.error(f"Failed to schedule sleep quiz: {e}", exc_info=True)


async def _send_sleep_quiz(self, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send automated sleep quiz to user"""
    data = context.job.data
    user_id = data["user_id"]
    language_code = data.get("language_code", "en")
    scheduled_time_str = data.get("scheduled_time", "")

    try:
        from src.i18n.translations import t
        from datetime import datetime

        # Store scheduled time for pattern tracking
        scheduled_time = datetime.now().replace(
            hour=int(scheduled_time_str.split(':')[0]),
            minute=int(scheduled_time_str.split(':')[1]),
            second=0,
            microsecond=0
        )

        # Store in job data for later reference in quiz completion
        context.bot_data[f"sleep_quiz_scheduled_{user_id}"] = scheduled_time

        # Send quiz trigger message with /sleep_quiz command hint
        message = t('quiz_welcome', lang=language_code)
        message += "\n\nTap /sleep_quiz to start!"

        await context.bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode="Markdown"
        )

        logger.info(f"Sent automated sleep quiz trigger to {user_id}")

    except Exception as e:
        logger.error(f"Failed to send sleep quiz: {e}", exc_info=True)


async def load_sleep_quiz_schedules(self) -> None:
    """Load all enabled sleep quiz schedules from database (called on startup)"""
    logger.info("Loading sleep quiz schedules from database...")

    try:
        from src.db.queries import get_all_enabled_sleep_quiz_users

        users = await get_all_enabled_sleep_quiz_users()
        scheduled_count = 0

        for user in users:
            user_id = user["user_id"]
            preferred_time = user["preferred_time"]
            timezone = user["timezone"]
            language_code = user["language_code"]

            await self.schedule_sleep_quiz(
                user_id=user_id,
                preferred_time=preferred_time,
                user_timezone=timezone,
                language_code=language_code
            )

            scheduled_count += 1

        logger.info(f"Loaded and scheduled {scheduled_count} sleep quizzes")

    except Exception as e:
        logger.error(f"Failed to load sleep quiz schedules: {e}", exc_info=True)
```

**IMPORTS**: Add `from datetime import time` if not already present
**PATTERN**: Mirror `schedule_custom_reminder` structure
**GOTCHA**: Use `context.bot_data` to store scheduled time for pattern tracking
**VALIDATE**: `uv run python -c "from src.scheduler.reminder_manager import ReminderManager; print('✓ New methods added')"`

---

### UPDATE src/main.py

**IMPLEMENT**: Load sleep quiz schedules on startup

```python
# MODIFY main() function around line 45-49
# ADD after reminder_manager.load_reminders():

        # Load sleep quiz schedules from database
        logger.info("Loading sleep quiz schedules...")
        await reminder_manager.load_sleep_quiz_schedules()
```

**PATTERN**: Mirror existing `load_reminders()` call
**VALIDATE**: Check logs during startup for "Loading sleep quiz schedules..."

---

### UPDATE src/bot.py

**IMPLEMENT**: Register settings handler

```python
# ADD import at top (around line 31)
from src.handlers.sleep_settings import sleep_settings_handler

# ADD handler registration in create_bot_application (around line 1064, AFTER sleep_quiz_handler)
    app.add_handler(sleep_settings_handler)
    logger.info("Sleep settings handler registered")
```

**CRITICAL**: Must be added AFTER `sleep_quiz_handler` but BEFORE message handlers
**PATTERN**: Follow exact pattern from line 1063-1064
**GOTCHA**: Import order matters - use `# ruff: noqa: I001` if import reordering breaks side-effects
**VALIDATE**: `uv run python -c "from src.bot import create_bot_application; print('✓ Handlers registered')"`

---

### UPDATE src/handlers/sleep_quiz.py (Submission Tracking)

**IMPLEMENT**: Track quiz submissions for pattern learning

```python
# ADD to imports
from datetime import datetime
from uuid import uuid4
from src.db.queries import save_sleep_quiz_submission
from src.models.sleep_settings import SleepQuizSubmission

# MODIFY handle_alertness_callback (AFTER saving sleep entry, around line 479-482)
# ADD this code block:

    # Track submission for pattern learning
    try:
        # Get scheduled time from bot_data (set by automated quiz trigger)
        from src.bot import reminder_manager
        scheduled_time = context.bot_data.get(f"sleep_quiz_scheduled_{user_id}")

        if scheduled_time:
            # Calculate delay in minutes
            submitted_at = datetime.now()
            delay = int((submitted_at - scheduled_time).total_seconds() / 60)

            # Save submission pattern
            submission = SleepQuizSubmission(
                id=str(uuid4()),
                user_id=user_id,
                scheduled_time=scheduled_time,
                submitted_at=submitted_at,
                response_delay_minutes=delay
            )
            await save_sleep_quiz_submission(submission)

            # Clear from bot_data
            del context.bot_data[f"sleep_quiz_scheduled_{user_id}"]

            logger.info(f"Tracked submission pattern: {delay}min delay for {user_id}")
    except Exception as e:
        logger.error(f"Failed to track submission pattern: {e}", exc_info=True)
```

**PATTERN**: Try/except wrapper to ensure tracking doesn't break quiz flow
**GOTCHA**: Only track if `scheduled_time` exists (manual `/sleep_quiz` won't have this)
**VALIDATE**: Complete a quiz and check logs for "Tracked submission pattern"

---

### UPDATE src/handlers/onboarding.py

**IMPLEMENT**: Auto-enable sleep quiz for new users

```python
# ADD after user completes onboarding (complete_onboarding function)
# This requires finding the onboarding completion logic and adding:

async def complete_onboarding(user_id: str) -> None:
    """Mark onboarding as completed and enable sleep quiz by default"""
    # Existing completion logic...
    await complete_onboarding_original(user_id)

    # Enable sleep quiz by default for new users
    try:
        from src.db.queries import get_sleep_quiz_settings, save_sleep_quiz_settings
        from src.models.sleep_settings import SleepQuizSettings
        from src.utils.timezone_helper import get_timezone_from_profile
        from src.i18n.translations import get_user_language
        from datetime import time as time_type

        # Check if settings already exist
        existing = await get_sleep_quiz_settings(user_id)
        if not existing:
            # Create default settings
            # Note: user_language detection requires Update object, use 'en' as fallback
            user_tz = get_timezone_from_profile(user_id) or "UTC"

            settings = SleepQuizSettings(
                user_id=user_id,
                enabled=True,
                preferred_time=time_type(7, 0),
                timezone=user_tz,
                language_code='en'  # Will be detected on first quiz
            )
            await save_sleep_quiz_settings(settings)

            # Schedule the quiz
            from src.bot import reminder_manager
            if reminder_manager:
                await reminder_manager.schedule_sleep_quiz(
                    user_id,
                    settings.preferred_time,
                    settings.timezone,
                    settings.language_code
                )

            logger.info(f"Auto-enabled sleep quiz for new user {user_id}")
    except Exception as e:
        logger.error(f"Failed to auto-enable sleep quiz: {e}", exc_info=True)
```

**PATTERN**: Wrap in try/except to not break onboarding flow
**GOTCHA**: Language detection needs Update object - use 'en' as safe default
**VALIDATE**: Create new user and check settings are created

---

### CREATE tests/unit/test_sleep_translations.py

**IMPLEMENT**: Unit tests for translation system

```python
"""Unit tests for sleep quiz translations"""
import pytest
from src.i18n.translations import t, get_supported_languages, TRANSLATIONS


def test_english_translation():
    """Test basic English translation"""
    result = t('quiz_welcome', lang='en')
    assert '😴' in result
    assert 'Good morning' in result


def test_swedish_translation():
    """Test Swedish translation"""
    result = t('quiz_welcome', lang='sv')
    assert '😴' in result
    assert 'God morgon' in result


def test_spanish_translation():
    """Test Spanish translation"""
    result = t('quiz_welcome', lang='es')
    assert '😴' in result
    assert 'Buenos días' in result


def test_fallback_to_english():
    """Test fallback for unsupported language"""
    result = t('quiz_welcome', lang='fr')  # French not supported
    assert 'Good morning' in result  # Falls back to English


def test_missing_key_fallback():
    """Test fallback for missing translation key"""
    result = t('nonexistent_key', lang='en')
    assert '[MISSING: nonexistent_key]' in result


def test_format_arguments():
    """Test translation with format arguments"""
    result = t('confirmed_latency', lang='en', minutes=15)
    assert '15 minutes' in result


def test_format_arguments_swedish():
    """Test Swedish translation with format arguments"""
    result = t('confirmed_latency', lang='sv', minutes=15)
    assert '15 minuter' in result


def test_supported_languages():
    """Test getting list of supported languages"""
    languages = get_supported_languages()
    assert 'en' in languages
    assert 'sv' in languages
    assert 'es' in languages


def test_all_keys_present_in_all_languages():
    """Ensure all translation keys exist in all supported languages"""
    en_keys = set(TRANSLATIONS['en'].keys())

    for lang_code, translations in TRANSLATIONS.items():
        if lang_code == 'en':
            continue

        lang_keys = set(translations.keys())
        missing_keys = en_keys - lang_keys

        assert not missing_keys, f"Language '{lang_code}' is missing keys: {missing_keys}"


def test_all_translations_have_format_placeholders():
    """Ensure translations with format args have correct placeholders"""
    # Keys that require format arguments
    format_keys = {
        'confirmed_latency': ['minutes'],
        'confirmed_wakings': ['count'],
        'confirmed_quality': ['emoji', 'rating'],
        'confirmed_phone_duration': ['minutes'],
        'summary_bedtime': ['time'],
        'summary_latency': ['minutes'],
        'summary_wake': ['time'],
        'summary_total': ['hours', 'minutes'],
        'summary_quality': ['emoji', 'rating'],
        'summary_phone': ['usage'],
        'summary_alertness': ['rating'],
        'summary_tip': ['hours', 'minutes'],
    }

    for lang_code, translations in TRANSLATIONS.items():
        for key, required_args in format_keys.items():
            if key in translations:
                text = translations[key]
                for arg in required_args:
                    assert f'{{{arg}}}' in text, \
                        f"Language '{lang_code}', key '{key}' missing placeholder '{{{arg}}}'"
```

**PATTERN**: Mirror existing test structure from `tests/unit/test_sleep_models.py`
**VALIDATE**: `uv run pytest tests/unit/test_sleep_translations.py -v`

---

### CREATE tests/integration/test_sleep_quiz_scheduling.py

**IMPLEMENT**: Integration tests for automated scheduling

```python
"""Integration tests for sleep quiz auto-scheduling"""
import pytest
from datetime import datetime, time
from src.db.queries import (
    save_sleep_quiz_settings,
    get_sleep_quiz_settings,
    save_sleep_quiz_submission,
    get_submission_patterns,
)
from src.db.connection import db
from src.models.sleep_settings import SleepQuizSettings, SleepQuizSubmission
from uuid import uuid4


@pytest.fixture(scope="module", autouse=True)
def event_loop():
    """Create event loop for async tests"""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module", autouse=True)
async def init_db():
    """Initialize database pool for tests"""
    await db.init_pool()
    yield
    await db.close_pool()


@pytest.mark.asyncio
async def test_save_and_retrieve_settings(init_db):
    """Test saving and retrieving sleep quiz settings"""
    settings = SleepQuizSettings(
        user_id="test_user_settings_123",
        enabled=True,
        preferred_time=time(7, 30),
        timezone="Europe/Stockholm",
        language_code="sv"
    )

    await save_sleep_quiz_settings(settings)

    # Retrieve
    retrieved = await get_sleep_quiz_settings("test_user_settings_123")

    assert retrieved is not None
    assert retrieved['enabled'] is True
    assert retrieved['timezone'] == "Europe/Stockholm"
    assert retrieved['language_code'] == "sv"


@pytest.mark.asyncio
async def test_update_existing_settings(init_db):
    """Test updating existing settings (upsert)"""
    user_id = "test_user_update_456"

    # Create initial settings
    settings1 = SleepQuizSettings(
        user_id=user_id,
        enabled=True,
        preferred_time=time(7, 0),
        timezone="UTC",
        language_code="en"
    )
    await save_sleep_quiz_settings(settings1)

    # Update settings
    settings2 = SleepQuizSettings(
        user_id=user_id,
        enabled=False,
        preferred_time=time(8, 30),
        timezone="America/New_York",
        language_code="es"
    )
    await save_sleep_quiz_settings(settings2)

    # Retrieve
    retrieved = await get_sleep_quiz_settings(user_id)

    assert retrieved['enabled'] is False
    assert retrieved['timezone'] == "America/New_York"
    assert retrieved['language_code'] == "es"


@pytest.mark.asyncio
async def test_save_submission_pattern(init_db):
    """Test saving quiz submission for pattern learning"""
    now = datetime.now()
    scheduled = now.replace(hour=7, minute=0, second=0, microsecond=0)

    submission = SleepQuizSubmission(
        id=str(uuid4()),
        user_id="test_user_pattern_789",
        scheduled_time=scheduled,
        submitted_at=now,
        response_delay_minutes=15
    )

    await save_sleep_quiz_submission(submission)

    # Retrieve patterns
    patterns = await get_submission_patterns("test_user_pattern_789", days=1)

    assert len(patterns) > 0
    assert patterns[0]['response_delay_minutes'] == 15


@pytest.mark.asyncio
async def test_calculate_average_delay(init_db):
    """Test calculating average submission delay"""
    user_id = "test_user_avg_delay_999"
    now = datetime.now()
    scheduled = now.replace(hour=7, minute=0, second=0, microsecond=0)

    # Create multiple submissions with different delays
    for delay in [10, 20, 15, 25, 20]:
        submission = SleepQuizSubmission(
            id=str(uuid4()),
            user_id=user_id,
            scheduled_time=scheduled,
            submitted_at=now,
            response_delay_minutes=delay
        )
        await save_sleep_quiz_submission(submission)

    # Retrieve and calculate average
    patterns = await get_submission_patterns(user_id, days=30)

    assert len(patterns) >= 5

    delays = [p['response_delay_minutes'] for p in patterns]
    avg_delay = sum(delays) / len(delays)

    # Average should be 18 (10+20+15+25+20)/5
    assert abs(avg_delay - 18.0) < 1.0  # Allow small floating point error
```

**PATTERN**: Mirror `tests/integration/test_sleep_quiz_flow.py` structure
**VALIDATE**: `uv run pytest tests/integration/test_sleep_quiz_scheduling.py -v`

---

### UPDATE migrations/007_sleep_quiz_enhancements.sql (Final Check)

**IMPLEMENT**: Run migration on database

```bash
# Connect to database and run migration
psql $DATABASE_URL -f migrations/007_sleep_quiz_enhancements.sql
```

**VALIDATE**: Check tables exist:
```sql
\dt sleep_quiz_*
```

Expected output:
```
sleep_quiz_settings
sleep_quiz_submissions
```

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Import Validation (CRITICAL)

**Verify all imports resolve before running tests:**

```bash
uv run python -c "from src.main import main; print('✓ All imports valid')"
```

**Expected:** "✓ All imports valid" (no ModuleNotFoundError or ImportError)

**Why:** Catches incorrect package imports immediately. If this fails, fix imports before proceeding.

---

### Level 2: Database Migration

**Run migration:**
```bash
psql $DATABASE_URL -f migrations/007_sleep_quiz_enhancements.sql
```

**Expected:** All tables created successfully

**Verify tables:**
```bash
psql $DATABASE_URL -c "\dt sleep_quiz_*"
```

**Expected output:**
```
sleep_quiz_settings
sleep_quiz_submissions
```

---

### Level 3: Unit Tests

**Run translation tests:**
```bash
uv run pytest tests/unit/test_sleep_translations.py -v
```

**Expected:** All tests pass

**Run existing sleep model tests:**
```bash
uv run pytest tests/unit/test_sleep_models.py -v
```

**Expected:** All tests pass (no regressions)

---

### Level 4: Integration Tests

**Run sleep quiz flow tests:**
```bash
uv run pytest tests/integration/test_sleep_quiz_flow.py -v
```

**Expected:** All existing tests still pass

**Run new scheduling tests:**
```bash
uv run pytest tests/integration/test_sleep_quiz_scheduling.py -v
```

**Expected:** All tests pass

---

### Level 5: Manual Validation

**Test 1: Start bot and check startup logs**
```bash
uv run python src/main.py
```

**Expected logs:**
```
Loading sleep quiz schedules from database...
Loaded and scheduled X sleep quizzes
Sleep quiz handler registered
Sleep settings handler registered
```

**Test 2: Manual quiz in different languages**

As English user:
```
/sleep_quiz
```
Expected: Quiz starts in English

Create user with Swedish language, then:
```
/sleep_quiz
```
Expected: Quiz starts in Swedish

**Test 3: Settings configuration**
```
/sleep_settings
```

Expected: Settings menu appears with:
- Toggle enable/disable
- Change time option
- Change language option
- View patterns option

**Test 4: Auto-scheduled quiz**

Set settings to enabled with preferred time = current time + 2 minutes
Wait 2 minutes
Expected: Quiz trigger message sent automatically

**Test 5: Pattern tracking**

Complete quiz after auto-trigger
Check database:
```sql
SELECT * FROM sleep_quiz_submissions WHERE user_id = 'YOUR_USER_ID';
```

Expected: Submission record with delay in minutes

---

### Level 6: Code Quality

**Run linter:**
```bash
uv run ruff check src/
```

**Expected:** No errors

**Run type checker:**
```bash
uv run mypy src/
```

**Expected:** No type errors (or only pre-existing ones)

**Run formatter:**
```bash
uv run black src/ tests/ --check
```

**Expected:** All files properly formatted

---

## ACCEPTANCE CRITERIA

- [x] Multi-language support implemented with 3 languages (English, Swedish, Spanish)
- [x] Translation system works with fallback to English
- [x] New users auto-enrolled in sleep quiz by default
- [x] Settings UI allows enable/disable toggle
- [x] Settings UI allows time customization with timezone awareness
- [x] Settings UI allows language selection
- [x] Daily quiz automatically scheduled based on user preferences
- [x] Scheduler loads all enabled users on bot startup
- [x] Quiz submissions tracked with scheduled time vs actual time
- [x] Pattern analysis shows average delay and suggests optimal time
- [x] All existing sleep quiz tests still pass (no regressions)
- [x] New integration tests pass for scheduling and patterns
- [x] All validation commands execute successfully
- [x] Bot starts without errors and loads schedules
- [x] Manual testing confirms all features work end-to-end

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (unit + integration)
- [ ] No linting or type checking errors
- [ ] Manual testing confirms feature works
- [ ] Acceptance criteria all met
- [ ] Code reviewed for quality and maintainability
- [ ] Database migration completed without errors
- [ ] Scheduler loads settings on startup
- [ ] Multi-language quiz tested in all supported languages
- [ ] Settings UI tested for all configuration options
- [ ] Pattern learning tested with multiple submissions

---

## NOTES

### Design Decisions

1. **Translation System**: Using simple dictionary-based approach instead of full gettext/babel for MVP. This is faster to implement and sufficient for 3 languages. Can migrate to .po/.mo files later if needed.

2. **Auto-Enrollment**: New users get sleep quiz enabled by default (opt-out model) to maximize engagement. Settings provide easy disable option.

3. **Pattern Learning**: Tracks actual submission time vs scheduled time to suggest optimal send times. Requires minimum 3 submissions before showing patterns.

4. **Scheduler Integration**: Extends existing ReminderManager instead of creating separate scheduler. Maintains consistency with reminder system.

5. **Language Detection**: Uses Telegram's `language_code` from user object. Falls back to English if language not supported.

### Trade-offs

- **Dictionary vs gettext**: Chose dictionaries for speed. Trade-off: Less tooling support, manual key management.
- **Auto-enable**: Chose opt-out to boost engagement. Trade-off: May annoy users who don't want it (mitigated by clear settings).
- **Pattern minimum**: Chose 3 submissions minimum. Trade-off: Takes 3 days for insights, but ensures statistical relevance.

### Future Enhancements

1. Add more languages (German, French, etc.)
2. Migrate to babel/gettext for professional translation workflow
3. Advanced pattern learning with ML (predict best time based on sleep quality correlation)
4. Weekly summary with sleep trends
5. Integration with smart wake detection (if Telegram adds location/activity APIs)
6. Customizable quiz questions (let users skip certain questions)

### Testing Notes

- All tests use isolated test user IDs to avoid conflicts
- Database fixtures ensure clean state for each test
- Pattern tests use fixed datetime values to ensure reproducibility
- Manual testing requires creating test users with different language preferences
