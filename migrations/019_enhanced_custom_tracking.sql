-- Enhanced Custom Tracking System
-- Epic 006 - Phase 1: Database Schema Enhancement

-- Enhance tracking_categories with validation and metadata
ALTER TABLE tracking_categories
ADD COLUMN IF NOT EXISTS field_schema JSONB,
ADD COLUMN IF NOT EXISTS validation_rules JSONB,
ADD COLUMN IF NOT EXISTS icon TEXT,
ADD COLUMN IF NOT EXISTS color TEXT,
ADD COLUMN IF NOT EXISTS category_type TEXT DEFAULT 'custom';

-- Add constraints
ALTER TABLE tracking_categories
DROP CONSTRAINT IF EXISTS valid_category_type;

ALTER TABLE tracking_categories
ADD CONSTRAINT valid_category_type
CHECK (category_type IN ('custom', 'system', 'template'));

-- Enhance tracking_entries with metadata
ALTER TABLE tracking_entries
ADD COLUMN IF NOT EXISTS validation_status TEXT DEFAULT 'valid',
ADD COLUMN IF NOT EXISTS validation_errors JSONB;

-- Add constraints for validation status
ALTER TABLE tracking_entries
DROP CONSTRAINT IF EXISTS valid_validation_status;

ALTER TABLE tracking_entries
ADD CONSTRAINT valid_validation_status
CHECK (validation_status IN ('valid', 'warning', 'error'));

-- Add indexes for pattern queries
CREATE INDEX IF NOT EXISTS idx_tracking_categories_type
ON tracking_categories(user_id, category_type, active);

CREATE INDEX IF NOT EXISTS idx_tracking_entries_category_time
ON tracking_entries(category_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_tracking_entries_validation
ON tracking_entries(validation_status)
WHERE validation_status != 'valid';

-- Add GIN index for complex JSONB queries (using jsonb_path_ops for better performance)
CREATE INDEX IF NOT EXISTS idx_tracking_entries_data_advanced
ON tracking_entries USING GIN(data jsonb_path_ops);

-- Add comments for documentation
COMMENT ON COLUMN tracking_categories.field_schema IS 'JSON Schema defining valid field types and constraints';
COMMENT ON COLUMN tracking_categories.validation_rules IS 'Custom validation rules for cross-field validation';
COMMENT ON COLUMN tracking_categories.icon IS 'Emoji icon for tracker (e.g., 🩸, ⚡, 💊)';
COMMENT ON COLUMN tracking_categories.color IS 'Hex color code for UI display';
COMMENT ON COLUMN tracking_categories.category_type IS 'Type: custom (user-created), system (built-in), template (predefined)';
COMMENT ON COLUMN tracking_entries.validation_status IS 'Validation status: valid, warning, error';
COMMENT ON COLUMN tracking_entries.validation_errors IS 'JSONB object containing validation error details per field';
