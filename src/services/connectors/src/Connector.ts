/**
 * PAKE System - Unified Connector Interface
 *
 * MCP-like connector interface providing uniform access to external data sources
 * including web scraping, databases, and message queues.
 */

import { EventEmitter } from 'events';
import { createLogger, Logger } from '../../orchestrator/src/utils/logger';
import { metrics } from '../../orchestrator/src/utils/metrics';

export interface ConnectorRequest {
  // Request identification
  id: string;
  type: ConnectorRequestType;

  // Target specification
  target: string; // URL, table name, queue name, etc.

  // Parameters
  parameters: Record<string, any>;

  // Configuration
  config: ConnectorConfig;

  // Metadata
  metadata: {
    requestedAt: string;
    correlationId?: string;
    priority?: 'low' | 'normal' | 'high' | 'urgent';
    timeout?: number;
    retries?: number;
  };
}

export enum ConnectorRequestType {
  // Web scraping operations
  SCRAPE_URL = 'scrape_url',
  SCRAPE_SITEMAP = 'scrape_sitemap',
  FETCH_RSS = 'fetch_rss',

  // Database operations
  SELECT = 'select',
  INSERT = 'insert',
  UPDATE = 'update',
  DELETE = 'delete',
  QUERY = 'query',

  // Queue operations
  PUBLISH = 'publish',
  SUBSCRIBE = 'subscribe',
  CONSUME = 'consume',
  ACKNOWLEDGE = 'acknowledge',

  // Generic operations
  FETCH = 'fetch',
  STREAM = 'stream',
  BATCH = 'batch',
}

export interface ConnectorConfig {
  // Connection settings
  timeout: number;
  maxRetries: number;
  retryDelay: number;

  // Authentication
  credentials?: {
    type: 'basic' | 'bearer' | 'api_key' | 'oauth' | 'custom';
    data: Record<string, string>;
  };

  // Rate limiting
  rateLimit?: {
    requestsPerSecond: number;
    burstSize: number;
    backoffMultiplier: number;
  };

  // Caching
  cache?: {
    enabled: boolean;
    ttlSeconds: number;
    maxSize: number;
  };

  // Custom headers/options
  headers?: Record<string, string>;
  options?: Record<string, any>;
}

export interface ResponseEnvelope<T = any> {
  // Response identification
  requestId: string;
  correlationId?: string;

  // Status
  success: boolean;
  status: ResponseStatus;
  statusCode?: number;

  // Data
  data: T;

  // Metadata
  metadata: {
    executionTime: number;
    timestamp: string;
    source: string;
    connector: string;

    // Data characteristics
    dataSize?: number;
    recordCount?: number;
    hasMore?: boolean;
    nextCursor?: string;

    // Quality indicators
    freshness?: number; // seconds since last update
    confidence?: number; // 0-1 confidence score
    completeness?: number; // 0-1 completeness score
  };

  // Error information
  error?: {
    code: string;
    message: string;
    details?: Record<string, any>;
    retryable: boolean;
    retryAfter?: number;
  };

  // Warnings and notices
  warnings?: string[];
  notices?: string[];
}

export enum ResponseStatus {
  SUCCESS = 'success',
  PARTIAL_SUCCESS = 'partial_success',
  ERROR = 'error',
  TIMEOUT = 'timeout',
  RATE_LIMITED = 'rate_limited',
  NOT_FOUND = 'not_found',
  UNAUTHORIZED = 'unauthorized',
  FORBIDDEN = 'forbidden',
  INVALID_REQUEST = 'invalid_request',
  SERVICE_UNAVAILABLE = 'service_unavailable',
}

export interface ConnectorMetrics {
  // Request statistics
  totalRequests: number;
  successfulRequests: number;
  failedRequests: number;

  // Performance metrics
  averageResponseTime: number;
  p95ResponseTime: number;
  p99ResponseTime: number;

  // Error analysis
  errorsByType: Map<string, number>;
  errorRate: number;

  // Rate limiting
  rateLimitHits: number;
  throttleEvents: number;

  // Data quality
  averageFreshness: number;
  averageConfidence: number;
  averageCompleteness: number;

  // Resource usage
  cacheHitRate: number;
  bandwidthUsed: number;
  connectionPoolSize: number;
}

/**
 * Base connector interface that all connectors must implement
 */
export abstract class Connector extends EventEmitter {
  protected readonly logger: Logger;
  protected readonly metrics: ConnectorMetrics;
  protected readonly config: ConnectorConfig;

  // Internal state
  protected isConnected = false;
  protected connectionHealth = 1.0; // 0-1 health score
  protected lastHealthCheck = 0;

  constructor(
    protected readonly name: string,
    config: Partial<ConnectorConfig> = {}
  ) {
    super();

    this.logger = createLogger(`Connector:${name}`);
    this.config = this.mergeWithDefaults(config);
    this.metrics = this.initializeMetrics();

    // Emit events for monitoring
    this.on('request', this.trackRequest.bind(this));
    this.on('response', this.trackResponse.bind(this));
    this.on('error', this.trackError.bind(this));
  }

