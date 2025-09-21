/**
 * PAKE System - Video Generation Service Logger
 * Structured logging utility optimized for video processing workflows
 */

import fs from 'fs';
import path from 'path';

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
  FATAL = 4,
}

export interface LogEntry {
  timestamp: Date;
  level: LogLevel;
  component: string;
  message: string;
  data?: any;
  error?: Error;
  videoId?: string;
  jobId?: string;
  provider?: string;
}

export interface LoggerConfig {
  level: LogLevel;
  console: boolean;
  file: boolean;
  filePath?: string;
  maxFileSize?: number;
  maxFiles?: number;
  structured?: boolean;
}

/**
 * Logger optimized for video generation service
 */
export class Logger {
  private component: string;
  private config: LoggerConfig;
  private logFilePath?: string;

  constructor(component: string, config?: Partial<LoggerConfig>) {
    this.component = component;

    this.config = {
      level: this.parseLogLevel(process.env.LOG_LEVEL) || LogLevel.INFO,
      console: true,
      file: process.env.NODE_ENV === 'production',
      filePath: process.env.LOG_PATH || 'logs',
      maxFileSize: 10 * 1024 * 1024, // 10MB
      maxFiles: 10,
      structured: true,
      ...config,
    };

    if (this.config.file) {
      this.setupFileLogging();
    }
  }

  debug(message: string, data?: any): void {
    this.log(LogLevel.DEBUG, message, data);
  }

  info(message: string, data?: any): void {
    this.log(LogLevel.INFO, message, data);
  }

  warn(message: string, data?: any): void {
    this.log(LogLevel.WARN, message, data);
  }

  error(message: string, error?: any, data?: any): void {
    const errorObj =
      error instanceof Error
        ? error
        : error && error.message
          ? new Error(error.message)
          : error
            ? new Error(String(error))
            : undefined;

    this.log(LogLevel.ERROR, message, data, errorObj);
  }

  fatal(message: string, error?: any, data?: any): void {
    const errorObj =
      error instanceof Error
        ? error
        : error && error.message
          ? new Error(error.message)
          : error
            ? new Error(String(error))
            : undefined;

    this.log(LogLevel.FATAL, message, data, errorObj);
  }

  /**
   * Create child logger with video-specific context
   */
  child(context: {
    videoId?: string;
    jobId?: string;
    provider?: string;
  }): Logger {
    const childLogger = new Logger(this.component, this.config);

    const originalLog = childLogger.log.bind(childLogger);
    childLogger.log = (
      level: LogLevel,
      message: string,
      data?: any,
      error?: Error
    ) => {
      const contextualData = { ...context, ...data };
      originalLog(level, message, contextualData, error);
    };

    return childLogger;
  }

  private log(
    level: LogLevel,
    message: string,
    data?: any,
    error?: Error
  ): void {
    if (level < this.config.level) {
      return;
    }

    const logEntry: LogEntry = {
      timestamp: new Date(),
      level,
      component: this.component,
      message,
      data,
      error,
      videoId: data?.videoId,
      jobId: data?.jobId,
      provider: data?.provider,
    };

    if (this.config.console) {
      this.writeToConsole(logEntry);
    }

    if (this.config.file && this.logFilePath) {
      this.writeToFile(logEntry);
    }
  }

  private writeToConsole(entry: LogEntry): void {
    const timestamp = entry.timestamp.toISOString();
    const levelStr = LogLevel[entry.level].padEnd(5);
    const component = entry.component.padEnd(20);

    let output = `${timestamp} [${levelStr}] ${component} ${entry.message}`;

    // Add video context if present
    if (entry.videoId || entry.jobId || entry.provider) {
      const context = [];
      if (entry.provider) context.push(`provider=${entry.provider}`);
      if (entry.videoId) context.push(`video=${entry.videoId}`);
      if (entry.jobId) context.push(`job=${entry.jobId}`);
      output += ` (${context.join(', ')})`;
    }

    // Add structured data
    if (entry.data && Object.keys(entry.data).length > 0) {
      if (this.config.structured) {
        output += ` | ${JSON.stringify(entry.data)}`;
      } else {
        output += ` | ${this.formatDataForConsole(entry.data)}`;
      }
    }

    // Add error details
    if (entry.error) {
      output += `\n  Error: ${entry.error.message}`;
      if (entry.error.stack && entry.level >= LogLevel.ERROR) {
        output += `\n  Stack: ${entry.error.stack}`;
      }
    }

    switch (entry.level) {
      case LogLevel.DEBUG:
        console.debug(output);
        break;
      case LogLevel.INFO:
        console.info(output);
        break;
      case LogLevel.WARN:
        console.warn(output);
        break;
      case LogLevel.ERROR:
      case LogLevel.FATAL:
        console.error(output);
        break;
    }
  }

  private writeToFile(entry: LogEntry): void {
    if (!this.logFilePath) return;

    try {
      let logLine: string;

      if (this.config.structured) {
        const logObject = {
          timestamp: entry.timestamp.toISOString(),
          level: LogLevel[entry.level],
          component: entry.component,
          message: entry.message,
          ...(entry.videoId && { videoId: entry.videoId }),
          ...(entry.jobId && { jobId: entry.jobId }),
          ...(entry.provider && { provider: entry.provider }),
          ...(entry.data && { data: entry.data }),
          ...(entry.error && {
            error: {
              message: entry.error.message,
              stack: entry.error.stack,
            },
          }),
        };
        logLine = JSON.stringify(logObject) + '\n';
      } else {
        logLine = `${entry.timestamp.toISOString()} [${LogLevel[entry.level]}] ${entry.component} ${entry.message}`;

        if (entry.data) {
          logLine += ` | ${this.formatDataForFile(entry.data)}`;
        }

        if (entry.error) {
          logLine += ` | ERROR: ${entry.error.message}`;
        }

        logLine += '\n';
      }

      this.checkAndRotateLog();
      fs.appendFileSync(this.logFilePath, logLine, 'utf8');
    } catch (error) {
      console.error(`Failed to write to log file: ${error.message}`);
    }
  }

