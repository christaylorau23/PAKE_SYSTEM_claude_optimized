// Enterprise Integration Framework Type Definitions
// Comprehensive types for 50+ enterprise platform integrations

export interface IntegrationProvider {
  id: string;
  name: string;
  category: IntegrationCategory;
  type: IntegrationType;
  version: string;
  description: string;
  capabilities: IntegrationCapabilities;
  authentication: AuthenticationConfig;
  rateLimit: RateLimitConfig;
  webhook?: WebhookConfig;
  isActive: boolean;
  metadata: ProviderMetadata;
}

export type IntegrationCategory =
  | 'productivity'
  | 'communication'
  | 'storage'
  | 'crm'
  | 'project_management'
  | 'development'
  | 'analytics'
  | 'security'
  | 'finance'
  | 'marketing';

export type IntegrationType =
  | 'api'
  | 'webhook'
  | 'bot'
  | 'addon'
  | 'plugin'
  | 'connector';

export interface IntegrationCapabilities {
  read: boolean;
  write: boolean;
  delete: boolean;
  subscribe: boolean;
  stream: boolean;
  batch: boolean;
  realtime: boolean;
  supportedOperations: string[];
  dataTypes: string[];
  maxBatchSize?: number;
  streamingTypes?: string[];
}

export interface AuthenticationConfig {
  type: AuthType;
  scopes: string[];
  endpoints: AuthEndpoints;
  tokenStorage: TokenStorageConfig;
  refreshable: boolean;
  expirationTime?: number;
}

export type AuthType =
  | 'oauth2'
  | 'oauth1'
  | 'api_key'
  | 'bearer_token'
  | 'basic'
  | 'jwt'
  | 'custom';

export interface AuthEndpoints {
  authorize?: string;
  token?: string;
  refresh?: string;
  revoke?: string;
  userInfo?: string;
}

export interface TokenStorageConfig {
  encrypted: boolean;
  location: 'database' | 'redis' | 'memory';
  keyPrefix: string;
  ttl?: number;
}

export interface RateLimitConfig {
  requestsPerSecond: number;
  requestsPerMinute: number;
  requestsPerHour: number;
  requestsPerDay: number;
  burstAllowance: number;
  backoffStrategy: 'exponential' | 'linear' | 'fixed';
  retryAttempts: number;
}

export interface WebhookConfig {
  supportedEvents: string[];
  endpoint: string;
  secret?: string;
  signatureHeader?: string;
  verificationMethod: 'hmac' | 'jwt' | 'none';
  maxRetries: number;
  retryInterval: number;
}

export interface ProviderMetadata {
  baseUrl: string;
  apiVersion: string;
  documentation: string;
  status: 'active' | 'deprecated' | 'beta';
  supportLevel: 'full' | 'partial' | 'experimental';
  lastUpdated: Date;
  maintainer: string;
  tags: string[];
}

// Connection Management
export interface IntegrationConnection {
  id: string;
  providerId: string;
  userId: string;
  workspaceId: string;
  name: string;
  status: ConnectionStatus;
  credentials: ConnectionCredentials;
  settings: ConnectionSettings;
  lastSync?: Date;
  lastError?: string;
  createdAt: Date;
  updatedAt: Date;
  metadata: Record<string, any>;
}

export type ConnectionStatus =
  | 'active'
  | 'inactive'
  | 'error'
  | 'expired'
  | 'revoked'
  | 'pending'
  | 'testing';

export interface ConnectionCredentials {
  accessToken?: string;
  refreshToken?: string;
  apiKey?: string;
  secret?: string;
  additionalCredentials?: Record<string, any>;
  expiresAt?: Date;
  scopes?: string[];
}

export interface ConnectionSettings {
  syncFrequency: number; // milliseconds
  batchSize: number;
  enableRealtime: boolean;
  conflictResolution: ConflictResolutionStrategy;
  dataFilters: DataFilter[];
  customSettings: Record<string, any>;
}

export type ConflictResolutionStrategy =
  | 'source_wins'
  | 'target_wins'
  | 'timestamp_wins'
  | 'manual_review'
  | 'merge'
  | 'skip';

export interface DataFilter {
  field: string;
  operator: 'equals' | 'contains' | 'startsWith' | 'endsWith' | 'regex';
  value: any;
  include: boolean;
}

// Data Synchronization
export interface SyncOperation {
  id: string;
  connectionId: string;
  type: SyncType;
  direction: SyncDirection;
  entityType: string;
  status: SyncStatus;
  startTime: Date;
  endTime?: Date;
  recordsProcessed: number;
  recordsSuccessful: number;
  recordsFailed: number;
  errors: SyncError[];
  metrics: SyncMetrics;
  metadata: Record<string, any>;
}

