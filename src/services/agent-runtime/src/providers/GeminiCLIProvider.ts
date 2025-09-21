/**
 * PAKE System - Gemini CLI Provider
 *
 * Secure containerized execution of Gemini CLI commands with comprehensive isolation,
 * resource limits, and safety controls.
 */

import { spawn, ChildProcess } from 'child_process';
import { promises as fs, createReadStream } from 'fs';
import { join, resolve, basename } from 'path';
import { createHash, randomBytes } from 'crypto';
import { AgentProvider } from './AgentProvider';
import {
  AgentTask,
  AgentResult,
  AgentResultStatus,
  AgentCapability,
  AgentTaskType,
} from '../types/Agent';
import { sandboxEnforcer } from '../../policy/Sandbox';
import { createLogger, Logger } from '../../../orchestrator/src/utils/logger';
import { metrics, TaskLifecycleEvent } from '../../../orchestrator/src/utils/metrics';
import { FeatureFlags } from '../../config/FeatureFlags';
import Docker from 'dockerode';

export interface GeminiCLIConfig {
  // API Configuration
  apiKey: string;
  project?: string;
  region?: string;
  model?: string;

  // Container Configuration
  containerImage: string;
  maxExecutionTime: number;
  memoryLimitMB: number;
  cpuLimit: number;
  networkMode: 'none' | 'bridge' | 'host';

  // Security Configuration
  sandboxEnabled: boolean;
  allowFileSystem: boolean;
  allowedPaths: string[];
  redactSecrets: boolean;

  // CLI Configuration
  cliPath: string;
  tempDirectory: string;
  logLevel: 'debug' | 'info' | 'warn' | 'error';
}

export interface ContainerExecution {
  containerId: string;
  startTime: number;
  command: string[];
  status: 'starting' | 'running' | 'completed' | 'failed' | 'timeout' | 'killed';
  exitCode?: number;
  stdout: string;
  stderr: string;
  metrics: {
    executionTime: number;
    memoryUsedMB: number;
    cpuUsedPercent: number;
  };
}

/**
 * Docker-based Gemini CLI provider with comprehensive security isolation
 */
export class GeminiCLIProvider implements AgentProvider {
  public readonly name = 'GeminiCLIProvider';
  public readonly version = '1.0.0';
  public readonly capabilities: AgentCapability[] = [
    AgentCapability.TEXT_ANALYSIS,
    AgentCapability.CONTENT_GENERATION,
    AgentCapability.SUMMARIZATION,
    AgentCapability.QUESTION_ANSWERING,
    AgentCapability.CODE_ANALYSIS,
    AgentCapability.MULTIMODAL_ANALYSIS,
  ];

  private readonly config: GeminiCLIConfig;
  private readonly docker: Docker;
  private readonly logger: Logger;
  private readonly featureFlags: FeatureFlags;
  private readonly activeContainers: Map<string, ContainerExecution> = new Map();

  // Security and monitoring
  private executionCount = 0;
  private lastHealthCheck = 0;
  private readonly healthCheckInterval = 30000; // 30 seconds

  constructor(config: Partial<GeminiCLIConfig> = {}, featureFlags?: FeatureFlags) {
    this.config = {
      // Default secure configuration
      apiKey: config.apiKey || process.env.GEMINI_API_KEY || '',
      project: config.project || process.env.GOOGLE_CLOUD_PROJECT,
      region: config.region || 'us-central1',
      model: config.model || 'gemini-pro',

      containerImage: config.containerImage || 'pake-agent-sandbox:latest',
      maxExecutionTime: config.maxExecutionTime || 60000, // 1 minute
      memoryLimitMB: config.memoryLimitMB || 512,
      cpuLimit: config.cpuLimit || 0.5,
      networkMode: config.networkMode || 'none',

      sandboxEnabled: config.sandboxEnabled ?? true,
      allowFileSystem: config.allowFileSystem ?? false,
      allowedPaths: config.allowedPaths || ['/tmp/gemini'],
      redactSecrets: config.redactSecrets ?? true,

      cliPath: config.cliPath || '/usr/local/bin/gemini',
      tempDirectory: config.tempDirectory || '/tmp/pake-gemini',
      logLevel: config.logLevel || 'info',
    };

    this.docker = new Docker();
    this.logger = createLogger('GeminiCLIProvider', { provider: this.name });
    this.featureFlags = featureFlags || new FeatureFlags();

    // Validate configuration
    this.validateConfiguration();

    // Register sandbox policy
    if (this.config.sandboxEnabled) {
      this.registerSandboxPolicy();
    }

    this.logger.info('Gemini CLI Provider initialized', {
      model: this.config.model,
      sandboxEnabled: this.config.sandboxEnabled,
      networkMode: this.config.networkMode,
      memoryLimit: this.config.memoryLimitMB,
    });

    // Cleanup orphaned containers on startup
    this.cleanupOrphanedContainers();
  }

