/**
 * Metrics Collection System
 *
 * Provides comprehensive metrics tracking for performance monitoring,
 * alerting, and system observability.
 */

import { EventEmitter } from 'events';
import { createLogger, Logger } from './logger';

export interface MetricLabels {
  [key: string]: string | number;
}

export interface CounterMetric {
  name: string;
  value: number;
  labels: MetricLabels;
  timestamp: number;
}

export interface GaugeMetric {
  name: string;
  value: number;
  labels: MetricLabels;
  timestamp: number;
}

export interface HistogramMetric {
  name: string;
  value: number;
  buckets: number[];
  labels: MetricLabels;
  timestamp: number;
}

export interface TimerMetric {
  name: string;
  duration: number;
  labels: MetricLabels;
  timestamp: number;
}

/**
 * Task lifecycle events for structured tracking
 */
export enum TaskLifecycleEvent {
  TASK_SUBMITTED = 'task_submitted',
  TASK_STARTED = 'task_started',
  TASK_COMPLETED = 'task_completed',
  TASK_FAILED = 'task_failed',
  TASK_TIMEOUT = 'task_timeout',
  PROVIDER_SELECTED = 'provider_selected',
  PROVIDER_FAILED = 'provider_failed',
  CIRCUIT_BREAKER_OPENED = 'circuit_breaker_opened',
  CIRCUIT_BREAKER_CLOSED = 'circuit_breaker_closed',
  RATE_LIMIT_HIT = 'rate_limit_hit',
}

export interface TaskLifecycleMetric {
  event: TaskLifecycleEvent;
  taskId: string;
  taskType: string;
  provider?: string;
  duration?: number;
  error?: string;
  labels: MetricLabels;
  timestamp: number;
}

/**
 * Main metrics collector
 */
export class MetricsCollector extends EventEmitter {
  private readonly logger: Logger;
  private readonly counters: Map<string, CounterMetric> = new Map();
  private readonly gauges: Map<string, GaugeMetric> = new Map();
  private readonly histograms: Map<string, HistogramMetric[]> = new Map();
  private readonly timers: Map<string, number> = new Map(); // Active timers
  private readonly lifecycleEvents: TaskLifecycleMetric[] = [];

  // System metrics tracking
  private readonly systemMetrics = {
    startTime: Date.now(),
    totalRequests: 0,
    successfulRequests: 0,
    failedRequests: 0,
    activeRequests: 0,
    averageResponseTime: 0,
    providerUsage: new Map<string, number>(),
    errorRates: new Map<string, number>(),
  };

  constructor() {
    super();
    this.logger = createLogger('MetricsCollector');

    // Cleanup old lifecycle events every hour
    setInterval(
      () => {
        this.cleanupOldEvents();
      },
      60 * 60 * 1000
    );

    // Log system metrics every 5 minutes
    setInterval(
      () => {
        this.logSystemMetrics();
      },
      5 * 60 * 1000
    );
  }

  /**
   * Increment a counter metric
   */
  incrementCounter(name: string, labels: MetricLabels = {}, value: number = 1): void {
    const key = this.getMetricKey(name, labels);
    const existing = this.counters.get(key);

    const metric: CounterMetric = {
      name,
      value: existing ? existing.value + value : value,
      labels,
      timestamp: Date.now(),
    };

    this.counters.set(key, metric);
    this.emit('counter', metric);
  }

  /**
   * Set a gauge metric value
   */
  setGauge(name: string, value: number, labels: MetricLabels = {}): void {
    const key = this.getMetricKey(name, labels);

    const metric: GaugeMetric = {
      name,
      value,
      labels,
      timestamp: Date.now(),
    };

    this.gauges.set(key, metric);
    this.emit('gauge', metric);
  }

  /**
   * Record histogram value
   */
  recordHistogram(
    name: string,
    value: number,
    buckets: number[] = [10, 50, 100, 500, 1000, 5000],
    labels: MetricLabels = {}
  ): void {
    const key = this.getMetricKey(name, labels);

    const metric: HistogramMetric = {
      name,
      value,
      buckets,
      labels,
      timestamp: Date.now(),
    };

    if (!this.histograms.has(key)) {
      this.histograms.set(key, []);
    }

    this.histograms.get(key)!.push(metric);
    this.emit('histogram', metric);
  }

  /**
   * Start a timer
   */
  startTimer(name: string, labels: MetricLabels = {}): string {
    const timerId = `${name}_${Date.now()}_${Math.random()}`;
    const key = this.getMetricKey(name, labels);

    this.timers.set(timerId, Date.now());

    return timerId;
  }

