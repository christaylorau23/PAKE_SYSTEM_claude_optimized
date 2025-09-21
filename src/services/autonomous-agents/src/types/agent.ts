// Autonomous Agent Framework Type Definitions
// Core types for multi-agent orchestration and task execution

import { EventEmitter } from 'events';

// Base Agent Types
export interface AgentConfig {
  id: string;
  name: string;
  type: AgentType;
  description: string;
  capabilities: string[];
  constraints: AgentConstraints;
  metadata?: Record<string, unknown>;
}

export type AgentType =
  | 'research'
  | 'analysis'
  | 'creation'
  | 'review'
  | 'orchestrator'
  | 'specialist';

export interface AgentConstraints {
  maxExecutionTime: number; // milliseconds
  maxTokensPerTask: number;
  maxApiCallsPerHour: number;
  maxCostPerTask: number; // USD
  allowedTools: string[];
  requiresApproval: boolean;
  canDelegateToOthers: boolean;
  accessLevel: 'read' | 'write' | 'admin';
}

export interface AgentCapabilities {
  webSearch: boolean;
  fileOperations: boolean;
  codeExecution: boolean;
  apiCalls: boolean;
  emailSending: boolean;
  documentCreation: boolean;
  dataAnalysis: boolean;
  imageProcessing: boolean;
  audioProcessing: boolean;
  videoProcessing: boolean;
}

// Task Types
export interface Task {
  id: string;
  title: string;
  description: string;
  type: TaskType;
  priority: TaskPriority;
  status: TaskStatus;
  assignedAgentId?: string;
  parentTaskId?: string;
  subtasks: string[];
  requirements: TaskRequirements;
  context: TaskContext;
  deadline?: Date;
  createdAt: Date;
  updatedAt: Date;
  completedAt?: Date;
  results?: TaskResult;
  approvals?: TaskApproval[];
}

export type TaskType =
  | 'research'
  | 'analysis'
  | 'creation'
  | 'review'
  | 'synthesis'
  | 'validation'
  | 'orchestration';

export type TaskPriority = 'low' | 'medium' | 'high' | 'urgent';

export type TaskStatus =
  | 'pending'
  | 'assigned'
  | 'in_progress'
  | 'waiting_approval'
  | 'approved'
  | 'rejected'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface TaskRequirements {
  inputs: TaskInput[];
  outputs: TaskOutput[];
  tools: string[];
  dependencies: string[];
  qualityThreshold: number; // 0-1
  confidenceThreshold: number; // 0-1
}

export interface TaskInput {
  name: string;
  type: 'text' | 'file' | 'url' | 'data' | 'reference';
  required: boolean;
  value?: unknown;
  validation?: ValidationRule;
}

export interface TaskOutput {
  name: string;
  type: 'text' | 'file' | 'data' | 'analysis' | 'recommendations';
  format: string;
  required: boolean;
}

export interface ValidationRule {
  type: 'regex' | 'range' | 'enum' | 'custom';
  rule: string | number[] | string[] | Function;
  message?: string;
}

export interface TaskContext {
  userId: string;
  sessionId: string;
  project?: string;
  tags: string[];
  metadata: Record<string, any>;
  previousTasks: string[];
  relatedDocuments: string[];
}

export interface TaskResult {
  outputs: Record<string, any>;
  metrics: TaskMetrics;
  logs: TaskLog[];
  artifacts: TaskArtifact[];
  feedback?: TaskFeedback;
  confidence: number;
  quality: number;
}

export interface TaskMetrics {
  executionTime: number;
  tokensUsed: number;
  apiCallsMade: number;
  costIncurred: number;
  toolsUsed: string[];
  errorCount: number;
  retryCount: number;
}

export interface TaskLog {
  timestamp: Date;
  level: 'debug' | 'info' | 'warn' | 'error';
  message: string;
  metadata?: Record<string, unknown>;
}

export interface TaskArtifact {
  id: string;
  name: string;
  type: 'file' | 'data' | 'visualization' | 'report';
  path: string;
  size: number;
  createdAt: Date;
  metadata?: Record<string, unknown>;
}

// Approval and Human-in-the-Loop
export interface TaskApproval {
  id: string;
  taskId: string;
  approverId: string;
  status: 'pending' | 'approved' | 'rejected' | 'expired';
  reason?: string;
  feedback?: string;
  requestedAt: Date;
  respondedAt?: Date;
  expiresAt: Date;
  approvalType: 'execution' | 'result' | 'delegation' | 'resource_usage';
}

