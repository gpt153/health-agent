# Telegram Sleep Quiz Implementation Research

## Executive Summary

This document outlines how to implement the sleep quiz features described in `sleep-quiz-research.md` using Telegram Bot API capabilities. After researching Telegram's current UI options, here's what's possible and what workarounds are needed.

**Date of Research:** 2025-12-17
**Target Framework:** python-telegram-bot v22.5
**Telegram Bot API Version:** 2.0+

---

## Quick Answer: What Telegram Supports

### ✅ Native Support (Easy)
- **Inline Keyboard Buttons** - Radio buttons, multi-select, yes/no toggles
- **Reply Keyboards** - Persistent keyboard layouts
- **Callback Queries** - Button clicks without sending messages to chat

### ⚠️ Workaround Needed (Moderate Difficulty)
- **Number Pickers / Sliders** - Simulated using inline keyboard buttons with +/- controls
- **Time Pickers** - Custom implementations using inline keyboards or third-party libraries
- **Multi-step Forms** - Conversation state management required

### ❌ Not Natively Supported (Complex Alternative)
- **True Slider Controls** - Require Telegram Mini Apps (Web Apps)
- **Native Mobile UI Components** - Must use Telegram Mini Apps for iOS/Android native feel

---

## Implementation Strategies for Each Quiz Element

### 1. Buttons (Radio Buttons) - ✅ FULLY SUPPORTED

**Use Case:** Multiple choice questions with 2-5 options

**Implementation:**
```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Example: Sleep latency question
keyboard = [
    [InlineKeyboardButton("Less than 15 min", callback_data="latency_0-15")],
    [InlineKeyboardButton("15-30 min", callback_data="latency_15-30")],
    [InlineKeyboardButton("30-60 min", callback_data="latency_30-60")],
    [InlineKeyboardButton("More than 1 hour", callback_data="latency_60+")],
]
reply_markup = InlineKeyboardMarkup(keyboard)

await update.message.reply_text(
    "How long did it take you to fall asleep?",
    reply_markup=reply_markup
)
```

**Handling Callbacks:**
```python
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Remove loading animation

    # Parse the callback data
    data = query.data  # e.g., "latency_15-30"

    # Update the message to show selection
    await query.edit_message_text(
        text=f"✅ Selected: {query.data}"
    )

    # Save to database
    # Move to next question
```

