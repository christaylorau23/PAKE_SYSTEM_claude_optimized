/**
 * JWT Token Service
 * Handles JWT token creation, validation, and management
 */

import jwt from 'jsonwebtoken';
import { v4 as uuidv4 } from 'uuid';
import { AuthToken, JWTPayload, User } from '../types';
import { authConfig } from '../config/auth.config';
import { RedisService } from './RedisService';
import { Logger } from '../utils/logger';

export class TokenService {
  private readonly logger = new Logger('TokenService');
  private readonly redis: RedisService;

  constructor(redis: RedisService) {
    this.redis = redis;
  }

  /**
   * Generate access and refresh tokens for a user
   */
  async generateTokens(
    user: User,
    sessionId: string,
    mfaVerified = false
  ): Promise<AuthToken> {
    const payload: JWTPayload = {
      sub: user.id,
      email: user.email,
      username: user.username,
      roles: user.roles.map(r => r.name),
      permissions: user.permissions.map(p => `${p.resource}:${p.action}`),
      iat: Math.floor(Date.now() / 1000),
      exp:
        Math.floor(Date.now() / 1000) +
        this.parseTokenExpiry(authConfig.jwt.accessTokenExpiry),
      iss: authConfig.jwt.issuer,
      aud: authConfig.jwt.audience,
      sessionId,
      mfaVerified,
    };

    const accessToken = jwt.sign(payload, authConfig.jwt.secret, {
      algorithm: 'HS256',
    });

    const refreshTokenId = uuidv4();
    const refreshToken = jwt.sign(
      {
        sub: user.id,
        sessionId,
        tokenId: refreshTokenId,
        type: 'refresh',
      },
      authConfig.jwt.secret,
      {
        expiresIn: authConfig.jwt.refreshTokenExpiry,
        algorithm: 'HS256',
      }
    );

    // Store refresh token in Redis with expiry
    const refreshTokenExpiry = this.parseTokenExpiry(
      authConfig.jwt.refreshTokenExpiry
    );
    await this.redis.setex(
      `refresh_token:${refreshTokenId}`,
      refreshTokenExpiry,
      JSON.stringify({
        userId: user.id,
        sessionId,
        createdAt: new Date().toISOString(),
        lastUsed: new Date().toISOString(),
      })
    );

    this.logger.info('Tokens generated successfully', {
      userId: user.id,
      sessionId,
    });

    return {
      accessToken,
      refreshToken,
      tokenType: 'Bearer',
      expiresIn: this.parseTokenExpiry(authConfig.jwt.accessTokenExpiry),
      scope: 'read write',
    };
  }

  /**
   * Verify and decode JWT token
   */
  async verifyToken(token: string): Promise<JWTPayload | null> {
    try {
      const payload = jwt.verify(token, authConfig.jwt.secret, {
        algorithms: ['HS256'],
        issuer: authConfig.jwt.issuer,
        audience: authConfig.jwt.audience,
      }) as JWTPayload;

      // Check if session is still active
      const sessionActive = await this.redis.exists(
        `session:${payload.sessionId}`
      );
      if (!sessionActive) {
        this.logger.warn('Token verification failed: session not active', {
          sessionId: payload.sessionId,
        });
        return null;
      }

      return payload;
    } catch (error) {
      this.logger.warn('Token verification failed', { error: error.message });
      return null;
    }
  }

