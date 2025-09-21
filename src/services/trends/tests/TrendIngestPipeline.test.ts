/**
 * PAKE System - TrendIngestPipeline Tests
 *
 * Comprehensive tests for trend record ingestion including validation,
 * deduplication, anomaly detection, and entity extraction.
 */

import {
  describe,
  beforeEach,
  afterEach,
  it,
  expect,
  jest,
  beforeAll,
  afterAll,
} from '@jest/globals';
import { TrendIngestPipeline } from '../src/ingest';
import { TrendRepository } from '../src/store/TrendRepository';
import { TrendRecord, AnomalyFlag, EntityType } from '../src/types/TrendRecord';
import { mockTrendRecords } from '../../connectors/tests/fixtures/testData';

// Mock the TrendRepository
jest.mock('../src/store/TrendRepository');

// Mock external dependencies
jest.mock('../../orchestrator/src/utils/logger', () => ({
  createLogger: jest.fn(() => ({
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
    debug: jest.fn(),
  })),
}));

jest.mock('../../orchestrator/src/utils/metrics', () => ({
  metrics: {
    counter: jest.fn(),
    histogram: jest.fn(),
    gauge: jest.fn(),
  },
}));

jest.mock('../../security/OutputSanitizer', () => ({
  outputSanitizer: {
    sanitize: jest.fn(input => input), // Pass through for tests
  },
}));

