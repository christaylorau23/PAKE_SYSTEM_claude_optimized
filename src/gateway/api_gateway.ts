/**
 * PAKE System API Gateway
 * Centralized entry point for all service requests with security, rate limiting, and circuit breaking
 */

import express, { Request, Response, NextFunction } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import { SecretsValidator } from '../utils/secrets_validator';
import { validateInput, SecurityLevel } from '../middleware/input_validation';
import { CircuitBreaker } from './circuit_breaker';
import { ServiceRegistry } from './service_registry';
import { AuthMiddleware } from './auth_middleware';
import { Logger } from '../utils/logger';

export interface RouteConfig {
  path: string;
  service: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  authRequired: boolean;
  rateLimit?: {
    windowMs: number;
    max: number;
  };
  circuitBreaker?: {
    failureThreshold: number;
    timeout: number;
  };
}

export interface APIGatewayConfig {
  port: number;
  routes: RouteConfig[];
  cors: {
    origin: string[];
    credentials: boolean;
  };
  rateLimiting: {
    windowMs: number;
    max: number;
  };
  security: {
    helmet: boolean;
    inputValidation: boolean;
  };
}

export class APIGateway {
  private app: express.Application;
  private config: APIGatewayConfig;
  private serviceRegistry: ServiceRegistry;
  private circuitBreakers: Map<string, CircuitBreaker> = new Map();
  private logger: Logger;

  constructor(config: APIGatewayConfig) {
    this.config = config;
    this.app = express();
    this.serviceRegistry = new ServiceRegistry();
    this.logger = new Logger('APIGateway');

    this.initializeMiddleware();
    this.setupRoutes();
    this.initializeCircuitBreakers();
  }

  private initializeMiddleware(): void {
    // Security middleware
    if (this.config.security.helmet) {
      this.app.use(helmet());
    }

    // CORS configuration
    this.app.use(
      cors({
        origin: this.config.cors.origin,
        credentials: this.config.cors.credentials,
      })
    );

    // Body parsing
    this.app.use(express.json({ limit: '10mb' }));
    this.app.use(express.urlencoded({ extended: true, limit: '10mb' }));

    // Request logging
    this.app.use((req: Request, res: Response, next: NextFunction) => {
      this.logger.info('Request received', {
        method: req.method,
        url: req.url,
        ip: req.ip,
        userAgent: req.get('User-Agent'),
      });
      next();
    });

    // Global rate limiting
    const globalRateLimit = rateLimit({
      windowMs: this.config.rateLimiting.windowMs,
      max: this.config.rateLimiting.max,
      message: {
        error: 'Too many requests',
        retryAfter: Math.ceil(this.config.rateLimiting.windowMs / 1000),
      },
      standardHeaders: true,
      legacyHeaders: false,
    });
    this.app.use(globalRateLimit);
  }

