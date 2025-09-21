/**
 * PAKE System - APE (Automatic Prompt Experiments) Tests
 *
 * Comprehensive test suite for A/B testing framework, prompt variants,
 * statistical analysis, and experiment lifecycle management.
 */

import {
  describe,
  beforeEach,
  afterEach,
  it,
  expect,
  jest,
} from '@jest/globals';
import { APEEngine, ExperimentStatus, PromptVariant } from '../src/ape';
import { ScorecardEvaluator } from '../src/scorecards';

describe('APEEngine', () => {
  let apeEngine: APEEngine;
  let mockScorecard: ScorecardEvaluator;

  const basePromptVariants: Omit<PromptVariant, 'id'>[] = [
    {
      name: 'Control',
      prompt: 'Please analyze the following text and provide insights.',
      parameters: {
        temperature: 0.7,
        maxTokens: 1000,
        topP: 1.0,
        frequencyPenalty: 0.0,
        presencePenalty: 0.0,
      },
      trafficAllocation: 50,
      isControl: true,
      metadata: {
        generationMethod: 'manual',
      },
    },
    {
      name: 'Variant A',
      prompt:
        'Analyze this text thoroughly and provide detailed insights with examples.',
      parameters: {
        temperature: 0.5,
        maxTokens: 1000,
        topP: 1.0,
        frequencyPenalty: 0.0,
        presencePenalty: 0.0,
      },
      trafficAllocation: 50,
      isControl: false,
      metadata: {
        generationMethod: 'manual',
      },
    },
  ];

  beforeEach(() => {
    // Mock scorecard evaluator
    mockScorecard = {
      evaluate: jest.fn().mockResolvedValue({
        overallScore: 0.75,
        overallGrade: 'B' as const,
        categoryScores: {},
        criterionScores: new Map(),
        quality: {
          confidence: 0.8,
          completeness: 1.0,
          consistency: 0.85,
          reliability: 0.8,
        },
        metadata: {
          scorecardId: process.env.UNKNOWN,
          scorecardVersion: '1.0',
          evaluationId: 'eval-001',
          timestamp: new Date(),
          processingTime: 100,
          evaluatorVersions: {},
        },
        feedback: {
          strengths: ['Good analysis'],
          weaknesses: [],
          suggestions: [],
          criticalIssues: [],
        },
      }),
    } as any;

    apeEngine = new APEEngine(mockScorecard);
  });

  afterEach(() => {
    apeEngine.cleanup();
  });

  describe('Experiment Creation', () => {
    it('should create experiment with valid variants', async () => {
      const experiment = await apeEngine.createExperiment(
        'Test Experiment',
        'Testing prompt variations for analysis tasks',
        basePromptVariants,
        {
          evaluation: {
            scorecardIds: ['general_quality'],
          },
        },
        {
          hypothesis: 'More detailed prompts will improve quality',
        }
      );

      expect(experiment).toBeDefined();
      expect(experiment.id).toMatch(/^exp_/);
      expect(experiment.name).toBe('Test Experiment');
      expect(experiment.status).toBe(ExperimentStatus.DRAFT);
      expect(experiment.variants).toHaveLength(2);
      expect(experiment.variants[0].id).toBeDefined();
      expect(experiment.variants[1].id).toBeDefined();
    });

    it('should validate traffic allocation', async () => {
      const invalidVariants = [
        { ...basePromptVariants[0], trafficAllocation: 60 },
        { ...basePromptVariants[1], trafficAllocation: 50 }, // Total > 100
      ];

      await expect(
        apeEngine.createExperiment(
          'Invalid Experiment',
          'Test invalid traffic allocation',
          invalidVariants
        )
      ).rejects.toThrow('Traffic allocation must sum to 100%');
    });

    it('should require at least one control variant', async () => {
      const noControlVariants = basePromptVariants.map(v => ({
        ...v,
        isControl: false,
      }));

      await expect(
        apeEngine.createExperiment(
          'No Control Experiment',
          'Test without control',
          noControlVariants
        )
      ).rejects.toThrow();
    });

    it('should generate variant IDs automatically', async () => {
      const experiment = await apeEngine.createExperiment(
        'ID Test',
        'Testing ID generation',
        basePromptVariants
      );

      const variantIds = experiment.variants.map(v => v.id);
      expect(variantIds).toHaveLength(2);
      expect(variantIds[0]).not.toBe(variantIds[1]);
      expect(variantIds.every(id => id.includes(experiment.id))).toBe(true);
    });
  });

  describe('Variant Generation', () => {
    it('should generate prompt variants automatically', async () => {
      const basePrompt = 'Analyze this data and provide insights.';
      const variants = await apeEngine.generateVariants(basePrompt, 3);

      expect(variants).toHaveLength(4); // 3 + 1 control
      expect(variants.find(v => v.isControl)).toBeDefined();
      expect(variants.filter(v => !v.isControl)).toHaveLength(3);

      // Check that variants are actually different
      const prompts = variants.map(v => v.prompt);
      const uniquePrompts = new Set(prompts);
      expect(uniquePrompts.size).toBe(variants.length);
    });

    it('should use different generation strategies', async () => {
      const variants = await apeEngine.generateVariants('Test prompt', 2, [
        'temperature',
        'rephrase',
      ]);

      expect(variants).toHaveLength(3); // 2 + control

      const nonControlVariants = variants.filter(v => !v.isControl);
      expect(nonControlVariants[0].name).toContain('temperature');
      expect(nonControlVariants[1].name).toContain('rephrase');

      // Temperature variant should have different temperature
      const tempVariant = nonControlVariants.find(v =>
        v.name.includes('temperature')
      );
      const controlVariant = variants.find(v => v.isControl);

      expect(tempVariant?.parameters.temperature).not.toBe(
        controlVariant?.parameters.temperature
      );
    });

    it('should handle empty or invalid base prompts', async () => {
      await expect(apeEngine.generateVariants('', 2)).resolves.toBeDefined();

      const variants = await apeEngine.generateVariants('Very short', 1);
      expect(variants).toHaveLength(2); // 1 + control
    });
  });

  describe('Experiment Lifecycle', () => {
    let testExperiment: any;

    beforeEach(async () => {
      testExperiment = await apeEngine.createExperiment(
        'Lifecycle Test',
        'Testing experiment lifecycle',
        basePromptVariants,
        {
          evaluation: {
            scorecardIds: ['general_quality'],
          },
          sampling: {
            minSampleSize: 5,
            maxSampleSize: 100,
          },
        }
      );
    });

    it('should start experiment successfully', async () => {
      await apeEngine.startExperiment(testExperiment.id);

      const activeExperiments = apeEngine.getActiveExperiments();
      const startedExperiment = activeExperiments.find(
        e => e.id === testExperiment.id
      );

      expect(startedExperiment).toBeDefined();
      expect(startedExperiment?.status).toBe(ExperimentStatus.RUNNING);
      expect(startedExperiment?.results.startTime).toBeDefined();
    });

    it('should prevent starting invalid experiments', async () => {
      await expect(
        apeEngine.startExperiment('non-existent-id')
      ).rejects.toThrow('Experiment not found');
    });

    it('should evaluate prompts and record results', async () => {
      await apeEngine.startExperiment(testExperiment.id);

      const input = 'Sample input for testing';
      const result = await apeEngine.evaluatePrompt(testExperiment.id, input);

      expect(result).toBeDefined();
      expect(result.variantId).toBeDefined();
      expect(result.result).toBeDefined();
      expect(result.result.overallScore).toBeGreaterThanOrEqual(0);
      expect(result.result.overallScore).toBeLessThanOrEqual(1);
    });

    it('should stop experiment and analyze results', async () => {
      await apeEngine.startExperiment(testExperiment.id);

      // Run some evaluations
      for (let i = 0; i < 10; i++) {
        await apeEngine.evaluatePrompt(testExperiment.id, `Test input ${i}`);
      }

      const results = await apeEngine.stopExperiment(
        testExperiment.id,
        'manual'
      );

      expect(results.status).toBe('completed');
      expect(results.endTime).toBeDefined();
      expect(results.totalSamples).toBeGreaterThan(0);
      expect(results.statisticalResults).toBeDefined();
    });
  });

  describe('Statistical Analysis', () => {
    let testExperiment: any;

    beforeEach(async () => {
      testExperiment = await apeEngine.createExperiment(
        'Statistical Test',
        'Testing statistical analysis',
        basePromptVariants,
        {
          evaluation: { scorecardIds: ['general_quality'] },
          sampling: { minSampleSize: 20, maxSampleSize: 200 },
          statistical: {
            confidenceLevel: 0.95,
            minimumDetectableEffect: 0.05,
          },
        }
      );

      await apeEngine.startExperiment(testExperiment.id);
    });

    it('should accumulate variant metrics correctly', async () => {
      // Mock different scores for different variants
      mockScorecard.evaluate = jest
        .fn()
        .mockResolvedValueOnce({ overallScore: 0.6, overallGrade: 'C' } as any) // Control
        .mockResolvedValueOnce({ overallScore: 0.8, overallGrade: 'B' } as any) // Variant A
        .mockResolvedValueOnce({ overallScore: 0.7, overallGrade: 'B' } as any); // Control

      await apeEngine.evaluatePrompt(testExperiment.id, 'test 1');
      await apeEngine.evaluatePrompt(testExperiment.id, 'test 2');
      await apeEngine.evaluatePrompt(testExperiment.id, 'test 3');

      const results = apeEngine.getExperimentResults(testExperiment.id);

      expect(results).toBeDefined();
      expect(results?.totalSamples).toBe(3);
      expect(results?.variantMetrics.size).toBeGreaterThan(0);

      // Check that metrics are being accumulated
      for (const [variantId, metrics] of results!.variantMetrics) {
        expect(metrics.sampleSize).toBeGreaterThan(0);
        expect(metrics.performance.averageScore).toBeGreaterThanOrEqual(0);
        expect(metrics.performance.averageScore).toBeLessThanOrEqual(1);
      }
    });

    it('should calculate statistical significance', async () => {
      // Generate enough samples with clear difference
      mockScorecard.evaluate = jest.fn().mockImplementation(() =>
        Promise.resolve({
          overallScore: Math.random() > 0.5 ? 0.9 : 0.5, // Bimodal distribution
          overallGrade: 'B' as const,
          categoryScores: {},
          criterionScores: new Map(),
          quality: {
            confidence: 0.8,
            completeness: 1,
            consistency: 0.8,
            reliability: 0.8,
          },
          metadata: {
            scorecardId: process.env.UNKNOWN,
            scorecardVersion: '1.0',
            evaluationId: process.env.UNKNOWN,
            timestamp: new Date(),
            processingTime: 100,
            evaluatorVersions: {},
          },
          feedback: {
            strengths: [],
            weaknesses: [],
            suggestions: [],
            criticalIssues: [],
          },
        })
      );

      // Run many evaluations
      for (let i = 0; i < 50; i++) {
        await apeEngine.evaluatePrompt(testExperiment.id, `test ${i}`);
      }

      const results = await apeEngine.stopExperiment(testExperiment.id);

      expect(results.statisticalResults.significanceTest).toBeDefined();
      expect(
        results.statisticalResults.significanceTest.pValue
      ).toBeGreaterThanOrEqual(0);
      expect(
        results.statisticalResults.significanceTest.pValue
      ).toBeLessThanOrEqual(1);
      expect(results.statisticalResults.effectSize).toBeGreaterThanOrEqual(0);
    });
  });

  describe('Performance and Scalability', () => {
    it('should handle multiple concurrent experiments', async () => {
      const experiments = await Promise.all([
        apeEngine.createExperiment('Exp 1', 'Test 1', basePromptVariants),
        apeEngine.createExperiment('Exp 2', 'Test 2', basePromptVariants),
        apeEngine.createExperiment('Exp 3', 'Test 3', basePromptVariants),
      ]);

      for (const exp of experiments) {
        await apeEngine.startExperiment(exp.id);
      }

      const activeExperiments = apeEngine.getActiveExperiments();
      expect(activeExperiments).toHaveLength(3);

      // Should be able to evaluate all experiments concurrently
      const evaluationPromises = experiments.map(exp =>
        apeEngine.evaluatePrompt(exp.id, 'concurrent test')
      );

      const results = await Promise.all(evaluationPromises);
      expect(results).toHaveLength(3);
      results.forEach(result => {
        expect(result.result).toBeDefined();
      });
    });

    it('should process evaluations efficiently', async () => {
      const experiment = await apeEngine.createExperiment(
        'Performance Test',
        'Testing performance',
        basePromptVariants,
        {
          evaluation: { scorecardIds: ['general_quality'] },
        }
      );

      await apeEngine.startExperiment(experiment.id);

      const startTime = Date.now();
      const evaluationPromises = Array.from({ length: 20 }, (_, i) =>
        apeEngine.evaluatePrompt(experiment.id, `performance test ${i}`)
      );

      await Promise.all(evaluationPromises);
      const processingTime = Date.now() - startTime;

      expect(processingTime).toBeLessThan(10000); // Should complete within 10s

      const results = apeEngine.getExperimentResults(experiment.id);
      expect(results?.totalSamples).toBe(20);
    });

    it('should track performance metrics correctly', async () => {
      const experiment = await apeEngine.createExperiment(
        'Metrics Test',
        'Testing metrics',
        basePromptVariants
      );

      await apeEngine.startExperiment(experiment.id);
      await apeEngine.evaluatePrompt(experiment.id, 'metrics test');
      await apeEngine.stopExperiment(experiment.id);

      const stats = apeEngine.getPerformanceStats();

      expect(stats.totalExperiments).toBeGreaterThan(0);
      expect(stats.completedExperiments).toBeGreaterThan(0);
      expect(stats.averageSuccessRate).toBeGreaterThanOrEqual(0);
      expect(stats.averageSuccessRate).toBeLessThanOrEqual(1);
    });
  });

  describe('Error Handling and Edge Cases', () => {
    it('should handle scorecard evaluation failures', async () => {
      mockScorecard.evaluate = jest
        .fn()
        .mockRejectedValue(new Error('Evaluation failed'));

      const experiment = await apeEngine.createExperiment(
        'Error Test',
        'Testing error handling',
        basePromptVariants
      );

      await apeEngine.startExperiment(experiment.id);

      await expect(
        apeEngine.evaluatePrompt(experiment.id, 'error test')
      ).rejects.toThrow('Failed to evaluate content quality');
    });

    it('should handle invalid experiment IDs gracefully', async () => {
      await expect(
        apeEngine.evaluatePrompt('invalid-id', 'test')
      ).rejects.toThrow('Experiment not available');

      await expect(apeEngine.stopExperiment('invalid-id')).rejects.toThrow(
        'Experiment not found'
      );
    });

    it('should handle empty or invalid inputs', async () => {
      const experiment = await apeEngine.createExperiment(
        'Input Test',
        'Testing invalid inputs',
        basePromptVariants
      );

      await apeEngine.startExperiment(experiment.id);

      // Should handle empty input
      await expect(
        apeEngine.evaluatePrompt(experiment.id, '')
      ).resolves.toBeDefined();

      // Should handle null/undefined context
      await expect(
        apeEngine.evaluatePrompt(experiment.id, 'test', undefined)
      ).resolves.toBeDefined();
    });
  });

  describe('Experiment Configuration', () => {
    it('should respect sampling configuration', async () => {
      const experiment = await apeEngine.createExperiment(
        'Sampling Test',
        'Testing sampling config',
        basePromptVariants,
        {
          sampling: {
            minSampleSize: 5,
            maxSampleSize: 10,
            sampleRatio: [30, 70], // Uneven split
          },
        }
      );

      expect(experiment.config.sampling.minSampleSize).toBe(5);
      expect(experiment.config.sampling.maxSampleSize).toBe(10);
      expect(experiment.config.sampling.sampleRatio).toEqual([30, 70]);
    });

    it('should handle duration limits', async () => {
      const shortExperiment = await apeEngine.createExperiment(
        'Duration Test',
        'Testing duration limits',
        basePromptVariants,
        {
          duration: {
            maxDurationHours: 0.001, // Very short duration
            minDurationHours: 0,
            earlyStoppingEnabled: true,
          },
        }
      );

      await apeEngine.startExperiment(shortExperiment.id);

      // Wait for duration to exceed
      await new Promise(resolve => setTimeout(resolve, 100));

      // Check if experiment auto-stops (implementation dependent)
      const results = apeEngine.getExperimentResults(shortExperiment.id);
      expect(results).toBeDefined();
    });
  });

  describe('Data Quality and Validation', () => {
    it('should validate experiment results structure', async () => {
      const experiment = await apeEngine.createExperiment(
        'Validation Test',
        'Testing result validation',
        basePromptVariants
      );

      await apeEngine.startExperiment(experiment.id);
      await apeEngine.evaluatePrompt(experiment.id, 'validation test');
      const results = await apeEngine.stopExperiment(experiment.id);

      // Validate complete results structure
      expect(results).toHaveProperty('status');
      expect(results).toHaveProperty('startTime');
      expect(results).toHaveProperty('endTime');
      expect(results).toHaveProperty('totalSamples');
      expect(results).toHaveProperty('variantSamples');
      expect(results).toHaveProperty('variantMetrics');
      expect(results).toHaveProperty('statisticalResults');
      expect(results).toHaveProperty('qualityMetrics');

      expect(results.statisticalResults).toHaveProperty('significanceTest');
      expect(results.statisticalResults).toHaveProperty('recommendation');
    });

    it('should maintain data consistency across operations', async () => {
      const experiment = await apeEngine.createExperiment(
        'Consistency Test',
        'Testing data consistency',
        basePromptVariants
      );

      await apeEngine.startExperiment(experiment.id);

      // Run multiple evaluations
      const evaluationCount = 10;
      for (let i = 0; i < evaluationCount; i++) {
        await apeEngine.evaluatePrompt(experiment.id, `consistency test ${i}`);
      }

      const results = apeEngine.getExperimentResults(experiment.id);

      // Total samples should match evaluation count
      expect(results?.totalSamples).toBe(evaluationCount);

      // Sum of variant samples should equal total samples
      const variantSampleSum = Array.from(
        results!.variantSamples.values()
      ).reduce((sum, count) => sum + count, 0);
      expect(variantSampleSum).toBe(evaluationCount);
    });
  });
});

// Helper function to create deterministic test data
function createTestPromptVariant(
  id: string,
  overrides: Partial<Omit<PromptVariant, 'id'>> = {}
): Omit<PromptVariant, 'id'> {
  return {
    name: `Test Variant ${id}`,
    prompt: `Test prompt ${id}`,
    parameters: {
      temperature: 0.7,
      maxTokens: 1000,
      topP: 1.0,
      frequencyPenalty: 0.0,
      presencePenalty: 0.0,
    },
    trafficAllocation: 50,
    isControl: false,
    metadata: {
      generationMethod: 'manual',
    },
    ...overrides,
  };
}
