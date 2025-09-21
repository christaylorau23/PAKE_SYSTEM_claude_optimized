import {
  CostControlsConfig,
  TokenBudget,
  BudgetAlert,
  CostMetrics,
  ThrottleStatus,
  CostTrackingConfig,
  BudgetExceededError,
  SecurityContext,
} from '../types/security.types';
import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';
import NodeCache from 'node-cache';
import * as tiktoken from 'tiktoken';

interface UsageRecord {
  timestamp: Date;
  tokens: number;
  cost: number;
  modelType: string;
  requestId: string;
}

interface BudgetPeriod {
  start: Date;
  end: Date;
  budget: number;
  used: number;
  resetScheduled: boolean;
}

export class CostControls extends EventEmitter {
  private config: CostControlsConfig;
  private budgetCache: NodeCache;
  private usageCache: NodeCache;
  private throttleCache: NodeCache;
  private metricsCache: NodeCache;
  private tokenEncoders: Map<string, tiktoken.Tiktoken>;

  // Token counting models and their associated encoders
  private static readonly MODEL_ENCODERS = {
    'gpt-4': 'cl100k_base',
    'gpt-4-32k': 'cl100k_base',
    'gpt-3.5-turbo': 'cl100k_base',
    'gpt-3.5-turbo-16k': 'cl100k_base',
    'claude-3-opus': 'cl100k_base', // Approximation
    'claude-3-sonnet': 'cl100k_base', // Approximation
    'claude-3-haiku': 'cl100k_base', // Approximation
    'text-davinci-003': 'p50k_base',
    'text-davinci-002': 'p50k_base',
    'text-ada-001': 'r50k_base',
    'text-babbage-001': 'r50k_base',
    'text-curie-001': 'r50k_base',
  };

  // Default cost per token for different models (in USD)
  private static readonly DEFAULT_COSTS = {
    'gpt-4': { input: 0.00003, output: 0.00006 },
    'gpt-4-32k': { input: 0.00006, output: 0.00012 },
    'gpt-3.5-turbo': { input: 0.0000015, output: 0.000002 },
    'gpt-3.5-turbo-16k': { input: 0.000003, output: 0.000004 },
    'claude-3-opus': { input: 0.000015, output: 0.000075 },
    'claude-3-sonnet': { input: 0.000003, output: 0.000015 },
    'claude-3-haiku': { input: 0.00000025, output: 0.00000125 },
    'text-davinci-003': { input: 0.00002, output: 0.00002 },
    ollama: { input: 0, output: 0 }, // Local models have no API cost
    'gemini-pro': { input: 0.0000005, output: 0.0000015 },
  };

  constructor(config: CostControlsConfig) {
    super();
    this.config = config;

    // Initialize caches
    this.budgetCache = new NodeCache({ stdTTL: 0 }); // No auto-expiry for budgets
    this.usageCache = new NodeCache({ stdTTL: 86400 }); // 24 hours for usage records
    this.throttleCache = new NodeCache({ stdTTL: 3600 }); // 1 hour for throttle status
    this.metricsCache = new NodeCache({ stdTTL: 300 }); // 5 minutes for metrics

    // Initialize token encoders
    this.tokenEncoders = new Map();
    this.initializeTokenEncoders();

    // Setup periodic budget resets
    this.setupBudgetResetSchedule();

    this.emit('initialized', { config });
  }

  private initializeTokenEncoders(): void {
    try {
      for (const [model, encodingName] of Object.entries(
        CostControls.MODEL_ENCODERS
      )) {
        try {
          const encoder = tiktoken.getEncoding(
            encodingName as tiktoken.TiktokenEncoding
          );
          this.tokenEncoders.set(model, encoder);
        } catch (error) {
          console.warn(`Failed to load encoder for model ${model}:`, error);
        }
      }
      this.emit('encodersInitialized', { count: this.tokenEncoders.size });
    } catch (error) {
      console.error('Failed to initialize token encoders:', error);
    }
  }

