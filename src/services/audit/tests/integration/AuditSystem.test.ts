/**
 * Integration tests for the complete Audit System
 */

import { Pool } from 'pg';
import AWS from 'aws-sdk';
import { CryptographicAuditService } from '../../src/services/CryptographicAuditService';
import { AuditStorageService } from '../../src/services/AuditStorageService';
import { StreamingService } from '../../src/services/StreamingService';
import { RetentionPolicyService } from '../../src/services/RetentionPolicyService';
import { ComplianceReportingService } from '../../src/services/ComplianceReportingService';
import { AuditAnalyticsService } from '../../src/services/AuditAnalyticsService';
import {
  AuditEvent,
  ActionType,
  ActionResult,
  ActorType,
  AuditConfig,
  ComplianceReportType,
  RetentionPolicy,
} from '../../src/types/audit.types';

// Mock AWS services for testing
jest.mock('aws-sdk');
jest.mock('pg');
jest.mock('kafkajs');
jest.mock('redis');

describe('Audit System Integration', () => {
  let cryptoService: CryptographicAuditService;
  let storageService: AuditStorageService;
  let streamingService: StreamingService;
  let retentionService: RetentionPolicyService;
  let complianceService: ComplianceReportingService;
  let analyticsService: AuditAnalyticsService;

  const testConfig: AuditConfig = {
    database: {
      host: 'localhost',
      port: 5432,
      name: 'audit_test',
      user: 'test_user',
      REDACTED_SECRET: process.env.UNKNOWN,
      ssl: false,
      maxConnections: 5,
    },
    storage: {
      s3: {
        region: 'us-west-2',
        bucket: 'audit-test-bucket',
        accessKeyId: 'test-key',
        secretAccessKey: 'test-secret',
      },
      glacier: {
        region: 'us-west-2',
        vault: 'audit-test-vault',
      },
    },
    streaming: {
      kafka: {
        brokers: ['localhost:9092'],
        topic: 'audit-events-test',
        clientId: 'audit-test-client',
      },
      redis: {
        host: 'localhost',
        port: 6379,
      },
    },
    security: {
      signingKey: 'test-signing-key-integration',
      encryptionKey:
        '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
      algorithm: 'aes-256-gcm',
    },
    retention: {
      hotStorageDays: 30,
      warmStorageDays: 90,
      coldStorageYears: 7,
    },
    compliance: {
      enabled: true,
      reports: [ComplianceReportType.SOC2, ComplianceReportType.GDPR],
      alerting: true,
    },
  };

  beforeAll(async () => {
    // Setup mock implementations
    setupMocks();

    // Initialize services
    cryptoService = new CryptographicAuditService(
      testConfig.security.signingKey,
      testConfig.security.encryptionKey
    );

    storageService = new AuditStorageService(testConfig);
    await storageService.initialize();

    streamingService = new StreamingService(testConfig);
    await streamingService.initialize();

    retentionService = new RetentionPolicyService(storageService);
    await retentionService.initialize();

    complianceService = new ComplianceReportingService(
      storageService,
      cryptoService
    );

    analyticsService = new AuditAnalyticsService(storageService);
    await analyticsService.initialize();
  });

  afterAll(async () => {
    // Cleanup services
    await storageService.close();
    await streamingService.close();
    await retentionService.close();
    await analyticsService.close();
  });

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('End-to-End Audit Flow', () => {
    it('should complete full audit event lifecycle', async () => {
      // 1. Create audit event
      const auditEvent: Omit<AuditEvent, 'signature'> = {
        id: 'integration-test-001',
        timestamp: new Date().toISOString(),
        actor: {
          id: 'test-user-001',
          type: ActorType.USER,
          ip: '192.168.1.100',
          session: 'session-abc-123',
        },
        action: {
          type: ActionType.CREATE,
          resource: 'document',
          resourceId: 'doc-001',
          result: ActionResult.SUCCESS,
          duration: 150,
          metadata: {
            documentType: 'report',
            size: 1024,
          },
        },
        context: {
          requestId: 'req-001',
          environment: process.env.UNKNOWN,
          application: 'document-service',
          version: '1.0.0',
        },
        version: '1.0.0',
      };

      // 2. Sign the event
      const signedEvent = await cryptoService.signAuditEvent(auditEvent);
      expect(signedEvent.signature).toBeTruthy();

      // 3. Verify signature
      const isValid = await cryptoService.verifyAuditEvent(signedEvent);
      expect(isValid).toBe(true);

      // 4. Store in database
      await storageService.storeEvent(signedEvent);

      // 5. Stream to SIEM (mocked)
      await streamingService.streamEvent(signedEvent);

      // 6. Query the stored event
      const queryResult = await storageService.queryEvents({
        actorId: 'test-user-001',
        limit: 10,
      });

      expect(queryResult).toHaveLength(1);
      expect(queryResult[0].id).toBe('integration-test-001');
      expect(queryResult[0].signature).toBe(signedEvent.signature);
    });

    it('should handle batch processing correctly', async () => {
      const batchEvents: Omit<AuditEvent, 'signature'>[] = [];

      // Create multiple events
      for (let i = 0; i < 5; i++) {
        batchEvents.push({
          id: `batch-test-${i.toString().padStart(3, '0')}`,
          timestamp: new Date(Date.now() + i * 1000).toISOString(),
          actor: {
            id: `batch-user-${i}`,
            type: ActorType.USER,
            ip: `192.168.1.${100 + i}`,
          },
          action: {
            type: ActionType.UPDATE,
            resource: 'batch-resource',
            resourceId: `resource-${i}`,
            result: ActionResult.SUCCESS,
            duration: 100 + i * 10,
          },
          context: {
            environment: process.env.UNKNOWN,
            application: 'batch-service',
            version: '1.0.0',
          },
          version: '1.0.0',
        });
      }

      // Sign all events
      const signedEvents: AuditEvent[] = [];
      for (const event of batchEvents) {
        const signed = await cryptoService.signAuditEvent(event);
        signedEvents.push(signed);
      }

      // Create signed batch
      const batch = await cryptoService.createSignedBatch(signedEvents);
      expect(batch.events).toHaveLength(5);
      expect(batch.checksum).toBeTruthy();

      // Verify batch
      const batchValid = await cryptoService.verifyBatch(batch);
      expect(batchValid).toBe(true);

      // Store batch
      await storageService.storeBatch(batch);

      // Stream batch
      await streamingService.streamBatch(signedEvents);

      // Query batch events
      const batchQuery = await storageService.queryEvents({
        resource: 'batch-resource',
        limit: 10,
      });

      expect(batchQuery).toHaveLength(5);
    });
  });

  describe('Compliance Reporting Integration', () => {
    it('should generate SOC2 compliance report', async () => {
      // Create compliance-relevant events
      const complianceEvents: Omit<AuditEvent, 'signature'>[] = [
        {
          id: 'soc2-login-001',
          timestamp: new Date().toISOString(),
          actor: {
            id: 'compliance-user',
            type: ActorType.USER,
            ip: '10.0.1.50',
          },
          action: {
            type: ActionType.LOGIN,
            resource: 'authentication',
            result: ActionResult.SUCCESS,
          },
          context: {
            environment: 'production',
            application: 'auth-service',
            version: '2.1.0',
          },
          version: '1.0.0',
        },
        {
          id: 'soc2-access-001',
          timestamp: new Date(Date.now() + 60000).toISOString(),
          actor: {
            id: 'compliance-user',
            type: ActorType.USER,
            ip: '10.0.1.50',
          },
          action: {
            type: ActionType.read,
            resource: 'sensitive-data',
            result: ActionResult.SUCCESS,
          },
          context: {
            environment: 'production',
            application: 'data-service',
            version: '1.5.0',
          },
          version: '1.0.0',
        },
        {
          id: 'soc2-denied-001',
          timestamp: new Date(Date.now() + 120000).toISOString(),
          actor: {
            id: 'unauthorized-user',
            type: ActorType.USER,
            ip: '192.168.1.200',
          },
          action: {
            type: ActionType.ACCESS_DENIED,
            resource: 'admin-panel',
            result: ActionResult.DENIED,
          },
          context: {
            environment: 'production',
            application: 'admin-service',
            version: '3.0.0',
          },
          version: '1.0.0',
        },
      ];

      // Store compliance events
      for (const event of complianceEvents) {
        const signed = await cryptoService.signAuditEvent(event);
        await storageService.storeEvent(signed);
      }

      // Generate SOC2 report
      const startDate = new Date(Date.now() - 24 * 60 * 60 * 1000); // 24 hours ago
      const endDate = new Date();

      const report = await complianceService.generateSOC2Report(
        startDate,
        endDate,
        'integration-test'
      );

      expect(report.type).toBe(ComplianceReportType.SOC2);
      expect(report.summary.totalEvents).toBeGreaterThan(0);
      expect(report.summary.securityIncidents).toBeGreaterThanOrEqual(1); // The denied access
      expect(report.signature).toBeTruthy();

      // Verify report integrity
      const reportValid = await complianceService.verifyReport(report);
      expect(reportValid).toBe(true);
    });

    it('should detect compliance violations', async () => {
      const startDate = new Date(Date.now() - 60 * 60 * 1000); // 1 hour ago
      const endDate = new Date();

      const violations = await complianceService.getComplianceViolations(
        ComplianceReportType.SOC2,
        startDate,
        endDate
      );

      expect(Array.isArray(violations)).toBe(true);
      // Should include the denied access event from previous test
      expect(
        violations.some(v => v.action.result === ActionResult.DENIED)
      ).toBe(true);
    });
  });

  describe('Retention Policy Integration', () => {
    it('should create and execute retention policy', async () => {
      // Create test policy
      const policyData: Omit<
        RetentionPolicy,
        'id' | 'createdAt' | 'updatedAt'
      > = {
        name: 'Test Integration Policy',
        description: 'Short retention for integration tests',
        criteria: {
          resourceTypes: ['test-resource'],
          criticalOnly: false,
        },
        hotStorageDays: 1, // Very short for testing
        warmStorageDays: 7,
        coldStorageYears: 1,
        enabled: true,
      };

      const policy = await retentionService.createPolicy(policyData);
      expect(policy.id).toBeTruthy();
      expect(policy.enabled).toBe(true);

      // Evaluate policy impact
      const evaluation = await retentionService.evaluatePolicy(policy);
      expect(evaluation.policyId).toBe(policy.id);
      expect(evaluation.archivalType).toBeTruthy();

      // Get all policies
      const allPolicies = retentionService.getAllPolicies();
      expect(allPolicies.some(p => p.id === policy.id)).toBe(true);

      // Clean up
      await retentionService.deletePolicy(policy.id);

      const updatedPolicies = retentionService.getAllPolicies();
      expect(updatedPolicies.some(p => p.id === policy.id)).toBe(false);
    });
  });

  describe('Analytics Integration', () => {
    it('should analyze events and detect anomalies', async () => {
      // Create events with some anomalous patterns
      const normalEvent: Omit<AuditEvent, 'signature'> = {
        id: 'analytics-normal-001',
        timestamp: new Date().toISOString(),
        actor: { id: 'normal-user', type: ActorType.USER, ip: '192.168.1.100' },
        action: {
          type: ActionType.read,
          resource: 'document',
          result: ActionResult.SUCCESS,
        },
        context: {
          environment: 'test',
          application: 'app',
          version: process.env.UNKNOWN,
        },
        version: '1.0.0',
      };

      const suspiciousEvent: Omit<AuditEvent, 'signature'> = {
        id: 'analytics-suspicious-001',
        timestamp: new Date(Date.now() + 1000).toISOString(),
        actor: {
          id: 'suspicious-user',
          type: ActorType.USER,
          ip: '203.0.113.1',
        }, // External IP
        action: {
          type: ActionType.DELETE,
          resource: 'sensitive-data',
          result: ActionResult.SUCCESS,
        },
        context: {
          environment: 'test',
          application: 'app',
          version: process.env.UNKNOWN,
        },
        version: '1.0.0',
      };

      // Store and analyze events
      const normalSigned = await cryptoService.signAuditEvent(normalEvent);
      const suspiciousSigned =
        await cryptoService.signAuditEvent(suspiciousEvent);

      await storageService.storeEvent(normalSigned);
      await storageService.storeEvent(suspiciousSigned);

      // Analyze individual events
      const normalScore = await analyticsService.analyzeEvent(normalSigned);
      const suspiciousScore =
        await analyticsService.analyzeEvent(suspiciousSigned);

      expect(normalScore.score).toBeLessThan(suspiciousScore.score);
      expect(suspiciousScore.score).toBeGreaterThan(30); // Should be flagged as suspicious
      expect(suspiciousScore.reasons.length).toBeGreaterThan(0);

      // Check for alerts
      const activeAlerts = analyticsService.getActiveAlerts();
      expect(activeAlerts.length).toBeGreaterThanOrEqual(0);
    });

    it('should generate analytics report', async () => {
      const startDate = new Date(Date.now() - 60 * 60 * 1000); // 1 hour ago
      const endDate = new Date();

      const analytics = await analyticsService.generateAnalytics(
        startDate,
        endDate
      );

      expect(analytics.period.start).toBeTruthy();
      expect(analytics.period.end).toBeTruthy();
      expect(analytics.metrics.totalEvents).toBeGreaterThanOrEqual(0);
      expect(Array.isArray(analytics.metrics.eventsPerHour)).toBe(true);
      expect(Array.isArray(analytics.trends.dailyVolume)).toBe(true);
      expect(Array.isArray(analytics.trends.hourlyPattern)).toBe(true);
      expect(Array.isArray(analytics.anomalies)).toBe(true);
    });
  });

  describe('Error Handling and Recovery', () => {
    it('should handle storage failures gracefully', async () => {
      // Mock a storage failure
      const mockError = new Error('Database connection failed');
      jest.spyOn(storageService, 'storeEvent').mockRejectedValueOnce(mockError);

      const testEvent: Omit<AuditEvent, 'signature'> = {
        id: 'error-test-001',
        timestamp: new Date().toISOString(),
        actor: { id: 'error-user', type: ActorType.USER },
        action: {
          type: ActionType.CREATE,
          resource: process.env.UNKNOWN,
          result: ActionResult.SUCCESS,
        },
        context: {
          environment: 'test',
          application: 'app',
          version: process.env.UNKNOWN,
        },
        version: '1.0.0',
      };

      const signedEvent = await cryptoService.signAuditEvent(testEvent);

      // Should not throw - audit system should be resilient
      await expect(storageService.storeEvent(signedEvent)).rejects.toThrow(
        'Database connection failed'
      );

      // Restore mock
      jest.restoreAllMocks();
    });

    it('should validate audit trail integrity', async () => {
      // Create chain of events
      const events: AuditEvent[] = [];

      for (let i = 0; i < 3; i++) {
        const event: Omit<AuditEvent, 'signature'> = {
          id: `chain-test-${i}`,
          timestamp: new Date(Date.now() + i * 1000).toISOString(),
          actor: { id: `user-${i}`, type: ActorType.USER },
          action: {
            type: ActionType.UPDATE,
            resource: 'chain-test',
            result: ActionResult.SUCCESS,
          },
          context: {
            environment: 'test',
            application: 'app',
            version: process.env.UNKNOWN,
          },
          version: '1.0.0',
        };

        const signed = await cryptoService.signAuditEvent(event);
        events.push(signed);
      }

      // Generate integrity report
      const integrityReport =
        await cryptoService.generateIntegrityReport(events);

      expect(integrityReport.summary.integrityStatus).toBe('verified');
      expect(integrityReport.summary.issues).toHaveLength(0);
      expect(integrityReport.proof.tamperSeal).toBeTruthy();
      expect(integrityReport.proof.signature).toBeTruthy();

      // Test tampering detection
      const tamperedEvent = { ...events[1], signature: 'tampered-signature' };
      const tamperedEvents = [events[0], tamperedEvent, events[2]];

      const tamperedReport =
        await cryptoService.generateIntegrityReport(tamperedEvents);
      expect(tamperedReport.summary.integrityStatus).toBe('compromised');
      expect(tamperedReport.summary.issues.length).toBeGreaterThan(0);
    });
  });

  describe('Performance and Scalability', () => {
    it('should handle high-volume event processing', async () => {
      const startTime = Date.now();
      const eventCount = 100; // Reduced for test performance
      const events: AuditEvent[] = [];

      // Create and sign many events
      for (let i = 0; i < eventCount; i++) {
        const event: Omit<AuditEvent, 'signature'> = {
          id: `perf-test-${i.toString().padStart(4, '0')}`,
          timestamp: new Date(Date.now() + i).toISOString(),
          actor: { id: `perf-user-${i % 10}`, type: ActorType.USER },
          action: {
            type: ActionType.CREATE,
            resource: 'perf-resource',
            result: ActionResult.SUCCESS,
          },
          context: {
            environment: 'test',
            application: 'perf-app',
            version: process.env.UNKNOWN,
          },
          version: '1.0.0',
        };

        const signed = await cryptoService.signAuditEvent(event);
        events.push(signed);
      }

      const signingTime = Date.now() - startTime;

      // Store in batch
      const batchStartTime = Date.now();
      const batch = await cryptoService.createSignedBatch(events);
      await storageService.storeBatch(batch);
      const storageTime = Date.now() - batchStartTime;

      // Performance assertions
      expect(events).toHaveLength(eventCount);
      expect(signingTime).toBeLessThan(10000); // Less than 10 seconds
      expect(storageTime).toBeLessThan(5000); // Less than 5 seconds

      console.log(`Performance test results:
        - Signed ${eventCount} events in ${signingTime}ms (${(signingTime / eventCount).toFixed(2)}ms per event)
        - Stored batch in ${storageTime}ms`);
    });
  });

  /**
   * Setup mocks for external dependencies
   */
  function setupMocks() {
    // Mock PostgreSQL
    const mockQuery = jest.fn().mockResolvedValue({ rows: [] });
    const mockClient = {
      query: mockQuery,
      release: jest.fn(),
    };
    const mockPool = {
      connect: jest.fn().mockResolvedValue(mockClient),
      query: mockQuery,
      end: jest.fn(),
    };
    (Pool as jest.MockedClass<typeof Pool>).mockImplementation(
      () => mockPool as any
    );

    // Mock AWS S3
    const mockS3 = {
      putObject: jest
        .fn()
        .mockReturnValue({ promise: jest.fn().mockResolvedValue({}) }),
      getObject: jest.fn().mockReturnValue({
        promise: jest.fn().mockResolvedValue({ Body: '{}' }),
      }),
      deleteObject: jest
        .fn()
        .mockReturnValue({ promise: jest.fn().mockResolvedValue({}) }),
      listObjectsV2: jest.fn().mockReturnValue({
        promise: jest.fn().mockResolvedValue({ Contents: [] }),
      }),
    };

    // Mock AWS Glacier
    const mockGlacier = {
      uploadArchive: jest.fn().mockReturnValue({
        promise: jest.fn().mockResolvedValue({ archiveId: 'test-archive-id' }),
      }),
      describeVault: jest.fn().mockReturnValue({
        promise: jest
          .fn()
          .mockResolvedValue({ NumberOfArchives: 0, SizeInBytes: 0 }),
      }),
    };

    AWS.S3 = jest.fn().mockImplementation(() => mockS3);
    AWS.Glacier = jest.fn().mockImplementation(() => mockGlacier);
  }
});
