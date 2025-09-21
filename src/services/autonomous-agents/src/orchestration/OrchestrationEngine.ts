import { EventEmitter } from 'events';
import {
  ExecutionPlan,
  Task,
  AgentState,
  OrchestrationPattern,
  ExecutionStatus,
  ExecutionConstraints,
  AgentMessage,
  MessageType,
  CollaborationRequest,
} from '@/types/agent';
import { BaseAgent } from '@/core/BaseAgent';
import { Logger } from '@/utils/logger';
import { v4 as uuidv4 } from 'uuid';
import { performance } from 'perf_hooks';

interface ExecutionContext {
  planId: string;
  plan: ExecutionPlan;
  agents: Map<string, BaseAgent>;
  taskStates: Map<string, TaskExecutionState>;
  executionQueue: ExecutionQueue;
  messageQueue: MessageQueue;
  metrics: ExecutionMetrics;
  startTime: Date;
  checkpoints: ExecutionCheckpoint[];
}

interface TaskExecutionState {
  taskId: string;
  assignedAgentId?: string;
  status:
    | 'pending'
    | 'assigned'
    | 'executing'
    | 'completed'
    | 'failed'
    | 'blocked';
  startTime?: Date;
  endTime?: Date;
  attempts: number;
  dependencies: string[];
  dependents: string[];
  result?: any;
  error?: Error;
  retries: number;
}

interface ExecutionQueue {
  ready: string[];
  waiting: string[];
  executing: string[];
  completed: string[];
  failed: string[];
}

interface MessageQueue {
  pending: AgentMessage[];
  processing: AgentMessage[];
  delivered: AgentMessage[];
  failed: AgentMessage[];
}

interface ExecutionMetrics {
  tasksTotal: number;
  tasksCompleted: number;
  tasksFailed: number;
  agentsActive: number;
  executionTime: number;
  avgTaskTime: number;
  resourceUtilization: Record<string, number>;
  costAccumulated: number;
}

interface ExecutionCheckpoint {
  id: string;
  timestamp: Date;
  completedTasks: string[];
  agentStates: Record<string, any>;
  context: any;
  description: string;
}

interface PatternExecutor {
  execute(context: ExecutionContext): Promise<void>;
  canRecover(context: ExecutionContext, error: Error): boolean;
  recover(context: ExecutionContext, error: Error): Promise<void>;
}

export class OrchestrationEngine extends EventEmitter {
  private logger: Logger;
  private activeExecutions: Map<string, ExecutionContext> = new Map();
  private patternExecutors: Map<OrchestrationPattern, PatternExecutor> =
    new Map();
  private agentPool: Map<string, BaseAgent> = new Map();
  private messageHandlers: Map<MessageType, Function> = new Map();
  private maxConcurrentExecutions = 10;
  private maxRetries = 3;
  private checkpointInterval = 30000; // 30 seconds

  constructor() {
    super();
    this.logger = new Logger('OrchestrationEngine');
    this.initializePatternExecutors();
    this.initializeMessageHandlers();
    this.setupPeriodicTasks();
    this.logger.info('Orchestration Engine initialized');
  }

