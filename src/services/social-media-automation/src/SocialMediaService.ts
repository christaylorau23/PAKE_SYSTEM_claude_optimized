/**
 * PAKE System - Main Social Media Automation Service
 * Orchestrates multi-platform posting, content generation, and analytics
 */

import express, { Router } from 'express';
import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';
import Bull from 'bull';
import Redis from 'ioredis';
import cron from 'node-cron';
import { RateLimiterMemory } from 'rate-limiter-flexible';
import Joi from 'joi';

import {
  SocialMediaPost,
  PostContent,
  SocialPlatform,
  PostStatus,
  ServiceConfig,
  AIContentRequest,
  Campaign,
  ContentTemplate,
  QueueJob,
  JobType,
  ServiceMetrics,
  PostPriority,
} from './types';

import { TwitterProvider } from './platforms/TwitterProvider';
import { AIContentGenerator } from './content/AIContentGenerator';
import { Logger } from './utils/Logger';

export class SocialMediaService extends EventEmitter {
  private logger: Logger;
  private config: ServiceConfig;
  private redis: Redis;
  private queue: Bull.Queue;
  private router: Router;
  private rateLimiter: RateLimiterMemory;

  // Providers
  private twitterProvider?: TwitterProvider;

  // Services
  private aiGenerator: AIContentGenerator;

  // Storage
  private posts: Map<string, SocialMediaPost> = new Map();
  private campaigns: Map<string, Campaign> = new Map();
  private templates: Map<string, ContentTemplate> = new Map();

  // State
  private initialized = false;

  constructor() {
    super();
    this.logger = new Logger('SocialMediaService');
    this.config = this.loadConfiguration();

    this.setupRedis();
    this.setupQueue();
    this.setupProviders();
    this.setupAI();
    this.setupRateLimiting();
    this.setupRoutes();
    this.setupScheduling();
  }

  /**
   * Initialize the service
   */
  async initialize(): Promise<void> {
    if (this.initialized) return;

    try {
      this.logger.info('Initializing social media service');

      // Test provider connections
      await this.testProviderConnections();

      // Start queue processing
      this.startQueueProcessing();

      // Load templates
      await this.loadContentTemplates();

      this.initialized = true;
      this.logger.info('Social media service initialization complete');
    } catch (error) {
      this.logger.error('Failed to initialize social media service', error);
      throw error;
    }
  }

  /**
   * Create and schedule a social media post
   */
  async createPost(postData: {
    content: PostContent;
    platforms: SocialPlatform[];
    scheduledAt?: Date;
    campaign?: string;
    priority?: PostPriority;
    metadata?: any;
  }): Promise<SocialMediaPost> {
    const postId = uuidv4();
    const timer = this.logger.timer('Create social media post');

    try {
      this.logger.info('Creating social media post', {
        postId,
        platforms: postData.platforms,
        scheduledAt: postData.scheduledAt,
        hasMedia:
          (postData.content.images?.length || 0) +
            (postData.content.videos?.length || 0) >
          0,
      });

      const post: SocialMediaPost = {
        id: postId,
        platforms: postData.platforms,
        content: postData.content,
        scheduledAt: postData.scheduledAt,
        status: postData.scheduledAt ? PostStatus.SCHEDULED : PostStatus.DRAFT,
        metadata: {
          createdBy: 'system',
          priority: postData.priority || PostPriority.NORMAL,
          campaign: postData.campaign,
          contentType: postData.metadata?.contentType || 'original',
          ...postData.metadata,
        },
      };

      // Store post
      this.posts.set(postId, post);

      // Queue for immediate publishing or scheduling
      if (postData.scheduledAt) {
        await this.schedulePost(post);
      } else {
        await this.queuePost(post);
      }

      timer.end({ postId, status: post.status });
      this.emit('post-created', post);

      return post;
    } catch (error) {
      timer.end({ error: error.message });
      this.logger.error('Failed to create social media post', error, {
        postId,
      });
      throw error;
    }
  }

