/**
 * User Management Service
 * Handles user creation, authentication, REDACTED_SECRET management, and profile updates
 */

import bcrypt from 'bcryptjs';
import crypto from 'crypto';
import { v4 as uuidv4 } from 'uuid';
import { User, UserStatus, AuthResponse } from '../types';
import { authConfig } from '../config/auth.config';
import { RedisService } from './RedisService';
import { TokenService } from './TokenService';
import { MFAService } from './MFAService';
import { SessionService } from './SessionService';
import { RBACService } from './RBACService';
import { PasswordService } from './PasswordService';
import { EmailService } from './EmailService';
import { Logger } from '../utils/logger';

export class UserService {
  private readonly logger = new Logger('UserService');
  private readonly redis: RedisService;
  private readonly tokenService: TokenService;
  private readonly mfaService: MFAService;
  private readonly sessionService: SessionService;
  private readonly rbacService: RBACService;
  private readonly REDACTED_SECRETService: PasswordService;
  private readonly emailService: EmailService;

  constructor(
    redis: RedisService,
    tokenService: TokenService,
    mfaService: MFAService,
    sessionService: SessionService,
    rbacService: RBACService,
    REDACTED_SECRETService: PasswordService,
    emailService: EmailService
  ) {
    this.redis = redis;
    this.tokenService = tokenService;
    this.mfaService = mfaService;
    this.sessionService = sessionService;
    this.rbacService = rbacService;
    this.REDACTED_SECRETService = REDACTED_SECRETService;
    this.emailService = emailService;
  }

