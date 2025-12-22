# Root Cause Analysis: Issue #24 - Onboarding System Failures

**Issue:** #24
**Title:** Onboarding not working as it should
**Date:** 2025-12-22
**Status:** RCA Complete

---

## Problem Summary

The onboarding system exhibits multiple critical failures:
1. **Some users don't receive onboarding at all**
2. **Buttons appear but clicking them does nothing**
3. **"Quick Tour" appears as user's message text instead of triggering action**
4. **Buttons loop back repeatedly after user writes anything**
5. **Buttons persist beneath keyboard on mobile (not on laptop)**
6. **Users cannot escape the loop except by clicking the last option**

---

## Root Causes Identified

### Root Cause #1: **ReplyKeyboardMarkup vs InlineKeyboardMarkup Confusion**

**Severity:** CRITICAL
**Location:** `src/handlers/onboarding.py` - All onboarding flow functions

**Analysis:**

The entire onboarding system uses `ReplyKeyboardMarkup` instead of `InlineKeyboardMarkup`. These are fundamentally different:

**ReplyKeyboardMarkup:**
- Creates **custom keyboard buttons** that replace the default keyboard
- When clicked, sends the button TEXT as a regular message from the user
- Does NOT trigger callbacks
- Persists until explicitly removed with `ReplyKeyboardRemove()`
- Behavior: User clicks "Quick Tour" → Bot receives message "Quick Tour 🎬 (2 min)" as if user typed it

**InlineKeyboardMarkup:**
- Creates **inline buttons** attached to a specific message
- When clicked, triggers a callback_query (not a message)
- Automatically disappears when message is dismissed
- Requires callback handlers to process button clicks

**Evidence:**
```python
# src/handlers/onboarding.py:48-53
keyboard = [
    ["Quick Start 🚀 (30 sec)"],
    ["Show Me Around 🎬 (2 min)"],
    ["Just Chat 💬 (start now)"]
]
reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
```

**Why This Causes the Issues:**

1. **"Quick Tour appears as user's message"** → ReplyKeyboardMarkup sends button text as a message, not a callback
2. **Buttons do nothing** → No callback handlers registered, system expects callbacks but receives messages
3. **Buttons loop back** → When user sends ANY message, onboarding handler gets invoked but doesn't match the text patterns, re-displays the same screen
4. **Buttons persist on mobile** → `one_time_keyboard=True` is unreliable on mobile Telegram clients; ReplyKeyboard stays visible until explicitly removed

---

### Root Cause #2: **Message Routing Logic Relies on Text Pattern Matching**

**Severity:** HIGH
**Location:** `src/handlers/onboarding.py:63-100` (`handle_path_selection`)

**Analysis:**

The path selection handler uses fragile text pattern matching:

```python
# Lines 71-76
if "quick" in text or "🚀" in text:
    path = "quick"
elif "show" in text or "tour" in text or "around" in text or "🎬" in text:
    path = "full"
elif "chat" in text or "💬" in text:
    path = "chat"
```

**Problems:**
1. **Case sensitive** → User types "QUICK" → doesn't match (text is lowercased, but emoji checks aren't robust)
2. **Partial matches** → User types "I want to start chatting" → matches "chat" path unintentionally
3. **No exact matching** → User types anything with word "quick" → triggers quick path
4. **Relies on keyboard being used** → If user types manually instead of clicking, might trigger wrong path

**Why This Causes Issues:**
- When user writes anything during onboarding, the text matching fails
- Handler doesn't recognize the input → falls through to `else` block (lines 78-87)
- Shows path selection keyboard again → **LOOP BACK**

---

### Root Cause #3: **State Persistence Without Keyboard Removal**

**Severity:** MEDIUM
**Location:** Multiple functions in `src/handlers/onboarding.py`

**Analysis:**

Many onboarding steps create new `ReplyKeyboardMarkup` keyboards but don't explicitly remove the previous one:

```python
# Example: quick_start_timezone (line 175)
reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

# Example: quick_start_focus_selection (line 196)
reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
```

**Problem:**
- `one_time_keyboard=True` means keyboard *should* hide after one use
- **BUT:** On mobile clients, this flag is inconsistently respected
- Multiple keyboards stack → user sees old buttons beneath new ones
- When user clicks old button → sends old text → triggers wrong handler → confusion

**Why This Causes "Buttons beneath keyboard" on Mobile:**
- Mobile Telegram clients don't reliably hide `one_time_keyboard`
- Desktop clients implement it correctly → why it works on laptop
- Without explicit `ReplyKeyboardRemove()`, keyboards accumulate

---

### Root Cause #4: **Onboarding State Not Updated on Path Selection**

**Severity:** MEDIUM
**Location:** `src/handlers/onboarding.py:58` and `handle_path_selection:90`

**Analysis:**

When showing path selection:
```python
# Line 58
await start_onboarding(user_id, "pending")  # Will be set when user picks path
```

Then on selection:
```python
# Line 90
await start_onboarding(user_id, path)
```

