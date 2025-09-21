/**
 * PAKE System - Voice Quality Monitoring and Performance Tracking
 * Real-time monitoring of voice agent performance, quality, and system health
 */

import { EventEmitter } from 'events';
import { Logger } from '../utils/Logger';

export interface VoiceMonitorConfig {
  qualityThreshold: number; // Minimum acceptable quality score (0-1)
  latencyThreshold: number; // Maximum acceptable latency in ms
  enabled?: boolean; // Enable monitoring (default: true)
  metricsRetentionHours?: number; // How long to keep metrics (default: 24)
  alertingEnabled?: boolean; // Enable alerting (default: true)
}

export interface QualityMetrics {
  audioQuality: number; // Audio quality score (0-1)
  responseLatency: number; // Average response latency in ms
  transcriptionAccuracy: number; // Transcription accuracy score (0-1)
  conversationFlow: number; // Conversation flow score (0-1)
  userSatisfaction: number; // Inferred user satisfaction (0-1)
  uptime: number; // Service uptime percentage
}

export interface CallMetrics {
  callId: string;
  startTime: Date;
  endTime?: Date;
  duration: number;
  messageCount: number;
  averageResponseTime: number;
  qualityScores: QualityDataPoint[];
  errors: ErrorEvent[];
  userFeedback?: number;
}

export interface QualityDataPoint {
  timestamp: Date;
  audioQuality: number;
  latency: number;
  transcriptionScore: number;
  confidence: number;
  metadata?: Record<string, any>;
}

export interface ErrorEvent {
  timestamp: Date;
  type: string;
  message: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  context?: Record<string, any>;
}

export interface ApiMetrics {
  totalCalls: number;
  successfulCalls: number;
  failedCalls: number;
  averageLatency: number;
  errorRate: number;
  lastCallTime?: Date;
}

export interface PerformanceAlert {
  type: 'quality' | 'latency' | 'error' | 'availability';
  severity: 'warning' | 'critical';
  message: string;
  metrics: Record<string, any>;
  timestamp: Date;
  callId?: string;
}

/**
 * VoiceMonitor - Comprehensive monitoring for voice agent performance and quality
 * Tracks real-time metrics, quality scores, and generates alerts for degradation
 */
export class VoiceMonitor extends EventEmitter {
  private logger: Logger;
  private config: VoiceMonitorConfig;
  private activeCallMetrics: Map<string, CallMetrics> = new Map();
  private qualityHistory: QualityDataPoint[] = [];
  private errorHistory: ErrorEvent[] = [];
  private apiMetrics: ApiMetrics;
  private systemStartTime: Date;
  private monitoringInterval?: NodeJS.Timeout;
  private cleanupInterval?: NodeJS.Timeout;

  constructor(config: VoiceMonitorConfig) {
    super();
    this.config = { enabled: true, metricsRetentionHours: 24, alertingEnabled: true, ...config };
    this.logger = new Logger('VoiceMonitor');
    this.systemStartTime = new Date();

    // Initialize API metrics
    this.apiMetrics = {
      totalCalls: 0,
      successfulCalls: 0,
      failedCalls: 0,
      averageLatency: 0,
      errorRate: 0,
    };

    if (this.config.enabled) {
      this.startMonitoring();
      this.startCleanupProcess();
    }

    this.logger.info('Voice monitor initialized', {
      qualityThreshold: config.qualityThreshold,
      latencyThreshold: config.latencyThreshold,
      enabled: this.config.enabled,
    });
  }

  /**
   * Start monitoring a voice call
   */
  startCallMonitoring(callId: string, context: any = {}): void {
    if (!this.config.enabled) return;

    const callMetrics: CallMetrics = {
      callId,
      startTime: new Date(),
      duration: 0,
      messageCount: 0,
      averageResponseTime: 0,
      qualityScores: [],
      errors: [],
    };

    this.activeCallMetrics.set(callId, callMetrics);

    this.logger.debug('Started call monitoring', {
      callId,
      context: Object.keys(context),
    });

    this.emit('call-monitoring-started', { callId, startTime: callMetrics.startTime });
  }

