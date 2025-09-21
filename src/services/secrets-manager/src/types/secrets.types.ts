/**
 * Secrets Management Types
 * Comprehensive type definitions for secrets management and encryption
 */

export interface SecretMetadata {
  id: string;
  name: string;
  description?: string;
  version: number;
  createdAt: string;
  updatedAt: string;
  expiresAt?: string;
  rotationPolicy?: RotationPolicy;
  tags: Record<string, string>;
  classification: SecretClassification;
  environment: string;
  application: string;
  owner: string;
  lastAccessedAt?: string;
  accessCount: number;
}

export interface Secret {
  metadata: SecretMetadata;
  value: string | Record<string, unknown>;
  encrypted: boolean;
  algorithm?: string;
  keyId?: string;
}

export interface EncryptedSecret {
  metadata: SecretMetadata;
  encryptedValue: string;
  algorithm: string;
  keyId: string;
  iv: string;
  authTag?: string;
  encryptionContext?: Record<string, string>;
}

export enum SecretClassification {
  PUBLIC = 'public',
  INTERNAL = 'internal',
  CONFIDENTIAL = 'confidential',
  RESTRICTED = 'restricted',
  TOP_SECRET = 'top_secret',
}

export enum SecretType {
  API_KEY = 'api_key',
  DATABASE_PASSWORD = process.env.UNKNOWN,
  DATABASE_CONNECTION = 'database_connection',
  SERVICE_ACCOUNT = 'service_account',
  CERTIFICATE = 'certificate',
  PRIVATE_KEY = 'private_key',
  OAUTH_TOKEN = 'oauth_token',
  ENCRYPTION_KEY = 'encryption_key',
  SIGNING_KEY = 'signing_key',
  JWT_SECRET = process.env.UNKNOWN,
  WEBHOOK_SECRET = 'webhook_secret',
  CONFIG_VALUE = 'config_value',
  USER_CREDENTIAL = 'user_credential',
}

export interface RotationPolicy {
  enabled: boolean;
  intervalDays: number;
  gracePeriodHours: number;
  rotationStrategy: RotationStrategy;
  notificationPolicy: NotificationPolicy;
  backupCount: number;
  autoApprove: boolean;
  requiredApprovers?: string[];
}

export enum RotationStrategy {
  IMMEDIATE = 'immediate',
  GRADUAL = 'gradual',
  BLUE_GREEN = 'blue_green',
  CANARY = 'canary',
}

export interface NotificationPolicy {
  enabled: boolean;
  channels: NotificationChannel[];
  events: NotificationEvent[];
  recipients: string[];
  templates?: Record<string, string>;
}

export enum NotificationChannel {
  EMAIL = 'email',
  SLACK = 'slack',
  WEBHOOK = 'webhook',
  SMS = 'sms',
  PAGERDUTY = 'pagerduty',
}

export enum NotificationEvent {
  ROTATION_STARTED = 'rotation_started',
  ROTATION_COMPLETED = 'rotation_completed',
  ROTATION_FAILED = 'rotation_failed',
  SECRET_ACCESSED = 'secret_accessed',
  SECRET_CREATED = 'secret_created',
  SECRET_UPDATED = 'secret_updated',
  SECRET_DELETED = 'secret_deleted',
  SECRET_EXPIRED = 'secret_expired',
  ACCESS_DENIED = 'access_denied',
  BREACH_DETECTED = 'breach_detected',
}

export interface VaultConfig {
  endpoint: string;
  token?: string;
  roleId?: string;
  secretId?: string;
  namespace?: string;
  tlsConfig?: TLSConfig;
  authMethod: VaultAuthMethod;
  engines: VaultEngineConfig[];
  policies: string[];
  tokenRenewalBuffer: number;
  maxRetries: number;
  retryDelay: number;
}

export enum VaultAuthMethod {
  TOKEN = 'token',
  APPROLE = 'approle',
  KUBERNETES = 'kubernetes',
  AWS_IAM = 'aws_iam',
  AZURE = 'azure',
  GCP = 'gcp',
  USERPASS = 'userpass',
  LDAP = 'ldap',
}

export interface VaultEngineConfig {
  type: VaultEngineType;
  path: string;
  config?: Record<string, any>;
  options?: Record<string, any>;
}

export enum VaultEngineType {
  KV_V1 = 'kv',
  KV_V2 = 'kv-v2',
  DATABASE = 'database',
  TRANSIT = 'transit',
  PKI = 'pki',
  SSH = 'ssh',
  TOTP = 'totp',
  AWS = 'aws',
  AZURE = 'azure',
  GCP = 'gcp',
}

export interface TLSConfig {
  enabled: boolean;
  cert?: string;
  key?: string;
  ca?: string;
  insecure?: boolean;
  serverName?: string;
  clientAuth?: ClientAuth;
}