  /**
   * End a timer and record duration
   */
  endTimer(timerId: string, name: string, labels: MetricLabels = {}): number {
    const startTime = this.timers.get(timerId);
    if (!startTime) {
      this.logger.warn('Timer not found', { timerId, name });
      return 0;
    }

    const duration = Date.now() - startTime;
    this.timers.delete(timerId);

    const metric: TimerMetric = {
      name,
      duration,
      labels,
      timestamp: Date.now(),
    };

    this.recordHistogram(`${name}_duration`, duration, undefined, labels);
    this.emit('timer', metric);

    return duration;
  }

  /**
   * Record task lifecycle event
   */
  recordTaskLifecycle(
    event: TaskLifecycleEvent,
    taskId: string,
    taskType: string,
    provider?: string,
    duration?: number,
    error?: string,
    labels: MetricLabels = {}
  ): void {
    const metric: TaskLifecycleMetric = {
      event,
      taskId,
      taskType,
      provider,
      duration,
      error,
      labels,
      timestamp: Date.now(),
    };

    this.lifecycleEvents.push(metric);

    // Update system metrics
    this.updateSystemMetrics(event, provider, duration, error);

    // Emit structured event
    this.emit('lifecycle', metric);

    // Log important events
    this.logLifecycleEvent(metric);
  }

  /**
   * Update system-level metrics
   */
  private updateSystemMetrics(
    event: TaskLifecycleEvent,
    provider?: string,
    duration?: number,
    error?: string
  ): void {
    switch (event) {
      case TaskLifecycleEvent.TASK_SUBMITTED:
        this.systemMetrics.totalRequests++;
        this.systemMetrics.activeRequests++;
        break;

      case TaskLifecycleEvent.TASK_COMPLETED:
        this.systemMetrics.successfulRequests++;
        this.systemMetrics.activeRequests--;
        if (provider) {
          this.systemMetrics.providerUsage.set(
            provider,
            (this.systemMetrics.providerUsage.get(provider) || 0) + 1
          );
        }
        if (duration) {
          this.systemMetrics.averageResponseTime =
            (this.systemMetrics.averageResponseTime * (this.systemMetrics.successfulRequests - 1) +
              duration) /
            this.systemMetrics.successfulRequests;
        }
        break;

      case TaskLifecycleEvent.TASK_FAILED:
      case TaskLifecycleEvent.TASK_TIMEOUT:
        this.systemMetrics.failedRequests++;
        this.systemMetrics.activeRequests--;
        if (error) {
          this.systemMetrics.errorRates.set(
            error,
            (this.systemMetrics.errorRates.get(error) || 0) + 1
          );
        }
        break;
    }

    // Update gauge metrics
    this.setGauge('system_active_requests', this.systemMetrics.activeRequests);
    this.setGauge('system_total_requests', this.systemMetrics.totalRequests);
    this.setGauge(
      'system_success_rate',
      this.systemMetrics.totalRequests > 0
        ? this.systemMetrics.successfulRequests / this.systemMetrics.totalRequests
        : 0
    );
    this.setGauge('system_average_response_time', this.systemMetrics.averageResponseTime);
  }

  /**
   * Log lifecycle events for monitoring
   */
  private logLifecycleEvent(metric: TaskLifecycleMetric): void {
    const context = {
      event: metric.event,
      taskId: metric.taskId,
      taskType: metric.taskType,
      provider: metric.provider,
      duration: metric.duration,
      ...metric.labels,
    };

    switch (metric.event) {
      case TaskLifecycleEvent.TASK_SUBMITTED:
        this.logger.info('Task submitted for processing', context);
        break;

      case TaskLifecycleEvent.TASK_STARTED:
        this.logger.info('Task execution started', context);
        break;

      case TaskLifecycleEvent.TASK_COMPLETED:
        this.logger.info('Task completed successfully', context);
        break;

      case TaskLifecycleEvent.TASK_FAILED:
        this.logger.error('Task execution failed', { ...context, error: metric.error });
        break;

      case TaskLifecycleEvent.TASK_TIMEOUT:
        this.logger.warn('Task execution timed out', context);
        break;

      case TaskLifecycleEvent.PROVIDER_FAILED:
        this.logger.warn('Provider execution failed', { ...context, error: metric.error });
        break;

      case TaskLifecycleEvent.CIRCUIT_BREAKER_OPENED:
        this.logger.warn('Circuit breaker opened for provider', context);
        break;

      case TaskLifecycleEvent.RATE_LIMIT_HIT:
        this.logger.warn('Rate limit exceeded', context);
        break;
    }
  }

  /**
   * Get all current metrics
   */
  getAllMetrics(): {
    counters: CounterMetric[];
    gauges: GaugeMetric[];
    histograms: { [key: string]: HistogramMetric[] };
    lifecycleEvents: TaskLifecycleMetric[];
    systemMetrics: any;
  } {
    return {
      counters: Array.from(this.counters.values()),
      gauges: Array.from(this.gauges.values()),
      histograms: Object.fromEntries(this.histograms),
      lifecycleEvents: this.lifecycleEvents.slice(-1000), // Last 1000 events
      systemMetrics: {
        ...this.systemMetrics,
        providerUsage: Object.fromEntries(this.systemMetrics.providerUsage),
        errorRates: Object.fromEntries(this.systemMetrics.errorRates),
        uptime: Date.now() - this.systemMetrics.startTime,
      },
    };
  }