  /**
   * Primary interface method - fetch data using the connector
   */
  abstract fetch<T = any>(
    request: ConnectorRequest
  ): Promise<ResponseEnvelope<T>>;

  /**
   * Initialize connection to the data source
   */
  abstract connect(): Promise<void>;

  /**
   * Close connection and cleanup resources
   */
  abstract disconnect(): Promise<void>;

  /**
   * Check health of the connector and its connection
   */
  abstract healthCheck(): Promise<boolean>;

  /**
   * Validate request format and parameters
   */
  protected validateRequest(request: ConnectorRequest): void {
    if (!request.id) {
      throw new Error('Request ID is required');
    }

    if (!request.type) {
      throw new Error('Request type is required');
    }

    if (!request.target) {
      throw new Error('Request target is required');
    }

    // Validate timeout
    const timeout = request.metadata.timeout || this.config.timeout;
    if (timeout < 100 || timeout > 300000) {
      throw new Error('Timeout must be between 100ms and 5 minutes');
    }
  }

  /**
   * Create standardized response envelope
   */
  protected createResponse<T>(
    request: ConnectorRequest,
    data: T,
    status: ResponseStatus = ResponseStatus.SUCCESS,
    executionTime: number,
    additionalMetadata: Record<string, any> = {}
  ): ResponseEnvelope<T> {
    const success =
      status === ResponseStatus.SUCCESS ||
      status === ResponseStatus.PARTIAL_SUCCESS;

    return {
      requestId: request.id,
      correlationId: request.metadata.correlationId,
      success,
      status,
      data,
      metadata: {
        executionTime,
        timestamp: new Date().toISOString(),
        source: request.target,
        connector: this.name,
        dataSize: this.calculateDataSize(data),
        ...additionalMetadata,
      },
    };
  }

  /**
   * Create error response envelope
   */
  protected createErrorResponse<T = null>(
    request: ConnectorRequest,
    error: Error,
    status: ResponseStatus = ResponseStatus.ERROR,
    executionTime: number,
    retryable: boolean = false
  ): ResponseEnvelope<T> {
    return {
      requestId: request.id,
      correlationId: request.metadata.correlationId,
      success: false,
      status,
      data: null as T,
      metadata: {
        executionTime,
        timestamp: new Date().toISOString(),
        source: request.target,
        connector: this.name,
      },
      error: {
        code: error.name || 'UNKNOWN_ERROR',
        message: error.message,
        details: { stack: error.stack },
        retryable,
      },
    };
  }

