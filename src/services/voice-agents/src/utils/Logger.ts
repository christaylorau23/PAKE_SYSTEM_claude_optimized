/**
 * PAKE System - Structured Logger for Voice Agents
 * Provides structured logging with multiple output formats and log levels
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
  requestId?: string;
  sessionId?: string;
  userId?: string;
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
 * Logger - Structured logging utility for voice agent services
 * Supports multiple output formats, log levels, and structured data
 */
export class Logger {
  private component: string;
  private config: LoggerConfig;
  private logFilePath?: string;

  constructor(component: string, config?: Partial<LoggerConfig>) {
    this.component = component;

    // Default configuration
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

    // Setup file logging if enabled
    if (this.config.file) {
      this.setupFileLogging();
    }
  }

  /**
   * Log debug message
   */
  debug(message: string, data?: any): void {
    this.log(LogLevel.DEBUG, message, data);
  }

  /**
   * Log info message
   */
  info(message: string, data?: any): void {
    this.log(LogLevel.INFO, message, data);
  }

  /**
   * Log warning message
   */
  warn(message: string, data?: any): void {
    this.log(LogLevel.WARN, message, data);
  }

  /**
   * Log error message
   */
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

  /**
   * Log fatal error message
   */
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
   * Create a child logger with additional context
   */
  child(context: { requestId?: string; sessionId?: string; userId?: string }): Logger {
    const childLogger = new Logger(this.component, this.config);

    // Override the log method to include context
    const originalLog = childLogger.log.bind(childLogger);
    childLogger.log = (level: LogLevel, message: string, data?: any, error?: Error) => {
      const contextualData = { ...context, ...data };
      originalLog(level, message, contextualData, error);
    };

    return childLogger;
  }

  /**
   * Core logging method
   */
  private log(level: LogLevel, message: string, data?: any, error?: Error): void {
    // Check if log level meets threshold
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
    };

    // Console output
    if (this.config.console) {
      this.writeToConsole(logEntry);
    }

