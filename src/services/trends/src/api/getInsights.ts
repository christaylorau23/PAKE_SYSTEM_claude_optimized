/**
 * PAKE System - Insights API Endpoint
 *
 * RESTful API for exposing analytics results to other services.
 * Provides endpoints for anomaly detection, topic modeling, and
 * comprehensive trend insights with caching and rate limiting.
 */

import { Request, Response, NextFunction } from 'express';
import { createLogger, Logger } from '../../../orchestrator/src/utils/logger';
import { metrics } from '../../../orchestrator/src/utils/metrics';
import {
  AnomalyDetector,
  AnomalyDetectionResult,
} from '../../../analytics/src/anomaly';
import { TopicModelEngine, TopicResult } from '../../../analytics/src/topics';
import {
  APEEngine,
  PromptExperiment,
  ExperimentResults,
} from '../../../analytics/src/ape';
import {
  ScorecardEvaluator,
  EvaluationResult,
} from '../../../analytics/src/scorecards';
import { TrendRepository, TrendQuery } from '../store/TrendRepository';
import { TrendRecord } from '../types/TrendRecord';

export interface InsightsApiConfig {
  // Service instances
  anomalyDetector: AnomalyDetector;
  topicEngine: TopicModelEngine;
  apeEngine: APEEngine;
  scorecardEvaluator: ScorecardEvaluator;
  trendRepository: TrendRepository;

  // API configuration
  api: {
    rateLimiting: {
      enabled: boolean;
      windowMs: number; // Rate limit window in milliseconds
      maxRequests: number; // Max requests per window
    };
    caching: {
      enabled: boolean;
      defaultTtlSeconds: number;
      maxCacheSize: number;
    };
    pagination: {
      defaultLimit: number;
      maxLimit: number;
    };
    cors: {
      enabled: boolean;
      origins: string[];
    };
  };

  // Feature flags
  features: {
    realTimeAnalytics: boolean;
    batchProcessing: boolean;
    experimentalFeatures: boolean;
  };
}

export interface InsightsResponse<T = any> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
  metadata: {
    timestamp: string;
    requestId: string;
    processingTime: number;
    version: string;
    cached: boolean;
  };
  pagination?: {
    page: number;
    limit: number;
    total: number;
    hasMore: boolean;
  };
}

export interface TrendInsight {
  // Basic trend information
  trend: TrendRecord;

  // Analytics results
  analytics: {
    anomalies: AnomalyDetectionResult;
    topics: TopicResult;
    quality: EvaluationResult;
  };

  // Derived insights
  insights: {
    riskScore: number; // 0-1 overall risk assessment
    viralityPotential: number; // 0-1 likelihood to go viral
    authenticity: number; // 0-1 authenticity score
    influence: number; // 0-1 influence potential
    recommendedActions: string[];
  };

  // Context
  context: {
    similarTrends: TrendRecord[];
    historicalContext: any;
    geographicSpread: any;
    temporalPatterns: any;
  };
}

export interface DashboardInsights {
  // Summary statistics
  summary: {
    totalTrends: number;
    newTrendsToday: number;
    activeAnomalies: number;
    topTopics: Array<{ topic: string; count: number }>;
    averageQuality: number;
  };

  // Time series data
  timeSeries: {
    trendVolume: Array<{ timestamp: string; count: number }>;
    qualityTrends: Array<{ timestamp: string; avgQuality: number }>;
    anomalyFrequency: Array<{ timestamp: string; anomalies: number }>;
  };

  // Distribution data
  distributions: {
    platforms: Record<string, number>;
    categories: Record<string, number>;
    languages: Record<string, number>;
    regions: Record<string, number>;
  };

  // Recent activity
  recentActivity: {
    criticalAnomalies: AnomalyDetectionResult[];
    emergingTopics: Array<{ topic: string; growth: number }>;
    qualityDegradation: TrendRecord[];
  };
}

/**
 * Insights API controller with comprehensive analytics endpoints
 */
