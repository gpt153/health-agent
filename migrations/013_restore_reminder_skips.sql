-- ========================================
-- Migration 013: Restore reminder_skips table
-- Fixes issue #39: Table was dropped by rollback file executing in alphabetical order
-- ========================================

-- Create reminder_skips table (idempotent - safe if already exists)
CREATE TABLE IF NOT EXISTS reminder_skips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reminder_id UUID NOT NULL REFERENCES reminders(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    scheduled_time TIMESTAMP NOT NULL,  -- When the reminder was scheduled
    skipped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- When user clicked Skip
    reason VARCHAR(100),  -- 'sick', 'out_of_stock', 'doctor_advice', 'other', null
    notes TEXT  -- Optional user note
);

-- Indexes for skip tracking
CREATE INDEX IF NOT EXISTS idx_reminder_skips_user_skipped
    ON reminder_skips(user_id, skipped_at DESC);

CREATE INDEX IF NOT EXISTS idx_reminder_skips_reminder
    ON reminder_skips(reminder_id, skipped_at DESC);

-- Comments
COMMENT ON TABLE reminder_skips IS 'Tracks when users explicitly skip reminders with optional reason';
COMMENT ON COLUMN reminder_skips.scheduled_time IS 'Original scheduled time of the reminder';
COMMENT ON COLUMN reminder_skips.reason IS 'Pre-defined reason: sick, out_of_stock, doctor_advice, other';

-- Index on reminders for tracking queries (if not already exists from migration 007)
CREATE INDEX IF NOT EXISTS idx_reminders_tracking_enabled
    ON reminders(user_id, enable_completion_tracking)
    WHERE enable_completion_tracking = true;
