/**
 * PAKE System - Main Video Generation Service
 * Orchestrates video generation providers, storage, and monitoring
 */

import express, { Router } from 'express';
import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';
import multer from 'multer';
import { RateLimiterMemory } from 'rate-limiter-flexible';
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
import { DIDProvider } from './providers/DIDProvider';
import { HeyGenProvider } from './providers/HeyGenProvider';
import { StorageManager } from './storage/StorageManager';
import { VideoMonitor } from './monitoring/VideoMonitor';
import { Logger } from './utils/Logger';

export class VideoGenerationService extends EventEmitter {
  private logger: Logger;
  private config: ServiceConfig;
  private didProvider?: DIDProvider;
  private heygenProvider?: HeyGenProvider;
  private storageManager: StorageManager;
  private videoMonitor: VideoMonitor;
  private router: Router;
  private rateLimiter: RateLimiterMemory;
  private uploadHandler: multer.Multer;
  private jobQueue: Map<string, VideoProcessingJob> = new Map();
  private processing = false;

  constructor() {
    super();
    this.logger = new Logger('VideoGenerationService');
    this.config = this.loadConfiguration();

    this.setupProviders();
    this.setupStorage();
    this.setupMonitoring();
    this.setupRateLimiting();
    this.setupFileUpload();
    this.setupRoutes();
    this.startJobProcessor();
  }

  /**
   * Generate video from request
   */
  async generateVideo(
    request: VideoGenerationRequest
  ): Promise<VideoGenerationResponse> {
    const videoId = uuidv4();
    const timer = this.logger.timer('Video generation');

    try {
      this.logger.info('Starting video generation', {
        videoId,
        provider: request.provider,
        scriptLength: request.script.length,
      });

      // Create processing job
      const job: VideoProcessingJob = {
        id: videoId,
        request,
        status: VideoStatus.PENDING,
        attempts: 0,
        maxAttempts: 3,
        createdAt: new Date(),
        updatedAt: new Date(),
        priority: JobPriority.NORMAL,
      };

      // Start monitoring
      this.videoMonitor.startMonitoring(videoId, request);

      // Queue job for processing
      this.jobQueue.set(videoId, job);

      // Process immediately if not busy
      this.processJobQueue();

      timer.end({ videoId, queued: true });
      this.emit('video-queued', { videoId, job });

      // Return initial response
      return {
        id: videoId,
        status: VideoStatus.PENDING,
        createdAt: new Date(),
        metadata: {
          provider: request.provider,
          dimensions: {
            width: this.getResolutionDimensions(
              request.videoSettings.resolution
            ).width,
            height: this.getResolutionDimensions(
              request.videoSettings.resolution
            ).height,
          },
          audioSettings: request.voiceSettings,
          avatarUsed: request.avatarSettings,
        },
      };
    } catch (error) {
      timer.end({ videoId, error: error.message });
      this.logger.error('Failed to queue video generation', error, { videoId });
      throw error;
    }
  }

  /**
   * Generate multiple videos in bulk
   */
  async generateBulkVideos(
    bulkRequest: BulkVideoRequest
  ): Promise<VideoGenerationResponse[]> {
    const results: VideoGenerationResponse[] = [];

    try {
      this.logger.info('Starting bulk video generation', {
        templateId: bulkRequest.templateId,
        videoCount: bulkRequest.videos.length,
      });

      for (const videoRequest of bulkRequest.videos) {
        // Create individual video generation request
        const request: VideoGenerationRequest = {
          provider: 'heygen', // Bulk operations typically use HeyGen
          script: videoRequest.script,
          voiceSettings: {
            voiceId: 'default',
            ...videoRequest.voiceOverrides,
          },
          avatarSettings: {
            avatarId: 'default',
            avatarType: 'default',
            backgroundType: 'default',
            ...videoRequest.avatarOverrides,
          },
          videoSettings: {
            resolution: '1080p',
            aspectRatio: '16:9',
            fps: 30,
            format: 'mp4',
            quality: 'high',
            ...videoRequest.videoOverrides,
          },
          callbackUrl: bulkRequest.callbackUrl,
          metadata: {
            ...videoRequest.metadata,
            bulkId: bulkRequest.templateId,
            individualId: videoRequest.id,
          },
        };

        const response = await this.generateVideo(request);
        results.push(response);
      }

      this.logger.info('Bulk video generation queued', {
        bulkId: bulkRequest.templateId,
        videoCount: results.length,
      });

      return results;
    } catch (error) {
      this.logger.error('Failed to generate bulk videos', error, {
        templateId: bulkRequest.templateId,
      });
      throw error;
    }
  }

