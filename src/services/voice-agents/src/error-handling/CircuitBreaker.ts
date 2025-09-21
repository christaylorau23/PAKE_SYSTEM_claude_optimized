/**
 * PAKE System - Circuit Breaker Pattern Implementation
 * Advanced error handling with automatic failover and recovery detection
 */

import { EventEmitter } from 'events';
import { Logger } from '../utils/Logger';

export interface CircuitBreakerConfig {
  failureThreshold: number; // Number of failures before opening circuit
  timeout: number; // Timeout for service calls in milliseconds
  resetTimeout: number; // Time to wait before attempting recovery
  name: string; // Circuit breaker identifier
  monitoringWindow?: number; // Time window for failure counting (default: 60000ms)
  halfOpenMaxCalls?: number; // Max calls to test in half-open state (default: 3)
  successThreshold?: number; // Successes needed to close circuit (default: 2)
}

export enum CircuitBreakerState {
  CLOSED = 'CLOSED', // Normal operation
  OPEN = 'OPEN', // Service unavailable, failing fast
  HALF_OPEN = 'HALF_OPEN', // Testing service recovery
}

export interface CircuitBreakerMetrics {
  totalRequests: number;
  successfulRequests: number;
  failedRequests: number;
  timeouts: number;
  circuitOpenings: number;
  lastFailureTime?: Date;
  lastSuccessTime?: Date;
  currentState: CircuitBreakerState;
  uptime: number;
}

export class CircuitBreaker extends EventEmitter {
  private state: CircuitBreakerState = CircuitBreakerState.CLOSED;
  private failureCount = 0;
  private successCount = 0;
  private lastFailureTime?: Date;
  private lastSuccessTime?: Date;
  private nextAttempt?: Date;
  private halfOpenCallCount = 0;
  private metrics: CircuitBreakerMetrics;
  private logger: Logger;
  private monitoringInterval?: NodeJS.Timeout;
  private failureWindow: Array<{ timestamp: Date; error: string }> = [];

  constructor(private config: CircuitBreakerConfig) {
    super();
    this.logger = new Logger(`CircuitBreaker:${config.name}`);

    this.metrics = {
      totalRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      timeouts: 0,
      circuitOpenings: 0,
      currentState: this.state,
      uptime: Date.now(),
    };

    // Start monitoring
    this.startMonitoring();

    this.logger.info(`Circuit breaker initialized`, {
      name: config.name,
      failureThreshold: config.failureThreshold,
      timeout: config.timeout,
      resetTimeout: config.resetTimeout,
    });
  }

  /**
   * Execute a function with circuit breaker protection
   */
  async execute<T>(fn: () => Promise<T>): Promise<T> {
    this.metrics.totalRequests++;

    // Fast fail if circuit is open
    if (this.state === CircuitBreakerState.OPEN) {
      if (this.shouldAttemptReset()) {
        this.transitionToHalfOpen();
      } else {
        this.metrics.failedRequests++;
        const error = new Error(`Circuit breaker is OPEN for ${this.config.name}`);
        error.name = 'CircuitBreakerOpenError';
        throw error;
      }
    }

    // Limit concurrent calls in half-open state
    if (this.state === CircuitBreakerState.HALF_OPEN) {
      if (this.halfOpenCallCount >= (this.config.halfOpenMaxCalls || 3)) {
        this.metrics.failedRequests++;
        const error = new Error(
          `Circuit breaker HALF_OPEN call limit exceeded for ${this.config.name}`
        );
        error.name = 'CircuitBreakerHalfOpenLimitError';
        throw error;
      }
      this.halfOpenCallCount++;
    }

    try {
      // Execute with timeout
      const result = await this.executeWithTimeout(fn);

      // Record success
      this.onSuccess();
      return result;
    } catch (error) {
      // Record failure
      this.onFailure(error);
      throw error;
    }
  }

