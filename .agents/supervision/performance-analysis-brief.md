# Performance Analysis Brief: Telegram Response Latency

**Created**: 2026-01-11
**Issue**: User reports >1 minute response times in Telegram
**Goal**: Identify bottlenecks and provide optimization recommendations

---

## Current Message Flow (Observed from Code)

### 1. Message Receipt → Authorization (bot.py:696-740)
- Topic filter check
- Subscription status check
- Authorization check
- **Estimated time**: <100ms

### 2. Conversation History Load (bot.py:831)
```python
message_history = await get_conversation_history(user_id, limit=20)
```
- Database query for last 20 messages
- **Potential bottleneck**: Database query time
- **Test needed**: Measure query execution time

### 3. Agent Response Generation (src/agent/__init__.py:2576-2792)

**Step 3a: Load User Memory (line 2600)**
```python
user_memory = await memory_manager.load_user_memory(telegram_id)
```
- Reads multiple markdown files from disk
- **Potential bottleneck**: File I/O
- **Test needed**: Measure file read time

**Step 3b: Extract Direct Answer (line 2603)**
```python
direct_answer = extract_direct_answer(user_message, patterns_content)
```
- Pattern matching against patterns.md
- **Estimated time**: <50ms (regex/string matching)

**Step 3c: Generate System Prompt (line 2633)**
```python
system_prompt = generate_system_prompt(user_memory, user_id=telegram_id, current_query=enhanced_message)
```
- **CRITICAL**: Includes Mem0 semantic search
- **High likelihood bottleneck**: Mem0 uses pgvector for semantic retrieval
- **Test needed**: Measure system prompt generation time

**Step 3d: Convert Message History (line 2645-2656)**
- Convert dicts → ModelMessage objects
- **Estimated time**: <10ms (in-memory)

**Step 3e: Tool Registration (line 2665-2711)**
- Registers 70+ tools on agent instance
- **Potential bottleneck**: Tool registration overhead
- **Test needed**: Check if tools are registered fresh each time

**Step 3f: LLM API Call (line 2714-2716)**
```python
result = await dynamic_agent.run(enhanced_message, deps=deps, message_history=converted_history)
```
- Network latency to Claude API
- Model inference time
- **Major bottleneck**: This is likely 10-30 seconds minimum
- **Test needed**: Measure actual API call duration

### 4. Save Responses (bot.py:841-845)
```python
await save_conversation_message(user_id, "user", text, message_type="text")
await save_conversation_message(user_id, "assistant", response, message_type="text")
mem0_manager.add_message(user_id, text, role="user", ...)
```
- Two database writes
- One Mem0 add (generates semantic embedding)
- **Potential bottleneck**: Mem0 embedding generation
- **Test needed**: Measure save operations time

---

## Suspected Bottlenecks (Ranked by Likelihood)

### 1. **LLM API Call** (HIGHEST)
- **Estimated impact**: 10-40 seconds
- **Why**: Claude Sonnet 3.5 typically takes 5-30s for complex queries
- **Evidence needed**: Actual timing measurement
- **Solution**: Streaming (already doing?), caching, faster model

### 2. **Mem0 Semantic Search** (HIGH)
- **Estimated impact**: 1-10 seconds
- **Why**: pgvector similarity search on large memory corpus
- **Evidence needed**: Profile system_prompt generation
- **Solution**: Limit search scope, cache recent results, disable for simple queries

### 3. **Tool Registration** (MEDIUM)
- **Estimated impact**: 500ms-2 seconds
- **Why**: Registering 70+ tools on every message
- **Evidence needed**: Measure tool registration time
- **Solution**: Singleton agent instance, lazy loading

### 4. **Conversation History Load** (LOW-MEDIUM)
- **Estimated impact**: 100ms-1 second
- **Why**: Database query for 20 messages with joins
- **Evidence needed**: Database query profiling
- **Solution**: Caching, reduce limit, indexing

### 5. **User Memory File Loading** (LOW)
- **Estimated impact**: 50-200ms
- **Why**: Multiple file reads from disk
- **Evidence needed**: Profile file I/O
- **Solution**: Caching in Redis/memory