  /**
   * Get video status
   */
  async getVideoStatus(
    videoId: string
  ): Promise<VideoGenerationResponse | null> {
    try {
      const job = this.jobQueue.get(videoId);

      if (job?.result) {
        return job.result;
      }

      if (job) {
        return {
          id: videoId,
          status: job.status,
          createdAt: job.createdAt,
          metadata: {
            provider: job.request.provider,
            dimensions: {
              width: this.getResolutionDimensions(
                job.request.videoSettings.resolution
              ).width,
              height: this.getResolutionDimensions(
                job.request.videoSettings.resolution
              ).height,
            },
            audioSettings: job.request.voiceSettings,
            avatarUsed: job.request.avatarSettings,
          },
          error: job.error,
        };
      }

      // Check providers for status
      const didStatus = this.didProvider
        ? await this.didProvider.getVideoStatus(videoId)
        : null;
      if (didStatus) return didStatus;

      const heygenStatus = this.heygenProvider
        ? await this.heygenProvider.getVideoStatus(videoId)
        : null;
      if (heygenStatus) return heygenStatus;

      return null;
    } catch (error) {
      this.logger.error('Failed to get video status', error, { videoId });
      return null;
    }
  }

  /**
   * Cancel video generation
   */
  async cancelVideo(videoId: string): Promise<boolean> {
    try {
      const job = this.jobQueue.get(videoId);

      if (job && job.status === VideoStatus.PENDING) {
        job.status = VideoStatus.CANCELLED;
        job.updatedAt = new Date();
        this.videoMonitor.updateStatus(videoId, VideoStatus.CANCELLED);

        this.logger.info('Video generation cancelled', { videoId });
        return true;
      }

      // Try to cancel with providers
      if (this.didProvider) {
        await this.didProvider.cancelVideo(videoId);
      }

      if (this.heygenProvider) {
        await this.heygenProvider.cancelVideo(videoId);
      }

      return true;
    } catch (error) {
      this.logger.error('Failed to cancel video', error, { videoId });
      return false;
    }
  }

  /**
   * Get service metrics
   */
  getMetrics(): any {
    return {
      service: 'video-generation',
      uptime: process.uptime(),
      timestamp: new Date().toISOString(),
      queue: this.videoMonitor.getQueueMetrics(),
      providers: this.videoMonitor.getProviderMetrics(),
      processing: this.videoMonitor.getProcessingStats(),
      performance: this.videoMonitor.getPerformanceInsights(),
      alerts: this.videoMonitor.getActiveAlerts(),
      memory: {
        heapUsed: Math.round(process.memoryUsage().heapUsed / 1024 / 1024),
        heapTotal: Math.round(process.memoryUsage().heapTotal / 1024 / 1024),
        rss: Math.round(process.memoryUsage().rss / 1024 / 1024),
      },
      nodejs: process.version,
    };
  }

  /**
   * Get Express router
   */
  getRouter(): Router {
    return this.router;
  }

  /**
   * Health check
   */
  async getHealthStatus(): Promise<any> {
    const health = {
      service: 'video-generation',
      status: 'healthy',
      timestamp: new Date().toISOString(),
      providers: {} as any,
      storage: 'healthy',
      queue: {
        size: this.jobQueue.size,
        processing: this.processing,
      },
    };

    // Check provider health
    if (this.didProvider) {
      const didHealth = await this.didProvider.getHealthStatus();
      health.providers.did = didHealth.healthy ? 'healthy' : 'unhealthy';
    }

    if (this.heygenProvider) {
      const heygenHealth = await this.heygenProvider.getHealthStatus();
      health.providers.heygen = heygenHealth.healthy ? 'healthy' : 'unhealthy';
    }

    // Overall status
    const unhealthyProviders = Object.values(health.providers).filter(
      status => status === 'unhealthy'
    );
    if (unhealthyProviders.length > 0) {
      health.status = 'degraded';
    }

    return health;
  }

