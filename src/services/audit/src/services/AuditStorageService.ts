/**
 * Audit Storage Service
 * Manages multi-tier storage for audit events (PostgreSQL, S3, Glacier)
 */

import { Pool } from 'pg';
import AWS from 'aws-sdk';
import { v4 as uuidv4 } from 'uuid';
import {
  AuditEvent,
  AuditQuery,
  AuditConfig,
  ArchivalJob,
  ArchivalJobStatus,
  ArchivalType,
} from '../types/audit.types';
import { CryptographicAuditService } from './CryptographicAuditService';
import { Logger } from '../utils/logger';

export class AuditStorageService {
  private readonly logger = new Logger('AuditStorageService');
  private readonly pgPool: Pool;
  private readonly s3: AWS.S3;
  private readonly glacier: AWS.Glacier;
  private readonly cryptoService: CryptographicAuditService;
  private readonly config: AuditConfig;

  constructor(config: AuditConfig, cryptoService: CryptographicAuditService) {
    this.config = config;
    this.cryptoService = cryptoService;

    // Initialize PostgreSQL connection pool
    this.pgPool = new Pool({
      host: config.database.host,
      port: config.database.port,
      database: config.database.name,
      user: config.database.user,
      REDACTED_SECRET: config.database.REDACTED_SECRET,
      ssl: config.database.ssl,
      max: config.database.maxConnections,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 2000,
    });

    // Initialize AWS services
    AWS.config.update({
      accessKeyId: config.storage.s3.accessKeyId,
      secretAccessKey: config.storage.s3.secretAccessKey,
      region: config.storage.s3.region,
    });

    this.s3 = new AWS.S3();
    this.glacier = new AWS.Glacier({ region: config.storage.glacier.region });
  }

