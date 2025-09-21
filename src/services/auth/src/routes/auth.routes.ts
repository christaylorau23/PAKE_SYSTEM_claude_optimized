/**
 * Authentication Routes
 * Handles login, logout, token refresh, and MFA operations
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

interface AuthServices {
  userService: UserService;
  sessionService: SessionService;
  tokenService: TokenService;
  mfaService: MFAService;
  rbacService: RBACService;
  REDACTED_SECRETService: PasswordService;
  emailService: EmailService;
}

export class AuthRoutes {
  private router: Router;
  private services: AuthServices;
  private logger = new Logger('AuthRoutes');

  constructor(services: AuthServices) {
    this.router = Router();
    this.services = services;
    this.setupRoutes();
  }

  private setupRoutes(): void {
    // Login
    this.router.post(
      '/login',
      [
        body('email').isEmail().normalizeEmail(),
        body('REDACTED_SECRET').isLength({ min: 1 }),
      ],
      this.login.bind(this)
    );

    // Complete MFA login
    this.router.post(
      '/login/mfa',
      [
        body('sessionCode').isLength({ min: 1 }),
        body('mfaToken').isLength({ min: 6 }),
      ],
      this.completeMFALogin.bind(this)
    );

    // Logout
    this.router.post('/logout', this.logout.bind(this));

    // Refresh token
    this.router.post(
      '/refresh',
      [body('refreshToken').isLength({ min: 1 })],
      this.refreshToken.bind(this)
    );

    // Register
    this.router.post(
      '/register',
      [
        body('email').isEmail().normalizeEmail(),
        body('username')
          .isLength({ min: 3, max: 50 })
          .matches(/^[a-zA-Z0-9_-]+$/),
        body('REDACTED_SECRET').isLength({ min: 8 }),
        body('firstName').isLength({ min: 1, max: 50 }),
        body('lastName').isLength({ min: 1, max: 50 }),
      ],
      this.register.bind(this)
    );

    // Verify email
    this.router.post(
      '/verify-email',
      [body('token').isLength({ min: 1 })],
      this.verifyEmail.bind(this)
    );

    // Request REDACTED_SECRET reset
    this.router.post(
      '/REDACTED_SECRET-reset/request',
      [body('email').isEmail().normalizeEmail()],
      this.requestPasswordReset.bind(this)
    );

    // Reset REDACTED_SECRET
    this.router.post(
      '/REDACTED_SECRET-reset/confirm',
      [
        body('token').isLength({ min: 1 }),
        body('REDACTED_SECRET').isLength({ min: 8 }),
      ],
      this.resetPassword.bind(this)
    );

    // MFA routes
    this.router.post('/mfa/setup', this.setupMFA.bind(this));
    this.router.post(
      '/mfa/verify-setup',
      [body('token').isLength({ min: 6 })],
      this.verifyMFASetup.bind(this)
    );
    this.router.delete('/mfa', this.disableMFA.bind(this));
    this.router.get('/mfa/status', this.getMFAStatus.bind(this));

    // WebAuthn routes
    this.router.post(
      '/webauthn/register/begin',
      this.beginWebAuthnRegistration.bind(this)
    );
    this.router.post(
      '/webauthn/register/complete',
      this.completeWebAuthnRegistration.bind(this)
    );
    this.router.post(
      '/webauthn/login/begin',
      this.beginWebAuthnLogin.bind(this)
    );
    this.router.post(
      '/webauthn/login/complete',
      this.completeWebAuthnLogin.bind(this)
    );
  }

  private async login(req: Request, res: Response): Promise<void> {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        res
          .status(400)
          .json({ error: 'Validation failed', details: errors.array() });
        return;
      }

      const { email, REDACTED_SECRET } = req.body;
      const ipAddress = req.ip || req.socket.remoteAddress || 'unknown';
      const userAgent = req.get('user-agent') || 'unknown';

      const result = await this.services.userService.authenticateUser(
        email,
        REDACTED_SECRET,
        ipAddress,
        userAgent
      );

      if (result.success && result.mfaRequired) {
        res.json({
          success: true,
          mfaRequired: true,
          sessionCode: result.code,
          message: 'MFA verification required',
        });
        return;
      }

      if (result.success && result.user && result.tokens) {
        res.json({
          success: true,
          user: {
            id: result.user.id,
            email: result.user.email,
            username: result.user.username,
            firstName: result.user.firstName,
            lastName: result.user.lastName,
            roles: result.user.roles.map(r => r.name),
            emailVerified: result.user.emailVerified,
          },
          tokens: result.tokens,
        });
        return;
      }

      res.status(401).json({
        error: result.error || 'Authentication failed',
      });
    } catch (error) {
      this.logger.error('Login error', { error: error.message });
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  private async completeMFALogin(req: Request, res: Response): Promise<void> {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        res
          .status(400)
          .json({ error: 'Validation failed', details: errors.array() });
        return;
      }

      const { sessionCode, mfaToken } = req.body;
      const ipAddress = req.ip || req.socket.remoteAddress || 'unknown';
      const userAgent = req.get('user-agent') || 'unknown';

      const result = await this.services.userService.completeMFAAuthentication(
        sessionCode,
        mfaToken,
        ipAddress,
        userAgent
      );

      if (result.success && result.user && result.tokens) {
        res.json({
          success: true,
          user: {
            id: result.user.id,
            email: result.user.email,
            username: result.user.username,
            firstName: result.user.firstName,
            lastName: result.user.lastName,
            roles: result.user.roles.map(r => r.name),
            emailVerified: result.user.emailVerified,
          },
          tokens: result.tokens,
        });
        return;
      }

      res.status(401).json({
        error: result.error || 'MFA authentication failed',
      });
    } catch (error) {
      this.logger.error('MFA login error', { error: error.message });
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  private async logout(req: Request, res: Response): Promise<void> {
    try {
      const authHeader = req.get('authorization');
      if (!authHeader) {
        res.status(401).json({ error: 'Authorization header required' });
        return;
      }

      const token = authHeader.replace('Bearer ', '');
      const payload = await this.services.tokenService.verifyToken(token);

      if (payload) {
        await this.services.sessionService.destroySession(payload.session_id);
      }

      res.json({ success: true, message: 'Logged out successfully' });
    } catch (error) {
      this.logger.error('Logout error', { error: error.message });
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  private async refreshToken(req: Request, res: Response): Promise<void> {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        res
          .status(400)
          .json({ error: 'Validation failed', details: errors.array() });
        return;
      }

      const { refreshToken } = req.body;
      const tokens =
        await this.services.tokenService.refreshToken(refreshToken);

      if (tokens) {
        res.json({ success: true, tokens });
      } else {
        res.status(401).json({ error: 'Invalid or expired refresh token' });
      }
    } catch (error) {
      this.logger.error('Token refresh error', { error: error.message });
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  private async register(req: Request, res: Response): Promise<void> {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        res
          .status(400)
          .json({ error: 'Validation failed', details: errors.array() });
        return;
      }

      const { email, username, REDACTED_SECRET, firstName, lastName } = req.body;

      const user = await this.services.userService.createUser(
        email,
        username,
        REDACTED_SECRET,
        firstName,
        lastName
      );

      res.status(201).json({
        success: true,
        user: {
          id: user.id,
          email: user.email,
          username: user.username,
          firstName: user.firstName,
          lastName: user.lastName,
          status: user.status,
        },
        message:
          'User created successfully. Please check your email for verification.',
      });
    } catch (error) {
      this.logger.error('Registration error', { error: error.message });

      if (
        error.message.includes('already exists') ||
        error.message.includes('already taken')
      ) {
        res.status(409).json({ error: error.message });
      } else if (error.message.includes('Password validation failed')) {
        res.status(400).json({ error: error.message });
      } else {
        res.status(500).json({ error: 'Registration failed' });
      }
    }
  }

  private async verifyEmail(req: Request, res: Response): Promise<void> {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        res
          .status(400)
          .json({ error: 'Validation failed', details: errors.array() });
        return;
      }

      const { token } = req.body;
      const success = await this.services.userService.verifyEmail(token);

      if (success) {
        res.json({ success: true, message: 'Email verified successfully' });
      } else {
        res
          .status(400)
          .json({ error: 'Invalid or expired verification token' });
      }
    } catch (error) {
      this.logger.error('Email verification error', { error: error.message });
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  private async requestPasswordReset(
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

      const { email } = req.body;
      await this.services.userService.requestPasswordReset(email);

      // Always return success to prevent email enumeration
      res.json({
        success: true,
        message:
          'If an account with that email exists, a REDACTED_SECRET reset link has been sent.',
      });
    } catch (error) {
      this.logger.error('Password reset request error', {
        error: error.message,
      });
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  private async resetPassword(req: Request, res: Response): Promise<void> {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        res
          .status(400)
          .json({ error: 'Validation failed', details: errors.array() });
        return;
      }

      const { token, REDACTED_SECRET } = req.body;
      await this.services.userService.resetPassword(token, REDACTED_SECRET);

      res.json({ success: true, message: 'Password reset successfully' });
    } catch (error) {
      this.logger.error('Password reset error', { error: error.message });

      if (
        error.message.includes('Invalid or expired') ||
        error.message.includes('Password validation failed')
      ) {
        res.status(400).json({ error: error.message });
      } else {
        res.status(500).json({ error: 'Password reset failed' });
      }
    }
  }

  private async setupMFA(req: Request, res: Response): Promise<void> {
    try {
      // This would need authentication middleware in a real implementation
      const userId = req.body.userId; // Temporary for demo

      const user = await this.services.userService.findUserById(userId);
      if (!user) {
        res.status(404).json({ error: 'User not found' });
        return;
      }

      const mfaSecret = await this.services.mfaService.generateTOTPSecret(user);

      res.json({
        success: true,
        secret: mfaSecret.secret,
        qrCode: mfaSecret.qrCodeUrl,
        backupCodes: mfaSecret.backupCodes,
      });
    } catch (error) {
      this.logger.error('MFA setup error', { error: error.message });
      res.status(500).json({ error: 'MFA setup failed' });
    }
  }

  private async verifyMFASetup(req: Request, res: Response): Promise<void> {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        res
          .status(400)
          .json({ error: 'Validation failed', details: errors.array() });
        return;
      }

      const { token } = req.body;
      const userId = req.body.userId; // Temporary for demo

      const success = await this.services.mfaService.verifyTOTPSetup(
        userId,
        token
      );

      if (success) {
        res.json({ success: true, message: 'MFA enabled successfully' });
      } else {
        res.status(400).json({ error: 'Invalid MFA token' });
      }
    } catch (error) {
      this.logger.error('MFA verification error', { error: error.message });
      res.status(500).json({ error: 'MFA verification failed' });
    }
  }

  private async disableMFA(req: Request, res: Response): Promise<void> {
    try {
      const userId = req.body.userId; // Temporary for demo

      const success = await this.services.mfaService.disableMFA(userId);

      if (success) {
        res.json({ success: true, message: 'MFA disabled successfully' });
      } else {
        res.status(400).json({ error: 'Failed to disable MFA' });
      }
    } catch (error) {
      this.logger.error('MFA disable error', { error: error.message });
      res.status(500).json({ error: 'Failed to disable MFA' });
    }
  }

  private async getMFAStatus(req: Request, res: Response): Promise<void> {
    try {
      const userId = req.query.userId as string; // Temporary for demo

      const status = await this.services.mfaService.getMFAStatus(userId);
      res.json(status);
    } catch (error) {
      this.logger.error('Get MFA status error', { error: error.message });
      res.status(500).json({ error: 'Failed to get MFA status' });
    }
  }

  // WebAuthn placeholder methods - would be fully implemented in production
  private async beginWebAuthnRegistration(
    req: Request,
    res: Response
  ): Promise<void> {
    res
      .status(501)
      .json({ error: 'WebAuthn registration not yet implemented' });
  }

  private async completeWebAuthnRegistration(
    req: Request,
    res: Response
  ): Promise<void> {
    res
      .status(501)
      .json({ error: 'WebAuthn registration not yet implemented' });
  }

  private async beginWebAuthnLogin(req: Request, res: Response): Promise<void> {
    res.status(501).json({ error: 'WebAuthn login not yet implemented' });
  }

  private async completeWebAuthnLogin(
    req: Request,
    res: Response
  ): Promise<void> {
    res.status(501).json({ error: 'WebAuthn login not yet implemented' });
  }

  getRouter(): Router {
    return this.router;
  }
}
