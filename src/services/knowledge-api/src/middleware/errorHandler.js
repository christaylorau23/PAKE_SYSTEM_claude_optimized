import { logger } from '../utils/logger.js';

export function errorHandler(error, req, res, next) {
  // Log the error
  logger.error('Unhandled error:', {
    error: error.message,
    stack: error.stack,
    url: req.originalUrl,
    method: req.method,
    ip: req.ip,
    userAgent: req.get('User-Agent'),
    correlationId: req.correlationId,
  });

  // Default error response
  let statusCode = 500;
  let errorResponse = {
    success: false,
    error: 'Internal Server Error',
    message: 'An unexpected error occurred',
    requestId: req.correlationId,
    timestamp: new Date().toISOString(),
  };

  // Handle specific error types
  if (error.name === 'ValidationError') {
    statusCode = 400;
    errorResponse.error = 'Validation Error';
    errorResponse.message = error.message;
  } else if (error.name === 'CastError') {
    statusCode = 400;
    errorResponse.error = 'Invalid Input';
    errorResponse.message = 'Invalid input format';
  } else if (error.code === 'ENOENT') {
    statusCode = 404;
    errorResponse.error = 'File Not Found';
    errorResponse.message = 'The requested file or resource was not found';
  } else if (error.code === 'EACCES') {
    statusCode = 403;
    errorResponse.error = 'Access Denied';
    errorResponse.message = 'Permission denied to access the resource';
  } else if (error.code === 'EMFILE' || error.code === 'ENFILE') {
    statusCode = 503;
    errorResponse.error = 'Service Temporarily Unavailable';
    errorResponse.message = 'Too many files open, please try again later';
  }

  // Include error details in development
  if (process.env.NODE_ENV === 'development') {
    errorResponse.details = {
      stack: error.stack,
      code: error.code,
      errno: error.errno,
    };
  }

  res.status(statusCode).json(errorResponse);
}
