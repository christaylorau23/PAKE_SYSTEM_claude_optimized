/**
 * Audit System Types
 * Comprehensive type definitions for tamper-proof audit logging
 */

export interface AuditEvent {
  id: string;
  timestamp: string; // ISO8601
  actor: AuditActor;
  action: AuditAction;
  context: AuditContext;
  signature?: string; // Cryptographic hash
  version: string;
}

export interface AuditActor {
  id: string;
  type: ActorType;
  ip?: string;
  session?: string;
  userAgent?: string;
  service?: string;
  metadata?: Record<string, any>;
}

export enum ActorType {
  USER = 'user',
  SERVICE = 'service',
  SYSTEM = 'system',
  API_KEY = 'api_key',
  ANONYMOUS = 'anonymous',
}

export interface AuditAction {
  type: ActionType;
  resource: string;
  resourceId?: string;
  result: ActionResult;
  details?: string;
  metadata?: Record<string, any>;
  duration?: number; // milliseconds
  error?: string;
}

export enum ActionType {
  CREATE = 'create',
  READ = 'read',
  UPDATE = 'update',
  DELETE = 'delete',
  EXECUTE = 'execute',
  LOGIN = 'login',
  LOGOUT = 'logout',
  ACCESS_GRANTED = 'access_granted',
  ACCESS_DENIED = 'access_denied',
  EXPORT = 'export',
  IMPORT = 'import',
  CONFIGURE = 'configure',
  BACKUP = 'backup',
  RESTORE = 'restore',
}

export enum ActionResult {
  SUCCESS = 'success',
  FAILURE = 'failure',
  PARTIAL = 'partial',
  DENIED = 'denied',
  ERROR = 'error',
}

export interface AuditContext {
  requestId?: string;
  parentId?: string; // For nested operations
  traceId?: string; // Distributed tracing
  environment: string;
  application: string;
  version: string;
  metadata?: Record<string, any>;
}

export interface AuditQuery {
  startTime?: Date;
  endTime?: Date;
  actorId?: string;
  actorType?: ActorType;
  actionType?: ActionType;
  resource?: string;
  resourceId?: string;
  result?: ActionResult;
  limit?: number;
  offset?: number;
  orderBy?: string;
  orderDirection?: 'asc' | 'desc';
}

export interface AuditEventBatch {
  events: AuditEvent[];
  batchId: string;
  timestamp: string;
  checksum: string;
}

export interface ComplianceReport {
  id: string;
  type: ComplianceReportType;
  period: {
    start: string;
    end: string;
  };
  summary: ComplianceReportSummary;
  events: AuditEvent[];
  generatedAt: string;
  generatedBy: string;
  signature: string;
}

export enum ComplianceReportType {
  SOC2 = 'soc2',
  HIPAA = 'hipaa',
  GDPR = 'gdpr',
  PCI_DSS = 'pci_dss',
  CUSTOM = 'custom',
}

export interface ComplianceReportSummary {
  totalEvents: number;
  successfulActions: number;
  failedActions: number;
  uniqueUsers: number;
  criticalEvents: number;
  securityIncidents: number;
  dataAccess: {
    reads: number;
    writes: number;
    exports: number;
  };
  authentication: {
    logins: number;
    logouts: number;
    failedAttempts: number;
  };
}