export interface TaskFeedback {
  rating: number; // 1-5
  comments?: string;
  suggestions?: string[];
  providedBy: string;
  providedAt: Date;
}

// Orchestration Types
export interface ExecutionPlan {
  id: string;
  title: string;
  description: string;
  pattern: OrchestrationPattern;
  tasks: string[];
  agents: string[];
  timeline: ExecutionTimeline;
  constraints: ExecutionConstraints;
  rollbackStrategy: RollbackStrategy;
  createdAt: Date;
  status: ExecutionStatus;
}

export type OrchestrationPattern =
  | 'sequential'
  | 'parallel'
  | 'hierarchical'
  | 'consensus'
  | 'pipeline'
  | 'conditional'
  | 'loop';

export interface ExecutionTimeline {
  estimatedDuration: number;
  startTime?: Date;
  endTime?: Date;
  milestones: ExecutionMilestone[];
}

export interface ExecutionMilestone {
  name: string;
  targetTime: Date;
  dependencies: string[];
  status: 'pending' | 'completed' | 'missed';
}

export interface ExecutionConstraints {
  maxDuration: number;
  maxCost: number;
  maxAgents: number;
  requiredApprovals: string[];
  failureThreshold: number; // 0-1, percentage of tasks that can fail
}

export interface RollbackStrategy {
  enabled: boolean;
  checkpoints: string[];
  onFailure: 'rollback' | 'continue' | 'pause' | 'escalate';
  cleanupActions: string[];
}

export type ExecutionStatus =
  | 'planning'
  | 'approved'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'rolled_back';

// Agent Communication
export interface AgentMessage {
  id: string;
  fromAgentId: string;
  toAgentId: string | string[]; // single agent or broadcast
  type: MessageType;
  content: unknown;
  priority: 'low' | 'medium' | 'high';
  requiresResponse: boolean;
  correlationId?: string;
  timestamp: Date;
  expiresAt?: Date;
}

export type MessageType =
  | 'task_assignment'
  | 'task_completion'
  | 'collaboration_request'
  | 'resource_sharing'
  | 'status_update'
  | 'error_report'
  | 'approval_request'
  | 'consensus_vote'
  | 'delegation'
  | 'escalation';

export interface CollaborationRequest {
  requestId: string;
  requesterAgentId: string;
  collaborationType: CollaborationType;
  taskId: string;
  requirements: string[];
  expectedContribution: string;
  timeframe: number;
  priority: TaskPriority;
}

export type CollaborationType =
  | 'parallel_processing'
  | 'sequential_handoff'
  | 'peer_review'
  | 'consensus_building'
  | 'expert_consultation'
  | 'resource_sharing';

// Tool Integration
export interface Tool {
  id: string;
  name: string;
  description: string;
  category: ToolCategory;
  version: string;
  capabilities: ToolCapabilities;
  authentication?: ToolAuthentication;
  rateLimit: RateLimit;
  cost: ToolCost;
  documentation: string;
  isActive: boolean;
}

export type ToolCategory =
  | 'web_search'
  | 'file_operations'
  | 'api_integration'
  | 'data_processing'
  | 'communication'
  | 'content_creation'
  | 'analysis'
  | 'visualization'
  | 'automation';

export interface ToolCapabilities {
  inputs: ToolParameter[];
  outputs: ToolParameter[];
  supportsStreaming: boolean;
  supportsBatch: boolean;
  maxConcurrentUses: number;
}

export interface ToolParameter {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'file' | 'array' | 'object';
  required: boolean;
  description: string;
  default?: unknown;
  validation?: ValidationRule;
}

export interface ToolAuthentication {
  type: 'api_key' | 'oauth' | 'basic' | 'bearer_token' | 'none';
  required: boolean;
  scopes?: string[];
}

export interface RateLimit {
  requestsPerMinute: number;
  requestsPerHour: number;
  requestsPerDay: number;
  concurrentRequests: number;
}

export interface ToolCost {
  type: 'free' | 'per_request' | 'per_token' | 'subscription' | 'hybrid';
  amount: number;
  currency: string;
  billingCycle?: 'request' | 'monthly' | 'annual';
}

export interface ToolExecution {
  id: string;
  toolId: string;
  agentId: string;
  taskId: string;
  parameters: Record<string, unknown>;
  startTime: Date;
  endTime?: Date;
  status: 'running' | 'completed' | 'failed' | 'timeout' | 'cancelled';
  result?: unknown;
  error?: string;
  metrics: ToolExecutionMetrics;
}

