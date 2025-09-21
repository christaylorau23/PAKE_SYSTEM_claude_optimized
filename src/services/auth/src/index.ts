#!/usr/bin/env ts-node
/**
 * PAKE Authentication Service
 * Main application entry point
 */

import express, { Application, Request, Response, NextFunction } from 'express';
import helmet from 'helmet';
import cors from 'cors';
import rateLimit from 'express-rate-limit';
import { createServer } from 'http';
import path from 'path';

import {
  authConfig,
  validateAuthConfig,
  redisConfig,
} from './config/auth.config';
import { RedisService } from './services/RedisService';
import { TokenService } from './services/TokenService';
import { MFAService } from './services/MFAService';
import { SessionService } from './services/SessionService';
import { RBACService } from './services/RBACService';
import { PasswordService } from './services/PasswordService';
import { EmailService } from './services/EmailService';
import { UserService } from './services/UserService';
import { Logger, PerformanceTimer, logRequest } from './utils/logger';
import { AuthRoutes } from './routes/auth.routes';
import { UserRoutes } from './routes/user.routes';
import { AdminRoutes } from './routes/admin.routes';

interface AuthApplication {
  app: Application;
  redis: RedisService;
  userService: UserService;
  rbacService: RBACService;
  tokenService: TokenService;
  mfaService: MFAService;
  sessionService: SessionService;
  REDACTED_SECRETService: PasswordService;
  emailService: EmailService;
}

class AuthenticationService {
  private readonly logger = new Logger('AuthService');
  private app: Application;
  private server: any;
  private redis: RedisService;
  private services: {
    userService: UserService;
    rbacService: RBACService;
    tokenService: TokenService;
    mfaService: MFAService;
    sessionService: SessionService;
    REDACTED_SECRETService: PasswordService;
    emailService: EmailService;
  };

  constructor() {
    this.app = express();
    this.redis = new RedisService();
  }

