# System Sequence Diagrams

This document illustrates key interaction flows in the Health Agent system through sequence diagrams. Each diagram shows how components collaborate to fulfill user requests.

---

## 1. Food Photo Analysis Flow

This diagram shows the complete flow when a user sends a food photo for nutrition analysis.

```mermaid
sequenceDiagram
    participant U as User
    participant TB as Telegram Bot
    participant BH as Bot Handler
    participant A as PydanticAI Agent
    participant V as Vision AI<br/>(Multi-Agent)
    participant N as USDA Nutrition<br/>Service
    participant DB as PostgreSQL
    participant G as Gamification<br/>Service
    participant M as Mem0<br/>Memory

    U->>TB: Send food photo
    TB->>BH: photo_message event
    BH->>BH: Save photo to storage
    BH->>BH: Build conversation history
    BH->>A: "Analyze this food photo"<br/>[photo_path, conversation_history]

    Note over A: Agent decides to call<br/>analyze_food_photo tool

    A->>V: analyze_food_photo(photo_path)

    %% Multi-agent consensus
    Note over V: Parallel execution of 3 agents
    par Conservative Agent
        V->>V: Analyze (low estimate)
    and Moderate Agent
        V->>V: Analyze (balanced)
    and Optimistic Agent
        V->>V: Analyze (high estimate)
    end

    V->>V: Moderator synthesizes estimates
    V->>N: verify_with_usda(food_items)
    N-->>V: USDA nutrition data
    V->>V: Build consensus with USDA verification
    V-->>A: {foods, calories, protein, carbs, fat,<br/>confidence, reasoning}

    Note over A: Agent decides to call<br/>save_food_entry tool

    A->>DB: save_food_entry(user_id, foods, nutrition)
    DB->>DB: INSERT INTO food_entries
    DB-->>A: Entry saved (UUID)

    Note over DB,G: Database trigger fires

    DB->>G: food_entry_created event
    G->>G: Calculate XP (food logging + accuracy)
    G->>G: Check/update streak
    G->>DB: UPDATE user_xp SET xp = xp + 50
    G->>DB: UPDATE user_streaks SET current = 7
    G-->>A: {xp_gained: 50, streak: 7, level: 3}

    A->>M: add_memory(conversation)
    M->>M: Extract: "User ate chicken and rice"
    M->>DB: INSERT INTO memories (with embedding)
    M-->>A: Memory saved

    A-->>BH: Response: "Logged 450 calories, 30g protein...<br/>+50 XP! 7-day streak 🔥"
    BH->>BH: Format for Telegram (Markdown)
    BH-->>TB: reply_text(formatted_response)
    TB-->>U: Display nutrition analysis + XP notification
```

**Key Points**:
- Multi-agent consensus runs in parallel (conservative, moderate, optimistic)
- USDA verification adds ground-truth data
- Database trigger automatically awards XP and updates streaks
- Mem0 extracts important facts for long-term memory
- Total flow time: ~5 seconds (vision AI is the bottleneck)

---

## 2. Chat Message Processing Flow

This diagram shows how a simple text message is processed through the agent system.

```mermaid
sequenceDiagram
    participant U as User
    participant TB as Telegram Bot
    participant BH as Bot Handler
    participant MM as Memory Manager
    participant M0 as Mem0 Memory
    participant A as PydanticAI Agent
    participant DB as PostgreSQL

    U->>TB: "What did I eat yesterday?"
    TB->>BH: text_message event

    %% Context gathering
    BH->>MM: read_profile(user_id)
    MM-->>BH: profile.md content
    BH->>MM: read_preferences(user_id)
    MM-->>BH: preferences.md content

    BH->>M0: search_memories(query="yesterday food")
    M0->>M0: Generate query embedding
    M0->>DB: Vector similarity search
    DB-->>M0: Top 5 relevant memories
    M0-->>BH: ["User had salmon yesterday", ...]

    BH->>DB: get_conversation_history(user_id, limit=20)
    DB-->>BH: Last 20 messages

    BH->>BH: Build agent context:<br/>- Profile + preferences<br/>- Semantic memories<br/>- Conversation history<br/>- Current message

    BH->>A: run_sync(context, deps={user_id, db, memory, ...})

    Note over A: Agent analyzes context<br/>Decides to call get_daily_food_summary tool

    A->>DB: get_daily_food_summary(user_id, date="yesterday")
    DB->>DB: SELECT * FROM food_entries<br/>WHERE user_id=X AND date=yesterday
    DB-->>A: [food_entry_1, food_entry_2, ...]

    A->>A: Generate response with summary

    A-->>BH: "Yesterday you had:<br/>- Salmon (300 cal)<br/>- Brown rice (200 cal)<br/>Total: 1850 calories, 95g protein"

    BH->>DB: save_conversation_turn(user_id, message, response)
    DB-->>BH: Saved

    BH->>M0: add_memory(conversation_turn)
    M0->>M0: Extract facts (if any)
    M0->>DB: INSERT INTO memories (if needed)
    M0-->>BH: Done

    BH-->>TB: reply_text(response)
    TB-->>U: Display food summary
```

