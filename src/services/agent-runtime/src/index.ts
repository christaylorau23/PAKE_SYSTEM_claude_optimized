/**
 * Agent Runtime - Core Module Exports
 *
 * This module provides a centralized export point for the Agent Runtime system,
 * including providers, types, schemas, and utilities.
 */

// Core interfaces and types
export * from './types';
export * from './providers/AgentProvider';

// Provider implementations
export { NullProvider } from './providers/NullProvider';

// Feature flags and configuration
export * from '../config/FeatureFlags';

/**
 * Agent Runtime System - Main orchestrator
 */
import { AgentProvider, AgentProviderConfig } from './providers/AgentProvider';
import { NullProvider } from './providers/NullProvider';
import { AgentTask, AgentResult, AgentTaskType } from './types';
import { agentRuntimeFlags, flags } from '../config/FeatureFlags';

/**
 * Agent Runtime configuration
 */
export interface AgentRuntimeConfig {
  /** Default provider to use when none specified */
  defaultProvider?: string;
  /** Provider configurations */
  providers?: Record<string, AgentProviderConfig>;
  /** Global timeout for tasks */
  globalTimeout?: number;
  /** Maximum concurrent tasks */
  maxConcurrentTasks?: number;
  /** Enable metrics collection */
  enableMetrics?: boolean;
}

/**
 * Task execution options
 */
export interface TaskExecutionOptions {
  /** Specific provider to use for this task */
  provider?: string;
  /** Override timeout for this task */
  timeout?: number;
  /** Task priority (higher numbers = higher priority) */
  priority?: number;
}

/**
 * Agent Runtime Statistics
 */
export interface AgentRuntimeStats {
  /** Total tasks executed */
  totalTasks: number;
  /** Tasks by status */
  tasksByStatus: Record<string, number>;
  /** Tasks by provider */
  tasksByProvider: Record<string, number>;
  /** Average execution time by task type */
  avgExecutionTime: Record<AgentTaskType, number>;
  /** Currently active tasks */
  activeTasks: number;
  /** Uptime in milliseconds */
  uptime: number;
}

/**
 * Main Agent Runtime System
 */
export class AgentRuntime {
  private readonly providers = new Map<string, AgentProvider>();
  private readonly config: AgentRuntimeConfig;
  private readonly stats: AgentRuntimeStats;
  private readonly startTime = Date.now();
  private taskCounter = 0;

  constructor(config: AgentRuntimeConfig = {}) {
    this.config = {
      defaultProvider: 'null',
      maxConcurrentTasks: flags.getConcurrentTaskLimit(),
      globalTimeout: flags.getTaskTimeout(),
      enableMetrics: flags.isMetricsCollectionEnabled(),
      ...config,
    };

    this.stats = {
      totalTasks: 0,
      tasksByStatus: {},
      tasksByProvider: {},
      avgExecutionTime: {} as Record<AgentTaskType, number>,
      activeTasks: 0,
      uptime: 0,
    };

    this.initializeDefaultProviders();
  }

  /**
   * Initialize default providers based on feature flags
   */
  private initializeDefaultProviders(): void {
    // Always register NullProvider for testing
    if (flags.isNullProviderEnabled()) {
      const nullProvider = new NullProvider(this.config.providers?.null);
      this.registerProvider('null', nullProvider);
    }

    // TODO: Add other providers based on feature flags
    // if (flags.isLLMProviderEnabled()) {
    //   this.registerProvider('llm', new LLMProvider(this.config.providers?.llm));
    // }
  }

  /**
   * Register an agent provider
   */
  registerProvider(name: string, provider: AgentProvider): void {
    this.providers.set(name, provider);
  }

  /**
   * Get registered provider by name
   */
  getProvider(name: string): AgentProvider | undefined {
    return this.providers.get(name);
  }

  /**
   * List all registered providers
   */
  listProviders(): string[] {
    return Array.from(this.providers.keys());
  }

  /**
   * Execute an agent task
   */
  async executeTask(task: AgentTask, options: TaskExecutionOptions = {}): Promise<AgentResult> {
    if (!flags.isAgentRuntimeEnabled()) {
      throw new Error('Agent Runtime is disabled via feature flag');
    }

    // Apply timeout override
    if (options.timeout && task.config.timeout) {
      task.config.timeout = Math.min(task.config.timeout, options.timeout);
    } else if (options.timeout) {
      task.config.timeout = options.timeout;
    } else if (this.config.globalTimeout && !task.config.timeout) {
      task.config.timeout = this.config.globalTimeout;
    }

    // Select provider
    const providerName = options.provider || this.config.defaultProvider || 'null';
    const provider = this.providers.get(providerName);

    if (!provider) {
      throw new Error(`Provider '${providerName}' not found`);
    }

    // Check concurrent task limit
    if (this.stats.activeTasks >= (this.config.maxConcurrentTasks || 10)) {
      throw new Error('Maximum concurrent tasks limit reached');
    }

    // Execute task with metrics
    this.stats.activeTasks++;
    const startTime = Date.now();

    try {
      const result = await provider.run(task);

      // Update statistics
      if (this.config.enableMetrics) {
        this.updateStats(task, result, Date.now() - startTime);
      }

      return result;
    } catch (error) {
      // Update error statistics
      if (this.config.enableMetrics) {
        this.stats.tasksByStatus['error'] = (this.stats.tasksByStatus['error'] || 0) + 1;
      }
      throw error;
    } finally {
      this.stats.activeTasks--;
    }
  }