export enum ClientAuth {
  NO_CLIENT_CERT = 'NoClientCert',
  REQUEST_CLIENT_CERT = 'RequestClientCert',
  REQUIRE_ANY_CLIENT_CERT = 'RequireAnyClientCert',
  VERIFY_CLIENT_CERT_IF_GIVEN = 'VerifyClientCertIfGiven',
  REQUIRE_AND_VERIFY_CLIENT_CERT = 'RequireAndVerifyClientCert',
}

export interface HSMConfig {
  enabled: boolean;
  provider: HSMProvider;
  library: string;
  slot?: number;
  tokenLabel?: string;
  pin?: string;
  mechanisms: HSMMechanism[];
  keyTemplate?: HSMKeyTemplate;
}

export enum HSMProvider {
  AWS_CLOUDHSM = 'aws_cloudhsm',
  AZURE_DEDICATED_HSM = 'azure_dedicated_hsm',
  THALES = 'thales',
  UTIMACO = 'utimaco',
  SAFENET = 'safenet',
  SOFTHSM = 'softhsm',
}

export enum HSMMechanism {
  AES_KEY_GEN = 'CKM_AES_KEY_GEN',
  AES_GCM = 'CKM_AES_GCM',
  RSA_PKCS_KEY_PAIR_GEN = 'CKM_RSA_PKCS_KEY_PAIR_GEN',
  RSA_PKCS = 'CKM_RSA_PKCS',
  RSA_PSS = 'CKM_RSA_PSS',
  ECDSA_KEY_PAIR_GEN = 'CKM_EC_KEY_PAIR_GEN',
  ECDSA = 'CKM_ECDSA',
  SHA256 = 'CKM_SHA256',
  SHA512 = 'CKM_SHA512',
}

export interface HSMKeyTemplate {
  keyType: HSMKeyType;
  keySize?: number;
  curve?: string;
  extractable: boolean;
  persistent: boolean;
  encrypt?: boolean;
  decrypt?: boolean;
  sign?: boolean;
  verify?: boolean;
  wrap?: boolean;
  unwrap?: boolean;
}

export enum HSMKeyType {
  AES = 'CKK_AES',
  RSA = 'CKK_RSA',
  ECDSA = 'CKK_ECDSA',
  GENERIC_SECRET = 'CKK_GENERIC_SECRET',
}

export interface EncryptionConfig {
  algorithms: {
    symmetric: string;
    asymmetric: string;
    hashing: string;
    kdf: string;
  };
  keyDerivation: {
    iterations: number;
    memory: number;
    parallelism: number;
    saltLength: number;
  };
  fieldLevelEncryption: FieldEncryptionConfig[];
  transitEncryption: TransitEncryptionConfig;
}

export interface FieldEncryptionConfig {
  field: string;
  pattern?: string;
  algorithm: string;
  keyId: string;
  searchable?: boolean;
  indexable?: boolean;
}

export interface TransitEncryptionConfig {
  enabled: boolean;
  enforced: boolean;
  protocols: string[];
  cipherSuites: string[];
  minVersion: string;
  maxVersion: string;
  certificateValidation: boolean;
  hostnameVerification: boolean;
}

export interface EncryptionKey {
  id: string;
  name: string;
  algorithm: string;
  keySize: number;
  purpose: KeyPurpose[];
  status: KeyStatus;
  createdAt: string;
  expiresAt?: string;
  rotationPolicy: RotationPolicy;
  versions: EncryptionKeyVersion[];
  metadata: KeyMetadata;
}

export enum KeyPurpose {
  ENCRYPT = 'encrypt',
  DECRYPT = 'decrypt',
  SIGN = 'sign',
  VERIFY = 'verify',
  WRAP = 'wrap',
  UNWRAP = 'unwrap',
}

export enum KeyStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  PENDING_ACTIVATION = 'pending_activation',
  PENDING_DELETION = 'pending_deletion',
  COMPROMISED = 'compromised',
  DESTROYED = 'destroyed',
}

export interface EncryptionKeyVersion {
  version: number;
  keyMaterial?: string; // Only for software keys
  hsmHandle?: string; // Only for HSM keys
  createdAt: string;
  status: KeyStatus;
  usageCount: number;
  lastUsedAt?: string;
}

export interface KeyMetadata {
  origin: KeyOrigin;
  keySpec: string;
  usageStats: KeyUsageStats;
  compliance: ComplianceInfo;
  accessPolicy: AccessPolicy;
}

export enum KeyOrigin {
  GENERATED = 'generated',
  IMPORTED = 'imported',
  HSM = 'hsm',
  EXTERNAL = 'external',
}

export interface KeyUsageStats {
  encryptionCount: number;
  decryptionCount: number;
  signatureCount: number;
  verificationCount: number;
  lastActivity: string;
}

