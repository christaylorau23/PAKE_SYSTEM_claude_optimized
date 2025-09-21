import { EventEmitter } from 'events';
import {
  Tool,
  ToolExecution,
  ToolCategory,
  RateLimit,
  ToolAuthentication,
} from '@/types/agent';
import { Logger } from '@/utils/logger';
import { v4 as uuidv4 } from 'uuid';
import * as fs from 'fs';
import { performance } from 'perf_hooks';

interface ToolInstance {
  tool: Tool;
  executor: ToolExecutor;
  rateLimiter: RateLimiter;
  costTracker: CostTracker;
  usageStats: ToolUsageStats;
  authHandler?: AuthenticationHandler;
}

interface ToolExecutor {
  execute(
    parameters: Record<string, any>,
    context: ExecutionContext
  ): Promise<any>;
  validate(parameters: Record<string, any>): Promise<ValidationResult>;
  cleanup?(context: ExecutionContext): Promise<void>;
}

interface ExecutionContext {
  executionId: string;
  agentId: string;
  taskId: string;
  userId?: string;
  constraints: ExecutionConstraints;
  metadata: Record<string, any>;
}

interface ExecutionConstraints {
  maxExecutionTime: number; // milliseconds
  maxCost: number; // USD
  maxRetries: number;
  requiresApproval: boolean;
  allowedOutputFormats: string[];
  resourceLimits: ResourceLimits;
}

interface ResourceLimits {
  maxMemoryMB: number;
  maxCpuPercent: number;
  maxNetworkMBps: number;
  maxStorageMB: number;
}

interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
  sanitizedParameters: Record<string, any>;
}

interface RateLimiter {
  canExecute(toolId: string, userId?: string): boolean;
  recordExecution(toolId: string, userId?: string): void;
  getRemainingQuota(toolId: string, userId?: string): number;
  resetQuota(toolId: string, userId?: string): void;
}

interface CostTracker {
  calculateCost(toolId: string, parameters: any, result: any): number;
  recordCost(executionId: string, cost: number): void;
  getTotalCost(period: 'hour' | 'day' | 'month'): number;
  getUserCost(userId: string, period: 'hour' | 'day' | 'month'): number;
}

interface ToolUsageStats {
  totalExecutions: number;
  successfulExecutions: number;
  failedExecutions: number;
  averageExecutionTime: number;
  totalCost: number;
  lastUsed: Date;
  errorRate: number;
  popularParameters: Record<string, number>;
}

interface AuthenticationHandler {
  authenticate(credentials: any): Promise<boolean>;
  refreshToken?(): Promise<string>;
  validatePermissions(
    operation: string,
    context: ExecutionContext
  ): Promise<boolean>;
}

export class ToolRegistry extends EventEmitter {
  private logger: Logger;
  private tools: Map<string, ToolInstance> = new Map();
  private executions: Map<string, ToolExecution> = new Map();
  private rateLimiter: RateLimiter;
  private costTracker: CostTracker;
  private authProviders: Map<string, AuthenticationHandler> = new Map();

  constructor() {
    super();
    this.logger = new Logger('ToolRegistry');
    this.rateLimiter = new DefaultRateLimiter();
    this.costTracker = new DefaultCostTracker();
    this.initializeBuiltInTools();
    this.setupCleanupTasks();
    this.logger.info('Tool Registry initialized');
  }

  // Tool management
  async registerTool(tool: Tool, executor: ToolExecutor): Promise<void> {
    try {
      // Validate tool definition
      this.validateTool(tool);

      // Create authentication handler if needed
      let authHandler: AuthenticationHandler | undefined;
      if (tool.authentication && tool.authentication.required) {
        authHandler = this.createAuthHandler(tool.authentication);
      }

      // Create tool instance
      const instance: ToolInstance = {
        tool,
        executor,
        rateLimiter: new DefaultRateLimiter(tool.rateLimit),
        costTracker: new DefaultCostTracker(),
        usageStats: {
          totalExecutions: 0,
          successfulExecutions: 0,
          failedExecutions: 0,
          averageExecutionTime: 0,
          totalCost: 0,
          lastUsed: new Date(0),
          errorRate: 0,
          popularParameters: {},
        },
        authHandler,
      };

      this.tools.set(tool.id, instance);

      this.logger.info(`Tool registered: ${tool.name}`, {
        toolId: tool.id,
        category: tool.category,
      });

      this.emit('tool_registered', { tool });
    } catch (error) {
      this.logger.error('Failed to register tool', {
        toolId: tool.id,
        error: (error as Error).message,
      });
      throw error;
    }
  }

