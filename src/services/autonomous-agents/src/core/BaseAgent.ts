import { EventEmitter } from 'events';
import {
  AgentConfig,
  Task,
  TaskResult,
  AgentStatus,
  AgentCapabilities,
  TaskMetrics,
  TaskLog,
  AgentState,
  ToolExecution,
  AgentPerformanceMetrics,
} from '@/types/agent';
import { Logger } from '@/utils/logger';
import { v4 as uuidv4 } from 'uuid';
import { performance } from 'perf_hooks';

export abstract class BaseAgent extends EventEmitter {
  protected logger: Logger;
  protected status: AgentStatus = 'initializing';
  protected currentTask: Task | null = null;
  protected taskQueue: Task[] = [];
  protected metrics: AgentPerformanceMetrics = {
    tasksPerHour: 0,
    successRate: 0,
    averageTaskTime: 0,
    resourceUtilization: {
      cpu: 0,
      memory: 0,
      network: 0,
      storage: 0,
    },
    qualityScore: 0,
  };
  protected toolExecutions: Map<string, ToolExecution> = new Map();
  protected lastHeartbeat: Date = new Date();
  protected startTime: Date = new Date();

  constructor(public config: AgentConfig) {
    super();
    this.logger = new Logger(`Agent:${config.type}:${config.name}`);
    this.setupEventHandlers();
    this.startHeartbeat();
  }

  private setupEventHandlers(): void {
    this.on('task_started', this.onTaskStarted.bind(this));
    this.on('task_completed', this.onTaskCompleted.bind(this));
    this.on('task_failed', this.onTaskFailed.bind(this));
    this.on('error', this.onError.bind(this));
  }

  private startHeartbeat(): void {
    setInterval(() => {
      this.lastHeartbeat = new Date();
      this.emit('heartbeat', {
        agentId: this.config.id,
        status: this.status,
        currentTask: this.currentTask?.id,
        queueSize: this.taskQueue.length,
        metrics: this.metrics,
        timestamp: this.lastHeartbeat,
      });
    }, 30000); // Every 30 seconds
  }

  // Abstract methods that must be implemented by derived classes
  abstract execute(task: Task): Promise<TaskResult>;
  abstract canHandle(task: Task): boolean;
  abstract getCapabilities(): AgentCapabilities;

  // Core execution logic
  async processTask(task: Task): Promise<TaskResult> {
    if (!this.canHandle(task)) {
      throw new Error(
        `Agent ${this.config.name} cannot handle task type: ${task.type}`
      );
    }

    if (this.status !== 'idle' && this.status !== 'waiting') {
      throw new Error(
        `Agent ${this.config.name} is not available (status: ${this.status})`
      );
    }

    this.validateTask(task);

    this.currentTask = task;
    this.status = 'working';
    const startTime = performance.now();

    this.emit('task_started', { agentId: this.config.id, task });
    this.logger.info(`Starting task: ${task.title}`, { taskId: task.id });

    try {
      // Check constraints before execution
      await this.checkConstraints(task);

      // Execute the task
      const result = await this.execute(task);

      // Validate result
      await this.validateResult(task, result);

      // Record metrics
      const executionTime = performance.now() - startTime;
      result.metrics = {
        ...result.metrics,
        executionTime,
        tokensUsed: result.metrics?.tokensUsed || 0,
        apiCallsMade: result.metrics?.apiCallsMade || 0,
        costIncurred: result.metrics?.costIncurred || 0,
        toolsUsed: result.metrics?.toolsUsed || [],
        errorCount: result.metrics?.errorCount || 0,
        retryCount: result.metrics?.retryCount || 0,
      };

      // Update performance metrics
      this.updateMetrics(result.metrics, true);

      this.currentTask = null;
      this.status = 'idle';

      this.emit('task_completed', { agentId: this.config.id, task, result });
      this.logger.info(`Task completed: ${task.title}`, {
        taskId: task.id,
        executionTime,
        quality: result.quality,
        confidence: result.confidence,
      });

      return result;
    } catch (error) {
      const executionTime = performance.now() - startTime;
      const errorResult = this.createErrorResult(
        task,
        error as Error,
        executionTime
      );

      this.updateMetrics(errorResult.metrics, false);
      this.currentTask = null;
      this.status = 'idle';

      this.emit('task_failed', { agentId: this.config.id, task, error });
      this.logger.error(`Task failed: ${task.title}`, {
        taskId: task.id,
        error: (error as Error).message,
        executionTime,
      });

      throw error;
    }
  }

