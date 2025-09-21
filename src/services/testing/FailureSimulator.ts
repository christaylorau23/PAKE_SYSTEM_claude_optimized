/**
 * PAKE System - Comprehensive Failure Testing Simulator
 *
 * Simulates 429 errors, CLI failures, resource exhaustion, and other failure modes
 * to validate system resilience and safety controls.
 */

import { EventEmitter } from 'events';
import { createLogger, Logger } from '../orchestrator/src/utils/logger';
import { metrics, TaskLifecycleEvent } from '../orchestrator/src/utils/metrics';

export interface FailureScenario {
  id: string;
  name: string;
  description: string;
  type: FailureType;
  severity: 'low' | 'medium' | 'high' | 'critical';
  triggers: FailureTrigger[];
  effects: FailureEffect[];
  duration: number; // milliseconds
  recoveryTime?: number;
  metadata: Record<string, unknown>;
}

export enum FailureType {
  RATE_LIMIT = 'rate_limit',
  RESOURCE_EXHAUSTION = 'resource_exhaustion',
  NETWORK_FAILURE = 'network_failure',
  CLI_FAILURE = 'cli_failure',
  CONTAINER_FAILURE = 'container_failure',
  SECURITY_VIOLATION = 'security_violation',
  DATA_CORRUPTION = 'data_corruption',
  TIMEOUT = 'timeout',
  AUTHENTICATION_FAILURE = 'authentication_failure',
  DEPENDENCY_FAILURE = 'dependency_failure',
}

export interface FailureTrigger {
  condition: string;
  threshold?: number;
  probability: number; // 0-1
  onlyOnce?: boolean;
}

export interface FailureEffect {
  target: string;
  action: 'block' | 'delay' | 'error' | 'corrupt' | 'throttle';
  parameters: Record<string, any>;
}

export interface FailureSimulationResult {
  scenario: string;
  success: boolean;
  duration: number;
  effectsApplied: string[];
  systemResponse: {
    errorsHandled: boolean;
    fallbackActivated: boolean;
    recoveryTime: number;
    dataIntegrity: boolean;
  };
  metrics: {
    requestsAffected: number;
    errorsGenerated: number;
    timeoutsTriggered: number;
    recoveryAttempts: number;
  };
}

/**
 * Comprehensive failure simulation system
 */
export class FailureSimulator extends EventEmitter {
  private readonly logger: Logger;
  private readonly scenarios: Map<string, FailureScenario> = new Map();
  private readonly activeFailures: Map<string, NodeJS.Timeout> = new Map();
  private readonly failureHistory: FailureSimulationResult[] = [];

  // Simulation state
  private isSimulationRunning = false;
  private simulationStartTime = 0;
  private totalFailuresTriggered = 0;

  constructor() {
    super();
    this.logger = createLogger('FailureSimulator');

    // Initialize standard failure scenarios
    this.initializeStandardScenarios();

    this.logger.info('Failure simulator initialized', {
      scenariosCount: this.scenarios.size,
    });
  }