  async unregisterTool(toolId: string): Promise<void> {
    const instance = this.tools.get(toolId);
    if (!instance) {
      throw new Error(`Tool not found: ${toolId}`);
    }

    // Cancel any running executions
    const runningExecutions = Array.from(this.executions.values()).filter(
      exec => exec.toolId === toolId && exec.status === 'running'
    );

    for (const execution of runningExecutions) {
      await this.cancelExecution(execution.id);
    }

    // Cleanup tool resources
    if (instance.executor.cleanup) {
      await instance.executor.cleanup({
        executionId: '',
        agentId: '',
        taskId: '',
        constraints: this.getDefaultConstraints(),
        metadata: {},
      });
    }

    this.tools.delete(toolId);

    this.logger.info(`Tool unregistered: ${toolId}`);
    this.emit('tool_unregistered', { toolId });
  }

  // Tool execution
  async executeTool(
    toolId: string,
    parameters: Record<string, any>,
    context: ExecutionContext
  ): Promise<any> {
    const startTime = performance.now();
    const executionId = uuidv4();

    try {
      // Get tool instance
      const instance = this.tools.get(toolId);
      if (!instance) {
        throw new Error(`Tool not found: ${toolId}`);
      }

      // Check if tool is active
      if (!instance.tool.isActive) {
        throw new Error(`Tool is inactive: ${toolId}`);
      }

      // Check rate limits
      if (!instance.rateLimiter.canExecute(toolId, context.userId)) {
        throw new Error(`Rate limit exceeded for tool: ${toolId}`);
      }

      // Validate authentication
      if (instance.authHandler) {
        const hasPermission = await instance.authHandler.validatePermissions(
          'execute',
          context
        );
        if (!hasPermission) {
          throw new Error(`Insufficient permissions for tool: ${toolId}`);
        }
      }

      // Validate parameters
      const validation = await instance.executor.validate(parameters);
      if (!validation.isValid) {
        throw new Error(
          `Parameter validation failed: ${validation.errors.join(', ')}`
        );
      }

      // Check resource constraints
      this.validateResourceConstraints(context.constraints);

      // Create execution record
      const execution: ToolExecution = {
        id: executionId,
        toolId,
        agentId: context.agentId,
        taskId: context.taskId,
        parameters: validation.sanitizedParameters,
        startTime: new Date(),
        status: 'running',
        metrics: {
          duration: 0,
          requestsMade: 0,
          dataTransferred: 0,
          cost: 0,
        },
      };

      this.executions.set(executionId, execution);
      this.emit('execution_started', { execution });

      // Record rate limit usage
      instance.rateLimiter.recordExecution(toolId, context.userId);

      // Execute tool
      this.logger.info(`Executing tool: ${toolId}`, {
        executionId,
        agentId: context.agentId,
      });

      const result = await Promise.race([
        instance.executor.execute(validation.sanitizedParameters, context),
        this.createTimeoutPromise(context.constraints.maxExecutionTime),
      ]);

      // Calculate execution metrics
      const executionTime = performance.now() - startTime;
      const cost = instance.costTracker.calculateCost(
        toolId,
        parameters,
        result
      );

      // Update execution record
      execution.endTime = new Date();
      execution.status = 'completed';
      execution.result = result;
      execution.metrics.duration = executionTime;
      execution.metrics.cost = cost;

      // Update usage statistics
      this.updateUsageStats(instance, executionTime, cost, parameters, true);

      // Record cost
      instance.costTracker.recordCost(executionId, cost);

      this.logger.info(`Tool execution completed: ${toolId}`, {
        executionId,
        duration: executionTime,
        cost,
      });

      this.emit('execution_completed', { execution });
      return result;
    } catch (error) {
      const executionTime = performance.now() - startTime;
      const execution = this.executions.get(executionId);

      if (execution) {
        execution.endTime = new Date();
        execution.status = 'failed';
        execution.error = (error as Error).message;
        execution.metrics.duration = executionTime;
      }

      // Update failure statistics
      const instance = this.tools.get(toolId);
      if (instance) {
        this.updateUsageStats(instance, executionTime, 0, parameters, false);
      }

      this.logger.error(`Tool execution failed: ${toolId}`, {
        executionId,
        error: (error as Error).message,
      });

      this.emit('execution_failed', { executionId, error });
      throw error;
    } finally {
      // Cleanup execution record after delay
      setTimeout(() => {
        this.executions.delete(executionId);
      }, 300000); // 5 minutes
    }
  }

