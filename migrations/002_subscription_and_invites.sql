-- Add subscription fields to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR(20) DEFAULT 'free';
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_start_date TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_end_date TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS activated_at TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS invite_code_used VARCHAR(50);

-- Create invite codes table
CREATE TABLE IF NOT EXISTS invite_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) UNIQUE NOT NULL,
    max_uses INTEGER,  -- NULL = unlimited uses
    uses_count INTEGER DEFAULT 0,
    tier VARCHAR(20) DEFAULT 'free',  -- subscription tier this code grants
    trial_days INTEGER DEFAULT 0,  -- days of trial (0 = no trial)
    created_by VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,  -- NULL = never expires
    active BOOLEAN DEFAULT true
);

-- Create index for faster code lookups
CREATE INDEX IF NOT EXISTS idx_invite_codes_code ON invite_codes(code) WHERE active = true;
CREATE INDEX IF NOT EXISTS idx_users_subscription_status ON users(subscription_status);

-- Add comments for clarity
COMMENT ON COLUMN users.subscription_status IS 'pending: awaiting activation, trial: trial period, active: paid/active, cancelled: cancelled but still has time, expired: subscription ended';
COMMENT ON COLUMN invite_codes.max_uses IS 'NULL means unlimited uses, otherwise number of times code can be used';
