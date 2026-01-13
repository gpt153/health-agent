-- Disable onboarding for all users
-- This migration marks all existing users as having completed onboarding
-- and prevents new users from entering the onboarding flow

-- Mark all incomplete onboarding as completed
UPDATE user_onboarding_state
SET completed_at = CURRENT_TIMESTAMP,
    current_step = 'completed',
    last_interaction_at = CURRENT_TIMESTAMP
WHERE completed_at IS NULL;

-- Add comment for audit trail
COMMENT ON TABLE user_onboarding_state IS 'Onboarding system disabled 2026-01-05 - all users auto-completed';