  // Main execution methods
  async executePlan(
    plan: ExecutionPlan,
    agents: BaseAgent[]
  ): Promise<ExecutionResult> {
    const startTime = performance.now();

    try {
      // Validate execution capacity
      if (this.activeExecutions.size >= this.maxConcurrentExecutions) {
        throw new Error('Maximum concurrent executions reached');
      }

      // Validate plan
      this.validateExecutionPlan(plan);

      // Create execution context
      const context = this.createExecutionContext(plan, agents);

      this.logger.info(`Starting execution plan: ${plan.title}`, {
        planId: plan.id,
      });
      this.emit('execution_started', { planId: plan.id, plan });

      // Store context
      this.activeExecutions.set(plan.id, context);

      // Get pattern executor
      const executor = this.patternExecutors.get(plan.pattern);
      if (!executor) {
        throw new Error(`No executor found for pattern: ${plan.pattern}`);
      }

      // Update plan status
      plan.status = 'running';
      plan.timeline.startTime = new Date();

      // Execute plan
      await executor.execute(context);

      // Calculate final metrics
      const executionTime = performance.now() - startTime;
      context.metrics.executionTime = executionTime;

      // Determine final status
      const finalStatus = this.determineFinalStatus(context);
      plan.status = finalStatus;
      plan.timeline.endTime = new Date();

      this.logger.info(`Execution plan completed: ${plan.title}`, {
        planId: plan.id,
        status: finalStatus,
        duration: executionTime,
      });

      const result: ExecutionResult = {
        planId: plan.id,
        status: finalStatus,
        executionTime,
        tasksCompleted: context.metrics.tasksCompleted,
        tasksFailed: context.metrics.tasksFailed,
        agentsUsed: context.agents.size,
        costIncurred: context.metrics.costAccumulated,
        checkpoints: context.checkpoints,
        finalContext: context,
      };

      this.emit('execution_completed', { planId: plan.id, result });
      return result;
    } catch (error) {
      const executionTime = performance.now() - startTime;
      this.logger.error(`Execution plan failed: ${plan.title}`, {
        planId: plan.id,
        error: (error as Error).message,
      });

      plan.status = 'failed';
      plan.timeline.endTime = new Date();

      const result: ExecutionResult = {
        planId: plan.id,
        status: 'failed',
        executionTime,
        tasksCompleted: 0,
        tasksFailed: plan.tasks.length,
        agentsUsed: 0,
        costIncurred: 0,
        error: error as Error,
        checkpoints: [],
        finalContext: null,
      };

      this.emit('execution_failed', { planId: plan.id, error, result });
      return result;
    } finally {
      // Cleanup
      this.activeExecutions.delete(plan.id);
    }
  }

  async pauseExecution(planId: string): Promise<void> {
    const context = this.activeExecutions.get(planId);
    if (!context) {
      throw new Error(`No active execution found for plan: ${planId}`);
    }

    context.plan.status = 'paused';

    // Pause all agents
    for (const agent of context.agents.values()) {
      await agent.pause();
    }

    // Create checkpoint
    await this.createCheckpoint(context, 'Manual pause');

    this.logger.info(`Execution paused: ${planId}`);
    this.emit('execution_paused', { planId });
  }

  async resumeExecution(planId: string): Promise<void> {
    const context = this.activeExecutions.get(planId);
    if (!context) {
      throw new Error(`No active execution found for plan: ${planId}`);
    }

    if (context.plan.status !== 'paused') {
      throw new Error(`Execution is not paused: ${planId}`);
    }

    context.plan.status = 'running';

    // Resume all agents
    for (const agent of context.agents.values()) {
      await agent.resume();
    }

    this.logger.info(`Execution resumed: ${planId}`);
    this.emit('execution_resumed', { planId });
  }

  async cancelExecution(planId: string, reason?: string): Promise<void> {
    const context = this.activeExecutions.get(planId);
    if (!context) {
      throw new Error(`No active execution found for plan: ${planId}`);
    }

    context.plan.status = 'cancelled';

    // Stop all agents
    for (const agent of context.agents.values()) {
      await agent.stop();
    }

    // Execute rollback if configured
    if (context.plan.rollbackStrategy.enabled) {
      await this.executeRollback(context);
    }

    this.logger.info(`Execution cancelled: ${planId}`, { reason });
    this.emit('execution_cancelled', { planId, reason });
  }

  // Agent management
  registerAgent(agent: BaseAgent): void {
    this.agentPool.set(agent.config.id, agent);
    this.logger.info(`Agent registered: ${agent.config.name}`, {
      agentId: agent.config.id,
    });

    // Setup agent event handlers
    agent.on('task_completed', this.handleAgentTaskCompleted.bind(this));
    agent.on('task_failed', this.handleAgentTaskFailed.bind(this));
    agent.on('agent_error', this.handleAgentError.bind(this));
  }