  /**
   * Generate AI content and create post
   */
  async generateAndCreatePost(
    request: AIContentRequest
  ): Promise<SocialMediaPost> {
    try {
      this.logger.info('Generating AI content for post', {
        contentType: request.contentType,
        platforms: request.platforms,
        tone: request.tone,
      });

      // Generate content
      const generatedContent = await this.aiGenerator.generateContent(request);

      // Create post content
      const postContent: PostContent = {
        text: generatedContent.text,
        hashtags: generatedContent.hashtags,
        mentions: [],
        links: [],
      };

      // Create and return post
      return await this.createPost({
        content: postContent,
        platforms: request.platforms,
        metadata: {
          contentType: request.contentType,
          aiGenerated: true,
          confidence: generatedContent.confidence,
          tone: request.tone,
        },
      });
    } catch (error) {
      this.logger.error('Failed to generate and create AI post', error);
      throw error;
    }
  }

  /**
   * Publish post immediately
   */
  async publishPost(postId: string): Promise<boolean> {
    const timer = this.logger.timer('Publish post');

    try {
      const post = this.posts.get(postId);
      if (!post) {
        throw new Error('Post not found');
      }

      this.logger.info('Publishing post immediately', {
        postId,
        platforms: post.platforms,
      });

      post.status = PostStatus.PUBLISHING;
      post.publishedAt = new Date();

      const results = await Promise.allSettled(
        post.platforms.map(platform => this.publishToPlatform(post, platform))
      );

      // Check if all publications succeeded
      const allSucceeded = results.every(
        result => result.status === 'fulfilled'
      );

      post.status = allSucceeded ? PostStatus.PUBLISHED : PostStatus.FAILED;

      timer.end({ postId, success: allSucceeded });
      this.emit('post-published', { post, success: allSucceeded });

      return allSucceeded;
    } catch (error) {
      timer.end({ error: error.message });
      this.logger.error('Failed to publish post', error, { postId });
      return false;
    }
  }

  /**
   * Get post status and analytics
   */
  async getPost(postId: string): Promise<SocialMediaPost | null> {
    try {
      const post = this.posts.get(postId);
      if (!post) return null;

      // Refresh analytics if post is published
      if (post.status === PostStatus.PUBLISHED) {
        await this.refreshPostAnalytics(post);
      }

      return post;
    } catch (error) {
      this.logger.error('Failed to get post', error, { postId });
      return null;
    }
  }

  /**
   * Create campaign
   */
  async createCampaign(campaignData: {
    name: string;
    description: string;
    startDate: Date;
    endDate?: Date;
    platforms: SocialPlatform[];
    goals?: any[];
  }): Promise<Campaign> {
    const campaignId = uuidv4();

    try {
      const campaign: Campaign = {
        id: campaignId,
        name: campaignData.name,
        description: campaignData.description,
        startDate: campaignData.startDate,
        endDate: campaignData.endDate,
        platforms: campaignData.platforms,
        posts: [],
        goals: campaignData.goals || [],
        status: 'draft',
        analytics: {
          totalPosts: 0,
          totalImpressions: 0,
          totalEngagements: 0,
          avgEngagementRate: 0,
          reachGrowth: 0,
          followersGained: 0,
          websiteClicks: 0,
          platformBreakdown: {},
        },
        metadata: {},
      };

      this.campaigns.set(campaignId, campaign);

      this.logger.info('Campaign created', {
        campaignId,
        name: campaignData.name,
      });
      this.emit('campaign-created', campaign);

      return campaign;
    } catch (error) {
      this.logger.error('Failed to create campaign', error, { campaignId });
      throw error;
    }
  }

