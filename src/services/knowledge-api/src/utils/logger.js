import winston from 'winston';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const logFormat = winston.format.combine(
  winston.format.timestamp({
    format: 'YYYY-MM-DD HH:mm:ss.SSS',
  }),
  winston.format.errors({ stack: true }),
  winston.format.json()
);

const consoleFormat = winston.format.combine(
  winston.format.colorize(),
  winston.format.timestamp({
    format: 'HH:mm:ss',
  }),
  winston.format.printf(({ timestamp, level, message, ...meta }) => {
    let log = `${timestamp} [${level}] ${message}`;
    if (Object.keys(meta).length > 0) {
      log += ` ${JSON.stringify(meta)}`;
    }
    return log;
  })
);

export const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: logFormat,
  defaultMeta: {
    service: 'pake-knowledge-api',
    environment: process.env.NODE_ENV || 'development',
  },
  transports: [
    // Console output with colors for development
    new winston.transports.Console({
      format: consoleFormat,
      level: process.env.NODE_ENV === 'production' ? 'warn' : 'debug',
    }),

    // File output for production
    new winston.transports.File({
      filename: join(__dirname, '../..', 'logs', 'knowledge-api-error.log'),
      level: 'error',
      maxsize: 5242880, // 5MB
      maxFiles: 5,
    }),

    new winston.transports.File({
      filename: join(__dirname, '../..', 'logs', 'knowledge-api-combined.log'),
      maxsize: 5242880, // 5MB
      maxFiles: 5,
    }),
  ],

  exceptionHandlers: [
    new winston.transports.File({
      filename: join(
        __dirname,
        '../..',
        'logs',
        'knowledge-api-exceptions.log'
      ),
    }),
  ],

  rejectionHandlers: [
    new winston.transports.File({
      filename: join(
        __dirname,
        '../..',
        'logs',
        'knowledge-api-rejections.log'
      ),
    }),
  ],
});

// Add request correlation ID support
export function addCorrelationId(req, res, next) {
  req.correlationId =
    req.headers['x-correlation-id'] ||
    `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

  logger.defaultMeta.correlationId = req.correlationId;
  res.set('X-Correlation-ID', req.correlationId);

  next();
}
