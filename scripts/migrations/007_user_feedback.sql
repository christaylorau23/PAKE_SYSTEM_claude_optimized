-- User Feedback Table Migration
-- Explicit user feedback on recommendations and content

CREATE TABLE IF NOT EXISTS user_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    content_id UUID NOT NULL,
    recommendation_id UUID, -- Optional: if feedback is on a specific recommendation
    feedback_type VARCHAR(20) NOT NULL CHECK (feedback_type IN ('rating', 'relevance', 'quality', 'not_interested')),
    feedback_value FLOAT NOT NULL CHECK (feedback_value >= 0.0 AND feedback_value <= 5.0),
    feedback_reason TEXT,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    is_implicit BOOLEAN NOT NULL DEFAULT false, -- true if derived from behavior, false if explicit
    session_id VARCHAR(100),
    context VARCHAR(50), -- Where feedback was given (feed, search, recommendation)
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for performance optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_feedback_user_id ON user_feedback USING btree (user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_feedback_content_id ON user_feedback USING btree (content_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_feedback_recommendation_id ON user_feedback USING btree (recommendation_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_feedback_timestamp ON user_feedback USING btree (timestamp DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_feedback_feedback_type ON user_feedback USING btree (feedback_type);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_feedback_feedback_value ON user_feedback USING btree (feedback_value DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_feedback_is_implicit ON user_feedback USING btree (is_implicit);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_feedback_context ON user_feedback USING btree (context);

-- Composite indexes for analytics
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_feedback_analytics
ON user_feedback USING btree (user_id, feedback_type, timestamp DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_feedback_content_analytics
ON user_feedback USING btree (content_id, feedback_type, feedback_value DESC);

-- Constraints
ALTER TABLE user_feedback ADD CONSTRAINT chk_user_feedback_timestamp_not_future
    CHECK (timestamp <= NOW());

-- Feedback value ranges based on type
ALTER TABLE user_feedback ADD CONSTRAINT chk_user_feedback_value_range
    CHECK (
        (feedback_type = 'rating' AND feedback_value >= 1.0 AND feedback_value <= 5.0) OR
        (feedback_type = 'relevance' AND feedback_value >= 0.0 AND feedback_value <= 1.0) OR
        (feedback_type = 'quality' AND feedback_value >= 0.0 AND feedback_value <= 1.0) OR
        (feedback_type = 'not_interested' AND feedback_value = 0.0)
    );

-- Prevent duplicate explicit feedback for same content by same user
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_user_feedback_unique_explicit
ON user_feedback (user_id, content_id, feedback_type)
WHERE is_implicit = false;

-- Foreign key constraints
ALTER TABLE user_feedback ADD CONSTRAINT fk_user_feedback_user_id
    FOREIGN KEY (user_id) REFERENCES user_profiles(id) ON DELETE CASCADE;

ALTER TABLE user_feedback ADD CONSTRAINT fk_user_feedback_content_id
    FOREIGN KEY (content_id) REFERENCES content_items(id) ON DELETE CASCADE;

ALTER TABLE user_feedback ADD CONSTRAINT fk_user_feedback_recommendation_id
    FOREIGN KEY (recommendation_id) REFERENCES recommendations(id) ON DELETE SET NULL;

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_user_feedback_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_user_feedback_updated_at ON user_feedback;
CREATE TRIGGER trg_user_feedback_updated_at
    BEFORE UPDATE ON user_feedback
    FOR EACH ROW
    EXECUTE FUNCTION update_user_feedback_updated_at();

-- Function to record explicit feedback
CREATE OR REPLACE FUNCTION record_explicit_feedback(
    p_user_id UUID,
    p_content_id UUID,
    p_feedback_type VARCHAR(20),
    p_feedback_value FLOAT,
    p_feedback_reason TEXT DEFAULT NULL,
    p_recommendation_id UUID DEFAULT NULL,
    p_context VARCHAR(50) DEFAULT 'general'
)
RETURNS UUID AS $$
DECLARE
    feedback_id UUID;
BEGIN
    INSERT INTO user_feedback (
        user_id, content_id, recommendation_id, feedback_type,
        feedback_value, feedback_reason, is_implicit, context
    )
    VALUES (
        p_user_id, p_content_id, p_recommendation_id, p_feedback_type,
        p_feedback_value, p_feedback_reason, false, p_context
    )
    ON CONFLICT (user_id, content_id, feedback_type)
    WHERE is_implicit = false
    DO UPDATE SET
        feedback_value = EXCLUDED.feedback_value,
        feedback_reason = EXCLUDED.feedback_reason,
        timestamp = NOW(),
        updated_at = NOW()
    RETURNING id INTO feedback_id;

    RETURN feedback_id;
END;
$$ LANGUAGE plpgsql;

-- Function to record implicit feedback from user behavior
CREATE OR REPLACE FUNCTION record_implicit_feedback(
    p_user_id UUID,
    p_content_id UUID,
    p_interaction_type VARCHAR(20),
    p_interaction_value FLOAT,
    p_context VARCHAR(50) DEFAULT 'behavior'
)
RETURNS UUID AS $$
DECLARE
    feedback_id UUID;
    derived_feedback_type VARCHAR(20);
    derived_feedback_value FLOAT;
BEGIN
    -- Map interaction types to feedback types and values
    CASE p_interaction_type
        WHEN 'save' THEN
            derived_feedback_type := 'rating';
            derived_feedback_value := 4.0;
        WHEN 'share' THEN
            derived_feedback_type := 'rating';
            derived_feedback_value := 4.5;
        WHEN 'dwell' THEN
            derived_feedback_type := 'relevance';
            derived_feedback_value := LEAST(p_interaction_value / 100.0, 1.0); -- Normalize dwell time
        WHEN 'click' THEN
            derived_feedback_type := 'relevance';
            derived_feedback_value := 0.7;
        ELSE
            derived_feedback_type := 'relevance';
            derived_feedback_value := LEAST(p_interaction_value / 5.0, 1.0);
    END CASE;

    INSERT INTO user_feedback (
        user_id, content_id, feedback_type, feedback_value,
        is_implicit, context, metadata
    )
    VALUES (
        p_user_id, p_content_id, derived_feedback_type, derived_feedback_value,
        true, p_context, jsonb_build_object('interaction_type', p_interaction_type)
    )
    RETURNING id INTO feedback_id;

    RETURN feedback_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get user feedback summary
CREATE OR REPLACE FUNCTION get_user_feedback_summary(p_user_id UUID, p_days INTEGER DEFAULT 30)
RETURNS TABLE (
    feedback_type VARCHAR(20),
    explicit_count BIGINT,
    implicit_count BIGINT,
    avg_explicit_value NUMERIC,
    avg_implicit_value NUMERIC,
    latest_feedback TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        uf.feedback_type,
        COUNT(*) FILTER (WHERE uf.is_implicit = false) as explicit_count,
        COUNT(*) FILTER (WHERE uf.is_implicit = true) as implicit_count,
        ROUND(AVG(uf.feedback_value) FILTER (WHERE uf.is_implicit = false), 2) as avg_explicit_value,
        ROUND(AVG(uf.feedback_value) FILTER (WHERE uf.is_implicit = true), 2) as avg_implicit_value,
        MAX(uf.timestamp) as latest_feedback
    FROM user_feedback uf
    WHERE uf.user_id = p_user_id
    AND uf.timestamp >= NOW() - INTERVAL '1 day' * p_days
    GROUP BY uf.feedback_type
    ORDER BY explicit_count DESC, implicit_count DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to get content feedback analysis
CREATE OR REPLACE FUNCTION get_content_feedback_analysis(p_content_id UUID)
RETURNS TABLE (
    total_feedback BIGINT,
    avg_rating NUMERIC,
    avg_relevance NUMERIC,
    avg_quality NUMERIC,
    not_interested_count BIGINT,
    feedback_distribution JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*) as total_feedback,
        ROUND(AVG(uf.feedback_value) FILTER (WHERE uf.feedback_type = 'rating'), 2) as avg_rating,
        ROUND(AVG(uf.feedback_value) FILTER (WHERE uf.feedback_type = 'relevance'), 2) as avg_relevance,
        ROUND(AVG(uf.feedback_value) FILTER (WHERE uf.feedback_type = 'quality'), 2) as avg_quality,
        COUNT(*) FILTER (WHERE uf.feedback_type = 'not_interested') as not_interested_count,
        jsonb_build_object(
            'rating_distribution', jsonb_object_agg(
                CASE WHEN uf.feedback_type = 'rating' THEN
                    CASE
                        WHEN uf.feedback_value >= 4.0 THEN 'positive'
                        WHEN uf.feedback_value >= 3.0 THEN 'neutral'
                        ELSE 'negative'
                    END
                END,
                COUNT(*) FILTER (WHERE uf.feedback_type = 'rating')
            ),
            'explicit_vs_implicit', jsonb_object_agg(
                CASE WHEN uf.is_implicit THEN 'implicit' ELSE 'explicit' END,
                COUNT(*)
            )
        ) as feedback_distribution
    FROM user_feedback uf
    WHERE uf.content_id = p_content_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get recommendation feedback effectiveness
CREATE OR REPLACE FUNCTION get_recommendation_feedback_effectiveness(p_recommendation_id UUID)
RETURNS TABLE (
    recommendation_relevance FLOAT,
    user_feedback_count BIGINT,
    avg_user_rating NUMERIC,
    feedback_alignment NUMERIC -- How well recommendation score aligns with user feedback
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        r.relevance_score as recommendation_relevance,
        COUNT(uf.id) as user_feedback_count,
        ROUND(AVG(uf.feedback_value), 2) as avg_user_rating,
        ROUND(
            1.0 - ABS(r.relevance_score - AVG(uf.feedback_value) / 5.0), 2
        ) as feedback_alignment
    FROM recommendations r
    LEFT JOIN user_feedback uf ON r.id = uf.recommendation_id
    WHERE r.id = p_recommendation_id
    AND (uf.feedback_type IS NULL OR uf.feedback_type = 'rating')
    GROUP BY r.id, r.relevance_score;
END;
$$ LANGUAGE plpgsql;

-- View for recent feedback activity
CREATE OR REPLACE VIEW recent_feedback_activity AS
SELECT
    uf.id,
    uf.user_id,
    up.user_id as external_user_id,
    uf.content_id,
    ci.title as content_title,
    uf.feedback_type,
    uf.feedback_value,
    uf.feedback_reason,
    uf.is_implicit,
    uf.timestamp,
    uf.context
FROM user_feedback uf
JOIN user_profiles up ON uf.user_id = up.id
JOIN content_items ci ON uf.content_id = ci.id
WHERE uf.timestamp >= NOW() - INTERVAL '24 hours'
ORDER BY uf.timestamp DESC;

-- Trigger to update content engagement metrics when feedback is added
CREATE OR REPLACE FUNCTION update_content_engagement_on_feedback()
RETURNS TRIGGER AS $$
BEGIN
    -- Update content_items engagement_metrics with latest feedback
    UPDATE content_items
    SET engagement_metrics = engagement_metrics || jsonb_build_object(
        'avg_rating', (
            SELECT ROUND(AVG(feedback_value), 2)
            FROM user_feedback
            WHERE content_id = NEW.content_id
            AND feedback_type = 'rating'
        ),
        'feedback_count', (
            SELECT COUNT(*)
            FROM user_feedback
            WHERE content_id = NEW.content_id
        ),
        'last_feedback', NOW()
    )
    WHERE id = NEW.content_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_user_feedback_update_engagement ON user_feedback;
CREATE TRIGGER trg_user_feedback_update_engagement
    AFTER INSERT ON user_feedback
    FOR EACH ROW
    EXECUTE FUNCTION update_content_engagement_on_feedback();

-- Sample data for testing (optional)
-- INSERT INTO user_feedback (user_id, content_id, feedback_type, feedback_value, feedback_reason, is_implicit, context)
-- SELECT
--     up.id as user_id,
--     ci.id as content_id,
--     'rating' as feedback_type,
--     4.5 as feedback_value,
--     'Very informative and well-written' as feedback_reason,
--     false as is_implicit,
--     'recommendation' as context
-- FROM user_profiles up, content_items ci
-- WHERE up.user_id = 'user123' AND ci.title LIKE '%Machine Learning%'
-- LIMIT 1;

COMMENT ON TABLE user_feedback IS 'Explicit and implicit user feedback on content and recommendations';
COMMENT ON COLUMN user_feedback.feedback_value IS 'Numeric feedback: 1-5 for ratings, 0-1 for relevance/quality, 0 for not_interested';
COMMENT ON COLUMN user_feedback.is_implicit IS 'true if derived from behavior, false if explicitly given by user';
COMMENT ON FUNCTION record_explicit_feedback IS 'Records user-provided feedback with conflict resolution';
COMMENT ON FUNCTION record_implicit_feedback IS 'Derives feedback from user behavior patterns';
COMMENT ON FUNCTION get_user_feedback_summary IS 'Returns comprehensive feedback statistics for a user';
COMMENT ON FUNCTION get_content_feedback_analysis IS 'Analyzes all feedback for a specific content item';