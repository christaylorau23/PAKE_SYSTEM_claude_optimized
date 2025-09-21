/**
 * Task Submission API Endpoint
 *
 * Provides RESTful API for task submission with comprehensive error handling,
 * validation, rate limiting, and audit trail integration.
 *
 * Features:
 * - Request validation with JSON Schema
 * - Rate limiting per client/IP
 * - Provider routing with fallback
 * - Comprehensive error handling
 * - Audit trail integration
 * - Response caching for duplicate requests
 * - Request timeout handling
 * - Circuit breaker integration
 */

import { Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import { RateLimiterMemory } from 'rate-limiter-flexible';
import { v4 as uuidv4 } from 'uuid';
import {
  AgentTask,
  AgentResult,
  AgentTaskType,
  AgentResultStatus,
} from '../../agent-runtime/src/types/Agent';
import { OrchestratorRouter, RoutingDecision } from '../router';
import { AuditLog, AuditContext, AuditEventType } from '../store/AuditLog';
import { FeatureFlags, FeatureFlagContext } from '../../config/FeatureFlags';
import { createLogger, Logger } from '../utils/logger';

// Request/Response schemas
const TaskSubmissionRequestSchema = z.object({
  type: z.nativeEnum(AgentTaskType),
  input: z.object({
    content: z.string().min(1).max(50000),
    context: z.record(z.any()).optional(),
    format: z.enum(['text', 'json', 'structured']).optional().default('text'),
    language: z.string().optional(),
    priority: z.enum(['low', 'normal', 'high', 'urgent']).optional().default('normal'),
  }),
  config: z
    .object({
      timeout: z.number().min(1000).max(300000).optional().default(30000),
      maxRetries: z.number().min(0).max(5).optional().default(3),
      temperature: z.number().min(0).max(2).optional(),
      maxTokens: z.number().min(1).max(100000).optional(),
      stream: z.boolean().optional().default(false),
      preferredProvider: z.string().optional(),
      fallbackProviders: z.array(z.string()).optional(),
      costLimit: z.number().min(0).optional(),
      quality: z.enum(['fast', 'balanced', 'best']).optional().default('balanced'),
    })
    .optional()
    .default({}),
  metadata: z
    .object({
      source: z.string().optional(),
      userId: z.string().optional(),
      sessionId: z.string().optional(),
      clientId: z.string().optional(),
      correlationId: z.string().optional(),
      tags: z.array(z.string()).optional(),
      priority: z.enum(['low', 'normal', 'high', 'urgent']).optional().default('normal'),
      createdAt: z.string().optional(),
    })
    .optional()
    .default({}),
});

const TaskSubmissionResponseSchema = z.object({
  success: z.boolean(),
  taskId: z.string(),
  status: z.nativeEnum(AgentResultStatus),
  result: z
    .object({
      output: z.any(),
      metadata: z.record(z.any()),
      provider: z.string(),
      executionTime: z.number(),
      tokensUsed: z.number().optional(),
      cost: z.number().optional(),
    })
    .optional(),
  routing: z
    .object({
      selectedProvider: z.string(),
      reason: z.string(),
      alternatives: z.array(z.string()),
      fallbacksUsed: z.array(z.string()).optional(),
      loadBalancingStrategy: z.string().optional(),
    })
    .optional(),
  error: z
    .object({
      code: z.string(),
      message: z.string(),
      details: z.record(z.any()).optional(),
      retryable: z.boolean().optional(),
      suggestedRetryAfter: z.number().optional(),
    })
    .optional(),
  warnings: z.array(z.string()).optional(),
  audit: z.object({
    requestId: z.string(),
    timestamp: z.string(),
    processingTime: z.number(),
  }),
});

type TaskSubmissionRequest = z.infer<typeof TaskSubmissionRequestSchema>;
type TaskSubmissionResponse = z.infer<typeof TaskSubmissionResponseSchema>;

/**
 * Task submission error types
 */
export enum TaskSubmissionErrorCode {
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  RATE_LIMIT_EXCEEDED = 'RATE_LIMIT_EXCEEDED',
  PROVIDER_UNAVAILABLE = 'PROVIDER_UNAVAILABLE',
  TIMEOUT_ERROR = 'TIMEOUT_ERROR',
  QUOTA_EXCEEDED = 'QUOTA_EXCEEDED',
  INVALID_CONFIGURATION = 'INVALID_CONFIGURATION',
  INTERNAL_ERROR = 'INTERNAL_ERROR',
  CIRCUIT_BREAKER_OPEN = 'CIRCUIT_BREAKER_OPEN',
  COST_LIMIT_EXCEEDED = 'COST_LIMIT_EXCEEDED',
  CONTENT_POLICY_VIOLATION = 'CONTENT_POLICY_VIOLATION',
}

export class TaskSubmissionError extends Error {
  constructor(
    public readonly code: TaskSubmissionErrorCode,
    message: string,
    public readonly details?: Record<string, unknown>,
    public readonly retryable: boolean = false,
    public readonly suggestedRetryAfter?: number
  ) {
    super(message);
    this.name = 'TaskSubmissionError';
  }
}

/**
 * Request cache for handling duplicate submissions
 */
interface CacheEntry {
  response: TaskSubmissionResponse;
  timestamp: number;
  expiresAt: number;
}

/**
 * Main task submission API handler
 */
export class TaskSubmissionAPI {
  private readonly router: OrchestratorRouter;
  private readonly auditLog: AuditLog;
  private readonly featureFlags: FeatureFlags;
  private readonly logger: Logger;

  // Rate limiting - different limits for different tiers
  private readonly rateLimiters: Map<string, RateLimiterMemory>;

  // Response caching for duplicate requests
  private readonly responseCache: Map<string, CacheEntry> = new Map();
  private readonly cacheCleanupInterval: NodeJS.Timeout;

  // Metrics tracking
  private readonly metrics = {
    requestsTotal: 0,
    requestsSuccessful: 0,
    requestsFailed: 0,
    requestsRateLimited: 0,
    averageExecutionTime: 0,
    providersUsed: new Map<string, number>(),
    errorsByType: new Map<string, number>(),
  };

  constructor(
    router: OrchestratorRouter,
    auditLog: AuditLog,
    featureFlags: FeatureFlags,
    logger?: Logger
  ) {
    this.router = router;
    this.auditLog = auditLog;
    this.featureFlags = featureFlags;
    this.logger = logger || createLogger('TaskSubmissionAPI');

    // Initialize rate limiters for different tiers
    this.rateLimiters = new Map([
      // Free tier: 10 requests per minute
      [
        'free',
        new RateLimiterMemory({
          points: 10,
          duration: 60,
          blockDuration: 60,
        }),
      ],
      // Basic tier: 100 requests per minute
      [
        'basic',
        new RateLimiterMemory({
          points: 100,
          duration: 60,
          blockDuration: 30,
        }),
      ],
      // Pro tier: 1000 requests per minute
      [
        'pro',
        new RateLimiterMemory({
          points: 1000,
          duration: 60,
          blockDuration: 10,
        }),
      ],
      // Enterprise tier: 10000 requests per minute
      [
        'enterprise',
        new RateLimiterMemory({
          points: 10000,
          duration: 60,
          blockDuration: 5,
        }),
      ],
    ]);

    // Cleanup cache every 5 minutes
    this.cacheCleanupInterval = setInterval(
      () => {
        this.cleanupCache();
      },
      5 * 60 * 1000
    );
  }

  /**
   * Main middleware function for handling task submission
   */
  public handleSubmission = async (
    req: Request,
    res: Response,
    next: NextFunction
  ): Promise<void> => {
    const startTime = Date.now();
    const requestId = uuidv4();

    try {
      // Check if API is enabled via feature flags
      const apiEnabled = this.featureFlags.evaluate('TASK_SUBMISSION_API_ENABLED', {
        userId: req.headers['x-user-id'] as string,
        environment: process.env.NODE_ENV || 'development',
      });

      if (!apiEnabled.value) {
        throw new TaskSubmissionError(
          TaskSubmissionErrorCode.INTERNAL_ERROR,
          'Task submission API is currently disabled'
        );
      }

      // Extract client information
      const clientInfo = this.extractClientInfo(req);

      // Rate limiting check
      await this.checkRateLimit(clientInfo);

      // Validate request body
      const validatedRequest = this.validateRequest(req.body);

      // Create agent task
      const agentTask = this.createAgentTask(validatedRequest, requestId, clientInfo);

      // Check cache for duplicate requests
      const cacheKey = this.generateCacheKey(agentTask);
      const cachedResponse = this.getCachedResponse(cacheKey);
      if (cachedResponse) {
        this.logger.info('Returning cached response', {
          requestId,
          taskId: agentTask.id,
          cacheKey,
        });
        res.status(200).json(cachedResponse);
        return;
      }

      // Create audit context
      const auditContext: AuditContext = {
        requestId,
        userId: clientInfo.userId,
        sessionId: clientInfo.sessionId,
        clientId: clientInfo.clientId,
        ipAddress: clientInfo.ipAddress,
        userAgent: clientInfo.userAgent,
        correlationId: validatedRequest.metadata?.correlationId,
        additionalData: {
          requestSize: JSON.stringify(req.body).length,
          contentLength: validatedRequest.input.content.length,
          taskType: validatedRequest.type,
        },
      };

      // Log task submission
      await this.auditLog.logTaskSubmission(agentTask, auditContext);

      // Execute task with timeout
      const executionPromise = this.executeTaskWithTimeout(
        agentTask,
        auditContext,
        validatedRequest.config?.timeout || 30000
      );

      const { result, decision } = await executionPromise;

      // Build response
      const response = this.buildSuccessResponse(agentTask, result, decision, requestId, startTime);

      // Cache response if appropriate
      if (this.shouldCacheResponse(agentTask, result)) {
        this.cacheResponse(cacheKey, response);
      }

      // Update metrics
      this.updateMetrics('success', decision.selectedProvider, Date.now() - startTime);

      // Send response
      res.status(200).json(response);
    } catch (error) {
      await this.handleError(error, req, res, requestId, startTime);
    }
  };

  /**
   * Extract client information from request
   */
  private extractClientInfo(req: Request): {
    userId?: string;
    sessionId?: string;
    clientId?: string;
    ipAddress: string;
    userAgent: string;
    tier: string;
  } {
    return {
      userId: req.headers['x-user-id'] as string,
      sessionId: req.headers['x-session-id'] as string,
      clientId: req.headers['x-client-id'] as string,
      ipAddress: req.ip || req.connection.remoteAddress || 'unknown',
      userAgent: req.headers['user-agent'] || 'unknown',
      tier: (req.headers['x-user-tier'] as string) || 'free',
    };
  }

  /**
   * Check rate limiting based on client tier
   */
  private async checkRateLimit(clientInfo: unknown): Promise<void> {
    const rateLimiter = this.rateLimiters.get(clientInfo.tier) || this.rateLimiters.get('free')!;
    const key = clientInfo.userId || clientInfo.clientId || clientInfo.ipAddress;

    try {
      await rateLimiter.consume(key);
    } catch (rateLimiterRes) {
      this.metrics.requestsRateLimited++;

      throw new TaskSubmissionError(
        TaskSubmissionErrorCode.RATE_LIMIT_EXCEEDED,
        `Rate limit exceeded for tier ${clientInfo.tier}`,
        {
          tier: clientInfo.tier,
          resetTime: new Date(Date.now() + (rateLimiterRes as any).msBeforeNext),
        },
        true,
        Math.ceil((rateLimiterRes as any).msBeforeNext / 1000)
      );
    }
  }

  /**
   * Validate request body against schema
   */
  private validateRequest(body: unknown): TaskSubmissionRequest {
    try {
      return TaskSubmissionRequestSchema.parse(body);
    } catch (error) {
      throw new TaskSubmissionError(
        TaskSubmissionErrorCode.VALIDATION_ERROR,
        'Invalid request format',
        { validationErrors: error }
      );
    }
  }

  /**
   * Create AgentTask from validated request
   */
  private createAgentTask(
    request: TaskSubmissionRequest,
    requestId: string,
    clientInfo: unknown
  ): AgentTask {
    return {
      id: requestId,
      type: request.type,
      input: request.input,
      config: {
        timeout: request.config?.timeout || 30000,
        maxRetries: request.config?.maxRetries || 3,
        temperature: request.config?.temperature,
        maxTokens: request.config?.maxTokens,
        stream: request.config?.stream || false,
        preferredProvider: request.config?.preferredProvider,
        fallbackProviders: request.config?.fallbackProviders || [],
        costLimit: request.config?.costLimit,
        quality: request.config?.quality || 'balanced',
        priority: request.metadata?.priority || 'normal',
      },
      metadata: {
        ...request.metadata,
        createdAt: new Date().toISOString(),
        source: request.metadata?.source || 'api',
        requestId,
        clientInfo,
      },
    };
  }

  /**
   * Generate cache key for request deduplication
   */
  private generateCacheKey(task: AgentTask): string {
    const keyData = {
      type: task.type,
      content: task.input.content,
      config: {
        temperature: task.config.temperature,
        maxTokens: task.config.maxTokens,
        quality: task.config.quality,
      },
    };

    return Buffer.from(JSON.stringify(keyData)).toString('base64');
  }

  /**
   * Get cached response if available and valid
   */
  private getCachedResponse(cacheKey: string): TaskSubmissionResponse | null {
    const entry = this.responseCache.get(cacheKey);
    if (!entry || Date.now() > entry.expiresAt) {
      this.responseCache.delete(cacheKey);
      return null;
    }
    return entry.response;
  }

  /**
   * Cache response for future duplicate requests
   */
  private cacheResponse(cacheKey: string, response: TaskSubmissionResponse): void {
    const cacheTTL = this.featureFlags.evaluate('RESPONSE_CACHE_TTL_SECONDS').value || 300;

    this.responseCache.set(cacheKey, {
      response,
      timestamp: Date.now(),
      expiresAt: Date.now() + cacheTTL * 1000,
    });
  }

  /**
   * Determine if response should be cached
   */
  private shouldCacheResponse(task: AgentTask, result: AgentResult): boolean {
    // Only cache successful results for certain task types
    if (result.status !== AgentResultStatus.SUCCESS) {
      return false;
    }

    // Don't cache streaming responses or very large responses
    if (task.config.stream || JSON.stringify(result.output).length > 10000) {
      return false;
    }

    return this.featureFlags.evaluate('ENABLE_RESPONSE_CACHING').value;
  }

  /**
   * Execute task with timeout handling
   */
  private async executeTaskWithTimeout(
    task: AgentTask,
    auditContext: AuditContext,
    timeoutMs: number
  ): Promise<{ result: AgentResult; decision: RoutingDecision }> {
    return new Promise(async (resolve, reject) => {
      const timeoutHandle = setTimeout(() => {
        reject(
          new TaskSubmissionError(
            TaskSubmissionErrorCode.TIMEOUT_ERROR,
            `Task execution timed out after ${timeoutMs}ms`,
            { timeout: timeoutMs },
            true,
            60
          )
        );
      }, timeoutMs);

      try {
        const executionResult = await this.router.executeTask(task);
        clearTimeout(timeoutHandle);

        // Log successful execution
        await this.auditLog.logTaskExecution(
          task,
          executionResult.result,
          executionResult.decision,
          auditContext
        );

        resolve(executionResult);
      } catch (error) {
        clearTimeout(timeoutHandle);

        // Log failed execution
        await this.auditLog.logTaskError(task, error, auditContext);

        // Convert router errors to submission errors
        if (error.name === 'ProviderUnavailableError') {
          reject(
            new TaskSubmissionError(
              TaskSubmissionErrorCode.PROVIDER_UNAVAILABLE,
              error.message,
              { originalError: error },
              true,
              30
            )
          );
        } else if (error.name === 'CircuitBreakerOpenError') {
          reject(
            new TaskSubmissionError(
              TaskSubmissionErrorCode.CIRCUIT_BREAKER_OPEN,
              error.message,
              { originalError: error },
              true,
              error.retryAfter || 60
            )
          );
        } else {
          reject(
            new TaskSubmissionError(
              TaskSubmissionErrorCode.INTERNAL_ERROR,
              'Task execution failed',
              { originalError: error },
              false
            )
          );
        }
      }
    });
  }

  /**
   * Build successful response object
   */
  private buildSuccessResponse(
    task: AgentTask,
    result: AgentResult,
    decision: RoutingDecision,
    requestId: string,
    startTime: number
  ): TaskSubmissionResponse {
    return {
      success: true,
      taskId: task.id,
      status: result.status,
      result: {
        output: result.output,
        metadata: result.metadata,
        provider: decision.selectedProvider,
        executionTime: result.metadata.executionTimeMs || 0,
        tokensUsed: result.metadata.tokensUsed,
        cost: result.metadata.estimatedCost,
      },
      routing: {
        selectedProvider: decision.selectedProvider,
        reason: decision.reason,
        alternatives: decision.alternatives,
        fallbacksUsed: decision.fallbacksUsed,
        loadBalancingStrategy: decision.loadBalancingStrategy,
      },
      warnings: result.metadata.warnings as string[],
      audit: {
        requestId,
        timestamp: new Date().toISOString(),
        processingTime: Date.now() - startTime,
      },
    };
  }

  /**
   * Handle errors and send appropriate response
   */
  private async handleError(
    error: unknown,
    req: Request,
    res: Response,
    requestId: string,
    startTime: number
  ): Promise<void> {
    const processingTime = Date.now() - startTime;

    // Log error for monitoring
    this.logger.error('Task submission error', {
      requestId,
      error: error.message,
      stack: error.stack,
      processingTime,
    });

    // Update metrics
    this.updateMetrics('error', 'none', processingTime, error.code);

    // Determine HTTP status code
    let statusCode = 500;
    if (error instanceof TaskSubmissionError) {
      switch (error.code) {
        case TaskSubmissionErrorCode.VALIDATION_ERROR:
          statusCode = 400;
          break;
        case TaskSubmissionErrorCode.RATE_LIMIT_EXCEEDED:
          statusCode = 429;
          break;
        case TaskSubmissionErrorCode.PROVIDER_UNAVAILABLE:
        case TaskSubmissionErrorCode.CIRCUIT_BREAKER_OPEN:
          statusCode = 503;
          break;
        case TaskSubmissionErrorCode.TIMEOUT_ERROR:
          statusCode = 408;
          break;
        case TaskSubmissionErrorCode.QUOTA_EXCEEDED:
        case TaskSubmissionErrorCode.COST_LIMIT_EXCEEDED:
          statusCode = 402;
          break;
        case TaskSubmissionErrorCode.CONTENT_POLICY_VIOLATION:
          statusCode = 400;
          break;
        default:
          statusCode = 500;
      }
    }

    // Build error response
    const response: TaskSubmissionResponse = {
      success: false,
      taskId: requestId,
      status: AgentResultStatus.ERROR,
      error: {
        code:
          error instanceof TaskSubmissionError
            ? error.code
            : TaskSubmissionErrorCode.INTERNAL_ERROR,
        message: error.message,
        details: error instanceof TaskSubmissionError ? error.details : undefined,
        retryable: error instanceof TaskSubmissionError ? error.retryable : false,
        suggestedRetryAfter:
          error instanceof TaskSubmissionError ? error.suggestedRetryAfter : undefined,
      },
      audit: {
        requestId,
        timestamp: new Date().toISOString(),
        processingTime,
      },
    };

    // Set retry-after header if applicable
    if (error instanceof TaskSubmissionError && error.suggestedRetryAfter) {
      res.setHeader('Retry-After', error.suggestedRetryAfter.toString());
    }

    res.status(statusCode).json(response);
  }

  /**
   * Update internal metrics
   */
  private updateMetrics(
    type: 'success' | 'error',
    provider: string,
    executionTime: number,
    errorCode?: string
  ): void {
    this.metrics.requestsTotal++;

    if (type === 'success') {
      this.metrics.requestsSuccessful++;
      this.metrics.providersUsed.set(provider, (this.metrics.providersUsed.get(provider) || 0) + 1);
    } else {
      this.metrics.requestsFailed++;
      if (errorCode) {
        this.metrics.errorsByType.set(
          errorCode,
          (this.metrics.errorsByType.get(errorCode) || 0) + 1
        );
      }
    }

    // Update running average execution time
    this.metrics.averageExecutionTime =
      (this.metrics.averageExecutionTime * (this.metrics.requestsTotal - 1) + executionTime) /
      this.metrics.requestsTotal;
  }

  /**
   * Clean up expired cache entries
   */
  private cleanupCache(): void {
    const now = Date.now();
    let cleanedCount = 0;

    for (const [key, entry] of this.responseCache.entries()) {
      if (now > entry.expiresAt) {
        this.responseCache.delete(key);
        cleanedCount++;
      }
    }

    if (cleanedCount > 0) {
      this.logger.debug(`Cleaned up ${cleanedCount} expired cache entries`);
    }
  }

  /**
   * Get current metrics for monitoring
   */
  public getMetrics(): Record<string, any> {
    return {
      ...this.metrics,
      cacheSize: this.responseCache.size,
      providersUsed: Object.fromEntries(this.metrics.providersUsed),
      errorsByType: Object.fromEntries(this.metrics.errorsByType),
    };
  }

  /**
   * Health check endpoint
   */
  public healthCheck = async (req: Request, res: Response): Promise<void> => {
    try {
      // Check if all dependencies are healthy
      const routerHealth = await this.router.healthCheck();
      const auditLogHealth = await this.auditLog.healthCheck();

      const health = {
        status: 'healthy',
        timestamp: new Date().toISOString(),
        dependencies: {
          router: routerHealth ? 'healthy' : 'unhealthy',
          auditLog: auditLogHealth ? 'healthy' : 'unhealthy',
        },
        metrics: this.getMetrics(),
      };

      const statusCode = routerHealth && auditLogHealth ? 200 : 503;
      res.status(statusCode).json(health);
    } catch (error) {
      res.status(503).json({
        status: 'unhealthy',
        timestamp: new Date().toISOString(),
        error: error.message,
      });
    }
  };

  /**
   * Cleanup resources
   */
  public dispose(): void {
    if (this.cacheCleanupInterval) {
      clearInterval(this.cacheCleanupInterval);
    }

    this.responseCache.clear();
  }
}

// Express router setup
import express from 'express';

export function createTaskSubmissionRouter(
  router: OrchestratorRouter,
  auditLog: AuditLog,
  featureFlags: FeatureFlags
): express.Router {
  const apiRouter = express.Router();
  const taskSubmissionAPI = new TaskSubmissionAPI(router, auditLog, featureFlags);

  // Middleware for JSON parsing and CORS
  apiRouter.use(express.json({ limit: '10mb' }));
  apiRouter.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header(
      'Access-Control-Allow-Headers',
      'Origin, X-Requested-With, Content-Type, Accept, Authorization, X-User-Id, X-Session-Id, X-Client-Id, X-User-Tier'
    );
    res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    next();
  });

  // Routes
  apiRouter.post('/submit', taskSubmissionAPI.handleSubmission);
  apiRouter.get('/health', taskSubmissionAPI.healthCheck);

  // Metrics endpoint (protected)
  apiRouter.get('/metrics', (req, res) => {
    const apiKey = req.headers['x-api-key'];
    if (!apiKey || apiKey !== process.env.METRICS_API_KEY) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    res.json(taskSubmissionAPI.getMetrics());
  });

  return apiRouter;
}

export { TaskSubmissionAPI, TaskSubmissionError, TaskSubmissionErrorCode };
