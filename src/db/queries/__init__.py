"""
Database queries - Re-export all functions for backward compatibility.

After refactoring, this module maintains the same API as the old monolithic
queries.py file. All imports like 'from src.db.queries import create_user'
continue to work unchanged.

Module organization:
- user.py: User profiles, authentication, onboarding, subscriptions
- food.py: Food entries, nutrition tracking, corrections
- tracking.py: Custom tracking categories, health metrics, sleep
- reminders.py: Reminder system, completions, analytics, streaks
- gamification.py: XP system, achievements, streaks, leaderboard
- conversation.py: Conversation history and memory
- dynamic_tools.py: Dynamic AI tool management
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
    get_recent_tracker_entries,
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
    # User (16 functions)
    "create_user",
    "user_exists",
    "create_invite_code",
    "validate_invite_code",
    "use_invite_code",
    "get_user_subscription_status",
    "get_master_codes",
    "deactivate_invite_code",
    "get_onboarding_state",
    "start_onboarding",
    "update_onboarding_step",
    "complete_onboarding",
    "log_feature_discovery",
    "log_feature_usage",
    "audit_profile_update",
    "audit_preference_update",

    # Food (5 functions)
    "save_food_entry",
    "update_food_entry",
    "get_recent_food_entries",
    "get_food_entries_by_date",
    "has_logged_food_in_window",

    # Tracking (5 functions)
    "create_tracking_category",
    "get_tracking_categories",
    "save_tracking_entry",
    "save_sleep_entry",
    "get_sleep_entries",

    # Reminders (27 functions)
    "create_reminder",
    "get_active_reminders",
    "get_active_reminders_all",
    "get_reminder_by_id",
    "delete_reminder",
    "update_reminder",
    "find_duplicate_reminders",
    "deactivate_duplicate_reminders",
    "save_reminder_completion",
    "get_reminder_completions",
    "has_completed_reminder_today",
    "save_reminder_skip",
    "update_completion_note",
    "check_missed_reminder_grace_period",
    "calculate_current_streak",
    "calculate_best_streak",
    "get_reminder_analytics",
    "analyze_day_of_week_patterns",
    "get_multi_reminder_comparison",
    "detect_timing_patterns",
    "detect_difficult_days",
    "generate_adaptive_suggestions",
    "get_sleep_quiz_settings",
    "save_sleep_quiz_settings",
    "get_all_enabled_sleep_quiz_users",
    "save_sleep_quiz_submission",
    "get_submission_patterns",

    # Gamification (23 functions)
    "get_user_xp_data",
    "update_user_xp",
    "add_xp_transaction",
    "get_xp_transactions",
    "get_user_xp_level",
    "get_user_streak",
    "update_user_streak",
    "get_all_user_streaks",
    "get_user_streaks",
    "get_all_achievements",
    "get_achievement_by_key",
    "get_user_achievement_unlocks",
    "add_user_achievement",
    "has_user_unlocked_achievement",
    "get_user_achievements",
    "unlock_user_achievement",
    "unlock_achievement",
    "count_user_completions",
    "count_early_completions",
    "count_active_reminders",
    "count_perfect_completion_days",
    "check_recovery_pattern",
    "count_stats_views",

    # Conversation (3 functions)
    "save_conversation_message",
    "get_conversation_history",
    "clear_conversation_history",

    # Dynamic Tools (11 functions)
    "save_dynamic_tool",
    "get_all_enabled_tools",
    "get_tool_by_name",
    "update_tool_version",
    "disable_tool",
    "enable_tool",
    "log_tool_execution",
    "create_tool_approval_request",
    "approve_tool",
    "reject_tool",
    "get_pending_approvals",
]