  /**
   * Refresh access token using refresh token
   */
  async refreshToken(refreshToken: string): Promise<AuthToken | null> {
    try {
      const payload = jwt.verify(refreshToken, authConfig.jwt.secret) as any;

      if (payload.type !== 'refresh') {
        throw new Error('Invalid token type');
      }

      // Check if refresh token exists in Redis
      const tokenData = await this.redis.get(
        `refresh_token:${payload.tokenId}`
      );
      if (!tokenData) {
        this.logger.warn('Refresh token not found in store', {
          tokenId: payload.tokenId,
        });
        return null;
      }

      const { userId, sessionId } = JSON.parse(tokenData);

      // Check if session is still active
      const sessionData = await this.redis.get(`session:${sessionId}`);
      if (!sessionData) {
        this.logger.warn('Session not active for refresh token', { sessionId });
        return null;
      }

      // Update last used timestamp
      await this.redis.setex(
        `refresh_token:${payload.tokenId}`,
        this.parseTokenExpiry(authConfig.jwt.refreshTokenExpiry),
        JSON.stringify({
          userId,
          sessionId,
          createdAt: JSON.parse(tokenData).createdAt,
          lastUsed: new Date().toISOString(),
        })
      );

      // Get user data to generate new access token
      // Note: In a real implementation, you'd fetch this from the database
      const userData = JSON.parse(sessionData);

      const newAccessToken = jwt.sign(
        {
          sub: userId,
          email: userData.email,
          username: userData.username,
          roles: userData.roles || [],
          permissions: userData.permissions || [],
          iat: Math.floor(Date.now() / 1000),
          exp:
            Math.floor(Date.now() / 1000) +
            this.parseTokenExpiry(authConfig.jwt.accessTokenExpiry),
          iss: authConfig.jwt.issuer,
          aud: authConfig.jwt.audience,
          sessionId,
          mfaVerified: userData.mfaVerified || false,
        },
        authConfig.jwt.secret,
        { algorithm: 'HS256' }
      );

      this.logger.info('Access token refreshed successfully', {
        userId,
        sessionId,
      });

      return {
        accessToken: newAccessToken,
        refreshToken, // Keep the same refresh token
        tokenType: 'Bearer',
        expiresIn: this.parseTokenExpiry(authConfig.jwt.accessTokenExpiry),
        scope: 'read write',
      };
    } catch (error) {
      this.logger.warn('Token refresh failed', { error: error.message });
      return null;
    }
  }

  /**
   * Revoke refresh token
   */
  async revokeRefreshToken(refreshToken: string): Promise<boolean> {
    try {
      const payload = jwt.verify(refreshToken, authConfig.jwt.secret) as any;

      if (payload.type !== 'refresh') {
        return false;
      }

      const deleted = await this.redis.del(`refresh_token:${payload.tokenId}`);

      this.logger.info('Refresh token revoked', { tokenId: payload.tokenId });
      return deleted > 0;
    } catch (error) {
      this.logger.warn('Token revocation failed', { error: error.message });
      return false;
    }
  }

  /**
   * Revoke all refresh tokens for a user
   */
  async revokeAllUserTokens(userId: string): Promise<number> {
    try {
      const keys = await this.redis.keys(`refresh_token:*`);
      let revokedCount = 0;

      for (const key of keys) {
        const tokenData = await this.redis.get(key);
        if (tokenData) {
          const { userId: tokenUserId } = JSON.parse(tokenData);
          if (tokenUserId === userId) {
            await this.redis.del(key);
            revokedCount++;
          }
        }
      }

      this.logger.info('All user tokens revoked', {
        userId,
        count: revokedCount,
      });
      return revokedCount;
    } catch (error) {
      this.logger.error('Failed to revoke all user tokens', {
        userId,
        error: error.message,
      });
      return 0;
    }
  }

  /**
   * Clean up expired tokens
   */
  async cleanupExpiredTokens(): Promise<number> {
    try {
      const keys = await this.redis.keys(`refresh_token:*`);
      let cleanedCount = 0;

      for (const key of keys) {
        const ttl = await this.redis.ttl(key);
        if (ttl <= 0) {
          await this.redis.del(key);
          cleanedCount++;
        }
      }

      if (cleanedCount > 0) {
        this.logger.info('Expired tokens cleaned up', { count: cleanedCount });
      }

      return cleanedCount;
    } catch (error) {
      this.logger.error('Token cleanup failed', { error: error.message });
      return 0;
    }
  }

  /**
   * Parse token expiry string to seconds
   */
  private parseTokenExpiry(expiry: string): number {
    const unit = expiry.slice(-1);
    const value = parseInt(expiry.slice(0, -1));

    switch (unit) {
      case 's':
        return value;
      case 'm':
        return value * 60;
      case 'h':
        return value * 60 * 60;
      case 'd':
        return value * 24 * 60 * 60;
      case 'w':
        return value * 7 * 24 * 60 * 60;
      default:
        return parseInt(expiry); // Assume seconds if no unit
    }
  }

  /**
   * Get token information without verification
   */
  decodeToken(token: string): any {
    try {
      return jwt.decode(token, { complete: true });
    } catch (error) {
      return null;
    }
  }

  /**
   * Check if token is expired
   */
  isTokenExpired(token: string): boolean {
    try {
      const decoded = jwt.decode(token) as any;
      if (!decoded || !decoded.exp) {
        return true;
      }
      return decoded.exp < Math.floor(Date.now() / 1000);
    } catch (error) {
      return true;
    }
  }
}
