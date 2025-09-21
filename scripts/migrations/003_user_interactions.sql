-- User Interactions Table Migration
-- Tracks all user interactions with content for learning and analytics

CREATE TABLE IF NOT EXISTS user_interactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    content_id UUID NOT NULL,
    interaction_type VARCHAR(20) NOT NULL CHECK (interaction_type IN ('view', 'save', 'share', 'click', 'scroll', 'dwell')),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    duration INTEGER CHECK (duration IS NULL OR duration > 0), -- seconds spent (for dwell interactions)
    context VARCHAR(50), -- where interaction happened (e.g., "feed", "search", "recommendation")
    device_type VARCHAR(50),
    session_id VARCHAR(100),
    interaction_value FLOAT NOT NULL DEFAULT 1.0 CHECK (interaction_value >= 0.0 AND interaction_value <= 10.0),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for performance optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_interactions_user_id ON user_interactions USING btree (user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_interactions_content_id ON user_interactions USING btree (content_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_interactions_timestamp ON user_interactions USING btree (timestamp DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_interactions_interaction_type ON user_interactions USING btree (interaction_type);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_interactions_session_id ON user_interactions USING btree (session_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_interactions_context ON user_interactions USING btree (context);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_interactions_user_timestamp ON user_interactions USING btree (user_id, timestamp DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_interactions_content_timestamp ON user_interactions USING btree (content_id, timestamp DESC);

-- Composite index for analytics queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_interactions_analytics
ON user_interactions USING btree (user_id, interaction_type, timestamp DESC);

-- Constraints
ALTER TABLE user_interactions ADD CONSTRAINT chk_user_interactions_timestamp_not_future
    CHECK (timestamp <= NOW());

ALTER TABLE user_interactions ADD CONSTRAINT chk_user_interactions_duration_for_dwell
    CHECK (
        (interaction_type = 'dwell' AND duration IS NOT NULL AND duration > 0) OR
        (interaction_type != 'dwell')
    );

-- Foreign key constraints (assuming user_profiles and content_items tables exist)
ALTER TABLE user_interactions ADD CONSTRAINT fk_user_interactions_user_id
    FOREIGN KEY (user_id) REFERENCES user_profiles(id) ON DELETE CASCADE;

ALTER TABLE user_interactions ADD CONSTRAINT fk_user_interactions_content_id
    FOREIGN KEY (content_id) REFERENCES content_items(id) ON DELETE CASCADE;

-- Trigger to update user profile interaction count
CREATE OR REPLACE FUNCTION update_user_interaction_count()
RETURNS TRIGGER AS $$
BEGIN
    -- Increment interaction count for the user
    UPDATE user_profiles
    SET interaction_count = interaction_count + 1,
        last_updated = NOW()
    WHERE id = NEW.user_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_user_interactions_update_count ON user_interactions;
CREATE TRIGGER trg_user_interactions_update_count
    AFTER INSERT ON user_interactions
    FOR EACH ROW
    EXECUTE FUNCTION update_user_interaction_count();

-- Function to get user interaction summary
CREATE OR REPLACE FUNCTION get_user_interaction_summary(p_user_id UUID, p_days INTEGER DEFAULT 30)
RETURNS TABLE (
    interaction_type VARCHAR(20),
    count BIGINT,
    avg_value NUMERIC,
    total_duration BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ui.interaction_type,
        COUNT(*) as count,
        ROUND(AVG(ui.interaction_value), 2) as avg_value,
        COALESCE(SUM(ui.duration), 0) as total_duration
    FROM user_interactions ui
    WHERE ui.user_id = p_user_id
    AND ui.timestamp >= NOW() - INTERVAL '1 day' * p_days
    GROUP BY ui.interaction_type
    ORDER BY count DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to get content engagement metrics
CREATE OR REPLACE FUNCTION get_content_engagement_metrics(p_content_id UUID)
RETURNS TABLE (
    total_interactions BIGINT,
    unique_users BIGINT,
    avg_interaction_value NUMERIC,
    total_dwell_time BIGINT,
    click_through_rate NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*) as total_interactions,
        COUNT(DISTINCT ui.user_id) as unique_users,
        ROUND(AVG(ui.interaction_value), 2) as avg_interaction_value,
        COALESCE(SUM(ui.duration), 0) as total_dwell_time,
        ROUND(
            COUNT(*) FILTER (WHERE ui.interaction_type = 'click')::NUMERIC /
            NULLIF(COUNT(*) FILTER (WHERE ui.interaction_type = 'view'), 0) * 100, 2
        ) as click_through_rate
    FROM user_interactions ui
    WHERE ui.content_id = p_content_id;
END;
$$ LANGUAGE plpgsql;

-- View for recent user activity
CREATE OR REPLACE VIEW recent_user_activity AS
SELECT
    ui.user_id,
    up.user_id as external_user_id,
    ui.content_id,
    ci.title as content_title,
    ci.url as content_url,
    ui.interaction_type,
    ui.timestamp,
    ui.context,
    ui.interaction_value
FROM user_interactions ui
JOIN user_profiles up ON ui.user_id = up.id
JOIN content_items ci ON ui.content_id = ci.id
WHERE ui.timestamp >= NOW() - INTERVAL '24 hours'
ORDER BY ui.timestamp DESC;

-- Sample data for testing (optional)
-- INSERT INTO user_interactions (user_id, content_id, interaction_type, context, interaction_value)
-- SELECT
--     up.id as user_id,
--     ci.id as content_id,
--     'view' as interaction_type,
--     'feed' as context,
--     2.0 as interaction_value
-- FROM user_profiles up, content_items ci
-- WHERE up.user_id = 'user123' AND ci.title LIKE '%Machine Learning%'
-- LIMIT 1;

COMMENT ON TABLE user_interactions IS 'Tracks all user interactions with content for learning and analytics';
COMMENT ON COLUMN user_interactions.duration IS 'Time spent in seconds (for dwell interactions only)';
COMMENT ON COLUMN user_interactions.interaction_value IS 'Weighted importance of interaction (0.0-10.0)';
COMMENT ON COLUMN user_interactions.context IS 'Where interaction occurred (feed, search, recommendation, etc.)';
COMMENT ON FUNCTION get_user_interaction_summary IS 'Returns interaction summary for a user within specified days';
COMMENT ON FUNCTION get_content_engagement_metrics IS 'Returns comprehensive engagement metrics for content item';