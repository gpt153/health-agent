# Gamification & Motivation System - Implementation Plan

**Issue**: #11 - Comprehensive Health Journey System
**Vision Document**: `.agents/plans/gamification-and-motivation-comprehensive-vision.md`
**Timeline**: 11 weeks across 5 phases
**Architecture**: Extends existing reminder completion tracking (Issue #9)

---

## Executive Summary

Transform the Health Agent from a tracking tool into a comprehensive motivation platform using proven gamification frameworks (Duolingo, Fitbit, behavioral psychology). This plan implements:

- **Universal XP & Levels** (36+ levels across 4 tiers)
- **Multi-Domain Streaks** (medication, nutrition, exercise, sleep, hydration, mindfulness, overall)
- **30+ Achievements** (consistency, domain-specific, recovery, social, milestones)
- **Adaptive Intelligence** (motivation profiles, personalized messaging, smart suggestions)
- **Weekly/Monthly Reports** (automated summaries with insights)
- **Challenge Library** (10-15 pre-built + custom challenges)
- **Ethical Design** (no dark patterns, user autonomy, privacy-first)

---

## Current System Analysis

### Existing Foundation (Built in Issue #9 Phases 1-2)

✅ **Database Tables** (already exist):
- `reminder_completions` - Tracks when users complete reminders
- `reminder_skips` - Tracks skipped reminders with reasons
- `reminders` - Has `enable_completion_tracking` and `streak_motivation` flags

✅ **Database Functions** (already implemented):
- `save_reminder_completion()` - Saves completion with timestamp
- `save_reminder_skip()` - Saves skip with reason
- `calculate_current_streak()` - Calculates current consecutive days
- `calculate_best_streak()` - Finds longest streak
- `get_reminder_analytics()` - Comprehensive analytics (30-day default)
- `analyze_day_of_week_patterns()` - Day-of-week breakdown
- `get_multi_reminder_comparison()` - Compares all reminders

✅ **Handler Implementation**:
- `/src/handlers/reminders.py` - Callback handlers for Done/Skip/Snooze buttons
- Inline keyboards with completion tracking
- Streak display in reminder notifications (🔥 emoji)
- Time difference tracking (early/late/on-time)

✅ **Agent Tools** (existing):
- `schedule_reminder()` - Creates reminders with tracking enabled
- `get_reminder_statistics()` - Gets stats for specific reminder
- `compare_all_reminders()` - Compares all tracked reminders

✅ **Models**:
- `src/models/reminder.py` - Reminder model with tracking flags
- `src/models/tracking.py` - Tracking categories and entries
- `src/models/user.py` - User preferences

### Architecture Patterns to Follow

**Database Approach**:
- PostgreSQL with JSONB for flexible data
- UUID primary keys
- Timestamp tracking with timezone support
- Indexes for performance (GIN indexes for JSONB)
- Soft deletes (active flags)

**Tool Pattern**:
- PydanticAI agent tools with `@agent.tool` decorator
- Result models (BaseModel) with `success`, `message`, and data fields
- Dependency injection via `AgentDeps` (includes `telegram_id`, `memory_manager`, `user_memory`, `reminder_manager`, `bot_application`)
- Error handling with try/except and logging

**Handler Pattern**:
- Telegram callback query handlers
- Pattern-based routing (`^pattern\\|`)
- Inline keyboards for user interaction
- Authorization checks via `is_authorized()`
- Markdown formatting for rich messages

**Scheduler Pattern**:
- `ReminderManager` class with JobQueue integration
- Timezone-aware scheduling
- One-time and recurring jobs
- Job data passed via context

---

## Phase 1: Foundation (Weeks 1-3)

### 1.1 Database Schema (Migration 008)

**File**: `migrations/008_gamification_foundation.sql`

```sql
-- =====================================================
-- XP & Levels System
-- =====================================================

-- User XP tracking table
CREATE TABLE IF NOT EXISTS user_xp (
    user_id VARCHAR(255) PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
    total_xp INTEGER DEFAULT 0,
    current_level INTEGER DEFAULT 1,
    current_tier VARCHAR(20) DEFAULT 'bronze',  -- bronze, silver, gold, platinum
    xp_for_next_level INTEGER DEFAULT 100,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- XP transaction log (audit trail)
CREATE TABLE IF NOT EXISTS xp_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    xp_amount INTEGER NOT NULL,
    xp_source VARCHAR(100) NOT NULL,  -- 'reminder_completion', 'food_log', 'exercise_log', 'sleep_log', 'quiz_completion'
    source_id UUID,  -- ID of the action that triggered XP (e.g., reminder_id, food_entry_id)
    description TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_xp_transactions_user_timestamp ON xp_transactions(user_id, timestamp DESC);
CREATE INDEX idx_xp_transactions_source ON xp_transactions(xp_source, timestamp DESC);

-- =====================================================
-- Streaks System (Multi-Domain)
-- =====================================================

-- User streaks across different health domains
CREATE TABLE IF NOT EXISTS user_streaks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    streak_type VARCHAR(50) NOT NULL,  -- 'medication', 'nutrition', 'exercise', 'sleep', 'hydration', 'mindfulness', 'overall_health'
    entity_id UUID,  -- Optional: specific reminder_id or tracking_category_id
    current_streak INTEGER DEFAULT 0,
    best_streak INTEGER DEFAULT 0,
    last_action_date DATE,
    freeze_days_available INTEGER DEFAULT 2,  -- Streak protection days
    freeze_days_used INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, streak_type, entity_id)
);

CREATE INDEX idx_user_streaks_user_type ON user_streaks(user_id, streak_type);
CREATE INDEX idx_user_streaks_entity ON user_streaks(entity_id);

-- Streak freeze usage log
CREATE TABLE IF NOT EXISTS streak_freeze_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    streak_id UUID NOT NULL REFERENCES user_streaks(id) ON DELETE CASCADE,
    freeze_date DATE NOT NULL,
    reason VARCHAR(50),  -- 'manual', 'vacation_mode', 'weekend_flex'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_streak_freeze_user_date ON streak_freeze_log(user_id, freeze_date DESC);

-- =====================================================
-- Achievements & Badges System
-- =====================================================

-- Achievement definitions (pre-populated via seed script)
CREATE TABLE IF NOT EXISTS achievements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    achievement_key VARCHAR(100) UNIQUE NOT NULL,  -- e.g., 'week_warrior', 'pill_pro_gold'
    name VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,  -- 'consistency', 'domain_specific', 'recovery', 'social', 'milestone'
    tier VARCHAR(20),  -- 'bronze', 'silver', 'gold', NULL for non-tiered
    icon_emoji VARCHAR(10),
    unlock_criteria JSONB NOT NULL,  -- Flexible criteria definition
    xp_reward INTEGER DEFAULT 0,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_achievements_category ON achievements(category, tier);

-- User achievement unlocks
CREATE TABLE IF NOT EXISTS user_achievements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    achievement_id UUID NOT NULL REFERENCES achievements(id) ON DELETE CASCADE,
    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    progress JSONB,  -- Track progress toward achievement
    UNIQUE(user_id, achievement_id)
);

CREATE INDEX idx_user_achievements_user ON user_achievements(user_id, unlocked_at DESC);
CREATE INDEX idx_user_achievements_achievement ON user_achievements(achievement_id);

-- =====================================================
-- Challenges System
-- =====================================================

-- Challenge definitions (both built-in and custom)
CREATE TABLE IF NOT EXISTS challenges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    challenge_key VARCHAR(100) UNIQUE,  -- NULL for custom challenges
    name VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    challenge_type VARCHAR(50) NOT NULL,  -- 'built_in', 'custom', 'group'
    difficulty VARCHAR(20) DEFAULT 'medium',  -- 'easy', 'medium', 'hard'
    duration_days INTEGER NOT NULL,
    success_criteria JSONB NOT NULL,  -- Flexible success definition
    xp_reward INTEGER DEFAULT 0,
    icon_emoji VARCHAR(10),
    created_by VARCHAR(255),  -- user_id for custom challenges, 'system' for built-in
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_challenges_type ON challenges(challenge_type, active);

-- User challenge participation
CREATE TABLE IF NOT EXISTS user_challenges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    challenge_id UUID NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    target_end_date DATE NOT NULL,
    actual_end_date DATE,
    status VARCHAR(20) DEFAULT 'active',  -- 'active', 'completed', 'failed', 'abandoned'
    progress JSONB,  -- Track daily/weekly progress
    completion_rate FLOAT DEFAULT 0.0,
    notes TEXT,
    UNIQUE(user_id, challenge_id, started_at)
);

CREATE INDEX idx_user_challenges_user_status ON user_challenges(user_id, status);
CREATE INDEX idx_user_challenges_dates ON user_challenges(started_at, target_end_date);

-- =====================================================
-- Adaptive Intelligence & Personalization
-- =====================================================

-- User motivation profile (learned over time)
CREATE TABLE IF NOT EXISTS user_motivation_profile (
    user_id VARCHAR(255) PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
    motivation_type VARCHAR(50) DEFAULT 'achiever',  -- 'achiever', 'competitor', 'socializer', 'explorer'
    response_patterns JSONB,  -- Learned patterns (time of day, day of week)
    preferred_messaging_style VARCHAR(50) DEFAULT 'supportive',  -- 'supportive', 'analytical', 'competitive'
    opt_in_social BOOLEAN DEFAULT false,
    opt_in_challenges BOOLEAN DEFAULT true,
    opt_in_reports BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- Reports & Summaries
-- =====================================================

-- Report generation log (to avoid duplicate sends)
CREATE TABLE IF NOT EXISTS report_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    report_type VARCHAR(50) NOT NULL,  -- 'weekly', 'monthly'
    period_start_date DATE NOT NULL,
    period_end_date DATE NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP,
    report_data JSONB,  -- Store report content for later viewing
    UNIQUE(user_id, report_type, period_start_date)
);

CREATE INDEX idx_report_history_user_type ON report_history(user_id, report_type, period_start_date DESC);

-- Comments
COMMENT ON TABLE user_xp IS 'Tracks user XP and level progression across all health activities';
COMMENT ON TABLE xp_transactions IS 'Audit log of all XP-earning actions for transparency';
COMMENT ON TABLE user_streaks IS 'Multi-domain streak tracking with freeze protection';
COMMENT ON TABLE achievements IS 'Achievement definitions (30+ pre-defined achievements)';
COMMENT ON TABLE user_achievements IS 'Tracks which achievements users have unlocked';
COMMENT ON TABLE challenges IS 'Challenge library (built-in and custom)';
COMMENT ON TABLE user_challenges IS 'User participation in challenges with progress tracking';
COMMENT ON TABLE user_motivation_profile IS 'Learned user preferences for adaptive messaging';
COMMENT ON TABLE report_history IS 'Tracks generated weekly/monthly reports';
```

### 1.2 Achievement Seed Data

**File**: `migrations/008_gamification_seed_achievements.sql`

```sql
-- =====================================================
-- Seed 30+ Achievements
-- =====================================================

-- CONSISTENCY ACHIEVEMENTS
INSERT INTO achievements (achievement_key, name, description, category, tier, icon_emoji, unlock_criteria, xp_reward) VALUES
('week_warrior', 'Week Warrior', 'Complete all health actions for 7 consecutive days', 'consistency', NULL, '🏆', '{"type": "streak", "domain": "overall_health", "days": 7}', 100),
('monthly_master', 'Monthly Master', 'Complete all health actions for 30 consecutive days', 'consistency', NULL, '👑', '{"type": "streak", "domain": "overall_health", "days": 30}', 500),
('perfect_month', 'Perfect Month', '100% completion rate for an entire month', 'consistency', NULL, '💯', '{"type": "completion_rate", "period_days": 30, "rate": 100}', 750),
('century_club', 'Century Club', '100-day streak on any health action', 'consistency', NULL, '💯', '{"type": "streak", "days": 100}', 1000),
('year_legend', 'Year Legend', '365-day streak on any health action', 'consistency', NULL, '🌟', '{"type": "streak", "days": 365}', 5000);

-- DOMAIN-SPECIFIC ACHIEVEMENTS (Medication)
INSERT INTO achievements (achievement_key, name, description, category, tier, icon_emoji, unlock_criteria, xp_reward) VALUES
('pill_pro_bronze', 'Pill Pro (Bronze)', '7-day medication streak', 'domain_specific', 'bronze', '💊', '{"type": "streak", "domain": "medication", "days": 7}', 50),
('pill_pro_silver', 'Pill Pro (Silver)', '30-day medication streak', 'domain_specific', 'silver', '💊', '{"type": "streak", "domain": "medication", "days": 30}', 200),
('pill_pro_gold', 'Pill Pro (Gold)', '90-day medication streak', 'domain_specific', 'gold', '💊', '{"type": "streak", "domain": "medication", "days": 90}', 800);

-- DOMAIN-SPECIFIC ACHIEVEMENTS (Nutrition)
INSERT INTO achievements (achievement_key, name, description, category, tier, icon_emoji, unlock_criteria, xp_reward) VALUES
('nutrition_ninja_bronze', 'Nutrition Ninja (Bronze)', 'Log food for 7 consecutive days', 'domain_specific', 'bronze', '🥗', '{"type": "streak", "domain": "nutrition", "days": 7}', 50),
('nutrition_ninja_silver', 'Nutrition Ninja (Silver)', 'Log food for 30 consecutive days', 'domain_specific', 'silver', '🥗', '{"type": "streak", "domain": "nutrition", "days": 30}', 200),
('nutrition_ninja_gold', 'Nutrition Ninja (Gold)', 'Log food for 90 consecutive days', 'domain_specific', 'gold', '🥗', '{"type": "streak", "domain": "nutrition", "days": 90}', 800);

-- DOMAIN-SPECIFIC ACHIEVEMENTS (Exercise)
INSERT INTO achievements (achievement_key, name, description, category, tier, icon_emoji, unlock_criteria, xp_reward) VALUES
('movement_maker_bronze', 'Movement Maker (Bronze)', 'Exercise for 7 consecutive days', 'domain_specific', 'bronze', '💪', '{"type": "streak", "domain": "exercise", "days": 7}', 50),
('movement_maker_silver', 'Movement Maker (Silver)', 'Exercise for 30 consecutive days', 'domain_specific', 'silver', '💪', '{"type": "streak", "domain": "exercise", "days": 30}', 200),
('movement_maker_gold', 'Movement Maker (Gold)', 'Exercise for 90 consecutive days', 'domain_specific', 'gold', '💪', '{"type": "streak", "domain": "exercise", "days": 90}', 800);

-- DOMAIN-SPECIFIC ACHIEVEMENTS (Sleep)
INSERT INTO achievements (achievement_key, name, description, category, tier, icon_emoji, unlock_criteria, xp_reward) VALUES
('sleep_scholar_bronze', 'Sleep Scholar (Bronze)', 'Log sleep for 7 consecutive days', 'domain_specific', 'bronze', '😴', '{"type": "streak", "domain": "sleep", "days": 7}', 50),
('sleep_scholar_silver', 'Sleep Scholar (Silver)', 'Log sleep for 30 consecutive days', 'domain_specific', 'silver', '😴', '{"type": "streak", "domain": "sleep", "days": 30}', 200),
('sleep_scholar_gold', 'Sleep Scholar (Gold)', 'Log sleep for 90 consecutive days', 'domain_specific', 'gold', '😴', '{"type": "streak", "domain": "sleep", "days": 90}', 800);

-- DOMAIN-SPECIFIC ACHIEVEMENTS (Hydration)
INSERT INTO achievements (achievement_key, name, description, category, tier, icon_emoji, unlock_criteria, xp_reward) VALUES
('hydration_hero', 'Hydration Hero', 'Track water intake for 14 consecutive days', 'domain_specific', NULL, '💧', '{"type": "streak", "domain": "hydration", "days": 14}', 100);

-- DOMAIN-SPECIFIC ACHIEVEMENTS (Mindfulness)
INSERT INTO achievements (achievement_key, name, description, category, tier, icon_emoji, unlock_criteria, xp_reward) VALUES
('zen_master_bronze', 'Zen Master (Bronze)', '7-day mindfulness streak', 'domain_specific', 'bronze', '🧘', '{"type": "streak", "domain": "mindfulness", "days": 7}', 50),
('zen_master_silver', 'Zen Master (Silver)', '30-day mindfulness streak', 'domain_specific', 'silver', '🧘', '{"type": "streak", "domain": "mindfulness", "days": 30}', 200);

-- RECOVERY ACHIEVEMENTS
INSERT INTO achievements (achievement_key, name, description, category, tier, icon_emoji, unlock_criteria, xp_reward) VALUES
('comeback_kid', 'Comeback Kid', 'Rebuild a streak after breaking it', 'recovery', NULL, '🔄', '{"type": "streak_rebuild", "min_days": 7}', 150),
('bounce_back', 'Bounce Back', 'Complete action the day after skipping', 'recovery', NULL, '↗️', '{"type": "recovery_after_skip", "within_hours": 24}', 75),
('persistent', 'Persistent', 'Maintain 80%+ completion rate over 30 days despite missed days', 'recovery', NULL, '🛡️', '{"type": "completion_rate", "period_days": 30, "rate": 80}', 200);

-- SOCIAL ACHIEVEMENTS (Opt-in)
INSERT INTO achievements (achievement_key, name, description, category, tier, icon_emoji, unlock_criteria, xp_reward) VALUES
('community_member', 'Community Member', 'Join a group challenge', 'social', NULL, '👥', '{"type": "join_group_challenge"}', 50),
('helpful_friend', 'Helpful Friend', 'Share a tip or encourage another user', 'social', NULL, '💬', '{"type": "social_interaction"}', 100);

-- MILESTONE ACHIEVEMENTS
INSERT INTO achievements (achievement_key, name, description, category, tier, icon_emoji, unlock_criteria, xp_reward) VALUES
('first_step', 'First Step', 'Complete your first health action', 'milestone', NULL, '🎯', '{"type": "first_action"}', 25),
('xp_1000', '1,000 XP Club', 'Earn 1,000 total XP', 'milestone', NULL, '⭐', '{"type": "total_xp", "amount": 1000}', 100),
('xp_10000', '10,000 XP Legend', 'Earn 10,000 total XP', 'milestone', NULL, '🌟', '{"type": "total_xp", "amount": 10000}', 500),
('bronze_tier', 'Bronze Tier', 'Reach Bronze tier (Level 1-9)', 'milestone', 'bronze', '🥉', '{"type": "level_tier", "tier": "bronze"}', 50),
('silver_tier', 'Silver Tier', 'Reach Silver tier (Level 10-19)', 'milestone', 'silver', '🥈', '{"type": "level_tier", "tier": "silver"}', 200),
('gold_tier', 'Gold Tier', 'Reach Gold tier (Level 20-29)', 'milestone', 'gold', '🥇', '{"type": "level_tier", "tier": "gold"}', 500),
('platinum_tier', 'Platinum Tier', 'Reach Platinum tier (Level 30+)', 'milestone', 'platinum', '💎', '{"type": "level_tier", "tier": "platinum"}', 1000);
```

### 1.3 Core XP & Streak Logic (Database Functions)

**File**: `src/db/gamification.py` (new file)

```python
"""Gamification database functions - XP, streaks, achievements, challenges"""
import logging
from typing import Optional
from datetime import datetime, date, timedelta
from uuid import UUID
from src.db.connection import db

logger = logging.getLogger(__name__)

# =====================================================
# XP SYSTEM FUNCTIONS
# =====================================================

async def award_xp(
    user_id: str,
    xp_amount: int,
    xp_source: str,
    source_id: Optional[str] = None,
    description: Optional[str] = None
) -> dict:
    """
    Award XP to user and update level/tier

    Args:
        user_id: Telegram user ID
        xp_amount: Amount of XP to award
        xp_source: Source of XP (e.g., 'reminder_completion', 'food_log')
        source_id: Optional ID of source action
        description: Optional description

    Returns:
        dict with new_total_xp, new_level, level_up (bool), tier_up (bool)
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Get current XP state
            await cur.execute(
                """
                SELECT total_xp, current_level, current_tier
                FROM user_xp
                WHERE user_id = %s
                """,
                (user_id,)
            )
            row = await cur.fetchone()

            if not row:
                # Initialize user XP
                await cur.execute(
                    """
                    INSERT INTO user_xp (user_id, total_xp, current_level, current_tier)
                    VALUES (%s, 0, 1, 'bronze')
                    """,
                    (user_id,)
                )
                current_xp = 0
                current_level = 1
                current_tier = 'bronze'
            else:
                current_xp = row[0]
                current_level = row[1]
                current_tier = row[2]

            # Calculate new XP
            new_xp = current_xp + xp_amount

            # Calculate new level (quadratic progression: level 1=100, 2=250, 3=450, etc.)
            new_level, xp_for_next = _calculate_level(new_xp)

            # Determine tier
            new_tier = _get_tier_for_level(new_level)

            # Check for level/tier changes
            level_up = new_level > current_level
            tier_up = new_tier != current_tier

            # Update user XP
            await cur.execute(
                """
                UPDATE user_xp
                SET total_xp = %s,
                    current_level = %s,
                    current_tier = %s,
                    xp_for_next_level = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
                """,
                (new_xp, new_level, new_tier, xp_for_next, user_id)
            )

            # Log XP transaction
            await cur.execute(
                """
                INSERT INTO xp_transactions
                (user_id, xp_amount, xp_source, source_id, description)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, xp_amount, xp_source, source_id, description)
            )

            await conn.commit()

    logger.info(f"Awarded {xp_amount} XP to {user_id}: {xp_source}")

    return {
        "new_total_xp": new_xp,
        "new_level": new_level,
        "new_tier": new_tier,
        "level_up": level_up,
        "tier_up": tier_up,
        "xp_for_next_level": xp_for_next
    }


def _calculate_level(total_xp: int) -> tuple[int, int]:
    """
    Calculate level from total XP (quadratic progression)

    Formula: XP required for level N = 50 * N * (N + 1)
    Level 1: 100 XP
    Level 2: 250 XP total (150 more)
    Level 3: 450 XP total (200 more)
    Level 10: 5,500 XP total
    Level 20: 21,000 XP total
    Level 30: 46,500 XP total

    Returns:
        (level, xp_for_next_level)
    """
    level = 1
    cumulative_xp = 0

    while True:
        xp_needed = 50 * level * (level + 1)
        if cumulative_xp + xp_needed > total_xp:
            # Current level
            xp_for_next = cumulative_xp + xp_needed - total_xp
            return (level, xp_for_next)
        cumulative_xp += xp_needed
        level += 1
        if level > 100:  # Safety cap
            return (100, 0)


def _get_tier_for_level(level: int) -> str:
    """Get tier name for a given level"""
    if level < 10:
        return 'bronze'
    elif level < 20:
        return 'silver'
    elif level < 30:
        return 'gold'
    else:
        return 'platinum'


async def get_user_xp_stats(user_id: str) -> Optional[dict]:
    """Get user's XP statistics"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT total_xp, current_level, current_tier, xp_for_next_level, created_at
                FROM user_xp
                WHERE user_id = %s
                """,
                (user_id,)
            )
            row = await cur.fetchone()

            if not row:
                return None

            return {
                "total_xp": row[0],
                "current_level": row[1],
                "current_tier": row[2],
                "xp_for_next_level": row[3],
                "member_since": row[4]
            }


# =====================================================
# STREAK SYSTEM FUNCTIONS
# =====================================================

async def update_streak(
    user_id: str,
    streak_type: str,
    entity_id: Optional[str] = None,
    action_date: Optional[date] = None
) -> dict:
    """
    Update user streak for a domain

    Args:
        user_id: Telegram user ID
        streak_type: Type of streak ('medication', 'nutrition', etc.)
        entity_id: Optional specific entity (reminder_id, category_id)
        action_date: Date of action (defaults to today)

    Returns:
        dict with current_streak, best_streak, is_new_best
    """
    if action_date is None:
        action_date = date.today()

    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Get or create streak record
            await cur.execute(
                """
                SELECT id, current_streak, best_streak, last_action_date, freeze_days_available
                FROM user_streaks
                WHERE user_id = %s AND streak_type = %s
                  AND (entity_id = %s OR (entity_id IS NULL AND %s IS NULL))
                """,
                (user_id, streak_type, entity_id, entity_id)
            )
            row = await cur.fetchone()

            if not row:
                # Create new streak
                await cur.execute(
                    """
                    INSERT INTO user_streaks
                    (user_id, streak_type, entity_id, current_streak, best_streak, last_action_date)
                    VALUES (%s, %s, %s, 1, 1, %s)
                    RETURNING id, current_streak, best_streak
                    """,
                    (user_id, streak_type, entity_id, action_date)
                )
                new_row = await cur.fetchone()
                await conn.commit()

                return {
                    "current_streak": 1,
                    "best_streak": 1,
                    "is_new_best": True
                }

            streak_id = row[0]
            current_streak = row[1]
            best_streak = row[2]
            last_action = row[3]
            freeze_days = row[4]

            # Calculate days since last action
            days_diff = (action_date - last_action).days

            if days_diff == 0:
                # Same day action - no change
                return {
                    "current_streak": current_streak,
                    "best_streak": best_streak,
                    "is_new_best": False
                }
            elif days_diff == 1:
                # Consecutive day - increment
                new_streak = current_streak + 1
                new_best = max(new_streak, best_streak)

                await cur.execute(
                    """
                    UPDATE user_streaks
                    SET current_streak = %s,
                        best_streak = %s,
                        last_action_date = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (new_streak, new_best, action_date, streak_id)
                )
                await conn.commit()

                return {
                    "current_streak": new_streak,
                    "best_streak": new_best,
                    "is_new_best": new_streak == new_best
                }
            elif days_diff <= freeze_days + 1:
                # Within freeze protection - maintain streak
                # TODO: Log freeze usage
                new_streak = current_streak  # Maintain

                await cur.execute(
                    """
                    UPDATE user_streaks
                    SET last_action_date = %s,
                        freeze_days_used = freeze_days_used + %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (action_date, days_diff - 1, streak_id)
                )
                await conn.commit()

                return {
                    "current_streak": new_streak,
                    "best_streak": best_streak,
                    "is_new_best": False,
                    "freeze_used": True
                }
            else:
                # Streak broken - reset to 1
                await cur.execute(
                    """
                    UPDATE user_streaks
                    SET current_streak = 1,
                        last_action_date = %s,
                        freeze_days_used = 0,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (action_date, streak_id)
                )
                await conn.commit()

                return {
                    "current_streak": 1,
                    "best_streak": best_streak,
                    "is_new_best": False,
                    "streak_broken": True
                }


async def get_user_streaks(user_id: str) -> list[dict]:
    """Get all user streaks"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT streak_type, current_streak, best_streak, last_action_date,
                       freeze_days_available, freeze_days_used
                FROM user_streaks
                WHERE user_id = %s
                ORDER BY current_streak DESC
                """,
                (user_id,)
            )
            rows = await cur.fetchall()

            if not rows:
                return []

            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in rows]


# =====================================================
# ACHIEVEMENT FUNCTIONS
# =====================================================

async def check_and_unlock_achievements(user_id: str) -> list[dict]:
    """
    Check all achievements and unlock any newly earned ones

    Returns:
        List of newly unlocked achievements
    """
    newly_unlocked = []

    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Get all achievements user doesn't have yet
            await cur.execute(
                """
                SELECT a.id, a.achievement_key, a.name, a.unlock_criteria, a.xp_reward
                FROM achievements a
                WHERE a.active = true
                  AND NOT EXISTS (
                      SELECT 1 FROM user_achievements ua
                      WHERE ua.user_id = %s AND ua.achievement_id = a.id
                  )
                """,
                (user_id,)
            )
            achievements = await cur.fetchall()

            for achievement in achievements:
                ach_id, ach_key, ach_name, criteria, xp_reward = achievement

                # Check if user meets criteria
                if await _check_achievement_criteria(user_id, criteria, cur):
                    # Unlock achievement
                    await cur.execute(
                        """
                        INSERT INTO user_achievements (user_id, achievement_id)
                        VALUES (%s, %s)
                        """,
                        (user_id, ach_id)
                    )

                    newly_unlocked.append({
                        "achievement_key": ach_key,
                        "name": ach_name,
                        "xp_reward": xp_reward
                    })

                    # Award XP for achievement
                    if xp_reward > 0:
                        await award_xp(
                            user_id=user_id,
                            xp_amount=xp_reward,
                            xp_source="achievement_unlock",
                            source_id=str(ach_id),
                            description=f"Unlocked: {ach_name}"
                        )

            await conn.commit()

    return newly_unlocked


async def _check_achievement_criteria(
    user_id: str,
    criteria: dict,
    cur
) -> bool:
    """Check if user meets achievement criteria (simplified for MVP)"""
    criteria_type = criteria.get("type")

    if criteria_type == "streak":
        # Check streak achievement
        domain = criteria.get("domain")
        required_days = criteria.get("days", 0)

        # Query user streaks
        await cur.execute(
            """
            SELECT current_streak
            FROM user_streaks
            WHERE user_id = %s AND streak_type = %s
            """,
            (user_id, domain)
        )
        row = await cur.fetchone()

        if row and row[0] >= required_days:
            return True

    elif criteria_type == "total_xp":
        # Check total XP milestone
        required_xp = criteria.get("amount", 0)

        await cur.execute(
            """
            SELECT total_xp
            FROM user_xp
            WHERE user_id = %s
            """,
            (user_id,)
        )
        row = await cur.fetchone()

        if row and row[0] >= required_xp:
            return True

    elif criteria_type == "level_tier":
        # Check tier achievement
        required_tier = criteria.get("tier")

        await cur.execute(
            """
            SELECT current_tier
            FROM user_xp
            WHERE user_id = %s
            """,
            (user_id,)
        )
        row = await cur.fetchone()

        if row and row[0] == required_tier:
            return True

    # Add more criteria types as needed

    return False


async def get_user_achievements(user_id: str) -> list[dict]:
    """Get all unlocked achievements for user"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT a.achievement_key, a.name, a.description, a.category,
                       a.tier, a.icon_emoji, a.xp_reward, ua.unlocked_at
                FROM user_achievements ua
                JOIN achievements a ON ua.achievement_id = a.id
                WHERE ua.user_id = %s
                ORDER BY ua.unlocked_at DESC
                """,
                (user_id,)
            )
            rows = await cur.fetchall()

            if not rows:
                return []

            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in rows]
```

### 1.4 PydanticAI Agent Tools (XP, Streaks, Achievements)

**Add to**: `src/agent/__init__.py`

```python
# Add new result models
class XPAwardResult(BaseModel):
    """Result of XP award"""
    success: bool
    message: str
    new_total_xp: int
    new_level: int
    level_up: bool
    tier_up: bool

class StreakUpdateResult(BaseModel):
    """Result of streak update"""
    success: bool
    message: str
    current_streak: int
    best_streak: int
    is_new_best: bool

class AchievementCheckResult(BaseModel):
    """Result of achievement check"""
    success: bool
    message: str
    newly_unlocked: list[dict]

class GamificationStatsResult(BaseModel):
    """Result of gamification stats query"""
    success: bool
    message: str
    formatted_stats: Optional[str] = None

# Add tools
@agent.tool
async def get_my_stats(ctx) -> GamificationStatsResult:
    """
    Get comprehensive gamification statistics (XP, level, streaks, achievements)

    Use this when user asks "my stats", "how am I doing", "show progress", etc.

    Returns:
        GamificationStatsResult with formatted statistics
    """
    deps: AgentDeps = ctx.deps

    try:
        from src.db.gamification import (
            get_user_xp_stats,
            get_user_streaks,
            get_user_achievements
        )

        # Get XP stats
        xp_stats = await get_user_xp_stats(deps.telegram_id)

        # Get streaks
        streaks = await get_user_streaks(deps.telegram_id)

        # Get achievements
        achievements = await get_user_achievements(deps.telegram_id)

        # Format message
        if not xp_stats:
            # Initialize user
            from src.db.gamification import award_xp
            await award_xp(deps.telegram_id, 0, "initialization", description="Account initialized")
            xp_stats = await get_user_xp_stats(deps.telegram_id)

        tier_emoji = {
            'bronze': '🥉',
            'silver': '🥈',
            'gold': '🥇',
            'platinum': '💎'
        }

        formatted = f"""📊 **Your Health Journey Stats**

🏆 **Progress**
• Level: {xp_stats['current_level']} {tier_emoji.get(xp_stats['current_tier'], '')} {xp_stats['current_tier'].title()} Tier
• Total XP: {xp_stats['total_xp']:,}
• Next Level: {xp_stats['xp_for_next_level']} XP away

🔥 **Active Streaks**"""

        if streaks:
            for streak in streaks[:5]:  # Top 5 streaks
                formatted += f"\n• {streak['streak_type'].replace('_', ' ').title()}: {streak['current_streak']} days (best: {streak['best_streak']})"
        else:
            formatted += "\n• No active streaks yet - start today!"

        formatted += f"\n\n🏅 **Achievements**"
        if achievements:
            formatted += f"\n• Unlocked: {len(achievements)} achievements"
            # Show recent
            for ach in achievements[:3]:
                formatted += f"\n• {ach.get('icon_emoji', '🏆')} {ach['name']}"
        else:
            formatted += "\n• No achievements yet - keep going!"

        return GamificationStatsResult(
            success=True,
            message=formatted,
            formatted_stats=formatted
        )

    except Exception as e:
        logger.error(f"Error getting gamification stats: {e}", exc_info=True)
        return GamificationStatsResult(
            success=False,
            message=f"Error retrieving stats: {str(e)}",
            formatted_stats=None
        )
```

### 1.5 Integration with Existing Reminder System

**Modify**: `src/handlers/reminders.py` - Update `handle_reminder_completion()`

```python
async def handle_reminder_completion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle when user clicks 'Done' on a reminder

    NOW WITH GAMIFICATION:
    - Awards XP
    - Updates streaks
    - Checks for achievements
    - Shows level-up messages
    """
    query = update.callback_query
    user_id = str(update.effective_user.id)

    # ... existing authorization check ...

    try:
        await query.answer("✅ Marked as done!")

        # ... existing callback data parsing ...

        reminder_id = parts[1]
        scheduled_time = parts[2]

        # Save completion to database
        await save_reminder_completion(
            reminder_id=reminder_id,
            user_id=user_id,
            scheduled_time=scheduled_time,
            notes=None
        )

        # ============ GAMIFICATION INTEGRATION ============
        from src.db.gamification import (
            award_xp,
            update_streak,
            check_and_unlock_achievements
        )

        # 1. Award XP for completion
        xp_result = await award_xp(
            user_id=user_id,
            xp_amount=10,  # Base XP for reminder completion
            xp_source="reminder_completion",
            source_id=reminder_id,
            description="Completed reminder"
        )

        # 2. Update streak (medication domain)
        streak_result = await update_streak(
            user_id=user_id,
            streak_type="medication",
            entity_id=reminder_id
        )

        # 3. Check for achievements
        new_achievements = await check_and_unlock_achievements(user_id)

        # ============ BUILD COMPLETION MESSAGE ============

        original_text = query.message.text

        # ... existing time difference calculation ...

        # Base completion message
        completion_message = (
            f"{original_text}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{time_note}\n"
            f"⏰ Scheduled: {scheduled_hour}\n"
            f"✅ Completed: {actual_time}\n\n"
        )

        # Add XP notification
        completion_message += f"💫 +10 XP"

        # Add level-up notification
        if xp_result['level_up']:
            completion_message += f"\n\n🎉 **LEVEL UP!** You're now Level {xp_result['new_level']}!"
            if xp_result['tier_up']:
                tier_emoji = {'bronze': '🥉', 'silver': '🥈', 'gold': '🥇', 'platinum': '💎'}
                completion_message += f"\n{tier_emoji.get(xp_result['new_tier'], '')} **{xp_result['new_tier'].upper()} TIER UNLOCKED!**"

        # Add streak notification
        if streak_result['is_new_best']:
            completion_message += f"\n🔥 **NEW BEST STREAK: {streak_result['current_streak']} days!**"
        elif streak_result['current_streak'] > 1:
            fire_count = min(streak_result['current_streak'], 3)
            completion_message += f"\n{'🔥' * fire_count} {streak_result['current_streak']}-day streak!"

        # Add achievement notifications
        if new_achievements:
            completion_message += "\n\n🏆 **NEW ACHIEVEMENT"
            if len(new_achievements) > 1:
                completion_message += "S"
            completion_message += "!**"
            for ach in new_achievements:
                completion_message += f"\n• {ach['name']} (+{ach['xp_reward']} XP)"

        await query.edit_message_text(
            completion_message,
            parse_mode="Markdown"
        )

        logger.info(
            f"Reminder completed with gamification: user={user_id}, "
            f"xp={xp_result['new_total_xp']}, level={xp_result['new_level']}, "
            f"streak={streak_result['current_streak']}"
        )

    except Exception as e:
        logger.error(f"Error handling reminder completion: {e}", exc_info=True)
        # ... existing error handling ...
```

---

## Phase 2: Visualization & Reports (Weeks 4-5)

### 2.1 Dashboard Command Handler

**File**: `src/handlers/dashboard.py` (new file)

```python
"""Dashboard command handlers"""
import logging
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from src.utils.auth import is_authorized

logger = logging.getLogger(__name__)


async def handle_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /dashboard command - show daily health snapshot
    """
    user_id = str(update.effective_user.id)

    if not await is_authorized(user_id):
        await update.message.reply_text("Unauthorized")
        return

    try:
        from src.db.gamification import (
            get_user_xp_stats,
            get_user_streaks,
            get_user_achievements
        )
        from src.db.queries import get_reminder_completions
        from datetime import datetime, timedelta

        # Get today's completions
        today = datetime.now().date()
        completions_today = await get_reminder_completions(
            user_id=user_id,
            days=1
        )

        # Get XP stats
        xp_stats = await get_user_xp_stats(user_id)

        # Get active streaks
        streaks = await get_user_streaks(user_id)

        # Get recent achievements
        achievements = await get_user_achievements(user_id)

        # Build dashboard
        tier_emoji = {
            'bronze': '🥉',
            'silver': '🥈',
            'gold': '🥇',
            'platinum': '💎'
        }

        dashboard_text = f"""📊 **Daily Health Dashboard**
__{today.strftime('%A, %B %d, %Y')}__

🏆 **Your Progress**
• Level {xp_stats['current_level']} {tier_emoji.get(xp_stats['current_tier'], '')} ({xp_stats['total_xp']:,} XP)
• {xp_stats['xp_for_next_level']} XP to next level

✅ **Today**
• Reminders completed: {len(completions_today)}

🔥 **Active Streaks**"""

        if streaks:
            for streak in streaks[:3]:  # Top 3
                dashboard_text += f"\n• {streak['streak_type'].replace('_', ' ').title()}: {streak['current_streak']} days"
        else:
            dashboard_text += "\n• Start your first streak today!"

        dashboard_text += f"\n\n🏅 **Achievements**: {len(achievements)} unlocked"

        dashboard_text += "\n\n_Use /stats for detailed statistics_"

        await update.message.reply_text(
            dashboard_text,
            parse_mode="Markdown"
        )

        logger.info(f"Sent dashboard to {user_id}")

    except Exception as e:
        logger.error(f"Error generating dashboard: {e}", exc_info=True)
        await update.message.reply_text("Error generating dashboard. Please try again.")


# Create command handler
dashboard_handler = CommandHandler("dashboard", handle_dashboard)
```

### 2.2 Weekly Report Generator

**File**: `src/scheduler/report_generator.py` (new file)

```python
"""Automated weekly and monthly report generation"""
import logging
from datetime import datetime, timedelta, date
from telegram.ext import Application
from src.db.connection import db
from src.db.gamification import get_user_xp_stats, get_user_streaks, get_user_achievements
from src.db.queries import get_reminder_completions, get_active_reminders

logger = logging.getLogger(__name__)


async def generate_weekly_report(user_id: str) -> str:
    """
    Generate weekly summary report

    Returns:
        Formatted report text
    """
    # Calculate week boundaries
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday
    week_end = week_start + timedelta(days=6)  # Sunday

    # Get XP stats
    xp_stats = await get_user_xp_stats(user_id)

    # Get completions for the week
    completions = await get_reminder_completions(user_id=user_id, days=7)

    # Get active reminders
    reminders = await get_active_reminders(user_id)

    # Calculate completion rate
    expected_completions = len(reminders) * 7  # Assuming daily reminders
    completion_rate = (len(completions) / expected_completions * 100) if expected_completions > 0 else 0

    # Get streaks
    streaks = await get_user_streaks(user_id)

    # Get achievements this week
    achievements_all = await get_user_achievements(user_id)
    week_ago = datetime.now() - timedelta(days=7)
    achievements_this_week = [
        a for a in achievements_all
        if a['unlocked_at'] >= week_ago
    ]

    # Build report
    report = f"""📅 **Weekly Health Report**
__{week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}__

🎯 **This Week's Performance**
• Completion Rate: {completion_rate:.1f}%
• Reminders Completed: {len(completions)} / {expected_completions}
• XP Earned: [Calculate from transactions]
• Current Level: {xp_stats['current_level']}

🔥 **Streaks**"""

    if streaks:
        for streak in streaks[:3]:
            report += f"\n• {streak['streak_type'].replace('_', ' ').title()}: {streak['current_streak']} days"
    else:
        report += "\n• No active streaks - start fresh this week!"

    if achievements_this_week:
        report += f"\n\n🏆 **New Achievements This Week**"
        for ach in achievements_this_week:
            report += f"\n• {ach.get('icon_emoji', '🏆')} {ach['name']}"

    # Add insights
    if completion_rate >= 90:
        report += "\n\n💪 **Amazing week! You're crushing it!**"
    elif completion_rate >= 70:
        report += "\n\n👍 **Great work this week! Keep it up!**"
    elif completion_rate >= 50:
        report += "\n\n💙 **Good effort. Every step counts!**"
    else:
        report += "\n\n🌱 **New week, new opportunities. You've got this!**"

    report += "\n\n_Keep building those healthy habits!_"

    return report


async def send_weekly_reports(application: Application) -> None:
    """
    Send weekly reports to all opted-in users

    Called by scheduler every Monday morning
    """
    try:
        # Get all users who want weekly reports
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT user_id
                    FROM user_motivation_profile
                    WHERE opt_in_reports = true
                    """
                )
                users = await cur.fetchall()

        sent_count = 0
        for user_row in users:
            user_id = user_row[0]

            try:
                # Generate report
                report = await generate_weekly_report(user_id)

                # Send via Telegram
                await application.bot.send_message(
                    chat_id=user_id,
                    text=report,
                    parse_mode="Markdown"
                )

                # Log report generation
                async with db.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            """
                            INSERT INTO report_history
                            (user_id, report_type, period_start_date, period_end_date, sent_at)
                            VALUES (%s, 'weekly', %s, %s, CURRENT_TIMESTAMP)
                            """,
                            (user_id,
                             (date.today() - timedelta(days=7)).isoformat(),
                             date.today().isoformat())
                        )
                        await conn.commit()

                sent_count += 1
                logger.info(f"Sent weekly report to {user_id}")

            except Exception as e:
                logger.error(f"Failed to send weekly report to {user_id}: {e}")

        logger.info(f"Sent {sent_count} weekly reports")

    except Exception as e:
        logger.error(f"Error sending weekly reports: {e}", exc_info=True)


async def generate_monthly_report(user_id: str) -> str:
    """Generate comprehensive monthly report (similar structure, expanded scope)"""
    # TODO: Implement (similar to weekly, but 30-day scope)
    pass
```

### 2.3 Schedule Weekly Reports

**Modify**: `src/scheduler/reminder_manager.py`

```python
# Add to ReminderManager class

async def schedule_weekly_reports(self) -> None:
    """
    Schedule weekly reports to be sent every Monday at 9 AM
    """
    from datetime import time
    from zoneinfo import ZoneInfo
    from src.scheduler.report_generator import send_weekly_reports

    # Schedule for Mondays at 9 AM UTC
    self.job_queue.run_daily(
        callback=lambda context: send_weekly_reports(self.application),
        time=time(hour=9, minute=0, tzinfo=ZoneInfo("UTC")),
        days=(0,),  # Monday = 0
        name="weekly_reports"
    )

    logger.info("Scheduled weekly report generation")
```

---

## Phase 3: Adaptive Intelligence (Weeks 6-7)

### 3.1 Motivation Profile Detection

**File**: `src/db/adaptive.py` (new file)

```python
"""Adaptive intelligence functions - motivation profiles, smart suggestions"""
import logging
from typing import Optional
from datetime import datetime, timedelta
from src.db.connection import db

logger = logging.getLogger(__name__)


async def detect_motivation_profile(user_id: str) -> str:
    """
    Detect user's motivation type based on behavior patterns

    Types:
    - achiever: Loves streaks, levels, milestones
    - competitor: Responds to comparisons, leaderboards
    - socializer: Engages with group features
    - explorer: Tries new features, experiments

    Returns:
        Motivation type string
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Analyze user behavior

            # Check achievement unlock rate
            await cur.execute(
                """
                SELECT COUNT(*) FROM user_achievements
                WHERE user_id = %s
                  AND unlocked_at > NOW() - INTERVAL '30 days'
                """,
                (user_id,)
            )
            recent_achievements = (await cur.fetchone())[0]

            # Check streak consistency
            await cur.execute(
                """
                SELECT AVG(current_streak), COUNT(*)
                FROM user_streaks
                WHERE user_id = %s AND current_streak > 0
                """,
                (user_id,)
            )
            streak_data = await cur.fetchone()
            avg_streak = streak_data[0] if streak_data[0] else 0
            active_streaks = streak_data[1]

            # Check completion rate variance (exploration indicator)
            await cur.execute(
                """
                SELECT COUNT(DISTINCT source_id)
                FROM xp_transactions
                WHERE user_id = %s
                  AND timestamp > NOW() - INTERVAL '30 days'
                """,
                (user_id,)
            )
            activity_variety = (await cur.fetchone())[0]

            # Classify
            if active_streaks >= 3 and avg_streak > 14:
                motivation_type = 'achiever'
            elif activity_variety >= 5:
                motivation_type = 'explorer'
            else:
                motivation_type = 'achiever'  # Default

            # Save profile
            await cur.execute(
                """
                INSERT INTO user_motivation_profile (user_id, motivation_type)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE
                SET motivation_type = EXCLUDED.motivation_type,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, motivation_type)
            )
            await conn.commit()

            return motivation_type


async def get_personalized_message(
    user_id: str,
    event_type: str,
    context: dict = None
) -> str:
    """
    Get personalized motivational message based on user's motivation profile

    Args:
        user_id: Telegram user ID
        event_type: Type of event ('streak_milestone', 'level_up', 'achievement_unlock', etc.)
        context: Additional context (streak count, level, etc.)

    Returns:
        Personalized message string
    """
    # Get user's motivation profile
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT motivation_type, preferred_messaging_style
                FROM user_motivation_profile
                WHERE user_id = %s
                """,
                (user_id,)
            )
            row = await cur.fetchone()

            if not row:
                # Detect motivation profile
                motivation_type = await detect_motivation_profile(user_id)
                messaging_style = 'supportive'
            else:
                motivation_type = row[0]
                messaging_style = row[1]

    # Message templates by motivation type
    templates = {
        'achiever': {
            'streak_milestone': [
                "🔥 {streak} days! You're unstoppable!",
                "💪 {streak}-day streak! Every day counts!",
                "🎯 {streak} days in a row - consistency is your superpower!"
            ],
            'level_up': [
                "🎉 Level {level} unlocked! Keep climbing!",
                "⬆️ You've reached Level {level}! Progress!",
                "🏆 Level {level}! You're leveling up your health!"
            ]
        },
        'competitor': {
            'streak_milestone': [
                "🥇 {streak} days! You're ahead of the game!",
                "📈 {streak}-day streak! Top performer!",
                "💎 {streak} days - elite consistency!"
            ],
            'level_up': [
                "🚀 Level {level}! Rising through the ranks!",
                "⚡ Level {level} achieved! Keep dominating!",
                "🏅 Level {level} - you're climbing the leaderboard!"
            ]
        },
        'socializer': {
            'streak_milestone': [
                "🎉 {streak} days! Your progress inspires others!",
                "💙 {streak}-day streak! The community is proud!",
                "👏 {streak} days - you're setting an example!"
            ],
            'level_up': [
                "🌟 Level {level}! Share your success!",
                "🎊 Level {level}! Celebrate with the community!",
                "💬 Level {level} reached! Tell us your secret!"
            ]
        },
        'explorer': {
            'streak_milestone': [
                "🌱 {streak} days! New habit established!",
                "🔍 {streak}-day streak! Discovery through consistency!",
                "✨ {streak} days - exploring what works for you!"
            ],
            'level_up': [
                "🎨 Level {level}! New features unlocked!",
                "🗺️ Level {level}! More to explore!",
                "🌈 Level {level} - try new challenges!"
            ]
        }
    }

    # Get templates for user's type
    user_templates = templates.get(motivation_type, templates['achiever'])
    event_templates = user_templates.get(event_type, ["Great job!"])

    # Select random template
    import random
    message = random.choice(event_templates)

    # Format with context
    if context:
        message = message.format(**context)

    return message
```

### 3.2 Smart Suggestions (Difficult Day Detection)

**File**: `src/db/insights.py` (new file)

```python
"""Insight generation and smart suggestions"""
import logging
from datetime import datetime, timedelta, date
from src.db.connection import db

logger = logging.getLogger(__name__)


async def detect_difficult_day(user_id: str) -> Optional[dict]:
    """
    Detect if user is having a difficult day based on patterns

    Returns:
        dict with is_difficult, reason, suggestion
    """
    today = date.today()

    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Check for skips today
            await cur.execute(
                """
                SELECT COUNT(*)
                FROM reminder_skips
                WHERE user_id = %s
                  AND DATE(skipped_at) = %s
                """,
                (user_id, today)
            )
            skips_today = (await cur.fetchone())[0]

            # Check for late completions
            await cur.execute(
                """
                SELECT COUNT(*)
                FROM reminder_completions
                WHERE user_id = %s
                  AND DATE(completed_at) = %s
                  AND EXTRACT(EPOCH FROM (completed_at - scheduled_time)) > 7200  -- 2+ hours late
                """,
                (user_id, today)
            )
            late_completions = (await cur.fetchone())[0]

            # Check day of week pattern
            await cur.execute(
                """
                SELECT AVG(skip_count)
                FROM (
                    SELECT DATE(skipped_at) as skip_date, COUNT(*) as skip_count
                    FROM reminder_skips
                    WHERE user_id = %s
                      AND EXTRACT(DOW FROM skipped_at) = EXTRACT(DOW FROM CURRENT_DATE)
                      AND skipped_at > NOW() - INTERVAL '60 days'
                    GROUP BY DATE(skipped_at)
                ) subquery
                """,
                (user_id,)
            )
            avg_skips_this_day = (await cur.fetchone())[0] or 0

            # Determine if difficult day
            is_difficult = False
            reason = None
            suggestion = None

            if skips_today >= 2:
                is_difficult = True
                reason = "multiple_skips_today"
                suggestion = "It's okay to have tough days. Focus on just one small action today."
            elif late_completions >= 2:
                is_difficult = True
                reason = "late_completions"
                suggestion = "Running behind schedule? Try breaking tasks into smaller steps."
            elif avg_skips_this_day > 1.5:
                is_difficult = True
                reason = "challenging_day_of_week"
                day_name = today.strftime('%A')
                suggestion = f"{day_name}s seem challenging. Consider adjusting your schedule for this day."

            return {
                "is_difficult": is_difficult,
                "reason": reason,
                "suggestion": suggestion
            }


async def generate_smart_suggestions(user_id: str) -> list[str]:
    """
    Generate personalized suggestions based on user patterns

    Returns:
        List of suggestion strings
    """
    suggestions = []

    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Analyze completion patterns
            await cur.execute(
                """
                SELECT
                    EXTRACT(HOUR FROM completed_at) as hour,
                    COUNT(*) as count
                FROM reminder_completions
                WHERE user_id = %s
                  AND completed_at > NOW() - INTERVAL '30 days'
                GROUP BY EXTRACT(HOUR FROM completed_at)
                ORDER BY count DESC
                LIMIT 1
                """,
                (user_id,)
            )
            best_hour = await cur.fetchone()

            if best_hour and best_hour[0]:
                hour = int(best_hour[0])
                suggestions.append(
                    f"💡 Your best completion time is around {hour}:00. "
                    f"Consider scheduling more reminders then."
                )

            # Check for broken streaks
            from src.db.gamification import get_user_streaks
            streaks = await get_user_streaks(user_id)

            for streak in streaks:
                if streak['best_streak'] > streak['current_streak'] + 5:
                    domain = streak['streak_type'].replace('_', ' ').title()
                    suggestions.append(
                        f"🔄 You had a {streak['best_streak']}-day {domain} streak before. "
                        f"You can rebuild it!"
                    )

            return suggestions[:3]  # Max 3 suggestions
```

---

## Phase 4: Challenges & Social (Weeks 8-9)

### 4.1 Challenge System Implementation

**File**: `src/db/challenges.py` (new file)

```python
"""Challenge management functions"""
import logging
from typing import Optional
from datetime import datetime, timedelta, date
from uuid import UUID
from src.db.connection import db

logger = logging.getLogger(__name__)


async def start_challenge(
    user_id: str,
    challenge_id: str,
    duration_days: Optional[int] = None
) -> dict:
    """
    Start a challenge for user

    Args:
        user_id: Telegram user ID
        challenge_id: UUID of challenge
        duration_days: Optional override duration

    Returns:
        dict with challenge details and start confirmation
    """
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            # Get challenge details
            await cur.execute(
                """
                SELECT name, description, duration_days, success_criteria, xp_reward
                FROM challenges
                WHERE id = %s AND active = true
                """,
                (challenge_id,)
            )
            challenge = await cur.fetchone()

            if not challenge:
                return {"success": False, "error": "Challenge not found"}

            name, description, default_duration, criteria, xp_reward = challenge
            duration = duration_days or default_duration

            # Calculate target end date
            target_end = date.today() + timedelta(days=duration)

            # Start challenge
            await cur.execute(
                """
                INSERT INTO user_challenges
                (user_id, challenge_id, target_end_date, status, progress)
                VALUES (%s, %s, %s, 'active', %s)
                """,
                (user_id, challenge_id, target_end, '{}')
            )
            await conn.commit()

            return {
                "success": True,
                "name": name,
                "description": description,
                "duration_days": duration,
                "target_end_date": target_end,
                "xp_reward": xp_reward
            }


async def update_challenge_progress(
    user_id: str,
    challenge_id: str,
    progress_data: dict
) -> dict:
    """
    Update progress on active challenge

    Returns:
        dict with updated progress and completion status
    """
    # TODO: Implement progress tracking
    pass


async def get_active_challenges(user_id: str) -> list[dict]:
    """Get all active challenges for user"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT
                    c.name,
                    c.description,
                    c.icon_emoji,
                    uc.started_at,
                    uc.target_end_date,
                    uc.completion_rate,
                    c.xp_reward
                FROM user_challenges uc
                JOIN challenges c ON uc.challenge_id = c.id
                WHERE uc.user_id = %s AND uc.status = 'active'
                ORDER BY uc.started_at DESC
                """,
                (user_id,)
            )
            rows = await cur.fetchall()

            if not rows:
                return []

            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in rows]


async def get_challenge_library() -> list[dict]:
    """Get all available built-in challenges"""
    async with db.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, name, description, difficulty, duration_days,
                       icon_emoji, xp_reward
                FROM challenges
                WHERE challenge_type = 'built_in' AND active = true
                ORDER BY difficulty, duration_days
                """
            )
            rows = await cur.fetchall()

            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in rows]
```

### 4.2 Pre-built Challenge Seed Data

**File**: `migrations/009_challenge_library.sql`

```sql
-- =====================================================
-- Seed Built-in Challenges
-- =====================================================

INSERT INTO challenges (challenge_key, name, description, challenge_type, difficulty, duration_days, success_criteria, xp_reward, icon_emoji, created_by) VALUES

-- EASY CHALLENGES (7 days)
('7_day_streak', '7-Day Streak', 'Complete all health actions for 7 consecutive days', 'built_in', 'easy', 7, '{"type": "streak", "days": 7}', 100, '🎯', 'system'),
('hydration_week', 'Hydration Week', 'Track water intake daily for 7 days', 'built_in', 'easy', 7, '{"type": "daily_action", "action": "hydration", "days": 7}', 75, '💧', 'system'),
('sleep_tracker', 'Sleep Tracker', 'Log sleep quality for 7 consecutive nights', 'built_in', 'easy', 7, '{"type": "daily_action", "action": "sleep_log", "days": 7}', 75, '😴', 'system'),

-- MEDIUM CHALLENGES (14-30 days)
('medication_master', 'Medication Master', 'Take all medications on time for 14 days', 'built_in', 'medium', 14, '{"type": "streak", "domain": "medication", "days": 14, "on_time": true}', 200, '💊', 'system'),
('nutrition_ninja', 'Nutrition Ninja', 'Log all meals for 14 consecutive days', 'built_in', 'medium', 14, '{"type": "daily_action", "action": "food_log", "days": 14}', 200, '🥗', 'system'),
('30_day_consistency', '30-Day Consistency', 'Maintain 80%+ completion rate for 30 days', 'built_in', 'medium', 30, '{"type": "completion_rate", "days": 30, "rate": 80}', 500, '💪', 'system'),

-- HARD CHALLENGES (60-90 days)
('quarter_commitment', 'Quarter Commitment', '90-day streak on any health action', 'built_in', 'hard', 90, '{"type": "streak", "days": 90}', 1000, '🏆', 'system'),
('perfect_month', 'Perfect Month Challenge', '100% completion rate for 30 days', 'built_in', 'hard', 30, '{"type": "completion_rate", "days": 30, "rate": 100}', 750, '💯', 'system'),

-- SPECIALTY CHALLENGES
('workout_warrior', 'Workout Warrior', 'Exercise 5 days a week for 4 weeks', 'built_in', 'medium', 28, '{"type": "weekly_target", "action": "exercise", "weeks": 4, "days_per_week": 5}', 400, '🏋️', 'system'),
('mindful_may', 'Mindful May', 'Practice mindfulness daily for 31 days', 'built_in', 'medium', 31, '{"type": "daily_action", "action": "mindfulness", "days": 31}', 350, '🧘', 'system');
```

---

## Phase 5: Polish & Enhancements (Weeks 10-11)

### 5.1 Completion Notes (from Issue #9 Phase 5)

**Modify**: `src/handlers/reminders.py`

```python
# Add after completion
async def handle_add_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle adding a note to a completion

    Callback data format: add_note|{completion_id}
    """
    # TODO: Implement note addition with templates
    pass
```

### 5.2 UI Enhancements

- Add progress bars (text-based) for XP to next level
- Emoji-based streak indicators
- Achievement showcase command
- Leaderboard (opt-in, non-competitive)

### 5.3 Testing & Optimization

**File**: `tests/integration/test_gamification.py`

```python
"""Integration tests for gamification system"""
import pytest
from src.db.gamification import award_xp, update_streak, check_and_unlock_achievements


@pytest.mark.asyncio
async def test_xp_award_and_level_up():
    """Test XP awarding and level progression"""
    user_id = "test_user_123"

    # Award initial XP
    result = await award_xp(user_id, 50, "test", description="Test XP")

    assert result["new_total_xp"] == 50
    assert result["new_level"] == 1
    assert not result["level_up"]

    # Award enough to level up
    result = await award_xp(user_id, 60, "test")  # Total: 110

    assert result["new_total_xp"] == 110
    assert result["new_level"] == 2
    assert result["level_up"]


@pytest.mark.asyncio
async def test_streak_progression():
    """Test streak tracking across days"""
    user_id = "test_user_456"

    from datetime import date, timedelta

    today = date.today()
    yesterday = today - timedelta(days=1)

    # Start streak
    result = await update_streak(user_id, "medication", action_date=yesterday)
    assert result["current_streak"] == 1

    # Continue streak
    result = await update_streak(user_id, "medication", action_date=today)
    assert result["current_streak"] == 2
    assert result["is_new_best"]


@pytest.mark.asyncio
async def test_achievement_unlock():
    """Test achievement unlock on criteria met"""
    # TODO: Implement
    pass
```

---

## Implementation Checklist

### Week 1-3: Foundation
- [ ] Create migration `008_gamification_foundation.sql`
- [ ] Create migration `008_gamification_seed_achievements.sql`
- [ ] Implement `src/db/gamification.py` (XP, streaks, achievements)
- [ ] Add agent tools to `src/agent/__init__.py` (get_my_stats, etc.)
- [ ] Modify `src/handlers/reminders.py` to integrate gamification
- [ ] Test XP awarding on reminder completion
- [ ] Test streak updates
- [ ] Test achievement unlocking
- [ ] Test level-up notifications

### Week 4-5: Visualization & Reports
- [ ] Create `src/handlers/dashboard.py`
- [ ] Register dashboard command in `src/bot.py`
- [ ] Create `src/scheduler/report_generator.py`
- [ ] Implement weekly report generation
- [ ] Implement monthly report generation
- [ ] Schedule weekly reports in `ReminderManager`
- [ ] Test dashboard display
- [ ] Test report generation and sending

### Week 6-7: Adaptive Intelligence
- [ ] Create `src/db/adaptive.py` (motivation profiles)
- [ ] Implement motivation type detection
- [ ] Implement personalized messaging
- [ ] Create `src/db/insights.py` (smart suggestions)
- [ ] Implement difficult day detection
- [ ] Implement smart timing suggestions
- [ ] Test adaptive messaging
- [ ] Test suggestion generation

### Week 8-9: Challenges & Social
- [ ] Create migration `009_challenge_library.sql`
- [ ] Create `src/db/challenges.py`
- [ ] Implement challenge start/join
- [ ] Implement challenge progress tracking
- [ ] Add challenge agent tools
- [ ] Create challenge command handlers
- [ ] Test challenge flow end-to-end
- [ ] (Optional) Implement group challenges

### Week 10-11: Polish & Testing
- [ ] Implement completion notes with templates
- [ ] Add progress bars and visual enhancements
- [ ] Create achievement showcase command
- [ ] Implement opt-in leaderboard
- [ ] Write integration tests (`tests/integration/test_gamification.py`)
- [ ] Write unit tests for key functions
- [ ] Performance testing (database queries)
- [ ] User acceptance testing
- [ ] Documentation updates
- [ ] Final polish and bug fixes

---

## Success Metrics (Post-Launch)

### Engagement (30 days post-launch)
- [ ] 75%+ use completion buttons regularly
- [ ] 3+ dashboard views per user per week
- [ ] 60%+ open weekly reports
- [ ] 40%+ participate in at least one challenge

### Behavior Change (60 days post-launch)
- [ ] 25% improvement in reminder completion rates
- [ ] 10+ day average streaks for medication reminders
- [ ] 50% reduction in missed days (no completion, no skip)
- [ ] Users actively tracking 2+ health domains on average

### Product Health
- [ ] 2x retention rate for gamification-enabled users vs non-enabled
- [ ] 8/10 average satisfaction score (via surveys)
- [ ] 40%+ acceptance rate for adaptive suggestions
- [ ] Net Promoter Score: 50+

---

## Risk Mitigation

### Technical Risks
1. **Database Performance**: Gamification adds many queries
   - Mitigation: Indexes on hot paths, batch operations, caching
2. **XP Calculation Bugs**: Wrong level calculations could break trust
   - Mitigation: Comprehensive unit tests, manual verification
3. **Achievement Spam**: Too many notifications could be annoying
   - Mitigation: Batch achievements, user preferences for notifications

### User Experience Risks
1. **Overwhelming Complexity**: Too many features at once
   - Mitigation: Progressive disclosure, onboarding flow
2. **Gamification Fatigue**: Users burn out on points/badges
   - Mitigation: Allow opt-out, focus on intrinsic motivation
3. **Unfair Comparisons**: Leaderboards could demotivate
   - Mitigation: Opt-in only, focus on personal progress

### Ethical Risks
1. **Addiction Mechanics**: Gamification could feel manipulative
   - Mitigation: Transparency, user control, no dark patterns
2. **Shame/Guilt**: Breaking streaks could feel punitive
   - Mitigation: Recovery achievements, supportive messaging, freeze days

---

## Future Enhancements (Post-MVP)

1. **Avatar Customization**: Unlock cosmetic items with XP
2. **Health Coins**: Virtual currency for unlocking features
3. **Quests**: Multi-step challenges with narrative
4. **Social Features**: Friend connections, group challenges (opt-in)
5. **Data Export**: Download full gamification history
6. **API**: Allow third-party integrations
7. **Machine Learning**: Predictive streak maintenance, personalized XP rewards

---

## Notes

- All gamification features are **opt-in by default** for new users
- Existing users will be migrated with a notification explaining new features
- Database migrations are **backwards compatible** (can be rolled back)
- All XP values are **configurable** and can be adjusted post-launch
- Achievement criteria use **JSONB** for flexibility in future updates
- Ethical guidelines are **enforced at code level** (no forced engagement, no data exploitation)

---

**End of Plan**
