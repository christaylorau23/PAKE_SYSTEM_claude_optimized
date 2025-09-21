/**
 * PAKE System - Trend Record Ingest Pipeline
 *
 * Comprehensive pipeline for ingesting, validating, deduplicating, and storing
 * trend records with anomaly detection and entity extraction.
 */

import { createHash } from 'crypto';
import Ajv from 'ajv';
import addFormats from 'ajv-formats';
import { EventEmitter } from 'events';
import { TrendRepository } from './store/TrendRepository';
import {
  TrendRecord,
  TrendEntity,
  EntityType,
  AnomalyDetection,
  AnomalyFlag,
  IngestResult,
  IngestMetrics,
  ProcessingConfig,
  QualityThresholds,
  TrendValidationResult,
} from './types/TrendRecord';
import { createLogger, Logger } from '../../orchestrator/src/utils/logger';
import { metrics } from '../../orchestrator/src/utils/metrics';
import { outputSanitizer } from '../../security/OutputSanitizer';

// Internal processing interfaces
interface IngestStats {
  totalProcessed: number;
  successfulIngests: number;
  duplicatesSkipped: number;
  validationFailures: number;
  rejections: number;
  averageProcessingTime: number;
  anomaliesDetected: number;
  entitiesExtracted: number;
}

/**
 * Main trend record ingest pipeline
 */
export class TrendIngestPipeline extends EventEmitter {
  private readonly logger: Logger;
  private readonly repository: TrendRepository;
  private readonly validator: Ajv;
  private readonly stats: IngestStats;

  // Deduplication tracking
  private readonly recentHashes = new Map<
    string,
    { id: string; timestamp: number }
  >();
  private readonly hashCleanupInterval: NodeJS.Timeout;

  // Anomaly detection parameters
  private readonly anomalyThresholds = {
    unusualVelocity: 10.0, // 10x normal growth rate
    suspiciousEngagement: 0.95, // 95th percentile
    viralitySpike: 0.8, // 80% virality threshold
    credibilityDrop: 0.3, // Below 30% credibility
  };

  constructor(repository: TrendRepository) {
    super();

    this.logger = createLogger('TrendIngestPipeline');
    this.repository = repository;

    // Initialize JSON Schema validator
    this.validator = new Ajv({ allErrors: true, verbose: true });
    addFormats(this.validator);

    // Load TrendRecord schema
    this.validator.addSchema(this.getTrendRecordSchema(), 'TrendRecord');

    this.stats = {
      totalProcessed: 0,
      successfulIngests: 0,
      duplicatesSkipped: 0,
      validationFailures: 0,
      rejections: 0,
      averageProcessingTime: 0,
      anomaliesDetected: 0,
      entitiesExtracted: 0,
    };

    // Clean up old hashes every hour
    this.hashCleanupInterval = setInterval(
      () => {
        this.cleanupOldHashes();
      },
      60 * 60 * 1000
    );

    this.logger.info('TrendIngestPipeline initialized');
  }