  /**
   * Execute request with timeout and retry logic
   */
  protected async executeWithRetry<T>(
    request: ConnectorRequest,
    executor: () => Promise<ResponseEnvelope<T>>
  ): Promise<ResponseEnvelope<T>> {
    const maxRetries = request.metadata.retries ?? this.config.maxRetries;
    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        this.emit('request', { request, attempt });

        const response = await this.withTimeout(
          executor(),
          request.metadata.timeout ?? this.config.timeout
        );

        this.emit('response', { request, response, attempt });
        return response;
      } catch (error) {
        lastError = error as Error;
        this.emit('error', { request, error, attempt });

        // Don't retry on certain errors
        if (
          this.isNonRetryableError(error as Error) ||
          attempt === maxRetries
        ) {
          break;
        }

        // Wait before retrying with exponential backoff
        const delay = this.config.retryDelay * Math.pow(2, attempt);
        await this.sleep(delay);
      }
    }

    // All retries exhausted
    const executionTime = Date.now(); // Approximate
    return this.createErrorResponse(
      request,
      lastError || new Error('Maximum retries exceeded'),
      ResponseStatus.ERROR,
      executionTime,
      false
    );
  }

  /**
   * Execute operation with timeout
   */
  protected async withTimeout<T>(
    promise: Promise<T>,
    timeoutMs: number
  ): Promise<T> {
    const timeoutPromise = new Promise<never>((_, reject) => {
      setTimeout(() => reject(new Error('Operation timeout')), timeoutMs);
    });

    return Promise.race([promise, timeoutPromise]);
  }

  /**
   * Check if error should not be retried
   */
  protected isNonRetryableError(error: Error): boolean {
    const nonRetryablePatterns = [
      /authentication/i,
      /authorization/i,
      /forbidden/i,
      /not found/i,
      /bad request/i,
      /invalid/i,
    ];

    return nonRetryablePatterns.some(
      pattern => pattern.test(error.message) || pattern.test(error.name)
    );
  }

  /**
   * Calculate approximate data size
   */
  protected calculateDataSize(data: any): number {
    try {
      return JSON.stringify(data).length;
    } catch {
      return 0;
    }
  }

  /**
   * Sleep for specified milliseconds
   */
  protected sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Track request metrics
   */
  private trackRequest(event: {
    request: ConnectorRequest;
    attempt: number;
  }): void {
    this.metrics.totalRequests++;

    metrics.counter('connector_requests_total', {
      connector: this.name,
      type: event.request.type,
      attempt: event.attempt.toString(),
    });
  }

  /**
   * Track response metrics
   */
  private trackResponse(event: {
    request: ConnectorRequest;
    response: ResponseEnvelope;
    attempt: number;
  }): void {
    if (event.response.success) {
      this.metrics.successfulRequests++;
    } else {
      this.metrics.failedRequests++;
    }

    // Update response time metrics
    const responseTime = event.response.metadata.executionTime;
    this.updateResponseTimeMetrics(responseTime);

    // Track data quality metrics
    if (event.response.metadata.freshness !== undefined) {
      this.updateFreshnessMetrics(event.response.metadata.freshness);
    }

    metrics.histogram('connector_response_time', responseTime, undefined, {
      connector: this.name,
      status: event.response.status,
    });
  }

  /**
   * Track error metrics
   */
  private trackError(event: {
    request: ConnectorRequest;
    error: Error;
    attempt: number;
  }): void {
    const errorType = event.error.name || 'UnknownError';
    const currentCount = this.metrics.errorsByType.get(errorType) || 0;
    this.metrics.errorsByType.set(errorType, currentCount + 1);

    // Update error rate
    this.metrics.errorRate =
      this.metrics.failedRequests / this.metrics.totalRequests;

    metrics.counter('connector_errors_total', {
      connector: this.name,
      error_type: errorType,
      attempt: event.attempt.toString(),
    });
  }

  /**
   * Update response time metrics with running averages
   */
  private updateResponseTimeMetrics(responseTime: number): void {
    const totalRequests = this.metrics.totalRequests;
    this.metrics.averageResponseTime =
      (this.metrics.averageResponseTime * (totalRequests - 1) + responseTime) /
      totalRequests;
  }

  /**
   * Update freshness metrics
   */
  private updateFreshnessMetrics(freshness: number): void {
    const successfulRequests = this.metrics.successfulRequests;
    this.metrics.averageFreshness =
      (this.metrics.averageFreshness * (successfulRequests - 1) + freshness) /
      successfulRequests;
  }

  /**
   * Get current connector metrics
   */
  public getMetrics(): ConnectorMetrics {
    return { ...this.metrics };
  }

  /**
   * Get connector status
   */
  public getStatus(): {
    name: string;
    connected: boolean;
    health: number;
    lastHealthCheck: number;
    metrics: ConnectorMetrics;
  } {
    return {
      name: this.name,
      connected: this.isConnected,
      health: this.connectionHealth,
      lastHealthCheck: this.lastHealthCheck,
      metrics: this.getMetrics(),
    };
  }

  /**
   * Merge config with defaults
   */
  private mergeWithDefaults(config: Partial<ConnectorConfig>): ConnectorConfig {
    return {
      timeout: 30000, // 30 seconds
      maxRetries: 3,
      retryDelay: 1000, // 1 second
      rateLimit: {
        requestsPerSecond: 10,
        burstSize: 20,
        backoffMultiplier: 2.0,
      },
      cache: {
        enabled: true,
        ttlSeconds: 300, // 5 minutes
        maxSize: 1000,
      },
      ...config,
    };
  }

  /**
   * Initialize metrics structure
   */
  private initializeMetrics(): ConnectorMetrics {
    return {
      totalRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      averageResponseTime: 0,
      p95ResponseTime: 0,
      p99ResponseTime: 0,
      errorsByType: new Map(),
      errorRate: 0,
      rateLimitHits: 0,
      throttleEvents: 0,
      averageFreshness: 0,
      averageConfidence: 0,
      averageCompleteness: 0,
      cacheHitRate: 0,
      bandwidthUsed: 0,
      connectionPoolSize: 0,
    };
  }
}

/**
 * Connector factory for creating connector instances
 */
export class ConnectorFactory {
  private static readonly connectors = new Map<string, typeof Connector>();

  /**
   * Register a connector class
   */
  static register(type: string, connectorClass: typeof Connector): void {
    this.connectors.set(type, connectorClass);
  }

  /**
   * Create connector instance
   */
  static create(
    type: string,
    name: string,
    config: Partial<ConnectorConfig> = {}
  ): Connector {
    const ConnectorClass = this.connectors.get(type);
    if (!ConnectorClass) {
      throw new Error(`Connector type '${type}' not registered`);
    }

    return new ConnectorClass(name, config);
  }

  /**
   * List available connector types
   */
  static getAvailableTypes(): string[] {
    return Array.from(this.connectors.keys());
  }
}

// Export types and interfaces
export type { ConnectorMetrics };
export { Connector, ConnectorFactory };
