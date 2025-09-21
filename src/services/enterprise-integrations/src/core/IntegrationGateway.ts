import { EventEmitter } from 'events';
import {
  IntegrationProvider,
  IntegrationConnection,
  APIGatewayRequest,
  APIGatewayResponse,
  APIGatewayRule,
  RuleCondition,
  RuleAction,
  SyncOperation,
  IntegrationMetrics,
} from '@/types/integration';
import { Logger } from '@/utils/logger';
import { RedisClient } from '@/utils/redis';
import { RateLimiter } from '@/utils/rate-limiter';
import { SecurityManager } from '@/security/SecurityManager';
import { MetricsCollector } from '@/monitoring/MetricsCollector';
import { v4 as uuidv4 } from 'uuid';
import axios, { AxiosRequestConfig, AxiosResponse } from 'axios';
import * as crypto from 'crypto';

interface GatewayConfig {
  maxConcurrentRequests: number;
  requestTimeout: number;
  enableCaching: boolean;
  cacheTimeout: number;
  enableMetrics: boolean;
  enableSecurity: boolean;
  enableRateLimit: boolean;
  defaultRateLimit: {
    requests: number;
    window: number;
  };
}

interface RequestContext {
  requestId: string;
  userId: string;
  workspaceId: string;
  providerId: string;
  connectionId: string;
  startTime: Date;
  metadata: Record<string, unknown>;
}

interface CacheEntry {
  data: unknown;
  timestamp: Date;
  ttl: number;
  etag?: string;
}

export class IntegrationGateway extends EventEmitter {
  private logger: Logger;
  private redis: RedisClient;
  private rateLimiter: RateLimiter;
  private securityManager: SecurityManager;
  private metricsCollector: MetricsCollector;
  private config: GatewayConfig;

  private providers: Map<string, IntegrationProvider> = new Map();
  private connections: Map<string, IntegrationConnection> = new Map();
  private rules: Map<string, APIGatewayRule> = new Map();
  private cache: Map<string, CacheEntry> = new Map();
  private activeRequests: Map<string, RequestContext> = new Map();

  constructor(config: Partial<GatewayConfig> = {}) {
    super();

    this.config = {
      maxConcurrentRequests: 1000,
      requestTimeout: 30000,
      enableCaching: true,
      cacheTimeout: 300000, // 5 minutes
      enableMetrics: true,
      enableSecurity: true,
      enableRateLimit: true,
      defaultRateLimit: {
        requests: 100,
        window: 60000, // 1 minute
      },
      ...config,
    };

    this.logger = new Logger('IntegrationGateway');
    this.redis = new RedisClient();
    this.rateLimiter = new RateLimiter();
    this.securityManager = new SecurityManager();
    this.metricsCollector = new MetricsCollector();

    this.initializeGateway();
  }

  private async initializeGateway(): Promise<void> {
    try {
      // Initialize components
      await this.redis.connect();
      await this.securityManager.initialize();
      await this.metricsCollector.initialize();

      // Load providers and connections
      await this.loadProviders();
      await this.loadConnections();
      await this.loadRules();

      // Setup cleanup tasks
      this.setupCleanupTasks();

      this.logger.info('Integration Gateway initialized successfully');
      this.emit('gateway_initialized');
    } catch (error) {
      this.logger.error('Failed to initialize Integration Gateway:', error);
      throw error;
    }
  }

  // Provider Management
  async registerProvider(provider: IntegrationProvider): Promise<void> {
    try {
      this.validateProvider(provider);
      this.providers.set(provider.id, provider);

      // Store in Redis for persistence
      await this.redis.set(`provider:${provider.id}`, JSON.stringify(provider));

      this.logger.info(`Provider registered: ${provider.name}`, {
        providerId: provider.id,
      });
      this.emit('provider_registered', { provider });
    } catch (error) {
      this.logger.error('Failed to register provider:', error);
      throw error;
    }
  }

  async unregisterProvider(providerId: string): Promise<void> {
    const provider = this.providers.get(providerId);
    if (!provider) {
      throw new Error(`Provider not found: ${providerId}`);
    }

    // Deactivate all connections for this provider
    const providerConnections = Array.from(this.connections.values()).filter(
      conn => conn.providerId === providerId
    );

    for (const connection of providerConnections) {
      await this.deactivateConnection(connection.id);
    }

    this.providers.delete(providerId);
    await this.redis.del(`provider:${providerId}`);

    this.logger.info(`Provider unregistered: ${providerId}`);
    this.emit('provider_unregistered', { providerId });
  }

