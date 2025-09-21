/**
 * Audit Middleware for Express Applications
 * Automatically logs all HTTP requests as audit events
 */

import { Request, Response, NextFunction } from 'express';
import { v4 as uuidv4 } from 'uuid';
import {
  AuditEvent,
  ActorType,
  ActionType,
  ActionResult,
  AuditActor,
  AuditAction,
  AuditContext,
} from '../types/audit.types';
import { CryptographicAuditService } from '../services/CryptographicAuditService';
import { AuditStorageService } from '../services/AuditStorageService';
import { StreamingService } from '../services/StreamingService';
import { Logger } from '../utils/logger';

interface AuditMiddlewareConfig {
  excludePaths?: string[];
  includeRequestBody?: boolean;
  includeResponseBody?: boolean;
  sensitiveFields?: string[];
  maxBodySize?: number;
  asyncLogging?: boolean;
}

interface AuthenticatedRequest extends Request {
  user?: {
    id: string;
    email: string;
    username: string;
    roles?: string[];
    permissions?: string[];
    session_id?: string;
  };
  sessionId?: string;
  traceId?: string;
  requestId?: string;
}

export class AuditMiddleware {
  private readonly logger = new Logger('AuditMiddleware');
  private readonly cryptoService: CryptographicAuditService;
  private readonly storageService: AuditStorageService;
  private readonly streamingService: StreamingService;
  private readonly config: AuditMiddlewareConfig;

  constructor(
    cryptoService: CryptographicAuditService,
    storageService: AuditStorageService,
    streamingService: StreamingService,
    config: AuditMiddlewareConfig = {}
  ) {
    this.cryptoService = cryptoService;
    this.storageService = storageService;
    this.streamingService = streamingService;
    this.config = {
      excludePaths: ['/health', '/metrics', '/favicon.ico'],
      includeRequestBody: true,
      includeResponseBody: false,
      sensitiveFields: ['REDACTED_SECRET', 'token', 'secret', 'key', 'authorization'],
      maxBodySize: 10000, // 10KB
      asyncLogging: true,
      ...config,
    };
  }

  /**
   * Express middleware function
   */
  middleware() {
    return async (
      req: AuthenticatedRequest,
      res: Response,
      next: NextFunction
    ) => {
      // Skip excluded paths
      if (this.shouldExcludePath(req.path)) {
        return next();
      }

      // Generate request ID if not present
      req.requestId = req.requestId || uuidv4();
      res.setHeader('X-Request-ID', req.requestId);

      // Store original response methods
      const originalJson = res.json;
      const originalSend = res.send;
      const originalStatus = res.status;

      let responseBody: any = null;
      let statusCode = 200;
      let responseHeaders: any = {};

      // Override response methods to capture data
      res.status = function (code: number) {
        statusCode = code;
        return originalStatus.call(this, code);
      };

      res.json = function (body: any) {
        responseBody = body;
        responseHeaders = { ...res.getHeaders() };
        return originalJson.call(this, body);
      };

      res.send = function (body: any) {
        if (!responseBody) {
          responseBody = body;
          responseHeaders = { ...res.getHeaders() };
        }
        return originalSend.call(this, body);
      };

      // Capture request start time
      const startTime = Date.now();

      // Handle response completion
      res.on('finish', async () => {
        try {
          const endTime = Date.now();
          const duration = endTime - startTime;

          const auditEvent = await this.createAuditEvent(
            req,
            res,
            statusCode,
            duration,
            responseBody,
            responseHeaders
          );

          if (this.config.asyncLogging) {
            // Log asynchronously to avoid blocking
            setImmediate(() => this.logAuditEvent(auditEvent));
          } else {
            await this.logAuditEvent(auditEvent);
          }
        } catch (error) {
          this.logger.error('Failed to create audit log', {
            requestId: req.requestId,
            path: req.path,
            method: req.method,
            error: error.message,
          });
        }
      });

      next();
    };
  }