  /**
   * Execute agent task in secure container
   */
  async run(task: AgentTask): Promise<AgentResult> {
    const startTime = Date.now();
    const executionId = this.generateExecutionId();

    this.logger.info('Starting Gemini CLI task execution', {
      taskId: task.id,
      executionId,
      type: task.type,
      contentLength: task.input.content?.length || 0,
    });

    // Track lifecycle
    metrics.taskLifecycle(TaskLifecycleEvent.TASK_STARTED, task.id, task.type, this.name);

    try {
      // Validate task and configuration
      await this.validateTask(task);

      // Check resource constraints
      await this.validateResourceConstraints(task);

      // Create secure execution environment
      const container = await this.createSecureContainer(task, executionId);

      // Execute Gemini CLI in container
      const result = await this.executeInContainer(container, task);

      // Clean up container
      await this.cleanupContainer(container.containerId);

      const executionTime = Date.now() - startTime;

      this.logger.info('Gemini CLI task completed successfully', {
        taskId: task.id,
        executionId,
        executionTime,
        outputSize: JSON.stringify(result.output).length,
      });

      metrics.taskLifecycle(
        TaskLifecycleEvent.TASK_COMPLETED,
        task.id,
        task.type,
        this.name,
        executionTime
      );

      return {
        taskId: task.id,
        status: AgentResultStatus.SUCCESS,
        output: result.output,
        metadata: {
          provider: this.name,
          executionId,
          executionTimeMs: executionTime,
          model: this.config.model,
          containerMetrics: result.metrics,
          securityLevel: this.config.sandboxEnabled ? 'sandboxed' : 'standard',
        },
      };
    } catch (error) {
      const executionTime = Date.now() - startTime;

      this.logger.error('Gemini CLI task execution failed', {
        taskId: task.id,
        executionId,
        error: error.message,
        executionTime,
      });

      metrics.taskLifecycle(
        TaskLifecycleEvent.TASK_FAILED,
        task.id,
        task.type,
        this.name,
        executionTime,
        error.message
      );

      return {
        taskId: task.id,
        status: AgentResultStatus.ERROR,
        output: { error: this.sanitizeError(error.message) },
        metadata: {
          provider: this.name,
          executionId,
          executionTimeMs: executionTime,
          error: this.sanitizeError(error.message),
        },
      };
    }
  }