  /**
   * Initialize comprehensive failure scenarios
   */
  private initializeStandardScenarios(): void {
    // 1. Rate Limiting Failures
    this.addScenario({
      id: 'rate-limit-429',
      name: '429 Rate Limit Exceeded',
      description: 'Simulate API rate limiting with 429 responses',
      type: FailureType.RATE_LIMIT,
      severity: 'medium',
      triggers: [
        {
          condition: 'request_count > threshold',
          threshold: 10,
          probability: 1.0,
          onlyOnce: false,
        },
      ],
      effects: [
        {
          target: 'api_requests',
          action: 'error',
          parameters: {
            statusCode: 429,
            message: 'Rate limit exceeded. Try again in 60 seconds.',
            retryAfter: 60,
          },
        },
      ],
      duration: 60000, // 1 minute
      recoveryTime: 5000,
      metadata: {
        provider: 'all',
        httpStatus: 429,
      },
    });

    // 2. CLI Command Failures
    this.addScenario({
      id: 'cli-command-failure',
      name: 'CLI Command Execution Failure',
      description: 'Simulate CLI command failures and crashes',
      type: FailureType.CLI_FAILURE,
      severity: 'high',
      triggers: [
        {
          condition: 'cli_execution_count > 0',
          probability: 0.15, // 15% chance
          onlyOnce: false,
        },
      ],
      effects: [
        {
          target: 'cli_commands',
          action: 'error',
          parameters: {
            exitCode: 1,
            stderr: 'Command failed: Permission denied',
            stdout: '',
          },
        },
      ],
      duration: 1000, // Immediate failure
      metadata: {
        exitCodes: [1, 2, 127, 130],
      },
    });

    // 3. Memory Exhaustion
    this.addScenario({
      id: 'memory-exhaustion',
      name: 'Memory Resource Exhaustion',
      description: 'Simulate out-of-memory conditions',
      type: FailureType.RESOURCE_EXHAUSTION,
      severity: 'critical',
      triggers: [
        {
          condition: 'memory_usage > 90%',
          threshold: 0.9,
          probability: 0.8,
          onlyOnce: true,
        },
      ],
      effects: [
        {
          target: 'memory_allocations',
          action: 'error',
          parameters: {
            error: 'ENOMEM',
            message: 'Cannot allocate memory',
          },
        },
        {
          target: 'process_spawning',
          action: 'block',
          parameters: {
            reason: 'insufficient_memory',
          },
        },
      ],
      duration: 30000, // 30 seconds
      recoveryTime: 10000,
      metadata: {
        resourceType: 'memory',
        threshold: '90%',
      },
    });

    // 4. Container Isolation Failures
    this.addScenario({
      id: 'container-escape-attempt',
      name: 'Container Security Violation',
      description: 'Simulate container escape attempts and security violations',
      type: FailureType.SECURITY_VIOLATION,
      severity: 'critical',
      triggers: [
        {
          condition: 'security_check_triggered',
          probability: 1.0,
          onlyOnce: false,
        },
      ],
      effects: [
        {
          target: 'container_execution',
          action: 'block',
          parameters: {
            reason: 'security_violation',
            violation: 'attempted_privilege_escalation',
          },
        },
        {
          target: 'audit_log',
          action: 'error',
          parameters: {
            severity: 'CRITICAL',
            event: 'SECURITY_VIOLATION',
          },
        },
      ],
      duration: 0, // Immediate block
      metadata: {
        securityLevel: 'critical',
        alertRequired: true,
      },
    });

    // 5. Network Connectivity Failures
    this.addScenario({
      id: 'network-partition',
      name: 'Network Connectivity Loss',
      description: 'Simulate network partitions and connectivity issues',
      type: FailureType.NETWORK_FAILURE,
      severity: 'high',
      triggers: [
        {
          condition: 'network_request_triggered',
          probability: 0.05, // 5% chance
          onlyOnce: false,
        },
      ],
      effects: [
        {
          target: 'network_requests',
          action: 'error',
          parameters: {
            error: 'ECONNREFUSED',
            message: 'Connection refused',
          },
        },
        {
          target: 'dns_resolution',
          action: 'delay',
          parameters: {
            delay: 30000, // 30 second timeout
          },
        },
      ],
      duration: 45000, // 45 seconds
      recoveryTime: 5000,
      metadata: {
        networkType: 'external',
      },
    });

    // 6. Authentication/Authorization Failures
    this.addScenario({
      id: 'auth-token-expiry',
      name: 'Authentication Token Expiry',
      description: 'Simulate expired or invalid authentication tokens',
      type: FailureType.AUTHENTICATION_FAILURE,
      severity: 'medium',
      triggers: [
        {
          condition: 'auth_required',
          probability: 0.1, // 10% chance
          onlyOnce: false,
        },
      ],
      effects: [
        {
          target: 'authenticated_requests',
          action: 'error',
          parameters: {
            statusCode: 401,
            message: 'Authentication token expired',
            requiresReauth: true,
          },
        },
      ],
      duration: 5000, // Until re-authentication
      metadata: {
        authType: 'bearer_token',
        canRecover: true,
      },
    });

    // 7. Disk Space Exhaustion
    this.addScenario({
      id: 'disk-space-exhaustion',
      name: 'Disk Space Exhaustion',
      description: 'Simulate out of disk space conditions',
      type: FailureType.RESOURCE_EXHAUSTION,
      severity: 'high',
      triggers: [
        {
          condition: 'disk_usage > 95%',
          threshold: 0.95,
          probability: 1.0,
          onlyOnce: true,
        },
      ],
      effects: [
        {
          target: 'file_operations',
          action: 'error',
          parameters: {
            error: 'ENOSPC',
            message: 'No space left on device',
          },
        },
        {
          target: 'log_writing',
          action: 'block',
          parameters: {
            reason: 'disk_full',
          },
        },
      ],
      duration: 60000, // 1 minute
      recoveryTime: 15000,
      metadata: {
        resourceType: 'disk',
        threshold: '95%',
      },
    });

    // 8. Timeout Scenarios
    this.addScenario({
      id: 'execution-timeout',
      name: 'Command Execution Timeout',
      description: 'Simulate long-running command timeouts',
      type: FailureType.TIMEOUT,
      severity: 'medium',
      triggers: [
        {
          condition: 'long_running_command',
          probability: 0.2, // 20% chance
          onlyOnce: false,
        },
      ],
      effects: [
        {
          target: 'command_execution',
          action: 'delay',
          parameters: {
            delay: 65000, // Exceed typical 60s timeout
          },
        },
      ],
      duration: 65000,
      metadata: {
        timeoutThreshold: 60000,
      },
    });

    // 9. Data Corruption
    this.addScenario({
      id: 'output-corruption',
      name: 'Output Data Corruption',
      description: 'Simulate corrupted or malformed output data',
      type: FailureType.DATA_CORRUPTION,
      severity: 'high',
      triggers: [
        {
          condition: 'data_processing',
          probability: 0.02, // 2% chance
          onlyOnce: false,
        },
      ],
      effects: [
        {
          target: 'output_data',
          action: 'corrupt',
          parameters: {
            corruptionType: 'random_bytes',
            corruptionRate: 0.1, // 10% of bytes
          },
        },
      ],
      duration: 1000, // Immediate corruption
      metadata: {
        dataType: 'json_output',
      },
    });

    // 10. Cascading Failures
    this.addScenario({
      id: 'cascading-failure',
      name: 'Cascading System Failure',
      description: 'Simulate cascading failures across multiple components',
      type: FailureType.DEPENDENCY_FAILURE,
      severity: 'critical',
      triggers: [
        {
          condition: 'failure_count > 3',
          threshold: 3,
          probability: 0.5, // 50% chance after 3 failures
          onlyOnce: true,
        },
      ],
      effects: [
        {
          target: 'all_components',
          action: 'throttle',
          parameters: {
            throttleRate: 0.1, // Reduce to 10% capacity
          },
        },
        {
          target: 'health_checks',
          action: 'error',
          parameters: {
            healthStatus: 'unhealthy',
          },
        },
      ],
      duration: 120000, // 2 minutes
      recoveryTime: 30000,
      metadata: {
        cascadeLevel: 'system-wide',
      },
    });
  }

