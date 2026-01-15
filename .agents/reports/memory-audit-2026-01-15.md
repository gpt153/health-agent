# Memory Retrieval Audit Report

**Date**: 2026-01-15 (Stockholm time)
**Auditor**: Supervisor Agent
**Trigger**: User concern about personalization being skipped
**Related Issue**: #42 (Research: Memory retrieval quality)

---

## Executive Summary

**Finding**: Memory retrieval is ALWAYS performed when the AI agent is invoked, BUT the response cache bypasses the agent entirely for ~10% of messages, resulting in zero personalization for greetings and simple acknowledgments.

**Impact**: Contradicts core product USP ("agent that knows its users")

**Recommendation**: Remove response cache entirely. Optimize memory retrieval speed instead.

---

## Audit Methodology

1. ✅ Traced code flow from user message → agent response
2. ✅ Analyzed PR #37 (performance optimization that introduced caching)
3. ✅ Examined memory retrieval in `get_agent_response()`
4. ✅ Reviewed system prompt generation and Mem0 integration
5. ✅ Analyzed query routing (Haiku vs Sonnet)

---

## Findings

### 1. **Response Cache: The Culprit** ⚠️

**Location**: `src/bot.py` lines 718-724

```python
# Check for cached response (instant replies for greetings, thanks, etc.)
from src.utils.response_cache import response_cache
cached_response = response_cache.get_cached_response(text)
if cached_response:
    # Send instant cached response (no LLM needed)
    await update.message.reply_text(cached_response)
    logger.info(f"Sent cached response to {user_id}")
    return  # <-- RETURNS WITHOUT LOADING MEMORY!
```

**What happens:**
- Executed BEFORE agent is called
- Matches patterns like: `^(hi|hey|hello)[\s!.]*$`
- Returns generic response: "Hey! 👋 How can I help you today?"
- No memory loading
- No Mem0 search
- No personalization

**Cached patterns** (`src/utils/response_cache.py` lines 18-60):
- Greetings: `hi`, `hey`, `hello`, `sup`, `yo`, `hola`
- Thanks: `thanks`, `thank you`, `thx`, `ty`
- Good morning/night
- OK/Alright
- Yes/No (single word)