  /**
   * Load service configuration
   */
  private loadConfiguration(): ServiceConfig {
    return {
      port: parseInt(process.env.VIDEO_GENERATION_PORT || '9001'),
      environment: process.env.NODE_ENV || 'development',
      logLevel: process.env.LOG_LEVEL || 'info',
      corsOrigins: process.env.ALLOWED_ORIGINS?.split(',') || [
        'http://localhost:3000',
      ],
      rateLimiting: {
        windowMs: 60000, // 1 minute
        maxRequests: 100,
      },
      providers: {
        did: {
          apiKey: process.env.DID_API_KEY || '',
          endpoint: process.env.DID_API_ENDPOINT || 'https://api.d-id.com',
          timeout: parseInt(process.env.DID_TIMEOUT || '300000'),
          retries: parseInt(process.env.DID_RETRIES || '3'),
        },
        heygen: {
          apiKey: process.env.HEYGEN_API_KEY || '',
          endpoint: process.env.HEYGEN_API_ENDPOINT || 'https://api.heygen.com',
          timeout: parseInt(process.env.HEYGEN_TIMEOUT || '300000'),
          retries: parseInt(process.env.HEYGEN_RETRIES || '3'),
        },
      },
      storage: {
        provider: (process.env.STORAGE_PROVIDER as any) || 'local',
        bucket: process.env.STORAGE_BUCKET,
        region: process.env.STORAGE_REGION,
        endpoint: process.env.STORAGE_ENDPOINT,
        accessKey: process.env.STORAGE_ACCESS_KEY,
        secretKey: process.env.STORAGE_SECRET_KEY,
        uploadPath: process.env.UPLOAD_PATH || 'uploads',
        maxFileSize: parseInt(process.env.MAX_FILE_SIZE || '100000000'), // 100MB
        allowedFormats: ['mp4', 'mov', 'avi', 'jpg', 'jpeg', 'png'],
      },
      queue: {
        concurrency: parseInt(process.env.QUEUE_CONCURRENCY || '3'),
        retryDelay: parseInt(process.env.RETRY_DELAY || '60000'),
        maxRetries: parseInt(process.env.MAX_RETRIES || '3'),
      },
      monitoring: {
        enabled: process.env.MONITORING_ENABLED !== 'false',
        metricsInterval: parseInt(process.env.METRICS_INTERVAL || '60000'),
        healthCheckInterval: parseInt(
          process.env.HEALTH_CHECK_INTERVAL || '30000'
        ),
      },
    };
  }

  /**
   * Setup video providers
   */
  private setupProviders(): void {
    if (this.config.providers.did.apiKey) {
      this.didProvider = new DIDProvider(this.config.providers.did);
      this.logger.info('D-ID provider initialized');
    }

    if (this.config.providers.heygen.apiKey) {
      this.heygenProvider = new HeyGenProvider(this.config.providers.heygen);
      this.logger.info('HeyGen provider initialized');
    }

    if (!this.didProvider && !this.heygenProvider) {
      throw new Error('At least one video provider must be configured');
    }
  }

  /**
   * Setup storage manager
   */
  private setupStorage(): void {
    this.storageManager = new StorageManager(this.config.storage);
    this.logger.info('Storage manager initialized', {
      provider: this.config.storage.provider,
    });
  }

  /**
   * Setup monitoring
   */
  private setupMonitoring(): void {
    this.videoMonitor = new VideoMonitor();

    // Listen to monitor events
    this.videoMonitor.on('provider-unhealthy', data => {
      this.logger.warn('Provider health alert', data);
    });

    this.videoMonitor.on('status-updated', data => {
      this.emit('video-status-updated', data);
    });

    this.logger.info('Video monitoring initialized');
  }

  /**
   * Setup rate limiting
   */
  private setupRateLimiting(): void {
    this.rateLimiter = new RateLimiterMemory({
      keyGenerator: req => req.ip,
      points: this.config.rateLimiting.maxRequests,
      duration: this.config.rateLimiting.windowMs / 1000,
    });
  }

