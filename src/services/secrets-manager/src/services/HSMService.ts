/**
 * Hardware Security Module (HSM) Service
 * Provides integration with Hardware Security Modules for key management
 */

import { EventEmitter } from 'events';
import {
  HSMConfig,
  HSMProvider,
  HSMMechanism,
  HSMKeyTemplate,
  HSMKeyType,
  EncryptionKey,
  KeyStatus,
  SecretEvent,
  SecretEventType,
} from '../types/secrets.types';
import { Logger } from '../utils/logger';

interface HSMSession {
  id: string;
  slot: number;
  state: 'open' | 'closed' | 'error';
  createdAt: Date;
  lastUsedAt: Date;
  operationCount: number;
}

interface HSMKeyInfo {
  handle: string;
  label: string;
  keyType: HSMKeyType;
  keySize: number;
  mechanism: HSMMechanism;
  extractable: boolean;
  persistent: boolean;
  usageFlags: string[];
  createdAt: Date;
  keyMaterial?: string; // Only for software HSM simulation
}

interface HSMOperationResult {
  success: boolean;
  data?: Buffer;
  signature?: Buffer;
  keyHandle?: string;
  error?: string;
  duration: number;
}

export class HSMService extends EventEmitter {
  private readonly logger = new Logger('HSMService');
  private readonly config: HSMConfig;

  private isInitialized = false;
  private pkcs11?: any; // PKCS#11 library handle
  private sessions = new Map<string, HSMSession>();
  private keys = new Map<string, HSMKeyInfo>();
  private healthCheckInterval?: NodeJS.Timeout;

  // Mock HSM for development/testing
  private mockMode = false;
  private mockKeys = new Map<
    string,
    { keyMaterial: Buffer; metadata: HSMKeyInfo }
  >();

  constructor(config: HSMConfig) {
    super();
    this.config = config;

    // Enable mock mode for SoftHSM or when library is not available
    this.mockMode =
      config.provider === HSMProvider.SOFTHSM ||
      process.env.HSM_MOCK_MODE === 'true';
  }