  /**
   * Create secure container for task execution
   */
  private async createSecureContainer(
    task: AgentTask,
    executionId: string
  ): Promise<ContainerExecution> {
    const containerName = `pake-gemini-${executionId}`;

    // Create temporary directory for task files
    const taskTempDir = join(this.config.tempDirectory, executionId);
    await fs.mkdir(taskTempDir, { recursive: true, mode: 0o700 });

    // Prepare input files
    await this.prepareTaskFiles(task, taskTempDir);

    // Container configuration with security hardening
    const containerConfig = {
      Image: this.config.containerImage,
      name: containerName,
      Cmd: await this.buildGeminiCommand(task, executionId),
      Env: this.buildSecureEnvironment(task),

      // Resource limits
      HostConfig: {
        Memory: this.config.memoryLimitMB * 1024 * 1024, // Convert MB to bytes
        CpuQuota: Math.floor(this.config.cpuLimit * 100000), // CPU limit as quota
        CpuPeriod: 100000,
        PidsLimit: 32, // Limit process count

        // Security settings
        ReadonlyRootfs: true,
        SecurityOpt: ['no-new-privileges:true', 'seccomp:/app/security/seccomp-profile.json'],
        CapDrop: ['ALL'], // Drop all capabilities
        NetworkMode: this.config.networkMode,

        // Filesystem isolation
        Binds: this.buildVolumeMounts(taskTempDir),
        Tmpfs: {
          '/tmp': 'noexec,nosuid,size=100m',
          '/var/tmp': 'noexec,nosuid,size=50m',
        },
      },

      // Working directory
      WorkingDir: '/app/sandbox',

      // User context (non-root)
      User: '1001:1001',
    };

    this.logger.debug('Creating secure container', {
      name: containerName,
      image: this.config.containerImage,
      memoryLimit: this.config.memoryLimitMB,
      cpuLimit: this.config.cpuLimit,
      networkMode: this.config.networkMode,
    });

    const container = await this.docker.createContainer(containerConfig);

    const execution: ContainerExecution = {
      containerId: container.id,
      startTime: Date.now(),
      command: containerConfig.Cmd || [],
      status: 'starting',
      stdout: '',
      stderr: '',
      metrics: {
        executionTime: 0,
        memoryUsedMB: 0,
        cpuUsedPercent: 0,
      },
    };

    this.activeContainers.set(container.id, execution);
    return execution;
  }

  /**
   * Execute task in container with comprehensive monitoring
   */
  private async executeInContainer(
    containerExec: ContainerExecution,
    task: AgentTask
  ): Promise<{ output: any; metrics: any }> {
    const container = this.docker.getContainer(containerExec.containerId);

    return new Promise(async (resolve, reject) => {
      let timeoutHandle: NodeJS.Timeout;
      let resolved = false;

      const cleanup = () => {
        if (timeoutHandle) clearTimeout(timeoutHandle);
        if (!resolved) {
          resolved = true;
          containerExec.status = 'killed';
          this.killContainer(containerExec.containerId);
        }
      };

      try {
        // Start container
        await container.start();
        containerExec.status = 'running';

        this.logger.debug('Container started', {
          containerId: containerExec.containerId,
          taskId: task.id,
        });

        // Set timeout
        timeoutHandle = setTimeout(() => {
          if (!resolved) {
            resolved = true;
            containerExec.status = 'timeout';
            this.logger.warn('Container execution timeout', {
              containerId: containerExec.containerId,
              taskId: task.id,
              timeout: this.config.maxExecutionTime,
            });
            cleanup();
            reject(new Error(`Execution timeout after ${this.config.maxExecutionTime}ms`));
          }
        }, this.config.maxExecutionTime);

        // Monitor container execution
        const monitoringPromise = this.monitorContainerExecution(containerExec);

        // Wait for container to complete
        const waitResult = await container.wait();

        if (!resolved) {
          resolved = true;
          clearTimeout(timeoutHandle);

          containerExec.status = waitResult.StatusCode === 0 ? 'completed' : 'failed';
          containerExec.exitCode = waitResult.StatusCode;

          // Get execution logs
          const logs = await container.logs({
            stdout: true,
            stderr: true,
            timestamps: true,
          });

          const logString = logs.toString('utf8');
          const { stdout, stderr } = this.parseLogs(logString);

          containerExec.stdout = stdout;
          containerExec.stderr = stderr;

          // Finalize metrics
          containerExec.metrics = await monitoringPromise;
          containerExec.metrics.executionTime = Date.now() - containerExec.startTime;

          if (waitResult.StatusCode !== 0) {
            this.logger.error('Container execution failed', {
              containerId: containerExec.containerId,
              taskId: task.id,
              exitCode: waitResult.StatusCode,
              stderr: this.sanitizeOutput(stderr),
            });

            reject(
              new Error(
                `Container execution failed with exit code ${waitResult.StatusCode}: ${stderr}`
              )
            );
            return;
          }

          // Parse and validate output
          const output = await this.parseGeminiOutput(stdout, task);

          this.logger.debug('Container execution completed', {
            containerId: containerExec.containerId,
            taskId: task.id,
            executionTime: containerExec.metrics.executionTime,
            memoryUsed: containerExec.metrics.memoryUsedMB,
          });

          resolve({
            output,
            metrics: containerExec.metrics,
          });
        }
      } catch (error) {
        cleanup();
        if (!resolved) {
          resolved = true;
          this.logger.error('Container execution error', {
            containerId: containerExec.containerId,
            taskId: task.id,
            error: error.message,
          });
          reject(error);
        }
      }
    });
  }

