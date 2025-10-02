/**
 * PAKE System - Refactored Video Generation Service (SRP Compliant)
 * Single Responsibility: Orchestrating video generation workflow
 *
 * This service now follows SRP by delegating specific responsibilities to focused managers:
 * - Configuration: VideoConfigManager
 * - Provider Management: VideoProviderRegistry
 * - Storage: VideoStorageManager
 * - Monitoring: VideoMonitor
 * - Rate Limiting: VideoRateLimiter
 * - Job Processing: VideoJobProcessor
 */

import express, { Router } from 'express';
import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';
import multer from 'multer';
import Joi from 'joi';

import {
  VideoGenerationRequest,
  VideoGenerationResponse,
  VideoStatus,
  ServiceConfig,
  VideoProcessingJob,
  JobPriority,
  BulkVideoRequest,
} from './types';
import { Logger } from './utils/Logger';

// Import decomposed managers
import { VideoConfigManager, VideoConfigManagerImpl } from './managers/VideoConfigManager';
import { VideoProviderRegistry, VideoProviderRegistryImpl } from './managers/VideoProviderRegistry';
import { VideoStorageManager, VideoStorageManagerImpl } from './managers/VideoStorageManager';
import { VideoMonitor, VideoMonitorImpl } from './managers/VideoMonitor';
import { VideoRateLimiter, VideoRateLimiterImpl } from './managers/VideoRateLimiter';
import { VideoJobProcessor, VideoJobProcessorImpl } from './managers/VideoJobProcessor';

export class VideoGenerationService extends EventEmitter {
  private logger: Logger;

  // Decomposed managers - each with single responsibility
  private configManager: VideoConfigManager;
  private providerRegistry: VideoProviderRegistry;
  private storageManager: VideoStorageManager;
  private monitor: VideoMonitor;
  private rateLimiter: VideoRateLimiter;
  private jobProcessor: VideoJobProcessor;

  private router: Router;
  private uploadHandler: multer.Multer;

  constructor() {
    super();
    this.logger = new Logger('VideoGenerationService');

    // Initialize decomposed managers
    this.initializeManagers();

    // Setup remaining components
    this.setupFileUpload();
    this.setupRoutes();
  }

  /**
   * Initialize all decomposed managers with dependency injection
   */
  private initializeManagers(): void {
    // Configuration manager
    this.configManager = new VideoConfigManagerImpl();

    // Provider registry
    this.providerRegistry = new VideoProviderRegistryImpl();

    // Storage manager
    this.storageManager = new VideoStorageManagerImpl(
      this.createStorageImplementation(),
      this.logger
    );

    // Monitor
    this.monitor = new VideoMonitorImpl(this.logger);

    // Rate limiter
    this.rateLimiter = new VideoRateLimiterImpl(this.logger);

    // Job processor
    this.jobProcessor = new VideoJobProcessorImpl(
      this.logger,
      this.configManager.getConfig().maxConcurrentJobs
    );
  }

  /**
   * Generate video from request - orchestrates the workflow
   */
  async generateVideo(request: VideoGenerationRequest): Promise<VideoGenerationResponse> {
    const videoId = uuidv4();
    const timer = this.logger.timer('Video generation');

    try {
      this.logger.info('Starting video generation', {
        videoId,
        provider: request.provider,
        scriptLength: request.script.length,
      });

      // Validate request
      this.validateRequest(request);

      // Check rate limits
      const canProceed = await this.rateLimiter.checkLimit(request.userId || 'anonymous');
      if (!canProceed) {
        throw new Error('Rate limit exceeded');
      }

      // Consume rate limit
      await this.rateLimiter.consumeLimit(request.userId || 'anonymous');

      // Start monitoring
      this.monitor.startMonitoring(videoId, request);

      // Create processing job
      const job: VideoProcessingJob = {
        id: videoId,
        request,
        status: VideoStatus.PENDING,
        attempts: 0,
        maxAttempts: this.configManager.getConfig().retryAttempts,
        createdAt: new Date(),
        updatedAt: new Date(),
        priority: JobPriority.NORMAL,
      };

      // Add job to processor
      this.jobProcessor.addJob(job);

      timer.end({ videoId, queued: true });
      this.emit('video-queued', { videoId, job });

      // Return initial response
      return {
        id: videoId,
        status: VideoStatus.PENDING,
        createdAt: new Date(),
        metadata: {
          provider: request.provider,
          estimatedDuration: this.estimateDuration(request),
        },
      };
    } catch (error) {
      this.logger.error('Video generation failed', {
        videoId,
        error: error.message,
      });

      this.monitor.recordError(videoId, error.message);
      throw error;
    }
  }