export interface ComplianceInfo {
  fipsValidated: boolean;
  commonCriteria: string[];
  certifications: string[];
  auditTrail: boolean;
}

export interface AccessPolicy {
  principals: Principal[];
  conditions: AccessCondition[];
  permissions: Permission[];
  effect: PolicyEffect;
}

export interface Principal {
  type: PrincipalType;
  identifier: string;
  attributes?: Record<string, string>;
}

export enum PrincipalType {
  USER = 'user',
  SERVICE = 'service',
  ROLE = 'role',
  GROUP = 'group',
  POLICY = 'policy',
}

export interface AccessCondition {
  type: ConditionType;
  operator: ConditionOperator;
  values: string[];
}

export enum ConditionType {
  TIME_OF_DAY = 'time_of_day',
  DATE_RANGE = 'date_range',
  IP_ADDRESS = 'ip_address',
  ENVIRONMENT = 'environment',
  APPLICATION = 'application',
  REQUEST_CONTEXT = 'request_context',
}

export enum ConditionOperator {
  EQUALS = 'equals',
  NOT_EQUALS = 'not_equals',
  IN = 'in',
  NOT_IN = 'not_in',
  GREATER_THAN = 'greater_than',
  LESS_THAN = 'less_than',
  CONTAINS = 'contains',
  MATCHES = 'matches',
}

export enum Permission {
  READ = 'read',
  WRITE = 'write',
  DELETE = 'delete',
  ENCRYPT = 'encrypt',
  DECRYPT = 'decrypt',
  SIGN = 'sign',
  VERIFY = 'verify',
  ROTATE = 'rotate',
  MANAGE = 'manage',
}

export enum PolicyEffect {
  ALLOW = 'allow',
  DENY = 'deny',
}

export interface CertificateConfig {
  commonName: string;
  organization?: string;
  organizationalUnit?: string;
  country?: string;
  state?: string;
  locality?: string;
  keyAlgorithm: string;
  keySize: number;
  validityDays: number;
  extensions?: CertificateExtension[];
  alternativeNames?: AlternativeName[];
}

export interface CertificateExtension {
  oid: string;
  critical: boolean;
  value: string;
}

export interface AlternativeName {
  type: AlternativeNameType;
  value: string;
}

export enum AlternativeNameType {
  DNS = 'dns',
  IP = 'ip',
  EMAIL = 'email',
  URI = 'uri',
}

export interface Certificate {
  id: string;
  certificate: string;
  privateKey?: string;
  certificateChain?: string[];
  serialNumber: string;
  issuer: string;
  subject: string;
  notBefore: string;
  notAfter: string;
  keyUsage: string[];
  extendedKeyUsage: string[];
  subjectAlternativeNames: AlternativeName[];
  fingerprint: string;
  status: CertificateStatus;
  metadata: CertificateMetadata;
}

export enum CertificateStatus {
  ACTIVE = 'active',
  EXPIRED = 'expired',
  REVOKED = 'revoked',
  PENDING = 'pending',
  RENEWED = 'renewed',
}

export interface CertificateMetadata {
  purpose: CertificatePurpose;
  autoRenew: boolean;
  renewalThreshold: number;
  ocspUrls: string[];
  crlUrls: string[];
  issuerCertificate?: string;
}

export enum CertificatePurpose {
  SERVER_AUTH = 'server_auth',
  CLIENT_AUTH = 'client_auth',
  CODE_SIGNING = 'code_signing',
  EMAIL_PROTECTION = 'email_protection',
  TIMESTAMPING = 'timestamping',
  IPSEC_IKE = 'ipsec_ike',
}

export interface BreakGlassConfig {
  enabled: boolean;
  emergencyContacts: EmergencyContact[];
  procedures: BreakGlassProcedure[];
  approvalRequired: boolean;
  approvers: string[];
  auditTrail: boolean;
  sessionTimeout: number;
  allowedActions: string[];
}

export interface EmergencyContact {
  name: string;
  email: string;
  phone?: string;
  role: string;
  priority: number;
}

export interface BreakGlassProcedure {
  id: string;
  name: string;
  description: string;
  justification: string;
  actions: BreakGlassAction[];
  requiredApprovals: number;
  timeLimit: number;
  audit: boolean;
}

export interface BreakGlassAction {
  type: BreakGlassActionType;
  resource: string;
  permission: string;
  duration?: number;
  conditions?: Record<string, any>;
}

export enum BreakGlassActionType {
  GRANT_ACCESS = 'grant_access',
  BYPASS_POLICY = 'bypass_policy',
  EMERGENCY_DECRYPT = 'emergency_decrypt',
  DISABLE_ROTATION = 'disable_rotation',
  REVEAL_SECRET = 'reveal_secret',
  OVERRIDE_EXPIRATION = 'override_expiration',
}