  /**
   * Execute function with timeout protection
   */
  private async executeWithTimeout<T>(fn: () => Promise<T>): Promise<T> {
    return new Promise<T>(async (resolve, reject) => {
      const timeoutId = setTimeout(() => {
        this.metrics.timeouts++;
        const error = new Error(
          `Circuit breaker timeout (${this.config.timeout}ms) for ${this.config.name}`
        );
        error.name = 'CircuitBreakerTimeoutError';
        reject(error);
      }, this.config.timeout);

      try {
        const result = await fn();
        clearTimeout(timeoutId);
        resolve(result);
      } catch (error) {
        clearTimeout(timeoutId);
        reject(error);
      }
    });
  }

  /**
   * Handle successful execution
   */
  private onSuccess(): void {
    this.metrics.successfulRequests++;
    this.lastSuccessTime = new Date();
    this.failureCount = 0;

    // Clear old failures from monitoring window
    this.cleanupFailureWindow();

    if (this.state === CircuitBreakerState.HALF_OPEN) {
      this.successCount++;

      if (this.successCount >= (this.config.successThreshold || 2)) {
        this.transitionToClosed();
      }
    }

    this.emit('success', {
      name: this.config.name,
      state: this.state,
      timestamp: this.lastSuccessTime,
    });
  }

  /**
   * Handle failed execution
   */
  private onFailure(error: any): void {
    this.metrics.failedRequests++;
    this.lastFailureTime = new Date();
    this.failureCount++;
    this.successCount = 0; // Reset success count on any failure

    // Add to failure window for monitoring
    this.failureWindow.push({
      timestamp: this.lastFailureTime,
      error: error.message || 'Unknown error',
    });

    // Clean up old failures
    this.cleanupFailureWindow();

    this.logger.warn(`Circuit breaker recorded failure`, {
      name: this.config.name,
      failureCount: this.failureCount,
      error: error.message,
      currentState: this.state,
    });

    // Check if we should open the circuit
    if (this.state === CircuitBreakerState.CLOSED) {
      if (this.shouldOpenCircuit()) {
        this.transitionToOpen();
      }
    } else if (this.state === CircuitBreakerState.HALF_OPEN) {
      // Any failure in half-open immediately returns to open
      this.transitionToOpen();
    }

    this.emit('failure', {
      name: this.config.name,
      state: this.state,
      error: error.message,
      failureCount: this.failureCount,
      timestamp: this.lastFailureTime,
    });
  }

  /**
   * Check if circuit should be opened
   */
  private shouldOpenCircuit(): boolean {
    // Check failure count within monitoring window
    const windowMs = this.config.monitoringWindow || 60000;
    const cutoffTime = new Date(Date.now() - windowMs);
    const recentFailures = this.failureWindow.filter((f) => f.timestamp > cutoffTime).length;

    return recentFailures >= this.config.failureThreshold;
  }

  /**
   * Check if we should attempt to reset from OPEN to HALF_OPEN
   */
  private shouldAttemptReset(): boolean {
    if (!this.nextAttempt) {
      this.nextAttempt = new Date(Date.now() + this.config.resetTimeout);
      return false;
    }

    return new Date() >= this.nextAttempt;
  }

  /**
   * Transition to OPEN state
   */
  private transitionToOpen(): void {
    this.state = CircuitBreakerState.OPEN;
    this.metrics.circuitOpenings++;
    this.metrics.currentState = this.state;
    this.nextAttempt = new Date(Date.now() + this.config.resetTimeout);
    this.halfOpenCallCount = 0;

    this.logger.warn(`Circuit breaker OPENED`, {
      name: this.config.name,
      failureCount: this.failureCount,
      resetAt: this.nextAttempt,
    });

    this.emit('open', {
      name: this.config.name,
      failureCount: this.failureCount,
      resetTimeout: this.config.resetTimeout,
      nextAttempt: this.nextAttempt,
    });
  }

  /**
   * Transition to HALF_OPEN state
   */
  private transitionToHalfOpen(): void {
    this.state = CircuitBreakerState.HALF_OPEN;
    this.metrics.currentState = this.state;
    this.halfOpenCallCount = 0;
    this.successCount = 0;
    this.nextAttempt = undefined;

    this.logger.info(`Circuit breaker HALF_OPEN`, {
      name: this.config.name,
      maxTestCalls: this.config.halfOpenMaxCalls || 3,
    });

    this.emit('half-open', {
      name: this.config.name,
      maxTestCalls: this.config.halfOpenMaxCalls || 3,
    });
  }