  /**
   * Build Gemini CLI command for the specific task
   */
  private async buildGeminiCommand(task: AgentTask, executionId: string): Promise<string[]> {
    const command = [
      this.config.cliPath,
      '--project',
      this.config.project || 'default',
      '--region',
      this.config.region,
      '--model',
      this.config.model,
      '--format',
      'json',
      '--log-level',
      this.config.logLevel,
    ];

    // Add task-specific parameters
    switch (task.type) {
      case AgentTaskType.TEXT_ANALYSIS:
        command.push('analyze-text');
        command.push('--input', `/app/sandbox/input-${executionId}.txt`);
        break;

      case AgentTaskType.CONTENT_GENERATION:
        command.push('generate-content');
        command.push('--prompt', `/app/sandbox/prompt-${executionId}.txt`);
        if (task.config.temperature) {
          command.push('--temperature', task.config.temperature.toString());
        }
        if (task.config.maxTokens) {
          command.push('--max-tokens', task.config.maxTokens.toString());
        }
        break;

      case AgentTaskType.SUMMARIZATION:
        command.push('summarize');
        command.push('--input', `/app/sandbox/input-${executionId}.txt`);
        command.push('--style', task.config.summaryStyle || 'bullet-points');
        break;

      case AgentTaskType.QUESTION_ANSWERING:
        command.push('answer-question');
        command.push('--context', `/app/sandbox/context-${executionId}.txt`);
        command.push('--question', `/app/sandbox/question-${executionId}.txt`);
        break;

      case AgentTaskType.CODE_ANALYSIS:
        command.push('analyze-code');
        command.push('--code', `/app/sandbox/code-${executionId}.txt`);
        command.push('--language', task.input.language || 'auto');
        break;

      default:
        throw new Error(`Unsupported task type: ${task.type}`);
    }

    // Add output file
    command.push('--output', `/app/sandbox/output-${executionId}.json`);

    return command;
  }

  /**
   * Prepare task input files in secure directory
   */
  private async prepareTaskFiles(task: AgentTask, tempDir: string): Promise<void> {
    const executionId = basename(tempDir);

    // Main input content
    if (task.input.content) {
      await fs.writeFile(join(tempDir, `input-${executionId}.txt`), task.input.content, {
        mode: 0o600,
      });
    }

    // Task-specific files
    switch (task.type) {
      case AgentTaskType.CONTENT_GENERATION:
        if (task.input.prompt) {
          await fs.writeFile(join(tempDir, `prompt-${executionId}.txt`), task.input.prompt, {
            mode: 0o600,
          });
        }
        break;

      case AgentTaskType.QUESTION_ANSWERING:
        if (task.input.context) {
          await fs.writeFile(join(tempDir, `context-${executionId}.txt`), task.input.context, {
            mode: 0o600,
          });
        }
        if (task.input.question) {
          await fs.writeFile(join(tempDir, `question-${executionId}.txt`), task.input.question, {
            mode: 0o600,
          });
        }
        break;

      case AgentTaskType.CODE_ANALYSIS:
        if (task.input.code) {
          await fs.writeFile(join(tempDir, `code-${executionId}.txt`), task.input.code, {
            mode: 0o600,
          });
        }
        break;
    }

    this.logger.debug('Task files prepared', {
      tempDir,
      executionId,
      taskType: task.type,
    });
  }

