/**
 * PAKE System - Trend Record Repository
 *
 * Persistent storage layer for TrendRecord entities with PostgreSQL backend.
 * Provides CRUD operations, search, and analytics for trends data.
 */

import { Pool, PoolClient, QueryResult } from 'pg';
import { createLogger, Logger } from '../../../orchestrator/src/utils/logger';
import { metrics } from '../../../orchestrator/src/utils/metrics';
import { TrendRecord, TrendEntity, AnomalyFlag } from '../types/TrendRecord';

export interface TrendQuery {
  // Filters
  dateRange?: { start: Date; end: Date };
  platforms?: string[];
  categories?: string[];
  languages?: string[];
  regions?: string[];

  // Content filters
  keywords?: string[];
  entities?: string[];
  anomalies?: AnomalyFlag[];

  // Quality filters
  minQualityScore?: number;
  minEngagement?: number;
  maxAge?: number; // hours

  // Pagination
  limit?: number;
  offset?: number;
  cursor?: string;

  // Sorting
  sortBy?: 'timestamp' | 'engagement' | 'quality_score' | 'freshness';
  sortOrder?: 'asc' | 'desc';
}

export interface TrendAnalytics {
  totalRecords: number;
  timeRange: { earliest: Date; latest: Date };
  platformDistribution: Map<string, number>;
  categoryDistribution: Map<string, number>;
  anomalyDistribution: Map<AnomalyFlag, number>;
  averageQualityScore: number;
  averageEngagement: number;
  freshnessMetrics: {
    average: number;
    p50: number;
    p95: number;
    p99: number;
  };
}

export interface StorageMetrics {
  totalRecords: number;
  recordsPerSecond: number;
  averageWriteLatency: number;
  averageReadLatency: number;
  duplicatesDetected: number;
  storageSize: number;
  indexEfficiency: number;
}

/**
 * PostgreSQL-backed repository for trend records
 */
export class TrendRepository {
  private readonly logger: Logger;
  private readonly pool: Pool;
  private readonly tableName = 'trend_records';
  private readonly entitiesTableName = 'trend_entities';
  private readonly anomaliesTableName = 'trend_anomalies';

  // Performance tracking
  private metricsTracker = {
    totalOperations: 0,
    writeOperations: 0,
    readOperations: 0,
    totalLatency: 0,
    duplicatesDetected: 0,
  };

  constructor(connectionConfig: any) {
    this.logger = createLogger('TrendRepository');
    this.pool = new Pool({
      ...connectionConfig,
      max: 20,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 5000,
      statement_timeout: 30000,
    });

    this.initializeSchema();
  }