export class InsightsApi {
  private readonly logger: Logger;
  private readonly config: InsightsApiConfig;

  // Request cache
  private readonly responseCache = new Map<
    string,
    { data: any; expiry: number }
  >();

  // Rate limiting tracking
  private readonly rateLimitMap = new Map<
    string,
    { count: number; resetTime: number }
  >();

  // Performance metrics
  private readonly apiStats = {
    totalRequests: 0,
    successfulRequests: 0,
    failedRequests: 0,
    averageResponseTime: 0,
    cacheHitRate: 0,
    endpointUsage: new Map<string, number>(),
  };

  constructor(config: InsightsApiConfig) {
    this.logger = createLogger('InsightsApi');
    this.config = config;

    // Start cleanup tasks
    this.startMaintenanceTasks();

    this.logger.info('Insights API initialized');
  }

  /**
   * Get comprehensive insights for a single trend
   */
  getTrendInsights = async (
    req: Request,
    res: Response,
    next: NextFunction
  ): Promise<void> => {
    const requestId = this.generateRequestId();
    const startTime = Date.now();

    try {
      // Rate limiting check
      if (this.config.api.rateLimiting.enabled) {
        const rateLimitResult = this.checkRateLimit(req.ip);
        if (!rateLimitResult.allowed) {
          res
            .status(429)
            .json(
              this.createErrorResponse(
                'RATE_LIMIT_EXCEEDED',
                'Too many requests',
                { retryAfter: rateLimitResult.retryAfter },
                requestId,
                startTime
              )
            );
          return;
        }
      }

      const { trendId } = req.params;
      const options = this.parseQueryOptions(req.query);

      // Validate input
      if (!trendId) {
        res
          .status(400)
          .json(
            this.createErrorResponse(
              'INVALID_INPUT',
              'Trend ID is required',
              null,
              requestId,
              startTime
            )
          );
        return;
      }

      // Check cache
      const cacheKey = `trend_insights:${trendId}:${JSON.stringify(options)}`;
      if (this.config.api.caching.enabled) {
        const cached = this.getFromCache(cacheKey);
        if (cached) {
          this.updateApiStats(
            'getTrendInsights',
            true,
            Date.now() - startTime,
            true
          );
          res.json(
            this.createSuccessResponse(cached, requestId, startTime, true)
          );
          return;
        }
      }

      // Get trend record
      const trend = await this.config.trendRepository.findById(trendId);
      if (!trend) {
        res
          .status(404)
          .json(
            this.createErrorResponse(
              'TREND_NOT_FOUND',
              `Trend not found: ${trendId}`,
              null,
              requestId,
              startTime
            )
          );
        return;
      }

      // Generate comprehensive insights
      const insights = await this.generateTrendInsights(trend, options);

      // Cache response
      if (this.config.api.caching.enabled) {
        this.setCache(
          cacheKey,
          insights,
          this.config.api.caching.defaultTtlSeconds
        );
      }

      this.updateApiStats(
        'getTrendInsights',
        true,
        Date.now() - startTime,
        false
      );

      res.json(
        this.createSuccessResponse(insights, requestId, startTime, false)
      );
    } catch (error) {
      this.updateApiStats(
        'getTrendInsights',
        false,
        Date.now() - startTime,
        false
      );

      this.logger.error('Get trend insights failed', {
        requestId,
        trendId: req.params.trendId,
        error: error.message,
      });

      res
        .status(500)
        .json(
          this.createErrorResponse(
            'INTERNAL_ERROR',
            'Failed to generate trend insights',
            { error: error.message },
            requestId,
            startTime
          )
        );
    }
  };