  // Connection Management
  async createConnection(connection: IntegrationConnection): Promise<void> {
    try {
      this.validateConnection(connection);

      // Test connection
      const testResult = await this.testConnection(connection);
      if (!testResult.success) {
        throw new Error(`Connection test failed: ${testResult.error}`);
      }

      connection.status = 'active';
      connection.lastSync = new Date();
      this.connections.set(connection.id, connection);

      // Store encrypted credentials
      await this.storeConnectionCredentials(connection);

      this.logger.info(`Connection created: ${connection.name}`, {
        connectionId: connection.id,
      });
      this.emit('connection_created', { connection });
    } catch (error) {
      this.logger.error('Failed to create connection:', error);
      throw error;
    }
  }

  async updateConnection(
    connectionId: string,
    updates: Partial<IntegrationConnection>
  ): Promise<void> {
    const connection = this.connections.get(connectionId);
    if (!connection) {
      throw new Error(`Connection not found: ${connectionId}`);
    }

    // Apply updates
    Object.assign(connection, updates, { updatedAt: new Date() });

    // Test updated connection if credentials changed
    if (updates.credentials) {
      const testResult = await this.testConnection(connection);
      if (!testResult.success) {
        throw new Error(`Updated connection test failed: ${testResult.error}`);
      }
    }

    this.connections.set(connectionId, connection);
    await this.storeConnectionCredentials(connection);

    this.logger.info(`Connection updated: ${connectionId}`);
    this.emit('connection_updated', { connection });
  }

  async deactivateConnection(connectionId: string): Promise<void> {
    const connection = this.connections.get(connectionId);
    if (!connection) {
      throw new Error(`Connection not found: ${connectionId}`);
    }

    connection.status = 'inactive';
    connection.updatedAt = new Date();

    this.connections.set(connectionId, connection);
    await this.storeConnectionCredentials(connection);

    this.logger.info(`Connection deactivated: ${connectionId}`);
    this.emit('connection_deactivated', { connection });
  }

  // API Gateway Request Processing
  async processRequest(
    request: APIGatewayRequest
  ): Promise<APIGatewayResponse> {
    const startTime = Date.now();

    try {
      // Check concurrent request limit
      if (this.activeRequests.size >= this.config.maxConcurrentRequests) {
        throw new Error('Too many concurrent requests');
      }

      // Create request context
      const context: RequestContext = {
        requestId: request.id,
        userId: request.userId,
        workspaceId: '', // Would be extracted from request
        providerId: request.providerId,
        connectionId: request.connectionId,
        startTime: new Date(),
        metadata: {},
      };

      this.activeRequests.set(request.id, context);
      this.emit('request_started', { request, context });

      // Apply gateway rules
      const processedRequest = await this.applyGatewayRules(request, context);

      // Security validation
      if (this.config.enableSecurity) {
        await this.securityManager.validateRequest(processedRequest, context);
      }

      // Rate limiting
      if (this.config.enableRateLimit) {
        await this.checkRateLimit(processedRequest, context);
      }

      // Check cache
      let response: APIGatewayResponse;
      const cacheKey = this.generateCacheKey(processedRequest);

      if (this.config.enableCaching && processedRequest.method === 'GET') {
        const cachedResponse = await this.getCachedResponse(cacheKey);
        if (cachedResponse) {
          response = cachedResponse;
          response.cached = true;
          this.logger.debug('Serving cached response', {
            requestId: request.id,
          });
        }
      }

      // Forward request to provider if not cached
      if (!response!) {
        response = await this.forwardRequest(processedRequest, context);

        // Cache successful GET responses
        if (
          this.config.enableCaching &&
          processedRequest.method === 'GET' &&
          response.status < 400
        ) {
          await this.cacheResponse(cacheKey, response);
        }
      }

      // Collect metrics
      if (this.config.enableMetrics) {
        await this.recordMetrics(
          request,
          response,
          Date.now() - startTime,
          context
        );
      }

      this.logger.info('Request processed successfully', {
        requestId: request.id,
        status: response.status,
        duration: Date.now() - startTime,
        cached: response.cached,
      });

      this.emit('request_completed', { request, response, context });
      return response;
    } catch (error) {
      const errorResponse: APIGatewayResponse = {
        requestId: request.id,
        status: error.statusCode || 500,
        headers: {},
        body: { error: error.message },
        duration: Date.now() - startTime,
        cached: false,
        timestamp: new Date(),
      };

      this.logger.error('Request processing failed', {
        requestId: request.id,
        error: error.message,
        duration: Date.now() - startTime,
      });

      this.emit('request_failed', { request, error, response: errorResponse });
      return errorResponse;
    } finally {
      this.activeRequests.delete(request.id);
    }
  }

