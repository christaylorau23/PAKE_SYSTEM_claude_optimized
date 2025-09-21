/**
 * PAKE System - Anomaly Detection Module
 *
 * Configurable anomaly detection with Z-score spike detection, configurable thresholds,
 * and source-specific tuning. Supports multiple detection algorithms and real-time scoring.
 */

import { EventEmitter } from 'events';
import { createLogger, Logger } from '../../orchestrator/src/utils/logger';
import { metrics } from '../../orchestrator/src/utils/metrics';
import { TrendRecord } from '../../trends/src/types/TrendRecord';

export interface AnomalyConfig {
  // Detection algorithms enabled
  algorithms: {
    zScore: boolean;
    isolation: boolean;
    seasonality: boolean;
    velocity: boolean;
    clustering: boolean;
  };

  // Thresholds per algorithm
  thresholds: {
    zScore: number; // Standard deviations (default: 2.5)
    isolation: number; // Isolation score threshold (0-1)
    seasonality: number; // Seasonal deviation threshold
    velocity: number; // Rate of change threshold
    clustering: number; // Distance from cluster centers
  };

  // Source-specific overrides
  sourceOverrides: Record<string, Partial<AnomalyConfig>>;

  // Temporal windows
  windows: {
    shortTerm: number; // Minutes for short-term analysis
    mediumTerm: number; // Hours for medium-term analysis
    longTerm: number; // Days for long-term analysis
  };

  // Data requirements
  minSampleSize: number; // Minimum samples needed for detection
  warmupPeriod: number; // Minutes to collect baseline data

  // Performance settings
  batchSize: number;
  maxConcurrency: number;

  // Feature flags
  enableRealtime: boolean;
  enableBatching: boolean;
  enableAdaptive: boolean; // Adaptive threshold adjustment
}

export interface AnomalyDetectionResult {
  recordId: string;
  anomalies: DetectedAnomaly[];
  overallScore: number; // 0-1 composite anomaly score
  confidence: number; // 0-1 confidence in detection
  baseline: BaselineMetrics;
  metadata: {
    algorithmsUsed: string[];
    processingTime: number;
    sampleSize: number;
    timestamp: Date;
  };
}

export interface DetectedAnomaly {
  type: AnomalyType;
  algorithm: string;
  score: number; // Raw anomaly score
  normalizedScore: number; // 0-1 normalized score
  severity: 'low' | 'medium' | 'high' | 'critical';
  confidence: number;
  description: string;
  context: {
    metric: string;
    expectedValue: number;
    actualValue: number;
    threshold: number;
    historicalMean: number;
    historicalStdDev: number;
  };
  metadata: Record<string, any>;
}

export enum AnomalyType {
  // Engagement anomalies
  ENGAGEMENT_SPIKE = 'engagement_spike',
  ENGAGEMENT_DROP = 'engagement_drop',
  UNUSUAL_VELOCITY = 'unusual_velocity',

  // Content anomalies
  CONTENT_SIMILARITY = 'content_similarity',
  LANGUAGE_ANOMALY = 'language_anomaly',
  LENGTH_ANOMALY = 'length_anomaly',

  // Temporal anomalies
  TIME_CLUSTERING = 'time_clustering',
  OFF_PEAK_ACTIVITY = 'off_peak_activity',
  SEASONAL_DEVIATION = 'seasonal_deviation',

  // Behavioral anomalies
  COORDINATED_BEHAVIOR = 'coordinated_behavior',
  BOT_SIGNATURES = 'bot_signatures',
  ASTROTURFING = 'astroturfing',

  // Network anomalies
  SOURCE_ANOMALY = 'source_anomaly',
  PROPAGATION_PATTERN = 'propagation_pattern',
  INFLUENCE_SPIKE = 'influence_spike',
}

interface BaselineMetrics {
  engagementMean: number;
  engagementStdDev: number;
  velocityMean: number;
  velocityStdDev: number;
  temporalPattern: number[];
  contentSimilarity: number;
  sourceDistribution: Record<string, number>;
}

interface TimeSeriesPoint {
  timestamp: Date;
  value: number;
  metadata?: Record<string, any>;
}

/**
 * Advanced anomaly detection engine with multiple algorithms
 */