  /**
   * Transition to CLOSED state
   */
  private transitionToClosed(): void {
    this.state = CircuitBreakerState.CLOSED;
    this.metrics.currentState = this.state;
    this.failureCount = 0;
    this.successCount = 0;
    this.halfOpenCallCount = 0;
    this.nextAttempt = undefined;

    this.logger.info(`Circuit breaker CLOSED - service recovered`, {
      name: this.config.name,
    });

    this.emit('closed', {
      name: this.config.name,
      recoveryTime: new Date(),
    });
  }

  /**
   * Clean up old failures from monitoring window
   */
  private cleanupFailureWindow(): void {
    const windowMs = this.config.monitoringWindow || 60000;
    const cutoffTime = new Date(Date.now() - windowMs);
    this.failureWindow = this.failureWindow.filter((f) => f.timestamp > cutoffTime);
  }

  /**
   * Start monitoring and maintenance tasks
   */
  private startMonitoring(): void {
    this.monitoringInterval = setInterval(() => {
      this.cleanupFailureWindow();

      // Emit periodic health check
      this.emit('health-check', {
        name: this.config.name,
        state: this.state,
        metrics: this.getMetrics(),
        timestamp: new Date(),
      });
    }, 30000); // Every 30 seconds
  }

  /**
   * Get current circuit breaker status
   */
  getStatus(): {
    name: string;
    state: CircuitBreakerState;
    failureCount: number;
    lastFailure?: Date;
    lastSuccess?: Date;
    nextAttempt?: Date;
  } {
    return {
      name: this.config.name,
      state: this.state,
      failureCount: this.failureCount,
      lastFailure: this.lastFailureTime,
      lastSuccess: this.lastSuccessTime,
      nextAttempt: this.nextAttempt,
    };
  }

  /**
   * Get comprehensive metrics
   */
  getMetrics(): CircuitBreakerMetrics {
    return {
      ...this.metrics,
      lastFailureTime: this.lastFailureTime,
      lastSuccessTime: this.lastSuccessTime,
      uptime: Date.now() - this.metrics.uptime,
    };
  }

  /**
   * Force circuit state (for testing/emergency)
   */
  forceState(state: CircuitBreakerState): void {
    this.logger.warn(`Force changing circuit breaker state`, {
      name: this.config.name,
      from: this.state,
      to: state,
    });

    const oldState = this.state;
    this.state = state;
    this.metrics.currentState = state;

    if (state === CircuitBreakerState.CLOSED) {
      this.failureCount = 0;
      this.successCount = 0;
      this.halfOpenCallCount = 0;
      this.nextAttempt = undefined;
    }

    this.emit('state-forced', {
      name: this.config.name,
      oldState,
      newState: state,
      timestamp: new Date(),
    });
  }

  /**
   * Reset all metrics and state
   */
  reset(): void {
    this.logger.info(`Resetting circuit breaker`, {
      name: this.config.name,
    });

    this.state = CircuitBreakerState.CLOSED;
    this.failureCount = 0;
    this.successCount = 0;
    this.halfOpenCallCount = 0;
    this.lastFailureTime = undefined;
    this.lastSuccessTime = undefined;
    this.nextAttempt = undefined;
    this.failureWindow = [];

    this.metrics = {
      totalRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      timeouts: 0,
      circuitOpenings: 0,
      currentState: this.state,
      uptime: Date.now(),
    };

    this.emit('reset', {
      name: this.config.name,
      timestamp: new Date(),
    });
  }

  /**
   * Check if circuit breaker is healthy (not failing frequently)
   */
  isHealthy(): boolean {
    const recentFailureRate =
      this.metrics.totalRequests > 0 ? this.failureWindow.length / this.metrics.totalRequests : 0;

    return this.state !== CircuitBreakerState.OPEN && recentFailureRate < 0.5; // Less than 50% failure rate
  }

  /**
   * Cleanup resources
   */
  destroy(): void {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
      this.monitoringInterval = undefined;
    }

    this.removeAllListeners();

    this.logger.info(`Circuit breaker destroyed`, {
      name: this.config.name,
    });
  }
}

export default CircuitBreaker;