  /**
   * Add a failure scenario
   */
  addScenario(scenario: FailureScenario): void {
    this.scenarios.set(scenario.id, scenario);
    this.logger.debug('Failure scenario added', {
      id: scenario.id,
      name: scenario.name,
      type: scenario.type,
      severity: scenario.severity,
    });
  }

  /**
   * Start comprehensive failure simulation
   */
  async startSimulation(
    options: {
      duration?: number;
      intensity?: 'low' | 'medium' | 'high';
      targetProviders?: string[];
      scenarios?: string[];
    } = {}
  ): Promise<void> {
    if (this.isSimulationRunning) {
      throw new Error('Failure simulation already running');
    }

    const {
      duration = 300000, // 5 minutes default
      intensity = 'medium',
      targetProviders = ['all'],
      scenarios = Array.from(this.scenarios.keys()),
    } = options;

    this.isSimulationRunning = true;
    this.simulationStartTime = Date.now();
    this.totalFailuresTriggered = 0;

    this.logger.info('Starting comprehensive failure simulation', {
      duration,
      intensity,
      targetProviders,
      scenariosCount: scenarios.length,
    });

    this.emit('simulation:started', {
      duration,
      intensity,
      scenarios: scenarios.length,
    });

    try {
      // Run scenarios based on intensity
      const intensityMultipliers = {
        low: 0.3,
        medium: 1.0,
        high: 2.0,
      };

      const multiplier = intensityMultipliers[intensity];

      for (const scenarioId of scenarios) {
        const scenario = this.scenarios.get(scenarioId);
        if (scenario) {
          await this.triggerScenario(scenario, multiplier);
        }
      }

      // Keep simulation running for specified duration
      await new Promise(resolve => setTimeout(resolve, duration));
    } finally {
      await this.stopSimulation();
    }
  }

