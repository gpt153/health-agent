-- Conversation history table for persistent multi-turn conversations
CREATE TABLE IF NOT EXISTS conversation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,           -- 'user' or 'assistant'
    content TEXT NOT NULL,
    message_type VARCHAR(50),            -- 'text', 'photo', 'reminder', 'voice', etc.
    metadata JSONB,                      -- Additional context (photo_path, food analysis, etc.)
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast retrieval of recent messages
CREATE INDEX IF NOT EXISTS idx_conversation_user_timestamp 
    ON conversation_history(user_id, timestamp DESC);

-- Index for querying by message type
CREATE INDEX IF NOT EXISTS idx_conversation_message_type 
    ON conversation_history(user_id, message_type);
