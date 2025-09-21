/**
 * Break Glass Emergency Access Service
 * Provides emergency access to secrets during critical situations
 */

import crypto from 'crypto';
import { EventEmitter } from 'events';
import { VaultService } from './VaultService';
import { SecretsManagerSDK } from './SecretsManagerSDK';
import {
  BreakGlassConfig,
  BreakGlassProcedure,
  BreakGlassAction,
  BreakGlassActionType,
  BreakGlassSession,
  BreakGlassStatus,
  BreakGlassActionLog,
  EmergencyContact,
  SecretEvent,
  SecretEventType,
} from '../types/secrets.types';
import { Logger } from '../utils/logger';

interface BreakGlassRequest {
  procedureId: string;
  initiator: string;
  justification: string;
  urgency: 'low' | 'medium' | 'high' | 'critical';
  contactInfo: {
    email: string;
    phone?: string;
  };
  metadata?: Record<string, any>;
}

interface BreakGlassApproval {
  sessionId: string;
  approver: string;
  approved: boolean;
  reason?: string;
  timestamp: string;
  ipAddress?: string;
  mfaVerified?: boolean;
}

interface EmergencySecretAccess {
  secretPath: string;
  value: any;
  accessedAt: string;
  accessedBy: string;
  sessionId: string;
  reason: string;
}

export class BreakGlassService extends EventEmitter {
  private readonly logger = new Logger('BreakGlassService');
  private readonly config: BreakGlassConfig;
  private readonly vaultService?: VaultService;
  private readonly secretsSDK?: SecretsManagerSDK;

  private activeSessions = new Map<string, BreakGlassSession>();
  private procedures = new Map<string, BreakGlassProcedure>();
  private sessionHistory: BreakGlassSession[] = [];

  private isInitialized = false;
  private sessionMonitor?: NodeJS.Timeout;

  // Emergency master keys (encrypted)
  private emergencyKeys = new Map<string, string>();

  constructor(
    config: BreakGlassConfig,
    vaultService?: VaultService,
    secretsSDK?: SecretsManagerSDK
  ) {
    super();
    this.config = config;
    this.vaultService = vaultService;
    this.secretsSDK = secretsSDK;
  }