  public async checkBudget(
    userId: string,
    estimatedTokens: number,
    modelType: string
  ): Promise<{
    allowed: boolean;
    budget: TokenBudget;
    throttleStatus?: ThrottleStatus;
  }> {
    const budget = await this.getUserBudget(userId);
    const estimatedCost = this.estimateCost(
      estimatedTokens,
      modelType,
      'output'
    );

    // Check if request would exceed budget
    const wouldExceedBudget = budget.used + estimatedTokens > budget.budget;
    const usagePercentage = (budget.used + estimatedTokens) / budget.budget;

    // Check throttle status
    let throttleStatus: ThrottleStatus | undefined;
    if (usagePercentage >= this.config.throttleThreshold) {
      throttleStatus = await this.checkThrottleStatus(userId, usagePercentage);
    }

    // Trigger budget alerts
    await this.checkBudgetAlerts(budget, usagePercentage);

    const result = {
      allowed:
        !wouldExceedBudget && (!throttleStatus || !throttleStatus.isThrottled),
      budget,
      throttleStatus,
    };

    this.emit('budgetChecked', {
      userId,
      estimatedTokens,
      modelType,
      currentUsage: budget.used,
      budgetLimit: budget.budget,
      usagePercentage,
      allowed: result.allowed,
    });

    return result;
  }

