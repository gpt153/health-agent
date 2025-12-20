-- ========================================
-- Migration 008: Gamification System
-- Achievements, badges, and user progress tracking
-- ========================================

-- Achievement definitions table
CREATE TABLE IF NOT EXISTS achievements (
    id VARCHAR(50) PRIMARY KEY,  -- e.g., 'first_completion', 'week_warrior'
    name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    icon VARCHAR(10) NOT NULL,  -- emoji
    category VARCHAR(50) NOT NULL,  -- 'consistency', 'milestones', 'recovery', 'exploration'
    criteria JSONB NOT NULL,  -- {type: 'streak', value: 7}
    tier VARCHAR(20) NOT NULL,  -- 'bronze', 'silver', 'gold', 'platinum'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User achievements (unlocked badges)
CREATE TABLE IF NOT EXISTS user_achievements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    achievement_id VARCHAR(50) NOT NULL REFERENCES achievements(id),
    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,  -- {reminder_id: '...', streak: 30}
    UNIQUE(user_id, achievement_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_achievements_user ON user_achievements(user_id, unlocked_at DESC);
CREATE INDEX IF NOT EXISTS idx_achievements_category ON achievements(category);
CREATE INDEX IF NOT EXISTS idx_achievements_tier ON achievements(tier);

-- Comments
COMMENT ON TABLE achievements IS 'Achievement definitions for gamification system';
COMMENT ON TABLE user_achievements IS 'Tracks which achievements each user has unlocked';
COMMENT ON COLUMN achievements.criteria IS 'JSON criteria for unlocking: {type: "streak", value: 7}';
COMMENT ON COLUMN user_achievements.metadata IS 'Context about how achievement was earned';

-- Insert default achievements
INSERT INTO achievements (id, name, description, icon, category, criteria, tier) VALUES
('first_steps', 'First Steps', 'Completed your first tracked reminder', '👣', 'milestones', '{"type": "total_completions", "value": 1}', 'bronze'),
('week_warrior', 'Week Warrior', 'Maintained a 7-day streak', '🔥', 'consistency', '{"type": "streak", "value": 7}', 'silver'),
('perfect_month', 'Perfect Month', '100% completion rate for 30 days', '💯', 'consistency', '{"type": "perfect_days", "value": 30}', 'gold'),
('century_club', 'Century Club', 'Completed 100 tracked tasks', '💯', 'milestones', '{"type": "total_completions", "value": 100}', 'gold'),
('early_bird', 'Early Bird', 'Completed 10 reminders early (before scheduled time)', '🌅', 'consistency', '{"type": "early_completions", "value": 10}', 'silver'),
('comeback_kid', 'Comeback Kid', 'Returned to 80%+ completion rate after a difficult week', '💪', 'recovery', '{"type": "recovery", "threshold": 0.8}', 'gold'),
('multi_tasker', 'Multi-Tasker', 'Actively tracking 3+ health habits', '⚡', 'milestones', '{"type": "active_reminders", "value": 3}', 'silver'),
('data_enthusiast', 'Data Enthusiast', 'Checked statistics 10+ times', '📊', 'exploration', '{"type": "stats_views", "value": 10}', 'bronze'),
('streak_legend', 'Streak Legend', 'Achieved a 30-day streak', '🏆', 'consistency', '{"type": "streak", "value": 30}', 'platinum'),
('hundred_day_hero', '100-Day Hero', 'Maintained a 100-day streak', '💎', 'consistency', '{"type": "streak", "value": 100}', 'platinum')
ON CONFLICT (id) DO NOTHING;
