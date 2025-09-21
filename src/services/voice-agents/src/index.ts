/**
 * PAKE System - Voice Agent Service Entry Point
 * Bootstraps the voice agent service with all components and monitoring
 */

import dotenv from 'dotenv';
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import { VoiceAgentService } from './VoiceAgentService';
import { Logger } from './utils/Logger';

// Load environment variables
dotenv.config();

const logger = new Logger('VoiceAgentBootstrap');

/**
 * Application bootstrap and startup
 */
class Application {
  private app: express.Application;
  private voiceAgentService: VoiceAgentService;
  private server: any;
  private port: number;

  constructor() {
    this.port = parseInt(process.env.VOICE_AGENT_PORT || '9000');
    this.app = express();
    this.voiceAgentService = new VoiceAgentService();

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
        origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
        credentials: true,
        methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
        allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With'],
      })
    );

    // Compression and parsing
    this.app.use(compression());
    this.app.use(express.json({ limit: '10mb' }));
    this.app.use(express.urlencoded({ extended: true, limit: '10mb' }));

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
      });

      next();
    });
  }

  /**
   * Setup API routes
   */
  private setupRoutes(): void {
    // Health check endpoint
    this.app.get('/health', (req, res) => {
      const health = {
        status: 'healthy',
        timestamp: new Date().toISOString(),
        version: process.env.npm_package_version || '1.0.0',
        uptime: process.uptime(),
        environment: process.env.NODE_ENV || 'development',
        service: 'voice-agents',
        dependencies: {
          redis: this.voiceAgentService.isRedisConnected(),
          knowledgeVault: this.voiceAgentService.isKnowledgeVaultConnected(),
        },
      };

      res.status(200).json(health);
    });

    // Ready check endpoint (for Kubernetes)
    this.app.get('/ready', async (req, res) => {
      try {
        const isReady = await this.voiceAgentService.isReady();
        if (isReady) {
          res.status(200).json({ status: 'ready' });
        } else {
          res.status(503).json({ status: 'not ready' });
        }
      } catch (error) {
        logger.error('Readiness check failed', error);
        res.status(503).json({ status: 'not ready', error: error.message });
      }
    });

    // Metrics endpoint
    this.app.get('/metrics', (req, res) => {
      try {
        const metrics = this.voiceAgentService.getMetrics();
        res.status(200).json(metrics);
      } catch (error) {
        logger.error('Failed to get metrics', error);
        res.status(500).json({ error: 'Failed to retrieve metrics' });
      }
    });

    // Voice agent API routes
    this.app.use('/api/v1', this.voiceAgentService.getRouter());

    // Default route
    this.app.get('/', (req, res) => {
      res.json({
        service: 'PAKE Voice Agent Service',
        version: process.env.npm_package_version || '1.0.0',
        endpoints: {
          health: '/health',
          ready: '/ready',
          metrics: '/metrics',
          api: '/api/v1',
        },
        documentation: '/docs',
      });
    });

    // API documentation (simple endpoint list)
    this.app.get('/docs', (req, res) => {
      res.json({
        title: 'PAKE Voice Agent Service API',
        version: '1.0.0',
        endpoints: {
          'POST /api/v1/assistants': 'Create a new voice assistant',
          'GET /api/v1/assistants': 'List all voice assistants',
          'POST /api/v1/calls': 'Initiate a voice call',
          'GET /api/v1/calls/:callId': 'Get call status',
          'PATCH /api/v1/calls/:callId': 'Update call context',
          'DELETE /api/v1/calls/:callId': 'End a voice call',
          'POST /api/v1/knowledge/search': 'Search knowledge base',
          'GET /api/v1/conversations/:sessionId': 'Get conversation context',
          'POST /api/v1/conversations/:sessionId/messages': 'Add message to conversation',
        },
      });
    });

    // 404 handler
    this.app.use('*', (req, res) => {
      res.status(404).json({
        error: 'Not Found',
        message: `Route ${req.method} ${req.originalUrl} not found`,
        availableEndpoints: ['/health', '/ready', '/metrics', '/api/v1', '/docs'],
      });
    });
  }

  /**
   * Setup error handling middleware
   */
  private setupErrorHandling(): void {
    this.app.use(
      (err: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
        logger.error('Unhandled error in request', err, {
          requestId: req.requestId,
          method: req.method,
          path: req.path,
          userAgent: req.headers['user-agent'],
        });

        // Don't expose error details in production
        const isDevelopment = process.env.NODE_ENV === 'development';

        res.status(err.status || 500).json({
          error: 'Internal Server Error',
          message: isDevelopment ? err.message : 'An unexpected error occurred',
          requestId: req.requestId,
          ...(isDevelopment && { stack: err.stack }),
        });
      }
    );
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
        // Shutdown voice agent service
        await this.voiceAgentService.shutdown();
        logger.info('Voice agent service shutdown complete');

        // Give some time for final cleanup
        setTimeout(() => {
          logger.info('Graceful shutdown complete');
          process.exit(0);
        }, 1000);
      } catch (error) {
        logger.error('Error during graceful shutdown', error);
        process.exit(1);
      }
    };

    // Handle various shutdown signals
    process.on('SIGTERM', () => shutdown('SIGTERM'));
    process.on('SIGINT', () => shutdown('SIGINT'));
    process.on('SIGHUP', () => shutdown('SIGHUP'));

    // Handle uncaught exceptions
    process.on('uncaughtException', (error) => {
      logger.fatal('Uncaught exception', error);
      process.exit(1);
    });

    // Handle unhandled promise rejections
    process.on('unhandledRejection', (reason, promise) => {
      logger.fatal('Unhandled promise rejection', { reason, promise });
      process.exit(1);
    });
  }

  /**
   * Start the application server
   */
  async start(): Promise<void> {
    try {
      // Initialize voice agent service
      await this.voiceAgentService.initialize();
      logger.info('Voice agent service initialized');

      // Start HTTP server
      this.server = this.app.listen(this.port, () => {
        logger.info(`PAKE Voice Agent Service started`, {
          port: this.port,
          environment: process.env.NODE_ENV || 'development',
          nodeVersion: process.version,
          processId: process.pid,
        });

        // Log important URLs
        console.log('🚀 PAKE Voice Agent Service');
        console.log('================================');
        console.log(`🌍 Server: http://localhost:${this.port}`);
        console.log(`❤️  Health: http://localhost:${this.port}/health`);
        console.log(`📊 Metrics: http://localhost:${this.port}/metrics`);
        console.log(`📚 API Docs: http://localhost:${this.port}/docs`);
        console.log('================================');
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
      logger.fatal('Failed to start voice agent service', error);
      process.exit(1);
    }
  }
}

// Start the application
const app = new Application();
app.start().catch((error) => {
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