  unregisterAgent(agentId: string): void {
    const agent = this.agentPool.get(agentId);
    if (agent) {
      agent.removeAllListeners();
      this.agentPool.delete(agentId);
      this.logger.info(`Agent unregistered: ${agentId}`);
    }
  }

  getAvailableAgents(): BaseAgent[] {
    return Array.from(this.agentPool.values()).filter(
      agent => agent.getStatus() === 'idle'
    );
  }

  // Private methods
  private validateExecutionPlan(plan: ExecutionPlan): void {
    if (!plan.tasks || plan.tasks.length === 0) {
      throw new Error('Execution plan must have at least one task');
    }

    if (!plan.agents || plan.agents.length === 0) {
      throw new Error('Execution plan must specify required agents');
    }

    // Validate task dependencies
    for (const taskId of plan.tasks) {
      // In a real implementation, we'd validate task dependency graph
    }

    // Validate constraints
    if (plan.constraints.maxDuration < 60000) {
      throw new Error('Maximum duration must be at least 1 minute');
    }

    if (plan.constraints.maxCost <= 0) {
      throw new Error('Maximum cost must be positive');
    }
  }

  private createExecutionContext(
    plan: ExecutionPlan,
    agents: BaseAgent[]
  ): ExecutionContext {
    const agentMap = new Map<string, BaseAgent>();
    agents.forEach(agent => agentMap.set(agent.config.id, agent));

    const taskStates = new Map<string, TaskExecutionState>();
    plan.tasks.forEach(taskId => {
      taskStates.set(taskId, {
        taskId,
        status: 'pending',
        attempts: 0,
        dependencies: [], // Would be populated from task definitions
        dependents: [],
        retries: 0,
      });
    });

    return {
      planId: plan.id,
      plan,
      agents: agentMap,
      taskStates,
      executionQueue: {
        ready: [],
        waiting: [...plan.tasks],
        executing: [],
        completed: [],
        failed: [],
      },
      messageQueue: {
        pending: [],
        processing: [],
        delivered: [],
        failed: [],
      },
      metrics: {
        tasksTotal: plan.tasks.length,
        tasksCompleted: 0,
        tasksFailed: 0,
        agentsActive: 0,
        executionTime: 0,
        avgTaskTime: 0,
        resourceUtilization: {},
        costAccumulated: 0,
      },
      startTime: new Date(),
      checkpoints: [],
    };
  }

  private initializePatternExecutors(): void {
    this.patternExecutors.set('sequential', new SequentialExecutor());
    this.patternExecutors.set('parallel', new ParallelExecutor());
    this.patternExecutors.set('hierarchical', new HierarchicalExecutor());
    this.patternExecutors.set('consensus', new ConsensusExecutor());
    this.patternExecutors.set('pipeline', new PipelineExecutor());
    this.patternExecutors.set('conditional', new ConditionalExecutor());
  }

  private initializeMessageHandlers(): void {
    this.messageHandlers.set(
      'task_assignment',
      this.handleTaskAssignmentMessage.bind(this)
    );
    this.messageHandlers.set(
      'task_completion',
      this.handleTaskCompletionMessage.bind(this)
    );
    this.messageHandlers.set(
      'collaboration_request',
      this.handleCollaborationRequest.bind(this)
    );
    this.messageHandlers.set(
      'approval_request',
      this.handleApprovalRequest.bind(this)
    );
  }

  private setupPeriodicTasks(): void {
    // Checkpoint creation
    setInterval(() => {
      for (const [planId, context] of this.activeExecutions) {
        if (context.plan.status === 'running') {
          this.createCheckpoint(context, 'Periodic checkpoint').catch(error => {
            this.logger.error('Failed to create checkpoint', {
              planId,
              error: error.message,
            });
          });
        }
      }
    }, this.checkpointInterval);

    // Metrics collection
    setInterval(() => {
      this.collectMetrics();
    }, 10000); // Every 10 seconds

    // Health monitoring
    setInterval(() => {
      this.monitorHealth();
    }, 30000); // Every 30 seconds
  }