  /**
   * Ingest a single trend record
   */
  async ingest(rawRecord: Partial<TrendRecord>): Promise<IngestResult> {
    const startTime = Date.now();
    const recordId = rawRecord.id || this.generateRecordId();

    this.logger.debug('Starting trend record ingest', {
      recordId,
      topic: rawRecord.topic,
      source: rawRecord.source?.platform,
    });

    this.stats.totalProcessed++;

    try {
      // 1. Sanitize input data
      const sanitizedRecord = outputSanitizer.sanitize(
        rawRecord,
        'trend-ingest'
      ) as Partial<TrendRecord>;

      // 2. Validate record structure
      const validationStart = Date.now();
      const validationResult = this.validateRecord(sanitizedRecord);
      const validationTime = Date.now() - validationStart;

      if (!validationResult.valid) {
        this.stats.validationFailures++;

        this.logger.warn('Record validation failed', {
          recordId,
          errors: validationResult.errors,
        });

        return {
          id: recordId,
          status: 'invalid',
          validationErrors: validationResult.errors,
          metrics: {
            processingTime: Date.now() - startTime,
            validationTime,
            deduplicationTime: 0,
            storageTime: 0,
          },
        };
      }

      // 3. Normalize and enrich the record
      const normalizedRecord = await this.normalizeRecord(
        sanitizedRecord as TrendRecord
      );

      // 4. Check for duplicates
      const deduplicationStart = Date.now();
      const duplicateCheck = await this.checkDuplicates(normalizedRecord);
      const deduplicationTime = Date.now() - deduplicationStart;

      if (duplicateCheck.isDuplicate) {
        this.stats.duplicatesSkipped++;

        this.logger.debug('Duplicate record detected', {
          recordId,
          duplicateOf: duplicateCheck.existingId,
          similarityScore: duplicateCheck.similarityScore,
        });

        return {
          id: recordId,
          status: 'duplicate',
          duplicateOf: duplicateCheck.existingId,
          metrics: {
            processingTime: Date.now() - startTime,
            validationTime,
            deduplicationTime,
            storageTime: 0,
          },
        };
      }

      // 5. Detect anomalies
      const anomalies = await this.detectAnomalies(normalizedRecord);
      normalizedRecord.metadata.anomalyFlags = anomalies;

      if (anomalies.length > 0) {
        this.stats.anomaliesDetected += anomalies.length;

        this.logger.info('Anomalies detected in record', {
          recordId,
          anomalies: anomalies.map(a => ({
            type: a.type,
            severity: a.severity,
          })),
        });
      }

      // 6. Final quality check
      const qualityCheck = this.performQualityCheck(normalizedRecord);
      if (!qualityCheck.passed) {
        this.stats.rejections++;

        this.logger.warn('Record rejected by quality check', {
          recordId,
          reason: qualityCheck.reason,
          score: qualityCheck.score,
        });

        return {
          id: recordId,
          status: 'rejected',
          rejectionReason: qualityCheck.reason,
          metrics: {
            processingTime: Date.now() - startTime,
            validationTime,
            deduplicationTime,
            storageTime: 0,
          },
        };
      }

      // 7. Store the record
      const storageStart = Date.now();
      await this.repository.store(normalizedRecord);
      const storageTime = Date.now() - storageStart;

      // 8. Update tracking
      this.updateHashTracking(normalizedRecord);
      this.stats.successfulIngests++;
      this.stats.entitiesExtracted += normalizedRecord.entities.length;

      const processingTime = Date.now() - startTime;
      this.updateProcessingTimeMetrics(processingTime);

      this.logger.info('Trend record ingested successfully', {
        recordId,
        topic: normalizedRecord.topic,
        entitiesCount: normalizedRecord.entities.length,
        anomaliesCount: anomalies.length,
        processingTime,
      });

      // Emit events for monitoring
      this.emit('record:ingested', {
        record: normalizedRecord,
        processingTime,
        anomalies: anomalies.length,
      });

      // Track metrics
      metrics.counter('trend_records_ingested', {
        topic: normalizedRecord.topic,
        source: normalizedRecord.source.platform,
        has_anomalies: (anomalies.length > 0).toString(),
      });

      return {
        id: recordId,
        status: 'ingested',
        record: normalizedRecord,
        metrics: {
          processingTime,
          validationTime,
          deduplicationTime,
          storageTime,
        },
      };
    } catch (error) {
      this.stats.rejections++;

      this.logger.error('Trend record ingest failed', {
        recordId,
        error: (error as Error).message,
        stack: (error as Error).stack,
      });

      this.emit('record:failed', {
        recordId,
        error: error as Error,
      });

      return {
        id: recordId,
        status: 'rejected',
        rejectionReason: `Processing error: ${(error as Error).message}`,
        metrics: {
          processingTime: Date.now() - startTime,
          validationTime: 0,
          deduplicationTime: 0,
          storageTime: 0,
        },
      };
    }
  }