describe('TrendIngestPipeline', () => {
  let pipeline: TrendIngestPipeline;
  let mockRepository: jest.Mocked<TrendRepository>;

  beforeEach(() => {
    jest.clearAllMocks();

    // Create mock repository
    mockRepository = {
      store: jest.fn(),
      findById: jest.fn(),
      search: jest.fn(),
      bulkStore: jest.fn(),
      findByContentHash: jest.fn(),
      findBySimilarityHash: jest.fn(),
      getAnalytics: jest.fn(),
      cleanup: jest.fn(),
      getStorageMetrics: jest.fn(),
      close: jest.fn(),
    } as any;

    (
      TrendRepository as jest.MockedClass<typeof TrendRepository>
    ).mockImplementation(() => mockRepository);

    pipeline = new TrendIngestPipeline(mockRepository);
  });

  afterEach(() => {
    pipeline.destroy();
  });

  describe('Basic Ingestion', () => {
    it('should successfully ingest a valid trend record', async () => {
      const validRecord = mockTrendRecords.valid;

      // Mock repository methods
      mockRepository.findByContentHash.mockResolvedValue(null);
      mockRepository.findBySimilarityHash.mockResolvedValue([]);
      mockRepository.store.mockResolvedValue(validRecord.id);

      const result = await pipeline.ingest(validRecord);

      expect(result.status).toBe('ingested');
      expect(result.id).toBe(validRecord.id);
      expect(result.record).toBeDefined();
      expect(result.errors).toBeUndefined();
      expect(result.processingTime).toBeGreaterThan(0);

      expect(mockRepository.store).toHaveBeenCalledWith(
        expect.objectContaining({
          id: validRecord.id,
          title: validRecord.title,
          platform: validRecord.platform,
        })
      );
    });

    it('should reject invalid trend records', async () => {
      const invalidRecord = {
        // Missing required fields
        title: 'Incomplete record',
        platform: 'twitter',
        // Missing: id, category, language, region, content, timestamp, etc.
      };

      const result = await pipeline.ingest(invalidRecord as any);

      expect(result.status).toBe('rejected');
      expect(result.errors).toBeDefined();
      expect(result.errors!.length).toBeGreaterThan(0);
      expect(result.record).toBeUndefined();

      expect(mockRepository.store).not.toHaveBeenCalled();
    });

    it('should handle missing optional fields gracefully', async () => {
      const recordWithoutOptionals = {
        ...mockTrendRecords.valid,
        url: undefined,
        author: undefined,
        entities: [],
        anomalies: [],
      };

      mockRepository.findByContentHash.mockResolvedValue(null);
      mockRepository.findBySimilarityHash.mockResolvedValue([]);
      mockRepository.store.mockResolvedValue(recordWithoutOptionals.id);

      const result = await pipeline.ingest(recordWithoutOptionals);

      expect(result.status).toBe('ingested');
      expect(result.record?.url).toBeUndefined();
      expect(result.record?.author).toBeUndefined();
      expect(result.record?.entities).toEqual([]);
    });
  });

  describe('Duplicate Detection', () => {
    it('should detect exact duplicates by content hash', async () => {
      const originalRecord = mockTrendRecords.valid;
      const duplicateRecord = { ...originalRecord };

      // Mock finding existing record with same content hash
      mockRepository.findByContentHash.mockResolvedValue(originalRecord);

      const result = await pipeline.ingest(duplicateRecord);

      expect(result.status).toBe('duplicate');
      expect(result.id).toBe(originalRecord.id);

      // Should not attempt to store duplicate
      expect(mockRepository.store).not.toHaveBeenCalled();
    });

    it('should detect similar records by similarity hash', async () => {
      const originalRecord = mockTrendRecords.valid;
      const similarRecord = {
        ...originalRecord,
        id: 'trend-similar',
        title: 'AI Breakthrough: New Quantum Computing Algorithm Announced', // Slightly different
        contentHash: 'different-exact-hash', // Different exact hash
      };

      // Mock no exact duplicate but similar records found
      mockRepository.findByContentHash.mockResolvedValue(null);
      mockRepository.findBySimilarityHash.mockResolvedValue([originalRecord]);

      const result = await pipeline.ingest(similarRecord);

      expect(result.status).toBe('duplicate');
      expect(mockRepository.store).not.toHaveBeenCalled();
    });

    it('should allow ingestion if similarity is below threshold', async () => {
      const originalRecord = mockTrendRecords.valid;
      const dissimilarRecord = {
        ...originalRecord,
        id: 'trend-different',
        title: 'Completely different topic about weather',
        content: 'Weather forecast shows rain tomorrow',
        category: 'weather',
        contentHash: 'different-exact-hash',
        similarityHash: 'different-similarity-hash',
      };

      mockRepository.findByContentHash.mockResolvedValue(null);
      mockRepository.findBySimilarityHash.mockResolvedValue([]); // No similar records
      mockRepository.store.mockResolvedValue(dissimilarRecord.id);

      const result = await pipeline.ingest(dissimilarRecord);

      expect(result.status).toBe('ingested');
      expect(mockRepository.store).toHaveBeenCalled();
    });
  });

  describe('Anomaly Detection', () => {
    it('should detect engagement spike anomalies', async () => {
      const spikyRecord = {
        ...mockTrendRecords.valid,
        id: 'trend-spike',
        engagementCount: 100000, // Very high engagement
        viewCount: 5000000,
        shareCount: 25000,
      };

      mockRepository.findByContentHash.mockResolvedValue(null);
      mockRepository.findBySimilarityHash.mockResolvedValue([]);
      mockRepository.store.mockResolvedValue(spikyRecord.id);

      const result = await pipeline.ingest(spikyRecord);

      expect(result.status).toBe('ingested');
      expect(result.anomaliesDetected).toContainEqual(
        expect.objectContaining({
          type: AnomalyFlag.ENGAGEMENT_SPIKE,
        })
      );

      // Should still ingest but with anomaly flags
      expect(result.record?.anomalies).toContainEqual(
        expect.objectContaining({
          type: AnomalyFlag.ENGAGEMENT_SPIKE,
          severity: expect.any(Number),
          confidence: expect.any(Number),
        })
      );
    });

    it('should detect coordinated behavior anomalies', async () => {
      const coordinatedRecord = mockTrendRecords.withAnomalies;

      mockRepository.findByContentHash.mockResolvedValue(null);
      mockRepository.findBySimilarityHash.mockResolvedValue([]);
      mockRepository.store.mockResolvedValue(coordinatedRecord.id);

      const result = await pipeline.ingest(coordinatedRecord);

      expect(result.status).toBe('ingested');
      expect(result.anomaliesDetected).toContainEqual(
        expect.objectContaining({
          type: AnomalyFlag.COORDINATED_BEHAVIOR,
        })
      );
    });

    it('should detect low quality content', async () => {
      const lowQualityRecord = mockTrendRecords.lowQuality;

      mockRepository.findByContentHash.mockResolvedValue(null);
      mockRepository.findBySimilarityHash.mockResolvedValue([]);
      mockRepository.store.mockResolvedValue(lowQualityRecord.id);

      const result = await pipeline.ingest(lowQualityRecord);

      expect(result.status).toBe('ingested');
      expect(result.anomaliesDetected).toContainEqual(
        expect.objectContaining({
          type: AnomalyFlag.LOW_QUALITY_CONTENT,
        })
      );
    });

    it('should reject records with too many high-severity anomalies', async () => {
      const highAnomalyRecord = {
        ...mockTrendRecords.valid,
        id: 'trend-high-anomaly',
        anomalies: [
          {
            type: AnomalyFlag.BOT_ACTIVITY,
            severity: 0.95,
            confidence: 0.9,
            description: 'High bot activity detected',
            metadata: {},
          },
          {
            type: AnomalyFlag.COORDINATED_BEHAVIOR,
            severity: 0.9,
            confidence: 0.85,
            description: 'Coordinated sharing pattern',
            metadata: {},
          },
          {
            type: AnomalyFlag.POTENTIAL_MISINFORMATION,
            severity: 0.8,
            confidence: 0.75,
            description: 'Potential misinformation detected',
            metadata: {},
          },
        ],
        anomalyScore: 0.95,
      };

      const result = await pipeline.ingest(highAnomalyRecord);

      expect(result.status).toBe('rejected');
      expect(result.errors).toContain('Anomaly score too high');
      expect(mockRepository.store).not.toHaveBeenCalled();
    });
  });

  describe('Entity Extraction and Normalization', () => {
    it('should extract and normalize entities from content', async () => {
      const recordWithEntities = {
        ...mockTrendRecords.valid,
        entities: [
          {
            name: 'quantum computing',
            type: EntityType.TOPIC,
            confidence: 0.9,
            metadata: {},
          },
          {
            name: 'AI',
            type: EntityType.TOPIC,
            confidence: 0.85,
            aliases: ['Artificial Intelligence'],
            metadata: {},
          },
        ],
      };

      mockRepository.findByContentHash.mockResolvedValue(null);
      mockRepository.findBySimilarityHash.mockResolvedValue([]);
      mockRepository.store.mockResolvedValue(recordWithEntities.id);

      const result = await pipeline.ingest(recordWithEntities);

      expect(result.status).toBe('ingested');
      expect(result.record?.entities).toHaveLength(2);
      expect(result.record?.entities).toContainEqual(
        expect.objectContaining({
          name: 'quantum computing',
          type: EntityType.TOPIC,
          confidence: 0.9,
        })
      );
    });

    it('should merge similar entities', async () => {
      const recordWithDuplicateEntities = {
        ...mockTrendRecords.valid,
        entities: [
          {
            name: 'AI',
            type: EntityType.TOPIC,
            confidence: 0.8,
            metadata: {},
          },
          {
            name: 'Artificial Intelligence',
            type: EntityType.TOPIC,
            confidence: 0.9,
            aliases: ['AI'],
            metadata: {},
          },
          {
            name: 'artificial intelligence',
            type: EntityType.TOPIC,
            confidence: 0.75,
            metadata: {},
          },
        ],
      };

      mockRepository.findByContentHash.mockResolvedValue(null);
      mockRepository.findBySimilarityHash.mockResolvedValue([]);
      mockRepository.store.mockResolvedValue(recordWithDuplicateEntities.id);

      const result = await pipeline.ingest(recordWithDuplicateEntities);

      expect(result.status).toBe('ingested');

      // Should have merged similar entities
      expect(result.record?.entities.length).toBeLessThan(3);

      const aiEntity = result.record?.entities.find(
        e =>
          e.name.toLowerCase().includes('artificial intelligence') ||
          e.name.toLowerCase() === 'ai'
      );

      expect(aiEntity).toBeDefined();
      expect(aiEntity?.confidence).toBe(0.9); // Should use highest confidence
    });
  });

  describe('Quality Control', () => {
    it('should calculate quality scores correctly', async () => {
      const record = mockTrendRecords.valid;

      mockRepository.findByContentHash.mockResolvedValue(null);
      mockRepository.findBySimilarityHash.mockResolvedValue([]);
      mockRepository.store.mockResolvedValue(record.id);

      const result = await pipeline.ingest(record);

      expect(result.status).toBe('ingested');
      expect(result.record?.qualityScore).toBeGreaterThan(0);
      expect(result.record?.qualityScore).toBeLessThanOrEqual(1);
      expect(result.record?.freshnessScore).toBeGreaterThan(0);
      expect(result.record?.freshnessScore).toBeLessThanOrEqual(1);
    });

    it('should reject records below quality threshold', async () => {
      const veryLowQualityRecord = {
        ...mockTrendRecords.valid,
        id: 'trend-very-low-quality',
        title: 'bad',
        content: 'very short',
        qualityScore: 0.05,
      };

      const result = await pipeline.ingest(veryLowQualityRecord);

      expect(result.status).toBe('rejected');
      expect(result.errors).toContain('Quality score below threshold');
      expect(mockRepository.store).not.toHaveBeenCalled();
    });
  });

  describe('Batch Processing', () => {
    it('should process multiple records efficiently', async () => {
      const records = [
        mockTrendRecords.valid,
        { ...mockTrendRecords.valid, id: 'trend-002', title: 'Second trend' },
        { ...mockTrendRecords.valid, id: 'trend-003', title: 'Third trend' },
      ];

      mockRepository.findByContentHash.mockResolvedValue(null);
      mockRepository.findBySimilarityHash.mockResolvedValue([]);
      mockRepository.bulkStore.mockResolvedValue(records.map(r => r.id));

      const results = await pipeline.bulkIngest(records);

      expect(results).toHaveLength(3);
      expect(results.every(r => r.status === 'ingested')).toBe(true);
      expect(mockRepository.bulkStore).toHaveBeenCalledWith(
        expect.arrayContaining([
          expect.objectContaining({ id: 'trend-001' }),
          expect.objectContaining({ id: 'trend-002' }),
          expect.objectContaining({ id: 'trend-003' }),
        ])
      );
    });

    it('should handle mixed success/failure in batch processing', async () => {
      const records = [
        mockTrendRecords.valid,
        { title: 'Invalid record' }, // Missing required fields
        { ...mockTrendRecords.valid, id: 'trend-003', title: 'Valid record' },
      ];

      mockRepository.findByContentHash.mockResolvedValue(null);
      mockRepository.findBySimilarityHash.mockResolvedValue([]);
      mockRepository.bulkStore.mockResolvedValue(['trend-001', 'trend-003']);

      const results = await pipeline.bulkIngest(records as any);

      expect(results).toHaveLength(3);
      expect(results[0].status).toBe('ingested');
      expect(results[1].status).toBe('rejected');
      expect(results[2].status).toBe('ingested');
    });
  });

  describe('Performance and Monitoring', () => {
    it('should track processing statistics', async () => {
      const records = [
        mockTrendRecords.valid,
        mockTrendRecords.withAnomalies,
        mockTrendRecords.lowQuality,
      ];

      mockRepository.findByContentHash.mockResolvedValue(null);
      mockRepository.findBySimilarityHash.mockResolvedValue([]);
      mockRepository.store.mockResolvedValue('test-id');

      // Process records
      for (const record of records) {
        await pipeline.ingest(record);
      }

      const stats = pipeline.getStats();

      expect(stats.totalProcessed).toBe(3);
      expect(stats.successfulIngests).toBe(3);
      expect(stats.duplicatesSkipped).toBe(0);
      expect(stats.validationFailures).toBe(0);
      expect(stats.rejections).toBe(0);
      expect(stats.averageProcessingTime).toBeGreaterThan(0);
      expect(stats.anomaliesDetected).toBeGreaterThan(0);
      expect(stats.entitiesExtracted).toBeGreaterThan(0);
    });

    it('should emit processing events', async () => {
      const eventListener = jest.fn();
      pipeline.on('record:ingested', eventListener);

      const record = mockTrendRecords.valid;
      mockRepository.findByContentHash.mockResolvedValue(null);
      mockRepository.findBySimilarityHash.mockResolvedValue([]);
      mockRepository.store.mockResolvedValue(record.id);

      await pipeline.ingest(record);

      expect(eventListener).toHaveBeenCalledWith(
        expect.objectContaining({
          record: expect.objectContaining({ id: record.id }),
          processingTime: expect.any(Number),
          anomalies: expect.any(Number),
        })
      );
    });

    it('should handle processing errors gracefully', async () => {
      const errorListener = jest.fn();
      pipeline.on('record:failed', errorListener);

      const record = mockTrendRecords.valid;
      mockRepository.store.mockRejectedValue(new Error('Database error'));

      const result = await pipeline.ingest(record);

      expect(result.status).toBe('failed');
      expect(result.errors).toContain('Database error');
      expect(errorListener).toHaveBeenCalled();
    });
  });

  describe('Content Hashing', () => {
    it('should generate consistent content hashes', async () => {
      const record1 = mockTrendRecords.valid;
      const record2 = { ...mockTrendRecords.valid }; // Identical content

      mockRepository.findByContentHash.mockResolvedValue(null);
      mockRepository.findBySimilarityHash.mockResolvedValue([]);
      mockRepository.store.mockResolvedValue('test-id');

      const result1 = await pipeline.ingest(record1);
      const result2 = await pipeline.ingest(record2);

      expect(result1.record?.contentHash).toBeDefined();
      expect(result2.record?.contentHash).toBeDefined();
      expect(result1.record?.contentHash).toBe(result2.record?.contentHash);
    });

    it('should generate different hashes for different content', async () => {
      const record1 = mockTrendRecords.valid;
      const record2 = {
        ...mockTrendRecords.valid,
        title: 'Different title',
        content: 'Different content',
      };

      mockRepository.findByContentHash.mockResolvedValue(null);
      mockRepository.findBySimilarityHash.mockResolvedValue([]);
      mockRepository.store.mockResolvedValue('test-id');

      const result1 = await pipeline.ingest(record1);
      const result2 = await pipeline.ingest(record2);

      expect(result1.record?.contentHash).not.toBe(result2.record?.contentHash);
      expect(result1.record?.similarityHash).not.toBe(
        result2.record?.similarityHash
      );
    });
  });

  describe('Timestamp Normalization', () => {
    it('should normalize timestamps to UTC', async () => {
      const recordWithLocalTime = {
        ...mockTrendRecords.valid,
        timestamp: new Date('2024-01-15T10:30:00-05:00'), // EST timezone
      };

      mockRepository.findByContentHash.mockResolvedValue(null);
      mockRepository.findBySimilarityHash.mockResolvedValue([]);
      mockRepository.store.mockResolvedValue(recordWithLocalTime.id);

      const result = await pipeline.ingest(recordWithLocalTime);

      expect(result.status).toBe('ingested');
      expect(result.record?.timestamp.toISOString()).toBe(
        '2024-01-15T15:30:00.000Z'
      );
    });

    it('should handle invalid timestamps', async () => {
      const recordWithInvalidTime = {
        ...mockTrendRecords.valid,
        timestamp: new Date('invalid-date'),
      };

      mockRepository.findByContentHash.mockResolvedValue(null);
      mockRepository.findBySimilarityHash.mockResolvedValue([]);
      mockRepository.store.mockResolvedValue(recordWithInvalidTime.id);

      const result = await pipeline.ingest(recordWithInvalidTime);

      expect(result.status).toBe('ingested');
      expect(result.record?.timestamp).toBeInstanceOf(Date);
      expect(result.warnings).toContain(
        'Invalid timestamp, using current time'
      );
    });
  });
});
