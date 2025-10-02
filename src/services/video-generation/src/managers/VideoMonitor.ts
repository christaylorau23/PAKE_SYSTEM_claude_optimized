/**
 * PAKE System - Video Monitor
 * Single Responsibility: Monitoring and metrics collection for video generation
 */

import { VideoGenerationRequest, VideoStatus } from '../types';

export interface VideoMonitor {
  startMonitoring(videoId: string, request: VideoGenerationRequest): void;
  updateStatus(videoId: string, status: VideoStatus): void;
  recordMetric(videoId: string, metric: string, value: number): void;
  getMetrics(videoId: string): VideoMetrics;
  getAllMetrics(): Map<string, VideoMetrics>;
  stopMonitoring(videoId: string): void;
}

export interface VideoMetrics {
  videoId: string;
  status: VideoStatus;
  startTime: Date;
  endTime?: Date;
  duration?: number;
  attempts: number;
  errorCount: number;
  lastError?: string;
  customMetrics: Map<string, number>;
}

export class VideoMonitorImpl implements VideoMonitor {
  private metrics: Map<string, VideoMetrics> = new Map();
  private logger: any;

  constructor(logger: any) {
    this.logger = logger;
  }

  startMonitoring(videoId: string, request: VideoGenerationRequest): void {
    this.logger.info('Starting video monitoring', { videoId });

    this.metrics.set(videoId, {
      videoId,
      status: VideoStatus.PENDING,
      startTime: new Date(),
      attempts: 0,
      errorCount: 0,
      customMetrics: new Map()
    });
  }

  updateStatus(videoId: string, status: VideoStatus): void {
    const metrics = this.metrics.get(videoId);
    if (!metrics) {
      this.logger.warn('Attempted to update status for unknown video', { videoId });
      return;
    }

    metrics.status = status;

    if (status === VideoStatus.COMPLETED || status === VideoStatus.FAILED) {
      metrics.endTime = new Date();
      metrics.duration = metrics.endTime.getTime() - metrics.startTime.getTime();
    }

    this.logger.info('Video status updated', { videoId, status });
  }

  recordMetric(videoId: string, metric: string, value: number): void {
    const metrics = this.metrics.get(videoId);
    if (!metrics) {
      this.logger.warn('Attempted to record metric for unknown video', { videoId });
      return;
    }

    metrics.customMetrics.set(metric, value);
    this.logger.debug('Metric recorded', { videoId, metric, value });
  }

  getMetrics(videoId: string): VideoMetrics {
    const metrics = this.metrics.get(videoId);
    if (!metrics) {
      throw new Error(`No metrics found for video ${videoId}`);
    }
    return { ...metrics };
  }

  getAllMetrics(): Map<string, VideoMetrics> {
    return new Map(this.metrics);
  }

  stopMonitoring(videoId: string): void {
    const metrics = this.metrics.get(videoId);
    if (metrics) {
      metrics.endTime = new Date();
      metrics.duration = metrics.endTime.getTime() - metrics.startTime.getTime();
      this.logger.info('Stopped monitoring video', { videoId, duration: metrics.duration });
    }
  }

  incrementAttempts(videoId: string): void {
    const metrics = this.metrics.get(videoId);
    if (metrics) {
      metrics.attempts++;
    }
  }

  recordError(videoId: string, error: string): void {
    const metrics = this.metrics.get(videoId);
    if (metrics) {
      metrics.errorCount++;
      metrics.lastError = error;
    }
  }
}