export class AnomalyDetector extends EventEmitter {
  private readonly logger: Logger;
  private readonly config: AnomalyConfig;

  // Historical data storage
  private readonly historicalData = new Map<string, TimeSeriesPoint[]>();
  private readonly baselineCache = new Map<string, BaselineMetrics>();

  // Adaptive thresholds
  private readonly adaptiveThresholds = new Map<
    string,
    Record<string, number>
  >();

  // Performance tracking
  private readonly detectionStats = {
    totalDetections: 0,
    totalAnomalies: 0,
    processingTimes: [] as number[],
    algorithmUsage: new Map<string, number>(),
    falsePositiveRate: 0,
    accuracyMetrics: new Map<string, number>(),
  };

  constructor(config: Partial<AnomalyConfig> = {}) {
    super();

    this.logger = createLogger('AnomalyDetector');
    this.config = this.mergeWithDefaults(config);

    // Start cleanup interval
    this.startMaintenanceTasks();

    this.logger.info('AnomalyDetector initialized', {
      algorithms: this.config.algorithms,
      thresholds: this.config.thresholds,
    });
  }

  /**
   * Detect anomalies in a trend record
   */
  async detectAnomalies(
    record: TrendRecord,
    sourceId: string = record.platform
  ): Promise<AnomalyDetectionResult> {
    const startTime = Date.now();
    const effectiveConfig = this.getEffectiveConfig(sourceId);

    try {
      // Prepare data for analysis
      const analysisData = this.prepareAnalysisData(record);

      // Get historical baseline
      const baseline = await this.getBaseline(sourceId, analysisData);

      // Run enabled detection algorithms
      const anomalies = await this.runDetectionAlgorithms(
        analysisData,
        baseline,
        effectiveConfig
      );

      // Calculate composite scores
      const { overallScore, confidence } =
        this.calculateCompositeScore(anomalies);

      // Track performance metrics
      const processingTime = Date.now() - startTime;
      this.updatePerformanceStats(anomalies, processingTime);

      // Update historical data
      this.updateHistoricalData(sourceId, analysisData);

      const result: AnomalyDetectionResult = {
        recordId: record.id,
        anomalies,
        overallScore,
        confidence,
        baseline,
        metadata: {
          algorithmsUsed: this.getEnabledAlgorithms(effectiveConfig),
          processingTime,
          sampleSize: this.historicalData.get(sourceId)?.length || 0,
          timestamp: new Date(),
        },
      };

      // Emit events for monitoring
      this.emit('anomalies:detected', {
        sourceId,
        result,
        anomalyCount: anomalies.length,
      });

      // Track metrics
      metrics.counter('anomaly_detections_total', {
        source: sourceId,
        anomaly_count: anomalies.length.toString(),
        has_critical: anomalies.some(a => a.severity === 'critical').toString(),
      });

      metrics.histogram('anomaly_detection_duration', processingTime, 'ms', {
        source: sourceId,
        algorithms_used: this.getEnabledAlgorithms(effectiveConfig).join(','),
      });

      return result;
    } catch (error) {
      this.logger.error('Anomaly detection failed', {
        recordId: record.id,
        sourceId,
        error: error.message,
        stack: error.stack,
      });

      throw new Error(`Anomaly detection failed: ${error.message}`);
    }
  }

  /**
   * Batch anomaly detection for multiple records
   */
  async detectAnomaliesBatch(
    records: TrendRecord[],
    sourceId?: string
  ): Promise<AnomalyDetectionResult[]> {
    this.logger.info('Starting batch anomaly detection', {
      recordCount: records.length,
      sourceId,
    });

    const results: AnomalyDetectionResult[] = [];
    const batchSize = this.config.batchSize;

    // Process in batches to manage memory and concurrency
    for (let i = 0; i < records.length; i += batchSize) {
      const batch = records.slice(i, i + batchSize);

      const batchPromises = batch.map(record =>
        this.detectAnomalies(record, sourceId || record.platform)
      );

      const batchResults = await Promise.all(batchPromises);
      results.push(...batchResults);

      // Rate limiting between batches
      if (i + batchSize < records.length) {
        await this.sleep(100); // Brief pause between batches
      }
    }

    this.logger.info('Batch anomaly detection completed', {
      recordCount: records.length,
      totalAnomalies: results.reduce((sum, r) => sum + r.anomalies.length, 0),
    });

    return results;
  }

