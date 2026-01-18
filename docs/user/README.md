# Health Agent User Guide

Complete guide for using the Health Agent Telegram bot.

---

## Getting Started

### 1. Find the Bot

Search for your Health Agent bot in Telegram (bot name provided by admin)

### 2. Start Conversation

Send `/start` to begin

### 3. Complete Onboarding

Answer questions about:
- Your age
- Height and weight
- Health goals
- Dietary preferences

### 4. Start Tracking!

Begin logging food, setting reminders, and tracking progress

---

## Food Tracking

### Logging Food with Photos

**Method 1**: Send a photo
1. Take a photo of your meal
2. Send it to the bot
3. AI analyzes and estimates calories/macros
4. Review and confirm

**Example**:
```
You: [Photo of chicken and rice]
Bot: I analyzed your meal:
     - 200g chicken breast (220 cal, 46g protein)
     - 150g brown rice (165 cal, 3.5g protein, 35g carbs)

     Total: 385 calories
     Protein: 49.5g | Carbs: 35g | Fat: 4g

     Looks good? (Confirm/Correct)
```

---

### Logging Food with Text

**Method 2**: Describe what you ate
1. Type what you ate
2. AI parses and estimates nutrition
3. Saved to your food diary

**Examples**:
- "I ate 200g chicken breast and 150g rice"
- "Had a large burger with fries for lunch"
- "Breakfast: oatmeal with banana and peanut butter"

---

### Viewing Food History

**Commands**:
- "What did I eat today?"
- "Show me yesterday's food log"
- "How many calories did I eat this week?"

**Example**:
```
You: What did I eat today?
Bot: Today's food (Jan 18, 2025):

     Breakfast (8:30 AM): 350 calories
     - Oatmeal with banana

     Lunch (12:45 PM): 450 calories
     - Grilled chicken salad

     Dinner (6:30 PM): 520 calories
     - Salmon with quinoa

     Total: 1,320 calories
     Protein: 85g | Carbs: 120g | Fat: 35g
```

---

### Correcting Food Entries

Made a mistake? Just tell the bot:

**Examples**:
- "Actually that was 200g of chicken, not 150g"
- "Correction: I had 2 slices of pizza, not 1"
- "The rice portion was larger, about 200g"

---

## Reminders

### Creating Reminders

**Daily Reminders**:
- "Remind me to take vitamins at 9am every day"
- "Set a daily reminder to drink water at 10am"

**One-Time Reminders**:
- "Remind me to weigh myself tomorrow at 7am"
- "Set a reminder to meal prep on Sunday at 2pm"

---

### Managing Reminders

**View Reminders**:
- "Show my reminders"
- "What reminders do I have?"

**Delete Reminders**:
- "Delete my vitamin reminder"
- "Remove the 9am reminder"

**Example**:
```
You: Show my reminders
Bot: Your active reminders:

     1. Take vitamins
        Daily at 9:00 AM

     2. Drink water
        Daily at 10:00 AM, 2:00 PM, 6:00 PM

     3. Weigh yourself
        Tomorrow at 7:00 AM (one-time)
```

---

## Gamification

### XP and Levels

Earn XP for healthy activities:
- Food logging (text): **50 XP**
- Food logging (photo): **75 XP**
- Reminder completion: **25 XP**
- Challenge completion: **100-500 XP**

**Streak Bonus**: +5 XP per day (max 100 XP)

---

### Levels and Tiers

**Level Formula**: XP needed = level² × 100

| Tier | Levels | XP Range |
|------|--------|----------|
| Bronze | 1-10 | 0 - 10,000 |
| Silver | 11-25 | 10,000 - 62,500 |
| Gold | 26-50 | 62,500 - 250,000 |
| Platinum | 51+ | 250,000+ |

**Check your level**:
- "What's my level?"
- "How much XP do I have?"

---

### Streaks

Track consecutive days of activity:
- **Daily logging streak**: Log food every day
- **Reminder completion streak**: Complete reminders
- **Overall streak**: Any bot interaction

**Check streaks**:
- "What's my streak?"
- "Show me my current streaks"

**Example**:
```
You: What's my streak?
Bot: Your streaks 🔥:

     Daily logging: 7 days
     Reminder completion: 12 days
     Overall activity: 15 days

     Best ever: 23 days

     Keep it up! +35 bonus XP today!
```

---

### Achievements

Unlock achievements for milestones:
- **First Steps**: Log your first meal
- **Week Warrior**: 7-day logging streak
- **Centurion**: Log 100 meals
- **Level 5**: Reach level 5
- **Protein Pro**: Average >100g protein for a week

**View achievements**:
- "Show my achievements"
- "What achievements do I have?"

