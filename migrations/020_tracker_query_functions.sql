-- JSONB Query Functions for Custom Tracker System
-- Epic 006 - Phase 3: Advanced querying capabilities for tracker data

-- ================================================================
-- Function: query_tracker_entries
-- Purpose: Query tracker entries by field value with flexible operators
-- ================================================================
CREATE OR REPLACE FUNCTION query_tracker_entries(
    p_user_id TEXT,
    p_category_id UUID,
    p_field_name TEXT,
    p_operator TEXT,  -- '=', '>', '<', '>=', '<=', 'contains', 'in'
    p_value JSONB,
    p_start_date TIMESTAMP DEFAULT NULL,
    p_end_date TIMESTAMP DEFAULT NULL
) RETURNS TABLE (
    id UUID,
    "timestamp" TIMESTAMP,
    data JSONB,
    notes TEXT,
    validation_status TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        te.id,
        te.timestamp,
        te.data,
        te.notes,
        te.validation_status
    FROM tracking_entries te
    WHERE te.user_id = p_user_id
      AND te.category_id = p_category_id
      AND (p_start_date IS NULL OR te.timestamp >= p_start_date)
      AND (p_end_date IS NULL OR te.timestamp <= p_end_date)
      AND te.validation_status = 'valid'  -- Only return valid entries
      AND CASE p_operator
          -- Exact match
          WHEN '=' THEN te.data->p_field_name = p_value
          -- Numeric comparisons (cast to numeric)
          WHEN '>' THEN (te.data->>p_field_name)::numeric > (p_value->>0)::numeric
          WHEN '<' THEN (te.data->>p_field_name)::numeric < (p_value->>0)::numeric
          WHEN '>=' THEN (te.data->>p_field_name)::numeric >= (p_value->>0)::numeric
          WHEN '<=' THEN (te.data->>p_field_name)::numeric <= (p_value->>0)::numeric
          -- Array contains (for multiselect fields)
          WHEN 'contains' THEN te.data->p_field_name ? (p_value->>0)
          -- Value is in array (for checking if field value is in a list)
          WHEN 'in' THEN te.data->p_field_name <@ p_value
          ELSE FALSE
      END
    ORDER BY te.timestamp DESC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION query_tracker_entries IS 'Query tracker entries with flexible field-based filtering';

-- ================================================================
-- Function: aggregate_tracker_field
-- Purpose: Calculate aggregate statistics for a tracker field
-- ================================================================
CREATE OR REPLACE FUNCTION aggregate_tracker_field(
    p_user_id TEXT,
    p_category_id UUID,
    p_field_name TEXT,
    p_aggregation TEXT,  -- 'avg', 'min', 'max', 'count', 'sum'
    p_start_date TIMESTAMP DEFAULT NULL,
    p_end_date TIMESTAMP DEFAULT NULL
) RETURNS NUMERIC AS $$
DECLARE
    result NUMERIC;
BEGIN
    SELECT
        CASE p_aggregation
            WHEN 'avg' THEN AVG((data->>p_field_name)::numeric)
            WHEN 'min' THEN MIN((data->>p_field_name)::numeric)
            WHEN 'max' THEN MAX((data->>p_field_name)::numeric)
            WHEN 'sum' THEN SUM((data->>p_field_name)::numeric)
            WHEN 'count' THEN COUNT(*)
            ELSE NULL
        END INTO result
    FROM tracking_entries
    WHERE user_id = p_user_id
      AND category_id = p_category_id
      AND data ? p_field_name  -- Field exists
      AND validation_status = 'valid'
      AND (p_start_date IS NULL OR timestamp >= p_start_date)
      AND (p_end_date IS NULL OR timestamp <= p_end_date);

    RETURN COALESCE(result, 0);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION aggregate_tracker_field IS 'Calculate statistics (avg, min, max, sum, count) for a tracker field';

-- ================================================================
-- Function: find_tracker_correlation
-- Purpose: Find correlations between two tracker fields
-- ================================================================
CREATE OR REPLACE FUNCTION find_tracker_correlation(
    p_user_id TEXT,
    p_category_id_1 UUID,
    p_field_1 TEXT,
    p_category_id_2 UUID,
    p_field_2 TEXT,
    p_days_range INTEGER DEFAULT 30
) RETURNS TABLE (
    date DATE,
    value_1 NUMERIC,
    value_2 NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        te1.timestamp::DATE as date,
        (te1.data->>p_field_1)::numeric as value_1,
        (te2.data->>p_field_2)::numeric as value_2
    FROM tracking_entries te1
    JOIN tracking_entries te2 ON te1.timestamp::DATE = te2.timestamp::DATE
    WHERE te1.user_id = p_user_id
      AND te2.user_id = p_user_id
      AND te1.category_id = p_category_id_1
      AND te2.category_id = p_category_id_2
      AND te1.validation_status = 'valid'
      AND te2.validation_status = 'valid'
      AND te1.timestamp >= NOW() - INTERVAL '1 day' * p_days_range
      AND te2.timestamp >= NOW() - INTERVAL '1 day' * p_days_range
    ORDER BY date DESC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION find_tracker_correlation IS 'Find correlations between two tracker fields on the same dates';

-- ================================================================
-- Function: get_tracker_entries_by_daterange
-- Purpose: Get all tracker entries for a date range (optimized for dashboards)
-- ================================================================
CREATE OR REPLACE FUNCTION get_tracker_entries_by_daterange(
    p_user_id TEXT,
    p_category_id UUID,
    p_start_date TIMESTAMP,
    p_end_date TIMESTAMP
) RETURNS TABLE (
    id UUID,
    "timestamp" TIMESTAMP,
    data JSONB,
    notes TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        te.id,
        te.timestamp,
        te.data,
        te.notes
    FROM tracking_entries te
    WHERE te.user_id = p_user_id
      AND te.category_id = p_category_id
      AND te.timestamp >= p_start_date
      AND te.timestamp <= p_end_date
      AND te.validation_status = 'valid'
    ORDER BY te.timestamp DESC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_tracker_entries_by_daterange IS 'Get all valid tracker entries within a date range';

-- ================================================================
-- Function: get_recent_tracker_entries
-- Purpose: Get N most recent entries for a tracker
-- ================================================================
CREATE OR REPLACE FUNCTION get_recent_tracker_entries(
    p_user_id TEXT,
    p_category_id UUID,
    p_limit INTEGER DEFAULT 10
) RETURNS TABLE (
    id UUID,
    "timestamp" TIMESTAMP,
    data JSONB,
    notes TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        te.id,
        te.timestamp,
        te.data,
        te.notes
    FROM tracking_entries te
    WHERE te.user_id = p_user_id
      AND te.category_id = p_category_id
      AND te.validation_status = 'valid'
    ORDER BY te.timestamp DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_recent_tracker_entries IS 'Get N most recent valid entries for a tracker';

-- ================================================================
-- Function: count_tracker_entries_by_field_value
-- Purpose: Count how many times a specific field value appears
-- ================================================================
CREATE OR REPLACE FUNCTION count_tracker_entries_by_field_value(
    p_user_id TEXT,
    p_category_id UUID,
    p_field_name TEXT,
    p_field_value JSONB,
    p_start_date TIMESTAMP DEFAULT NULL,
    p_end_date TIMESTAMP DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    count_result INTEGER;
BEGIN
    SELECT COUNT(*)::INTEGER INTO count_result
    FROM tracking_entries
    WHERE user_id = p_user_id
      AND category_id = p_category_id
      AND data->p_field_name = p_field_value
      AND validation_status = 'valid'
      AND (p_start_date IS NULL OR timestamp >= p_start_date)
      AND (p_end_date IS NULL OR timestamp <= p_end_date);

    RETURN count_result;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION count_tracker_entries_by_field_value IS 'Count occurrences of a specific field value';

-- ================================================================
-- Function: get_field_value_distribution
-- Purpose: Get distribution of values for a field (useful for analytics)
-- ================================================================
CREATE OR REPLACE FUNCTION get_field_value_distribution(
    p_user_id TEXT,
    p_category_id UUID,
    p_field_name TEXT,
    p_start_date TIMESTAMP DEFAULT NULL,
    p_end_date TIMESTAMP DEFAULT NULL
) RETURNS TABLE (
    field_value TEXT,
    count BIGINT,
    percentage NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH value_counts AS (
        SELECT
            data->>p_field_name as value,
            COUNT(*) as cnt
        FROM tracking_entries
        WHERE user_id = p_user_id
          AND category_id = p_category_id
          AND data ? p_field_name
          AND validation_status = 'valid'
          AND (p_start_date IS NULL OR timestamp >= p_start_date)
          AND (p_end_date IS NULL OR timestamp <= p_end_date)
        GROUP BY data->>p_field_name
    ),
    total AS (
        SELECT SUM(cnt) as total_count FROM value_counts
    )
    SELECT
        vc.value,
        vc.cnt,
        ROUND((vc.cnt::NUMERIC / t.total_count::NUMERIC) * 100, 2) as pct
    FROM value_counts vc
    CROSS JOIN total t
    ORDER BY vc.cnt DESC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_field_value_distribution IS 'Get distribution of values for a field with counts and percentages';

-- ================================================================
-- Function: find_pattern_days
-- Purpose: Find days matching a specific pattern (e.g., low energy days)
-- ================================================================
CREATE OR REPLACE FUNCTION find_pattern_days(
    p_user_id TEXT,
    p_category_id UUID,
    p_field_name TEXT,
    p_threshold NUMERIC,
    p_operator TEXT,  -- '<', '>', '<=', '>=', '='
    p_days_back INTEGER DEFAULT 30
) RETURNS TABLE (
    date DATE,
    field_value NUMERIC,
    notes TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        te.timestamp::DATE as date,
        (te.data->>p_field_name)::numeric as field_value,
        te.notes
    FROM tracking_entries te
    WHERE te.user_id = p_user_id
      AND te.category_id = p_category_id
      AND te.data ? p_field_name
      AND te.validation_status = 'valid'
      AND te.timestamp >= NOW() - INTERVAL '1 day' * p_days_back
      AND CASE p_operator
          WHEN '<' THEN (te.data->>p_field_name)::numeric < p_threshold
          WHEN '>' THEN (te.data->>p_field_name)::numeric > p_threshold
          WHEN '<=' THEN (te.data->>p_field_name)::numeric <= p_threshold
          WHEN '>=' THEN (te.data->>p_field_name)::numeric >= p_threshold
          WHEN '=' THEN (te.data->>p_field_name)::numeric = p_threshold
          ELSE FALSE
      END
    ORDER BY date DESC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION find_pattern_days IS 'Find days where a field value matches a threshold condition';

-- ================================================================
-- Create indexes for better query performance
-- ================================================================

-- Index for timestamp-based queries (already exists, but ensure it's there)
CREATE INDEX IF NOT EXISTS idx_tracking_entries_user_category_timestamp
ON tracking_entries(user_id, category_id, timestamp DESC);

-- Index for validation status filtering
CREATE INDEX IF NOT EXISTS idx_tracking_entries_valid_only
ON tracking_entries(category_id, validation_status)
WHERE validation_status = 'valid';

-- GIN index for JSONB data queries (using jsonb_path_ops for better performance)
-- This already exists from migration 019, but ensuring it's optimal
DROP INDEX IF EXISTS idx_tracking_entries_data_advanced;
CREATE INDEX idx_tracking_entries_data_advanced
ON tracking_entries USING GIN(data jsonb_path_ops);