  /**
   * Z-score based spike detection
   */
  private async detectZScoreAnomalies(
    data: AnalysisData,
    baseline: BaselineMetrics,
    threshold: number
  ): Promise<DetectedAnomaly[]> {
    const anomalies: DetectedAnomaly[] = [];

    // Check engagement spike
    const engagementZScore = Math.abs(
      (data.engagementCount - baseline.engagementMean) /
        baseline.engagementStdDev
    );

    if (engagementZScore > threshold) {
      anomalies.push({
        type:
          data.engagementCount > baseline.engagementMean
            ? AnomalyType.ENGAGEMENT_SPIKE
            : AnomalyType.ENGAGEMENT_DROP,
        algorithm: 'z-score',
        score: engagementZScore,
        normalizedScore: Math.min(engagementZScore / (threshold * 2), 1),
        severity: this.categorizeSeverity(engagementZScore, threshold),
        confidence: this.calculateConfidence(
          engagementZScore,
          baseline.engagementStdDev
        ),
        description: `Engagement ${data.engagementCount > baseline.engagementMean ? 'spike' : 'drop'} detected: ${engagementZScore.toFixed(2)} standard deviations from baseline`,
        context: {
          metric: 'engagement_count',
          expectedValue: baseline.engagementMean,
          actualValue: data.engagementCount,
          threshold,
          historicalMean: baseline.engagementMean,
          historicalStdDev: baseline.engagementStdDev,
        },
        metadata: {
          algorithm: 'z-score',
          windowSize: this.config.windows.mediumTerm,
        },
      });
    }

    // Check velocity anomalies
    if (data.velocity && baseline.velocityStdDev > 0) {
      const velocityZScore = Math.abs(
        (data.velocity - baseline.velocityMean) / baseline.velocityStdDev
      );

      if (velocityZScore > threshold) {
        anomalies.push({
          type: AnomalyType.UNUSUAL_VELOCITY,
          algorithm: 'z-score',
          score: velocityZScore,
          normalizedScore: Math.min(velocityZScore / (threshold * 2), 1),
          severity: this.categorizeSeverity(velocityZScore, threshold),
          confidence: this.calculateConfidence(
            velocityZScore,
            baseline.velocityStdDev
          ),
          description: `Unusual velocity detected: ${velocityZScore.toFixed(2)} standard deviations from baseline`,
          context: {
            metric: 'velocity',
            expectedValue: baseline.velocityMean,
            actualValue: data.velocity,
            threshold,
            historicalMean: baseline.velocityMean,
            historicalStdDev: baseline.velocityStdDev,
          },
          metadata: {
            algorithm: 'z-score',
            velocityWindow: this.config.windows.shortTerm,
          },
        });
      }
    }

    return anomalies;
  }

  /**
   * Isolation forest based anomaly detection
   */
  private async detectIsolationAnomalies(
    data: AnalysisData,
    baseline: BaselineMetrics,
    threshold: number
  ): Promise<DetectedAnomaly[]> {
    const anomalies: DetectedAnomaly[] = [];

    // Simplified isolation score calculation
    // In a full implementation, this would use a proper isolation forest algorithm
    const features = [
      data.engagementCount / (baseline.engagementMean || 1),
      data.contentLength / 1000,
      data.velocity || 0,
      data.temporalFeatures.hourOfDay / 24,
    ];

    const isolationScore = this.calculateIsolationScore(features, baseline);

    if (isolationScore > threshold) {
      anomalies.push({
        type: AnomalyType.SOURCE_ANOMALY,
        algorithm: 'isolation-forest',
        score: isolationScore,
        normalizedScore: isolationScore,
        severity: this.categorizeSeverity(isolationScore * 10, 5), // Scale for severity
        confidence: Math.min(isolationScore * 1.2, 1),
        description: `Multivariate anomaly detected with isolation score: ${isolationScore.toFixed(3)}`,
        context: {
          metric: 'isolation_score',
          expectedValue: 0.1, // Expected low isolation score
          actualValue: isolationScore,
          threshold,
          historicalMean: 0.1,
          historicalStdDev: 0.05,
        },
        metadata: {
          algorithm: 'isolation-forest',
          features: ['engagement', 'content_length', 'velocity', 'temporal'],
          featureValues: features,
        },
      });
    }

    return anomalies;
  }