  /**
   * Detect anomalies in trends
   */
  detectAnomalies = async (
    req: Request,
    res: Response,
    next: NextFunction
  ): Promise<void> => {
    const requestId = this.generateRequestId();
    const startTime = Date.now();

    try {
      const { sourceId, limit = 10, severity } = req.query;
      const options = {
        sourceId: sourceId as string,
        limit: parseInt(limit as string),
        severity: severity as string,
      };

      // Get recent trends for anomaly detection
      const query: TrendQuery = {
        limit: options.limit * 2, // Get more to analyze
        sortBy: 'timestamp',
        sortOrder: 'desc',
      };

      if (options.sourceId) {
        query.platforms = [options.sourceId];
      }

      const { records: trends } =
        await this.config.trendRepository.search(query);

      // Run anomaly detection on each trend
      const anomalyResults: Array<{
        trend: TrendRecord;
        anomalies: AnomalyDetectionResult;
      }> = [];

      for (const trend of trends.slice(0, options.limit)) {
        try {
          const anomalies = await this.config.anomalyDetector.detectAnomalies(
            trend,
            options.sourceId
          );

          // Filter by severity if specified
          if (options.severity) {
            anomalies.anomalies = anomalies.anomalies.filter(
              anomaly => anomaly.severity === options.severity
            );
          }

          if (anomalies.anomalies.length > 0) {
            anomalyResults.push({ trend, anomalies });
          }
        } catch (error) {
          this.logger.warn('Anomaly detection failed for trend', {
            trendId: trend.id,
            error: error.message,
          });
        }
      }

      this.updateApiStats(
        'detectAnomalies',
        true,
        Date.now() - startTime,
        false
      );

      res.json(
        this.createSuccessResponse(anomalyResults, requestId, startTime, false)
      );
    } catch (error) {
      this.updateApiStats(
        'detectAnomalies',
        false,
        Date.now() - startTime,
        false
      );

      this.logger.error('Anomaly detection failed', {
        requestId,
        error: error.message,
      });

      res
        .status(500)
        .json(
          this.createErrorResponse(
            'ANOMALY_DETECTION_ERROR',
            'Failed to detect anomalies',
            { error: error.message },
            requestId,
            startTime
          )
        );
    }
  };

  /**
   * Get topic modeling results
   */
  getTopics = async (
    req: Request,
    res: Response,
    next: NextFunction
  ): Promise<void> => {
    const requestId = this.generateRequestId();
    const startTime = Date.now();

    try {
      const { trendIds, limit = 50 } = req.query;

      if (trendIds) {
        // Get topics for specific trends
        const ids = (trendIds as string).split(',');
        const results: Array<{ trendId: string; topics: TopicResult }> = [];

        for (const trendId of ids) {
          try {
            const trend = await this.config.trendRepository.findById(
              trendId.trim()
            );
            if (trend) {
              const topics = await this.config.topicEngine.extractTopics(trend);
              results.push({ trendId: trend.id, topics });
            }
          } catch (error) {
            this.logger.warn('Topic extraction failed for trend', {
              trendId: trendId.trim(),
              error: error.message,
            });
          }
        }

        res.json(
          this.createSuccessResponse(results, requestId, startTime, false)
        );
      } else {
        // Get all available topics
        const topics = await this.config.topicEngine.getTopics();
        const limitedTopics = topics.slice(0, parseInt(limit as string));

        res.json(
          this.createSuccessResponse(limitedTopics, requestId, startTime, false)
        );
      }

      this.updateApiStats('getTopics', true, Date.now() - startTime, false);
    } catch (error) {
      this.updateApiStats('getTopics', false, Date.now() - startTime, false);

      this.logger.error('Get topics failed', {
        requestId,
        error: error.message,
      });

      res
        .status(500)
        .json(
          this.createErrorResponse(
            'TOPIC_MODELING_ERROR',
            'Failed to get topics',
            { error: error.message },
            requestId,
            startTime
          )
        );
    }
  };