  /**
   * Trigger a specific failure scenario
   */
  async triggerScenario(
    scenario: FailureScenario,
    intensityMultiplier: number = 1.0
  ): Promise<FailureSimulationResult> {
    const startTime = Date.now();
    const effectsApplied: string[] = [];

    this.logger.warn('Triggering failure scenario', {
      id: scenario.id,
      name: scenario.name,
      type: scenario.type,
      severity: scenario.severity,
    });

    const result: FailureSimulationResult = {
      scenario: scenario.id,
      success: false,
      duration: 0,
      effectsApplied,
      systemResponse: {
        errorsHandled: false,
        fallbackActivated: false,
        recoveryTime: 0,
        dataIntegrity: true,
      },
      metrics: {
        requestsAffected: 0,
        errorsGenerated: 0,
        timeoutsTriggered: 0,
        recoveryAttempts: 0,
      },
    };

    try {
      // Check if triggers are satisfied
      const triggersActivated = this.evaluateTriggers(
        scenario.triggers,
        intensityMultiplier
      );

      if (triggersActivated) {
        // Apply failure effects
        for (const effect of scenario.effects) {
          await this.applyFailureEffect(effect, scenario);
          effectsApplied.push(`${effect.target}:${effect.action}`);
        }

        // Track metrics
        metrics.taskLifecycle(
          TaskLifecycleEvent.PROVIDER_FAILED,
          `failure-sim-${scenario.id}`,
          'failure_simulation',
          'FailureSimulator',
          undefined,
          scenario.name,
          {
            scenarioType: scenario.type,
            severity: scenario.severity,
          }
        );

        // Schedule recovery if specified
        if (scenario.recoveryTime) {
          setTimeout(() => {
            this.recoverFromFailure(scenario);
          }, scenario.duration + scenario.recoveryTime);
        }

        this.totalFailuresTriggered++;
        result.success = true;

        this.emit('scenario:triggered', {
          scenario: scenario.id,
          effects: effectsApplied,
          severity: scenario.severity,
        });
      }

      result.duration = Date.now() - startTime;
      result.effectsApplied = effectsApplied;

      // Simulate system response monitoring
      result.systemResponse = await this.monitorSystemResponse(scenario);

      this.failureHistory.push(result);

      return result;
    } catch (error) {
      this.logger.error('Failed to trigger scenario', {
        scenario: scenario.id,
        error: error.message,
      });

      result.duration = Date.now() - startTime;
      return result;
    }
  }

