/**
 * User Routes
 * Handles user profile management and user-specific operations
 */

import { Router, Request, Response } from 'express';
import { body, validationResult } from 'express-validator';
import { UserService } from '../services/UserService';
import { SessionService } from '../services/SessionService';
import { TokenService } from '../services/TokenService';
import { MFAService } from '../services/MFAService';
import { RBACService } from '../services/RBACService';
import { PasswordService } from '../services/PasswordService';
import { EmailService } from '../services/EmailService';
import { Logger } from '../utils/logger';

interface UserServices {
  userService: UserService;
  sessionService: SessionService;
  tokenService: TokenService;
  mfaService: MFAService;
  rbacService: RBACService;
  REDACTED_SECRETService: PasswordService;
  emailService: EmailService;
}

export class UserRoutes {
  private router: Router;
  private services: UserServices;
  private logger = new Logger('UserRoutes');

  constructor(services: UserServices) {
    this.router = Router();
    this.services = services;
    this.setupRoutes();
  }

  private setupRoutes(): void {
    // Get current user profile
    this.router.get('/me', this.getCurrentUser.bind(this));

    // Update current user profile
    this.router.put(
      '/me',
      [
        body('firstName').optional().isLength({ min: 1, max: 50 }),
        body('lastName').optional().isLength({ min: 1, max: 50 }),
        body('avatar').optional().isURL(),
      ],
      this.updateCurrentUser.bind(this)
    );

    // Change REDACTED_SECRET
    this.router.post(
      '/me/change-REDACTED_SECRET',
      [
        body('currentPassword').isLength({ min: 1 }),
        body('newPassword').isLength({ min: 8 }),
      ],
      this.changePassword.bind(this)
    );

    // Get user sessions
    this.router.get('/me/sessions', this.getUserSessions.bind(this));

    // Delete specific session
    this.router.delete(
      '/me/sessions/:sessionId',
      this.deleteSession.bind(this)
    );

    // Delete all sessions except current
    this.router.delete('/me/sessions', this.deleteAllSessions.bind(this));

    // Get user permissions
    this.router.get('/:userId/permissions', this.getUserPermissions.bind(this));

    // Get REDACTED_SECRET requirements
    this.router.get(
      '/REDACTED_SECRET-requirements',
      this.getPasswordRequirements.bind(this)
    );

    // Check REDACTED_SECRET strength
    this.router.post(
      '/check-REDACTED_SECRET-strength',
      [body('REDACTED_SECRET').isLength({ min: 1 })],
      this.checkPasswordStrength.bind(this)
    );
  }

