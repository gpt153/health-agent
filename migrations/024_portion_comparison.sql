-- Portion Comparison System (Epic 009 - Phase 4)
-- Compare current photo portions to reference images using visual analysis

-- ================================================================
-- Table: food_item_detections
-- Purpose: Store bounding boxes for detected food items in images
-- ================================================================
CREATE TABLE IF NOT EXISTS food_item_detections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    food_entry_id UUID NOT NULL REFERENCES food_entries(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    photo_path VARCHAR(500) NOT NULL,

    -- Detected food item details
    item_name VARCHAR(200) NOT NULL,  -- "rice", "chicken", etc.

    -- Bounding box (normalized 0-1 coordinates)
    bbox_x FLOAT NOT NULL CHECK (bbox_x >= 0 AND bbox_x <= 1),
    bbox_y FLOAT NOT NULL CHECK (bbox_y >= 0 AND bbox_y <= 1),
    bbox_width FLOAT NOT NULL CHECK (bbox_width >= 0 AND bbox_width <= 1),
    bbox_height FLOAT NOT NULL CHECK (bbox_height >= 0 AND bbox_height <= 1),

    -- Calculated area (pixels or normalized)
    pixel_area FLOAT NOT NULL CHECK (pixel_area >= 0),

    -- Detection metadata
    detection_confidence FLOAT CHECK (detection_confidence >= 0 AND detection_confidence <= 1),
    detection_method VARCHAR(50) DEFAULT 'vision_ai',  -- 'vision_ai', 'manual', 'heuristic'

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_detection_food_entry FOREIGN KEY (food_entry_id)
        REFERENCES food_entries(id) ON DELETE CASCADE,
    CONSTRAINT fk_detection_user FOREIGN KEY (user_id)
        REFERENCES users(telegram_id) ON DELETE CASCADE
);

-- Indexes for food item detections
CREATE INDEX IF NOT EXISTS idx_food_detections_entry
    ON food_item_detections(food_entry_id);

CREATE INDEX IF NOT EXISTS idx_food_detections_user
    ON food_item_detections(user_id);

CREATE INDEX IF NOT EXISTS idx_food_detections_user_item
    ON food_item_detections(user_id, item_name);

CREATE INDEX IF NOT EXISTS idx_food_detections_created
    ON food_item_detections(created_at DESC);

-- ================================================================
-- Table: portion_comparisons
-- Purpose: Store portion comparisons between current and reference images
-- ================================================================
CREATE TABLE IF NOT EXISTS portion_comparisons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,

    -- Current vs reference food entries
    current_food_entry_id UUID NOT NULL REFERENCES food_entries(id) ON DELETE CASCADE,
    reference_food_entry_id UUID NOT NULL REFERENCES food_entries(id) ON DELETE CASCADE,

    -- Food item being compared
    item_name VARCHAR(200) NOT NULL,

    -- Area measurements
    current_area FLOAT NOT NULL CHECK (current_area >= 0),
    reference_area FLOAT NOT NULL CHECK (reference_area >= 0),
    area_difference_ratio FLOAT NOT NULL,  -- (current - ref) / ref

    -- Portion estimates
    estimated_grams_difference FLOAT,  -- Can be positive or negative
    confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1),

    -- Context used for Vision AI enhancement
    comparison_context TEXT,

    -- Optional plate reference
    plate_id UUID REFERENCES recognized_plates(id) ON DELETE SET NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_comparison_user FOREIGN KEY (user_id)
        REFERENCES users(telegram_id) ON DELETE CASCADE,
    CONSTRAINT fk_comparison_current FOREIGN KEY (current_food_entry_id)
        REFERENCES food_entries(id) ON DELETE CASCADE,
    CONSTRAINT fk_comparison_reference FOREIGN KEY (reference_food_entry_id)
        REFERENCES food_entries(id) ON DELETE CASCADE
);

-- Indexes for portion comparisons
CREATE INDEX IF NOT EXISTS idx_portion_comparisons_current
    ON portion_comparisons(current_food_entry_id);