  protected validateTask(task: Task): void {
    // Check required inputs
    for (const input of task.requirements.inputs) {
      if (input.required && !input.value) {
        throw new Error(`Required input '${input.name}' is missing`);
      }

      if (input.validation) {
        this.validateInput(input.value, input.validation);
      }
    }

    // Check tool availability
    for (const toolId of task.requirements.tools) {
      if (!this.config.constraints.allowedTools.includes(toolId)) {
        throw new Error(`Tool '${toolId}' is not allowed for this agent`);
      }
    }

    // Check deadline
    if (task.deadline && task.deadline < new Date()) {
      throw new Error(`Task deadline has passed: ${task.deadline}`);
    }
  }

  protected validateInput(value: any, validation: any): void {
    switch (validation.type) {
      case 'regex':
        if (
          typeof value === 'string' &&
          !new RegExp(validation.rule).test(value)
        ) {
          throw new Error(
            validation.message ||
              `Input does not match pattern: ${validation.rule}`
          );
        }
        break;
      case 'range':
        if (typeof value === 'number') {
          const [min, max] = validation.rule as number[];
          if (value < min || value > max) {
            throw new Error(
              validation.message || `Input must be between ${min} and ${max}`
            );
          }
        }
        break;
      case 'enum':
        if (!(validation.rule as string[]).includes(value)) {
          throw new Error(
            validation.message ||
              `Input must be one of: ${(validation.rule as string[]).join(', ')}`
          );
        }
        break;
      case 'custom':
        if (typeof validation.rule === 'function' && !validation.rule(value)) {
          throw new Error(validation.message || 'Input validation failed');
        }
        break;
    }
  }

  protected async checkConstraints(task: Task): Promise<void> {
    // Check execution time constraint
    if (task.deadline) {
      const timeRemaining = task.deadline.getTime() - Date.now();
      if (timeRemaining < this.config.constraints.maxExecutionTime) {
        throw new Error(
          'Insufficient time remaining to complete task within constraints'
        );
      }
    }

    // Check approval requirement
    if (
      this.config.constraints.requiresApproval &&
      !task.approvals?.some(a => a.status === 'approved')
    ) {
      throw new Error('Task requires approval before execution');
    }

    // Additional constraint checks can be added here
  }

  protected async validateResult(
    task: Task,
    result: TaskResult
  ): Promise<void> {
    // Check quality threshold
    if (result.quality < task.requirements.qualityThreshold) {
      throw new Error(
        `Result quality (${result.quality}) below threshold (${task.requirements.qualityThreshold})`
      );
    }

    // Check confidence threshold
    if (result.confidence < task.requirements.confidenceThreshold) {
      throw new Error(
        `Result confidence (${result.confidence}) below threshold (${task.requirements.confidenceThreshold})`
      );
    }

    // Check required outputs
    for (const output of task.requirements.outputs) {
      if (output.required && !result.outputs[output.name]) {
        throw new Error(`Required output '${output.name}' is missing`);
      }
    }
  }

  protected createErrorResult(
    task: Task,
    error: Error,
    executionTime: number
  ): TaskResult {
    return {
      outputs: {},
      metrics: {
        executionTime,
        tokensUsed: 0,
        apiCallsMade: 0,
        costIncurred: 0,
        toolsUsed: [],
        errorCount: 1,
        retryCount: 0,
      },
      logs: [
        {
          timestamp: new Date(),
          level: 'error',
          message: error.message,
          metadata: { stack: error.stack },
        },
      ],
      artifacts: [],
      confidence: 0,
      quality: 0,
    };
  }

  protected updateMetrics(taskMetrics: TaskMetrics, success: boolean): void {
    const now = new Date();
    const hoursSinceStart =
      (now.getTime() - this.startTime.getTime()) / (1000 * 60 * 60);

    // Update success rate (exponential moving average)
    const alpha = 0.1; // Smoothing factor
    this.metrics.successRate =
      this.metrics.successRate * (1 - alpha) + (success ? 1 : 0) * alpha;

    // Update average task time
    this.metrics.averageTaskTime =
      this.metrics.averageTaskTime * (1 - alpha) +
      taskMetrics.executionTime * alpha;

    // Update tasks per hour
    this.metrics.tasksPerHour = hoursSinceStart > 0 ? 1 / hoursSinceStart : 0;

    // Update quality score (if quality data available)
    // This would be updated based on task results and feedback

    this.emit('metrics_updated', {
      agentId: this.config.id,
      metrics: this.metrics,
    });
  }

