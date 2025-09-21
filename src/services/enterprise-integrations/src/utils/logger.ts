import winston from 'winston';
import DailyRotateFile from 'winston-daily-rotate-file';

export class Logger {
  private static instance: Logger;
  private winston: winston.Logger;

  private constructor() {
    this.winston = winston.createLogger({
      level: process.env.LOG_LEVEL || 'info',
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.errors({ stack: true }),
        winston.format.json(),
        winston.format.printf(
          ({ timestamp, level, message, stack, ...meta }) => {
            let log = `${timestamp} [${level.toUpperCase()}]: ${message}`;

            if (Object.keys(meta).length > 0) {
              log += ` ${JSON.stringify(meta)}`;
            }

            if (stack) {
              log += `\n${stack}`;
            }

            return log;
          }
        )
      ),
      transports: [
        new winston.transports.Console({
          format: winston.format.combine(
            winston.format.colorize(),
            winston.format.simple()
          ),
        }),
        new DailyRotateFile({
          filename: 'logs/application-%DATE%.log',
          datePattern: 'YYYY-MM-DD',
          zippedArchive: true,
          maxSize: '20m',
          maxFiles: '14d',
        }),
        new DailyRotateFile({
          level: 'error',
          filename: 'logs/error-%DATE%.log',
          datePattern: 'YYYY-MM-DD',
          zippedArchive: true,
          maxSize: '20m',
          maxFiles: '30d',
        }),
      ],
      exceptionHandlers: [
        new winston.transports.File({ filename: 'logs/exceptions.log' }),
      ],
      rejectionHandlers: [
        new winston.transports.File({ filename: 'logs/rejections.log' }),
      ],
    });
  }

  public static getInstance(): Logger {
    if (!Logger.instance) {
      Logger.instance = new Logger();
    }
    return Logger.instance;
  }

  info(message: string, meta?: any): void {
    this.winston.info(message, meta);
  }

  warn(message: string, meta?: any): void {
    this.winston.warn(message, meta);
  }

  error(message: string, error?: any, meta?: any): void {
    if (error instanceof Error) {
      this.winston.error(message, {
        error: error.message,
        stack: error.stack,
        ...meta,
      });
    } else if (error) {
      this.winston.error(message, { error, ...meta });
    } else {
      this.winston.error(message, meta);
    }
  }

  debug(message: string, meta?: any): void {
    this.winston.debug(message, meta);
  }

  verbose(message: string, meta?: any): void {
    this.winston.verbose(message, meta);
  }

  silly(message: string, meta?: any): void {
    this.winston.silly(message, meta);
  }

  log(level: string, message: string, meta?: any): void {
    this.winston.log(level, message, meta);
  }

  child(defaultMeta: any): winston.Logger {
    return this.winston.child(defaultMeta);
  }

  profile(id: string): void {
    this.winston.profile(id);
  }

  startTimer(): winston.Profiler {
    return this.winston.startTimer();
  }
}