  /**
   * Initialize HSM service
   */
  async initialize(): Promise<void> {
    try {
      if (this.mockMode) {
        await this.initializeMockHSM();
      } else {
        await this.initializeRealHSM();
      }

      // Start health monitoring
      this.startHealthCheck();

      this.isInitialized = true;
      this.logger.info('HSM service initialized successfully', {
        provider: this.config.provider,
        mockMode: this.mockMode,
        slot: this.config.slot,
      });
    } catch (error) {
      this.logger.error('Failed to initialize HSM service', {
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Generate a new key in HSM
   */
  async generateKey(
    label: string,
    keyType: HSMKeyType,
    keySize: number,
    template?: Partial<HSMKeyTemplate>
  ): Promise<HSMKeyInfo> {
    this.ensureInitialized();

    try {
      const keyTemplate: HSMKeyTemplate = {
        keyType,
        keySize,
        extractable: false,
        persistent: true,
        encrypt: true,
        decrypt: true,
        sign: keyType !== HSMKeyType.AES,
        verify: keyType !== HSMKeyType.AES,
        wrap: false,
        unwrap: false,
        ...template,
      };

      let keyInfo: HSMKeyInfo;

      if (this.mockMode) {
        keyInfo = await this.generateMockKey(label, keyTemplate);
      } else {
        keyInfo = await this.generateRealKey(label, keyTemplate);
      }

      this.keys.set(label, keyInfo);

      // Emit event
      this.emit('keyGenerated', {
        id: `hsm-key-${Date.now()}`,
        timestamp: new Date().toISOString(),
        type: SecretEventType.KEY_GENERATE,
        secretId: label,
        actor: 'hsm-service',
        source: 'hsm',
        success: true,
        metadata: { keyType, keySize, provider: this.config.provider },
      } as SecretEvent);

      this.logger.info('HSM key generated successfully', {
        label,
        keyType,
        keySize,
        handle: keyInfo.handle,
      });

      return keyInfo;
    } catch (error) {
      this.logger.error('HSM key generation failed', {
        label,
        keyType,
        keySize,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Get key information
   */
  async getKey(label: string): Promise<HSMKeyInfo | null> {
    this.ensureInitialized();

    const keyInfo = this.keys.get(label);
    if (!keyInfo) {
      this.logger.debug('HSM key not found', { label });
      return null;
    }

    // Update last used timestamp
    keyInfo.createdAt = keyInfo.createdAt || new Date();

    return keyInfo;
  }

  /**
   * Encrypt data using HSM key
   */
  async encrypt(
    keyLabel: string,
    plaintext: Buffer,
    mechanism: HSMMechanism = HSMMechanism.AES_GCM
  ): Promise<HSMOperationResult> {
    this.ensureInitialized();

    const startTime = Date.now();

    try {
      const keyInfo = this.keys.get(keyLabel);
      if (!keyInfo) {
        throw new Error(`HSM key not found: ${keyLabel}`);
      }

      let result: HSMOperationResult;

      if (this.mockMode) {
        result = await this.mockEncrypt(keyInfo, plaintext, mechanism);
      } else {
        result = await this.realEncrypt(keyInfo, plaintext, mechanism);
      }

      result.duration = Date.now() - startTime;

      // Emit event
      this.emit('hsmOperation', {
        id: `hsm-op-${Date.now()}`,
        timestamp: new Date().toISOString(),
        type: SecretEventType.ENCRYPT,
        secretId: keyLabel,
        actor: 'hsm-service',
        source: 'hsm',
        success: result.success,
        metadata: {
          operation: 'encrypt',
          mechanism,
          dataSize: plaintext.length,
          duration: result.duration,
        },
      } as SecretEvent);

      return result;
    } catch (error) {
      const duration = Date.now() - startTime;
      this.logger.error('HSM encryption failed', {
        keyLabel,
        mechanism,
        error: error.message,
        duration,
      });

      return {
        success: false,
        error: error.message,
        duration,
      };
    }
  }

  /**
   * Decrypt data using HSM key
   */
  async decrypt(
    keyLabel: string,
    ciphertext: Buffer,
    mechanism: HSMMechanism = HSMMechanism.AES_GCM
  ): Promise<HSMOperationResult> {
    this.ensureInitialized();

    const startTime = Date.now();

    try {
      const keyInfo = this.keys.get(keyLabel);
      if (!keyInfo) {
        throw new Error(`HSM key not found: ${keyLabel}`);
      }

      let result: HSMOperationResult;

      if (this.mockMode) {
        result = await this.mockDecrypt(keyInfo, ciphertext, mechanism);
      } else {
        result = await this.realDecrypt(keyInfo, ciphertext, mechanism);
      }

      result.duration = Date.now() - startTime;

      // Emit event
      this.emit('hsmOperation', {
        id: `hsm-op-${Date.now()}`,
        timestamp: new Date().toISOString(),
        type: SecretEventType.DECRYPT,
        secretId: keyLabel,
        actor: 'hsm-service',
        source: 'hsm',
        success: result.success,
        metadata: {
          operation: 'decrypt',
          mechanism,
          dataSize: result.data?.length || 0,
          duration: result.duration,
        },
      } as SecretEvent);

      return result;
    } catch (error) {
      const duration = Date.now() - startTime;
      this.logger.error('HSM decryption failed', {
        keyLabel,
        mechanism,
        error: error.message,
        duration,
      });

      return {
        success: false,
        error: error.message,
        duration,
      };
    }
  }

  /**
   * Sign data using HSM key
   */
  async sign(
    keyLabel: string,
    data: Buffer,
    mechanism: HSMMechanism = HSMMechanism.RSA_PSS
  ): Promise<HSMOperationResult> {
    this.ensureInitialized();

    const startTime = Date.now();

    try {
      const keyInfo = this.keys.get(keyLabel);
      if (!keyInfo) {
        throw new Error(`HSM key not found: ${keyLabel}`);
      }

      if (!keyInfo.usageFlags.includes('sign')) {
        throw new Error(`HSM key does not support signing: ${keyLabel}`);
      }

      let result: HSMOperationResult;

      if (this.mockMode) {
        result = await this.mockSign(keyInfo, data, mechanism);
      } else {
        result = await this.realSign(keyInfo, data, mechanism);
      }

      result.duration = Date.now() - startTime;

      // Emit event
      this.emit('hsmOperation', {
        id: `hsm-op-${Date.now()}`,
        timestamp: new Date().toISOString(),
        type: SecretEventType.SIGN,
        secretId: keyLabel,
        actor: 'hsm-service',
        source: 'hsm',
        success: result.success,
        metadata: {
          operation: 'sign',
          mechanism,
          dataSize: data.length,
          signatureSize: result.signature?.length || 0,
          duration: result.duration,
        },
      } as SecretEvent);

      return result;
    } catch (error) {
      const duration = Date.now() - startTime;
      this.logger.error('HSM signing failed', {
        keyLabel,
        mechanism,
        error: error.message,
        duration,
      });

      return {
        success: false,
        error: error.message,
        duration,
      };
    }
  }

  /**
   * Verify signature using HSM key
   */
  async verify(
    keyLabel: string,
    data: Buffer,
    signature: Buffer,
    mechanism: HSMMechanism = HSMMechanism.RSA_PSS
  ): Promise<HSMOperationResult> {
    this.ensureInitialized();

    const startTime = Date.now();

    try {
      const keyInfo = this.keys.get(keyLabel);
      if (!keyInfo) {
        throw new Error(`HSM key not found: ${keyLabel}`);
      }

      if (!keyInfo.usageFlags.includes('verify')) {
        throw new Error(`HSM key does not support verification: ${keyLabel}`);
      }

      let result: HSMOperationResult;

      if (this.mockMode) {
        result = await this.mockVerify(keyInfo, data, signature, mechanism);
      } else {
        result = await this.realVerify(keyInfo, data, signature, mechanism);
      }

      result.duration = Date.now() - startTime;

      // Emit event
      this.emit('hsmOperation', {
        id: `hsm-op-${Date.now()}`,
        timestamp: new Date().toISOString(),
        type: SecretEventType.VERIFY,
        secretId: keyLabel,
        actor: 'hsm-service',
        source: 'hsm',
        success: result.success,
        metadata: {
          operation: 'verify',
          mechanism,
          dataSize: data.length,
          signatureSize: signature.length,
          duration: result.duration,
          verified: result.success,
        },
      } as SecretEvent);

      return result;
    } catch (error) {
      const duration = Date.now() - startTime;
      this.logger.error('HSM verification failed', {
        keyLabel,
        mechanism,
        error: error.message,
        duration,
      });

      return {
        success: false,
        error: error.message,
        duration,
      };
    }
  }

  /**
   * List all keys in HSM
   */
  async listKeys(): Promise<HSMKeyInfo[]> {
    this.ensureInitialized();
    return Array.from(this.keys.values());
  }

  /**
   * Delete key from HSM
   */
  async deleteKey(label: string): Promise<boolean> {
    this.ensureInitialized();

    try {
      const keyInfo = this.keys.get(label);
      if (!keyInfo) {
        return false;
      }

      if (this.mockMode) {
        this.mockKeys.delete(keyInfo.handle);
      } else {
        await this.realDeleteKey(keyInfo);
      }

      this.keys.delete(label);

      this.logger.info('HSM key deleted successfully', { label });
      return true;
    } catch (error) {
      this.logger.error('HSM key deletion failed', {
        label,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Get HSM status and health
   */
  async getStatus(): Promise<{
    initialized: boolean;
    provider: HSMProvider;
    mockMode: boolean;
    slotInfo?: any;
    keyCount: number;
    sessionCount: number;
  }> {
    return {
      initialized: this.isInitialized,
      provider: this.config.provider,
      mockMode: this.mockMode,
      slotInfo: this.mockMode
        ? { description: 'Mock HSM' }
        : await this.getRealSlotInfo(),
      keyCount: this.keys.size,
      sessionCount: this.sessions.size,
    };
  }

  /**
   * Private methods for real HSM operations
   */

  private async initializeRealHSM(): Promise<void> {
    try {
      // Load PKCS#11 library
      const pkcs11js = await import('pkcs11js');
      this.pkcs11 = new pkcs11js.PKCS11();

      // Load the HSM library
      this.pkcs11.load(this.config.library);

      // Initialize PKCS#11
      this.pkcs11.C_Initialize();

      // Get slot list
      const slots = this.pkcs11.C_GetSlotList(true);
      if (slots.length === 0) {
        throw new Error('No HSM slots available');
      }

      const slotId = this.config.slot || slots[0];

      // Get slot info
      const slotInfo = this.pkcs11.C_GetSlotInfo(slotId);
      this.logger.debug('HSM slot info', slotInfo);

      // Open session
      const session = this.pkcs11.C_OpenSession(
        slotId,
        pkcs11js.CKF_SERIAL_SESSION | pkcs11js.CKF_RW_SESSION
      );

      // Login if PIN provided
      if (this.config.pin) {
        this.pkcs11.C_Login(session, pkcs11js.CKU_USER, this.config.pin);
      }

      // Store session
      const sessionInfo: HSMSession = {
        id: `session-${session}`,
        slot: slotId,
        state: 'open',
        createdAt: new Date(),
        lastUsedAt: new Date(),
        operationCount: 0,
      };

      this.sessions.set(sessionInfo.id, sessionInfo);

      this.logger.debug('Real HSM initialized successfully');
    } catch (error) {
      this.logger.error('Real HSM initialization failed', {
        error: error.message,
      });
      // Fall back to mock mode
      this.mockMode = true;
      await this.initializeMockHSM();
    }
  }

  private async initializeMockHSM(): Promise<void> {
    this.logger.info('Initializing HSM in mock mode');

    // Create some default mock keys for testing
    await this.generateMockKey('default-aes', {
      keyType: HSMKeyType.AES,
      keySize: 256,
      extractable: false,
      persistent: true,
      encrypt: true,
      decrypt: true,
      sign: false,
      verify: false,
      wrap: false,
      unwrap: false,
    });

    this.logger.debug('Mock HSM initialized with default keys');
  }

  private async generateRealKey(
    label: string,
    template: HSMKeyTemplate
  ): Promise<HSMKeyInfo> {
    // Implementation would use PKCS#11 to generate key in real HSM
    // This is a stub for the interface
    throw new Error('Real HSM key generation not implemented in this version');
  }

  private async generateMockKey(
    label: string,
    template: HSMKeyTemplate
  ): Promise<HSMKeyInfo> {
    const crypto = await import('crypto');

    // Generate mock key material
    let keyMaterial: Buffer;

    switch (template.keyType) {
      case HSMKeyType.AES:
        keyMaterial = crypto.randomBytes(template.keySize! / 8);
        break;
      case HSMKeyType.RSA:
        // For mock, we'll just generate random bytes
        keyMaterial = crypto.randomBytes(template.keySize! / 8);
        break;
      default:
        keyMaterial = crypto.randomBytes(32);
    }

    const handle = `mock-${crypto.randomUUID()}`;

    const keyInfo: HSMKeyInfo = {
      handle,
      label,
      keyType: template.keyType,
      keySize: template.keySize || 256,
      mechanism: this.getMechanismForKeyType(template.keyType),
      extractable: template.extractable,
      persistent: template.persistent,
      usageFlags: this.getUsageFlags(template),
      createdAt: new Date(),
      keyMaterial: keyMaterial.toString('hex'),
    };

    // Store mock key
    this.mockKeys.set(handle, { keyMaterial, metadata: keyInfo });

    return keyInfo;
  }

  private async mockEncrypt(
    keyInfo: HSMKeyInfo,
    plaintext: Buffer,
    mechanism: HSMMechanism
  ): Promise<HSMOperationResult> {
    const crypto = await import('crypto');

    const mockKey = this.mockKeys.get(keyInfo.handle);
    if (!mockKey) {
      throw new Error('Mock key not found');
    }

    // Simple AES-GCM encryption for mock
    const iv = crypto.randomBytes(12);
    const cipher = crypto.createCipher('aes-256-gcm', mockKey.keyMaterial, {
      iv,
    });

    const encrypted = Buffer.concat([cipher.update(plaintext), cipher.final()]);

    const authTag = cipher.getAuthTag();
    const result = Buffer.concat([iv, authTag, encrypted]);

    return {
      success: true,
      data: result,
      duration: 0, // Will be set by caller
    };
  }

  private async mockDecrypt(
    keyInfo: HSMKeyInfo,
    ciphertext: Buffer,
    mechanism: HSMMechanism
  ): Promise<HSMOperationResult> {
    const crypto = await import('crypto');

    const mockKey = this.mockKeys.get(keyInfo.handle);
    if (!mockKey) {
      throw new Error('Mock key not found');
    }

    try {
      // Extract IV, auth tag, and encrypted data
      const iv = ciphertext.subarray(0, 12);
      const authTag = ciphertext.subarray(12, 28);
      const encrypted = ciphertext.subarray(28);

      const decipher = crypto.createDecipher(
        'aes-256-gcm',
        mockKey.keyMaterial,
        { iv }
      );
      decipher.setAuthTag(authTag);

      const decrypted = Buffer.concat([
        decipher.update(encrypted),
        decipher.final(),
      ]);

      return {
        success: true,
        data: decrypted,
        duration: 0, // Will be set by caller
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
        duration: 0,
      };
    }
  }

  private async mockSign(
    keyInfo: HSMKeyInfo,
    data: Buffer,
    mechanism: HSMMechanism
  ): Promise<HSMOperationResult> {
    const crypto = await import('crypto');

    const mockKey = this.mockKeys.get(keyInfo.handle);
    if (!mockKey) {
      throw new Error('Mock key not found');
    }

    // Simple HMAC for mock signing
    const signature = crypto
      .createHmac('sha256', mockKey.keyMaterial)
      .update(data)
      .digest();

    return {
      success: true,
      signature,
      duration: 0, // Will be set by caller
    };
  }

  private async mockVerify(
    keyInfo: HSMKeyInfo,
    data: Buffer,
    signature: Buffer,
    mechanism: HSMMechanism
  ): Promise<HSMOperationResult> {
    const crypto = await import('crypto');

    const mockKey = this.mockKeys.get(keyInfo.handle);
    if (!mockKey) {
      throw new Error('Mock key not found');
    }

    // Verify HMAC
    const expectedSignature = crypto
      .createHmac('sha256', mockKey.keyMaterial)
      .update(data)
      .digest();

    const isValid = crypto.timingSafeEqual(signature, expectedSignature);

    return {
      success: isValid,
      duration: 0, // Will be set by caller
    };
  }

  private getMechanismForKeyType(keyType: HSMKeyType): HSMMechanism {
    switch (keyType) {
      case HSMKeyType.AES:
        return HSMMechanism.AES_GCM;
      case HSMKeyType.RSA:
        return HSMMechanism.RSA_PSS;
      case HSMKeyType.ECDSA:
        return HSMMechanism.ECDSA;
      default:
        return HSMMechanism.AES_GCM;
    }
  }

  private getUsageFlags(template: HSMKeyTemplate): string[] {
    const flags: string[] = [];
    if (template.encrypt) flags.push('encrypt');
    if (template.decrypt) flags.push('decrypt');
    if (template.sign) flags.push('sign');
    if (template.verify) flags.push('verify');
    if (template.wrap) flags.push('wrap');
    if (template.unwrap) flags.push('unwrap');
    return flags;
  }

  private async getRealSlotInfo(): Promise<any> {
    // Implementation would return real HSM slot information
    return { description: 'Real HSM slot info not implemented' };
  }

  private async realEncrypt(
    keyInfo: HSMKeyInfo,
    plaintext: Buffer,
    mechanism: HSMMechanism
  ): Promise<HSMOperationResult> {
    throw new Error('Real HSM encryption not implemented in this version');
  }

  private async realDecrypt(
    keyInfo: HSMKeyInfo,
    ciphertext: Buffer,
    mechanism: HSMMechanism
  ): Promise<HSMOperationResult> {
    throw new Error('Real HSM decryption not implemented in this version');
  }

  private async realSign(
    keyInfo: HSMKeyInfo,
    data: Buffer,
    mechanism: HSMMechanism
  ): Promise<HSMOperationResult> {
    throw new Error('Real HSM signing not implemented in this version');
  }

  private async realVerify(
    keyInfo: HSMKeyInfo,
    data: Buffer,
    signature: Buffer,
    mechanism: HSMMechanism
  ): Promise<HSMOperationResult> {
    throw new Error('Real HSM verification not implemented in this version');
  }

  private async realDeleteKey(keyInfo: HSMKeyInfo): Promise<void> {
    throw new Error('Real HSM key deletion not implemented in this version');
  }

  private startHealthCheck(): void {
    this.healthCheckInterval = setInterval(async () => {
      try {
        const status = await this.getStatus();
        this.emit('healthCheck', { status: 'healthy', details: status });
      } catch (error) {
        this.emit('healthCheck', { status: 'unhealthy', error: error.message });
      }
    }, 60000); // Check every minute
  }

  private ensureInitialized(): void {
    if (!this.isInitialized) {
      throw new Error('HSM service not initialized. Call initialize() first.');
    }
  }

  /**
   * Close HSM service
   */
  async close(): Promise<void> {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
    }

    // Close PKCS#11 sessions
    for (const session of this.sessions.values()) {
      if (this.pkcs11 && session.state === 'open') {
        try {
          this.pkcs11.C_CloseSession(parseInt(session.id.split('-')[1]));
        } catch (error) {
          this.logger.warn('Failed to close HSM session', {
            error: error.message,
          });
        }
      }
    }

    if (this.pkcs11 && !this.mockMode) {
      try {
        this.pkcs11.C_Finalize();
      } catch (error) {
        this.logger.warn('Failed to finalize PKCS#11', {
          error: error.message,
        });
      }
    }

    // Clear sensitive data
    this.sessions.clear();
    this.keys.clear();
    this.mockKeys.clear();

    this.isInitialized = false;
    this.logger.info('HSM service closed');
  }
}