  /**
   * Temporal clustering based anomaly detection
   */
  private async detectTemporalAnomalies(
    data: AnalysisData,
    baseline: BaselineMetrics,
    threshold: number
  ): Promise<DetectedAnomaly[]> {
    const anomalies: DetectedAnomaly[] = [];

    const { hourOfDay, dayOfWeek } = data.temporalFeatures;
    const expectedActivity = baseline.temporalPattern[hourOfDay] || 0.5;

    // Detect off-peak activity
    const isOffPeak = expectedActivity < 0.3; // Low expected activity
    const hasHighActivity = data.engagementCount > baseline.engagementMean;

    if (isOffPeak && hasHighActivity) {
      const anomalyScore =
        (data.engagementCount / baseline.engagementMean) *
        (1 - expectedActivity);

      if (anomalyScore > threshold) {
        anomalies.push({
          type: AnomalyType.OFF_PEAK_ACTIVITY,
          algorithm: 'temporal-clustering',
          score: anomalyScore,
          normalizedScore: Math.min(anomalyScore / 5, 1),
          severity: this.categorizeSeverity(anomalyScore, threshold),
          confidence: 0.8, // High confidence for temporal patterns
          description: `High activity during typically low-activity period (hour ${hourOfDay})`,
          context: {
            metric: 'temporal_activity',
            expectedValue: expectedActivity,
            actualValue: data.engagementCount / baseline.engagementMean,
            threshold,
            historicalMean: expectedActivity,
            historicalStdDev: 0.1,
          },
          metadata: {
            algorithm: 'temporal-clustering',
            hourOfDay,
            dayOfWeek,
            expectedActivity,
            isWeekend: dayOfWeek >= 5,
          },
        });
      }
    }

    return anomalies;
  }

  /**
   * Get effective configuration with source overrides
   */
  private getEffectiveConfig(sourceId: string): AnomalyConfig {
    const override = this.config.sourceOverrides[sourceId];
    if (!override) return this.config;

    return {
      ...this.config,
      ...override,
      algorithms: { ...this.config.algorithms, ...override.algorithms },
      thresholds: { ...this.config.thresholds, ...override.thresholds },
      windows: { ...this.config.windows, ...override.windows },
    };
  }

  /**
   * Prepare analysis data from trend record
   */
  private prepareAnalysisData(record: TrendRecord): AnalysisData {
    const now = new Date();
    const recordTime = record.timestamp;
    const age = (now.getTime() - recordTime.getTime()) / (1000 * 60); // Age in minutes

    return {
      engagementCount: record.engagementCount,
      viewCount: record.viewCount,
      shareCount: record.shareCount,
      contentLength: record.content.length,
      velocity: this.calculateVelocity(record),
      temporalFeatures: {
        hourOfDay: recordTime.getHours(),
        dayOfWeek: recordTime.getDay(),
        age,
      },
      qualityScore: record.qualityScore,
      platform: record.platform,
      category: record.category,
    };
  }

  /**
   * Get baseline metrics for source
   */
  private async getBaseline(
    sourceId: string,
    currentData: AnalysisData
  ): Promise<BaselineMetrics> {
    const cached = this.baselineCache.get(sourceId);
    if (cached && this.isBaselineValid(cached)) {
      return cached;
    }

    const historicalData = this.historicalData.get(sourceId) || [];
    if (historicalData.length < this.config.minSampleSize) {
      // Use default baseline for new sources
      return this.getDefaultBaseline(currentData);
    }

    const baseline = this.calculateBaseline(historicalData);
    this.baselineCache.set(sourceId, baseline);

    return baseline;
  }