  public async recordUsage(
    userId: string,
    inputTokens: number,
    outputTokens: number,
    modelType: string,
    context: SecurityContext
  ): Promise<CostMetrics> {
    const startTime = performance.now();

    try {
      // Calculate costs
      const inputCost = this.estimateCost(inputTokens, modelType, 'input');
      const outputCost = this.estimateCost(outputTokens, modelType, 'output');
      const totalCost = inputCost + outputCost;
      const totalTokens = inputTokens + outputTokens;

      // Update user budget
      const budget = await this.getUserBudget(userId);
      budget.used += totalTokens;

      // Check if budget exceeded after usage
      if (budget.used > budget.budget) {
        const overage = budget.used - budget.budget;
        this.handleBudgetOverage(userId, overage, context);
      }

      await this.updateUserBudget(userId, budget);

      // Record usage metrics
      const metrics: CostMetrics = {
        userId,
        modelType,
        tokensUsed: totalTokens,
        requestCount: 1,
        computeTimeMs: context.endTime
          ? context.endTime.getTime() - context.startTime.getTime()
          : 0,
        estimatedCost: totalCost,
        timestamp: new Date(),
      };

      await this.storeMetrics(metrics);

      // Record detailed usage for analytics
      const usageRecord: UsageRecord = {
        timestamp: new Date(),
        tokens: totalTokens,
        cost: totalCost,
        modelType,
        requestId: context.requestId,
      };

      await this.storeUsageRecord(userId, usageRecord);

      this.emit('usageRecorded', {
        userId,
        inputTokens,
        outputTokens,
        totalCost,
        modelType,
        budgetRemaining: budget.budget - budget.used,
        processingTime: performance.now() - startTime,
      });

      return metrics;
    } catch (error) {
      this.emit('usageRecordingError', { userId, modelType, error });
      throw new Error(
        `Failed to record usage: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    }
  }

  public countTokens(text: string, modelType: string): number {
    try {
      const encoder =
        this.tokenEncoders.get(modelType) ||
        this.tokenEncoders.get('gpt-3.5-turbo'); // Fallback encoder

      if (encoder) {
        return encoder.encode(text).length;
      }

      // Fallback: estimate based on character count (rough approximation)
      return Math.ceil(text.length / 4);
    } catch (error) {
      console.warn(`Token counting failed for model ${modelType}:`, error);
      // Fallback estimation
      return Math.ceil(text.length / 4);
    }
  }

  public estimateCost(
    tokens: number,
    modelType: string,
    type: 'input' | 'output' = 'output'
  ): number {
    const modelCosts =
      this.config.costTracking.costPerToken[modelType] ||
      CostControls.DEFAULT_COSTS[modelType] ||
      CostControls.DEFAULT_COSTS['gpt-3.5-turbo'];

    if (typeof modelCosts === 'object' && modelCosts[type]) {
      return tokens * modelCosts[type];
    }

    // Fallback to simple per-token cost
    const fallbackCost = typeof modelCosts === 'number' ? modelCosts : 0.000002;
    return tokens * fallbackCost;
  }

  private async getUserBudget(userId: string): Promise<TokenBudget> {
    const cached = this.budgetCache.get<TokenBudget>(`budget:${userId}`);
    if (cached && this.isBudgetPeriodValid(cached)) {
      return cached;
    }

    // Create new budget for current period
    const period = this.getCurrentBudgetPeriod();
    const budget: TokenBudget = {
      userId,
      budget: this.config.defaultTokenBudget,
      used: 0,
      remaining: this.config.defaultTokenBudget,
      period: this.config.budgetPeriod,
      periodStart: period.start,
      periodEnd: period.end,
      alerts: this.config.alertThresholds.map(threshold => ({
        threshold,
        triggered: false,
        notified: false,
      })),
    };

    this.budgetCache.set(`budget:${userId}`, budget);
    this.emit('budgetCreated', {
      userId,
      budget: budget.budget,
      period: budget.period,
    });

    return budget;
  }

  private async updateUserBudget(
    userId: string,
    budget: TokenBudget
  ): Promise<void> {
    budget.remaining = Math.max(0, budget.budget - budget.used);
    this.budgetCache.set(`budget:${userId}`, budget);
  }

  private getCurrentBudgetPeriod(): { start: Date; end: Date } {
    const now = new Date();
    let start: Date;
    let end: Date;

    switch (this.config.budgetPeriod) {
      case 'hourly':
        start = new Date(
          now.getFullYear(),
          now.getMonth(),
          now.getDate(),
          now.getHours()
        );
        end = new Date(start.getTime() + 60 * 60 * 1000);
        break;
      case 'daily':
        start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        end = new Date(start.getTime() + 24 * 60 * 60 * 1000);
        break;
      case 'weekly':
        const dayOfWeek = now.getDay();
        start = new Date(
          now.getFullYear(),
          now.getMonth(),
          now.getDate() - dayOfWeek
        );
        end = new Date(start.getTime() + 7 * 24 * 60 * 60 * 1000);
        break;
      case 'monthly':
        start = new Date(now.getFullYear(), now.getMonth(), 1);
        end = new Date(now.getFullYear(), now.getMonth() + 1, 1);
        break;
      default:
        start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        end = new Date(start.getTime() + 24 * 60 * 60 * 1000);
    }

    return { start, end };
  }

  private isBudgetPeriodValid(budget: TokenBudget): boolean {
    const now = new Date();
    return now >= budget.periodStart && now < budget.periodEnd;
  }

  private async checkBudgetAlerts(
    budget: TokenBudget,
    usagePercentage: number
  ): Promise<void> {
    for (const alert of budget.alerts) {
      if (!alert.triggered && usagePercentage >= alert.threshold) {
        alert.triggered = true;
        alert.timestamp = new Date();

        this.emit('budgetAlert', {
          userId: budget.userId,
          threshold: alert.threshold,
          currentUsage: budget.used,
          budgetLimit: budget.budget,
          usagePercentage,
        });

        // Send notification (if configured)
        if (!alert.notified) {
          await this.sendBudgetNotification(
            budget.userId,
            alert,
            usagePercentage
          );
          alert.notified = true;
        }
      }
    }
  }

  private async sendBudgetNotification(
    userId: string,
    alert: BudgetAlert,
    usagePercentage: number
  ): Promise<void> {
    // This would integrate with notification service
    this.emit('budgetNotification', {
      userId,
      threshold: alert.threshold,
      usagePercentage,
      message: `Budget ${(alert.threshold * 100).toFixed(0)}% threshold reached`,
    });
  }

  private async checkThrottleStatus(
    userId: string,
    usagePercentage: number
  ): Promise<ThrottleStatus> {
    const throttleKey = `throttle:${userId}`;
    const cached = this.throttleCache.get<ThrottleStatus>(throttleKey);

    if (cached) {
      return cached;
    }

    const shouldThrottle = usagePercentage >= this.config.throttleThreshold;
    const status: ThrottleStatus = {
      isThrottled: shouldThrottle,
      reason: shouldThrottle
        ? `Usage ${(usagePercentage * 100).toFixed(1)}% exceeds throttle threshold`
        : 'Normal operation',
      retryAfter: shouldThrottle
        ? this.calculateRetryAfter(usagePercentage)
        : undefined,
      currentUsage: usagePercentage,
      limit: this.config.throttleThreshold,
    };

    if (shouldThrottle) {
      this.throttleCache.set(throttleKey, status, 300); // 5 minutes
      this.emit('userThrottled', {
        userId,
        usagePercentage,
        reason: status.reason,
      });
    }

    return status;
  }

  private calculateRetryAfter(usagePercentage: number): number {
    // Calculate retry delay based on how much over the threshold the user is
    const overageRatio =
      (usagePercentage - this.config.throttleThreshold) /
      (1 - this.config.throttleThreshold);
    const baseDelay = 60; // 1 minute base
    const maxDelay = 1800; // 30 minutes max

    return Math.min(baseDelay + overageRatio * baseDelay * 10, maxDelay);
  }

  private handleBudgetOverage(
    userId: string,
    overage: number,
    context: SecurityContext
  ): void {
    const overagePercentage = (overage / this.config.defaultTokenBudget) * 100;

    this.emit('budgetExceeded', {
      userId,
      overage,
      overagePercentage,
      context,
    });

    switch (this.config.overagePolicy) {
      case 'block':
        throw new BudgetExceededError(
          `Token budget exceeded by ${overage} tokens (${overagePercentage.toFixed(1)}%)`,
          context
        );
      case 'throttle':
        // Throttling handled in checkThrottleStatus
        break;
      case 'alert':
        // Alert already sent via budgetExceeded event
        break;
    }
  }

  private async storeMetrics(metrics: CostMetrics): Promise<void> {
    const key = `metrics:${metrics.userId}:${Date.now()}`;
    this.metricsCache.set(key, metrics, 86400); // 24 hours
  }

  private async storeUsageRecord(
    userId: string,
    record: UsageRecord
  ): Promise<void> {
    const userRecords =
      this.usageCache.get<UsageRecord[]>(`usage:${userId}`) || [];
    userRecords.push(record);

    // Keep only recent records (sliding window)
    const cutoffTime = Date.now() - 7 * 24 * 60 * 60 * 1000; // 7 days
    const filteredRecords = userRecords.filter(
      r => r.timestamp.getTime() > cutoffTime
    );

    this.usageCache.set(`usage:${userId}`, filteredRecords);
  }

  private setupBudgetResetSchedule(): void {
    const getNextResetTime = (): number => {
      const now = new Date();
      let nextReset: Date;

      switch (this.config.budgetPeriod) {
        case 'hourly':
          nextReset = new Date(now.getTime() + 60 * 60 * 1000);
          nextReset.setMinutes(0, 0, 0);
          break;
        case 'daily':
          nextReset = new Date(now.getTime() + 24 * 60 * 60 * 1000);
          nextReset.setHours(0, 0, 0, 0);
          break;
        case 'weekly':
          nextReset = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
          nextReset.setHours(0, 0, 0, 0);
          const daysToNextMonday = (7 - nextReset.getDay() + 1) % 7 || 7;
          nextReset.setDate(nextReset.getDate() + daysToNextMonday);
          break;
        case 'monthly':
          nextReset = new Date(now.getFullYear(), now.getMonth() + 1, 1);
          break;
        default:
          nextReset = new Date(now.getTime() + 24 * 60 * 60 * 1000);
      }

      return nextReset.getTime() - now.getTime();
    };

    const scheduleNextReset = () => {
      const timeToNext = getNextResetTime();
      setTimeout(() => {
        this.resetAllBudgets();
        scheduleNextReset(); // Schedule next reset
      }, timeToNext);
    };

    scheduleNextReset();
  }

  private resetAllBudgets(): void {
    const budgetKeys = this.budgetCache
      .keys()
      .filter(key => key.startsWith('budget:'));
    let resetCount = 0;

    for (const key of budgetKeys) {
      const budget = this.budgetCache.get<TokenBudget>(key);
      if (budget) {
        const newPeriod = this.getCurrentBudgetPeriod();
        budget.used = 0;
        budget.remaining = budget.budget;
        budget.periodStart = newPeriod.start;
        budget.periodEnd = newPeriod.end;

        // Reset alert triggers
        budget.alerts.forEach(alert => {
          alert.triggered = false;
          alert.notified = false;
          alert.timestamp = undefined;
        });

        this.budgetCache.set(key, budget);
        resetCount++;
      }
    }

    this.emit('budgetsReset', {
      count: resetCount,
      period: this.config.budgetPeriod,
    });
  }

  // Public API methods

  public async getUserUsageMetrics(
    userId: string,
    days: number = 7
  ): Promise<{
    totalTokens: number;
    totalCost: number;
    requestCount: number;
    dailyBreakdown: Array<{
      date: string;
      tokens: number;
      cost: number;
      requests: number;
    }>;
    modelBreakdown: Array<{
      model: string;
      tokens: number;
      cost: number;
      requests: number;
    }>;
  }> {
    const records = this.usageCache.get<UsageRecord[]>(`usage:${userId}`) || [];
    const cutoffTime = Date.now() - days * 24 * 60 * 60 * 1000;
    const filteredRecords = records.filter(
      r => r.timestamp.getTime() > cutoffTime
    );

    const totalTokens = filteredRecords.reduce((sum, r) => sum + r.tokens, 0);
    const totalCost = filteredRecords.reduce((sum, r) => sum + r.cost, 0);
    const requestCount = filteredRecords.length;

    // Daily breakdown
    const dailyMap = new Map<
      string,
      { tokens: number; cost: number; requests: number }
    >();
    filteredRecords.forEach(record => {
      const date = record.timestamp.toISOString().split('T')[0];
      const existing = dailyMap.get(date) || {
        tokens: 0,
        cost: 0,
        requests: 0,
      };
      existing.tokens += record.tokens;
      existing.cost += record.cost;
      existing.requests++;
      dailyMap.set(date, existing);
    });

    // Model breakdown
    const modelMap = new Map<
      string,
      { tokens: number; cost: number; requests: number }
    >();
    filteredRecords.forEach(record => {
      const existing = modelMap.get(record.modelType) || {
        tokens: 0,
        cost: 0,
        requests: 0,
      };
      existing.tokens += record.tokens;
      existing.cost += record.cost;
      existing.requests++;
      modelMap.set(record.modelType, existing);
    });

    return {
      totalTokens,
      totalCost,
      requestCount,
      dailyBreakdown: Array.from(dailyMap.entries()).map(([date, data]) => ({
        date,
        ...data,
      })),
      modelBreakdown: Array.from(modelMap.entries()).map(([model, data]) => ({
        model,
        ...data,
      })),
    };
  }

  public setBudget(userId: string, budget: number): void {
    const userBudget = this.budgetCache.get<TokenBudget>(`budget:${userId}`);
    if (userBudget) {
      userBudget.budget = budget;
      userBudget.remaining = Math.max(0, budget - userBudget.used);
      this.budgetCache.set(`budget:${userId}`, userBudget);
    }

    this.emit('budgetUpdated', { userId, newBudget: budget });
  }

  public getThrottleStatus(userId: string): ThrottleStatus | null {
    return this.throttleCache.get<ThrottleStatus>(`throttle:${userId}`) || null;
  }

  public clearThrottle(userId: string): void {
    this.throttleCache.del(`throttle:${userId}`);
    this.emit('throttleCleared', { userId });
  }

  public getMetrics() {
    const budgetKeys = this.budgetCache
      .keys()
      .filter(key => key.startsWith('budget:'));
    const usageKeys = this.usageCache
      .keys()
      .filter(key => key.startsWith('usage:'));
    const throttleKeys = this.throttleCache
      .keys()
      .filter(key => key.startsWith('throttle:'));

    return {
      activeBudgets: budgetKeys.length,
      usageRecords: usageKeys.length,
      throttledUsers: throttleKeys.length,
      encodersLoaded: this.tokenEncoders.size,
      config: this.config,
    };
  }

  public updateConfig(newConfig: Partial<CostControlsConfig>): void {
    this.config = { ...this.config, ...newConfig };
    this.emit('configUpdated', this.config);
  }

  public cleanup(): void {
    // Clear all caches
    this.budgetCache.flushAll();
    this.usageCache.flushAll();
    this.throttleCache.flushAll();
    this.metricsCache.flushAll();

    // Free token encoders
    for (const encoder of this.tokenEncoders.values()) {
      encoder.free();
    }
    this.tokenEncoders.clear();

    this.emit('cleanup');
  }
}
