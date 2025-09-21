import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { CostControls } from '../core/CostControls';
import {
  CostControlsConfig,
  SecurityContext,
  BudgetExceededError,
} from '../types/security.types';

describe('Cost Controls', () => {
  let costControls: CostControls;
  let config: CostControlsConfig;
  let mockContext: SecurityContext;

  beforeEach(() => {
    config = {
      enabled: true,
      defaultTokenBudget: 10000,
      budgetPeriod: 'daily',
      throttleThreshold: 0.8,
      alertThresholds: [0.5, 0.75, 0.9],
      overagePolicy: 'throttle',
      costTracking: {
        trackTokens: true,
        trackRequests: true,
        trackComputeTime: true,
        costPerToken: {
          'gpt-4': 0.00003,
          'gpt-3.5-turbo': 0.000002,
          'claude-3-opus': 0.000015,
        },
        costPerRequest: {
          'gpt-4': 0.01,
          'gpt-3.5-turbo': 0.001,
        },
        costPerSecond: {
          'gpt-4': 0.0001,
          'gpt-3.5-turbo': 0.00001,
        },
      },
    };

    mockContext = {
      userId: 'test-user',
      sessionId: 'test-session',
      requestId: 'test-request',
      modelType: 'gpt-4',
      inputTokens: 100,
      outputTokens: 200,
      startTime: new Date(),
      endTime: new Date(Date.now() + 1000),
      threats: [],
      cost: 0.01,
    };

    costControls = new CostControls(config);
  });

  afterEach(() => {
    costControls.cleanup();
    vi.clearAllMocks();
  });

  describe('Token Budget Management', () => {
    it('should create default budget for new users', async () => {
      const result = await costControls.checkBudget('new-user', 100, 'gpt-4');

      expect(result.allowed).toBe(true);
      expect(result.budget.userId).toBe('new-user');
      expect(result.budget.budget).toBe(10000);
      expect(result.budget.used).toBe(0);
      expect(result.budget.remaining).toBe(10000);
      expect(result.budget.period).toBe('daily');
    });

    it('should track token usage accurately', async () => {
      const userId = 'usage-test-user';
      const inputTokens = 150;
      const outputTokens = 300;

      const metrics = await costControls.recordUsage(
        userId,
        inputTokens,
        outputTokens,
        'gpt-4',
        mockContext
      );

      expect(metrics.tokensUsed).toBe(450);
      expect(metrics.estimatedCost).toBeGreaterThan(0);
      expect(metrics.requestCount).toBe(1);

      // Check budget was updated
      const checkResult = await costControls.checkBudget(userId, 0, 'gpt-4');
      expect(checkResult.budget.used).toBe(450);
      expect(checkResult.budget.remaining).toBe(9550);
    });

    it('should enforce budget limits', async () => {
      const userId = 'budget-limit-user';

      // Set a small budget
      costControls.setBudget(userId, 1000);

      // Try to use more than budget allows
      const result = await costControls.checkBudget(userId, 1200, 'gpt-4');

      expect(result.allowed).toBe(false);
      expect(result.budget.budget).toBe(1000);
    });

    it('should handle budget overage according to policy', async () => {
      const userId = 'overage-user';

      // Set small budget and block policy
      costControls.setBudget(userId, 500);
      costControls.updateConfig({ overagePolicy: 'block' });

      // Record usage that exceeds budget
      await expect(
        costControls.recordUsage(userId, 300, 400, 'gpt-4', mockContext)
      ).rejects.toThrow(BudgetExceededError);
    });

    it('should support different budget periods', async () => {
      const periods: Array<'hourly' | 'daily' | 'weekly' | 'monthly'> = [
        'hourly',
        'daily',
        'weekly',
        'monthly',
      ];

      for (const period of periods) {
        const periodConfig = { ...config, budgetPeriod: period };
        const periodControls = new CostControls(periodConfig);

        const result = await periodControls.checkBudget(
          `user-${period}`,
          100,
          'gpt-4'
        );

        expect(result.budget.period).toBe(period);
        expect(result.budget.periodStart).toBeInstanceOf(Date);
        expect(result.budget.periodEnd).toBeInstanceOf(Date);
        expect(result.budget.periodEnd.getTime()).toBeGreaterThan(
          result.budget.periodStart.getTime()
        );

        periodControls.cleanup();
      }
    });

    it('should reset budgets at period boundaries', async () => {
      const userId = 'reset-user';

      // Record some usage
      await costControls.recordUsage(userId, 100, 200, 'gpt-4', mockContext);

      let budget = await costControls.checkBudget(userId, 0, 'gpt-4');
      expect(budget.budget.used).toBe(300);

      // Manually trigger budget reset
      costControls['resetAllBudgets']();

      budget = await costControls.checkBudget(userId, 0, 'gpt-4');
      expect(budget.budget.used).toBe(0);
      expect(budget.budget.remaining).toBe(budget.budget.budget);
    });
  });

  describe('Token Counting and Cost Estimation', () => {
    it('should count tokens accurately for different models', () => {
      const testText = 'This is a test string for token counting accuracy.';

      const models = [
        'gpt-4',
        'gpt-3.5-turbo',
        'claude-3-opus',
        'unknown-model',
      ];

      for (const model of models) {
        const tokenCount = costControls.countTokens(testText, model);

        expect(tokenCount).toBeGreaterThan(0);
        expect(tokenCount).toBeLessThan(testText.length); // Should be more efficient than character count
      }
    });

    it('should estimate costs accurately for different models', () => {
      const tokenCount = 1000;

      // Test known models with different costs
      const gpt4Cost = costControls.estimateCost(tokenCount, 'gpt-4', 'output');
      const gpt35Cost = costControls.estimateCost(
        tokenCount,
        'gpt-3.5-turbo',
        'output'
      );
      const claudeCost = costControls.estimateCost(
        tokenCount,
        'claude-3-opus',
        'output'
      );

      expect(gpt4Cost).toBeGreaterThan(gpt35Cost); // GPT-4 should be more expensive
      expect(claudeCost).toBeGreaterThan(gpt35Cost); // Claude should be more expensive than GPT-3.5

      // Test input vs output costs
      const inputCost = costControls.estimateCost(tokenCount, 'gpt-4', 'input');
      const outputCost = costControls.estimateCost(
        tokenCount,
        'gpt-4',
        'output'
      );

      expect(outputCost).toBeGreaterThanOrEqual(inputCost); // Output typically costs more
    });

    it('should handle large token counts efficiently', () => {
      const largeText = 'This is a very long text string. '.repeat(1000); // ~35KB

      const startTime = performance.now();
      const tokenCount = costControls.countTokens(largeText, 'gpt-4');
      const duration = performance.now() - startTime;

      expect(tokenCount).toBeGreaterThan(1000);
      expect(duration).toBeLessThan(100); // Should count quickly even for large text
    });

    it('should provide fallback for unknown models', () => {
      const testText = 'Test text for unknown model';
      const tokenCount = costControls.countTokens(testText, 'unknown-model');
      const cost = costControls.estimateCost(1000, 'unknown-model');

      expect(tokenCount).toBeGreaterThan(0);
      expect(cost).toBeGreaterThan(0);
    });
  });

  describe('Throttling and Rate Limiting', () => {
    it('should throttle users approaching budget limits', async () => {
      const userId = 'throttle-user';

      // Set budget and use most of it
      costControls.setBudget(userId, 1000);
      await costControls.recordUsage(userId, 400, 400, 'gpt-4', mockContext); // 80% used

      const result = await costControls.checkBudget(userId, 100, 'gpt-4');

      expect(result.throttleStatus).toBeDefined();
      expect(result.throttleStatus?.isThrottled).toBe(true);
      expect(result.throttleStatus?.reason).toContain('throttle threshold');
      expect(result.throttleStatus?.retryAfter).toBeGreaterThan(0);
    });

    it('should calculate retry delays based on overage', async () => {
      const userId1 = 'delay-user-1';
      const userId2 = 'delay-user-2';

      // Set budgets
      costControls.setBudget(userId1, 1000);
      costControls.setBudget(userId2, 1000);

      // User 1: Slightly over threshold (85%)
      await costControls.recordUsage(userId1, 400, 450, 'gpt-4', mockContext);

      // User 2: Way over threshold (95%)
      await costControls.recordUsage(userId2, 450, 500, 'gpt-4', mockContext);

      const result1 = await costControls.checkBudget(userId1, 0, 'gpt-4');
      const result2 = await costControls.checkBudget(userId2, 0, 'gpt-4');

      expect(result1.throttleStatus?.retryAfter).toBeLessThan(
        result2.throttleStatus?.retryAfter!
      );
    });

    it('should clear throttle status when usage drops', async () => {
      const userId = 'clear-throttle-user';

      // Get throttled
      costControls.setBudget(userId, 1000);
      await costControls.recordUsage(userId, 400, 400, 'gpt-4', mockContext);

      const throttledResult = await costControls.checkBudget(
        userId,
        100,
        'gpt-4'
      );
      expect(throttledResult.throttleStatus?.isThrottled).toBe(true);

      // Clear throttle manually
      costControls.clearThrottle(userId);

      const clearedStatus = costControls.getThrottleStatus(userId);
      expect(clearedStatus).toBeNull();
    });
  });

  describe('Budget Alerts and Notifications', () => {
    it('should trigger alerts at configured thresholds', async () => {
      const userId = 'alert-user';
      const alertSpy = vi.fn();

      costControls.on('budgetAlert', alertSpy);
      costControls.setBudget(userId, 1000);

      // Trigger 50% alert
      await costControls.recordUsage(userId, 250, 250, 'gpt-4', mockContext);

      expect(alertSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          userId,
          threshold: 0.5,
          currentUsage: 500,
          budgetLimit: 1000,
          usagePercentage: 0.5,
        })
      );
    });

    it('should not duplicate alert notifications', async () => {
      const userId = 'duplicate-alert-user';
      const alertSpy = vi.fn();

      costControls.on('budgetAlert', alertSpy);
      costControls.setBudget(userId, 1000);

      // Cross 50% threshold multiple times
      await costControls.recordUsage(userId, 250, 250, 'gpt-4', mockContext);
      await costControls.recordUsage(userId, 50, 50, 'gpt-4', mockContext);
      await costControls.recordUsage(userId, 50, 50, 'gpt-4', mockContext);

      // Should only trigger alert once for 50% threshold
      const fiftyPercentAlerts = alertSpy.mock.calls.filter(
        call => call[0].threshold === 0.5
      );
      expect(fiftyPercentAlerts).toHaveLength(1);
    });

    it('should trigger multiple threshold alerts', async () => {
      const userId = 'multiple-alert-user';
      const alertSpy = vi.fn();

      costControls.on('budgetAlert', alertSpy);
      costControls.setBudget(userId, 1000);

      // Trigger multiple thresholds in one large usage
      await costControls.recordUsage(userId, 400, 500, 'gpt-4', mockContext); // 90% usage

      // Should trigger 50%, 75%, and 90% alerts
      expect(alertSpy).toHaveBeenCalledTimes(3);

      const thresholds = alertSpy.mock.calls.map(call => call[0].threshold);
      expect(thresholds).toContain(0.5);
      expect(thresholds).toContain(0.75);
      expect(thresholds).toContain(0.9);
    });
  });

  describe('Usage Analytics and Reporting', () => {
    it('should provide comprehensive usage metrics', async () => {
      const userId = 'metrics-user';

      // Record various usage
      await costControls.recordUsage(userId, 100, 200, 'gpt-4', mockContext);
      await costControls.recordUsage(
        userId,
        150,
        250,
        'gpt-3.5-turbo',
        mockContext
      );
      await costControls.recordUsage(
        userId,
        80,
        120,
        'claude-3-opus',
        mockContext
      );

      const metrics = await costControls.getUserUsageMetrics(userId, 7);

      expect(metrics.totalTokens).toBe(900); // 300 + 400 + 200
      expect(metrics.totalCost).toBeGreaterThan(0);
      expect(metrics.requestCount).toBe(3);
      expect(metrics.dailyBreakdown).toHaveLength.greaterThan(0);
      expect(metrics.modelBreakdown).toHaveLength(3);

      // Check model breakdown
      const gpt4Usage = metrics.modelBreakdown.find(m => m.model === 'gpt-4');
      expect(gpt4Usage?.tokens).toBe(300);
      expect(gpt4Usage?.requests).toBe(1);
    });

    it('should handle time-based filtering', async () => {
      const userId = 'time-filter-user';

      // Record usage
      await costControls.recordUsage(userId, 100, 100, 'gpt-4', mockContext);

      // Get metrics for different time periods
      const metrics1Day = await costControls.getUserUsageMetrics(userId, 1);
      const metrics7Days = await costControls.getUserUsageMetrics(userId, 7);
      const metrics30Days = await costControls.getUserUsageMetrics(userId, 30);

      expect(metrics1Day.totalTokens).toBe(200);
      expect(metrics7Days.totalTokens).toBe(200);
      expect(metrics30Days.totalTokens).toBe(200);

      // Daily breakdown should vary by period
      expect(metrics30Days.dailyBreakdown.length).toBeGreaterThanOrEqual(
        metrics7Days.dailyBreakdown.length
      );
    });

    it('should track cost accurately across different models', async () => {
      const userId = 'cost-tracking-user';

      const models = [
        { name: 'gpt-4', tokens: 1000 },
        { name: 'gpt-3.5-turbo', tokens: 2000 },
        { name: 'claude-3-opus', tokens: 1500 },
      ];

      let totalExpectedCost = 0;

      for (const model of models) {
        const inputTokens = Math.floor(model.tokens * 0.4);
        const outputTokens = Math.floor(model.tokens * 0.6);

        await costControls.recordUsage(
          userId,
          inputTokens,
          outputTokens,
          model.name,
          mockContext
        );

        totalExpectedCost += costControls.estimateCost(
          inputTokens,
          model.name,
          'input'
        );
        totalExpectedCost += costControls.estimateCost(
          outputTokens,
          model.name,
          'output'
        );
      }

      const metrics = await costControls.getUserUsageMetrics(userId, 7);

      // Allow for small floating-point differences
      expect(Math.abs(metrics.totalCost - totalExpectedCost)).toBeLessThan(
        0.001
      );
    });
  });

  describe('Success Criteria Validation', () => {
    it('should maintain costs within 10% of projections', async () => {
      const userId = 'projection-test-user';
      const modelUsage = [
        { model: 'gpt-4', inputTokens: 500, outputTokens: 1000, requests: 5 },
        {
          model: 'gpt-3.5-turbo',
          inputTokens: 1000,
          outputTokens: 2000,
          requests: 10,
        },
        {
          model: 'claude-3-opus',
          inputTokens: 300,
          outputTokens: 700,
          requests: 3,
        },
      ];

      let projectedCost = 0;
      let actualCost = 0;

      for (const usage of modelUsage) {
        // Calculate projected cost
        const projectedInputCost = costControls.estimateCost(
          usage.inputTokens,
          usage.model,
          'input'
        );
        const projectedOutputCost = costControls.estimateCost(
          usage.outputTokens,
          usage.model,
          'output'
        );
        projectedCost +=
          (projectedInputCost + projectedOutputCost) * usage.requests;

        // Simulate actual usage
        for (let i = 0; i < usage.requests; i++) {
          const metrics = await costControls.recordUsage(
            userId,
            usage.inputTokens / usage.requests,
            usage.outputTokens / usage.requests,
            usage.model,
            mockContext
          );
          actualCost += metrics.estimatedCost;
        }
      }

      const costVariance = Math.abs(actualCost - projectedCost) / projectedCost;

      console.log(`Projected cost: $${projectedCost.toFixed(6)}`);
      console.log(`Actual cost: $${actualCost.toFixed(6)}`);
      console.log(`Cost variance: ${(costVariance * 100).toFixed(2)}%`);

      // Success criteria: Token costs within 10% of projections
      expect(costVariance).toBeLessThan(0.1);
    });

    it('should prevent budget overruns', async () => {
      const userId = 'overrun-prevention-user';
      const budget = 1000;

      costControls.setBudget(userId, budget);
      costControls.updateConfig({ overagePolicy: 'block' });

      // Try to exceed budget in multiple attempts
      let totalUsed = 0;
      let blockCount = 0;

      const attempts = [
        { input: 200, output: 300 }, // 500 tokens
        { input: 150, output: 250 }, // 400 tokens
        { input: 100, output: 200 }, // 300 tokens - should be blocked
        { input: 50, output: 50 }, // 100 tokens - should be blocked
      ];

      for (const attempt of attempts) {
        try {
          await costControls.recordUsage(
            userId,
            attempt.input,
            attempt.output,
            'gpt-4',
            mockContext
          );
          totalUsed += attempt.input + attempt.output;
        } catch (error) {
          if (error instanceof BudgetExceededError) {
            blockCount++;
          }
        }
      }

      console.log(`Total tokens used: ${totalUsed}/${budget}`);
      console.log(`Blocked attempts: ${blockCount}`);

      expect(totalUsed).toBeLessThanOrEqual(budget);
      expect(blockCount).toBeGreaterThan(0);
    });

    it('should maintain performance under load', async () => {
      const userCount = 100;
      const operationsPerUser = 5;

      const startTime = performance.now();

      const promises = [];
      for (let i = 0; i < userCount; i++) {
        for (let j = 0; j < operationsPerUser; j++) {
          promises.push(
            costControls.recordUsage(`load-test-user-${i}`, 100, 200, 'gpt-4', {
              ...mockContext,
              userId: `load-test-user-${i}`,
            })
          );
        }
      }

      const results = await Promise.allSettled(promises);
      const duration = performance.now() - startTime;

      const successfulOperations = results.filter(
        r => r.status === 'fulfilled'
      ).length;
      const operationsPerSecond = (successfulOperations / duration) * 1000;

      console.log(
        `Processed ${successfulOperations} operations in ${duration.toFixed(2)}ms`
      );
      console.log(
        `Performance: ${operationsPerSecond.toFixed(2)} operations/second`
      );

      expect(successfulOperations).toBe(userCount * operationsPerUser);
      expect(operationsPerSecond).toBeGreaterThan(100); // Should handle at least 100 ops/sec
    });

    it('should accurately track token budgets across periods', async () => {
      const userId = 'period-tracking-user';
      const dailyBudget = 5000;

      costControls.setBudget(userId, dailyBudget);

      // Use 60% of budget
      await costControls.recordUsage(userId, 1500, 1500, 'gpt-4', mockContext);

      let budgetCheck = await costControls.checkBudget(userId, 0, 'gpt-4');
      expect(budgetCheck.budget.used).toBe(3000);
      expect(budgetCheck.budget.remaining).toBe(2000);

      // Simulate period reset
      costControls['resetAllBudgets']();

      budgetCheck = await costControls.checkBudget(userId, 0, 'gpt-4');
      expect(budgetCheck.budget.used).toBe(0);
      expect(budgetCheck.budget.remaining).toBe(dailyBudget);
    });
  });

  describe('Edge Cases and Error Handling', () => {
    it('should handle zero or negative token counts', async () => {
      const userId = 'edge-case-user';

      // Test zero tokens
      const zeroResult = await costControls.recordUsage(
        userId,
        0,
        0,
        'gpt-4',
        mockContext
      );
      expect(zeroResult.tokensUsed).toBe(0);
      expect(zeroResult.estimatedCost).toBe(0);

      // Test negative tokens (should be handled gracefully)
      const negativeResult = await costControls.recordUsage(
        userId,
        -10,
        -5,
        'gpt-4',
        mockContext
      );
      expect(negativeResult.tokensUsed).toBeGreaterThanOrEqual(0);
    });

    it('should handle unknown model types', async () => {
      const userId = 'unknown-model-user';

      const result = await costControls.recordUsage(
        userId,
        100,
        200,
        'unknown-model',
        mockContext
      );

      expect(result.tokensUsed).toBe(300);
      expect(result.estimatedCost).toBeGreaterThanOrEqual(0);
      expect(result.modelType).toBe('unknown-model');
    });

    it('should handle concurrent budget updates', async () => {
      const userId = 'concurrent-user';
      const promises = [];

      // Submit multiple concurrent usage updates
      for (let i = 0; i < 10; i++) {
        promises.push(
          costControls.recordUsage(userId, 50, 50, 'gpt-4', mockContext)
        );
      }

      const results = await Promise.allSettled(promises);
      const successfulResults = results.filter(r => r.status === 'fulfilled');

      expect(successfulResults).toHaveLength(10);

      // Final budget should reflect all updates
      const finalCheck = await costControls.checkBudget(userId, 0, 'gpt-4');
      expect(finalCheck.budget.used).toBe(1000); // 10 * 100 tokens
    });

    it('should recover from cache failures gracefully', () => {
      // Simulate cache failure
      costControls['budgetCache'].flushAll();
      costControls['usageCache'].flushAll();

      // Operations should still work
      expect(() => {
        costControls.getMetrics();
      }).not.toThrow();

      expect(async () => {
        await costControls.checkBudget('recovery-user', 100, 'gpt-4');
      }).not.toThrow();
    });
  });

  describe('Configuration and Management', () => {
    it('should provide comprehensive system metrics', () => {
      const metrics = costControls.getMetrics();

      expect(metrics).toHaveProperty('activeBudgets');
      expect(metrics).toHaveProperty('usageRecords');
      expect(metrics).toHaveProperty('throttledUsers');
      expect(metrics).toHaveProperty('encodersLoaded');
      expect(metrics).toHaveProperty('config');

      expect(metrics.config).toEqual(config);
      expect(metrics.encodersLoaded).toBeGreaterThan(0);
    });

    it('should allow runtime configuration updates', () => {
      const newConfig = {
        ...config,
        defaultTokenBudget: 20000,
        throttleThreshold: 0.9,
        overagePolicy: 'block' as const,
      };

      costControls.updateConfig(newConfig);

      const metrics = costControls.getMetrics();
      expect(metrics.config.defaultTokenBudget).toBe(20000);
      expect(metrics.config.throttleThreshold).toBe(0.9);
      expect(metrics.config.overagePolicy).toBe('block');
    });

    it('should support custom budget assignments', async () => {
      const userId = 'custom-budget-user';
      const customBudget = 25000;

      costControls.setBudget(userId, customBudget);

      const result = await costControls.checkBudget(userId, 0, 'gpt-4');

      expect(result.budget.budget).toBe(customBudget);
      expect(result.budget.remaining).toBe(customBudget);
    });

    it('should handle system cleanup properly', () => {
      // Add some data
      costControls.setBudget('cleanup-user', 5000);

      const beforeMetrics = costControls.getMetrics();
      expect(beforeMetrics.activeBudgets).toBeGreaterThan(0);

      // Cleanup
      costControls.cleanup();

      const afterMetrics = costControls.getMetrics();
      expect(afterMetrics.activeBudgets).toBe(0);
      expect(afterMetrics.usageRecords).toBe(0);
      expect(afterMetrics.throttledUsers).toBe(0);
    });
  });
});