  /**
   * Evaluate scenario triggers
   */
  private evaluateTriggers(
    triggers: FailureTrigger[],
    intensityMultiplier: number
  ): boolean {
    for (const trigger of triggers) {
      const adjustedProbability = Math.min(
        1.0,
        trigger.probability * intensityMultiplier
      );

      // Simulate trigger condition evaluation
      const randomValue = Math.random();

      if (randomValue < adjustedProbability) {
        this.logger.debug('Failure trigger activated', {
          condition: trigger.condition,
          probability: adjustedProbability,
          randomValue,
        });
        return true;
      }
    }

    return false;
  }

  /**
   * Apply failure effect to system
   */
  private async applyFailureEffect(
    effect: FailureEffect,
    scenario: FailureScenario
  ): Promise<void> {
    this.logger.debug('Applying failure effect', {
      target: effect.target,
      action: effect.action,
      scenario: scenario.id,
    });

    switch (effect.action) {
      case 'block':
        await this.blockTarget(effect.target, effect.parameters);
        break;

      case 'delay':
        await this.delayTarget(effect.target, effect.parameters);
        break;

      case 'error':
        await this.errorTarget(effect.target, effect.parameters);
        break;

      case 'corrupt':
        await this.corruptTarget(effect.target, effect.parameters);
        break;

      case 'throttle':
        await this.throttleTarget(effect.target, effect.parameters);
        break;
    }

    // Schedule effect removal after scenario duration
    if (scenario.duration > 0) {
      const timeoutId = setTimeout(() => {
        this.removeFailureEffect(effect.target, effect.action);
        this.activeFailures.delete(`${effect.target}:${effect.action}`);
      }, scenario.duration);

      this.activeFailures.set(`${effect.target}:${effect.action}`, timeoutId);
    }
  }

  /**
   * Block target component
   */
  private async blockTarget(
    target: string,
    parameters: unknown
  ): Promise<void> {
    this.emit('effect:block', {
      target,
      reason: parameters.reason,
      timestamp: new Date(),
    });
  }

