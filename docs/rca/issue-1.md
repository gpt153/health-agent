# Root Cause Analysis: GitHub Issue #1

## Issue Summary

- **GitHub Issue ID**: #1
- **Issue URL**: https://github.com/gpt153/health-agent/issues/1
- **Title**: onboarding stuck
- **Reporter**: gpt153
- **Severity**: High
- **Status**: OPEN
- **Created**: 2025-12-19T18:03:50Z

## Problem Description

The onboarding process for new users is faulty and gets stuck, preventing users from completing the initial setup flow and accessing the bot's features.

**Expected Behavior:**
When a new user starts the bot with `/start`, they should be guided through an onboarding flow that:
1. Shows path selection (Quick Start, Full Tour, or Just Chat)
2. Routes them through the selected onboarding path
3. Collects necessary information (timezone, preferences)
4. Completes successfully, allowing access to all bot features

**Actual Behavior:**
Users get stuck in the onboarding flow because the onboarding message handler is disabled in the main bot message handler. When users respond to onboarding prompts, their messages are not routed to the onboarding handler, causing the flow to stall.

**Symptoms:**
- Users can trigger `/start` and see initial onboarding messages
- Users cannot progress through onboarding steps
- Responses to onboarding prompts are not processed
- Users remain in incomplete onboarding state indefinitely
- Bot does not respond appropriately to onboarding-related user inputs

## Reproduction

**Steps to Reproduce:**
1. Start a fresh session with the bot as a new user
2. Send `/start` command
3. Bot displays path selection options (Quick Start, Full Tour, Just Chat)
4. Select any option (e.g., "Quick Start 🚀")
5. Observe that the bot does not progress to the next onboarding step
6. User is stuck and cannot complete onboarding

**Reproduction Verified:** Yes

## Root Cause

### Affected Components

- **Files**:
  - `src/bot.py` (main message handler)
  - `src/handlers/onboarding.py` (onboarding flow handlers)
  - `src/db/queries.py` (onboarding state management)

- **Functions/Classes**:
  - `handle_message()` in `src/bot.py` (lines 676-681)
  - `handle_onboarding_message()` in `src/handlers/onboarding.py`
  - `get_onboarding_state()` in `src/db/queries.py`

- **Dependencies**:
  - Database table: `user_onboarding_state`
  - Telegram bot message routing

### Analysis

The root cause is that the onboarding check in the main message handler (`src/bot.py`) was **intentionally disabled for debugging** and never re-enabled.

**Why This Occurs:**

In commit `5c8095c` (2025-12-19), the onboarding flow was temporarily disabled to allow users to interact with the bot without setup friction during debugging. The commit message states:

> "Temporarily commented out onboarding flow and timezone validation to allow users to interact with the bot without setup friction."

However, this temporary debugging change was never reverted, leaving the onboarding system in a broken state.

**Code Location:**

```
File: src/bot.py
Lines: 676-681
```

```python
# Check if user is in onboarding
# DISABLED: Onboarding check commented out for debugging
# onboarding = await get_onboarding_state(user_id)
# if onboarding and not onboarding.get('completed_at'):
#     # Route to onboarding handler
#     await handle_onboarding_message(update, context)
#     return
```

**How the Flow Should Work:**

1. User sends a message to the bot
2. `handle_message()` receives the message
3. System checks if user has incomplete onboarding (`get_onboarding_state()`)
4. If onboarding is incomplete, route message to `handle_onboarding_message()`
5. Onboarding handler processes the input based on current step
6. User progresses through onboarding flow

**What Actually Happens:**

1. User sends a message to the bot
2. `handle_message()` receives the message
3. Onboarding check is commented out (skipped)
4. Message is processed as normal bot conversation
5. Onboarding state is never updated
6. User remains stuck in incomplete onboarding

### Related Issues

- Timezone validation is also disabled in the same commit (lines 687-690), which may cause additional setup issues even after onboarding is fixed
- The `/start` command can still initiate onboarding and update the database state, creating a mismatch where users are "in onboarding" according to the database but the bot doesn't route their messages to the onboarding handler

## Impact Assessment

**Scope:**
All new users attempting to use the bot for the first time are affected. Existing users who have already completed onboarding are not affected.

**Affected Features:**
- New user onboarding (completely broken)
- First-time user experience
- User activation flow
- Timezone setup
- Feature discovery and introduction

**Severity Justification:**
This is a **High** severity issue because:
- It affects 100% of new users
- It prevents new users from accessing the bot's core functionality
- It creates a poor first impression
- The bot appears broken to new users
- There is no workaround for users (only developers can manually mark onboarding as complete in the database)

**Data/Security Concerns:**
- No data corruption risk
- No security implications
- Database integrity is maintained (state is correctly stored, just not checked)
- May result in orphaned onboarding records in the database

## Proposed Fix

### Fix Strategy

**Primary Fix: Re-enable the onboarding check in the message handler**

Simply uncomment the onboarding check in `src/bot.py` to restore the original functionality. The onboarding system itself is fully implemented and functional - it just needs to be connected to the message routing logic.