**Key Points**:
- Context gathered from three memory tiers (Markdown, PostgreSQL, Mem0)
- Agent has full context before generating response
- Conversation history limited to 20 messages (context window management)
- Semantic memories supplement conversation history
- Total flow time: ~2 seconds

---

## 3. Reminder Scheduling and Triggering Flow

This diagram shows how reminders are created, scheduled, and triggered.

```mermaid
sequenceDiagram
    participant U as User
    participant TB as Telegram Bot
    participant A as PydanticAI Agent
    participant DB as PostgreSQL
    participant RS as Reminder<br/>Scheduler
    participant AP as APScheduler

    Note over U,AP: Reminder Creation

    U->>TB: "Remind me to take vitamins daily at 9am"
    TB->>A: Natural language message

    Note over A: Agent extracts:<br/>- Action: "take vitamins"<br/>- Schedule: "daily at 9am"<br/>- Type: recurring

    A->>A: Tool call: create_reminder()
    A->>DB: INSERT INTO reminders<br/>(user_id, message, schedule_type, time, active)
    DB-->>A: reminder_id (UUID)

    A->>RS: schedule_reminder(reminder_id)
    RS->>DB: SELECT reminder details
    DB-->>RS: {reminder_id, schedule, message}

    RS->>AP: add_job(<br/>  func=trigger_reminder,<br/>  trigger=CronTrigger(hour=9, minute=0),<br/>  args=[reminder_id]<br/>)
    AP-->>RS: Job created (job_id)

    RS->>DB: UPDATE reminders SET job_id = ?
    RS-->>A: Reminder scheduled successfully

    A-->>TB: "Daily reminder set for 9:00 AM"
    TB-->>U: Confirmation message

    Note over U,AP: Next day at 9:00 AM...

    AP->>RS: trigger_reminder(reminder_id)
    RS->>DB: SELECT reminder details
    DB-->>RS: {user_id, message, active=true}

    alt Reminder is active
        RS->>TB: send_message(user_id, "⏰ Time to take vitamins!")
        TB->>U: Reminder notification

        RS->>DB: INSERT INTO reminder_completions<br/>(reminder_id, triggered_at)
        DB-->>RS: Completion logged

        Note over DB,RS: Gamification trigger
        RS->>DB: Award XP for reminder completion
    else Reminder is inactive
        RS->>RS: Skip (user deactivated reminder)
    end
```

**Key Points**:
- Agent parses natural language into structured reminder parameters
- APScheduler handles cron-based scheduling
- Reminders persist in database (survive restarts)
- Completion tracking for gamification
- Reminders can be deactivated without deletion

---

## 4. Gamification XP Award Flow

This diagram shows how XP is awarded when a user completes health activities.

```mermaid
sequenceDiagram
    participant U as User
    participant TB as Telegram Bot
    participant A as PydanticAI Agent
    participant DB as PostgreSQL
    participant G as Gamification<br/>Service

    U->>TB: Complete health activity<br/>(food log, reminder, etc.)
    TB->>A: Activity completed event

    A->>DB: Save activity data<br/>(food_entry, reminder_completion, etc.)
    DB-->>A: Activity saved

    Note over DB,G: Database trigger OR<br/>explicit gamification call

    DB->>G: activity_completed event<br/>{user_id, activity_type}

    G->>DB: SELECT current XP, level, tier
    DB-->>G: {xp: 450, level: 3, tier: "Bronze"}

    G->>G: Calculate XP for activity:<br/>- Food log: 50 XP<br/>- Photo food log: 75 XP<br/>- Reminder completion: 25 XP<br/>- Streak bonus: +20 XP

    G->>G: Calculate new level:<br/>xp_for_next_level = level² × 100

    alt XP crosses level threshold
        G->>G: Level up! 3 → 4
        G->>G: Check tier promotion:<br/>Bronze (1-10), Silver (11-25), Gold (26-50)
        G->>DB: UPDATE user_xp<br/>SET xp=?, level=?, tier=?
        DB-->>G: Updated

        G->>G: Check for achievements:<br/>"Reach Level 5", "100 Foods Logged", etc.

        alt Achievement unlocked
            G->>DB: INSERT INTO user_achievements
            DB-->>G: Achievement saved
            G-->>A: {xp_gained: 70, level_up: true,<br/>new_level: 4, achievement: "Level Up!"}
        else No achievement
            G-->>A: {xp_gained: 70, level_up: true,<br/>new_level: 4}
        end
    else No level up
        G->>DB: UPDATE user_xp SET xp = xp + 70
        DB-->>G: Updated
        G-->>A: {xp_gained: 70, level_up: false}
    end

    A->>A: Format gamification response
    A-->>TB: "Food logged! +70 XP 🌟<br/>Level 4 reached! 🎉"
    TB-->>U: Display XP notification with celebration
```

