// AI Security Type Definitions for PAKE System
// Comprehensive types for AI-specific security controls

import { Request, Response, NextFunction } from 'express';

// ==== Core Security Types ====

export interface AISecurityConfig {
  promptInjection: PromptInjectionConfig;
  modelProtection: ModelProtectionConfig;
  costControls: CostControlsConfig;
  adversarialDefense: AdversarialDefenseConfig;
  logging: LoggingConfig;
  redis?: RedisConfig;
}

export interface RedisConfig {
  host: string;
  port: number;
  REDACTED_SECRET?: string;
  db: number;
  keyPrefix: string;
}

export interface LoggingConfig {
  level: 'debug' | 'info' | 'warn' | 'error';
  enableAudit: boolean;
  enableMetrics: boolean;
  logSensitiveData: boolean;
}

// ==== Prompt Injection Prevention ====

export interface PromptInjectionConfig {
  enabled: boolean;
  strictMode: boolean;
  maxPromptLength: number;
  maxOutputLength: number;
  suspiciousPatterns: string[];
  whitelistedTerms: string[];
  blocklistPatterns: RegExp[];
  semanticAnalysis: boolean;
  contextAnalysis: boolean;
}

export interface PromptAnalysisResult {
  isClean: boolean;
  confidence: number;
  threats: ThreatDetection[];
  sanitizedInput?: string;
  metadata: {
    originalLength: number;
    processedLength: number;
    processingTime: number;
    analysisId: string;
  };
}

export interface ThreatDetection {
  type: ThreatType;
  severity: 'low' | 'medium' | 'high' | 'critical';
  pattern: string;
  description: string;
  position: {
    start: number;
    end: number;
  };
  confidence: number;
}

export enum ThreatType {
  PROMPT_INJECTION = 'prompt_injection',
  SYSTEM_OVERRIDE = 'system_override',
  INSTRUCTION_IGNORE = 'instruction_ignore',
  ROLE_CONFUSION = 'role_confusion',
  JAILBREAK_ATTEMPT = 'jailbreak_attempt',
  INDIRECT_INJECTION = 'indirect_injection',
  CONTEXT_POLLUTION = 'context_pollution',
  EXTRACTION_ATTEMPT = 'extraction_attempt',
}

export interface InputSanitizer {
  sanitize(
    input: string,
    context?: SanitizationContext
  ): Promise<SanitizationResult>;
  analyze(input: string): Promise<PromptAnalysisResult>;
}

export interface SanitizationContext {
  userId: string;
  sessionId: string;
  requestId: string;
  modelType: string;
  conversationHistory?: ConversationMessage[];
}

export interface SanitizationResult {
  sanitized: string;
  wasModified: boolean;
  removedThreats: ThreatDetection[];
  confidence: number;
}

export interface ConversationMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  metadata?: Record<string, any>;
}

// ==== Model Protection ====

export interface ModelProtectionConfig {
  enabled: boolean;
  watermarking: WatermarkingConfig;
  rateLimiting: RateLimitingConfig;
  queryAnalysis: QueryAnalysisConfig;
  extractionPrevention: ExtractionPreventionConfig;
}

export interface WatermarkingConfig {
  enabled: boolean;
  algorithm: 'statistical' | 'lexical' | 'semantic';
  strength: number; // 0.1 to 1.0
  detectability: number; // 0.1 to 1.0
  keyRotationInterval: number; // hours
}

export interface RateLimitingConfig {
  enabled: boolean;
  requestsPerMinute: number;
  tokensPerHour: number;
  burstLimit: number;
  slidingWindow: boolean;
}

export interface QueryAnalysisConfig {
  enabled: boolean;
  patternDetection: boolean;
  behaviorAnalysis: boolean;
  extractionThreshold: number;
  suspiciousQueryPatterns: string[];
}

export interface ExtractionPreventionConfig {
  enabled: boolean;
  maxSimilarQueries: number;
  timeWindow: number; // minutes
  confidenceThreshold: number;
  blockSuspiciousQueries: boolean;
}

export interface ModelWatermark {
  id: string;
  algorithm: string;
  strength: number;
  createdAt: Date;
  expiresAt: Date;
  metadata: Record<string, any>;
}

export interface QueryPattern {
  userId: string;
  pattern: string;
  frequency: number;
  firstSeen: Date;
  lastSeen: Date;
  suspiciousScore: number;
}

export interface ExtractionAttempt {
  userId: string;
  sessionId: string;
  queries: string[];
  similarityScore: number;
  timestamp: Date;
  blocked: boolean;
  reason: string;
}

// ==== Cost Controls ====

export interface CostControlsConfig {
  enabled: boolean;
  defaultTokenBudget: number;
  budgetPeriod: 'hourly' | 'daily' | 'weekly' | 'monthly';
  throttleThreshold: number; // 0.0 to 1.0
  alertThresholds: number[];
  overagePolicy: 'block' | 'throttle' | 'alert';
  costTracking: CostTrackingConfig;
}

export interface CostTrackingConfig {
  trackTokens: boolean;
  trackRequests: boolean;
  trackComputeTime: boolean;
  costPerToken: Record<string, number>; // model -> cost
  costPerRequest: Record<string, number>; // model -> cost
  costPerSecond: Record<string, number>; // model -> cost
}

export interface TokenBudget {
  userId: string;
  budget: number;
  used: number;
  remaining: number;
  period: string;
  periodStart: Date;
  periodEnd: Date;
  alerts: BudgetAlert[];
}

export interface BudgetAlert {
  threshold: number;
  triggered: boolean;
  timestamp?: Date;
  notified: boolean;
}