  /**
   * Get prompt experiments status and results
   */
  getExperiments = async (
    req: Request,
    res: Response,
    next: NextFunction
  ): Promise<void> => {
    const requestId = this.generateRequestId();
    const startTime = Date.now();

    try {
      const { status, limit = 20 } = req.query;

      let experiments: PromptExperiment[] = [];

      if (status === 'active') {
        experiments = this.config.apeEngine.getActiveExperiments();
      } else {
        experiments = this.config.apeEngine.getExperimentHistory(
          parseInt(limit as string)
        );
      }

      // Include performance stats
      const performanceStats = this.config.apeEngine.getPerformanceStats();

      const response = {
        experiments,
        stats: performanceStats,
      };

      this.updateApiStats(
        'getExperiments',
        true,
        Date.now() - startTime,
        false
      );

      res.json(
        this.createSuccessResponse(response, requestId, startTime, false)
      );
    } catch (error) {
      this.updateApiStats(
        'getExperiments',
        false,
        Date.now() - startTime,
        false
      );

      this.logger.error('Get experiments failed', {
        requestId,
        error: error.message,
      });

      res
        .status(500)
        .json(
          this.createErrorResponse(
            'EXPERIMENT_ERROR',
            'Failed to get experiments',
            { error: error.message },
            requestId,
            startTime
          )
        );
    }
  };

  /**
   * Get dashboard insights with summary statistics
   */
  getDashboard = async (
    req: Request,
    res: Response,
    next: NextFunction
  ): Promise<void> => {
    const requestId = this.generateRequestId();
    const startTime = Date.now();

    try {
      const { timeRange = '24h' } = req.query;

      // Check cache first
      const cacheKey = `dashboard:${timeRange}`;
      if (this.config.api.caching.enabled) {
        const cached = this.getFromCache(cacheKey);
        if (cached) {
          this.updateApiStats(
            'getDashboard',
            true,
            Date.now() - startTime,
            true
          );
          res.json(
            this.createSuccessResponse(cached, requestId, startTime, true)
          );
          return;
        }
      }

      // Generate dashboard insights
      const dashboard = await this.generateDashboardInsights(
        timeRange as string
      );

      // Cache for shorter period (dashboard data changes frequently)
      if (this.config.api.caching.enabled) {
        this.setCache(cacheKey, dashboard, 300); // 5 minutes
      }

      this.updateApiStats('getDashboard', true, Date.now() - startTime, false);

      res.json(
        this.createSuccessResponse(dashboard, requestId, startTime, false)
      );
    } catch (error) {
      this.updateApiStats('getDashboard', false, Date.now() - startTime, false);

      this.logger.error('Get dashboard failed', {
        requestId,
        error: error.message,
      });

      res
        .status(500)
        .json(
          this.createErrorResponse(
            'DASHBOARD_ERROR',
            'Failed to generate dashboard insights',
            { error: error.message },
            requestId,
            startTime
          )
        );
    }
  };

  /**
   * Evaluate content quality using scorecards
   */
  evaluateQuality = async (
    req: Request,
    res: Response,
    next: NextFunction
  ): Promise<void> => {
    const requestId = this.generateRequestId();
    const startTime = Date.now();

    try {
      const { content, scorecardIds, context } = req.body;

      if (!content || !scorecardIds) {
        res
          .status(400)
          .json(
            this.createErrorResponse(
              'INVALID_INPUT',
              'Content and scorecard IDs are required',
              null,
              requestId,
              startTime
            )
          );
        return;
      }

      const evaluation = await this.config.scorecardEvaluator.evaluate(
        content,
        {
          scorecardIds: Array.isArray(scorecardIds)
            ? scorecardIds
            : [scorecardIds],
          context,
        }
      );

      this.updateApiStats(
        'evaluateQuality',
        true,
        Date.now() - startTime,
        false
      );

      res.json(
        this.createSuccessResponse(evaluation, requestId, startTime, false)
      );
    } catch (error) {
      this.updateApiStats(
        'evaluateQuality',
        false,
        Date.now() - startTime,
        false
      );

      this.logger.error('Quality evaluation failed', {
        requestId,
        error: error.message,
      });

      res
        .status(500)
        .json(
          this.createErrorResponse(
            'EVALUATION_ERROR',
            'Failed to evaluate content quality',
            { error: error.message },
            requestId,
            startTime
          )
        );
    }
  };

