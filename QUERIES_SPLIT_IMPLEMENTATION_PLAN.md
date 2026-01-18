# Implementation Plan: Split queries.py by Domain

**Epic:** 007 | **Priority:** HIGH | **Time Estimate:** 4 hours

---

## Executive Summary

This plan details the systematic refactoring of `src/db/queries.py` (3,270 lines) into domain-specific modules. The file has grown to contain 93 functions across 7 distinct domains, making it difficult to maintain and navigate.

**Goal:** Create `src/db/queries/` directory with domain-organized modules while maintaining 100% backward compatibility through re-exports.

---

## Current State Analysis

### File Statistics
- **Total Lines:** 3,270
- **Total Functions:** 93 functions
- **Import Dependencies:** 38 files across the codebase
- **Primary Consumers:**
  - `src/bot.py` (main Telegram bot)
  - `src/api/routes.py` (REST API)
  - `src/handlers/*` (feature handlers)
  - `src/gamification/*` (gamification system)
  - `src/agent/*` (AI agent tools)

### Current Import Patterns
Two patterns are used across the codebase:
1. **Named imports:** `from src.db.queries import create_user, user_exists`
2. **Module imports:** `from src.db import queries` → `queries.create_user()`

**Critical:** Both patterns MUST continue to work after the split.

---

## Proposed Architecture

### Directory Structure
```
src/db/
├── queries.py              # BECOMES: __init__.py (re-export module)
└── queries/
    ├── __init__.py        # Re-exports all functions for backward compatibility
    ├── user.py            # 16 functions - user profiles, auth, onboarding
    ├── food.py            # 5 functions - food entries, nutrition data
    ├── tracking.py        # 5 functions - tracking categories, sleep entries
    ├── reminders.py       # 26 functions - reminders, completions, analytics
    ├── gamification.py    # 27 functions - XP, achievements, streaks
    ├── conversation.py    # 3 functions - conversation history
    └── dynamic_tools.py   # 11 functions - dynamic tool management
```

### Module Breakdown

#### 1. **user.py** (16 functions, ~450 lines)
**Scope:** User profiles, authentication, subscription, onboarding, audit

**Functions:**
- `create_user(telegram_id)` - Create new user
- `user_exists(telegram_id)` - Check if user exists
- `create_invite_code()` - Create invite code
- `validate_invite_code(code)` - Validate invite code
- `use_invite_code(code, telegram_id)` - Mark code as used
- `get_user_subscription_status(telegram_id)` - Get subscription status
- `get_master_codes()` - Get master codes
- `deactivate_invite_code(code)` - Deactivate code
- `get_onboarding_state(user_id)` - Get onboarding state
- `start_onboarding(user_id, path)` - Start onboarding
- `update_onboarding_step(user_id, step, data)` - Update step
- `complete_onboarding(user_id)` - Mark complete
- `log_feature_discovery(user_id, feature)` - Log discovery
- `log_feature_usage(user_id, feature)` - Log usage
- `audit_profile_update()` - Audit profile changes
- `audit_preference_update()` - Audit preference changes

**Imports:**
```python
from src.models.user import UserProfile
```

---

#### 2. **food.py** (5 functions, ~650 lines)
**Scope:** Food entries, nutrition tracking, corrections, audit

**Functions:**
- `save_food_entry(entry)` - Save food entry
- `update_food_entry(entry_id, ...)` - Update with corrections
- `get_recent_food_entries(user_id, limit)` - Get recent entries
- `get_food_entries_by_date(user_id, start, end)` - Get by date range
- `has_logged_food_in_window(user_id, hours)` - Check logging window

**Imports:**
```python
from src.models.food import FoodEntry
```

---

#### 3. **tracking.py** (5 functions, ~500 lines)
**Scope:** Custom tracking categories, health metrics, sleep entries

**Functions:**
- `create_tracking_category(category)` - Create category
- `get_tracking_categories(user_id, active_only)` - Get categories
- `save_tracking_entry(entry)` - Save entry
- `save_sleep_entry(entry)` - Save sleep data
- `get_sleep_entries(user_id, days)` - Get sleep history

**Imports:**
```python
from src.models.tracking import TrackingCategory, TrackingEntry
from src.models.sleep import SleepEntry
```