export interface CostMetrics {
  userId: string;
  modelType: string;
  tokensUsed: number;
  requestCount: number;
  computeTimeMs: number;
  estimatedCost: number;
  timestamp: Date;
}

export interface ThrottleStatus {
  isThrottled: boolean;
  reason: string;
  retryAfter?: number; // seconds
  currentUsage: number;
  limit: number;
}

// ==== Adversarial Defense ====

export interface AdversarialDefenseConfig {
  enabled: boolean;
  perturbationDetection: PerturbationDetectionConfig;
  consistencyChecking: ConsistencyCheckingConfig;
  outputValidation: OutputValidationConfig;
  falsePositiveTarget: number;
}

export interface PerturbationDetectionConfig {
  enabled: boolean;
  threshold: number; // 0.0 to 1.0
  algorithms: string[];
  sensitivity: 'low' | 'medium' | 'high';
}

export interface ConsistencyCheckingConfig {
  enabled: boolean;
  sampleSize: number;
  variationThreshold: number;
  timeoutMs: number;
}

export interface OutputValidationConfig {
  enabled: boolean;
  maxOutputLength: number;
  forbiddenPatterns: string[];
  requireCoherence: boolean;
  factualityChecking: boolean;
}

export interface AdversarialDetection {
  isAdversarial: boolean;
  confidence: number;
  detectionType: AdversarialType;
  perturbations: PerturbationAnalysis[];
  mitigationSuggestions: string[];
}

export enum AdversarialType {
  INPUT_PERTURBATION = 'input_perturbation',
  OUTPUT_MANIPULATION = 'output_manipulation',
  CONTEXT_POISONING = 'context_poisoning',
  GRADIENT_ATTACK = 'gradient_attack',
  MEMBERSHIP_INFERENCE = 'membership_inference',
  MODEL_INVERSION = 'model_inversion',
}

export interface PerturbationAnalysis {
  type: string;
  severity: number;
  location: {
    start: number;
    end: number;
  };
  originalText: string;
  perturbedText: string;
  confidence: number;
}

export interface ConsistencyCheck {
  inputId: string;
  variations: string[];
  responses: string[];
  consistencyScore: number;
  isConsistent: boolean;
  anomalies: string[];
}

// ==== API Security ====

export interface AISecurityMiddleware {
  (req: Request, res: Response, next: NextFunction): Promise<void>;
}

export interface AISecurityRequest extends Request {
  security: {
    analysisId: string;
    threatLevel: 'none' | 'low' | 'medium' | 'high' | 'critical';
    sanitizedInput?: string;
    watermark?: ModelWatermark;
    budget?: TokenBudget;
    throttled?: boolean;
  };
}

export interface SecurityContext {
  userId: string;
  sessionId: string;
  requestId: string;
  modelType: string;
  inputTokens: number;
  outputTokens: number;
  startTime: Date;
  endTime?: Date;
  threats: ThreatDetection[];
  watermark?: ModelWatermark;
  cost?: number;
}

// ==== Monitoring & Analytics ====

export interface SecurityMetrics {
  promptInjections: {
    detected: number;
    blocked: number;
    bypassed: number;
    falsePositives: number;
  };
  modelProtection: {
    extractionAttempts: number;
    watermarksApplied: number;
    queriesAnalyzed: number;
  };
  costControls: {
    budgetExceeded: number;
    throttledRequests: number;
    totalCost: number;
  };
  adversarialDefense: {
    attacksDetected: number;
    attacksBlocked: number;
    falsePositives: number;
  };
}

export interface SecurityAlert {
  id: string;
  type: string;
  severity: 'info' | 'warning' | 'critical';
  message: string;
  context: SecurityContext;
  timestamp: Date;
  resolved: boolean;
  resolvedAt?: Date;
  resolvedBy?: string;
}

export interface AuditEvent {
  id: string;
  userId: string;
  action: string;
  resource: string;
  outcome: 'success' | 'failure' | 'blocked';
  threatLevel: string;
  timestamp: Date;
  metadata: Record<string, any>;
}

// ==== Configuration Validation ====

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

export interface ConfigValidator {
  validate(config: AISecurityConfig): ValidationResult;
}

// ==== Plugin System ====

export interface SecurityPlugin {
  name: string;
  version: string;
  initialize(config: AISecurityConfig): Promise<void>;
  analyze(input: string, context: SecurityContext): Promise<PluginResult>;
  cleanup?(): Promise<void>;
}

export interface PluginResult {
  pluginName: string;
  threats: ThreatDetection[];
  metadata: Record<string, any>;
  processingTime: number;
}

// ==== Error Types ====

export class AISecurityError extends Error {
  public readonly code: string;
  public readonly context: SecurityContext;

  constructor(message: string, code: string, context: SecurityContext) {
    super(message);
    this.name = 'AISecurityError';
    this.code = code;
    this.context = context;
  }
}

export class PromptInjectionError extends AISecurityError {
  constructor(message: string, context: SecurityContext) {
    super(message, 'PROMPT_INJECTION_DETECTED', context);
    this.name = 'PromptInjectionError';
  }
}

export class ModelExtractionError extends AISecurityError {
  constructor(message: string, context: SecurityContext) {
    super(message, 'MODEL_EXTRACTION_ATTEMPT', context);
    this.name = 'ModelExtractionError';
  }
}

export class BudgetExceededError extends AISecurityError {
  constructor(message: string, context: SecurityContext) {
    super(message, 'BUDGET_EXCEEDED', context);
    this.name = 'BudgetExceededError';
  }
}

export class AdversarialAttackError extends AISecurityError {
  constructor(message: string, context: SecurityContext) {
    super(message, 'ADVERSARIAL_ATTACK_DETECTED', context);
    this.name = 'AdversarialAttackError';
  }
}