CREATE INDEX IF NOT EXISTS idx_portion_comparisons_reference
    ON portion_comparisons(reference_food_entry_id);

CREATE INDEX IF NOT EXISTS idx_portion_comparisons_user
    ON portion_comparisons(user_id);

CREATE INDEX IF NOT EXISTS idx_portion_comparisons_user_created
    ON portion_comparisons(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_portion_comparisons_item
    ON portion_comparisons(item_name);

-- ================================================================
-- Table: portion_estimate_accuracy
-- Purpose: Track accuracy of portion estimates for learning
-- ================================================================
CREATE TABLE IF NOT EXISTS portion_estimate_accuracy (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    portion_comparison_id UUID NOT NULL REFERENCES portion_comparisons(id) ON DELETE CASCADE,

    -- Estimate vs reality
    estimated_grams FLOAT NOT NULL,
    user_confirmed_grams FLOAT NOT NULL,
    variance_percentage FLOAT NOT NULL,  -- abs(estimated - confirmed) / confirmed * 100

    -- Learning data for improvement
    plate_id UUID REFERENCES recognized_plates(id) ON DELETE SET NULL,
    food_item_type VARCHAR(200) NOT NULL,
    visual_fill_percentage FLOAT CHECK (visual_fill_percentage >= 0 AND visual_fill_percentage <= 1),

    -- Context at time of estimate
    camera_angle_notes TEXT,
    lighting_notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_accuracy_user FOREIGN KEY (user_id)
        REFERENCES users(telegram_id) ON DELETE CASCADE,
    CONSTRAINT fk_accuracy_comparison FOREIGN KEY (portion_comparison_id)
        REFERENCES portion_comparisons(id) ON DELETE CASCADE
);

-- Indexes for portion estimate accuracy
CREATE INDEX IF NOT EXISTS idx_estimate_accuracy_user
    ON portion_estimate_accuracy(user_id);

CREATE INDEX IF NOT EXISTS idx_estimate_accuracy_comparison
    ON portion_estimate_accuracy(portion_comparison_id);

CREATE INDEX IF NOT EXISTS idx_estimate_accuracy_variance
    ON portion_estimate_accuracy(variance_percentage);

CREATE INDEX IF NOT EXISTS idx_estimate_accuracy_food_type
    ON portion_estimate_accuracy(food_item_type);

CREATE INDEX IF NOT EXISTS idx_estimate_accuracy_plate
    ON portion_estimate_accuracy(plate_id) WHERE plate_id IS NOT NULL;

-- ================================================================
-- Function: get_user_portion_accuracy
-- Purpose: Get accuracy statistics for a user
-- ================================================================
CREATE OR REPLACE FUNCTION get_user_portion_accuracy(p_user_id TEXT)
RETURNS TABLE (
    total_estimates INTEGER,
    avg_variance_percentage FLOAT,
    within_20_percent INTEGER,
    within_10_percent INTEGER,
    accuracy_rate FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::INTEGER AS total_estimates,
        AVG(pea.variance_percentage)::FLOAT AS avg_variance_percentage,
        COUNT(*) FILTER (WHERE pea.variance_percentage <= 20)::INTEGER AS within_20_percent,
        COUNT(*) FILTER (WHERE pea.variance_percentage <= 10)::INTEGER AS within_10_percent,
        (COUNT(*) FILTER (WHERE pea.variance_percentage <= 20)::FLOAT /
            NULLIF(COUNT(*)::FLOAT, 0) * 100)::FLOAT AS accuracy_rate
    FROM portion_estimate_accuracy pea
    WHERE pea.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- ================================================================
-- Function: get_food_item_portion_history
-- Purpose: Get portion comparison history for a specific food item
-- ================================================================
CREATE OR REPLACE FUNCTION get_food_item_portion_history(
    p_user_id TEXT,
    p_food_item VARCHAR(200),
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    comparison_id UUID,
    comparison_date TIMESTAMP,
    area_difference_ratio FLOAT,
    estimated_grams_difference FLOAT,
    confirmed_grams_difference FLOAT,
    variance_percentage FLOAT,
    plate_id UUID
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        pc.id AS comparison_id,
        pc.created_at AS comparison_date,
        pc.area_difference_ratio,
        pc.estimated_grams_difference,
        pea.user_confirmed_grams - pea.estimated_grams AS confirmed_grams_difference,
        pea.variance_percentage,
        pc.plate_id
    FROM portion_comparisons pc
    LEFT JOIN portion_estimate_accuracy pea ON pc.id = pea.portion_comparison_id
    WHERE pc.user_id = p_user_id
      AND pc.item_name = p_food_item
    ORDER BY pc.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ================================================================
-- Function: get_plate_portion_accuracy
-- Purpose: Get accuracy statistics for a specific plate
-- ================================================================
CREATE OR REPLACE FUNCTION get_plate_portion_accuracy(p_plate_id UUID)
RETURNS TABLE (
    total_estimates INTEGER,
    avg_variance_percentage FLOAT,
    within_20_percent INTEGER,
    most_accurate_food_type VARCHAR(200)
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::INTEGER AS total_estimates,
        AVG(pea.variance_percentage)::FLOAT AS avg_variance_percentage,
        COUNT(*) FILTER (WHERE pea.variance_percentage <= 20)::INTEGER AS within_20_percent,
        (
            SELECT pea2.food_item_type
            FROM portion_estimate_accuracy pea2
            WHERE pea2.plate_id = p_plate_id
            GROUP BY pea2.food_item_type
            ORDER BY AVG(pea2.variance_percentage) ASC
            LIMIT 1
        ) AS most_accurate_food_type
    FROM portion_estimate_accuracy pea
    WHERE pea.plate_id = p_plate_id;
END;
$$ LANGUAGE plpgsql;

-- ================================================================
-- Function: calculate_area_difference_ratio
-- Purpose: Helper to calculate area difference ratio
-- ================================================================
CREATE OR REPLACE FUNCTION calculate_area_difference_ratio(
    p_current_area FLOAT,
    p_reference_area FLOAT
)
RETURNS FLOAT AS $$
BEGIN
    IF p_reference_area = 0 OR p_reference_area IS NULL THEN
        RETURN NULL;  -- Cannot calculate ratio
    END IF;

    RETURN (p_current_area - p_reference_area) / p_reference_area;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ================================================================
-- Function: calculate_variance_percentage
-- Purpose: Helper to calculate variance percentage
-- ================================================================
CREATE OR REPLACE FUNCTION calculate_variance_percentage(
    p_estimated FLOAT,
    p_actual FLOAT
)
RETURNS FLOAT AS $$
BEGIN
    IF p_actual = 0 OR p_actual IS NULL THEN
        RETURN NULL;  -- Cannot calculate variance
    END IF;

    RETURN ABS(p_estimated - p_actual) / ABS(p_actual) * 100;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ================================================================
-- Comments for documentation
-- ================================================================
COMMENT ON TABLE food_item_detections IS
'Stores bounding boxes and metadata for detected food items in images';

COMMENT ON TABLE portion_comparisons IS
'Stores portion comparisons between current and reference food images';

COMMENT ON TABLE portion_estimate_accuracy IS
'Tracks accuracy of portion estimates vs user-confirmed amounts for learning';

COMMENT ON FUNCTION get_user_portion_accuracy IS
'Returns accuracy statistics for a user: total estimates, average variance, and accuracy rate';

COMMENT ON FUNCTION get_food_item_portion_history IS
'Returns portion comparison history for a specific food item for a user';

COMMENT ON FUNCTION get_plate_portion_accuracy IS
'Returns accuracy statistics for portion estimates using a specific plate';

COMMENT ON FUNCTION calculate_area_difference_ratio IS
'Calculates the ratio of area difference: (current - reference) / reference';

COMMENT ON FUNCTION calculate_variance_percentage IS
'Calculates the percentage variance between estimated and actual values';