  /**
   * Stop monitoring a voice call
   */
  stopCallMonitoring(callId: string): CallMetrics | null {
    if (!this.config.enabled) return null;

    const metrics = this.activeCallMetrics.get(callId);
    if (!metrics) {
      this.logger.warn('Attempted to stop monitoring non-existent call', { callId });
      return null;
    }

    metrics.endTime = new Date();
    metrics.duration = metrics.endTime.getTime() - metrics.startTime.getTime();

    // Calculate final averages
    if (metrics.qualityScores.length > 0) {
      metrics.averageResponseTime =
        metrics.qualityScores.reduce((sum, score) => sum + score.latency, 0) /
        metrics.qualityScores.length;
    }

    // Store in history (keep for retention period)
    this.activeCallMetrics.delete(callId);

    this.logger.info('Stopped call monitoring', {
      callId,
      duration: metrics.duration,
      messageCount: metrics.messageCount,
      averageResponseTime: metrics.averageResponseTime,
      qualityDataPoints: metrics.qualityScores.length,
      errors: metrics.errors.length,
    });

    this.emit('call-monitoring-stopped', {
      callId,
      metrics: this.sanitizeMetricsForEvent(metrics),
    });

    // Check for quality issues
    this.analyzeCallQuality(metrics);

    return metrics;
  }

  /**
   * Record a quality data point for a call
   */
  recordQualityDataPoint(callId: string, dataPoint: Partial<QualityDataPoint>): void {
    if (!this.config.enabled) return;

    const metrics = this.activeCallMetrics.get(callId);
    if (!metrics) {
      this.logger.warn('Cannot record quality data for unknown call', { callId });
      return;
    }

    const fullDataPoint: QualityDataPoint = {
      timestamp: new Date(),
      audioQuality: dataPoint.audioQuality || 0.8,
      latency: dataPoint.latency || 0,
      transcriptionScore: dataPoint.transcriptionScore || 0.9,
      confidence: dataPoint.confidence || 0.8,
      metadata: dataPoint.metadata,
    };

    metrics.qualityScores.push(fullDataPoint);
    this.qualityHistory.push(fullDataPoint);
    metrics.messageCount++;

    // Check for quality warnings
    this.checkQualityThresholds(callId, fullDataPoint);

    this.emit('quality-data-recorded', {
      callId,
      dataPoint: fullDataPoint,
    });
  }

  /**
   * Record an API call for metrics tracking
   */
  recordApiCall(method: string, endpoint: string): void {
    if (!this.config.enabled) return;

    this.apiMetrics.totalCalls++;
    this.apiMetrics.lastCallTime = new Date();

    this.logger.debug('API call recorded', { method, endpoint });
  }

  /**
   * Record API response latency
   */
  recordApiLatency(endpoint: string, latency: number): void {
    if (!this.config.enabled) return;

    this.apiMetrics.successfulCalls++;

    // Update average latency
    const totalSuccessful = this.apiMetrics.successfulCalls;
    this.apiMetrics.averageLatency =
      (this.apiMetrics.averageLatency * (totalSuccessful - 1) + latency) / totalSuccessful;

    // Update error rate
    this.apiMetrics.errorRate = this.apiMetrics.failedCalls / this.apiMetrics.totalCalls;

    // Check latency threshold
    if (latency > this.config.latencyThreshold) {
      this.recordError('api_latency', `High API latency: ${latency}ms`, 'warning', {
        endpoint,
        latency,
        threshold: this.config.latencyThreshold,
      });
    }
  }

  /**
   * Record API error
   */
  recordApiError(endpoint: string, error: any): void {
    if (!this.config.enabled) return;

    this.apiMetrics.failedCalls++;

    // Update error rate
    this.apiMetrics.errorRate = this.apiMetrics.failedCalls / this.apiMetrics.totalCalls;

    this.recordError('api_error', `API call failed: ${error.message}`, 'medium', {
      endpoint,
      status: error.response?.status,
      message: error.message,
    });
  }

