/**
 * Comprehensive Integration Tests
 *
 * Tests the complete flow from API call to provider execution and audit logging
 * with mocked endpoints and failure scenarios.
 */

import request from 'supertest';
import express from 'express';
import { Server } from 'http';
import nock from 'nock';
import { jest } from '@jest/globals';
import { AgentTaskType, AgentResultStatus } from '../../agent-runtime/src/types/Agent';
import { TaskSubmissionAPI, createTaskSubmissionRouter } from '../../src/api/submitTask';
import { OrchestratorRouter } from '../../src/router';
import { AuditLog } from '../../src/store/AuditLog';
import { FeatureFlags } from '../../config/FeatureFlags';
import { ClaudeProvider } from '../../agent-runtime/src/providers/ClaudeProvider';
import { OllamaProvider } from '../../agent-runtime/src/providers/OllamaProvider';
import { NullProvider } from '../../agent-runtime/src/providers/NullProvider';
import { metrics, metricsCollector, TaskLifecycleEvent } from '../../src/utils/metrics';
import fs from 'fs/promises';
import path from 'path';

describe('Full Integration Flow', () => {
  let app: express.Application;
  let server: Server;
  let router: OrchestratorRouter;
  let auditLog: AuditLog;
  let featureFlags: FeatureFlags;
  let taskSubmissionAPI: TaskSubmissionAPI;

  // Test data directories
  const testDataDir = path.join(__dirname, 'test-data');
  const auditLogPath = path.join(testDataDir, 'audit-test.jsonl');

  beforeAll(async () => {
    // Create test data directory
    await fs.mkdir(testDataDir, { recursive: true });

    // Initialize feature flags with test configuration
    featureFlags = new FeatureFlags();
    featureFlags.setOverride('TASK_SUBMISSION_API_ENABLED', true);
    featureFlags.setOverride('CLAUDE_PROVIDER_ENABLED', true);
    featureFlags.setOverride('OLLAMA_PROVIDER_ENABLED', true);
    featureFlags.setOverride('NULL_PROVIDER_ENABLED', true);
    featureFlags.setOverride('ENABLE_RESPONSE_CACHING', true);
    featureFlags.setOverride('RESPONSE_CACHE_TTL_SECONDS', 300);

    // Initialize audit log with test file
    auditLog = new AuditLog(auditLogPath);
    await auditLog.initialize();

    // Initialize router with test providers
    router = new OrchestratorRouter(featureFlags);

    // Register providers for testing
    const nullProvider = new NullProvider();
    const claudeProvider = new ClaudeProvider({
      apiKey: process.env.UNKNOWN,
      model: 'claude-3-sonnet-20240229',
    });
    const ollamaProvider = new OllamaProvider({
      baseUrl: 'http://localhost:11434',
      defaultModel: 'llama2',
    });

    router.registerProvider('null', nullProvider, 1);
    router.registerProvider('claude', claudeProvider, 5);
    router.registerProvider('ollama', ollamaProvider, 3);

    // Set up Express app with routes
    app = express();
    const apiRouter = createTaskSubmissionRouter(router, auditLog, featureFlags);
    app.use('/api/v1/tasks', apiRouter);

    // Start test server
    server = app.listen(0);
  });

  afterAll(async () => {
    // Cleanup
    server.close();
    await auditLog.close();

    // Clean up test data
    try {
      await fs.rm(testDataDir, { recursive: true });
    } catch (error) {
      // Ignore cleanup errors
    }

    // Clear nock interceptors
    nock.cleanAll();
  });

  beforeEach(() => {
    // Reset metrics before each test
    jest.clearAllMocks();
    nock.cleanAll();
  });

  describe('Successful Task Execution Flow', () => {
    test('should handle sentiment analysis with NullProvider', async () => {
      const taskRequest = {
        type: AgentTaskType.SENTIMENT_ANALYSIS,
        input: {
          content: 'This is a great product! I love it.',
          priority: 'normal',
        },
        config: {
          timeout: 10000,
          preferredProvider: 'null',
        },
        metadata: {
          source: 'integration-test',
          userId: 'test-user-123',
          sessionId: 'test-session-456',
        },
      };

      const response = await request(app)
        .post('/api/v1/tasks/submit')
        .send(taskRequest)
        .expect(200);

      // Verify response structure
      expect(response.body).toMatchObject({
        success: true,
        taskId: expect.any(String),
        status: AgentResultStatus.SUCCESS,
        result: {
          output: expect.any(Object),
          metadata: expect.any(Object),
          provider: 'null',
          executionTime: expect.any(Number),
        },
        routing: {
          selectedProvider: 'null',
          reason: expect.any(String),
          alternatives: expect.any(Array),
        },
        audit: {
          requestId: expect.any(String),
          timestamp: expect.any(String),
          processingTime: expect.any(Number),
        },
      });

      // Verify audit log entry was created
      const auditEntries = await auditLog.getEntriesByTaskId(response.body.taskId);
      expect(auditEntries.length).toBeGreaterThan(0);

      const submissionEntry = auditEntries.find((e) => e.eventType === 'TASK_SUBMITTED');
      expect(submissionEntry).toBeDefined();
      expect(submissionEntry?.data.taskType).toBe(AgentTaskType.SENTIMENT_ANALYSIS);
    });

    test('should handle content analysis with ClaudeProvider (mocked)', async () => {
      // Mock Claude API response
      const mockClaudeResponse = {
        id: 'msg_test123',
        type: 'message',
        role: 'assistant',
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              analysis: 'This is a comprehensive analysis of the content',
              sentiment: 'positive',
              key_topics: ['product', 'quality', 'satisfaction'],
              confidence: 0.95,
            }),
          },
        ],
        model: 'claude-3-sonnet-20240229',
        stop_reason: 'end_turn',
        stop_sequence: null,
        usage: {
          input_tokens: 100,
          output_tokens: 150,
        },
      };

      nock('https://api.anthropic.com').post('/v1/messages').reply(200, mockClaudeResponse);

      const taskRequest = {
        type: AgentTaskType.CONTENT_ANALYSIS,
        input: {
          content:
            'Analyze this product review: This smartphone has excellent battery life and camera quality.',
          priority: 'high',
        },
        config: {
          timeout: 30000,
          preferredProvider: 'claude',
          temperature: 0.7,
          maxTokens: 1000,
        },
        metadata: {
          source: 'integration-test',
          userId: 'test-user-789',
          correlationId: 'test-correlation-123',
        },
      };

      const response = await request(app)
        .post('/api/v1/tasks/submit')
        .send(taskRequest)
        .expect(200);

      // Verify response
      expect(response.body.success).toBe(true);
      expect(response.body.result.provider).toBe('claude');
      expect(response.body.result.tokensUsed).toBeDefined();
      expect(response.body.result.cost).toBeDefined();

      // Verify audit trail
      const auditEntries = await auditLog.getEntriesByTaskId(response.body.taskId);
      const executionEntry = auditEntries.find((e) => e.eventType === 'TASK_EXECUTED');
      expect(executionEntry).toBeDefined();
      expect(executionEntry?.data.provider).toBe('claude');
    });

    test('should handle entity extraction with OllamaProvider (mocked)', async () => {
      // Mock Ollama API responses
      nock('http://localhost:11434')
        .get('/api/tags')
        .reply(200, {
          models: [
            {
              name: 'llama2:latest',
              model: 'llama2',
              modified_at: '2024-01-01T00:00:00Z',
              size: 3825819519,
            },
          ],
        });

      nock('http://localhost:11434')
        .post('/api/generate')
        .reply(200, {
          model: 'llama2',
          created_at: '2024-01-01T12:00:00Z',
          response: JSON.stringify({
            entities: [
              { text: 'Apple Inc.', type: 'ORGANIZATION', confidence: 0.95 },
              { text: 'Tim Cook', type: 'PERSON', confidence: 0.92 },
              { text: 'Cupertino', type: 'LOCATION', confidence: 0.88 },
            ],
          }),
          done: true,
          context: [],
          total_duration: 2500000000,
          load_duration: 500000000,
          prompt_eval_count: 50,
          prompt_eval_duration: 800000000,
          eval_count: 75,
          eval_duration: 1200000000,
        });

      const taskRequest = {
        type: AgentTaskType.ENTITY_EXTRACTION,
        input: {
          content:
            'Tim Cook, the CEO of Apple Inc., announced new products at the Cupertino headquarters.',
          priority: 'normal',
        },
        config: {
          timeout: 20000,
          preferredProvider: 'ollama',
        },
        metadata: {
          source: 'integration-test',
          userId: 'test-user-456',
        },
      };

      const response = await request(app)
        .post('/api/v1/tasks/submit')
        .send(taskRequest)
        .expect(200);

      // Verify response
      expect(response.body.success).toBe(true);
      expect(response.body.result.provider).toBe('ollama');
      expect(response.body.result.output.entities).toBeDefined();
      expect(response.body.result.output.entities).toHaveLength(3);
    });
  });

  describe('Error Handling and Fallback Scenarios', () => {
    test('should fallback to secondary provider when primary fails', async () => {
      // Mock Claude API failure
      nock('https://api.anthropic.com')
        .post('/v1/messages')
        .reply(500, { error: 'Internal server error' });

      const taskRequest = {
        type: AgentTaskType.SENTIMENT_ANALYSIS,
        input: {
          content: 'Test content for fallback scenario',
        },
        config: {
          preferredProvider: 'claude',
          fallbackProviders: ['null'],
        },
      };

      const response = await request(app)
        .post('/api/v1/tasks/submit')
        .send(taskRequest)
        .expect(200);

      // Should succeed with fallback to null provider
      expect(response.body.success).toBe(true);
      expect(response.body.result.provider).toBe('null');
      expect(response.body.routing.fallbacksUsed).toContain('null');

      // Verify audit log contains failure and fallback entries
      const auditEntries = await auditLog.getEntriesByTaskId(response.body.taskId);
      const failureEntry = auditEntries.find((e) => e.eventType === 'PROVIDER_FAILED');
      expect(failureEntry).toBeDefined();
    });

    test('should return error when all providers fail', async () => {
      // Mock all provider failures
      nock('https://api.anthropic.com')
        .post('/v1/messages')
        .reply(500, { error: 'Service unavailable' });

      nock('http://localhost:11434').get('/api/tags').reply(500, { error: 'Connection refused' });

      // Disable null provider for this test
      featureFlags.setOverride('NULL_PROVIDER_ENABLED', false);

      const taskRequest = {
        type: AgentTaskType.SENTIMENT_ANALYSIS,
        input: {
          content: 'Test content for complete failure scenario',
        },
        config: {
          preferredProvider: 'claude',
          fallbackProviders: ['ollama'],
        },
      };

      const response = await request(app)
        .post('/api/v1/tasks/submit')
        .send(taskRequest)
        .expect(503);

      expect(response.body.success).toBe(false);
      expect(response.body.error.code).toBe('PROVIDER_UNAVAILABLE');

      // Re-enable null provider
      featureFlags.setOverride('NULL_PROVIDER_ENABLED', true);
    });

    test('should handle timeout scenarios', async () => {
      // Mock slow Claude API response
      nock('https://api.anthropic.com')
        .post('/v1/messages')
        .delay(2000) // 2 second delay
        .reply(200, {
          /* response */
        });

      const taskRequest = {
        type: AgentTaskType.SENTIMENT_ANALYSIS,
        input: {
          content: 'Test content for timeout scenario',
        },
        config: {
          timeout: 1000, // 1 second timeout
          preferredProvider: 'claude',
        },
      };

      const response = await request(app)
        .post('/api/v1/tasks/submit')
        .send(taskRequest)
        .expect(408);

      expect(response.body.success).toBe(false);
      expect(response.body.error.code).toBe('TIMEOUT_ERROR');
      expect(response.body.error.retryable).toBe(true);
    });
  });

  describe('Rate Limiting and Validation', () => {
    test('should enforce rate limiting for free tier', async () => {
      const taskRequest = {
        type: AgentTaskType.SENTIMENT_ANALYSIS,
        input: {
          content: 'Test rate limiting',
        },
        config: {
          preferredProvider: 'null',
        },
      };

      // Make requests up to the free tier limit (10 per minute)
      const requests = [];
      for (let i = 0; i < 12; i++) {
        requests.push(
          request(app)
            .post('/api/v1/tasks/submit')
            .set('X-User-Tier', 'free')
            .set('X-User-Id', 'rate-limit-test-user')
            .send(taskRequest)
        );
      }

      const responses = await Promise.all(requests);

      // First 10 should succeed, last 2 should be rate limited
      const successCount = responses.filter((r) => r.status === 200).length;
      const rateLimitedCount = responses.filter((r) => r.status === 429).length;

      expect(successCount).toBe(10);
      expect(rateLimitedCount).toBe(2);

      // Verify rate limited responses have proper structure
      const rateLimitedResponse = responses.find((r) => r.status === 429);
      expect(rateLimitedResponse?.body.error.code).toBe('RATE_LIMIT_EXCEEDED');
      expect(rateLimitedResponse?.headers['retry-after']).toBeDefined();
    });

    test('should validate request schema', async () => {
      const invalidRequest = {
        type: 'INVALID_TYPE',
        input: {
          // Missing required content field
        },
      };

      const response = await request(app)
        .post('/api/v1/tasks/submit')
        .send(invalidRequest)
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error.code).toBe('VALIDATION_ERROR');
    });
  });

  describe('Metrics and Monitoring', () => {
    test('should track task lifecycle metrics', async () => {
      const initialMetrics = metrics.getAll();
      const initialRequestCount = initialMetrics.systemMetrics.totalRequests;

      const taskRequest = {
        type: AgentTaskType.SENTIMENT_ANALYSIS,
        input: {
          content: 'Test metrics tracking',
        },
        config: {
          preferredProvider: 'null',
        },
      };

      await request(app).post('/api/v1/tasks/submit').send(taskRequest).expect(200);

      // Check that metrics were updated
      const updatedMetrics = metrics.getAll();
      expect(updatedMetrics.systemMetrics.totalRequests).toBe(initialRequestCount + 1);
      expect(updatedMetrics.systemMetrics.successfulRequests).toBeGreaterThan(0);

      // Check lifecycle events were recorded
      const lifecycleEvents = updatedMetrics.lifecycleEvents;
      expect(lifecycleEvents.some((e) => e.event === TaskLifecycleEvent.TASK_SUBMITTED)).toBe(true);
      expect(lifecycleEvents.some((e) => e.event === TaskLifecycleEvent.TASK_COMPLETED)).toBe(true);
    });

    test('should generate Prometheus metrics format', async () => {
      await request(app)
        .post('/api/v1/tasks/submit')
        .send({
          type: AgentTaskType.SENTIMENT_ANALYSIS,
          input: { content: 'Test prometheus metrics' },
          config: { preferredProvider: 'null' },
        })
        .expect(200);

      const prometheusOutput = metrics.prometheus();
      expect(prometheusOutput).toContain('system_total_requests');
      expect(prometheusOutput).toContain('system_success_rate');
    });
  });

  describe('Response Caching', () => {
    test('should cache and return identical requests', async () => {
      const taskRequest = {
        type: AgentTaskType.SENTIMENT_ANALYSIS,
        input: {
          content: 'This exact content should be cached',
        },
        config: {
          preferredProvider: 'null',
          temperature: 0.5,
        },
      };

      // First request
      const response1 = await request(app)
        .post('/api/v1/tasks/submit')
        .send(taskRequest)
        .expect(200);

      // Second identical request (should be cached)
      const response2 = await request(app)
        .post('/api/v1/tasks/submit')
        .send(taskRequest)
        .expect(200);

      // Results should be identical
      expect(response1.body.result.output).toEqual(response2.body.result.output);

      // But audit information should be different
      expect(response1.body.audit.requestId).not.toBe(response2.body.audit.requestId);
    });
  });

  describe('Health Check Endpoint', () => {
    test('should return health status', async () => {
      const response = await request(app).get('/api/v1/tasks/health').expect(200);

      expect(response.body).toMatchObject({
        status: 'healthy',
        timestamp: expect.any(String),
        dependencies: {
          router: 'healthy',
          auditLog: 'healthy',
        },
        metrics: expect.any(Object),
      });
    });
  });

  describe('Metrics Endpoint', () => {
    test('should require API key for metrics endpoint', async () => {
      await request(app).get('/api/v1/tasks/metrics').expect(401);
    });

    test('should return metrics with valid API key', async () => {
      // Set test API key
      process.env.METRICS_API_KEY = process.env.UNKNOWN;

      const response = await request(app)
        .get('/api/v1/tasks/metrics')
        .set('X-API-Key', 'test-metrics-key')
        .expect(200);

      expect(response.body).toHaveProperty('counters');
      expect(response.body).toHaveProperty('gauges');
      expect(response.body).toHaveProperty('systemMetrics');
    });
  });
});
