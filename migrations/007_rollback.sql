-- ========================================
-- Rollback for Migration 007
-- Removes reminder tracking enhancements
-- ========================================

-- Drop indexes
DROP INDEX IF EXISTS idx_reminder_skips_user_skipped;
DROP INDEX IF EXISTS idx_reminder_skips_reminder;
DROP INDEX IF EXISTS idx_reminders_tracking_enabled;

-- Drop table
DROP TABLE IF EXISTS reminder_skips;

-- Remove columns from reminders table
ALTER TABLE reminders
DROP COLUMN IF EXISTS enable_completion_tracking,
DROP COLUMN IF EXISTS streak_motivation;