**Resources:**
- [python-telegram-bot InlineKeyboardButton docs](https://docs.python-telegram-bot.org/en/stable/telegram.inlinekeyboardbutton.html)
- [Official inline keyboard example](https://github.com/python-telegram-bot/python-telegram-bot/blob/master/examples/inlinekeyboard.py)

---

### 2. Multi-Select Buttons - ✅ SUPPORTED (Custom Logic)

**Use Case:** "What disrupted your sleep? (Select all that apply)"

**Implementation Strategy:**
Store selections in context.user_data and update button states with checkmarks.

```python
async def disruption_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Initialize selection state
    if 'disruptions' not in context.user_data:
        context.user_data['disruptions'] = set()

    selected = context.user_data['disruptions']

    # Build keyboard with checkmarks for selected items
    keyboard = [
        [InlineKeyboardButton(
            f"{'✅ ' if 'noise' in selected else ''}🔊 Noise",
            callback_data="disruption_noise"
        )],
        [InlineKeyboardButton(
            f"{'✅ ' if 'light' in selected else ''}💡 Light",
            callback_data="disruption_light"
        )],
        [InlineKeyboardButton(
            f"{'✅ ' if 'temp' in selected else ''}🌡️ Temperature",
            callback_data="disruption_temp"
        )],
        [InlineKeyboardButton(
            f"{'✅ ' if 'stress' in selected else ''}😰 Stress",
            callback_data="disruption_stress"
        )],
        [InlineKeyboardButton("✅ Done", callback_data="disruption_done")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "What disrupted your sleep? (Select all that apply)",
        reply_markup=reply_markup
    )

async def disruption_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "disruption_done":
        # Proceed to next question
        await query.edit_message_text("Moving to next question...")
    else:
        # Toggle selection
        disruption_type = query.data.replace("disruption_", "")

        if disruption_type in context.user_data['disruptions']:
            context.user_data['disruptions'].remove(disruption_type)
        else:
            context.user_data['disruptions'].add(disruption_type)

        # Rebuild keyboard with updated selections
        # (reuse the keyboard building logic from above)
        await query.edit_message_reply_markup(reply_markup=new_keyboard)
```

**Resource:**
- [Medium: Multiselection Inline Keyboards](https://medium.com/@moraneus/enhancing-user-engagement-with-multiselection-inline-keyboards-in-telegram-bots-7cea9a371b8d)

---

### 3. Sliders (1-10 Scale) - ⚠️ WORKAROUND NEEDED

**Use Case:** "How would you rate your sleep quality?" (1-10 scale)

**Option A: Button Grid (Recommended for Simplicity)**
```python
# Create a 2-row button grid for 1-10
keyboard = [
    [InlineKeyboardButton(str(i), callback_data=f"quality_{i}") for i in range(1, 6)],
    [InlineKeyboardButton(str(i), callback_data=f"quality_{i}") for i in range(6, 11)],
]

# Add emoji labels
await update.message.reply_text(
    "How would you rate your sleep quality?\n\n"
    "😫 1-2 = Terrible\n"
    "😐 5-6 = Okay\n"
    "😊 9-10 = Excellent",
    reply_markup=InlineKeyboardMarkup(keyboard)
)
```

**Option B: Incremental Slider (More Interactive)**
```python
async def show_slider(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_value = context.user_data.get('quality_rating', 5)

    keyboard = [
        [
            InlineKeyboardButton("➖", callback_data="quality_dec"),
            InlineKeyboardButton(f"⭐ {current_value} ⭐", callback_data="quality_noop"),
            InlineKeyboardButton("➕", callback_data="quality_inc"),
        ],
        [InlineKeyboardButton("✅ Confirm", callback_data="quality_confirm")],
    ]

    emoji_map = {
        1: "😫", 2: "😫", 3: "😕", 4: "😐", 5: "😐",
        6: "🙂", 7: "🙂", 8: "😊", 9: "😊", 10: "😊"
    }

    await update.message.reply_text(
        f"Sleep Quality: {current_value}/10 {emoji_map[current_value]}\n\n"
        f"Use ➖ and ➕ to adjust",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def slider_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    current = context.user_data.get('quality_rating', 5)

    if query.data == "quality_inc" and current < 10:
        context.user_data['quality_rating'] = current + 1
        # Rebuild and update keyboard
    elif query.data == "quality_dec" and current > 1:
        context.user_data['quality_rating'] = current - 1
        # Rebuild and update keyboard
    elif query.data == "quality_confirm":
        # Save and move to next question
        pass
```

**Option C: Telegram Mini App (Full Slider)**
For true HTML5 slider controls, implement as a Web App (see section below).

**Resources:**
- [Telegram Bot API Buttons docs](https://core.telegram.org/api/bots/buttons)
- [go-telegram/ui slider example](https://github.com/go-telegram/ui/blob/main/slider/readme.md) (Go, but shows the concept)

---

### 4. Time Pickers - ⚠️ WORKAROUND NEEDED

**Use Case:** "What time did you get into bed?" / "What time did you wake up?"

**Option A: Use Existing Library (Easiest)**

For **date picking**, there are libraries available:
- [python-telegram-bot-calendar](https://pypi.org/project/python-telegram-bot-calendar/)
- [calendar-telegram](https://github.com/unmonoqueteclea/calendar-telegram)

For **time picking**, no mature python-telegram-bot library exists, but there's:
- [inline-timepicker for aiogram](https://github.com/Birdi7/inline-timepicker) (could be adapted)

**Option B: Custom Implementation (Recommended)**

```python
async def time_picker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show time picker for bedtime"""
    hour = context.user_data.get('bedtime_hour', 22)
    minute = context.user_data.get('bedtime_minute', 0)

    keyboard = [
        [
            InlineKeyboardButton("🔼", callback_data="time_hour_up"),
            InlineKeyboardButton("", callback_data="noop"),
            InlineKeyboardButton("🔼", callback_data="time_min_up"),
        ],
        [
            InlineKeyboardButton(f"{hour:02d}", callback_data="noop"),
            InlineKeyboardButton(":", callback_data="noop"),
            InlineKeyboardButton(f"{minute:02d}", callback_data="noop"),
        ],
        [
            InlineKeyboardButton("🔽", callback_data="time_hour_down"),
            InlineKeyboardButton("", callback_data="noop"),
            InlineKeyboardButton("🔽", callback_data="time_min_down"),
        ],
        [InlineKeyboardButton("✅ Confirm", callback_data="time_confirm")],
    ]

    await update.message.reply_text(
        "What time did you get into bed?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def time_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    hour = context.user_data.get('bedtime_hour', 22)
    minute = context.user_data.get('bedtime_minute', 0)

    if query.data == "time_hour_up":
        hour = (hour + 1) % 24
    elif query.data == "time_hour_down":
        hour = (hour - 1) % 24
    elif query.data == "time_min_up":
        minute = (minute + 15) % 60  # Increment by 15 min
    elif query.data == "time_min_down":
        minute = (minute - 15) % 60
    elif query.data == "time_confirm":
        # Save and proceed
        pass

    context.user_data['bedtime_hour'] = hour
    context.user_data['bedtime_minute'] = minute

    # Rebuild keyboard and update message
```

**Option C: Quick Selection Buttons**
For faster completion, offer pre-set time options:

```python
keyboard = [
    [
        InlineKeyboardButton("9 PM", callback_data="bedtime_21:00"),
        InlineKeyboardButton("10 PM", callback_data="bedtime_22:00"),
        InlineKeyboardButton("11 PM", callback_data="bedtime_23:00"),
    ],
    [
        InlineKeyboardButton("12 AM", callback_data="bedtime_00:00"),
        InlineKeyboardButton("1 AM", callback_data="bedtime_01:00"),
        InlineKeyboardButton("2 AM", callback_data="bedtime_02:00"),
    ],
    [InlineKeyboardButton("⏰ Custom time...", callback_data="bedtime_custom")],
]
```

**Option D: Text Input with Parse**
Simply ask user to type time:
```python
await update.message.reply_text(
    "What time did you get into bed?\n\n"
    "Reply with time like: 10:30 PM or 22:30"
)

# Parse response with regex or dateutil.parser
```

**Resources:**
- [python-telegram-bot-calendar on PyPI](https://pypi.org/project/python-telegram-bot-calendar/)
- [inline-timepicker (aiogram)](https://github.com/Birdi7/inline-timepicker)

---

### 5. Toggle Switches (Yes/No) - ✅ FULLY SUPPORTED

**Use Case:** "Did you use your phone while in bed?"

**Implementation:**
```python
keyboard = [
    [
        InlineKeyboardButton("✅ Yes", callback_data="phone_yes"),
        InlineKeyboardButton("❌ No", callback_data="phone_no"),
    ],
]

await update.message.reply_text(
    "Did you use your phone/screen while in bed?",
    reply_markup=InlineKeyboardMarkup(keyboard)
)
```

**With Conditional Follow-up:**
```python
async def phone_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "phone_yes":
        # Show follow-up question: "For how long?"
        keyboard = [
            [InlineKeyboardButton("< 15 min", callback_data="phone_dur_0-15")],
            [InlineKeyboardButton("15-30 min", callback_data="phone_dur_15-30")],
            [InlineKeyboardButton("30-60 min", callback_data="phone_dur_30-60")],
            [InlineKeyboardButton("1+ hour", callback_data="phone_dur_60+")],
        ]
        await query.edit_message_text(
            "For how long?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        # Skip follow-up, move to next question
        context.user_data['phone_usage'] = False
        await query.edit_message_text("✅ Noted: No phone usage")
        # Proceed to next question
```

---

## Conversation State Management

For multi-step quiz flow, use ConversationHandler:

```python
from telegram.ext import ConversationHandler, CallbackQueryHandler, MessageHandler

# Define states
SLEEP_TIMING, SLEEP_QUALITY, PHONE_USAGE, DISRUPTIONS, ALERTNESS = range(5)

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start sleep quiz"""
    await update.message.reply_text(
        "Good morning! Let's log your sleep 😴\n\n"
        "This will take about 60 seconds."
    )

    # Ask first question (bedtime)
    await ask_bedtime(update, context)
    return SLEEP_TIMING

async def ask_bedtime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Show time picker
    # ... (implementation from above)
    pass

# Conversation handler
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('sleep_quiz', start_quiz)],
    states={
        SLEEP_TIMING: [CallbackQueryHandler(bedtime_callback)],
        SLEEP_QUALITY: [CallbackQueryHandler(quality_callback)],
        PHONE_USAGE: [CallbackQueryHandler(phone_callback)],
        DISRUPTIONS: [CallbackQueryHandler(disruption_callback)],
        ALERTNESS: [CallbackQueryHandler(alertness_callback)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)

application.add_handler(conv_handler)
```

**Resources:**
- [python-telegram-bot ConversationHandler docs](https://docs.python-telegram-bot.org/en/stable/telegram.ext.conversationhandler.html)
- [Official conversation example](https://github.com/python-telegram-bot/python-telegram-bot/blob/master/examples/conversationbot.py)

---

## Advanced Option: Telegram Mini Apps (Web Apps)

If you need **true slider controls, native UI feel, and complex forms**, use Telegram Mini Apps.

### What Are Mini Apps?

Mini Apps are HTML5 web applications that run inside Telegram with native-like integration. They support:
- ✅ Full HTML5/CSS/JavaScript control
- ✅ Real slider inputs, date/time pickers, custom forms
- ✅ Access to Telegram user data and theming
- ✅ Payment integration
- ✅ Cross-platform (iOS, Android, Desktop)

### When to Use Mini Apps vs. Inline Keyboards

**Use Inline Keyboards If:**
- Simple forms with < 15 questions
- Binary choices and multiple choice
- Quick interactions
- No need for complex validation
- Want to keep everything in chat

**Use Mini Apps If:**
- Need true slider controls
- Complex multi-step forms (20+ questions)
- Advanced UI (charts, graphs, animations)
- Native mobile feel is important
- Need custom validation and complex logic
- Payment integration required

### Implementation Overview

**1. Create HTML5 App:**
```html
<!DOCTYPE html>
<html>
<head>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        /* Use Telegram theme colors */
        body {
            background-color: var(--tg-theme-bg-color);
            color: var(--tg-theme-text-color);
        }
        .slider {
            width: 100%;
            height: 40px;
            /* Native slider styling */
        }
    </style>
</head>
<body>
    <h2>Sleep Quality</h2>
    <input type="range" min="1" max="10" value="5" class="slider" id="quality">
    <p>Quality: <span id="qualityValue">5</span>/10</p>

    <button id="submit">Submit</button>

    <script>
        // Access Telegram WebApp API
        const tg = window.Telegram.WebApp;

        // Get user data
        const user = tg.initDataUnsafe.user;

        // Send data back to bot
        document.getElementById('submit').addEventListener('click', () => {
            const quality = document.getElementById('quality').value;
            tg.sendData(JSON.stringify({quality: quality}));
            tg.close();
        });

        // Update slider display
        document.getElementById('quality').oninput = function() {
            document.getElementById('qualityValue').textContent = this.value;
        };
    </script>
</body>
</html>
```

**2. Host the Web App:**
- Host on any HTTPS server (required)
- Or use services like GitHub Pages, Vercel, Netlify

**3. Register Web App with BotFather:**
```
/mybots → Select your bot → Bot Settings → Menu Button → Edit Menu Button URL
```

**4. Send Web App Button from Bot:**
```python
from telegram import WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup

keyboard = [
    [InlineKeyboardButton(
        "📊 Fill Sleep Quiz",
        web_app=WebAppInfo(url="https://yourdomain.com/sleep-quiz.html")
    )],
]

await update.message.reply_text(
    "Ready to log your sleep?",
    reply_markup=InlineKeyboardMarkup(keyboard)
)
```

**5. Handle Data from Web App:**
```python
async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle data sent from web app"""
    data = json.loads(update.message.web_app_data.data)

    quality = data['quality']
    # Save to database

    await update.message.reply_text(
        f"✅ Sleep quality recorded: {quality}/10"
    )

app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
```

### UI Frameworks for Mini Apps

**React-based:**
- [TelegramUI by Telegram Mini Apps](https://github.com/telegram-mini-apps-dev/TelegramUI) - 25+ components, 250+ styles
- [@telegram-apps/sdk-react](https://docs.telegram-mini-apps.com/packages/telegram-apps-sdk-react/1-x)

**Design Resources:**
- [Telegram Mini Apps UI Kit (Figma)](https://www.figma.com/community/file/1348989725141777736/telegram-mini-apps-ui-kit)

**Resources:**
- [Official Telegram Mini Apps docs](https://core.telegram.org/bots/webapps)
- [Step-by-step Mini App guide (Python)](https://medium.com/@calixtemayoraz/step-by-step-guide-to-build-a-telegram-chatbot-with-a-simple-webapp-ui-using-python-44dca453522f)
- [Telegram Mini Apps guide 2024](https://www.directual.com/blog/all-you-should-know-about-telegram-mini-apps-in-2024)
- [How to Build a Telegram Mini App](https://metaschool.so/articles/how-to-build-telegram-mini-app)

---

## Recommended Approach for Sleep Quiz

### Phase 1: MVP with Inline Keyboards (Recommended Start)

**Advantages:**
- ✅ No web hosting required
- ✅ Works entirely in chat
- ✅ Faster development
- ✅ Simpler maintenance
- ✅ Good enough for 80% of use cases

**Implementation:**
1. Use **inline keyboard buttons** for all multiple choice
2. Use **button grid (1-10)** for quality ratings instead of sliders
3. Use **custom time picker** with +/- buttons OR **quick selection buttons**
4. Use **multi-select buttons** with checkmarks for disruptions
5. Use **ConversationHandler** for state management

**Expected Completion Time:** 60-90 seconds (matches research goal)

**Sample Flow:**
```
Bot: "Good morning! Let's log your sleep 😴 (60 seconds)"

Q1: What time did you get into bed?
     [9PM] [10PM] [11PM] [12AM] [1AM] [2AM] [⏰ Custom]

Q2: How long to fall asleep?
     [< 15 min] [15-30 min] [30-60 min] [1+ hour]

Q3: What time did you wake up?
     [6AM] [7AM] [8AM] [9AM] [10AM] [⏰ Custom]

Q4: Did you wake up during the night?
     [No] [Yes, 1-2 times] [Yes, 3+ times]

Q5: Sleep quality rating?
     [1] [2] [3] [4] [5] [6] [7] [8] [9] [10]
     😫 Terrible  😐 Okay  😊 Excellent

Q6: Did you use your phone in bed?
     [✅ Yes] [❌ No]
     → If yes: For how long? [<15min] [15-30min] [30-60min] [1+hr]

Q7: What disrupted your sleep? (multi-select)
     [🔊 Noise] [💡 Light] [🌡️ Temperature]
     [😰 Stress] [😱 Bad dream] [🤕 Pain]
     [✅ Nothing] [Done ✓]

Q8: How alert do you feel now?
     [1] [2] [3] [4] [5] [6] [7] [8] [9] [10]
     😴 Exhausted  😐 Normal  ⚡ Wide awake

Bot: "✅ Sleep logged! You slept 7h 15min. Quality: 7/10"
     [📊 View Report] [📈 See Trends]
```

### Phase 2: Enhanced with Mini App (Future)

When you need:
- True slider controls for better UX
- Visual charts and graphs
- More complex forms (15+ questions)
- Native mobile feel

Then migrate to a Mini App with:
- HTML5 sliders for quality ratings
- Native time pickers
- Interactive visualizations
- Smooth animations

---

## Database Schema for Sleep Quiz

```python
# In src/models/sleep.py
from pydantic import BaseModel
from datetime import datetime, time
from typing import Optional

class SleepEntry(BaseModel):
    """Sleep quiz entry"""
    id: str
    user_id: str
    logged_at: datetime  # When quiz was filled

    # Timing
    bedtime: time
    sleep_latency_minutes: int  # Time to fall asleep
    wake_time: time
    total_sleep_hours: float  # Calculated

    # Quality
    night_wakings: int  # 0, 1-2, 3+
    sleep_quality_rating: int  # 1-10
    disruptions: list[str]  # ["noise", "light", "stress"]

    # Behavior
    phone_usage: bool
    phone_duration_minutes: Optional[int]

    # Current state
    alertness_rating: int  # 1-10

    # Optional fields
    exercise_yesterday: Optional[str]
    stress_level: Optional[int]
    consumed_before_bed: Optional[list[str]]
```

```sql
-- Migration: 005_sleep_tracking.sql
CREATE TABLE IF NOT EXISTS sleep_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Timing
    bedtime TIME NOT NULL,
    sleep_latency_minutes INTEGER NOT NULL,
    wake_time TIME NOT NULL,
    total_sleep_hours FLOAT NOT NULL,

    -- Quality
    night_wakings INTEGER NOT NULL,
    sleep_quality_rating INTEGER NOT NULL CHECK (sleep_quality_rating BETWEEN 1 AND 10),
    disruptions JSONB,  -- ["noise", "light"]

    -- Behavior
    phone_usage BOOLEAN NOT NULL,
    phone_duration_minutes INTEGER,

    -- Current state
    alertness_rating INTEGER NOT NULL CHECK (alertness_rating BETWEEN 1 AND 10),

    -- Optional
    exercise_yesterday VARCHAR(50),
    stress_level INTEGER,
    consumed_before_bed JSONB
);

CREATE INDEX idx_sleep_entries_user_logged ON sleep_entries(user_id, logged_at DESC);
```

---

## Code Integration Points

### 1. Add Handler in src/bot.py

```python
from src.handlers.sleep_quiz import sleep_quiz_handler

# In create_bot_application():
app.add_handler(sleep_quiz_handler)
```

### 2. Create Handler File

```python
# src/handlers/sleep_quiz.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# States
BEDTIME, SLEEP_LATENCY, WAKE_TIME, NIGHT_WAKINGS, QUALITY, PHONE, DISRUPTIONS, ALERTNESS = range(8)

async def start_sleep_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for sleep quiz"""
    # Implementation...
    pass

async def bedtime_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Implementation...
    pass

# ... more handlers

sleep_quiz_handler = ConversationHandler(
    entry_points=[CommandHandler('sleep_quiz', start_sleep_quiz)],
    states={
        BEDTIME: [CallbackQueryHandler(bedtime_callback)],
        SLEEP_LATENCY: [CallbackQueryHandler(latency_callback)],
        # ... more states
    },
    fallbacks=[CommandHandler('cancel', cancel_quiz)],
)
```

### 3. Add to Database Queries

```python
# src/db/queries.py

async def save_sleep_entry(entry: SleepEntry) -> None:
    """Save sleep quiz entry to database"""
    query = """
        INSERT INTO sleep_entries (
            user_id, bedtime, sleep_latency_minutes, wake_time,
            total_sleep_hours, night_wakings, sleep_quality_rating,
            disruptions, phone_usage, phone_duration_minutes,
            alertness_rating
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
    """
    # Implementation...

async def get_sleep_entries(user_id: str, days: int = 7) -> list[dict]:
    """Get recent sleep entries for user"""
    # Implementation...
```

### 4. Trigger Options

**Option A: Daily Reminder**
```python
# In src/scheduler/reminder_manager.py
# Schedule daily reminder at 9 AM to fill sleep quiz
```

**Option B: User-Initiated**
```python
# User sends /sleep_quiz command
# Or inline keyboard button in main menu
```

**Option C: Automatic Trigger**
```python
# Detect first message of the day and prompt
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Check if sleep logged today
    if not await has_logged_sleep_today(user_id):
        keyboard = [[InlineKeyboardButton(
            "📊 Log Last Night's Sleep",
            callback_data="start_sleep_quiz"
        )]]
        await update.message.reply_text(
            "Good morning! Ready to log your sleep?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
```

---

## UX Best Practices for Telegram Implementation

### 1. Show Progress
```python
progress = f"Question {current_question}/8 {'▓' * current_question}{'░' * (8-current_question)}"
```

### 2. Provide Context
```python
# Always show what was previously answered
context_text = (
    f"✅ Bedtime: {bedtime}\n"
    f"✅ Sleep latency: {latency}\n"
    f"Current: Wake time?"
)
```

### 3. Allow Editing
```python
keyboard = [
    # ... question buttons
    [InlineKeyboardButton("← Go Back", callback_data="prev_question")],
]
```

### 4. Immediate Feedback
```python
await query.answer("✅ Saved!")  # Toast notification
await query.edit_message_text(f"✅ Selected: {choice}")
```

### 5. Summary at End
```python
summary = f"""
✅ Sleep Logged!

🛏️ Bedtime: {bedtime}
😴 Fell asleep: {sleep_latency} min
⏰ Woke up: {wake_time}
⏱️ Total sleep: {total_hours}h {total_minutes}m

🌙 Quality: {quality_emoji} {quality}/10
📱 Phone usage: {phone_usage}
😌 Alertness: {alertness}/10

💡 Tip: You got {total_hours}h of sleep. Aim for 8-10h for optimal health!

[📊 View Week] [📈 See Trends] [🏆 Achievements]
"""
```

---

## Performance Considerations

### 1. Callback Data Limits
- Maximum callback_data size: **64 bytes** (UTF-8)
- Keep identifiers short: `"q1_opt2"` instead of `"sleep_quality_rating_option_2"`

### 2. Message Edit Rate Limits
- Don't update message too frequently (max ~30 edits/sec globally)
- For sliders, use debouncing or require "Confirm" button

### 3. Conversation Timeouts
```python
conv_handler = ConversationHandler(
    # ...
    conversation_timeout=600,  # 10 minutes
)
```

### 4. State Persistence
Store conversation state in context.user_data:
```python
context.user_data['quiz_state'] = {
    'bedtime': '22:00',
    'latency': 15,
    'started_at': datetime.now().isoformat()
}
```

For multi-bot deployments, use persistence:
```python
from telegram.ext import PicklePersistence

persistence = PicklePersistence(filepath="conversation_state.pickle")
app = Application.builder().token(TOKEN).persistence(persistence).build()
```

---

## Testing Strategy

### 1. Unit Tests
```python
# tests/unit/test_sleep_quiz.py
import pytest
from src.handlers.sleep_quiz import parse_time_input

def test_time_parsing():
    assert parse_time_input("10:30 PM") == time(22, 30)
    assert parse_time_input("22:30") == time(22, 30)
```

### 2. Integration Tests
```python
# tests/integration/test_sleep_quiz_flow.py
async def test_complete_sleep_quiz_flow():
    # Simulate full quiz completion
    # Assert database entry created
    pass
```

### 3. Manual Testing Checklist
- [ ] All buttons clickable
- [ ] Callback queries answered (no infinite loading)
- [ ] State transitions work correctly
- [ ] Cancel/back buttons work
- [ ] Data saves correctly to database
- [ ] Summary displays correct calculations
- [ ] Edge cases (midnight bedtime/wake, 24-hour wake)

---

## Comparison Table: Implementation Options

| Feature | Inline Keyboard | Mini App |
|---------|----------------|----------|
| **Development Time** | 2-3 days | 1-2 weeks |
| **Hosting Required** | No | Yes (HTTPS) |
| **User Experience** | Good | Excellent |
| **Mobile Feel** | Chat-based | Native-like |
| **Slider Controls** | Simulated | True HTML5 |
| **Time Pickers** | Custom | Native |
| **Maintenance** | Simple | Moderate |
| **Works Offline** | No | Can cache |
| **Cross-Platform** | ✅ All Telegram clients | ✅ All Telegram clients |
| **Recommended For** | MVP, simple forms | Advanced UI, complex forms |

---

## Conclusion & Recommendations

### For Your Health Agent Bot: Start with Inline Keyboards

**Why:**
1. ✅ Meets all core requirements from sleep-quiz-research.md
2. ✅ 60-90 second completion time achievable
3. ✅ No additional infrastructure needed
4. ✅ Integrates seamlessly with existing bot architecture
5. ✅ Can migrate to Mini App later if needed

**Implementation Roadmap:**

**Week 1: Core Quiz Flow**
- [ ] Create ConversationHandler with 8 states
- [ ] Implement time picker (quick select + custom)
- [ ] Implement quality rating (button grid 1-10)
- [ ] Add multi-select disruptions

**Week 2: Data & Polish**
- [ ] Create database migration
- [ ] Add save_sleep_entry query
- [ ] Implement summary view
- [ ] Add daily reminder trigger

**Week 3: Analytics & Insights**
- [ ] Calculate sleep metrics (duration, efficiency)
- [ ] Show weekly trends
- [ ] Add recommendations based on patterns

**Future Enhancement: Mini App**
- Only if users request better sliders/UI
- Can reuse all backend logic
- Frontend would be new HTML5 app

---

## Additional Resources

### Telegram Bot API
- [Official Telegram Bot API docs](https://core.telegram.org/bots/api)
- [python-telegram-bot documentation](https://docs.python-telegram-bot.org/)
- [Telegram Bot Features overview](https://core.telegram.org/bots/features)

### Examples & Tutorials
- [python-telegram-bot examples](https://github.com/python-telegram-bot/python-telegram-bot/tree/master/examples)
- [GeeksforGeeks: Keyboard buttons in Telegram bot](https://www.geeksforgeeks.org/python/keyboard-buttons-in-telegram-bot-using-python/)
- [Building Telegram Bot with Buttons (Medium)](https://medium.com/@travilabs/building-a-simple-telegram-bot-with-buttons-using-python-0a16c52485c0)

### UI Components
- [keyboa - Keyboard builder for python-telegram-bot](https://pypi.org/project/keyboa/)
- [Telegram Mini Apps UI Kit (Figma)](https://www.figma.com/community/file/1348989725141777736/telegram-mini-apps-ui-kit)

### Date/Time Pickers
- [python-telegram-bot-calendar](https://pypi.org/project/python-telegram-bot-calendar/)
- [calendar-telegram](https://github.com/unmonoqueteclea/calendar-telegram)
- [inline-timepicker for aiogram](https://github.com/Birdi7/inline-timepicker)

### Mini Apps
- [Telegram Mini Apps official docs](https://core.telegram.org/bots/webapps)
- [Mini Apps API reference](https://core.telegram.org/api/bots/webapps)
- [TelegramUI React Components](https://github.com/telegram-mini-apps-dev/TelegramUI)
- [Step-by-step Mini App guide](https://medium.com/@calixtemayoraz/step-by-step-guide-to-build-a-telegram-chatbot-with-a-simple-webapp-ui-using-python-44dca453522f)

---

**Document Version:** 1.0
**Last Updated:** 2025-12-17
**Author:** Health Agent Development Team
**Status:** Ready for Implementation