  /**
   * Batch ingest multiple records
   */
  async ingestBatch(records: Partial<TrendRecord>[]): Promise<IngestResult[]> {
    const startTime = Date.now();

    this.logger.info('Starting batch ingest', {
      recordCount: records.length,
    });

    const results: IngestResult[] = [];
    const batchSize = 10; // Process in smaller batches to manage memory

    for (let i = 0; i < records.length; i += batchSize) {
      const batch = records.slice(i, i + batchSize);

      const batchPromises = batch.map(record => this.ingest(record));
      const batchResults = await Promise.allSettled(batchPromises);

      for (const result of batchResults) {
        if (result.status === 'fulfilled') {
          results.push(result.value);
        } else {
          this.logger.error('Batch ingest item failed', {
            error: result.reason,
          });

          results.push({
            id: 'batch-error',
            status: 'rejected',
            rejectionReason: result.reason.message,
            metrics: {
              processingTime: 0,
              validationTime: 0,
              deduplicationTime: 0,
              storageTime: 0,
            },
          });
        }
      }
    }

    const processingTime = Date.now() - startTime;

    this.logger.info('Batch ingest completed', {
      totalRecords: records.length,
      successful: results.filter(r => r.status === 'ingested').length,
      duplicates: results.filter(r => r.status === 'duplicate').length,
      invalid: results.filter(r => r.status === 'invalid').length,
      rejected: results.filter(r => r.status === 'rejected').length,
      processingTime,
    });

    return results;
  }

  /**
   * Validate record against JSON schema
   */
  private validateRecord(record: Partial<TrendRecord>): {
    valid: boolean;
    errors: string[];
  } {
    const validate = this.validator.getSchema('TrendRecord');
    if (!validate) {
      return { valid: false, errors: ['Schema not found'] };
    }

    const valid = validate(record);

    if (valid) {
      return { valid: true, errors: [] };
    }

    const errors = validate.errors?.map(error => {
      return `${error.instancePath || 'root'}: ${error.message}`;
    }) || ['Unknown validation error'];

    return { valid: false, errors };
  }

  /**
   * Normalize and enrich record
   */
  private async normalizeRecord(record: TrendRecord): Promise<TrendRecord> {
    const now = new Date().toISOString();

    // Ensure UTC timestamps
    const timestamp = this.normalizeTimestamp(record.timestamp);

    // Generate content hashes for deduplication
    const contentHash = this.generateContentHash(record);
    const similarityHash = this.generateSimilarityHash(record);

    // Normalize source information
    const normalizedSource = {
      ...record.source,
      reliability: Math.max(0, Math.min(1, record.source.reliability || 0.5)),
    };

    // Ensure metadata structure
    const metadata = {
      ingestionTime: now,
      processingVersion: '1.0.0',
      confidence: Math.max(0, Math.min(1, record.metadata?.confidence || 0.8)),
      tags: Array.from(new Set(record.metadata?.tags || [])), // Remove duplicates
      anomalyFlags: record.metadata?.anomalyFlags || [],
    };

    // Normalize entities
    const entities = await this.normalizeEntities(record.entities || []);

    return {
      ...record,
      id: record.id || this.generateRecordId(),
      timestamp,
      contentHash,
      similarityHash,
      source: normalizedSource,
      metadata,
      entities,
    };
  }

  /**
   * Normalize timestamp to UTC
   */
  private normalizeTimestamp(timestamp: string): string {
    try {
      const date = new Date(timestamp);
      if (isNaN(date.getTime())) {
        throw new Error('Invalid date');
      }
      return date.toISOString();
    } catch {
      // Fallback to current time
      this.logger.warn('Invalid timestamp, using current time', { timestamp });
      return new Date().toISOString();
    }
  }

  /**
   * Generate content hash for exact duplicate detection
   */
  private generateContentHash(record: TrendRecord): string {
    const content = {
      title: record.content.title.toLowerCase().trim(),
      summary: record.content.summary.toLowerCase().trim(),
      source: record.source.platform + ':' + record.source.sourceId,
    };

    return createHash('sha256').update(JSON.stringify(content)).digest('hex');
  }

  /**
   * Generate similarity hash for near-duplicate detection
   */
  private generateSimilarityHash(record: TrendRecord): string {
    // Use first 100 chars of title + summary for similarity matching
    const text = (record.content.title + ' ' + record.content.summary)
      .toLowerCase()
      .replace(/[^\w\s]/g, '') // Remove punctuation
      .replace(/\s+/g, ' ') // Normalize whitespace
      .substring(0, 100);

    return createHash('md5').update(text).digest('hex');
  }