export type SyncType = 'full' | 'incremental' | 'delta' | 'realtime' | 'manual';

export type SyncDirection = 'inbound' | 'outbound' | 'bidirectional';

export type SyncStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'paused';

export interface SyncError {
  recordId?: string;
  error: string;
  code?: string;
  details?: Record<string, any>;
  recoverable: boolean;
  timestamp: Date;
}

export interface SyncMetrics {
  duration: number;
  throughput: number; // records per second
  dataTransferred: number; // bytes
  apiCallsMade: number;
  rateLimitHits: number;
  retryAttempts: number;
}

// Data Models
export interface IntegrationData {
  id: string;
  sourceId: string;
  sourceProvider: string;
  targetId?: string;
  targetProvider?: string;
  entityType: string;
  data: Record<string, any>;
  mappedData?: Record<string, any>;
  metadata: DataMetadata;
  syncStatus: DataSyncStatus;
  conflicts?: DataConflict[];
  version: number;
  lastSynced: Date;
}

export interface DataMetadata {
  sourceTimestamp: Date;
  targetTimestamp?: Date;
  hash: string;
  size: number;
  mimeType?: string;
  encoding?: string;
  checksum?: string;
  relationshipIds?: string[];
}

export type DataSyncStatus =
  | 'synced'
  | 'pending'
  | 'conflict'
  | 'error'
  | 'deleted';

export interface DataConflict {
  id: string;
  field: string;
  sourceValue: any;
  targetValue: any;
  conflictType: ConflictType;
  resolution?: ConflictResolution;
  timestamp: Date;
}

export type ConflictType =
  | 'value_mismatch'
  | 'concurrent_update'
  | 'delete_modify'
  | 'type_mismatch'
  | 'schema_change';

export interface ConflictResolution {
  strategy: ConflictResolutionStrategy;
  resolvedValue: any;
  resolvedBy: string;
  resolvedAt: Date;
  notes?: string;
}

// Mapping and Transformation
export interface DataMapping {
  id: string;
  name: string;
  sourceProvider: string;
  targetProvider: string;
  entityType: string;
  mappingRules: MappingRule[];
  transformations: DataTransformation[];
  isActive: boolean;
  version: number;
  createdAt: Date;
  updatedAt: Date;
}

export interface MappingRule {
  sourceField: string;
  targetField: string;
  required: boolean;
  defaultValue?: any;
  validation?: ValidationRule;
  transformation?: string;
}

export interface DataTransformation {
  id: string;
  name: string;
  type: TransformationType;
  configuration: Record<string, any>;
  script?: string;
  order: number;
}

export type TransformationType =
  | 'field_mapping'
  | 'value_transformation'
  | 'data_enrichment'
  | 'format_conversion'
  | 'validation'
  | 'custom_script';

export interface ValidationRule {
  type: 'regex' | 'range' | 'enum' | 'required' | 'custom';
  rule: string | number[] | string[] | Function;
  message?: string;
}

// Webhook Management
export interface WebhookEvent {
  id: string;
  providerId: string;
  connectionId: string;
  eventType: string;
  payload: Record<string, any>;
  headers: Record<string, string>;
  signature?: string;
  verified: boolean;
  processed: boolean;
  processingError?: string;
  receivedAt: Date;
  processedAt?: Date;
  retryCount: number;
}

export interface WebhookSubscription {
  id: string;
  providerId: string;
  connectionId: string;
  eventTypes: string[];
  endpoint: string;
  secret?: string;
  isActive: boolean;
  createdAt: Date;
  lastEvent?: Date;
  eventCount: number;
  errorCount: number;
}

// Analytics and Monitoring
export interface IntegrationMetrics {
  providerId: string;
  connectionId?: string;
  period: MetricsPeriod;
  metrics: {
    totalOperations: number;
    successfulOperations: number;
    failedOperations: number;
    averageResponseTime: number;
    dataTransferred: number;
    rateLimitHits: number;
    errorRate: number;
    uptime: number;
    cost: number;
  };
  timestamp: Date;
}

export type MetricsPeriod = 'minute' | 'hour' | 'day' | 'week' | 'month';

export interface IntegrationHealth {
  providerId: string;
  status: 'healthy' | 'degraded' | 'down';
  lastCheck: Date;
  responseTime: number;
  errorCount: number;
  issues: HealthIssue[];
  uptime: number;
  availability: number;
}

export interface HealthIssue {
  type: 'connectivity' | 'rate_limit' | 'authentication' | 'quota' | 'other';
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  timestamp: Date;
  resolved: boolean;
  resolvedAt?: Date;
}

// API Gateway Types
export interface APIGatewayRequest {
  id: string;
  method: string;
  path: string;
  headers: Record<string, string>;
  query: Record<string, any>;
  body?: any;
  providerId: string;
  connectionId: string;
  userId: string;
  timestamp: Date;
}

