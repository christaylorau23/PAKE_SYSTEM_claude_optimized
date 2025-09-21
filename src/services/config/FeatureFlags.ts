/**
 * Feature Flagging System with Environment-Driven Configuration
 *
 * This module provides a centralized feature flag system that:
 * - Loads configuration from environment variables
 * - Supports typed feature flag definitions
 * - Enables runtime feature toggling without deployments
 * - Provides audit logging of feature flag usage
 * - Supports gradual rollouts and A/B testing
 */

/**
 * Supported feature flag types
 */
export enum FeatureFlagType {
  BOOLEAN = 'boolean',
  STRING = 'string',
  NUMBER = 'number',
  JSON = 'json',
  PERCENTAGE = 'percentage',
}

/**
 * Feature flag definition with metadata
 */
export interface FeatureFlagDefinition<T = any> {
  /** Unique flag identifier */
  key: string;
  /** Flag type for validation */
  type: FeatureFlagType;
  /** Default value when not configured */
  defaultValue: T;
  /** Human-readable description */
  description: string;
  /** Environment variable name (optional, defaults to FEATURE_<KEY>) */
  envVar?: string;
  /** Validation function for custom validation */
  validator?: (value: T) => boolean;
  /** Flag category for organization */
  category?: string;
  /** Deprecation information */
  deprecated?: {
    since: string;
    replacedBy?: string;
    removeAfter?: string;
  };
}

/**
 * Feature flag evaluation context
 */
export interface FeatureFlagContext {
  /** User ID for user-specific flags */
  userId?: string;
  /** Request ID for tracing */
  requestId?: string;
  /** Environment (dev, staging, prod) */
  environment?: string;
  /** Additional context properties */
  properties?: Record<string, any>;
}

/**
 * Feature flag evaluation result
 */
export interface FeatureFlagResult<T = any> {
  /** Flag key */
  key: string;
  /** Evaluated value */
  value: T;
  /** Source of the value (default, env, override) */
  source: 'default' | 'environment' | 'override' | 'percentage';
  /** Evaluation timestamp */
  timestamp: string;
  /** Evaluation context used */
  context?: FeatureFlagContext;
}

/**
 * Central feature flag registry and manager
 */
export class FeatureFlags {
  private readonly flags = new Map<string, FeatureFlagDefinition>();
  private readonly overrides = new Map<string, any>();
  private readonly evaluationLog: FeatureFlagResult[] = [];
  private readonly maxLogSize = 1000;

  /**
   * Register a feature flag definition
   */
  register<T>(definition: FeatureFlagDefinition<T>): void {
    this.flags.set(definition.key, definition);
  }

  /**
   * Register multiple feature flags
   */
  registerAll(definitions: FeatureFlagDefinition[]): void {
    definitions.forEach(def => this.register(def));
  }

  /**
   * Evaluate a feature flag with optional context
   */
  evaluate<T = any>(
    key: string,
    context?: FeatureFlagContext
  ): FeatureFlagResult<T> {
    const definition = this.flags.get(key);
    if (!definition) {
      throw new Error(`Feature flag '${key}' is not registered`);
    }

    let value: T;
    let source: FeatureFlagResult['source'];

    // Check for runtime override first
    if (this.overrides.has(key)) {
      value = this.overrides.get(key);
      source = 'override';
    } else {
      // Get environment variable name
      const envVar = definition.envVar || `FEATURE_${key.toUpperCase()}`;
      const envValue = process.env[envVar];

      if (envValue !== undefined) {
        value = this.parseEnvironmentValue(envValue, definition.type);
        source = 'environment';
      } else {
        value = definition.defaultValue;
        source = 'default';
      }
    }

    // Handle percentage-based flags
    if (definition.type === FeatureFlagType.PERCENTAGE && context?.userId) {
      const percentage = value as unknown as number;
      const userHash = this.hashUserId(context.userId);
      const shouldEnable = userHash % 100 < percentage;
      value = shouldEnable as T;
      source = 'percentage';
    }

    // Validate the value
    if (definition.validator && !definition.validator(value)) {
      console.warn(
        `Feature flag '${key}' failed validation, using default value`
      );
      value = definition.defaultValue;
      source = 'default';
    }

    const result: FeatureFlagResult<T> = {
      key,
      value,
      source,
      timestamp: new Date().toISOString(),
      context,
    };

    // Log evaluation (with size limit)
    this.logEvaluation(result);

    return result;
  }