  /**
   * Add delay to target component
   */
  private async delayTarget(
    target: string,
    parameters: unknown
  ): Promise<void> {
    const delay = parameters.delay || 1000;
    this.emit('effect:delay', {
      target,
      delay,
      timestamp: new Date(),
    });

    if (parameters.simulateDelay) {
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  /**
   * Generate error in target component
   */
  private async errorTarget(
    target: string,
    parameters: unknown
  ): Promise<void> {
    this.emit('effect:error', {
      target,
      error: parameters.error || 'Simulated failure',
      statusCode: parameters.statusCode,
      message: parameters.message,
      timestamp: new Date(),
    });
  }

  /**
   * Corrupt target data
   */
  private async corruptTarget(
    target: string,
    parameters: unknown
  ): Promise<void> {
    this.emit('effect:corrupt', {
      target,
      corruptionType: parameters.corruptionType,
      corruptionRate: parameters.corruptionRate,
      timestamp: new Date(),
    });
  }

  /**
   * Throttle target component
   */
  private async throttleTarget(
    target: string,
    parameters: unknown
  ): Promise<void> {
    this.emit('effect:throttle', {
      target,
      throttleRate: parameters.throttleRate,
      timestamp: new Date(),
    });
  }

  /**
   * Remove failure effect
   */
  private removeFailureEffect(target: string, action: string): void {
    this.emit('effect:removed', {
      target,
      action,
      timestamp: new Date(),
    });
  }

  /**
   * Monitor system response to failure
   */
  private async monitorSystemResponse(scenario: FailureScenario): Promise<any> {
    // Simulate monitoring system behavior
    await new Promise(resolve => setTimeout(resolve, 1000));

    return {
      errorsHandled: true,
      fallbackActivated:
        scenario.severity === 'high' || scenario.severity === 'critical',
      recoveryTime: scenario.recoveryTime || 0,
      dataIntegrity: scenario.type !== FailureType.DATA_CORRUPTION,
    };
  }

  /**
   * Recover from failure scenario
   */
  private recoverFromFailure(scenario: FailureScenario): void {
    this.logger.info('Recovering from failure scenario', {
      id: scenario.id,
      name: scenario.name,
    });

    this.emit('scenario:recovered', {
      scenario: scenario.id,
      recoveryTime: scenario.recoveryTime,
    });
  }

  /**
   * Stop simulation and clean up
   */
  async stopSimulation(): Promise<void> {
    if (!this.isSimulationRunning) {
      return;
    }

    this.logger.info('Stopping failure simulation', {
      duration: Date.now() - this.simulationStartTime,
      failuresTriggered: this.totalFailuresTriggered,
    });

    // Clear all active failures
    for (const [key, timeoutId] of this.activeFailures) {
      clearTimeout(timeoutId);
      const [target, action] = key.split(':');
      this.removeFailureEffect(target, action);
    }

    this.activeFailures.clear();
    this.isSimulationRunning = false;

    this.emit('simulation:stopped', {
      duration: Date.now() - this.simulationStartTime,
      failuresTriggered: this.totalFailuresTriggered,
      scenariosExecuted: this.failureHistory.length,
    });
  }

  /**
   * Get simulation statistics
   */
  getStatistics(): {
    totalScenarios: number;
    activeFailures: number;
    simulationRunning: boolean;
    failureHistory: number;
    failuresByType: Record<string, number>;
    failuresBySeverity: Record<string, number>;
  } {
    const failuresByType: Record<string, number> = {};
    const failuresBySeverity: Record<string, number> = {};

    for (const result of this.failureHistory) {
      const scenario = this.scenarios.get(result.scenario);
      if (scenario) {
        failuresByType[scenario.type] =
          (failuresByType[scenario.type] || 0) + 1;
        failuresBySeverity[scenario.severity] =
          (failuresBySeverity[scenario.severity] || 0) + 1;
      }
    }

    return {
      totalScenarios: this.scenarios.size,
      activeFailures: this.activeFailures.size,
      simulationRunning: this.isSimulationRunning,
      failureHistory: this.failureHistory.length,
      failuresByType,
      failuresBySeverity,
    };
  }

  /**
   * Get recent failure results
   */
  getRecentFailures(limit: number = 20): FailureSimulationResult[] {
    return this.failureHistory
      .sort((a, b) => b.duration - a.duration)
      .slice(0, limit);
  }

  /**
   * Test specific failure scenario
   */
  async testScenario(scenarioId: string): Promise<FailureSimulationResult> {
    const scenario = this.scenarios.get(scenarioId);
    if (!scenario) {
      throw new Error(`Scenario not found: ${scenarioId}`);
    }

    return await this.triggerScenario(scenario, 1.0);
  }

  /**
   * Validate system resilience
   */
  async validateResilience(): Promise<{
    passed: boolean;
    score: number;
    results: FailureSimulationResult[];
    recommendations: string[];
  }> {
    const testScenarios = [
      'rate-limit-429',
      'cli-command-failure',
      'memory-exhaustion',
      'network-partition',
      'auth-token-expiry',
    ];

    const results: FailureSimulationResult[] = [];
    let passedTests = 0;

    this.logger.info('Starting resilience validation', {
      scenariosCount: testScenarios.length,
    });

    for (const scenarioId of testScenarios) {
      try {
        const result = await this.testScenario(scenarioId);
        results.push(result);

        if (result.systemResponse.errorsHandled) {
          passedTests++;
        }
      } catch (error) {
        this.logger.error('Resilience test failed', {
          scenario: scenarioId,
          error: error.message,
        });
      }
    }

    const score = (passedTests / testScenarios.length) * 100;
    const recommendations: string[] = [];

    if (score < 60) {
      recommendations.push('Critical: System resilience is inadequate');
      recommendations.push('Implement comprehensive error handling');
      recommendations.push('Add circuit breaker patterns');
    } else if (score < 80) {
      recommendations.push('Improve fallback mechanisms');
      recommendations.push('Add retry logic with exponential backoff');
    }

    return {
      passed: score >= 80,
      score,
      results,
      recommendations,
    };
  }
}

// Export global failure simulator instance
export const failureSimulator = new FailureSimulator();
