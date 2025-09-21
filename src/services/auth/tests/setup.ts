/**
 * Test Setup
 * Global test configuration and utilities
 */

import { RedisService } from '../src/services/RedisService';
import { Logger } from '../src/utils/logger';

// Mock Redis for testing
jest.mock('../src/services/RedisService', () => {
  return {
    RedisService: jest.fn().mockImplementation(() => ({
      connect: jest.fn().mockResolvedValue(undefined),
      disconnect: jest.fn().mockResolvedValue(undefined),
      set: jest.fn().mockResolvedValue(undefined),
      setex: jest.fn().mockResolvedValue(undefined),
      get: jest.fn().mockResolvedValue(null),
      del: jest.fn().mockResolvedValue(1),
      exists: jest.fn().mockResolvedValue(0),
      expire: jest.fn().mockResolvedValue(true),
      ttl: jest.fn().mockResolvedValue(-1),
      keys: jest.fn().mockResolvedValue([]),
      incr: jest.fn().mockResolvedValue(1),
      sadd: jest.fn().mockResolvedValue(1),
      srem: jest.fn().mockResolvedValue(1),
      smembers: jest.fn().mockResolvedValue([]),
      lpush: jest.fn().mockResolvedValue(1),
      llen: jest.fn().mockResolvedValue(0),
      lpop: jest.fn().mockResolvedValue(null),
      isHealthy: jest.fn().mockReturnValue(true),
      ping: jest.fn().mockResolvedValue('PONG'),
    })),
  };
});

// Mock Logger to reduce noise in tests
jest.mock('../src/utils/logger', () => ({
  Logger: jest.fn().mockImplementation(() => ({
    info: jest.fn(),
    error: jest.fn(),
    warn: jest.fn(),
    debug: jest.fn(),
    security: jest.fn(),
    audit: jest.fn(),
    performance: jest.fn(),
  })),
  PerformanceTimer: jest.fn().mockImplementation(() => ({
    end: jest.fn().mockReturnValue(100),
  })),
}));

// Global test utilities
export const createMockRedis = (): jest.Mocked<RedisService> => {
  return new RedisService() as jest.Mocked<RedisService>;
};

export const createMockUser = (overrides = {}) => ({
  id: 'user-123',
  email: 'test@example.com',
  username: 'testuser',
  firstName: process.env.UNKNOWN,
  lastName: 'User',
  emailVerified: true,
  mfaEnabled: false,
  status: 'active' as const,
  roles: [
    {
      id: 'role-1',
      name: 'user',
      description: 'Standard user',
      permissions: [],
      isSystem: true,
      createdAt: new Date(),
      updatedAt: new Date(),
    },
  ],
  permissions: [],
  createdAt: new Date(),
  updatedAt: new Date(),
  metadata: {},
  ...overrides,
});

export const createMockSession = (overrides = {}) => ({
  id: 'session-123',
  userId: 'user-123',
  deviceInfo: {
    deviceId: 'device-123',
    deviceName: 'Chrome Browser',
    deviceType: 'desktop' as const,
    os: 'Windows',
    browser: 'Chrome',
    isTrusted: false,
  },
  ipAddress: '127.0.0.1',
  userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
  isActive: true,
  lastActivityAt: new Date(),
  expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000),
  createdAt: new Date(),
  metadata: {},
  ...overrides,
});

export const createMockRole = (overrides = {}) => ({
  id: 'role-123',
  name: 'test-role',
  description: 'Test role',
  permissions: [],
  isSystem: false,
  createdAt: new Date(),
  updatedAt: new Date(),
  ...overrides,
});

export const createMockPermission = (overrides = {}) => ({
  id: 'perm-123',
  name: 'test.read',
  resource: process.env.UNKNOWN,
  action: 'read',
  description: 'Test read permission',
  ...overrides,
});

// Setup and teardown helpers
export const setupTestEnvironment = async () => {
  // Set test environment variables
  process.env.NODE_ENV = process.env.UNKNOWN;
  process.env.JWT_SECRET = 'test-jwt-secret';
  process.env.REDIS_DB = '15'; // Use separate DB for tests
};

export const cleanupTestEnvironment = async () => {
  // Cleanup logic if needed
};

// Mock external services
export const mockEmailService = {
  sendVerificationEmail: jest.fn().mockResolvedValue(true),
  sendPasswordResetEmail: jest.fn().mockResolvedValue(true),
  sendPasswordResetConfirmation: jest.fn().mockResolvedValue(true),
  sendLoginNotification: jest.fn().mockResolvedValue(true),
  sendMFABackupCodes: jest.fn().mockResolvedValue(true),
  sendSecurityAlert: jest.fn().mockResolvedValue(true),
  sendWelcomeEmail: jest.fn().mockResolvedValue(true),
  testConfiguration: jest.fn().mockResolvedValue(true),
};

// Test data generators
export const generateTestEmail = (prefix = process.env.UNKNOWN) =>
  `${prefix}+${Date.now()}@example.com`;
export const generateTestUsername = (prefix = 'user') =>
  `${prefix}_${Date.now()}`;
export const generateTestPassword = () => 'TestPassword123!@#';

// Time helpers
export const advanceTime = (milliseconds: number) => {
  jest.advanceTimersByTime(milliseconds);
};

// Assertion helpers
export const expectValidJWT = (token: string) => {
  expect(token).toBeDefined();
  expect(typeof token).toBe('string');
  expect(token.split('.')).toHaveLength(3);
};

export const expectValidUUID = (uuid: string) => {
  expect(uuid).toBeDefined();
  expect(typeof uuid).toBe('string');
  expect(uuid).toMatch(
    /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
  );
};

// Setup Jest globals
beforeAll(async () => {
  await setupTestEnvironment();
});

afterAll(async () => {
  await cleanupTestEnvironment();
});

beforeEach(() => {
  jest.clearAllMocks();
});

// Enable fake timers for testing time-dependent code
jest.useFakeTimers();
