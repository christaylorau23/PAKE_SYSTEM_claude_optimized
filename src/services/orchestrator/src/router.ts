/**
 * Orchestrator Router - Intelligent provider selection and routing
 *
 * Features:
 * - Policy-based provider selection
 * - Task type optimization
 * - Load balancing and failover
 * - Cost and performance optimization
 * - Circuit breaker pattern for failing providers
 * - Audit trail for routing decisions
 */

import {
  AgentProvider,
  AgentTask,
  AgentResult,
  AgentTaskType,
  AgentCapability,
} from '../../agent-runtime/src/providers/AgentProvider';
import { agentRuntimeFlags, flags } from '../../config/FeatureFlags';
import { RouterAnalytics } from './router-analytics';

/**
 * Routing policy configuration
 */
export interface RoutingPolicy {
  /** Policy name */
  name: string;
  /** Policy priority (higher = more important) */
  priority: number;
  /** Task type mappings */
  taskTypePreferences: Record<AgentTaskType, ProviderPreference[]>;
  /** Default provider preferences */
  defaultPreferences: ProviderPreference[];
  /** Load balancing strategy */
  loadBalancing: LoadBalancingStrategy;
  /** Failover configuration */
  failover: FailoverConfig;
  /** Cost optimization settings */
  costOptimization: CostOptimizationConfig;
  /** Performance requirements */
  performanceRequirements: PerformanceConfig;
}

/**
 * Provider preference configuration
 */
export interface ProviderPreference {
  /** Provider name */
  provider: string;
  /** Preference weight (0-1, higher = more preferred) */
  weight: number;
  /** Conditions for using this provider */
  conditions?: ProviderCondition[];
  /** Maximum cost per request */
  maxCostPerRequest?: number;
  /** Required capabilities */
  requiredCapabilities?: AgentCapability[];
}

/**
 * Provider condition for conditional routing
 */
export interface ProviderCondition {
  type: 'content_length' | 'task_priority' | 'time_constraint' | 'cost_budget' | 'user_preference';
  operator: 'lt' | 'lte' | 'gt' | 'gte' | 'eq' | 'contains' | 'in';
  value: any;
}

/**
 * Load balancing strategies
 */
export enum LoadBalancingStrategy {
  ROUND_ROBIN = 'round_robin',
  WEIGHTED_RANDOM = 'weighted_random',
  LEAST_CONNECTIONS = 'least_connections',
  RESPONSE_TIME = 'response_time',
  COST_OPTIMIZED = 'cost_optimized',
  CAPABILITY_MATCH = 'capability_match',
}

/**
 * Failover configuration
 */
export interface FailoverConfig {
  /** Enable automatic failover */
  enabled: boolean;
  /** Maximum retry attempts */
  maxRetries: number;
  /** Retry delay in milliseconds */
  retryDelay: number;
  /** Circuit breaker configuration */
  circuitBreaker: CircuitBreakerConfig;
  /** Fallback providers in order */
  fallbackProviders: string[];
}

/**
 * Circuit breaker configuration
 */
export interface CircuitBreakerConfig {
  /** Failure threshold to open circuit */
  failureThreshold: number;
  /** Success threshold to close circuit */
  successThreshold: number;
  /** Timeout for half-open state */
  timeout: number;
  /** Window size for failure rate calculation */
  windowSize: number;
}

/**
 * Cost optimization configuration
 */
export interface CostOptimizationConfig {
  /** Enable cost optimization */
  enabled: boolean;
  /** Maximum cost per request */
  maxCostPerRequest: number;
  /** Cost budget per hour */
  hourlyBudget?: number;
  /** Prefer free/local providers */
  preferFreeProviders: boolean;
  /** Cost tracking window in hours */
  costTrackingWindow: number;
}

/**
 * Performance requirements
 */
export interface PerformanceConfig {
  /** Maximum acceptable response time in milliseconds */
  maxResponseTime: number;
  /** Minimum acceptable confidence score */
  minConfidence: number;
  /** Required accuracy for specific task types */
  taskAccuracyRequirements?: Record<AgentTaskType, number>;
  /** Prefer faster providers */
  preferFastProviders: boolean;
}