  /**
   * Get API health and performance metrics
   */
  getHealth = async (
    req: Request,
    res: Response,
    next: NextFunction
  ): Promise<void> => {
    const requestId = this.generateRequestId();
    const startTime = Date.now();

    try {
      // Check service health
      const anomalyHealth = await this.config.anomalyDetector.getStatistics();
      const topicHealth = await this.config.topicEngine.getMetrics();
      const apeHealth = this.config.apeEngine.getPerformanceStats();
      const scorecardHealth =
        this.config.scorecardEvaluator.getEvaluationStats();

      const health = {
        status: 'healthy',
        timestamp: new Date().toISOString(),
        services: {
          anomalyDetection: {
            status: 'healthy',
            totalDetections: anomalyHealth.totalRequests,
            averageProcessingTime: anomalyHealth.averageProcessingTime,
          },
          topicModeling: {
            status: 'healthy',
            totalDocuments: topicHealth.totalDocuments,
            totalTopics: topicHealth.totalTopics,
            averageConfidence: topicHealth.averageConfidence,
          },
          promptExperiments: {
            status: 'healthy',
            activeExperiments: apeHealth.activeExperiments,
            totalExperiments: apeHealth.totalExperiments,
            successRate: apeHealth.averageSuccessRate,
          },
          qualityEvaluation: {
            status: 'healthy',
            totalEvaluations: scorecardHealth.totalEvaluations,
            successRate: scorecardHealth.successRate,
            averageScore: scorecardHealth.averageScore,
          },
        },
        api: {
          totalRequests: this.apiStats.totalRequests,
          successRate:
            this.apiStats.totalRequests > 0
              ? this.apiStats.successfulRequests / this.apiStats.totalRequests
              : 0,
          averageResponseTime: this.apiStats.averageResponseTime,
          cacheHitRate: this.apiStats.cacheHitRate,
        },
      };

      res.json(this.createSuccessResponse(health, requestId, startTime, false));
    } catch (error) {
      res
        .status(500)
        .json(
          this.createErrorResponse(
            'HEALTH_CHECK_ERROR',
            'Failed to get health status',
            { error: error.message },
            requestId,
            startTime
          )
        );
    }
  };

  // Private methods

  private async generateTrendInsights(
    trend: TrendRecord,
    options: any
  ): Promise<TrendInsight> {
    // Run analytics in parallel
    const [anomalies, topics, quality] = await Promise.all([
      this.config.anomalyDetector.detectAnomalies(trend),
      this.config.topicEngine.extractTopics(trend),
      this.config.scorecardEvaluator.evaluate(trend.content, {
        scorecardIds: ['general_quality'],
        context: {
          platform: trend.platform,
          category: trend.category,
        },
      }),
    ]);

    // Calculate derived insights
    const insights = {
      riskScore: this.calculateRiskScore(anomalies, quality),
      viralityPotential: this.calculateViralityPotential(trend, topics),
      authenticity: this.calculateAuthenticity(anomalies, quality),
      influence: this.calculateInfluence(trend, topics),
      recommendedActions: this.generateRecommendations(anomalies, quality),
    };

    // Get similar trends for context
    const similarTrends = await this.findSimilarTrends(trend);

    return {
      trend,
      analytics: {
        anomalies,
        topics,
        quality,
      },
      insights,
      context: {
        similarTrends,
        historicalContext: {}, // Would implement historical analysis
        geographicSpread: {}, // Would implement geographic analysis
        temporalPatterns: {}, // Would implement temporal analysis
      },
    };
  }