  // Gateway Rules Processing
  private async applyGatewayRules(
    request: APIGatewayRequest,
    context: RequestContext
  ): Promise<APIGatewayRequest> {
    let processedRequest = { ...request };

    // Get applicable rules sorted by priority
    const applicableRules = Array.from(this.rules.values())
      .filter(rule => rule.isActive)
      .filter(rule =>
        this.evaluateRuleConditions(rule.conditions, request, context)
      )
      .sort((a, b) => a.priority - b.priority);

    // Apply rules in order
    for (const rule of applicableRules) {
      processedRequest = await this.applyRuleActions(
        rule.actions,
        processedRequest,
        context
      );
    }

    return processedRequest;
  }

  private evaluateRuleConditions(
    conditions: RuleCondition[],
    request: APIGatewayRequest,
    context: RequestContext
  ): boolean {
    return conditions.every(condition => {
      const fieldValue = this.getFieldValue(condition.field, request, context);
      return this.evaluateCondition(condition, fieldValue);
    });
  }

  private getFieldValue(
    field: string,
    request: APIGatewayRequest,
    context: RequestContext
  ): unknown {
    const parts = field.split('.');
    let value: unknown = { request, context };

    for (const part of parts) {
      if (value && typeof value === 'object') {
        value = value[part];
      } else {
        return undefined;
      }
    }

    return value;
  }

  private evaluateCondition(condition: RuleCondition, value: unknown): boolean {
    switch (condition.operator) {
      case 'equals':
        return value === condition.value;
      case 'contains':
        return typeof value === 'string' && value.includes(condition.value);
      case 'startsWith':
        return typeof value === 'string' && value.startsWith(condition.value);
      case 'regex':
        return (
          typeof value === 'string' && new RegExp(condition.value).test(value)
        );
      case 'exists':
        return value !== undefined && value !== null;
      default:
        return false;
    }
  }

  private async applyRuleActions(
    actions: RuleAction[],
    request: APIGatewayRequest,
    context: RequestContext
  ): Promise<APIGatewayRequest> {
    let processedRequest = { ...request };

    for (const action of actions) {
      switch (action.type) {
        case 'transform':
          processedRequest = this.transformRequest(
            processedRequest,
            action.configuration
          );
          break;
        case 'filter':
          processedRequest = this.filterRequest(
            processedRequest,
            action.configuration
          );
          break;
        case 'rate_limit':
          await this.applyCustomRateLimit(
            processedRequest,
            context,
            action.configuration
          );
          break;
        case 'block':
          throw new Error(
            `Request blocked by rule: ${action.configuration.reason || 'Blocked'}`
          );
      }
    }

    return processedRequest;
  }

  private transformRequest(
    request: APIGatewayRequest,
    config: unknown
  ): APIGatewayRequest {
    const transformed = { ...request };

    if (config.headers) {
      transformed.headers = { ...transformed.headers, ...config.headers };
    }

    if (config.query) {
      transformed.query = { ...transformed.query, ...config.query };
    }

    if (config.pathTransform) {
      transformed.path = transformed.path.replace(
        new RegExp(config.pathTransform.pattern),
        config.pathTransform.replacement
      );
    }

    return transformed;
  }

  private filterRequest(
    request: APIGatewayRequest,
    config: unknown
  ): APIGatewayRequest {
    const filtered = { ...request };

    if (config.removeHeaders) {
      for (const header of config.removeHeaders) {
        delete filtered.headers[header];
      }
    }

    if (config.removeQueryParams) {
      for (const param of config.removeQueryParams) {
        delete filtered.query[param];
      }
    }

    return filtered;
  }