  /**
   * Calculate baseline metrics from historical data
   */
  private calculateBaseline(
    historicalData: TimeSeriesPoint[]
  ): BaselineMetrics {
    const engagementValues = historicalData.map(p => p.value);
    const velocityValues = historicalData
      .map((p, i) => (i > 0 ? p.value - historicalData[i - 1].value : 0))
      .slice(1);

    // Calculate temporal patterns (24-hour pattern)
    const temporalPattern = new Array(24).fill(0);
    const hourlyCounts = new Array(24).fill(0);

    historicalData.forEach(point => {
      const hour = point.timestamp.getHours();
      temporalPattern[hour] += point.value;
      hourlyCounts[hour]++;
    });

    // Normalize temporal patterns
    for (let i = 0; i < 24; i++) {
      temporalPattern[i] =
        hourlyCounts[i] > 0 ? temporalPattern[i] / hourlyCounts[i] : 0;
    }

    const maxActivity = Math.max(...temporalPattern);
    if (maxActivity > 0) {
      for (let i = 0; i < 24; i++) {
        temporalPattern[i] /= maxActivity;
      }
    }

    return {
      engagementMean: this.calculateMean(engagementValues),
      engagementStdDev: this.calculateStdDev(engagementValues),
      velocityMean: this.calculateMean(velocityValues),
      velocityStdDev: this.calculateStdDev(velocityValues),
      temporalPattern,
      contentSimilarity: 0.7, // Placeholder - would need content analysis
      sourceDistribution: {}, // Placeholder - would track source patterns
    };
  }

  /**
   * Run all enabled detection algorithms
   */
  private async runDetectionAlgorithms(
    data: AnalysisData,
    baseline: BaselineMetrics,
    config: AnomalyConfig
  ): Promise<DetectedAnomaly[]> {
    const allAnomalies: DetectedAnomaly[] = [];

    // Z-score detection
    if (config.algorithms.zScore) {
      const zScoreAnomalies = await this.detectZScoreAnomalies(
        data,
        baseline,
        config.thresholds.zScore
      );
      allAnomalies.push(...zScoreAnomalies);
      this.detectionStats.algorithmUsage.set(
        'z-score',
        (this.detectionStats.algorithmUsage.get('z-score') || 0) + 1
      );
    }

    // Isolation forest detection
    if (config.algorithms.isolation) {
      const isolationAnomalies = await this.detectIsolationAnomalies(
        data,
        baseline,
        config.thresholds.isolation
      );
      allAnomalies.push(...isolationAnomalies);
      this.detectionStats.algorithmUsage.set(
        'isolation',
        (this.detectionStats.algorithmUsage.get('isolation') || 0) + 1
      );
    }

    // Temporal detection
    if (config.algorithms.seasonality) {
      const temporalAnomalies = await this.detectTemporalAnomalies(
        data,
        baseline,
        config.thresholds.seasonality
      );
      allAnomalies.push(...temporalAnomalies);
      this.detectionStats.algorithmUsage.set(
        'temporal',
        (this.detectionStats.algorithmUsage.get('temporal') || 0) + 1
      );
    }

    // Remove duplicates and sort by severity
    return this.deduplicateAndPrioritize(allAnomalies);
  }

  /**
   * Calculate composite anomaly score and confidence
   */
  private calculateCompositeScore(anomalies: DetectedAnomaly[]): {
    overallScore: number;
    confidence: number;
  } {
    if (anomalies.length === 0) {
      return { overallScore: 0, confidence: 1 };
    }

    // Weighted composite score based on severity and algorithm confidence
    let weightedScore = 0;
    let totalWeight = 0;
    let confidenceSum = 0;

    anomalies.forEach(anomaly => {
      const weight = this.getSeverityWeight(anomaly.severity);
      weightedScore += anomaly.normalizedScore * weight;
      totalWeight += weight;
      confidenceSum += anomaly.confidence;
    });

    const overallScore = totalWeight > 0 ? weightedScore / totalWeight : 0;
    const confidence =
      anomalies.length > 0 ? confidenceSum / anomalies.length : 0;

    return {
      overallScore: Math.min(overallScore, 1),
      confidence: Math.min(confidence, 1),
    };
  }

  /**
   * Helper methods for calculations
   */
  private calculateMean(values: number[]): number {
    return values.length > 0
      ? values.reduce((sum, v) => sum + v, 0) / values.length
      : 0;
  }