  async cancelExecution(executionId: string): Promise<void> {
    const execution = this.executions.get(executionId);
    if (!execution) {
      throw new Error(`Execution not found: ${executionId}`);
    }

    if (execution.status !== 'running') {
      throw new Error(`Execution is not running: ${executionId}`);
    }

    execution.status = 'cancelled';
    execution.endTime = new Date();

    this.logger.info(`Execution cancelled: ${executionId}`);
    this.emit('execution_cancelled', { executionId });
  }

  // Tool discovery and information
  getAvailableTools(category?: ToolCategory): Tool[] {
    return Array.from(this.tools.values())
      .filter(instance => instance.tool.isActive)
      .filter(instance => !category || instance.tool.category === category)
      .map(instance => instance.tool);
  }

  getTool(toolId: string): Tool | null {
    const instance = this.tools.get(toolId);
    return instance ? instance.tool : null;
  }

  getToolUsageStats(toolId: string): ToolUsageStats | null {
    const instance = this.tools.get(toolId);
    return instance ? instance.usageStats : null;
  }

  searchTools(query: string, category?: ToolCategory): Tool[] {
    const searchTerms = query.toLowerCase().split(' ');

    return Array.from(this.tools.values())
      .filter(instance => instance.tool.isActive)
      .filter(instance => !category || instance.tool.category === category)
      .filter(instance => {
        const searchText = [
          instance.tool.name,
          instance.tool.description,
          ...instance.tool.capabilities.inputs.map(i => i.name),
          ...instance.tool.capabilities.outputs.map(o => o.name),
        ]
          .join(' ')
          .toLowerCase();

        return searchTerms.every(term => searchText.includes(term));
      })
      .map(instance => instance.tool);
  }

  // Execution monitoring
  getActiveExecutions(): ToolExecution[] {
    return Array.from(this.executions.values()).filter(
      exec => exec.status === 'running'
    );
  }

  getExecution(executionId: string): ToolExecution | null {
    return this.executions.get(executionId) || null;
  }

  getExecutionHistory(limit: number = 100): ToolExecution[] {
    return Array.from(this.executions.values())
      .filter(exec => exec.status !== 'running')
      .sort((a, b) => b.startTime.getTime() - a.startTime.getTime())
      .slice(0, limit);
  }

  // Cost and usage analytics
  getTotalCost(period: 'hour' | 'day' | 'month'): number {
    return this.costTracker.getTotalCost(period);
  }

  getUserCost(userId: string, period: 'hour' | 'day' | 'month'): number {
    return this.costTracker.getUserCost(userId, period);
  }

  getToolCostBreakdown(): Record<string, number> {
    const breakdown: Record<string, number> = {};

    for (const [toolId, instance] of this.tools) {
      breakdown[toolId] = instance.usageStats.totalCost;
    }

    return breakdown;
  }

  // Rate limiting management
  getRemainingQuota(toolId: string, userId?: string): number {
    const instance = this.tools.get(toolId);
    return instance
      ? instance.rateLimiter.getRemainingQuota(toolId, userId)
      : 0;
  }