  /**
   * Normalize entities and extract additional information
   */
  private async normalizeEntities(
    entities: TrendEntity[]
  ): Promise<TrendEntity[]> {
    const normalized: TrendEntity[] = [];
    const entityMap = new Map<string, TrendEntity>();

    // Merge entities with same text but different cases/variations
    for (const entity of entities) {
      const normalizedText = entity.text.toLowerCase().trim();

      if (entityMap.has(normalizedText)) {
        const existing = entityMap.get(normalizedText)!;
        existing.mentions += entity.mentions || 1;
        existing.confidence = Math.max(existing.confidence, entity.confidence);
        existing.aliases = Array.from(
          new Set([...existing.aliases, ...entity.aliases, entity.text])
        );
      } else {
        entityMap.set(normalizedText, {
          ...entity,
          text: entity.text.trim(),
          mentions: entity.mentions || 1,
          aliases: [...(entity.aliases || []), entity.text],
          confidence: Math.max(0, Math.min(1, entity.confidence)),
        });
      }
    }

    return Array.from(entityMap.values());
  }

  /**
   * Check for duplicates
   */
  private async checkDuplicates(record: TrendRecord): Promise<{
    isDuplicate: boolean;
    existingId?: string;
    similarityScore?: number;
  }> {
    // Check exact duplicates first (content hash)
    const exactDuplicate = this.recentHashes.get(record.contentHash);
    if (exactDuplicate) {
      return {
        isDuplicate: true,
        existingId: exactDuplicate.id,
        similarityScore: 1.0,
      };
    }

    // Check database for exact duplicates
    const existingByHash = await this.repository.findByContentHash(
      record.contentHash
    );
    if (existingByHash) {
      return {
        isDuplicate: true,
        existingId: existingByHash.id,
        similarityScore: 1.0,
      };
    }

    // Check for similar records (similarity hash)
    const similarRecords = await this.repository.findBySimilarityHash(
      record.similarityHash
    );
    if (similarRecords.length > 0) {
      // Calculate more detailed similarity if needed
      const mostSimilar = similarRecords[0];
      const similarityScore = this.calculateSimilarity(record, mostSimilar);

      if (similarityScore > 0.8) {
        // 80% similarity threshold
        return {
          isDuplicate: true,
          existingId: mostSimilar.id,
          similarityScore,
        };
      }
    }

    return { isDuplicate: false };
  }

  /**
   * Calculate similarity between two records
   */
  private calculateSimilarity(
    record1: TrendRecord,
    record2: TrendRecord
  ): number {
    // Simple similarity calculation based on content overlap
    const text1 = (
      record1.content.title +
      ' ' +
      record1.content.summary
    ).toLowerCase();
    const text2 = (
      record2.content.title +
      ' ' +
      record2.content.summary
    ).toLowerCase();

    const words1 = new Set(text1.split(/\s+/));
    const words2 = new Set(text2.split(/\s+/));

    const intersection = new Set([...words1].filter(x => words2.has(x)));
    const union = new Set([...words1, ...words2]);

    return intersection.size / union.size; // Jaccard similarity
  }