  /**
   * Get video status
   */
  async getVideoStatus(videoId: string): Promise<VideoGenerationResponse> {
    const job = this.jobProcessor.getJobStatus(videoId);
    if (!job) {
      throw new Error(`Video ${videoId} not found`);
    }

    const metrics = this.monitor.getMetrics(videoId);

    return {
      id: videoId,
      status: job.status,
      createdAt: job.createdAt,
      updatedAt: job.updatedAt,
      metadata: {
        attempts: job.attempts,
        duration: metrics.duration,
        lastError: metrics.lastError,
      },
    };
  }

  /**
   * Cancel video generation
   */
  async cancelVideo(videoId: string): Promise<boolean> {
    const cancelled = this.jobProcessor.cancelJob(videoId);
    if (cancelled) {
      this.monitor.stopMonitoring(videoId);
      this.emit('video-cancelled', { videoId });
    }
    return cancelled;
  }

  /**
   * Get service health status
   */
  async getHealthStatus(): Promise<any> {
    const config = this.configManager.getConfig();
    const queueStats = this.jobProcessor.getQueueStats();
    const storageStats = await this.storageManager.getStorageStats();

    return {
      status: 'healthy',
      config: {
        maxConcurrentJobs: config.maxConcurrentJobs,
        timeoutMs: config.timeoutMs,
      },
      queue: queueStats,
      storage: storageStats,
      providers: this.providerRegistry.getAvailableProviders().map(p => p.getName()),
    };
  }

  /**
   * Setup file upload handler
   */
  private setupFileUpload(): void {
    this.uploadHandler = multer({
      storage: multer.memoryStorage(),
      limits: {
        fileSize: 50 * 1024 * 1024, // 50MB
      },
    });
  }

  /**
   * Setup API routes
   */
  private setupRoutes(): void {
    this.router = express.Router();

    // Generate video endpoint
    this.router.post('/generate', async (req, res) => {
      try {
        const response = await this.generateVideo(req.body);
        res.json(response);
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    // Get video status endpoint
    this.router.get('/status/:videoId', async (req, res) => {
      try {
        const response = await this.getVideoStatus(req.params.videoId);
        res.json(response);
      } catch (error) {
        res.status(404).json({ error: error.message });
      }
    });

    // Cancel video endpoint
    this.router.delete('/cancel/:videoId', async (req, res) => {
      try {
        const cancelled = await this.cancelVideo(req.params.videoId);
        res.json({ cancelled });
      } catch (error) {
        res.status(400).json({ error: error.message });
      }
    });

    // Health check endpoint
    this.router.get('/health', async (req, res) => {
      try {
        const health = await this.getHealthStatus();
        res.json(health);
      } catch (error) {
        res.status(500).json({ error: error.message });
      }
    });
  }

  /**
   * Validate video generation request
   */
  private validateRequest(request: VideoGenerationRequest): void {
    const schema = Joi.object({
      script: Joi.string().min(1).max(10000).required(),
      provider: Joi.string().valid('did', 'heygen').optional(),
      userId: Joi.string().optional(),
    });

    const { error } = schema.validate(request);
    if (error) {
      throw new Error(`Invalid request: ${error.details[0].message}`);
    }
  }

  /**
   * Estimate video duration based on script length
   */
  private estimateDuration(request: VideoGenerationRequest): number {
    // Rough estimate: 150 words per minute
    const wordCount = request.script.split(' ').length;
    return Math.ceil(wordCount / 150) * 60; // seconds
  }

  /**
   * Create storage implementation (would be injected in real implementation)
   */
  private createStorageImplementation(): any {
    // This would be a proper storage implementation
    return {
      storeVideo: async (id: string, data: Buffer, metadata: any) => `storage/${id}.mp4`,
      retrieveVideo: async (id: string) => null,
      deleteVideo: async (id: string) => true,
      getVideoMetadata: async (id: string) => null,
      listVideos: async () => [],
    };
  }

  /**
   * Get Express router
   */
  getRouter(): Router {
    return this.router;
  }
}
