/**
 * Structured Logging System
 *
 * Provides comprehensive logging with structured data, log levels,
 * and integration with monitoring systems.
 */

import winston from 'winston';
import { ElasticsearchTransport } from 'winston-elasticsearch';

export interface LogContext {
  requestId?: string;
  taskId?: string;
  userId?: string;
  sessionId?: string;
  correlationId?: string;
  provider?: string;
  executionTime?: number;
  [key: string]: any;
}

export interface Logger {
  debug(message: string, context?: LogContext): void;
  info(message: string, context?: LogContext): void;
  warn(message: string, context?: LogContext): void;
  error(message: string, context?: LogContext): void;
  child(defaultContext: LogContext): Logger;
}

/**
 * Winston-based logger implementation with structured output
 */
export class StructuredLogger implements Logger {
  private readonly winston: winston.Logger;
  private readonly defaultContext: LogContext;

  constructor(name: string, defaultContext: LogContext = {}) {
    this.defaultContext = defaultContext;

    const formats = [
      winston.format.timestamp(),
      winston.format.errors({ stack: true }),
      winston.format.json(),
    ];

    // Add colorization for console in development
    if (process.env.NODE_ENV === 'development') {
      formats.push(winston.format.colorize());
      formats.push(winston.format.simple());
    }

    const transports: winston.transport[] = [
      new winston.transports.Console({
        level: process.env.LOG_LEVEL || 'info',
        format: winston.format.combine(...formats),
      }),
    ];

    // Add file transport for production
    if (process.env.NODE_ENV === 'production') {
      transports.push(
        new winston.transports.File({
          filename: 'logs/error.log',
          level: 'error',
          format: winston.format.combine(...formats),
        }),
        new winston.transports.File({
          filename: 'logs/combined.log',
          format: winston.format.combine(...formats),
        })
      );
    }

    // Add Elasticsearch transport if configured
    if (process.env.ELASTICSEARCH_URL) {
      transports.push(
        new ElasticsearchTransport({
          level: 'info',
          clientOpts: { node: process.env.ELASTICSEARCH_URL },
          index: `pake-system-logs-${new Date().toISOString().slice(0, 7)}`,
        })
      );
    }

    this.winston = winston.createLogger({
      level: process.env.LOG_LEVEL || 'info',
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.errors({ stack: true }),
        winston.format.json(),
        winston.format.printf(({ timestamp, level, message, ...meta }) => {
          return JSON.stringify({
            timestamp,
            level,
            message,
            service: 'pake-orchestrator',
            component: name,
            ...this.defaultContext,
            ...meta,
          });
        })
      ),
      transports,
      exitOnError: false,
    });
  }

  debug(message: string, context: LogContext = {}): void {
    this.winston.debug(message, { ...this.defaultContext, ...context });
  }

  info(message: string, context: LogContext = {}): void {
    this.winston.info(message, { ...this.defaultContext, ...context });
  }

  warn(message: string, context: LogContext = {}): void {
    this.winston.warn(message, { ...this.defaultContext, ...context });
  }

  error(message: string, context: LogContext = {}): void {
    this.winston.error(message, { ...this.defaultContext, ...context });
  }

  child(childContext: LogContext): Logger {
    return new StructuredLogger('child', { ...this.defaultContext, ...childContext });
  }
}

// Global logger instances
const loggers: Map<string, Logger> = new Map();

export function createLogger(name: string, defaultContext?: LogContext): Logger {
  if (!loggers.has(name)) {
    loggers.set(name, new StructuredLogger(name, defaultContext));
  }
  return loggers.get(name)!;
}
