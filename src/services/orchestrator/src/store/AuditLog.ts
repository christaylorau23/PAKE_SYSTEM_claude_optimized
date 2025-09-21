/**
 * Persistent Audit Log - Comprehensive audit trail for agent operations
 *
 * Features:
 * - Structured logging of all provider interactions
 * - Routing decisions and policy applications
 * - Performance metrics and error tracking
 * - Compliance and forensic analysis support
 * - Configurable retention and archival
 * - Query interface for investigation
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import { AgentTask, AgentResult } from '../../../agent-runtime/src/types';
import { RoutingDecision } from '../router';

/**
 * Audit event types
 */
export enum AuditEventType {
  TASK_SUBMITTED = 'task_submitted',
  ROUTING_DECISION = 'routing_decision',
  PROVIDER_SELECTED = 'provider_selected',
  EXECUTION_START = 'execution_start',
  EXECUTION_SUCCESS = 'execution_success',
  EXECUTION_FAILURE = 'execution_failure',
  PROVIDER_HEALTH_CHECK = 'provider_health_check',
  CIRCUIT_BREAKER_OPENED = 'circuit_breaker_opened',
  CIRCUIT_BREAKER_CLOSED = 'circuit_breaker_closed',
  FAILOVER_TRIGGERED = 'failover_triggered',
  RATE_LIMIT_HIT = 'rate_limit_hit',
  COST_THRESHOLD_EXCEEDED = 'cost_threshold_exceeded',
  POLICY_APPLIED = 'policy_applied',
  SYSTEM_ERROR = 'system_error',
}

/**
 * Audit log entry structure
 */
export interface AuditLogEntry {
  /** Unique entry ID */
  id: string;
  /** Timestamp (ISO format) */
  timestamp: string;
  /** Event type */
  eventType: AuditEventType;
  /** Related task ID */
  taskId?: string;
  /** User context */
  userId?: string;
  /** Request correlation ID */
  correlationId?: string;
  /** Provider involved */
  provider?: string;
  /** Event severity */
  severity: 'info' | 'warn' | 'error' | 'critical';
  /** Human-readable message */
  message: string;
  /** Structured event data */
  data: Record<string, any>;
  /** Performance metrics */
  metrics?: AuditMetrics;
  /** Error information */
  error?: AuditError;
  /** Tags for categorization */
  tags: string[];
  /** Event context */
  context: AuditContext;
}

/**
 * Performance metrics for audit entries
 */
export interface AuditMetrics {
  /** Execution duration in milliseconds */
  duration?: number;
  /** Token usage */
  tokensUsed?: number;
  /** Memory usage in MB */
  memoryUsage?: number;
  /** Cost incurred */
  cost?: number;
  /** Response size in bytes */
  responseSize?: number;
  /** Queue wait time */
  queueTime?: number;
}

/**
 * Error information for audit entries
 */
export interface AuditError {
  /** Error code */
  code: string;
  /** Error message */
  message: string;
  /** Stack trace (if available) */
  stack?: string;
  /** Error category */
  category:
    | 'validation'
    | 'network'
    | 'authentication'
    | 'rate_limit'
    | 'internal'
    | 'provider'
    | 'timeout';
  /** Retry attempts */
  retryCount?: number;
  /** Recovery action taken */
  recoveryAction?: string;
}

/**
 * Context information for audit entries
 */
export interface AuditContext {
  /** Environment (dev, staging, prod) */
  environment: string;
  /** Service version */
  version: string;
  /** Instance ID */
  instanceId: string;
  /** Client IP address */
  clientIp?: string;
  /** User agent */
  userAgent?: string;
  /** Request headers */
  headers?: Record<string, string>;
  /** Feature flags active */
  featureFlags?: Record<string, any>;
  /** System resource usage */
  systemMetrics?: {
    cpuUsage: number;
    memoryUsage: number;
    diskUsage: number;
  };
}

/**
 * Audit log configuration
 */
