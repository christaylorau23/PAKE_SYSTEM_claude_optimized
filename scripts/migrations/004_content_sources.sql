-- Content Sources Table Migration
-- Represents external data sources with reliability and performance metrics

CREATE TABLE IF NOT EXISTS content_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    base_url TEXT NOT NULL,
    source_type VARCHAR(20) NOT NULL CHECK (source_type IN ('academic', 'news', 'social', 'blog', 'institutional')),
    reliability_score FLOAT NOT NULL DEFAULT 0.5 CHECK (reliability_score >= 0.0 AND reliability_score <= 1.0),
    update_frequency VARCHAR(50) DEFAULT 'daily', -- e.g., 'hourly', 'daily', 'weekly'
    avg_quality_score FLOAT CHECK (avg_quality_score IS NULL OR (avg_quality_score >= 0.0 AND avg_quality_score <= 1.0)),
    is_active BOOLEAN NOT NULL DEFAULT true,
    api_config JSONB DEFAULT '{}',
    rate_limits JSONB DEFAULT '{"requests_per_hour": 1000, "requests_per_day": 10000}',
    last_crawled TIMESTAMP,
    content_count INTEGER NOT NULL DEFAULT 0 CHECK (content_count >= 0),
    total_crawl_attempts INTEGER NOT NULL DEFAULT 0,
    successful_crawl_attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    last_error_timestamp TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for performance optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_sources_name ON content_sources USING btree (name);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_sources_source_type ON content_sources USING btree (source_type);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_sources_reliability_score ON content_sources USING btree (reliability_score DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_sources_is_active ON content_sources USING btree (is_active);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_sources_last_crawled ON content_sources USING btree (last_crawled DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_sources_content_count ON content_sources USING btree (content_count DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_sources_avg_quality ON content_sources USING btree (avg_quality_score DESC);

-- Constraints
ALTER TABLE content_sources ADD CONSTRAINT chk_content_sources_successful_attempts
    CHECK (successful_crawl_attempts <= total_crawl_attempts);

ALTER TABLE content_sources ADD CONSTRAINT chk_content_sources_base_url_format
    CHECK (base_url LIKE 'http%://%');

-- JSON schema validation for rate_limits
ALTER TABLE content_sources ADD CONSTRAINT chk_content_sources_rate_limits_schema
    CHECK (
        jsonb_typeof(rate_limits->'requests_per_hour') = 'number' AND
        jsonb_typeof(rate_limits->'requests_per_day') = 'number' AND
        (rate_limits->>'requests_per_hour')::integer > 0 AND
        (rate_limits->>'requests_per_day')::integer > 0
    );

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_content_sources_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_content_sources_updated_at ON content_sources;
CREATE TRIGGER trg_content_sources_updated_at
    BEFORE UPDATE ON content_sources
    FOR EACH ROW
    EXECUTE FUNCTION update_content_sources_updated_at();

-- Function to update source statistics after content ingestion
CREATE OR REPLACE FUNCTION update_source_statistics(p_source_name VARCHAR(100), p_quality_score FLOAT DEFAULT NULL)
RETURNS VOID AS $$
BEGIN
    UPDATE content_sources
    SET
        content_count = content_count + 1,
        avg_quality_score = CASE
            WHEN p_quality_score IS NOT NULL AND avg_quality_score IS NOT NULL THEN
                (avg_quality_score * content_count + p_quality_score) / (content_count + 1)
            WHEN p_quality_score IS NOT NULL AND avg_quality_score IS NULL THEN
                p_quality_score
            ELSE
                avg_quality_score
        END,
        last_crawled = NOW()
    WHERE name = p_source_name;
END;
$$ LANGUAGE plpgsql;

-- Function to record crawl attempt
CREATE OR REPLACE FUNCTION record_crawl_attempt(p_source_name VARCHAR(100), p_success BOOLEAN, p_error_message TEXT DEFAULT NULL)
RETURNS VOID AS $$
BEGIN
    UPDATE content_sources
    SET
        total_crawl_attempts = total_crawl_attempts + 1,
        successful_crawl_attempts = CASE WHEN p_success THEN successful_crawl_attempts + 1 ELSE successful_crawl_attempts END,
        last_crawled = CASE WHEN p_success THEN NOW() ELSE last_crawled END,
        last_error = CASE WHEN NOT p_success THEN p_error_message ELSE last_error END,
        last_error_timestamp = CASE WHEN NOT p_success THEN NOW() ELSE last_error_timestamp END
    WHERE name = p_source_name;
END;
$$ LANGUAGE plpgsql;

-- Function to get source reliability metrics
CREATE OR REPLACE FUNCTION get_source_reliability_metrics(p_source_name VARCHAR(100))
RETURNS TABLE (
    success_rate NUMERIC,
    avg_quality NUMERIC,
    content_volume INTEGER,
    last_active TIMESTAMP,
    days_since_last_crawl INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        CASE
            WHEN cs.total_crawl_attempts = 0 THEN 0
            ELSE ROUND(cs.successful_crawl_attempts::NUMERIC / cs.total_crawl_attempts * 100, 2)
        END as success_rate,
        ROUND(cs.avg_quality_score, 2) as avg_quality,
        cs.content_count as content_volume,
        cs.last_crawled as last_active,
        CASE
            WHEN cs.last_crawled IS NULL THEN NULL
            ELSE EXTRACT(DAY FROM NOW() - cs.last_crawled)::INTEGER
        END as days_since_last_crawl
    FROM content_sources cs
    WHERE cs.name = p_source_name;
END;
$$ LANGUAGE plpgsql;

-- View for active sources summary
CREATE OR REPLACE VIEW active_sources_summary AS
SELECT
    cs.name,
    cs.source_type,
    cs.reliability_score,
    cs.avg_quality_score,
    cs.content_count,
    CASE
        WHEN cs.total_crawl_attempts = 0 THEN 0
        ELSE ROUND(cs.successful_crawl_attempts::NUMERIC / cs.total_crawl_attempts * 100, 2)
    END as success_rate,
    cs.last_crawled,
    EXTRACT(DAY FROM NOW() - cs.last_crawled)::INTEGER as days_since_crawl
FROM content_sources cs
WHERE cs.is_active = true
ORDER BY cs.reliability_score DESC, cs.avg_quality_score DESC;

-- Foreign key reference for content_items
ALTER TABLE content_items ADD CONSTRAINT fk_content_items_source
    FOREIGN KEY (source) REFERENCES content_sources(name) ON UPDATE CASCADE;

-- Sample data for testing (optional)
INSERT INTO content_sources (name, base_url, source_type, reliability_score, update_frequency, api_config)
VALUES
    ('arxiv', 'https://arxiv.org', 'academic', 0.95, 'daily', '{"api_endpoint": "http://export.arxiv.org/api/query", "max_results": 100}'),
    ('pubmed', 'https://pubmed.ncbi.nlm.nih.gov', 'academic', 0.98, 'daily', '{"api_endpoint": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", "max_results": 100}'),
    ('nature', 'https://www.nature.com', 'academic', 0.92, 'daily', '{"rss_feed": "https://www.nature.com/nature.rss", "max_articles": 50}'),
    ('techcrunch', 'https://techcrunch.com', 'news', 0.75, 'hourly', '{"rss_feed": "https://techcrunch.com/feed/", "max_articles": 100}'),
    ('medium', 'https://medium.com', 'blog', 0.65, 'hourly', '{"api_endpoint": "https://medium.com/feed", "max_articles": 200}')
ON CONFLICT (name) DO NOTHING;

COMMENT ON TABLE content_sources IS 'External data sources with reliability and performance metrics';
COMMENT ON COLUMN content_sources.reliability_score IS 'Source trustworthiness score (0.0-1.0)';
COMMENT ON COLUMN content_sources.avg_quality_score IS 'Average quality score of content from this source';
COMMENT ON COLUMN content_sources.api_config IS 'Source-specific API configuration and endpoints';
COMMENT ON COLUMN content_sources.rate_limits IS 'API usage restrictions and throttling settings';
COMMENT ON FUNCTION update_source_statistics IS 'Updates content count and quality statistics for a source';
COMMENT ON FUNCTION record_crawl_attempt IS 'Records crawl attempt success/failure with error handling';
COMMENT ON VIEW active_sources_summary IS 'Summary of active sources with performance metrics';