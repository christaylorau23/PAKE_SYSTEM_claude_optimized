/**
 * Multi-Factor Authentication Service
 * Handles TOTP (Time-based One-Time Password) and WebAuthn authentication
 */

import speakeasy from 'speakeasy';
import QRCode from 'qrcode';
import {
  generateRegistrationOptions,
  verifyRegistrationResponse,
  generateAuthenticationOptions,
  verifyAuthenticationResponse,
  RegistrationResponseJSON,
  AuthenticationResponseJSON,
} from '@simplewebauthn/server';
import { v4 as uuidv4 } from 'uuid';
import crypto from 'crypto';

import { MFASecret, WebAuthnCredential, User } from '../types';
import { authConfig, webAuthnConfig } from '../config/auth.config';
import { RedisService } from './RedisService';
import { Logger } from '../utils/logger';

export class MFAService {
  private readonly logger = new Logger('MFAService');
  private readonly redis: RedisService;

  constructor(redis: RedisService) {
    this.redis = redis;
  }

  /**
   * Generate TOTP secret and QR code for user
   */
  async generateTOTPSecret(user: User): Promise<MFASecret> {
    const secret = speakeasy.generateSecret({
      name: user.email,
      issuer: authConfig.mfa.issuer,
      length: 32,
    });

    // Generate backup codes
    const backupCodes = this.generateBackupCodes(10);

    // Generate QR code
    const qrCodeUrl = await QRCode.toDataURL(secret.otpauth_url!);

    const mfaSecret: MFASecret = {
      userId: user.id,
      secret: secret.base32!,
      backupCodes,
      qrCodeUrl,
      isVerified: false,
      createdAt: new Date(),
    };

    // Store temporarily in Redis for verification
    await this.redis.setex(
      `mfa_setup:${user.id}`,
      300, // 5 minutes
      JSON.stringify(mfaSecret)
    );

    this.logger.info('TOTP secret generated for user', { userId: user.id });

    return mfaSecret;
  }