export interface BreakGlassSession {
  id: string;
  initiator: string;
  procedure: BreakGlassProcedure;
  justification: string;
  approvers: string[];
  status: BreakGlassStatus;
  startTime: string;
  endTime?: string;
  actions: BreakGlassActionLog[];
  auditTrail: string[];
}

export enum BreakGlassStatus {
  PENDING = 'pending',
  APPROVED = 'approved',
  ACTIVE = 'active',
  COMPLETED = 'completed',
  EXPIRED = 'expired',
  REVOKED = 'revoked',
}

export interface BreakGlassActionLog {
  action: BreakGlassAction;
  timestamp: string;
  result: 'success' | 'failure';
  error?: string;
  metadata?: Record<string, any>;
}

export interface SecretsManagerConfig {
  vault: VaultConfig;
  hsm?: HSMConfig;
  encryption: EncryptionConfig;
  rotation: GlobalRotationConfig;
  breakGlass: BreakGlassConfig;
  audit: AuditConfig;
  compliance: ComplianceConfig;
  performance: PerformanceConfig;
}

export interface GlobalRotationConfig {
  enabled: boolean;
  schedules: Record<string, string>; // cron schedules by secret type
  gracePeriods: Record<string, number>; // hours by secret type
  backupCount: number;
  notifications: NotificationPolicy;
  dryRun: boolean;
}

export interface AuditConfig {
  enabled: boolean;
  logLevel: 'debug' | 'info' | 'warn' | 'error';
  destinations: AuditDestination[];
  retention: number; // days
  encryption: boolean;
  realTime: boolean;
}

export interface AuditDestination {
  type: 'file' | 'syslog' | 'webhook' | 'database' | 'vault';
  config: Record<string, any>;
  filters?: string[];
}

export interface ComplianceConfig {
  standards: ComplianceStandard[];
  reporting: ComplianceReporting;
  validation: ComplianceValidation;
}

export enum ComplianceStandard {
  FIPS_140_2 = 'fips_140_2',
  COMMON_CRITERIA = 'common_criteria',
  SOX = 'sox',
  PCI_DSS = 'pci_dss',
  HIPAA = 'hipaa',
  GDPR = 'gdpr',
  SOC2 = 'soc2',
  ISO_27001 = 'iso_27001',
}

export interface ComplianceReporting {
  enabled: boolean;
  schedule: string;
  recipients: string[];
  standards: ComplianceStandard[];
  includeMetrics: boolean;
}

export interface ComplianceValidation {
  enabled: boolean;
  rules: ComplianceRule[];
  enforcement: 'warn' | 'block';
}

export interface ComplianceRule {
  id: string;
  name: string;
  standard: ComplianceStandard;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  condition: string;
  remediation: string;
}

export interface PerformanceConfig {
  caching: CachingConfig;
  pooling: PoolingConfig;
  timeouts: TimeoutConfig;
  optimization: OptimizationConfig;
}

export interface CachingConfig {
  enabled: boolean;
  ttl: number; // seconds
  maxSize: number;
  strategy: 'lru' | 'lfu' | 'ttl';
  encryption: boolean;
}

export interface PoolingConfig {
  vault: {
    maxConnections: number;
    idleTimeout: number;
    connectionTimeout: number;
  };
  hsm: {
    maxSessions: number;
    sessionTimeout: number;
  };
}

export interface TimeoutConfig {
  vault: {
    read: number;
    write: number;
    auth: number;
  };
  hsm: {
    operation: number;
    session: number;
  };
  network: {
    connect: number;
    request: number;
  };
}

export interface OptimizationConfig {
  batchOperations: boolean;
  connectionReuse: boolean;
  compression: boolean;
  preloadSecrets: string[];
}

// Event types for secrets management
export interface SecretEvent {
  id: string;
  timestamp: string;
  type: SecretEventType;
  secretId: string;
  actor: string;
  source: string;
  metadata?: Record<string, any>;
  success: boolean;
  error?: string;
}

export enum SecretEventType {
  SECRET_READ = 'secret_read',
  SECRET_WRITE = 'secret_write',
  SECRET_DELETE = 'secret_delete',
  KEY_GENERATE = 'key_generate',
  KEY_ROTATE = 'key_rotate',
  ENCRYPT = 'encrypt',
  DECRYPT = 'decrypt',
  SIGN = 'sign',
  VERIFY = 'verify',
  CERTIFICATE_ISSUE = 'certificate_issue',
  CERTIFICATE_RENEW = 'certificate_renew',
  BREAK_GLASS_ACTIVATE = 'break_glass_activate',
  POLICY_VIOLATION = 'policy_violation',
}
