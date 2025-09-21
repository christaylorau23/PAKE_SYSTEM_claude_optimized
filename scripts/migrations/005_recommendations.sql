-- Recommendations Table Migration
-- Represents generated content recommendations with explanation and tracking

CREATE TABLE IF NOT EXISTS recommendations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    content_id UUID NOT NULL,
    relevance_score FLOAT NOT NULL CHECK (relevance_score >= 0.0 AND relevance_score <= 1.0),
    ranking_position INTEGER NOT NULL CHECK (ranking_position > 0),
    algorithm_version VARCHAR(50) NOT NULL DEFAULT 'v1.0',
    explanation_tags TEXT[] DEFAULT '{}',
    detailed_explanation TEXT,
    confidence_score FLOAT CHECK (confidence_score IS NULL OR (confidence_score >= 0.0 AND confidence_score <= 1.0)),
    feature_weights JSONB DEFAULT '{}',
    generated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    is_served BOOLEAN NOT NULL DEFAULT false,
    served_at TIMESTAMP,
    clicked BOOLEAN DEFAULT false,
    clicked_at TIMESTAMP,
    dismissed BOOLEAN DEFAULT false,
    dismissed_at TIMESTAMP,
    recommendation_batch_id UUID, -- For tracking batch generations
    context VARCHAR(50) DEFAULT 'general', -- Context where recommendation was generated
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for performance optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recommendations_user_id ON recommendations USING btree (user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recommendations_content_id ON recommendations USING btree (content_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recommendations_generated_at ON recommendations USING btree (generated_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recommendations_expires_at ON recommendations USING btree (expires_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recommendations_relevance_score ON recommendations USING btree (relevance_score DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recommendations_ranking_position ON recommendations USING btree (ranking_position);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recommendations_is_served ON recommendations USING btree (is_served);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recommendations_algorithm_version ON recommendations USING btree (algorithm_version);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recommendations_batch_id ON recommendations USING btree (recommendation_batch_id);

-- Composite indexes for common queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recommendations_user_active
ON recommendations USING btree (user_id, expires_at DESC) WHERE is_served = false AND expires_at > NOW();

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recommendations_user_served
ON recommendations USING btree (user_id, served_at DESC) WHERE is_served = true;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recommendations_ranking
ON recommendations USING btree (user_id, ranking_position) WHERE is_served = false AND expires_at > NOW();

-- Constraints
ALTER TABLE recommendations ADD CONSTRAINT chk_recommendations_expires_after_generated
    CHECK (expires_at > generated_at);

ALTER TABLE recommendations ADD CONSTRAINT chk_recommendations_served_logic
    CHECK (
        (is_served = false AND served_at IS NULL) OR
        (is_served = true AND served_at IS NOT NULL AND served_at >= generated_at)
    );

ALTER TABLE recommendations ADD CONSTRAINT chk_recommendations_clicked_logic
    CHECK (
        (clicked = false AND clicked_at IS NULL) OR
        (clicked = true AND clicked_at IS NOT NULL AND is_served = true)
    );

ALTER TABLE recommendations ADD CONSTRAINT chk_recommendations_dismissed_logic
    CHECK (
        (dismissed = false AND dismissed_at IS NULL) OR
        (dismissed = true AND dismissed_at IS NOT NULL)
    );

-- Foreign key constraints
ALTER TABLE recommendations ADD CONSTRAINT fk_recommendations_user_id
    FOREIGN KEY (user_id) REFERENCES user_profiles(id) ON DELETE CASCADE;

ALTER TABLE recommendations ADD CONSTRAINT fk_recommendations_content_id
    FOREIGN KEY (content_id) REFERENCES content_items(id) ON DELETE CASCADE;

-- Unique constraint to prevent duplicate recommendations in same batch
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_recommendations_unique_user_content_batch
ON recommendations (user_id, content_id, recommendation_batch_id)
WHERE recommendation_batch_id IS NOT NULL;

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_recommendations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_recommendations_updated_at ON recommendations;
CREATE TRIGGER trg_recommendations_updated_at
    BEFORE UPDATE ON recommendations
    FOR EACH ROW
    EXECUTE FUNCTION update_recommendations_updated_at();

-- Function to mark recommendation as served
CREATE OR REPLACE FUNCTION mark_recommendation_served(p_recommendation_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE recommendations
    SET
        is_served = true,
        served_at = NOW()
    WHERE
        id = p_recommendation_id
        AND is_served = false
        AND expires_at > NOW();

    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count > 0;
END;
$$ LANGUAGE plpgsql;

-- Function to record recommendation interaction
CREATE OR REPLACE FUNCTION record_recommendation_interaction(
    p_recommendation_id UUID,
    p_action VARCHAR(20), -- 'click', 'dismiss'
    p_timestamp TIMESTAMP DEFAULT NOW()
)
RETURNS BOOLEAN AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    IF p_action = 'click' THEN
        UPDATE recommendations
        SET
            clicked = true,
            clicked_at = p_timestamp
        WHERE
            id = p_recommendation_id
            AND is_served = true
            AND clicked = false;
    ELSIF p_action = 'dismiss' THEN
        UPDATE recommendations
        SET
            dismissed = true,
            dismissed_at = p_timestamp
        WHERE
            id = p_recommendation_id
            AND dismissed = false;
    END IF;

    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count > 0;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up expired recommendations
CREATE OR REPLACE FUNCTION cleanup_expired_recommendations(p_batch_size INTEGER DEFAULT 1000)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM recommendations
    WHERE
        id IN (
            SELECT id
            FROM recommendations
            WHERE expires_at < NOW() - INTERVAL '7 days'
            AND is_served = false
            ORDER BY expires_at
            LIMIT p_batch_size
        );

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get recommendation performance metrics
CREATE OR REPLACE FUNCTION get_recommendation_performance(
    p_user_id UUID DEFAULT NULL,
    p_algorithm_version VARCHAR(50) DEFAULT NULL,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    total_recommendations BIGINT,
    served_recommendations BIGINT,
    clicked_recommendations BIGINT,
    dismissed_recommendations BIGINT,
    click_through_rate NUMERIC,
    dismissal_rate NUMERIC,
    avg_relevance_score NUMERIC,
    avg_confidence_score NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*) as total_recommendations,
        COUNT(*) FILTER (WHERE r.is_served = true) as served_recommendations,
        COUNT(*) FILTER (WHERE r.clicked = true) as clicked_recommendations,
        COUNT(*) FILTER (WHERE r.dismissed = true) as dismissed_recommendations,
        ROUND(
            COUNT(*) FILTER (WHERE r.clicked = true)::NUMERIC /
            NULLIF(COUNT(*) FILTER (WHERE r.is_served = true), 0) * 100, 2
        ) as click_through_rate,
        ROUND(
            COUNT(*) FILTER (WHERE r.dismissed = true)::NUMERIC /
            NULLIF(COUNT(*) FILTER (WHERE r.is_served = true), 0) * 100, 2
        ) as dismissal_rate,
        ROUND(AVG(r.relevance_score), 3) as avg_relevance_score,
        ROUND(AVG(r.confidence_score), 3) as avg_confidence_score
    FROM recommendations r
    WHERE
        r.generated_at >= NOW() - INTERVAL '1 day' * p_days
        AND (p_user_id IS NULL OR r.user_id = p_user_id)
        AND (p_algorithm_version IS NULL OR r.algorithm_version = p_algorithm_version);
END;
$$ LANGUAGE plpgsql;

-- View for active recommendations
CREATE OR REPLACE VIEW active_recommendations AS
SELECT
    r.id,
    r.user_id,
    up.user_id as external_user_id,
    r.content_id,
    ci.title as content_title,
    ci.url as content_url,
    r.relevance_score,
    r.ranking_position,
    r.explanation_tags,
    r.detailed_explanation,
    r.generated_at,
    r.expires_at
FROM recommendations r
JOIN user_profiles up ON r.user_id = up.id
JOIN content_items ci ON r.content_id = ci.id
WHERE
    r.is_served = false
    AND r.expires_at > NOW()
ORDER BY r.user_id, r.ranking_position;

-- Sample data for testing (optional)
-- INSERT INTO recommendations (user_id, content_id, relevance_score, ranking_position, expires_at, explanation_tags)
-- SELECT
--     up.id as user_id,
--     ci.id as content_id,
--     0.85 as relevance_score,
--     1 as ranking_position,
--     NOW() + INTERVAL '24 hours' as expires_at,
--     ARRAY['interests match', 'high quality'] as explanation_tags
-- FROM user_profiles up, content_items ci
-- WHERE up.user_id = 'user123' AND ci.title LIKE '%Machine Learning%'
-- LIMIT 1;

COMMENT ON TABLE recommendations IS 'Generated content recommendations with explanation and tracking';
COMMENT ON COLUMN recommendations.relevance_score IS 'Predicted user interest score (0.0-1.0)';
COMMENT ON COLUMN recommendations.explanation_tags IS 'Quick explanation labels for recommendation reasoning';
COMMENT ON COLUMN recommendations.feature_weights IS 'JSON object with contribution of different recommendation factors';
COMMENT ON COLUMN recommendations.recommendation_batch_id IS 'UUID to group recommendations generated together';
COMMENT ON FUNCTION mark_recommendation_served IS 'Marks recommendation as served to user with timestamp';
COMMENT ON FUNCTION record_recommendation_interaction IS 'Records user interaction (click/dismiss) with recommendation';
COMMENT ON FUNCTION get_recommendation_performance IS 'Returns comprehensive recommendation performance metrics';