  private setupFileLogging(): void {
    try {
      const logDir = this.config.filePath!;

      if (!fs.existsSync(logDir)) {
        fs.mkdirSync(logDir, { recursive: true });
      }

      const timestamp = new Date().toISOString().split('T')[0];
      const fileName = `video-generation-${this.component.toLowerCase()}-${timestamp}.log`;
      this.logFilePath = path.join(logDir, fileName);

      if (!fs.existsSync(this.logFilePath)) {
        fs.writeFileSync(this.logFilePath, '');
      }
    } catch (error) {
      console.error(`Failed to setup file logging: ${error.message}`);
      this.config.file = false;
    }
  }

  private checkAndRotateLog(): void {
    if (!this.logFilePath || !this.config.maxFileSize) return;

    try {
      const stats = fs.statSync(this.logFilePath);

      if (stats.size > this.config.maxFileSize) {
        this.rotateLogFile();
      }
    } catch (error) {
      // File might not exist yet
    }
  }

  private rotateLogFile(): void {
    if (!this.logFilePath) return;

    try {
      const logDir = path.dirname(this.logFilePath);
      const logFileName = path.basename(this.logFilePath, '.log');

      let rotationNum = 1;
      let rotatedPath = path.join(logDir, `${logFileName}.${rotationNum}.log`);

      while (
        fs.existsSync(rotatedPath) &&
        rotationNum < (this.config.maxFiles || 10)
      ) {
        rotationNum++;
        rotatedPath = path.join(logDir, `${logFileName}.${rotationNum}.log`);
      }

      if (rotationNum >= (this.config.maxFiles || 10)) {
        const oldestPath = path.join(
          logDir,
          `${logFileName}.${this.config.maxFiles}.log`
        );
        if (fs.existsSync(oldestPath)) {
          fs.unlinkSync(oldestPath);
        }

        for (let i = this.config.maxFiles! - 1; i >= 1; i--) {
          const oldPath = path.join(logDir, `${logFileName}.${i}.log`);
          const newPath = path.join(logDir, `${logFileName}.${i + 1}.log`);

          if (fs.existsSync(oldPath)) {
            fs.renameSync(oldPath, newPath);
          }
        }

        rotatedPath = path.join(logDir, `${logFileName}.1.log`);
      }

      fs.renameSync(this.logFilePath, rotatedPath);
      fs.writeFileSync(this.logFilePath, '');
    } catch (error) {
      console.error(`Failed to rotate log file: ${error.message}`);
    }
  }

  private formatDataForConsole(data: any): string {
    if (typeof data === 'string') return data;
    if (typeof data === 'number' || typeof data === 'boolean')
      return String(data);

    if (typeof data === 'object' && data !== null) {
      const keys = Object.keys(data);
      if (keys.length === 1) {
        return `${keys[0]}=${data[keys[0]]}`;
      } else if (keys.length <= 3) {
        return keys.map(key => `${key}=${data[key]}`).join(' ');
      }
    }

    return JSON.stringify(data);
  }

  private formatDataForFile(data: any): string {
    try {
      return JSON.stringify(data);
    } catch (error) {
      return String(data);
    }
  }

  private parseLogLevel(levelStr?: string): LogLevel | null {
    if (!levelStr) return null;

    const upperLevel = levelStr.toUpperCase();
    switch (upperLevel) {
      case 'DEBUG':
        return LogLevel.DEBUG;
      case 'INFO':
        return LogLevel.INFO;
      case 'WARN':
      case 'WARNING':
        return LogLevel.WARN;
      case 'ERROR':
        return LogLevel.ERROR;
      case 'FATAL':
        return LogLevel.FATAL;
      default:
        return null;
    }
  }

  getLevel(): LogLevel {
    return this.config.level;
  }

  setLevel(level: LogLevel): void {
    this.config.level = level;
  }

  isLevelEnabled(level: LogLevel): boolean {
    return level >= this.config.level;
  }

  /**
   * Create timing logger for video processing operations
   */
  timer(label: string): { end: (data?: any) => void } {
    const startTime = process.hrtime.bigint();

    return {
      end: (data?: any) => {
        const endTime = process.hrtime.bigint();
        const durationMs = Number(endTime - startTime) / 1000000;

        this.debug(`${label} completed`, {
          duration: `${durationMs.toFixed(2)}ms`,
          ...data,
        });
      },
    };
  }

  /**
   * Log video processing milestone
   */
  videoMilestone(videoId: string, milestone: string, data?: any): void {
    this.info(`Video ${milestone}`, {
      videoId,
      milestone,
      ...data,
    });
  }

  /**
   * Log provider interaction
   */
  providerCall(provider: string, action: string, data?: any): void {
    this.debug(`Provider call: ${provider}.${action}`, {
      provider,
      action,
      ...data,
    });
  }
}

export default Logger;