### 6. **Mem0 add_message** (LOW-MEDIUM)
- **Estimated impact**: 500ms-2 seconds
- **Why**: Generates embedding and stores in pgvector
- **Evidence needed**: Profile add_message call
- **Solution**: Move to background task, batch inserts

---

## Investigation Tasks

### Task 1: Add Timing Instrumentation
Create a test message handler with detailed timing:

```python
import time

async def instrumented_message_handler(user_id, text):
    timings = {}

    t0 = time.time()
    message_history = await get_conversation_history(user_id, limit=20)
    timings['conversation_history'] = time.time() - t0

    t0 = time.time()
    user_memory = await memory_manager.load_user_memory(user_id)
    timings['load_memory'] = time.time() - t0

    t0 = time.time()
    system_prompt = generate_system_prompt(user_memory, user_id=user_id, current_query=text)
    timings['system_prompt'] = time.time() - t0

    t0 = time.time()
    response = await get_agent_response(user_id, text, memory_manager, ...)
    timings['agent_response'] = time.time() - t0

    t0 = time.time()
    await save_conversation_message(user_id, "user", text)
    await save_conversation_message(user_id, "assistant", response)
    timings['save_messages'] = time.time() - t0

    t0 = time.time()
    mem0_manager.add_message(user_id, text, role="user")
    timings['mem0_add'] = time.time() - t0

    return response, timings
```

### Task 2: Test with Mock User
- Use test_user_999888777 from testing
- Send 5-10 varied messages
- Collect timing data for each stage
- Identify which stages take >1 second

### Task 3: Database Query Analysis
- Run EXPLAIN ANALYZE on conversation history query
- Check if indexes exist on conversation_messages table
- Measure actual query execution time

### Task 4: Mem0 Profiling
- Measure semantic search time in generate_system_prompt
- Count number of memories being searched
- Test with Mem0 disabled (if possible) to isolate impact

### Task 5: Tool Registration Check
- Verify if Agent instance is created fresh each time
- Count number of tools registered
- Test with minimal tools to measure overhead

---

## Quick Wins (No Code Changes)

1. **Check Claude API status** - Is there an outage or slowdown?
2. **Check database performance** - Are indexes missing?
3. **Check Mem0 memory count** - Too many memories = slow search
4. **Check system prompt size** - How long is it? (logged in code)

---

## Optimization Strategies (If Bottlenecks Confirmed)

### If LLM API is slow (10-40s):
- ✅ **Already streaming?** Check if streaming is enabled
- Add response caching for common queries
- Use faster model (Haiku) for simple queries
- Implement "typing" indicator updates during long waits

### If Mem0 is slow (1-10s):
- Limit semantic search to recent memories only
- Cache search results for session
- Disable for simple queries (e.g., "hi", "thanks")
- Move to background task (async)

### If Tool Registration is slow (0.5-2s):
- Create singleton agent instance (reuse across messages)
- Lazy-load tools only when needed
- Reduce number of tools registered upfront

### If Database queries are slow (100ms-1s):
- Add indexes on frequently queried columns
- Reduce conversation_history limit (20 → 10)
- Implement Redis caching for recent messages

### If File I/O is slow (50-200ms):
- Cache user memory in Redis with TTL
- Load only changed files (last_modified check)

---

## Expected Execution Plan

1. Run instrumented testing (30-60 minutes)
2. Analyze timing data to identify top 2-3 bottlenecks
3. Implement targeted optimizations for confirmed bottlenecks
4. Re-test to measure improvement
5. Report findings with before/after metrics

---

## Success Metrics

**Target**: Reduce response time from >60s to <10s

**Acceptable breakdown**:
- Database queries: <500ms
- Memory loading: <200ms
- System prompt generation: <1s
- LLM API call: 5-15s (unavoidable, model dependent)
- Save operations: <1s
- **Total**: 7-18 seconds (realistic target)

**Stretch goal**: <5s for simple queries (no tools, no semantic search)
