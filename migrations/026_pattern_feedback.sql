-- Migration: Add pattern feedback system
-- Epic 009 - Phase 7: Integration & Agent Tools
-- Enables user feedback on discovered patterns for quality improvement

-- Add user_feedback column to discovered_patterns
ALTER TABLE discovered_patterns ADD COLUMN IF NOT EXISTS user_feedback JSONB DEFAULT '{
    "helpful_count": 0,
    "not_helpful_count": 0,
    "feedback_history": []
}'::jsonb;

-- Create index for feedback queries
CREATE INDEX IF NOT EXISTS idx_discovered_patterns_feedback
ON discovered_patterns USING GIN (user_feedback);

-- Function to record pattern feedback
CREATE OR REPLACE FUNCTION record_pattern_feedback(
    p_pattern_id INTEGER,
    p_is_helpful BOOLEAN,
    p_user_comment TEXT DEFAULT NULL
) RETURNS VOID AS $$
DECLARE
    v_feedback_entry JSONB;
BEGIN
    -- Build feedback entry
    v_feedback_entry := jsonb_build_object(
        'timestamp', NOW(),
        'is_helpful', p_is_helpful,
        'comment', p_user_comment
    );

    -- Add to feedback history
    UPDATE discovered_patterns
    SET user_feedback = jsonb_set(
        user_feedback,
        '{feedback_history}',
        COALESCE(user_feedback->'feedback_history', '[]'::jsonb) || v_feedback_entry
    )
    WHERE id = p_pattern_id;

    -- Update counters
    IF p_is_helpful THEN
        UPDATE discovered_patterns
        SET user_feedback = jsonb_set(
            user_feedback,
            '{helpful_count}',
            to_jsonb((COALESCE((user_feedback->>'helpful_count')::int, 0) + 1))
        ),
        user_feedback = jsonb_set(
            user_feedback,
            '{last_helpful}',
            to_jsonb(NOW()::text)
        )
        WHERE id = p_pattern_id;
    ELSE
        UPDATE discovered_patterns
        SET user_feedback = jsonb_set(
            user_feedback,
            '{not_helpful_count}',
            to_jsonb((COALESCE((user_feedback->>'not_helpful_count')::int, 0) + 1))
        ),
        user_feedback = jsonb_set(
            user_feedback,
            '{last_not_helpful}',
            to_jsonb(NOW()::text)
        )
        WHERE id = p_pattern_id;
    END IF;

    -- Update updated_at timestamp
    UPDATE discovered_patterns
    SET updated_at = NOW()
    WHERE id = p_pattern_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get pattern feedback ratio
CREATE OR REPLACE FUNCTION get_pattern_feedback_ratio(p_pattern_id INTEGER)
RETURNS NUMERIC AS $$
DECLARE
    v_helpful INTEGER;
    v_not_helpful INTEGER;
    v_total INTEGER;
BEGIN
    SELECT
        COALESCE((user_feedback->>'helpful_count')::int, 0),
        COALESCE((user_feedback->>'not_helpful_count')::int, 0)
    INTO v_helpful, v_not_helpful
    FROM discovered_patterns
    WHERE id = p_pattern_id;

    v_total := v_helpful + v_not_helpful;

    IF v_total = 0 THEN
        RETURN NULL;  -- No feedback yet
    END IF;

    RETURN v_helpful::NUMERIC / v_total::NUMERIC;
END;
$$ LANGUAGE plpgsql;

-- Function to adjust pattern confidence based on feedback
CREATE OR REPLACE FUNCTION adjust_pattern_confidence_from_feedback(p_pattern_id INTEGER)
RETURNS VOID AS $$
DECLARE
    v_helpful INTEGER;
    v_not_helpful INTEGER;
    v_total INTEGER;
    v_helpful_ratio NUMERIC;
    v_current_confidence NUMERIC;
    v_new_confidence NUMERIC;
