# Root Cause Analysis: GitHub Issue #18

## Issue Summary

- **GitHub Issue ID**: #18
- **Issue URL**: https://github.com/gpt153/health-agent/issues/18
- **Title**: sleep quiz not startable
- **Reporter**: gpt153
- **Severity**: High
- **Status**: OPEN

## Problem Description

When users ask the AI agent to log their sleep (natural language requests like "log my sleep", "I want to log sleep", etc.), they receive an AI-generated response instead of being directed to the ready-made interactive sleep quiz with buttons that was implemented earlier.

**Expected Behavior:**
- User asks to log sleep in natural language
- AI agent recognizes the intent and directs them to use `/sleep_quiz` command
- User runs `/sleep_quiz` and gets the interactive inline keyboard quiz
- User completes the 8-question quiz with button-based UI

**Actual Behavior:**
- User asks to log sleep in natural language
- AI agent provides a conversational, text-based response asking for sleep details
- The interactive quiz with buttons is bypassed entirely
- User doesn't get the streamlined button-based experience

**Symptoms:**
- Interactive sleep quiz is not accessible via natural language
- Users must know the exact command `/sleep_quiz` to access the quiz
- AI agent doesn't suggest or redirect to the quiz when user asks about logging sleep

## Reproduction

**Steps to Reproduce:**
1. Send message to bot: "I want to log my sleep"
2. Observe AI response (text-based questions)
3. Expected: AI should direct to `/sleep_quiz` command
4. Actual: AI provides generic conversational response

**Reproduction Verified:** Yes (based on issue description)

## Root Cause

### Affected Components

- **Files**:
  - `src/agent/__init__.py` (AI agent response handler)
  - `src/memory/system_prompt.py` (system prompt generation)
  - `src/handlers/sleep_quiz.py` (sleep quiz handler - working correctly)

- **Functions/Classes**:
  - `get_agent_response()` in `src/agent/__init__.py`
  - `generate_system_prompt()` in `src/memory/system_prompt.py`

- **Dependencies**:
  - PydanticAI agent system
  - Telegram ConversationHandler for sleep quiz

### Analysis

**Why This Occurs:**

The root cause is a **missing system prompt instruction** for the AI agent. The sleep quiz is implemented correctly as a Telegram ConversationHandler and is accessible via the `/sleep_quiz` command, but the AI agent lacks explicit instructions on when and how to direct users to it.

**Code Flow Analysis:**

1. User sends: "log my sleep" → `handle_message()` in `src/bot.py`
2. Message goes to `get_agent_response()` in `src/agent/__init__.py`
3. Agent uses system prompt from `generate_system_prompt()` in `src/memory/system_prompt.py`
4. **PROBLEM**: System prompt doesn't mention sleep quiz or when to use it
5. Agent tries to help conversationally instead of directing to `/sleep_quiz`

**Evidence:**

Looking at `src/memory/system_prompt.py` (lines 89-187), the system prompt includes:
- General capabilities description
- User context (profile, patterns, memories)
- Safety rules about data accuracy
- Instructions for dynamic tool creation
- **MISSING**: Any mention of the sleep quiz or when to use `/sleep_quiz` command

The sleep quiz handler is properly registered in `src/bot.py` (line 1156):
```python
app.add_handler(sleep_quiz_handler)
logger.info("Sleep quiz handler registered")
```

The quiz is fully functional and accessible via `/sleep_quiz`, but the AI has no knowledge of it.

### Related Issues

This is related to the broader pattern of AI agent awareness of available bot commands. The same issue could exist for other command-based features if they aren't documented in the system prompt.

## Impact Assessment

**Scope:**
- Affects all users trying to log sleep via natural language
- Does not affect users who know to use `/sleep_quiz` command directly
- Does not affect automated sleep quiz triggers (those work via reminder system)

**Affected Features:**
- Natural language sleep logging
- User discoverability of sleep quiz feature
- Overall user experience (button-based quiz is much better UX than text back-and-forth)

**Severity Justification:**
**High** because:
- Sleep tracking is a core feature
- Users expect AI to guide them to best UX
- The better UI (button quiz) exists but is hidden
- Impacts user adoption and satisfaction

**Data/Security Concerns:**
None. This is a UX/discoverability issue, not a data integrity or security issue.

## Proposed Fix

### Fix Strategy