---

#### 4. **reminders.py** (26 functions, ~400 lines)
**Scope:** Reminders, scheduling, completions, analytics, patterns

**Functions:**

*Basic CRUD:*
- `create_reminder(reminder)` - Create reminder
- `get_active_reminders(user_id)` - Get active reminders
- `get_active_reminders_all()` - Get all reminders
- `get_reminder_by_id(reminder_id)` - Get by ID
- `delete_reminder(reminder_id, user_id)` - Delete reminder
- `update_reminder(reminder_id, ...)` - Update reminder
- `find_duplicate_reminders(user_id)` - Find duplicates
- `deactivate_duplicate_reminders(user_id)` - Remove duplicates

*Completion Tracking:*
- `save_reminder_completion(user_id, reminder_id, ...)` - Log completion
- `get_reminder_completions(user_id, reminder_id, ...)` - Get history
- `has_completed_reminder_today(user_id, reminder_id)` - Check today
- `save_reminder_skip(user_id, reminder_id, reason)` - Log skip
- `update_completion_note(completion_id, note)` - Add note
- `check_missed_reminder_grace_period(...)` - Check missed

*Streak Calculations:*
- `calculate_current_streak(user_id, reminder_id)` - Current streak
- `calculate_best_streak(user_id, reminder_id)` - Best streak

*Analytics:*
- `get_reminder_analytics(user_id, reminder_id, days)` - Full analytics
- `analyze_day_of_week_patterns(user_id, reminder_id, days)` - DOW patterns
- `get_multi_reminder_comparison(user_id)` - Compare reminders
- `detect_timing_patterns(user_id, reminder_id, days)` - Timing analysis
- `detect_difficult_days(user_id, reminder_id, days)` - Problem days
- `generate_adaptive_suggestions(user_id, reminder_id)` - AI suggestions

*Sleep Quiz:*
- `get_sleep_quiz_settings(user_id)` - Get settings
- `save_sleep_quiz_settings(settings)` - Save settings
- `get_all_enabled_sleep_quiz_users()` - Get enabled users
- `save_sleep_quiz_submission(submission)` - Save submission
- `get_submission_patterns(user_id, days)` - Get patterns

**Imports:**
```python
from src.models.reminder import Reminder
from src.models.sleep_settings import SleepQuizSettings, SleepQuizSubmission
```

---

#### 5. **gamification.py** (27 functions, ~270 lines)
**Scope:** XP system, achievements, streaks, leaderboard

**Functions:**

*XP System:*
- `get_user_xp_data(user_id)` - Get XP data
- `update_user_xp(user_id, xp_data)` - Update XP
- `add_xp_transaction(user_id, amount, reason)` - Add XP
- `get_xp_transactions(user_id, limit)` - Get history
- `get_user_xp_level(user_id)` - API wrapper

*Streak System:*
- `get_user_streak(user_id, streak_type, source_id)` - Get streak
- `update_user_streak(user_id, streak_type, streak_data)` - Update streak
- `get_all_user_streaks(user_id)` - Get all streaks
- `get_user_streaks(user_id)` - API wrapper

*Achievement System:*
- `get_all_achievements()` - Get achievement definitions
- `get_achievement_by_key(key)` - Get by key
- `get_user_achievement_unlocks(user_id)` - Get unlocked
- `add_user_achievement(user_id, achievement_id)` - Unlock achievement
- `has_user_unlocked_achievement(user_id, achievement_id)` - Check unlocked
- `get_user_achievements(user_id)` - Alias
- `unlock_user_achievement(user_id, achievement_id)` - Alias
- `unlock_achievement(user_id, achievement_id)` - Legacy function

*Helper Functions (for achievement checks):*
- `count_user_completions(user_id)` - Total completions
- `count_early_completions(user_id)` - Early completions
- `count_active_reminders(user_id, tracking_enabled)` - Active count
- `count_perfect_completion_days(user_id)` - Perfect days
- `check_recovery_pattern(user_id, threshold)` - Recovery check
- `count_stats_views(user_id)` - Stats views

**Imports:**
```python
# No specific model imports needed - gamification works with raw data
```

