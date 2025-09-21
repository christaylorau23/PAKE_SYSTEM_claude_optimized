/**
 * Contract Tests for NullProvider
 *
 * These tests ensure the NullProvider adheres to the AgentProvider interface contract
 * and produces outputs that conform to the expected JSON schemas.
 */

import { NullProvider } from '../../src/providers/NullProvider';
import {
  AgentProvider,
  AgentCapability,
  AgentExecutionError,
} from '../../src/providers/AgentProvider';
import { AgentTask, AgentResult, AgentTaskType, AgentResultStatus } from '../../src/types';

// Import JSON schemas for validation
const AgentTaskSchema = require('../../src/schemas/AgentTask.json');
const AgentResultSchema = require('../../src/schemas/AgentResult.json');

describe('NullProvider Contract Tests', () => {
  let provider: NullProvider;

  beforeEach(() => {
    provider = new NullProvider();
  });

  afterEach(async () => {
    await provider.dispose();
  });

  describe('AgentProvider Interface Compliance', () => {
    it('should implement all required interface methods', () => {
      expect(typeof provider.run).toBe('function');
      expect(typeof provider.healthCheck).toBe('function');
      expect(typeof provider.dispose).toBe('function');
    });

    it('should have required metadata properties', () => {
      expect(typeof provider.name).toBe('string');
      expect(provider.name.length).toBeGreaterThan(0);

      expect(typeof provider.version).toBe('string');
      expect(provider.version).toMatch(/^\d+\.\d+\.\d+$/);

      expect(Array.isArray(provider.capabilities)).toBe(true);
      expect(provider.capabilities.length).toBeGreaterThan(0);
    });

    it('should return Promise from async methods', () => {
      const task: AgentTask = {
        id: 'contract_test',
        type: AgentTaskType.SENTIMENT_ANALYSIS,
        input: { content: process.env.UNKNOWN },
        config: {},
        metadata: { source: 'contract_test', createdAt: new Date().toISOString() },
      };

      const runPromise = provider.run(task);
      const healthPromise = provider.healthCheck();
      const disposePromise = provider.dispose();

      expect(runPromise).toBeInstanceOf(Promise);
      expect(healthPromise).toBeInstanceOf(Promise);
      expect(disposePromise).toBeInstanceOf(Promise);

      // Clean up
      return disposePromise;
    });
  });

  describe('Input Validation Contract', () => {
    it('should handle valid AgentTask input', async () => {
      const validTask: AgentTask = {
        id: 'valid_task_001',
        type: AgentTaskType.CONTENT_ANALYSIS,
        input: {
          content: 'This is valid test content for analysis.',
          data: { language: 'en', domain: process.env.UNKNOWN },
        },
        config: {
          timeout: 30000,
          priority: 5,
          parameters: { includeMetrics: true },
        },
        metadata: {
          source: 'contract_test_suite',
          createdAt: '2024-01-01T12:00:00Z',
          correlationId: 'contract_001',
          userId: 'test_user',
        },
      };

      const result = await provider.run(validTask);
      expect(result).toBeDefined();
      expect(result.taskId).toBe(validTask.id);
    });

    it('should handle minimal valid task', async () => {
      const minimalTask: AgentTask = {
        id: 'minimal_task',
        type: AgentTaskType.SENTIMENT_ANALYSIS,
        input: {},
        config: {},
        metadata: {
          source: process.env.UNKNOWN,
          createdAt: new Date().toISOString(),
        },
      };

      const result = await provider.run(minimalTask);
      expect(result).toBeDefined();
      expect(result.status).toBe(AgentResultStatus.SUCCESS);
    });

    it('should handle empty content gracefully', async () => {
      const emptyContentTask: AgentTask = {
        id: 'empty_content',
        type: AgentTaskType.TEXT_ANALYSIS,
        input: { content: '' },
        config: {},
        metadata: { source: process.env.UNKNOWN, createdAt: new Date().toISOString() },
      };

      const result = await provider.run(emptyContentTask);
      expect(result.status).toBe(AgentResultStatus.SUCCESS);
    });

    it('should handle null/undefined content gracefully', async () => {
      const nullContentTask: AgentTask = {
        id: 'null_content',
        type: AgentTaskType.ENTITY_EXTRACTION,
        input: { content: undefined },
        config: {},
        metadata: { source: process.env.UNKNOWN, createdAt: new Date().toISOString() },
      };

      const result = await provider.run(nullContentTask);
      expect(result.status).toBe(AgentResultStatus.SUCCESS);
    });
  });

  describe('Output Schema Compliance', () => {
    it('should produce AgentResult conforming to schema structure', async () => {
      const task: AgentTask = {
        id: 'schema_test',
        type: AgentTaskType.SENTIMENT_ANALYSIS,
        input: { content: 'Schema compliance test' },
        config: { timeout: 15000 },
        metadata: { source: 'schema_test', createdAt: new Date().toISOString() },
      };

      const result = await provider.run(task);

      // Check required properties
      expect(result).toHaveProperty('taskId');
      expect(result).toHaveProperty('status');
      expect(result).toHaveProperty('output');
      expect(result).toHaveProperty('metadata');

      expect(typeof result.taskId).toBe('string');
      expect(Object.values(AgentResultStatus)).toContain(result.status);
      expect(typeof result.output).toBe('object');
      expect(typeof result.metadata).toBe('object');
    });

    it('should include required metadata fields', async () => {
      const task: AgentTask = {
        id: 'metadata_test',
        type: AgentTaskType.CONTENT_ANALYSIS,
        input: { content: 'Metadata test' },
        config: {},
        metadata: { source: process.env.UNKNOWN, createdAt: new Date().toISOString() },
      };

      const result = await provider.run(task);
      const metadata = result.metadata;

      expect(metadata).toHaveProperty('provider');
      expect(metadata).toHaveProperty('startTime');
      expect(metadata).toHaveProperty('endTime');
      expect(metadata).toHaveProperty('duration');

      expect(typeof metadata.provider).toBe('string');
      expect(typeof metadata.startTime).toBe('string');
      expect(typeof metadata.endTime).toBe('string');
      expect(typeof metadata.duration).toBe('number');

      // Validate timestamp formats
      expect(() => new Date(metadata.startTime)).not.toThrow();
      expect(() => new Date(metadata.endTime)).not.toThrow();
      expect(metadata.duration).toBeGreaterThan(0);
    });

    it('should include confidence scores within valid range', async () => {
      const task: AgentTask = {
        id: 'confidence_test',
        type: AgentTaskType.SENTIMENT_ANALYSIS,
        input: { content: 'Confidence test' },
        config: {},
        metadata: { source: process.env.UNKNOWN, createdAt: new Date().toISOString() },
      };

      const result = await provider.run(task);

      if (result.metadata.confidence !== undefined) {
        expect(result.metadata.confidence).toBeWithinRange(0, 1);
      }

      if (result.output.sentiment?.confidence !== undefined) {
        expect(result.output.sentiment.confidence).toBeWithinRange(0, 1);
      }
    });

    it('should include usage metrics when available', async () => {
      const task: AgentTask = {
        id: 'usage_test',
        type: AgentTaskType.ENTITY_EXTRACTION,
        input: { content: 'Usage metrics test content' },
        config: {},
        metadata: { source: process.env.UNKNOWN, createdAt: new Date().toISOString() },
      };

      const result = await provider.run(task);

      if (result.metadata.usage) {
        const usage = result.metadata.usage;

        if (usage.tokens !== undefined) {
          expect(typeof usage.tokens).toBe('number');
          expect(usage.tokens).toBeGreaterThanOrEqual(0);
        }

        if (usage.apiCalls !== undefined) {
          expect(typeof usage.apiCalls).toBe('number');
          expect(usage.apiCalls).toBeGreaterThanOrEqual(0);
        }

        if (usage.memoryMb !== undefined) {
          expect(typeof usage.memoryMb).toBe('number');
          expect(usage.memoryMb).toBeGreaterThanOrEqual(0);
        }
      }
    });
  });

  describe('Entity Extraction Contract', () => {
    it('should return valid entity structure', async () => {
      const task: AgentTask = {
        id: 'entity_contract',
        type: AgentTaskType.ENTITY_EXTRACTION,
        input: { content: 'Dr. John Smith works at Microsoft in Seattle.' },
        config: {},
        metadata: { source: process.env.UNKNOWN, createdAt: new Date().toISOString() },
      };

      const result = await provider.run(task);

      if (result.output.entities) {
        expect(Array.isArray(result.output.entities)).toBe(true);

        result.output.entities.forEach((entity) => {
          expect(entity).toHaveProperty('type');
          expect(entity).toHaveProperty('value');
          expect(entity).toHaveProperty('confidence');

          expect(typeof entity.type).toBe('string');
          expect(typeof entity.value).toBe('string');
          expect(typeof entity.confidence).toBe('number');
          expect(entity.confidence).toBeWithinRange(0, 1);

          if (entity.span) {
            expect(typeof entity.span.start).toBe('number');
            expect(typeof entity.span.end).toBe('number');
            expect(entity.span.start).toBeLessThanOrEqual(entity.span.end);
          }
        });
      }
    });
  });

  describe('Sentiment Analysis Contract', () => {
    it('should return valid sentiment structure', async () => {
      const task: AgentTask = {
        id: 'sentiment_contract',
        type: AgentTaskType.SENTIMENT_ANALYSIS,
        input: { content: 'I absolutely love this new product!' },
        config: {},
        metadata: { source: process.env.UNKNOWN, createdAt: new Date().toISOString() },
      };

      const result = await provider.run(task);

      if (result.output.sentiment) {
        const sentiment = result.output.sentiment;

        expect(sentiment).toHaveProperty('score');
        expect(sentiment).toHaveProperty('label');
        expect(sentiment).toHaveProperty('confidence');

        expect(typeof sentiment.score).toBe('number');
        expect(sentiment.score).toBeWithinRange(-1, 1);

        expect(typeof sentiment.label).toBe('string');
        expect(['positive', 'negative', 'neutral']).toContain(sentiment.label);

        expect(typeof sentiment.confidence).toBe('number');
        expect(sentiment.confidence).toBeWithinRange(0, 1);

        if (sentiment.emotions) {
          expect(typeof sentiment.emotions).toBe('object');
          Object.values(sentiment.emotions).forEach((emotionScore) => {
            expect(typeof emotionScore).toBe('number');
            expect(emotionScore).toBeWithinRange(0, 1);
          });
        }
      }
    });
  });

  describe('Trend Analysis Contract', () => {
    it('should return valid trend structure', async () => {
      const task: AgentTask = {
        id: 'trend_contract',
        type: AgentTaskType.TREND_DETECTION,
        input: { content: 'Artificial intelligence adoption is rising rapidly.' },
        config: {},
        metadata: { source: process.env.UNKNOWN, createdAt: new Date().toISOString() },
      };

      const result = await provider.run(task);

      if (result.output.trends) {
        expect(Array.isArray(result.output.trends)).toBe(true);

        result.output.trends.forEach((trend) => {
          expect(trend).toHaveProperty('topic');
          expect(trend).toHaveProperty('direction');
          expect(trend).toHaveProperty('strength');
          expect(trend).toHaveProperty('period');

          expect(typeof trend.topic).toBe('string');
          expect(['up', 'down', 'stable']).toContain(trend.direction);
          expect(typeof trend.strength).toBe('number');
          expect(trend.strength).toBeWithinRange(0, 1);

          expect(trend.period).toHaveProperty('start');
          expect(trend.period).toHaveProperty('end');
          expect(typeof trend.period.start).toBe('string');
          expect(typeof trend.period.end).toBe('string');

          // Validate timestamps
          expect(() => new Date(trend.period.start)).not.toThrow();
          expect(() => new Date(trend.period.end)).not.toThrow();

          if (trend.dataPoints) {
            expect(Array.isArray(trend.dataPoints)).toBe(true);
            trend.dataPoints.forEach((point) => {
              expect(point).toHaveProperty('timestamp');
              expect(point).toHaveProperty('value');
              expect(typeof point.timestamp).toBe('string');
              expect(typeof point.value).toBe('number');
            });
          }
        });
      }
    });
  });

  describe('Error Handling Contract', () => {
    it('should handle disposal state correctly', async () => {
      await provider.dispose();

      const task: AgentTask = {
        id: 'disposed_test',
        type: AgentTaskType.SENTIMENT_ANALYSIS,
        input: { content: process.env.UNKNOWN },
        config: {},
        metadata: { source: process.env.UNKNOWN, createdAt: new Date().toISOString() },
      };

      await expect(provider.run(task)).rejects.toThrow(AgentExecutionError);

      try {
        await provider.run(task);
      } catch (error) {
        if (error instanceof AgentExecutionError) {
          expect(error.code).toBe('PROVIDER_UNAVAILABLE');
          expect(error.provider).toBe('NullProvider');
          expect(error.task).toBe(task);
        }
      }
    });
  });

  describe('Performance Contract', () => {
    it('should complete within reasonable time limits', async () => {
      const task: AgentTask = {
        id: 'performance_test',
        type: AgentTaskType.CONTENT_ANALYSIS,
        input: { content: 'Performance test content' },
        config: { timeout: 5000 },
        metadata: { source: process.env.UNKNOWN, createdAt: new Date().toISOString() },
      };

      const startTime = Date.now();
      const result = await provider.run(task);
      const endTime = Date.now();

      const actualDuration = endTime - startTime;
      const reportedDuration = result.metadata.duration;

      // Should complete within configured timeout
      expect(actualDuration).toBeLessThan(5000);

      // Reported duration should be close to actual duration
      expect(Math.abs(reportedDuration - actualDuration)).toBeLessThan(100);
    });

    it('should handle concurrent requests', async () => {
      const tasks = Array.from({ length: 5 }, (_, i) => ({
        id: `concurrent_test_${i}`,
        type: AgentTaskType.SENTIMENT_ANALYSIS,
        input: { content: `Concurrent test message ${i}` },
        config: {},
        metadata: { source: process.env.UNKNOWN, createdAt: new Date().toISOString() },
      }));

      const startTime = Date.now();
      const results = await Promise.all(tasks.map((task) => provider.run(task)));
      const endTime = Date.now();

      expect(results).toHaveLength(5);
      results.forEach((result) => {
        expect(result.status).toBe(AgentResultStatus.SUCCESS);
      });

      // Concurrent execution should not take much longer than sequential
      expect(endTime - startTime).toBeLessThan(2000);
    });
  });
});