  resetUserQuota(toolId: string, userId: string): void {
    const instance = this.tools.get(toolId);
    if (instance) {
      instance.rateLimiter.resetQuota(toolId, userId);
    }
  }

  // Private methods
  private validateTool(tool: Tool): void {
    if (!tool.id || !tool.name || !tool.description) {
      throw new Error('Tool must have id, name, and description');
    }

    if (
      !tool.capabilities ||
      !tool.capabilities.inputs ||
      !tool.capabilities.outputs
    ) {
      throw new Error('Tool must define input and output capabilities');
    }

    if (!tool.rateLimit) {
      throw new Error('Tool must define rate limits');
    }

    if (!tool.cost) {
      throw new Error('Tool must define cost structure');
    }
  }

  private createAuthHandler(auth: ToolAuthentication): AuthenticationHandler {
    // Create appropriate authentication handler based on type
    switch (auth.type) {
      case 'api_key':
        return new ApiKeyAuthHandler();
      case 'oauth':
        return new OAuthAuthHandler();
      case 'bearer_token':
        return new BearerTokenAuthHandler();
      default:
        throw new Error(`Unsupported authentication type: ${auth.type}`);
    }
  }

  private validateResourceConstraints(constraints: ExecutionConstraints): void {
    // Validate resource constraints
    if (constraints.maxExecutionTime < 1000) {
      throw new Error('Maximum execution time must be at least 1 second');
    }

    if (constraints.maxCost <= 0) {
      throw new Error('Maximum cost must be positive');
    }
  }

  private createTimeoutPromise(timeout: number): Promise<never> {
    return new Promise((_, reject) => {
      setTimeout(() => {
        reject(new Error(`Tool execution timed out after ${timeout}ms`));
      }, timeout);
    });
  }

  private updateUsageStats(
    instance: ToolInstance,
    executionTime: number,
    cost: number,
    parameters: any,
    success: boolean
  ): void {
    const stats = instance.usageStats;

    stats.totalExecutions++;
    if (success) {
      stats.successfulExecutions++;
    } else {
      stats.failedExecutions++;
    }

    stats.averageExecutionTime =
      (stats.averageExecutionTime * (stats.totalExecutions - 1) +
        executionTime) /
      stats.totalExecutions;
    stats.totalCost += cost;
    stats.lastUsed = new Date();
    stats.errorRate = stats.failedExecutions / stats.totalExecutions;

    // Track popular parameters
    Object.keys(parameters).forEach(param => {
      stats.popularParameters[param] =
        (stats.popularParameters[param] || 0) + 1;
    });
  }

  private getDefaultConstraints(): ExecutionConstraints {
    return {
      maxExecutionTime: 300000, // 5 minutes
      maxCost: 1.0, // $1
      maxRetries: 3,
      requiresApproval: false,
      allowedOutputFormats: ['json', 'text', 'binary'],
      resourceLimits: {
        maxMemoryMB: 512,
        maxCpuPercent: 50,
        maxNetworkMBps: 10,
        maxStorageMB: 100,
      },
    };
  }

  private initializeBuiltInTools(): void {
    // Initialize built-in tools
    this.registerBuiltInWebSearchTool();
    this.registerBuiltInFileOperationsTool();
    this.registerBuiltInCodeExecutionTool();
    this.registerBuiltInEmailTool();
    this.registerBuiltInDataProcessingTool();
  }

