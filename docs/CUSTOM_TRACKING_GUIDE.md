# Custom Tracking System - User Guide

## Overview

The Custom Tracking System lets you track any health metric you want beyond just food logging. Track period cycles, symptoms, energy levels, medications, mood, sleep quality, and more!

## Quick Start

### 1. Create Your First Tracker

Use the `/create_tracker` command in Telegram:

```
/create_tracker
```

You'll be presented with template options:
- 🩸 Period Tracking
- ⚡ Energy Levels
- 🤒 Symptom Tracking
- 💊 Medication Tracking
- 😊 Mood Tracking
- 😴 Sleep Quality
- 💧 Water Intake
- 🏃 Exercise Tracking

**Choose a template** to get started quickly, or **create custom** (coming soon) for fully personalized trackers.

### 2. Log Data

Once you've created a tracker, log data with `/log_tracker`:

```
/log_tracker
```

Select your tracker and enter values for each field. The format is simple:

```
field_name: value
another_field: another value
```

Example for Energy tracker:
```
level: 7
time_of_day: morning
quality: felt energized
```

### 3. View Your Data

See your recent tracking history with `/view_tracker`:

```
/view_tracker
```

Select the tracker you want to view. You'll see:
- Recent entries (last 10)
- Timestamps
- All field values
- Any notes you added

### 4. Ask the AI About Your Data

This is where the magic happens! Just chat naturally with the bot:

- "How has my energy been this week?"
- "Show me when I had headaches this month"
- "What's my average mood rating?"
- "Find days where my energy was below 5"
- "When should I expect my next period?"

The AI will use your tracker data to provide insights and recommendations!

## Available Tracker Templates

### 🩸 Period Tracking

**Fields:**
- Flow intensity (1-5 rating: spotting to very heavy)
- Symptoms (multiselect: cramps, headache, mood swings, fatigue, bloating, etc.)
- Mood (1-5 rating)
- Pain level (0-10 rating)

**What the AI can do:**
- Predict next period based on cycle length
- Suggest nutrition timing for cycle phases
- Identify symptom patterns
- Correlate symptoms with food intake

### ⚡ Energy Levels

**Fields:**
- Energy level (1-10 rating)
- Time of day (morning, midday, afternoon, evening, night)
- Notes (text)

**What the AI can do:**
- Track energy patterns throughout the day
- Identify low-energy periods
- Correlate energy with nutrition and sleep
- Suggest meal timing adjustments

### 🤒 Symptom Tracking

**Fields:**
- Symptom type (headache, nausea, dizziness, fatigue, etc.)
- Severity (1-10 rating)
- Duration (e.g., "30min", "2h")
- Possible triggers (text)

**What the AI can do:**
- Identify symptom frequency
- Find potential food triggers
- Correlate with sleep quality
- Suggest preventive measures

### 💊 Medication Tracking

**Fields:**
- Medication name
- Dosage
- Time taken
- Taken as prescribed (yes/no)
- Side effects (text)

**What the AI can do:**
- Track adherence
- Monitor side effects
- Send reminders (if scheduled)
- Correlate effectiveness with other metrics

### 😊 Mood Tracking

**Fields:**
- Overall mood (1-10 rating)
- Emotions felt (multiselect: happy, sad, anxious, calm, stressed, etc.)
- Stress level (1-10 rating)
- Notes on influences

**What the AI can do:**
- Track mood trends
- Identify stress patterns
- Correlate mood with food, sleep, exercise
- Suggest interventions for low moods

### 😴 Sleep Quality

**Fields:**
- Sleep quality rating (1-10)
- Felt refreshed (yes/no)
- Times woken up
- Remember dreams (yes/no)
- Sleep notes

**What the AI can do:**
- Track sleep quality trends
- Correlate with nutrition and evening routines
- Identify factors affecting sleep
- Suggest sleep optimization strategies

### 💧 Water Intake

**Fields:**
- Amount in ml
- Time logged

**What the AI can do:**
- Track daily hydration
- Identify hydration patterns
- Suggest hydration goals
- Correlate with energy and health metrics

### 🏃 Exercise Tracking

**Fields:**
- Exercise type (running, walking, cycling, strength training, yoga, etc.)
- Duration in minutes
- Intensity (1-10 rating)
- Workout notes

**What the AI can do:**
- Track exercise frequency
- Monitor workout intensity
- Correlate with energy and mood
- Suggest recovery nutrition

