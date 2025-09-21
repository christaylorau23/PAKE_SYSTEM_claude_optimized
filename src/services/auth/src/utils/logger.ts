/**
 * Structured Logger Utility
 * Provides consistent logging across the authentication system
 */

import winston from 'winston';
import path from 'path';

interface LogContext {
  [key: string]: any;
}

export class Logger {
  private logger: winston.Logger;
  private context: string;

  constructor(context: string) {
    this.context = context;
    this.logger = winston.createLogger({
      level: process.env.LOG_LEVEL || 'info',
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.errors({ stack: true }),
        winston.format.json(),
        winston.format.printf(
          ({ timestamp, level, message, context, ...meta }) => {
            const logEntry = {
              timestamp,
              level,
              context: context || this.context,
              message,
              ...meta,
            };
            return JSON.stringify(logEntry);
          }
        )
      ),
      defaultMeta: { context: this.context },
      transports: [
        new winston.transports.Console({
          format: winston.format.combine(
            winston.format.colorize(),
            winston.format.simple(),
            winston.format.printf(
              ({ timestamp, level, context, message, ...meta }) => {
                const metaStr =
                  Object.keys(meta).length > 0
                    ? ` ${JSON.stringify(meta)}`
                    : '';
                return `${timestamp} [${context}] ${level}: ${message}${metaStr}`;
              }
            )
          ),
        }),
        new winston.transports.File({
          filename: path.join(process.cwd(), 'logs', 'auth-error.log'),
          level: 'error',
        }),
        new winston.transports.File({
          filename: path.join(process.cwd(), 'logs', 'auth-combined.log'),
        }),
      ],
      exceptionHandlers: [
        new winston.transports.File({
          filename: path.join(process.cwd(), 'logs', 'auth-exceptions.log'),
        }),
      ],
      rejectionHandlers: [
        new winston.transports.File({
          filename: path.join(process.cwd(), 'logs', 'auth-rejections.log'),
        }),
      ],
    });

    // Create logs directory if it doesn't exist
    const fs = require('fs');
    const logsDir = path.join(process.cwd(), 'logs');
    if (!fs.existsSync(logsDir)) {
      fs.mkdirSync(logsDir, { recursive: true });
    }
  }

  info(message: string, context?: LogContext): void {
    this.logger.info(message, context);
  }

  error(message: string, context?: LogContext): void {
    this.logger.error(message, context);
  }

  warn(message: string, context?: LogContext): void {
    this.logger.warn(message, context);
  }

  debug(message: string, context?: LogContext): void {
    this.logger.debug(message, context);
  }

  verbose(message: string, context?: LogContext): void {
    this.logger.verbose(message, context);
  }

  /**
   * Create child logger with additional context
   */
  child(additionalContext: LogContext): Logger {
    const childLogger = new Logger(this.context);
    childLogger.logger = this.logger.child(additionalContext);
    return childLogger;
  }

  /**
   * Log security event with standardized format
   */
  security(
    event: string,
    userId?: string,
    ipAddress?: string,
    additionalContext?: LogContext
  ): void {
    this.logger.info('Security Event', {
      event,
      userId,
      ipAddress,
      timestamp: new Date().toISOString(),
      ...additionalContext,
    });
  }

  /**
   * Log audit event with standardized format
   */
  audit(
    action: string,
    userId: string,
    resource: string,
    success: boolean,
    ipAddress?: string,
    additionalContext?: LogContext
  ): void {
    this.logger.info('Audit Event', {
      action,
      userId,
      resource,
      success,
      ipAddress,
      timestamp: new Date().toISOString(),
      ...additionalContext,
    });
  }

  /**
   * Log performance metrics
   */
  performance(
    operation: string,
    duration: number,
    additionalContext?: LogContext
  ): void {
    this.logger.info('Performance Metric', {
      operation,
      duration,
      timestamp: new Date().toISOString(),
      ...additionalContext,
    });
  }

  /**
   * Get the underlying Winston logger
   */
  getWinstonLogger(): winston.Logger {
    return this.logger;
  }
}

// Create default logger instance
export const defaultLogger = new Logger('Auth');

// Performance timing utility
export class PerformanceTimer {
  private startTime: number;
  private logger: Logger;
  private operation: string;

  constructor(operation: string, logger: Logger = defaultLogger) {
    this.operation = operation;
    this.logger = logger;
    this.startTime = Date.now();
  }

  end(additionalContext?: LogContext): number {
    const duration = Date.now() - this.startTime;
    this.logger.performance(this.operation, duration, additionalContext);
    return duration;
  }
}

// Request logging middleware helper
export function logRequest(req: any, res: any, duration: number): void {
  const logger = new Logger('HTTP');

  logger.info('HTTP Request', {
    method: req.method,
    url: req.url,
    statusCode: res.statusCode,
    duration,
    userAgent: req.get('user-agent'),
    ip: req.ip || req.connection.remoteAddress,
    userId: req.user?.id,
  });
}