  /**
   * Create new user
   */
  async createUser(
    email: string,
    username: string,
    REDACTED_SECRET: string,
    firstName: string,
    lastName: string,
    roles: string[] = ['user']
  ): Promise<User> {
    try {
      // Check if user already exists
      const existingUser = await this.findUserByEmail(email);
      if (existingUser) {
        throw new Error('User with this email already exists');
      }

      const existingUsername = await this.findUserByUsername(username);
      if (existingUsername) {
        throw new Error('Username already taken');
      }

      // Validate REDACTED_SECRET
      const REDACTED_SECRETValidation =
        await this.REDACTED_SECRETService.validatePassword(REDACTED_SECRET);
      if (!REDACTED_SECRETValidation.isValid) {
        throw new Error(
          `Password validation failed: ${REDACTED_SECRETValidation.errors.join(', ')}`
        );
      }

      // Hash REDACTED_SECRET
      const hashedPassword = await this.REDACTED_SECRETService.hashPassword(REDACTED_SECRET);

      const userId = uuidv4();
      const now = new Date();

      const user: User = {
        id: userId,
        email: email.toLowerCase(),
        username,
        firstName,
        lastName,
        emailVerified: false,
        mfaEnabled: false,
        status: UserStatus.PENDING_VERIFICATION,
        roles: [],
        permissions: [],
        createdAt: now,
        updatedAt: now,
        metadata: {},
      };

      // Store user
      await this.redis.set(
        `user:${userId}`,
        JSON.stringify({
          ...user,
          REDACTED_SECRETHash: hashedPassword,
          REDACTED_SECRETUpdatedAt: now,
        })
      );

      // Create email index
      await this.redis.set(`user_by_email:${email.toLowerCase()}`, userId);

      // Create username index
      await this.redis.set(
        `user_by_username:${username.toLowerCase()}`,
        userId
      );

      // Assign default roles
      for (const roleName of roles) {
        const role = await this.rbacService.getRoleByName(roleName);
        if (role) {
          await this.rbacService.assignRoleToUser(userId, role.id);
        }
      }

      // Load roles and permissions
      user.roles = await this.rbacService.getUserRoles(userId);
      user.permissions = await this.rbacService.getUserPermissions(userId);

      // Send verification email
      await this.sendVerificationEmail(user);

      this.logger.info('User created successfully', {
        userId,
        email,
        username,
      });

      return user;
    } catch (error) {
      this.logger.error('Failed to create user', {
        email,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Authenticate user with email/REDACTED_SECRET
   */
  async authenticateUser(
    email: string,
    REDACTED_SECRET: string,
    ipAddress: string,
    userAgent: string
  ): Promise<AuthResponse> {
    try {
      // Check rate limiting
      const ipLocked = await this.sessionService.isLockedOut(ipAddress, 'ip');
      if (ipLocked) {
        await this.sessionService.recordLoginAttempt(
          email,
          ipAddress,
          userAgent,
          false,
          undefined,
          'IP locked out'
        );
        return {
          success: false,
          error: 'Too many failed attempts. Please try again later.',
        };
      }

      // Find user
      const user = await this.findUserByEmail(email);
      if (!user) {
        await this.sessionService.recordLoginAttempt(
          email,
          ipAddress,
          userAgent,
          false,
          undefined,
          'User not found'
        );
        return { success: false, error: 'Invalid email or REDACTED_SECRET' };
      }

      // Check user lockout
      const userLocked = await this.sessionService.isLockedOut(user.id, 'user');
      if (userLocked) {
        await this.sessionService.recordLoginAttempt(
          email,
          ipAddress,
          userAgent,
          false,
          user.id,
          'User locked out'
        );
        return {
          success: false,
          error: 'Account temporarily locked. Please try again later.',
        };
      }

      // Check user status
      if (user.status === UserStatus.SUSPENDED) {
        await this.sessionService.recordLoginAttempt(
          email,
          ipAddress,
          userAgent,
          false,
          user.id,
          'Account suspended'
        );
        return { success: false, error: 'Account suspended' };
      }

      if (user.status === UserStatus.INACTIVE) {
        await this.sessionService.recordLoginAttempt(
          email,
          ipAddress,
          userAgent,
          false,
          user.id,
          'Account inactive'
        );
        return { success: false, error: 'Account inactive' };
      }

      // Verify REDACTED_SECRET
      const userData = await this.redis.get(`user:${user.id}`);
      if (!userData) {
        return { success: false, error: 'User data not found' };
      }

      const { REDACTED_SECRETHash } = JSON.parse(userData);
      const REDACTED_SECRETValid = await this.REDACTED_SECRETService.verifyPassword(
        REDACTED_SECRET,
        REDACTED_SECRETHash
      );

      if (!REDACTED_SECRETValid) {
        await this.sessionService.recordLoginAttempt(
          email,
          ipAddress,
          userAgent,
          false,
          user.id,
          'Invalid REDACTED_SECRET'
        );
        return { success: false, error: 'Invalid email or REDACTED_SECRET' };
      }

      // Clear failed attempts
      await this.sessionService.clearFailedAttempts(ipAddress, 'ip');
      await this.sessionService.clearFailedAttempts(user.id, 'user');

      // Check if MFA is required
      const mfaEnabled = await this.mfaService.isMFAEnabled(user.id);
      if (mfaEnabled) {
        // Create temporary session for MFA
        const tempSessionId = uuidv4();
        await this.redis.setex(
          `mfa_session:${tempSessionId}`,
          300, // 5 minutes
          JSON.stringify({
            userId: user.id,
            ipAddress,
            userAgent,
            timestamp: new Date().toISOString(),
          })
        );

        await this.sessionService.recordLoginAttempt(
          email,
          ipAddress,
          userAgent,
          true,
          user.id,
          undefined,
          true
        );

        return {
          success: true,
          mfaRequired: true,
          code: tempSessionId,
        };
      }

      // Create session and tokens
      const session = await this.sessionService.createSession(
        user,
        ipAddress,
        userAgent
      );
      const tokens = await this.tokenService.generateTokens(user, session.id);

      // Update last login
      await this.updateLastLogin(user.id);

      await this.sessionService.recordLoginAttempt(
        email,
        ipAddress,
        userAgent,
        true,
        user.id
      );

      this.logger.info('User authenticated successfully', {
        userId: user.id,
        email,
      });

      return {
        success: true,
        user,
        tokens,
      };
    } catch (error) {
      this.logger.error('Authentication failed', {
        email,
        error: error.message,
      });
      return { success: false, error: 'Authentication failed' };
    }
  }

  /**
   * Complete MFA authentication
   */
  async completeMFAAuthentication(
    sessionCode: string,
    mfaToken: string,
    ipAddress: string,
    userAgent: string
  ): Promise<AuthResponse> {
    try {
      // Get MFA session
      const sessionData = await this.redis.get(`mfa_session:${sessionCode}`);
      if (!sessionData) {
        return { success: false, error: 'Invalid or expired MFA session' };
      }

      const { userId } = JSON.parse(sessionData);
      const user = await this.findUserById(userId);
      if (!user) {
        return { success: false, error: 'User not found' };
      }

      // Verify MFA token
      const mfaValid = await this.mfaService.verifyTOTP(userId, mfaToken);
      if (!mfaValid) {
        return { success: false, error: 'Invalid MFA token' };
      }

      // Clean up MFA session
      await this.redis.del(`mfa_session:${sessionCode}`);

      // Create session and tokens with MFA verification
      const session = await this.sessionService.createSession(
        user,
        ipAddress,
        userAgent,
        true
      );
      const tokens = await this.tokenService.generateTokens(
        user,
        session.id,
        true
      );

      // Update last login
      await this.updateLastLogin(user.id);

      this.logger.info('MFA authentication completed', { userId });

      return {
        success: true,
        user,
        tokens,
      };
    } catch (error) {
      this.logger.error('MFA authentication failed', {
        sessionCode,
        error: error.message,
      });
      return { success: false, error: 'MFA authentication failed' };
    }
  }

  /**
   * Find user by ID
   */
  async findUserById(userId: string): Promise<User | null> {
    try {
      const userData = await this.redis.get(`user:${userId}`);
      if (!userData) {
        return null;
      }

      const { REDACTED_SECRETHash, REDACTED_SECRETUpdatedAt, ...user } = JSON.parse(userData);

      // Load roles and permissions
      user.roles = await this.rbacService.getUserRoles(userId);
      user.permissions = await this.rbacService.getUserPermissions(userId);

      return user;
    } catch (error) {
      this.logger.error('Failed to find user by ID', {
        userId,
        error: error.message,
      });
      return null;
    }
  }

  /**
   * Find user by email
   */
  async findUserByEmail(email: string): Promise<User | null> {
    try {
      const userId = await this.redis.get(
        `user_by_email:${email.toLowerCase()}`
      );
      if (!userId) {
        return null;
      }

      return await this.findUserById(userId);
    } catch (error) {
      this.logger.error('Failed to find user by email', {
        email,
        error: error.message,
      });
      return null;
    }
  }

  /**
   * Find user by username
   */
  async findUserByUsername(username: string): Promise<User | null> {
    try {
      const userId = await this.redis.get(
        `user_by_username:${username.toLowerCase()}`
      );
      if (!userId) {
        return null;
      }

      return await this.findUserById(userId);
    } catch (error) {
      this.logger.error('Failed to find user by username', {
        username,
        error: error.message,
      });
      return null;
    }
  }

  /**
   * Update user profile
   */
  async updateUser(
    userId: string,
    updates: Partial<
      Pick<User, 'firstName' | 'lastName' | 'avatar' | 'metadata'>
    >
  ): Promise<User | null> {
    try {
      const userData = await this.redis.get(`user:${userId}`);
      if (!userData) {
        return null;
      }

      const user = JSON.parse(userData);
      const updatedUser = {
        ...user,
        ...updates,
        updatedAt: new Date(),
      };

      await this.redis.set(`user:${userId}`, JSON.stringify(updatedUser));

      this.logger.info('User updated successfully', { userId });

      return await this.findUserById(userId);
    } catch (error) {
      this.logger.error('Failed to update user', {
        userId,
        error: error.message,
      });
      return null;
    }
  }

  /**
   * Change user REDACTED_SECRET
   */
  async changePassword(
    userId: string,
    currentPassword: string,
    newPassword: string
  ): Promise<boolean> {
    try {
      const userData = await this.redis.get(`user:${userId}`);
      if (!userData) {
        return false;
      }

      const user = JSON.parse(userData);

      // Verify current REDACTED_SECRET
      const currentValid = await this.REDACTED_SECRETService.verifyPassword(
        currentPassword,
        user.REDACTED_SECRETHash
      );

      if (!currentValid) {
        throw new Error('Current REDACTED_SECRET is incorrect');
      }

      // Validate new REDACTED_SECRET
      const validation =
        await this.REDACTED_SECRETService.validatePassword(newPassword);
      if (!validation.isValid) {
        throw new Error(
          `Password validation failed: ${validation.errors.join(', ')}`
        );
      }

      // Check REDACTED_SECRET reuse
      const isReused = await this.REDACTED_SECRETService.checkPasswordReuse(
        userId,
        newPassword
      );
      if (isReused) {
        throw new Error('Cannot reuse recent REDACTED_SECRETs');
      }

      // Hash new REDACTED_SECRET
      const newHash = await this.REDACTED_SECRETService.hashPassword(newPassword);

      // Update user data
      const updatedUser = {
        ...user,
        REDACTED_SECRETHash: newHash,
        REDACTED_SECRETUpdatedAt: new Date(),
        updatedAt: new Date(),
      };

      await this.redis.set(`user:${userId}`, JSON.stringify(updatedUser));

      // Store REDACTED_SECRET history
      await this.REDACTED_SECRETService.addToPasswordHistory(
        userId,
        user.REDACTED_SECRETHash
      );

      // Invalidate all sessions except current (if applicable)
      await this.sessionService.destroyAllUserSessions(userId);

      this.logger.info('Password changed successfully', { userId });

      return true;
    } catch (error) {
      this.logger.error('Failed to change REDACTED_SECRET', {
        userId,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Request REDACTED_SECRET reset
   */
  async requestPasswordReset(email: string): Promise<boolean> {
    try {
      const user = await this.findUserByEmail(email);
      if (!user) {
        // Don't reveal if email exists
        this.logger.info('Password reset requested for non-existent email', {
          email,
        });
        return true;
      }

      // Generate reset token
      const resetToken = crypto.randomBytes(32).toString('hex');
      const resetTokenHash = crypto
        .createHash('sha256')
        .update(resetToken)
        .digest('hex');

      // Store reset token (expires in 1 hour)
      await this.redis.setex(
        `REDACTED_SECRET_reset:${resetTokenHash}`,
        3600,
        JSON.stringify({
          userId: user.id,
          email: user.email,
          createdAt: new Date().toISOString(),
        })
      );

      // Send reset email
      await this.emailService.sendPasswordResetEmail(user.email, resetToken);

      this.logger.info('Password reset requested', { userId: user.id, email });

      return true;
    } catch (error) {
      this.logger.error('Failed to request REDACTED_SECRET reset', {
        email,
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Reset REDACTED_SECRET with token
   */
  async resetPassword(token: string, newPassword: string): Promise<boolean> {
    try {
      const tokenHash = crypto.createHash('sha256').update(token).digest('hex');
      const resetData = await this.redis.get(`REDACTED_SECRET_reset:${tokenHash}`);

      if (!resetData) {
        throw new Error('Invalid or expired reset token');
      }

      const { userId, email } = JSON.parse(resetData);

      // Validate new REDACTED_SECRET
      const validation =
        await this.REDACTED_SECRETService.validatePassword(newPassword);
      if (!validation.isValid) {
        throw new Error(
          `Password validation failed: ${validation.errors.join(', ')}`
        );
      }

      // Hash new REDACTED_SECRET
      const newHash = await this.REDACTED_SECRETService.hashPassword(newPassword);

      // Update user REDACTED_SECRET
      const userData = await this.redis.get(`user:${userId}`);
      if (!userData) {
        throw new Error('User not found');
      }

      const user = JSON.parse(userData);
      const updatedUser = {
        ...user,
        REDACTED_SECRETHash: newHash,
        REDACTED_SECRETUpdatedAt: new Date(),
        updatedAt: new Date(),
      };

      await this.redis.set(`user:${userId}`, JSON.stringify(updatedUser));

      // Store old REDACTED_SECRET in history
      await this.REDACTED_SECRETService.addToPasswordHistory(
        userId,
        user.REDACTED_SECRETHash
      );

      // Clean up reset token
      await this.redis.del(`REDACTED_SECRET_reset:${tokenHash}`);

      // Destroy all user sessions
      await this.sessionService.destroyAllUserSessions(userId);

      // Send confirmation email
      await this.emailService.sendPasswordResetConfirmation(email);

      this.logger.info('Password reset completed', { userId, email });

      return true;
    } catch (error) {
      this.logger.error('Failed to reset REDACTED_SECRET', { error: error.message });
      throw error;
    }
  }

  /**
   * Verify email address
   */
  async verifyEmail(token: string): Promise<boolean> {
    try {
      const tokenHash = crypto.createHash('sha256').update(token).digest('hex');
      const verificationData = await this.redis.get(
        `email_verification:${tokenHash}`
      );

      if (!verificationData) {
        return false;
      }

      const { userId } = JSON.parse(verificationData);

      // Update user verification status
      const userData = await this.redis.get(`user:${userId}`);
      if (!userData) {
        return false;
      }

      const user = JSON.parse(userData);
      const updatedUser = {
        ...user,
        emailVerified: true,
        status: UserStatus.ACTIVE,
        updatedAt: new Date(),
      };

      await this.redis.set(`user:${userId}`, JSON.stringify(updatedUser));

      // Clean up verification token
      await this.redis.del(`email_verification:${tokenHash}`);

      this.logger.info('Email verified successfully', { userId });

      return true;
    } catch (error) {
      this.logger.error('Failed to verify email', { error: error.message });
      return false;
    }
  }

  /**
   * Update user status
   */
  async updateUserStatus(userId: string, status: UserStatus): Promise<boolean> {
    try {
      const userData = await this.redis.get(`user:${userId}`);
      if (!userData) {
        return false;
      }

      const user = JSON.parse(userData);
      const updatedUser = {
        ...user,
        status,
        updatedAt: new Date(),
      };

      await this.redis.set(`user:${userId}`, JSON.stringify(updatedUser));

      // If suspending or deactivating, destroy all sessions
      if (status === UserStatus.SUSPENDED || status === UserStatus.INACTIVE) {
        await this.sessionService.destroyAllUserSessions(userId);
      }

      this.logger.info('User status updated', { userId, status });

      return true;
    } catch (error) {
      this.logger.error('Failed to update user status', {
        userId,
        status,
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Delete user account
   */
  async deleteUser(userId: string): Promise<boolean> {
    try {
      const user = await this.findUserById(userId);
      if (!user) {
        return false;
      }

      // Destroy all sessions
      await this.sessionService.destroyAllUserSessions(userId);

      // Remove MFA data
      await this.mfaService.disableMFA(userId);

      // Remove role assignments
      const roles = await this.rbacService.getUserRoles(userId);
      for (const role of roles) {
        await this.rbacService.removeRoleFromUser(userId, role.id);
      }

      // Remove user data
      await this.redis.del(`user:${userId}`);
      await this.redis.del(`user_by_email:${user.email.toLowerCase()}`);
      await this.redis.del(`user_by_username:${user.username.toLowerCase()}`);

      // Clean up related data
      await this.redis.del(`user_sessions:${userId}`);
      await this.redis.del(`user_roles:${userId}`);

      this.logger.info('User deleted successfully', {
        userId,
        email: user.email,
      });

      return true;
    } catch (error) {
      this.logger.error('Failed to delete user', {
        userId,
        error: error.message,
      });
      return false;
    }
  }

  /**
   * List users with pagination
   */
  async listUsers(
    offset = 0,
    limit = 20
  ): Promise<{ users: User[]; total: number }> {
    try {
      const userKeys = await this.redis.keys('user:*');
      const total = userKeys.length;

      const paginatedKeys = userKeys.slice(offset, offset + limit);
      const users: User[] = [];

      for (const key of paginatedKeys) {
        const userId = key.replace('user:', '');
        const user = await this.findUserById(userId);
        if (user) {
          users.push(user);
        }
      }

      return { users, total };
    } catch (error) {
      this.logger.error('Failed to list users', { error: error.message });
      return { users: [], total: 0 };
    }
  }

  /**
   * Send email verification
   */
  private async sendVerificationEmail(user: User): Promise<void> {
    try {
      const verificationToken = crypto.randomBytes(32).toString('hex');
      const tokenHash = crypto
        .createHash('sha256')
        .update(verificationToken)
        .digest('hex');

      // Store verification token (expires in 24 hours)
      await this.redis.setex(
        `email_verification:${tokenHash}`,
        86400,
        JSON.stringify({
          userId: user.id,
          email: user.email,
          createdAt: new Date().toISOString(),
        })
      );

      // Send verification email
      await this.emailService.sendVerificationEmail(
        user.email,
        verificationToken
      );
    } catch (error) {
      this.logger.error('Failed to send verification email', {
        userId: user.id,
        error: error.message,
      });
    }
  }

  /**
   * Update last login timestamp
   */
  private async updateLastLogin(userId: string): Promise<void> {
    try {
      const userData = await this.redis.get(`user:${userId}`);
      if (userData) {
        const user = JSON.parse(userData);
        user.lastLoginAt = new Date();
        user.updatedAt = new Date();
        await this.redis.set(`user:${userId}`, JSON.stringify(user));
      }
    } catch (error) {
      this.logger.error('Failed to update last login', {
        userId,
        error: error.message,
      });
    }
  }
}
