-- Add master code support to invite_codes table
-- Migration 004: Master Code Feature

-- Add columns for master code functionality
ALTER TABLE invite_codes ADD COLUMN IF NOT EXISTS is_master_code BOOLEAN DEFAULT false;
ALTER TABLE invite_codes ADD COLUMN IF NOT EXISTS description TEXT;

-- Create index for efficient master code lookups
CREATE INDEX IF NOT EXISTS idx_invite_codes_master ON invite_codes(is_master_code) WHERE is_master_code = true;

-- Add comments for clarity
COMMENT ON COLUMN invite_codes.is_master_code IS 'true for permanent reusable codes with unlimited uses, false for regular codes';
COMMENT ON COLUMN invite_codes.description IS 'Human-readable description of the code purpose (e.g., "Family & Friends Master Code")';

-- Example: Create a master code (commented out, run manually if needed)
-- INSERT INTO invite_codes (code, created_by, max_uses, tier, trial_days, is_master_code, description, active)
-- VALUES ('family-premium-access', '7376426503', NULL, 'premium', 0, true, 'VIP Friends and Family Code', true);