  private async createCheckpoint(
    context: ExecutionContext,
    description: string
  ): Promise<void> {
    const checkpoint: ExecutionCheckpoint = {
      id: uuidv4(),
      timestamp: new Date(),
      completedTasks: context.executionQueue.completed,
      agentStates: {},
      context: {
        metrics: context.metrics,
        queueState: context.executionQueue,
      },
      description,
    };

    // Capture agent states
    for (const [agentId, agent] of context.agents) {
      checkpoint.agentStates[agentId] = agent.getState();
    }

    context.checkpoints.push(checkpoint);

    // Keep only last 10 checkpoints
    if (context.checkpoints.length > 10) {
      context.checkpoints.splice(0, context.checkpoints.length - 10);
    }

    this.logger.debug('Checkpoint created', {
      planId: context.planId,
      checkpointId: checkpoint.id,
    });
  }

  private async executeRollback(context: ExecutionContext): Promise<void> {
    const strategy = context.plan.rollbackStrategy;

    this.logger.info('Executing rollback', { planId: context.planId });

    // Find latest checkpoint
    const latestCheckpoint =
      context.checkpoints[context.checkpoints.length - 1];

    if (latestCheckpoint) {
      // Restore to checkpoint state
      context.executionQueue = latestCheckpoint.context.queueState;
      context.metrics = latestCheckpoint.context.metrics;
    }

    // Execute cleanup actions
    for (const action of strategy.cleanupActions) {
      try {
        await this.executeCleanupAction(action, context);
      } catch (error) {
        this.logger.error('Cleanup action failed', {
          action,
          error: (error as Error).message,
        });
      }
    }

    context.plan.status = 'rolled_back';
    this.emit('execution_rolled_back', { planId: context.planId });
  }

  private async executeCleanupAction(
    action: string,
    context: ExecutionContext
  ): Promise<void> {
    // Implementation would depend on specific cleanup actions
    this.logger.info('Executing cleanup action', {
      action,
      planId: context.planId,
    });
  }

  private determineFinalStatus(context: ExecutionContext): ExecutionStatus {
    const { completed, failed } = context.executionQueue;
    const total = context.metrics.tasksTotal;

    if (failed.length > 0) {
      const failureRate = failed.length / total;
      if (failureRate > context.plan.constraints.failureThreshold) {
        return 'failed';
      }
    }

    if (completed.length === total) {
      return 'completed';
    } else if (completed.length > 0) {
      return 'completed'; // Partial completion still considered success
    } else {
      return 'failed';
    }
  }

  private collectMetrics(): void {
    for (const [planId, context] of this.activeExecutions) {
      // Update metrics
      context.metrics.agentsActive = Array.from(context.agents.values()).filter(
        agent => agent.getStatus() === 'working'
      ).length;

      context.metrics.executionTime = Date.now() - context.startTime.getTime();

      if (context.metrics.tasksCompleted > 0) {
        context.metrics.avgTaskTime =
          context.metrics.executionTime / context.metrics.tasksCompleted;
      }

      // Emit metrics update
      this.emit('metrics_updated', { planId, metrics: context.metrics });
    }
  }

  private monitorHealth(): void {
    const totalExecutions = this.activeExecutions.size;
    const healthStatus = {
      activeExecutions: totalExecutions,
      availableAgents: this.getAvailableAgents().length,
      totalAgents: this.agentPool.size,
      systemLoad: totalExecutions / this.maxConcurrentExecutions,
      timestamp: new Date(),
    };

    this.emit('health_status', healthStatus);

    if (healthStatus.systemLoad > 0.8) {
      this.logger.warn('High system load detected', healthStatus);
    }
  }

  // Message handling
  async sendMessage(message: AgentMessage): Promise<void> {
    const context = Array.from(this.activeExecutions.values()).find(ctx =>
      ctx.agents.has(message.fromAgentId)
    );

    if (!context) {
      throw new Error('No active execution context found for agent');
    }

    context.messageQueue.pending.push(message);
    await this.processMessageQueue(context);
  }

