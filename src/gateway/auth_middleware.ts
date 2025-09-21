/**
 * Authentication Middleware for API Gateway
 * Handles JWT token validation and user authentication
 */

import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import { SecretsValidator } from '../utils/secrets_validator';
import { Logger } from '../utils/logger';

export interface AuthenticatedRequest extends Request {
  user?: {
    id: string;
    email: string;
    roles: string[];
    permissions: string[];
    sessionId: string;
  };
  session?: {
    id: string;
    userId: string;
    isActive: boolean;
    expiresAt: Date;
  };
}

export interface JWTPayload {
  sub: string; // User ID
  email: string;
  roles: string[];
  permissions: string[];
  sessionId: string;
  iat: number; // Issued at
  exp: number; // Expires at
  iss: string; // Issuer
  aud: string; // Audience
}

export class AuthMiddleware {
  private static logger = new Logger('AuthMiddleware');
  private static jwtSecret: string;

  static {
    // Initialize JWT secret
    try {
      this.jwtSecret = SecretsValidator.getRequiredSecret('JWT_SECRET');
    } catch (error) {
      this.logger.error('Failed to initialize JWT secret', {
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Authenticate request using JWT token
   */
  public static authenticate(
    req: AuthenticatedRequest,
    res: Response,
    next: NextFunction
  ): void {
    try {
      const token = this.extractToken(req);

      if (!token) {
        return res.status(401).json({
          error: 'Authentication required',
          code: 'MISSING_TOKEN',
        });
      }

      const payload = this.verifyToken(token);
      req.user = {
        id: payload.sub,
        email: payload.email,
        roles: payload.roles,
        permissions: payload.permissions,
        sessionId: payload.sessionId,
      };

      this.logger.debug('User authenticated', {
        userId: payload.sub,
        email: payload.email,
        sessionId: payload.sessionId,
      });

      next();
    } catch (error) {
      this.logger.warn('Authentication failed', {
        error: error.message,
        ip: req.ip,
        userAgent: req.get('User-Agent'),
      });

      if (error.name === 'TokenExpiredError') {
        return res.status(401).json({
          error: 'Token expired',
          code: 'TOKEN_EXPIRED',
        });
      }

      if (error.name === 'JsonWebTokenError') {
        return res.status(401).json({
          error: 'Invalid token',
          code: 'INVALID_TOKEN',
        });
      }

      return res.status(401).json({
        error: 'Authentication failed',
        code: 'AUTH_FAILED',
      });
    }
  }

  /**
   * Optional authentication - doesn't fail if no token
   */
  public static optionalAuth(
    req: AuthenticatedRequest,
    res: Response,
    next: NextFunction
  ): void {
    try {
      const token = this.extractToken(req);

      if (token) {
        const payload = this.verifyToken(token);
        req.user = {
          id: payload.sub,
          email: payload.email,
          roles: payload.roles,
          permissions: payload.permissions,
          sessionId: payload.sessionId,
        };
      }

      next();
    } catch (error) {
      // For optional auth, we just continue without user info
      this.logger.debug('Optional authentication failed', {
        error: error.message,
      });
      next();
    }
  }

  /**
   * Require specific role
   */
  public static requireRole(role: string) {
    return (
      req: AuthenticatedRequest,
      res: Response,
      next: NextFunction
    ): void => {
      if (!req.user) {
        return res.status(401).json({
          error: 'Authentication required',
          code: 'MISSING_TOKEN',
        });
      }

      if (!req.user.roles.includes(role)) {
        this.logger.warn('Insufficient role', {
          userId: req.user.id,
          requiredRole: role,
          userRoles: req.user.roles,
        });

        return res.status(403).json({
          error: 'Insufficient permissions',
          code: 'INSUFFICIENT_ROLE',
          required: role,
        });
      }

      next();
    };
  }

  /**
   * Require specific permission
   */
  public static requirePermission(permission: string) {
    return (
      req: AuthenticatedRequest,
      res: Response,
      next: NextFunction
    ): void => {
      if (!req.user) {
        return res.status(401).json({
          error: 'Authentication required',
          code: 'MISSING_TOKEN',
        });
      }

      if (!req.user.permissions.includes(permission)) {
        this.logger.warn('Insufficient permission', {
          userId: req.user.id,
          requiredPermission: permission,
          userPermissions: req.user.permissions,
        });

        return res.status(403).json({
          error: 'Insufficient permissions',
          code: 'INSUFFICIENT_PERMISSION',
          required: permission,
        });
      }

      next();
    };
  }

  /**
   * Require any of the specified roles
   */
  public static requireAnyRole(roles: string[]) {
    return (
      req: AuthenticatedRequest,
      res: Response,
      next: NextFunction
    ): void => {
      if (!req.user) {
        return res.status(401).json({
          error: 'Authentication required',
          code: 'MISSING_TOKEN',
        });
      }

      const hasRole = roles.some(role => req.user!.roles.includes(role));

      if (!hasRole) {
        this.logger.warn('Insufficient role', {
          userId: req.user.id,
          requiredRoles: roles,
          userRoles: req.user.roles,
        });

        return res.status(403).json({
          error: 'Insufficient permissions',
          code: 'INSUFFICIENT_ROLE',
          required: roles,
        });
      }

      next();
    };
  }

  /**
   * Require any of the specified permissions
   */
  public static requireAnyPermission(permissions: string[]) {
    return (
      req: AuthenticatedRequest,
      res: Response,
      next: NextFunction
    ): void => {
      if (!req.user) {
        return res.status(401).json({
          error: 'Authentication required',
          code: 'MISSING_TOKEN',
        });
      }

      const hasPermission = permissions.some(permission =>
        req.user!.permissions.includes(permission)
      );

      if (!hasPermission) {
        this.logger.warn('Insufficient permission', {
          userId: req.user.id,
          requiredPermissions: permissions,
          userPermissions: req.user.permissions,
        });

        return res.status(403).json({
          error: 'Insufficient permissions',
          code: 'INSUFFICIENT_PERMISSION',
          required: permissions,
        });
      }

      next();
    };
  }

  /**
   * Extract token from request
   */
  private static extractToken(req: Request): string | null {
    // Check Authorization header
    const authHeader = req.get('Authorization');
    if (authHeader && authHeader.startsWith('Bearer ')) {
      return authHeader.substring(7);
    }

    // Check query parameter
    if (req.query.token && typeof req.query.token === 'string') {
      return req.query.token;
    }

    // Check cookies
    if (req.cookies && req.cookies.token) {
      return req.cookies.token;
    }

    return null;
  }

  /**
   * Verify JWT token
   */
  private static verifyToken(token: string): JWTPayload {
    const payload = jwt.verify(token, this.jwtSecret, {
      issuer: process.env.JWT_ISSUER || 'pake-system',
      audience: process.env.JWT_AUDIENCE || 'pake-users',
      algorithms: ['HS256'],
    }) as JWTPayload;

    // Validate required fields
    if (!payload.sub || !payload.email || !payload.sessionId) {
      throw new Error('Invalid token payload');
    }

    return payload;
  }

  /**
   * Generate JWT token
   */
  public static generateToken(
    payload: Omit<JWTPayload, 'iat' | 'exp' | 'iss' | 'aud'>
  ): string {
    const tokenPayload: JWTPayload = {
      ...payload,
      iat: Math.floor(Date.now() / 1000),
      exp: Math.floor(Date.now() / 1000) + 15 * 60, // 15 minutes
      iss: process.env.JWT_ISSUER || 'pake-system',
      aud: process.env.JWT_AUDIENCE || 'pake-users',
    };

    return jwt.sign(tokenPayload, this.jwtSecret, {
      algorithm: 'HS256',
    });
  }

  /**
   * Generate refresh token
   */
  public static generateRefreshToken(
    payload: Omit<JWTPayload, 'iat' | 'exp' | 'iss' | 'aud'>
  ): string {
    const tokenPayload: JWTPayload = {
      ...payload,
      iat: Math.floor(Date.now() / 1000),
      exp: Math.floor(Date.now() / 1000) + 7 * 24 * 60 * 60, // 7 days
      iss: process.env.JWT_ISSUER || 'pake-system',
      aud: process.env.JWT_AUDIENCE || 'pake-users',
    };

    return jwt.sign(tokenPayload, this.jwtSecret, {
      algorithm: 'HS256',
    });
  }

  /**
   * Decode token without verification (for debugging)
   */
  public static decodeToken(token: string): unknown {
    return jwt.decode(token);
  }

  /**
   * Get user from request
   */
  public static getUser(req: AuthenticatedRequest): unknown {
    return req.user;
  }

  /**
   * Check if user has role
   */
  public static hasRole(req: AuthenticatedRequest, role: string): boolean {
    return req.user?.roles.includes(role) || false;
  }

  /**
   * Check if user has permission
   */
  public static hasPermission(
    req: AuthenticatedRequest,
    permission: string
  ): boolean {
    return req.user?.permissions.includes(permission) || false;
  }
}