export interface RetentionPolicy {
  id: string;
  name: string;
  description: string;
  criteria: RetentionCriteria;
  hotStorageDays: number; // PostgreSQL
  warmStorageDays: number; // S3
  coldStorageYears: number; // Glacier
  enabled: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface RetentionCriteria {
  resourceTypes?: string[];
  actionTypes?: ActionType[];
  actorTypes?: ActorType[];
  results?: ActionResult[];
  criticalOnly?: boolean;
}

export interface ArchivalJob {
  id: string;
  status: ArchivalJobStatus;
  type: ArchivalType;
  criteria: {
    olderThan: string;
    resourceTypes?: string[];
  };
  progress: {
    total: number;
    processed: number;
    errors: number;
  };
  startedAt: string;
  completedAt?: string;
  error?: string;
}

export enum ArchivalJobStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

export enum ArchivalType {
  WARM_TO_COLD = 'warm_to_cold',
  HOT_TO_WARM = 'hot_to_warm',
  PERMANENT_DELETE = 'permanent_delete',
}

export interface SIEMIntegration {
  id: string;
  name: string;
  type: SIEMType;
  config: SIEMConfig;
  enabled: boolean;
  healthStatus: 'healthy' | 'degraded' | 'failed';
  lastSync: string;
  eventsSent: number;
  errorsCount: number;
}

export enum SIEMType {
  SPLUNK = 'splunk',
  ELASTICSEARCH = 'elasticsearch',
  LOGSTASH = 'logstash',
  SUMO_LOGIC = 'sumo_logic',
  DATADOG = 'datadog',
  KAFKA = 'kafka',
  WEBHOOK = 'webhook',
}

export interface SIEMConfig {
  endpoint?: string;
  apiKey?: string;
  token?: string;
  kafkaBrokers?: string[];
  topic?: string;
  index?: string;
  webhookUrl?: string;
  headers?: Record<string, string>;
  batchSize?: number;
  flushInterval?: number; // milliseconds
}

export interface AuditAlert {
  id: string;
  type: AlertType;
  severity: AlertSeverity;
  title: string;
  description: string;
  events: AuditEvent[];
  triggeredAt: string;
  acknowledged: boolean;
  acknowledgedBy?: string;
  acknowledgedAt?: string;
  resolved: boolean;
  resolvedAt?: string;
}

export enum AlertType {
  SUSPICIOUS_ACTIVITY = 'suspicious_activity',
  FAILED_LOGIN_ATTEMPTS = 'failed_login_attempts',
  PRIVILEGE_ESCALATION = 'privilege_escalation',
  DATA_EXFILTRATION = 'data_exfiltration',
  UNUSUAL_ACCESS_PATTERN = 'unusual_access_pattern',
  SYSTEM_COMPROMISE = 'system_compromise',
  COMPLIANCE_VIOLATION = 'compliance_violation',
}

export enum AlertSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical',
}

export interface AuditAnalytics {
  period: {
    start: string;
    end: string;
  };
  metrics: {
    totalEvents: number;
    eventsPerHour: number[];
    topActors: Array<{ id: string; count: number }>;
    topActions: Array<{ type: string; count: number }>;
    topResources: Array<{ resource: string; count: number }>;
    errorRate: number;
    securityIncidents: number;
  };
  trends: {
    dailyVolume: Array<{ date: string; count: number }>;
    hourlyPattern: Array<{ hour: number; count: number }>;
    userActivity: Array<{ userId: string; activityScore: number }>;
  };
  anomalies: Array<{
    type: string;
    description: string;
    severity: AlertSeverity;
    detectedAt: string;
  }>;
}

export interface AuditConfig {
  database: {
    host: string;
    port: number;
    name: string;
    user: string;
    REDACTED_SECRET: string;
    ssl: boolean;
    maxConnections: number;
  };
  storage: {
    s3: {
      region: string;
      bucket: string;
      accessKeyId: string;
      secretAccessKey: string;
    };
    glacier: {
      region: string;
      vault: string;
    };
  };
  streaming: {
    kafka?: {
      brokers: string[];
      topic: string;
      clientId: string;
    };
    redis?: {
      host: string;
      port: number;
      REDACTED_SECRET?: string;
    };
  };
  security: {
    signingKey: string;
    encryptionKey: string;
    algorithm: string;
  };
  retention: {
    hotStorageDays: number;
    warmStorageDays: number;
    coldStorageYears: number;
  };
  compliance: {
    enabled: boolean;
    reports: ComplianceReportType[];
    alerting: boolean;
  };
}

// Event-specific types for common PAKE operations
export interface UserAuditEvent extends AuditEvent {
  action: AuditAction & {
    resource: 'user';
    metadata: {
      email?: string;
      roles?: string[];
      previousRoles?: string[];
    };
  };
}

export interface VaultAuditEvent extends AuditEvent {
  action: AuditAction & {
    resource: 'vault' | 'note' | 'knowledge';
    metadata: {
      noteId?: string;
      path?: string;
      size?: number;
      tags?: string[];
    };
  };
}

export interface AuthAuditEvent extends AuditEvent {
  action: AuditAction & {
    resource: 'authentication' | 'session' | 'token';
    metadata: {
      method?: 'REDACTED_SECRET' | 'mfa' | 'oauth';
      provider?: string;
      deviceInfo?: any;
    };
  };
}

export interface SystemAuditEvent extends AuditEvent {
  action: AuditAction & {
    resource: 'system' | 'configuration' | 'backup';
    metadata: {
      component?: string;
      configKey?: string;
      backupSize?: number;
    };
  };
}