  private async generateDashboardInsights(
    timeRange: string
  ): Promise<DashboardInsights> {
    const timeRangeMs = this.parseTimeRange(timeRange);
    const startDate = new Date(Date.now() - timeRangeMs);

    // Get trends from time range
    const { records: trends, total } = await this.config.trendRepository.search(
      {
        dateRange: { start: startDate, end: new Date() },
        limit: 1000,
      }
    );

    // Calculate summary statistics
    const summary = {
      totalTrends: total,
      newTrendsToday: trends.filter(
        t => t.timestamp.getTime() > Date.now() - 24 * 60 * 60 * 1000
      ).length,
      activeAnomalies: 0, // Would count from anomaly results
      topTopics: [], // Would calculate from topic results
      averageQuality:
        trends.reduce((sum, t) => sum + t.qualityScore, 0) / trends.length,
    };

    // Generate time series data
    const timeSeries = this.generateTimeSeries(trends, timeRange);

    // Calculate distributions
    const distributions = {
      platforms: this.calculateDistribution(trends, 'platform'),
      categories: this.calculateDistribution(trends, 'category'),
      languages: this.calculateDistribution(trends, 'language'),
      regions: this.calculateDistribution(trends, 'region'),
    };

    // Get recent activity
    const recentActivity = {
      criticalAnomalies: [], // Would get from anomaly results
      emergingTopics: [], // Would get from topic analysis
      qualityDegradation: trends
        .filter(t => t.qualityScore < 0.5)
        .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
        .slice(0, 10),
    };

    return {
      summary,
      timeSeries,
      distributions,
      recentActivity,
    };
  }

  private calculateRiskScore(
    anomalies: AnomalyDetectionResult,
    quality: EvaluationResult
  ): number {
    // Combine anomaly score and quality score to calculate risk
    const anomalyRisk = anomalies.overallScore;
    const qualityRisk = 1 - quality.overallScore;

    return anomalyRisk * 0.6 + qualityRisk * 0.4;
  }

  private calculateViralityPotential(
    trend: TrendRecord,
    topics: TopicResult
  ): number {
    // Simple virality calculation based on engagement and topics
    const engagementScore = Math.min(trend.engagementCount / 1000, 1); // Normalize
    const topicRelevance = topics.confidence;
    const freshnessBoost = trend.freshnessScore > 0.8 ? 0.2 : 0;

    return Math.min(
      engagementScore * 0.5 + topicRelevance * 0.3 + freshnessBoost,
      1
    );
  }

  private calculateAuthenticity(
    anomalies: AnomalyDetectionResult,
    quality: EvaluationResult
  ): number {
    // Higher authenticity for lower anomaly scores and higher quality
    const anomalyPenalty = anomalies.overallScore;
    const qualityBonus = quality.overallScore;

    return Math.max(0, qualityBonus - anomalyPenalty * 0.5);
  }

  private calculateInfluence(trend: TrendRecord, topics: TopicResult): number {
    // Simple influence calculation
    const engagementInfluence = Math.min(trend.engagementCount / 5000, 1);
    const topicInfluence =
      topics.topics.length > 0 ? topics.topics[0].confidence : 0;
    const qualityInfluence = trend.qualityScore;

    return (
      engagementInfluence * 0.4 + topicInfluence * 0.3 + qualityInfluence * 0.3
    );
  }

  private generateRecommendations(
    anomalies: AnomalyDetectionResult,
    quality: EvaluationResult
  ): string[] {
    const recommendations: string[] = [];

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

    if (anomalies.anomalies.some(a => a.severity === 'critical')) {
      recommendations.push(
        'Critical anomalies detected - immediate review recommended'
      );
    }

    if (recommendations.length === 0) {
      recommendations.push('Content appears normal - continue monitoring');
    }

    return recommendations;
  }

  private async findSimilarTrends(trend: TrendRecord): Promise<TrendRecord[]> {
    // Find similar trends based on category and content similarity
    const { records } = await this.config.trendRepository.search({
      categories: [trend.category],
      limit: 5,
    });

    return records.filter(t => t.id !== trend.id);
  }