**Potential Issue:**
- `start_onboarding()` might not properly update state if row already exists
- Need to verify database query logic

Let's check the database function:
```python
# src/db/queries.py:1030-1043
async def start_onboarding(user_id: str, path: str) -> None:
    """Initialize onboarding state for a user"""
    await cur.execute(
        """
        INSERT INTO user_onboarding_state (user_id, onboarding_path, current_step)
        VALUES (%s, %s, 'path_selection')
        ON CONFLICT (user_id) DO UPDATE SET
            onboarding_path = EXCLUDED.onboarding_path,
            current_step = 'path_selection',
            started_at = CURRENT_TIMESTAMP,
            last_interaction_at = CURRENT_TIMESTAMP
        """,
        (user_id, path)
    )
```

**Problem Found:**
- When called with `path="pending"`, sets `current_step='path_selection'` ✓
- When called again with actual path, **RESETS `current_step` BACK TO 'path_selection'** ✗
- This means after user selects a path, the state is reset → onboarding breaks

---

### Root Cause #5: **Missing `/onboard` Command Handler**

**Severity:** LOW
**Location:** `src/bot.py` - No command registered

**Analysis:**

Issue description states:
> "if they want they can type /onboard and do it again"

**Problem:**
- No `/onboard` command exists in codebase
- User expectation: Can restart onboarding via `/onboard`
- Reality: Command does nothing

**Impact:**
- Users who complete onboarding can't redo it
- No way to test onboarding without database wipes

---

## System Flow Analysis

### Expected Flow:
```
1. User sends /start
   ↓
2. handle_onboarding_start() shows path selection with InlineKeyboard
   ↓
3. User clicks button → callback_query triggered
   ↓
4. Callback handler receives "quick" / "full" / "chat" data
   ↓
5. start_onboarding(user_id, path) updates state
   ↓
6. Route to appropriate first step
   ↓
7. Progress through onboarding
   ↓
8. complete_onboarding() marks complete
   ↓
9. User proceeds to normal usage
```

### Actual Flow:
```
1. User sends /start
   ↓
2. handle_onboarding_start() shows path selection with ReplyKeyboard
   ↓
3. User clicks button → TEXT MESSAGE sent (not callback)
   ↓
4. handle_onboarding_message() receives message
   ↓
5. current_step = "path_selection" → calls handle_path_selection()
   ↓
6. Text matching logic tries to parse "Quick Start 🚀 (30 sec)"
   ↓
7. If matched: start_onboarding(user_id, path) RESETS current_step to "path_selection"
   ↓
8. State is now inconsistent
   ↓
9. Next message → routes to handle_path_selection again → LOOP
   ↓
10. User stuck in loop
```

---

## Evidence of Issues

### Issue #1: "Some users don't get onboarding at all"

**Hypothesis:** Users who skip initial message or whose messages don't match patterns

**Code Path:**
- If user types anything other than matching text → falls into `else` block
- `else` block shows path selection again
- If user continues typing instead of clicking → never progresses

### Issue #2: "Buttons appear but clicking does nothing"

**Root Cause:** ReplyKeyboardMarkup doesn't trigger actions, just sends text

**Evidence:**
- All onboarding keyboards use `ReplyKeyboardMarkup`
- No callback handlers registered for onboarding
- System expects messages, not callbacks

### Issue #3: "Quick Tour comes up as their message"

**Root Cause:** ReplyKeyboardMarkup sends button text as user message

**Evidence:**
- When user clicks "Quick Tour 🎬 (2 min)" button
- Telegram sends message: `text = "Quick Tour 🎬 (2 min)"`
- Bot receives this as normal message from user
- User sees their own message bubble

### Issue #4: "If they write something else, option buttons come back"

**Root Cause:** Text doesn't match patterns → handler shows path selection again

**Code Path:**
```python
# Lines 78-87
else:
    # Invalid selection, show options again
    await update.message.reply_text(
        "Please choose one of the three options:",
        reply_markup=ReplyKeyboardMarkup([...])
    )
    return
```

### Issue #5: "If they click last option they can continue using"

**Why "Just Chat" works:**
- "Just Chat" path calls `complete_onboarding(user_id)` immediately (line 457)
- Marks onboarding as complete
- Future messages bypass onboarding check (line 696: `if onboarding and not onboarding.get('completed_at')`)
- User escapes the loop

### Issue #6: "Buttons beneath keyboard on mobile, not laptop"

**Root Cause:** Mobile clients don't respect `one_time_keyboard=True` reliably

**Evidence:**
- Desktop Telegram implements keyboard hiding correctly
- Mobile clients (especially Android) have inconsistent behavior
- Without explicit `ReplyKeyboardRemove()`, keyboards persist

---

## Impact Assessment

**User Experience:**
- **Critical:** New users cannot onboard → cannot use bot
- **Critical:** Stuck in onboarding loop → frustration, abandonment
- **High:** Confusion from seeing own button text as messages
- **Medium:** Keyboard UI clutter on mobile

