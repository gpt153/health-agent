-- Add support for correcting food entries
-- This allows updating existing food entries when users correct information

-- Add correction tracking fields to food_entries
ALTER TABLE food_entries
ADD COLUMN IF NOT EXISTS correction_note TEXT,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN IF NOT EXISTS corrected_by VARCHAR(50); -- 'user' or 'auto'

-- Add trigger to auto-update updated_at timestamp
CREATE TRIGGER update_food_entries_updated_at BEFORE UPDATE ON food_entries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add index for finding recently updated entries
CREATE INDEX IF NOT EXISTS idx_food_entries_updated_at ON food_entries(updated_at DESC);

-- Add audit log table for tracking all food entry changes
CREATE TABLE IF NOT EXISTS food_entry_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    food_entry_id UUID NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    action VARCHAR(50) NOT NULL, -- 'created', 'updated', 'deleted'
    old_values JSONB,
    new_values JSONB,
    correction_note TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_food_entry_audit_entry_id ON food_entry_audit(food_entry_id);
CREATE INDEX IF NOT EXISTS idx_food_entry_audit_user_timestamp ON food_entry_audit(user_id, timestamp DESC);