  // Request Forwarding
  private async forwardRequest(
    request: APIGatewayRequest,
    context: RequestContext
  ): Promise<APIGatewayResponse> {
    const provider = this.providers.get(request.providerId);
    const connection = this.connections.get(request.connectionId);

    if (!provider) {
      throw new Error(`Provider not found: ${request.providerId}`);
    }

    if (!connection) {
      throw new Error(`Connection not found: ${request.connectionId}`);
    }

    if (connection.status !== 'active') {
      throw new Error(`Connection is not active: ${request.connectionId}`);
    }

    // Build request configuration
    const axiosConfig: AxiosRequestConfig = {
      method: request.method as any,
      url: this.buildProviderUrl(provider, request.path),
      headers: await this.buildProviderHeaders(
        provider,
        connection,
        request.headers
      ),
      params: request.query,
      data: request.body,
      timeout: this.config.requestTimeout,
      validateStatus: () => true, // Don't throw on HTTP error status
    };

    const startTime = Date.now();

    try {
      this.logger.debug('Forwarding request to provider', {
        providerId: provider.id,
        method: request.method,
        url: axiosConfig.url,
      });

      const axiosResponse: AxiosResponse = await axios(axiosConfig);

      const response: APIGatewayResponse = {
        requestId: request.id,
        status: axiosResponse.status,
        headers: axiosResponse.headers,
        body: axiosResponse.data,
        duration: Date.now() - startTime,
        cached: false,
        timestamp: new Date(),
      };

      // Handle provider-specific response processing
      return await this.processProviderResponse(provider, response);
    } catch (error) {
      if (error.response) {
        // HTTP error response
        return {
          requestId: request.id,
          status: error.response.status,
          headers: error.response.headers || {},
          body: error.response.data || { error: 'Request failed' },
          duration: Date.now() - startTime,
          cached: false,
          timestamp: new Date(),
        };
      } else {
        // Network or other error
        throw new Error(`Provider request failed: ${error.message}`);
      }
    }
  }