Add explicit instructions to the AI agent's system prompt about when and how to direct users to the sleep quiz command.

### Files to Modify

1. **`src/memory/system_prompt.py`**
   - Changes: Add sleep quiz guidance to the system prompt
   - Reason: This is where the AI learns about available bot features
   - Location: After line 101 (in the "Your Capabilities" section)

### Detailed Fix

**In `src/memory/system_prompt.py`, add after line 101:**

```python
**Sleep Tracking:**
When users want to log their sleep (phrases like "log my sleep", "track sleep", "I slept", "record my night"), always direct them to use the `/sleep_quiz` command. The sleep quiz is an interactive 8-question survey with buttons that captures:
- Bedtime and wake time
- Sleep latency (time to fall asleep)
- Night wakings
- Sleep quality rating (1-10)
- Phone usage before bed
- Sleep disruptions
- Morning alertness rating

DO NOT try to collect this data conversationally. Always say: "To log your sleep, use the `/sleep_quiz` command - it's a quick 60-second interactive quiz with buttons that makes tracking easy!"
```

### Alternative Approaches

**Alternative 1: Create an agent tool for sleep logging**
- Pros: Would allow AI to handle sleep logging directly without command
- Cons: Duplicates existing quiz functionality, harder to maintain, loses button-based UX
- Verdict: Not recommended - defeats purpose of the nice UI

**Alternative 2: Auto-trigger quiz from agent**
- Pros: Seamless UX
- Cons: Technically complex (ConversationHandler state management), may break message flow
- Verdict: Not recommended for MVP - too complex

**Recommended: System prompt update (proposed fix above)**
- Pros: Simple, immediate, maintains separation of concerns
- Cons: Requires users to run a command
- Verdict: Best solution - clean, maintainable, preserves excellent button UI

### Risks and Considerations

- **Risk**: Users may not like being told to use a command
  - **Mitigation**: Explain the benefit ("quick 60-second interactive quiz with buttons")

- **Risk**: Doesn't work if user doesn't follow instruction
  - **Mitigation**: Make the prompt friendly and clear about why

- **Side effects**: None - this is purely additive to system prompt

### Testing Requirements

**Test Cases Needed:**

1. **Test Case 1 - Verify AI directs to quiz**
   - User message: "I want to log my sleep"
   - Expected: AI response mentions `/sleep_quiz` command
   - Verify: Response doesn't try to collect sleep data conversationally

2. **Test Case 2 - Verify variations**
   - User messages: "track my sleep", "I slept", "log sleep"
   - Expected: All direct to `/sleep_quiz`
   - Verify: Consistent behavior across phrasings

3. **Test Case 3 - Quiz still works**
   - User runs: `/sleep_quiz`
   - Expected: Interactive quiz starts normally
   - Verify: No regression to quiz functionality

4. **Test Case 4 - End-to-end flow**
   - User: "log my sleep" → AI directs → User runs `/sleep_quiz` → completes quiz
   - Expected: Full flow works smoothly
   - Verify: Data saves correctly, gamification triggers

**Validation Commands:**
```bash
# Start bot in test mode
python src/main.py

# In Telegram, test:
# 1. "I want to log my sleep"
# 2. "track my sleep"
# 3. "/sleep_quiz"
# 4. Complete full quiz

# Check logs for:
grep "sleep" bot.log
grep "quiz" bot.log

# Verify database entry:
# psql health_agent_db
# SELECT * FROM sleep_entries ORDER BY logged_at DESC LIMIT 1;
```

## Implementation Plan

1. **Update system prompt** in `src/memory/system_prompt.py`
   - Add sleep quiz instruction block after line 101
   - Test locally with various sleep-related queries

2. **Test variations**
   - "log my sleep"
   - "I want to track my sleep"
   - "I slept 8 hours"
   - "record my night"

3. **Verify quiz still works**
   - Run `/sleep_quiz` directly
   - Complete full quiz flow
   - Check database for entry

4. **Update documentation** (if needed)
   - Add to bot help text
   - Update README with sleep tracking info

5. **Deploy and monitor**
   - Push to production
   - Monitor for user feedback
   - Check if users successfully use `/sleep_quiz`

This RCA document should be used as reference for implementing the fix.

## Next Steps

1. Review this RCA document
2. Implement the system prompt update
3. Test thoroughly with various phrasings
4. Deploy fix
5. Monitor user behavior to ensure fix works