**Impact**: ~10% of messages (per PR #37) bypass personalization entirely

**Why this is wrong for this product:**
- User's USP: "Agent gets to know its users - that's the main USP"
- A returning user saying "Hi" should get: "Morning! Ready for your usual 8am workout?"
- Not: "Hey! 👋 How can I help you today?" (generic)

---

### 2. **Memory Retrieval: Works When Agent is Called** ✅

**Location**: `src/agent/__init__.py` lines 2632-2666

```python
async def get_agent_response(...):
    # Load user memory from markdown files
    user_memory = await memory_manager.load_user_memory(telegram_id)  # Line 2633

    # Generate dynamic system prompt with Mem0 semantic search
    system_prompt = generate_system_prompt(
        user_memory,
        user_id=telegram_id,
        current_query=enhanced_message
    )  # Line 2666
```

**Flow when agent IS called:**
1. Load user memory (profile, preferences, patterns) ✅
2. Perform Mem0 semantic search for relevant memories ✅
3. Generate personalized system prompt ✅
4. Create agent with full context ✅

**Verified locations:**
- `src/memory/system_prompt.py` lines 57-88: Mem0 search executed
- `src/memory/system_prompt.py` lines 146-158: User memory injected into prompt
- System prompt includes:
  - `<profile>`: User demographics, goals
  - `<patterns_and_schedules>`: Habits, routines
  - `<semantic_memories>`: Mem0 search results

**Conclusion**: Memory IS always loaded and used when the agent runs.

---

### 3. **Query Routing: Does NOT Skip Memory** ✅

**Location**: `src/utils/query_router.py`
**Also**: `src/bot.py` lines 852-868

```python
# Route query to appropriate model (Haiku for simple, Sonnet for complex)
from src.utils.query_router import query_router
model_choice, routing_reason = query_router.route_query(text)

# Select model based on routing
model_override = None
if model_choice == "haiku":
    model_override = "anthropic:claude-3-5-haiku-latest"

# Get agent response with conversation history
response = await get_agent_response(
    user_id, text, memory_manager, reminder_manager, message_history,
    bot_application=context.application,
    model_override=model_override  # <-- Haiku or Sonnet
)
```

**How routing works:**
- Simple queries (< 8 words, factual) → Haiku (2-3s)
- Complex queries (analysis, reasoning) → Sonnet (6-8s)
- BOTH models receive the SAME system prompt
- BOTH models get full memory context

**Verified**:
- Line 2633: Memory loaded BEFORE routing decision
- Line 2666: System prompt generated with memory
- Line 2703-2707: Agent created with full system prompt (regardless of model)

**Conclusion**: Query routing is NOT the problem. Both Haiku and Sonnet get personalization.

---

### 4. **Mem0 Semantic Search: Always Performed** ✅

**Location**: `src/memory/system_prompt.py` lines 57-88

```python
# Search Mem0 for relevant context if query provided
mem0_context = ""
if user_id and current_query:
    try:
        memories = mem0_manager.search(user_id, current_query, limit=5)
        # ... process memories ...
        mem0_context = "\n\n**RELEVANT MEMORIES (from semantic search):**\n"
        for mem in memories:
            mem0_context += f"- {memory_text}\n"
    except Exception as e:
        logger.error(f"[MEM0_DEBUG] Error searching memories: {e}")
```

**Verified**:
- Mem0 search runs for EVERY agent invocation
- Searches for top 5 relevant memories
- Injects into system prompt under `<semantic_memories>`

**Conclusion**: Mem0 works correctly when agent is called.

---

## Performance Analysis (PR #37)

**Introduced optimizations:**

1. ✅ **Persistent typing indicator**: Good UX, no personalization impact
2. ⚠️ **Response caching**: 99% faster but ZERO personalization (~10% of messages)
3. ✅ **Query routing**: 60% faster for simple queries, personalization maintained
4. ✅ **Background Mem0 embedding**: Saves 0.7-1.5s, no personalization impact

**Trade-off made:**
- Speed: <100ms for cached responses
- Cost: Lost personalization for 10% of messages

**User's perspective:**
- Speed gained: Minimal (greetings were already fast queries for Haiku)
- Personalization lost: Significant (violates core product promise)

---

## User's Vision vs Current Implementation

### User's Vision (from conversation)

> "i always want user info to influence agent answer. so if user takes a picture of food similar to ones he has uploaded before, and previously explained what it was, agent should realise this."

> "or like me i always drink my protein powder mixed with 3% milk, 0.5dl powder per 1dl milk. so if i say 3dl whey100 it should know its 3dl milk 3%, and 3 * 0.5dl = 1.5 portions of whey100."

> "i just always want personalised answers, that is what will set us apart from a regular calory-tracking app. our agent gets to know its users!!! thats the main USP."

### Current Behavior

**Scenario 1: Regular user returns**
- User: "Hi"
- Current: "Hey! 👋 How can I help you today?" (generic, cached)
- Expected: "Morning! Ready for your usual 8am workout?" (personalized)

**Scenario 2: User has protein shake habit**
- User: "3dl whey100"
- Current flow:
  - NOT cached (no pattern match)
  - Agent IS called → Memory IS loaded → Pattern recognized ✅
- Expected: Works correctly (agent called)

**Scenario 3: User says thanks after food log**
- User: "Thanks"
- Current: "You're welcome! 😊" (generic, cached)
- Expected: "You're welcome! You're on a 5-day logging streak 🔥" (personalized)

---

## Root Cause Analysis

**The response cache was designed for speed, not for personalization.**

**Assumption made**: Simple messages don't need context.
**Reality**: EVERY message should be personalized in this product.

**Why the assumption was wrong:**
1. Greeting from returning user should reference their routine
2. "Thanks" after food log should celebrate their streak
3. "OK" after reminder should acknowledge their consistency
4. Every interaction is a coaching opportunity

**Comparison to competitors:**
- Replika: ALWAYS personalized, even for "hi"
- Pi (Inflection AI): ALWAYS contextual
- Character.ai: ALWAYS in-character

These products succeed BECAUSE they maintain context always, not just sometimes.

---

## Recommendations

### Option 1: Remove Response Cache (Recommended)

**Why:**
- Aligns with core USP
- Simplifies codebase
- Eliminates entire class of "missed personalization" bugs

**Performance impact:**
- Greetings: <100ms (cached) → 2-4s (Haiku with memory)
- Acceptable for AI coaching product
- Still faster than 60s baseline before PR #37

**Implementation:**
1. Delete `src/utils/response_cache.py`
2. Remove cache check from `src/bot.py` lines 718-724
3. All messages go through agent with full memory

**Benefits:**
- 100% personalization guarantee
- No "sometimes works, sometimes doesn't" confusion
- Simpler mental model for developers

---

### Option 2: Smart Personalized Cache (Not Recommended)

**Concept**: Cache responses per-user with memory

```python
cache_key = f"{user_id}:{message_hash}:{memory_hash}"
```

**Why not recommended:**
1. Complex implementation
2. Memory changes make cache stale
3. Hard to validate correctness
4. Doesn't align with "learning agent" philosophy

---

### Option 3: Optimize Memory Retrieval Instead (Complementary)

**Goal**: Make full personalization fast enough that caching isn't needed

**Current bottlenecks** (estimated):
- Mem0 vector search: ~200-300ms
- Memory file loading: ~50ms
- System prompt generation: ~50ms
- **Total overhead**: ~300-400ms

**Target**: <200ms total for memory operations

**Optimizations:**
- **Parallel execution**: Load memory + Mem0 search concurrently
- **Memory compression**: Summarize old patterns
- **Faster embeddings**: Use smaller embedding model
- **Database connection pooling**: Already implemented ✅

**Implementation**:
```python
async def retrieve_user_context(user_id: int, query: str):
    # All execute in parallel
    results = await asyncio.gather(
        vector_search_memories(user_id, query),      # ~200ms
        load_memory_files(user_id),                  # ~50ms
        get_recent_logs(user_id, days=7)             # ~50ms
    )
    return compress_context(results)  # ~50ms
```

**Benefits:**
- Maintains personalization
- Improves speed
- Doesn't compromise on quality

---

## Proposed Solution

### Phase 1: Remove Cache (Immediate)

**Action items:**
1. Delete `src/utils/response_cache.py`
2. Remove cache logic from `src/bot.py` (lines 718-724)
3. Update PR #37 description to note cache removal
4. Run tests to ensure no breakage

**Expected outcome:**
- 100% personalization restored
- Slight latency increase for greetings (acceptable)

---

### Phase 2: Optimize Memory Retrieval (Follow-up)

**Action items:**
1. Benchmark current memory retrieval time
2. Implement parallel memory operations
3. Profile Mem0 search performance
4. Consider memory compression strategies

**Expected outcome:**
- Personalized responses in 3-5s (competitive)
- Fast AND personalized (not fast OR personalized)

---

### Phase 3: Habit Extraction System (Future Enhancement)

**Action items:**
1. Build pattern detection layer
2. Create `user_habits` database table
3. Automatically extract habits after 3+ repetitions
4. Include habits in system prompt

**Example**: User's "3dl whey100" habit
- After 3 times: Extract pattern
- Store: `{"food": "whey100", "ratio": "1:1", "liquid": "milk_3_percent"}`
- Agent auto-calculates: 3dl = 3dl milk + 1.5 portions

**Expected outcome:**
- Deeper personalization over time
- Proactive habit recognition
- Reduced need for user explanations

---

## Conclusion

**The good news:** Memory retrieval works correctly when the agent is invoked.

**The bad news:** Response cache bypasses the agent for ~10% of messages, completely eliminating personalization.

**The fix:** Remove the response cache. Optimize memory retrieval speed to maintain acceptable latency with full personalization.

**Philosophy alignment:**
- User's vision: "Our agent gets to know its users - that's the USP"
- Current cache: "Skip the agent for speed"
- These are fundamentally incompatible.

**Next step:** Create new issue or reframe #42 to focus on removing the cache and optimizing memory retrieval.

---

## Appendix: Code Locations

**Response cache:**
- Implementation: `src/utils/response_cache.py`
- Usage: `src/bot.py` lines 718-724

**Memory retrieval:**
- Agent entry: `src/agent/__init__.py` line 2633
- System prompt: `src/memory/system_prompt.py` lines 8-282
- Mem0 search: `src/memory/system_prompt.py` lines 57-88

**Query routing:**
- Router: `src/utils/query_router.py`
- Usage: `src/bot.py` lines 852-868

**PR #37 changes:**
- Merged: 2026-01-12
- Introduced: Response cache, query routing, background tasks, typing indicator

---

**Report complete. Ready for decision on Issue #42.**

---

## ADDENDUM: Food Photo Analysis Memory Audit

**Date**: 2026-01-15 (continued)
**Scope Extension**: User requested audit of food photo memory usage

---

### Finding Summary

**Food photo analysis has LIMITED memory integration** - significantly more basic than text conversations.

**Current state:**
- ✅ Uses `visual_patterns` field from memory
- ❌ Does NOT use Mem0 semantic search
- ❌ Does NOT detect similar past photos
- ❌ Does NOT apply food habits
- ❌ Does NOT include past food history context

---

### Current Implementation

**Code flow** (`src/bot.py` lines 952-961):

```python
# Load user's visual patterns for better recognition
user_memory = await memory_manager.load_user_memory(user_id)
visual_patterns = user_memory.get("visual_patterns", "")

# Analyze with vision AI (with caption and visual patterns)
analysis = await analyze_food_photo(
    str(photo_path),
    caption=caption,
    user_id=user_id,
    visual_patterns=visual_patterns  # <-- Only this passed
)
```

**Vision AI prompt enhancement** (`src/utils/vision.py` lines 118-119, 262-263):

```python
if visual_patterns:
    prompt_text += f"\n\nUser's known food patterns:\n{visual_patterns}\nCheck if this matches any known items."
```

**That's the entire memory integration.**

---

### What Works

1. **Visual patterns field** ✅
   - Agent can save patterns via `remember_visual_pattern` tool
   - Stored in memory markdown files
   - Passed to vision AI as text

2. **Example saved pattern:**
   ```
   My protein shaker: Clear bottle with white liquid, 30g protein, 150 cal
   ```

3. **Vision AI receives:**
   ```
   User's known food patterns:
   My protein shaker: Clear bottle with white liquid, 30g protein, 150 cal
   Check if this matches any known items.
   ```

---

### What's Missing

#### 1. Mem0 Semantic Search ❌

**Text conversations:**
```python
# src/memory/system_prompt.py lines 57-88
memories = mem0_manager.search(user_id, current_query, limit=5)
# Always performed for text messages
```

**Food photos:**
```python
# NO Mem0 search performed
# Vision AI doesn't get semantic memory context
```

**Impact:**
- Can't retrieve relevant food context from past conversations
- User says "I always have protein shakes after workout" in chat
- Vision AI doesn't know this when analyzing shake photo

---

#### 2. Photo Similarity Detection ❌

**User's requirement:**
> "if user takes a picture of food similar to ones he has uploaded before, and previously explained what it was, agent should realise this"

**Current implementation:**
- No photo embeddings stored
- No vector database for photos
- No similarity search

**What's needed:**
```sql
CREATE TABLE food_photo_embeddings (
  user_id VARCHAR,
  photo_id UUID,
  embedding VECTOR(512),        -- CLIP or similar model
  food_description TEXT,         -- What user said about it
  nutrition_summary JSONB,
  logged_at TIMESTAMP
);

-- Query with vector similarity
SELECT * FROM food_photo_embeddings
WHERE user_id = 'X'
ORDER BY embedding <-> current_photo_embedding
LIMIT 5;
```

**Workflow:**
1. User uploads burger photo
2. Generate embedding (CLIP model)
3. Search for similar past photos (cosine similarity > 0.85)
4. If match found: "This looks like the burger from Restaurant X you had last week - 800 cal"

**Currently:** Impossible - no photo comparison capability

---

#### 3. Habit Application ❌

**User's requirement:**
> "like me i always drink my protein powder mixed with 3% milk, 0.5dl powder per 1dl milk. so if i say 3dl whey100 it should know its 3dl milk 3%, and 3 * 0.5dl = 1.5 portions of whey100."

**Text conversations:**
- Agent could learn this from Mem0 memories
- System prompt includes user patterns
- Agent can apply calculation

**Food photos:**
- Vision AI doesn't have access to habit database
- Can't apply "3dl whey100 = 3dl milk + 1.5 portions" rule
- User would need to type this in caption every time

**What's needed:**
```python
# Load user's food habits
habits = await get_user_habits(user_id, category="food_prep")

# Pass to vision AI
habit_context = "\n".join([
    f"- {h['habit_key']}: {h['habit_data']}"
    for h in habits
])

analysis = await analyze_food_photo(
    photo_path,
    caption=caption,
    visual_patterns=visual_patterns,
    food_habits=habit_context  # NEW
)
```

**Currently:** Vision AI doesn't know user's habits

---

#### 4. Past Food History Context ❌

**What would be useful:**
- "This looks like your usual breakfast - oatmeal with berries"
- "Similar to what you logged 3 days ago - chicken and rice"
- "Your portion sizes have been consistent this week"

**Current implementation:**
- Vision AI has NO access to past food logs
- Can't compare to user's typical meals
- Can't learn from portion size patterns

**What's needed:**
```python
# Get recent food history
recent_foods = await get_food_entries_by_date(
    user_id,
    start_date=seven_days_ago,
    end_date=today
)

# Summarize for context
food_summary = summarize_recent_foods(recent_foods)

# Pass to vision AI
analysis = await analyze_food_photo(
    photo_path,
    caption=caption,
    visual_patterns=visual_patterns,
    recent_food_history=food_summary  # NEW
)
```

**Currently:** Vision AI works in isolation from food history

---

### Comparison: Text vs Photo Memory

| Feature | Text Messages | Food Photos |
|---------|--------------|-------------|
| Load user memory | ✅ Always | ✅ Limited (visual_patterns only) |
| Mem0 semantic search | ✅ Always | ❌ Never |
| System prompt personalization | ✅ Full context | ❌ Basic text field |
| Habit application | ✅ Via agent tools | ❌ Not available |
| Past history context | ✅ 20-message window | ❌ No history |
| Similar item detection | N/A | ❌ Not implemented |

---

### Why This Matters

**User's vision:**
- Agent that learns from ALL interactions
- Recognizes patterns across modalities (text + photos)
- Applies knowledge consistently

**Current reality:**
- Text conversations: Well-personalized
- Food photos: Basic personalization
- **Disconnect between modalities**

**Example scenario:**

**Conversation 1 (Text):**
- User: "I always have my protein shake after morning workouts"
- Agent: [Saves to Mem0] "Got it, I'll remember that!"

**2 weeks later (Photo):**
- User: [Uploads photo of protein shake after workout]
- Vision AI: "I see a protein shake, approximately 30g protein, 200 cal"
- **Missing**: "Your usual post-workout shake! Right on schedule 💪"

**The agent should connect the dots** - that's the USP.

---

### Recommendations

#### Short-term (Phases 1-3)

**Focus on response cache removal first:**
1. Affects ALL interactions (10% of messages)
2. Violates core USP
3. Quick fix (30 min - 2 hours)

**Food photos already work** - they're not broken, just less sophisticated.

---

#### Long-term (Phase 4: Enhanced Photo Memory)

**Priority order:**

**4.1: Add Mem0 Search (Easy, High Impact)**
- Estimated: 1-2 hours
- Add Mem0 search before vision AI call
- Pass relevant memories as context
- Immediate benefit: "Your usual breakfast" recognition

**4.2: Include Recent Food History (Medium, High Impact)**
- Estimated: 2-3 hours
- Query last 7 days of food logs
- Summarize and pass to vision AI
- Benefit: Better portion size estimates, pattern recognition

**4.3: Habit Application (Medium, High Impact)**
- Estimated: 3-4 hours
- Build habit database (from Phase 3)
- Pass food habits to vision AI
- Benefit: Auto-calculate "3dl whey100" scenarios

**4.4: Photo Similarity Detection (Hard, Medium Impact)**
- Estimated: 6-8 hours
- Implement photo embeddings (CLIP model)
- Build vector search
- Store embeddings in database
- Benefit: "Similar to burger from last week"

**Total Phase 4 effort:** 12-17 hours

---

### Implementation Approach

**Phase 4.1 Example: Add Mem0 Search**

```python
# src/bot.py in handle_photo() around line 950

# Load user's visual patterns AND semantic memories
user_memory = await memory_manager.load_user_memory(user_id)
visual_patterns = user_memory.get("visual_patterns", "")

# NEW: Search Mem0 for relevant food context
food_memories = mem0_manager.search(
    user_id,
    query=f"food photo {caption if caption else 'meal'}",
    limit=5
)

# Build context from memories
mem0_context = ""
if food_memories:
    mem0_context = "\n\n**Relevant context from past conversations:**\n"
    for mem in food_memories:
        memory_text = mem.get('memory', str(mem))
        mem0_context += f"- {memory_text}\n"

# Analyze with vision AI (NOW with Mem0 context)
analysis = await analyze_food_photo(
    str(photo_path),
    caption=caption,
    user_id=user_id,
    visual_patterns=visual_patterns,
    semantic_context=mem0_context  # NEW parameter
)
```

**Update vision.py to accept semantic_context:**
```python
# src/utils/vision.py line 13-18

async def analyze_food_photo(
    photo_path: str,
    caption: Optional[str] = None,
    user_id: Optional[str] = None,
    visual_patterns: Optional[str] = None,
    semantic_context: Optional[str] = None  # NEW
) -> VisionAnalysisResult:
```

**Add to prompt (lines 119, 263):**
```python
if visual_patterns:
    prompt_text += f"\n\nUser's known food patterns:\n{visual_patterns}"

if semantic_context:  # NEW
    prompt_text += f"\n\n{semantic_context}"
```

**Estimated time:** 1 hour

---

### Conclusion

**Food photo analysis uses memory, but minimally:**
- Only `visual_patterns` text field
- No Mem0, no embeddings, no habits, no history

**This is acceptable short-term because:**
1. Photos aren't broken - they work
2. Response cache is a higher priority issue (affects ALL messages)
3. Photo enhancements are complex (6-17 hours total)

**Long-term strategy:**
- Phase 1-3: Fix response cache, optimize text conversations
- Phase 4: Enhance food photo memory (Mem0, history, habits, similarity)

**Vision:**
- Unified memory across all modalities
- Agent that connects text + photo context
- "Your usual post-workout shake" recognition

---

## Final Audit Summary

**Text conversations:**
- ✅ Memory works correctly when agent is called
- ⚠️ Response cache bypasses agent (10% of messages)
- **Fix:** Remove cache (Phase 1)

**Food photos:**
- ✅ Basic memory integration (visual_patterns)
- ⚠️ No Mem0, habits, or similarity detection
- **Fix:** Enhance in Phase 4 (future)

**Priority:** Text conversations first (response cache removal), then enhance photos.

**Report complete.**