  /**
   * Record a general error event
   */
  recordError(
    type: string,
    message: string,
    severity: ErrorEvent['severity'] = 'medium',
    context?: Record<string, any>
  ): void {
    if (!this.config.enabled) return;

    const errorEvent: ErrorEvent = {
      timestamp: new Date(),
      type,
      message,
      severity,
      context,
    };

    this.errorHistory.push(errorEvent);

    this.logger.error('Voice agent error recorded', {
      type,
      message,
      severity,
      context,
    });

    this.emit('error-recorded', errorEvent);

    // Send alert if critical
    if (severity === 'critical' && this.config.alertingEnabled) {
      this.sendAlert({
        type: 'error',
        severity: 'critical',
        message: `Critical error: ${message}`,
        metrics: { type, context },
        timestamp: errorEvent.timestamp,
      });
    }
  }

  /**
   * Get current quality metrics
   */
  getQualityMetrics(): QualityMetrics {
    if (!this.config.enabled) {
      return this.getEmptyQualityMetrics();
    }

    const recentDataPoints = this.getRecentQualityDataPoints(3600000); // Last hour

    if (recentDataPoints.length === 0) {
      return this.getEmptyQualityMetrics();
    }

    const avgAudioQuality =
      recentDataPoints.reduce((sum, dp) => sum + dp.audioQuality, 0) / recentDataPoints.length;
    const avgLatency =
      recentDataPoints.reduce((sum, dp) => sum + dp.latency, 0) / recentDataPoints.length;
    const avgTranscription =
      recentDataPoints.reduce((sum, dp) => sum + dp.transcriptionScore, 0) /
      recentDataPoints.length;
    const avgConfidence =
      recentDataPoints.reduce((sum, dp) => sum + dp.confidence, 0) / recentDataPoints.length;

    // Calculate conversation flow score (simplified)
    const conversationFlow = this.calculateConversationFlowScore(recentDataPoints);

    // Calculate user satisfaction (inferred from quality metrics)
    const userSatisfaction =
      (avgAudioQuality + avgTranscription + avgConfidence + conversationFlow) / 4;

    // Calculate uptime
    const uptime = this.calculateUptime();

    return {
      audioQuality: Number(avgAudioQuality.toFixed(3)),
      responseLatency: Number(avgLatency.toFixed(0)),
      transcriptionAccuracy: Number(avgTranscription.toFixed(3)),
      conversationFlow: Number(conversationFlow.toFixed(3)),
      userSatisfaction: Number(userSatisfaction.toFixed(3)),
      uptime: Number(uptime.toFixed(3)),
    };
  }

  /**
   * Get API metrics
   */
  getApiMetrics(): ApiMetrics {
    return { ...this.apiMetrics };
  }

  /**
   * Get comprehensive monitoring report
   */
  getMonitoringReport(): {
    overview: QualityMetrics;
    api: ApiMetrics;
    activeCalls: number;
    recentErrors: ErrorEvent[];
    alerts: PerformanceAlert[];
    uptime: string;
  } {
    const recentErrors = this.errorHistory.slice(-10);
    const uptime = Date.now() - this.systemStartTime.getTime();

    return {
      overview: this.getQualityMetrics(),
      api: this.getApiMetrics(),
      activeCalls: this.activeCallMetrics.size,
      recentErrors,
      alerts: [], // Would store recent alerts in production
      uptime: this.formatUptime(uptime),
    };
  }

  /**
   * Check quality thresholds and send warnings
   */
  private checkQualityThresholds(callId: string, dataPoint: QualityDataPoint): void {
    const warnings = [];

    if (dataPoint.audioQuality < this.config.qualityThreshold) {
      warnings.push(`Audio quality below threshold: ${(dataPoint.audioQuality * 100).toFixed(1)}%`);
    }

    if (dataPoint.latency > this.config.latencyThreshold) {
      warnings.push(`Response latency above threshold: ${dataPoint.latency}ms`);
    }

    if (dataPoint.transcriptionScore < this.config.qualityThreshold) {
      warnings.push(
        `Transcription accuracy below threshold: ${(dataPoint.transcriptionScore * 100).toFixed(1)}%`
      );
    }

    if (warnings.length > 0 && this.config.alertingEnabled) {
      this.emit('quality-warning', {
        callId,
        warnings,
        dataPoint,
        timestamp: dataPoint.timestamp,
      });

      this.sendAlert({
        type: 'quality',
        severity: 'warning',
        message: `Quality issues detected: ${warnings.join(', ')}`,
        metrics: { callId, dataPoint },
        timestamp: dataPoint.timestamp,
        callId,
      });
    }
  }