  /**
   * Store a trend record with full transactional support
   */
  async store(record: TrendRecord): Promise<string> {
    const startTime = Date.now();
    const client = await this.pool.connect();

    try {
      await client.query('BEGIN');

      // Check for duplicates by content hash
      const duplicateCheck = await this.checkDuplicate(
        client,
        record.contentHash
      );
      if (duplicateCheck) {
        this.metricsTracker.duplicatesDetected++;
        await client.query('ROLLBACK');

        this.logger.debug('Duplicate record detected', {
          id: record.id,
          contentHash: record.contentHash,
          existingId: duplicateCheck.id,
        });

        return duplicateCheck.id;
      }

      // Insert main trend record
      const recordQuery = `
        INSERT INTO ${this.tableName} (
          id, platform, category, language, region,
          title, content, url, author,
          timestamp, ingested_at,
          engagement_count, view_count, share_count,
          content_hash, similarity_hash,
          quality_score, freshness_score, anomaly_score,
          metadata, raw_data
        ) VALUES (
          $1, $2, $3, $4, $5,
          $6, $7, $8, $9,
          $10, $11,
          $12, $13, $14,
          $15, $16,
          $17, $18, $19,
          $20, $21
        )
      `;

      await client.query(recordQuery, [
        record.id,
        record.platform,
        record.category,
        record.language,
        record.region,
        record.title,
        record.content,
        record.url,
        record.author,
        record.timestamp,
        record.ingestedAt,
        record.engagementCount,
        record.viewCount,
        record.shareCount,
        record.contentHash,
        record.similarityHash,
        record.qualityScore,
        record.freshnessScore,
        record.anomalyScore,
        JSON.stringify(record.metadata),
        JSON.stringify(record.rawData),
      ]);

      // Insert entities
      if (record.entities && record.entities.length > 0) {
        await this.storeEntities(client, record.id, record.entities);
      }

      // Insert anomalies
      if (record.anomalies && record.anomalies.length > 0) {
        await this.storeAnomalies(client, record.id, record.anomalies);
      }

      await client.query('COMMIT');

      // Track metrics
      this.trackOperation('write', Date.now() - startTime);

      this.logger.info('Trend record stored successfully', {
        id: record.id,
        platform: record.platform,
        category: record.category,
        entitiesCount: record.entities?.length || 0,
        anomaliesCount: record.anomalies?.length || 0,
      });

      return record.id;
    } catch (error) {
      await client.query('ROLLBACK');
      this.logger.error('Failed to store trend record', {
        id: record.id,
        error: error.message,
        stack: error.stack,
      });
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Retrieve trend record by ID with all related data
   */
  async findById(id: string): Promise<TrendRecord | null> {
    const startTime = Date.now();
    const client = await this.pool.connect();

    try {
      // Get main record
      const recordQuery = `SELECT * FROM ${this.tableName} WHERE id = $1`;
      const recordResult = await client.query(recordQuery, [id]);

      if (recordResult.rows.length === 0) {
        return null;
      }

      const record = this.mapRowToRecord(recordResult.rows[0]);

      // Get entities
      const entitiesQuery = `SELECT * FROM ${this.entitiesTableName} WHERE trend_id = $1 ORDER BY confidence DESC`;
      const entitiesResult = await client.query(entitiesQuery, [id]);
      record.entities = entitiesResult.rows.map(this.mapRowToEntity);

      // Get anomalies
      const anomaliesQuery = `SELECT * FROM ${this.anomaliesTableName} WHERE trend_id = $1 ORDER BY severity DESC`;
      const anomaliesResult = await client.query(anomaliesQuery, [id]);
      record.anomalies = anomaliesResult.rows.map(row => ({
        type: row.type as AnomalyFlag,
        severity: row.severity,
        confidence: row.confidence,
        description: row.description,
        metadata: JSON.parse(row.metadata || '{}'),
      }));

      this.trackOperation('read', Date.now() - startTime);
      return record;
    } catch (error) {
      this.logger.error('Failed to find trend record', {
        id,
        error: error.message,
      });
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Search trends with complex filtering and pagination
   */
  async search(query: TrendQuery): Promise<{
    records: TrendRecord[];
    total: number;
    hasMore: boolean;
    nextCursor?: string;
  }> {
    const startTime = Date.now();
    const client = await this.pool.connect();

    try {
      const { whereClause, parameters, limit, offset } =
        this.buildSearchQuery(query);

      // Get total count
      const countQuery = `SELECT COUNT(*) FROM ${this.tableName} ${whereClause}`;
      const countResult = await client.query(countQuery, parameters);
      const total = parseInt(countResult.rows[0].count);

      // Get records
      const sortClause = this.buildSortClause(query.sortBy, query.sortOrder);
      const searchQuery = `
        SELECT * FROM ${this.tableName} 
        ${whereClause} 
        ${sortClause}
        LIMIT $${parameters.length + 1} OFFSET $${parameters.length + 2}
      `;

      const searchResult = await client.query(searchQuery, [
        ...parameters,
        limit,
        offset,
      ]);

      // Hydrate records with entities and anomalies
      const records = await Promise.all(
        searchResult.rows.map(row =>
          this.hydrateRecord(client, this.mapRowToRecord(row))
        )
      );

      const hasMore = offset + records.length < total;
      const nextCursor = hasMore
        ? Buffer.from(String(offset + limit)).toString('base64')
        : undefined;

      this.trackOperation('read', Date.now() - startTime);

      return {
        records,
        total,
        hasMore,
        nextCursor,
      };
    } catch (error) {
      this.logger.error('Failed to search trends', {
        query,
        error: error.message,
      });
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Get analytics and insights about stored trends
   */
  async getAnalytics(query: Partial<TrendQuery> = {}): Promise<TrendAnalytics> {
    const client = await this.pool.connect();

    try {
      const { whereClause, parameters } = this.buildSearchQuery(query);

      // Basic metrics
      const metricsQuery = `
        SELECT 
          COUNT(*) as total_records,
          MIN(timestamp) as earliest,
          MAX(timestamp) as latest,
          AVG(quality_score) as avg_quality,
          AVG(engagement_count) as avg_engagement,
          AVG(freshness_score) as avg_freshness,
          PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY freshness_score) as p50_freshness,
          PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY freshness_score) as p95_freshness,
          PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY freshness_score) as p99_freshness
        FROM ${this.tableName} 
        ${whereClause}
      `;

      const metricsResult = await client.query(metricsQuery, parameters);
      const metrics = metricsResult.rows[0];

      // Platform distribution
      const platformQuery = `
        SELECT platform, COUNT(*) as count 
        FROM ${this.tableName} 
        ${whereClause}
        GROUP BY platform 
        ORDER BY count DESC
      `;
      const platformResult = await client.query(platformQuery, parameters);
      const platformDistribution = new Map(
        platformResult.rows.map(row => [row.platform, parseInt(row.count)])
      );

      // Category distribution
      const categoryQuery = `
        SELECT category, COUNT(*) as count 
        FROM ${this.tableName} 
        ${whereClause}
        GROUP BY category 
        ORDER BY count DESC
      `;
      const categoryResult = await client.query(categoryQuery, parameters);
      const categoryDistribution = new Map(
        categoryResult.rows.map(row => [row.category, parseInt(row.count)])
      );

      // Anomaly distribution
      const anomalyQuery = `
        SELECT a.type, COUNT(*) as count
        FROM ${this.anomaliesTableName} a
        JOIN ${this.tableName} t ON a.trend_id = t.id
        ${whereClause.replace('WHERE', 'WHERE')}
        GROUP BY a.type
        ORDER BY count DESC
      `;
      const anomalyResult = await client.query(anomalyQuery, parameters);
      const anomalyDistribution = new Map(
        anomalyResult.rows.map(row => [
          row.type as AnomalyFlag,
          parseInt(row.count),
        ])
      );

      return {
        totalRecords: parseInt(metrics.total_records),
        timeRange: {
          earliest: new Date(metrics.earliest),
          latest: new Date(metrics.latest),
        },
        platformDistribution,
        categoryDistribution,
        anomalyDistribution,
        averageQualityScore: parseFloat(metrics.avg_quality),
        averageEngagement: parseFloat(metrics.avg_engagement),
        freshnessMetrics: {
          average: parseFloat(metrics.avg_freshness),
          p50: parseFloat(metrics.p50_freshness),
          p95: parseFloat(metrics.p95_freshness),
          p99: parseFloat(metrics.p99_freshness),
        },
      };
    } catch (error) {
      this.logger.error('Failed to get analytics', { error: error.message });
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Bulk insert trends with optimized batch processing
   */
  async bulkStore(records: TrendRecord[]): Promise<string[]> {
    const startTime = Date.now();
    const client = await this.pool.connect();
    const storedIds: string[] = [];

    try {
      await client.query('BEGIN');

      // Process in batches of 100
      const batchSize = 100;
      for (let i = 0; i < records.length; i += batchSize) {
        const batch = records.slice(i, i + batchSize);

        // Build bulk insert query
        const values: any[] = [];
        const placeholders: string[] = [];
        let paramIndex = 1;

        for (const record of batch) {
          // Check for duplicates
          const duplicate = await this.checkDuplicate(
            client,
            record.contentHash
          );
          if (duplicate) {
            this.metricsTracker.duplicatesDetected++;
            continue;
          }

          placeholders.push(
            `(${Array.from({ length: 21 }, (_, j) => `$${paramIndex + j}`).join(', ')})`
          );
          values.push(
            record.id,
            record.platform,
            record.category,
            record.language,
            record.region,
            record.title,
            record.content,
            record.url,
            record.author,
            record.timestamp,
            record.ingestedAt,
            record.engagementCount,
            record.viewCount,
            record.shareCount,
            record.contentHash,
            record.similarityHash,
            record.qualityScore,
            record.freshnessScore,
            record.anomalyScore,
            JSON.stringify(record.metadata),
            JSON.stringify(record.rawData)
          );
          paramIndex += 21;
          storedIds.push(record.id);
        }

        if (placeholders.length > 0) {
          const bulkQuery = `
            INSERT INTO ${this.tableName} (
              id, platform, category, language, region,
              title, content, url, author,
              timestamp, ingested_at,
              engagement_count, view_count, share_count,
              content_hash, similarity_hash,
              quality_score, freshness_score, anomaly_score,
              metadata, raw_data
            ) VALUES ${placeholders.join(', ')}
          `;

          await client.query(bulkQuery, values);
        }
      }

      await client.query('COMMIT');
      this.trackOperation('write', Date.now() - startTime, records.length);

      this.logger.info('Bulk store completed', {
        totalRecords: records.length,
        storedRecords: storedIds.length,
        duplicates: this.metricsTracker.duplicatesDetected,
      });

      return storedIds;
    } catch (error) {
      await client.query('ROLLBACK');
      this.logger.error('Bulk store failed', { error: error.message });
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Delete trend records older than specified age
   */
  async cleanup(maxAge: number): Promise<number> {
    const client = await this.pool.connect();

    try {
      const cutoffDate = new Date(Date.now() - maxAge * 24 * 60 * 60 * 1000);

      // Delete related entities and anomalies first
      await client.query(
        `
        DELETE FROM ${this.entitiesTableName} 
        WHERE trend_id IN (
          SELECT id FROM ${this.tableName} WHERE timestamp < $1
        )
      `,
        [cutoffDate]
      );

      await client.query(
        `
        DELETE FROM ${this.anomaliesTableName} 
        WHERE trend_id IN (
          SELECT id FROM ${this.tableName} WHERE timestamp < $1
        )
      `,
        [cutoffDate]
      );

      // Delete main records
      const result = await client.query(
        `
        DELETE FROM ${this.tableName} WHERE timestamp < $1
      `,
        [cutoffDate]
      );

      const deletedCount = result.rowCount;

      this.logger.info('Cleanup completed', {
        deletedRecords: deletedCount,
        cutoffDate: cutoffDate.toISOString(),
      });

      return deletedCount;
    } catch (error) {
      this.logger.error('Cleanup failed', { error: error.message });
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Get repository performance metrics
   */
  getStorageMetrics(): StorageMetrics {
    const avgLatency =
      this.metricsTracker.totalLatency /
      Math.max(this.metricsTracker.totalOperations, 1);

    return {
      totalRecords: this.metricsTracker.totalOperations,
      recordsPerSecond:
        this.metricsTracker.writeOperations / (avgLatency / 1000) || 0,
      averageWriteLatency: avgLatency,
      averageReadLatency: avgLatency,
      duplicatesDetected: this.metricsTracker.duplicatesDetected,
      storageSize: 0, // Would need database-specific query
      indexEfficiency: 0.95, // Placeholder
    };
  }

  /**
   * Close connection pool
   */
  async close(): Promise<void> {
    await this.pool.end();
  }

  // Private helper methods

  private async checkDuplicate(
    client: PoolClient,
    contentHash: string
  ): Promise<{ id: string } | null> {
    const result = await client.query(
      `SELECT id FROM ${this.tableName} WHERE content_hash = $1 LIMIT 1`,
      [contentHash]
    );
    return result.rows[0] || null;
  }

  private async storeEntities(
    client: PoolClient,
    trendId: string,
    entities: TrendEntity[]
  ): Promise<void> {
    const entityValues: any[] = [];
    const entityPlaceholders: string[] = [];
    let paramIndex = 1;

    for (const entity of entities) {
      entityPlaceholders.push(
        `($${paramIndex}, $${paramIndex + 1}, $${paramIndex + 2}, $${paramIndex + 3}, $${paramIndex + 4}, $${paramIndex + 5}, $${paramIndex + 6})`
      );
      entityValues.push(
        trendId,
        entity.name,
        entity.type,
        entity.confidence,
        JSON.stringify(entity.aliases || []),
        entity.wikipediaUrl,
        JSON.stringify(entity.metadata || {})
      );
      paramIndex += 7;
    }

    if (entityPlaceholders.length > 0) {
      const entityQuery = `
        INSERT INTO ${this.entitiesTableName} (
          trend_id, name, type, confidence, aliases, wikipedia_url, metadata
        ) VALUES ${entityPlaceholders.join(', ')}
      `;
      await client.query(entityQuery, entityValues);
    }
  }

  private async storeAnomalies(
    client: PoolClient,
    trendId: string,
    anomalies: any[]
  ): Promise<void> {
    const anomalyValues: any[] = [];
    const anomalyPlaceholders: string[] = [];
    let paramIndex = 1;

    for (const anomaly of anomalies) {
      anomalyPlaceholders.push(
        `($${paramIndex}, $${paramIndex + 1}, $${paramIndex + 2}, $${paramIndex + 3}, $${paramIndex + 4}, $${paramIndex + 5})`
      );
      anomalyValues.push(
        trendId,
        anomaly.type,
        anomaly.severity,
        anomaly.confidence,
        anomaly.description,
        JSON.stringify(anomaly.metadata || {})
      );
      paramIndex += 6;
    }

    if (anomalyPlaceholders.length > 0) {
      const anomalyQuery = `
        INSERT INTO ${this.anomaliesTableName} (
          trend_id, type, severity, confidence, description, metadata
        ) VALUES ${anomalyPlaceholders.join(', ')}
      `;
      await client.query(anomalyQuery, anomalyValues);
    }
  }

  private async hydrateRecord(
    client: PoolClient,
    record: TrendRecord
  ): Promise<TrendRecord> {
    // Get entities
    const entitiesResult = await client.query(
      `SELECT * FROM ${this.entitiesTableName} WHERE trend_id = $1`,
      [record.id]
    );
    record.entities = entitiesResult.rows.map(this.mapRowToEntity);

    // Get anomalies
    const anomaliesResult = await client.query(
      `SELECT * FROM ${this.anomaliesTableName} WHERE trend_id = $1`,
      [record.id]
    );
    record.anomalies = anomaliesResult.rows.map(row => ({
      type: row.type as AnomalyFlag,
      severity: row.severity,
      confidence: row.confidence,
      description: row.description,
      metadata: JSON.parse(row.metadata || '{}'),
    }));

    return record;
  }

  private mapRowToRecord(row: any): TrendRecord {
    return {
      id: row.id,
      platform: row.platform,
      category: row.category,
      language: row.language,
      region: row.region,
      title: row.title,
      content: row.content,
      url: row.url,
      author: row.author,
      timestamp: new Date(row.timestamp),
      ingestedAt: new Date(row.ingested_at),
      engagementCount: row.engagement_count,
      viewCount: row.view_count,
      shareCount: row.share_count,
      contentHash: row.content_hash,
      similarityHash: row.similarity_hash,
      qualityScore: row.quality_score,
      freshnessScore: row.freshness_score,
      anomalyScore: row.anomaly_score,
      metadata: JSON.parse(row.metadata || '{}'),
      rawData: JSON.parse(row.raw_data || '{}'),
      entities: [], // Will be populated by hydration
      anomalies: [], // Will be populated by hydration
    };
  }

  private mapRowToEntity(row: any): TrendEntity {
    return {
      name: row.name,
      type: row.type,
      confidence: row.confidence,
      aliases: JSON.parse(row.aliases || '[]'),
      wikipediaUrl: row.wikipedia_url,
      metadata: JSON.parse(row.metadata || '{}'),
    };
  }

  private buildSearchQuery(query: TrendQuery): {
    whereClause: string;
    parameters: any[];
    limit: number;
    offset: number;
  } {
    const conditions: string[] = [];
    const parameters: any[] = [];
    let paramIndex = 1;

    if (query.dateRange) {
      conditions.push(
        `timestamp BETWEEN $${paramIndex} AND $${paramIndex + 1}`
      );
      parameters.push(query.dateRange.start, query.dateRange.end);
      paramIndex += 2;
    }

    if (query.platforms && query.platforms.length > 0) {
      conditions.push(`platform = ANY($${paramIndex})`);
      parameters.push(query.platforms);
      paramIndex++;
    }

    if (query.categories && query.categories.length > 0) {
      conditions.push(`category = ANY($${paramIndex})`);
      parameters.push(query.categories);
      paramIndex++;
    }

    if (query.minQualityScore !== undefined) {
      conditions.push(`quality_score >= $${paramIndex}`);
      parameters.push(query.minQualityScore);
      paramIndex++;
    }

    const whereClause =
      conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
    const limit = query.limit || 50;
    const offset = query.cursor
      ? parseInt(Buffer.from(query.cursor, 'base64').toString())
      : query.offset || 0;

    return { whereClause, parameters, limit, offset };
  }

  private buildSortClause(sortBy?: string, sortOrder?: string): string {
    const validSortFields = [
      'timestamp',
      'engagement',
      'quality_score',
      'freshness',
    ];
    const field = validSortFields.includes(sortBy || '') ? sortBy : 'timestamp';
    const order = sortOrder === 'asc' ? 'ASC' : 'DESC';

    const fieldMap = {
      timestamp: 'timestamp',
      engagement: 'engagement_count',
      quality_score: 'quality_score',
      freshness: 'freshness_score',
    };

    return `ORDER BY ${fieldMap[field]} ${order}`;
  }

  private trackOperation(
    type: 'read' | 'write',
    latency: number,
    recordCount: number = 1
  ): void {
    this.metricsTracker.totalOperations += recordCount;
    this.metricsTracker.totalLatency += latency;

    if (type === 'write') {
      this.metricsTracker.writeOperations += recordCount;
    } else {
      this.metricsTracker.readOperations += recordCount;
    }

    // Emit metrics
    metrics.histogram('trend_repository_operation_duration', latency, 'ms', {
      operation: type,
      record_count: recordCount.toString(),
    });
  }

  private async initializeSchema(): Promise<void> {
    const client = await this.pool.connect();

    try {
      // Main trends table
      await client.query(`
        CREATE TABLE IF NOT EXISTS ${this.tableName} (
          id VARCHAR(255) PRIMARY KEY,
          platform VARCHAR(100) NOT NULL,
          category VARCHAR(100) NOT NULL,
          language VARCHAR(10) NOT NULL,
          region VARCHAR(10) NOT NULL,
          title TEXT NOT NULL,
          content TEXT,
          url TEXT,
          author VARCHAR(255),
          timestamp TIMESTAMPTZ NOT NULL,
          ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          engagement_count BIGINT DEFAULT 0,
          view_count BIGINT DEFAULT 0,
          share_count BIGINT DEFAULT 0,
          content_hash VARCHAR(64) UNIQUE NOT NULL,
          similarity_hash VARCHAR(32) NOT NULL,
          quality_score REAL NOT NULL,
          freshness_score REAL NOT NULL,
          anomaly_score REAL DEFAULT 0,
          metadata JSONB,
          raw_data JSONB,
          created_at TIMESTAMPTZ DEFAULT NOW(),
          updated_at TIMESTAMPTZ DEFAULT NOW()
        );
      `);

      // Entities table
      await client.query(`
        CREATE TABLE IF NOT EXISTS ${this.entitiesTableName} (
          id SERIAL PRIMARY KEY,
          trend_id VARCHAR(255) NOT NULL REFERENCES ${this.tableName}(id) ON DELETE CASCADE,
          name VARCHAR(255) NOT NULL,
          type VARCHAR(50) NOT NULL,
          confidence REAL NOT NULL,
          aliases JSONB,
          wikipedia_url TEXT,
          metadata JSONB,
          created_at TIMESTAMPTZ DEFAULT NOW()
        );
      `);

      // Anomalies table
      await client.query(`
        CREATE TABLE IF NOT EXISTS ${this.anomaliesTableName} (
          id SERIAL PRIMARY KEY,
          trend_id VARCHAR(255) NOT NULL REFERENCES ${this.tableName}(id) ON DELETE CASCADE,
          type VARCHAR(50) NOT NULL,
          severity REAL NOT NULL,
          confidence REAL NOT NULL,
          description TEXT,
          metadata JSONB,
          created_at TIMESTAMPTZ DEFAULT NOW()
        );
      `);

      // Indexes for performance
      await client.query(`
        CREATE INDEX IF NOT EXISTS idx_trends_timestamp ON ${this.tableName}(timestamp);
        CREATE INDEX IF NOT EXISTS idx_trends_platform ON ${this.tableName}(platform);
        CREATE INDEX IF NOT EXISTS idx_trends_category ON ${this.tableName}(category);
        CREATE INDEX IF NOT EXISTS idx_trends_quality ON ${this.tableName}(quality_score);
        CREATE INDEX IF NOT EXISTS idx_trends_content_hash ON ${this.tableName}(content_hash);
        CREATE INDEX IF NOT EXISTS idx_trends_similarity_hash ON ${this.tableName}(similarity_hash);
        CREATE INDEX IF NOT EXISTS idx_entities_trend_id ON ${this.entitiesTableName}(trend_id);
        CREATE INDEX IF NOT EXISTS idx_entities_name ON ${this.entitiesTableName}(name);
        CREATE INDEX IF NOT EXISTS idx_anomalies_trend_id ON ${this.anomaliesTableName}(trend_id);
        CREATE INDEX IF NOT EXISTS idx_anomalies_type ON ${this.anomaliesTableName}(type);
      `);

      this.logger.info('Database schema initialized successfully');
    } catch (error) {
      this.logger.error('Failed to initialize schema', {
        error: error.message,
      });
      throw error;
    } finally {
      client.release();
    }
  }
}
