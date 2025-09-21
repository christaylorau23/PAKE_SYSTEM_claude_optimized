/**
 * PAKE System Authentication Types
 * Comprehensive type definitions for the authentication system
 */

export interface User {
  id: string;
  email: string;
  username: string;
  firstName: string;
  lastName: string;
  avatar?: string;
  emailVerified: boolean;
  mfaEnabled: boolean;
  status: UserStatus;
  roles: Role[];
  permissions: Permission[];
  lastLoginAt?: Date;
  createdAt: Date;
  updatedAt: Date;
  metadata?: Record<string, any>;
}

export interface Role {
  id: string;
  name: string;
  description: string;
  permissions: Permission[];
  isSystem: boolean;
  createdAt: Date;
  updatedAt: Date;
}

export interface Permission {
  id: string;
  name: string;
  resource: string;
  action: string;
  conditions?: Record<string, any>;
  description: string;
}

export enum UserStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  SUSPENDED = 'suspended',
  PENDING_VERIFICATION = 'pending_verification',
}

export interface AuthToken {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn: number;
  scope?: string;
}

export interface JWTPayload {
  sub: string; // user id
  email: string;
  username: string;
  roles: string[];
  permissions: string[];
  iat: number;
  exp: number;
  iss: string;
  aud: string;
  sessionId: string;
  mfaVerified?: boolean;
}

export interface Session {
  id: string;
  userId: string;
  deviceInfo: DeviceInfo;
  ipAddress: string;
  userAgent: string;
  isActive: boolean;
  lastActivityAt: Date;
  expiresAt: Date;
  createdAt: Date;
  metadata?: Record<string, any>;
}

export interface DeviceInfo {
  deviceId: string;
  deviceName?: string;
  deviceType: 'desktop' | 'mobile' | 'tablet' | 'unknown';
  os?: string;
  browser?: string;
  isTrusted: boolean;
}

export interface MFASecret {
  userId: string;
  secret: string;
  backupCodes: string[];
  qrCodeUrl: string;
  isVerified: boolean;
  createdAt: Date;
}

export interface WebAuthnCredential {
  id: string;
  userId: string;
  credentialId: string;
  publicKey: string;
  counter: number;
  deviceName?: string;
  isBackupEligible: boolean;
  isBackedUp: boolean;
  createdAt: Date;
  lastUsedAt?: Date;
}

export interface LoginAttempt {
  id: string;
  userId?: string;
  email: string;
  ipAddress: string;
  userAgent: string;
  success: boolean;
  failureReason?: string;
  mfaRequired: boolean;
  attemptedAt: Date;
}

export interface PasswordPolicy {
  minLength: number;
  maxLength: number;
  requireUppercase: boolean;
  requireLowercase: boolean;
  requireNumbers: boolean;
  requireSymbols: boolean;
  preventCommonPasswords: boolean;
  preventReuse: number;
  maxAge: number; // days
}

export interface AuthConfig {
  jwt: {
    secret: string;
    accessTokenExpiry: string;
    refreshTokenExpiry: string;
    issuer: string;
    audience: string;
  };
  oauth: {
    providers: {
      google?: OAuth2Provider;
      github?: OAuth2Provider;
      microsoft?: OAuth2Provider;
    };
  };
  mfa: {
    issuer: string;
    windowSize: number;
  };
  session: {
    maxSessions: number;
    maxAge: number;
    extendOnActivity: boolean;
  };
  security: {
    REDACTED_SECRETPolicy: PasswordPolicy;
    lockoutPolicy: {
      maxAttempts: number;
      lockoutDuration: number; // minutes
      resetAfter: number; // minutes
    };
    rateLimiting: {
      windowMs: number;
      maxRequests: number;
    };
  };
}

export interface OAuth2Provider {
  clientId: string;
  clientSecret: string;
  scope: string[];
  redirectUri: string;
  authUrl: string;
  tokenUrl: string;
  userInfoUrl: string;
}

export interface AuthRequest extends Express.Request {
  user?: User;
  session?: Session;
  permissions?: Permission[];
}

export interface AuthResponse {
  success: boolean;
  user?: User;
  tokens?: AuthToken;
  mfaRequired?: boolean;
  mfaSecret?: {
    secret: string;
    qrCode: string;
    backupCodes: string[];
  };
  error?: string;
  code?: string;
}

export interface PermissionCheck {
  resource: string;
  action: string;
  conditions?: Record<string, any>;
}

export interface AuditLog {
  id: string;
  userId?: string;
  action: string;
  resource: string;
  resourceId?: string;
  ipAddress: string;
  userAgent: string;
  success: boolean;
  error?: string;
  metadata?: Record<string, any>;
  timestamp: Date;
}

// Middleware types
export interface AuthMiddlewareOptions {
  required?: boolean;
  permissions?: PermissionCheck[];
  roles?: string[];
  mfaRequired?: boolean;
}

// Event types
export interface AuthEvent {
  type: AuthEventType;
  userId?: string;
  sessionId?: string;
  metadata?: Record<string, any>;
  timestamp: Date;
}

export enum AuthEventType {
  LOGIN_SUCCESS = 'login_success',
  LOGIN_FAILED = 'login_failed',
  LOGOUT = 'logout',
  MFA_ENABLED = 'mfa_enabled',
  MFA_DISABLED = 'mfa_disabled',
  PASSWORD_CHANGED = 'REDACTED_SECRET_changed',
  ACCOUNT_LOCKED = 'account_locked',
  PERMISSION_DENIED = 'permission_denied',
  TOKEN_REFRESHED = 'token_refreshed',
  SESSION_EXPIRED = 'session_expired',
}