  /**
   * Detect anomalies in the record
   */
  private async detectAnomalies(record: TrendRecord): Promise<AnomalyFlag[]> {
    const anomalies: AnomalyFlag[] = [];
    const now = new Date().toISOString();

    // Check for unusual velocity/growth
    if (
      record.metrics.velocity.growthRate >
      this.anomalyThresholds.unusualVelocity
    ) {
      anomalies.push({
        type: 'spike',
        severity: 'high',
        confidence: 0.9,
        description: `Unusual growth rate: ${record.metrics.velocity.growthRate}x`,
        detectedAt: now,
        parameters: { growthRate: record.metrics.velocity.growthRate },
      });
    }

    // Check for suspicious engagement patterns
    const engagement = record.metrics.engagement;
    const totalEngagement =
      (engagement.likes || 0) +
      (engagement.shares || 0) +
      (engagement.comments || 0);
    const views = engagement.views || 1;
    const engagementRate = totalEngagement / views;

    if (engagementRate > this.anomalyThresholds.suspiciousEngagement) {
      anomalies.push({
        type: 'unusual_pattern',
        severity: 'medium',
        confidence: 0.7,
        description: `Unusually high engagement rate: ${(engagementRate * 100).toFixed(1)}%`,
        detectedAt: now,
        parameters: {
          engagementRate,
          threshold: this.anomalyThresholds.suspiciousEngagement,
        },
      });
    }

    // Check for virality spike
    if (record.metrics.impact.virality > this.anomalyThresholds.viralitySpike) {
      anomalies.push({
        type: 'spike',
        severity: 'high',
        confidence: 0.85,
        description: `High virality detected: ${record.metrics.impact.virality}`,
        detectedAt: now,
        parameters: { virality: record.metrics.impact.virality },
      });
    }

    // Check for credibility issues
    if (
      record.metrics.impact.credibility < this.anomalyThresholds.credibilityDrop
    ) {
      anomalies.push({
        type: 'suspicious_source',
        severity: 'medium',
        confidence: 0.8,
        description: `Low credibility score: ${record.metrics.impact.credibility}`,
        detectedAt: now,
        parameters: { credibility: record.metrics.impact.credibility },
      });
    }

    // Check for coordinated behavior patterns
    const coordinationScore = this.detectCoordinatedBehavior(record);
    if (coordinationScore > 0.7) {
      anomalies.push({
        type: 'coordinated_behavior',
        severity: 'critical',
        confidence: coordinationScore,
        description: 'Potential coordinated behavior detected',
        detectedAt: now,
        parameters: { coordinationScore },
      });
    }

    return anomalies;
  }

  /**
   * Detect potential coordinated behavior
   */
  private detectCoordinatedBehavior(record: TrendRecord): number {
    let suspicionScore = 0;

    // Check for unusual timing patterns
    const recordTime = new Date(record.timestamp);
    const hour = recordTime.getUTCHours();

    // Posting during unusual hours might indicate automation
    if (hour >= 2 && hour <= 5) {
      suspicionScore += 0.2;
    }

    // Check for repetitive content patterns
    const repetitiveWords = this.detectRepetitiveContent(
      record.content.title + ' ' + record.content.summary
    );
    if (repetitiveWords > 0.3) {
      suspicionScore += 0.3;
    }

    // Check for suspicious entity patterns
    const entityTypes = record.entities.map(e => e.type);
    const uniqueTypes = new Set(entityTypes);
    if (entityTypes.length > 0 && uniqueTypes.size / entityTypes.length < 0.5) {
      suspicionScore += 0.2;
    }

    return Math.min(1, suspicionScore);
  }

  /**
   * Detect repetitive content patterns
   */
  private detectRepetitiveContent(text: string): number {
    const words = text.toLowerCase().split(/\s+/);
    const wordCount = new Map<string, number>();

    for (const word of words) {
      wordCount.set(word, (wordCount.get(word) || 0) + 1);
    }

    const totalWords = words.length;
    let repetitiveWords = 0;

    for (const [word, count] of wordCount) {
      if (count > 3 && word.length > 3) {
        // Word appears more than 3 times
        repetitiveWords += count;
      }
    }

    return repetitiveWords / totalWords;
  }

  /**
   * Perform final quality check
   */
  private performQualityCheck(record: TrendRecord): {
    passed: boolean;
    score: number;
    reason?: string;
  } {
    let qualityScore = 0.5; // Base score

    // Content quality checks
    if (record.content.title.length > 10) qualityScore += 0.1;
    if (record.content.summary.length > 50) qualityScore += 0.1;
    if (record.content.keywords.length > 0) qualityScore += 0.1;

    // Source reliability
    qualityScore += record.source.reliability * 0.2;

    // Entity extraction quality
    if (record.entities.length > 0) qualityScore += 0.1;

    // Confidence factors
    qualityScore += record.metadata.confidence * 0.1;

    // Anomaly penalty
    const criticalAnomalies = record.metadata.anomalyFlags.filter(
      a => a.severity === 'critical'
    );
    if (criticalAnomalies.length > 0) {
      qualityScore -= 0.3;
    }

    qualityScore = Math.max(0, Math.min(1, qualityScore));

    // Minimum quality threshold
    if (qualityScore < 0.3) {
      return {
        passed: false,
        score: qualityScore,
        reason: `Quality score too low: ${qualityScore.toFixed(2)}`,
      };
    }

    // Check for critical anomalies
    if (criticalAnomalies.length > 0) {
      return {
        passed: false,
        score: qualityScore,
        reason: `Critical anomalies detected: ${criticalAnomalies.map(a => a.type).join(', ')}`,
      };
    }

    return { passed: true, score: qualityScore };
  }