**Secondary Consideration: Re-enable timezone validation**

The timezone check should also be reviewed and potentially re-enabled, as it was disabled in the same debugging session.

**Testing Strategy:**

Verify that the complete flow works end-to-end:
1. New user sends `/start`
2. User selects an onboarding path
3. User progresses through all steps
4. Onboarding completes successfully
5. User can then use the bot normally

### Files to Modify

1. **src/bot.py** (lines 676-681)
   - Changes: Uncomment the onboarding check and message routing
   - Reason: This restores the connection between user messages and the onboarding handler

2. **src/bot.py** (lines 687-730) - Optional
   - Changes: Review and potentially re-enable timezone validation
   - Reason: Complete the user setup flow properly

### Alternative Approaches

**Alternative 1: Remove onboarding entirely**
- Pro: Simpler user experience, no setup friction
- Con: Users miss important feature discovery, lose guided introduction
- **Rejected**: Onboarding system is well-designed and provides value

**Alternative 2: Make onboarding optional**
- Pro: Users can skip if they want
- Con: Adds complexity, many users might skip and miss features
- **Consideration**: Could be added as future enhancement (skip button)

**Alternative 3: Async onboarding in background**
- Pro: Users can use bot immediately while onboarding happens
- Con: Significantly more complex, could confuse users
- **Rejected**: Current flow is well-designed, just needs to be enabled

**Why the proposed approach is better:**

The simplest fix is the best - the onboarding system is already fully implemented, tested, and working. It just needs to be reconnected. This is a one-line change (uncommenting code) with minimal risk.

### Risks and Considerations

**Risks:**
- **Low risk**: The code being uncommented is the original implementation that was working before
- **Testing needed**: Should verify all three onboarding paths (quick, full, chat) work correctly
- **Database state**: Some users might be stuck in incomplete onboarding state in the database - may need cleanup script

**Side effects to watch for:**
- Users who were created during the debugging period might have incomplete onboarding state
- Timezone validation re-enablement might interrupt existing users who don't have timezone set

**Breaking changes:**
- None - this restores original functionality

### Testing Requirements

**Test Cases Needed:**

1. **Test Quick Start path** - Verify user can complete quick onboarding
   - Start bot with `/start`
   - Select "Quick Start 🚀"
   - Set timezone
   - Answer language preference
   - Select focus area
   - Complete onboarding
   - Verify user can use bot normally

2. **Test Full Tour path** - Verify user can complete full onboarding
   - Start bot with `/start`
   - Select "Show Me Around 🎬"
   - Complete all demo steps
   - Verify onboarding completes
   - Verify user can use bot normally

3. **Test Just Chat path** - Verify immediate completion
   - Start bot with `/start`
   - Select "Just Chat 💬"
   - Verify onboarding completes immediately
   - Verify user can chat normally

4. **Test edge cases**
   - Invalid path selection
   - Invalid timezone input
   - User sends unrelated message during onboarding
   - User tries to use commands during onboarding

5. **Test existing users** - Verify no regression
   - Users who already completed onboarding should not be affected
   - Users should not see onboarding prompts again

**Validation Commands:**

```bash
# Test with a fresh user (requires Telegram account)
# 1. Start conversation with bot
# 2. Send: /start
# 3. Select: Quick Start 🚀
# 4. Provide timezone: America/New_York
# 5. Select language preference
# 6. Select focus: 🍽️ Track nutrition
# 7. Verify completion message appears

# Check database state
psql -d health_agent -c "SELECT user_id, onboarding_path, current_step, completed_at FROM user_onboarding_state ORDER BY started_at DESC LIMIT 5;"

# Run existing integration tests
pytest tests/integration/test_onboarding_flow.py -v

# Run all onboarding tests
pytest tests/unit/test_onboarding_state.py tests/integration/test_onboarding_flow.py -v
```

## Implementation Plan

### Phase 1: Core Fix (Immediate)
1. Uncomment onboarding check in `src/bot.py` (lines 676-681)
2. Test all three onboarding paths manually
3. Run automated tests
4. Deploy to production

### Phase 2: Timezone Validation (Follow-up)
1. Review timezone validation logic
2. Decide if it should be re-enabled or removed
3. Test timezone setup flow
4. Deploy if re-enabling

### Phase 3: Data Cleanup (Optional)
1. Identify users stuck in incomplete onboarding state
2. Create migration script to mark them as complete or reset them
3. Run cleanup script

### Phase 4: Monitoring (Ongoing)
1. Monitor new user onboarding completion rates
2. Track where users drop off in the flow
3. Identify any remaining issues

## Next Steps

1. ✅ **Review this RCA document** - Completed
2. **Implement the fix** - Uncomment the onboarding check in src/bot.py
3. **Test thoroughly** - Run manual and automated tests
4. **Deploy** - Commit and push changes
5. **Monitor** - Watch for new user onboarding success

---

**Analysis completed**: 2025-12-19
**Analyst**: Claude Code
**Status**: Ready for implementation