export interface AuditLogConfig {
  /** Log directory path */
  logDirectory: string;
  /** Maximum log file size in MB */
  maxFileSize: number;
  /** Number of log files to retain */
  maxFiles: number;
  /** Retention period in days */
  retentionDays: number;
  /** Enable compression for archived logs */
  enableCompression: boolean;
  /** Write to console in addition to file */
  consoleOutput: boolean;
  /** Log level filtering */
  logLevel: 'info' | 'warn' | 'error';
  /** Enable sensitive data redaction */
  redactSensitiveData: boolean;
  /** Batch size for bulk operations */
  batchSize: number;
  /** Flush interval in milliseconds */
  flushInterval: number;
}

/**
 * Query interface for audit logs
 */
export interface AuditLogQuery {
  /** Date range filter */
  dateRange?: {
    start: string;
    end: string;
  };
  /** Event type filter */
  eventTypes?: AuditEventType[];
  /** Provider filter */
  providers?: string[];
  /** User ID filter */
  userIds?: string[];
  /** Task ID filter */
  taskIds?: string[];
  /** Correlation ID filter */
  correlationIds?: string[];
  /** Severity filter */
  severities?: ('info' | 'warn' | 'error' | 'critical')[];
  /** Tag filter */
  tags?: string[];
  /** Text search in messages */
  searchText?: string;
  /** Pagination */
  offset?: number;
  /** Results per page */
  limit?: number;
  /** Sort order */
  sortBy?: 'timestamp' | 'eventType' | 'severity' | 'duration';
  /** Sort direction */
  sortOrder?: 'asc' | 'desc';
}

/**
 * Audit log statistics
 */
export interface AuditLogStats {
  /** Total entries */
  totalEntries: number;
  /** Entries by event type */
  entriesByType: Record<AuditEventType, number>;
  /** Entries by severity */
  entriesBySeverity: Record<string, number>;
  /** Entries by provider */
  entriesByProvider: Record<string, number>;
  /** Average metrics */
  averageMetrics: {
    duration: number;
    tokensUsed: number;
    cost: number;
  };
  /** Error rate */
  errorRate: number;
  /** Top errors */
  topErrors: Array<{ error: string; count: number }>;
  /** Time range covered */
  timeRange: {
    earliest: string;
    latest: string;
  };
}

/**
 * Main audit logging system
 */
export class AuditLog {
  private readonly config: AuditLogConfig;
  private writeQueue: AuditLogEntry[] = [];
  private flushTimer?: NodeJS.Timeout;
  private currentLogFile?: string;
  private fileHandle?: fs.FileHandle;
  private entryCounter = 0;

  constructor(config: Partial<AuditLogConfig> = {}) {
    this.config = {
      logDirectory: config.logDirectory || './logs/audit',
      maxFileSize: config.maxFileSize || 100, // 100MB
      maxFiles: config.maxFiles || 30,
      retentionDays: config.retentionDays || 90,
      enableCompression: config.enableCompression ?? true,
      consoleOutput: config.consoleOutput ?? false,
      logLevel: config.logLevel || 'info',
      redactSensitiveData: config.redactSensitiveData ?? true,
      batchSize: config.batchSize || 100,
      flushInterval: config.flushInterval || 5000,
      ...config,
    };

    this.initializeLogging();
    this.startPeriodicFlush();
    this.startLogRotation();
  }

  /**
   * Log task submission
   */
  async logTaskSubmission(task: AgentTask, context: AuditContext): Promise<void> {
    await this.writeEntry({
      id: this.generateEntryId(),
      timestamp: new Date().toISOString(),
      eventType: AuditEventType.TASK_SUBMITTED,
      taskId: task.id,
      userId: task.metadata.userId,
      correlationId: task.metadata.correlationId,
      severity: 'info',
      message: `Task ${task.id} submitted for processing`,
      data: {
        taskType: task.type,
        inputSize: this.calculateInputSize(task.input),
        priority: task.config.priority,
        timeout: task.config.timeout,
        source: task.metadata.source,
      },
      tags: ['task', 'submission', task.type],
      context: this.redactContext(context),
    });
  }