  /**
   * Update hash tracking for deduplication
   */
  private updateHashTracking(record: TrendRecord): void {
    const now = Date.now();

    // Store hash for recent lookup
    this.recentHashes.set(record.contentHash, {
      id: record.id,
      timestamp: now,
    });

    // Also store similarity hash
    this.recentHashes.set(record.similarityHash, {
      id: record.id,
      timestamp: now,
    });
  }

  /**
   * Clean up old hashes from memory
   */
  private cleanupOldHashes(): void {
    const now = Date.now();
    const maxAge = 24 * 60 * 60 * 1000; // 24 hours
    let cleanedCount = 0;

    for (const [hash, data] of this.recentHashes) {
      if (now - data.timestamp > maxAge) {
        this.recentHashes.delete(hash);
        cleanedCount++;
      }
    }

    if (cleanedCount > 0) {
      this.logger.debug(`Cleaned up ${cleanedCount} old hashes from memory`);
    }
  }

  /**
   * Update processing time metrics
   */
  private updateProcessingTimeMetrics(processingTime: number): void {
    const totalProcessed = this.stats.totalProcessed;
    this.stats.averageProcessingTime =
      (this.stats.averageProcessingTime * (totalProcessed - 1) +
        processingTime) /
      totalProcessed;
  }

  /**
   * Generate unique record ID
   */
  private generateRecordId(): string {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substring(2, 8);
    return `tr_${timestamp}_${random}`;
  }

