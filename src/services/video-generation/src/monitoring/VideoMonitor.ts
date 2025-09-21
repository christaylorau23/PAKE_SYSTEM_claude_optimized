/**
 * PAKE System - Video Generation Monitoring Service
 * Comprehensive monitoring for video generation workflows and provider performance
 */

import { EventEmitter } from 'events';
import {
  VideoGenerationRequest,
  VideoGenerationResponse,
  VideoStatus,
  ProviderMetrics,
  ProcessingStats,
  QueueMetrics,
  JobPriority,
} from '../types';
import { Logger } from '../utils/Logger';

interface ProcessingMetric {
  videoId: string;
  provider: string;
  startTime: Date;
  endTime?: Date;
  duration?: number;
  status: VideoStatus;
  error?: string;
  quality?: number;
  cost?: number;
  metadata: any;
}

interface ProviderHealth {
  provider: string;
  healthy: boolean;
  lastCheck: Date;
  responseTime: number;
  errorRate: number;
  successRate: number;
  totalRequests: number;
  failedRequests: number;
}

export class VideoMonitor extends EventEmitter {
  private logger: Logger;
  private metrics: Map<string, ProcessingMetric> = new Map();
  private providerHealth: Map<string, ProviderHealth> = new Map();
  private queueStats = {
    totalJobs: 0,
    pendingJobs: 0,
    processingJobs: 0,
    completedJobs: 0,
    failedJobs: 0,
    averageProcessingTime: 0,
    successRate: 0,
  };

  constructor() {
    super();
    this.logger = new Logger('VideoMonitor');
    this.startPeriodicCleanup();
  }

  /**
   * Start monitoring a video generation request
   */
  startMonitoring(videoId: string, request: VideoGenerationRequest): void {
    const metric: ProcessingMetric = {
      videoId,
      provider: request.provider,
      startTime: new Date(),
      status: VideoStatus.PENDING,
      metadata: {
        scriptLength: request.script.length,
        avatarId: request.avatarSettings.avatarId,
        voiceId: request.voiceSettings.voiceId,
        resolution: request.videoSettings.resolution,
        format: request.videoSettings.format,
      },
    };

    this.metrics.set(videoId, metric);
    this.queueStats.totalJobs++;
    this.queueStats.pendingJobs++;

    this.logger.info('Started video monitoring', {
      videoId,
      provider: request.provider,
    });
    this.emit('monitoring-started', { videoId, metric });
  }

  /**
   * Update video processing status
   */
  updateStatus(
    videoId: string,
    status: VideoStatus,
    additionalData?: any
  ): void {
    const metric = this.metrics.get(videoId);
    if (!metric) {
      this.logger.warn('Attempted to update unknown video', { videoId });
      return;
    }

    const previousStatus = metric.status;
    metric.status = status;

    // Update queue statistics
    if (
      previousStatus === VideoStatus.PENDING &&
      status === VideoStatus.PROCESSING
    ) {
      this.queueStats.pendingJobs--;
      this.queueStats.processingJobs++;
    } else if (
      previousStatus === VideoStatus.PROCESSING &&
      status === VideoStatus.COMPLETED
    ) {
      this.queueStats.processingJobs--;
      this.queueStats.completedJobs++;
      metric.endTime = new Date();
      metric.duration = metric.endTime.getTime() - metric.startTime.getTime();
      this.updateAverageProcessingTime();
    } else if (status === VideoStatus.FAILED) {
      if (previousStatus === VideoStatus.PENDING) this.queueStats.pendingJobs--;
      if (previousStatus === VideoStatus.PROCESSING)
        this.queueStats.processingJobs--;
      this.queueStats.failedJobs++;
      metric.endTime = new Date();
      metric.error = additionalData?.error;
    }

    // Update additional data
    if (additionalData) {
      metric.quality = additionalData.quality;
      metric.cost = additionalData.cost;
      metric.metadata = { ...metric.metadata, ...additionalData };
    }

    this.updateSuccessRate();
    this.updateProviderMetrics(metric.provider, status);

    this.logger.info('Video status updated', {
      videoId,
      status,
      previousStatus,
      duration: metric.duration,
    });

    this.emit('status-updated', { videoId, status, metric });
  }