  /**
   * Log routing decision
   */
  async logRoutingDecision(
    decision: RoutingDecision,
    task: AgentTask,
    context: AuditContext
  ): Promise<void> {
    await this.writeEntry({
      id: this.generateEntryId(),
      timestamp: new Date().toISOString(),
      eventType: AuditEventType.ROUTING_DECISION,
      taskId: task.id,
      userId: task.metadata.userId,
      correlationId: task.metadata.correlationId,
      provider: decision.selectedProvider,
      severity: 'info',
      message: `Provider ${decision.selectedProvider} selected for task ${task.id}`,
      data: {
        selectedProvider: decision.selectedProvider,
        alternatives: decision.alternatives,
        reason: decision.reason,
        appliedPolicies: decision.appliedPolicies,
        estimatedCost: decision.estimatedCost,
        estimatedResponseTime: decision.estimatedResponseTime,
      },
      metrics: {
        cost: decision.estimatedCost,
        duration: decision.estimatedResponseTime,
      },
      tags: ['routing', 'decision', decision.selectedProvider],
      context: this.redactContext(context),
    });
  }

  /**
   * Log execution start
   */
  async logExecutionStart(task: AgentTask, provider: string, context: AuditContext): Promise<void> {
    await this.writeEntry({
      id: this.generateEntryId(),
      timestamp: new Date().toISOString(),
      eventType: AuditEventType.EXECUTION_START,
      taskId: task.id,
      userId: task.metadata.userId,
      correlationId: task.metadata.correlationId,
      provider,
      severity: 'info',
      message: `Execution started for task ${task.id} using ${provider}`,
      data: {
        provider,
        taskType: task.type,
        inputSize: this.calculateInputSize(task.input),
      },
      tags: ['execution', 'start', provider],
      context: this.redactContext(context),
    });
  }

  /**
   * Log execution success
   */
  async logExecutionSuccess(
    task: AgentTask,
    result: AgentResult,
    provider: string,
    context: AuditContext
  ): Promise<void> {
    await this.writeEntry({
      id: this.generateEntryId(),
      timestamp: new Date().toISOString(),
      eventType: AuditEventType.EXECUTION_SUCCESS,
      taskId: task.id,
      userId: task.metadata.userId,
      correlationId: task.metadata.correlationId,
      provider,
      severity: 'info',
      message: `Task ${task.id} executed successfully by ${provider}`,
      data: {
        provider,
        status: result.status,
        outputSize: this.calculateOutputSize(result.output),
        confidence: result.metadata.confidence,
      },
      metrics: {
        duration: result.metadata.duration,
        tokensUsed: result.metadata.usage?.tokens,
        memoryUsage: result.metadata.usage?.memoryMb,
        cost: this.estimateCost(result.metadata.usage?.tokens || 0, provider),
        responseSize: this.calculateOutputSize(result.output),
      },
      tags: ['execution', 'success', provider, task.type],
      context: this.redactContext(context),
    });
  }

  /**
   * Log execution failure
   */
  async logExecutionFailure(
    task: AgentTask,
    error: Error,
    provider: string,
    context: AuditContext,
    retryCount = 0
  ): Promise<void> {
    await this.writeEntry({
      id: this.generateEntryId(),
      timestamp: new Date().toISOString(),
      eventType: AuditEventType.EXECUTION_FAILURE,
      taskId: task.id,
      userId: task.metadata.userId,
      correlationId: task.metadata.correlationId,
      provider,
      severity: 'error',
      message: `Task ${task.id} failed during execution by ${provider}`,
      data: {
        provider,
        taskType: task.type,
      },
      error: {
        code: this.extractErrorCode(error),
        message: error.message,
        stack: error.stack,
        category: this.categorizeError(error),
        retryCount,
        recoveryAction: retryCount > 0 ? 'retry_attempted' : 'none',
      },
      tags: ['execution', 'failure', 'error', provider],
      context: this.redactContext(context),
    });
  }