  /**
   * Setup file upload handling
   */
  private setupFileUpload(): void {
    const storage = multer.memoryStorage();
    this.uploadHandler = multer({
      storage,
      limits: {
        fileSize: this.config.storage.maxFileSize,
      },
      fileFilter: (req, file, cb) => {
        const ext = file.originalname.split('.').pop()?.toLowerCase();
        if (ext && this.config.storage.allowedFormats.includes(ext)) {
          cb(null, true);
        } else {
          cb(
            new Error(
              `Invalid file format. Allowed: ${this.config.storage.allowedFormats.join(', ')}`
            )
          );
        }
      },
    });
  }

  /**
   * Setup HTTP API routes
   */
  private setupRoutes(): void {
    this.router = express.Router();

    // Rate limiting middleware
    this.router.use(async (req, res, next) => {
      try {
        await this.rateLimiter.consume(req.ip);
        next();
      } catch (rejRes) {
        res.status(429).json({
          error: 'Too Many Requests',
          message: 'Rate limit exceeded',
          retryAfter: Math.round(rejRes.msBeforeNext / 1000) || 60,
        });
      }
    });

    // Validation middleware
    const validate = (schema: Joi.ObjectSchema) => {
      return (
        req: express.Request,
        res: express.Response,
        next: express.NextFunction
      ) => {
        const { error } = schema.validate(req.body);
        if (error) {
          res.status(400).json({
            error: 'Validation Error',
            message: error.details[0].message,
            details: error.details,
          });
          return;
        }
        next();
      };
    };

    // Video generation endpoint
    this.router.post(
      '/generate',
      validate(this.getVideoGenerationSchema()),
      async (req, res) => {
        try {
          const result = await this.generateVideo(req.body);
          res.status(201).json(result);
        } catch (error) {
          this.logger.error('Video generation endpoint failed', error);
          res.status(500).json({
            error: 'Video generation failed',
            message: error.message,
          });
        }
      }
    );

    // Bulk video generation endpoint
    this.router.post(
      '/generate/bulk',
      validate(this.getBulkVideoGenerationSchema()),
      async (req, res) => {
        try {
          const results = await this.generateBulkVideos(req.body);
          res.status(201).json({ videos: results });
        } catch (error) {
          this.logger.error('Bulk video generation failed', error);
          res.status(500).json({
            error: 'Bulk video generation failed',
            message: error.message,
          });
        }
      }
    );

    // Get video status
    this.router.get('/videos/:videoId', async (req, res) => {
      try {
        const status = await this.getVideoStatus(req.params.videoId);
        if (!status) {
          res.status(404).json({ error: 'Video not found' });
          return;
        }
        res.json(status);
      } catch (error) {
        this.logger.error('Get video status failed', error, {
          videoId: req.params.videoId,
        });
        res.status(500).json({
          error: 'Failed to get video status',
          message: error.message,
        });
      }
    });

    // Cancel video generation
    this.router.delete('/videos/:videoId', async (req, res) => {
      try {
        const cancelled = await this.cancelVideo(req.params.videoId);
        if (cancelled) {
          res.json({ success: true, message: 'Video generation cancelled' });
        } else {
          res.status(400).json({ error: 'Unable to cancel video generation' });
        }
      } catch (error) {
        this.logger.error('Cancel video failed', error, {
          videoId: req.params.videoId,
        });
        res.status(500).json({
          error: 'Failed to cancel video',
          message: error.message,
        });
      }
    });

    // Upload avatar image
    this.router.post(
      '/avatars/upload',
      this.uploadHandler.single('avatar'),
      async (req, res) => {
        try {
          if (!req.file) {
            res.status(400).json({ error: 'No file uploaded' });
            return;
          }

          const provider = req.body.provider || 'did';
          let avatarId: string;

          if (provider === 'did' && this.didProvider) {
            avatarId = await this.didProvider.uploadAvatar(
              req.file.buffer,
              req.file.originalname
            );
          } else if (provider === 'heygen' && this.heygenProvider) {
            avatarId = await this.heygenProvider.uploadAvatar(
              req.file.buffer,
              req.file.originalname
            );
          } else {
            res
              .status(400)
              .json({ error: 'Invalid provider or provider not configured' });
            return;
          }

          res.json({ avatarId, provider });
        } catch (error) {
          this.logger.error('Avatar upload failed', error);
          res.status(500).json({
            error: 'Avatar upload failed',
            message: error.message,
          });
        }
      }
    );

    // Get available avatars
    this.router.get('/avatars', async (req, res) => {
      try {
        const provider = (req.query.provider as string) || 'did';
        let avatars: any[] = [];

        if (provider === 'did' && this.didProvider) {
          avatars = await this.didProvider.getAvailableAvatars();
        } else if (provider === 'heygen' && this.heygenProvider) {
          avatars = await this.heygenProvider.getAvailableAvatars();
        }

        res.json({ provider, avatars });
      } catch (error) {
        this.logger.error('Get avatars failed', error);
        res.status(500).json({
          error: 'Failed to get avatars',
          message: error.message,
        });
      }
    });

    // Get available voices
    this.router.get('/voices', async (req, res) => {
      try {
        const provider = (req.query.provider as string) || 'did';
        let voices: any[] = [];

        if (provider === 'did' && this.didProvider) {
          voices = await this.didProvider.getAvailableVoices();
        } else if (provider === 'heygen' && this.heygenProvider) {
          voices = await this.heygenProvider.getAvailableVoices();
        }

        res.json({ provider, voices });
      } catch (error) {
        this.logger.error('Get voices failed', error);
        res.status(500).json({
          error: 'Failed to get voices',
          message: error.message,
        });
      }
    });

    // Metrics endpoint
    this.router.get('/metrics', (req, res) => {
      try {
        const metrics = this.getMetrics();
        res.json(metrics);
      } catch (error) {
        this.logger.error('Get metrics failed', error);
        res.status(500).json({
          error: 'Failed to get metrics',
          message: error.message,
        });
      }
    });

    // Health check endpoint
    this.router.get('/health', async (req, res) => {
      try {
        const health = await this.getHealthStatus();
        res.json(health);
      } catch (error) {
        this.logger.error('Health check failed', error);
        res.status(500).json({
          error: 'Health check failed',
          message: error.message,
        });
      }
    });
  }