## Commands Reference

| Command | Description |
|---------|-------------|
| `/create_tracker` | Create a new custom tracker |
| `/log_tracker` | Log an entry to an existing tracker |
| `/view_tracker` | View recent tracker data |
| `/my_trackers` | List all your active trackers |

## AI-Powered Insights

Once you have tracker data, the AI can provide powerful insights by:

### 1. Pattern Detection

The AI automatically looks for patterns in your data:

- **Low energy days**: "You've had energy below 5 on 40% of days this month"
- **Symptom triggers**: "Headaches occurred 3 times, each within 2 hours of processed foods"
- **Cycle patterns**: "Your period cycle averages 28 days"

### 2. Correlations

The AI correlates tracker data with other metrics:

- **Energy + Nutrition**: "Low energy days coincide with low protein intake"
- **Symptoms + Food**: "Nausea tends to follow dairy consumption"
- **Mood + Sleep**: "Your mood averages 3/10 after nights with poor sleep"

### 3. Predictive Insights

Based on patterns, the AI can predict and suggest:

- **Next period**: "Based on your 28-day cycle, expect your period around Feb 15th"
- **Energy dips**: "Your energy tends to drop in the afternoon - consider a protein-rich lunch"
- **Symptom prevention**: "Avoid processed foods on days 1-3 of your cycle to reduce headaches"

### 4. Actionable Recommendations

The AI provides specific, data-driven advice:

- "Your average energy is 4/10. Increase protein by 20g per day to boost energy."
- "You had headaches on 3 days this month. Common factor: less than 6 hours sleep. Prioritize sleep."
- "Your mood improves 2 points on exercise days. Try 20min walks 3x per week."

## Example Conversations

### Energy Tracking

**User**: "I'm always tired"
**AI**: Checks Energy tracker → "Looking at your energy data, you've averaged 4/10 this week with 5 days below 5. I also checked your food logs - you're averaging 45g protein/day, well below the recommended 80g for your weight. Try adding protein to breakfast."

### Period Tracking

**User**: "When's my next period?"
**AI**: Checks Period tracker → "Based on your last 3 cycles (averaging 28 days), your next period is likely around January 25th. I recommend increasing iron-rich foods (spinach, red meat) starting January 22nd to prepare."

### Symptom Tracking

**User**: "I have another headache"
**AI**: Logs to Symptoms tracker → "This is your 4th headache this month. Pattern detected: Each occurred 2-4 hours after eating processed foods or skipping meals. Try eating regularly spaced meals with whole foods to prevent future headaches."

## Tips for Effective Tracking

1. **Be Consistent**: Log data daily for best pattern detection
2. **Add Notes**: Include context that might be relevant (stress, lack of sleep, etc.)
3. **Start Simple**: Begin with 1-2 trackers, add more as you get comfortable
4. **Ask Questions**: The AI is most powerful when you ask it to analyze your data
5. **Trust the Process**: Patterns emerge over time (aim for 2-4 weeks of data)

## Privacy & Data

- All tracker data is stored securely in your database
- Only you and the AI have access to your data
- You can delete trackers and entries at any time
- Data is never shared with third parties

## Frequently Asked Questions

**Q: How many trackers can I create?**
A: Unlimited! Create as many as you need to track your health comprehensively.

**Q: Can I edit past entries?**
A: Not yet - this feature is coming soon. For now, you can add a note explaining corrections.

**Q: Can I export my tracker data?**
A: This feature is planned for a future update.

**Q: Can I share tracker templates with others?**
A: Not yet, but shareable templates are coming in a future update.

**Q: What if I forget to log data?**
A: If you set up a schedule when creating a tracker, you'll get automatic reminders. You can also ask the AI "Did I log my energy today?" and it will remind you.

**Q: Can I track multiple things in one tracker?**
A: Each tracker can have multiple fields! For example, your Period tracker includes flow, symptoms, mood, and pain all in one tracker.

## Advanced: Creating Custom Trackers

Custom tracker creation (beyond templates) is coming soon! This will let you:

- Define your own field types
- Create validation rules
- Set custom schedules
- Share templates with the community

Stay tuned for updates!

## Need Help?

- Use `/help` to see all commands
- Ask the AI: "How do I use trackers?"
- Report issues or suggest features via GitHub

---

**Pro Tip**: The AI learns from your tracking patterns. The more consistently you track, the better and more personalized the insights become! 🎯