  /**
   * Initialize break glass service
   */
  async initialize(): Promise<void> {
    try {
      // Load break glass procedures
      await this.loadProcedures();

      // Initialize emergency keys
      await this.initializeEmergencyKeys();

      // Start session monitoring
      this.startSessionMonitoring();

      this.isInitialized = true;
      this.logger.info('Break glass service initialized successfully', {
        procedureCount: this.procedures.size,
        enabled: this.config.enabled,
      });
    } catch (error) {
      this.logger.error('Failed to initialize break glass service', {
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Initiate break glass session
   */
  async initiateBreakGlass(request: BreakGlassRequest): Promise<string> {
    this.ensureInitialized();

    if (!this.config.enabled) {
      throw new Error('Break glass procedures are disabled');
    }

    try {
      const procedure = this.procedures.get(request.procedureId);
      if (!procedure) {
        throw new Error(
          `Break glass procedure not found: ${request.procedureId}`
        );
      }

      // Generate session ID
      const sessionId = crypto.randomUUID();

      // Create break glass session
      const session: BreakGlassSession = {
        id: sessionId,
        initiator: request.initiator,
        procedure,
        justification: request.justification,
        approvers: [],
        status: BreakGlassStatus.PENDING,
        startTime: new Date().toISOString(),
        actions: [],
        auditTrail: [
          `${new Date().toISOString()}: Session initiated by ${request.initiator}`,
          `${new Date().toISOString()}: Procedure: ${procedure.name}`,
          `${new Date().toISOString()}: Justification: ${request.justification}`,
        ],
      };

      this.activeSessions.set(sessionId, session);

      // Send emergency notifications
      await this.notifyEmergencyContacts(session, 'initiated');

      // Log security event
      await this.logSecurityEvent({
        id: `break-glass-${Date.now()}`,
        timestamp: new Date().toISOString(),
        type: SecretEventType.BREAK_GLASS_ACTIVATE,
        secretId: sessionId,
        actor: request.initiator,
        source: 'break-glass',
        success: true,
        metadata: {
          procedureId: request.procedureId,
          urgency: request.urgency,
          justification: request.justification,
        },
      });

      // Auto-approve if configured
      if (!this.config.approvalRequired || procedure.requiredApprovals === 0) {
        await this.approveSession(
          sessionId,
          'system',
          true,
          'Auto-approved based on configuration'
        );
      }

      this.logger.warn('Break glass session initiated', {
        sessionId,
        initiator: request.initiator,
        procedure: procedure.name,
        urgency: request.urgency,
        justification: request.justification,
      });

      return sessionId;
    } catch (error) {
      this.logger.error('Failed to initiate break glass session', {
        procedureId: request.procedureId,
        initiator: request.initiator,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Approve or deny break glass session
   */
  async approveSession(
    sessionId: string,
    approver: string,
    approved: boolean,
    reason?: string
  ): Promise<void> {
    this.ensureInitialized();

    try {
      const session = this.activeSessions.get(sessionId);
      if (!session) {
        throw new Error(`Break glass session not found: ${sessionId}`);
      }

      if (session.status !== BreakGlassStatus.PENDING) {
        throw new Error(`Session is not pending approval: ${session.status}`);
      }

      // Add approval
      const approval: BreakGlassApproval = {
        sessionId,
        approver,
        approved,
        reason,
        timestamp: new Date().toISOString(),
      };

      if (approved) {
        session.approvers.push(approver);
      }

      session.auditTrail.push(
        `${approval.timestamp}: ${approved ? 'APPROVED' : 'DENIED'} by ${approver}${reason ? ` - ${reason}` : ''}`
      );

      // Check if we have enough approvals
      const requiredApprovals = session.procedure.requiredApprovals;
      const currentApprovals = session.approvers.length;

      if (!approved && requiredApprovals > 0) {
        // Denied
        session.status = BreakGlassStatus.REVOKED;
        session.endTime = new Date().toISOString();

        await this.notifyEmergencyContacts(session, 'denied');
        this.moveSessionToHistory(session);
      } else if (currentApprovals >= requiredApprovals) {
        // Approved and activated
        session.status = BreakGlassStatus.ACTIVE;

        // Set session timeout
        if (session.procedure.timeLimit > 0) {
          setTimeout(
            () => {
              this.expireSession(sessionId);
            },
            session.procedure.timeLimit * 60 * 1000
          ); // Convert to milliseconds
        }

        await this.notifyEmergencyContacts(session, 'approved');
      }

      this.logger.warn('Break glass session approval recorded', {
        sessionId,
        approver,
        approved,
        currentApprovals,
        requiredApprovals,
        status: session.status,
      });
    } catch (error) {
      this.logger.error('Failed to approve break glass session', {
        sessionId,
        approver,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Execute break glass action
   */
  async executeAction(
    sessionId: string,
    actionType: BreakGlassActionType,
    resource: string,
    parameters?: Record<string, any>
  ): Promise<any> {
    this.ensureInitialized();

    try {
      const session = this.activeSessions.get(sessionId);
      if (!session) {
        throw new Error(`Break glass session not found: ${sessionId}`);
      }

      if (session.status !== BreakGlassStatus.ACTIVE) {
        throw new Error(`Session is not active: ${session.status}`);
      }

      // Check if action is allowed
      const allowedAction = session.procedure.actions.find(
        action => action.type === actionType && action.resource === resource
      );

      if (!allowedAction) {
        throw new Error(
          `Action not allowed in this procedure: ${actionType} on ${resource}`
        );
      }

      // Execute the action
      const actionLog: BreakGlassActionLog = {
        action: allowedAction,
        timestamp: new Date().toISOString(),
        result: 'success',
        metadata: parameters,
      };

      let result: any;

      try {
        switch (actionType) {
          case BreakGlassActionType.REVEAL_SECRET:
            result = await this.revealSecret(resource, session);
            break;

          case BreakGlassActionType.EMERGENCY_DECRYPT:
            result = await this.emergencyDecrypt(resource, parameters, session);
            break;

          case BreakGlassActionType.GRANT_ACCESS:
            result = await this.grantEmergencyAccess(
              resource,
              parameters,
              session
            );
            break;

          case BreakGlassActionType.BYPASS_POLICY:
            result = await this.bypassPolicy(resource, parameters, session);
            break;

          case BreakGlassActionType.DISABLE_ROTATION:
            result = await this.disableRotation(resource, parameters, session);
            break;

          case BreakGlassActionType.OVERRIDE_EXPIRATION:
            result = await this.overrideExpiration(
              resource,
              parameters,
              session
            );
            break;

          default:
            throw new Error(`Unsupported action type: ${actionType}`);
        }

        actionLog.result = 'success';
      } catch (error) {
        actionLog.result = 'failure';
        actionLog.error = error.message;
        throw error;
      } finally {
        // Always log the action
        session.actions.push(actionLog);
        session.auditTrail.push(
          `${actionLog.timestamp}: ${actionType} on ${resource} - ${actionLog.result.toUpperCase()}${actionLog.error ? ` (${actionLog.error})` : ''}`
        );

        // Log security event
        await this.logSecurityEvent({
          id: `break-glass-action-${Date.now()}`,
          timestamp: new Date().toISOString(),
          type: SecretEventType.BREAK_GLASS_ACTIVATE,
          secretId: resource,
          actor: session.initiator,
          source: 'break-glass',
          success: actionLog.result === 'success',
          error: actionLog.error,
          metadata: {
            sessionId,
            actionType,
            parameters,
          },
        });
      }

      this.logger.warn('Break glass action executed', {
        sessionId,
        actionType,
        resource,
        result: actionLog.result,
        initiator: session.initiator,
      });

      return result;
    } catch (error) {
      this.logger.error('Failed to execute break glass action', {
        sessionId,
        actionType,
        resource,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Get active break glass sessions
   */
  getActiveSessions(): BreakGlassSession[] {
    return Array.from(this.activeSessions.values());
  }

  /**
   * Get break glass session history
   */
  getSessionHistory(limit?: number): BreakGlassSession[] {
    return limit
      ? this.sessionHistory.slice(0, limit)
      : [...this.sessionHistory];
  }

  /**
   * Revoke active session
   */
  async revokeSession(
    sessionId: string,
    revoker: string,
    reason?: string
  ): Promise<void> {
    this.ensureInitialized();

    try {
      const session = this.activeSessions.get(sessionId);
      if (!session) {
        throw new Error(`Break glass session not found: ${sessionId}`);
      }

      session.status = BreakGlassStatus.REVOKED;
      session.endTime = new Date().toISOString();
      session.auditTrail.push(
        `${new Date().toISOString()}: Session revoked by ${revoker}${reason ? ` - ${reason}` : ''}`
      );

      await this.notifyEmergencyContacts(session, 'revoked');
      this.moveSessionToHistory(session);

      this.logger.warn('Break glass session revoked', {
        sessionId,
        revoker,
        reason,
      });
    } catch (error) {
      this.logger.error('Failed to revoke break glass session', {
        sessionId,
        revoker,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Private helper methods
   */

  private async loadProcedures(): Promise<void> {
    // Default emergency procedures
    const defaultProcedures: BreakGlassProcedure[] = [
      {
        id: 'emergency-access',
        name: 'Emergency Secret Access',
        description: 'Access critical secrets during outages or emergencies',
        justification:
          'System outage preventing normal access to critical secrets',
        actions: [
          {
            type: BreakGlassActionType.REVEAL_SECRET,
            resource: 'production/database',
            permission: 'read',
          },
          {
            type: BreakGlassActionType.REVEAL_SECRET,
            resource: 'production/api-keys',
            permission: 'read',
          },
        ],
        requiredApprovals: this.config.approvalRequired ? 2 : 0,
        timeLimit: 240, // 4 hours
        audit: true,
      },
      {
        id: 'security-incident',
        name: 'Security Incident Response',
        description: 'Emergency access during security incidents',
        justification: 'Active security incident requiring emergency access',
        actions: [
          {
            type: BreakGlassActionType.REVEAL_SECRET,
            resource: 'security/*',
            permission: 'read',
          },
          {
            type: BreakGlassActionType.BYPASS_POLICY,
            resource: 'access-policies/*',
            permission: 'override',
          },
          {
            type: BreakGlassActionType.DISABLE_ROTATION,
            resource: 'production/*',
            permission: 'manage',
          },
        ],
        requiredApprovals: this.config.approvalRequired ? 1 : 0,
        timeLimit: 120, // 2 hours
        audit: true,
      },
      {
        id: 'disaster-recovery',
        name: 'Disaster Recovery',
        description: 'Full system recovery access',
        justification:
          'Complete system failure requiring full recovery procedures',
        actions: [
          {
            type: BreakGlassActionType.REVEAL_SECRET,
            resource: '*',
            permission: 'read',
          },
          {
            type: BreakGlassActionType.EMERGENCY_DECRYPT,
            resource: '*',
            permission: 'decrypt',
          },
          {
            type: BreakGlassActionType.BYPASS_POLICY,
            resource: '*',
            permission: 'override',
          },
        ],
        requiredApprovals: this.config.approvalRequired ? 3 : 0,
        timeLimit: 480, // 8 hours
        audit: true,
      },
    ];

    for (const procedure of defaultProcedures) {
      this.procedures.set(procedure.id, procedure);
    }
  }

  private async initializeEmergencyKeys(): Promise<void> {
    // Initialize emergency master keys
    // In production, these would be derived from secure sources
    const masterKey =
      process.env.BREAK_GLASS_MASTER_KEY ||
      crypto.randomBytes(32).toString('hex');
    this.emergencyKeys.set('master', masterKey);

    this.logger.debug('Emergency keys initialized');
  }

  private async revealSecret(
    secretPath: string,
    session: BreakGlassSession
  ): Promise<EmergencySecretAccess> {
    if (!this.secretsSDK) {
      throw new Error('Secrets SDK not available for emergency access');
    }

    const secret = await this.secretsSDK.getSecret(secretPath);
    if (!secret) {
      throw new Error(`Secret not found: ${secretPath}`);
    }

    return {
      secretPath,
      value: secret.value,
      accessedAt: new Date().toISOString(),
      accessedBy: session.initiator,
      sessionId: session.id,
      reason: session.justification,
    };
  }

  private async emergencyDecrypt(
    resource: string,
    parameters: Record<string, any> | undefined,
    session: BreakGlassSession
  ): Promise<any> {
    // Emergency decryption using master keys
    const encryptedData = parameters?.data;
    if (!encryptedData) {
      throw new Error('No encrypted data provided');
    }

    const masterKey = this.emergencyKeys.get('master');
    if (!masterKey) {
      throw new Error('Emergency master key not available');
    }

    // Decrypt using emergency key (simplified implementation)
    try {
      const decipher = crypto.createDecipher('aes-256-gcm', masterKey, {
        iv: Buffer.from(parameters?.iv || '', 'hex'),
      });

      const decrypted = Buffer.concat([
        decipher.update(Buffer.from(encryptedData, 'hex')),
        decipher.final(),
      ]);

      return {
        decryptedData: decrypted.toString('utf8'),
        decryptedAt: new Date().toISOString(),
        decryptedBy: session.initiator,
        sessionId: session.id,
      };
    } catch (error) {
      throw new Error(`Emergency decryption failed: ${error.message}`);
    }
  }

  private async grantEmergencyAccess(
    resource: string,
    parameters: Record<string, any> | undefined,
    session: BreakGlassSession
  ): Promise<any> {
    return {
      resource,
      accessGranted: true,
      grantedAt: new Date().toISOString(),
      grantedBy: session.initiator,
      sessionId: session.id,
      duration: parameters?.duration || session.procedure.timeLimit,
    };
  }

  private async bypassPolicy(
    resource: string,
    parameters: Record<string, any> | undefined,
    session: BreakGlassSession
  ): Promise<any> {
    return {
      resource,
      policyBypassed: true,
      bypassedAt: new Date().toISOString(),
      bypassedBy: session.initiator,
      sessionId: session.id,
      originalPolicy: parameters?.originalPolicy,
    };
  }

  private async disableRotation(
    resource: string,
    parameters: Record<string, any> | undefined,
    session: BreakGlassSession
  ): Promise<any> {
    return {
      resource,
      rotationDisabled: true,
      disabledAt: new Date().toISOString(),
      disabledBy: session.initiator,
      sessionId: session.id,
      duration: parameters?.duration || 24, // hours
    };
  }

  private async overrideExpiration(
    resource: string,
    parameters: Record<string, any> | undefined,
    session: BreakGlassSession
  ): Promise<any> {
    return {
      resource,
      expirationOverridden: true,
      overriddenAt: new Date().toISOString(),
      overriddenBy: session.initiator,
      sessionId: session.id,
      newExpiration: parameters?.newExpiration,
    };
  }

  private async notifyEmergencyContacts(
    session: BreakGlassSession,
    event: string
  ): Promise<void> {
    const message = {
      event,
      sessionId: session.id,
      procedure: session.procedure.name,
      initiator: session.initiator,
      justification: session.justification,
      timestamp: new Date().toISOString(),
    };

    for (const contact of this.config.emergencyContacts) {
      try {
        // Send notification (implementation would use actual notification service)
        this.logger.warn('Emergency notification sent', {
          contact: contact.email,
          event,
          sessionId: session.id,
        });
      } catch (error) {
        this.logger.error('Failed to notify emergency contact', {
          contact: contact.email,
          error: error.message,
        });
      }
    }

    // Emit event for external notification systems
    this.emit('emergencyNotification', message);
  }

  private async logSecurityEvent(event: SecretEvent): Promise<void> {
    // Log to audit system
    this.emit('securityEvent', event);

    // Also log locally for break glass audit trail
    this.logger.warn('BREAK GLASS SECURITY EVENT', event);
  }

  private expireSession(sessionId: string): void {
    const session = this.activeSessions.get(sessionId);
    if (session && session.status === BreakGlassStatus.ACTIVE) {
      session.status = BreakGlassStatus.EXPIRED;
      session.endTime = new Date().toISOString();
      session.auditTrail.push(
        `${new Date().toISOString()}: Session expired due to time limit`
      );

      this.moveSessionToHistory(session);

      this.logger.warn('Break glass session expired', { sessionId });
    }
  }

  private moveSessionToHistory(session: BreakGlassSession): void {
    this.activeSessions.delete(session.id);
    this.sessionHistory.unshift(session); // Add to beginning

    // Keep only last 100 sessions in memory
    if (this.sessionHistory.length > 100) {
      this.sessionHistory.splice(100);
    }
  }

  private startSessionMonitoring(): void {
    this.sessionMonitor = setInterval(() => {
      this.checkSessionTimeouts();
    }, 60000); // Check every minute
  }

  private checkSessionTimeouts(): void {
    const now = new Date();

    for (const [sessionId, session] of this.activeSessions.entries()) {
      if (
        session.status === BreakGlassStatus.ACTIVE &&
        session.procedure.timeLimit > 0
      ) {
        const startTime = new Date(session.startTime);
        const timeLimit = session.procedure.timeLimit * 60 * 1000; // Convert to milliseconds

        if (now.getTime() - startTime.getTime() > timeLimit) {
          this.expireSession(sessionId);
        }
      }
    }
  }

  private ensureInitialized(): void {
    if (!this.isInitialized) {
      throw new Error(
        'Break glass service not initialized. Call initialize() first.'
      );
    }
  }

  /**
   * Close break glass service
   */
  async close(): Promise<void> {
    if (this.sessionMonitor) {
      clearInterval(this.sessionMonitor);
    }

    // Revoke all active sessions
    for (const [sessionId, session] of this.activeSessions.entries()) {
      if (session.status === BreakGlassStatus.ACTIVE) {
        await this.revokeSession(sessionId, 'system', 'Service shutdown');
      }
    }

    // Clear sensitive data
    this.emergencyKeys.clear();
    this.activeSessions.clear();

    this.isInitialized = false;
    this.logger.info('Break glass service closed');
  }
}