    // File output
    if (this.config.file && this.logFilePath) {
      this.writeToFile(logEntry);
    }
  }

  /**
   * Write log entry to console
   */
  private writeToConsole(entry: LogEntry): void {
    const timestamp = entry.timestamp.toISOString();
    const levelStr = LogLevel[entry.level].padEnd(5);
    const component = entry.component.padEnd(20);

    let output = `${timestamp} [${levelStr}] ${component} ${entry.message}`;

    // Add structured data if present
    if (entry.data && Object.keys(entry.data).length > 0) {
      if (this.config.structured) {
        output += ` | ${JSON.stringify(entry.data)}`;
      } else {
        output += ` | ${this.formatDataForConsole(entry.data)}`;
      }
    }

    // Add error details if present
    if (entry.error) {
      output += `\n  Error: ${entry.error.message}`;
      if (entry.error.stack && entry.level >= LogLevel.ERROR) {
        output += `\n  Stack: ${entry.error.stack}`;
      }
    }

    // Use appropriate console method based on log level
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

  /**
   * Write log entry to file
   */
  private writeToFile(entry: LogEntry): void {
    if (!this.logFilePath) return;

    try {
      let logLine: string;

      if (this.config.structured) {
        // JSON structured logging
        const logObject = {
          timestamp: entry.timestamp.toISOString(),
          level: LogLevel[entry.level],
          component: entry.component,
          message: entry.message,
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
        // Plain text logging
        logLine = `${entry.timestamp.toISOString()} [${LogLevel[entry.level]}] ${entry.component} ${entry.message}`;

        if (entry.data) {
          logLine += ` | ${this.formatDataForFile(entry.data)}`;
        }

        if (entry.error) {
          logLine += ` | ERROR: ${entry.error.message}`;
        }

        logLine += '\n';
      }

      // Check file size and rotate if necessary
      this.checkAndRotateLog();

      // Append to log file
      fs.appendFileSync(this.logFilePath, logLine, 'utf8');
    } catch (error) {
      console.error(`Failed to write to log file: ${error.message}`);
    }
  }

  /**
   * Setup file logging directory and initial file
   */
  private setupFileLogging(): void {
    try {
      const logDir = this.config.filePath!;

      // Create log directory if it doesn't exist
      if (!fs.existsSync(logDir)) {
        fs.mkdirSync(logDir, { recursive: true });
      }

      // Create log file path
      const timestamp = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
      const fileName = `voice-agent-${this.component.toLowerCase()}-${timestamp}.log`;
      this.logFilePath = path.join(logDir, fileName);

      // Create file if it doesn't exist
      if (!fs.existsSync(this.logFilePath)) {
        fs.writeFileSync(this.logFilePath, '');
      }
    } catch (error) {
      console.error(`Failed to setup file logging: ${error.message}`);
      this.config.file = false; // Disable file logging on setup failure
    }
  }

  /**
   * Check file size and rotate log if necessary
   */
  private checkAndRotateLog(): void {
    if (!this.logFilePath || !this.config.maxFileSize) return;

    try {
      const stats = fs.statSync(this.logFilePath);

      if (stats.size > this.config.maxFileSize) {
        this.rotateLogFile();
      }
    } catch (error) {
      // File might not exist yet, ignore error
    }
  }

  /**
   * Rotate log file when it gets too large
   */
  private rotateLogFile(): void {
    if (!this.logFilePath) return;

    try {
      const logDir = path.dirname(this.logFilePath);
      const logFileName = path.basename(this.logFilePath, '.log');

      // Find next rotation number
      let rotationNum = 1;
      let rotatedPath = path.join(logDir, `${logFileName}.${rotationNum}.log`);

      while (fs.existsSync(rotatedPath) && rotationNum < (this.config.maxFiles || 10)) {
        rotationNum++;
        rotatedPath = path.join(logDir, `${logFileName}.${rotationNum}.log`);
      }

      // If we've reached max files, remove the oldest
      if (rotationNum >= (this.config.maxFiles || 10)) {
        const oldestPath = path.join(logDir, `${logFileName}.${this.config.maxFiles}.log`);
        if (fs.existsSync(oldestPath)) {
          fs.unlinkSync(oldestPath);
        }

        // Shift all files down
        for (let i = this.config.maxFiles! - 1; i >= 1; i--) {
          const oldPath = path.join(logDir, `${logFileName}.${i}.log`);
          const newPath = path.join(logDir, `${logFileName}.${i + 1}.log`);

          if (fs.existsSync(oldPath)) {
            fs.renameSync(oldPath, newPath);
          }
        }

        rotatedPath = path.join(logDir, `${logFileName}.1.log`);
      }

      // Rotate current log file
      fs.renameSync(this.logFilePath, rotatedPath);

      // Create new empty log file
      fs.writeFileSync(this.logFilePath, '');

      console.info(`Log file rotated: ${path.basename(rotatedPath)}`);
    } catch (error) {
      console.error(`Failed to rotate log file: ${error.message}`);
    }
  }

  /**
   * Format data object for console output
   */
  private formatDataForConsole(data: any): string {
    if (typeof data === 'string') return data;
    if (typeof data === 'number' || typeof data === 'boolean') return String(data);

    if (typeof data === 'object' && data !== null) {
      const keys = Object.keys(data);
      if (keys.length === 1) {
        return `${keys[0]}=${data[keys[0]]}`;
      } else if (keys.length <= 3) {
        return keys.map((key) => `${key}=${data[key]}`).join(' ');
      }
    }

    return JSON.stringify(data);
  }

  /**
   * Format data object for file output
   */
  private formatDataForFile(data: any): string {
    try {
      return JSON.stringify(data);
    } catch (error) {
      return String(data);
    }
  }

  /**
   * Parse log level from string
   */
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

  /**
   * Get current log level
   */
  getLevel(): LogLevel {
    return this.config.level;
  }

  /**
   * Set log level
   */
  setLevel(level: LogLevel): void {
    this.config.level = level;
  }

  /**
   * Check if a log level would be written
   */
  isLevelEnabled(level: LogLevel): boolean {
    return level >= this.config.level;
  }

  /**
   * Create timing logger for performance measurement
   */
  timer(label: string): { end: (data?: any) => void } {
    const startTime = process.hrtime.bigint();

    return {
      end: (data?: any) => {
        const endTime = process.hrtime.bigint();
        const durationMs = Number(endTime - startTime) / 1000000; // Convert to milliseconds

        this.debug(`${label} completed`, {
          duration: `${durationMs.toFixed(2)}ms`,
          ...data,
        });
      },
    };
  }

  /**
   * Create rate-limited logger to prevent log flooding
   */
  createRateLimited(maxLogsPerMinute: number = 10): {
    debug: (message: string, data?: any) => void;
    info: (message: string, data?: any) => void;
    warn: (message: string, data?: any) => void;
    error: (message: string, error?: any, data?: any) => void;
  } {
    const logCounts = new Map<string, { count: number; resetTime: number }>();

    const checkRateLimit = (key: string): boolean => {
      const now = Date.now();
      const minute = Math.floor(now / 60000);
      const entry = logCounts.get(key);

      if (!entry || entry.resetTime < minute) {
        logCounts.set(key, { count: 1, resetTime: minute });
        return true;
      }

      if (entry.count >= maxLogsPerMinute) {
        return false;
      }

      entry.count++;
      return true;
    };

    return {
      debug: (message: string, data?: any) => {
        if (checkRateLimit(`debug:${message}`)) {
          this.debug(message, data);
        }
      },
      info: (message: string, data?: any) => {
        if (checkRateLimit(`info:${message}`)) {
          this.info(message, data);
        }
      },
      warn: (message: string, data?: any) => {
        if (checkRateLimit(`warn:${message}`)) {
          this.warn(message, data);
        }
      },
      error: (message: string, error?: any, data?: any) => {
        if (checkRateLimit(`error:${message}`)) {
          this.error(message, error, data);
        }
      },
    };
  }

  /**
   * Flush any pending log writes (useful before shutdown)
   */
  flush(): void {
    // For file-based logging, this would ensure all writes are completed
    // Since we're using synchronous writes, this is mainly a placeholder
    // for future asynchronous implementations
  }
}

export default Logger;
