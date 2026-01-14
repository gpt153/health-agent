-- Migration: Add conditional reminder checking
-- Date: 2026-01-14
-- Description: Add check_condition JSONB field to reminders table to enable conditional reminder logic

-- Add check_condition column to reminders table
-- This column stores conditional logic configuration in JSONB format
-- Example structure:
--   {"type": "food_logged", "window_hours": 2, "meal_type": "lunch"}
--   {"type": "completion_check"}
-- NULL value means no conditions (backward compatible with existing reminders)
ALTER TABLE reminders
ADD COLUMN check_condition JSONB DEFAULT NULL;

-- Add comment to document column purpose
COMMENT ON COLUMN reminders.check_condition IS
'Conditional logic for smart reminders. If condition is met, reminder is skipped. Supported types: food_logged (check if food logged in window_hours), completion_check (check if reminder completed today). NULL = no conditions.';