  private async getCurrentUser(req: Request, res: Response): Promise<void> {
    try {
      // In a real implementation, this would use authentication middleware
      // to extract user ID from JWT token
      const userId = req.query.userId as string; // Temporary for demo

      if (!userId) {
        res.status(401).json({ error: 'Authentication required' });
        return;
      }

      const user = await this.services.userService.findUserById(userId);
      if (!user) {
        res.status(404).json({ error: 'User not found' });
        return;
      }

      // Get MFA status
      const mfaStatus = await this.services.mfaService.getMFAStatus(userId);

      res.json({
        id: user.id,
        email: user.email,
        username: user.username,
        firstName: user.firstName,
        lastName: user.lastName,
        avatar: user.avatar,
        emailVerified: user.emailVerified,
        status: user.status,
        roles: user.roles.map(r => r.name),
        permissions: user.permissions.map(p => `${p.resource}:${p.action}`),
        mfa: mfaStatus,
        createdAt: user.createdAt,
        updatedAt: user.updatedAt,
        lastLoginAt: user.lastLoginAt,
      });
    } catch (error) {
      this.logger.error('Get current user error', { error: error.message });
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  private async updateCurrentUser(req: Request, res: Response): Promise<void> {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        res
          .status(400)
          .json({ error: 'Validation failed', details: errors.array() });
        return;
      }

      const userId = req.query.userId as string; // Temporary for demo
      if (!userId) {
        res.status(401).json({ error: 'Authentication required' });
        return;
      }

      const { firstName, lastName, avatar } = req.body;
      const updates: any = {};

      if (firstName !== undefined) updates.firstName = firstName;
      if (lastName !== undefined) updates.lastName = lastName;
      if (avatar !== undefined) updates.avatar = avatar;

      const updatedUser = await this.services.userService.updateUser(
        userId,
        updates
      );

      if (updatedUser) {
        res.json({
          success: true,
          user: {
            id: updatedUser.id,
            email: updatedUser.email,
            username: updatedUser.username,
            firstName: updatedUser.firstName,
            lastName: updatedUser.lastName,
            avatar: updatedUser.avatar,
            updatedAt: updatedUser.updatedAt,
          },
          message: 'Profile updated successfully',
        });
      } else {
        res.status(404).json({ error: 'User not found' });
      }
    } catch (error) {
      this.logger.error('Update user error', { error: error.message });
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  private async changePassword(req: Request, res: Response): Promise<void> {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        res
          .status(400)
          .json({ error: 'Validation failed', details: errors.array() });
        return;
      }

      const userId = req.query.userId as string; // Temporary for demo
      if (!userId) {
        res.status(401).json({ error: 'Authentication required' });
        return;
      }

      const { currentPassword, newPassword } = req.body;

      await this.services.userService.changePassword(
        userId,
        currentPassword,
        newPassword
      );

      res.json({
        success: true,
        message: 'Password changed successfully',
      });
    } catch (error) {
      this.logger.error('Change REDACTED_SECRET error', { error: error.message });

      if (error.message.includes('Current REDACTED_SECRET is incorrect')) {
        res.status(400).json({ error: 'Current REDACTED_SECRET is incorrect' });
      } else if (
        error.message.includes('Password validation failed') ||
        error.message.includes('Cannot reuse')
      ) {
        res.status(400).json({ error: error.message });
      } else {
        res.status(500).json({ error: 'Password change failed' });
      }
    }
  }