  /**
   * Create audit event from request/response
   */
  private async createAuditEvent(
    req: AuthenticatedRequest,
    res: Response,
    statusCode: number,
    duration: number,
    responseBody: any,
    responseHeaders: any
  ): Promise<AuditEvent> {
    const actor = this.extractActor(req);
    const action = this.extractAction(req, statusCode, duration);
    const context = this.extractContext(req, responseHeaders);

    const auditEvent: Omit<AuditEvent, 'signature'> = {
      id: uuidv4(),
      timestamp: new Date().toISOString(),
      actor,
      action,
      context,
      version: '1.0.0',
    };

    // Add request/response bodies if configured
    if (this.config.includeRequestBody && req.body) {
      action.metadata = action.metadata || {};
      action.metadata.requestBody = this.sanitizeData(req.body);
    }

    if (this.config.includeResponseBody && responseBody) {
      action.metadata = action.metadata || {};
      action.metadata.responseBody = this.sanitizeData(responseBody);
    }

    return auditEvent;
  }

  /**
   * Extract actor information from request
   */
  private extractActor(req: AuthenticatedRequest): AuditActor {
    const actor: AuditActor = {
      id: 'anonymous',
      type: ActorType.ANONYMOUS,
      ip: this.getClientIP(req),
      userAgent: req.headers['user-agent'],
      session: req.sessionId,
    };

    // Extract authenticated user info
    if (req.user) {
      actor.id = req.user.id;
      actor.type = ActorType.USER;
      actor.session = req.user.session_id || req.sessionId;
      actor.metadata = {
        username: req.user.username,
        email: req.user.email,
        roles: req.user.roles || [],
        permissions: req.user.permissions || [],
      };
    } else if (req.headers.authorization?.startsWith('Bearer ')) {
      // API key or service token
      actor.type = ActorType.API_KEY;
      actor.id = 'api-client';
    }

    return actor;
  }

  /**
   * Extract action information from request
   */
  private extractAction(
    req: AuthenticatedRequest,
    statusCode: number,
    duration: number
  ): AuditAction {
    const method = req.method.toLowerCase();
    const resource = this.extractResource(req.path);
    const resourceId = this.extractResourceId(req);

    // Map HTTP methods to audit actions
    const actionTypeMap: Record<string, ActionType> = {
      get: ActionType.read,
      post: ActionType.CREATE,
      put: ActionType.UPDATE,
      patch: ActionType.UPDATE,
      delete: ActionType.DELETE,
      head: ActionType.read,
      options: ActionType.read,
    };

    const actionType = actionTypeMap[method] || ActionType.EXECUTE;
    const result = this.determineActionResult(statusCode);

    const action: AuditAction = {
      type: actionType,
      resource: resource,
      resourceId: resourceId,
      result: result,
      duration: duration,
      metadata: {
        httpMethod: req.method,
        httpPath: req.path,
        httpQuery: req.query,
        statusCode: statusCode,
        userAgent: req.headers['user-agent'],
        referer: req.headers.referer,
      },
    };

    if (statusCode >= 400) {
      action.error = `HTTP ${statusCode}`;
    }

    return action;
  }

  /**
   * Extract context information from request
   */
  private extractContext(
    req: AuthenticatedRequest,
    responseHeaders: any
  ): AuditContext {
    return {
      requestId: req.requestId!,
      traceId: req.traceId || (req.headers['x-trace-id'] as string),
      environment: process.env.NODE_ENV || 'development',
      application: process.env.APP_NAME || 'pake-service',
      version: process.env.APP_VERSION || '1.0.0',
      metadata: {
        host: req.headers.host,
        protocol: req.protocol,
        secure: req.secure,
        responseHeaders: this.sanitizeHeaders(responseHeaders),
      },
    };
  }

  /**
   * Log audit event
   */
  private async logAuditEvent(
    auditEvent: Omit<AuditEvent, 'signature'>
  ): Promise<void> {
    try {
      // Sign the event
      const signedEvent = await this.cryptoService.signAuditEvent(auditEvent);

      // Store in database
      await this.storageService.storeEvent(signedEvent);

      // Stream to SIEM systems
      await this.streamingService.streamEvent(signedEvent);

      this.logger.debug('Audit event logged successfully', {
        eventId: signedEvent.id,
        actor: signedEvent.actor.id,
        action: `${signedEvent.action.type}:${signedEvent.action.resource}`,
        result: signedEvent.action.result,
      });
    } catch (error) {
      this.logger.error('Failed to log audit event', {
        eventId: auditEvent.id,
        error: error.message,
      });

      // Don't throw - audit logging shouldn't break the application
    }
  }

