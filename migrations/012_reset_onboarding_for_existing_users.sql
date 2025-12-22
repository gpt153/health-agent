-- Migration: Reset onboarding for existing users (Issue #24)
-- This allows existing users to experience the fixed onboarding system
-- WITHOUT losing any of their existing data (food logs, conversations, etc)

-- IMPORTANT: This only resets the onboarding_state table
-- All other user data (profiles, food entries, memories) remains intact

-- Step 1: Clear all completed onboarding states
-- This will trigger the onboarding flow next time user sends /start
UPDATE user_onboarding_state
SET
    completed_at = NULL,
    current_step = 'welcome',
    onboarding_path = NULL,
    completed_steps = '{}',
    last_interaction_at = CURRENT_TIMESTAMP
WHERE completed_at IS NOT NULL;

-- Step 2: For users who never started onboarding, ensure they have a row
-- This ensures everyone gets prompted
INSERT INTO user_onboarding_state (user_id, onboarding_path, current_step, completed_at)
SELECT
    u.telegram_id,
    NULL,
    'welcome',
    NULL
FROM users u
LEFT JOIN user_onboarding_state uos ON u.telegram_id = uos.user_id
WHERE uos.user_id IS NULL
ON CONFLICT (user_id) DO NOTHING;

-- Verification query (run this to check results):
-- SELECT
--     user_id,
--     onboarding_path,
--     current_step,
--     completed_at,
--     started_at,
--     last_interaction_at
-- FROM user_onboarding_state
-- ORDER BY last_interaction_at DESC;

-- ROLLBACK PLAN:
-- If you need to undo this migration, you can mark all onboarding as complete:
-- UPDATE user_onboarding_state SET completed_at = CURRENT_TIMESTAMP WHERE completed_at IS NULL;

COMMENT ON TABLE user_onboarding_state IS 'Tracks user progress through onboarding paths - Reset for Issue #24 onboarding fix';