  /**
   * Record provider health check
   */
  recordProviderHealth(
    provider: string,
    healthy: boolean,
    responseTime: number,
    error?: string
  ): void {
    let health = this.providerHealth.get(provider);

    if (!health) {
      health = {
        provider,
        healthy,
        lastCheck: new Date(),
        responseTime,
        errorRate: 0,
        successRate: 0,
        totalRequests: 0,
        failedRequests: 0,
      };
      this.providerHealth.set(provider, health);
    }

    health.healthy = healthy;
    health.lastCheck = new Date();
    health.responseTime = responseTime;
    health.totalRequests++;

    if (!healthy) {
      health.failedRequests++;
    }

    health.errorRate = (health.failedRequests / health.totalRequests) * 100;
    health.successRate = 100 - health.errorRate;

    this.logger.debug('Provider health recorded', {
      provider,
      healthy,
      responseTime,
      errorRate: health.errorRate.toFixed(2),
    });

    this.emit('provider-health-updated', { provider, health });

    // Alert if provider is unhealthy
    if (!healthy) {
      this.emit('provider-unhealthy', { provider, error, health });
    }
  }

  /**
   * Get comprehensive processing statistics
   */
  getProcessingStats(): ProcessingStats {
    const completedMetrics = Array.from(this.metrics.values()).filter(
      m => m.status === VideoStatus.COMPLETED && m.duration
    );

    const totalProcessed = completedMetrics.length;
    const averageProcessingTime =
      totalProcessed > 0
        ? completedMetrics.reduce((sum, m) => sum + (m.duration || 0), 0) /
          totalProcessed
        : 0;

    const totalCost = completedMetrics.reduce(
      (sum, m) => sum + (m.cost || 0),
      0
    );
    const avgCostPerVideo = totalProcessed > 0 ? totalCost / totalProcessed : 0;

    const costByProvider: Record<string, number> = {};
    const qualityScores = completedMetrics
      .filter(m => m.quality !== undefined)
      .map(m => m.quality!);

    // Calculate cost by provider
    completedMetrics.forEach(metric => {
      if (metric.cost) {
        costByProvider[metric.provider] =
          (costByProvider[metric.provider] || 0) + metric.cost;
      }
    });

    const avgQualityScore =
      qualityScores.length > 0
        ? qualityScores.reduce((sum, q) => sum + q, 0) / qualityScores.length
        : 0;

    const highQualityCount = qualityScores.filter(q => q >= 0.8).length;
    const lowQualityCount = qualityScores.filter(q => q < 0.6).length;

    return {
      totalProcessed,
      averageProcessingTime,
      successRate: this.queueStats.successRate,
      errorRate: 100 - this.queueStats.successRate,
      costAnalysis: {
        totalCost,
        avgCostPerVideo,
        costByProvider,
      },
      qualityMetrics: {
        avgQualityScore,
        highQualityCount,
        lowQualityCount,
      },
    };
  }

  /**
   * Get queue metrics
   */
  getQueueMetrics(): QueueMetrics {
    return { ...this.queueStats };
  }

  /**
   * Get provider metrics
   */
  getProviderMetrics(): ProviderMetrics[] {
    return Array.from(this.providerHealth.values()).map(health => ({
      name: health.provider,
      totalRequests: health.totalRequests,
      successfulRequests: health.totalRequests - health.failedRequests,
      failedRequests: health.failedRequests,
      averageResponseTime: health.responseTime,
      uptime: health.successRate,
      lastError: health.healthy ? undefined : 'Provider health check failed',
      costPerRequest: this.calculateAverageCostForProvider(health.provider),
    }));
  }

  /**
   * Get video processing timeline
   */
  getVideoTimeline(videoId: string): any {
    const metric = this.metrics.get(videoId);
    if (!metric) return null;

    return {
      videoId,
      provider: metric.provider,
      startTime: metric.startTime,
      endTime: metric.endTime,
      duration: metric.duration,
      status: metric.status,
      milestones: this.getVideoMilestones(videoId),
      metadata: metric.metadata,
    };
  }