  /**
   * Verify TOTP token and complete MFA setup
   */
  async verifyTOTPSetup(userId: string, token: string): Promise<boolean> {
    try {
      const mfaData = await this.redis.get(`mfa_setup:${userId}`);
      if (!mfaData) {
        this.logger.warn('MFA setup data not found', { userId });
        return false;
      }

      const mfaSecret: MFASecret = JSON.parse(mfaData);

      const verified = speakeasy.totp.verify({
        secret: mfaSecret.secret,
        encoding: 'base32',
        token,
        window: authConfig.mfa.windowSize,
      });

      if (verified) {
        // Mark as verified and store permanently
        mfaSecret.isVerified = true;

        // Store in persistent storage (in production, this would be a database)
        await this.redis.set(`mfa_secret:${userId}`, JSON.stringify(mfaSecret));

        // Clean up temporary setup data
        await this.redis.del(`mfa_setup:${userId}`);

        this.logger.info('TOTP setup completed successfully', { userId });
        return true;
      }

      this.logger.warn('TOTP verification failed during setup', { userId });
      return false;
    } catch (error) {
      this.logger.error('TOTP setup verification error', {
        userId,
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Verify TOTP token for authentication
   */
  async verifyTOTP(userId: string, token: string): Promise<boolean> {
    try {
      // Check if it's a backup code first
      if (await this.verifyBackupCode(userId, token)) {
        return true;
      }

      const mfaData = await this.redis.get(`mfa_secret:${userId}`);
      if (!mfaData) {
        this.logger.warn('MFA secret not found for user', { userId });
        return false;
      }

      const mfaSecret: MFASecret = JSON.parse(mfaData);

      if (!mfaSecret.isVerified) {
        this.logger.warn('MFA not yet verified for user', { userId });
        return false;
      }

      const verified = speakeasy.totp.verify({
        secret: mfaSecret.secret,
        encoding: 'base32',
        token,
        window: authConfig.mfa.windowSize,
      });

      if (verified) {
        this.logger.info('TOTP verification successful', { userId });
      } else {
        this.logger.warn('TOTP verification failed', { userId });
      }

      return verified;
    } catch (error) {
      this.logger.error('TOTP verification error', {
        userId,
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Verify backup code
   */
  async verifyBackupCode(userId: string, code: string): Promise<boolean> {
    try {
      const mfaData = await this.redis.get(`mfa_secret:${userId}`);
      if (!mfaData) {
        return false;
      }

      const mfaSecret: MFASecret = JSON.parse(mfaData);
      const codeIndex = mfaSecret.backupCodes.indexOf(code);

      if (codeIndex !== -1) {
        // Remove the used backup code
        mfaSecret.backupCodes.splice(codeIndex, 1);

        // Update stored data
        await this.redis.set(`mfa_secret:${userId}`, JSON.stringify(mfaSecret));

        this.logger.info('Backup code used successfully', {
          userId,
          remainingCodes: mfaSecret.backupCodes.length,
        });
        return true;
      }

      return false;
    } catch (error) {
      this.logger.error('Backup code verification error', {
        userId,
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Disable MFA for user
   */
  async disableMFA(userId: string): Promise<boolean> {
    try {
      // Remove TOTP secret
      await this.redis.del(`mfa_secret:${userId}`);

      // Remove all WebAuthn credentials
      const credentialKeys = await this.redis.keys(
        `webauthn_credential:${userId}:*`
      );
      if (credentialKeys.length > 0) {
        await this.redis.del(...credentialKeys);
      }

      this.logger.info('MFA disabled for user', { userId });
      return true;
    } catch (error) {
      this.logger.error('Failed to disable MFA', {
        userId,
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Generate WebAuthn registration options
   */
  async generateWebAuthnRegistration(user: User): Promise<any> {
    try {
      // Get existing credentials for this user
      const existingCredentials = await this.getWebAuthnCredentials(user.id);

      const options = await generateRegistrationOptions({
        rpName: webAuthnConfig.rpName,
        rpID: webAuthnConfig.rpID,
        userID: Buffer.from(user.id),
        userName: user.email,
        userDisplayName: `${user.firstName} ${user.lastName}`,
        timeout: webAuthnConfig.timeout,
        attestationType: webAuthnConfig.attestation,
        excludeCredentials: existingCredentials.map(cred => ({
          id: Buffer.from(cred.credentialId, 'base64'),
          type: 'public-key' as const,
          transports: ['usb', 'ble', 'nfc', 'internal'] as const,
        })),
        authenticatorSelection: {
          residentKey: 'discouraged',
          userVerification: webAuthnConfig.userVerification,
        },
        supportedAlgorithmIDs: [-7, -257],
      });

      // Store challenge temporarily
      await this.redis.setex(
        `webauthn_challenge:${user.id}`,
        300, // 5 minutes
        JSON.stringify({
          challenge: options.challenge,
          userId: user.id,
        })
      );

      this.logger.info('WebAuthn registration options generated', {
        userId: user.id,
      });

      return options;
    } catch (error) {
      this.logger.error('WebAuthn registration options generation failed', {
        userId: user.id,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Verify WebAuthn registration response
   */
  async verifyWebAuthnRegistration(
    userId: string,
    response: RegistrationResponseJSON,
    deviceName?: string
  ): Promise<WebAuthnCredential | null> {
    try {
      const challengeData = await this.redis.get(
        `webauthn_challenge:${userId}`
      );
      if (!challengeData) {
        this.logger.warn('WebAuthn challenge not found', { userId });
        return null;
      }

      const { challenge } = JSON.parse(challengeData);

      const verification = await verifyRegistrationResponse({
        response,
        expectedChallenge: challenge,
        expectedOrigin: webAuthnConfig.origin,
        expectedRPID: webAuthnConfig.rpID,
      });

      if (!verification.verified || !verification.registrationInfo) {
        this.logger.warn('WebAuthn registration verification failed', {
          userId,
        });
        return null;
      }

      const {
        credentialID,
        credentialPublicKey,
        counter,
        credentialBackedUp,
        credentialDeviceType,
      } = verification.registrationInfo;

      const credential: WebAuthnCredential = {
        id: uuidv4(),
        userId,
        credentialId: Buffer.from(credentialID).toString('base64'),
        publicKey: Buffer.from(credentialPublicKey).toString('base64'),
        counter,
        deviceName: deviceName || 'Unknown Device',
        isBackupEligible: credentialBackedUp,
        isBackedUp: credentialBackedUp,
        createdAt: new Date(),
      };

      // Store credential
      await this.redis.set(
        `webauthn_credential:${userId}:${credential.id}`,
        JSON.stringify(credential)
      );

      // Clean up challenge
      await this.redis.del(`webauthn_challenge:${userId}`);

      this.logger.info('WebAuthn credential registered successfully', {
        userId,
        credentialId: credential.id,
      });

      return credential;
    } catch (error) {
      this.logger.error('WebAuthn registration verification failed', {
        userId,
        error: error.message,
      });
      return null;
    }
  }

  /**
   * Generate WebAuthn authentication options
   */
  async generateWebAuthnAuthentication(userId: string): Promise<any> {
    try {
      const credentials = await this.getWebAuthnCredentials(userId);

      if (credentials.length === 0) {
        throw new Error('No WebAuthn credentials found for user');
      }

      const options = await generateAuthenticationOptions({
        rpID: webAuthnConfig.rpID,
        timeout: webAuthnConfig.timeout,
        allowCredentials: credentials.map(cred => ({
          id: Buffer.from(cred.credentialId, 'base64'),
          type: 'public-key' as const,
          transports: ['usb', 'ble', 'nfc', 'internal'] as const,
        })),
        userVerification: webAuthnConfig.userVerification,
      });

      // Store challenge temporarily
      await this.redis.setex(
        `webauthn_auth_challenge:${userId}`,
        300, // 5 minutes
        JSON.stringify({
          challenge: options.challenge,
          userId,
        })
      );

      this.logger.info('WebAuthn authentication options generated', { userId });

      return options;
    } catch (error) {
      this.logger.error('WebAuthn authentication options generation failed', {
        userId,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Verify WebAuthn authentication response
   */
  async verifyWebAuthnAuthentication(
    userId: string,
    response: AuthenticationResponseJSON
  ): Promise<boolean> {
    try {
      const challengeData = await this.redis.get(
        `webauthn_auth_challenge:${userId}`
      );
      if (!challengeData) {
        this.logger.warn('WebAuthn authentication challenge not found', {
          userId,
        });
        return false;
      }

      const { challenge } = JSON.parse(challengeData);

      // Find the credential being used
      const credentialId = Buffer.from(response.id, 'base64url').toString(
        'base64'
      );
      const credentials = await this.getWebAuthnCredentials(userId);
      const credential = credentials.find(c => c.credentialId === credentialId);

      if (!credential) {
        this.logger.warn('WebAuthn credential not found', {
          userId,
          credentialId,
        });
        return false;
      }

      const verification = await verifyAuthenticationResponse({
        response,
        expectedChallenge: challenge,
        expectedOrigin: webAuthnConfig.origin,
        expectedRPID: webAuthnConfig.rpID,
        authenticator: {
          credentialID: Buffer.from(credential.credentialId, 'base64'),
          credentialPublicKey: Buffer.from(credential.publicKey, 'base64'),
          counter: credential.counter,
        },
      });

      if (verification.verified) {
        // Update counter
        credential.counter = verification.authenticationInfo.newCounter;
        credential.lastUsedAt = new Date();

        await this.redis.set(
          `webauthn_credential:${userId}:${credential.id}`,
          JSON.stringify(credential)
        );

        // Clean up challenge
        await this.redis.del(`webauthn_auth_challenge:${userId}`);

        this.logger.info('WebAuthn authentication successful', {
          userId,
          credentialId: credential.id,
        });
        return true;
      }

      this.logger.warn('WebAuthn authentication verification failed', {
        userId,
      });
      return false;
    } catch (error) {
      this.logger.error('WebAuthn authentication verification failed', {
        userId,
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Get all WebAuthn credentials for a user
   */
  async getWebAuthnCredentials(userId: string): Promise<WebAuthnCredential[]> {
    try {
      const keys = await this.redis.keys(`webauthn_credential:${userId}:*`);
      const credentials: WebAuthnCredential[] = [];

      for (const key of keys) {
        const credentialData = await this.redis.get(key);
        if (credentialData) {
          credentials.push(JSON.parse(credentialData));
        }
      }

      return credentials;
    } catch (error) {
      this.logger.error('Failed to get WebAuthn credentials', {
        userId,
        error: error.message,
      });
      return [];
    }
  }

  /**
   * Remove WebAuthn credential
   */
  async removeWebAuthnCredential(
    userId: string,
    credentialId: string
  ): Promise<boolean> {
    try {
      const deleted = await this.redis.del(
        `webauthn_credential:${userId}:${credentialId}`
      );

      if (deleted > 0) {
        this.logger.info('WebAuthn credential removed', {
          userId,
          credentialId,
        });
      }

      return deleted > 0;
    } catch (error) {
      this.logger.error('Failed to remove WebAuthn credential', {
        userId,
        credentialId,
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Check if user has MFA enabled
   */
  async isMFAEnabled(userId: string): Promise<boolean> {
    try {
      const hasTOTP = await this.redis.exists(`mfa_secret:${userId}`);
      const webAuthnCredentials = await this.getWebAuthnCredentials(userId);

      return hasTOTP > 0 || webAuthnCredentials.length > 0;
    } catch (error) {
      this.logger.error('Failed to check MFA status', {
        userId,
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Get MFA status for user
   */
  async getMFAStatus(userId: string): Promise<{
    enabled: boolean;
    methods: string[];
    backupCodesRemaining?: number;
    webAuthnCredentials?: number;
  }> {
    try {
      const methods: string[] = [];
      let backupCodesRemaining: number | undefined;

      // Check TOTP
      const mfaData = await this.redis.get(`mfa_secret:${userId}`);
      if (mfaData) {
        const mfaSecret: MFASecret = JSON.parse(mfaData);
        if (mfaSecret.isVerified) {
          methods.push('totp');
          backupCodesRemaining = mfaSecret.backupCodes.length;
        }
      }

      // Check WebAuthn
      const webAuthnCredentials = await this.getWebAuthnCredentials(userId);
      if (webAuthnCredentials.length > 0) {
        methods.push('webauthn');
      }

      return {
        enabled: methods.length > 0,
        methods,
        backupCodesRemaining,
        webAuthnCredentials: webAuthnCredentials.length,
      };
    } catch (error) {
      this.logger.error('Failed to get MFA status', {
        userId,
        error: error.message,
      });
      return { enabled: false, methods: [] };
    }
  }

  /**
   * Generate backup codes
   */
  private generateBackupCodes(count: number): string[] {
    const codes: string[] = [];

    for (let i = 0; i < count; i++) {
      // Generate 8-character alphanumeric code
      const code = crypto.randomBytes(4).toString('hex').toUpperCase();
      codes.push(code);
    }

    return codes;
  }

  /**
   * Regenerate backup codes
   */
  async regenerateBackupCodes(userId: string): Promise<string[] | null> {
    try {
      const mfaData = await this.redis.get(`mfa_secret:${userId}`);
      if (!mfaData) {
        return null;
      }

      const mfaSecret: MFASecret = JSON.parse(mfaData);
      mfaSecret.backupCodes = this.generateBackupCodes(10);

      await this.redis.set(`mfa_secret:${userId}`, JSON.stringify(mfaSecret));

      this.logger.info('Backup codes regenerated', { userId });
      return mfaSecret.backupCodes;
    } catch (error) {
      this.logger.error('Failed to regenerate backup codes', {
        userId,
        error: error.message,
      });
      return null;
    }
  }
}