  /**
   * Get service metrics
   */
  getMetrics(): ServiceMetrics {
    const posts = Array.from(this.posts.values());

    return {
      posts: {
        total: posts.length,
        scheduled: posts.filter(p => p.status === PostStatus.SCHEDULED).length,
        published: posts.filter(p => p.status === PostStatus.PUBLISHED).length,
        failed: posts.filter(p => p.status === PostStatus.FAILED).length,
        byPlatform: this.getPostsByPlatform(posts),
        byStatus: this.getPostsByStatus(posts),
      },
      platforms: {
        connected: this.getConnectedPlatforms(),
        healthy: [], // Would be populated by health checks
        errors: {},
      },
      queue: {
        waiting: 0, // Would be populated from Bull queue
        active: 0,
        completed: 0,
        failed: 0,
        throughput: 0,
      },
      analytics: {
        totalImpressions: this.calculateTotalImpressions(posts),
        totalEngagements: this.calculateTotalEngagements(posts),
        avgEngagementRate: this.calculateAvgEngagementRate(posts),
        topPerformingPost: this.getTopPerformingPost(posts),
        trending: {
          hashtags: this.getTrendingHashtags(posts),
          topics: this.getTrendingTopics(posts),
        },
      },
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
      service: 'social-media-automation',
      status: 'healthy',
      timestamp: new Date().toISOString(),
      platforms: {} as any,
      queue: {
        connected: this.queue ? true : false,
        jobs: this.queue ? await this.queue.getJobCounts() : null,
      },
      ai: {
        available: this.aiGenerator ? true : false,
      },
    };

    // Check platform health
    const platformChecks = await Promise.allSettled([
      this.twitterProvider?.checkHealth(),
    ]);

    platformChecks.forEach((result, index) => {
      const platform = ['twitter'][index];
      if (result.status === 'fulfilled') {
        health.platforms[platform] = result.value?.healthy
          ? 'healthy'
          : 'unhealthy';
      } else {
        health.platforms[platform] = 'unhealthy';
      }
    });

    // Overall status
    const unhealthyPlatforms = Object.values(health.platforms).filter(
      status => status === 'unhealthy'
    );
    if (unhealthyPlatforms.length > 0) {
      health.status = 'degraded';
    }

    return health;
  }