  private async registerBuiltInWebSearchTool(): Promise<void> {
    const tool: Tool = {
      id: 'web_search',
      name: 'Web Search',
      description:
        'Search the web for information using various search engines',
      category: 'web_search',
      version: '1.0.0',
      capabilities: {
        inputs: [
          {
            name: 'query',
            type: 'string',
            required: true,
            description: 'Search query',
          },
          {
            name: 'maxResults',
            type: 'number',
            required: false,
            description: 'Maximum results to return',
            default: 10,
          },
          {
            name: 'language',
            type: 'string',
            required: false,
            description: 'Search language',
            default: 'en',
          },
        ],
        outputs: [
          {
            name: 'results',
            type: 'array',
            required: true,
            description: 'Search results',
          },
        ],
        supportsStreaming: false,
        supportsBatch: true,
        maxConcurrentUses: 10,
      },
      rateLimit: {
        requestsPerMinute: 60,
        requestsPerHour: 1000,
        requestsPerDay: 10000,
        concurrentRequests: 5,
      },
      cost: {
        type: 'per_request',
        amount: 0.01,
        currency: 'USD',
      },
      documentation: 'https://docs.pake.local/tools/web-search',
      isActive: true,
    };

    const executor = new WebSearchExecutor();
    await this.registerTool(tool, executor);
  }

  private async registerBuiltInFileOperationsTool(): Promise<void> {
    const tool: Tool = {
      id: 'file_operations',
      name: 'File Operations',
      description:
        'Perform file system operations like read, write, create, delete',
      category: 'file_operations',
      version: '1.0.0',
      capabilities: {
        inputs: [
          {
            name: 'operation',
            type: 'string',
            required: true,
            description: 'Operation type: read, write, create, delete, list',
          },
          {
            name: 'path',
            type: 'string',
            required: true,
            description: 'File or directory path',
          },
          {
            name: 'content',
            type: 'string',
            required: false,
            description: 'Content for write operations',
          },
        ],
        outputs: [
          {
            name: 'result',
            type: 'object',
            required: true,
            description: 'Operation result',
          },
        ],
        supportsStreaming: true,
        supportsBatch: true,
        maxConcurrentUses: 5,
      },
      rateLimit: {
        requestsPerMinute: 120,
        requestsPerHour: 5000,
        requestsPerDay: 50000,
        concurrentRequests: 3,
      },
      cost: {
        type: 'free',
        amount: 0,
        currency: 'USD',
      },
      documentation: 'https://docs.pake.local/tools/file-operations',
      isActive: true,
    };

    const executor = new FileOperationsExecutor();
    await this.registerTool(tool, executor);
  }

  private async registerBuiltInCodeExecutionTool(): Promise<void> {
    const tool: Tool = {
      id: 'code_execution',
      name: 'Code Execution',
      description: 'Execute code in various programming languages',
      category: 'analysis',
      version: '1.0.0',
      capabilities: {
        inputs: [
          {
            name: 'language',
            type: 'string',
            required: true,
            description: 'Programming language',
          },
          {
            name: 'code',
            type: 'string',
            required: true,
            description: 'Code to execute',
          },
          {
            name: 'timeout',
            type: 'number',
            required: false,
            description: 'Execution timeout in seconds',
            default: 30,
          },
        ],
        outputs: [
          {
            name: 'result',
            type: 'object',
            required: true,
            description: 'Execution result',
          },
        ],
        supportsStreaming: false,
        supportsBatch: false,
        maxConcurrentUses: 3,
      },
      rateLimit: {
        requestsPerMinute: 10,
        requestsPerHour: 100,
        requestsPerDay: 1000,
        concurrentRequests: 2,
      },
      cost: {
        type: 'per_request',
        amount: 0.05,
        currency: 'USD',
      },
      documentation: 'https://docs.pake.local/tools/code-execution',
      isActive: true,
    };

    const executor = new CodeExecutionExecutor();
    await this.registerTool(tool, executor);
  }

