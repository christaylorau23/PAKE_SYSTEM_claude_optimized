-- Content Items Table Migration
-- Stores individual pieces of content with comprehensive metadata and curation attributes

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

CREATE TABLE IF NOT EXISTS content_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    url TEXT NOT NULL UNIQUE,
    source VARCHAR(100) NOT NULL,
    content_type VARCHAR(20) NOT NULL CHECK (content_type IN ('paper', 'article', 'blog', 'video', 'podcast')),
    summary TEXT,
    full_text TEXT,
    published_date TIMESTAMP,
    ingested_date TIMESTAMP NOT NULL DEFAULT NOW(),
    author VARCHAR(200),
    domain VARCHAR(100),
    quality_score FLOAT CHECK (quality_score >= 0.0 AND quality_score <= 1.0),
    authority_score FLOAT CHECK (authority_score >= 0.0 AND authority_score <= 1.0),
    engagement_metrics JSONB DEFAULT '{}',
    topic_tags TEXT[] NOT NULL DEFAULT '{}',
    content_embedding VECTOR(384), -- For sentence-transformers/all-MiniLM-L6-v2
    is_active BOOLEAN NOT NULL DEFAULT true,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for performance optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_items_url ON content_items USING btree (url);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_items_source ON content_items USING btree (source);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_items_content_type ON content_items USING btree (content_type);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_items_published_date ON content_items USING btree (published_date DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_items_ingested_date ON content_items USING btree (ingested_date DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_items_quality_score ON content_items USING btree (quality_score DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_items_authority_score ON content_items USING btree (authority_score DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_items_domain ON content_items USING btree (domain);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_items_is_active ON content_items USING btree (is_active);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_items_topic_tags ON content_items USING gin (topic_tags);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_items_title_gin ON content_items USING gin (title gin_trgm_ops);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_items_full_text_gin ON content_items USING gin (to_tsvector('english', full_text));

-- Vector similarity index (requires pgvector extension)
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_items_embedding_ivfflat ON content_items
-- USING ivfflat (content_embedding vector_cosine_ops) WITH (lists = 100);

-- Constraints
ALTER TABLE content_items ADD CONSTRAINT chk_content_items_published_not_future
    CHECK (published_date IS NULL OR published_date <= NOW());

ALTER TABLE content_items ADD CONSTRAINT chk_content_items_topic_tags_not_empty
    CHECK (array_length(topic_tags, 1) > 0 OR topic_tags = '{}');

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_content_items_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_content_items_updated_at ON content_items;
CREATE TRIGGER trg_content_items_updated_at
    BEFORE UPDATE ON content_items
    FOR EACH ROW
    EXECUTE FUNCTION update_content_items_updated_at();

-- Sample data for testing (optional)
-- INSERT INTO content_items (title, url, source, content_type, domain, quality_score, authority_score, topic_tags)
-- VALUES
-- ('Machine Learning in Healthcare', 'https://example.com/ml-healthcare', 'arxiv', 'paper', 'machine_learning', 0.9, 0.95, ARRAY['machine learning', 'healthcare', 'ai']),
-- ('Introduction to Deep Learning', 'https://example.com/intro-dl', 'blog', 'article', 'machine_learning', 0.7, 0.6, ARRAY['deep learning', 'neural networks', 'tutorial']);

COMMENT ON TABLE content_items IS 'Stores individual pieces of content with comprehensive metadata and curation attributes';
COMMENT ON COLUMN content_items.content_embedding IS 'Semantic embedding vector for similarity computation (384-dimensional)';
COMMENT ON COLUMN content_items.engagement_metrics IS 'JSON object storing click-through rates, save rates, etc.';
COMMENT ON COLUMN content_items.topic_tags IS 'Array of extracted topic keywords for content classification';
COMMENT ON COLUMN content_items.metadata IS 'Source-specific additional data in JSON format';