  /**
   * Log provider health check
   */
  async logHealthCheck(provider: string, isHealthy: boolean, context: AuditContext): Promise<void> {
    await this.writeEntry({
      id: this.generateEntryId(),
      timestamp: new Date().toISOString(),
      eventType: AuditEventType.PROVIDER_HEALTH_CHECK,
      provider,
      severity: isHealthy ? 'info' : 'warn',
      message: `Health check for ${provider}: ${isHealthy ? 'healthy' : 'unhealthy'}`,
      data: {
        provider,
        isHealthy,
        checkType: 'periodic',
      },
      tags: ['health-check', provider, isHealthy ? 'healthy' : 'unhealthy'],
      context: this.redactContext(context),
    });
  }

  /**
   * Log circuit breaker events
   */
  async logCircuitBreakerEvent(
    provider: string,
    event: 'opened' | 'closed',
    reason: string,
    context: AuditContext
  ): Promise<void> {
    await this.writeEntry({
      id: this.generateEntryId(),
      timestamp: new Date().toISOString(),
      eventType:
        event === 'opened'
          ? AuditEventType.CIRCUIT_BREAKER_OPENED
          : AuditEventType.CIRCUIT_BREAKER_CLOSED,
      provider,
      severity: event === 'opened' ? 'warn' : 'info',
      message: `Circuit breaker ${event} for ${provider}: ${reason}`,
      data: {
        provider,
        event,
        reason,
      },
      tags: ['circuit-breaker', event, provider],
      context: this.redactContext(context),
    });
  }

  /**
   * Log system errors
   */
  async logSystemError(
    error: Error,
    context: AuditContext,
    additionalData?: Record<string, any>
  ): Promise<void> {
    await this.writeEntry({
      id: this.generateEntryId(),
      timestamp: new Date().toISOString(),
      eventType: AuditEventType.SYSTEM_ERROR,
      severity: 'critical',
      message: `System error: ${error.message}`,
      data: {
        ...additionalData,
      },
      error: {
        code: this.extractErrorCode(error),
        message: error.message,
        stack: error.stack,
        category: 'internal',
      },
      tags: ['system', 'error', 'critical'],
      context: this.redactContext(context),
    });
  }

  /**
   * Query audit logs
   */
  async queryLogs(query: AuditLogQuery): Promise<AuditLogEntry[]> {
    const logFiles = await this.getLogFiles();
    const results: AuditLogEntry[] = [];

    for (const logFile of logFiles) {
      const entries = await this.readLogFile(logFile);
      const filteredEntries = this.filterEntries(entries, query);
      results.push(...filteredEntries);
    }

    // Sort results
    const sortBy = query.sortBy || 'timestamp';
    const sortOrder = query.sortOrder || 'desc';

    results.sort((a, b) => {
      let aValue: any;
      let bValue: any;

      switch (sortBy) {
        case 'timestamp':
          aValue = new Date(a.timestamp).getTime();
          bValue = new Date(b.timestamp).getTime();
          break;
        case 'duration':
          aValue = a.metrics?.duration || 0;
          bValue = b.metrics?.duration || 0;
          break;
        default:
          aValue = a[sortBy as keyof AuditLogEntry];
          bValue = b[sortBy as keyof AuditLogEntry];
      }

      if (sortOrder === 'asc') {
        return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
      } else {
        return aValue > bValue ? -1 : aValue < bValue ? 1 : 0;
      }
    });

    // Apply pagination
    const offset = query.offset || 0;
    const limit = query.limit || 100;

    return results.slice(offset, offset + limit);
  }