  /**
   * Analyze overall call quality and generate insights
   */
  private analyzeCallQuality(metrics: CallMetrics): void {
    if (metrics.qualityScores.length === 0) return;

    const avgQuality =
      metrics.qualityScores.reduce((sum, score) => sum + score.audioQuality, 0) /
      metrics.qualityScores.length;

    const avgLatency = metrics.averageResponseTime;
    const errorCount = metrics.errors.length;

    // Determine overall call quality
    let overallQuality = 'good';
    if (
      avgQuality < this.config.qualityThreshold ||
      avgLatency > this.config.latencyThreshold ||
      errorCount > 2
    ) {
      overallQuality = 'poor';
    } else if (
      avgQuality < this.config.qualityThreshold * 1.2 ||
      avgLatency > this.config.latencyThreshold * 0.8
    ) {
      overallQuality = 'fair';
    }

    this.logger.info('Call quality analysis completed', {
      callId: metrics.callId,
      overallQuality,
      avgQuality: avgQuality.toFixed(3),
      avgLatency: avgLatency.toFixed(0),
      errorCount,
      duration: metrics.duration,
    });

    this.emit('call-quality-analyzed', {
      callId: metrics.callId,
      overallQuality,
      metrics: this.sanitizeMetricsForEvent(metrics),
    });
  }

  /**
   * Send performance alert
   */
  private sendAlert(alert: PerformanceAlert): void {
    this.logger.warn('Performance alert triggered', alert);
    this.emit('performance-alert', alert);

    // In production, this would integrate with alerting systems
    // like PagerDuty, Slack, email notifications, etc.
  }

  /**
   * Get recent quality data points within time window
   */
  private getRecentQualityDataPoints(timeWindowMs: number): QualityDataPoint[] {
    const cutoff = Date.now() - timeWindowMs;
    return this.qualityHistory.filter((dp) => dp.timestamp.getTime() > cutoff);
  }

  /**
   * Calculate conversation flow score based on response patterns
   */
  private calculateConversationFlowScore(dataPoints: QualityDataPoint[]): number {
    if (dataPoints.length < 2) return 0.8; // Default good score for short conversations

    // Analyze latency consistency
    const latencies = dataPoints.map((dp) => dp.latency);
    const avgLatency = latencies.reduce((sum, lat) => sum + lat, 0) / latencies.length;
    const latencyVariance =
      latencies.reduce((sum, lat) => sum + Math.pow(lat - avgLatency, 2), 0) / latencies.length;
    const latencyStdDev = Math.sqrt(latencyVariance);

    // Lower variance = better flow
    const consistencyScore = Math.max(0, 1 - latencyStdDev / avgLatency);

    // Analyze confidence trends
    const confidences = dataPoints.map((dp) => dp.confidence);
    const avgConfidence = confidences.reduce((sum, conf) => sum + conf, 0) / confidences.length;

    // Combine factors
    return consistencyScore * 0.6 + avgConfidence * 0.4;
  }

  /**
   * Calculate system uptime percentage
   */
  private calculateUptime(): number {
    // Simplified uptime calculation
    // In production, would track actual downtime events
    const totalTime = Date.now() - this.systemStartTime.getTime();
    const criticalErrors = this.errorHistory.filter((err) => err.severity === 'critical').length;

    // Assume each critical error represents 1 minute of downtime
    const estimatedDowntime = criticalErrors * 60000; // 1 minute per critical error

    return Math.max(0, (totalTime - estimatedDowntime) / totalTime);
  }

  /**
   * Get empty quality metrics (when monitoring is disabled)
   */
  private getEmptyQualityMetrics(): QualityMetrics {
    return {
      audioQuality: 0,
      responseLatency: 0,
      transcriptionAccuracy: 0,
      conversationFlow: 0,
      userSatisfaction: 0,
      uptime: 0,
    };
  }

  /**
   * Sanitize metrics for event emission (remove sensitive data)
   */
  private sanitizeMetricsForEvent(metrics: CallMetrics): any {
    return {
      callId: metrics.callId,
      duration: metrics.duration,
      messageCount: metrics.messageCount,
      averageResponseTime: metrics.averageResponseTime,
      qualityScoresCount: metrics.qualityScores.length,
      errorCount: metrics.errors.length,
      userFeedback: metrics.userFeedback,
    };
  }

