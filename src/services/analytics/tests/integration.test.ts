/**
 * PAKE System - Analytics Integration Tests
 *
 * End-to-end integration tests for the complete analytics system including
 * anomaly detection, topic modeling, APE experiments, and insights API.
 */

import {
  describe,
  beforeAll,
  afterAll,
  beforeEach,
  afterEach,
  it,
  expect,
  jest,
} from '@jest/globals';
import { AnomalyDetector } from '../src/anomaly';
import { TopicModelEngine } from '../src/topics';
import { APEEngine } from '../src/ape';
import { ScorecardEvaluator } from '../src/scorecards';
import { InsightsApi } from '../../trends/src/api/getInsights';
import { TrendRepository } from '../../trends/src/store/TrendRepository';
import { TrendRecord } from '../../trends/src/types/TrendRecord';

describe('Analytics System Integration', () => {
  let anomalyDetector: AnomalyDetector;
  let topicEngine: TopicModelEngine;
  let apeEngine: APEEngine;
  let scorecardEvaluator: ScorecardEvaluator;
  let trendRepository: TrendRepository;
  let insightsApi: InsightsApi;

  const mockTrends: TrendRecord[] = [
    {
      id: 'trend-tech-001',
      platform: 'twitter',
      category: 'technology',
      language: 'en',
      region: 'US',
      title: 'AI Breakthrough in Natural Language Processing',
      content:
        'Scientists announce major advancement in transformer models, achieving 95% accuracy on complex reasoning tasks. The new architecture promises to revolutionize how AI understands context.',
      timestamp: new Date('2024-01-15T10:30:00Z'),
      ingestedAt: new Date(),
      engagementCount: 2500,
      viewCount: 45000,
      shareCount: 680,
      contentHash: 'tech-hash-001',
      similarityHash: 'tech-sim-001',
      qualityScore: 0.92,
      freshnessScore: 0.98,
      anomalyScore: 0.15,
      entities: [],
      anomalies: [],
      metadata: { source: 'verified_account', verified: true },
      rawData: { tweet_id: '123456789', retweets: 680 },
    },
    {
      id: 'trend-viral-002',
      platform: 'tiktok',
      category: 'entertainment',
      language: 'en',
      region: 'US',
      title: 'Viral Dance Challenge Takes Internet by Storm',
      content:
        'New dance challenge spreads across social platforms with over 10 million participants. Created by 16-year-old influencer, the trend showcases creativity and community spirit.',
      timestamp: new Date('2024-01-15T14:45:00Z'),
      ingestedAt: new Date(),
      engagementCount: 75000,
      viewCount: 2500000,
      shareCount: 45000,
      contentHash: 'viral-hash-002',
      similarityHash: 'viral-sim-002',
      qualityScore: 0.68,
      freshnessScore: 0.99,
      anomalyScore: 0.85,
      entities: [],
      anomalies: [],
      metadata: { viral_score: 0.95, rapid_growth: true },
      rawData: { video_id: 'tik_987654321', likes: 75000 },
    },
    {
      id: 'trend-news-003',
      platform: 'reddit',
      category: 'politics',
      language: 'en',
      region: 'US',
      title: 'Climate Policy Update Sparks Debate',
      content:
        'Government announces new environmental regulations affecting multiple industries. Stakeholders express mixed reactions, with some praising the initiative while others raise concerns about economic impact.',
      timestamp: new Date('2024-01-15T09:15:00Z'),
      ingestedAt: new Date(),
      engagementCount: 1200,
      viewCount: 18000,
      shareCount: 240,
      contentHash: 'news-hash-003',
      similarityHash: 'news-sim-003',
      qualityScore: 0.78,
      freshnessScore: 0.87,
      anomalyScore: 0.25,
      entities: [],
      anomalies: [],
      metadata: { source: 'news_outlet', credibility: 0.85 },
      rawData: { post_id: 'reddit_abc123', upvotes: 1200, comments: 340 },
    },
  ];

  beforeAll(async () => {
    // Initialize all analytics components
    anomalyDetector = new AnomalyDetector({
      algorithms: {
        zScore: true,
        isolation: true,
        seasonality: true,
        velocity: true,
        clustering: false,
      },
      thresholds: {
        zScore: 2.0,
        isolation: 0.6,
        seasonality: 1.8,
        velocity: 2.5,
        clustering: 0.7,
      },
    });

    topicEngine = new TopicModelEngine({
      provider: 'lda',
      modelParams: {
        numTopics: 10,
        iterations: 50,
      },
    });
    await topicEngine.initialize();

    scorecardEvaluator = new ScorecardEvaluator();

    apeEngine = new APEEngine(scorecardEvaluator);

    // Mock trend repository
    trendRepository = {
      findById: jest.fn(),
      search: jest.fn(),
      store: jest.fn(),
      bulkStore: jest.fn(),
      getAnalytics: jest.fn(),
      cleanup: jest.fn(),
      getStorageMetrics: jest.fn(),
      close: jest.fn(),
    } as any;

    // Setup mocks
    (trendRepository.findById as jest.Mock).mockImplementation((id: string) => {
      return Promise.resolve(mockTrends.find(t => t.id === id) || null);
    });

    (trendRepository.search as jest.Mock).mockImplementation(() => {
      return Promise.resolve({
        records: mockTrends,
        total: mockTrends.length,
        hasMore: false,
      });
    });

    insightsApi = new InsightsApi({
      anomalyDetector,
      topicEngine,
      apeEngine,
      scorecardEvaluator,
      trendRepository,
      api: {
        rateLimiting: { enabled: false, windowMs: 60000, maxRequests: 100 },
        caching: { enabled: true, defaultTtlSeconds: 300, maxCacheSize: 1000 },
        pagination: { defaultLimit: 50, maxLimit: 1000 },
        cors: { enabled: true, origins: ['*'] },
      },
      features: {
        realTimeAnalytics: true,
        batchProcessing: true,
        experimentalFeatures: false,
      },
    });
  });

  afterAll(async () => {
    await topicEngine.cleanup();
    anomalyDetector.destroy();
    apeEngine.cleanup();
    scorecardEvaluator.cleanup();
    insightsApi.cleanup();
  });

  describe('End-to-End Trend Analysis', () => {
    it('should perform complete analysis pipeline for normal trend', async () => {
      const trend = mockTrends[0]; // Tech trend - normal

      // 1. Anomaly Detection
      const anomalies = await anomalyDetector.detectAnomalies(trend);
      expect(anomalies.recordId).toBe(trend.id);
      expect(anomalies.overallScore).toBeLessThan(0.5); // Should be normal

      // 2. Topic Modeling
      const topics = await topicEngine.extractTopics(trend);
      expect(topics.documentId).toBe(trend.id);
      expect(topics.topics.length).toBeGreaterThan(0);
      expect(topics.confidence).toBeGreaterThan(0);

      // 3. Quality Evaluation
      const quality = await scorecardEvaluator.evaluate(trend.content, {
        scorecardIds: ['general_quality'],
      });
      expect(quality.overallScore).toBeGreaterThan(0.7); // High quality content
      expect(quality.overallGrade).toMatch(/[A-C]/);

      // 4. Verify all components return consistent data
      expect(anomalies.metadata.timestamp).toBeInstanceOf(Date);
      expect(topics.metadata.timestamp).toBeInstanceOf(Date);
      expect(quality.metadata.timestamp).toBeInstanceOf(Date);
    });

    it('should detect anomalies in viral content', async () => {
      const viralTrend = mockTrends[1]; // Viral TikTok trend

      const anomalies = await anomalyDetector.detectAnomalies(viralTrend);

      // Should detect engagement spike due to high engagement numbers
      expect(anomalies.overallScore).toBeGreaterThan(0.5);
      expect(anomalies.anomalies.length).toBeGreaterThan(0);

      const engagementAnomaly = anomalies.anomalies.find(
        a => a.type === 'engagement_spike'
      );
      expect(engagementAnomaly).toBeDefined();
      expect(engagementAnomaly?.severity).toMatch(/high|critical/);
    });

    it('should handle batch processing efficiently', async () => {
      const startTime = Date.now();

      // Process all trends simultaneously
      const [anomalyResults, topicResults] = await Promise.all([
        anomalyDetector.detectAnomaliesBatch(mockTrends),
        topicEngine.extractTopicsBatch(
          mockTrends.map(t => ({ id: t.id, content: t.content }))
        ),
      ]);

      const processingTime = Date.now() - startTime;

      expect(anomalyResults).toHaveLength(3);
      expect(topicResults).toHaveLength(3);
      expect(processingTime).toBeLessThan(15000); // Should complete within 15s

      // Verify results are properly mapped
      anomalyResults.forEach(result => {
        const originalTrend = mockTrends.find(t => t.id === result.recordId);
        expect(originalTrend).toBeDefined();
      });
    });
  });

  describe('APE Integration with Analytics', () => {
    it('should create and run experiments with analytics feedback', async () => {
      // Create experiment for content analysis prompts
      const experiment = await apeEngine.createExperiment(
        'Content Analysis Optimization',
        'Testing different prompts for trend analysis',
        [
          {
            name: 'Control',
            prompt: 'Analyze this trend data and provide insights.',
            parameters: {
              temperature: 0.7,
              maxTokens: 500,
              topP: 1.0,
              frequencyPenalty: 0.0,
              presencePenalty: 0.0,
            },
            trafficAllocation: 50,
            isControl: true,
            metadata: { generationMethod: 'manual' },
          },
          {
            name: 'Detailed Analysis',
            prompt:
              'Conduct a comprehensive analysis of this trend, including anomaly detection, topic identification, and quality assessment. Provide detailed insights and recommendations.',
            parameters: {
              temperature: 0.5,
              maxTokens: 800,
              topP: 0.9,
              frequencyPenalty: 0.1,
              presencePenalty: 0.1,
            },
            trafficAllocation: 50,
            isControl: false,
            metadata: { generationMethod: 'manual' },
          },
        ],
        {
          evaluation: {
            scorecardIds: ['general_quality'],
            evaluationFrequency: 'realtime',
          },
          sampling: {
            minSampleSize: 5,
            maxSampleSize: 20,
          },
        }
      );

      await apeEngine.startExperiment(experiment.id);

      // Run evaluations using trend data
      const evaluationResults = [];
      for (const trend of mockTrends) {
        const result = await apeEngine.evaluatePrompt(
          experiment.id,
          `Analyze this trend: ${trend.title} - ${trend.content.substring(0, 100)}...`
        );
        evaluationResults.push(result);
      }

      expect(evaluationResults).toHaveLength(3);
      evaluationResults.forEach(result => {
        expect(result.result.overallScore).toBeGreaterThan(0);
        expect(result.variantId).toBeDefined();
      });

      // Stop experiment and check results
      const experimentResults = await apeEngine.stopExperiment(experiment.id);
      expect(experimentResults.totalSamples).toBe(3);
      expect(experimentResults.statisticalResults).toBeDefined();
    });
  });

  describe('Insights API Integration', () => {
    let mockReq: any;
    let mockRes: any;

    beforeEach(() => {
      mockReq = {
        params: {},
        query: {},
        body: {},
        ip: '127.0.0.1',
      };

      mockRes = {
        json: jest.fn(),
        status: jest.fn().mockReturnThis(),
      };
    });

    it('should provide comprehensive trend insights', async () => {
      mockReq.params = { trendId: 'trend-tech-001' };

      await insightsApi.getTrendInsights(mockReq, mockRes, jest.fn());

      expect(mockRes.json).toHaveBeenCalledWith(
        expect.objectContaining({
          success: true,
          data: expect.objectContaining({
            trend: expect.objectContaining({
              id: 'trend-tech-001',
            }),
            analytics: expect.objectContaining({
              anomalies: expect.any(Object),
              topics: expect.any(Object),
              quality: expect.any(Object),
            }),
            insights: expect.objectContaining({
              riskScore: expect.any(Number),
              viralityPotential: expect.any(Number),
              authenticity: expect.any(Number),
              influence: expect.any(Number),
              recommendedActions: expect.any(Array),
            }),
          }),
          metadata: expect.objectContaining({
            requestId: expect.any(String),
            processingTime: expect.any(Number),
          }),
        })
      );
    });

    it('should detect and report anomalies via API', async () => {
      mockReq.query = { sourceId: 'tiktok', limit: '10' };

      await insightsApi.detectAnomalies(mockReq, mockRes, jest.fn());

      expect(mockRes.json).toHaveBeenCalledWith(
        expect.objectContaining({
          success: true,
          data: expect.any(Array),
        })
      );

      const response = mockRes.json.mock.calls[0][0];
      if (response.data.length > 0) {
        // Should find the viral TikTok trend with anomalies
        const viralResult = response.data.find(
          (result: any) => result.trend.id === 'trend-viral-002'
        );

        if (viralResult) {
          expect(viralResult.anomalies.anomalies.length).toBeGreaterThan(0);
        }
      }
    });

    it('should provide dashboard insights with aggregated data', async () => {
      mockReq.query = { timeRange: '24h' };

      await insightsApi.getDashboard(mockReq, mockRes, jest.fn());

      expect(mockRes.json).toHaveBeenCalledWith(
        expect.objectContaining({
          success: true,
          data: expect.objectContaining({
            summary: expect.objectContaining({
              totalTrends: expect.any(Number),
              newTrendsToday: expect.any(Number),
              averageQuality: expect.any(Number),
            }),
            timeSeries: expect.objectContaining({
              trendVolume: expect.any(Array),
              qualityTrends: expect.any(Array),
            }),
            distributions: expect.objectContaining({
              platforms: expect.any(Object),
              categories: expect.any(Object),
            }),
          }),
        })
      );
    });

    it('should handle API errors gracefully', async () => {
      // Test with non-existent trend ID
      mockReq.params = { trendId: 'non-existent-trend' };

      await insightsApi.getTrendInsights(mockReq, mockRes, jest.fn());

      expect(mockRes.status).toHaveBeenCalledWith(404);
      expect(mockRes.json).toHaveBeenCalledWith(
        expect.objectContaining({
          success: false,
          error: expect.objectContaining({
            code: 'TREND_NOT_FOUND',
          }),
        })
      );
    });

    it('should provide health status for all components', async () => {
      await insightsApi.getHealth(mockReq, mockRes, jest.fn());

      expect(mockRes.json).toHaveBeenCalledWith(
        expect.objectContaining({
          success: true,
          data: expect.objectContaining({
            status: 'healthy',
            services: expect.objectContaining({
              anomalyDetection: expect.objectContaining({
                status: 'healthy',
              }),
              topicModeling: expect.objectContaining({
                status: 'healthy',
              }),
              promptExperiments: expect.objectContaining({
                status: 'healthy',
              }),
              qualityEvaluation: expect.objectContaining({
                status: 'healthy',
              }),
            }),
            api: expect.objectContaining({
              totalRequests: expect.any(Number),
              successRate: expect.any(Number),
            }),
          }),
        })
      );
    });
  });

  describe('Performance and Resource Management', () => {
    it('should handle high load across all components', async () => {
      const testData = Array.from({ length: 50 }, (_, i) => ({
        ...mockTrends[0],
        id: `load-test-${i}`,
        engagementCount: 1000 + Math.random() * 2000,
      }));

      const startTime = Date.now();

      // Test parallel processing across all components
      const [anomalies, topics, quality] = await Promise.all([
        anomalyDetector.detectAnomaliesBatch(testData),
        topicEngine.extractTopicsBatch(
          testData.map(t => ({ id: t.id, content: t.content }))
        ),
        scorecardEvaluator.evaluateBatch(
          testData.map(t => ({ id: t.id, content: t.content })),
          ['general_quality']
        ),
      ]);

      const processingTime = Date.now() - startTime;

      expect(anomalies).toHaveLength(50);
      expect(topics).toHaveLength(50);
      expect(quality.size).toBe(50);
      expect(processingTime).toBeLessThan(30000); // Should complete within 30s

      // Verify data consistency
      testData.forEach(trend => {
        const anomalyResult = anomalies.find(a => a.recordId === trend.id);
        const topicResult = topics.find(t => t.documentId === trend.id);
        const qualityResult = quality.get(trend.id);

        expect(anomalyResult).toBeDefined();
        expect(topicResult).toBeDefined();
        expect(qualityResult).toBeDefined();
      });
    });

    it('should properly clean up resources', async () => {
      // Get initial memory usage (simplified check)
      const initialStats = {
        anomaly: anomalyDetector.getStatistics(),
        topic: await topicEngine.getMetrics(),
        ape: apeEngine.getPerformanceStats(),
        scorecard: scorecardEvaluator.getEvaluationStats(),
      };

      // Process data
      for (const trend of mockTrends) {
        await anomalyDetector.detectAnomalies(trend);
        await topicEngine.extractTopics(trend);
      }

      // Get final stats
      const finalStats = {
        anomaly: anomalyDetector.getStatistics(),
        topic: await topicEngine.getMetrics(),
        ape: apeEngine.getPerformanceStats(),
        scorecard: scorecardEvaluator.getEvaluationStats(),
      };

      // Verify processing occurred
      expect(finalStats.anomaly.totalRequests).toBeGreaterThan(
        initialStats.anomaly.totalRequests
      );
      expect(finalStats.topic.totalDocuments).toBeGreaterThan(
        initialStats.topic.totalDocuments
      );

      // Memory usage should be reasonable (implementation dependent)
      expect(finalStats.anomaly.totalRequests).toBeLessThan(1000000); // Sanity check
    });
  });

  describe('Data Quality and Consistency', () => {
    it('should maintain data consistency across components', async () => {
      const testTrend = mockTrends[0];

      // Run analysis multiple times
      const runs = await Promise.all([
        Promise.all([
          anomalyDetector.detectAnomalies(testTrend),
          topicEngine.extractTopics(testTrend),
          scorecardEvaluator.evaluate(testTrend.content, {
            scorecardIds: ['general_quality'],
          }),
        ]),
        Promise.all([
          anomalyDetector.detectAnomalies(testTrend),
          topicEngine.extractTopics(testTrend),
          scorecardEvaluator.evaluate(testTrend.content, {
            scorecardIds: ['general_quality'],
          }),
        ]),
      ]);

      // Results should be consistent across runs
      const [run1, run2] = runs;

      // Anomaly scores should be similar
      expect(
        Math.abs(run1[0].overallScore - run2[0].overallScore)
      ).toBeLessThan(0.2);

      // Topic confidence should be similar
      expect(Math.abs(run1[1].confidence - run2[1].confidence)).toBeLessThan(
        0.3
      );

      // Quality scores should be identical (deterministic evaluation)
      expect(run1[2].overallScore).toBe(run2[2].overallScore);
    });

    it('should validate all output formats', async () => {
      const trend = mockTrends[0];

      const [anomalies, topics, quality] = await Promise.all([
        anomalyDetector.detectAnomalies(trend),
        topicEngine.extractTopics(trend),
        scorecardEvaluator.evaluate(trend.content, {
          scorecardIds: ['general_quality'],
        }),
      ]);

      // Validate anomaly detection output
      expect(anomalies).toMatchObject({
        recordId: expect.any(String),
        anomalies: expect.any(Array),
        overallScore: expect.any(Number),
        confidence: expect.any(Number),
        baseline: expect.any(Object),
        metadata: expect.objectContaining({
          algorithmsUsed: expect.any(Array),
          processingTime: expect.any(Number),
          timestamp: expect.any(Date),
        }),
      });

      // Validate topic modeling output
      expect(topics).toMatchObject({
        documentId: expect.any(String),
        topics: expect.any(Array),
        processingTime: expect.any(Number),
        confidence: expect.any(Number),
        metadata: expect.objectContaining({
          provider: expect.any(String),
          timestamp: expect.any(Date),
        }),
      });

      // Validate scorecard output
      expect(quality).toMatchObject({
        overallScore: expect.any(Number),
        overallGrade: expect.stringMatching(/[A-F]/),
        categoryScores: expect.any(Object),
        criterionScores: expect.any(Map),
        metadata: expect.objectContaining({
          timestamp: expect.any(Date),
          processingTime: expect.any(Number),
        }),
      });
    });
  });

  describe('Real-world Scenario Simulation', () => {
    it('should handle realistic content moderation workflow', async () => {
      // Simulate suspicious content that needs review
      const suspiciousContent: TrendRecord = {
        ...mockTrends[1], // Use viral trend as base
        id: 'suspicious-001',
        content:
          'This content contains coordinated messaging patterns and unusual engagement spikes that may indicate artificial manipulation.',
        engagementCount: 100000, // Extremely high
        timestamp: new Date(Date.now() - 60000), // Very recent
        anomalyScore: 0.95,
      };

      // 1. Anomaly detection should flag this
      const anomalies =
        await anomalyDetector.detectAnomalies(suspiciousContent);
      expect(anomalies.overallScore).toBeGreaterThan(0.7);
      expect(
        anomalies.anomalies.some(
          a => a.severity === 'critical' || a.severity === 'high'
        )
      ).toBe(true);

      // 2. Quality evaluation should show concerns
      const quality = await scorecardEvaluator.evaluate(
        suspiciousContent.content,
        {
          scorecardIds: ['general_quality'],
        }
      );

      // 3. Topic analysis should still work
      const topics = await topicEngine.extractTopics(suspiciousContent);
      expect(topics.documentId).toBe(suspiciousContent.id);

      // 4. Combined analysis should recommend review
      const riskScore =
        anomalies.overallScore * 0.6 + (1 - quality.overallScore) * 0.4;
      expect(riskScore).toBeGreaterThan(0.5); // High risk

      // 5. Should generate appropriate recommendations
      const recommendations = [];
      if (anomalies.overallScore > 0.7) {
        recommendations.push(
          'High anomaly score detected - investigate for potential manipulation'
        );
      }
      if (quality.overallScore < 0.6) {
        recommendations.push(
          'Content quality below threshold - consider review or improvement'
        );
      }

      expect(recommendations.length).toBeGreaterThan(0);
    });
  });
});

// Helper functions for integration tests
function generateTestTrend(overrides: Partial<TrendRecord> = {}): TrendRecord {
  return {
    id: `test-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    platform: 'twitter',
    category: 'technology',
    language: 'en',
    region: 'US',
    title: 'Test Trend Title',
    content: 'This is test content for integration testing purposes.',
    timestamp: new Date(),
    ingestedAt: new Date(),
    engagementCount: 1000,
    viewCount: 15000,
    shareCount: 150,
    contentHash: 'test-hash',
    similarityHash: 'test-sim-hash',
    qualityScore: 0.8,
    freshnessScore: 0.9,
    anomalyScore: 0.1,
    entities: [],
    anomalies: [],
    metadata: {},
    rawData: {},
    ...overrides,
  };
}

async function waitForAsyncOperations(): Promise<void> {
  // Allow time for async operations to complete
  await new Promise(resolve => setTimeout(resolve, 100));
}
