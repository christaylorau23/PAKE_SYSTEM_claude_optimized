/**
 * Circuit Breaker Pattern Implementation
 * Prevents cascade failures by monitoring service health and temporarily blocking requests to failing services
 */

import { Request, Response, NextFunction } from 'express';
import { Logger } from '../utils/logger';

export enum CircuitState {
  CLOSED = 'CLOSED', // Normal operation
  OPEN = 'OPEN', // Circuit is open, requests are blocked
  HALF_OPEN = 'HALF_OPEN', // Testing if service has recovered
}

export interface CircuitBreakerConfig {
  failureThreshold: number; // Number of failures before opening circuit
  timeout: number; // Time in ms before attempting to close circuit
  retryInterval: number; // Time in ms between retry attempts
  successThreshold: number; // Number of successes needed to close circuit
  serviceName: string; // Name of the service being protected
}

export interface CircuitBreakerMetrics {
  state: CircuitState;
  failureCount: number;
  successCount: number;
  lastFailureTime: number;
  lastSuccessTime: number;
  totalRequests: number;
  totalFailures: number;
  totalSuccesses: number;
}

export class CircuitBreaker {
  private config: CircuitBreakerConfig;
  private state: CircuitState = CircuitState.CLOSED;
  private failureCount: number = 0;
  private successCount: number = 0;
  private lastFailureTime: number = 0;
  private lastSuccessTime: number = 0;
  private totalRequests: number = 0;
  private totalFailures: number = 0;
  private totalSuccesses: number = 0;
  private logger: Logger;
  private timeoutId: NodeJS.Timeout | null = null;

  constructor(config: CircuitBreakerConfig) {
    this.config = config;
    this.logger = new Logger(`CircuitBreaker-${config.serviceName}`);

    this.logger.info('Circuit breaker initialized', {
      service: config.serviceName,
      failureThreshold: config.failureThreshold,
      timeout: config.timeout,
    });
  }

  /**
   * Execute a function with circuit breaker protection
   */
  public async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (this.state === CircuitState.OPEN) {
      throw new Error(
        `Circuit breaker is OPEN for service ${this.config.serviceName}`
      );
    }

    this.totalRequests++;

    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  /**
   * Express middleware for circuit breaker
   */
  public middleware(req: Request, res: Response, next: NextFunction): void {
    if (this.state === CircuitState.OPEN) {
      this.logger.warn('Circuit breaker is OPEN, blocking request', {
        service: this.config.serviceName,
        url: req.url,
        method: req.method,
      });

      return res.status(503).json({
        error: 'Service temporarily unavailable',
        service: this.config.serviceName,
        retryAfter: this.getRetryAfter(),
      });
    }

    // Add circuit breaker info to request
    req.circuitBreaker = {
      service: this.config.serviceName,
      state: this.state,
      failureCount: this.failureCount,
    };

    next();
  }

  /**
   * Handle successful request
   */
  private onSuccess(): void {
    this.totalSuccesses++;
    this.successCount++;
    this.lastSuccessTime = Date.now();

    if (this.state === CircuitState.HALF_OPEN) {
      if (this.successCount >= this.config.successThreshold) {
        this.closeCircuit();
      }
    } else if (this.state === CircuitState.CLOSED) {
      // Reset failure count on success
      this.failureCount = 0;
    }

    this.logger.debug('Circuit breaker success', {
      service: this.config.serviceName,
      state: this.state,
      successCount: this.successCount,
      failureCount: this.failureCount,
    });
  }

  /**
   * Handle failed request
   */
  private onFailure(): void {
    this.totalFailures++;
    this.failureCount++;
    this.lastFailureTime = Date.now();

    if (this.state === CircuitState.CLOSED) {
      if (this.failureCount >= this.config.failureThreshold) {
        this.openCircuit();
      }
    } else if (this.state === CircuitState.HALF_OPEN) {
      // If we're testing and it fails, go back to open
      this.openCircuit();
    }

    this.logger.warn('Circuit breaker failure', {
      service: this.config.serviceName,
      state: this.state,
      failureCount: this.failureCount,
      totalFailures: this.totalFailures,
    });
  }

  /**
   * Open the circuit breaker
   */
  private openCircuit(): void {
    this.state = CircuitState.OPEN;
    this.successCount = 0;

    // Set timeout to attempt to close circuit
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
    }