  private async processMessageQueue(context: ExecutionContext): Promise<void> {
    const { messageQueue } = context;

    while (messageQueue.pending.length > 0) {
      const message = messageQueue.pending.shift()!;
      messageQueue.processing.push(message);

      try {
        const handler = this.messageHandlers.get(message.type);
        if (handler) {
          await handler(message, context);
          messageQueue.delivered.push(message);
        } else {
          throw new Error(`No handler for message type: ${message.type}`);
        }
      } catch (error) {
        this.logger.error('Message processing failed', {
          messageId: message.id,
          error: (error as Error).message,
        });
        messageQueue.failed.push(message);
      } finally {
        const index = messageQueue.processing.indexOf(message);
        if (index >= 0) {
          messageQueue.processing.splice(index, 1);
        }
      }
    }
  }

  private async handleTaskAssignmentMessage(
    message: AgentMessage,
    context: ExecutionContext
  ): Promise<void> {
    // Handle task assignment logic
  }

  private async handleTaskCompletionMessage(
    message: AgentMessage,
    context: ExecutionContext
  ): Promise<void> {
    // Handle task completion logic
  }

  private async handleCollaborationRequest(
    message: AgentMessage,
    context: ExecutionContext
  ): Promise<void> {
    // Handle collaboration request
  }

  private async handleApprovalRequest(
    message: AgentMessage,
    context: ExecutionContext
  ): Promise<void> {
    // Handle approval request
  }

  // Agent event handlers
  private handleAgentTaskCompleted(event: any): void {
    this.logger.debug('Agent task completed', event);
    // Update execution context
  }

  private handleAgentTaskFailed(event: any): void {
    this.logger.warn('Agent task failed', event);
    // Handle task failure, retry logic, etc.
  }

  private handleAgentError(event: any): void {
    this.logger.error('Agent error', event);
    // Handle agent errors
  }

  // Public API
  getExecutionStatus(planId: string): ExecutionContext | null {
    return this.activeExecutions.get(planId) || null;
  }

  getActiveExecutions(): string[] {
    return Array.from(this.activeExecutions.keys());
  }

  getSystemMetrics(): any {
    return {
      activeExecutions: this.activeExecutions.size,
      maxConcurrentExecutions: this.maxConcurrentExecutions,
      totalAgents: this.agentPool.size,
      availableAgents: this.getAvailableAgents().length,
    };
  }
}

// Pattern Executor Implementations
class SequentialExecutor implements PatternExecutor {
  async execute(context: ExecutionContext): Promise<void> {
    // Execute tasks one by one in order
    for (const taskId of context.plan.tasks) {
      const taskState = context.taskStates.get(taskId);
      if (!taskState) continue;

      // Find available agent
      const availableAgent = Array.from(context.agents.values()).find(
        agent => agent.getStatus() === 'idle'
      );

      if (!availableAgent) {
        throw new Error('No available agents for task execution');
      }

      // Execute task
      taskState.status = 'executing';
      taskState.assignedAgentId = availableAgent.config.id;
      taskState.startTime = new Date();

      try {
        // This would execute the actual task
        await this.executeTask(taskId, availableAgent, context);

        taskState.status = 'completed';
        taskState.endTime = new Date();
        context.executionQueue.completed.push(taskId);
        context.metrics.tasksCompleted++;
      } catch (error) {
        taskState.status = 'failed';
        taskState.error = error as Error;
        context.executionQueue.failed.push(taskId);
        context.metrics.tasksFailed++;
        throw error; // Stop sequential execution on failure
      }
    }
  }

  canRecover(context: ExecutionContext, error: Error): boolean {
    return false; // Sequential execution cannot recover from failures
  }

  async recover(context: ExecutionContext, error: Error): Promise<void> {
    throw new Error('Sequential executor cannot recover from failures');
  }