  private generateTimeSeries(
    trends: TrendRecord[],
    timeRange: string
  ): DashboardInsights['timeSeries'] {
    // Generate time series data for the dashboard
    const buckets = this.createTimeBuckets(timeRange);
    const trendVolume = buckets.map(bucket => ({
      timestamp: bucket.toISOString(),
      count: trends.filter(
        t =>
          t.timestamp >= bucket &&
          t.timestamp <
            new Date(bucket.getTime() + this.getBucketSize(timeRange))
      ).length,
    }));

    const qualityTrends = buckets.map(bucket => {
      const bucketTrends = trends.filter(
        t =>
          t.timestamp >= bucket &&
          t.timestamp <
            new Date(bucket.getTime() + this.getBucketSize(timeRange))
      );

      const avgQuality =
        bucketTrends.length > 0
          ? bucketTrends.reduce((sum, t) => sum + t.qualityScore, 0) /
            bucketTrends.length
          : 0;

      return {
        timestamp: bucket.toISOString(),
        avgQuality,
      };
    });

    return {
      trendVolume,
      qualityTrends,
      anomalyFrequency: buckets.map(bucket => ({
        timestamp: bucket.toISOString(),
        anomalies: 0, // Would calculate from anomaly data
      })),
    };
  }

  private calculateDistribution(
    trends: TrendRecord[],
    field: keyof TrendRecord
  ): Record<string, number> {
    const distribution: Record<string, number> = {};

    trends.forEach(trend => {
      const value = String(trend[field]);
      distribution[value] = (distribution[value] || 0) + 1;
    });

    return distribution;
  }

  private parseTimeRange(timeRange: string): number {
    const unit = timeRange.slice(-1);
    const value = parseInt(timeRange.slice(0, -1));

    switch (unit) {
      case 'h':
        return value * 60 * 60 * 1000;
      case 'd':
        return value * 24 * 60 * 60 * 1000;
      case 'w':
        return value * 7 * 24 * 60 * 60 * 1000;
      default:
        return 24 * 60 * 60 * 1000; // Default to 24h
    }
  }

  private createTimeBuckets(timeRange: string): Date[] {
    const bucketSize = this.getBucketSize(timeRange);
    const totalTime = this.parseTimeRange(timeRange);
    const bucketCount = Math.ceil(totalTime / bucketSize);
    const buckets: Date[] = [];

    for (let i = 0; i < bucketCount; i++) {
      buckets.push(new Date(Date.now() - totalTime + i * bucketSize));
    }

    return buckets;
  }

  private getBucketSize(timeRange: string): number {
    // Determine appropriate bucket size based on time range
    const totalTime = this.parseTimeRange(timeRange);

    if (totalTime <= 24 * 60 * 60 * 1000) {
      return 60 * 60 * 1000; // 1 hour buckets for <= 24h
    } else if (totalTime <= 7 * 24 * 60 * 60 * 1000) {
      return 6 * 60 * 60 * 1000; // 6 hour buckets for <= 7 days
    } else {
      return 24 * 60 * 60 * 1000; // 1 day buckets for > 7 days
    }
  }

  private checkRateLimit(clientIp: string): {
    allowed: boolean;
    retryAfter?: number;
  } {
    const now = Date.now();
    const windowMs = this.config.api.rateLimiting.windowMs;
    const maxRequests = this.config.api.rateLimiting.maxRequests;

    const clientData = this.rateLimitMap.get(clientIp);

    if (!clientData || now >= clientData.resetTime) {
      // Reset or initialize rate limit data
      this.rateLimitMap.set(clientIp, {
        count: 1,
        resetTime: now + windowMs,
      });
      return { allowed: true };
    }

    if (clientData.count >= maxRequests) {
      return {
        allowed: false,
        retryAfter: Math.ceil((clientData.resetTime - now) / 1000),
      };
    }

    clientData.count++;
    return { allowed: true };
  }

  private getFromCache(key: string): any {
    const cached = this.responseCache.get(key);
    if (cached && cached.expiry > Date.now()) {
      return cached.data;
    }
    return null;
  }