  private calculateStdDev(values: number[]): number {
    if (values.length <= 1) return 0;

    const mean = this.calculateMean(values);
    const variance =
      values.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) /
      (values.length - 1);
    return Math.sqrt(variance);
  }

  private calculateVelocity(record: TrendRecord): number {
    const ageMinutes = (Date.now() - record.timestamp.getTime()) / (1000 * 60);
    return ageMinutes > 0 ? record.engagementCount / ageMinutes : 0;
  }

  private calculateIsolationScore(
    features: number[],
    baseline: BaselineMetrics
  ): number {
    // Simplified isolation score - measures deviation from expected patterns
    let deviationSum = 0;
    const totalFeatures = features.length;

    features.forEach((feature, index) => {
      // Normalize and calculate deviation (simplified approach)
      const expectedRange = index === 0 ? baseline.engagementMean : 1;
      const deviation =
        Math.abs(feature - expectedRange) / Math.max(expectedRange, 1);
      deviationSum += Math.min(deviation, 2); // Cap extreme deviations
    });

    return Math.min(deviationSum / totalFeatures, 1);
  }

  private categorizeSeverity(
    score: number,
    threshold: number
  ): DetectedAnomaly['severity'] {
    const ratio = score / threshold;
    if (ratio >= 3) return 'critical';
    if (ratio >= 2) return 'high';
    if (ratio >= 1.5) return 'medium';
    return 'low';
  }

  private calculateConfidence(score: number, stdDev: number): number {
    // Higher scores with lower standard deviations indicate higher confidence
    const baseConfidence = Math.min(score / 5, 1); // Normalize score
    const stabilityFactor = stdDev > 0 ? Math.min(1 / stdDev, 1) : 1;
    return Math.min(baseConfidence * stabilityFactor, 1);
  }

  private getSeverityWeight(severity: DetectedAnomaly['severity']): number {
    switch (severity) {
      case 'critical':
        return 4;
      case 'high':
        return 3;
      case 'medium':
        return 2;
      case 'low':
        return 1;
      default:
        return 1;
    }
  }

  private getEnabledAlgorithms(config: AnomalyConfig): string[] {
    const enabled = [];
    if (config.algorithms.zScore) enabled.push('z-score');
    if (config.algorithms.isolation) enabled.push('isolation');
    if (config.algorithms.seasonality) enabled.push('temporal');
    if (config.algorithms.velocity) enabled.push('velocity');
    if (config.algorithms.clustering) enabled.push('clustering');
    return enabled;
  }

  private deduplicateAndPrioritize(
    anomalies: DetectedAnomaly[]
  ): DetectedAnomaly[] {
    // Group by type and keep highest scoring anomaly per type
    const typeMap = new Map<AnomalyType, DetectedAnomaly>();

    anomalies.forEach(anomaly => {
      const existing = typeMap.get(anomaly.type);
      if (!existing || anomaly.score > existing.score) {
        typeMap.set(anomaly.type, anomaly);
      }
    });

    // Sort by severity and score
    return Array.from(typeMap.values()).sort((a, b) => {
      const severityOrder = { critical: 4, high: 3, medium: 2, low: 1 };
      const severityDiff =
        severityOrder[b.severity] - severityOrder[a.severity];
      return severityDiff !== 0 ? severityDiff : b.score - a.score;
    });
  }

  private updateHistoricalData(sourceId: string, data: AnalysisData): void {
    let history = this.historicalData.get(sourceId) || [];

    history.push({
      timestamp: new Date(),
      value: data.engagementCount,
      metadata: {
        velocity: data.velocity,
        contentLength: data.contentLength,
        qualityScore: data.qualityScore,
      },
    });

    // Limit history size (keep last N points)
    const maxHistory = this.config.windows.longTerm * 24 * 60; // Minutes in long-term window
    if (history.length > maxHistory) {
      history = history.slice(-maxHistory);
    }

    this.historicalData.set(sourceId, history);

    // Invalidate baseline cache to force recalculation
    this.baselineCache.delete(sourceId);
  }

  private updatePerformanceStats(
    anomalies: DetectedAnomaly[],
    processingTime: number
  ): void {
    this.detectionStats.totalDetections++;
    this.detectionStats.totalAnomalies += anomalies.length;
    this.detectionStats.processingTimes.push(processingTime);

    // Keep only last 1000 processing times
    if (this.detectionStats.processingTimes.length > 1000) {
      this.detectionStats.processingTimes =
        this.detectionStats.processingTimes.slice(-1000);
    }
  }

  private getDefaultBaseline(data: AnalysisData): BaselineMetrics {
    // Provide reasonable defaults for new sources
    return {
      engagementMean: 100,
      engagementStdDev: 50,
      velocityMean: 5,
      velocityStdDev: 2,
      temporalPattern: new Array(24).fill(0.5), // Uniform distribution
      contentSimilarity: 0.7,
      sourceDistribution: {},
    };
  }

  private isBaselineValid(baseline: BaselineMetrics): boolean {
    // Check if baseline is recent enough (within last hour)
    return true; // Simplified - would check timestamp in real implementation
  }

  private startMaintenanceTasks(): void {
    // Clean up old historical data every hour
    setInterval(
      () => {
        this.cleanupOldData();
      },
      60 * 60 * 1000
    );

    // Update adaptive thresholds every 30 minutes
    if (this.config.enableAdaptive) {
      setInterval(
        () => {
          this.updateAdaptiveThresholds();
        },
        30 * 60 * 1000
      );
    }
  }

  private cleanupOldData(): void {
    const cutoffTime = new Date(
      Date.now() - this.config.windows.longTerm * 24 * 60 * 60 * 1000
    );

    for (const [sourceId, history] of this.historicalData.entries()) {
      const filteredHistory = history.filter(
        point => point.timestamp > cutoffTime
      );
      if (filteredHistory.length !== history.length) {
        this.historicalData.set(sourceId, filteredHistory);
        this.baselineCache.delete(sourceId); // Invalidate baseline
      }
    }
  }

  private updateAdaptiveThresholds(): void {
    // Adjust thresholds based on false positive rates and accuracy metrics
    // This is a placeholder for a more sophisticated adaptive algorithm
    this.logger.debug('Updating adaptive thresholds', {
      currentStats: this.detectionStats,
    });
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private mergeWithDefaults(config: Partial<AnomalyConfig>): AnomalyConfig {
    return {
      algorithms: {
        zScore: true,
        isolation: true,
        seasonality: true,
        velocity: true,
        clustering: false,
        ...config.algorithms,
      },
      thresholds: {
        zScore: 2.5,
        isolation: 0.7,
        seasonality: 2.0,
        velocity: 3.0,
        clustering: 0.8,
        ...config.thresholds,
      },
      sourceOverrides: config.sourceOverrides || {},
      windows: {
        shortTerm: 60, // 1 hour
        mediumTerm: 720, // 12 hours
        longTerm: 7, // 7 days
        ...config.windows,
      },
      minSampleSize: 50,
      warmupPeriod: 60,
      batchSize: 100,
      maxConcurrency: 10,
      enableRealtime: true,
      enableBatching: true,
      enableAdaptive: false,
      ...config,
    };
  }

  /**
   * Get detection statistics
   */
  getStatistics(): typeof this.detectionStats & {
    averageProcessingTime: number;
  } {
    const avgProcessingTime =
      this.detectionStats.processingTimes.length > 0
        ? this.detectionStats.processingTimes.reduce(
            (sum, time) => sum + time,
            0
          ) / this.detectionStats.processingTimes.length
        : 0;

    return {
      ...this.detectionStats,
      averageProcessingTime: avgProcessingTime,
    };
  }

  /**
   * Update configuration
   */
  updateConfig(newConfig: Partial<AnomalyConfig>): void {
    Object.assign(this.config, newConfig);
    this.logger.info('Configuration updated', { newConfig });
  }

  /**
   * Reset historical data for testing
   */
  reset(): void {
    this.historicalData.clear();
    this.baselineCache.clear();
    this.adaptiveThresholds.clear();
  }

  /**
   * Cleanup resources
   */
  destroy(): void {
    this.removeAllListeners();
    this.historicalData.clear();
    this.baselineCache.clear();
    this.adaptiveThresholds.clear();
  }
}

// Internal interfaces
interface AnalysisData {
  engagementCount: number;
  viewCount: number;
  shareCount: number;
  contentLength: number;
  velocity: number;
  temporalFeatures: {
    hourOfDay: number;
    dayOfWeek: number;
    age: number; // Minutes since creation
  };
  qualityScore: number;
  platform: string;
  category: string;
}

export { AnomalyDetector };