  private async executeTask(
    taskId: string,
    agent: BaseAgent,
    context: ExecutionContext
  ): Promise<void> {
    // Mock task execution
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
}

class ParallelExecutor implements PatternExecutor {
  async execute(context: ExecutionContext): Promise<void> {
    // Execute all tasks in parallel
    const taskPromises = context.plan.tasks.map(taskId =>
      this.executeTaskInParallel(taskId, context)
    );

    const results = await Promise.allSettled(taskPromises);

    // Process results
    results.forEach((result, index) => {
      const taskId = context.plan.tasks[index];
      const taskState = context.taskStates.get(taskId);

      if (!taskState) return;

      if (result.status === 'fulfilled') {
        taskState.status = 'completed';
        context.executionQueue.completed.push(taskId);
        context.metrics.tasksCompleted++;
      } else {
        taskState.status = 'failed';
        taskState.error = result.reason;
        context.executionQueue.failed.push(taskId);
        context.metrics.tasksFailed++;
      }
    });
  }

  canRecover(context: ExecutionContext, error: Error): boolean {
    return context.metrics.tasksFailed < context.plan.tasks.length * 0.5; // Can recover if <50% failed
  }

  async recover(context: ExecutionContext, error: Error): Promise<void> {
    // Retry failed tasks
    const failedTasks = context.executionQueue.failed;
    context.executionQueue.failed = [];

    const retryPromises = failedTasks.map(taskId =>
      this.executeTaskInParallel(taskId, context)
    );

    await Promise.allSettled(retryPromises);
  }

  private async executeTaskInParallel(
    taskId: string,
    context: ExecutionContext
  ): Promise<void> {
    const taskState = context.taskStates.get(taskId);
    if (!taskState) throw new Error(`Task state not found: ${taskId}`);

    // Find available agent
    const availableAgent = Array.from(context.agents.values()).find(
      agent => agent.getStatus() === 'idle'
    );

    if (!availableAgent) {
      throw new Error('No available agents for task execution');
    }

    taskState.status = 'executing';
    taskState.assignedAgentId = availableAgent.config.id;
    taskState.startTime = new Date();

    // Mock task execution
    await new Promise(resolve =>
      setTimeout(resolve, Math.random() * 2000 + 1000)
    );

    taskState.endTime = new Date();
  }
}

class HierarchicalExecutor implements PatternExecutor {
  async execute(context: ExecutionContext): Promise<void> {
    // Implement hierarchical task delegation
    // Manager agent delegates to specialist agents
  }

  canRecover(context: ExecutionContext, error: Error): boolean {
    return true; // Can recover through delegation
  }

  async recover(context: ExecutionContext, error: Error): Promise<void> {
    // Implement recovery through re-delegation
  }
}

class ConsensusExecutor implements PatternExecutor {
  async execute(context: ExecutionContext): Promise<void> {
    // Execute tasks with multiple agents and build consensus
  }

  canRecover(context: ExecutionContext, error: Error): boolean {
    return true; // Can recover by seeking new consensus
  }

  async recover(context: ExecutionContext, error: Error): Promise<void> {
    // Implement consensus-based recovery
  }
}

class PipelineExecutor implements PatternExecutor {
  async execute(context: ExecutionContext): Promise<void> {
    // Execute tasks in pipeline stages
  }

  canRecover(context: ExecutionContext, error: Error): boolean {
    return true; // Can recover by restarting from last checkpoint
  }

  async recover(context: ExecutionContext, error: Error): Promise<void> {
    // Implement pipeline recovery
  }
}

class ConditionalExecutor implements PatternExecutor {
  async execute(context: ExecutionContext): Promise<void> {
    // Execute tasks based on conditions and branching logic
  }

  canRecover(context: ExecutionContext, error: Error): boolean {
    return true; // Can recover by trying alternative branches
  }

  async recover(context: ExecutionContext, error: Error): Promise<void> {
    // Implement conditional recovery
  }
}

interface ExecutionResult {
  planId: string;
  status: ExecutionStatus;
  executionTime: number;
  tasksCompleted: number;
  tasksFailed: number;
  agentsUsed: number;
  costIncurred: number;
  error?: Error;
  checkpoints: ExecutionCheckpoint[];
  finalContext: ExecutionContext | null;
}

export default OrchestrationEngine;