**Business Impact:**
- **High:** 77% of users abandon apps within 3 days (industry stat from ONBOARDING_STRATEGY.md)
- **High:** First 30 seconds determine retention → onboarding failures = churn
- **Medium:** Support burden from users reporting issues

**Technical Debt:**
- **High:** Fundamental architecture issue (wrong keyboard type)
- **Medium:** Fragile text matching logic
- **Low:** Missing `/onboard` command

---

## Affected Components

### Files Requiring Changes:
1. **`src/handlers/onboarding.py`** (PRIMARY)
   - All keyboard implementations
   - All handler functions
   - Message routing logic

2. **`src/bot.py`**
   - Need to register callback handlers for onboarding buttons
   - Add `/onboard` command handler

3. **`src/db/queries.py`**
   - Fix `start_onboarding()` to not reset `current_step`

4. **Database migrations (possibly)**
   - May need to clear corrupted onboarding states

### Functions Requiring Refactor:
- `handle_onboarding_start()` → Switch to InlineKeyboard
- `handle_path_selection()` → Remove, replace with callback handler
- `quick_start_timezone()` → Fix keyboard
- `quick_start_focus_selection()` → Fix keyboard
- `full_tour_*()` functions → Fix all keyboards
- All step handlers → Add explicit `ReplyKeyboardRemove()` where appropriate

---

## Recommended Fix Strategy

### Phase 1: Critical Fixes (Immediate)
1. **Replace all ReplyKeyboardMarkup with InlineKeyboardMarkup** in onboarding flow
2. **Implement callback_query handlers** for all onboarding buttons
3. **Fix `start_onboarding()`** to not reset state incorrectly
4. **Add explicit `ReplyKeyboardRemove()`** when transitioning between steps

### Phase 2: Robustness (Short-term)
1. **Add `/onboard` command** to restart onboarding
2. **Add state validation** to detect and recover from corrupted states
3. **Add logging** for better debugging
4. **Add user-facing error messages** when onboarding breaks

### Phase 3: Testing (Before deployment)
1. **Test on mobile** (Android + iOS)
2. **Test on desktop**
3. **Test all three paths:** Quick / Full / Chat
4. **Test edge cases:** Typing instead of clicking, clicking old buttons, etc.

---

## Testing Checklist

### New User Onboarding:
- [ ] User receives path selection with inline buttons
- [ ] Clicking "Quick Start" triggers quick flow
- [ ] Clicking "Show Me Around" triggers full tour
- [ ] Clicking "Just Chat" completes onboarding immediately
- [ ] Buttons don't persist after clicking
- [ ] No button text appears as user messages

### Quick Start Path:
- [ ] Timezone setup works (location + text input)
- [ ] Focus selection works
- [ ] Feature demo appropriate to selected focus
- [ ] Completion message appears
- [ ] Onboarding marked complete in database

### Full Tour Path:
- [ ] All demo steps appear in sequence
- [ ] Skip buttons work
- [ ] Final completion message appears
- [ ] Onboarding marked complete in database

### Mobile-Specific:
- [ ] Keyboards don't stack on Android
- [ ] Keyboards don't stack on iOS
- [ ] Inline buttons work correctly
- [ ] No orphaned reply keyboards

### Edge Cases:
- [ ] User types instead of clicking → graceful handling
- [ ] User sends /start during onboarding → reset or continue?
- [ ] User sends `/onboard` after completion → restarts
- [ ] User closes app mid-onboarding → state persists, can resume

---

## Additional Observations

### Code Quality Issues Found:
1. **Inconsistent state management:** Mix of database state and handler logic
2. **No error handling:** What if database query fails?
3. **No timeout logic:** User stuck in onboarding forever if they abandon
4. **No analytics:** Can't track where users drop off
5. **Hard-coded text:** Difficult to A/B test or internationalize

### Design Considerations:
1. **Consider ConversationHandler:** Would provide more robust state management (but requires significant refactor)
2. **Consider timeout/expiry:** Auto-complete onboarding after 15 minutes of inactivity
3. **Consider progressive disclosure:** Maybe onboarding is too long? (per ONBOARDING_STRATEGY.md, users abandon in 30 seconds)

---

## Conclusion

The onboarding system has **fundamental architectural flaws** due to using the wrong keyboard type (`ReplyKeyboardMarkup` instead of `InlineKeyboardMarkup`). This causes cascading failures:

1. Buttons send text messages instead of triggering callbacks
2. Text matching logic is fragile and fails often
3. Failed matches cause loop-back to path selection
4. Reply keyboards persist on mobile, creating UI confusion
5. State management has bugs that reset progress

**The fix requires:**
- Complete refactor of keyboard implementation
- Addition of callback handlers
- Database query fixes
- Explicit keyboard cleanup

**Estimated effort:** ~4-6 hours for full implementation + testing

**Risk:** HIGH - Changes touch core onboarding flow, must be thoroughly tested

---

## Next Steps

1. ✅ RCA Complete
2. ⏳ Implement fix (NEXT)
3. ⏳ Test on all platforms
4. ⏳ Deploy and monitor
5. ⏳ Add analytics to track success

---

**End of RCA**
