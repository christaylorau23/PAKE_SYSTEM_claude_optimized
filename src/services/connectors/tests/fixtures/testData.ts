/**
 * PAKE System - Test Fixtures for Connectors
 *
 * Comprehensive test data for all connector types and scenarios.
 */

import {
  ConnectorRequest,
  ConnectorRequestType,
  ResponseEnvelope,
  ResponseStatus,
} from '../../src/Connector';

// Base test configurations
export const testConfigs = {
  database: {
    host: 'localhost',
    port: 5432,
    database: 'pake_test',
    user: 'test_user',
    REDACTED_SECRET: process.env.UNKNOWN,
    ssl: false,
  },
  redis: {
    host: 'localhost',
    port: 6379,
    REDACTED_SECRET: null,
    database: 0,
  },
  webscraper: {
    userAgent: 'PAKE-Test-Bot/1.0',
    respectRobots: true,
    maxConcurrency: 2,
    requestDelay: 1000,
  },
};

// Sample connector requests
export const sampleRequests = {
  webScrape: {
    basic: {
      id: 'web-001',
      type: ConnectorRequestType.SCRAPE_URL,
      target: 'https://example.com',
      parameters: {
        extractText: true,
        extractLinks: true,
        extractMetadata: true,
      },
      config: {
        timeout: 10000,
        maxRetries: 2,
        retryDelay: 1000,
      },
      metadata: {
        requestedAt: new Date().toISOString(),
        correlationId: 'test-corr-001',
        priority: 'normal' as const,
      },
    } as ConnectorRequest,

    withHeaders: {
      id: 'web-002',
      type: ConnectorRequestType.SCRAPE_URL,
      target: 'https://api.example.com/data',
      parameters: {
        extractJson: true,
        followRedirects: true,
      },
      config: {
        timeout: 15000,
        maxRetries: 3,
        retryDelay: 2000,
        headers: {
          Authorization: 'Bearer test-token',
          'X-Custom-Header': 'test-value',
        },
      },
      metadata: {
        requestedAt: new Date().toISOString(),
        correlationId: 'test-corr-002',
        priority: 'high' as const,
      },
    } as ConnectorRequest,

    sitemap: {
      id: 'web-003',
      type: ConnectorRequestType.SCRAPE_SITEMAP,
      target: 'https://example.com/sitemap.xml',
      parameters: {
        maxUrls: 100,
        filterPattern: '.*\\.html$',
      },
      config: {
        timeout: 30000,
        maxRetries: 2,
        retryDelay: 5000,
      },
      metadata: {
        requestedAt: new Date().toISOString(),
        correlationId: 'test-corr-003',
      },
    } as ConnectorRequest,
  },

  database: {
    select: {
      id: 'db-001',
      type: ConnectorRequestType.SELECT,
      target: 'users',
      parameters: {
        columns: ['id', 'name', 'email'],
        where: { active: true },
        orderBy: [{ column: 'created_at', direction: 'DESC' }],
        limit: 50,
      },
      config: {
        timeout: 5000,
        maxRetries: 2,
        retryDelay: 1000,
      },
      metadata: {
        requestedAt: new Date().toISOString(),
        correlationId: 'test-corr-004',
      },
    } as ConnectorRequest,

    insert: {
      id: 'db-002',
      type: ConnectorRequestType.INSERT,
      target: 'events',
      parameters: {
        data: {
          event_type: 'user_signup',
          user_id: 12345,
          timestamp: new Date().toISOString(),
          metadata: { source: 'web' },
        },
        returning: ['id', 'created_at'],
      },
      config: {
        timeout: 3000,
        maxRetries: 3,
        retryDelay: 500,
      },
      metadata: {
        requestedAt: new Date().toISOString(),
        correlationId: 'test-corr-005',
      },
    } as ConnectorRequest,

    customQuery: {
      id: 'db-003',
      type: ConnectorRequestType.QUERY,
      target: 'analytics',
      parameters: {
        sql: `
          SELECT 
            DATE_TRUNC('day', created_at) as date,
            COUNT(*) as user_count,
            AVG(engagement_score) as avg_engagement
          FROM user_analytics 
          WHERE created_at >= $1 AND created_at <= $2
          GROUP BY DATE_TRUNC('day', created_at)
          ORDER BY date DESC
        `,
        params: ['2024-01-01', '2024-12-31'],
      },
      config: {
        timeout: 10000,
        maxRetries: 1,
        retryDelay: 2000,
      },
      metadata: {
        requestedAt: new Date().toISOString(),
        correlationId: 'test-corr-006',
      },
    } as ConnectorRequest,
  },

  queue: {
    publish: {
      id: 'queue-001',
      type: ConnectorRequestType.PUBLISH,
      target: 'trend-updates',
      parameters: {
        message: {
          id: 'trend-12345',
          platform: 'twitter',
          content: 'AI breakthrough in quantum computing',
          timestamp: new Date().toISOString(),
          engagement: { likes: 1250, shares: 89, comments: 45 },
        },
        options: {
          priority: 5,
          delay: 0,
          ttl: 86400000, // 24 hours
        },
      },
      config: {
        timeout: 5000,
        maxRetries: 3,
        retryDelay: 1000,
      },
      metadata: {
        requestedAt: new Date().toISOString(),
        correlationId: 'test-corr-007',
        priority: 'high' as const,
      },
    } as ConnectorRequest,

    consume: {
      id: 'queue-002',
      type: ConnectorRequestType.CONSUME,
      target: 'processed-trends',
      parameters: {
        count: 10,
        timeout: 5000,
        acknowledgeMode: 'auto',
      },
      config: {
        timeout: 10000,
        maxRetries: 2,
        retryDelay: 2000,
      },
      metadata: {
        requestedAt: new Date().toISOString(),
        correlationId: 'test-corr-008',
      },
    } as ConnectorRequest,

    subscribe: {
      id: 'queue-003',
      type: ConnectorRequestType.SUBSCRIBE,
      target: 'live-events',
      parameters: {
        pattern: 'events.trends.*',
        callback: 'handleTrendEvent',
        options: {
          durableSubscription: true,
          autoAck: false,
        },
      },
      config: {
        timeout: 30000,
        maxRetries: 1,
        retryDelay: 5000,
      },
      metadata: {
        requestedAt: new Date().toISOString(),
        correlationId: 'test-corr-009',
      },
    } as ConnectorRequest,
  },
};

