-- Topic Categories Table Migration
-- Hierarchical content classification system

CREATE TABLE IF NOT EXISTS topic_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    parent_id UUID,
    level INTEGER NOT NULL DEFAULT 0 CHECK (level >= 0),
    keywords TEXT[] DEFAULT '{}',
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    content_count INTEGER NOT NULL DEFAULT 0 CHECK (content_count >= 0),
    display_order INTEGER DEFAULT 0,
    color_code VARCHAR(7), -- Hex color code for UI display
    icon_name VARCHAR(50), -- Icon identifier for UI display
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for performance optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_topic_categories_name ON topic_categories USING btree (name);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_topic_categories_parent_id ON topic_categories USING btree (parent_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_topic_categories_level ON topic_categories USING btree (level);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_topic_categories_is_active ON topic_categories USING btree (is_active);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_topic_categories_content_count ON topic_categories USING btree (content_count DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_topic_categories_display_order ON topic_categories USING btree (display_order);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_topic_categories_keywords ON topic_categories USING gin (keywords);

-- Composite index for hierarchy queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_topic_categories_hierarchy
ON topic_categories USING btree (parent_id, level, display_order);

-- Unique constraint for name within same parent
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_topic_categories_unique_name_parent
ON topic_categories (name, COALESCE(parent_id, '00000000-0000-0000-0000-000000000000'::uuid));

-- Self-referential foreign key constraint
ALTER TABLE topic_categories ADD CONSTRAINT fk_topic_categories_parent_id
    FOREIGN KEY (parent_id) REFERENCES topic_categories(id) ON DELETE CASCADE;

-- Constraints
ALTER TABLE topic_categories ADD CONSTRAINT chk_topic_categories_not_self_parent
    CHECK (id != parent_id);

ALTER TABLE topic_categories ADD CONSTRAINT chk_topic_categories_level_consistency
    CHECK (
        (parent_id IS NULL AND level = 0) OR
        (parent_id IS NOT NULL AND level > 0)
    );

ALTER TABLE topic_categories ADD CONSTRAINT chk_topic_categories_color_format
    CHECK (color_code IS NULL OR color_code ~ '^#[0-9A-Fa-f]{6}$');

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_topic_categories_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_topic_categories_updated_at ON topic_categories;
CREATE TRIGGER trg_topic_categories_updated_at
    BEFORE UPDATE ON topic_categories
    FOR EACH ROW
    EXECUTE FUNCTION update_topic_categories_updated_at();

-- Trigger to validate hierarchy level consistency
CREATE OR REPLACE FUNCTION validate_topic_category_level()
RETURNS TRIGGER AS $$
DECLARE
    parent_level INTEGER;
BEGIN
    IF NEW.parent_id IS NOT NULL THEN
        SELECT level INTO parent_level
        FROM topic_categories
        WHERE id = NEW.parent_id;

        IF parent_level IS NULL THEN
            RAISE EXCEPTION 'Parent category not found';
        END IF;

        IF NEW.level != parent_level + 1 THEN
            NEW.level = parent_level + 1;
        END IF;
    ELSE
        NEW.level = 0;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_topic_categories_validate_level ON topic_categories;
CREATE TRIGGER trg_topic_categories_validate_level
    BEFORE INSERT OR UPDATE ON topic_categories
    FOR EACH ROW
    EXECUTE FUNCTION validate_topic_category_level();

-- Function to get category hierarchy path
CREATE OR REPLACE FUNCTION get_category_path(p_category_id UUID)
RETURNS TEXT AS $$
DECLARE
    path TEXT := '';
    current_id UUID := p_category_id;
    current_name VARCHAR(100);
    current_parent UUID;
BEGIN
    LOOP
        SELECT name, parent_id INTO current_name, current_parent
        FROM topic_categories
        WHERE id = current_id;

        IF current_name IS NULL THEN
            EXIT;
        END IF;

        IF path = '' THEN
            path := current_name;
        ELSE
            path := current_name || ' > ' || path;
        END IF;

        current_id := current_parent;
        EXIT WHEN current_id IS NULL;
    END LOOP;

    RETURN path;
END;
$$ LANGUAGE plpgsql;

-- Function to get all subcategories
CREATE OR REPLACE FUNCTION get_all_subcategories(p_parent_id UUID)
RETURNS TABLE (
    category_id UUID,
    category_name VARCHAR(100),
    category_level INTEGER,
    full_path TEXT
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE category_tree AS (
        -- Base case: direct children
        SELECT
            tc.id,
            tc.name,
            tc.level,
            tc.name::TEXT as path
        FROM topic_categories tc
        WHERE tc.parent_id = p_parent_id
        AND tc.is_active = true

        UNION ALL

        -- Recursive case: children of children
        SELECT
            tc.id,
            tc.name,
            tc.level,
            ct.path || ' > ' || tc.name
        FROM topic_categories tc
        INNER JOIN category_tree ct ON tc.parent_id = ct.id
        WHERE tc.is_active = true
    )
    SELECT
        ct.id as category_id,
        ct.name as category_name,
        ct.level as category_level,
        ct.path as full_path
    FROM category_tree ct
    ORDER BY ct.level, ct.name;
END;
$$ LANGUAGE plpgsql;

-- Function to update content count for category
CREATE OR REPLACE FUNCTION update_category_content_count(p_category_name VARCHAR(100), p_increment INTEGER DEFAULT 1)
RETURNS VOID AS $$
BEGIN
    UPDATE topic_categories
    SET content_count = content_count + p_increment
    WHERE name = p_category_name
    AND is_active = true;
END;
$$ LANGUAGE plpgsql;

-- Function to get category statistics
CREATE OR REPLACE FUNCTION get_category_statistics(p_category_id UUID DEFAULT NULL)
RETURNS TABLE (
    category_id UUID,
    category_name VARCHAR(100),
    direct_content_count INTEGER,
    total_content_count BIGINT,
    subcategory_count BIGINT,
    avg_content_quality NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE category_subtree AS (
        SELECT id, name, content_count
        FROM topic_categories
        WHERE
            (p_category_id IS NULL OR id = p_category_id)
            AND is_active = true

        UNION ALL

        SELECT tc.id, tc.name, tc.content_count
        FROM topic_categories tc
        INNER JOIN category_subtree cs ON tc.parent_id = cs.id
        WHERE tc.is_active = true
    ),
    content_mapping AS (
        SELECT DISTINCT
            tc.id as category_id,
            ci.id as content_id,
            ci.quality_score
        FROM topic_categories tc
        CROSS JOIN LATERAL unnest(tc.keywords) AS keyword
        JOIN content_items ci ON keyword = ANY(ci.topic_tags)
        WHERE tc.is_active = true AND ci.is_active = true
    )
    SELECT
        cs.id as category_id,
        cs.name as category_name,
        cs.content_count as direct_content_count,
        COUNT(cm.content_id) as total_content_count,
        (SELECT COUNT(*) FROM topic_categories WHERE parent_id = cs.id AND is_active = true) as subcategory_count,
        ROUND(AVG(cm.quality_score), 2) as avg_content_quality
    FROM category_subtree cs
    LEFT JOIN content_mapping cm ON cs.id = cm.category_id
    GROUP BY cs.id, cs.name, cs.content_count
    ORDER BY cs.name;
END;
$$ LANGUAGE plpgsql;

-- Many-to-Many relationship table for content-topic mapping
CREATE TABLE IF NOT EXISTS content_topic_mapping (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_id UUID NOT NULL,
    topic_category_id UUID NOT NULL,
    relevance_score FLOAT DEFAULT 1.0 CHECK (relevance_score >= 0.0 AND relevance_score <= 1.0),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for content-topic mapping
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_topic_mapping_content_id ON content_topic_mapping USING btree (content_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_topic_mapping_topic_id ON content_topic_mapping USING btree (topic_category_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_topic_mapping_relevance ON content_topic_mapping USING btree (relevance_score DESC);

-- Foreign key constraints for mapping table
ALTER TABLE content_topic_mapping ADD CONSTRAINT fk_content_topic_mapping_content_id
    FOREIGN KEY (content_id) REFERENCES content_items(id) ON DELETE CASCADE;

ALTER TABLE content_topic_mapping ADD CONSTRAINT fk_content_topic_mapping_topic_id
    FOREIGN KEY (topic_category_id) REFERENCES topic_categories(id) ON DELETE CASCADE;

-- Unique constraint to prevent duplicate mappings
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_content_topic_mapping_unique
ON content_topic_mapping (content_id, topic_category_id);

-- View for category hierarchy
CREATE OR REPLACE VIEW topic_category_hierarchy AS
WITH RECURSIVE category_tree AS (
    -- Root categories
    SELECT
        tc.id,
        tc.name,
        tc.parent_id,
        tc.level,
        tc.content_count,
        tc.name::TEXT as full_path,
        ARRAY[tc.id] as path_ids
    FROM topic_categories tc
    WHERE tc.parent_id IS NULL
    AND tc.is_active = true

    UNION ALL

    -- Child categories
    SELECT
        tc.id,
        tc.name,
        tc.parent_id,
        tc.level,
        tc.content_count,
        ct.full_path || ' > ' || tc.name,
        ct.path_ids || tc.id
    FROM topic_categories tc
    INNER JOIN category_tree ct ON tc.parent_id = ct.id
    WHERE tc.is_active = true
)
SELECT * FROM category_tree
ORDER BY level, name;

-- Sample data for testing
INSERT INTO topic_categories (name, level, keywords, description, color_code, display_order)
VALUES
    -- Level 0 (Root categories)
    ('Technology', 0, ARRAY['technology', 'tech', 'computing'], 'Technology and computing topics', '#3498db', 1),
    ('Science', 0, ARRAY['science', 'research', 'scientific'], 'Scientific research and discoveries', '#2ecc71', 2),
    ('Health', 0, ARRAY['health', 'medicine', 'medical', 'healthcare'], 'Health and medical topics', '#e74c3c', 3),
    ('Business', 0, ARRAY['business', 'finance', 'economics', 'market'], 'Business and economic topics', '#f39c12', 4)
ON CONFLICT (name, COALESCE(parent_id, '00000000-0000-0000-0000-000000000000'::uuid)) DO NOTHING;

-- Insert subcategories
INSERT INTO topic_categories (name, parent_id, level, keywords, description, display_order)
SELECT
    'Artificial Intelligence',
    tc.id,
    1,
    ARRAY['ai', 'artificial intelligence', 'machine learning', 'deep learning', 'neural networks'],
    'AI and machine learning technologies',
    1
FROM topic_categories tc
WHERE tc.name = 'Technology' AND tc.level = 0
ON CONFLICT (name, COALESCE(parent_id, '00000000-0000-0000-0000-000000000000'::uuid)) DO NOTHING;

INSERT INTO topic_categories (name, parent_id, level, keywords, description, display_order)
SELECT
    'Biotechnology',
    tc.id,
    1,
    ARRAY['biotech', 'biotechnology', 'genetics', 'genomics', 'bioinformatics'],
    'Biotechnology and genetic research',
    1
FROM topic_categories tc
WHERE tc.name = 'Science' AND tc.level = 0
ON CONFLICT (name, COALESCE(parent_id, '00000000-0000-0000-0000-000000000000'::uuid)) DO NOTHING;

COMMENT ON TABLE topic_categories IS 'Hierarchical content classification system';
COMMENT ON TABLE content_topic_mapping IS 'Many-to-many mapping between content items and topic categories';
COMMENT ON COLUMN topic_categories.level IS 'Hierarchy depth (0 = root, 1+ = subcategories)';
COMMENT ON COLUMN topic_categories.keywords IS 'Keywords associated with this category for content matching';
COMMENT ON COLUMN content_topic_mapping.relevance_score IS 'How relevant the content is to this topic (0.0-1.0)';
COMMENT ON FUNCTION get_category_path IS 'Returns full hierarchical path for a category (e.g., "Science > Biotechnology")';
COMMENT ON FUNCTION get_all_subcategories IS 'Returns all subcategories recursively for a given parent category';