  /**
   * Get video generation validation schema
   */
  private getVideoGenerationSchema(): Joi.ObjectSchema {
    return Joi.object({
      provider: Joi.string().valid('did', 'heygen').required(),
      script: Joi.string().min(1).max(5000).required(),
      voiceSettings: Joi.object({
        voiceId: Joi.string().required(),
        language: Joi.string().optional(),
        speed: Joi.number().min(0.25).max(4).optional(),
        pitch: Joi.number().min(-20).max(20).optional(),
        volume: Joi.number().min(0).max(100).optional(),
        emotion: Joi.string().optional(),
        stability: Joi.number().min(0).max(1).optional(),
        clarity: Joi.number().min(0).max(1).optional(),
      }).required(),
      avatarSettings: Joi.object({
        avatarId: Joi.string().required(),
        avatarType: Joi.string()
          .valid('default', 'custom', 'uploaded')
          .optional(),
        backgroundType: Joi.string()
          .valid('default', 'color', 'image', 'video')
          .optional(),
        backgroundValue: Joi.string().optional(),
        position: Joi.object({
          x: Joi.number().optional(),
          y: Joi.number().optional(),
          scale: Joi.number().min(0.1).max(3).optional(),
        }).optional(),
      }).required(),
      videoSettings: Joi.object({
        resolution: Joi.string().valid('720p', '1080p', '4k').optional(),
        aspectRatio: Joi.string()
          .valid('16:9', '9:16', '1:1', '4:3')
          .optional(),
        duration: Joi.number().min(1).max(600).optional(),
        fps: Joi.number().valid(24, 30, 60).optional(),
        format: Joi.string().valid('mp4', 'mov', 'avi').optional(),
        quality: Joi.string()
          .valid('low', 'medium', 'high', 'ultra')
          .optional(),
        watermark: Joi.boolean().optional(),
      }).required(),
      callbackUrl: Joi.string().uri().optional(),
      metadata: Joi.object().optional(),
    });
  }