  private setupRoutes(): void {
    // Health check endpoint
    this.app.get('/health', (req: Request, res: Response) => {
      res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        services: this.serviceRegistry.getServiceStatuses(),
      });
    });

    // Service discovery endpoint
    this.app.get('/services', (req: Request, res: Response) => {
      res.json({
        services: this.serviceRegistry.getAllServices(),
      });
    });

    // Setup service routes
    for (const route of this.config.routes) {
      this.setupRoute(route);
    }

    // 404 handler
    this.app.use('*', (req: Request, res: Response) => {
      res.status(404).json({
        error: 'Route not found',
        path: req.originalUrl,
        method: req.method,
      });
    });

    // Error handler
    this.app.use(
      (err: Error, req: Request, res: Response, next: NextFunction) => {
        this.logger.error('API Gateway error', {
          error: err.message,
          stack: err.stack,
          url: req.url,
          method: req.method,
        });

        res.status(500).json({
          error: 'Internal server error',
          requestId: req.headers['x-request-id'] || 'unknown',
        });
      }
    );
  }

  private setupRoute(route: RouteConfig): void {
    const middleware: express.RequestHandler[] = [];

    // Authentication middleware
    if (route.authRequired) {
      middleware.push(AuthMiddleware.authenticate);
    }

    // Route-specific rate limiting
    if (route.rateLimit) {
      const routeRateLimit = rateLimit({
        windowMs: route.rateLimit.windowMs,
        max: route.rateLimit.max,
        message: {
          error: 'Rate limit exceeded for this endpoint',
          retryAfter: Math.ceil(route.rateLimit.windowMs / 1000),
        },
      });
      middleware.push(routeRateLimit);
    }

    // Input validation middleware
    if (this.config.security.inputValidation) {
      middleware.push(this.inputValidationMiddleware.bind(this));
    }

    // Circuit breaker middleware
    if (route.circuitBreaker) {
      const circuitBreaker = this.circuitBreakers.get(route.service);
      if (circuitBreaker) {
        middleware.push(circuitBreaker.middleware.bind(circuitBreaker));
      }
    }

    // Service proxy middleware
    middleware.push(this.serviceProxyMiddleware(route.service).bind(this));

    // Apply middleware to route
    this.app[route.method.toLowerCase() as keyof express.Application](
      route.path,
      ...middleware
    );
  }

  private inputValidationMiddleware(
    req: Request,
    res: Response,
    next: NextFunction
  ): void {
    try {
      // Validate request body
      if (req.body && typeof req.body === 'object') {
        for (const [key, value] of Object.entries(req.body)) {
          if (typeof value === 'string') {
            req.body[key] = validateInput(value, 'string', {
              securityLevel: SecurityLevel.MEDIUM,
              maxLength: 10000,
            });
          }
        }
      }

      // Validate query parameters
      for (const [key, value] of Object.entries(req.query)) {
        if (typeof value === 'string') {
          req.query[key] = validateInput(value, 'string', {
            securityLevel: SecurityLevel.MEDIUM,
            maxLength: 1000,
          });
        }
      }

      next();
    } catch (error) {
      res.status(400).json({
        error: 'Invalid input',
        details: error.message,
      });
    }
  }

  private serviceProxyMiddleware(serviceName: string) {
    return async (req: Request, res: Response, next: NextFunction) => {
      try {
        const service = this.serviceRegistry.getService(serviceName);
        if (!service) {
          return res.status(503).json({
            error: 'Service unavailable',
            service: serviceName,
          });
        }

        // Forward request to service
        const response = await this.forwardRequest(service, req);

        // Set response headers
        Object.entries(response.headers).forEach(([key, value]) => {
          res.set(key, value as string);
        });

        res.status(response.status).json(response.data);
      } catch (error) {
        this.logger.error('Service proxy error', {
          service: serviceName,
          error: error.message,
          url: req.url,
        });

        res.status(500).json({
          error: 'Service error',
          service: serviceName,
        });
      }
    };
  }

  private async forwardRequest(service: any, req: Request): Promise<any> {
    // Implementation would forward the request to the actual service
    // This is a placeholder for the actual service communication
    return {
      status: 200,
      headers: {},
      data: { message: 'Service response' },
    };
  }

  private initializeCircuitBreakers(): void {
    for (const route of this.config.routes) {
      if (route.circuitBreaker) {
        const circuitBreaker = new CircuitBreaker({
          failureThreshold: route.circuitBreaker.failureThreshold,
          timeout: route.circuitBreaker.timeout,
          serviceName: route.service,
        });
        this.circuitBreakers.set(route.service, circuitBreaker);
      }
    }
  }

  public async start(): Promise<void> {
    return new Promise(resolve => {
      this.app.listen(this.config.port, () => {
        this.logger.info('API Gateway started', {
          port: this.config.port,
          routes: this.config.routes.length,
        });
        resolve();
      });
    });
  }

  public getApp(): express.Application {
    return this.app;
  }

  public getServiceRegistry(): ServiceRegistry {
    return this.serviceRegistry;
  }
}

// Default configuration
export const defaultGatewayConfig: APIGatewayConfig = {
  port: parseInt(process.env.GATEWAY_PORT || '3001'),
  routes: [
    // Authentication routes
    {
      path: '/api/auth/*',
      service: 'auth-service',
      method: 'GET',
      authRequired: false,
      rateLimit: { windowMs: 60000, max: 100 },
    },
    {
      path: '/api/auth/login',
      service: 'auth-service',
      method: 'POST',
      authRequired: false,
      rateLimit: { windowMs: 60000, max: 10 },
      circuitBreaker: { failureThreshold: 5, timeout: 30000 },
    },

    // Data routes
    {
      path: '/api/data/*',
      service: 'data-service',
      method: 'GET',
      authRequired: true,
      rateLimit: { windowMs: 60000, max: 1000 },
    },

    // AI routes
    {
      path: '/api/ai/*',
      service: 'ai-service',
      method: 'POST',
      authRequired: true,
      rateLimit: { windowMs: 60000, max: 100 },
      circuitBreaker: { failureThreshold: 3, timeout: 60000 },
    },
  ],
  cors: {
    origin: process.env.CORS_ORIGINS?.split(',') || ['http://localhost:3000'],
    credentials: true,
  },
  rateLimiting: {
    windowMs: 60000, // 1 minute
    max: 1000, // requests per minute
  },
  security: {
    helmet: true,
    inputValidation: true,
  },
};
