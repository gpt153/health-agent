# AI Health Coach - Onboarding Strategy

**Version:** 1.0
**Date:** 2025-12-17
**Status:** Research-backed strategy for dual-path onboarding

---

## Executive Summary

This document outlines an onboarding strategy for the AI Health Coach Telegram bot that balances speed with comprehensiveness. Based on industry research and conversational UI best practices, we implement a **dual-path progressive disclosure system** that serves users in a hurry while offering deep exploration for engaged users.

### Key Statistics (Industry Research)
- **77% of users abandon apps within 3 days** of installation
- **Day 1 retention:** 22.6% (Android), 25.6% (iOS)
- **Critical window:** First 30 seconds determines if user stays
- **Progressive onboarding increases retention by 50%** vs. static tutorials

---

## Research Foundation

### Best Practices Applied

#### 1. Progressive Disclosure
**Source:** [Agentic Design Patterns - Progressive Disclosure](https://agentic-design.ai/patterns/ui-ux-patterns/progressive-disclosure-patterns)

- Reveal features contextually when user needs them
- Don't front-load all capabilities at once
- Teach through interaction, not explanation

#### 2. Quick Time-to-Value
**Source:** [VWO Mobile Onboarding Guide](https://vwo.com/blog/mobile-app-onboarding-guide/), [UXCam Onboarding Examples](https://uxcam.com/blog/10-apps-with-great-user-onboarding/)

- Show value in first 30 seconds
- Allow exploration before sign-up friction
- Get to "aha moment" fast

#### 3. Conversational Interfaces Rock at Onboarding
**Source:** [Why conversational interfaces rock at onboarding](https://medium.com/@tomhewitson/why-conversational-interfaces-rock-at-onboarding-2db1e3352faa)

- Natural dialogue reduces cognitive load
- Questions feel like conversation, not forms
- Can adapt based on user responses in real-time

#### 4. Minimize Signup Friction
**Source:** [Userpilot App Onboarding Best Practices](https://userpilot.com/blog/app-onboarding-best-practices/)

- Reduce form fields to bare minimum
- Allow partial exploration before full commitment
- Progressive profiling over upfront data collection

#### 5. Interactive > Static
**Source:** [Plotline Mobile App Onboarding](https://www.plotline.so/blog/mobile-app-onboarding-examples)

- Learning by doing is 3x more effective than reading
- Tooltips > lengthy tutorials
- Show, don't tell

---

## Current State Analysis

### Existing Onboarding (Status Quo)

**Current Flow:**
1. User sends `/start`
2. Bot checks activation status
3. If activated: Static welcome message with 3 bullet points
4. Lists 3 commands
5. User is on their own

**Problems:**
- ❌ Doesn't show capabilities, only tells
- ❌ No personalization questions
- ❌ No value demonstration
- ❌ No path for different user types
- ❌ No "aha moment" trigger
- ❌ Commands listed but not explained

### Available Features (Often Undiscovered)

**High-Value Features:**
1. 📸 Food photo analysis (macros/calories)
2. 🎤 Voice note transcription
3. 📊 Custom tracking (sleep, workouts, mood)
4. ⏰ Smart reminders
5. 💬 Personalized coaching & pep talks
6. 🧠 Learning your patterns over time
7. 🔍 Transparency view (see what bot knows)
8. ⚙️ Adaptive personality (tone, brevity, style)
9. 🌍 Timezone-aware responses
10. 📝 Daily summaries
11. 🤝 Proactive check-ins

**Power Features:**
- Visual pattern learning (your protein shake, your meal prep)
- Direct answer extraction from history
- Self-extending capabilities (dynamic tools)

---

## Proposed Solution: Dual-Path Progressive Onboarding

### Core Principle: Ask, Don't Assume

Instead of:
> "Here's what I can do. Figure it out."

Do this:
> "What brings you here today? Let me show you how I can help."

---

## Implementation: Three-Tier System

### Tier 1: Welcome Gate (0-15 seconds)
**Goal:** Activate account + Quick value choice

```
👋 Welcome to AI Health Coach!

⚠️ Quick setup first - send your invite code.
Example: health-starter-2024

Don't have one? Contact @admin for access.
```

**After activation:**

```
✅ You're in! Let's get you started.

I'm your AI health coach - I track food, workouts, sleep,
give pep talks, and learn your habits over time.

How should we start?

[Quick Start] - Jump right in (30 sec)
[Show Me Around] - Full tour (2 min)
[Just Chat] - I'll learn as we go
```

**User choice → Branches to Tier 2**

---

### Tier 2A: Quick Start Path (15-45 seconds)
**For users in a hurry**

**Step 1: Set Timezone**
```
🌍 Quick setup: What's your timezone?

📍 Share your location (tap 📎 → Location)
   OR
⌨️ Type it: "America/New_York", "Europe/London", etc.

Why? So reminders hit at the right time!
```

**Step 2: Pick Your Focus**
```
🎯 What's your main goal right now?

1️⃣ Track nutrition (food photos → instant macros)
2️⃣ Build workout habit (custom tracking + reminders)
3️⃣ Improve sleep (log quality, spot patterns)
4️⃣ General health coaching (I'll adapt to you)

Reply with a number or just tell me what you want.
```

**Step 3: Immediate Action**
```
[If they pick nutrition:]

🍽️ Perfect! Let's try it right now.

Send me a photo of your last meal or snack.
I'll analyze it and show you calories + macros instantly.

📸 Try it → (waiting for photo)
```

```
[If they pick workouts:]

💪 Nice! Let's log your first workout.

Tell me what you did today. Examples:
• "Just did 30 min cardio"
• "Leg day: squats, deadlifts, lunges"
• "Rest day"

I'll remember it and can remind you tomorrow!
```

**Step 4: Quick Discovery**
```
🎉 Great! That's the core flow.

⚡ Quick tips:
• Send photos anytime → I'll analyze food
• Voice notes work too (I transcribe them)
• Just chat normally - I'll suggest features as you need them

Want to see everything I can do?
Reply "show features" or just start chatting!
```

**Total time: 30-45 seconds**
**Exit: User has experienced value + knows core action**

---

### Tier 2B: Full Tour Path (45-120 seconds)
**For engaged users who want comprehensive view**

**Step 1: Profile Setup**
```
🌍 First, your timezone:
📍 Share location or type it (e.g., "Asia/Tokyo")
```

```
👤 Tell me about yourself (optional, but helps me personalize):

• Your name?
• Age?
• Current goal? (lose weight, build muscle, maintain health)

You can skip any question - just say "skip" or "done"
```

**Step 2: Feature Showcase (Interactive)**
```
🎬 Here's what I can do. Let's try them!

1️⃣ 📸 FOOD TRACKING
Send me ANY food photo → instant calories + macros
No logging, no searching databases - just snap and send.

→ Try it now: Send me a photo from your gallery!
```

[After they send photo]
```
✨ See? That took 2 seconds.
I analyzed: [shows results]

I'll remember this and can tell you:
• "How many calories today?"
• "Did I hit my protein goal?"
• "What did I eat yesterday?"

Let's continue the tour...
```

**Step 3: Voice & Conversation**
```
2️⃣ 🎤 VOICE NOTES
Driving? At the gym? Just hold and talk.

I'll transcribe and respond to:
• "Log today's workout"
• "How am I doing this week?"
• "Give me motivation for leg day"

→ Try it: Send me a voice note right now!
```

**Step 4: Custom Tracking**
```
3️⃣ 📊 TRACK ANYTHING
Not just food - I can track whatever matters to you:

Examples:
• Sleep quality (1-10 scale)
• Energy levels throughout day
• Workout types & duration
• Mood patterns
• Water intake

→ Just tell me: "Track my sleep quality"
```

**Step 5: Smart Reminders**
```
4️⃣ ⏰ SMART REMINDERS
Never forget your habits.

Try saying:
• "Remind me to log food at 9 PM"
• "Daily workout check-in at 6 AM"
• "Weekly progress review on Sundays"

→ Want a reminder? Tell me when!
```

**Step 6: Personality Customization**
```
5️⃣ 🎭 ADAPTIVE PERSONALITY
I match YOUR style.

Preferences you can set:
• Tone: Friendly / Formal / Casual
• Brevity: Brief / Detailed / Medium
• Coaching: Supportive / Analytical / Tough Love
• Humor: On / Off

→ Try saying: "Be more brief" or "Use casual tone"
```

**Step 7: Learning & Memory**
```
6️⃣ 🧠 I LEARN ABOUT YOU
Over time, I'll remember:
• Your protein shake looks like THIS
• You train legs on Mondays
• You prefer evening workouts
• You hit a wall around 3 PM

Check what I know anytime: /transparency

→ This happens automatically - no work from you!
```

**Step 8: Tour Complete**
```
🎉 Tour complete! You're ready.

📝 Quick reference:
/transparency - See what I know about you
/settings - Change my personality
/help - Full command list

🚀 Start by:
• Sending a food photo
• Telling me your goal
• Or just chat - I'll guide you!

What would you like to do first?
```

**Total time: 90-120 seconds**
**Exit: User understands full capabilities + has tried 1-2 features**

---

### Tier 2C: Just Chat Path (Contextual Discovery)
**For users who want organic exploration**

**Immediate Response:**
```
💬 Perfect! I learn best through conversation anyway.

Tell me what brings you here - a goal, a question,
or just "I want to get healthier" works too.

I'll introduce features naturally as you need them.
```

**Then: Contextual Feature Discovery**

When user mentions food:
```
→ Trigger: "I ate chicken and rice for lunch"

Response: "Nice! 👍

By the way - if you send me photos of your meals,
I can give you instant calorie + macro breakdowns.
No manual logging. Want to try it?"
```

When user mentions workouts:
```
→ Trigger: "I need to hit the gym today"

Response: "Let's do it! 💪

I can track your workouts and even remind you on training days.
Want me to log today's session when you're done?"
```

When user asks about history:
```
→ Trigger: "What did I eat yesterday?"

Response: "Let me check your food log... [shows data]

I automatically track all your photos. You can always ask:
• 'How many calories this week?'
• 'Did I hit protein goal today?'
• 'Show my workout history'

What else would you like to know?"
```

**Progressive Unlocking:**
- Features revealed when relevant
- User controls pace of discovery
- Natural conversation flow maintained

---

## Tier 3: Ongoing Education (Days 2-30)
**Goal:** Prevent abandonment through continued value delivery

### Day 2: First Check-In
```
👋 Day 2 check-in!

How's it going so far? I've noticed:
[Shows 1-2 data points from Day 1]

💡 Did you know I can also [relevant unused feature]?
```

### Day 7: Feature Highlight
```
🎯 Week 1 complete! You've logged [X] meals and [Y] workouts.

🆕 Feature you haven't tried: [Personalized suggestion]

Example: "I can give you a weekly summary every Sunday -
want me to set that up?"
```

### Day 14: Advanced Features
```
🔥 Two weeks in! You're building a habit.

🚀 Ready for power features?
• I can learn YOUR specific foods (your protein shake, your meal prep)
• Set multiple daily reminders for different goals
• Track custom metrics beyond food/workouts

Interested? Just ask!
```

### Day 30: Full Mastery
```
🎉 30 days! You're a pro now.

📊 Your stats: [Summary]

✨ Advanced tips:
• Use voice notes for quick logging
• Ask me to spot patterns: "When do I eat most?"
• Request pep talks: "Motivate me for leg day"

Keep going - I'm learning you better every day! 💪
```

---

## Decision Tree Flow

```
/start
  ↓
Invite Code → Activation
  ↓
Path Selection:
  ├─ Quick Start (30-45s)
  │    ├─ Timezone
  │    ├─ Pick Focus
  │    ├─ Try One Feature
  │    └─ Exit to Normal Use
  │
  ├─ Full Tour (90-120s)
  │    ├─ Profile Setup
  │    ├─ Food Demo
  │    ├─ Voice Demo
  │    ├─ Tracking Demo
  │    ├─ Reminders Demo
  │    ├─ Personality Demo
  │    ├─ Learning Explanation
  │    └─ Exit to Normal Use
  │
  └─ Just Chat (Organic)
       ├─ Immediate Conversation
       ├─ Contextual Feature Reveals
       └─ Progressive Discovery
```

---

## Key Interaction Patterns

### Pattern 1: Show, Don't Tell
**Bad:**
> "I can analyze food photos to calculate calories and macros."

**Good:**
> "📸 Send me a food photo - I'll show you calories + macros in seconds. Try it!"

### Pattern 2: Action → Explanation
**Bad:**
> "Here are 10 things I can do: [list]"

**Good:**
> [User sends photo] → "✨ Found 650 cal! I can do this for ANY meal. Just send photos anytime."

### Pattern 3: Contextual Upselling
**Bad:**
> "You can track sleep, workouts, mood, water intake..."

**Good:**
> [User mentions being tired] → "Sounds rough! I can track your sleep quality if you want - just tell me '1-10' each morning. Might spot patterns!"

### Pattern 4: Permission-Based Features
**Bad:**
> [Sends daily summary without asking]

**Good:**
> "I can send you a daily summary at 9 PM with your stats. Want me to?"
> User: "Yes"
> "✅ Set! You'll get your first one tonight."

---

## Measurement & Optimization

### Key Metrics to Track

**Onboarding Funnel:**
1. **Activation Rate:** % who complete invite code
2. **Path Selection:** Quick (X%) vs Full (Y%) vs Chat (Z%)
3. **Feature Trial Rate:** % who try suggested feature in onboarding
4. **Time to First Value:** Seconds until first successful action
5. **Day 1 Retention:** % who return next day
6. **Day 7 Retention:** % still active after week
7. **Feature Discovery Rate:** % who discover each feature by Day 30

**Per-Path Metrics:**
- Quick Start: Completion rate (target: 85%+)
- Full Tour: Drop-off point analysis
- Just Chat: Feature discovery over time

### Success Criteria

**Week 1:**
- ✅ 70%+ activation to first action
- ✅ 50%+ Day 1 retention
- ✅ Average time-to-value < 45 seconds

**Week 4:**
- ✅ 35%+ Day 7 retention (vs 22.6% industry avg)
- ✅ Users discover average of 4+ features
- ✅ 60%+ engagement with contextual prompts

### A/B Testing Opportunities

1. **Path Selection Copy:**
   - Version A: "Quick Start / Show Me Around / Just Chat"
   - Version B: "Jump In / Full Tour / Learn as I Go"

2. **Demo Order (Full Tour):**
   - Version A: Food → Voice → Tracking → Reminders
   - Version B: Tracking → Food → Reminders → Voice

3. **Tone Testing:**
   - Version A: Emoji-heavy, casual
   - Version B: Professional, minimal emoji

---

## Implementation Priorities

### Phase 1: Foundation (Week 1)
- [ ] Build path selection interface
- [ ] Implement Quick Start flow
- [ ] Add timezone setup
- [ ] Create focus selection (nutrition/workout/sleep/general)

### Phase 2: Comprehensive (Week 2)
- [ ] Build Full Tour flow with interactive demos
- [ ] Implement contextual feature reveals for Just Chat
- [ ] Add progress tracking for tour completion
- [ ] Create welcome message branching logic

### Phase 3: Engagement (Week 3)
- [ ] Day 2, 7, 14, 30 check-in messages
- [ ] Feature highlight system
- [ ] Usage analytics integration
- [ ] A/B testing framework

### Phase 4: Optimization (Week 4+)
- [ ] Analyze drop-off points
- [ ] Refine copy based on data
- [ ] Test alternative flows
- [ ] Personalization based on user type

---

## Copy Guidelines

### Tone Principles
1. **Conversational, not corporate**
   - ✅ "Let's try it!"
   - ❌ "Please proceed to initiate feature demonstration"

2. **Action-oriented**
   - ✅ "Send me a photo right now"
   - ❌ "You have the ability to send photos"

3. **Value-first**
   - ✅ "Get instant macros from any food photo"
   - ❌ "Our advanced computer vision algorithm..."

4. **Emoji as punctuation, not decoration**
   - ✅ "🎉 You did it!" (celebration)
   - ❌ "🤖🔥💯🚀✨" (emoji soup)

5. **Progressive complexity**
   - Start simple: "I track food"
   - Build up: "I track food and learn your habits"
   - Full detail: "I track food, learn patterns, and can remind you about goals"

### Message Length
- **Initial welcome:** 3-4 lines max
- **Feature explanations:** 1-2 lines + example
- **Options/choices:** 3-4 max (cognitive load)
- **Confirmations:** Single line

### Call-to-Action Format
```
[Emoji] WHAT IT DOES
Brief explanation (1 line)

→ ACTION: Specific thing to do now

[Button or next step]
```

---

## Technical Implementation Notes

### Database Schema Changes Needed

```sql
-- Track onboarding progress
CREATE TABLE user_onboarding_state (
    user_id VARCHAR(255) PRIMARY KEY REFERENCES users(telegram_id),
    onboarding_path VARCHAR(20), -- 'quick', 'full', 'chat'
    current_step VARCHAR(50),
    completed_steps JSONB,
    features_discovered JSONB,
    onboarding_started_at TIMESTAMP,
    onboarding_completed_at TIMESTAMP
);

-- Track feature discovery
CREATE TABLE feature_discovery_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) REFERENCES users(telegram_id),
    feature_name VARCHAR(100),
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    discovery_method VARCHAR(50) -- 'onboarding', 'contextual', 'manual'
);
```

### Bot Handler Changes

```python
# New handlers needed:
- handle_onboarding_path_selection()
- handle_quick_start_flow()
- handle_full_tour_flow()
- handle_just_chat_contextual()
- trigger_day_n_checkin()
- track_feature_discovery()
```

### State Machine

```python
class OnboardingState(Enum):
    NOT_STARTED = "not_started"
    PATH_SELECTION = "path_selection"
    QUICK_TIMEZONE = "quick_timezone"
    QUICK_FOCUS = "quick_focus"
    QUICK_DEMO = "quick_demo"
    FULL_PROFILE = "full_profile"
    FULL_FOOD_DEMO = "full_food_demo"
    FULL_VOICE_DEMO = "full_voice_demo"
    # ... etc
    COMPLETED = "completed"
```

---

## Edge Cases & Error Handling

### User Abandons Mid-Onboarding
**Scenario:** User picks "Full Tour" but stops responding at step 3

**Solution:**
- Save progress in database
- After 15 minutes of inactivity:
  ```
  👋 Still there?

  You were on step 3/7 of the tour. Want to:

  1️⃣ Continue where we left off
  2️⃣ Skip to the end
  3️⃣ Just start using it normally
  ```

### User Says "Skip" or "I don't care"
**Solution:**
- Respect the skip
- Mark feature as "dismissed"
- Don't re-suggest for 7 days
- Still allow organic discovery

### User Sends Message During Tour
**Scenario:** User asks question mid-tour

**Solution:**
- Answer the question
- Then: "Want to continue the tour, or explore on your own?"
- Flexibility > rigid flow

### Returning User Sees Onboarding Again
**Solution:**
- Check `onboarding_completed_at` in database
- If completed: Show standard welcome
- If started but not completed: Offer resume

---

## References & Sources

### Industry Research
1. [App Onboarding Guide - Top 10 Onboarding Flow Examples 2025](https://uxcam.com/blog/10-apps-with-great-user-onboarding/)
2. [Best Mobile App Onboarding Examples in 2025](https://www.plotline.so/blog/mobile-app-onboarding-examples)
3. [The Ultimate Mobile App Onboarding Guide (2026) | VWO](https://vwo.com/blog/mobile-app-onboarding-guide/)
4. [12 Web and Mobile App Onboarding Best Practices](https://userpilot.com/blog/app-onboarding-best-practices/)
5. [Mobile Onboarding UX: 11 Best Practices for Retention (2025)](https://www.designstudiouiux.com/blog/mobile-app-onboarding-best-practices/)
6. [Master Mobile App Onboarding: Best Practices & Examples](https://www.netguru.com/blog/mobile-app-onboarding)
7. [Unveiling 2025's Best Mobile Onboarding Practices for Apps](https://webisoft.com/articles/mobile-onboarding-best-practices/)

### Conversational UI Research
8. [Progressive Disclosure UI Patterns (PDP) - Agentic Design](https://agentic-design.ai/patterns/ui-ux-patterns/progressive-disclosure-patterns)
9. [New Users Need Support with Generative-AI Tools - NN/G](https://www.nngroup.com/articles/new-AI-users-onboarding/)
10. [Why conversational interfaces rock at onboarding | Tom Hewitson](https://medium.com/@tomhewitson/why-conversational-interfaces-rock-at-onboarding-2db1e3352faa)
11. [Conversational UI: 6 Best Practices](https://research.aimultiple.com/conversational-ui/)

---

## Appendix: Competitor Analysis

### Duolingo (Onboarding Champion)
**What they do well:**
- Immediate language selection (personalization)
- 1-minute demo lesson BEFORE signup
- Gamification from day 1
- Daily goal selection

**Applicable to us:**
- Immediate goal selection (nutrition/workout/sleep)
- Demo feature BEFORE asking personal info
- Streak tracking for motivation

### MyFitnessPal
**What they do well:**
- Clear value prop: "Track to lose weight"
- Barcode scanning demo
- Social proof (millions of users)

**Applicable to us:**
- Emphasize "photo = instant macros"
- Could add testimonials

**What they do poorly:**
- Lengthy signup form BEFORE value
- Tutorial screens instead of doing
- Don't show personalization options

**How we're better:**
- Try features first, profile later
- Interactive demos, not static screens
- Personality customization from day 1

### Headspace (Meditation App)
**What they do well:**
- 1-minute sample meditation immediately
- Asks about user's meditation experience
- Friendly, conversational tone
- Minimal friction to first value

**Applicable to us:**
- Conversational tone (already have)
- Ask experience level (new to tracking? experienced athlete?)
- Sample the value immediately

---

## Final Recommendations

### DO:
✅ Offer choice (quick/full/chat)
✅ Show value in < 30 seconds
✅ Interactive demos over explanations
✅ Progressive disclosure of features
✅ Respect user's pace
✅ Track and optimize based on data

### DON'T:
❌ Force all users down same path
❌ Explain all features upfront
❌ Use static tutorial screens
❌ Ask for profile info before showing value
❌ Make onboarding feel like homework
❌ Lock features behind tutorial completion

### Core Philosophy:
> **"Get the user to their first win in 30 seconds, then progressively reveal the magic."**

---

**Next Steps:** Review with team → Prioritize Phase 1 implementation → Build & test Quick Start flow → Measure & iterate

**Questions?** See Implementation Priorities section for development roadmap.
