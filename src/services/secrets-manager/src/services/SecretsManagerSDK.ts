/**
 * PAKE Secrets Manager SDK
 * Application integration SDK for seamless secrets management
 */

import { EventEmitter } from 'events';
import { VaultService } from './VaultService';
import { HSMService } from './HSMService';
import { EncryptionService } from './EncryptionService';
import {
  SecretsManagerConfig,
  Secret,
  SecretMetadata,
  EncryptedSecret,
  SecretType,
  SecretClassification,
  RotationPolicy,
} from '../types/secrets.types';
import { Logger } from '../utils/logger';
import { SecretCache } from '../cache/SecretCache';

interface SDKOptions {
  cacheEnabled?: boolean;
  cacheTTL?: number;
  retryAttempts?: number;
  retryDelay?: number;
  validateSecrets?: boolean;
  auditEnabled?: boolean;
}

interface SecretRequest {
  path: string;
  version?: number;
  environment?: string;
  ttl?: number;
  metadata?: Record<string, any>;
}

interface BulkSecretResponse {
  secrets: Map<string, Secret | null>;
  errors: Map<string, Error>;
  fromCache: Set<string>;
}

export class SecretsManagerSDK extends EventEmitter {
  private readonly logger = new Logger('SecretsManagerSDK');
  private readonly config: SecretsManagerConfig;
  private readonly options: SDKOptions;

  private vaultService: VaultService;
  private hsmService?: HSMService;
  private encryptionService: EncryptionService;
  private cache?: SecretCache;

  private isInitialized = false;
  private secretUsageStats = new Map<
    string,
    { accessCount: number; lastAccessed: Date }
  >();

  constructor(config: SecretsManagerConfig, options: SDKOptions = {}) {
    super();
    this.config = config;
    this.options = {
      cacheEnabled: true,
      cacheTTL: 300, // 5 minutes
      retryAttempts: 3,
      retryDelay: 1000,
      validateSecrets: true,
      auditEnabled: true,
      ...options,
    };
  }

