-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Food entries table
CREATE TABLE IF NOT EXISTS food_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    photo_path VARCHAR(500),
    foods JSONB NOT NULL,              -- [{name, quantity, calories, macros}]
    total_calories INTEGER,
    total_macros JSONB,                -- {protein, carbs, fat}
    meal_type VARCHAR(50),             -- breakfast/lunch/dinner/snack
    notes TEXT
);

-- Reminders table
CREATE TABLE IF NOT EXISTS reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    reminder_type VARCHAR(50) NOT NULL,  -- "simple", "tracking_prompt"
    message TEXT NOT NULL,
    schedule JSONB NOT NULL,             -- {type: "daily", time: "21:00", days: [0,1,2,3,4,5,6]}
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tracking categories table
CREATE TABLE IF NOT EXISTS tracking_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    fields JSONB NOT NULL,               -- Field definitions with types
    schedule JSONB,                      -- When to prompt for data
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, name)
);

-- Tracking entries table
CREATE TABLE IF NOT EXISTS tracking_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES tracking_categories(id) ON DELETE CASCADE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data JSONB NOT NULL,                 -- Actual tracked data
    notes TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_food_entries_user_timestamp ON food_entries(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_food_entries_foods ON food_entries USING GIN(foods);
CREATE INDEX IF NOT EXISTS idx_tracking_entries_user_timestamp ON tracking_entries(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_tracking_entries_data ON tracking_entries USING GIN(data);
CREATE INDEX IF NOT EXISTS idx_reminders_user_active ON reminders(user_id, active);

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
