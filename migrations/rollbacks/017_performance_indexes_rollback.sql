-- Rollback Migration 017: Performance Indexes
-- Removes all performance indexes added in migration 017

DROP INDEX IF EXISTS idx_conversation_history_user_timestamp_covering;
DROP INDEX IF EXISTS idx_food_entries_user_date_range;
DROP INDEX IF EXISTS idx_reminders_next_execution;
DROP INDEX IF EXISTS idx_users_telegram_id_active;
DROP INDEX IF EXISTS idx_user_gamification_xp_desc;
DROP INDEX IF EXISTS idx_food_entries_user_name;