  // Tool execution methods
  protected async executeTool(
    toolId: string,
    parameters: Record<string, any>,
    taskId: string
  ): Promise<any> {
    if (!this.config.constraints.allowedTools.includes(toolId)) {
      throw new Error(`Tool '${toolId}' is not allowed for this agent`);
    }

    const executionId = uuidv4();
    const execution: ToolExecution = {
      id: executionId,
      toolId,
      agentId: this.config.id,
      taskId,
      parameters,
      startTime: new Date(),
      status: 'running',
      metrics: {
        duration: 0,
        requestsMade: 0,
        dataTransferred: 0,
        cost: 0,
      },
    };

    this.toolExecutions.set(executionId, execution);
    this.emit('tool_execution_started', execution);

    try {
      // This would be implemented by the tool registry
      const result = await this.invokeToolExecution(toolId, parameters);

      execution.endTime = new Date();
      execution.status = 'completed';
      execution.result = result;
      execution.metrics.duration =
        execution.endTime.getTime() - execution.startTime.getTime();

      this.emit('tool_execution_completed', execution);
      return result;
    } catch (error) {
      execution.endTime = new Date();
      execution.status = 'failed';
      execution.error = (error as Error).message;
      execution.metrics.duration =
        execution.endTime.getTime() - execution.startTime.getTime();

      this.emit('tool_execution_failed', execution);
      throw error;
    } finally {
      this.toolExecutions.set(executionId, execution);
    }
  }

  protected abstract invokeToolExecution(
    toolId: string,
    parameters: Record<string, any>
  ): Promise<any>;

  // Logging helpers
  protected log(
    level: 'debug' | 'info' | 'warn' | 'error',
    message: string,
    metadata?: Record<string, any>
  ): TaskLog {
    const log: TaskLog = {
      timestamp: new Date(),
      level,
      message,
      metadata,
    };

    this.logger[level](message, metadata);
    this.emit('log', log);

    return log;
  }

  // Public interface methods
  public getStatus(): AgentStatus {
    return this.status;
  }

  public getState(): AgentState {
    return {
      agentId: this.config.id,
      status: this.status,
      currentTask: this.currentTask?.id,
      queuedTasks: this.taskQueue.map(t => t.id),
      capabilities: this.getCapabilities(),
      performance: this.metrics,
      lastHeartbeat: this.lastHeartbeat,
      metadata: {
        startTime: this.startTime,
        totalTasksProcessed: 0, // Would track this
        toolExecutions: this.toolExecutions.size,
      },
    };
  }

  public async pause(): Promise<void> {
    if (this.status === 'working') {
      this.status = 'paused';
      this.emit('agent_paused', { agentId: this.config.id });
      this.logger.info('Agent paused');
    }
  }

  public async resume(): Promise<void> {
    if (this.status === 'paused') {
      this.status = this.currentTask ? 'working' : 'idle';
      this.emit('agent_resumed', { agentId: this.config.id });
      this.logger.info('Agent resumed');
    }
  }

  public async stop(): Promise<void> {
    this.status = 'offline';
    this.taskQueue = [];

    // Cancel any running tool executions
    for (const execution of this.toolExecutions.values()) {
      if (execution.status === 'running') {
        execution.status = 'cancelled';
        execution.endTime = new Date();
      }
    }

    this.emit('agent_stopped', { agentId: this.config.id });
    this.logger.info('Agent stopped');
    this.removeAllListeners();
  }

  public queueTask(task: Task): void {
    this.taskQueue.push(task);
    this.emit('task_queued', { agentId: this.config.id, task });
  }

  public getQueueSize(): number {
    return this.taskQueue.length;
  }

  public getMetrics(): AgentPerformanceMetrics {
    return { ...this.metrics };
  }

  public updateConfig(updates: Partial<AgentConfig>): void {
    this.config = { ...this.config, ...updates };
    this.emit('config_updated', {
      agentId: this.config.id,
      config: this.config,
    });
    this.logger.info('Agent configuration updated');
  }

  // Event handlers
  protected onTaskStarted(event: any): void {
    this.logger.debug('Task started event', event);
  }

  protected onTaskCompleted(event: any): void {
    this.logger.debug('Task completed event', event);
  }

  protected onTaskFailed(event: any): void {
    this.logger.error('Task failed event', event);
  }

  protected onError(error: Error): void {
    this.logger.error('Agent error', {
      error: error.message,
      stack: error.stack,
    });
    this.status = 'error';
  }
}

export default BaseAgent;