  /**
   * Load service configuration
   */
  private loadConfiguration(): ServiceConfig {
    return {
      port: parseInt(process.env.SOCIAL_MEDIA_PORT || '9002'),
      environment: process.env.NODE_ENV || 'development',
      logLevel: process.env.LOG_LEVEL || 'info',
      corsOrigins: process.env.ALLOWED_ORIGINS?.split(',') || [
        'http://localhost:3000',
      ],
      rateLimiting: {
        windowMs: 60000,
        maxRequests: 100,
      },
      redis: {
        url: process.env.REDIS_URL || 'redis://localhost:6379',
        keyPrefix: 'pake:social:',
      },
      queue: {
        concurrency: parseInt(process.env.QUEUE_CONCURRENCY || '5'),
        retryDelay: parseInt(process.env.RETRY_DELAY || '300000'), // 5 minutes
        maxRetries: parseInt(process.env.MAX_RETRIES || '3'),
        cleanupInterval: parseInt(process.env.CLEANUP_INTERVAL || '3600000'), // 1 hour
      },
      ai: {
        openai: process.env.OPENAI_API_KEY
          ? {
              apiKey: process.env.OPENAI_API_KEY,
              model: process.env.OPENAI_MODEL || 'gpt-4',
            }
          : undefined,
        anthropic: process.env.ANTHROPIC_API_KEY
          ? {
              apiKey: process.env.ANTHROPIC_API_KEY,
              model: process.env.ANTHROPIC_MODEL || 'claude-3-sonnet-20240229',
            }
          : undefined,
      },
      platforms: {
        [SocialPlatform.TWITTER]: {
          platform: SocialPlatform.TWITTER,
          credentials: {
            apiKey: process.env.TWITTER_API_KEY,
            apiSecret: process.env.TWITTER_API_SECRET,
            accessToken: process.env.TWITTER_ACCESS_TOKEN,
            accessTokenSecret: process.env.TWITTER_ACCESS_TOKEN_SECRET,
          },
          settings: {
            enabled: !!process.env.TWITTER_API_KEY,
            autoPost: process.env.TWITTER_AUTO_POST !== 'false',
            requireApproval: process.env.TWITTER_REQUIRE_APPROVAL === 'true',
            timezone: process.env.TIMEZONE || 'UTC',
            contentFilters: [],
          },
          limits: {
            maxTextLength: 280,
            maxImages: 4,
            maxVideos: 1,
            maxHashtags: 2,
            maxMentions: 10,
            dailyPostLimit: 300,
            hourlyPostLimit: 300,
            imageFormats: ['jpg', 'jpeg', 'png', 'gif', 'webp'],
            videoFormats: ['mp4', 'mov'],
            maxImageSize: 5 * 1024 * 1024,
            maxVideoSize: 512 * 1024 * 1024,
            maxVideoDuration: 140,
          },
          features: {
            supportsImages: true,
            supportsVideos: true,
            supportsPolls: true,
            supportsStories: false,
            supportsThreads: true,
            supportsScheduling: false,
            supportsHashtags: true,
            supportsMentions: true,
            supportsLinks: true,
            supportsLinkPreviews: true,
          },
        },
        [SocialPlatform.LINKEDIN]: {
          platform: SocialPlatform.LINKEDIN,
          credentials: {
            clientId: process.env.LINKEDIN_CLIENT_ID,
            clientSecret: process.env.LINKEDIN_CLIENT_SECRET,
            accessToken: process.env.LINKEDIN_ACCESS_TOKEN,
          },
          settings: {
            enabled: !!process.env.LINKEDIN_CLIENT_ID,
            autoPost: process.env.LINKEDIN_AUTO_POST !== 'false',
            requireApproval: process.env.LINKEDIN_REQUIRE_APPROVAL === 'true',
            timezone: process.env.TIMEZONE || 'UTC',
            contentFilters: [],
          },
          limits: {
            maxTextLength: 3000,
            maxImages: 9,
            maxVideos: 1,
            maxHashtags: 5,
            maxMentions: 5,
            dailyPostLimit: 25,
            hourlyPostLimit: 25,
            imageFormats: ['jpg', 'jpeg', 'png'],
            videoFormats: ['mp4', 'avi', 'mov'],
            maxImageSize: 10 * 1024 * 1024,
            maxVideoSize: 200 * 1024 * 1024,
            maxVideoDuration: 600,
          },
          features: {
            supportsImages: true,
            supportsVideos: true,
            supportsPolls: true,
            supportsStories: false,
            supportsThreads: false,
            supportsScheduling: false,
            supportsHashtags: true,
            supportsMentions: true,
            supportsLinks: true,
            supportsLinkPreviews: true,
          },
        },
        [SocialPlatform.INSTAGRAM]: {
          platform: SocialPlatform.INSTAGRAM,
          credentials: {
            accessToken: process.env.INSTAGRAM_ACCESS_TOKEN,
            userId: process.env.INSTAGRAM_USER_ID,
          },
          settings: {
            enabled: !!process.env.INSTAGRAM_ACCESS_TOKEN,
            autoPost: process.env.INSTAGRAM_AUTO_POST !== 'false',
            requireApproval: process.env.INSTAGRAM_REQUIRE_APPROVAL === 'true',
            timezone: process.env.TIMEZONE || 'UTC',
            contentFilters: [],
          },
          limits: {
            maxTextLength: 2200,
            maxImages: 10,
            maxVideos: 1,
            maxHashtags: 30,
            maxMentions: 5,
            dailyPostLimit: 25,
            hourlyPostLimit: 5,
            imageFormats: ['jpg', 'jpeg', 'png'],
            videoFormats: ['mp4', 'mov'],
            maxImageSize: 8 * 1024 * 1024,
            maxVideoSize: 100 * 1024 * 1024,
            maxVideoDuration: 60,
          },
          features: {
            supportsImages: true,
            supportsVideos: true,
            supportsPolls: false,
            supportsStories: true,
            supportsThreads: false,
            supportsScheduling: false,
            supportsHashtags: true,
            supportsMentions: true,
            supportsLinks: false,
            supportsLinkPreviews: false,
          },
        },
        [SocialPlatform.FACEBOOK]: {
          platform: SocialPlatform.FACEBOOK,
          credentials: {
            accessToken: process.env.FACEBOOK_ACCESS_TOKEN,
            pageId: process.env.FACEBOOK_PAGE_ID,
          },
          settings: {
            enabled: !!process.env.FACEBOOK_ACCESS_TOKEN,
            autoPost: process.env.FACEBOOK_AUTO_POST !== 'false',
            requireApproval: process.env.FACEBOOK_REQUIRE_APPROVAL === 'true',
            timezone: process.env.TIMEZONE || 'UTC',
            contentFilters: [],
          },
          limits: {
            maxTextLength: 63206,
            maxImages: 10,
            maxVideos: 1,
            maxHashtags: 30,
            maxMentions: 5,
            dailyPostLimit: 25,
            hourlyPostLimit: 5,
            imageFormats: ['jpg', 'jpeg', 'png', 'gif'],
            videoFormats: ['mp4', 'avi', 'mov'],
            maxImageSize: 4 * 1024 * 1024,
            maxVideoSize: 1024 * 1024 * 1024,
            maxVideoDuration: 240,
          },
          features: {
            supportsImages: true,
            supportsVideos: true,
            supportsPolls: true,
            supportsStories: true,
            supportsThreads: false,
            supportsScheduling: false,
            supportsHashtags: true,
            supportsMentions: true,
            supportsLinks: true,
            supportsLinkPreviews: true,
          },
        },
      },
      content: {
        moderationEnabled: process.env.CONTENT_MODERATION_ENABLED === 'true',
        autoHashtagsEnabled: process.env.AUTO_HASHTAGS_ENABLED !== 'false',
        maxHashtagsPerPost: parseInt(process.env.MAX_HASHTAGS_PER_POST || '5'),
        imageOptimizationEnabled:
          process.env.IMAGE_OPTIMIZATION_ENABLED !== 'false',
        videoTranscodingEnabled:
          process.env.VIDEO_TRANSCODING_ENABLED === 'true',
      },
      scheduling: {
        enabled: process.env.SCHEDULING_ENABLED !== 'false',
        lookAheadDays: parseInt(process.env.SCHEDULING_LOOKAHEAD_DAYS || '7'),
        batchSize: parseInt(process.env.SCHEDULING_BATCH_SIZE || '10'),
      },
      analytics: {
        enabled: process.env.ANALYTICS_ENABLED !== 'false',
        fetchInterval: parseInt(
          process.env.ANALYTICS_FETCH_INTERVAL || '3600000'
        ), // 1 hour
        retentionDays: parseInt(process.env.ANALYTICS_RETENTION_DAYS || '90'),
      },
      webhooks: {
        enabled: process.env.WEBHOOKS_ENABLED === 'true',
        secret: process.env.WEBHOOK_SECRET || '',
        endpoints: {
          [SocialPlatform.TWITTER]: process.env.TWITTER_WEBHOOK_URL || '',
          [SocialPlatform.LINKEDIN]: process.env.LINKEDIN_WEBHOOK_URL || '',
          [SocialPlatform.INSTAGRAM]: process.env.INSTAGRAM_WEBHOOK_URL || '',
          [SocialPlatform.FACEBOOK]: process.env.FACEBOOK_WEBHOOK_URL || '',
        },
      },
    };
  }