  /**
   * Get performance insights
   */
  getPerformanceInsights(): any {
    const stats = this.getProcessingStats();
    const providers = this.getProviderMetrics();

    const insights = {
      performance: {
        status:
          stats.successRate > 95
            ? 'excellent'
            : stats.successRate > 85
              ? 'good'
              : stats.successRate > 70
                ? 'fair'
                : 'poor',
        averageProcessingTime: stats.averageProcessingTime,
        successRate: stats.successRate,
        recommendations: [],
      },
      costs: {
        trend: this.analyzeCostTrend(),
        efficiency: stats.costAnalysis.avgCostPerVideo,
        recommendations: [],
      },
      quality: {
        average: stats.qualityMetrics.avgQualityScore,
        trend: this.analyzeQualityTrend(),
        recommendations: [],
      },
      providers: providers.map(p => ({
        name: p.name,
        reliability: p.uptime,
        performance: p.averageResponseTime,
        recommendation: this.getProviderRecommendation(p),
      })),
    };

    // Add performance recommendations
    if (stats.averageProcessingTime > 300000) {
      // 5 minutes
      insights.performance.recommendations.push(
        'Consider optimizing video processing workflows'
      );
    }

    if (stats.successRate < 90) {
      insights.performance.recommendations.push(
        'Investigate and resolve frequent failures'
      );
    }

    return insights;
  }

  /**
   * Get alerts and warnings
   */
  getActiveAlerts(): any[] {
    const alerts = [];
    const stats = this.getProcessingStats();

    // High error rate alert
    if (stats.errorRate > 15) {
      alerts.push({
        type: 'error',
        severity: 'high',
        message: `High error rate detected: ${stats.errorRate.toFixed(1)}%`,
        threshold: '15%',
        action: 'Investigate provider issues and error patterns',
      });
    }

    // Slow processing alert
    if (stats.averageProcessingTime > 600000) {
      // 10 minutes
      alerts.push({
        type: 'performance',
        severity: 'medium',
        message: `Slow average processing time: ${(stats.averageProcessingTime / 1000).toFixed(1)}s`,
        threshold: '600s',
        action: 'Review processing optimization opportunities',
      });
    }

    // Provider health alerts
    for (const [provider, health] of this.providerHealth.entries()) {
      if (!health.healthy) {
        alerts.push({
          type: 'provider',
          severity: 'high',
          message: `Provider ${provider} is unhealthy`,
          lastCheck: health.lastCheck,
          action: 'Check provider API status and credentials',
        });
      }

      if (health.errorRate > 20) {
        alerts.push({
          type: 'provider',
          severity: 'medium',
          message: `High error rate for ${provider}: ${health.errorRate.toFixed(1)}%`,
          threshold: '20%',
          action: 'Review provider configuration and limits',
        });
      }
    }

    // Queue backlog alert
    if (this.queueStats.pendingJobs > 100) {
      alerts.push({
        type: 'queue',
        severity: 'medium',
        message: `High queue backlog: ${this.queueStats.pendingJobs} pending jobs`,
        threshold: '100 jobs',
        action: 'Consider scaling processing capacity',
      });
    }

    return alerts;
  }

  /**
   * Update average processing time
   */
  private updateAverageProcessingTime(): void {
    const completedMetrics = Array.from(this.metrics.values()).filter(
      m => m.status === VideoStatus.COMPLETED && m.duration
    );

    if (completedMetrics.length > 0) {
      this.queueStats.averageProcessingTime =
        completedMetrics.reduce((sum, m) => sum + (m.duration || 0), 0) /
        completedMetrics.length;
    }
  }

  /**
   * Update success rate
   */
  private updateSuccessRate(): void {
    const totalCompleted =
      this.queueStats.completedJobs + this.queueStats.failedJobs;
    if (totalCompleted > 0) {
      this.queueStats.successRate =
        (this.queueStats.completedJobs / totalCompleted) * 100;
    }
  }

  /**
   * Update provider-specific metrics
   */
  private updateProviderMetrics(provider: string, status: VideoStatus): void {
    // This would update detailed provider metrics
    // Implementation depends on specific tracking requirements
  }

  /**
   * Calculate average cost for a provider
   */
  private calculateAverageCostForProvider(provider: string): number {
    const providerMetrics = Array.from(this.metrics.values()).filter(
      m => m.provider === provider && m.cost !== undefined
    );

    if (providerMetrics.length === 0) return 0;

    return (
      providerMetrics.reduce((sum, m) => sum + (m.cost || 0), 0) /
      providerMetrics.length
    );
  }