/**
 * Routing decision information
 */
export interface RoutingDecision {
  /** Selected provider */
  selectedProvider: string;
  /** Reason for selection */
  reason: string;
  /** Alternative providers considered */
  alternatives: string[];
  /** Decision confidence */
  confidence: number;
  /** Estimated cost */
  estimatedCost: number;
  /** Estimated response time */
  estimatedResponseTime: number;
  /** Applied policies */
  appliedPolicies: string[];
  /** Timestamp of decision */
  timestamp: string;
  /** Analytics enhancement indicators */
  analyticsEnhanced?: boolean;
  /** ML prediction data */
  mlPrediction?: {
    confidence: number;
    ensembleMethods: string[];
    alternativeScores: Record<string, number>;
  };
  /** Optimization applied */
  optimizationApplied?: {
    type: 'ml_prediction' | 'cost_optimization' | 'load_balancing' | 'performance_tuning';
    description: string;
    impact: string;
  };
  /** Fallback reason if analytics unavailable */
  fallbackReason?: string;
  /** Used fallback providers */
  fallbacksUsed?: string[];
}

/**
 * Provider statistics for routing decisions
 */
interface ProviderStats {
  totalRequests: number;
  successfulRequests: number;
  failedRequests: number;
  avgResponseTime: number;
  avgCost: number;
  avgConfidence: number;
  lastSuccess: number;
  lastFailure: number;
  circuitBreakerState: 'closed' | 'open' | 'half-open';
  activeConnections: number;
}

/**
 * Main orchestrator router
 */
export class OrchestratorRouter {
  private readonly providers = new Map<string, AgentProvider>();
  private readonly providerStats = new Map<string, ProviderStats>();
  private readonly routingPolicies: RoutingPolicy[] = [];
  private readonly costTracker = new Map<string, { timestamp: number; cost: number }[]>();
  private roundRobinCounters = new Map<string, number>();
  private analytics?: RouterAnalytics;
  private analyticsEnabled = false;

  constructor() {
    this.initializeDefaultPolicies();
    this.startStatsCleanup();
  }

  /**
   * Enable analytics enhancements
   */
  enableAnalyticsEnhancements(analytics: RouterAnalytics): void {
    this.analytics = analytics;
    this.analyticsEnabled = true;
  }

  /**
   * Disable analytics enhancements
   */
  disableAnalyticsEnhancements(): void {
    this.analyticsEnabled = false;
  }

  /**
   * Register a provider with the router
   */
  registerProvider(name: string, provider: AgentProvider): void {
    this.providers.set(name, provider);
    this.initializeProviderStats(name);
  }

  /**
   * Unregister a provider
   */
  unregisterProvider(name: string): void {
    this.providers.delete(name);
    this.providerStats.delete(name);
    this.roundRobinCounters.delete(name);
  }

  /**
   * Add or update routing policy
   */
  addPolicy(policy: RoutingPolicy): void {
    const existingIndex = this.routingPolicies.findIndex((p) => p.name === policy.name);
    if (existingIndex >= 0) {
      this.routingPolicies[existingIndex] = policy;
    } else {
      this.routingPolicies.push(policy);
    }

    // Sort by priority (highest first)
    this.routingPolicies.sort((a, b) => b.priority - a.priority);
  }

  /**
   * Route task to appropriate provider
   */
  async routeTask(
    task: AgentTask
  ): Promise<{ provider: AgentProvider; decision: RoutingDecision }> {
    const startTime = Date.now();

    // Get available providers
    const availableProviders = await this.getAvailableProviders();

    if (availableProviders.length === 0) {
      throw new Error('No providers available for routing');
    }

    // Apply routing policies to select provider
    const decision = await this.selectProvider(task, availableProviders);

    const selectedProvider = this.providers.get(decision.selectedProvider);
    if (!selectedProvider) {
      throw new Error(`Selected provider ${decision.selectedProvider} not found`);
    }

    // Update provider stats
    this.updateProviderStats(decision.selectedProvider, 'route_selected', Date.now() - startTime);

    return { provider: selectedProvider, decision };
  }