  /**
   * Setup Redis connection
   */
  private setupRedis(): void {
    this.redis = new Redis(this.config.redis.url, {
      keyPrefix: this.config.redis.keyPrefix,
      retryDelayOnFailover: 100,
      maxRetriesPerRequest: 3,
    });

    this.redis.on('connect', () => {
      this.logger.info('Redis connected');
    });

    this.redis.on('error', error => {
      this.logger.error('Redis error', error);
    });
  }

  /**
   * Setup Bull queue
   */
  private setupQueue(): void {
    this.queue = new Bull('social-media-posts', this.config.redis.url, {
      defaultJobOptions: {
        removeOnComplete: 100,
        removeOnFail: 50,
        attempts: this.config.queue.maxRetries,
        backoff: {
          type: 'exponential',
          delay: this.config.queue.retryDelay,
        },
      },
    });

    this.queue.on('completed', job => {
      this.logger.info('Queue job completed', {
        jobId: job.id,
        type: job.data.type,
      });
    });

    this.queue.on('failed', (job, error) => {
      this.logger.error('Queue job failed', error, {
        jobId: job.id,
        type: job.data?.type,
      });
    });
  }

  /**
   * Setup social media providers
   */
  private setupProviders(): void {
    // Initialize Twitter provider if configured
    if (this.config.platforms[SocialPlatform.TWITTER].settings.enabled) {
      try {
        this.twitterProvider = new TwitterProvider(
          this.config.platforms[SocialPlatform.TWITTER]
        );
        this.logger.info('Twitter provider initialized');
      } catch (error) {
        this.logger.error('Failed to initialize Twitter provider', error);
      }
    }

    // TODO: Initialize other providers (LinkedIn, Instagram, Facebook)
    // Similar pattern as Twitter provider
  }