  /**
   * Analyze cost trend
   */
  private analyzeCostTrend(): 'increasing' | 'decreasing' | 'stable' {
    // Simplified trend analysis
    const recentMetrics = Array.from(this.metrics.values())
      .filter(m => m.cost !== undefined && m.endTime)
      .sort((a, b) => (b.endTime?.getTime() || 0) - (a.endTime?.getTime() || 0))
      .slice(0, 50);

    if (recentMetrics.length < 10) return 'stable';

    const firstHalf = recentMetrics.slice(
      0,
      Math.floor(recentMetrics.length / 2)
    );
    const secondHalf = recentMetrics.slice(
      Math.floor(recentMetrics.length / 2)
    );

    const firstAvg =
      firstHalf.reduce((sum, m) => sum + (m.cost || 0), 0) / firstHalf.length;
    const secondAvg =
      secondHalf.reduce((sum, m) => sum + (m.cost || 0), 0) / secondHalf.length;

    const percentChange = ((firstAvg - secondAvg) / secondAvg) * 100;

    if (percentChange > 10) return 'increasing';
    if (percentChange < -10) return 'decreasing';
    return 'stable';
  }

  /**
   * Analyze quality trend
   */
  private analyzeQualityTrend(): 'improving' | 'declining' | 'stable' {
    // Similar to cost trend analysis but for quality scores
    const recentMetrics = Array.from(this.metrics.values())
      .filter(m => m.quality !== undefined && m.endTime)
      .sort((a, b) => (b.endTime?.getTime() || 0) - (a.endTime?.getTime() || 0))
      .slice(0, 50);

    if (recentMetrics.length < 10) return 'stable';

    const firstHalf = recentMetrics.slice(
      0,
      Math.floor(recentMetrics.length / 2)
    );
    const secondHalf = recentMetrics.slice(
      Math.floor(recentMetrics.length / 2)
    );

    const firstAvg =
      firstHalf.reduce((sum, m) => sum + (m.quality || 0), 0) /
      firstHalf.length;
    const secondAvg =
      secondHalf.reduce((sum, m) => sum + (m.quality || 0), 0) /
      secondHalf.length;

    const percentChange = ((firstAvg - secondAvg) / secondAvg) * 100;

    if (percentChange > 5) return 'improving';
    if (percentChange < -5) return 'declining';
    return 'stable';
  }

  /**
   * Get provider recommendation
   */
  private getProviderRecommendation(provider: ProviderMetrics): string {
    if (provider.uptime < 90) {
      return 'Monitor closely - low reliability';
    }
    if (provider.averageResponseTime > 30000) {
      // 30 seconds
      return 'Consider alternatives - slow response time';
    }
    if (provider.uptime > 99 && provider.averageResponseTime < 10000) {
      return 'Excellent performance - recommended';
    }
    return 'Good performance - suitable for production';
  }

  /**
   * Get video milestones (placeholder for detailed milestone tracking)
   */
  private getVideoMilestones(videoId: string): any[] {
    // This would return detailed processing milestones
    return [];
  }

  /**
   * Start periodic cleanup of old metrics
   */
  private startPeriodicCleanup(): void {
    setInterval(
      () => {
        this.cleanupOldMetrics();
      },
      60 * 60 * 1000
    ); // Every hour
  }

  /**
   * Clean up metrics older than retention period
   */
  private cleanupOldMetrics(): void {
    const retentionPeriod = 7 * 24 * 60 * 60 * 1000; // 7 days
    const cutoffTime = Date.now() - retentionPeriod;
    let cleanedCount = 0;

    for (const [videoId, metric] of this.metrics.entries()) {
      if (metric.startTime.getTime() < cutoffTime) {
        this.metrics.delete(videoId);
        cleanedCount++;
      }
    }

    if (cleanedCount > 0) {
      this.logger.info('Cleaned up old metrics', { cleanedCount });
    }
  }

  /**
   * Export metrics data for analysis
   */
  exportMetrics(): any {
    return {
      metrics: Array.from(this.metrics.entries()).map(([videoId, metric]) => ({
        videoId,
        ...metric,
      })),
      providerHealth: Array.from(this.providerHealth.entries()).map(
        ([provider, health]) => ({
          provider,
          ...health,
        })
      ),
      queueStats: this.queueStats,
      exportedAt: new Date(),
    };
  }
}

export default VideoMonitor;
