/**
 * PAKE System - Video Generation Service Entry Point
 * Bootstraps the video generation service with all providers and monitoring
 */

import dotenv from 'dotenv';
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import path from 'path';
import { VideoGenerationService } from './VideoGenerationService';
import { Logger } from './utils/Logger';

// Load environment variables
dotenv.config();

const logger = new Logger('VideoGenerationBootstrap');

/**
 * Application bootstrap and startup
 */
class Application {
  private app: express.Application;
  private videoService: VideoGenerationService;
  private server: any;
  private port: number;

  constructor() {
    this.port = parseInt(process.env.VIDEO_GENERATION_PORT || '9001');
    this.app = express();
    this.videoService = new VideoGenerationService();

    this.setupMiddleware();
    this.setupRoutes();
    this.setupErrorHandling();
    this.setupGracefulShutdown();
  }

  /**
   * Setup Express middleware
   */
  private setupMiddleware(): void {
    // Security middleware
    this.app.use(
      helmet({
        contentSecurityPolicy: {
          directives: {
            defaultSrc: ["'self'"],
            scriptSrc: ["'self'"],
            styleSrc: ["'self'", "'unsafe-inline'"],
            imgSrc: ["'self'", 'data:', 'https:'],
            mediaSrc: ["'self'", 'https:'],
            frameSrc: ["'none'"],
            objectSrc: ["'none'"],
            upgradeInsecureRequests: [],
          },
        },
        hsts: {
          maxAge: 31536000,
          includeSubDomains: true,
          preload: true,
        },
      })
    );

    // CORS configuration
    this.app.use(
      cors({
        origin: process.env.ALLOWED_ORIGINS?.split(',') || [
          'http://localhost:3000',
        ],
        credentials: true,
        methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
        allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With'],
      })
    );

    // Compression and parsing
    this.app.use(compression());
    this.app.use(express.json({ limit: '50mb' })); // Large limit for video metadata
    this.app.use(express.urlencoded({ extended: true, limit: '50mb' }));

    // Static file serving for uploaded content
    const uploadPath = process.env.UPLOAD_PATH || 'uploads';
    this.app.use('/files', express.static(uploadPath));

    // Request logging
    this.app.use((req, res, next) => {
      const requestId =
        req.headers['x-request-id'] ||
        `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      req.requestId = requestId;

      logger.debug(`${req.method} ${req.path}`, {
        requestId,
        userAgent: req.headers['user-agent'],
        ip: req.ip,
        contentLength: req.headers['content-length'],
      });

      next();
    });
  }

  /**
   * Setup API routes
   */
  private setupRoutes(): void {
    // Health check endpoint
    this.app.get('/health', async (req, res) => {
      try {
        const health = await this.videoService.getHealthStatus();
        const httpStatus = health.status === 'healthy' ? 200 : 503;
        res.status(httpStatus).json(health);
      } catch (error) {
        logger.error('Health check failed', error);
        res.status(503).json({
          status: 'unhealthy',
          error: error.message,
          timestamp: new Date().toISOString(),
        });
      }
    });

    // Readiness check endpoint (for Kubernetes)
    this.app.get('/ready', async (req, res) => {
      try {
        const health = await this.videoService.getHealthStatus();
        if (health.status === 'healthy') {
          res.status(200).json({ status: 'ready' });
        } else {
          res.status(503).json({
            status: 'not ready',
            reason: 'Service not healthy',
          });
        }
      } catch (error) {
        logger.error('Readiness check failed', error);
        res.status(503).json({
          status: 'not ready',
          error: error.message,
        });
      }
    });

    // Metrics endpoint
    this.app.get('/metrics', (req, res) => {
      try {
        const metrics = this.videoService.getMetrics();
        res.status(200).json(metrics);
      } catch (error) {
        logger.error('Failed to get metrics', error);
        res.status(500).json({
          error: 'Failed to retrieve metrics',
          message: error.message,
        });
      }
    });

    // Video generation API routes
    this.app.use('/api/v1', this.videoService.getRouter());

    // Default route - service information
    this.app.get('/', (req, res) => {
      res.json({
        service: 'PAKE Video Generation Service',
        version: process.env.npm_package_version || '1.0.0',
        environment: process.env.NODE_ENV || 'development',
        endpoints: {
          health: '/health',
          ready: '/ready',
          metrics: '/metrics',
          api: '/api/v1',
          docs: '/docs',
        },
        providers: {
          did: !!process.env.DID_API_KEY,
          heygen: !!process.env.HEYGEN_API_KEY,
        },
        features: [
          'AI Avatar Video Generation',
          'Multi-Provider Support (D-ID, HeyGen)',
          'Bulk Video Processing',
          'Custom Avatar Upload',
          'Quality Monitoring',
          'Cost Analytics',
          'Real-time Status Updates',
        ],
      });
    });

    // API documentation endpoint
    this.app.get('/docs', (req, res) => {
      res.json({
        title: 'PAKE Video Generation Service API',
        version: '1.0.0',
        description: 'AI-powered video generation with realistic avatars',
        baseUrl: `http://localhost:${this.port}/api/v1`,
        endpoints: {
          'POST /api/v1/generate': {
            description: 'Generate a single video',
            body: {
              provider: 'did | heygen',
              script: 'string (1-5000 chars)',
              voiceSettings: {
                voiceId: 'string',
                language: 'string (optional)',
                speed: 'number (0.25-4, optional)',
                emotion: 'string (optional)',
              },
              avatarSettings: {
                avatarId: 'string',
                avatarType: 'default | custom | uploaded',
                backgroundType: 'default | color | image | video',
                backgroundValue: 'string (optional)',
              },
              videoSettings: {
                resolution: '720p | 1080p | 4k',
                aspectRatio: '16:9 | 9:16 | 1:1 | 4:3',
                format: 'mp4 | mov | avi',
                quality: 'low | medium | high | ultra',
              },
            },
          },
          'POST /api/v1/generate/bulk':
            'Generate multiple videos from template',
          'GET /api/v1/videos/:videoId': 'Get video generation status',
          'DELETE /api/v1/videos/:videoId': 'Cancel video generation',
          'POST /api/v1/avatars/upload': 'Upload custom avatar image',
          'GET /api/v1/avatars': 'List available avatars',
          'GET /api/v1/voices': 'List available voices',
          'GET /api/v1/metrics': 'Get service metrics',
          'GET /api/v1/health': 'Health check',
        },
        examples: {
          generateVideo: {
            provider: 'did',
            script: 'Hello! Welcome to our amazing product demonstration.',
            voiceSettings: {
              voiceId: 'en-US-AriaNeural',
              speed: 1.0,
              emotion: 'friendly',
            },
            avatarSettings: {
              avatarId: 'amy-jcu3W1jz2s',
              avatarType: 'default',
              backgroundType: 'color',
              backgroundValue: '#f0f8ff',
            },
            videoSettings: {
              resolution: '1080p',
              aspectRatio: '16:9',
              format: 'mp4',
              quality: 'high',
            },
          },
        },
      });
    });

    // 404 handler
    this.app.use('*', (req, res) => {
      res.status(404).json({
        error: 'Not Found',
        message: `Route ${req.method} ${req.originalUrl} not found`,
        availableEndpoints: [
          '/health',
          '/ready',
          '/metrics',
          '/api/v1',
          '/docs',
        ],
      });
    });
  }

  /**
   * Setup error handling middleware
   */
  private setupErrorHandling(): void {
    this.app.use(
      (
        err: any,
        req: express.Request,
        res: express.Response,
        next: express.NextFunction
      ) => {
        logger.error('Unhandled error in request', err, {
          requestId: req.requestId,
          method: req.method,
          path: req.path,
          userAgent: req.headers['user-agent'],
          body: req.body,
        });

        // Don't expose error details in production
        const isDevelopment = process.env.NODE_ENV === 'development';

        // Handle specific error types
        if (err.code === 'LIMIT_FILE_SIZE') {
          res.status(413).json({
            error: 'File Too Large',
            message: 'The uploaded file exceeds the maximum allowed size',
            maxSize: process.env.MAX_FILE_SIZE || '100MB',
          });
          return;
        }

        if (err.code === 'LIMIT_UNEXPECTED_FILE') {
          res.status(400).json({
            error: 'Invalid File Upload',
            message: 'Unexpected file upload field or too many files',
          });
          return;
        }

        res.status(err.status || 500).json({
          error: 'Internal Server Error',
          message: isDevelopment ? err.message : 'An unexpected error occurred',
          requestId: req.requestId,
          ...(isDevelopment && { stack: err.stack }),
        });
      }
    );

    // Handle promise rejections
    process.on('unhandledRejection', (reason, promise) => {
      logger.fatal('Unhandled promise rejection', { reason, promise });
    });

    // Handle uncaught exceptions
    process.on('uncaughtException', error => {
      logger.fatal('Uncaught exception', error);
      process.exit(1);
    });
  }

  /**
   * Setup graceful shutdown handling
   */
  private setupGracefulShutdown(): void {
    const shutdown = async (signal: string) => {
      logger.info(`Received ${signal}, starting graceful shutdown`);

      // Stop accepting new connections
      if (this.server) {
        this.server.close(() => {
          logger.info('HTTP server closed');
        });
      }

      try {
        // Allow time for current video generations to complete
        logger.info('Waiting for active video generations to complete...');
        await this.waitForActiveJobs(30000); // 30 seconds max

        logger.info('Graceful shutdown complete');
        process.exit(0);
      } catch (error) {
        logger.error('Error during graceful shutdown', error);
        process.exit(1);
      }
    };

    // Handle various shutdown signals
    process.on('SIGTERM', () => shutdown('SIGTERM'));
    process.on('SIGINT', () => shutdown('SIGINT'));
    process.on('SIGHUP', () => shutdown('SIGHUP'));
  }

  /**
   * Wait for active jobs to complete
   */
  private async waitForActiveJobs(timeout: number): Promise<void> {
    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
      const metrics = this.videoService.getMetrics();

      if (metrics.queue.processingJobs === 0) {
        logger.info('All active jobs completed');
        return;
      }

      logger.info(`Waiting for ${metrics.queue.processingJobs} active jobs...`);
      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    logger.warn(
      `Shutdown timeout reached with ${this.videoService.getMetrics().queue.processingJobs} active jobs`
    );
  }

  /**
   * Start the application server
   */
  async start(): Promise<void> {
    try {
      // Start HTTP server
      this.server = this.app.listen(this.port, () => {
        logger.info(`PAKE Video Generation Service started`, {
          port: this.port,
          environment: process.env.NODE_ENV || 'development',
          nodeVersion: process.version,
          processId: process.pid,
          providers: {
            did: !!process.env.DID_API_KEY,
            heygen: !!process.env.HEYGEN_API_KEY,
          },
        });

        // Log important URLs
        console.log('🎬 PAKE Video Generation Service');
        console.log('===================================');
        console.log(`🌍 Server: http://localhost:${this.port}`);
        console.log(`❤️  Health: http://localhost:${this.port}/health`);
        console.log(`📊 Metrics: http://localhost:${this.port}/metrics`);
        console.log(`📚 API Docs: http://localhost:${this.port}/docs`);
        console.log(
          `🎥 Generate: POST http://localhost:${this.port}/api/v1/generate`
        );
        console.log('===================================');

        // Show configured providers
        const providers = [];
        if (process.env.DID_API_KEY) providers.push('D-ID');
        if (process.env.HEYGEN_API_KEY) providers.push('HeyGen');
        console.log(`🤖 Providers: ${providers.join(', ')}`);

        const storage = process.env.STORAGE_PROVIDER || 'local';
        console.log(`💾 Storage: ${storage}`);
        console.log('===================================');
      });

      // Handle server errors
      this.server.on('error', (error: any) => {
        if (error.code === 'EADDRINUSE') {
          logger.fatal(`Port ${this.port} is already in use`);
          process.exit(1);
        } else {
          logger.fatal('Server error', error);
          process.exit(1);
        }
      });
    } catch (error) {
      logger.fatal('Failed to start video generation service', error);
      process.exit(1);
    }
  }
}

// Start the application
const app = new Application();
app.start().catch(error => {
  console.error('Failed to start application:', error);
  process.exit(1);
});

// Export for testing
export { Application };

// Add types to Express Request
declare global {
  namespace Express {
    interface Request {
      requestId?: string;
    }
  }
}