export interface APIGatewayResponse {
  requestId: string;
  status: number;
  headers: Record<string, string>;
  body: any;
  duration: number;
  cached: boolean;
  timestamp: Date;
}

export interface APIGatewayRule {
  id: string;
  name: string;
  priority: number;
  conditions: RuleCondition[];
  actions: RuleAction[];
  isActive: boolean;
}

export interface RuleCondition {
  field: string;
  operator: 'equals' | 'contains' | 'startsWith' | 'regex' | 'exists';
  value: any;
}

export interface RuleAction {
  type: 'transform' | 'filter' | 'cache' | 'rate_limit' | 'redirect' | 'block';
  configuration: Record<string, any>;
}

// Security and Compliance
export interface SecurityPolicy {
  id: string;
  name: string;
  description: string;
  rules: SecurityRule[];
  providerId?: string;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}

export interface SecurityRule {
  id: string;
  type: SecurityRuleType;
  condition: string;
  action: SecurityAction;
  severity: 'low' | 'medium' | 'high' | 'critical';
  enabled: boolean;
}

export type SecurityRuleType =
  | 'data_classification'
  | 'access_control'
  | 'encryption'
  | 'audit'
  | 'compliance'
  | 'threat_detection';

export type SecurityAction =
  | 'allow'
  | 'deny'
  | 'encrypt'
  | 'audit'
  | 'alert'
  | 'quarantine';

export interface AuditLog {
  id: string;
  event: string;
  userId: string;
  providerId: string;
  connectionId?: string;
  action: string;
  resource: string;
  details: Record<string, any>;
  ipAddress?: string;
  userAgent?: string;
  timestamp: Date;
  status: 'success' | 'failure' | 'warning';
}

// Batch Processing
export interface BatchJob {
  id: string;
  type: BatchJobType;
  connectionId: string;
  configuration: BatchJobConfig;
  status: BatchJobStatus;
  progress: BatchProgress;
  startTime: Date;
  endTime?: Date;
  results?: BatchJobResult;
  errors: BatchJobError[];
}

export type BatchJobType =
  | 'sync'
  | 'import'
  | 'export'
  | 'transform'
  | 'validate'
  | 'cleanup';

export type BatchJobStatus =
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'paused';

export interface BatchJobConfig {
  entityType: string;
  filters?: DataFilter[];
  mapping?: string;
  batchSize: number;
  maxRetries: number;
  timeout: number;
  customOptions?: Record<string, any>;
}

export interface BatchProgress {
  totalRecords: number;
  processedRecords: number;
  successfulRecords: number;
  failedRecords: number;
  currentBatch: number;
  totalBatches: number;
  estimatedTimeRemaining?: number;
}

export interface BatchJobResult {
  summary: BatchProgress;
  metrics: SyncMetrics;
  artifacts?: BatchArtifact[];
}

export interface BatchJobError {
  batchNumber: number;
  recordId?: string;
  error: string;
  code?: string;
  recoverable: boolean;
  timestamp: Date;
}

export interface BatchArtifact {
  id: string;
  type: 'report' | 'log' | 'data' | 'error_log';
  name: string;
  location: string;
  size: number;
  createdAt: Date;
}

// Event System
export interface IntegrationEvent {
  id: string;
  type: string;
  source: string;
  providerId: string;
  connectionId?: string;
  data: Record<string, any>;
  timestamp: Date;
  processed: boolean;
  processingAttempts: number;
  lastProcessingAttempt?: Date;
  processingError?: string;
}

export interface EventSubscription {
  id: string;
  eventType: string;
  providerId?: string;
  connectionId?: string;
  handler: string;
  configuration: Record<string, any>;
  isActive: boolean;
  createdAt: Date;
  lastTriggered?: Date;
  triggerCount: number;
  errorCount: number;
}

// Quota and Usage Management
export interface UsageQuota {
  id: string;
  providerId: string;
  connectionId?: string;
  quotaType: QuotaType;
  limit: number;
  period: QuotaPeriod;
  current: number;
  resetTime: Date;
  exceeded: boolean;
  alertThreshold: number;
}

export type QuotaType =
  | 'api_calls'
  | 'data_transfer'
  | 'storage'
  | 'users'
  | 'features'
  | 'cost';

export type QuotaPeriod = 'minute' | 'hour' | 'day' | 'week' | 'month' | 'year';

export interface UsageAlert {
  id: string;
  quotaId: string;
  alertType: 'threshold' | 'limit_exceeded' | 'quota_reset';
  message: string;
  severity: 'info' | 'warning' | 'critical';
  timestamp: Date;
  acknowledged: boolean;
  acknowledgedAt?: Date;
  acknowledgedBy?: string;
}
