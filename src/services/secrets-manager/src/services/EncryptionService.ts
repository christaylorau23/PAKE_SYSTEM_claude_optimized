/**
 * Encryption Service
 * Provides encryption at rest and field-level encryption for sensitive data
 */

import crypto from 'crypto';
import { promisify } from 'util';
import { VaultService } from './VaultService';
import { HSMService } from './HSMService';
import {
  EncryptionConfig,
  FieldEncryptionConfig,
  EncryptionKey,
  KeyPurpose,
  KeyStatus,
  SecretEvent,
  SecretEventType,
} from '../types/secrets.types';
import { Logger } from '../utils/logger';

interface EncryptionResult {
  ciphertext: string;
  keyId: string;
  algorithm: string;
  iv: string;
  authTag: string;
  timestamp: string;
}

interface DecryptionRequest {
  ciphertext: string;
  keyId: string;
  algorithm: string;
  iv: string;
  authTag: string;
  context?: Record<string, string>;
}

interface KeyDerivationResult {
  key: Buffer;
  salt: Buffer;
  iterations: number;
  algorithm: string;
}

export class EncryptionService {
  private readonly logger = new Logger('EncryptionService');
  private readonly config: EncryptionConfig;
  private readonly vaultService?: VaultService;
  private readonly hsmService?: HSMService;

  private keyCache = new Map<string, { key: Buffer; expiresAt: Date }>();
  private fieldEncryptionRules = new Map<string, FieldEncryptionConfig>();
  private isInitialized = false;

  // Supported algorithms and their configurations
  private readonly ALGORITHMS = {
    'aes-256-gcm': {
      keyLength: 32,
      ivLength: 12,
      tagLength: 16,
      blockSize: 16,
    },
    'aes-192-gcm': {
      keyLength: 24,
      ivLength: 12,
      tagLength: 16,
      blockSize: 16,
    },
    'chacha20-poly1305': {
      keyLength: 32,
      ivLength: 12,
      tagLength: 16,
      blockSize: 1,
    },
  };

  constructor(
    config: EncryptionConfig,
    vaultService?: VaultService,
    hsmService?: HSMService
  ) {
    this.config = config;
    this.vaultService = vaultService;
    this.hsmService = hsmService;
  }