  /**
   * Initialize the authentication service
   */
  async initialize(): Promise<void> {
    try {
      // Validate configuration
      validateAuthConfig();

      // Connect to Redis
      await this.redis.connect();

      // Initialize services
      await this.initializeServices();

      // Setup middleware
      this.setupMiddleware();

      // Setup routes
      this.setupRoutes();

      // Setup error handling
      this.setupErrorHandling();

      // Setup graceful shutdown
      this.setupGracefulShutdown();

      this.logger.info('Authentication service initialized successfully');
    } catch (error) {
      this.logger.error('Failed to initialize authentication service', {
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Initialize all services
   */
  private async initializeServices(): Promise<void> {
    const timer = new PerformanceTimer('service_initialization', this.logger);

    try {
      // Initialize services in dependency order
      const emailService = new EmailService();
      const REDACTED_SECRETService = new PasswordService(this.redis);
      const tokenService = new TokenService(this.redis);
      const mfaService = new MFAService(this.redis);
      const sessionService = new SessionService(this.redis);
      const rbacService = new RBACService(this.redis);

      // Initialize RBAC system
      await rbacService.initialize();

      const userService = new UserService(
        this.redis,
        tokenService,
        mfaService,
        sessionService,
        rbacService,
        REDACTED_SECRETService,
        emailService
      );

      this.services = {
        userService,
        rbacService,
        tokenService,
        mfaService,
        sessionService,
        REDACTED_SECRETService,
        emailService,
      };

      timer.end();
      this.logger.info('All services initialized successfully');
    } catch (error) {
      this.logger.error('Service initialization failed', {
        error: error.message,
      });
      throw error;
    }
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
            styleSrc: ["'self'", "'unsafe-inline'"],
            scriptSrc: ["'self'"],
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
        origin: process.env.ALLOWED_ORIGINS?.split(',') || [
          'http://localhost:3000',
        ],
        credentials: true,
        methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With'],
      })
    );

    // Rate limiting
    const limiter = rateLimit({
      windowMs: authConfig.security.rateLimiting.windowMs,
      max: authConfig.security.rateLimiting.maxRequests,
      message: {
        error: 'Too many requests from this IP, please try again later',
        code: 'RATE_LIMIT_EXCEEDED',
      },
      standardHeaders: true,
      legacyHeaders: false,
      skip: req => {
        // Skip rate limiting for health checks
        return req.path === '/health' || req.path === '/metrics';
      },
    });
    this.app.use(limiter);

    // Body parsing
    this.app.use(express.json({ limit: '10mb' }));
    this.app.use(express.urlencoded({ extended: true, limit: '10mb' }));

    // Request logging
    this.app.use((req: Request, res: Response, next: NextFunction) => {
      const timer = new PerformanceTimer(`${req.method} ${req.path}`);

      res.on('finish', () => {
        const duration = timer.end();
        logRequest(req, res, duration);
      });

      next();
    });

    // Health check endpoint
    this.app.get('/health', async (req: Request, res: Response) => {
      const health = {
        status: 'ok',
        timestamp: new Date().toISOString(),
        uptime: process.uptime(),
        services: {
          redis: this.redis.isHealthy(),
          email: await this.services.emailService.testConfiguration(),
        },
      };

      const allHealthy = Object.values(health.services).every(status => status);
      res.status(allHealthy ? 200 : 503).json(health);
    });

    // Metrics endpoint
    this.app.get('/metrics', async (req: Request, res: Response) => {
      try {
        const sessionStats =
          await this.services.sessionService.getSessionStats();
        const rbacStats = await this.services.rbacService.getStats();

        const metrics = {
          timestamp: new Date().toISOString(),
          uptime: process.uptime(),
          memory: process.memoryUsage(),
          sessions: sessionStats,
          rbac: rbacStats,
          redis: this.redis.isHealthy(),
        };

        res.json(metrics);
      } catch (error) {
        this.logger.error('Failed to get metrics', { error: error.message });
        res.status(500).json({ error: 'Failed to get metrics' });
      }
    });
  }

  /**
   * Setup API routes
   */
  private setupRoutes(): void {
    // API base path
    const apiRouter = express.Router();

    // Authentication routes
    const authRoutes = new AuthRoutes(this.services);
    apiRouter.use('/auth', authRoutes.getRouter());

    // User management routes
    const userRoutes = new UserRoutes(this.services);
    apiRouter.use('/users', userRoutes.getRouter());

    // Admin routes
    const adminRoutes = new AdminRoutes(this.services);
    apiRouter.use('/admin', adminRoutes.getRouter());

    // Mount API routes
    this.app.use('/api', apiRouter);

    // API documentation
    this.app.get('/api', (req: Request, res: Response) => {
      res.json({
        name: 'PAKE Authentication Service',
        version: '1.0.0',
        description:
          'Enterprise-grade authentication and authorization service',
        endpoints: {
          auth: '/api/auth',
          users: '/api/users',
          admin: '/api/admin',
          health: '/health',
          metrics: '/metrics',
        },
        documentation: '/api/docs',
      });
    });

    // Catch-all for undefined routes
    this.app.use('*', (req: Request, res: Response) => {
      res.status(404).json({
        error: 'Route not found',
        code: 'ROUTE_NOT_FOUND',
        path: req.path,
      });
    });
  }

  /**
   * Setup error handling
   */
  private setupErrorHandling(): void {
    // Global error handler
    this.app.use(
      (error: any, req: Request, res: Response, next: NextFunction) => {
        this.logger.error('Unhandled error', {
          error: error.message,
          stack: error.stack,
          url: req.url,
          method: req.method,
          ip: req.ip,
          userAgent: req.get('user-agent'),
        });

        // Don't expose error details in production
        const isDevelopment = process.env.NODE_ENV === 'development';

        res.status(error.status || 500).json({
          error: isDevelopment ? error.message : 'Internal server error',
          code: error.code || 'INTERNAL_ERROR',
          ...(isDevelopment && { stack: error.stack }),
        });
      }
    );

    // Handle unhandled promise rejections
    process.on('unhandledRejection', (reason: any, promise: Promise<any>) => {
      this.logger.error('Unhandled promise rejection', {
        reason: reason?.message || reason,
        stack: reason?.stack,
      });
    });

    // Handle uncaught exceptions
    process.on('uncaughtException', (error: Error) => {
      this.logger.error('Uncaught exception', {
        error: error.message,
        stack: error.stack,
      });

      // Graceful shutdown on uncaught exception
      this.shutdown(1);
    });
  }

  /**
   * Setup graceful shutdown
   */
  private setupGracefulShutdown(): void {
    const shutdown = async (signal: string) => {
      this.logger.info(`Received ${signal}, starting graceful shutdown`);

      // Stop accepting new connections
      if (this.server) {
        this.server.close(() => {
          this.logger.info('HTTP server closed');
        });
      }

      // Close Redis connection
      await this.redis.disconnect();

      this.logger.info('Graceful shutdown completed');
      process.exit(0);
    };

    process.on('SIGTERM', () => shutdown('SIGTERM'));
    process.on('SIGINT', () => shutdown('SIGINT'));
  }

  /**
   * Start the server
   */
  async start(port: number = 3001): Promise<void> {
    try {
      this.server = createServer(this.app);

      this.server.listen(port, () => {
        this.logger.info('Authentication service started', {
          port,
          environment: process.env.NODE_ENV || 'development',
          pid: process.pid,
        });
      });

      // Setup background tasks
      this.setupBackgroundTasks();
    } catch (error) {
      this.logger.error('Failed to start server', { error: error.message });
      throw error;
    }
  }

  /**
   * Setup background tasks
   */
  private setupBackgroundTasks(): void {
    // Clean up expired sessions every 15 minutes
    setInterval(
      async () => {
        try {
          const cleanedSessions =
            await this.services.sessionService.cleanupExpiredSessions();
          if (cleanedSessions > 0) {
            this.logger.info('Cleaned up expired sessions', {
              count: cleanedSessions,
            });
          }
        } catch (error) {
          this.logger.error('Session cleanup failed', { error: error.message });
        }
      },
      15 * 60 * 1000
    );

    // Clean up expired tokens every 30 minutes
    setInterval(
      async () => {
        try {
          const cleanedTokens =
            await this.services.tokenService.cleanupExpiredTokens();
          if (cleanedTokens > 0) {
            this.logger.info('Cleaned up expired tokens', {
              count: cleanedTokens,
            });
          }
        } catch (error) {
          this.logger.error('Token cleanup failed', { error: error.message });
        }
      },
      30 * 60 * 1000
    );

    // Clean up expired REDACTED_SECRET histories every hour
    setInterval(
      async () => {
        try {
          const cleanedHistories =
            await this.services.REDACTED_SECRETService.cleanupExpiredHistories();
          if (cleanedHistories > 0) {
            this.logger.info('Cleaned up expired REDACTED_SECRET histories', {
              count: cleanedHistories,
            });
          }
        } catch (error) {
          this.logger.error('Password history cleanup failed', {
            error: error.message,
          });
        }
      },
      60 * 60 * 1000
    );
  }

  /**
   * Shutdown the service
   */
  async shutdown(exitCode: number = 0): Promise<void> {
    try {
      if (this.server) {
        this.server.close();
      }

      await this.redis.disconnect();
      process.exit(exitCode);
    } catch (error) {
      this.logger.error('Shutdown error', { error: error.message });
      process.exit(1);
    }
  }

  /**
   * Get the Express application
   */
  getApp(): Application {
    return this.app;
  }

  /**
   * Get services (for testing)
   */
  getServices() {
    return this.services;
  }
}

// Create and export application instance
export const createAuthApp = async (): Promise<AuthApplication> => {
  const authService = new AuthenticationService();
  await authService.initialize();

  return {
    app: authService.getApp(),
    redis: authService['redis'],
    ...authService.getServices(),
  };
};

// Main execution
if (require.main === module) {
  const main = async () => {
    try {
      const authService = new AuthenticationService();
      await authService.initialize();

      const port = parseInt(process.env.PORT || '3001');
      await authService.start(port);
    } catch (error) {
      console.error('Failed to start authentication service:', error);
      process.exit(1);
    }
  };

  main();
}

export default createAuthApp;
