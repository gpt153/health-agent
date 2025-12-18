-- Reminder completions table
-- Tracks when users actually completed reminders (e.g., took medication)
-- Stores actual completion time, not scheduled reminder time

CREATE TABLE IF NOT EXISTS reminder_completions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reminder_id UUID REFERENCES reminders(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    scheduled_time TIMESTAMP NOT NULL,  -- When reminder was scheduled to fire
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- When user actually clicked "Done"
    notes TEXT  -- Optional notes from user
);

-- Index for querying user's completion history
CREATE INDEX IF NOT EXISTS idx_reminder_completions_user_completed
    ON reminder_completions(user_id, completed_at DESC);

-- Index for finding completions for a specific reminder
CREATE INDEX IF NOT EXISTS idx_reminder_completions_reminder
    ON reminder_completions(reminder_id, completed_at DESC);

-- Comment explaining the design
COMMENT ON TABLE reminder_completions IS 'Tracks actual completion time of reminders. scheduled_time is when reminder was sent, completed_at is when user clicked Done button.';
COMMENT ON COLUMN reminder_completions.scheduled_time IS 'Original scheduled time of the reminder (e.g., 08:00)';
COMMENT ON COLUMN reminder_completions.completed_at IS 'Actual time user completed the task and clicked Done (e.g., 09:15)';