---

#### 6. **conversation.py** (3 functions, NEW)
**Scope:** Conversation history and memory management

**Functions:**
- `save_conversation_message(user_id, role, content, ...)` - Save message
- `get_conversation_history(user_id, limit, ...)` - Get history
- `clear_conversation_history(user_id)` - Clear history

**Imports:**
```python
# Standard imports only
```

---

#### 7. **dynamic_tools.py** (11 functions, NEW)
**Scope:** Dynamic AI tool management system

**Functions:**
- `save_dynamic_tool(...)` - Save new tool
- `get_all_enabled_tools()` - Get enabled tools
- `get_tool_by_name(tool_name)` - Get by name
- `update_tool_version(...)` - Update tool
- `disable_tool(tool_id)` - Disable tool
- `enable_tool(tool_id)` - Enable tool
- `log_tool_execution(...)` - Log execution
- `create_tool_approval_request(...)` - Request approval
- `approve_tool(tool_id, approver_id)` - Approve tool
- `reject_tool(tool_id, approver_id, reason)` - Reject tool
- `get_pending_approvals()` - Get pending

**Imports:**
```python
# Standard imports only
```

---

## Implementation Strategy

### Phase 1: Setup (30 minutes)

#### Step 1.1: Create Directory Structure
```bash
mkdir -p src/db/queries
touch src/db/queries/__init__.py
```

#### Step 1.2: Backup Current File
```bash
cp src/db/queries.py src/db/queries.py.backup
```

#### Step 1.3: Create Module Skeletons
Create empty files with standard headers:
- `src/db/queries/user.py`
- `src/db/queries/food.py`
- `src/db/queries/tracking.py`
- `src/db/queries/reminders.py`
- `src/db/queries/gamification.py`
- `src/db/queries/conversation.py`
- `src/db/queries/dynamic_tools.py`

Each file should start with:
```python
"""[Domain] database queries"""
import json
import logging
from typing import Optional
from datetime import datetime
from src.db.connection import db

logger = logging.getLogger(__name__)
```

---

### Phase 2: Extract Functions (2 hours)

#### Extraction Order (Low Risk → High Risk)

**Priority 1: Self-Contained Modules (30 min)**
1. `conversation.py` - No dependencies
2. `dynamic_tools.py` - No dependencies
3. `food.py` - Minimal dependencies

**Priority 2: Core Domain Modules (45 min)**
4. `tracking.py` - Clear boundaries
5. `user.py` - Core functionality

**Priority 3: Complex Interdependent Modules (45 min)**
6. `reminders.py` - Large, many functions
7. `gamification.py` - Depends on reminders

#### Extraction Process (Per Module)

For each module:

1. **Copy functions** from `queries.py` to the new module file
2. **Copy relevant imports** (models, etc.)
3. **Test the module** can be imported: `python -c "from src.db.queries.user import create_user"`
4. **DO NOT delete from queries.py yet** (keep for backward compatibility testing)

#### Key Considerations

**Duplicate Functions to Remove:**
- Lines 2507-2538: Old `get_all_achievements()` - DELETE (keep newer version at 3033-3050)
- Lines 2541-2577: Old `get_user_achievements()` - KEEP but clarify it's different from the alias