// Sample response data
export const sampleResponses = {
  webScrape: {
    success: {
      requestId: 'web-001',
      success: true,
      status: ResponseStatus.SUCCESS,
      data: {
        url: 'https://example.com',
        title: 'Example Domain',
        content:
          'This domain is for use in illustrative examples in documents.',
        links: [
          {
            href: 'https://www.iana.org/domains/example',
            text: 'More information...',
          },
        ],
        metadata: {
          contentType: 'text/html',
          charset: 'UTF-8',
          lastModified: '2024-01-15T10:30:00Z',
        },
      },
      metadata: {
        executionTime: 1250,
        timestamp: new Date().toISOString(),
        source: 'https://example.com',
        connector: 'WebScrapeConnector',
        dataSize: 1024,
        freshness: 0,
      },
    } as ResponseEnvelope<any>,

    robotsBlocked: {
      requestId: 'web-002',
      success: false,
      status: ResponseStatus.FORBIDDEN,
      data: null,
      metadata: {
        executionTime: 500,
        timestamp: new Date().toISOString(),
        source: 'https://blocked.example.com',
        connector: 'WebScrapeConnector',
      },
      error: {
        code: 'ROBOTS_TXT_BLOCKED',
        message: 'Access blocked by robots.txt',
        details: { robotsUrl: 'https://blocked.example.com/robots.txt' },
        retryable: false,
      },
    } as ResponseEnvelope<null>,
  },

  database: {
    selectSuccess: {
      requestId: 'db-001',
      success: true,
      status: ResponseStatus.SUCCESS,
      data: {
        rows: [
          { id: 1, name: 'John Doe', email: 'john@example.com' },
          { id: 2, name: 'Jane Smith', email: 'jane@example.com' },
        ],
        rowCount: 2,
        command: 'SELECT',
      },
      metadata: {
        executionTime: 45,
        timestamp: new Date().toISOString(),
        source: 'users',
        connector: 'DBConnector',
        recordCount: 2,
      },
    } as ResponseEnvelope<any>,

    insertSuccess: {
      requestId: 'db-002',
      success: true,
      status: ResponseStatus.SUCCESS,
      data: {
        rows: [{ id: 12345, created_at: new Date().toISOString() }],
        rowCount: 1,
        command: 'INSERT',
      },
      metadata: {
        executionTime: 25,
        timestamp: new Date().toISOString(),
        source: 'events',
        connector: 'DBConnector',
        recordCount: 1,
      },
    } as ResponseEnvelope<any>,
  },

  queue: {
    publishSuccess: {
      requestId: 'queue-001',
      success: true,
      status: ResponseStatus.SUCCESS,
      data: {
        messageId: 'msg-12345',
        queue: 'trend-updates',
        published: true,
        timestamp: new Date().toISOString(),
      },
      metadata: {
        executionTime: 15,
        timestamp: new Date().toISOString(),
        source: 'trend-updates',
        connector: 'QueueConnector',
      },
    } as ResponseEnvelope<any>,

    consumeSuccess: {
      requestId: 'queue-002',
      success: true,
      status: ResponseStatus.SUCCESS,
      data: {
        messages: [
          {
            id: 'msg-001',
            content: { event: 'trend_detected', data: { platform: 'twitter' } },
            timestamp: new Date().toISOString(),
          },
          {
            id: 'msg-002',
            content: { event: 'trend_processed', data: { platform: 'reddit' } },
            timestamp: new Date().toISOString(),
          },
        ],
        count: 2,
        hasMore: false,
      },
      metadata: {
        executionTime: 150,
        timestamp: new Date().toISOString(),
        source: 'processed-trends',
        connector: 'QueueConnector',
        recordCount: 2,
      },
    } as ResponseEnvelope<any>,
  },
};

