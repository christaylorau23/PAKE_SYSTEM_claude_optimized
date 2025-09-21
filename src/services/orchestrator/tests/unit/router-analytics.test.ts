/**
 * Tests for Advanced Router Analytics & ML Features
 *
 * Tests ML-based provider selection, cost prediction, performance analytics,
 * and optimization recommendations.
 */

import { describe, beforeEach, afterEach, it, expect, jest } from '@jest/globals';
import { OrchestratorRouter } from '../../src/router';
import { RouterAnalytics } from '../../src/router-analytics';
import {
  AgentTask,
  AgentTaskType,
  AgentResult,
  AgentResultStatus,
} from '../../agent-runtime/src/types/Agent';

describe('RouterAnalytics - ML & Advanced Features', () => {
  let router: OrchestratorRouter;
  let analytics: RouterAnalytics;

  const createTestTask = (overrides: Partial<AgentTask> = {}): AgentTask => ({
    id: 'test-task-123',
    type: AgentTaskType.SENTIMENT_ANALYSIS,
    input: { content: 'Test content for sentiment analysis' },
    config: {
      timeout: 10000,
      maxRetries: 3,
      priority: 5,
    },
    metadata: {
      createdAt: new Date().toISOString(),
    },
    ...overrides,
  });

  beforeEach(() => {
    router = new OrchestratorRouter();
    analytics = new RouterAnalytics(router);
  });

  afterEach(() => {
    analytics.destroy();
  });

  describe('ML-Based Provider Selection', () => {
    it('should predict optimal provider based on historical performance', async () => {
      const task = createTestTask();

      // This test will fail initially because RouterAnalytics doesn't exist yet
      const prediction = await analytics.predictOptimalProvider(task);

      expect(prediction).toBeDefined();
      expect(prediction.recommendedProvider).toBeDefined();
      expect(prediction.confidence).toBeGreaterThan(0);
      expect(prediction.confidence).toBeLessThanOrEqual(1);
      expect(prediction.reasons).toBeInstanceOf(Array);
    });

    it('should learn from execution results to improve predictions', async () => {
      const task = createTestTask();

      // Get initial prediction
      const initialPrediction = await analytics.predictOptimalProvider(task);

      // Simulate successful execution with actual metrics
      const executionResult = {
        provider: 'claude',
        executionTime: 2500,
        cost: 0.003,
        confidence: 0.92,
        success: true,
      };

      await analytics.recordExecutionResult(task, executionResult);

      // Get updated prediction
      const updatedPrediction = await analytics.predictOptimalProvider(task);

      // Prediction should improve with learning
      expect(updatedPrediction.confidence).toBeGreaterThanOrEqual(initialPrediction.confidence);
    });

    it('should use ensemble methods for complex task prediction', async () => {
      const complexTask = createTestTask({
        type: AgentTaskType.CONTENT_GENERATION,
        input: {
          content: 'Generate a detailed technical analysis of AI trends with 2000+ words',
          requirements: ['technical', 'detailed', 'long-form'],
        },
      });

      const prediction = await analytics.predictOptimalProvider(complexTask);

      expect(prediction.ensembleMethods).toBeInstanceOf(Array);
      expect(prediction.ensembleMethods.length).toBeGreaterThan(1);
      expect(prediction.weightedScores).toBeDefined();
    });
  });

  describe('Cost Prediction & Optimization', () => {
    it('should predict costs accurately using historical data', async () => {
      const task = createTestTask();

      const costPrediction = await analytics.predictTaskCost(task);

      expect(costPrediction).toBeDefined();
      expect(costPrediction.estimatedCost).toBeGreaterThan(0);
      expect(costPrediction.confidenceInterval).toBeDefined();
      expect(costPrediction.confidenceInterval.lower).toBeLessThan(costPrediction.estimatedCost);
      expect(costPrediction.confidenceInterval.upper).toBeGreaterThan(costPrediction.estimatedCost);
      expect(costPrediction.costBreakdown).toBeDefined();
    });

    it('should recommend cost optimization strategies', async () => {
      const expensiveTask = createTestTask({
        input: {
          content: 'Very long content that will be expensive to process: ' + 'x'.repeat(10000),
        },
      });

      const optimization = await analytics.getCostOptimizationRecommendations(expensiveTask);

      expect(optimization.recommendations).toBeInstanceOf(Array);
      expect(optimization.recommendations.length).toBeGreaterThan(0);
      expect(optimization.potentialSavings).toBeGreaterThan(0);
      expect(optimization.alternativeProviders).toBeInstanceOf(Array);
    });

    it('should track budget utilization and provide alerts', async () => {
      const budgetStatus = await analytics.getBudgetStatus();

      expect(budgetStatus.currentSpend).toBeGreaterThanOrEqual(0);
      expect(budgetStatus.budgetRemaining).toBeDefined();
      expect(budgetStatus.projectedOverage).toBeDefined();
      expect(budgetStatus.alerts).toBeInstanceOf(Array);

      if (budgetStatus.projectedOverage > 0) {
        expect(budgetStatus.alerts).toContainEqual(
          expect.objectContaining({
            type: 'budget_warning',
            severity: expect.stringMatching(/low|medium|high/),
          })
        );
      }
    });
  });

  describe('Performance Analytics', () => {
    it('should analyze provider performance trends', async () => {
      const trendAnalysis = await analytics.getProviderPerformanceTrends('claude', {
        timeRange: '7d',
        metrics: ['response_time', 'success_rate', 'cost_efficiency'],
      });

      expect(trendAnalysis.metrics).toBeDefined();
      expect(trendAnalysis.trend).toMatch(/improving|stable|declining/);
      expect(trendAnalysis.dataPoints).toBeInstanceOf(Array);
      expect(trendAnalysis.recommendations).toBeInstanceOf(Array);
    });

    it('should detect performance anomalies', async () => {
      const anomalies = await analytics.detectPerformanceAnomalies({
        timeRange: '24h',
        providers: ['claude', 'ollama', 'null'],
      });

      expect(anomalies).toBeInstanceOf(Array);
      anomalies.forEach((anomaly) => {
        expect(anomaly.provider).toBeDefined();
        expect(anomaly.metric).toBeDefined();
        expect(anomaly.severity).toMatch(/low|medium|high|critical/);
        expect(anomaly.description).toBeDefined();
        expect(anomaly.timestamp).toBeDefined();
      });
    });

    it('should generate performance comparison reports', async () => {
      const comparison = await analytics.compareProviderPerformance({
        providers: ['claude', 'ollama'],
        taskTypes: [AgentTaskType.SENTIMENT_ANALYSIS, AgentTaskType.ENTITY_EXTRACTION],
        timeRange: '30d',
      });

      expect(comparison.providers).toHaveLength(2);
      expect(comparison.summary.bestOverallProvider).toBeDefined();
      expect(comparison.summary.bestCostEfficiencyProvider).toBeDefined();
      expect(comparison.summary.fastestProvider).toBeDefined();
      expect(comparison.detailedMetrics).toBeDefined();
    });
  });

  describe('Provider Efficiency Scoring', () => {
    it('should calculate comprehensive efficiency scores', async () => {
      const efficiencyScore = await analytics.calculateProviderEfficiency('claude');

      expect(efficiencyScore.overallScore).toBeGreaterThan(0);
      expect(efficiencyScore.overallScore).toBeLessThanOrEqual(100);
      expect(efficiencyScore.components.speed).toBeDefined();
      expect(efficiencyScore.components.cost).toBeDefined();
      expect(efficiencyScore.components.reliability).toBeDefined();
      expect(efficiencyScore.components.quality).toBeDefined();
      expect(efficiencyScore.weightedFactors).toBeDefined();
    });

    it('should rank providers by efficiency for specific task types', async () => {
      const ranking = await analytics.rankProvidersByEfficiency({
        taskType: AgentTaskType.CONTENT_GENERATION,
        weights: {
          speed: 0.3,
          cost: 0.3,
          reliability: 0.2,
          quality: 0.2,
        },
      });

      expect(ranking).toBeInstanceOf(Array);
      expect(ranking.length).toBeGreaterThan(0);

      // Rankings should be ordered by score (highest first)
      for (let i = 1; i < ranking.length; i++) {
        expect(ranking[i - 1].score).toBeGreaterThanOrEqual(ranking[i].score);
      }

      ranking.forEach((provider) => {
        expect(provider.name).toBeDefined();
        expect(provider.score).toBeGreaterThan(0);
        expect(provider.rank).toBeGreaterThan(0);
        expect(provider.strengths).toBeInstanceOf(Array);
        expect(provider.weaknesses).toBeInstanceOf(Array);
      });
    });

    it('should identify underperforming providers and suggest improvements', async () => {
      const underperformers = await analytics.identifyUnderperformingProviders({
        thresholds: {
          minSuccessRate: 0.95,
          maxResponseTime: 5000,
          maxCostPerRequest: 0.01,
        },
      });

      expect(underperformers).toBeInstanceOf(Array);

      underperformers.forEach((provider) => {
        expect(provider.name).toBeDefined();
        expect(provider.issues).toBeInstanceOf(Array);
        expect(provider.issues.length).toBeGreaterThan(0);
        expect(provider.improvementSuggestions).toBeInstanceOf(Array);
        expect(provider.priority).toMatch(/low|medium|high/);
      });
    });
  });

  describe('Real-time Optimization Recommendations', () => {
    it('should provide real-time routing recommendations', async () => {
      const task = createTestTask();

      const recommendation = await analytics.getRoutingRecommendation(task);

      expect(recommendation.recommendedProvider).toBeDefined();
      expect(recommendation.alternatives).toBeInstanceOf(Array);
      expect(recommendation.reasoning).toBeDefined();
      expect(recommendation.confidence).toBeGreaterThan(0);
      expect(recommendation.expectedOutcome).toBeDefined();
    });

    it('should adapt recommendations based on current system load', async () => {
      // Simulate high system load
      await analytics.updateSystemMetrics({
        activeRequests: 50,
        queueDepth: 15,
        avgResponseTime: 8000,
      });

      const task = createTestTask();
      const recommendation = await analytics.getRoutingRecommendation(task);

      expect(recommendation.loadBalancingAdjustment).toBeDefined();
      expect(recommendation.reasoning).toContain('load');
    });

    it('should provide optimization recommendations for batch processing', async () => {
      const batchTasks = Array.from({ length: 10 }, (_, i) =>
        createTestTask({ id: `batch-task-${i}` })
      );

      const batchOptimization = await analytics.optimizeBatchProcessing(batchTasks);

      expect(batchOptimization.batchingStrategy).toBeDefined();
      expect(batchOptimization.providerAllocation).toBeDefined();
      expect(batchOptimization.estimatedSavings.cost).toBeGreaterThanOrEqual(0);
      expect(batchOptimization.estimatedSavings.time).toBeGreaterThanOrEqual(0);
      expect(batchOptimization.parallelization).toBeDefined();
    });
  });

  describe('Analytics Data Management', () => {
    it('should store and retrieve historical analytics data', async () => {
      const task = createTestTask();
      const executionData = {
        provider: 'claude',
        executionTime: 3000,
        cost: 0.005,
        confidence: 0.88,
        success: true,
        timestamp: new Date(),
      };

      await analytics.storeExecutionData(task, executionData);

      const retrievedData = await analytics.getHistoricalData({
        taskId: task.id,
        provider: 'claude',
      });

      expect(retrievedData).toBeDefined();
      expect(retrievedData.executions).toBeInstanceOf(Array);
      expect(retrievedData.executions.length).toBeGreaterThan(0);
    });

    it('should export analytics data for external analysis', async () => {
      const exportData = await analytics.exportAnalyticsData({
        format: 'json',
        timeRange: '7d',
        includeMetrics: ['cost', 'performance', 'reliability'],
      });

      expect(exportData.metadata).toBeDefined();
      expect(exportData.data).toBeDefined();
      expect(exportData.format).toBe('json');
      expect(exportData.generatedAt).toBeDefined();
    });

    it('should clean up old analytics data automatically', async () => {
      const cleanupResult = await analytics.performDataCleanup({
        retentionPeriod: '90d',
        dryRun: true,
      });

      expect(cleanupResult.recordsToDelete).toBeGreaterThanOrEqual(0);
      expect(cleanupResult.spaceToFree).toBeGreaterThanOrEqual(0);
      expect(cleanupResult.categories).toBeDefined();
    });
  });

  describe('Integration with Existing Router', () => {
    it('should integrate seamlessly with existing router decisions', async () => {
      const task = createTestTask();

      // Enable analytics-enhanced routing
      router.enableAnalyticsEnhancements(analytics);

      const { provider, decision } = await router.routeTask(task);

      expect(decision.analyticsEnhanced).toBe(true);
      expect(decision.mlPrediction).toBeDefined();
      expect(decision.optimizationApplied).toBeDefined();
    });

    it('should fall back gracefully when analytics are unavailable', async () => {
      const task = createTestTask();

      // Disable analytics temporarily
      analytics.disable();

      const { provider, decision } = await router.routeTask(task);

      expect(provider).toBeDefined();
      expect(decision.analyticsEnhanced).toBe(false);
      expect(decision.fallbackReason).toContain('analytics unavailable');
    });
  });
});
