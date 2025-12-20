# Root Cause Analysis: GitHub Issue #20

## Issue Summary

- **GitHub Issue ID**: #20
- **Issue URL**: https://github.com/gpt153/health-agent/issues/20
- **Title**: memory malfunction
- **Reporter**: gpt153
- **Severity**: Critical
- **Status**: OPEN

## Problem Description

The bot's memory system is unreliable - information that the user explicitly asks to be remembered either isn't saved at all, or is retrieved incorrectly after conversation history is cleared with `/clear`.

**Expected Behavior:**
1. User tells bot to remember information (e.g., "3/8 pizza is ~1000 kcal, not 350 kcal")
2. Bot confirms it will remember
3. Information is permanently saved to long-term memory (Mem0 or patterns.md)
4. After `/clear`, bot retrieves data from database/long-term memory, not conversation history
5. Bot provides correct information based on saved data

**Actual Behavior:**
1. User tells bot to remember information
2. Bot confirms it will save (misleading the user)
3. Information is only stored in conversation history (short-term memory)
4. After `/clear`, conversation history is deleted
5. Bot retrieves data from database but gets incorrect/outdated results
6. User gets wrong answer (e.g., food totals don't include corrected pizza calories)

**Symptoms:**
- Bot says it will "remember" but doesn't save to permanent memory
- After `/clear`, previously corrected information reverts to wrong values
- Food intake calculations are inconsistent before and after `/clear`
- User explicitly states: "I tell it to remember, it says it will, but doesn't"

## Reproduction

**Steps to Reproduce:**
1. User logs food (e.g., pizza photo analyzed as 350 kcal)
2. User corrects the bot: "3/8 pizza should be ~1000 kcal"
3. Bot acknowledges and says it will save the correction
4. User asks "what did I eat today?" → Bot gives corrected total (~1440 kcal)
5. User runs `/clear` command to clear conversation history
6. User asks again "what did I eat today?" → Bot gives wrong total (790 kcal)
7. The pizza correction was lost

**Reproduction Verified:** Yes (based on user's example in issue #20)

## Root Cause

### Affected Components

**Files:**
- `src/bot.py` (lines 133-227, 805-813) - auto_save_user_info function
- `src/memory/mem0_manager.py` (lines 75-102) - add_message function
- `src/db/queries.py` (lines 290-334) - get_food_entries_by_date function
- `src/agent/__init__.py` (lines 895-954) - get_daily_food_summary tool

**Functions/Classes:**
- `auto_save_user_info()` - Extraction logic has gaps
- `mem0_manager.add_message()` - Automatic fact extraction unreliable
- Food entry correction workflow - No mechanism to update existing entries

**Dependencies:**
- OpenAI GPT-4o-mini (used for auto_save extraction)
- Mem0 OSS library (semantic memory)
- PostgreSQL (conversation history and food entries)

### Analysis

The memory malfunction has **three interconnected root causes**:

#### Root Cause #1: Auto-Save Extraction is Unreliable

**Location:** `src/bot.py` lines 133-227

The `auto_save_user_info()` function uses GPT-4o-mini to extract personal information from conversations. However:

1. **Extraction is too narrow**: The prompt asks for specific categories (Medical, Training, Sleep, etc.) but **doesn't extract food corrections or data updates**
2. **No category for "Corrections"**: When user says "that's wrong, it should be X", there's no category to capture this
3. **Silent failures**: If extraction returns `has_info=false`, nothing is saved and user isn't notified
4. **Misleading confirmations**: The main agent (Claude Sonnet) says "I'll save that!" but the extraction happens **after** the response is sent, so the agent doesn't know if saving succeeded

**Evidence from logs:**
```
2025-12-16 08:09:05,829 - src.bot - INFO - [DEBUG-FLOW] BEFORE auto_save_user_info
2025-12-16 08:09:07,914 - src.bot - INFO - [AUTO-SAVE] Extraction result: has_info=False, extractions=0
2025-12-16 08:09:07,914 - src.bot - INFO - [DEBUG-FLOW] AFTER auto_save_user_info completed successfully
```

The function "completes successfully" even when nothing is saved.

#### Root Cause #2: Mem0 Automatic Fact Extraction is Not Working

**Location:** `src/memory/mem0_manager.py` lines 75-102

Every message is sent to Mem0 for automatic fact extraction via `add_message()`:

```python
mem0_manager.add_message(user_id, text, role="user", metadata={"message_type": "text"})
mem0_manager.add_message(user_id, response, role="assistant", metadata={"message_type": "text"})
```

However:
1. **No verification** that facts were actually extracted
2. **No logging** of what memories Mem0 created
3. **Silent failures** - if Mem0 fails to extract, nothing happens
4. **No correction mechanism** - even if Mem0 extracts "pizza = 350 kcal", there's no way to update it when user corrects to "pizza = 1000 kcal"

#### Root Cause #3: Food Entries Cannot Be Updated

**Location:** `src/db/queries.py` lines 290-334

When user corrects a food entry:
- Original entry stays in database unchanged (e.g., pizza = 350 kcal)
- Correction only exists in conversation history
- After `/clear`, conversation history is deleted
- `get_food_entries_by_date()` returns original, uncorrected data
- `get_daily_food_summary()` calculates totals from wrong data

**There is NO mechanism to:**
- Update an existing food entry
- Flag an entry as "corrected"
- Link a correction to the original entry
- Store correction metadata

### Why This Occurs

The system has a **layered memory architecture**:

1. **Layer 1 (Ephemeral)**: Conversation history - deleted by `/clear`
2. **Layer 2 (Structured)**: Database (food_entries, tracking_entries, etc.) - permanent but immutable
3. **Layer 3 (Semantic)**: Mem0 + patterns.md - permanent but extraction is unreliable

**The bug happens when:**
- User provides correction/update in conversation
- Agent acknowledges and promises to save
- Correction lives in Layer 1 (conversation history)
- Auto-save and Mem0 fail to move it to Layer 2 or 3
- `/clear` deletes Layer 1
- Bot retrieves from Layer 2 (uncorrected database entries)
- User gets wrong answer

**Code Location Showing the Problem:**

`src/bot.py` lines 805-813:
```python
# Save user message and assistant response to database
await save_conversation_message(user_id, "user", text, message_type="text")
await save_conversation_message(user_id, "assistant", response, message_type="text")

# Add to Mem0 for semantic memory and automatic fact extraction
mem0_manager.add_message(user_id, text, role="user", metadata={"message_type": "text"})
mem0_manager.add_message(user_id, response, role="assistant", metadata={"message_type": "text"})

# Auto-save: Extract and save any personal information from the conversation
logger.info(f"[DEBUG-FLOW] BEFORE auto_save_user_info for user {user_id}")
await auto_save_user_info(user_id, text, response)
logger.info(f"[DEBUG-FLOW] AFTER auto_save_user_info completed successfully")
```

The agent sends response **before** auto_save runs, so it can't verify the save succeeded. The user is told "I'll remember that" but the save happens asynchronously and may fail silently.

### Related Issues

This is similar to issue #18 (incorrect answers) where the bot couldn't find information that was clearly present. Both stem from unreliable memory extraction and storage.

## Impact Assessment

**Scope:**
- Affects ALL users who correct information and later use `/clear`
- Affects ALL data types that can be corrected (food, training, sleep, etc.)
- Affects user trust in the system

**Affected Features:**
- Food tracking corrections
- Memory/profile updates
- User data corrections
- Any conversational data entry followed by `/clear`

**Severity Justification:**
This is **Critical** because:
1. **Data integrity**: Users get wrong information about their own data
2. **User trust**: Bot says it will remember but doesn't, breaking trust
3. **Health impact**: Wrong nutritional data can affect health decisions
4. **Reliability**: "WAY too unreliable" per user - core functionality broken

**Data/Security Concerns:**
- Food data discrepancies could lead to malnutrition if user relies on totals
- Medication/injection schedule corrections could be lost (dangerous)
- No audit trail of what was supposed to be saved vs. what actually saved

## Proposed Fix

### Fix Strategy

Implement a **multi-layered fix** addressing all three root causes:

1. **Make auto_save extraction comprehensive and verified**
   - Add "Data Corrections" category to extraction
   - Add verification and user notification on save failure
   - Return save status to agent so it can confirm or deny

2. **Add explicit update/correction tools**
   - Create `update_food_entry()` tool for correcting entries
   - Create `remember_fact()` tool for explicit memory saves
   - Allow agent to use these tools when user says "remember" or "that's wrong"

3. **Verify Mem0 integration**
   - Add logging of what Mem0 extracts
   - Add retrieval verification (test that saved data can be retrieved)
   - Add update mechanism for correcting Mem0 memories

4. **Add database update capabilities**
   - Create UPDATE query for food_entries
   - Add correction_note field to track why entry was updated
   - Add updated_at timestamp

### Files to Modify

1. **src/bot.py**
   - Changes: Enhance auto_save_user_info to:
     - Extract corrections and updates
     - Return success/failure status
     - Log what was saved
   - Reason: Fixes silent extraction failures

2. **src/memory/mem0_manager.py**
   - Changes: Add logging and verification:
     - Log what memories Mem0 creates
     - Add `update_memory()` method for corrections
     - Verify extraction succeeded
   - Reason: Makes Mem0 reliable and debuggable

3. **src/db/queries.py**
   - Changes: Add `update_food_entry()` function:
     - UPDATE existing entry by ID
     - Add correction_note parameter
     - Return old vs new values
   - Reason: Allows correcting database entries

4. **src/agent/__init__.py**
   - Changes: Add new tools:
     - `update_food_entry()` - update existing food log
     - `remember_fact()` - explicit memory save with verification
     - `recall_fact()` - test memory retrieval
   - Reason: Gives agent explicit memory control

5. **src/memory/system_prompt.py**
   - Changes: Update instructions:
     - When user says "remember X", use `remember_fact()` tool
     - When user corrects data, use appropriate update tool
     - Verify save succeeded before confirming to user
   - Reason: Teaches agent to use new tools correctly

### Alternative Approaches

**Alternative 1: Only rely on Mem0 (not recommended)**
- Remove auto_save and patterns.md
- Use only Mem0 for everything
- Cons: Mem0 is a black box, hard to debug, no guarantees

**Alternative 2: Make everything explicit (too rigid)**
- Remove auto-save entirely
- Force user to use commands like `/remember "fact"`
- Cons: Poor UX, defeats purpose of conversational agent

**Alternative 3: Proposed approach (best)**
- Keep auto-save but make it comprehensive and verified
- Add explicit tools as backup
- Agent can use tools when auto-save isn't appropriate
- Best balance of automation and reliability

### Risks and Considerations

**Risks:**
- Adding UPDATE queries could introduce data corruption if validation fails
- Multiple memory systems (Mem0 + patterns.md + database) could conflict
- Agent might overuse update tools, changing data when it shouldn't

**Mitigations:**
- Add transaction safety to database updates
- Implement audit log for all data changes
- Add user confirmation for critical updates (medications, allergies)
- Make update tools read-only by default, require approval for writes

**Side effects to watch for:**
- Performance impact of additional verification
- Database storage growth from audit logs
- Potential confusion if agent asks "should I save this?" too often

### Testing Requirements

**Test Cases Needed:**

1. **Test auto_save extraction for corrections**
   - User: "That's wrong, it should be X"
   - Verify: Correction is extracted and saved
   - Verify: User is notified if save fails

2. **Test food entry update**
   - Log food entry
   - Correct the entry
   - Run `/clear`
   - Query food for that day
   - Verify: Corrected values are returned

3. **Test Mem0 persistence**
   - Tell bot to remember a fact
   - Run `/clear`
   - Ask bot to recall the fact
   - Verify: Fact is correctly retrieved from Mem0

4. **Test explicit remember tool**
   - User: "Remember: I train Monday, Wednesday, Friday"
   - Agent uses `remember_fact()` tool
   - Verify: Saved to patterns.md
   - Run `/clear`
   - User: "What days do I train?"
   - Verify: Correct days returned

5. **Test update rejection**
   - Agent tries to update without user confirmation
   - Verify: Update is rejected
   - User confirms update
   - Verify: Update succeeds

**Validation Commands:**
```bash
# Test food entry correction
pytest tests/integration/test_food_correction.py -v

# Test memory persistence after /clear
pytest tests/integration/test_memory_persistence.py -v

# Test auto-save extraction
pytest tests/unit/test_auto_save.py -v

# Check Mem0 logs
docker logs health-agent-db -f | grep MEM0

# Manual test
# 1. Start bot
# 2. Tell bot "Remember: my favorite food is pizza"
# 3. Run /clear
# 4. Ask "What's my favorite food?"
# 5. Should respond: "pizza"
```

## Implementation Plan

This RCA identifies three interconnected root causes for the memory malfunction:

1. **Auto-save extraction is incomplete** - doesn't capture corrections
2. **Mem0 integration is unverified** - silent failures
3. **Food entries cannot be updated** - corrections only live in conversation history

**Recommended implementation order:**

1. **Phase 1 (Quick Win)**: Add explicit `remember_fact()` and `update_food_entry()` tools
   - Gives agent immediate capability to save reliably
   - Can be implemented in 1-2 hours
   - Provides workaround while deeper fixes are developed

2. **Phase 2 (Critical Fix)**: Fix auto_save_user_info extraction
   - Add "Corrections" category
   - Add verification and logging
   - Return status to agent
   - Estimated: 2-3 hours

3. **Phase 3 (Long-term Reliability)**: Verify and enhance Mem0 integration
   - Add extraction logging
   - Add update mechanism
   - Add retrieval verification
   - Estimated: 3-4 hours

This RCA document should be used by `/implement-fix 20` command.

## Next Steps

1. Review this RCA document with stakeholders
2. Prioritize which phase to implement first (recommend Phase 1)
3. Create feature branch for implementation
4. Implement fixes with comprehensive tests
5. Deploy to staging for testing
6. Monitor logs for auto-save and Mem0 extraction success rates
7. Deploy to production with rollback plan

**Success Criteria:**
- User can correct data and it persists after `/clear`
- Bot never says "I'll remember" unless save is verified
- All data corrections are logged and auditable
- Auto-save extraction success rate > 95%
- Zero cases of wrong data after `/clear` in testing