  /**
   * Execute task with automatic failover and retry
   */
  async executeTask(task: AgentTask): Promise<{ result: AgentResult; decision: RoutingDecision }> {
    let lastError: Error | null = null;
    let attempts = 0;
    const maxAttempts = this.getMaxRetryAttempts(task);

    while (attempts < maxAttempts) {
      try {
        const { provider, decision } = await this.routeTask(task);

        // Record execution attempt
        this.updateProviderStats(decision.selectedProvider, 'execution_start');

        const startTime = Date.now();
        const result = await provider.run(task);
        const executionTime = Date.now() - startTime;

        // Record success
        this.updateProviderStats(decision.selectedProvider, 'execution_success', executionTime);
        this.recordCost(decision.selectedProvider, decision.estimatedCost);

        // Record analytics data if enabled
        if (this.analyticsEnabled && this.analytics) {
          try {
            await this.analytics.recordExecutionResult(task, {
              provider: decision.selectedProvider,
              executionTime,
              cost: decision.estimatedCost,
              confidence: result.metadata?.confidence || 0.8,
              success: true,
            });
          } catch (error) {
            console.warn('Failed to record analytics data:', error);
          }
        }

        return { result, decision };
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));
        attempts++;

        // Record failure
        if (attempts === 1) {
          // Only record failure for the first attempt to avoid double counting
          const { decision } = await this.routeTask(task);
          this.updateProviderStats(decision.selectedProvider, 'execution_failure');

          // Record analytics data for failure
          if (this.analyticsEnabled && this.analytics) {
            try {
              await this.analytics.recordExecutionResult(task, {
                provider: decision.selectedProvider,
                executionTime: 0,
                cost: 0,
                confidence: 0,
                success: false,
                errorType: lastError?.message || 'unknown',
              });
            } catch (analyticsError) {
              console.warn('Failed to record analytics failure data:', analyticsError);
            }
          }
        }

        // Check if we should retry
        if (attempts < maxAttempts && this.shouldRetry(error, attempts)) {
          const delay = this.calculateRetryDelay(attempts);
          console.warn(
            `Task execution failed (attempt ${attempts}), retrying in ${delay}ms:`,
            error
          );
          await new Promise((resolve) => setTimeout(resolve, delay));
        }
      }
    }

    throw lastError || new Error('Max retry attempts exceeded');
  }

  /**
   * Get routing statistics
   */
  getStats(): Record<string, any> {
    return {
      providers: Object.fromEntries(this.providerStats.entries()),
      policies: this.routingPolicies.map((p) => ({ name: p.name, priority: p.priority })),
      totalProviders: this.providers.size,
      totalRequests: Array.from(this.providerStats.values()).reduce(
        (sum, stats) => sum + stats.totalRequests,
        0
      ),
    };
  }

  /**
   * Get available providers (excluding circuit-broken ones)
   */
  private async getAvailableProviders(): Promise<string[]> {
    const providers: string[] = [];

    for (const [name, provider] of this.providers) {
      const stats = this.providerStats.get(name);

      // Skip if circuit breaker is open
      if (stats?.circuitBreakerState === 'open') {
        continue;
      }

      // Check health if circuit breaker is half-open
      if (stats?.circuitBreakerState === 'half-open') {
        try {
          const isHealthy = await provider.healthCheck();
          if (!isHealthy) continue;
        } catch (error) {
          continue;
        }
      }

      // Skip if not enabled via feature flags
      if (!this.isProviderEnabled(name)) {
        continue;
      }

      providers.push(name);
    }

    return providers;
  }

  /**
   * Select provider based on policies and conditions
   */
  private async selectProvider(
    task: AgentTask,
    availableProviders: string[]
  ): Promise<RoutingDecision> {
    const decision: RoutingDecision = {
      selectedProvider: '',
      reason: '',
      alternatives: [...availableProviders],
      confidence: 0,
      estimatedCost: 0,
      estimatedResponseTime: 0,
      appliedPolicies: [],
      timestamp: new Date().toISOString(),
      analyticsEnhanced: this.analyticsEnabled,
    };

    // Try analytics-enhanced selection first
    if (this.analyticsEnabled && this.analytics) {
      try {
        const mlPrediction = await this.analytics.predictOptimalProvider(task);
        const recommendation = await this.analytics.getRoutingRecommendation(task);

        if (availableProviders.includes(mlPrediction.recommendedProvider)) {
          decision.selectedProvider = mlPrediction.recommendedProvider;
          decision.confidence = mlPrediction.confidence;
          decision.reason = `ML-enhanced selection: ${mlPrediction.reasons.join(', ')}`;
          decision.mlPrediction = {
            confidence: mlPrediction.confidence,
            ensembleMethods: mlPrediction.ensembleMethods,
            alternativeScores: mlPrediction.weightedScores,
          };
          decision.optimizationApplied = {
            type: 'ml_prediction',
            description: 'Used ML ensemble methods for optimal provider selection',
            impact: `${Math.round(mlPrediction.confidence * 100)}% confidence prediction`,
          };
          decision.estimatedCost = recommendation.expectedOutcome.estimatedCost;
          decision.estimatedResponseTime = recommendation.expectedOutcome.estimatedTime;

          return decision;
        }
      } catch (error) {
        console.warn('Analytics prediction failed, falling back to standard routing:', error);
        decision.fallbackReason = `Analytics unavailable: ${error instanceof Error ? error.message : 'unknown error'}`;
      }
    }

    let candidateProviders = availableProviders;

    // Apply routing policies in priority order
    for (const policy of this.routingPolicies) {
      const policyResult = await this.applyPolicy(policy, task, candidateProviders);

      if (policyResult.providers.length > 0) {
        candidateProviders = policyResult.providers;
        decision.appliedPolicies.push(policy.name);

        if (candidateProviders.length === 1) {
          decision.reason += policyResult.reason + ' ';
          break;
        }
      }
    }

    if (candidateProviders.length === 0) {
      // Fallback to any available provider
      candidateProviders = availableProviders;
      decision.reason += 'Fallback to available providers. ';
    }

    // Select final provider using load balancing
    const selectedProvider = await this.applyLoadBalancing(
      candidateProviders,
      task,
      this.routingPolicies[0]?.loadBalancing || LoadBalancingStrategy.WEIGHTED_RANDOM
    );

    decision.selectedProvider = selectedProvider;
    decision.confidence = this.calculateDecisionConfidence(selectedProvider, task);
    decision.estimatedCost = this.estimateProviderCost(selectedProvider, task);
    decision.estimatedResponseTime = this.estimateProviderResponseTime(selectedProvider, task);

    if (!decision.reason) {
      decision.reason = `Selected via ${this.routingPolicies[0]?.loadBalancing || 'default'} load balancing`;
    }

    return decision;
  }

  /**
   * Apply individual routing policy
   */
  private async applyPolicy(
    policy: RoutingPolicy,
    task: AgentTask,
    candidates: string[]
  ): Promise<{ providers: string[]; reason: string }> {
    let filteredProviders = candidates;
    let reason = '';

    // Check task type preferences
    const taskPreferences = policy.taskTypePreferences[task.type];
    if (taskPreferences) {
      const preferredProviders = taskPreferences
        .filter((pref) => this.evaluateConditions(pref.conditions || [], task))
        .map((pref) => pref.provider)
        .filter((provider) => candidates.includes(provider));

      if (preferredProviders.length > 0) {
        filteredProviders = preferredProviders;
        reason += `Task type ${task.type} preferences. `;
      }
    }

    // Apply cost optimization
    if (policy.costOptimization.enabled) {
      const costFilteredProviders = filteredProviders.filter((provider) => {
        const estimatedCost = this.estimateProviderCost(provider, task);
        return estimatedCost <= policy.costOptimization.maxCostPerRequest;
      });

      if (costFilteredProviders.length > 0) {
        filteredProviders = costFilteredProviders;
        reason += 'Cost optimization. ';
      }
    }

    // Apply performance requirements
    const performanceFilteredProviders = filteredProviders.filter((provider) => {
      const estimatedTime = this.estimateProviderResponseTime(provider, task);
      return estimatedTime <= policy.performanceRequirements.maxResponseTime;
    });

    if (performanceFilteredProviders.length > 0) {
      filteredProviders = performanceFilteredProviders;
      reason += 'Performance requirements. ';
    }

    return { providers: filteredProviders, reason };
  }

  /**
   * Apply load balancing strategy
   */
  private async applyLoadBalancing(
    providers: string[],
    task: AgentTask,
    strategy: LoadBalancingStrategy
  ): Promise<string> {
    if (providers.length === 1) {
      return providers[0];
    }

    switch (strategy) {
      case LoadBalancingStrategy.ROUND_ROBIN:
        return this.roundRobinSelection(providers);

      case LoadBalancingStrategy.WEIGHTED_RANDOM:
        return this.weightedRandomSelection(providers, task);

      case LoadBalancingStrategy.LEAST_CONNECTIONS:
        return this.leastConnectionsSelection(providers);

      case LoadBalancingStrategy.RESPONSE_TIME:
        return this.responseTimeSelection(providers);

      case LoadBalancingStrategy.COST_OPTIMIZED:
        return this.costOptimizedSelection(providers, task);

      case LoadBalancingStrategy.CAPABILITY_MATCH:
        return this.capabilityMatchSelection(providers, task);

      default:
        return providers[0];
    }
  }

  /**
   * Round robin load balancing
   */
  private roundRobinSelection(providers: string[]): string {
    const key = providers.sort().join(',');
    const counter = this.roundRobinCounters.get(key) || 0;
    const selected = providers[counter % providers.length];
    this.roundRobinCounters.set(key, counter + 1);
    return selected;
  }

  /**
   * Weighted random selection based on performance
   */
  private weightedRandomSelection(providers: string[], task: AgentTask): string {
    const weights = providers.map((provider) => {
      const stats = this.providerStats.get(provider);
      if (!stats || stats.totalRequests === 0) return 1;

      const successRate = stats.successfulRequests / stats.totalRequests;
      const responseTimeWeight = Math.max(0.1, 1 - stats.avgResponseTime / 10000); // Normalize around 10s
      const confidenceWeight = stats.avgConfidence || 0.5;

      return successRate * 0.4 + responseTimeWeight * 0.3 + confidenceWeight * 0.3;
    });

    const totalWeight = weights.reduce((sum, weight) => sum + weight, 0);
    const random = Math.random() * totalWeight;

    let weightSum = 0;
    for (let i = 0; i < providers.length; i++) {
      weightSum += weights[i];
      if (random <= weightSum) {
        return providers[i];
      }
    }

    return providers[providers.length - 1];
  }

  /**
   * Select provider with least active connections
   */
  private leastConnectionsSelection(providers: string[]): string {
    return providers.reduce((least, current) => {
      const leastStats = this.providerStats.get(least);
      const currentStats = this.providerStats.get(current);

      const leastConnections = leastStats?.activeConnections || 0;
      const currentConnections = currentStats?.activeConnections || 0;

      return currentConnections < leastConnections ? current : least;
    });
  }

  /**
   * Select provider with best average response time
   */
  private responseTimeSelection(providers: string[]): string {
    return providers.reduce((fastest, current) => {
      const fastestStats = this.providerStats.get(fastest);
      const currentStats = this.providerStats.get(current);

      const fastestTime = fastestStats?.avgResponseTime || Infinity;
      const currentTime = currentStats?.avgResponseTime || Infinity;

      return currentTime < fastestTime ? current : fastest;
    });
  }

  /**
   * Select most cost-effective provider
   */
  private costOptimizedSelection(providers: string[], task: AgentTask): string {
    return providers.reduce((cheapest, current) => {
      const cheapestCost = this.estimateProviderCost(cheapest, task);
      const currentCost = this.estimateProviderCost(current, task);

      return currentCost < cheapestCost ? current : cheapest;
    });
  }

  /**
   * Select provider with best capability match
   */
  private capabilityMatchSelection(providers: string[], task: AgentTask): string {
    // For now, just return the first provider
    // In a full implementation, this would match capabilities to task requirements
    return providers[0];
  }

  /**
   * Evaluate provider conditions
   */
  private evaluateConditions(conditions: ProviderCondition[], task: AgentTask): boolean {
    return conditions.every((condition) => {
      let taskValue: any;

      switch (condition.type) {
        case 'content_length':
          taskValue = task.input.content?.length || 0;
          break;
        case 'task_priority':
          taskValue = task.config.priority || 5;
          break;
        case 'time_constraint':
          taskValue = task.config.timeout || 30000;
          break;
        default:
          return true;
      }

      switch (condition.operator) {
        case 'lt':
          return taskValue < condition.value;
        case 'lte':
          return taskValue <= condition.value;
        case 'gt':
          return taskValue > condition.value;
        case 'gte':
          return taskValue >= condition.value;
        case 'eq':
          return taskValue === condition.value;
        case 'contains':
          return String(taskValue).includes(String(condition.value));
        case 'in':
          return Array.isArray(condition.value) && condition.value.includes(taskValue);
        default:
          return true;
      }
    });
  }

  /**
   * Check if provider is enabled via feature flags
   */
  private isProviderEnabled(providerName: string): boolean {
    switch (providerName) {
      case 'null':
      case 'NullProvider':
        return flags.isNullProviderEnabled();
      case 'claude':
      case 'ClaudeProvider':
        return flags.isLLMProviderEnabled();
      case 'ollama':
      case 'OllamaProvider':
        return agentRuntimeFlags.getValue('OLLAMA_PROVIDER_ENABLED', {}) || false;
      default:
        return true;
    }
  }

  /**
   * Initialize default routing policies
   */
  private initializeDefaultPolicies(): void {
    const defaultPolicy: RoutingPolicy = {
      name: 'default',
      priority: 1,
      taskTypePreferences: {
        [AgentTaskType.SENTIMENT_ANALYSIS]: [
          { provider: 'claude', weight: 0.8 },
          { provider: 'ollama', weight: 0.6 },
          { provider: 'null', weight: 0.2 },
        ],
        [AgentTaskType.ENTITY_EXTRACTION]: [
          { provider: 'claude', weight: 0.9 },
          { provider: 'ollama', weight: 0.7 },
          { provider: 'null', weight: 0.2 },
        ],
        [AgentTaskType.CONTENT_GENERATION]: [
          { provider: 'ollama', weight: 0.8 },
          { provider: 'claude', weight: 0.7 },
          { provider: 'null', weight: 0.1 },
        ],
        [AgentTaskType.TREND_DETECTION]: [
          { provider: 'claude', weight: 0.8 },
          { provider: 'ollama', weight: 0.6 },
          { provider: 'null', weight: 0.3 },
        ],
        [AgentTaskType.CONTENT_ANALYSIS]: [
          { provider: 'claude', weight: 0.8 },
          { provider: 'ollama', weight: 0.7 },
          { provider: 'null', weight: 0.3 },
        ],
        [AgentTaskType.CONTENT_SYNTHESIS]: [
          { provider: 'claude', weight: 0.7 },
          { provider: 'ollama', weight: 0.8 },
          { provider: 'null', weight: 0.2 },
        ],
        [AgentTaskType.DATA_PROCESSING]: [
          { provider: 'claude', weight: 0.6 },
          { provider: 'ollama', weight: 0.7 },
          { provider: 'null', weight: 0.4 },
        ],
      },
      defaultPreferences: [
        { provider: 'claude', weight: 0.7 },
        { provider: 'ollama', weight: 0.6 },
        { provider: 'null', weight: 0.3 },
      ],
      loadBalancing: LoadBalancingStrategy.WEIGHTED_RANDOM,
      failover: {
        enabled: true,
        maxRetries: 3,
        retryDelay: 1000,
        circuitBreaker: {
          failureThreshold: 5,
          successThreshold: 3,
          timeout: 60000,
          windowSize: 100,
        },
        fallbackProviders: ['ollama', 'null'],
      },
      costOptimization: {
        enabled: true,
        maxCostPerRequest: 1.0,
        preferFreeProviders: true,
        costTrackingWindow: 24,
      },
      performanceRequirements: {
        maxResponseTime: 60000,
        minConfidence: 0.5,
        preferFastProviders: false,
      },
    };

    this.addPolicy(defaultPolicy);
  }

  /**
   * Initialize provider statistics
   */
  private initializeProviderStats(name: string): void {
    this.providerStats.set(name, {
      totalRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      avgResponseTime: 0,
      avgCost: 0,
      avgConfidence: 0,
      lastSuccess: 0,
      lastFailure: 0,
      circuitBreakerState: 'closed',
      activeConnections: 0,
    });
  }

  /**
   * Update provider statistics
   */
  private updateProviderStats(provider: string, event: string, value?: number): void {
    const stats = this.providerStats.get(provider);
    if (!stats) return;

    const now = Date.now();

    switch (event) {
      case 'route_selected':
      case 'execution_start':
        stats.totalRequests++;
        stats.activeConnections++;
        break;

      case 'execution_success':
        stats.successfulRequests++;
        stats.activeConnections--;
        stats.lastSuccess = now;

        if (value !== undefined) {
          // Update average response time
          const totalTime = stats.avgResponseTime * (stats.successfulRequests - 1) + value;
          stats.avgResponseTime = totalTime / stats.successfulRequests;
        }

        // Update circuit breaker state
        this.updateCircuitBreaker(provider, true);
        break;

      case 'execution_failure':
        stats.failedRequests++;
        stats.activeConnections--;
        stats.lastFailure = now;

        // Update circuit breaker state
        this.updateCircuitBreaker(provider, false);
        break;
    }
  }

  /**
   * Update circuit breaker state
   */
  private updateCircuitBreaker(provider: string, success: boolean): void {
    const stats = this.providerStats.get(provider);
    if (!stats) return;

    const policy = this.routingPolicies[0]; // Use default policy for circuit breaker config
    if (!policy?.failover.circuitBreaker) return;

    const cb = policy.failover.circuitBreaker;
    const recentRequests = Math.min(stats.totalRequests, cb.windowSize);
    const failureRate = recentRequests > 0 ? stats.failedRequests / recentRequests : 0;

    switch (stats.circuitBreakerState) {
      case 'closed':
        if (failureRate >= cb.failureThreshold / cb.windowSize) {
          stats.circuitBreakerState = 'open';
          setTimeout(() => {
            if (this.providerStats.get(provider)?.circuitBreakerState === 'open') {
              const currentStats = this.providerStats.get(provider);
              if (currentStats) {
                currentStats.circuitBreakerState = 'half-open';
              }
            }
          }, cb.timeout);
        }
        break;

      case 'half-open':
        if (success) {
          // Count consecutive successes in half-open state
          const consecutiveSuccesses = this.getConsecutiveSuccesses(provider);
          if (consecutiveSuccesses >= cb.successThreshold) {
            stats.circuitBreakerState = 'closed';
          }
        } else {
          stats.circuitBreakerState = 'open';
          setTimeout(() => {
            if (this.providerStats.get(provider)?.circuitBreakerState === 'open') {
              const currentStats = this.providerStats.get(provider);
              if (currentStats) {
                currentStats.circuitBreakerState = 'half-open';
              }
            }
          }, cb.timeout);
        }
        break;
    }
  }

  /**
   * Get consecutive successes for circuit breaker
   */
  private getConsecutiveSuccesses(provider: string): number {
    // This is a simplified implementation
    // In a production system, you'd track individual request outcomes
    const stats = this.providerStats.get(provider);
    return stats ? Math.min(stats.successfulRequests, 3) : 0;
  }

  /**
   * Record cost for cost tracking
   */
  private recordCost(provider: string, cost: number): void {
    if (!this.costTracker.has(provider)) {
      this.costTracker.set(provider, []);
    }

    const costs = this.costTracker.get(provider)!;
    costs.push({ timestamp: Date.now(), cost });

    // Clean old entries (keep only last 24 hours)
    const cutoff = Date.now() - 24 * 60 * 60 * 1000;
    this.costTracker.set(
      provider,
      costs.filter((entry) => entry.timestamp > cutoff)
    );
  }

  /**
   * Estimate provider cost for task
   */
  private estimateProviderCost(provider: string, task: AgentTask): number {
    const contentLength =
      task.input.content?.length || JSON.stringify(task.input.data || {}).length;
    const estimatedTokens = Math.ceil(contentLength / 4);

    switch (provider) {
      case 'claude':
      case 'ClaudeProvider':
        // Rough estimate: $0.00001 per token for Claude
        return estimatedTokens * 0.00001;

      case 'ollama':
      case 'OllamaProvider':
        // Local model - essentially free
        return 0;

      case 'null':
      case 'NullProvider':
        // Test provider - free
        return 0;

      default:
        return 0.001; // Default small cost
    }
  }

  /**
   * Estimate provider response time
   */
  private estimateProviderResponseTime(provider: string, task: AgentTask): number {
    const stats = this.providerStats.get(provider);
    if (stats && stats.avgResponseTime > 0) {
      return stats.avgResponseTime;
    }

    // Default estimates
    switch (provider) {
      case 'null':
      case 'NullProvider':
        return 100; // Very fast

      case 'ollama':
      case 'OllamaProvider':
        return 5000; // Local processing

      case 'claude':
      case 'ClaudeProvider':
        return 3000; // API call

      default:
        return 10000; // Conservative default
    }
  }

  /**
   * Calculate decision confidence
   */
  private calculateDecisionConfidence(provider: string, task: AgentTask): number {
    const stats = this.providerStats.get(provider);
    if (!stats || stats.totalRequests === 0) {
      return 0.5; // Neutral confidence for new providers
    }

    const successRate = stats.successfulRequests / stats.totalRequests;
    const recencyBonus = stats.lastSuccess > Date.now() - 3600000 ? 0.1 : 0; // Recent success bonus
    const circuitPenalty = stats.circuitBreakerState !== 'closed' ? -0.2 : 0;

    return Math.max(0.1, Math.min(1.0, successRate + recencyBonus + circuitPenalty));
  }

  /**
   * Get maximum retry attempts for a task
   */
  private getMaxRetryAttempts(task: AgentTask): number {
    const priority = task.config.priority || 5;
    const defaultRetries = this.routingPolicies[0]?.failover.maxRetries || 3;

    // Higher priority tasks get more retries
    if (priority >= 8) return defaultRetries + 2;
    if (priority >= 6) return defaultRetries + 1;
    return defaultRetries;
  }

  /**
   * Check if error should trigger retry
   */
  private shouldRetry(error: any, attempt: number): boolean {
    const message = error instanceof Error ? error.message : String(error);

    // Don't retry validation errors
    if (message.includes('INVALID_INPUT') || message.includes('validation')) {
      return false;
    }

    // Always retry timeouts and network errors
    if (
      message.includes('timeout') ||
      message.includes('network') ||
      message.includes('connection')
    ) {
      return true;
    }

    // Retry rate limits with exponential backoff
    if (message.includes('rate') || message.includes('quota')) {
      return attempt <= 2;
    }

    return true;
  }

  /**
   * Calculate retry delay with exponential backoff
   */
  private calculateRetryDelay(attempt: number): number {
    const baseDelay = this.routingPolicies[0]?.failover.retryDelay || 1000;
    return Math.min(baseDelay * Math.pow(2, attempt - 1), 10000);
  }

  /**
   * Start periodic cleanup of old statistics
   */
  private startStatsCleanup(): void {
    setInterval(
      () => {
        const cutoff = Date.now() - 24 * 60 * 60 * 1000; // 24 hours

        // Clean cost tracking data
        for (const [provider, costs] of this.costTracker) {
          this.costTracker.set(
            provider,
            costs.filter((entry) => entry.timestamp > cutoff)
          );
        }
      },
      60 * 60 * 1000
    ); // Run every hour
  }
}