**Key Points**:
- XP awarded based on activity type and quality
- Level calculation: `xp_required = level² × 100`
- Tier system: Bronze → Silver → Gold → Platinum
- Achievement system checks after each XP award
- Celebration animations for level ups and achievements

---

## 5. Multi-Agent Nutrition Consensus (Detailed)

This diagram zooms into the multi-agent consensus process for food photo analysis.

```mermaid
sequenceDiagram
    participant V as Vision AI<br/>Orchestrator
    participant C as Conservative<br/>Agent
    participant M as Moderate<br/>Agent
    participant O as Optimistic<br/>Agent
    participant MOD as Moderator<br/>Agent
    participant USDA as USDA FoodData<br/>Central

    Note over V: Received photo_path from agent

    V->>V: Load photo as base64

    par Conservative Analysis
        V->>C: "Analyze this food photo"<br/>[photo, conservative_prompt]
        C->>C: GPT-4o Vision analysis<br/>(bias: underestimate)
        C-->>V: {<br/>  foods: ["chicken breast 150g"],<br/>  calories: 220,<br/>  protein: 40g<br/>}
    and Moderate Analysis
        V->>M: "Analyze this food photo"<br/>[photo, moderate_prompt]
        M->>M: GPT-4o Vision analysis<br/>(bias: balanced)
        M-->>V: {<br/>  foods: ["chicken breast 200g"],<br/>  calories: 280,<br/>  protein: 50g<br/>}
    and Optimistic Analysis
        V->>O: "Analyze this food photo"<br/>[photo, optimistic_prompt]
        O->>O: GPT-4o Vision analysis<br/>(bias: hidden calories)
        O-->>V: {<br/>  foods: ["chicken breast 200g",<br/>          "cooking oil 1 tbsp"],<br/>  calories: 400,<br/>  protein: 50g<br/>}
    end

    V->>V: Collect all three estimates

    V->>MOD: "Synthesize these estimates"<br/>[conservative, moderate, optimistic]

    MOD->>USDA: search_food("chicken breast")
    USDA-->>MOD: [<br/>  {name: "Chicken, broilers, breast, raw",<br/>   calories_per_100g: 110}<br/>]

    MOD->>USDA: get_food_details(fdcId)
    USDA-->>MOD: {<br/>  calories: 110 per 100g,<br/>  protein: 23g per 100g<br/>}

    MOD->>MOD: Build consensus:<br/>- Conservative: 220 cal (150g)<br/>- Moderate: 280 cal (200g)<br/>- Optimistic: 400 cal (200g + oil)<br/>- USDA (200g): 220 cal, 46g protein<br/><br/>Consensus: Likely 200g chicken<br/>+ some cooking oil (moderate oil use)<br/>Final: 300 cal, 46g protein

    MOD->>MOD: Assign confidence level:<br/>- High (estimates agree)<br/>- Medium (moderate disagreement)<br/>- Low (wide disagreement)<br/><br/>Result: MEDIUM (oil uncertainty)

    MOD-->>V: {<br/>  foods: [<br/>    {name: "chicken breast", amount: "200g"},<br/>    {name: "cooking oil", amount: "1 tsp"}<br/>  ],<br/>  calories: 300,<br/>  protein: 46,<br/>  carbs: 0,<br/>  fat: 8,<br/>  confidence: "medium",<br/>  reasoning: "Conservative and USDA align on...<br/>             Added small oil estimate..."<br/>}

    V-->>V: Return consensus to calling agent
```

**Key Points**:
- Three specialists run in parallel (faster than sequential)
- Each agent has a different bias to ensure diverse perspectives
- Moderator uses Claude 3.5 Sonnet (better at synthesis)
- USDA verification grounds estimates in factual data
- Confidence level reflects agreement across estimates
- Reasoning explains the consensus process

---

## 6. User Onboarding Flow