  /**
   * Check if path should be excluded from auditing
   */
  private shouldExcludePath(path: string): boolean {
    return (
      this.config.excludePaths?.some(excludePath =>
        path.startsWith(excludePath)
      ) || false
    );
  }

  /**
   * Extract resource name from request path
   */
  private extractResource(path: string): string {
    // Remove leading slash and extract first path segment
    const segments = path.replace(/^\//, '').split('/');
    return segments[0] || 'root';
  }

  /**
   * Extract resource ID from request
   */
  private extractResourceId(req: AuthenticatedRequest): string | undefined {
    // Check common ID patterns in path
    const pathSegments = req.path.split('/');

    for (let i = 0; i < pathSegments.length; i++) {
      const segment = pathSegments[i];

      // UUID pattern
      if (
        /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
          segment
        )
      ) {
        return segment;
      }

      // Numeric ID
      if (/^\d+$/.test(segment)) {
        return segment;
      }
    }

    // Check query parameters for ID
    if (req.query.id) {
      return String(req.query.id);
    }

    // Check request body for ID
    if (req.body && req.body.id) {
      return String(req.body.id);
    }

    return undefined;
  }

  /**
   * Determine action result from status code
   */
  private determineActionResult(statusCode: number): ActionResult {
    if (statusCode >= 200 && statusCode < 300) {
      return ActionResult.SUCCESS;
    } else if (statusCode === 403) {
      return ActionResult.DENIED;
    } else if (statusCode >= 400 && statusCode < 500) {
      return ActionResult.FAILURE;
    } else if (statusCode >= 500) {
      return ActionResult.ERROR;
    }

    return ActionResult.SUCCESS;
  }

  /**
   * Get client IP address
   */
  private getClientIP(req: Request): string {
    return (
      (req.headers['x-forwarded-for'] as string) ||
      (req.headers['x-real-ip'] as string) ||
      req.connection.remoteAddress ||
      req.socket.remoteAddress ||
      'unknown'
    )
      .split(',')[0]
      .trim();
  }

  /**
   * Sanitize sensitive data
   */
  private sanitizeData(data: any): any {
    if (!data || typeof data !== 'object') {
      return data;
    }

    const sanitized = Array.isArray(data) ? [] : {};

    for (const [key, value] of Object.entries(data)) {
      const lowerKey = key.toLowerCase();

      if (
        this.config.sensitiveFields?.some(field =>
          lowerKey.includes(field.toLowerCase())
        )
      ) {
        (sanitized as any)[key] = '[REDACTED]';
      } else if (typeof value === 'object' && value !== null) {
        (sanitized as any)[key] = this.sanitizeData(value);
      } else {
        (sanitized as any)[key] = value;
      }
    }

    // Truncate if too large
    const serialized = JSON.stringify(sanitized);
    if (serialized.length > this.config.maxBodySize!) {
      return '[TRUNCATED - Too Large]';
    }

    return sanitized;
  }

  /**
   * Sanitize response headers
   */
  private sanitizeHeaders(headers: any): any {
    const sanitized = { ...headers };

    // Remove sensitive headers
    const sensitiveHeaders = ['authorization', 'cookie', 'set-cookie'];
    for (const header of sensitiveHeaders) {
      if (sanitized[header]) {
        sanitized[header] = '[REDACTED]';
      }
    }

    return sanitized;
  }
}

/**
 * Factory function to create audit middleware
 */
export function createAuditMiddleware(
  cryptoService: CryptographicAuditService,
  storageService: AuditStorageService,
  streamingService: StreamingService,
  config?: AuditMiddlewareConfig
) {
  const middleware = new AuditMiddleware(
    cryptoService,
    storageService,
    streamingService,
    config
  );

  return middleware.middleware();
}
