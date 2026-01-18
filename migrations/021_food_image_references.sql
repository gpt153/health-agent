-- Food Image References with CLIP Embeddings (Epic 009 - Phase 1)
-- Visual food memory system using pgvector for similarity search

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- ================================================================
-- Table: food_image_references
-- Purpose: Store CLIP embeddings for food photos to enable visual search
-- ================================================================
CREATE TABLE IF NOT EXISTS food_image_references (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    food_entry_id UUID NOT NULL REFERENCES food_entries(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    photo_path VARCHAR(500) NOT NULL,

    -- CLIP embedding (512-dimensional vector)
    -- Using OpenAI's clip-vit-base-patch32 model
    embedding vector(512) NOT NULL,

    -- Metadata for tracking and debugging
    model_version VARCHAR(100) DEFAULT 'clip-vit-base-patch32',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_food_entry FOREIGN KEY (food_entry_id) REFERENCES food_entries(id) ON DELETE CASCADE,
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(telegram_id) ON DELETE CASCADE
);

-- ================================================================
-- HNSW Index for Fast Similarity Search
-- Using HNSW (Hierarchical Navigable Small World) algorithm
-- Parameters:
--   m=16: Number of connections per layer (default, good balance)
--   ef_construction=64: Size of dynamic candidate list (default, good quality)
-- ================================================================
CREATE INDEX IF NOT EXISTS idx_food_image_embeddings_hnsw
ON food_image_references
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Standard B-tree indexes for lookups
CREATE INDEX IF NOT EXISTS idx_food_image_references_user
ON food_image_references(user_id);

CREATE INDEX IF NOT EXISTS idx_food_image_references_entry
ON food_image_references(food_entry_id);

CREATE INDEX IF NOT EXISTS idx_food_image_references_created
ON food_image_references(created_at DESC);

-- Composite index for user + time range queries
CREATE INDEX IF NOT EXISTS idx_food_image_references_user_created
ON food_image_references(user_id, created_at DESC);

-- ================================================================
-- Table: image_analysis_cache
-- Purpose: Cache image analysis results to avoid reprocessing
-- ================================================================
CREATE TABLE IF NOT EXISTS image_analysis_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    photo_path VARCHAR(500) UNIQUE NOT NULL,

    -- Cached embedding
    embedding vector(512),

    -- Cache metadata
    model_version VARCHAR(100) DEFAULT 'clip-vit-base-patch32',
    analysis_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cache_hits INTEGER DEFAULT 0,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for cache lookups
CREATE INDEX IF NOT EXISTS idx_image_cache_photo_path
ON image_analysis_cache(photo_path);

CREATE INDEX IF NOT EXISTS idx_image_cache_accessed
ON image_analysis_cache(last_accessed DESC);

-- ================================================================
-- Function: find_similar_food_images
-- Purpose: Find visually similar food images using cosine similarity
-- ================================================================
CREATE OR REPLACE FUNCTION find_similar_food_images(
    p_user_id TEXT,
    p_embedding vector(512),
    p_limit INTEGER DEFAULT 5,
    p_distance_threshold FLOAT DEFAULT 0.3
) RETURNS TABLE (
    food_entry_id UUID,
    photo_path VARCHAR(500),
    similarity_score FLOAT,
    created_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        fir.food_entry_id,
        fir.photo_path,
        1 - (fir.embedding <=> p_embedding) AS similarity_score,
        fir.created_at
    FROM food_image_references fir
    WHERE fir.user_id = p_user_id
      AND (1 - (fir.embedding <=> p_embedding)) >= (1 - p_distance_threshold)
    ORDER BY fir.embedding <=> p_embedding
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ================================================================
-- Function: update_cache_hit
-- Purpose: Update cache hit counter and last accessed timestamp
-- ================================================================
CREATE OR REPLACE FUNCTION update_cache_hit(p_photo_path VARCHAR(500))
RETURNS VOID AS $$
BEGIN
    UPDATE image_analysis_cache
    SET cache_hits = cache_hits + 1,
        last_accessed = CURRENT_TIMESTAMP
    WHERE photo_path = p_photo_path;
END;
$$ LANGUAGE plpgsql;

-- ================================================================
-- Comments for documentation
-- ================================================================
COMMENT ON TABLE food_image_references IS
'Stores CLIP embeddings for food photos to enable visual similarity search';

COMMENT ON COLUMN food_image_references.embedding IS
'512-dimensional CLIP embedding from clip-vit-base-patch32 model';

COMMENT ON INDEX idx_food_image_embeddings_hnsw IS
'HNSW index for fast approximate nearest neighbor search using cosine distance';

COMMENT ON TABLE image_analysis_cache IS
'Caches image analysis results to avoid redundant API calls and improve performance';

COMMENT ON FUNCTION find_similar_food_images IS
'Finds visually similar food images for a user using cosine similarity.
Returns matches with similarity score >= (1 - distance_threshold).
Default threshold 0.3 means 70% similarity required.';