  /**
   * Get bulk video generation validation schema
   */
  private getBulkVideoGenerationSchema(): Joi.ObjectSchema {
    return Joi.object({
      templateId: Joi.string().required(),
      videos: Joi.array()
        .items(
          Joi.object({
            id: Joi.string().required(),
            script: Joi.string().min(1).max(5000).required(),
            voiceOverrides: Joi.object().optional(),
            avatarOverrides: Joi.object().optional(),
            videoOverrides: Joi.object().optional(),
            metadata: Joi.object().optional(),
          })
        )
        .min(1)
        .max(100)
        .required(),
      priority: Joi.number().valid(0, 1, 2, 3).optional(),
      callbackUrl: Joi.string().uri().optional(),
    });
  }

  /**
   * Process job queue
   */
  private async processJobQueue(): Promise<void> {
    if (this.processing) return;

    this.processing = true;

    try {
      const pendingJobs = Array.from(this.jobQueue.values())
        .filter(job => job.status === VideoStatus.PENDING)
        .sort((a, b) => b.priority - a.priority);

      const concurrentJobs = Math.min(
        pendingJobs.length,
        this.config.queue.concurrency
      );

      if (concurrentJobs > 0) {
        const jobs = pendingJobs.slice(0, concurrentJobs);
        await Promise.all(jobs.map(job => this.processJob(job)));
      }
    } catch (error) {
      this.logger.error('Job queue processing error', error);
    } finally {
      this.processing = false;
    }
  }

  /**
   * Process individual job
   */
  private async processJob(job: VideoProcessingJob): Promise<void> {
    const timer = this.logger.timer(`Job processing: ${job.id}`);

    try {
      job.status = VideoStatus.PROCESSING;
      job.processingStarted = new Date();
      job.updatedAt = new Date();
      job.attempts++;

      this.videoMonitor.updateStatus(job.id, VideoStatus.PROCESSING);

      let result: VideoGenerationResponse;

      if (job.request.provider === 'did' && this.didProvider) {
        result = await this.didProvider.generateVideo(job.request);
      } else if (job.request.provider === 'heygen' && this.heygenProvider) {
        result = await this.heygenProvider.generateVideo(job.request);
      } else {
        throw new Error(`Provider ${job.request.provider} not available`);
      }

      // Store video file if URL is provided
      if (result.videoUrl && result.status === VideoStatus.COMPLETED) {
        const videoFilename = `video-${job.id}.${job.request.videoSettings.format}`;
        const storedAsset = await this.storageManager.storeFromUrl(
          result.videoUrl,
          videoFilename,
          { videoId: job.id, provider: job.request.provider }
        );
        result.videoUrl = storedAsset.url;
      }

      job.status = VideoStatus.COMPLETED;
      job.result = result;
      job.processingCompleted = new Date();
      job.updatedAt = new Date();

      this.videoMonitor.updateStatus(job.id, VideoStatus.COMPLETED, {
        quality: result.metadata.qualityScore,
        cost: result.metadata.estimatedCost,
      });

      timer.end({ status: 'completed', duration: result.duration });
      this.emit('job-completed', { job, result });
    } catch (error) {
      job.error = error.message;
      job.updatedAt = new Date();

      if (job.attempts >= job.maxAttempts) {
        job.status = VideoStatus.FAILED;
        this.videoMonitor.updateStatus(job.id, VideoStatus.FAILED, {
          error: error.message,
        });
        this.emit('job-failed', { job, error });
      } else {
        job.status = VideoStatus.PENDING;
        // Retry after delay
        setTimeout(() => this.processJobQueue(), this.config.queue.retryDelay);
      }

      timer.end({ error: error.message, attempt: job.attempts });
      this.logger.error('Job processing failed', error, {
        videoId: job.id,
        attempt: job.attempts,
        maxAttempts: job.maxAttempts,
      });
    }
  }

  /**
   * Start job processor
   */
  private startJobProcessor(): void {
    // Process queue periodically
    setInterval(() => {
      this.processJobQueue();
    }, 5000); // Every 5 seconds

    this.logger.info('Job processor started');
  }

  /**
   * Get resolution dimensions
   */
  private getResolutionDimensions(resolution: string): {
    width: number;
    height: number;
  } {
    switch (resolution) {
      case '720p':
        return { width: 1280, height: 720 };
      case '1080p':
        return { width: 1920, height: 1080 };
      case '4k':
        return { width: 3840, height: 2160 };
      default:
        return { width: 1920, height: 1080 };
    }
  }
}

export default VideoGenerationService;
