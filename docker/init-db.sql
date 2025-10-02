-- Initialize PAKE+ database with required extensions and schemas

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create n8n database for workflow automation
CREATE DATABASE n8n;

-- Connect to pake_knowledge database
\c pake_knowledge;

-- Create knowledge_nodes table with vector support
CREATE TABLE IF NOT EXISTS knowledge_nodes (
    pake_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content TEXT NOT NULL,
    confidence_score REAL DEFAULT 0.0 CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    metadata JSONB DEFAULT '{}',
    embeddings vector(384), -- Sentence transformer embedding dimension
    connections TEXT[] DEFAULT '{}',
    type VARCHAR(50) DEFAULT 'note',
    status VARCHAR(50) DEFAULT 'draft',
    verification_status VARCHAR(50) DEFAULT 'pending',
    source_uri TEXT DEFAULT '',
    tags TEXT[] DEFAULT '{}',
    ai_summary TEXT DEFAULT '',
    human_notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW(),
    modified_at TIMESTAMP DEFAULT NOW()
);

-- Create node_connections table for relationship mapping
CREATE TABLE IF NOT EXISTS node_connections (
    id SERIAL PRIMARY KEY,
    source_id UUID REFERENCES knowledge_nodes(pake_id) ON DELETE CASCADE,
    target_id UUID REFERENCES knowledge_nodes(pake_id) ON DELETE CASCADE,
    connection_type VARCHAR(100) DEFAULT 'relates_to',
    strength REAL DEFAULT 0.5 CHECK (strength >= 0.0 AND strength <= 1.0),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(source_id, target_id, connection_type)
);

-- Create processing_logs table for audit trail
CREATE TABLE IF NOT EXISTS processing_logs (
    id SERIAL PRIMARY KEY,
    pake_id UUID REFERENCES knowledge_nodes(pake_id) ON DELETE CASCADE,
    operation VARCHAR(50) NOT NULL,
    details JSONB DEFAULT '{}',
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create confidence_history table for tracking confidence changes
CREATE TABLE IF NOT EXISTS confidence_history (
    id SERIAL PRIMARY KEY,
    pake_id UUID REFERENCES knowledge_nodes(pake_id) ON DELETE CASCADE,
    old_score REAL,
    new_score REAL,
    reason TEXT,
    changed_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_knowledge_embeddings
ON knowledge_nodes USING ivfflat (embeddings vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_knowledge_confidence
ON knowledge_nodes(confidence_score DESC);

CREATE INDEX IF NOT EXISTS idx_knowledge_verification
ON knowledge_nodes(verification_status);

CREATE INDEX IF NOT EXISTS idx_knowledge_type
ON knowledge_nodes(type);

CREATE INDEX IF NOT EXISTS idx_knowledge_status
ON knowledge_nodes(status);

CREATE INDEX IF NOT EXISTS idx_knowledge_created
ON knowledge_nodes(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_knowledge_modified
ON knowledge_nodes(modified_at DESC);

CREATE INDEX IF NOT EXISTS idx_knowledge_content_fts
ON knowledge_nodes USING GIN (to_tsvector('english', content));

CREATE INDEX IF NOT EXISTS idx_knowledge_tags
ON knowledge_nodes USING GIN (tags);

CREATE INDEX IF NOT EXISTS idx_connections_source
ON node_connections(source_id);

CREATE INDEX IF NOT EXISTS idx_connections_target
ON node_connections(target_id);

CREATE INDEX IF NOT EXISTS idx_processing_logs_pake_id
ON processing_logs(pake_id);

CREATE INDEX IF NOT EXISTS idx_processing_logs_created
ON processing_logs(created_at DESC);

-- Create views for common queries
CREATE OR REPLACE VIEW high_confidence_nodes AS
SELECT pake_id, content, confidence_score, type, tags, created_at
FROM knowledge_nodes
WHERE confidence_score >= 0.8 AND verification_status = 'verified';

CREATE OR REPLACE VIEW unverified_nodes AS
SELECT pake_id, content, confidence_score, type, source_uri, created_at
FROM knowledge_nodes
WHERE verification_status = 'pending'
ORDER BY confidence_score ASC, created_at DESC;

CREATE OR REPLACE VIEW node_connection_graph AS
SELECT
    nc.source_id,
    nc.target_id,
    nc.connection_type,
    nc.strength,
    s.content as source_content,
    t.content as target_content,
    s.type as source_type,
    t.type as target_type
FROM node_connections nc
JOIN knowledge_nodes s ON nc.source_id = s.pake_id
JOIN knowledge_nodes t ON nc.target_id = t.pake_id;

-- Create functions for confidence scoring updates
CREATE OR REPLACE FUNCTION update_confidence_score()
RETURNS TRIGGER AS $$
BEGIN
    -- Log confidence score changes
    IF OLD.confidence_score != NEW.confidence_score THEN
        INSERT INTO confidence_history (pake_id, old_score, new_score, reason, changed_by)
        VALUES (NEW.pake_id, OLD.confidence_score, NEW.confidence_score, 'automatic_update', 'system');
    END IF;

    -- Update modified timestamp
    NEW.modified_at = NOW();

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for confidence score updates
CREATE TRIGGER trigger_confidence_update
    BEFORE UPDATE ON knowledge_nodes
    FOR EACH ROW
    EXECUTE FUNCTION update_confidence_score();

-- Create function for updating connections array
CREATE OR REPLACE FUNCTION sync_connections_array()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- Add to source node connections
        UPDATE knowledge_nodes
        SET connections = array_append(connections, NEW.target_id::text)
        WHERE pake_id = NEW.source_id
        AND NOT (NEW.target_id::text = ANY(connections));

        -- Add to target node connections (bidirectional)
        UPDATE knowledge_nodes
        SET connections = array_append(connections, NEW.source_id::text)
        WHERE pake_id = NEW.target_id
        AND NOT (NEW.source_id::text = ANY(connections));

    ELSIF TG_OP = 'DELETE' THEN
        -- Remove from source node connections
        UPDATE knowledge_nodes
        SET connections = array_remove(connections, OLD.target_id::text)
        WHERE pake_id = OLD.source_id;

        -- Remove from target node connections
        UPDATE knowledge_nodes
        SET connections = array_remove(connections, OLD.source_id::text)
        WHERE pake_id = OLD.target_id;
    END IF;

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Create trigger for connections synchronization
CREATE TRIGGER trigger_sync_connections
    AFTER INSERT OR DELETE ON node_connections
    FOR EACH ROW
    EXECUTE FUNCTION sync_connections_array();

-- Insert sample data for testing
INSERT INTO knowledge_nodes (content, confidence_score, type, verification_status, tags, source_uri) VALUES
(
    'PAKE+ system initialization complete. Core components include MCP servers, PostgreSQL with pgvector, Redis for queuing, and Obsidian vault integration.',
    0.9,
    'system',
    'verified',
    ARRAY['system', 'pake', 'initialization'],
    'local://system'
),
(
    'Knowledge confidence scoring uses multiple factors: source authority, content coherence, cross-references, temporal relevance, linguistic quality, and verification status.',
    0.8,
    'note',
    'verified',
    ARRAY['confidence', 'scoring', 'algorithm'],
    'local://documentation'
);

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO pake_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO pake_admin;