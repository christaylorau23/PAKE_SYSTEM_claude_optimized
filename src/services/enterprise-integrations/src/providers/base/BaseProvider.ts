import { EventEmitter } from 'events';
import {
  IntegrationProvider,
  ConnectionCredentials,
  SyncOperation,
  IntegrationData,
  IntegrationMetrics,
  IntegrationHealth,
  BatchJob,
  WebhookEvent,
  APIGatewayRequest,
  APIGatewayResponse,
} from '../../types/integration';

export abstract class BaseProvider extends EventEmitter {
  protected isInitialized = false;
  protected metrics: Partial<IntegrationMetrics> = {};
  protected health: Partial<IntegrationHealth> = {
    status: 'healthy',
    errorCount: 0,
    issues: [],
  };

  constructor() {
    super();
    this.setupMetrics();
  }

  abstract getProviderInfo(): IntegrationProvider;
  abstract initialize(credentials: ConnectionCredentials): Promise<void>;
  abstract testConnection(): Promise<boolean>;
  abstract performSync(operation: SyncOperation): Promise<IntegrationData[]>;
  abstract disconnect(): Promise<void>;

  async isHealthy(): Promise<boolean> {
    try {
      if (!this.isInitialized) return false;
      return await this.testConnection();
    } catch (error) {
      this.recordError(error as Error);
      return false;
    }
  }

  getMetrics(): Partial<IntegrationMetrics> {
    return { ...this.metrics };
  }

  getHealth(): Partial<IntegrationHealth> {
    return { ...this.health };
  }

  async processRequest(
    request: APIGatewayRequest
  ): Promise<APIGatewayResponse> {
    const startTime = Date.now();

    try {
      this.incrementMetric('totalOperations');

      const response = await this.handleRequest(request);

      this.incrementMetric('successfulOperations');
      this.updateMetric('averageResponseTime', Date.now() - startTime);

      return {
        requestId: request.id,
        status: response.status || 200,
        headers: response.headers || {},
        body: response.body,
        duration: Date.now() - startTime,
        cached: false,
        timestamp: new Date(),
      };
    } catch (error) {
      this.incrementMetric('failedOperations');
      this.recordError(error as Error);

      return {
        requestId: request.id,
        status: 500,
        headers: {},
        body: { error: (error as Error).message },
        duration: Date.now() - startTime,
        cached: false,
        timestamp: new Date(),
      };
    }
  }

  protected async handleRequest(
    request: APIGatewayRequest
  ): Promise<Partial<APIGatewayResponse>> {
    throw new Error('handleRequest method must be implemented by subclass');
  }

  async processBatchJob(job: BatchJob): Promise<void> {
    this.emit('batchJobStarted', job);

    try {
      const syncOperation: SyncOperation = {
        id: job.id,
        connectionId: job.connectionId,
        type: 'manual',
        direction: 'inbound',
        entityType: job.configuration.entityType,
        status: 'running',
        startTime: new Date(),
        recordsProcessed: 0,
        recordsSuccessful: 0,
        recordsFailed: 0,
        errors: [],
        metrics: {
          duration: 0,
          throughput: 0,
          dataTransferred: 0,
          apiCallsMade: 0,
          rateLimitHits: 0,
          retryAttempts: 0,
        },
        metadata: job.configuration.customOptions || {},
      };

      const results = await this.performSync(syncOperation);

      this.emit('batchJobCompleted', {
        ...job,
        status: 'completed',
        results: {
          summary: {
            totalRecords: results.length,
            processedRecords: results.length,
            successfulRecords: results.length,
            failedRecords: 0,
            currentBatch: 1,
            totalBatches: 1,
          },
          metrics: syncOperation.metrics,
          artifacts: [],
        },
      });
    } catch (error) {
      this.emit('batchJobFailed', {
        ...job,
        status: 'failed',
        error: (error as Error).message,
      });
      throw error;
    }
  }

  async processWebhookEvent(event: WebhookEvent): Promise<void> {
    try {
      this.emit('webhookReceived', event);

      if (!event.verified) {
        throw new Error('Webhook event verification failed');
      }

      await this.handleWebhookEvent(event);

      this.emit('webhookProcessed', { ...event, processed: true });
    } catch (error) {
      this.emit('webhookError', {
        ...event,
        processingError: (error as Error).message,
      });
      throw error;
    }
  }

  protected async handleWebhookEvent(event: WebhookEvent): Promise<void> {
    // Default implementation - can be overridden by subclasses
    console.log(`Received webhook event: ${event.eventType}`);
  }

  protected recordError(error: Error): void {
    this.incrementMetric('errorCount');
    this.health.errorCount = (this.health.errorCount || 0) + 1;
    this.health.issues?.push({
      type: 'other',
      severity: 'medium',
      message: error.message,
      timestamp: new Date(),
      resolved: false,
    });

    // Limit health issues to last 100
    if (this.health.issues && this.health.issues.length > 100) {
      this.health.issues = this.health.issues.slice(-100);
    }

    this.updateHealthStatus();
    this.emit('error', error);
  }

  protected updateHealthStatus(): void {
    const errorCount = this.health.errorCount || 0;
    const criticalIssues =
      this.health.issues?.filter(i => i.severity === 'critical' && !i.resolved)
        .length || 0;

    if (criticalIssues > 0) {
      this.health.status = 'down';
    } else if (errorCount > 10) {
      this.health.status = 'degraded';
    } else {
      this.health.status = 'healthy';
    }

    this.health.lastCheck = new Date();
  }

  protected incrementMetric(key: keyof IntegrationMetrics): void {
    if (typeof this.metrics[key] === 'number') {
      (this.metrics[key] as number)++;
    } else {
      (this.metrics as any)[key] = 1;
    }
  }

  protected updateMetric(key: keyof IntegrationMetrics, value: number): void {
    if (key === 'averageResponseTime') {
      const current = this.metrics.averageResponseTime || 0;
      const total = this.metrics.totalOperations || 1;
      this.metrics.averageResponseTime =
        (current * (total - 1) + value) / total;
    } else {
      (this.metrics as any)[key] = value;
    }
  }

  private setupMetrics(): void {
    this.metrics = {
      totalOperations: 0,
      successfulOperations: 0,
      failedOperations: 0,
      averageResponseTime: 0,
      dataTransferred: 0,
      rateLimitHits: 0,
      errorRate: 0,
      uptime: 0,
      cost: 0,
      timestamp: new Date(),
    };

    // Update error rate every minute
    setInterval(() => {
      const total = this.metrics.totalOperations || 1;
      const failed = this.metrics.failedOperations || 0;
      this.metrics.errorRate = (failed / total) * 100;
    }, 60000);
  }

  protected async sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  protected async retry<T>(
    operation: () => Promise<T>,
    maxRetries = 3,
    delay = 1000
  ): Promise<T> {
    let lastError: Error;

    for (let i = 0; i <= maxRetries; i++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error as Error;
        this.incrementMetric('rateLimitHits'); // Assuming retries are due to rate limits

        if (i < maxRetries) {
          await this.sleep(delay * Math.pow(2, i)); // Exponential backoff
        }
      }
    }

    throw lastError!;
  }

  protected validateCredentials(credentials: ConnectionCredentials): void {
    if (!credentials) {
      throw new Error('Credentials are required');
    }
  }

  protected log(
    level: 'info' | 'warn' | 'error',
    message: string,
    meta?: any
  ): void {
    const logData = {
      provider: this.getProviderInfo().id,
      message,
      meta,
      timestamp: new Date(),
    };

    this.emit('log', { level, ...logData });
  }
}