export interface ToolExecutionMetrics {
  duration: number;
  tokensUsed?: number;
  requestsMade: number;
  dataTransferred: number;
  cost: number;
}

// Monitoring and Analytics
export interface AgentMetrics {
  agentId: string;
  period: MetricsPeriod;
  tasksCompleted: number;
  tasksSuccessful: number;
  averageExecutionTime: number;
  totalCost: number;
  toolUsage: Record<string, number>;
  errorRate: number;
  approvalRate: number;
  userSatisfaction: number;
  efficiency: number;
}

export type MetricsPeriod =
  | 'hour'
  | 'day'
  | 'week'
  | 'month'
  | 'quarter'
  | 'year';

export interface SystemHealth {
  timestamp: Date;
  totalAgents: number;
  activeAgents: number;
  queuedTasks: number;
  runningTasks: number;
  averageResponseTime: number;
  errorRate: number;
  systemLoad: number;
  memoryUsage: number;
  storageUsage: number;
}

// Configuration Types
export interface OrchestrationConfig {
  maxConcurrentTasks: number;
  maxConcurrentAgents: number;
  defaultTimeout: number;
  retryAttempts: number;
  approvalTimeout: number;
  resourceLimits: ResourceLimits;
  notifications: NotificationConfig;
  security: SecurityConfig;
}

export interface ResourceLimits {
  maxMemoryPerAgent: number; // MB
  maxCpuPerAgent: number; // CPU units
  maxStoragePerAgent: number; // MB
  maxNetworkBandwidth: number; // MB/s
  maxApiCallsPerHour: number;
  maxCostPerDay: number; // USD
}

export interface NotificationConfig {
  channels: NotificationChannel[];
  events: NotificationEvent[];
  escalation: EscalationConfig;
}

export interface NotificationChannel {
  type: 'email' | 'slack' | 'webhook' | 'sms' | 'push';
  endpoint: string;
  credentials?: Record<string, string>;
  enabled: boolean;
}

export interface NotificationEvent {
  type: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  channels: string[];
  template?: string;
}

export interface EscalationConfig {
  levels: EscalationLevel[];
  autoEscalate: boolean;
  escalationDelay: number; // minutes
}

export interface EscalationLevel {
  level: number;
  contacts: string[];
  actions: string[];
  timeoutMinutes: number;
}

export interface SecurityConfig {
  authentication: {
    required: boolean;
    methods: string[];
    tokenExpiry: number;
  };
  authorization: {
    rbac: boolean;
    defaultRole: string;
    roleHierarchy: Record<string, string[]>;
  };
  audit: {
    enabled: boolean;
    events: string[];
    retention: number; // days
  };
  encryption: {
    atRest: boolean;
    inTransit: boolean;
    algorithm: string;
  };
}

// Events and State Management
export interface AgentEvent {
  id: string;
  type: string;
  agentId: string;
  taskId?: string;
  timestamp: Date;
  data: Record<string, any>;
  severity: 'debug' | 'info' | 'warning' | 'error' | 'critical';
}

export interface AgentState {
  agentId: string;
  status: AgentStatus;
  currentTask?: string;
  queuedTasks: string[];
  capabilities: AgentCapabilities;
  performance: AgentPerformanceMetrics;
  lastHeartbeat: Date;
  metadata: Record<string, any>;
}

export type AgentStatus =
  | 'initializing'
  | 'idle'
  | 'working'
  | 'waiting'
  | 'paused'
  | 'error'
  | 'offline'
  | 'maintenance';

export interface AgentPerformanceMetrics {
  tasksPerHour: number;
  successRate: number;
  averageTaskTime: number;
  resourceUtilization: ResourceUtilization;
  qualityScore: number;
}

export interface ResourceUtilization {
  cpu: number; // 0-100%
  memory: number; // 0-100%
  network: number; // MB/s
  storage: number; // MB
}

// Abstract Base Classes
export abstract class BaseAgent extends EventEmitter {
  abstract config: AgentConfig;
  abstract execute(task: Task): Promise<TaskResult>;
  abstract canHandle(task: Task): boolean;
  abstract getCapabilities(): AgentCapabilities;
  abstract getStatus(): AgentStatus;
  abstract pause(): Promise<void>;
  abstract resume(): Promise<void>;
  abstract stop(): Promise<void>;
}
