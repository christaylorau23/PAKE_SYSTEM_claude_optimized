/**
 * AgentProvider Interface - Core abstraction for agent execution
 *
 * This interface defines the contract for all agent providers in the system.
 * Implementations handle the actual execution of agent tasks and return structured results.
 */

import { AgentTask, AgentResult } from '../types';

/**
 * Core interface for agent execution providers
 *
 * Providers implement different execution strategies:
 * - NullProvider: Returns stubbed results for testing/development
 * - LLMProvider: Executes tasks via Large Language Models
 * - LocalProvider: Uses local AI models or rule-based systems
 * - HybridProvider: Combines multiple execution strategies
 */
export interface AgentProvider {
  /**
   * Execute an agent task and return structured results
   *
   * @param task - The task to execute containing input data and configuration
   * @returns Promise resolving to structured agent result with outputs
   * @throws AgentExecutionError on execution failures
   */
  run(task: AgentTask): Promise<AgentResult>;

  /**
   * Provider metadata and capabilities
   */
  readonly name: string;
  readonly version: string;
  readonly capabilities: AgentCapability[];

  /**
   * Health check for provider availability
   *
   * @returns Promise resolving to true if provider is healthy and ready
   */
  healthCheck(): Promise<boolean>;

  /**
   * Clean up resources when provider is no longer needed
   *
   * @returns Promise resolving when cleanup is complete
   */
  dispose(): Promise<void>;
}

/**
 * Supported agent capabilities
 */
export enum AgentCapability {
  TEXT_ANALYSIS = 'text_analysis',
  SENTIMENT_ANALYSIS = 'sentiment_analysis',
  ENTITY_EXTRACTION = 'entity_extraction',
  TREND_DETECTION = 'trend_detection',
  CONTENT_GENERATION = 'content_generation',
  DATA_SYNTHESIS = 'data_synthesis',
  REAL_TIME_PROCESSING = 'real_time_processing',
}

/**
 * Agent execution error types
 */
export class AgentExecutionError extends Error {
  constructor(
    message: string,
    public readonly code: AgentErrorCode,
    public readonly provider: string,
    public readonly task?: AgentTask,
    public readonly cause?: Error
  ) {
    super(message);
    this.name = 'AgentExecutionError';
  }
}

export enum AgentErrorCode {
  INVALID_INPUT = 'INVALID_INPUT',
  PROVIDER_UNAVAILABLE = 'PROVIDER_UNAVAILABLE',
  TIMEOUT = 'TIMEOUT',
  QUOTA_EXCEEDED = 'QUOTA_EXCEEDED',
  INTERNAL_ERROR = 'INTERNAL_ERROR',
  CONFIGURATION_ERROR = 'CONFIGURATION_ERROR',
}

/**
 * Provider configuration interface
 */
export interface AgentProviderConfig {
  timeout?: number; // Execution timeout in milliseconds
  retries?: number; // Number of retry attempts
  concurrency?: number; // Max concurrent executions
  rateLimiting?: {
    requests: number;
    window: number; // Time window in milliseconds
  };
  [key: string]: any; // Provider-specific configuration
}

/**
 * Provider factory interface for dependency injection
 */
export interface AgentProviderFactory {
  create(config: AgentProviderConfig): AgentProvider;
  supports(providerType: string): boolean;
}