  private async registerBuiltInEmailTool(): Promise<void> {
    const tool: Tool = {
      id: 'email_sending',
      name: 'Email Sending',
      description: 'Send emails with support for attachments and templates',
      category: 'communication',
      version: '1.0.0',
      capabilities: {
        inputs: [
          {
            name: 'to',
            type: 'array',
            required: true,
            description: 'Recipient email addresses',
          },
          {
            name: 'subject',
            type: 'string',
            required: true,
            description: 'Email subject',
          },
          {
            name: 'body',
            type: 'string',
            required: true,
            description: 'Email body',
          },
          {
            name: 'attachments',
            type: 'array',
            required: false,
            description: 'File attachments',
          },
        ],
        outputs: [
          {
            name: 'messageId',
            type: 'string',
            required: true,
            description: 'Email message ID',
          },
        ],
        supportsStreaming: false,
        supportsBatch: true,
        maxConcurrentUses: 5,
      },
      rateLimit: {
        requestsPerMinute: 30,
        requestsPerHour: 500,
        requestsPerDay: 2000,
        concurrentRequests: 3,
      },
      cost: {
        type: 'per_request',
        amount: 0.02,
        currency: 'USD',
      },
      authentication: {
        type: 'api_key',
        required: true,
      },
      documentation: 'https://docs.pake.local/tools/email-sending',
      isActive: true,
    };

    const executor = new EmailSendingExecutor();
    await this.registerTool(tool, executor);
  }

  private async registerBuiltInDataProcessingTool(): Promise<void> {
    const tool: Tool = {
      id: 'data_processing',
      name: 'Data Processing',
      description: 'Process and transform data in various formats',
      category: 'data_processing',
      version: '1.0.0',
      capabilities: {
        inputs: [
          {
            name: 'operation',
            type: 'string',
            required: true,
            description: 'Processing operation',
          },
          {
            name: 'data',
            type: 'object',
            required: true,
            description: 'Input data',
          },
          {
            name: 'options',
            type: 'object',
            required: false,
            description: 'Processing options',
          },
        ],
        outputs: [
          {
            name: 'processedData',
            type: 'object',
            required: true,
            description: 'Processed data',
          },
        ],
        supportsStreaming: true,
        supportsBatch: true,
        maxConcurrentUses: 8,
      },
      rateLimit: {
        requestsPerMinute: 100,
        requestsPerHour: 2000,
        requestsPerDay: 20000,
        concurrentRequests: 5,
      },
      cost: {
        type: 'per_request',
        amount: 0.005,
        currency: 'USD',
      },
      documentation: 'https://docs.pake.local/tools/data-processing',
      isActive: true,
    };

    const executor = new DataProcessingExecutor();
    await this.registerTool(tool, executor);
  }

  private setupCleanupTasks(): void {
    // Clean up old execution records
    setInterval(
      () => {
        const cutoff = new Date(Date.now() - 24 * 60 * 60 * 1000); // 24 hours ago

        for (const [executionId, execution] of this.executions) {
          if (execution.endTime && execution.endTime < cutoff) {
            this.executions.delete(executionId);
          }
        }
      },
      60 * 60 * 1000
    ); // Every hour
  }
}

// Default implementations
class DefaultRateLimiter implements RateLimiter {
  private limits: Map<string, RateLimit>;
  private usage: Map<string, Map<string, number[]>> = new Map(); // toolId -> userId -> timestamps

  constructor(limits?: RateLimit) {
    this.limits = new Map();
    if (limits) {
      this.limits.set('default', limits);
    }
  }

  canExecute(toolId: string, userId: string = 'anonymous'): boolean {
    const limit = this.limits.get(toolId) || this.limits.get('default');
    if (!limit) return true;

    const userUsage = this.getUserUsage(toolId, userId);
    const now = Date.now();

    // Check per-minute limit
    const minuteUsage = userUsage.filter(
      timestamp => now - timestamp < 60000
    ).length;
    if (minuteUsage >= limit.requestsPerMinute) return false;

    // Check per-hour limit
    const hourUsage = userUsage.filter(
      timestamp => now - timestamp < 3600000
    ).length;
    if (hourUsage >= limit.requestsPerHour) return false;

    // Check per-day limit
    const dayUsage = userUsage.filter(
      timestamp => now - timestamp < 86400000
    ).length;
    if (dayUsage >= limit.requestsPerDay) return false;

    return true;
  }

  recordExecution(toolId: string, userId: string = 'anonymous'): void {
    const userUsage = this.getUserUsage(toolId, userId);
    userUsage.push(Date.now());
  }