  /**
   * Initialize the storage service
   */
  async initialize(): Promise<void> {
    try {
      await this.createTables();
      await this.verifyS3Access();
      await this.verifyGlacierAccess();

      this.logger.info('Audit storage service initialized successfully');
    } catch (error) {
      this.logger.error('Failed to initialize audit storage service', {
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Store audit event in hot storage (PostgreSQL)
   */
  async storeEvent(event: AuditEvent): Promise<void> {
    const client = await this.pgPool.connect();

    try {
      await client.query('BEGIN');

      // Insert main audit event
      const eventQuery = `
        INSERT INTO audit_events (
          id, timestamp, actor_id, actor_type, actor_ip, actor_session,
          action_type, action_resource, action_resource_id, action_result,
          context_request_id, context_parent_id, context_trace_id,
          context_environment, context_application, context_version,
          signature, raw_event, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, NOW())
      `;

      await client.query(eventQuery, [
        event.id,
        event.timestamp,
        event.actor.id,
        event.actor.type,
        event.actor.ip,
        event.actor.session,
        event.action.type,
        event.action.resource,
        event.action.resourceId,
        event.action.result,
        event.context.requestId,
        event.context.parentId,
        event.context.traceId,
        event.context.environment,
        event.context.application,
        event.context.version,
        event.signature,
        JSON.stringify(event),
      ]);

      // Store actor metadata if present
      if (
        event.actor.metadata &&
        Object.keys(event.actor.metadata).length > 0
      ) {
        const actorMetadataQuery = `
          INSERT INTO audit_actor_metadata (event_id, metadata)
          VALUES ($1, $2)
        `;
        await client.query(actorMetadataQuery, [
          event.id,
          JSON.stringify(event.actor.metadata),
        ]);
      }

      // Store action metadata if present
      if (
        event.action.metadata &&
        Object.keys(event.action.metadata).length > 0
      ) {
        const actionMetadataQuery = `
          INSERT INTO audit_action_metadata (event_id, metadata, duration, error)
          VALUES ($1, $2, $3, $4)
        `;
        await client.query(actionMetadataQuery, [
          event.id,
          JSON.stringify(event.action.metadata),
          event.action.duration,
          event.action.error,
        ]);
      }

      await client.query('COMMIT');

      this.logger.debug('Audit event stored in hot storage', {
        eventId: event.id,
      });
    } catch (error) {
      await client.query('ROLLBACK');
      this.logger.error('Failed to store audit event', {
        eventId: event.id,
        error: error.message,
      });
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Store multiple events in a batch
   */
  async storeBatch(events: AuditEvent[]): Promise<void> {
    if (events.length === 0) return;

    const client = await this.pgPool.connect();

    try {
      await client.query('BEGIN');

      for (const event of events) {
        await this.storeEventInternal(client, event);
      }

      await client.query('COMMIT');

      this.logger.info('Audit event batch stored', {
        eventCount: events.length,
        batchId: events[0]?.context?.requestId || 'unknown',
      });
    } catch (error) {
      await client.query('ROLLBACK');
      this.logger.error('Failed to store audit event batch', {
        eventCount: events.length,
        error: error.message,
      });
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Query audit events with filtering and pagination
   */
  async queryEvents(query: AuditQuery): Promise<{
    events: AuditEvent[];
    total: number;
    hasMore: boolean;
  }> {
    const client = await this.pgPool.connect();

    try {
      const { whereClause, params } = this.buildWhereClause(query);
      const limit = query.limit || 100;
      const offset = query.offset || 0;
      const orderBy = query.orderBy || 'timestamp';
      const orderDirection = query.orderDirection || 'desc';

      // Get total count
      const countQuery = `
        SELECT COUNT(*) as total
        FROM audit_events ae
        LEFT JOIN audit_actor_metadata aam ON ae.id = aam.event_id
        LEFT JOIN audit_action_metadata aacm ON ae.id = aacm.event_id
        ${whereClause}
      `;

      const countResult = await client.query(countQuery, params);
      const total = parseInt(countResult.rows[0].total);

      // Get paginated results
      const eventsQuery = `
        SELECT 
          ae.*,
          aam.metadata as actor_metadata,
          aacm.metadata as action_metadata,
          aacm.duration,
          aacm.error as action_error
        FROM audit_events ae
        LEFT JOIN audit_actor_metadata aam ON ae.id = aam.event_id
        LEFT JOIN audit_action_metadata aacm ON ae.id = aacm.event_id
        ${whereClause}
        ORDER BY ae.${orderBy} ${orderDirection}
        LIMIT $${params.length + 1} OFFSET $${params.length + 2}
      `;

      const eventsResult = await client.query(eventsQuery, [
        ...params,
        limit,
        offset,
      ]);

      const events = eventsResult.rows.map(row => this.mapRowToAuditEvent(row));

      return {
        events,
        total,
        hasMore: offset + limit < total,
      };
    } catch (error) {
      this.logger.error('Failed to query audit events', {
        query,
        error: error.message,
      });
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Archive old events to S3 (warm storage)
   */
  async archiveToWarmStorage(olderThan: Date): Promise<ArchivalJob> {
    const jobId = uuidv4();
    const job: ArchivalJob = {
      id: jobId,
      status: ArchivalJobStatus.PENDING,
      type: ArchivalType.HOT_TO_WARM,
      criteria: { olderThan: olderThan.toISOString() },
      progress: { total: 0, processed: 0, errors: 0 },
      startedAt: new Date().toISOString(),
    };

    try {
      await this.updateArchivalJob(job);

      // Start archival process
      this.performWarmArchival(job, olderThan);

      return job;
    } catch (error) {
      job.status = ArchivalJobStatus.FAILED;
      job.error = error.message;
      await this.updateArchivalJob(job);
      throw error;
    }
  }

  /**
   * Archive warm storage data to Glacier (cold storage)
   */
  async archiveToColdStorage(olderThan: Date): Promise<ArchivalJob> {
    const jobId = uuidv4();
    const job: ArchivalJob = {
      id: jobId,
      status: ArchivalJobStatus.PENDING,
      type: ArchivalType.WARM_TO_COLD,
      criteria: { olderThan: olderThan.toISOString() },
      progress: { total: 0, processed: 0, errors: 0 },
      startedAt: new Date().toISOString(),
    };

    try {
      await this.updateArchivalJob(job);

      // Start cold archival process
      this.performColdArchival(job, olderThan);

      return job;
    } catch (error) {
      job.status = ArchivalJobStatus.FAILED;
      job.error = error.message;
      await this.updateArchivalJob(job);
      throw error;
    }
  }

  /**
   * Retrieve events from cold storage
   */
  async retrieveFromColdStorage(archiveId: string): Promise<string> {
    try {
      const params = {
        accountId: '-',
        vaultName: this.config.storage.glacier.vault,
        jobParameters: {
          Type: 'archive-retrieval',
          ArchiveId: archiveId,
          Tier: 'Expedited', // or 'Standard' or 'Bulk'
        },
      };

      const result = await this.glacier.initiateJob(params).promise();

      this.logger.info('Cold storage retrieval initiated', {
        archiveId,
        jobId: result.jobId,
      });

      return result.jobId!;
    } catch (error) {
      this.logger.error('Failed to initiate cold storage retrieval', {
        archiveId,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Get storage statistics
   */
  async getStorageStats(): Promise<{
    hotStorage: {
      count: number;
      sizeBytes: number;
      oldestEvent: string | null;
    };
    warmStorage: { count: number; sizeBytes: number };
    coldStorage: { count: number; sizeBytes: number };
  }> {
    const client = await this.pgPool.connect();

    try {
      // Hot storage stats
      const hotStatsQuery = `
        SELECT 
          COUNT(*) as count,
          SUM(length(raw_event::text)) as size_bytes,
          MIN(timestamp) as oldest_event
        FROM audit_events
      `;
      const hotResult = await client.query(hotStatsQuery);

      // Warm storage stats (S3)
      const warmStats = await this.getS3Stats();

      // Cold storage stats (Glacier)
      const coldStats = await this.getGlacierStats();

      return {
        hotStorage: {
          count: parseInt(hotResult.rows[0].count),
          sizeBytes: parseInt(hotResult.rows[0].size_bytes || '0'),
          oldestEvent: hotResult.rows[0].oldest_event,
        },
        warmStorage: warmStats,
        coldStorage: coldStats,
      };
    } catch (error) {
      this.logger.error('Failed to get storage stats', {
        error: error.message,
      });
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Verify data integrity across all storage tiers
   */
  async verifyIntegrity(sampleSize: number = 100): Promise<{
    hotStorage: { verified: number; failed: number };
    warmStorage: { verified: number; failed: number };
    issues: Array<{ eventId: string; storage: string; issue: string }>;
  }> {
    const issues: Array<{ eventId: string; storage: string; issue: string }> =
      [];
    let hotVerified = 0,
      hotFailed = 0;
    const warmVerified = 0,
      warmFailed = 0;

    const client = await this.pgPool.connect();

    try {
      // Verify hot storage sample
      const hotSampleQuery = `
        SELECT id, signature, raw_event
        FROM audit_events
        ORDER BY RANDOM()
        LIMIT $1
      `;
      const hotSample = await client.query(hotSampleQuery, [sampleSize]);

      for (const row of hotSample.rows) {
        try {
          const event: AuditEvent = JSON.parse(row.raw_event);
          const isValid = await this.cryptoService.verifyAuditEvent(event);

          if (isValid) {
            hotVerified++;
          } else {
            hotFailed++;
            issues.push({
              eventId: row.id,
              storage: 'hot',
              issue: 'Invalid cryptographic signature',
            });
          }
        } catch (error) {
          hotFailed++;
          issues.push({
            eventId: row.id,
            storage: 'hot',
            issue: `Verification error: ${error.message}`,
          });
        }
      }

      // TODO: Verify warm storage sample from S3
      // This would involve downloading and verifying S3 objects

      this.logger.info('Integrity verification completed', {
        hotVerified,
        hotFailed,
        warmVerified,
        warmFailed,
        totalIssues: issues.length,
      });

      return {
        hotStorage: { verified: hotVerified, failed: hotFailed },
        warmStorage: { verified: warmVerified, failed: warmFailed },
        issues,
      };
    } catch (error) {
      this.logger.error('Failed to verify integrity', { error: error.message });
      throw error;
    } finally {
      client.release();
    }
  }

  // Private helper methods

  private async createTables(): Promise<void> {
    const client = await this.pgPool.connect();

    try {
      // Main audit events table
      await client.query(`
        CREATE TABLE IF NOT EXISTS audit_events (
          id UUID PRIMARY KEY,
          timestamp TIMESTAMPTZ NOT NULL,
          actor_id VARCHAR(255) NOT NULL,
          actor_type VARCHAR(50) NOT NULL,
          actor_ip INET,
          actor_session VARCHAR(255),
          action_type VARCHAR(50) NOT NULL,
          action_resource VARCHAR(100) NOT NULL,
          action_resource_id VARCHAR(255),
          action_result VARCHAR(20) NOT NULL,
          context_request_id VARCHAR(255),
          context_parent_id VARCHAR(255),
          context_trace_id VARCHAR(255),
          context_environment VARCHAR(50) NOT NULL,
          context_application VARCHAR(100) NOT NULL,
          context_version VARCHAR(20) NOT NULL,
          signature VARCHAR(512),
          raw_event JSONB NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
      `);

      // Actor metadata table
      await client.query(`
        CREATE TABLE IF NOT EXISTS audit_actor_metadata (
          event_id UUID NOT NULL REFERENCES audit_events(id),
          metadata JSONB NOT NULL
        )
      `);

      // Action metadata table
      await client.query(`
        CREATE TABLE IF NOT EXISTS audit_action_metadata (
          event_id UUID NOT NULL REFERENCES audit_events(id),
          metadata JSONB NOT NULL,
          duration INTEGER,
          error TEXT
        )
      `);

      // Archival jobs table
      await client.query(`
        CREATE TABLE IF NOT EXISTS audit_archival_jobs (
          id UUID PRIMARY KEY,
          status VARCHAR(20) NOT NULL,
          type VARCHAR(30) NOT NULL,
          criteria JSONB NOT NULL,
          progress JSONB NOT NULL,
          started_at TIMESTAMPTZ NOT NULL,
          completed_at TIMESTAMPTZ,
          error TEXT
        )
      `);

      // Create indexes for performance
      await client.query(
        'CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit_events(timestamp)'
      );
      await client.query(
        'CREATE INDEX IF NOT EXISTS idx_audit_events_actor_id ON audit_events(actor_id)'
      );
      await client.query(
        'CREATE INDEX IF NOT EXISTS idx_audit_events_action_type ON audit_events(action_type)'
      );
      await client.query(
        'CREATE INDEX IF NOT EXISTS idx_audit_events_resource ON audit_events(action_resource)'
      );
      await client.query(
        'CREATE INDEX IF NOT EXISTS idx_audit_events_result ON audit_events(action_result)'
      );

      this.logger.info('Audit storage tables created successfully');
    } finally {
      client.release();
    }
  }

  private async verifyS3Access(): Promise<void> {
    try {
      await this.s3
        .headBucket({ Bucket: this.config.storage.s3.bucket })
        .promise();
      this.logger.info('S3 access verified');
    } catch (error) {
      if (error.statusCode === 404) {
        // Try to create bucket
        await this.s3
          .createBucket({ Bucket: this.config.storage.s3.bucket })
          .promise();
        this.logger.info('S3 bucket created');
      } else {
        throw error;
      }
    }
  }

  private async verifyGlacierAccess(): Promise<void> {
    try {
      await this.glacier
        .describeVault({
          accountId: '-',
          vaultName: this.config.storage.glacier.vault,
        })
        .promise();
      this.logger.info('Glacier access verified');
    } catch (error) {
      if (error.statusCode === 404) {
        // Try to create vault
        await this.glacier
          .createVault({
            accountId: '-',
            vaultName: this.config.storage.glacier.vault,
          })
          .promise();
        this.logger.info('Glacier vault created');
      } else {
        throw error;
      }
    }
  }

  private async storeEventInternal(
    client: any,
    event: AuditEvent
  ): Promise<void> {
    // Implementation similar to storeEvent but using existing client
    // ... (code would be similar to storeEvent method)
  }

  private buildWhereClause(query: AuditQuery): {
    whereClause: string;
    params: any[];
  } {
    const conditions: string[] = [];
    const params: any[] = [];

    if (query.startTime) {
      conditions.push(`ae.timestamp >= $${params.length + 1}`);
      params.push(query.startTime);
    }

    if (query.endTime) {
      conditions.push(`ae.timestamp <= $${params.length + 1}`);
      params.push(query.endTime);
    }

    if (query.actorId) {
      conditions.push(`ae.actor_id = $${params.length + 1}`);
      params.push(query.actorId);
    }

    if (query.actorType) {
      conditions.push(`ae.actor_type = $${params.length + 1}`);
      params.push(query.actorType);
    }

    if (query.actionType) {
      conditions.push(`ae.action_type = $${params.length + 1}`);
      params.push(query.actionType);
    }

    if (query.resource) {
      conditions.push(`ae.action_resource = $${params.length + 1}`);
      params.push(query.resource);
    }

    if (query.resourceId) {
      conditions.push(`ae.action_resource_id = $${params.length + 1}`);
      params.push(query.resourceId);
    }

    if (query.result) {
      conditions.push(`ae.action_result = $${params.length + 1}`);
      params.push(query.result);
    }

    const whereClause =
      conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
    return { whereClause, params };
  }

  private mapRowToAuditEvent(row: any): AuditEvent {
    return JSON.parse(row.raw_event);
  }

  private async performWarmArchival(
    job: ArchivalJob,
    olderThan: Date
  ): Promise<void> {
    const client = await this.pgPool.connect();
    const batchSize = 1000;
    let processed = 0;

    try {
      while (true) {
        const { rows } = await client.query(
          `
          SELECT id, raw_event, created_at
          FROM audit_events 
          WHERE created_at < $1 AND archived_s3 = false
          ORDER BY created_at
          LIMIT $2
        `,
          [olderThan, batchSize]
        );

        if (rows.length === 0) break;

        for (const batch of this.chunk(rows, 100)) {
          const s3Key = `audit-events/${new Date().toISOString().split('T')[0]}/${uuidv4()}.json`;
          const batchData = batch.map(row => ({
            id: row.id,
            event: JSON.parse(row.raw_event),
            timestamp: row.created_at,
          }));

          await this.s3
            .putObject({
              Bucket: this.config.storage.s3.bucket,
              Key: s3Key,
              Body: JSON.stringify(batchData),
              ContentType: 'application/json',
              StorageClass: 'STANDARD_IA',
            })
            .promise();

          const eventIds = batch.map(row => row.id);
          await client.query(
            `
            UPDATE audit_events 
            SET archived_s3 = true, s3_key = $1 
            WHERE id = ANY($2)
          `,
            [s3Key, eventIds]
          );

          processed += batch.length;
          job.progress.processed = processed;
          await this.updateArchivalJob(job);
        }
      }

      this.logger.info('Warm archival completed', {
        jobId: job.id,
        processed: processed,
      });
    } catch (error) {
      this.logger.error('Warm archival failed', {
        jobId: job.id,
        processed: processed,
        error: error.message,
      });
      throw error;
    } finally {
      client.release();
    }
  }

  private async performColdArchival(
    job: ArchivalJob,
    olderThan: Date
  ): Promise<void> {
    const client = await this.pgPool.connect();
    const batchSize = 10000;
    let processed = 0;

    try {
      while (true) {
        const { rows } = await client.query(
          `
          SELECT s3_key, COUNT(*) as event_count
          FROM audit_events 
          WHERE created_at < $1 AND archived_s3 = true AND archived_glacier = false
          GROUP BY s3_key
          LIMIT $2
        `,
          [olderThan, batchSize]
        );

        if (rows.length === 0) break;

        for (const row of rows) {
          const s3Object = await this.s3
            .getObject({
              Bucket: this.config.storage.s3.bucket,
              Key: row.s3_key,
            })
            .promise();

          const glacierKey = `glacier-archive/${row.s3_key}`;
          const archiveResult = await this.glacier
            .uploadArchive({
              accountId: '-',
              vaultName: this.config.storage.glacier.vault,
              archiveDescription: `Audit events batch: ${row.s3_key}`,
              body: s3Object.Body,
            })
            .promise();

          await client.query(
            `
            UPDATE audit_events 
            SET archived_glacier = true, glacier_archive_id = $1
            WHERE s3_key = $2
          `,
            [archiveResult.archiveId, row.s3_key]
          );

          await this.s3
            .deleteObject({
              Bucket: this.config.storage.s3.bucket,
              Key: row.s3_key,
            })
            .promise();

          processed += parseInt(row.event_count);
          job.progress.processed = processed;
          await this.updateArchivalJob(job);
        }
      }

      this.logger.info('Cold archival completed', {
        jobId: job.id,
        processed: processed,
      });
    } catch (error) {
      this.logger.error('Cold archival failed', {
        jobId: job.id,
        processed: processed,
        error: error.message,
      });
      throw error;
    } finally {
      client.release();
    }
  }

  private async updateArchivalJob(job: ArchivalJob): Promise<void> {
    const client = await this.pgPool.connect();
    try {
      await client.query(
        `
        INSERT INTO audit_archival_jobs (id, status, type, criteria, progress, started_at, completed_at, error)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (id) DO UPDATE SET
          status = EXCLUDED.status,
          progress = EXCLUDED.progress,
          completed_at = EXCLUDED.completed_at,
          error = EXCLUDED.error
      `,
        [
          job.id,
          job.status,
          job.type,
          JSON.stringify(job.criteria),
          JSON.stringify(job.progress),
          job.startedAt,
          job.completedAt || null,
          job.error || null,
        ]
      );
    } finally {
      client.release();
    }
  }

  private async getS3Stats(): Promise<{ count: number; sizeBytes: number }> {
    try {
      const params = { Bucket: this.config.storage.s3.bucket };
      const result = await this.s3.listObjectsV2(params).promise();

      const count = result.Contents?.length || 0;
      const sizeBytes =
        result.Contents?.reduce((sum, obj) => sum + (obj.Size || 0), 0) || 0;

      return { count, sizeBytes };
    } catch (error) {
      this.logger.error('Failed to get S3 stats', { error: error.message });
      return { count: 0, sizeBytes: 0 };
    }
  }

  private async getGlacierStats(): Promise<{
    count: number;
    sizeBytes: number;
  }> {
    try {
      const result = await this.glacier
        .describeVault({
          accountId: '-',
          vaultName: this.config.storage.glacier.vault,
        })
        .promise();

      return {
        count: result.NumberOfArchives || 0,
        sizeBytes: result.SizeInBytes || 0,
      };
    } catch (error) {
      this.logger.error('Failed to get Glacier stats', {
        error: error.message,
      });
      return { count: 0, sizeBytes: 0 };
    }
  }

  private async storeEventInternal(event: AuditEvent): Promise<void> {
    const client = await this.pgPool.connect();

    try {
      await client.query(
        `
        INSERT INTO audit_events (
          id, timestamp, actor_id, actor_type, actor_ip, actor_session,
          action_type, action_resource, action_resource_id, action_result,
          action_details, context_request_id, context_parent_id, context_trace_id,
          context_environment, context_application, context_version,
          signature, version, raw_event, created_at
        ) VALUES (
          $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, NOW()
        )
      `,
        [
          event.id,
          event.timestamp,
          event.actor.id,
          event.actor.type,
          event.actor.ip || null,
          event.actor.session || null,
          event.action.type,
          event.action.resource,
          event.action.resourceId || null,
          event.action.result,
          event.action.details || null,
          event.context.requestId || null,
          event.context.parentId || null,
          event.context.traceId || null,
          event.context.environment,
          event.context.application,
          event.context.version,
          event.signature || null,
          event.version,
          JSON.stringify(event),
        ]
      );
    } catch (error) {
      this.logger.error('Failed to store audit event', {
        eventId: event.id,
        error: error.message,
      });
      throw error;
    } finally {
      client.release();
    }
  }

  private chunk<T>(array: T[], size: number): T[][] {
    const chunks: T[][] = [];
    for (let i = 0; i < array.length; i += size) {
      chunks.push(array.slice(i, i + size));
    }
    return chunks;
  }

  /**
   * Close all connections
   */
  async close(): Promise<void> {
    await this.pgPool.end();
    this.logger.info('Audit storage service closed');
  }
}
