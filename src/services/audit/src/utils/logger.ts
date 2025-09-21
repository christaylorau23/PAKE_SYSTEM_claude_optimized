/**
 * Centralized Logger for Audit System
 * Provides structured logging with different levels and audit-specific formatting
 */

import winston from 'winston';
import { LogstashTransport } from 'winston-logstash-ts';

export class Logger {
  private logger: winston.Logger;
  private context: string;

  constructor(context: string = 'AuditSystem') {
    this.context = context;

    // Create transports array
    const transports: winston.transport[] = [
      new winston.transports.Console({
        format: winston.format.combine(
          winston.format.colorize(),
          winston.format.simple()
        ),
      }),
      new winston.transports.File({
        filename: 'logs/audit-error.log',
        level: 'error',
        maxsize: 10485760, // 10MB
        maxFiles: 5,
      }),
      new winston.transports.File({
        filename: 'logs/audit-combined.log',
        maxsize: 10485760, // 10MB
        maxFiles: 10,
      }),
    ];

    // Add Logstash transport if configured
    if (process.env.LOGSTASH_HOST && process.env.LOGSTASH_PORT) {
      try {
        transports.push(
          new LogstashTransport({
            host: process.env.LOGSTASH_HOST,
            port: parseInt(process.env.LOGSTASH_PORT),
            format: winston.format.json(),
            level: process.env.LOGSTASH_LEVEL || 'info',
            node_name: process.env.LOGSTASH_NODE_NAME || 'pake-audit',
            tags: ['audit', 'pake-system', this.context],
          })
        );
      } catch (error) {
        console.error('Failed to initialize Logstash transport:', error);
      }
    }

    this.logger = winston.createLogger({
      level: process.env.LOG_LEVEL || 'info',
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.errors({ stack: true }),
        winston.format.json(),
        winston.format.printf(
          ({ timestamp, level, message, context, ...meta }) => {
            return JSON.stringify({
              timestamp,
              level,
              context: context || this.context,
              message,
              ...meta,
            });
          }
        )
      ),
      defaultMeta: {
        service: 'pake-audit',
        context: this.context,
      },
      transports,
    });

    // Handle uncaught exceptions and rejections
    this.logger.exceptions.handle(
      new winston.transports.File({ filename: 'logs/audit-exceptions.log' })
    );

    this.logger.rejections.handle(
      new winston.transports.File({ filename: 'logs/audit-rejections.log' })
    );
  }

  debug(message: string, meta: any = {}): void {
    this.logger.debug(message, { context: this.context, ...meta });
  }

  info(message: string, meta: any = {}): void {
    this.logger.info(message, { context: this.context, ...meta });
  }

  warn(message: string, meta: any = {}): void {
    this.logger.warn(message, { context: this.context, ...meta });
  }

  error(message: string, meta: any = {}): void {
    this.logger.error(message, { context: this.context, ...meta });
  }

  fatal(message: string, meta: any = {}): void {
    this.logger.error(message, { context: this.context, fatal: true, ...meta });
    process.exit(1);
  }

  // Audit-specific logging methods
  auditLog(event: any, meta: any = {}): void {
    this.logger.info('AUDIT_EVENT', {
      context: this.context,
      auditEvent: event,
      ...meta,
    });
  }

  securityLog(event: any, meta: any = {}): void {
    this.logger.warn('SECURITY_EVENT', {
      context: this.context,
      securityEvent: event,
      ...meta,
    });
  }

  complianceLog(event: any, meta: any = {}): void {
    this.logger.info('COMPLIANCE_EVENT', {
      context: this.context,
      complianceEvent: event,
      ...meta,
    });
  }

  // Performance logging
  startTimer(label: string): () => void {
    const start = Date.now();
    return () => {
      const duration = Date.now() - start;
      this.debug(`Timer: ${label}`, { duration: `${duration}ms` });
    };
  }

  // Create child logger with additional context
  child(additionalContext: any): Logger {
    const childLogger = new Logger(
      `${this.context}:${additionalContext.component || 'child'}`
    );
    return childLogger;
  }
}