  getRemainingQuota(toolId: string, userId: string = 'anonymous'): number {
    const limit = this.limits.get(toolId) || this.limits.get('default');
    if (!limit) return Infinity;

    const userUsage = this.getUserUsage(toolId, userId);
    const now = Date.now();
    const minuteUsage = userUsage.filter(
      timestamp => now - timestamp < 60000
    ).length;

    return Math.max(0, limit.requestsPerMinute - minuteUsage);
  }

  resetQuota(toolId: string, userId: string = 'anonymous'): void {
    const toolUsage = this.usage.get(toolId);
    if (toolUsage) {
      toolUsage.delete(userId);
    }
  }

  private getUserUsage(toolId: string, userId: string): number[] {
    if (!this.usage.has(toolId)) {
      this.usage.set(toolId, new Map());
    }

    const toolUsage = this.usage.get(toolId)!;
    if (!toolUsage.has(userId)) {
      toolUsage.set(userId, []);
    }

    return toolUsage.get(userId)!;
  }
}

class DefaultCostTracker implements CostTracker {
  private costs: Map<string, number> = new Map(); // executionId -> cost
  private userCosts: Map<string, number[]> = new Map(); // userId -> [timestamp, cost][]

  calculateCost(_toolId: string, _parameters: any, _result: any): number {
    // Simple cost calculation - would be more sophisticated in practice
    return 0.01; // Base cost
  }

  recordCost(executionId: string, cost: number): void {
    this.costs.set(executionId, cost);
  }

  getTotalCost(_period: 'hour' | 'day' | 'month'): number {
    // Would implement proper time-based filtering
    return Array.from(this.costs.values()).reduce((sum, cost) => sum + cost, 0);
  }

  getUserCost(_userId: string, _period: 'hour' | 'day' | 'month'): number {
    // Would implement user-specific cost tracking
    return 0;
  }
}

// Tool executor implementations
class WebSearchExecutor implements ToolExecutor {
  async execute(
    parameters: Record<string, any>,
    _context: ExecutionContext
  ): Promise<any> {
    // Mock web search implementation
    return {
      results: [
        {
          title: 'Sample Result 1',
          url: 'https://example1.com',
          snippet: 'Sample snippet 1',
        },
        {
          title: 'Sample Result 2',
          url: 'https://example2.com',
          snippet: 'Sample snippet 2',
        },
      ],
      totalResults: 2,
      query: parameters.query,
    };
  }

  async validate(parameters: Record<string, any>): Promise<ValidationResult> {
    const errors: string[] = [];

    if (!parameters.query || typeof parameters.query !== 'string') {
      errors.push('Query is required and must be a string');
    }

    if (
      parameters.maxResults &&
      (typeof parameters.maxResults !== 'number' || parameters.maxResults <= 0)
    ) {
      errors.push('MaxResults must be a positive number');
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings: [],
      sanitizedParameters: {
        query: parameters.query,
        maxResults: parameters.maxResults || 10,
        language: parameters.language || 'en',
      },
    };
  }
}

class FileOperationsExecutor implements ToolExecutor {
  async execute(
    parameters: Record<string, any>,
    _context: ExecutionContext
  ): Promise<any> {
    const { operation, path: filePath, content } = parameters;

    try {
      switch (operation) {
        case 'read':
          return {
            content: fs.readFileSync(filePath, 'utf8'),
            size: fs.statSync(filePath).size,
          };
        case 'write':
          fs.writeFileSync(filePath, content);
          return {
            success: true,
            bytesWritten: Buffer.byteLength(content, 'utf8'),
          };
        case 'list':
          return { items: fs.readdirSync(filePath) };
        case 'delete':
          fs.unlinkSync(filePath);
          return { success: true };
        default:
          throw new Error(`Unsupported operation: ${operation}`);
      }
    } catch (error) {
      throw new Error(`File operation failed: ${(error as Error).message}`);
    }
  }

