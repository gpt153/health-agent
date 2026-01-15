-- User Habits: Automatic pattern learning system
-- This enables the agent to learn and apply user habits automatically
-- Example: "3dl whey100" → learns 1:1 milk ratio after 3+ repetitions

CREATE TABLE IF NOT EXISTS user_habits (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    habit_type VARCHAR(50) NOT NULL,  -- 'food_prep', 'timing', 'routine', 'preference'
    habit_key VARCHAR(255) NOT NULL,   -- e.g., 'whey100_preparation', 'workout_timing'
    habit_data JSONB NOT NULL,         -- Structured habit details
    confidence FLOAT NOT NULL DEFAULT 0.5,  -- 0.0-1.0 based on repetitions
    occurrence_count INT NOT NULL DEFAULT 1,  -- Number of times pattern observed
    first_observed TIMESTAMP NOT NULL DEFAULT NOW(),
    last_observed TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, habit_type, habit_key)
);

-- Indexes for efficient querying
CREATE INDEX idx_user_habits_user ON user_habits(user_id);
CREATE INDEX idx_user_habits_user_type ON user_habits(user_id, habit_type);
CREATE INDEX idx_user_habits_confidence ON user_habits(user_id, confidence DESC);
CREATE INDEX idx_user_habits_last_observed ON user_habits(user_id, last_observed DESC);

-- Comments for documentation
COMMENT ON TABLE user_habits IS 'Learned user habits and patterns for personalization';
COMMENT ON COLUMN user_habits.habit_type IS 'Category: food_prep, timing, routine, preference';
COMMENT ON COLUMN user_habits.habit_key IS 'Unique identifier for the habit within its type';
COMMENT ON COLUMN user_habits.habit_data IS 'JSON structure with habit details (varies by type)';
COMMENT ON COLUMN user_habits.confidence IS 'Confidence score 0-1, increases with repetitions';
COMMENT ON COLUMN user_habits.occurrence_count IS 'Number of times this pattern was observed';

-- Example habit_data structures:
-- food_prep: {"food": "whey100", "ratio": "1:1", "liquid": "milk_3_percent", "portions_per_dl": 0.5}
-- timing: {"activity": "workout", "usual_time": "08:00", "days": ["Monday", "Wednesday", "Friday"]}
-- routine: {"sequence": ["breakfast", "workout", "protein"], "typical_duration": 120}
-- preference: {"communication_style": "brief", "emoji_usage": "minimal"}