  /**
   * Format uptime duration
   */
  private formatUptime(uptimeMs: number): string {
    const seconds = Math.floor(uptimeMs / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days}d ${hours % 24}h ${minutes % 60}m`;
    if (hours > 0) return `${hours}h ${minutes % 60}m`;
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    return `${seconds}s`;
  }

  /**
   * Start periodic monitoring tasks
   */
  private startMonitoring(): void {
    this.monitoringInterval = setInterval(() => {
      // Emit health check
      const metrics = this.getQualityMetrics();
      this.emit('health-check', {
        timestamp: new Date(),
        activeCalls: this.activeCallMetrics.size,
        metrics,
      });

      // Check for degraded performance
      if (metrics.responseLatency > this.config.latencyThreshold * 2) {
        this.sendAlert({
          type: 'latency',
          severity: 'warning',
          message: `High system latency detected: ${metrics.responseLatency}ms`,
          metrics: { averageLatency: metrics.responseLatency },
          timestamp: new Date(),
        });
      }

      if (metrics.audioQuality < this.config.qualityThreshold) {
        this.sendAlert({
          type: 'quality',
          severity: 'warning',
          message: `Low audio quality detected: ${(metrics.audioQuality * 100).toFixed(1)}%`,
          metrics: { audioQuality: metrics.audioQuality },
          timestamp: new Date(),
        });
      }
    }, 30000); // Every 30 seconds
  }

  /**
   * Start cleanup process for old metrics
   */
  private startCleanupProcess(): void {
    this.cleanupInterval = setInterval(() => {
      const retentionMs = (this.config.metricsRetentionHours || 24) * 3600000;
      const cutoff = Date.now() - retentionMs;

      // Clean quality history
      const oldQualityCount = this.qualityHistory.length;
      this.qualityHistory = this.qualityHistory.filter((dp) => dp.timestamp.getTime() > cutoff);

      // Clean error history
      const oldErrorCount = this.errorHistory.length;
      this.errorHistory = this.errorHistory.filter((err) => err.timestamp.getTime() > cutoff);

      const cleanedQuality = oldQualityCount - this.qualityHistory.length;
      const cleanedErrors = oldErrorCount - this.errorHistory.length;

      if (cleanedQuality > 0 || cleanedErrors > 0) {
        this.logger.debug('Cleaned old metrics', {
          qualityDataPoints: cleanedQuality,
          errorEvents: cleanedErrors,
        });
      }
    }, 3600000); // Every hour
  }

  /**
   * Get call metrics for a specific call
   */
  getCallMetrics(callId: string): CallMetrics | null {
    return this.activeCallMetrics.get(callId) || null;
  }

  /**
   * Set user feedback for a completed call
   */
  setUserFeedback(callId: string, rating: number): void {
    // For completed calls, you might need to store this separately
    // as the call might no longer be in activeCallMetrics
    this.logger.info('User feedback recorded', { callId, rating });
    this.emit('user-feedback', { callId, rating, timestamp: new Date() });
  }

  /**
   * Stop monitoring and cleanup resources
   */
  stop(): void {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
      this.monitoringInterval = undefined;
    }

    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = undefined;
    }

    // Stop monitoring all active calls
    const activeCallIds = Array.from(this.activeCallMetrics.keys());
    for (const callId of activeCallIds) {
      this.stopCallMonitoring(callId);
    }

    this.removeAllListeners();
    this.logger.info('Voice monitor stopped');
  }

  /**
   * Reset all metrics (for testing or maintenance)
   */
  reset(): void {
    this.qualityHistory = [];
    this.errorHistory = [];
    this.activeCallMetrics.clear();

    this.apiMetrics = {
      totalCalls: 0,
      successfulCalls: 0,
      failedCalls: 0,
      averageLatency: 0,
      errorRate: 0,
    };

    this.systemStartTime = new Date();
    this.logger.info('Voice monitor metrics reset');
    this.emit('metrics-reset', { timestamp: new Date() });
  }
}

export default VoiceMonitor;