    this.timeoutId = setTimeout(() => {
      this.halfOpenCircuit();
    }, this.config.timeout);

    this.logger.warn('Circuit breaker opened', {
      service: this.config.serviceName,
      failureCount: this.failureCount,
      timeout: this.config.timeout,
    });
  }

  /**
   * Close the circuit breaker
   */
  private closeCircuit(): void {
    this.state = CircuitState.CLOSED;
    this.failureCount = 0;
    this.successCount = 0;

    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
      this.timeoutId = null;
    }

    this.logger.info('Circuit breaker closed', {
      service: this.config.serviceName,
    });
  }

  /**
   * Set circuit breaker to half-open state for testing
   */
  private halfOpenCircuit(): void {
    this.state = CircuitState.HALF_OPEN;
    this.successCount = 0;

    this.logger.info('Circuit breaker half-opened', {
      service: this.config.serviceName,
    });
  }

  /**
   * Get metrics for the circuit breaker
   */
  public getMetrics(): CircuitBreakerMetrics {
    return {
      state: this.state,
      failureCount: this.failureCount,
      successCount: this.successCount,
      lastFailureTime: this.lastFailureTime,
      lastSuccessTime: this.lastSuccessTime,
      totalRequests: this.totalRequests,
      totalFailures: this.totalFailures,
      totalSuccesses: this.totalSuccesses,
    };
  }

  /**
   * Get current state
   */
  public getState(): CircuitState {
    return this.state;
  }

  /**
   * Get retry after time in seconds
   */
  private getRetryAfter(): number {
    const timeSinceFailure = Date.now() - this.lastFailureTime;
    const remainingTime = this.config.timeout - timeSinceFailure;
    return Math.max(0, Math.ceil(remainingTime / 1000));
  }

  /**
   * Reset circuit breaker to initial state
   */
  public reset(): void {
    this.state = CircuitState.CLOSED;
    this.failureCount = 0;
    this.successCount = 0;
    this.lastFailureTime = 0;
    this.lastSuccessTime = 0;

    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
      this.timeoutId = null;
    }

    this.logger.info('Circuit breaker reset', {
      service: this.config.serviceName,
    });
  }

  /**
   * Check if circuit breaker is healthy
   */
  public isHealthy(): boolean {
    return this.state === CircuitState.CLOSED;
  }

  /**
   * Get health status
   */
  public getHealthStatus(): {
    healthy: boolean;
    state: CircuitState;
    metrics: CircuitBreakerMetrics;
  } {
    return {
      healthy: this.isHealthy(),
      state: this.state,
      metrics: this.getMetrics(),
    };
  }
}

/**
 * Circuit Breaker Manager for managing multiple circuit breakers
 */
export class CircuitBreakerManager {
  private circuitBreakers: Map<string, CircuitBreaker> = new Map();
  private logger: Logger;

  constructor() {
    this.logger = new Logger('CircuitBreakerManager');
  }

  /**
   * Create a new circuit breaker
   */
  public createCircuitBreaker(config: CircuitBreakerConfig): CircuitBreaker {
    const circuitBreaker = new CircuitBreaker(config);
    this.circuitBreakers.set(config.serviceName, circuitBreaker);

    this.logger.info('Circuit breaker created', {
      service: config.serviceName,
    });

    return circuitBreaker;
  }

  /**
   * Get circuit breaker by service name
   */
  public getCircuitBreaker(serviceName: string): CircuitBreaker | undefined {
    return this.circuitBreakers.get(serviceName);
  }

  /**
   * Get all circuit breaker metrics
   */
  public getAllMetrics(): Record<string, CircuitBreakerMetrics> {
    const metrics: Record<string, CircuitBreakerMetrics> = {};

    for (const [serviceName, circuitBreaker] of this.circuitBreakers) {
      metrics[serviceName] = circuitBreaker.getMetrics();
    }

    return metrics;
  }

  /**
   * Get health status of all circuit breakers
   */
  public getHealthStatus(): Record<string, unknown> {
    const status: Record<string, unknown> = {};

    for (const [serviceName, circuitBreaker] of this.circuitBreakers) {
      status[serviceName] = circuitBreaker.getHealthStatus();
    }

    return status;
  }

  /**
   * Reset all circuit breakers
   */
  public resetAll(): void {
    for (const circuitBreaker of this.circuitBreakers.values()) {
      circuitBreaker.reset();
    }

    this.logger.info('All circuit breakers reset');
  }
}