**Functions to Move:**
- `calculate_current_streak` → Should move to `gamification.py` (it's streak logic)
- `calculate_best_streak` → Should move to `gamification.py` (it's streak logic)
- BUT: Keep in `reminders.py` temporarily for backward compat, re-import from gamification

---

### Phase 3: Create Re-Export Layer (45 minutes)

#### Step 3.1: Create `src/db/queries/__init__.py`

This file will re-export ALL functions to maintain backward compatibility:

```python
"""
Database queries - Re-export all functions for backward compatibility.

After refactoring, this module maintains the same API as the old monolithic
queries.py file. All imports like 'from src.db.queries import create_user'
continue to work unchanged.
"""

# User operations
from src.db.queries.user import (
    create_user,
    user_exists,
    create_invite_code,
    validate_invite_code,
    use_invite_code,
    get_user_subscription_status,
    get_master_codes,
    deactivate_invite_code,
    get_onboarding_state,
    start_onboarding,
    update_onboarding_step,
    complete_onboarding,
    log_feature_discovery,
    log_feature_usage,
    audit_profile_update,
    audit_preference_update,
)

# Food operations
from src.db.queries.food import (
    save_food_entry,
    update_food_entry,
    get_recent_food_entries,
    get_food_entries_by_date,
    has_logged_food_in_window,
)

# Tracking operations
from src.db.queries.tracking import (
    create_tracking_category,
    get_tracking_categories,
    save_tracking_entry,
    save_sleep_entry,
    get_sleep_entries,
)

# Reminder operations
from src.db.queries.reminders import (
    create_reminder,
    get_active_reminders,
    get_active_reminders_all,
    get_reminder_by_id,
    delete_reminder,
    update_reminder,
    find_duplicate_reminders,
    deactivate_duplicate_reminders,
    save_reminder_completion,
    get_reminder_completions,
    has_completed_reminder_today,
    save_reminder_skip,
    update_completion_note,
    check_missed_reminder_grace_period,
    calculate_current_streak,
    calculate_best_streak,
    get_reminder_analytics,
    analyze_day_of_week_patterns,
    get_multi_reminder_comparison,
    detect_timing_patterns,
    detect_difficult_days,
    generate_adaptive_suggestions,
    get_sleep_quiz_settings,
    save_sleep_quiz_settings,
    get_all_enabled_sleep_quiz_users,
    save_sleep_quiz_submission,
    get_submission_patterns,
)

# Gamification operations
from src.db.queries.gamification import (
    get_user_xp_data,
    update_user_xp,
    add_xp_transaction,
    get_xp_transactions,
    get_user_xp_level,
    get_user_streak,
    update_user_streak,
    get_all_user_streaks,
    get_user_streaks,
    get_all_achievements,
    get_achievement_by_key,
    get_user_achievement_unlocks,
    add_user_achievement,
    has_user_unlocked_achievement,
    get_user_achievements,
    unlock_user_achievement,
    unlock_achievement,
    count_user_completions,
    count_early_completions,
    count_active_reminders,
    count_perfect_completion_days,
    check_recovery_pattern,
    count_stats_views,
)

# Conversation operations
from src.db.queries.conversation import (
    save_conversation_message,
    get_conversation_history,
    clear_conversation_history,
)

# Dynamic tool operations
from src.db.queries.dynamic_tools import (
    save_dynamic_tool,
    get_all_enabled_tools,
    get_tool_by_name,
    update_tool_version,
    disable_tool,
    enable_tool,
    log_tool_execution,
    create_tool_approval_request,
    approve_tool,
    reject_tool,
    get_pending_approvals,
)

# Re-export for 'from src.db import queries' pattern
__all__ = [
    # User
    "create_user", "user_exists", "create_invite_code", "validate_invite_code",
    "use_invite_code", "get_user_subscription_status", "get_master_codes",
    "deactivate_invite_code", "get_onboarding_state", "start_onboarding",
    "update_onboarding_step", "complete_onboarding", "log_feature_discovery",
    "log_feature_usage", "audit_profile_update", "audit_preference_update",

    # Food
    "save_food_entry", "update_food_entry", "get_recent_food_entries",
    "get_food_entries_by_date", "has_logged_food_in_window",

    # Tracking
    "create_tracking_category", "get_tracking_categories", "save_tracking_entry",
    "save_sleep_entry", "get_sleep_entries",

    # Reminders
    "create_reminder", "get_active_reminders", "get_active_reminders_all",
    "get_reminder_by_id", "delete_reminder", "update_reminder",
    "find_duplicate_reminders", "deactivate_duplicate_reminders",
    "save_reminder_completion", "get_reminder_completions",
    "has_completed_reminder_today", "save_reminder_skip", "update_completion_note",
    "check_missed_reminder_grace_period", "calculate_current_streak",
    "calculate_best_streak", "get_reminder_analytics", "analyze_day_of_week_patterns",
    "get_multi_reminder_comparison", "detect_timing_patterns", "detect_difficult_days",
    "generate_adaptive_suggestions", "get_sleep_quiz_settings",
    "save_sleep_quiz_settings", "get_all_enabled_sleep_quiz_users",
    "save_sleep_quiz_submission", "get_submission_patterns",

    # Gamification
    "get_user_xp_data", "update_user_xp", "add_xp_transaction", "get_xp_transactions",
    "get_user_xp_level", "get_user_streak", "update_user_streak",
    "get_all_user_streaks", "get_user_streaks", "get_all_achievements",
    "get_achievement_by_key", "get_user_achievement_unlocks", "add_user_achievement",
    "has_user_unlocked_achievement", "get_user_achievements", "unlock_user_achievement",
    "unlock_achievement", "count_user_completions", "count_early_completions",
    "count_active_reminders", "count_perfect_completion_days", "check_recovery_pattern",
    "count_stats_views",

    # Conversation
    "save_conversation_message", "get_conversation_history", "clear_conversation_history",

    # Dynamic Tools
    "save_dynamic_tool", "get_all_enabled_tools", "get_tool_by_name",
    "update_tool_version", "disable_tool", "enable_tool", "log_tool_execution",
    "create_tool_approval_request", "approve_tool", "reject_tool", "get_pending_approvals",
]
```

#### Step 3.2: Replace Original queries.py

**Option A (Recommended): Move and Replace**
```bash
# Move original to backup
mv src/db/queries.py src/db/queries_monolith_backup.py

# The directory src/db/queries/ with __init__.py becomes the new "queries.py"
# Python treats src/db/queries/__init__.py as src/db/queries
```

**Result:** `from src.db.queries import create_user` automatically uses `src/db/queries/__init__.py`

---

### Phase 4: Testing & Validation (45 minutes)

#### Step 4.1: Import Tests

Create `tests/test_queries_split.py`:

```python
"""Test that queries split maintains backward compatibility"""
import pytest

def test_named_imports():
    """Test that named imports still work"""
    from src.db.queries import (
        create_user, user_exists,
        save_food_entry, get_recent_food_entries,
        create_reminder, get_active_reminders,
        get_user_xp_data, get_all_achievements,
    )

    # All functions should be callable
    assert callable(create_user)
    assert callable(user_exists)
    assert callable(save_food_entry)
    assert callable(create_reminder)
    assert callable(get_user_xp_data)


def test_module_imports():
    """Test that module imports still work"""
    from src.db import queries

    # Should be able to access functions via module
    assert hasattr(queries, 'create_user')
    assert hasattr(queries, 'save_food_entry')
    assert hasattr(queries, 'create_reminder')
    assert hasattr(queries, 'get_user_xp_data')
    assert callable(queries.create_user)


def test_direct_module_imports():
    """Test that direct module imports work"""
    from src.db.queries.user import create_user
    from src.db.queries.food import save_food_entry
    from src.db.queries.reminders import create_reminder
    from src.db.queries.gamification import get_user_xp_data

    assert callable(create_user)
    assert callable(save_food_entry)
    assert callable(create_reminder)
    assert callable(get_user_xp_data)


def test_all_functions_exported():
    """Test that all functions are in __all__"""
    from src.db import queries

    # Check critical functions from each domain
    critical_functions = [
        # User
        'create_user', 'user_exists', 'validate_invite_code',
        # Food
        'save_food_entry', 'update_food_entry',
        # Tracking
        'save_sleep_entry', 'create_tracking_category',
        # Reminders
        'create_reminder', 'save_reminder_completion', 'get_reminder_analytics',
        # Gamification
        'get_user_xp_data', 'get_all_achievements', 'add_xp_transaction',
        # Conversation
        'save_conversation_message', 'get_conversation_history',
        # Dynamic tools
        'save_dynamic_tool', 'approve_tool',
    ]

    for func_name in critical_functions:
        assert hasattr(queries, func_name), f"Missing function: {func_name}"
```

Run tests:
```bash
pytest tests/test_queries_split.py -v
```

#### Step 4.2: Integration Tests

Run existing test suite to ensure nothing broke:
```bash
# Run all tests
pytest tests/ -v

# Focus on database tests
pytest tests/integration/ -v

# Focus on API tests
pytest tests/api/ -v
```

#### Step 4.3: Bot Smoke Test

Start the bot and verify basic operations:
```bash
python -m src.main
```

Test operations:
1. Send a message (conversation queries)
2. Log food (food queries)
3. Complete a reminder (reminder queries)
4. Check XP (gamification queries)

---

### Phase 5: Cleanup & Documentation (30 minutes)

#### Step 5.1: Remove Backup File

Once all tests pass:
```bash
rm src/db/queries_monolith_backup.py
```

#### Step 5.2: Update Documentation

**Update `DEVELOPMENT.md`:**
```markdown
## Database Queries

Database queries are organized by domain in `src/db/queries/`:

- **user.py** - User profiles, authentication, onboarding
- **food.py** - Food entries and nutrition tracking
- **tracking.py** - Custom tracking categories and health metrics
- **reminders.py** - Reminder system and completion analytics
- **gamification.py** - XP, achievements, and streaks
- **conversation.py** - Conversation history
- **dynamic_tools.py** - Dynamic AI tool management

All functions are re-exported through `src/db/queries/__init__.py` for
backward compatibility. Both import patterns work:
- `from src.db.queries import create_user`
- `from src.db import queries` → `queries.create_user()`
```

#### Step 5.3: Add Module Docstrings

Each module should have a comprehensive docstring:

```python
"""
User database queries

This module handles all user-related database operations including:
- User creation and authentication
- Subscription and invite code management
- Onboarding flow tracking
- Feature discovery and usage analytics
- Profile and preference audit logging

All functions use async/await with the database connection pool.
"""
```

---

## Risk Mitigation

### Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Import errors break production | HIGH | MEDIUM | Re-export layer ensures backward compatibility |
| Missing function in re-exports | MEDIUM | MEDIUM | Comprehensive test suite verifies all exports |
| Circular import dependencies | MEDIUM | LOW | Clear dependency hierarchy (user → food → reminders → gamification) |
| Test suite doesn't catch real issues | HIGH | LOW | Manual smoke testing of critical paths |
| Git merge conflicts during refactor | LOW | LOW | Work in dedicated branch, complete in one session |

### Rollback Plan

If critical issues arise:

1. **Immediate Rollback:**
```bash
# Restore backup
mv src/db/queries_monolith_backup.py src/db/queries.py
rm -rf src/db/queries/  # Remove directory

# Restart services
./stop_bot.sh
./start_bot.sh
```

2. **Partial Rollback:**
Keep directory structure but temporarily redirect imports:
```python
# In src/db/queries/__init__.py
from src.db.queries_monolith_backup import *
```

---

## Success Criteria

### Definition of Done

- [ ] All 93 functions split into 7 domain modules
- [ ] `src/db/queries/__init__.py` re-exports all functions
- [ ] All existing imports continue to work (both patterns)
- [ ] Test suite passes 100% (no new failures)
- [ ] Bot starts successfully
- [ ] Manual smoke tests pass (message, food log, reminder, XP check)
- [ ] Original `queries.py` removed
- [ ] Documentation updated
- [ ] No duplicate functions (removed old `get_all_achievements`)

### Performance Metrics

**Before:**
- Single 3,270-line file
- All functions in one namespace
- Hard to find specific queries

**After:**
- 7 focused modules (~300-650 lines each)
- Clear domain separation
- Easy to locate and maintain queries
- Same runtime performance (imports are cached)

---

## Timeline

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Phase 1: Setup | 30 min | 0:30 |
| Phase 2: Extract Functions | 2 hours | 2:30 |
| Phase 3: Re-Export Layer | 45 min | 3:15 |
| Phase 4: Testing | 45 min | 4:00 |
| Phase 5: Cleanup | 30 min | **4:30** |

**Total Estimated Time:** 4.5 hours (includes buffer)

---

## Appendix: Function Mapping Reference

### Complete Function-to-Module Mapping

```
user.py (16):
  - create_user, user_exists
  - create_invite_code, validate_invite_code, use_invite_code
  - get_user_subscription_status, get_master_codes, deactivate_invite_code
  - get_onboarding_state, start_onboarding, update_onboarding_step, complete_onboarding
  - log_feature_discovery, log_feature_usage
  - audit_profile_update, audit_preference_update

food.py (5):
  - save_food_entry, update_food_entry, get_recent_food_entries
  - get_food_entries_by_date, has_logged_food_in_window

tracking.py (5):
  - create_tracking_category, get_tracking_categories, save_tracking_entry
  - save_sleep_entry, get_sleep_entries

reminders.py (26):
  - create_reminder, get_active_reminders, get_active_reminders_all, get_reminder_by_id
  - delete_reminder, update_reminder
  - find_duplicate_reminders, deactivate_duplicate_reminders
  - save_reminder_completion, get_reminder_completions, has_completed_reminder_today
  - save_reminder_skip, update_completion_note, check_missed_reminder_grace_period
  - calculate_current_streak, calculate_best_streak
  - get_reminder_analytics, analyze_day_of_week_patterns, get_multi_reminder_comparison
  - detect_timing_patterns, detect_difficult_days, generate_adaptive_suggestions
  - get_sleep_quiz_settings, save_sleep_quiz_settings, get_all_enabled_sleep_quiz_users
  - save_sleep_quiz_submission, get_submission_patterns

gamification.py (27):
  - get_user_xp_data, update_user_xp, add_xp_transaction, get_xp_transactions, get_user_xp_level
  - get_user_streak, update_user_streak, get_all_user_streaks, get_user_streaks
  - get_all_achievements, get_achievement_by_key, get_user_achievement_unlocks
  - add_user_achievement, has_user_unlocked_achievement
  - get_user_achievements, unlock_user_achievement, unlock_achievement
  - count_user_completions, count_early_completions, count_active_reminders
  - count_perfect_completion_days, check_recovery_pattern, count_stats_views

conversation.py (3):
  - save_conversation_message, get_conversation_history, clear_conversation_history

dynamic_tools.py (11):
  - save_dynamic_tool, get_all_enabled_tools, get_tool_by_name
  - update_tool_version, disable_tool, enable_tool
  - log_tool_execution, create_tool_approval_request
  - approve_tool, reject_tool, get_pending_approvals
```

---

## Questions & Answers

**Q: Why not update all imports across the codebase?**
A: The re-export layer ensures backward compatibility. We can optionally update imports to use domain-specific modules later as a separate, low-risk refactor.

**Q: Will this affect performance?**
A: No. Python caches module imports, so re-exporting has negligible overhead. The import happens once at startup.

**Q: Should we move streak functions from reminders to gamification?**
A: Yes, but keep them in reminders for now via re-import. We can refactor callers later.

**Q: What about the duplicate get_all_achievements functions?**
A: Keep the newer one (lines 3033-3050) which has more complete achievement data. Delete the older version.

**Q: Can we split this work across multiple PRs?**
A: Not recommended. The refactor should be atomic to avoid intermediate broken states. However, we could split into:
- PR 1: Create modules, keep queries.py
- PR 2: Add re-export layer, remove queries.py

---

## Implementation Checklist

### Pre-Implementation
- [ ] Review plan with team
- [ ] Ensure all tests pass on main branch
- [ ] Create feature branch: `git checkout -b refactor/split-queries-by-domain`

### Implementation
- [ ] **Phase 1:** Create directory structure
- [ ] **Phase 2:** Extract functions to domain modules
  - [ ] conversation.py
  - [ ] dynamic_tools.py
  - [ ] food.py
  - [ ] tracking.py
  - [ ] user.py
  - [ ] reminders.py
  - [ ] gamification.py
- [ ] **Phase 3:** Create re-export layer
  - [ ] Write `src/db/queries/__init__.py`
  - [ ] Move original queries.py to backup
  - [ ] Verify imports work
- [ ] **Phase 4:** Testing
  - [ ] Run import compatibility tests
  - [ ] Run full test suite
  - [ ] Manual smoke tests
- [ ] **Phase 5:** Cleanup
  - [ ] Remove backup file
  - [ ] Update documentation
  - [ ] Add module docstrings

### Post-Implementation
- [ ] Create PR with detailed description
- [ ] Request code review
- [ ] Merge to main after approval
- [ ] Monitor production for issues
- [ ] Close issue #72

---

**Plan Status:** READY FOR IMPLEMENTATION
**Next Step:** Begin Phase 1 - Setup
