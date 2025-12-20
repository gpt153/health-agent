-- Gamification Phase 1: Foundation - XP System and Multi-Domain Streaks
-- Part of Issue #11: Comprehensive Gamification & Motivation System

-- ============================================
-- XP and Leveling System
-- ============================================

-- User XP and Levels
CREATE TABLE IF NOT EXISTS user_xp (
    user_id VARCHAR(255) PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
    total_xp INT DEFAULT 0,
    current_level INT DEFAULT 1,
    xp_to_next_level INT DEFAULT 100,
    level_tier VARCHAR(20) DEFAULT 'bronze', -- bronze, silver, gold, platinum
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_xp_level ON user_xp(current_level DESC);
CREATE INDEX IF NOT EXISTS idx_user_xp_total ON user_xp(total_xp DESC);

-- XP Transaction Log (audit trail for all XP awards)
CREATE TABLE IF NOT EXISTS xp_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) REFERENCES users(telegram_id) ON DELETE CASCADE,
    amount INT NOT NULL,
    source_type VARCHAR(50) NOT NULL, -- 'reminder', 'meal', 'exercise', 'sleep', 'tracking'
    source_id UUID, -- Reference to the activity (reminder_completion_id, food_entry_id, etc.)
    reason TEXT, -- Human-readable description
    awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_xp_transactions_user ON xp_transactions(user_id, awarded_at DESC);
CREATE INDEX IF NOT EXISTS idx_xp_transactions_source ON xp_transactions(source_type, source_id);

-- ============================================
-- Multi-Domain Streak Tracking
-- ============================================

CREATE TABLE IF NOT EXISTS user_streaks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) REFERENCES users(telegram_id) ON DELETE CASCADE,
    streak_type VARCHAR(50) NOT NULL, -- 'medication', 'nutrition', 'exercise', 'sleep', 'hydration', 'mindfulness', 'overall'
    source_id UUID, -- Optional: specific reminder/category ID
    current_streak INT DEFAULT 0,
    best_streak INT DEFAULT 0,
    last_activity_date DATE,
    freeze_days_remaining INT DEFAULT 2, -- Streak protection
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, streak_type, source_id)
);

CREATE INDEX IF NOT EXISTS idx_user_streaks_user ON user_streaks(user_id);
CREATE INDEX IF NOT EXISTS idx_user_streaks_type ON user_streaks(streak_type);

-- ============================================
-- Achievement System
-- ============================================

-- Achievement definitions (static, seeded)
CREATE TABLE IF NOT EXISTS achievements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    achievement_key VARCHAR(100) UNIQUE NOT NULL, -- 'week_warrior', 'perfect_month', etc.
    name VARCHAR(200) NOT NULL,
    description TEXT,
    icon VARCHAR(50), -- Emoji or icon identifier
    category VARCHAR(50), -- 'consistency', 'milestone', 'domain_specific', 'recovery', 'social'
    criteria JSONB NOT NULL, -- {type: 'streak', value: 7, domain: 'any'}
    xp_reward INT DEFAULT 0,
    tier VARCHAR(20) DEFAULT 'bronze', -- bronze, silver, gold, platinum
    sort_order INT DEFAULT 0
);

-- User achievement unlocks
CREATE TABLE IF NOT EXISTS user_achievements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) REFERENCES users(telegram_id) ON DELETE CASCADE,
    achievement_id UUID REFERENCES achievements(id) ON DELETE CASCADE,
    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    progress JSONB, -- Current progress toward achievement (if not yet unlocked)
    UNIQUE(user_id, achievement_id)
);