  private setCache(key: string, data: any, ttlSeconds: number): void {
    // Simple LRU eviction when cache is full
    if (this.responseCache.size >= this.config.api.caching.maxCacheSize) {
      const oldestKey = this.responseCache.keys().next().value;
      this.responseCache.delete(oldestKey);
    }

    this.responseCache.set(key, {
      data,
      expiry: Date.now() + ttlSeconds * 1000,
    });
  }

  private parseQueryOptions(query: any): any {
    return {
      includeAnalytics: query.includeAnalytics !== 'false',
      includeSimilar: query.includeSimilar === 'true',
      includeContext: query.includeContext === 'true',
    };
  }

  private updateApiStats(
    endpoint: string,
    success: boolean,
    responseTime: number,
    cached: boolean
  ): void {
    this.apiStats.totalRequests++;

    if (success) {
      this.apiStats.successfulRequests++;
    } else {
      this.apiStats.failedRequests++;
    }

    // Update running average response time
    const n = this.apiStats.totalRequests;
    this.apiStats.averageResponseTime =
      (this.apiStats.averageResponseTime * (n - 1) + responseTime) / n;

    // Update cache hit rate
    if (cached) {
      const hits =
        this.apiStats.cacheHitRate * this.apiStats.successfulRequests + 1;
      this.apiStats.cacheHitRate = hits / this.apiStats.successfulRequests;
    }

    // Track endpoint usage
    const currentUsage = this.apiStats.endpointUsage.get(endpoint) || 0;
    this.apiStats.endpointUsage.set(endpoint, currentUsage + 1);
  }

  private createSuccessResponse<T>(
    data: T,
    requestId: string,
    startTime: number,
    cached: boolean
  ): InsightsResponse<T> {
    return {
      success: true,
      data,
      metadata: {
        timestamp: new Date().toISOString(),
        requestId,
        processingTime: Date.now() - startTime,
        version: '1.0.0',
        cached,
      },
    };
  }

  private createErrorResponse(
    code: string,
    message: string,
    details: any,
    requestId: string,
    startTime: number
  ): InsightsResponse {
    return {
      success: false,
      error: {
        code,
        message,
        details,
      },
      metadata: {
        timestamp: new Date().toISOString(),
        requestId,
        processingTime: Date.now() - startTime,
        version: '1.0.0',
        cached: false,
      },
    };
  }

  private generateRequestId(): string {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private startMaintenanceTasks(): void {
    // Clean up expired cache entries
    setInterval(
      () => {
        const now = Date.now();
        for (const [key, cached] of this.responseCache.entries()) {
          if (cached.expiry <= now) {
            this.responseCache.delete(key);
          }
        }
      },
      5 * 60 * 1000
    ); // Every 5 minutes

    // Clean up old rate limit entries
    setInterval(
      () => {
        const now = Date.now();
        for (const [ip, data] of this.rateLimitMap.entries()) {
          if (now >= data.resetTime) {
            this.rateLimitMap.delete(ip);
          }
        }
      },
      10 * 60 * 1000
    ); // Every 10 minutes
  }

  /**
   * Get API performance statistics
   */
  getApiStats(): typeof this.apiStats & {
    successRate: number;
    requestsPerMinute: number;
    topEndpoints: Array<{ endpoint: string; requests: number }>;
  } {
    const successRate =
      this.apiStats.totalRequests > 0
        ? this.apiStats.successfulRequests / this.apiStats.totalRequests
        : 0;

    const requestsPerMinute = this.apiStats.totalRequests; // Would calculate properly with time tracking

    const topEndpoints = Array.from(this.apiStats.endpointUsage.entries())
      .map(([endpoint, requests]) => ({ endpoint, requests }))
      .sort((a, b) => b.requests - a.requests)
      .slice(0, 5);

    return {
      ...this.apiStats,
      successRate,
      requestsPerMinute,
      topEndpoints,
    };
  }

  /**
   * Cleanup resources
   */
  cleanup(): void {
    this.responseCache.clear();
    this.rateLimitMap.clear();
  }
}

export { InsightsApi };