  /**
   * Initialize encryption service
   */
  async initialize(): Promise<void> {
    try {
      // Validate configuration
      this.validateConfiguration();

      // Setup field-level encryption rules
      if (this.config.fieldLevelEncryption) {
        for (const rule of this.config.fieldLevelEncryption) {
          this.fieldEncryptionRules.set(rule.field, rule);
        }
      }

      // Initialize encryption keys if using Vault
      if (this.vaultService) {
        await this.initializeVaultKeys();
      }

      // Test encryption/decryption
      await this.performSelfTest();

      this.isInitialized = true;
      this.logger.info('Encryption service initialized successfully', {
        algorithm: this.config.algorithms.symmetric,
        fieldRulesCount: this.fieldEncryptionRules.size,
        vaultIntegration: !!this.vaultService,
        hsmIntegration: !!this.hsmService,
      });
    } catch (error) {
      this.logger.error('Failed to initialize encryption service', {
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Encrypt data using AES-256-GCM
   */
  async encryptData(
    plaintext: string | Buffer,
    keyId?: string,
    context?: Record<string, string>
  ): Promise<EncryptionResult> {
    this.ensureInitialized();

    try {
      const algorithm = this.config.algorithms.symmetric;
      const data = Buffer.isBuffer(plaintext)
        ? plaintext
        : Buffer.from(plaintext, 'utf8');

      // Get or generate encryption key
      const encryptionKey = await this.getOrCreateKey(
        keyId || 'default',
        algorithm
      );

      // Generate random IV
      const algorithmConfig = this.ALGORITHMS[algorithm];
      if (!algorithmConfig) {
        throw new Error(`Unsupported algorithm: ${algorithm}`);
      }

      const iv = crypto.randomBytes(algorithmConfig.ivLength);

      // Create cipher
      const cipher = crypto.createCipher(algorithm, encryptionKey.key, { iv });

      // Add authentication data if context provided
      if (context) {
        const contextData = Buffer.from(JSON.stringify(context), 'utf8');
        cipher.setAAD(contextData);
      }

      // Encrypt data
      const encrypted = Buffer.concat([cipher.update(data), cipher.final()]);

      // Get authentication tag
      const authTag = cipher.getAuthTag();

      const result: EncryptionResult = {
        ciphertext: encrypted.toString('base64'),
        keyId: keyId || 'default',
        algorithm,
        iv: iv.toString('base64'),
        authTag: authTag.toString('base64'),
        timestamp: new Date().toISOString(),
      };

      this.logger.debug('Data encrypted successfully', {
        keyId: result.keyId,
        algorithm,
        dataSize: data.length,
        hasContext: !!context,
      });

      return result;
    } catch (error) {
      this.logger.error('Data encryption failed', {
        keyId,
        algorithm: this.config.algorithms.symmetric,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Decrypt data using AES-256-GCM
   */
  async decryptData(request: DecryptionRequest): Promise<Buffer> {
    this.ensureInitialized();

    try {
      // Get decryption key
      const decryptionKey = await this.getKey(request.keyId, request.algorithm);
      if (!decryptionKey) {
        throw new Error(`Decryption key not found: ${request.keyId}`);
      }

      // Create decipher
      const iv = Buffer.from(request.iv, 'base64');
      const authTag = Buffer.from(request.authTag, 'base64');
      const ciphertext = Buffer.from(request.ciphertext, 'base64');

      const decipher = crypto.createDecipher(
        request.algorithm,
        decryptionKey.key,
        { iv }
      );
      decipher.setAuthTag(authTag);

      // Add authentication data if context provided
      if (request.context) {
        const contextData = Buffer.from(
          JSON.stringify(request.context),
          'utf8'
        );
        decipher.setAAD(contextData);
      }

      // Decrypt data
      const decrypted = Buffer.concat([
        decipher.update(ciphertext),
        decipher.final(),
      ]);

      this.logger.debug('Data decrypted successfully', {
        keyId: request.keyId,
        algorithm: request.algorithm,
        dataSize: decrypted.length,
      });

      return decrypted;
    } catch (error) {
      this.logger.error('Data decryption failed', {
        keyId: request.keyId,
        algorithm: request.algorithm,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Encrypt field-level data with automatic rule detection
   */
  async encryptField(
    data: string,
    keyId?: string,
    context?: Record<string, string>
  ): Promise<string> {
    this.ensureInitialized();

    try {
      // Use Vault transit engine if available, otherwise local encryption
      if (this.vaultService && !keyId) {
        return await this.vaultService.encryptData(
          'field-encryption',
          data,
          context
        );
      }

      const result = await this.encryptData(data, keyId, context);

      // Return compact encrypted format
      return this.serializeEncryptionResult(result);
    } catch (error) {
      this.logger.error('Field encryption failed', {
        keyId,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Decrypt field-level data
   */
  async decryptField(
    encryptedData: string,
    context?: Record<string, string>
  ): Promise<string> {
    this.ensureInitialized();

    try {
      // Check if it's a Vault ciphertext
      if (encryptedData.startsWith('vault:v')) {
        if (!this.vaultService) {
          throw new Error('Vault service required for Vault ciphertext');
        }
        return await this.vaultService.decryptData(
          'field-encryption',
          encryptedData,
          context
        );
      }

      // Parse our encrypted format
      const request = this.deserializeEncryptionResult(encryptedData, context);
      const decrypted = await this.decryptData(request);

      return decrypted.toString('utf8');
    } catch (error) {
      this.logger.error('Field decryption failed', { error: error.message });
      throw error;
    }
  }

  /**
   * Encrypt object with selective field encryption
   */
  async encryptObject(
    obj: Record<string, any>,
    rules?: FieldEncryptionConfig[]
  ): Promise<Record<string, any>> {
    this.ensureInitialized();

    const encrypted: Record<string, any> = {};
    const appliedRules =
      rules || Array.from(this.fieldEncryptionRules.values());

    for (const [key, value] of Object.entries(obj)) {
      if (value === null || value === undefined) {
        encrypted[key] = value;
        continue;
      }

      // Check if field should be encrypted
      const rule = appliedRules.find(
        r => r.field === key || (r.pattern && new RegExp(r.pattern).test(key))
      );

      if (rule) {
        try {
          if (typeof value === 'string') {
            encrypted[key] = await this.encryptField(value, rule.keyId);
          } else if (typeof value === 'object') {
            // Recursively encrypt nested objects
            encrypted[key] = await this.encryptObject(value, appliedRules);
          } else {
            // Convert to string and encrypt
            encrypted[key] = await this.encryptField(String(value), rule.keyId);
          }

          // Mark as encrypted
          encrypted[`${key}_encrypted`] = true;
        } catch (error) {
          this.logger.warn('Failed to encrypt field, storing as plaintext', {
            field: key,
            error: error.message,
          });
          encrypted[key] = value;
        }
      } else if (typeof value === 'object' && !Array.isArray(value)) {
        // Recursively process nested objects
        encrypted[key] = await this.encryptObject(value, appliedRules);
      } else {
        encrypted[key] = value;
      }
    }

    return encrypted;
  }

  /**
   * Decrypt object with selective field decryption
   */
  async decryptObject(obj: Record<string, any>): Promise<Record<string, any>> {
    this.ensureInitialized();

    const decrypted: Record<string, any> = {};

    for (const [key, value] of Object.entries(obj)) {
      if (value === null || value === undefined) {
        decrypted[key] = value;
        continue;
      }

      // Skip encryption flags
      if (key.endsWith('_encrypted')) {
        continue;
      }

      // Check if field is marked as encrypted
      const isEncrypted = obj[`${key}_encrypted`] === true;

      if (isEncrypted && typeof value === 'string') {
        try {
          decrypted[key] = await this.decryptField(value);
        } catch (error) {
          this.logger.warn('Failed to decrypt field', {
            field: key,
            error: error.message,
          });
          decrypted[key] = value; // Return as-is if decryption fails
        }
      } else if (typeof value === 'object' && !Array.isArray(value)) {
        // Recursively decrypt nested objects
        decrypted[key] = await this.decryptObject(value);
      } else {
        decrypted[key] = value;
      }
    }

    return decrypted;
  }

  /**
   * Derive key from REDACTED_SECRET using Argon2id
   */
  async deriveKey(
    REDACTED_SECRET: string,
    salt?: Buffer,
    options?: Partial<typeof this.config.keyDerivation>
  ): Promise<KeyDerivationResult> {
    try {
      const argon2 = await import('argon2');

      const derivationOptions = {
        ...this.config.keyDerivation,
        ...options,
      };

      const keySalt = salt || crypto.randomBytes(32);

      const hash = await argon2.hash(REDACTED_SECRET, {
        type: argon2.argon2id,
        memoryCost: derivationOptions.memory,
        timeCost: derivationOptions.iterations,
        parallelism: derivationOptions.parallelism,
        salt: keySalt,
        hashLength: 32,
        raw: true,
      });

      return {
        key: Buffer.from(hash),
        salt: keySalt,
        iterations: derivationOptions.iterations,
        algorithm: 'argon2id',
      };
    } catch (error) {
      this.logger.error('Key derivation failed', { error: error.message });
      throw error;
    }
  }

  /**
   * Generate random encryption key
   */
  async generateKey(
    algorithm: string = this.config.algorithms.symmetric
  ): Promise<Buffer> {
    const algorithmConfig = this.ALGORITHMS[algorithm];
    if (!algorithmConfig) {
      throw new Error(`Unsupported algorithm: ${algorithm}`);
    }

    return crypto.randomBytes(algorithmConfig.keyLength);
  }

  /**
   * Hash data using secure algorithm
   */
  hash(
    data: string | Buffer,
    algorithm: string = this.config.algorithms.hashing
  ): Buffer {
    const input = Buffer.isBuffer(data) ? data : Buffer.from(data, 'utf8');
    return crypto.createHash(algorithm).update(input).digest();
  }

  /**
   * Generate HMAC
   */
  hmac(
    data: string | Buffer,
    key: Buffer,
    algorithm: string = this.config.algorithms.hashing
  ): Buffer {
    const input = Buffer.isBuffer(data) ? data : Buffer.from(data, 'utf8');
    return crypto.createHmac(algorithm, key).update(input).digest();
  }

  /**
   * Secure random bytes generation
   */
  randomBytes(size: number): Buffer {
    return crypto.randomBytes(size);
  }

  /**
   * Constant-time comparison
   */
  constantTimeCompare(a: Buffer, b: Buffer): boolean {
    if (a.length !== b.length) {
      return false;
    }
    return crypto.timingSafeEqual(a, b);
  }

  /**
   * Private helper methods
   */

  private validateConfiguration(): void {
    const requiredAlgorithms = ['symmetric', 'asymmetric', 'hashing', 'kdf'];

    for (const alg of requiredAlgorithms) {
      if (!this.config.algorithms[alg]) {
        throw new Error(`Missing required algorithm configuration: ${alg}`);
      }
    }

    // Validate symmetric algorithm
    if (!this.ALGORITHMS[this.config.algorithms.symmetric]) {
      throw new Error(
        `Unsupported symmetric algorithm: ${this.config.algorithms.symmetric}`
      );
    }

    // Validate key derivation parameters
    const kdf = this.config.keyDerivation;
    if (kdf.iterations < 10000) {
      throw new Error('Key derivation iterations too low (minimum 10000)');
    }
    if (kdf.memory < 1024) {
      throw new Error('Key derivation memory too low (minimum 1024 KB)');
    }
  }

  private async initializeVaultKeys(): Promise<void> {
    if (!this.vaultService) return;

    try {
      // Create default field encryption key in Vault
      await this.vaultService.createTransitKey(
        'field-encryption',
        'aes256-gcm96'
      );

      this.logger.debug('Vault encryption keys initialized');
    } catch (error) {
      // Keys might already exist
      this.logger.debug(
        'Vault key initialization skipped (may already exist)',
        {
          error: error.message,
        }
      );
    }
  }

  private async performSelfTest(): Promise<void> {
    try {
      const testData = 'encryption-self-test-' + Date.now();
      const testContext = {
        test: 'self-test',
        timestamp: Date.now().toString(),
      };

      // Test local encryption
      const encrypted = await this.encryptData(
        testData,
        'self-test',
        testContext
      );
      const decrypted = await this.decryptData({
        ciphertext: encrypted.ciphertext,
        keyId: encrypted.keyId,
        algorithm: encrypted.algorithm,
        iv: encrypted.iv,
        authTag: encrypted.authTag,
        context: testContext,
      });

      if (decrypted.toString('utf8') !== testData) {
        throw new Error(
          'Self-test failed: decrypted data does not match original'
        );
      }

      // Test field encryption
      const fieldEncrypted = await this.encryptField(testData);
      const fieldDecrypted = await this.decryptField(fieldEncrypted);

      if (fieldDecrypted !== testData) {
        throw new Error('Field encryption self-test failed');
      }

      this.logger.debug('Encryption self-test passed');
    } catch (error) {
      this.logger.error('Encryption self-test failed', {
        error: error.message,
      });
      throw error;
    }
  }

  private async getOrCreateKey(
    keyId: string,
    algorithm: string
  ): Promise<{ key: Buffer; expiresAt: Date }> {
    // Check cache first
    const cached = this.keyCache.get(keyId);
    if (cached && cached.expiresAt > new Date()) {
      return cached;
    }

    // Use HSM if available
    if (this.hsmService) {
      const hsmKey = await this.hsmService.getKey(keyId);
      if (hsmKey) {
        const keyData = {
          key: Buffer.from(hsmKey.keyMaterial, 'hex'),
          expiresAt: new Date(Date.now() + 3600000), // 1 hour cache
        };
        this.keyCache.set(keyId, keyData);
        return keyData;
      }
    }

    // Generate new key
    const key = await this.generateKey(algorithm);
    const keyData = {
      key,
      expiresAt: new Date(Date.now() + 3600000), // 1 hour cache
    };

    this.keyCache.set(keyId, keyData);

    this.logger.debug('New encryption key generated', { keyId, algorithm });

    return keyData;
  }

  private async getKey(
    keyId: string,
    algorithm: string
  ): Promise<{ key: Buffer } | null> {
    try {
      const keyData = await this.getOrCreateKey(keyId, algorithm);
      return { key: keyData.key };
    } catch (error) {
      this.logger.error('Failed to get encryption key', {
        keyId,
        error: error.message,
      });
      return null;
    }
  }

  private serializeEncryptionResult(result: EncryptionResult): string {
    const data = {
      k: result.keyId,
      a: result.algorithm,
      i: result.iv,
      t: result.authTag,
      c: result.ciphertext,
    };

    return `pake:${Buffer.from(JSON.stringify(data)).toString('base64')}`;
  }

  private deserializeEncryptionResult(
    encryptedData: string,
    context?: Record<string, string>
  ): DecryptionRequest {
    if (!encryptedData.startsWith('pake:')) {
      throw new Error('Invalid encrypted data format');
    }

    try {
      const dataStr = Buffer.from(encryptedData.slice(5), 'base64').toString(
        'utf8'
      );
      const data = JSON.parse(dataStr);

      return {
        keyId: data.k,
        algorithm: data.a,
        iv: data.i,
        authTag: data.t,
        ciphertext: data.c,
        context,
      };
    } catch (error) {
      throw new Error(`Failed to parse encrypted data: ${error.message}`);
    }
  }

  private ensureInitialized(): void {
    if (!this.isInitialized) {
      throw new Error(
        'Encryption service not initialized. Call initialize() first.'
      );
    }
  }

  /**
   * Close encryption service
   */
  async close(): Promise<void> {
    // Clear sensitive key cache
    this.keyCache.clear();
    this.fieldEncryptionRules.clear();

    this.isInitialized = false;
    this.logger.info('Encryption service closed');
  }
}