---

### Challenges

Join challenges for extra XP and motivation:

**Browse challenges**:
- "What challenges are available?"
- "Show me easy challenges"

**Start a challenge**:
- "I want to do the 30-day protein challenge"
- "Start the daily water intake challenge"

**Example challenges**:
- **30-Day Protein**: Hit protein goal 30 days in a row (500 XP)
- **Hydration Hero**: Log 8 glasses of water daily for 7 days (200 XP)
- **Consistent Logger**: Log all meals for 14 days (300 XP)

---

## Custom Tracking

### Creating Custom Trackers

Want to track something specific?

**Examples**:
- "I want to track my water intake"
- "Can we track my mood daily?"
- "Let's track my sleep quality"

Bot creates a custom tracker for you!

---

### Logging Custom Data

Once created, log naturally:

**Water Intake**:
- "I drank 8 glasses of water today"
- "Log 2 liters of water"

**Mood**:
- "My mood is happy today"
- "Feeling stressed - mood rating 5/10"

**Sleep**:
- "I slept 7.5 hours, quality was 8/10"
- "Sleep: 6 hours, quality poor"

---

## Profile and Preferences

### Updating Your Profile

**Demographics**:
- "I'm 32 years old"
- "My current weight is 76kg"
- "Update my height to 175cm"

**Goals**:
- "My goal is to lose 5kg"
- "I want to build muscle"
- "Target: 2000 calories per day"

---

### Communication Preferences

**Style**:
- "I prefer casual communication"
- "Use formal language please"
- "Send me lots of emojis"

**Timing**:
- "Send reminders at 9am"
- "Don't send notifications at night"

---

## Privacy and Data

### What Data is Stored?

- Food entries (photos and text)
- Conversation history (last 1000 messages)
- Profile information (age, weight, goals)
- Gamification data (XP, streaks, achievements)
- Reminders and custom tracking data

### Where is Data Stored?

- **Photos**: Your server (not shared)
- **Text data**: PostgreSQL database (encrypted)
- **Profile**: Markdown files (human-readable)
- **Memories**: Semantic memory system (for context)

### Data Access

- Only you can access your data
- Telegram ID whitelist authentication
- No data sold to third parties
- No external sharing

### Data Deletion

**Delete your account**:
- "Delete my account and all data"
- All data removed (cascade deletion)

**Delete specific data**:
- "Delete my food log from yesterday"
- "Remove my photo from last week"

---

## Tips and Tricks

### Best Practices

1. **Be specific**: "200g chicken breast" better than "some chicken"
2. **Use photos**: More accurate than text (75 XP vs 50 XP)
3. **Log immediately**: Don't forget details later
4. **Check summaries**: Review daily/weekly totals
5. **Set reminders**: Stay consistent
6. **Join challenges**: Extra motivation and XP

---

### Common Questions

**Q: How accurate is the calorie estimation?**
A: Vision AI uses 3-agent consensus + USDA verification. Typically within 15% of actual calories.

**Q: Can I edit a food entry?**
A: Yes! Just say "Actually that was 200g, not 150g"

**Q: What happens if I miss a day?**
A: Your streak resets, but you don't lose XP or levels.

**Q: Can I track exercise?**
A: Yes! Create a custom tracker: "I want to track my workouts"

**Q: How do I see my progress over time?**
A: Ask: "Show me my weekly summary" or "What's my protein trend?"

---

## Bot Commands Reference

### Core Commands

- `/start` - Start the bot and create account
- `/help` - Show help message
- `/settings` - View and update settings
- `/clear` - Clear conversation history
- `/stats` - Show gamification stats

---

### Conversation Starters

**Food Tracking**:
- [Send photo of food]
- "I ate [food description]"
- "What did I eat today?"

**Reminders**:
- "Remind me to [action] at [time]"
- "Show my reminders"
- "Delete [reminder name]"

**Gamification**:
- "What's my level?"
- "Show my streaks"
- "What achievements do I have?"
- "What challenges are available?"

**Profile**:
- "Update my [field] to [value]"
- "What's my current weight?"
- "Show my profile"

---

## Support

### Getting Help

1. Type "help" or ask a question
2. Bot will guide you through features
3. For technical issues, contact admin

### Reporting Bugs

If something isn't working:
1. Describe what you tried
2. Include error message (if any)
3. Mention when it happened
4. Screenshot if helpful

---

## Related Documentation

For Developers:
- [Development Guide](../development/) - Setting up development environment
- [API Reference](../api/) - API documentation
- [Architecture](../architecture/) - System design

## Revision History

- 2025-01-18: Initial user guide created for Phase 3.7