  /**
   * Generate Prometheus-format metrics
   */
  getPrometheusMetrics(): string {
    const lines: string[] = [];

    // Counters
    for (const counter of this.counters.values()) {
      const labelsStr = this.formatPrometheusLabels(counter.labels);
      lines.push(`${counter.name}_total${labelsStr} ${counter.value}`);
    }

    // Gauges
    for (const gauge of this.gauges.values()) {
      const labelsStr = this.formatPrometheusLabels(gauge.labels);
      lines.push(`${gauge.name}${labelsStr} ${gauge.value}`);
    }

    // Histograms (simplified)
    for (const [key, histograms] of this.histograms) {
      const values = histograms.map((h) => h.value).sort((a, b) => a - b);
      if (values.length > 0) {
        const p50 = values[Math.floor(values.length * 0.5)];
        const p95 = values[Math.floor(values.length * 0.95)];
        const p99 = values[Math.floor(values.length * 0.99)];

        const labels = histograms[0]?.labels || {};
        const labelsStr = this.formatPrometheusLabels(labels);

        lines.push(`${histograms[0].name}_p50${labelsStr} ${p50}`);
        lines.push(`${histograms[0].name}_p95${labelsStr} ${p95}`);
        lines.push(`${histograms[0].name}_p99${labelsStr} ${p99}`);
      }
    }

    return lines.join('\n');
  }

  /**
   * Helper methods
   */
  private getMetricKey(name: string, labels: MetricLabels): string {
    const sortedLabels = Object.keys(labels)
      .sort()
      .map((key) => `${key}=${labels[key]}`)
      .join(',');
    return `${name}{${sortedLabels}}`;
  }

  private formatPrometheusLabels(labels: MetricLabels): string {
    const labelPairs = Object.keys(labels)
      .map((key) => `${key}="${labels[key]}"`)
      .join(',');
    return labelPairs ? `{${labelPairs}}` : '';
  }

  private cleanupOldEvents(): void {
    const cutoff = Date.now() - 24 * 60 * 60 * 1000; // 24 hours
    const initialLength = this.lifecycleEvents.length;

    // Keep only recent events
    this.lifecycleEvents.splice(
      0,
      this.lifecycleEvents.findIndex((e) => e.timestamp > cutoff)
    );

    const cleaned = initialLength - this.lifecycleEvents.length;
    if (cleaned > 0) {
      this.logger.debug(`Cleaned up ${cleaned} old lifecycle events`);
    }
  }

  private logSystemMetrics(): void {
    this.logger.info('System metrics snapshot', {
      uptime: Date.now() - this.systemMetrics.startTime,
      totalRequests: this.systemMetrics.totalRequests,
      successRate:
        this.systemMetrics.totalRequests > 0
          ? this.systemMetrics.successfulRequests / this.systemMetrics.totalRequests
          : 0,
      activeRequests: this.systemMetrics.activeRequests,
      averageResponseTime: this.systemMetrics.averageResponseTime,
      topProviders: Array.from(this.systemMetrics.providerUsage.entries())
        .sort(([, a], [, b]) => b - a)
        .slice(0, 5),
      topErrors: Array.from(this.systemMetrics.errorRates.entries())
        .sort(([, a], [, b]) => b - a)
        .slice(0, 5),
    });
  }
}

// Global metrics collector instance
export const metricsCollector = new MetricsCollector();

/**
 * Convenience functions for common metrics operations
 */
export const metrics = {
  counter: (name: string, labels?: MetricLabels, value?: number) =>
    metricsCollector.incrementCounter(name, labels, value),

  gauge: (name: string, value: number, labels?: MetricLabels) =>
    metricsCollector.setGauge(name, value, labels),

  histogram: (name: string, value: number, buckets?: number[], labels?: MetricLabels) =>
    metricsCollector.recordHistogram(name, value, buckets, labels),

  timer: (name: string, labels?: MetricLabels) => metricsCollector.startTimer(name, labels),

  endTimer: (timerId: string, name: string, labels?: MetricLabels) =>
    metricsCollector.endTimer(timerId, name, labels),

  taskLifecycle: (
    event: TaskLifecycleEvent,
    taskId: string,
    taskType: string,
    provider?: string,
    duration?: number,
    error?: string,
    labels?: MetricLabels
  ) =>
    metricsCollector.recordTaskLifecycle(
      event,
      taskId,
      taskType,
      provider,
      duration,
      error,
      labels
    ),

  getAll: () => metricsCollector.getAllMetrics(),

  prometheus: () => metricsCollector.getPrometheusMetrics(),
};

export { MetricsCollector, TaskLifecycleEvent };