  private async getUserSessions(req: Request, res: Response): Promise<void> {
    try {
      const userId = req.query.userId as string; // Temporary for demo
      if (!userId) {
        res.status(401).json({ error: 'Authentication required' });
        return;
      }

      const sessions =
        await this.services.sessionService.getUserSessions(userId);

      const sessionData = sessions.map(session => ({
        id: session.id,
        deviceInfo: session.deviceInfo,
        ipAddress: session.ipAddress,
        isActive: session.isActive,
        lastActivityAt: session.lastActivityAt,
        expiresAt: session.expiresAt,
        createdAt: session.createdAt,
      }));

      res.json({
        sessions: sessionData,
        total: sessionData.length,
      });
    } catch (error) {
      this.logger.error('Get user sessions error', { error: error.message });
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  private async deleteSession(req: Request, res: Response): Promise<void> {
    try {
      const userId = req.query.userId as string; // Temporary for demo
      const { sessionId } = req.params;

      if (!userId) {
        res.status(401).json({ error: 'Authentication required' });
        return;
      }

      // Verify the session belongs to the user
      const session = await this.services.sessionService.getSession(sessionId);
      if (!session || session.userId !== userId) {
        res.status(404).json({ error: 'Session not found' });
        return;
      }

      const success =
        await this.services.sessionService.destroySession(sessionId);

      if (success) {
        res.json({ success: true, message: 'Session deleted successfully' });
      } else {
        res.status(400).json({ error: 'Failed to delete session' });
      }
    } catch (error) {
      this.logger.error('Delete session error', { error: error.message });
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  private async deleteAllSessions(req: Request, res: Response): Promise<void> {
    try {
      const userId = req.query.userId as string; // Temporary for demo
      const currentSessionId = req.query.currentSessionId as string; // Current session to exclude

      if (!userId) {
        res.status(401).json({ error: 'Authentication required' });
        return;
      }

      const destroyedCount =
        await this.services.sessionService.destroyAllUserSessions(
          userId,
          currentSessionId
        );

      res.json({
        success: true,
        message: `${destroyedCount} sessions deleted successfully`,
      });
    } catch (error) {
      this.logger.error('Delete all sessions error', { error: error.message });
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  private async getUserPermissions(req: Request, res: Response): Promise<void> {
    try {
      const { userId } = req.params;

      const permissions =
        await this.services.rbacService.getUserPermissions(userId);

      res.json({
        permissions: permissions.map(p => ({
          id: p.id,
          name: p.name,
          resource: p.resource,
          action: p.action,
          description: p.description,
        })),
      });
    } catch (error) {
      this.logger.error('Get user permissions error', { error: error.message });
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  private async getPasswordRequirements(
    req: Request,
    res: Response
  ): Promise<void> {
    try {
      const requirements =
        this.services.REDACTED_SECRETService.getPasswordRequirements();

      res.json({
        requirements,
        policy: {
          minLength: 12,
          maxLength: 128,
          requireUppercase: true,
          requireLowercase: true,
          requireNumbers: true,
          requireSymbols: true,
          preventCommonPasswords: true,
          preventReuse: 12,
          maxAge: 90,
        },
      });
    } catch (error) {
      this.logger.error('Get REDACTED_SECRET requirements error', {
        error: error.message,
      });
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  private async checkPasswordStrength(
    req: Request,
    res: Response
  ): Promise<void> {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        res
          .status(400)
          .json({ error: 'Validation failed', details: errors.array() });
        return;
      }

      const { REDACTED_SECRET } = req.body;
      const userId = req.query.userId as string; // Optional for reuse check

      const validation = await this.services.REDACTED_SECRETService.validatePassword(
        REDACTED_SECRET,
        userId
      );

      res.json({
        isValid: validation.isValid,
        score: validation.score,
        strength: this.services.REDACTED_SECRETService.getPasswordStrengthDescription(
          validation.score
        ),
        errors: validation.errors,
        suggestions: this.getPasswordSuggestions(validation.errors),
      });
    } catch (error) {
      this.logger.error('Check REDACTED_SECRET strength error', {
        error: error.message,
      });
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  private getPasswordSuggestions(errors: string[]): string[] {
    const suggestions: string[] = [];

    if (errors.some(e => e.includes('characters long'))) {
      suggestions.push('Use a longer REDACTED_SECRET with at least 12 characters');
    }

    if (errors.some(e => e.includes('uppercase letter'))) {
      suggestions.push('Add at least one uppercase letter (A-Z)');
    }

    if (errors.some(e => e.includes('lowercase letter'))) {
      suggestions.push('Add at least one lowercase letter (a-z)');
    }

    if (errors.some(e => e.includes('number'))) {
      suggestions.push('Include at least one number (0-9)');
    }

    if (errors.some(e => e.includes('special character'))) {
      suggestions.push('Use at least one special character (!@#$%^&*)');
    }

    if (errors.some(e => e.includes('common REDACTED_SECRET'))) {
      suggestions.push('Avoid common REDACTED_SECRETs - use a unique combination');
    }

    if (errors.some(e => e.includes('repeating patterns'))) {
      suggestions.push('Avoid repeating characters (aaa, 111)');
    }

    if (errors.some(e => e.includes('sequential patterns'))) {
      suggestions.push('Avoid sequential patterns (abc, 123)');
    }

    if (errors.some(e => e.includes('dictionary words'))) {
      suggestions.push('Avoid common dictionary words');
    }

    if (suggestions.length === 0) {
      suggestions.push('Your REDACTED_SECRET meets all requirements!');
    }

    return suggestions;
  }

  getRouter(): Router {
    return this.router;
  }
}