CREATE INDEX IF NOT EXISTS idx_user_achievements_user ON user_achievements(user_id, unlocked_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_achievements_achievement ON user_achievements(achievement_id);

-- ============================================
-- Extended Columns for Existing Tables
-- ============================================

-- Extend reminders table with gamification preferences
ALTER TABLE reminders
ADD COLUMN IF NOT EXISTS enable_completion_tracking BOOLEAN DEFAULT true,
ADD COLUMN IF NOT EXISTS streak_motivation BOOLEAN DEFAULT true,
ADD COLUMN IF NOT EXISTS adaptive_timing BOOLEAN DEFAULT false;

-- Extend tracking_categories with XP and streak config
ALTER TABLE tracking_categories
ADD COLUMN IF NOT EXISTS xp_per_entry INT DEFAULT 10,
ADD COLUMN IF NOT EXISTS contributes_to_streaks BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS streak_domain VARCHAR(50); -- Map to streak_type

-- ============================================
-- Update Timestamp Trigger for new tables
-- ============================================

-- Ensure update trigger exists (from previous migrations)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for tables with updated_at
CREATE TRIGGER update_user_xp_updated_at
    BEFORE UPDATE ON user_xp
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_streaks_updated_at
    BEFORE UPDATE ON user_streaks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Seed Initial Achievements
-- ============================================

-- Consistency Achievements
INSERT INTO achievements (achievement_key, name, description, icon, category, criteria, xp_reward, tier, sort_order) VALUES
('first_steps', 'First Steps', 'Complete your first tracked activity', '👣', 'consistency', '{"type": "completion_count", "value": 1, "domain": "any"}'::jsonb, 25, 'bronze', 1),
('week_warrior', 'Week Warrior', 'Maintain a 7-day streak', '🔥', 'consistency', '{"type": "streak", "value": 7, "domain": "any"}'::jsonb, 100, 'bronze', 2),
('two_week_titan', 'Two Week Titan', 'Maintain a 14-day streak', '⚡', 'consistency', '{"type": "streak", "value": 14, "domain": "any"}'::jsonb, 200, 'silver', 3),
('monthly_master', 'Monthly Master', 'Maintain a 30-day streak', '🏆', 'consistency', '{"type": "streak", "value": 30, "domain": "any"}'::jsonb, 500, 'gold', 4),
('perfect_week', 'Perfect Week', 'Achieve 100% completion for 7 days', '⭐', 'consistency', '{"type": "perfect_period", "value": 7}'::jsonb, 150, 'silver', 5),
('perfect_month', 'Perfect Month', 'Achieve 100% completion for 30 days', '💎', 'consistency', '{"type": "perfect_period", "value": 30}'::jsonb, 750, 'platinum', 6)
ON CONFLICT (achievement_key) DO NOTHING;

-- Domain-Specific Achievements
INSERT INTO achievements (achievement_key, name, description, icon, category, criteria, xp_reward, tier, sort_order) VALUES
('pill_pro', 'Pill Pro', 'Complete 30 medication reminders', '💊', 'domain_specific', '{"type": "domain_count", "value": 30, "domain": "medication"}'::jsonb, 100, 'bronze', 10),
('hydration_hero', 'Hydration Hero', 'Maintain 7-day water intake streak', '💧', 'domain_specific', '{"type": "streak", "value": 7, "domain": "hydration"}'::jsonb, 100, 'bronze', 11),
('movement_maker', 'Movement Maker', 'Log 20 exercise activities', '🏃', 'domain_specific', '{"type": "domain_count", "value": 20, "domain": "exercise"}'::jsonb, 150, 'silver', 12),
('sleep_scholar', 'Sleep Scholar', 'Complete 7 sleep tracking entries', '😴', 'domain_specific', '{"type": "domain_count", "value": 7, "domain": "sleep"}'::jsonb, 100, 'bronze', 13),
('nutrition_navigator', 'Nutrition Navigator', 'Log 50 meals', '🍎', 'domain_specific', '{"type": "domain_count", "value": 50, "domain": "nutrition"}'::jsonb, 200, 'silver', 14),
('zen_master', 'Zen Master', 'Maintain 14-day mindfulness streak', '🧘', 'domain_specific', '{"type": "streak", "value": 14, "domain": "mindfulness"}'::jsonb, 200, 'silver', 15)
ON CONFLICT (achievement_key) DO NOTHING;

-- Milestone Achievements
INSERT INTO achievements (achievement_key, name, description, icon, category, criteria, xp_reward, tier, sort_order) VALUES
('bronze_tier', 'Bronze Tier', 'Reach level 5', '🥉', 'milestone', '{"type": "level", "value": 5}'::jsonb, 50, 'bronze', 20),
('silver_tier', 'Silver Tier', 'Reach level 15', '🥈', 'milestone', '{"type": "level", "value": 15}'::jsonb, 150, 'silver', 21),
('gold_tier', 'Gold Tier', 'Reach level 30', '🥇', 'milestone', '{"type": "level", "value": 30}'::jsonb, 500, 'gold', 22),
('platinum_tier', 'Platinum Tier', 'Reach level 40', '💫', 'milestone', '{"type": "level", "value": 40}'::jsonb, 1000, 'platinum', 23),
('xp_collector', 'XP Collector', 'Earn 1000 total XP', '💰', 'milestone', '{"type": "total_xp", "value": 1000}'::jsonb, 200, 'silver', 24),
('xp_legend', 'XP Legend', 'Earn 10,000 total XP', '👑', 'milestone', '{"type": "total_xp", "value": 10000}'::jsonb, 1000, 'platinum', 25)
ON CONFLICT (achievement_key) DO NOTHING;

-- Recovery Achievements
INSERT INTO achievements (achievement_key, name, description, icon, category, criteria, xp_reward, tier, sort_order) VALUES
('bounce_back', 'Bounce Back', 'Return to 80%+ completion after a drop', '🎯', 'recovery', '{"type": "recovery", "threshold": 0.8}'::jsonb, 100, 'bronze', 30),
('comeback_kid', 'Comeback Kid', 'Start a 7-day streak after breaking one', '💪', 'recovery', '{"type": "streak_recovery", "value": 7}'::jsonb, 150, 'silver', 31),
('persistent', 'Persistent', 'Maintain 60%+ completion for 90 days', '🛡️', 'recovery', '{"type": "sustained_effort", "rate": 0.6, "days": 90}'::jsonb, 300, 'gold', 32)
ON CONFLICT (achievement_key) DO NOTHING;

-- Comments for documentation
COMMENT ON TABLE user_xp IS 'Tracks user XP totals, levels, and tier progression';
COMMENT ON TABLE xp_transactions IS 'Audit log of all XP awards with source tracking';
COMMENT ON TABLE user_streaks IS 'Multi-domain streak tracking with protection mechanisms';
COMMENT ON TABLE achievements IS 'Achievement definitions (static data, seeded on migration)';
COMMENT ON TABLE user_achievements IS 'User progress and unlocks for achievements';

COMMENT ON COLUMN user_xp.level_tier IS 'Current tier: bronze (1-5), silver (6-15), gold (16-30), platinum (31+)';
COMMENT ON COLUMN user_streaks.freeze_days_remaining IS 'Streak protection days (resets monthly)';
COMMENT ON COLUMN achievements.criteria IS 'JSONB criteria for achievement unlock (type, value, domain, etc.)';