  /**
   * Get audit log statistics
   */
  async getStats(timeRange?: { start: string; end: string }): Promise<AuditLogStats> {
    const query: AuditLogQuery = {
      dateRange: timeRange,
      limit: 10000, // Large limit to get comprehensive stats
    };

    const entries = await this.queryLogs(query);

    const stats: AuditLogStats = {
      totalEntries: entries.length,
      entriesByType: {} as Record<AuditEventType, number>,
      entriesBySeverity: {},
      entriesByProvider: {},
      averageMetrics: {
        duration: 0,
        tokensUsed: 0,
        cost: 0,
      },
      errorRate: 0,
      topErrors: [],
      timeRange: {
        earliest: '',
        latest: '',
      },
    };

    if (entries.length === 0) {
      return stats;
    }

    // Calculate statistics
    let totalDuration = 0;
    let totalTokens = 0;
    let totalCost = 0;
    let errorCount = 0;
    const errorCounts = new Map<string, number>();

    for (const entry of entries) {
      // Count by type
      stats.entriesByType[entry.eventType] = (stats.entriesByType[entry.eventType] || 0) + 1;

      // Count by severity
      stats.entriesBySeverity[entry.severity] = (stats.entriesBySeverity[entry.severity] || 0) + 1;

      // Count by provider
      if (entry.provider) {
        stats.entriesByProvider[entry.provider] =
          (stats.entriesByProvider[entry.provider] || 0) + 1;
      }

      // Accumulate metrics
      if (entry.metrics) {
        totalDuration += entry.metrics.duration || 0;
        totalTokens += entry.metrics.tokensUsed || 0;
        totalCost += entry.metrics.cost || 0;
      }

      // Count errors
      if (entry.severity === 'error' || entry.severity === 'critical') {
        errorCount++;
        if (entry.error) {
          const errorKey = `${entry.error.code}: ${entry.error.message}`;
          errorCounts.set(errorKey, (errorCounts.get(errorKey) || 0) + 1);
        }
      }
    }

    // Calculate averages
    stats.averageMetrics.duration = totalDuration / entries.length;
    stats.averageMetrics.tokensUsed = totalTokens / entries.length;
    stats.averageMetrics.cost = totalCost / entries.length;
    stats.errorRate = errorCount / entries.length;

    // Top errors
    stats.topErrors = Array.from(errorCounts.entries())
      .map(([error, count]) => ({ error, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);

    // Time range
    const timestamps = entries.map((e) => e.timestamp).sort();
    stats.timeRange.earliest = timestamps[0];
    stats.timeRange.latest = timestamps[timestamps.length - 1];

    return stats;
  }

  /**
   * Initialize logging system
   */
  private async initializeLogging(): Promise<void> {
    try {
      await fs.mkdir(this.config.logDirectory, { recursive: true });
      console.log(`Audit logging initialized: ${this.config.logDirectory}`);
    } catch (error) {
      console.error('Failed to initialize audit logging:', error);
      throw error;
    }
  }

  /**
   * Write entry to audit log
   */
  private async writeEntry(entry: AuditLogEntry): Promise<void> {
    // Filter by log level
    const severityLevels = ['info', 'warn', 'error', 'critical'];
    const minLevelIndex = severityLevels.indexOf(this.config.logLevel);
    const entryLevelIndex = severityLevels.indexOf(entry.severity);

    if (entryLevelIndex < minLevelIndex) {
      return; // Skip entries below log level
    }

    this.writeQueue.push(entry);

    // Console output if enabled
    if (this.config.consoleOutput) {
      console.log(
        `[AUDIT] ${entry.timestamp} ${entry.eventType} ${entry.severity}: ${entry.message}`
      );
    }

    // Flush if queue is full
    if (this.writeQueue.length >= this.config.batchSize) {
      await this.flush();
    }
  }

  /**
   * Flush write queue to disk
   */
  private async flush(): Promise<void> {
    if (this.writeQueue.length === 0) return;

    try {
      await this.ensureLogFile();

      const entries = this.writeQueue.splice(0); // Clear queue
      const logLines = entries.map((entry) => JSON.stringify(entry)).join('\n') + '\n';

      if (this.fileHandle) {
        await this.fileHandle.write(logLines);
        await this.fileHandle.sync(); // Force write to disk
      }
    } catch (error) {
      console.error('Failed to flush audit log:', error);
      // Put entries back in queue for retry
      this.writeQueue.unshift(...entries);
    }
  }

  /**
   * Ensure current log file is ready
   */
  private async ensureLogFile(): Promise<void> {
    const now = new Date();
    const dateStr = now.toISOString().split('T')[0]; // YYYY-MM-DD
    const expectedFile = path.join(this.config.logDirectory, `audit-${dateStr}.jsonl`);

    if (this.currentLogFile !== expectedFile) {
      // Close current file if open
      if (this.fileHandle) {
        await this.fileHandle.close();
      }

      // Open new file
      this.currentLogFile = expectedFile;
      this.fileHandle = await fs.open(expectedFile, 'a');
    }

    // Check file size for rotation
    if (this.fileHandle) {
      const stats = await this.fileHandle.stat();
      const sizeInMB = stats.size / (1024 * 1024);

      if (sizeInMB > this.config.maxFileSize) {
        await this.rotateLogFile();
      }
    }
  }

  /**
   * Rotate log file when it gets too large
   */
  private async rotateLogFile(): Promise<void> {
    if (!this.currentLogFile || !this.fileHandle) return;

    await this.fileHandle.close();

    const now = new Date();
    const timestamp = now.toISOString().replace(/[:.]/g, '-');
    const rotatedFile = this.currentLogFile.replace('.jsonl', `-${timestamp}.jsonl`);

    await fs.rename(this.currentLogFile, rotatedFile);

    // Compress if enabled
    if (this.config.enableCompression) {
      // Note: In a full implementation, you'd use a compression library here
      console.log(`Log file rotated: ${rotatedFile} (compression placeholder)`);
    }

    // Reopen current file
    this.fileHandle = await fs.open(this.currentLogFile, 'a');
  }

  /**
   * Start periodic flush
   */
  private startPeriodicFlush(): void {
    this.flushTimer = setInterval(async () => {
      await this.flush();
    }, this.config.flushInterval);
  }

  /**
   * Start log rotation and cleanup
   */
  private startLogRotation(): void {
    setInterval(
      async () => {
        await this.cleanupOldLogs();
      },
      24 * 60 * 60 * 1000
    ); // Run daily
  }

  /**
   * Clean up old log files
   */
  private async cleanupOldLogs(): Promise<void> {
    try {
      const files = await fs.readdir(this.config.logDirectory);
      const cutoffDate = new Date(Date.now() - this.config.retentionDays * 24 * 60 * 60 * 1000);

      for (const file of files) {
        if (!file.startsWith('audit-')) continue;

        const filePath = path.join(this.config.logDirectory, file);
        const stats = await fs.stat(filePath);

        if (stats.mtime < cutoffDate) {
          await fs.unlink(filePath);
          console.log(`Deleted old audit log: ${file}`);
        }
      }
    } catch (error) {
      console.error('Failed to cleanup old logs:', error);
    }
  }

  /**
   * Generate unique entry ID
   */
  private generateEntryId(): string {
    return `audit_${Date.now()}_${++this.entryCounter}`;
  }

  /**
   * Calculate input size in bytes
   */
  private calculateInputSize(input: any): number {
    return JSON.stringify(input).length;
  }

  /**
   * Calculate output size in bytes
   */
  private calculateOutputSize(output: any): number {
    return JSON.stringify(output).length;
  }

  /**
   * Estimate cost based on token usage and provider
   */
  private estimateCost(tokens: number, provider: string): number {
    switch (provider) {
      case 'claude':
      case 'ClaudeProvider':
        return tokens * 0.00001; // Rough estimate
      default:
        return 0;
    }
  }

  /**
   * Extract error code from error
   */
  private extractErrorCode(error: Error): string {
    // Check if it's an AgentExecutionError with a code property
    if ('code' in error) {
      return (error as any).code;
    }

    return error.name || 'UNKNOWN_ERROR';
  }

  /**
   * Categorize error for analysis
   */
  private categorizeError(error: Error): AuditError['category'] {
    const message = error.message.toLowerCase();

    if (message.includes('timeout')) return 'timeout';
    if (message.includes('auth') || message.includes('401') || message.includes('403'))
      return 'authentication';
    if (message.includes('rate') || message.includes('quota')) return 'rate_limit';
    if (message.includes('network') || message.includes('connection')) return 'network';
    if (message.includes('validation') || message.includes('invalid')) return 'validation';

    return 'internal';
  }

  /**
   * Redact sensitive data from context
   */
  private redactContext(context: AuditContext): AuditContext {
    if (!this.config.redactSensitiveData) {
      return context;
    }

    const redacted = { ...context };

    // Redact sensitive headers
    if (redacted.headers) {
      const sensitiveHeaders = ['authorization', 'x-api-key', 'cookie', 'x-auth-token'];
      redacted.headers = { ...redacted.headers };

      for (const header of sensitiveHeaders) {
        if (redacted.headers[header]) {
          redacted.headers[header] = '[REDACTED]';
        }
      }
    }

    return redacted;
  }

  /**
   * Get available log files
   */
  private async getLogFiles(): Promise<string[]> {
    const files = await fs.readdir(this.config.logDirectory);
    return files
      .filter((file) => file.startsWith('audit-') && file.endsWith('.jsonl'))
      .map((file) => path.join(this.config.logDirectory, file))
      .sort();
  }

  /**
   * Read entries from log file
   */
  private async readLogFile(filePath: string): Promise<AuditLogEntry[]> {
    const content = await fs.readFile(filePath, 'utf8');
    const lines = content
      .trim()
      .split('\n')
      .filter((line) => line.trim());

    const entries: AuditLogEntry[] = [];
    for (const line of lines) {
      try {
        entries.push(JSON.parse(line));
      } catch (error) {
        console.warn(`Failed to parse audit log line: ${line}`);
      }
    }

    return entries;
  }

  /**
   * Filter entries based on query
   */
  private filterEntries(entries: AuditLogEntry[], query: AuditLogQuery): AuditLogEntry[] {
    return entries.filter((entry) => {
      // Date range filter
      if (query.dateRange) {
        const entryTime = new Date(entry.timestamp).getTime();
        const startTime = new Date(query.dateRange.start).getTime();
        const endTime = new Date(query.dateRange.end).getTime();

        if (entryTime < startTime || entryTime > endTime) {
          return false;
        }
      }

      // Event type filter
      if (query.eventTypes && !query.eventTypes.includes(entry.eventType)) {
        return false;
      }

      // Provider filter
      if (query.providers && entry.provider && !query.providers.includes(entry.provider)) {
        return false;
      }

      // User ID filter
      if (query.userIds && entry.userId && !query.userIds.includes(entry.userId)) {
        return false;
      }

      // Task ID filter
      if (query.taskIds && entry.taskId && !query.taskIds.includes(entry.taskId)) {
        return false;
      }

      // Correlation ID filter
      if (
        query.correlationIds &&
        entry.correlationId &&
        !query.correlationIds.includes(entry.correlationId)
      ) {
        return false;
      }

      // Severity filter
      if (query.severities && !query.severities.includes(entry.severity)) {
        return false;
      }

      // Tags filter
      if (query.tags && !query.tags.some((tag) => entry.tags.includes(tag))) {
        return false;
      }

      // Text search
      if (query.searchText) {
        const searchLower = query.searchText.toLowerCase();
        const searchableText = `${entry.message} ${JSON.stringify(entry.data)}`.toLowerCase();

        if (!searchableText.includes(searchLower)) {
          return false;
        }
      }

      return true;
    });
  }

  /**
   * Cleanup resources
   */
  async dispose(): Promise<void> {
    // Clear timers
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
    }

    // Flush remaining entries
    await this.flush();

    // Close file handle
    if (this.fileHandle) {
      await this.fileHandle.close();
    }
  }
}

/**
 * Global audit log instance
 */
let globalAuditLog: AuditLog | null = null;

/**
 * Get or create global audit log instance
 */
export function getAuditLog(config?: Partial<AuditLogConfig>): AuditLog {
  if (!globalAuditLog) {
    globalAuditLog = new AuditLog(config);
  }
  return globalAuditLog;
}

/**
 * Initialize global audit log
 */
export function initializeAuditLog(config?: Partial<AuditLogConfig>): AuditLog {
  globalAuditLog = new AuditLog(config);
  return globalAuditLog;
}