// Error scenarios for testing
export const errorScenarios = {
  timeout: {
    requestId: 'error-001',
    success: false,
    status: ResponseStatus.TIMEOUT,
    data: null,
    metadata: {
      executionTime: 30000,
      timestamp: new Date().toISOString(),
      source: 'timeout-test',
      connector: 'TestConnector',
    },
    error: {
      code: 'TIMEOUT_ERROR',
      message: 'Operation timeout after 30000ms',
      details: {},
      retryable: true,
      retryAfter: 5000,
    },
  } as ResponseEnvelope<null>,

  rateLimit: {
    requestId: 'error-002',
    success: false,
    status: ResponseStatus.RATE_LIMITED,
    data: null,
    metadata: {
      executionTime: 100,
      timestamp: new Date().toISOString(),
      source: 'rate-limited-api',
      connector: 'TestConnector',
    },
    error: {
      code: 'RATE_LIMIT_EXCEEDED',
      message: 'Rate limit exceeded. Try again later.',
      details: { limit: 100, windowSize: 3600 },
      retryable: true,
      retryAfter: 3600,
    },
  } as ResponseEnvelope<null>,

  notFound: {
    requestId: 'error-003',
    success: false,
    status: ResponseStatus.NOT_FOUND,
    data: null,
    metadata: {
      executionTime: 200,
      timestamp: new Date().toISOString(),
      source: 'missing-resource',
      connector: 'TestConnector',
    },
    error: {
      code: 'RESOURCE_NOT_FOUND',
      message: 'Requested resource could not be found',
      details: { resource: 'missing-resource' },
      retryable: false,
    },
  } as ResponseEnvelope<null>,

  unauthorized: {
    requestId: 'error-004',
    success: false,
    status: ResponseStatus.UNAUTHORIZED,
    data: null,
    metadata: {
      executionTime: 150,
      timestamp: new Date().toISOString(),
      source: 'protected-resource',
      connector: 'TestConnector',
    },
    error: {
      code: 'AUTHENTICATION_REQUIRED',
      message: 'Valid authentication credentials are required',
      details: { authType: 'bearer' },
      retryable: false,
    },
  } as ResponseEnvelope<null>,
};