  /**
   * Build secure environment variables for container
   */
  private buildSecureEnvironment(task: AgentTask): string[] {
    const env = [
      'NODE_ENV=sandbox',
      'PYTHONPATH=/app',
      'PATH=/usr/local/bin:/usr/bin:/bin',
      'HOME=/app',
      'TMPDIR=/tmp',
      `GEMINI_MODEL=${this.config.model}`,
      `LOG_LEVEL=${this.config.logLevel}`,
      'REDACT_SECRETS=true',
    ];

    // Add API key (will be redacted in logs)
    if (this.config.apiKey) {
      env.push(`GEMINI_API_KEY=${this.config.apiKey}`);
    }

    // Add project configuration
    if (this.config.project) {
      env.push(`GOOGLE_CLOUD_PROJECT=${this.config.project}`);
    }

    return env;
  }

  /**
   * Build volume mounts for container
   */
  private buildVolumeMounts(taskTempDir: string): string[] {
    const mounts = [
      `${taskTempDir}:/app/sandbox:rw`, // Task-specific data
      '/app/logs:/app/logs:rw', // Logging directory
    ];

    // Add additional allowed paths if configured
    if (this.config.allowFileSystem) {
      for (const allowedPath of this.config.allowedPaths) {
        mounts.push(`${allowedPath}:${allowedPath}:ro`); // Read-only access
      }
    }

    return mounts;
  }

  /**
   * Monitor container resource usage during execution
   */
  private async monitorContainerExecution(
    containerExec: ContainerExecution
  ): Promise<{ executionTime: number; memoryUsedMB: number; cpuUsedPercent: number }> {
    const container = this.docker.getContainer(containerExec.containerId);
    let maxMemoryMB = 0;
    let avgCpuPercent = 0;
    let sampleCount = 0;

    const monitorInterval = setInterval(async () => {
      try {
        if (containerExec.status === 'running') {
          const stats = await container.stats({ stream: false });

          // Memory usage
          const memoryUsageMB = (stats.memory_stats.usage || 0) / (1024 * 1024);
          maxMemoryMB = Math.max(maxMemoryMB, memoryUsageMB);

          // CPU usage calculation
          const cpuDelta =
            (stats.cpu_stats.cpu_usage?.total_usage || 0) -
            (stats.precpu_stats.cpu_usage?.total_usage || 0);
          const systemDelta =
            (stats.cpu_stats.system_cpu_usage || 0) - (stats.precpu_stats.system_cpu_usage || 0);

          let cpuPercent = 0;
          if (systemDelta > 0) {
            cpuPercent = (cpuDelta / systemDelta) * 100;
          }

          avgCpuPercent = (avgCpuPercent * sampleCount + cpuPercent) / (sampleCount + 1);
          sampleCount++;

          // Check resource violations
          if (this.config.sandboxEnabled) {
            const resourceCheck = sandboxEnforcer.validateResourceUsage(
              this.name,
              'container-' + containerExec.containerId.slice(0, 8),
              {
                memoryMB: memoryUsageMB,
                processCount: stats.pids_stats?.current,
              }
            );

            if (!resourceCheck.allowed) {
              this.logger.warn('Container resource violation detected', {
                containerId: containerExec.containerId,
                violations: resourceCheck.violations,
              });
            }
          }
        }
      } catch (error) {
        // Ignore monitoring errors - don't fail the main execution
        this.logger.debug('Container monitoring error', {
          containerId: containerExec.containerId,
          error: error.message,
        });
      }
    }, 2000); // Monitor every 2 seconds

    // Wait for container to complete or timeout
    while (containerExec.status === 'running' || containerExec.status === 'starting') {
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }

    clearInterval(monitorInterval);

    return {
      executionTime: Date.now() - containerExec.startTime,
      memoryUsedMB: maxMemoryMB,
      cpuUsedPercent: avgCpuPercent,
    };
  }