  /**
   * Initialize the SDK
   */
  async initialize(): Promise<void> {
    try {
      // Initialize services
      this.vaultService = new VaultService(this.config.vault);
      await this.vaultService.initialize();

      if (this.config.hsm?.enabled) {
        this.hsmService = new HSMService(this.config.hsm);
        await this.hsmService.initialize();
      }

      this.encryptionService = new EncryptionService(
        this.config.encryption,
        this.vaultService,
        this.hsmService
      );
      await this.encryptionService.initialize();

      // Initialize cache if enabled
      if (this.options.cacheEnabled) {
        this.cache = new SecretCache({
          ttl: this.options.cacheTTL!,
          maxSize: 1000,
          encryption: true,
        });
      }

      // Setup event forwarding
      this.setupEventForwarding();

      this.isInitialized = true;
      this.logger.info('Secrets Manager SDK initialized successfully');
    } catch (error) {
      this.logger.error('Failed to initialize Secrets Manager SDK', {
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Get a secret by path
   */
  async getSecret(
    pathOrRequest: string | SecretRequest
  ): Promise<Secret | null> {
    this.ensureInitialized();

    const request: SecretRequest =
      typeof pathOrRequest === 'string'
        ? { path: pathOrRequest }
        : pathOrRequest;

    const cacheKey = this.getCacheKey(request);

    try {
      // Check cache first
      if (this.cache) {
        const cached = await this.cache.get(cacheKey);
        if (cached) {
          this.updateUsageStats(request.path);
          this.emit('secretRetrieved', { path: request.path, fromCache: true });
          return cached;
        }
      }

      // Retrieve from Vault with retry
      const secret = await this.retryOperation(() =>
        this.vaultService.getSecret(request.path)
      );

      if (!secret) {
        this.logger.debug('Secret not found', { path: request.path });
        return null;
      }

      // Validate secret if enabled
      if (this.options.validateSecrets) {
        this.validateSecret(secret);
      }

      // Cache the secret
      if (this.cache) {
        await this.cache.set(cacheKey, secret, request.ttl);
      }

      this.updateUsageStats(request.path);
      this.emit('secretRetrieved', { path: request.path, fromCache: false });

      return secret;
    } catch (error) {
      this.logger.error('Failed to get secret', {
        path: request.path,
        error: error.message,
      });
      this.emit('secretError', {
        path: request.path,
        error: error.message,
        operation: 'get',
      });
      throw error;
    }
  }

  /**
   * Get multiple secrets in bulk
   */
  async getBulkSecrets(requests: SecretRequest[]): Promise<BulkSecretResponse> {
    this.ensureInitialized();

    const response: BulkSecretResponse = {
      secrets: new Map(),
      errors: new Map(),
      fromCache: new Set(),
    };

    // Process requests concurrently
    const promises = requests.map(async request => {
      try {
        const secret = await this.getSecret(request);
        response.secrets.set(request.path, secret);

        // Check if it came from cache
        if (this.cache && (await this.cache.has(this.getCacheKey(request)))) {
          response.fromCache.add(request.path);
        }
      } catch (error) {
        response.errors.set(request.path, error);
      }
    });

    await Promise.allSettled(promises);

    this.emit('bulkSecretsRetrieved', {
      requestCount: requests.length,
      successCount: response.secrets.size,
      errorCount: response.errors.size,
      cacheHits: response.fromCache.size,
    });

    return response;
  }

  /**
   * Store a secret
   */
  async storeSecret(
    path: string,
    value: Record<string, any>,
    metadata?: Partial<SecretMetadata>
  ): Promise<void> {
    this.ensureInitialized();

    try {
      // Validate sensitive data
      if (this.containsSensitiveData(value)) {
        this.logger.warn('Storing potentially sensitive data', { path });
      }

      await this.retryOperation(() =>
        this.vaultService.storeSecret(path, value, metadata)
      );

      // Invalidate cache
      if (this.cache) {
        await this.cache.delete(path);
      }

      this.emit('secretStored', { path });
      this.logger.info('Secret stored successfully', { path });
    } catch (error) {
      this.logger.error('Failed to store secret', {
        path,
        error: error.message,
      });
      this.emit('secretError', {
        path,
        error: error.message,
        operation: 'store',
      });
      throw error;
    }
  }

  /**
   * Delete a secret
   */
  async deleteSecret(path: string): Promise<void> {
    this.ensureInitialized();

    try {
      await this.retryOperation(() => this.vaultService.deleteSecret(path));

      // Remove from cache
      if (this.cache) {
        await this.cache.delete(path);
      }

      // Remove usage stats
      this.secretUsageStats.delete(path);

      this.emit('secretDeleted', { path });
      this.logger.info('Secret deleted successfully', { path });
    } catch (error) {
      this.logger.error('Failed to delete secret', {
        path,
        error: error.message,
      });
      this.emit('secretError', {
        path,
        error: error.message,
        operation: 'delete',
      });
      throw error;
    }
  }

  /**
   * List secrets in a path
   */
  async listSecrets(path: string = ''): Promise<string[]> {
    this.ensureInitialized();

    try {
      const secrets = await this.retryOperation(() =>
        this.vaultService.listSecrets(path)
      );

      this.emit('secretsListed', { path, count: secrets.length });
      return secrets;
    } catch (error) {
      this.logger.error('Failed to list secrets', {
        path,
        error: error.message,
      });
      this.emit('secretError', {
        path,
        error: error.message,
        operation: 'list',
      });
      throw error;
    }
  }

  /**
   * Encrypt data using field-level encryption
   */
  async encryptField(
    data: string,
    keyId?: string,
    context?: Record<string, string>
  ): Promise<string> {
    this.ensureInitialized();

    try {
      const encrypted = await this.encryptionService.encryptField(
        data,
        keyId,
        context
      );

      this.emit('fieldEncrypted', { keyId, hasContext: !!context });
      return encrypted;
    } catch (error) {
      this.logger.error('Failed to encrypt field', {
        keyId,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Decrypt data using field-level encryption
   */
  async decryptField(
    encryptedData: string,
    context?: Record<string, string>
  ): Promise<string> {
    this.ensureInitialized();

    try {
      const decrypted = await this.encryptionService.decryptField(
        encryptedData,
        context
      );

      this.emit('fieldDecrypted', { hasContext: !!context });
      return decrypted;
    } catch (error) {
      this.logger.error('Failed to decrypt field', { error: error.message });
      throw error;
    }
  }

  /**
   * Get database credentials with automatic rotation
   */
  async getDatabaseCredentials(
    roleName: string
  ): Promise<{ username: string; REDACTED_SECRET: string; ttl: number }> {
    this.ensureInitialized();

    try {
      const credentials = await this.retryOperation(() =>
        this.vaultService.getDatabaseCredentials(roleName)
      );

      this.emit('databaseCredentialsRetrieved', {
        roleName,
        ttl: credentials.ttl,
      });

      return {
        username: credentials.username,
        REDACTED_SECRET: credentials.REDACTED_SECRET,
        ttl: credentials.ttl,
      };
    } catch (error) {
      this.logger.error('Failed to get database credentials', {
        roleName,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Get application configuration with secret resolution
   */
  async getAppConfig(configPath: string): Promise<Record<string, any>> {
    this.ensureInitialized();

    try {
      const config = await this.getSecret(configPath);
      if (!config) {
        throw new Error(`Configuration not found at path: ${configPath}`);
      }

      // Resolve nested secrets
      const resolvedConfig = await this.resolveNestedSecrets(
        config.value as Record<string, any>
      );

      this.emit('appConfigRetrieved', { configPath });
      return resolvedConfig;
    } catch (error) {
      this.logger.error('Failed to get app config', {
        configPath,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Create a typed secret accessor for specific paths
   */
  createTypedAccessor<T = Record<string, any>>(basePath: string) {
    return {
      get: async (subPath: string = ''): Promise<T | null> => {
        const fullPath = subPath ? `${basePath}/${subPath}` : basePath;
        const secret = await this.getSecret(fullPath);
        return (secret?.value as T) || null;
      },

      set: async (
        data: T,
        subPath: string = '',
        metadata?: Partial<SecretMetadata>
      ): Promise<void> => {
        const fullPath = subPath ? `${basePath}/${subPath}` : basePath;
        await this.storeSecret(fullPath, data as Record<string, any>, metadata);
      },

      delete: async (subPath: string = ''): Promise<void> => {
        const fullPath = subPath ? `${basePath}/${subPath}` : basePath;
        await this.deleteSecret(fullPath);
      },

      list: async (subPath: string = ''): Promise<string[]> => {
        const fullPath = subPath ? `${basePath}/${subPath}` : basePath;
        return await this.listSecrets(fullPath);
      },
    };
  }

  /**
   * Get secret usage statistics
   */
  getUsageStats(
    path?: string
  ): Map<string, { accessCount: number; lastAccessed: Date }> {
    if (path) {
      const stats = this.secretUsageStats.get(path);
      return stats ? new Map([[path, stats]]) : new Map();
    }
    return new Map(this.secretUsageStats);
  }

  /**
   * Clear cache
   */
  async clearCache(path?: string): Promise<void> {
    if (!this.cache) return;

    if (path) {
      await this.cache.delete(path);
    } else {
      await this.cache.clear();
    }

    this.emit('cacheCleared', { path });
  }

  /**
   * Preload secrets for performance optimization
   */
  async preloadSecrets(paths: string[]): Promise<void> {
    this.logger.info('Preloading secrets', { count: paths.length });

    const requests = paths.map(path => ({ path }));
    const response = await this.getBulkSecrets(requests);

    this.logger.info('Secrets preloaded', {
      successful: response.secrets.size,
      failed: response.errors.size,
    });
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<{
    status: string;
    details: Record<string, any>;
  }> {
    const health = {
      status: 'healthy',
      details: {
        vault: 'unknown',
        hsm: 'not_configured',
        cache: this.cache ? 'enabled' : 'disabled',
        initialized: this.isInitialized,
      },
    };

    try {
      // Check Vault health
      await this.vaultService.getHealth();
      health.details.vault = 'healthy';
    } catch (error) {
      health.details.vault = 'unhealthy';
      health.status = 'degraded';
    }

    try {
      // Check HSM health if configured
      if (this.hsmService) {
        await this.hsmService.getStatus();
        health.details.hsm = 'healthy';
      }
    } catch (error) {
      health.details.hsm = 'unhealthy';
      health.status = 'degraded';
    }

    return health;
  }

  /**
   * Private helper methods
   */

  private async retryOperation<T>(operation: () => Promise<T>): Promise<T> {
    let lastError: Error;

    for (let attempt = 1; attempt <= this.options.retryAttempts!; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error;

        if (attempt < this.options.retryAttempts!) {
          this.logger.debug('Operation failed, retrying', {
            attempt,
            maxAttempts: this.options.retryAttempts,
            error: error.message,
          });

          await this.sleep(this.options.retryDelay! * attempt);
        }
      }
    }

    throw lastError!;
  }

  private getCacheKey(request: SecretRequest): string {
    return `${request.path}:${request.version || 'latest'}:${request.environment || 'default'}`;
  }

  private validateSecret(secret: Secret): void {
    if (!secret.metadata.id || !secret.metadata.name) {
      throw new Error('Secret missing required metadata');
    }

    if (
      secret.metadata.expiresAt &&
      new Date(secret.metadata.expiresAt) < new Date()
    ) {
      throw new Error('Secret has expired');
    }

    // Additional validation rules can be added here
  }

  private containsSensitiveData(value: Record<string, any>): boolean {
    const sensitiveKeys = [
      'REDACTED_SECRET',
      'secret',
      'key',
      'token',
      'credential',
      'private',
      'confidential',
      'ssn',
      'credit_card',
    ];

    const checkObject = (obj: any, depth = 0): boolean => {
      if (depth > 3) return false; // Prevent infinite recursion

      for (const [key, val] of Object.entries(obj)) {
        if (
          sensitiveKeys.some(sensitive =>
            key.toLowerCase().includes(sensitive.toLowerCase())
          )
        ) {
          return true;
        }

        if (typeof val === 'object' && val !== null) {
          if (checkObject(val, depth + 1)) {
            return true;
          }
        }
      }

      return false;
    };

    return checkObject(value);
  }

  private async resolveNestedSecrets(
    config: Record<string, any>
  ): Promise<Record<string, any>> {
    const resolved: Record<string, any> = {};

    for (const [key, value] of Object.entries(config)) {
      if (typeof value === 'string' && value.startsWith('vault:')) {
        // Resolve vault reference
        const secretPath = value.replace('vault:', '');
        try {
          const secret = await this.getSecret(secretPath);
          resolved[key] = secret?.value;
        } catch (error) {
          this.logger.warn('Failed to resolve nested secret', {
            key,
            secretPath,
            error: error.message,
          });
          resolved[key] = null;
        }
      } else if (typeof value === 'object' && value !== null) {
        resolved[key] = await this.resolveNestedSecrets(value);
      } else {
        resolved[key] = value;
      }
    }

    return resolved;
  }

  private updateUsageStats(path: string): void {
    const stats = this.secretUsageStats.get(path) || {
      accessCount: 0,
      lastAccessed: new Date(),
    };
    stats.accessCount++;
    stats.lastAccessed = new Date();
    this.secretUsageStats.set(path, stats);
  }

  private setupEventForwarding(): void {
    // Forward events from services
    this.vaultService.on('secretStored', event =>
      this.emit('secretStored', event)
    );
    this.vaultService.on('secretAccessed', event =>
      this.emit('secretAccessed', event)
    );
    this.vaultService.on('keyRotated', event => this.emit('keyRotated', event));

    if (this.hsmService) {
      this.hsmService.on('hsmOperation', event =>
        this.emit('hsmOperation', event)
      );
    }
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private ensureInitialized(): void {
    if (!this.isInitialized) {
      throw new Error(
        'Secrets Manager SDK not initialized. Call initialize() first.'
      );
    }
  }

  /**
   * Close SDK and cleanup resources
   */
  async close(): Promise<void> {
    await this.vaultService.close();

    if (this.hsmService) {
      await this.hsmService.close();
    }

    if (this.cache) {
      await this.cache.close();
    }

    this.isInitialized = false;
    this.logger.info('Secrets Manager SDK closed');
  }
}