This diagram shows the guided onboarding process for new users.

```mermaid
sequenceDiagram
    participant U as User
    participant TB as Telegram Bot
    participant A as PydanticAI Agent
    participant DB as PostgreSQL
    participant MM as Memory Manager

    U->>TB: /start
    TB->>A: Start command (new user)

    A->>DB: SELECT * FROM users WHERE telegram_id = ?
    DB-->>A: No user found

    A->>DB: INSERT INTO users (telegram_id)
    DB-->>A: user_id (UUID)

    A->>DB: INSERT INTO user_onboarding<br/>(user_id, state="welcome", path="standard")
    DB-->>A: Onboarding initialized

    A-->>TB: "Welcome! I'm your health coach.<br/>Let's get started. What's your name?"
    TB-->>U: Onboarding greeting

    U->>TB: "Alex"
    TB->>A: User response

    A->>DB: UPDATE user_onboarding SET state="collect_age"
    A->>MM: save_to_profile(name="Alex")
    MM-->>A: Saved

    A-->>TB: "Nice to meet you, Alex!<br/>How old are you?"
    TB-->>U: Next question

    U->>TB: "32"
    TB->>A: User response

    A->>MM: save_to_profile(age=32)
    A->>DB: UPDATE user_onboarding SET state="collect_goals"

    A-->>TB: "What are your health goals?"
    TB-->>U: Goals question

    U->>TB: "Lose 5kg and build muscle"
    TB->>A: User response

    A->>MM: save_to_profile(goals=["weight_loss", "muscle_building"])
    A->>DB: UPDATE user_onboarding<br/>SET state="complete", completed_at=NOW()

    A->>DB: Initialize gamification:<br/>INSERT INTO user_xp (user_id, xp=0, level=1)
    A->>DB: INSERT INTO user_streaks (user_id, current=0)

    A-->>TB: "Perfect! You're all set. 🎉<br/>Start by logging your first meal!"
    TB-->>U: Onboarding complete
```

**Key Points**:
- Onboarding state tracked in database (survives restarts)
- Profile data saved to Markdown files incrementally
- Gamification initialized on completion
- Guided conversation flow with state machine
- Total onboarding time: ~2-3 minutes

---

## 7. Error Handling and Recovery Flow

This diagram shows how the system handles errors gracefully.

```mermaid
sequenceDiagram
    participant U as User
    participant TB as Telegram Bot
    participant A as PydanticAI Agent
    participant V as Vision AI
    participant DB as PostgreSQL

    U->>TB: Send food photo
    TB->>A: Analyze photo request

    A->>V: analyze_food_photo(photo_path)

    Note over V: OpenAI API error<br/>(rate limit exceeded)

    V-->>A: Error: RateLimitError

    Note over A: Agent has retries configured<br/>(retries=2)

    A->>V: Retry attempt 1
    V-->>A: Error: RateLimitError (still)

    A->>V: Retry attempt 2
    V-->>A: Error: RateLimitError

    Note over A: All retries exhausted<br/>Fallback strategy

    alt Fallback to Claude Vision
        A->>V: analyze_food_photo(photo_path, model="claude")
        V-->>A: Success (using Claude instead)
        A->>DB: save_food_entry()
        A-->>TB: "Food logged! (analyzed with Claude)"
        TB-->>U: Success message
    else No fallback available
        A->>A: Log error for monitoring
        A-->>TB: "Sorry, vision AI is temporarily unavailable.<br/>You can log food manually:<br/>'I ate 200g chicken and 150g rice'"
        TB-->>U: Error message with alternative

        U->>TB: "I ate 200g chicken and 150g rice"
        TB->>A: Text-based food log

        Note over A: Agent parses text<br/>(no vision needed)

        A->>DB: save_food_entry(foods_from_text)
        A-->>TB: "Food logged! (text-based)"
        TB-->>U: Success confirmation
    end
```

**Key Points**:
- Automatic retry logic (configurable)
- Fallback to alternative LLM providers
- Graceful degradation (vision → text-based logging)
- User-friendly error messages with alternatives
- Error logging for monitoring and debugging

---

## Related Documentation

- **Component Diagram**: `/docs/architecture/component-diagram.md` - System structure overview
- **Data Flow Diagram**: `/docs/architecture/data-flow-diagram.md` - Data movement patterns
- **ADR-001**: PydanticAI framework decision
- **ADR-004**: Multi-agent nutrition consensus rationale
- **API Documentation**: `/docs/api/` - REST API specifications

## Revision History

- 2025-01-18: Initial sequence diagrams created for Phase 3.7 documentation