  private buildProviderUrl(
    provider: IntegrationProvider,
    path: string
  ): string {
    const baseUrl = provider.metadata.baseUrl.replace(/\/$/, '');
    const cleanPath = path.replace(/^\//, '');
    return `${baseUrl}/${cleanPath}`;
  }

  private async buildProviderHeaders(
    provider: IntegrationProvider,
    connection: IntegrationConnection,
    requestHeaders: Record<string, string>
  ): Promise<Record<string, string>> {
    const headers = { ...requestHeaders };

    // Add authentication headers
    if (
      provider.authentication.type === 'bearer_token' &&
      connection.credentials.accessToken
    ) {
      headers['Authorization'] = `Bearer ${connection.credentials.accessToken}`;
    } else if (
      provider.authentication.type === 'api_key' &&
      connection.credentials.apiKey
    ) {
      headers['X-API-Key'] = connection.credentials.apiKey;
    } else if (
      provider.authentication.type === 'basic' &&
      connection.credentials.apiKey &&
      connection.credentials.secret
    ) {
      const credentials = Buffer.from(
        `${connection.credentials.apiKey}:${connection.credentials.secret}`
      ).toString('base64');
      headers['Authorization'] = `Basic ${credentials}`;
    }

    // Add common headers
    headers['User-Agent'] = 'PAKE-Integration-Gateway/1.0';
    headers['Accept'] = headers['Accept'] || 'application/json';
    headers['Content-Type'] = headers['Content-Type'] || 'application/json';

    return headers;
  }

  private async processProviderResponse(
    provider: IntegrationProvider,
    response: APIGatewayResponse
  ): Promise<APIGatewayResponse> {
    // Provider-specific response processing could be added here
    return response;
  }

  // Caching
  private generateCacheKey(request: APIGatewayRequest): string {
    const keyParts = [
      request.providerId,
      request.connectionId,
      request.method,
      request.path,
      JSON.stringify(request.query),
    ];

    return crypto.createHash('sha256').update(keyParts.join(':')).digest('hex');
  }

  private async getCachedResponse(
    cacheKey: string
  ): Promise<APIGatewayResponse | null> {
    const cached = this.cache.get(cacheKey);

    if (cached && Date.now() - cached.timestamp.getTime() < cached.ttl) {
      return cached.data;
    } else {
      this.cache.delete(cacheKey);
      return null;
    }
  }

  private async cacheResponse(
    cacheKey: string,
    response: APIGatewayResponse
  ): Promise<void> {
    const cacheEntry: CacheEntry = {
      data: response,
      timestamp: new Date(),
      ttl: this.config.cacheTimeout,
      etag: response.headers['etag'],
    };

    this.cache.set(cacheKey, cacheEntry);

    // Also store in Redis for shared cache
    await this.redis.setex(
      `cache:${cacheKey}`,
      Math.floor(this.config.cacheTimeout / 1000),
      JSON.stringify(cacheEntry)
    );
  }

  // Rate Limiting
  private async checkRateLimit(
    request: APIGatewayRequest,
    context: RequestContext
  ): Promise<void> {
    const provider = this.providers.get(request.providerId);
    if (!provider) return;

    const rateLimitKey = `rate_limit:${request.providerId}:${context.userId}`;
    const isAllowed = await this.rateLimiter.checkLimit(
      rateLimitKey,
      provider.rateLimit.requestsPerMinute,
      60000 // 1 minute window
    );

    if (!isAllowed) {
      const error = new Error('Rate limit exceeded');
      (error as any).statusCode = 429;
      throw error;
    }
  }

  private async applyCustomRateLimit(
    request: APIGatewayRequest,
    context: RequestContext,
    config: unknown
  ): Promise<void> {
    const rateLimitKey = `custom_rate_limit:${config.key || 'default'}:${context.userId}`;
    const isAllowed = await this.rateLimiter.checkLimit(
      rateLimitKey,
      config.requests || this.config.defaultRateLimit.requests,
      config.window || this.config.defaultRateLimit.window
    );

    if (!isAllowed) {
      const error = new Error(
        `Custom rate limit exceeded: ${config.message || 'Too many requests'}`
      );
      (error as any).statusCode = 429;
      throw error;
    }
  }

  // Connection Testing
  private async testConnection(
    connection: IntegrationConnection
  ): Promise<{ success: boolean; error?: string }> {
    const provider = this.providers.get(connection.providerId);
    if (!provider) {
      return { success: false, error: 'Provider not found' };
    }

    try {
      // Create a test request
      const testRequest: APIGatewayRequest = {
        id: uuidv4(),
        method: 'GET',
        path: '/health', // Most APIs have a health endpoint
        headers: {},
        query: {},
        providerId: connection.providerId,
        connectionId: connection.id,
        userId: connection.userId,
        timestamp: new Date(),
      };

      const testContext: RequestContext = {
        requestId: testRequest.id,
        userId: connection.userId,
        workspaceId: connection.workspaceId,
        providerId: connection.providerId,
        connectionId: connection.id,
        startTime: new Date(),
        metadata: { test: true },
      };

      // Try to make a simple request
      const response = await this.forwardRequest(testRequest, testContext);

      // Consider 2xx and 4xx as successful (connection works, might just be wrong endpoint)
      return { success: response.status < 500 };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  // Metrics Collection
  private async recordMetrics(
    request: APIGatewayRequest,
    response: APIGatewayResponse,
    duration: number,
    context: RequestContext
  ): Promise<void> {
    const metrics: Partial<IntegrationMetrics> = {
      providerId: request.providerId,
      connectionId: request.connectionId,
      period: 'minute',
      timestamp: new Date(),
    };

    await this.metricsCollector.recordRequest(
      request,
      response,
      duration,
      context
    );
  }

  // Validation
  private validateProvider(provider: IntegrationProvider): void {
    if (!provider.id || !provider.name || !provider.category) {
      throw new Error('Provider must have id, name, and category');
    }

    if (!provider.metadata.baseUrl) {
      throw new Error('Provider must have a base URL');
    }

    if (!provider.authentication) {
      throw new Error('Provider must have authentication configuration');
    }
  }

  private validateConnection(connection: IntegrationConnection): void {
    if (!connection.id || !connection.providerId || !connection.userId) {
      throw new Error('Connection must have id, providerId, and userId');
    }

    const provider = this.providers.get(connection.providerId);
    if (!provider) {
      throw new Error(`Provider not found: ${connection.providerId}`);
    }

    if (
      !connection.credentials ||
      Object.keys(connection.credentials).length === 0
    ) {
      throw new Error('Connection must have credentials');
    }
  }

  // Storage
  private async storeConnectionCredentials(
    connection: IntegrationConnection
  ): Promise<void> {
    // Encrypt and store credentials securely
    const encryptedCredentials = await this.securityManager.encryptCredentials(
      connection.credentials
    );
    const connectionData = {
      ...connection,
      credentials: encryptedCredentials,
    };

    await this.redis.set(
      `connection:${connection.id}`,
      JSON.stringify(connectionData)
    );
  }

  private async loadProviders(): Promise<void> {
    const keys = await this.redis.keys('provider:*');

    for (const key of keys) {
      try {
        const providerData = await this.redis.get(key);
        if (providerData) {
          const provider = JSON.parse(providerData);
          this.providers.set(provider.id, provider);
        }
      } catch (error) {
        this.logger.error(`Failed to load provider from ${key}:`, error);
      }
    }

    this.logger.info(`Loaded ${this.providers.size} providers`);
  }

  private async loadConnections(): Promise<void> {
    const keys = await this.redis.keys('connection:*');

    for (const key of keys) {
      try {
        const connectionData = await this.redis.get(key);
        if (connectionData) {
          const connection = JSON.parse(connectionData);
          // Decrypt credentials
          connection.credentials =
            await this.securityManager.decryptCredentials(
              connection.credentials
            );
          this.connections.set(connection.id, connection);
        }
      } catch (error) {
        this.logger.error(`Failed to load connection from ${key}:`, error);
      }
    }

    this.logger.info(`Loaded ${this.connections.size} connections`);
  }

  private async loadRules(): Promise<void> {
    const keys = await this.redis.keys('rule:*');

    for (const key of keys) {
      try {
        const ruleData = await this.redis.get(key);
        if (ruleData) {
          const rule = JSON.parse(ruleData);
          this.rules.set(rule.id, rule);
        }
      } catch (error) {
        this.logger.error(`Failed to load rule from ${key}:`, error);
      }
    }

    this.logger.info(`Loaded ${this.rules.size} rules`);
  }

  // Cleanup
  private setupCleanupTasks(): void {
    // Clean up expired cache entries
    setInterval(() => {
      const now = Date.now();
      for (const [key, entry] of this.cache.entries()) {
        if (now - entry.timestamp.getTime() > entry.ttl) {
          this.cache.delete(key);
        }
      }
    }, 60000); // Every minute

    // Clean up old active requests
    setInterval(() => {
      const cutoff = new Date(Date.now() - 300000); // 5 minutes ago
      for (const [requestId, context] of this.activeRequests.entries()) {
        if (context.startTime < cutoff) {
          this.activeRequests.delete(requestId);
        }
      }
    }, 300000); // Every 5 minutes
  }

  // Public API
  getProvider(providerId: string): IntegrationProvider | undefined {
    return this.providers.get(providerId);
  }

  getConnection(connectionId: string): IntegrationConnection | undefined {
    return this.connections.get(connectionId);
  }

  getProviders(): IntegrationProvider[] {
    return Array.from(this.providers.values());
  }

  getConnections(userId?: string): IntegrationConnection[] {
    const connections = Array.from(this.connections.values());
    return userId
      ? connections.filter(conn => conn.userId === userId)
      : connections;
  }

  getActiveRequests(): RequestContext[] {
    return Array.from(this.activeRequests.values());
  }

  getGatewayStats(): unknown {
    return {
      providers: this.providers.size,
      connections: this.connections.size,
      rules: this.rules.size,
      activeRequests: this.activeRequests.size,
      cacheSize: this.cache.size,
    };
  }

  async shutdown(): Promise<void> {
    this.logger.info('Shutting down Integration Gateway...');

    // Wait for active requests to complete (with timeout)
    const timeout = 30000; // 30 seconds
    const startTime = Date.now();

    while (this.activeRequests.size > 0 && Date.now() - startTime < timeout) {
      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    if (this.activeRequests.size > 0) {
      this.logger.warn(
        `Shutdown with ${this.activeRequests.size} active requests remaining`
      );
    }

    // Close connections
    await this.redis.disconnect();

    // Clear all data
    this.providers.clear();
    this.connections.clear();
    this.rules.clear();
    this.cache.clear();
    this.activeRequests.clear();

    this.emit('gateway_shutdown');
    this.logger.info('Integration Gateway shutdown complete');
  }
}

export default IntegrationGateway;