  /**
   * Parse Gemini CLI output and validate format
   */
  private async parseGeminiOutput(stdout: string, task: AgentTask): Promise<any> {
    try {
      // Extract JSON output from logs
      const jsonMatch = stdout.match(/\{.*\}/s);
      if (!jsonMatch) {
        throw new Error('No valid JSON output found in Gemini CLI response');
      }

      const rawOutput = JSON.parse(jsonMatch[0]);

      // Sanitize output for security
      const sanitizedOutput = this.sanitizeOutput(rawOutput);

      // Validate output structure based on task type
      return this.validateTaskOutput(sanitizedOutput, task);
    } catch (error) {
      this.logger.error('Failed to parse Gemini output', {
        error: error.message,
        stdout: this.sanitizeOutput(stdout.slice(0, 500)), // First 500 chars for debugging
      });
      throw new Error('Failed to parse Gemini CLI output');
    }
  }

  /**
   * Validate task output structure
   */
  private validateTaskOutput(output: any, task: AgentTask): any {
    switch (task.type) {
      case AgentTaskType.TEXT_ANALYSIS:
        if (!output.analysis) {
          throw new Error('Missing analysis field in Gemini output');
        }
        return {
          analysis: output.analysis,
          confidence: output.confidence || 0.5,
          metadata: output.metadata || {},
        };

      case AgentTaskType.CONTENT_GENERATION:
        if (!output.generated_content && !output.content) {
          throw new Error('Missing content field in Gemini output');
        }
        return {
          content: output.generated_content || output.content,
          metadata: output.metadata || {},
        };

      case AgentTaskType.SUMMARIZATION:
        if (!output.summary) {
          throw new Error('Missing summary field in Gemini output');
        }
        return {
          summary: output.summary,
          key_points: output.key_points || [],
          metadata: output.metadata || {},
        };

      default:
        return output;
    }
  }

  /**
   * Sanitize output by redacting sensitive information
   */
  private sanitizeOutput(output: any): any {
    if (!this.config.redactSecrets) {
      return output;
    }

    const sanitizedString = JSON.stringify(output)
      // API keys
      .replace(
        /([a-zA-Z0-9_-]*[kK]ey[a-zA-Z0-9_-]*["']?\s*[:=]\s*["']?)([a-zA-Z0-9+/]{20,}["']?)/g,
        '$1[REDACTED]'
      )
      // Tokens
      .replace(
        /([a-zA-Z0-9_-]*[tT]oken[a-zA-Z0-9_-]*["']?\s*[:=]\s*["']?)([a-zA-Z0-9+/]{20,}["']?)/g,
        '$1[REDACTED]'
      )
      // Email addresses
      .replace(/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g, '[REDACTED_EMAIL]')
      // Phone numbers
      .replace(/(\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}/g, '[REDACTED_PHONE]')
      // Credit card numbers
      .replace(/\b(?:\d{4}[-\s]?){3}\d{4}\b/g, '[REDACTED_CARD]')
      // SSNs
      .replace(/\b\d{3}-\d{2}-\d{4}\b/g, '[REDACTED_SSN]');

    try {
      return JSON.parse(sanitizedString);
    } catch {
      return sanitizedString;
    }
  }

  /**
   * Parse container logs into stdout and stderr
   */
  private parseLogs(logData: string): { stdout: string; stderr: string } {
    const lines = logData.split('\n');
    let stdout = '';
    let stderr = '';

    for (const line of lines) {
      // Docker log format: [timestamp] [stream] message
      if (line.includes('stdout')) {
        stdout += line.replace(/.*stdout\s+/, '') + '\n';
      } else if (line.includes('stderr')) {
        stderr += line.replace(/.*stderr\s+/, '') + '\n';
      }
    }

    return { stdout: stdout.trim(), stderr: stderr.trim() };
  }

