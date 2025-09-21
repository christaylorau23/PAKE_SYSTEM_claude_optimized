/**
 * Session Management Service
 * Handles user sessions with Redis storage and security features
 */

import { v4 as uuidv4 } from 'uuid';
import crypto from 'crypto';
import UAParser from 'ua-parser-js';
import { Session, DeviceInfo, User, LoginAttempt } from '../types';
import { authConfig } from '../config/auth.config';
import { RedisService } from './RedisService';
import { Logger } from '../utils/logger';
import { SecretsValidator } from '../../../utils/secrets_validator';

export class SessionService {
  private readonly logger = new Logger('SessionService');
  private readonly redis: RedisService;

  constructor(redis: RedisService) {
    this.redis = redis;
  }

  /**
   * Create new session for user
   */
  async createSession(
    user: User,
    ipAddress: string,
    userAgent: string,
    mfaVerified = false
  ): Promise<Session> {
    try {
      const deviceInfo = this.parseDeviceInfo(userAgent);
      const sessionId = uuidv4();
      const now = new Date();

      const session: Session = {
        id: sessionId,
        userId: user.id,
        deviceInfo,
        ipAddress,
        userAgent,
        isActive: true,
        lastActivityAt: now,
        expiresAt: new Date(now.getTime() + authConfig.session.maxAge * 1000),
        createdAt: now,
        metadata: {
          mfaVerified,
          loginMethod: 'secure_authentication', // Removed hardcoded REDACTED_SECRET fallback
          roles: user.roles.map(r => r.name),
          permissions: user.permissions.map(p => `${p.resource}:${p.action}`),
        },
      };

      // Check session limit for user
      await this.enforceSessionLimit(user.id);

      // Store session
      await this.redis.setex(
        `session:${sessionId}`,
        authConfig.session.maxAge,
        JSON.stringify(session)
      );

      // Add to user sessions list
      await this.redis.sadd(`user_sessions:${user.id}`, sessionId);

      // Store device tracking
      await this.trackDevice(user.id, deviceInfo);

      this.logger.info('Session created successfully', {
        sessionId,
        userId: user.id,
        deviceType: deviceInfo.deviceType,
        ipAddress,
      });

      return session;
    } catch (error) {
      this.logger.error('Failed to create session', {
        userId: user.id,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Get session by ID
   */
  async getSession(sessionId: string): Promise<Session | null> {
    try {
      const sessionData = await this.redis.get(`session:${sessionId}`);
      if (!sessionData) {
        return null;
      }

      const session: Session = JSON.parse(sessionData);

      // Check if session is expired
      if (new Date() > session.expiresAt) {
        await this.destroySession(sessionId);
        return null;
      }

      return session;
    } catch (error) {
      this.logger.error('Failed to get session', {
        sessionId,
        error: error.message,
      });
      return null;
    }
  }

  /**
   * Update session activity
   */
  async updateActivity(
    sessionId: string,
    ipAddress?: string
  ): Promise<boolean> {
    try {
      const session = await this.getSession(sessionId);
      if (!session) {
        return false;
      }

      const now = new Date();
      session.lastActivityAt = now;

      // Update IP address if provided and different
      if (ipAddress && ipAddress !== session.ipAddress) {
        session.ipAddress = ipAddress;
        this.logger.info('Session IP address updated', {
          sessionId,
          newIP: ipAddress,
        });
      }

      // Extend session if configured
      if (authConfig.session.extendOnActivity) {
        session.expiresAt = new Date(
          now.getTime() + authConfig.session.maxAge * 1000
        );

        // Update TTL in Redis
        await this.redis.expire(
          `session:${sessionId}`,
          authConfig.session.maxAge
        );
      }

      // Update session in Redis
      await this.redis.setex(
        `session:${sessionId}`,
        authConfig.session.maxAge,
        JSON.stringify(session)
      );

      return true;
    } catch (error) {
      this.logger.error('Failed to update session activity', {
        sessionId,
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Destroy session
   */
  async destroySession(sessionId: string): Promise<boolean> {
    try {
      const session = await this.getSession(sessionId);
      if (session) {
        // Remove from user sessions list
        await this.redis.srem(`user_sessions:${session.userId}`, sessionId);
      }

      // Delete session
      const deleted = await this.redis.del(`session:${sessionId}`);

      if (deleted > 0) {
        this.logger.info('Session destroyed', {
          sessionId,
          userId: session?.userId,
        });
      }

      return deleted > 0;
    } catch (error) {
      this.logger.error('Failed to destroy session', {
        sessionId,
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Get all active sessions for user
   */
  async getUserSessions(userId: string): Promise<Session[]> {
    try {
      const sessionIds = await this.redis.smembers(`user_sessions:${userId}`);
      const sessions: Session[] = [];

      for (const sessionId of sessionIds) {
        const session = await this.getSession(sessionId);
        if (session && session.isActive) {
          sessions.push(session);
        } else {
          // Clean up invalid session ID
          await this.redis.srem(`user_sessions:${userId}`, sessionId);
        }
      }

      return sessions.sort(
        (a, b) => b.lastActivityAt.getTime() - a.lastActivityAt.getTime()
      );
    } catch (error) {
      this.logger.error('Failed to get user sessions', {
        userId,
        error: error.message,
      });
      return [];
    }
  }

  /**
   * Destroy all sessions for user
   */
  async destroyAllUserSessions(
    userId: string,
    excludeSessionId?: string
  ): Promise<number> {
    try {
      const sessionIds = await this.redis.smembers(`user_sessions:${userId}`);
      let destroyedCount = 0;

      for (const sessionId of sessionIds) {
        if (sessionId !== excludeSessionId) {
          const destroyed = await this.destroySession(sessionId);
          if (destroyed) {
            destroyedCount++;
          }
        }
      }

      this.logger.info('User sessions destroyed', {
        userId,
        count: destroyedCount,
      });
      return destroyedCount;
    } catch (error) {
      this.logger.error('Failed to destroy user sessions', {
        userId,
        error: error.message,
      });
      return 0;
    }
  }

  /**
   * Verify session and get session info
   */
  async verifySession(
    sessionId: string,
    ipAddress?: string,
    userAgent?: string
  ): Promise<Session | null> {
    try {
      const session = await this.getSession(sessionId);
      if (!session || !session.isActive) {
        return null;
      }

      // Check for IP address changes (potential session hijacking)
      if (ipAddress && ipAddress !== session.ipAddress) {
        this.logger.warn('Session IP address mismatch', {
          sessionId,
          originalIP: session.ipAddress,
          newIP: ipAddress,
        });

        // For now, we'll allow it but log it. In production, you might want to:
        // 1. Force re-authentication
        // 2. Send security alert
        // 3. Destroy session

        // Update activity with new IP
        await this.updateActivity(sessionId, ipAddress);
      } else if (ipAddress) {
        // Update activity
        await this.updateActivity(sessionId, ipAddress);
      }

      return session;
    } catch (error) {
      this.logger.error('Session verification failed', {
        sessionId,
        error: error.message,
      });
      return null;
    }
  }

  /**
   * Clean up expired sessions
   */
  async cleanupExpiredSessions(): Promise<number> {
    try {
      const sessionKeys = await this.redis.keys('session:*');
      let cleanedCount = 0;

      for (const key of sessionKeys) {
        const ttl = await this.redis.ttl(key);
        if (ttl <= 0) {
          const sessionId = key.replace('session:', '');
          await this.destroySession(sessionId);
          cleanedCount++;
        }
      }

      if (cleanedCount > 0) {
        this.logger.info('Expired sessions cleaned up', {
          count: cleanedCount,
        });
      }

      return cleanedCount;
    } catch (error) {
      this.logger.error('Session cleanup failed', { error: error.message });
      return 0;
    }
  }

  /**
   * Record login attempt
   */
  async recordLoginAttempt(
    email: string,
    ipAddress: string,
    userAgent: string,
    success: boolean,
    userId?: string,
    failureReason?: string,
    mfaRequired = false
  ): Promise<void> {
    try {
      const attempt: LoginAttempt = {
        id: uuidv4(),
        userId,
        email,
        ipAddress,
        userAgent,
        success,
        failureReason,
        mfaRequired,
        attemptedAt: new Date(),
      };

      // Store attempt with 24 hour expiry
      await this.redis.setex(
        `login_attempt:${attempt.id}`,
        86400, // 24 hours
        JSON.stringify(attempt)
      );

      // Track failed attempts by IP and email for rate limiting
      if (!success) {
        await this.redis.incr(`failed_attempts_ip:${ipAddress}`);
        await this.redis.expire(`failed_attempts_ip:${ipAddress}`, 3600); // 1 hour

        if (userId) {
          await this.redis.incr(`failed_attempts_user:${userId}`);
          await this.redis.expire(`failed_attempts_user:${userId}`, 3600); // 1 hour
        }
      }

      this.logger.info('Login attempt recorded', {
        email,
        success,
        ipAddress,
        mfaRequired,
      });
    } catch (error) {
      this.logger.error('Failed to record login attempt', {
        email,
        error: error.message,
      });
    }
  }

  /**
   * Check if IP or user is locked out due to failed attempts
   */
  async isLockedOut(identifier: string, type: 'ip' | 'user'): Promise<boolean> {
    try {
      const key = `failed_attempts_${type}:${identifier}`;
      const attempts = await this.redis.get(key);

      if (!attempts) {
        return false;
      }

      const attemptCount = parseInt(attempts);
      return attemptCount >= authConfig.security.lockoutPolicy.maxAttempts;
    } catch (error) {
      this.logger.error('Lockout check failed', {
        identifier,
        type,
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Get failed attempt count
   */
  async getFailedAttemptCount(
    identifier: string,
    type: 'ip' | 'user'
  ): Promise<number> {
    try {
      const key = `failed_attempts_${type}:${identifier}`;
      const attempts = await this.redis.get(key);
      return attempts ? parseInt(attempts) : 0;
    } catch (error) {
      this.logger.error('Failed to get attempt count', {
        identifier,
        type,
        error: error.message,
      });
      return 0;
    }
  }

  /**
   * Clear failed attempts (after successful login)
   */
  async clearFailedAttempts(
    identifier: string,
    type: 'ip' | 'user'
  ): Promise<void> {
    try {
      const key = `failed_attempts_${type}:${identifier}`;
      await this.redis.del(key);
    } catch (error) {
      this.logger.error('Failed to clear attempt count', {
        identifier,
        type,
        error: error.message,
      });
    }
  }

  /**
   * Get session statistics
   */
  async getSessionStats(): Promise<{
    totalActiveSessions: number;
    sessionsPerUser: Record<string, number>;
    deviceTypes: Record<string, number>;
  }> {
    try {
      const sessionKeys = await this.redis.keys('session:*');
      const stats = {
        totalActiveSessions: sessionKeys.length,
        sessionsPerUser: {} as Record<string, number>,
        deviceTypes: {} as Record<string, number>,
      };

      for (const key of sessionKeys) {
        const sessionData = await this.redis.get(key);
        if (sessionData) {
          const session: Session = JSON.parse(sessionData);

          // Count sessions per user
          stats.sessionsPerUser[session.userId] =
            (stats.sessionsPerUser[session.userId] || 0) + 1;

          // Count device types
          const deviceType = session.deviceInfo.deviceType;
          stats.deviceTypes[deviceType] =
            (stats.deviceTypes[deviceType] || 0) + 1;
        }
      }

      return stats;
    } catch (error) {
      this.logger.error('Failed to get session stats', {
        error: error.message,
      });
      return {
        totalActiveSessions: 0,
        sessionsPerUser: {},
        deviceTypes: {},
      };
    }
  }

  /**
   * Enforce session limit per user
   */
  private async enforceSessionLimit(userId: string): Promise<void> {
    try {
      const sessions = await this.getUserSessions(userId);

      if (sessions.length >= authConfig.session.maxSessions) {
        // Remove oldest sessions
        const sessionsToRemove = sessions
          .sort(
            (a, b) => a.lastActivityAt.getTime() - b.lastActivityAt.getTime()
          )
          .slice(0, sessions.length - authConfig.session.maxSessions + 1);

        for (const session of sessionsToRemove) {
          await this.destroySession(session.id);
        }

        this.logger.info('Enforced session limit', {
          userId,
          removedSessions: sessionsToRemove.length,
        });
      }
    } catch (error) {
      this.logger.error('Failed to enforce session limit', {
        userId,
        error: error.message,
      });
    }
  }

  /**
   * Parse device information from user agent
   */
  private parseDeviceInfo(userAgent: string): DeviceInfo {
    const parser = new UAParser(userAgent);
    const result = parser.getResult();

    let deviceType: 'desktop' | 'mobile' | 'tablet' | 'unknown' = 'unknown';

    if (result.device.type === 'mobile') {
      deviceType = 'mobile';
    } else if (result.device.type === 'tablet') {
      deviceType = 'tablet';
    } else if (
      result.os.name &&
      ['Windows', 'Mac OS', 'Linux'].includes(result.os.name)
    ) {
      deviceType = 'desktop';
    }

    const deviceId = crypto
      .createHash('sha256')
      .update(userAgent + result.os.name + result.browser.name)
      .digest('hex');

    return {
      deviceId,
      deviceName:
        result.device.model || `${result.browser.name} on ${result.os.name}`,
      deviceType,
      os: result.os.name,
      browser: result.browser.name,
      isTrusted: false, // TODO: Implement device trust logic
    };
  }

  /**
   * Track device for user
   */
  private async trackDevice(
    userId: string,
    deviceInfo: DeviceInfo
  ): Promise<void> {
    try {
      const deviceKey = `user_device:${userId}:${deviceInfo.deviceId}`;
      const existingDevice = await this.redis.get(deviceKey);

      if (!existingDevice) {
        // New device detected
        await this.redis.setex(
          deviceKey,
          86400 * 30,
          JSON.stringify({
            ...deviceInfo,
            firstSeen: new Date(),
            lastSeen: new Date(),
            loginCount: 1,
          })
        );

        this.logger.info('New device detected', {
          userId,
          deviceId: deviceInfo.deviceId,
        });
      } else {
        // Update existing device
        const device = JSON.parse(existingDevice);
        device.lastSeen = new Date();
        device.loginCount = (device.loginCount || 0) + 1;

        await this.redis.setex(deviceKey, 86400 * 30, JSON.stringify(device));
      }
    } catch (error) {
      this.logger.error('Failed to track device', {
        userId,
        error: error.message,
      });
    }
  }
}
