/**
 * PAKE System - Trend Record Type Definitions
 *
 * TypeScript interfaces and types for trend records, entities, and related data structures.
 */

export interface TrendRecord {
  // Core identification
  id: string;
  platform: string;
  category: string;
  language: string;
  region: string;

  // Content
  title: string;
  content: string;
  url?: string;
  author?: string;

  // Timestamps (UTC)
  timestamp: Date;
  ingestedAt: Date;

  // Engagement metrics
  engagementCount: number;
  viewCount: number;
  shareCount: number;

  // Content fingerprinting
  contentHash: string; // SHA256 for exact duplicate detection
  similarityHash: string; // MD5 for similarity detection

  // Quality scores (0-1)
  qualityScore: number;
  freshnessScore: number;
  anomalyScore: number;

  // Extracted data
  entities: TrendEntity[];
  anomalies: AnomalyDetection[];

  // Raw data and metadata
  metadata: Record<string, unknown>;
  rawData: Record<string, unknown>;
}

export interface TrendEntity {
  name: string;
  type: EntityType;
  confidence: number; // 0-1 confidence score
  aliases?: string[];
  wikipediaUrl?: string;
  metadata: Record<string, unknown>;
}

export enum EntityType {
  PERSON = 'person',
  ORGANIZATION = 'organization',
  LOCATION = 'location',
  EVENT = 'event',
  PRODUCT = 'product',
  TOPIC = 'topic',
  HASHTAG = 'hashtag',
  MENTION = 'mention',
  URL = 'url',
  OTHER = 'other',
}

export interface AnomalyDetection {
  type: AnomalyFlag;
  severity: number; // 0-1 severity score
  confidence: number; // 0-1 confidence score
  description: string;
  metadata: Record<string, unknown>;
}

export enum AnomalyFlag {
  // Engagement anomalies
  ENGAGEMENT_SPIKE = 'engagement_spike',
  UNUSUAL_VELOCITY = 'unusual_velocity',

  // Content anomalies
  DUPLICATE_CONTENT = 'duplicate_content',
  SUSPICIOUS_PATTERN = 'suspicious_pattern',
  LANGUAGE_ANOMALY = 'language_anomaly',

  // Behavioral anomalies
  COORDINATED_BEHAVIOR = 'coordinated_behavior',
  BOT_ACTIVITY = 'bot_activity',
  ASTROTURFING = 'astroturfing',

  // Temporal anomalies
  OFF_PEAK_ACTIVITY = 'off_peak_activity',
  RAPID_SPREAD = 'rapid_spread',

  // Quality flags
  LOW_QUALITY_CONTENT = 'low_quality_content',
  POTENTIAL_MISINFORMATION = 'potential_misinformation',
  UNVERIFIED_CLAIM = 'unverified_claim',
}

export interface TrendMetrics {
  // Engagement metrics
  likes: number;
  shares: number;
  comments: number;
  views: number;
  clickThroughRate?: number;

  // Reach metrics
  impressions: number;
  reach: number;
  uniqueUsers: number;

  // Velocity metrics
  growthRate: number; // per hour/day
  peakVelocity: number;
  acceleration: number;

  // Network metrics
  influencerScore?: number;
  networkDensity?: number;
  viralCoefficient?: number;
}

export interface SentimentAnalysis {
  score: number; // -1 to 1 (negative to positive)
  confidence: number; // 0-1 confidence
  label: 'positive' | 'negative' | 'neutral' | 'mixed';
  emotions?: {
    joy: number;
    anger: number;
    fear: number;
    sadness: number;
    surprise: number;
    disgust: number;
  };
}

export interface TrendValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
  score: number; // Overall quality score 0-1
}

export interface IngestMetrics {
  // Processing metrics
  totalRecords: number;
  processedRecords: number;
  failedRecords: number;
  duplicateRecords: number;

  // Quality metrics
  averageQualityScore: number;
  averageFreshnessScore: number;
  averageAnomalyScore: number;

  // Performance metrics
  averageProcessingTime: number;
  recordsPerSecond: number;

  // Error analysis
  errorsByType: Map<string, number>;
  errorRate: number;

  // Anomaly statistics
  anomaliesDetected: number;
  anomaliesByType: Map<AnomalyFlag, number>;
}

export interface IngestResult {
  id: string;
  status: 'ingested' | 'duplicate' | 'rejected' | 'failed';
  record?: TrendRecord;
  errors?: string[];
  warnings?: string[];
  processingTime: number;
  anomaliesDetected: AnomalyDetection[];
}

export interface QualityThresholds {
  minQualityScore: number;
  minFreshnessScore: number;
  maxAnomalyScore: number;
  minContentLength: number;
  maxContentLength: number;
  requiredFields: string[];
}

export interface ProcessingConfig {
  // Validation settings
  strictValidation: boolean;
  qualityThresholds: QualityThresholds;

  // Deduplication settings
  enableExactDuplicateDetection: boolean;
  enableSimilarityDetection: boolean;
  similarityThreshold: number; // 0-1

  // Anomaly detection settings
  enableAnomalyDetection: boolean;
  anomalyThresholds: Record<AnomalyFlag, number>;

  // Entity extraction settings
  enableEntityExtraction: boolean;
  minEntityConfidence: number;

  // Performance settings
  batchSize: number;
  maxConcurrency: number;
  timeoutMs: number;

  // Storage settings
  enablePersistence: boolean;
  enableCaching: boolean;
  cacheTTLSeconds: number;
}
