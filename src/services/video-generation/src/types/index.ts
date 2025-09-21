/**
 * PAKE System - Video Generation Service Types
 * Comprehensive type definitions for video generation with D-ID and HeyGen
 */

export interface VideoGenerationRequest {
  provider: 'did' | 'heygen';
  script: string;
  voiceSettings: VoiceSettings;
  avatarSettings: AvatarSettings;
  videoSettings: VideoSettings;
  callbackUrl?: string;
  metadata?: Record<string, unknown>;
}

export interface VoiceSettings {
  voiceId: string;
  language?: string;
  speed?: number;
  pitch?: number;
  volume?: number;
  emotion?: string;
  stability?: number;
  clarity?: number;
}

export interface AvatarSettings {
  avatarId: string;
  avatarType: 'default' | 'custom' | 'uploaded';
  backgroundType: 'default' | 'color' | 'image' | 'video';
  backgroundValue?: string;
  position?: {
    x: number;
    y: number;
    scale: number;
  };
  clothing?: {
    style: string;
    color: string;
  };
}

export interface VideoSettings {
  resolution: '720p' | '1080p' | '4k';
  aspectRatio: '16:9' | '9:16' | '1:1' | '4:3';
  duration?: number;
  fps: 24 | 30 | 60;
  format: 'mp4' | 'mov' | 'avi';
  quality: 'low' | 'medium' | 'high' | 'ultra';
  watermark?: boolean;
}

export interface VideoGenerationResponse {
  id: string;
  status: VideoStatus;
  videoUrl?: string;
  thumbnailUrl?: string;
  duration?: number;
  createdAt: Date;
  completedAt?: Date;
  error?: string;
  metadata: VideoMetadata;
}

export interface VideoMetadata {
  provider: string;
  processingTime?: number;
  fileSize?: number;
  dimensions: {
    width: number;
    height: number;
  };
  audioSettings: VoiceSettings;
  avatarUsed: AvatarSettings;
  estimatedCost?: number;
  qualityScore?: number;
}

export enum VideoStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

export interface ProviderConfig {
  apiKey: string;
  endpoint: string;
  timeout: number;
  retries: number;
  webhookUrl?: string;
}

export interface DIDConfig extends ProviderConfig {
  presenterId?: string;
  driverUrl?: string;
}

export interface HeyGenConfig extends ProviderConfig {
  templateId?: string;
  videoTemplateId?: string;
}

export interface StorageConfig {
  provider: 'local' | 'aws' | 'minio' | 'gcp';
  bucket?: string;
  region?: string;
  endpoint?: string;
  accessKey?: string;
  secretKey?: string;
  uploadPath: string;
  maxFileSize: number;
  allowedFormats: string[];
}

export interface VideoProcessingJob {
  id: string;
  request: VideoGenerationRequest;
  status: VideoStatus;
  attempts: number;
  maxAttempts: number;
  createdAt: Date;
  updatedAt: Date;
  processingStarted?: Date;
  processingCompleted?: Date;
  error?: string;
  result?: VideoGenerationResponse;
  priority: JobPriority;
}

export enum JobPriority {
  LOW = 0,
  NORMAL = 1,
  HIGH = 2,
  URGENT = 3,
}

export interface QueueMetrics {
  totalJobs: number;
  pendingJobs: number;
  processingJobs: number;
  completedJobs: number;
  failedJobs: number;
  averageProcessingTime: number;
  successRate: number;
}

export interface ProviderMetrics {
  name: string;
  totalRequests: number;
  successfulRequests: number;
  failedRequests: number;
  averageResponseTime: number;
  uptime: number;
  lastError?: string;
  costPerRequest?: number;
}

export interface VideoAnalytics {
  videoId: string;
  views: number;
  downloads: number;
  shares: number;
  duration: number;
  qualityRating?: number;
  userFeedback?: number;
  createdAt: Date;
}

export interface WebhookPayload {
  eventType: 'video.completed' | 'video.failed' | 'video.processing';
  videoId: string;
  status: VideoStatus;
  data: VideoGenerationResponse;
  timestamp: Date;
  signature?: string;
}

export interface UploadedAsset {
  id: string;
  filename: string;
  originalName: string;
  mimeType: string;
  size: number;
  url: string;
  uploadedAt: Date;
  expiresAt?: Date;
  metadata: Record<string, any>;
}

export interface ServiceConfig {
  port: number;
  environment: string;
  logLevel: string;
  corsOrigins: string[];
  rateLimiting: {
    windowMs: number;
    maxRequests: number;
  };
  providers: {
    did: DIDConfig;
    heygen: HeyGenConfig;
  };
  storage: StorageConfig;
  queue: {
    concurrency: number;
    retryDelay: number;
    maxRetries: number;
  };
  monitoring: {
    enabled: boolean;
    metricsInterval: number;
    healthCheckInterval: number;
  };
}

export interface VideoTemplate {
  id: string;
  name: string;
  description: string;
  provider: 'did' | 'heygen';
  avatarSettings: AvatarSettings;
  videoSettings: VideoSettings;
  defaultVoiceSettings: VoiceSettings;
  previewUrl?: string;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}

export interface BulkVideoRequest {
  templateId: string;
  videos: Array<{
    id: string;
    script: string;
    voiceOverrides?: Partial<VoiceSettings>;
    avatarOverrides?: Partial<AvatarSettings>;
    videoOverrides?: Partial<VideoSettings>;
    metadata?: Record<string, unknown>;
  }>;
  priority: JobPriority;
  callbackUrl?: string;
}

export interface ProcessingStats {
  totalProcessed: number;
  averageProcessingTime: number;
  successRate: number;
  errorRate: number;
  costAnalysis: {
    totalCost: number;
    avgCostPerVideo: number;
    costByProvider: Record<string, number>;
  };
  qualityMetrics: {
    avgQualityScore: number;
    highQualityCount: number;
    lowQualityCount: number;
  };
}

export interface Error extends globalThis.Error {
  code?: string;
  statusCode?: number;
  provider?: string;
  videoId?: string;
  details?: Record<string, any>;
}

export type VideoGenerationProvider = 'did' | 'heygen';
export type VideoFormat = 'mp4' | 'mov' | 'avi';
export type VideoResolution = '720p' | '1080p' | '4k';
export type AspectRatio = '16:9' | '9:16' | '1:1' | '4:3';
export type VideoQuality = 'low' | 'medium' | 'high' | 'ultra';
