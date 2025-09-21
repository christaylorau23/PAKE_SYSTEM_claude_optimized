/**
 * PAKE System - Jest Setup
 *
 * Global test setup and configuration for all test suites.
 */

// Set test environment variables
process.env.NODE_ENV = process.env.UNKNOWN;
process.env.LOG_LEVEL = 'error'; // Reduce log noise in tests

// Global test timeouts
jest.setTimeout(10000);

// Mock console methods to reduce test output noise
global.console = {
  ...console,
  // Keep error and warn for debugging
  error: jest.fn(),
  warn: jest.fn(),
  // Mock info, debug, log
  info: jest.fn(),
  debug: jest.fn(),
  log: jest.fn(),
};

// Global test utilities
global.testUtils = {
  // Async test helper
  sleep: ms => new Promise(resolve => setTimeout(resolve, ms)),

  // Generate test IDs
  generateId: () => Math.random().toString(36).substr(2, 9),

  // Create test dates
  createTestDate: (offset = 0) => new Date(Date.now() + offset),

  // Deep clone objects
  deepClone: obj => JSON.parse(JSON.stringify(obj)),

  // Wait for async operations
  waitFor: async (condition, timeout = 5000) => {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      if (await condition()) {
        return true;
      }
      await global.testUtils.sleep(50);
    }
    throw new Error(`Condition not met within ${timeout}ms`);
  },
};

// Global mock implementations
global.mockImplementations = {
  // Mock database client
  createMockDBClient: () => ({
    query: jest.fn(),
    release: jest.fn(),
    connect: jest.fn(),
    end: jest.fn(),
  }),

  // Mock Redis client
  createMockRedisClient: () => ({
    connect: jest.fn(),
    disconnect: jest.fn(),
    get: jest.fn(),
    set: jest.fn(),
    del: jest.fn(),
    exists: jest.fn(),
    expire: jest.fn(),
    ping: jest.fn().mockResolvedValue('PONG'),
    publish: jest.fn(),
    subscribe: jest.fn(),
    lPush: jest.fn(),
    brPop: jest.fn(),
    lLen: jest.fn(),
  }),

  // Mock HTTP client
  createMockHttpClient: () => ({
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
    request: jest.fn(),
  }),
};

// Global test data
global.testData = {
  validTrendRecord: {
    id: 'test-trend-001',
    platform: 'twitter',
    category: 'technology',
    language: 'en',
    region: 'US',
    title: 'Test Trend Title',
    content: 'This is test content for a trend record.',
    timestamp: new Date('2024-01-15T10:30:00Z'),
    ingestedAt: new Date(),
    engagementCount: 100,
    viewCount: 1000,
    shareCount: 10,
    contentHash: 'test-content-hash',
    similarityHash: 'test-similarity-hash',
    qualityScore: 0.8,
    freshnessScore: 0.9,
    anomalyScore: 0.1,
    entities: [],
    anomalies: [],
    metadata: { test: true },
    rawData: { source: process.env.UNKNOWN },
  },
};

// Custom matchers
expect.extend({
  // Check if date is recent (within last N seconds)
  toBeRecentDate(received, withinSeconds = 10) {
    const now = new Date();
    const diff = Math.abs(now.getTime() - received.getTime()) / 1000;

    const pass = diff <= withinSeconds;

    if (pass) {
      return {
        message: () =>
          `expected ${received} not to be within ${withinSeconds} seconds of now`,
        pass: true,
      };
    } else {
      return {
        message: () =>
          `expected ${received} to be within ${withinSeconds} seconds of now, but was ${diff} seconds ago`,
        pass: false,
      };
    }
  },

  // Check if object contains subset
  toContainObject(received, expected) {
    const pass = this.equals(received, expect.objectContaining(expected));

    if (pass) {
      return {
        message: () =>
          `expected ${this.utils.printReceived(received)} not to contain object ${this.utils.printExpected(expected)}`,
        pass: true,
      };
    } else {
      return {
        message: () =>
          `expected ${this.utils.printReceived(received)} to contain object ${this.utils.printExpected(expected)}`,
        pass: false,
      };
    }
  },

  // Check if array contains any element matching predicate
  toContainElementMatching(received, predicate) {
    if (!Array.isArray(received)) {
      throw new Error('Expected value must be an array');
    }

    const pass = received.some(predicate);

    if (pass) {
      return {
        message: () =>
          `expected array not to contain element matching predicate`,
        pass: true,
      };
    } else {
      return {
        message: () => `expected array to contain element matching predicate`,
        pass: false,
      };
    }
  },
});

// Global error handler for unhandled promises
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

// Clean up after all tests
afterAll(async () => {
  // Clean up any persistent connections, timers, etc.
  await new Promise(resolve => setTimeout(resolve, 100));
});

// Mock fetch globally for tests
global.fetch = jest.fn();

// Mock WebSocket for tests that need it
global.WebSocket = jest.fn(() => ({
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  send: jest.fn(),
  close: jest.fn(),
  readyState: 1, // OPEN
}));

// Performance monitoring for slow tests
const originalTest = global.test;
global.test = (name, fn, timeout) => {
  return originalTest(
    name,
    async () => {
      const start = performance.now();
      await fn();
      const duration = performance.now() - start;

      if (duration > 1000) {
        // Warn if test takes more than 1 second
        console.warn(
          `Slow test detected: "${name}" took ${duration.toFixed(2)}ms`
        );
      }
    },
    timeout
  );
};