  /**
   * Setup AI content generator
   */
  private setupAI(): void {
    this.aiGenerator = new AIContentGenerator(this.config);
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
          retryAfter: Math.round(rejRes.msBeforeNext / 1000) || 60,
        });
      }
    });

    // Create post
    this.router.post('/posts', async (req, res) => {
      try {
        const post = await this.createPost(req.body);
        res.status(201).json(post);
      } catch (error) {
        this.logger.error('Create post endpoint failed', error);
        res
          .status(500)
          .json({ error: 'Failed to create post', message: error.message });
      }
    });

    // Generate AI content and create post
    this.router.post('/posts/ai-generate', async (req, res) => {
      try {
        const post = await this.generateAndCreatePost(req.body);
        res.status(201).json(post);
      } catch (error) {
        this.logger.error('AI generate post endpoint failed', error);
        res
          .status(500)
          .json({ error: 'Failed to generate post', message: error.message });
      }
    });

    // Get post
    this.router.get('/posts/:postId', async (req, res) => {
      try {
        const post = await this.getPost(req.params.postId);
        if (!post) {
          res.status(404).json({ error: 'Post not found' });
          return;
        }
        res.json(post);
      } catch (error) {
        this.logger.error('Get post endpoint failed', error);
        res
          .status(500)
          .json({ error: 'Failed to get post', message: error.message });
      }
    });

    // Publish post
    this.router.post('/posts/:postId/publish', async (req, res) => {
      try {
        const success = await this.publishPost(req.params.postId);
        if (success) {
          res.json({ success: true, message: 'Post published successfully' });
        } else {
          res.status(500).json({ error: 'Failed to publish post' });
        }
      } catch (error) {
        this.logger.error('Publish post endpoint failed', error);
        res
          .status(500)
          .json({ error: 'Failed to publish post', message: error.message });
      }
    });

    // Create campaign
    this.router.post('/campaigns', async (req, res) => {
      try {
        const campaign = await this.createCampaign(req.body);
        res.status(201).json(campaign);
      } catch (error) {
        this.logger.error('Create campaign endpoint failed', error);
        res
          .status(500)
          .json({ error: 'Failed to create campaign', message: error.message });
      }
    });

    // Get metrics
    this.router.get('/metrics', (req, res) => {
      try {
        const metrics = this.getMetrics();
        res.json(metrics);
      } catch (error) {
        this.logger.error('Get metrics endpoint failed', error);
        res
          .status(500)
          .json({ error: 'Failed to get metrics', message: error.message });
      }
    });

    // Health check
    this.router.get('/health', async (req, res) => {
      try {
        const health = await this.getHealthStatus();
        res.json(health);
      } catch (error) {
        this.logger.error('Health check endpoint failed', error);
        res
          .status(500)
          .json({ error: 'Health check failed', message: error.message });
      }
    });
  }

  /**
   * Setup scheduling
   */
  private setupScheduling(): void {
    if (!this.config.scheduling.enabled) return;

    // Schedule post processing every minute
    cron.schedule('* * * * *', () => {
      this.processScheduledPosts();
    });

    this.logger.info('Post scheduling enabled');
  }

  /**
   * Test provider connections
   */
  private async testProviderConnections(): Promise<void> {
    const tests = [];

    if (this.twitterProvider) {
      tests.push(this.twitterProvider.checkHealth());
    }

    const results = await Promise.allSettled(tests);

    results.forEach((result, index) => {
      const provider = ['Twitter'][index];
      if (result.status === 'rejected') {
        this.logger.warn(
          `${provider} provider health check failed`,
          result.reason
        );
      }
    });
  }

  /**
   * Start queue processing
   */
  private startQueueProcessing(): void {
    this.queue.process(
      'publish-post',
      this.config.queue.concurrency,
      async job => {
        const { postId, platform } = job.data;
        const post = this.posts.get(postId);

        if (!post) {
          throw new Error('Post not found');
        }

        return await this.publishToPlatform(post, platform);
      }
    );

    this.logger.info('Queue processing started');
  }

  /**
   * Load content templates
   */
  private async loadContentTemplates(): Promise<void> {
    // In a real implementation, this would load from database or file system
    // For now, create some default templates

    const defaultTemplates: ContentTemplate[] = [
      {
        id: uuidv4(),
        name: 'Product Announcement',
        description: 'Template for announcing new products or features',
        category: 'promotional',
        template:
          '🚀 Exciting news! {{product_name}} is now {{announcement_action}}!\n\n{{description}}\n\n{{call_to_action}}\n\n{{hashtags}}',
        platforms: [SocialPlatform.TWITTER, SocialPlatform.LINKEDIN],
        variables: [
          {
            name: 'product_name',
            type: 'text',
            required: true,
            description: 'Name of the product',
            default: '',
          },
          {
            name: 'announcement_action',
            type: 'text',
            required: true,
            description: 'Action (e.g., available, launching)',
            default: 'available',
          },
          {
            name: 'description',
            type: 'text',
            required: true,
            description: 'Product description',
            default: '',
          },
          {
            name: 'call_to_action',
            type: 'text',
            required: false,
            description: 'Call to action',
            default: 'Learn more:',
          },
          {
            name: 'hashtags',
            type: 'hashtag',
            required: false,
            description: 'Relevant hashtags',
            default: '',
          },
        ],
        examples: [],
        tags: ['product', 'announcement', 'marketing'],
        isActive: true,
        createdAt: new Date(),
        updatedAt: new Date(),
      },
    ];

    defaultTemplates.forEach(template => {
      this.templates.set(template.id, template);
    });

    this.logger.info('Content templates loaded', {
      count: defaultTemplates.length,
    });
  }

  /**
   * Queue post for publishing
   */
  private async queuePost(post: SocialMediaPost): Promise<void> {
    for (const platform of post.platforms) {
      await this.queue.add(
        'publish-post',
        {
          postId: post.id,
          platform,
        },
        {
          priority: post.metadata.priority,
          delay: 0,
        }
      );
    }

    this.logger.info('Post queued for publishing', {
      postId: post.id,
      platforms: post.platforms,
    });
  }

  /**
   * Schedule post for future publishing
   */
  private async schedulePost(post: SocialMediaPost): Promise<void> {
    const delay = post.scheduledAt!.getTime() - Date.now();

    if (delay <= 0) {
      // Should publish immediately
      await this.queuePost(post);
      return;
    }

    for (const platform of post.platforms) {
      await this.queue.add(
        'publish-post',
        {
          postId: post.id,
          platform,
        },
        {
          priority: post.metadata.priority,
          delay,
        }
      );
    }

    this.logger.info('Post scheduled for publishing', {
      postId: post.id,
      platforms: post.platforms,
      scheduledAt: post.scheduledAt,
    });
  }

  /**
   * Process scheduled posts
   */
  private async processScheduledPosts(): Promise<void> {
    // This would typically query database for posts due in the next minute
    // For now, we'll just log that scheduling is active
    this.logger.debug('Processing scheduled posts');
  }

  /**
   * Publish to specific platform
   */
  private async publishToPlatform(
    post: SocialMediaPost,
    platform: SocialPlatform
  ): Promise<boolean> {
    switch (platform) {
      case SocialPlatform.TWITTER: {
        if (!this.twitterProvider)
          throw new Error('Twitter provider not configured');
        const result = await this.twitterProvider.publishPost(post);
        return result.success;
      }

      // TODO: Add other platforms
      default:
        throw new Error(`Platform ${platform} not implemented`);
    }
  }

  /**
   * Refresh post analytics
   */
  private async refreshPostAnalytics(post: SocialMediaPost): Promise<void> {
    // Implementation would fetch latest analytics from platforms
    this.logger.debug('Refreshing post analytics', { postId: post.id });
  }

  // Helper methods for metrics calculation
  private getPostsByPlatform(
    posts: SocialMediaPost[]
  ): Record<SocialPlatform, number> {
    const counts = {} as Record<SocialPlatform, number>;
    posts.forEach(post => {
      post.platforms.forEach(platform => {
        counts[platform] = (counts[platform] || 0) + 1;
      });
    });
    return counts;
  }

  private getPostsByStatus(
    posts: SocialMediaPost[]
  ): Record<PostStatus, number> {
    const counts = {} as Record<PostStatus, number>;
    posts.forEach(post => {
      counts[post.status] = (counts[post.status] || 0) + 1;
    });
    return counts;
  }

  private getConnectedPlatforms(): SocialPlatform[] {
    const connected = [];
    if (this.twitterProvider) connected.push(SocialPlatform.TWITTER);
    // Add other platforms as they're implemented
    return connected;
  }

  private calculateTotalImpressions(posts: SocialMediaPost[]): number {
    return posts.reduce((total, post) => {
      if (post.analytics) {
        return total + post.analytics.aggregated.totalImpressions;
      }
      return total;
    }, 0);
  }

  private calculateTotalEngagements(posts: SocialMediaPost[]): number {
    return posts.reduce((total, post) => {
      if (post.analytics) {
        return total + post.analytics.aggregated.totalEngagements;
      }
      return total;
    }, 0);
  }

  private calculateAvgEngagementRate(posts: SocialMediaPost[]): number {
    const publishedPosts = posts.filter(
      p => p.status === PostStatus.PUBLISHED && p.analytics
    );
    if (publishedPosts.length === 0) return 0;

    const totalRate = publishedPosts.reduce((total, post) => {
      return total + post.analytics!.aggregated.engagementRate;
    }, 0);

    return totalRate / publishedPosts.length;
  }

  private getTopPerformingPost(posts: SocialMediaPost[]): string {
    let topPost = '';
    let maxScore = 0;

    posts.forEach(post => {
      if (post.analytics && post.analytics.aggregated.overallScore > maxScore) {
        maxScore = post.analytics.aggregated.overallScore;
        topPost = post.id;
      }
    });

    return topPost;
  }

  private getTrendingHashtags(posts: SocialMediaPost[]): string[] {
    const hashtags = new Map<string, number>();

    posts.forEach(post => {
      post.content.hashtags?.forEach(hashtag => {
        hashtags.set(hashtag, (hashtags.get(hashtag) || 0) + 1);
      });
    });

    return Array.from(hashtags.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(entry => entry[0]);
  }

  private getTrendingTopics(posts: SocialMediaPost[]): string[] {
    // Simplified topic extraction - in practice would use NLP
    const topics = new Set<string>();

    posts.forEach(post => {
      const words = post.content.text.toLowerCase().split(/\s+/);
      words.forEach(word => {
        if (word.length > 5 && !word.startsWith('@') && !word.startsWith('#')) {
          topics.add(word);
        }
      });
    });

    return Array.from(topics).slice(0, 10);
  }
}

export default SocialMediaService;