  /**
   * Get flag value directly (convenience method)
   */
  getValue<T = any>(key: string, context?: FeatureFlagContext): T {
    return this.evaluate<T>(key, context).value;
  }

  /**
   * Check if a boolean feature flag is enabled
   */
  isEnabled(key: string, context?: FeatureFlagContext): boolean {
    return this.getValue<boolean>(key, context);
  }

  /**
   * Set runtime override for a feature flag
   */
  setOverride<T>(key: string, value: T): void {
    this.overrides.set(key, value);
  }

  /**
   * Remove runtime override
   */
  removeOverride(key: string): boolean {
    return this.overrides.delete(key);
  }

  /**
   * Clear all runtime overrides
   */
  clearOverrides(): void {
    this.overrides.clear();
  }

  /**
   * Get all registered flag definitions
   */
  getDefinitions(): FeatureFlagDefinition[] {
    return Array.from(this.flags.values());
  }

  /**
   * Get evaluation history
   */
  getEvaluationLog(): FeatureFlagResult[] {
    return [...this.evaluationLog];
  }

  /**
   * Get current flag configuration for debugging
   */
  getConfiguration(): Record<string, any> {
    const config: Record<string, any> = {};

    for (const [key, definition] of this.flags) {
      const envVar = definition.envVar || `FEATURE_${key.toUpperCase()}`;
      const envValue = process.env[envVar];
      const override = this.overrides.get(key);

      config[key] = {
        type: definition.type,
        defaultValue: definition.defaultValue,
        environmentValue: envValue,
        override: override,
        currentValue:
          override ??
          (envValue
            ? this.parseEnvironmentValue(envValue, definition.type)
            : definition.defaultValue),
      };
    }

    return config;
  }

