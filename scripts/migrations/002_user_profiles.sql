-- User Profiles Table Migration
-- Represents user preferences, behavior patterns, and personalization settings

CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(100) NOT NULL UNIQUE, -- External user identifier from auth system
    interests TEXT[] NOT NULL DEFAULT '{}',
    preference_vector VECTOR(384), -- Learned user preferences embedding
    interaction_count INTEGER NOT NULL DEFAULT 0,
    created_date TIMESTAMP NOT NULL DEFAULT NOW(),
    last_updated TIMESTAMP NOT NULL DEFAULT NOW(),
    learning_rate FLOAT NOT NULL DEFAULT 0.1 CHECK (learning_rate >= 0.0 AND learning_rate <= 1.0),
    diversity_preference FLOAT NOT NULL DEFAULT 0.5 CHECK (diversity_preference >= 0.0 AND diversity_preference <= 1.0),
    quality_threshold FLOAT NOT NULL DEFAULT 0.7 CHECK (quality_threshold >= 0.0 AND quality_threshold <= 1.0),
    source_preferences JSONB DEFAULT '{"preferred_sources": [], "avoided_sources": []}',
    temporal_preferences JSONB DEFAULT '{"recency_weight": 0.3, "authority_weight": 0.4}',
    feedback_history JSONB DEFAULT '{}',
    notification_settings JSONB DEFAULT '{"email_enabled": true, "frequency": "daily"}',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for performance optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_profiles_user_id ON user_profiles USING btree (user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_profiles_created_date ON user_profiles USING btree (created_date);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_profiles_last_updated ON user_profiles USING btree (last_updated);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_profiles_interaction_count ON user_profiles USING btree (interaction_count DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_profiles_quality_threshold ON user_profiles USING btree (quality_threshold);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_profiles_interests ON user_profiles USING gin (interests);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_profiles_is_active ON user_profiles USING btree (is_active);

-- Vector similarity index for user preferences (requires pgvector extension)
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_profiles_preference_vector_ivfflat ON user_profiles
-- USING ivfflat (preference_vector vector_cosine_ops) WITH (lists = 50);

-- Constraints
ALTER TABLE user_profiles ADD CONSTRAINT chk_user_profiles_interests_not_empty
    CHECK (array_length(interests, 1) > 0 OR interests = '{}');

ALTER TABLE user_profiles ADD CONSTRAINT chk_user_profiles_interaction_count_positive
    CHECK (interaction_count >= 0);

-- JSON schema validation for source_preferences
ALTER TABLE user_profiles ADD CONSTRAINT chk_user_profiles_source_preferences_schema
    CHECK (
        jsonb_typeof(source_preferences->'preferred_sources') = 'array' AND
        jsonb_typeof(source_preferences->'avoided_sources') = 'array'
    );

-- JSON schema validation for temporal_preferences
ALTER TABLE user_profiles ADD CONSTRAINT chk_user_profiles_temporal_preferences_schema
    CHECK (
        (source_preferences->'recency_weight')::float >= 0.0 AND
        (source_preferences->'recency_weight')::float <= 1.0 AND
        (source_preferences->'authority_weight')::float >= 0.0 AND
        (source_preferences->'authority_weight')::float <= 1.0
    );

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_user_profiles_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    NEW.last_updated = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_user_profiles_updated_at ON user_profiles;
CREATE TRIGGER trg_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_user_profiles_updated_at();

-- Function to increment interaction count
CREATE OR REPLACE FUNCTION increment_user_interaction_count(p_user_id VARCHAR(100))
RETURNS VOID AS $$
BEGIN
    UPDATE user_profiles
    SET interaction_count = interaction_count + 1,
        last_updated = NOW()
    WHERE user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- Sample data for testing (optional)
-- INSERT INTO user_profiles (user_id, interests, quality_threshold, diversity_preference)
-- VALUES
-- ('user123', ARRAY['machine learning', 'healthcare', 'artificial intelligence'], 0.8, 0.3),
-- ('user456', ARRAY['climate change', 'renewable energy', 'sustainability'], 0.6, 0.5);

COMMENT ON TABLE user_profiles IS 'Stores user preferences, behavior patterns, and personalization settings';
COMMENT ON COLUMN user_profiles.preference_vector IS 'Learned user preferences embedding (384-dimensional)';
COMMENT ON COLUMN user_profiles.learning_rate IS 'Adaptation speed for new preferences (0.0-1.0)';
COMMENT ON COLUMN user_profiles.diversity_preference IS 'Balance between exploration and exploitation (0.0-1.0)';
COMMENT ON COLUMN user_profiles.source_preferences IS 'JSON object with preferred and avoided content sources';
COMMENT ON COLUMN user_profiles.temporal_preferences IS 'JSON object with recency vs authority weighting';
COMMENT ON COLUMN user_profiles.feedback_history IS 'Aggregated feedback patterns and statistics';