  /**
   * Create and execute a simple task
   */
  async runTask(
    type: AgentTaskType,
    content: string,
    options: TaskExecutionOptions & { userId?: string } = {}
  ): Promise<AgentResult> {
    const task: AgentTask = {
      id: `task_${++this.taskCounter}_${Date.now()}`,
      type,
      input: { content },
      config: {
        timeout: options.timeout || this.config.globalTimeout,
        priority: options.priority || 5,
      },
      metadata: {
        source: 'agent_runtime',
        createdAt: new Date().toISOString(),
        userId: options.userId,
      },
    };

    return this.executeTask(task, options);
  }

  /**
   * Health check for all providers
   */
  async healthCheck(): Promise<Record<string, boolean>> {
    const health: Record<string, boolean> = {};

    for (const [name, provider] of this.providers) {
      try {
        health[name] = await provider.healthCheck();
      } catch (error) {
        health[name] = false;
      }
    }

    return health;
  }

  /**
   * Get runtime statistics
   */
  getStats(): AgentRuntimeStats {
    return {
      ...this.stats,
      uptime: Date.now() - this.startTime,
    };
  }

  /**
   * Reset statistics
   */
  resetStats(): void {
    this.stats.totalTasks = 0;
    this.stats.tasksByStatus = {};
    this.stats.tasksByProvider = {};
    this.stats.avgExecutionTime = {} as Record<AgentTaskType, number>;
    this.taskCounter = 0;
  }

  /**
   * Shutdown the runtime and clean up resources
   */
  async shutdown(): Promise<void> {
    const providers = Array.from(this.providers.values());
    await Promise.allSettled(providers.map((provider) => provider.dispose()));
    this.providers.clear();
  }

  /**
   * Update execution statistics
   */
  private updateStats(task: AgentTask, result: AgentResult, executionTime: number): void {
    this.stats.totalTasks++;

    // Update status counts
    this.stats.tasksByStatus[result.status] = (this.stats.tasksByStatus[result.status] || 0) + 1;

    // Update provider counts
    this.stats.tasksByProvider[result.metadata.provider] =
      (this.stats.tasksByProvider[result.metadata.provider] || 0) + 1;

    // Update average execution time
    const currentAvg = this.stats.avgExecutionTime[task.type] || 0;
    const taskCount = this.stats.tasksByStatus['success'] || 1;
    this.stats.avgExecutionTime[task.type] =
      (currentAvg * (taskCount - 1) + executionTime) / taskCount;
  }
}

/**
 * Default agent runtime instance
 */
export const defaultAgentRuntime = new AgentRuntime();

/**
 * Convenience functions for common operations
 */
export const agent = {
  /**
   * Analyze sentiment of text content
   */
  analyzeSentiment: async (content: string, options?: TaskExecutionOptions) =>
    defaultAgentRuntime.runTask(AgentTaskType.SENTIMENT_ANALYSIS, content, options),

  /**
   * Extract entities from text content
   */
  extractEntities: async (content: string, options?: TaskExecutionOptions) =>
    defaultAgentRuntime.runTask(AgentTaskType.ENTITY_EXTRACTION, content, options),

  /**
   * Analyze content for insights
   */
  analyzeContent: async (content: string, options?: TaskExecutionOptions) =>
    defaultAgentRuntime.runTask(AgentTaskType.CONTENT_ANALYSIS, content, options),

  /**
   * Detect trends in content
   */
  detectTrends: async (content: string, options?: TaskExecutionOptions) =>
    defaultAgentRuntime.runTask(AgentTaskType.TREND_DETECTION, content, options),

  /**
   * Synthesize content
   */
  synthesizeContent: async (content: string, options?: TaskExecutionOptions) =>
    defaultAgentRuntime.runTask(AgentTaskType.CONTENT_SYNTHESIS, content, options),
};

// Re-export schema validation (if needed)
// Note: In a real implementation, you might want to add JSON Schema validation utilities
export const schemas = {
  agentTask: require('./schemas/AgentTask.json'),
  agentResult: require('./schemas/AgentResult.json'),
  trendRecord: require('./schemas/TrendRecord.json'),
};