  /**
   * Validate all environment variables match their definitions
   */
  validateConfiguration(): { valid: boolean; errors: string[] } {
    const errors: string[] = [];

    for (const [key, definition] of this.flags) {
      const envVar = definition.envVar || `FEATURE_${key.toUpperCase()}`;
      const envValue = process.env[envVar];

      if (envValue !== undefined) {
        try {
          const parsed = this.parseEnvironmentValue(envValue, definition.type);
          if (definition.validator && !definition.validator(parsed)) {
            errors.push(`Feature flag '${key}' failed validation`);
          }
        } catch (error) {
          errors.push(
            `Feature flag '${key}' has invalid environment value: ${envValue}`
          );
        }
      }

      // Check for deprecated flags
      if (definition.deprecated && envValue !== undefined) {
        const msg = `Feature flag '${key}' is deprecated since ${definition.deprecated.since}`;
        if (definition.deprecated.replacedBy) {
          errors.push(
            `${msg}, use '${definition.deprecated.replacedBy}' instead`
          );
        } else {
          errors.push(msg);
        }
      }
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  }

  /**
   * Parse environment variable value based on type
   */
  private parseEnvironmentValue(value: string, type: FeatureFlagType): any {
    switch (type) {
      case FeatureFlagType.BOOLEAN:
        return value.toLowerCase() === 'true' || value === '1';

      case FeatureFlagType.STRING:
        return value;

      case FeatureFlagType.NUMBER:
      case FeatureFlagType.PERCENTAGE: {
        const num = Number(value);
        if (isNaN(num)) {
          throw new Error(`Invalid number value: ${value}`);
        }
        return num;
      }

      case FeatureFlagType.JSON:
        try {
          return JSON.parse(value);
        } catch (error) {
          throw new Error(`Invalid JSON value: ${value}`);
        }

      default:
        return value;
    }
  }

  /**
   * Hash user ID for percentage-based flags
   */
  private hashUserId(userId: string): number {
    let hash = 0;
    for (let i = 0; i < userId.length; i++) {
      const char = userId.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return Math.abs(hash);
  }

  /**
   * Log feature flag evaluation (with rotation)
   */
  private logEvaluation(result: FeatureFlagResult): void {
    this.evaluationLog.push(result);

    // Rotate log if it gets too large
    if (this.evaluationLog.length > this.maxLogSize) {
      this.evaluationLog.splice(0, this.evaluationLog.length - this.maxLogSize);
    }
  }
}

/**
 * Default feature flags for the Agent Runtime system
 */
export const AGENT_RUNTIME_FLAGS: FeatureFlagDefinition[] = [
  {
    key: 'AGENT_RUNTIME_ENABLED',
    type: FeatureFlagType.BOOLEAN,
    defaultValue: true,
    description: 'Enable the agent runtime system',
    category: 'core',
  },
  {
    key: 'NULL_PROVIDER_ENABLED',
    type: FeatureFlagType.BOOLEAN,
    defaultValue: true,
    description: 'Enable the null provider for testing',
    category: 'providers',
  },
  {
    key: 'LLM_PROVIDER_ENABLED',
    type: FeatureFlagType.BOOLEAN,
    defaultValue: false,
    description: 'Enable LLM-based agent providers',
    category: 'providers',
  },
  {
    key: 'CONCURRENT_TASK_LIMIT',
    type: FeatureFlagType.NUMBER,
    defaultValue: 10,
    description: 'Maximum number of concurrent agent tasks',
    category: 'performance',
    validator: (value: number) => value > 0 && value <= 100,
  },
  {
    key: 'TASK_TIMEOUT_MS',
    type: FeatureFlagType.NUMBER,
    defaultValue: 30000,
    description: 'Default task timeout in milliseconds',
    category: 'performance',
    validator: (value: number) => value >= 1000 && value <= 300000,
  },
  {
    key: 'ENABLE_RESULT_CACHING',
    type: FeatureFlagType.BOOLEAN,
    defaultValue: false,
    description: 'Enable caching of agent results',
    category: 'performance',
  },
  {
    key: 'CACHE_TTL_SECONDS',
    type: FeatureFlagType.NUMBER,
    defaultValue: 3600,
    description: 'Cache time-to-live in seconds',
    category: 'performance',
  },
  {
    key: 'ENABLE_METRICS_COLLECTION',
    type: FeatureFlagType.BOOLEAN,
    defaultValue: true,
    description: 'Enable collection of agent execution metrics',
    category: 'observability',
  },
  {
    key: 'ENABLE_DETAILED_LOGGING',
    type: FeatureFlagType.BOOLEAN,
    defaultValue: false,
    description: 'Enable detailed debug logging',
    category: 'observability',
  },
  {
    key: 'ROLLOUT_PERCENTAGE',
    type: FeatureFlagType.PERCENTAGE,
    defaultValue: 100,
    description: 'Percentage of users to enable new features for',
    category: 'rollout',
    validator: (value: number) => value >= 0 && value <= 100,
  },
  {
    key: 'EXPERIMENTAL_FEATURES',
    type: FeatureFlagType.JSON,
    defaultValue: {},
    description: 'Configuration for experimental features',
    category: 'experimental',
  },
];

/**
 * Global feature flag instance for the agent runtime
 */
export const agentRuntimeFlags = new FeatureFlags();

// Register default flags
agentRuntimeFlags.registerAll(AGENT_RUNTIME_FLAGS);

/**
 * Convenience functions for common flag checks
 */
export const flags = {
  isAgentRuntimeEnabled: (context?: FeatureFlagContext) =>
    agentRuntimeFlags.isEnabled('AGENT_RUNTIME_ENABLED', context),

  isNullProviderEnabled: (context?: FeatureFlagContext) =>
    agentRuntimeFlags.isEnabled('NULL_PROVIDER_ENABLED', context),

  isLLMProviderEnabled: (context?: FeatureFlagContext) =>
    agentRuntimeFlags.isEnabled('LLM_PROVIDER_ENABLED', context),

  getConcurrentTaskLimit: (context?: FeatureFlagContext) =>
    agentRuntimeFlags.getValue<number>('CONCURRENT_TASK_LIMIT', context),

  getTaskTimeout: (context?: FeatureFlagContext) =>
    agentRuntimeFlags.getValue<number>('TASK_TIMEOUT_MS', context),

  isResultCachingEnabled: (context?: FeatureFlagContext) =>
    agentRuntimeFlags.isEnabled('ENABLE_RESULT_CACHING', context),

  isMetricsCollectionEnabled: (context?: FeatureFlagContext) =>
    agentRuntimeFlags.isEnabled('ENABLE_METRICS_COLLECTION', context),
};

/**
 * Configuration loader that initializes feature flags from environment
 */
export function loadFeatureFlags(): { success: boolean; errors: string[] } {
  const validation = agentRuntimeFlags.validateConfiguration();

  if (!validation.valid) {
    console.warn('Feature flag validation errors:', validation.errors);
  }

  return validation;
}