  /**
   * Get TrendRecord JSON schema
   */
  private getTrendRecordSchema(): any {
    // This would typically be loaded from the JSON schema files created in Phase A
    return {
      type: 'object',
      required: [
        'id',
        'timestamp',
        'topic',
        'content',
        'sentiment',
        'entities',
        'metrics',
        'source',
        'metadata',
      ],
      properties: {
        id: { type: 'string', pattern: '^tr_[a-z0-9_]+$' },
        timestamp: { type: 'string', format: 'date-time' },
        topic: { type: 'string', minLength: 1, maxLength: 200 },
        content: {
          type: 'object',
          required: ['title', 'summary', 'language', 'keywords'],
          properties: {
            title: { type: 'string', minLength: 1, maxLength: 500 },
            summary: { type: 'string', minLength: 1, maxLength: 2000 },
            fullText: { type: 'string', maxLength: 10000 },
            language: { type: 'string', pattern: '^[a-z]{2}(-[A-Z]{2})?$' },
            keywords: {
              type: 'array',
              items: { type: 'string' },
              maxItems: 50,
            },
          },
        },
        sentiment: {
          type: 'object',
          required: ['score', 'magnitude', 'label', 'confidence'],
          properties: {
            score: { type: 'number', minimum: -1, maximum: 1 },
            magnitude: { type: 'number', minimum: 0, maximum: 1 },
            label: { enum: ['positive', 'negative', 'neutral'] },
            confidence: { type: 'number', minimum: 0, maximum: 1 },
            emotions: {
              type: 'object',
              properties: {
                joy: { type: 'number', minimum: 0, maximum: 1 },
                anger: { type: 'number', minimum: 0, maximum: 1 },
                fear: { type: 'number', minimum: 0, maximum: 1 },
                sadness: { type: 'number', minimum: 0, maximum: 1 },
                surprise: { type: 'number', minimum: 0, maximum: 1 },
                disgust: { type: 'number', minimum: 0, maximum: 1 },
              },
            },
          },
        },
        entities: {
          type: 'array',
          items: {
            type: 'object',
            required: ['text', 'type', 'confidence', 'mentions', 'aliases'],
            properties: {
              text: { type: 'string', minLength: 1 },
              type: {
                enum: [
                  'person',
                  'organization',
                  'location',
                  'event',
                  'product',
                  'topic',
                  'other',
                ],
              },
              confidence: { type: 'number', minimum: 0, maximum: 1 },
              mentions: { type: 'integer', minimum: 1 },
              sentiment: { type: 'number', minimum: -1, maximum: 1 },
              wikipedia_url: { type: 'string', format: 'uri' },
              aliases: { type: 'array', items: { type: 'string' } },
            },
          },
        },
        metrics: {
          type: 'object',
          required: ['engagement', 'reach', 'velocity', 'impact'],
          properties: {
            engagement: {
              type: 'object',
              properties: {
                views: { type: 'integer', minimum: 0 },
                likes: { type: 'integer', minimum: 0 },
                shares: { type: 'integer', minimum: 0 },
                comments: { type: 'integer', minimum: 0 },
                retweets: { type: 'integer', minimum: 0 },
              },
            },
            reach: {
              type: 'object',
              properties: {
                impressions: { type: 'integer', minimum: 0 },
                uniqueUsers: { type: 'integer', minimum: 0 },
                followers: { type: 'integer', minimum: 0 },
              },
            },
            velocity: {
              type: 'object',
              required: ['growthRate', 'acceleration'],
              properties: {
                growthRate: { type: 'number', minimum: 0 },
                acceleration: { type: 'number' },
                peakTime: { type: 'string', format: 'date-time' },
              },
            },
            impact: {
              type: 'object',
              required: ['virality', 'influence', 'credibility'],
              properties: {
                virality: { type: 'number', minimum: 0, maximum: 1 },
                influence: { type: 'number', minimum: 0, maximum: 1 },
                credibility: { type: 'number', minimum: 0, maximum: 1 },
              },
            },
          },
        },
        source: {
          type: 'object',
          required: ['platform', 'sourceId', 'reliability'],
          properties: {
            platform: { type: 'string', minLength: 1 },
            url: { type: 'string', format: 'uri' },
            author: { type: 'string' },
            sourceId: { type: 'string', minLength: 1 },
            reliability: { type: 'number', minimum: 0, maximum: 1 },
          },
        },
        metadata: {
          type: 'object',
          required: [
            'ingestionTime',
            'processingVersion',
            'confidence',
            'tags',
            'anomalyFlags',
          ],
          properties: {
            ingestionTime: { type: 'string', format: 'date-time' },
            processingVersion: { type: 'string' },
            confidence: { type: 'number', minimum: 0, maximum: 1 },
            tags: { type: 'array', items: { type: 'string' } },
            anomalyFlags: {
              type: 'array',
              items: {
                type: 'object',
                required: [
                  'type',
                  'severity',
                  'confidence',
                  'description',
                  'detectedAt',
                ],
                properties: {
                  type: {
                    enum: [
                      'spike',
                      'drop',
                      'unusual_pattern',
                      'outlier',
                      'suspicious_source',
                      'coordinated_behavior',
                    ],
                  },
                  severity: { enum: ['low', 'medium', 'high', 'critical'] },
                  confidence: { type: 'number', minimum: 0, maximum: 1 },
                  description: { type: 'string' },
                  detectedAt: { type: 'string', format: 'date-time' },
                  parameters: { type: 'object' },
                },
              },
            },
          },
        },
        contentHash: { type: 'string', pattern: '^[a-f0-9]{64}$' },
        similarityHash: { type: 'string', pattern: '^[a-f0-9]{32}$' },
      },
    };
  }

  /**
   * Get current ingest statistics
   */
  getStats(): IngestStats {
    return { ...this.stats };
  }

  /**
   * Reset statistics
   */
  resetStats(): void {
    Object.assign(this.stats, {
      totalProcessed: 0,
      successfulIngests: 0,
      duplicatesSkipped: 0,
      validationFailures: 0,
      rejections: 0,
      averageProcessingTime: 0,
      anomaliesDetected: 0,
      entitiesExtracted: 0,
    });
  }

  /**
   * Cleanup resources
   */
  dispose(): void {
    if (this.hashCleanupInterval) {
      clearInterval(this.hashCleanupInterval);
    }

    this.recentHashes.clear();
    this.removeAllListeners();

    this.logger.info('TrendIngestPipeline disposed');
  }
}