// Mock data for trend records
export const mockTrendRecords = {
  valid: {
    id: 'trend-001',
    platform: 'twitter',
    category: 'technology',
    language: 'en',
    region: 'US',
    title: 'AI Breakthrough: New Quantum Computing Algorithm',
    content:
      'Scientists announce revolutionary quantum computing algorithm that could solve complex optimization problems 1000x faster.',
    url: 'https://twitter.com/tech_news/status/12345',
    author: '@tech_news',
    timestamp: new Date('2024-01-15T10:30:00Z'),
    ingestedAt: new Date(),
    engagementCount: 1500,
    viewCount: 25000,
    shareCount: 350,
    contentHash: 'abc123def456',
    similarityHash: '789xyz',
    qualityScore: 0.85,
    freshnessScore: 0.95,
    anomalyScore: 0.1,
    entities: [
      {
        name: 'Quantum Computing',
        type: 'topic' as const,
        confidence: 0.95,
        aliases: ['Quantum Computing', 'QC'],
        metadata: { category: 'technology' },
      },
      {
        name: 'AI',
        type: 'topic' as const,
        confidence: 0.88,
        aliases: ['AI', 'Artificial Intelligence'],
        metadata: { category: 'technology' },
      },
    ],
    anomalies: [],
    metadata: {
      extractedKeywords: ['AI', 'quantum', 'algorithm', 'breakthrough'],
      sentiment: 'positive',
      confidence: 0.9,
    },
    rawData: {
      originalText: 'Full original tweet text...',
      apiResponse: { user: 'tech_news', created_at: '2024-01-15T10:30:00Z' },
    },
  },

  withAnomalies: {
    id: 'trend-002',
    platform: 'reddit',
    category: 'politics',
    language: 'en',
    region: 'US',
    title: 'Breaking: Major Political Development',
    content: 'Suspicious political content with unusual engagement patterns.',
    timestamp: new Date('2024-01-15T12:00:00Z'),
    ingestedAt: new Date(),
    engagementCount: 50000,
    viewCount: 1000000,
    shareCount: 15000,
    contentHash: 'def456ghi789',
    similarityHash: 'uvw123',
    qualityScore: 0.45,
    freshnessScore: 0.99,
    anomalyScore: 0.85,
    entities: [],
    anomalies: [
      {
        type: 'engagement_spike' as const,
        severity: 0.9,
        confidence: 0.88,
        description: 'Unusual engagement spike detected - 10x normal rate',
        metadata: { normalRate: 500, currentRate: 5000, multiplier: 10 },
      },
      {
        type: 'coordinated_behavior' as const,
        severity: 0.7,
        confidence: 0.75,
        description: 'Potential coordinated sharing pattern detected',
        metadata: { suspiciousAccounts: 25, timeWindow: 300 },
      },
    ],
    metadata: {
      flags: ['suspicious_engagement', 'needs_review'],
      reviewRequired: true,
    },
    rawData: {
      subreddit: 'politics',
      score: 15000,
      comments: 2500,
    },
  },

  lowQuality: {
    id: 'trend-003',
    platform: 'tiktok',
    category: 'entertainment',
    language: 'en',
    region: 'US',
    title: 'short vid',
    content: 'lol this is funny 😂😂😂',
    timestamp: new Date('2024-01-15T14:00:00Z'),
    ingestedAt: new Date(),
    engagementCount: 10,
    viewCount: 100,
    shareCount: 2,
    contentHash: 'ghi789jkl012',
    similarityHash: 'rst456',
    qualityScore: 0.15,
    freshnessScore: 0.85,
    anomalyScore: 0.05,
    entities: [],
    anomalies: [
      {
        type: 'low_quality_content' as const,
        severity: 0.6,
        confidence: 0.82,
        description: 'Content quality below threshold',
        metadata: {
          reasons: ['short_text', 'informal_language', 'low_engagement'],
        },
      },
    ],
    metadata: {
      flags: ['low_quality', 'auto_reject'],
      qualityIssues: ['insufficient_content', 'poor_language'],
    },
    rawData: {
      videoLength: 15,
      hashtags: ['#funny', '#lol'],
      effects: ['comedy_filter'],
    },
  },
};

// Test helper utilities
export const testHelpers = {
  createMockConnectorRequest: (
    overrides: Partial<ConnectorRequest> = {}
  ): ConnectorRequest => ({
    id: 'test-' + Math.random().toString(36).substr(2, 9),
    type: ConnectorRequestType.FETCH,
    target: 'test-target',
    parameters: {},
    config: {
      timeout: 5000,
      maxRetries: 2,
      retryDelay: 1000,
    },
    metadata: {
      requestedAt: new Date().toISOString(),
      correlationId: 'test-correlation',
    },
    ...overrides,
  }),

  createMockResponse: <T>(
    data: T,
    overrides: Partial<ResponseEnvelope<T>> = {}
  ): ResponseEnvelope<T> => ({
    requestId: 'test-request',
    success: true,
    status: ResponseStatus.SUCCESS,
    data,
    metadata: {
      executionTime: 100,
      timestamp: new Date().toISOString(),
      source: 'test-source',
      connector: 'TestConnector',
    },
    ...overrides,
  }),

  delay: (ms: number): Promise<void> =>
    new Promise(resolve => setTimeout(resolve, ms)),

  generateRandomId: (): string => Math.random().toString(36).substr(2, 9),

  createTestDatabase: async (): Promise<void> => {
    // Mock database setup for tests
    console.log('Setting up test database...');
  },

  cleanupTestDatabase: async (): Promise<void> => {
    // Mock database cleanup for tests
    console.log('Cleaning up test database...');
  },
};