BEGIN
    -- Get feedback counts
    SELECT
        COALESCE((user_feedback->>'helpful_count')::int, 0),
        COALESCE((user_feedback->>'not_helpful_count')::int, 0),
        confidence
    INTO v_helpful, v_not_helpful, v_current_confidence
    FROM discovered_patterns
    WHERE id = p_pattern_id;

    v_total := v_helpful + v_not_helpful;

    -- Require at least 5 feedback entries
    IF v_total < 5 THEN
        RETURN;
    END IF;

    -- Calculate helpful ratio
    v_helpful_ratio := v_helpful::NUMERIC / v_total::NUMERIC;

    -- Adjust confidence based on feedback
    IF v_helpful_ratio < 0.5 THEN
        -- Poor feedback: reduce confidence by 10%
        v_new_confidence := v_current_confidence * 0.90;
    ELSIF v_helpful_ratio > 0.8 THEN
        -- Excellent feedback: increase confidence by 5%
        v_new_confidence := LEAST(v_current_confidence * 1.05, 1.0);
    ELSE
        -- Neutral feedback: no change
        v_new_confidence := v_current_confidence;
    END IF;

    -- Update confidence
    IF v_new_confidence != v_current_confidence THEN
        UPDATE discovered_patterns
        SET confidence = v_new_confidence,
            updated_at = NOW()
        WHERE id = p_pattern_id;

        -- Log confidence adjustment
        RAISE NOTICE 'Adjusted pattern % confidence: % → % (feedback ratio: %)',
            p_pattern_id, v_current_confidence, v_new_confidence, v_helpful_ratio;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to get patterns needing feedback
CREATE OR REPLACE FUNCTION get_patterns_needing_feedback(
    p_user_id TEXT,
    p_limit INTEGER DEFAULT 5
)
RETURNS TABLE (
    pattern_id INTEGER,
    pattern_type TEXT,
    actionable_insight TEXT,
    confidence NUMERIC,
    impact_score NUMERIC,
    occurrences INTEGER,
    feedback_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        id,
        dp.pattern_type::TEXT,
        dp.actionable_insight,
        dp.confidence,
        dp.impact_score,
        dp.occurrences,
        COALESCE((dp.user_feedback->>'helpful_count')::int, 0) +
        COALESCE((dp.user_feedback->>'not_helpful_count')::int, 0) AS feedback_count
    FROM discovered_patterns dp
    WHERE dp.user_id = p_user_id
      AND dp.confidence >= 0.70
      AND dp.impact_score >= 50
      AND (dp.pattern_rule->>'archived' IS NULL OR dp.pattern_rule->>'archived' != 'true')
      -- Prioritize patterns with no/little feedback
      AND (COALESCE((dp.user_feedback->>'helpful_count')::int, 0) +
           COALESCE((dp.user_feedback->>'not_helpful_count')::int, 0)) < 3
    ORDER BY
        dp.impact_score DESC,
        dp.confidence DESC,
        dp.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-adjust confidence when feedback is added
CREATE OR REPLACE FUNCTION trigger_adjust_confidence_on_feedback()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if feedback was added
    IF (NEW.user_feedback->>'helpful_count')::int + (NEW.user_feedback->>'not_helpful_count')::int >= 5
       AND (OLD.user_feedback->>'helpful_count')::int + (OLD.user_feedback->>'not_helpful_count')::int < 5
    THEN
        -- First time reaching 5+ feedback entries
        PERFORM adjust_pattern_confidence_from_feedback(NEW.id);
    ELSIF (NEW.user_feedback->>'helpful_count')::int + (NEW.user_feedback->>'not_helpful_count')::int > 5
          AND ((NEW.user_feedback->>'helpful_count')::int + (NEW.user_feedback->>'not_helpful_count')::int) % 5 = 0
    THEN
        -- Every 5 additional feedback entries
        PERFORM adjust_pattern_confidence_from_feedback(NEW.id);
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_adjust_confidence_on_feedback ON discovered_patterns;
CREATE TRIGGER tr_adjust_confidence_on_feedback
AFTER UPDATE OF user_feedback ON discovered_patterns
FOR EACH ROW
WHEN (NEW.user_feedback IS DISTINCT FROM OLD.user_feedback)
EXECUTE FUNCTION trigger_adjust_confidence_on_feedback();

-- Add comments for documentation
COMMENT ON COLUMN discovered_patterns.user_feedback IS 'JSONB storing user feedback: helpful_count, not_helpful_count, feedback_history[]';
COMMENT ON FUNCTION record_pattern_feedback IS 'Records user feedback (helpful/not helpful) for a pattern';
COMMENT ON FUNCTION get_pattern_feedback_ratio IS 'Returns helpful ratio (0-1) for a pattern';
COMMENT ON FUNCTION adjust_pattern_confidence_from_feedback IS 'Adjusts pattern confidence based on accumulated feedback';
COMMENT ON FUNCTION get_patterns_needing_feedback IS 'Returns high-quality patterns that need user feedback';