  /**
   * Validate task before execution
   */
  private async validateTask(task: AgentTask): Promise<void> {
    // Check if task type is supported
    if (
      !this.capabilities.some((cap) => {
        switch (task.type) {
          case AgentTaskType.TEXT_ANALYSIS:
            return cap === AgentCapability.TEXT_ANALYSIS;
          case AgentTaskType.CONTENT_GENERATION:
            return cap === AgentCapability.CONTENT_GENERATION;
          case AgentTaskType.SUMMARIZATION:
            return cap === AgentCapability.SUMMARIZATION;
          case AgentTaskType.QUESTION_ANSWERING:
            return cap === AgentCapability.QUESTION_ANSWERING;
          case AgentTaskType.CODE_ANALYSIS:
            return cap === AgentCapability.CODE_ANALYSIS;
          default:
            return false;
        }
      })
    ) {
      throw new Error(`Task type ${task.type} not supported by Gemini CLI Provider`);
    }

    // Validate required input
    if (!task.input.content && !task.input.prompt && !task.input.question) {
      throw new Error('Task must include content, prompt, or question in input');
    }

    // Check input size limits
    const inputSize = JSON.stringify(task.input).length;
    const maxInputSize = 1024 * 1024; // 1MB limit

    if (inputSize > maxInputSize) {
      throw new Error(`Input size ${inputSize} exceeds maximum ${maxInputSize} bytes`);
    }
  }

  /**
   * Validate resource constraints before execution
   */
  private async validateResourceConstraints(task: AgentTask): Promise<void> {
    if (!this.config.sandboxEnabled) return;

    // Check current resource usage
    const activeCount = this.activeContainers.size;
    const maxConcurrent = this.featureFlags.evaluate('GEMINI_MAX_CONCURRENT_CONTAINERS').value || 3;

    if (activeCount >= maxConcurrent) {
      throw new Error(`Maximum concurrent containers (${maxConcurrent}) exceeded`);
    }

    // Validate with sandbox enforcer
    const resourceCheck = sandboxEnforcer.validateResourceUsage(this.name, task.id, {
      memoryMB: this.config.memoryLimitMB,
      executionTimeMs: this.config.maxExecutionTime,
    });

    if (!resourceCheck.allowed) {
      throw new Error(`Resource constraints violated: ${resourceCheck.violations.join(', ')}`);
    }
  }

  /**
   * Register sandbox policy for this provider
   */
  private registerSandboxPolicy(): void {
    sandboxEnforcer.registerPolicy(this.name, {
      maxExecutionTimeMs: this.config.maxExecutionTime,
      maxMemoryMB: this.config.memoryLimitMB,
      allowNetworkAccess: this.config.networkMode !== 'none',
      allowFileSystem: this.config.allowFileSystem,
      allowedPaths: this.config.allowedPaths,
      redactSecrets: this.config.redactSecrets,
      requestsPerMinute: 20, // Conservative limit for CLI operations
      respectRobotsTxt: true,
    });
  }

  /**
   * Cleanup container and associated resources
   */
  private async cleanupContainer(containerId: string): Promise<void> {
    try {
      const container = this.docker.getContainer(containerId);

      // Stop container if still running
      try {
        await container.stop({ t: 5 }); // 5 second grace period
      } catch (stopError) {
        // Container might already be stopped
        this.logger.debug('Container stop failed (may already be stopped)', {
          containerId,
          error: stopError.message,
        });
      }

      // Remove container
      await container.remove({ force: true });

      // Remove from active containers
      this.activeContainers.delete(containerId);

      // Clean up temporary files
      const execution = this.activeContainers.get(containerId);
      if (execution) {
        const tempDir = join(this.config.tempDirectory, containerId.slice(0, 12));
        try {
          await fs.rmdir(tempDir, { recursive: true });
        } catch (cleanupError) {
          this.logger.warn('Failed to cleanup temp directory', {
            tempDir,
            error: cleanupError.message,
          });
        }
      }

      this.logger.debug('Container cleanup completed', { containerId });
    } catch (error) {
      this.logger.error('Container cleanup failed', {
        containerId,
        error: error.message,
      });
    }
  }