  async validate(parameters: Record<string, any>): Promise<ValidationResult> {
    const errors: string[] = [];
    const validOperations = ['read', 'write', 'create', 'delete', 'list'];

    if (
      !parameters.operation ||
      !validOperations.includes(parameters.operation)
    ) {
      errors.push('Operation must be one of: ' + validOperations.join(', '));
    }

    if (!parameters.path || typeof parameters.path !== 'string') {
      errors.push('Path is required and must be a string');
    }

    if (parameters.operation === 'write' && !parameters.content) {
      errors.push('Content is required for write operations');
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings: [],
      sanitizedParameters: parameters,
    };
  }
}

class CodeExecutionExecutor implements ToolExecutor {
  async execute(
    parameters: Record<string, any>,
    _context: ExecutionContext
  ): Promise<any> {
    // Mock code execution - would use sandboxed execution in practice
    return {
      output: 'Mock execution output',
      exitCode: 0,
      executionTime: 150,
    };
  }

  async validate(parameters: Record<string, any>): Promise<ValidationResult> {
    const errors: string[] = [];
    const supportedLanguages = ['javascript', 'python', 'bash'];

    if (
      !parameters.language ||
      !supportedLanguages.includes(parameters.language)
    ) {
      errors.push('Language must be one of: ' + supportedLanguages.join(', '));
    }

    if (!parameters.code || typeof parameters.code !== 'string') {
      errors.push('Code is required and must be a string');
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings: [],
      sanitizedParameters: parameters,
    };
  }
}

class EmailSendingExecutor implements ToolExecutor {
  async execute(
    parameters: Record<string, any>,
    _context: ExecutionContext
  ): Promise<any> {
    // Mock email sending
    return {
      messageId: `mock-${Date.now()}@pake.local`,
      status: 'sent',
      recipients: parameters.to.length,
    };
  }

  async validate(parameters: Record<string, any>): Promise<ValidationResult> {
    const errors: string[] = [];

    if (
      !parameters.to ||
      !Array.isArray(parameters.to) ||
      parameters.to.length === 0
    ) {
      errors.push('To field is required and must be a non-empty array');
    }

    if (!parameters.subject || typeof parameters.subject !== 'string') {
      errors.push('Subject is required and must be a string');
    }

    if (!parameters.body || typeof parameters.body !== 'string') {
      errors.push('Body is required and must be a string');
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings: [],
      sanitizedParameters: parameters,
    };
  }
}

class DataProcessingExecutor implements ToolExecutor {
  async execute(
    parameters: Record<string, any>,
    _context: ExecutionContext
  ): Promise<any> {
    // Mock data processing
    return {
      processedData: { processed: true, original: parameters.data },
      operation: parameters.operation,
      recordsProcessed: 1,
    };
  }

  async validate(parameters: Record<string, any>): Promise<ValidationResult> {
    const errors: string[] = [];

    if (!parameters.operation || typeof parameters.operation !== 'string') {
      errors.push('Operation is required and must be a string');
    }

    if (!parameters.data) {
      errors.push('Data is required');
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings: [],
      sanitizedParameters: parameters,
    };
  }
}

// Authentication handlers
class ApiKeyAuthHandler implements AuthenticationHandler {
  async authenticate(credentials: any): Promise<boolean> {
    // Mock API key validation
    return !!credentials.apiKey;
  }

  async validatePermissions(
    _operation: string,
    _context: ExecutionContext
  ): Promise<boolean> {
    return true; // Mock permission validation
  }
}

class OAuthAuthHandler implements AuthenticationHandler {
  async authenticate(credentials: any): Promise<boolean> {
    // Mock OAuth validation
    return !!credentials.accessToken;
  }

  async refreshToken(): Promise<string> {
    return 'mock-refreshed-token';
  }

  async validatePermissions(
    _operation: string,
    _context: ExecutionContext
  ): Promise<boolean> {
    return true;
  }
}

class BearerTokenAuthHandler implements AuthenticationHandler {
  async authenticate(credentials: any): Promise<boolean> {
    // Mock bearer token validation
    return !!credentials.token;
  }

  async validatePermissions(
    _operation: string,
    _context: ExecutionContext
  ): Promise<boolean> {
    return true;
  }
}

export default ToolRegistry;