  /**
   * Kill container forcefully
   */
  private async killContainer(containerId: string): Promise<void> {
    try {
      const container = this.docker.getContainer(containerId);
      await container.kill();
      this.logger.warn('Container killed due to timeout or violation', { containerId });
    } catch (error) {
      this.logger.error('Failed to kill container', {
        containerId,
        error: error.message,
      });
    }
  }

  /**
   * Clean up orphaned containers on startup
   */
  private async cleanupOrphanedContainers(): Promise<void> {
    try {
      const containers = await this.docker.listContainers({
        all: true,
        filters: { name: ['pake-gemini-'] },
      });

      for (const containerInfo of containers) {
        try {
          const container = this.docker.getContainer(containerInfo.Id);
          await container.remove({ force: true });
          this.logger.info('Cleaned up orphaned container', {
            containerId: containerInfo.Id,
            name: containerInfo.Names[0],
          });
        } catch (cleanupError) {
          this.logger.warn('Failed to cleanup orphaned container', {
            containerId: containerInfo.Id,
            error: cleanupError.message,
          });
        }
      }
    } catch (error) {
      this.logger.warn('Failed to cleanup orphaned containers', {
        error: error.message,
      });
    }
  }

  /**
   * Generate unique execution ID
   */
  private generateExecutionId(): string {
    this.executionCount++;
    const timestamp = Date.now().toString(36);
    const random = randomBytes(4).toString('hex');
    return `${timestamp}-${this.executionCount}-${random}`;
  }

  /**
   * Sanitize error message for logging
   */
  private sanitizeError(error: string): string {
    return this.config.redactSecrets ? (this.sanitizeOutput(error) as string) : error;
  }

  /**
   * Validate provider configuration
   */
  private validateConfiguration(): void {
    if (!this.config.apiKey) {
      throw new Error('Gemini API key is required');
    }

    if (this.config.maxExecutionTime < 1000 || this.config.maxExecutionTime > 300000) {
      throw new Error('maxExecutionTime must be between 1s and 5 minutes');
    }

    if (this.config.memoryLimitMB < 128 || this.config.memoryLimitMB > 2048) {
      throw new Error('memoryLimitMB must be between 128MB and 2GB');
    }
  }

  /**
   * Health check implementation
   */
  async healthCheck(): Promise<boolean> {
    const now = Date.now();

    // Rate limit health checks
    if (now - this.lastHealthCheck < this.healthCheckInterval) {
      return true; // Assume healthy if checked recently
    }

    this.lastHealthCheck = now;

    try {
      // Check Docker daemon connectivity
      await this.docker.ping();

      // Check if container image is available
      try {
        await this.docker.getImage(this.config.containerImage).inspect();
      } catch (imageError) {
        this.logger.error('Container image not available', {
          image: this.config.containerImage,
          error: imageError.message,
        });
        return false;
      }

      // Check sandbox enforcer if enabled
      if (this.config.sandboxEnabled) {
        const policy = sandboxEnforcer.getPolicy(this.name);
        if (!policy) {
          this.logger.error('Sandbox policy not found');
          return false;
        }
      }

      this.logger.debug('Health check passed');
      return true;
    } catch (error) {
      this.logger.error('Health check failed', { error: error.message });
      return false;
    }
  }

  /**
   * Dispose and cleanup resources
   */
  async dispose(): Promise<void> {
    this.logger.info('Disposing Gemini CLI Provider');

    // Cleanup all active containers
    const cleanupPromises = Array.from(this.activeContainers.keys()).map((containerId) =>
      this.cleanupContainer(containerId)
    );

    await Promise.allSettled(cleanupPromises);

    // Clean up temporary directory
    try {
      await fs.rmdir(this.config.tempDirectory, { recursive: true });
    } catch (error) {
      this.logger.warn('Failed to cleanup temp directory', {
        tempDir: this.config.tempDirectory,
        error: error.message,
      });
    }

    this.logger.info('Gemini CLI Provider disposed');
  }
}
