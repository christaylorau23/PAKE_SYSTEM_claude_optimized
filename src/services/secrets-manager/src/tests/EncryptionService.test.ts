import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { EncryptionService } from '../services/EncryptionService';
import { HSMService } from '../services/HSMService';
import {
  EncryptionConfig,
  EncryptionResult,
  FieldEncryptionConfig,
} from '../types/secrets.types';
import * as crypto from 'crypto';

vi.mock('../services/HSMService');
vi.mock('crypto', () => ({
  randomBytes: vi.fn(),
  createCipher: vi.fn(),
  createDecipher: vi.fn(),
  pbkdf2: vi.fn(),
  scrypt: vi.fn(),
  createHash: vi.fn(),
  createHmac: vi.fn(),
  timingSafeEqual: vi.fn(),
}));

describe('EncryptionService', () => {
  let encryptionService: EncryptionService;
  let mockHSMService: jest.Mocked<HSMService>;
  let config: EncryptionConfig;

  beforeEach(() => {
    mockHSMService = {
      initialize: vi.fn().mockResolvedValue(undefined),
      generateKey: vi.fn(),
      encryptData: vi.fn(),
      decryptData: vi.fn(),
      signData: vi.fn(),
      verifySignature: vi.fn(),
      getKeyInfo: vi.fn(),
      isInitialized: vi.fn().mockReturnValue(true),
    } as any;

    (HSMService as any).mockImplementation(() => mockHSMService);

    config = {
      algorithms: {
        symmetric: 'aes-256-gcm',
        asymmetric: 'rsa-4096',
        hash: 'sha256',
        kdf: 'argon2id',
      },
      keys: {
        masterKeyId: 'master-key-1',
        keyDerivationParams: {
          memory: 64 * 1024,
          iterations: 3,
          parallelism: 4,
        },
      },
      fieldLevel: {
        enabled: true,
        algorithms: {
          pii: 'aes-256-gcm',
          sensitive: 'aes-256-gcm',
        },
      },
      hsm: {
        enabled: true,
        provider: 'SoftHSM',
        config: {
          library: '/usr/lib/softhsm/libsofthsm2.so',
          slot: 0,
          pin: 'test-pin',
        },
      },
    };

    encryptionService = new EncryptionService(config, mockHSMService);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Initialization', () => {
    it('should initialize successfully with HSM', async () => {
      await encryptionService.initialize();
      expect(mockHSMService.initialize).toHaveBeenCalled();
    });

    it('should initialize without HSM when disabled', async () => {
      config.hsm.enabled = false;
      const service = new EncryptionService(config, mockHSMService);

      await service.initialize();
      expect(mockHSMService.initialize).not.toHaveBeenCalled();
    });
  });

  describe('Data Encryption', () => {
    beforeEach(async () => {
      await encryptionService.initialize();

      // Mock crypto functions
      (crypto.randomBytes as any).mockReturnValue(
        Buffer.from('1234567890123456')
      );

      const mockCipher = {
        update: vi.fn().mockReturnValue(Buffer.from('encrypted')),
        final: vi.fn().mockReturnValue(Buffer.from('final')),
        getAuthTag: vi.fn().mockReturnValue(Buffer.from('authTag123456')),
      };

      (crypto.createCipher as any).mockReturnValue(mockCipher);
    });

    it('should encrypt data successfully', async () => {
      const plaintext = 'sensitive data to encrypt';

      const result = await encryptionService.encryptData(plaintext);

      expect(result.ciphertext).toBeTruthy();
      expect(result.keyId).toBe('master-key-1');
      expect(result.algorithm).toBe('aes-256-gcm');
      expect(result.iv).toBeTruthy();
      expect(result.authTag).toBeTruthy();
    });

    it('should encrypt buffer data', async () => {
      const buffer = Buffer.from('binary data', 'utf8');

      const result = await encryptionService.encryptData(buffer);

      expect(result).toBeTruthy();
      expect(result.ciphertext).toBeTruthy();
    });

    it('should use specified key ID', async () => {
      const plaintext = 'test data';
      const customKeyId = 'custom-key-123';

      const result = await encryptionService.encryptData(
        plaintext,
        customKeyId
      );

      expect(result.keyId).toBe(customKeyId);
    });

    it('should handle encryption errors', async () => {
      (crypto.createCipher as any).mockImplementation(() => {
        throw new Error('Encryption failed');
      });

      await expect(encryptionService.encryptData('test')).rejects.toThrow(
        'Data encryption failed'
      );
    });
  });

  describe('Data Decryption', () => {
    beforeEach(async () => {
      await encryptionService.initialize();

      const mockDecipher = {
        setAuthTag: vi.fn(),
        update: vi.fn().mockReturnValue(Buffer.from('decrypted')),
        final: vi.fn().mockReturnValue(Buffer.from('final')),
      };

      (crypto.createDecipher as any).mockReturnValue(mockDecipher);
    });

    it('should decrypt data successfully', async () => {
      const encryptionResult: EncryptionResult = {
        ciphertext: 'encrypted-data-base64',
        keyId: 'master-key-1',
        algorithm: 'aes-256-gcm',
        iv: Buffer.from('1234567890123456').toString('base64'),
        authTag: Buffer.from('authTag123456').toString('base64'),
      };

      const decrypted = await encryptionService.decryptData(encryptionResult);

      expect(decrypted).toContain('decrypted');
    });

    it('should handle decryption with invalid auth tag', async () => {
      const mockDecipher = {
        setAuthTag: vi.fn(),
        update: vi.fn(),
        final: vi.fn().mockImplementation(() => {
          throw new Error('Unsupported state or unable to authenticate data');
        }),
      };

      (crypto.createDecipher as any).mockReturnValue(mockDecipher);

      const encryptionResult: EncryptionResult = {
        ciphertext: 'tampered-data',
        keyId: 'master-key-1',
        algorithm: 'aes-256-gcm',
        iv: Buffer.from('1234567890123456').toString('base64'),
        authTag: Buffer.from('invalid-tag').toString('base64'),
      };

      await expect(
        encryptionService.decryptData(encryptionResult)
      ).rejects.toThrow('Data decryption failed');
    });
  });

  describe('Field-Level Encryption', () => {
    beforeEach(async () => {
      await encryptionService.initialize();
    });

    it('should encrypt PII field', async () => {
      const fieldConfig: FieldEncryptionConfig = {
        fieldName: 'email',
        algorithm: 'aes-256-gcm',
        keyId: 'pii-key-1',
      };

      // Mock encryption
      vi.spyOn(encryptionService, 'encryptData').mockResolvedValue({
        ciphertext: 'encrypted-email',
        keyId: 'pii-key-1',
        algorithm: 'aes-256-gcm',
        iv: 'test-iv',
        authTag: 'test-tag',
      });

      const result = await encryptionService.encryptField(
        'user@example.com',
        fieldConfig
      );

      expect(result.ciphertext).toBe('encrypted-email');
      expect(result.keyId).toBe('pii-key-1');
    });

    it('should decrypt PII field', async () => {
      const encryptionResult: EncryptionResult = {
        ciphertext: 'encrypted-email',
        keyId: 'pii-key-1',
        algorithm: 'aes-256-gcm',
        iv: 'test-iv',
        authTag: 'test-tag',
      };

      const fieldConfig: FieldEncryptionConfig = {
        fieldName: 'email',
        algorithm: 'aes-256-gcm',
        keyId: 'pii-key-1',
      };

      // Mock decryption
      vi.spyOn(encryptionService, 'decryptData').mockResolvedValue(
        'user@example.com'
      );

      const result = await encryptionService.decryptField(
        encryptionResult,
        fieldConfig
      );

      expect(result).toBe('user@example.com');
    });

    it('should encrypt multiple fields in object', async () => {
      const data = {
        name: 'John Doe',
        email: 'john@example.com',
        ssn: '123-45-6789',
        age: 30,
      };

      const fieldsToEncrypt = [
        {
          fieldName: 'email',
          algorithm: 'aes-256-gcm' as const,
          keyId: 'pii-key',
        },
        {
          fieldName: 'ssn',
          algorithm: 'aes-256-gcm' as const,
          keyId: 'pii-key',
        },
      ];

      // Mock field encryption
      vi.spyOn(encryptionService, 'encryptField')
        .mockResolvedValueOnce({
          ciphertext: 'encrypted-email',
          keyId: 'pii-key',
          algorithm: 'aes-256-gcm',
          iv: 'iv1',
          authTag: 'tag1',
        })
        .mockResolvedValueOnce({
          ciphertext: 'encrypted-ssn',
          keyId: 'pii-key',
          algorithm: 'aes-256-gcm',
          iv: 'iv2',
          authTag: 'tag2',
        });

      const result = await encryptionService.encryptFields(
        data,
        fieldsToEncrypt
      );

      expect(result.name).toBe('John Doe'); // Not encrypted
      expect(result.age).toBe(30); // Not encrypted
      expect(result.email).toEqual({
        ciphertext: 'encrypted-email',
        keyId: 'pii-key',
        algorithm: 'aes-256-gcm',
        iv: 'iv1',
        authTag: 'tag1',
      });
      expect(result.ssn).toEqual({
        ciphertext: 'encrypted-ssn',
        keyId: 'pii-key',
        algorithm: 'aes-256-gcm',
        iv: 'iv2',
        authTag: 'tag2',
      });
    });
  });

  describe('Key Management', () => {
    beforeEach(async () => {
      await encryptionService.initialize();
    });

    it('should generate new encryption key', async () => {
      const keyInfo = {
        keyId: 'new-key-123',
        algorithm: 'aes-256-gcm',
        createdAt: new Date(),
        status: 'active' as const,
      };

      mockHSMService.generateKey.mockResolvedValue(keyInfo);

      const result = await encryptionService.generateKey(
        'test-key',
        'aes-256-gcm'
      );

      expect(result.keyId).toBe('new-key-123');
      expect(result.algorithm).toBe('aes-256-gcm');
      expect(mockHSMService.generateKey).toHaveBeenCalledWith(
        'test-key',
        'symmetric',
        256
      );
    });

    it('should rotate encryption key', async () => {
      const oldKeyId = 'old-key-123';
      const newKeyInfo = {
        keyId: 'new-key-456',
        algorithm: 'aes-256-gcm',
        createdAt: new Date(),
        status: 'active' as const,
      };

      mockHSMService.generateKey.mockResolvedValue(newKeyInfo);

      const result = await encryptionService.rotateKey(oldKeyId);

      expect(result.success).toBe(true);
      expect(result.newKeyId).toBe('new-key-456');
      expect(result.oldKeyId).toBe(oldKeyId);
    });
  });

  describe('Performance', () => {
    beforeEach(async () => {
      await encryptionService.initialize();

      // Mock crypto functions for performance test
      (crypto.randomBytes as any).mockReturnValue(
        Buffer.from('1234567890123456')
      );

      const mockCipher = {
        update: vi.fn().mockReturnValue(Buffer.from('encrypted')),
        final: vi.fn().mockReturnValue(Buffer.from('final')),
        getAuthTag: vi.fn().mockReturnValue(Buffer.from('authTag123456')),
      };

      (crypto.createCipher as any).mockReturnValue(mockCipher);
    });

    it('should meet encryption performance requirements', async () => {
      const plaintext = 'test data for performance measurement';

      const startTime = performance.now();
      await encryptionService.encryptData(plaintext);
      const duration = performance.now() - startTime;

      expect(duration).toBeLessThan(10); // Less than 10ms requirement
    });

    it('should meet decryption performance requirements', async () => {
      const encryptionResult: EncryptionResult = {
        ciphertext: 'encrypted-data',
        keyId: 'master-key-1',
        algorithm: 'aes-256-gcm',
        iv: Buffer.from('1234567890123456').toString('base64'),
        authTag: Buffer.from('authTag123456').toString('base64'),
      };

      const mockDecipher = {
        setAuthTag: vi.fn(),
        update: vi.fn().mockReturnValue(Buffer.from('decrypted')),
        final: vi.fn().mockReturnValue(Buffer.from('final')),
      };

      (crypto.createDecipher as any).mockReturnValue(mockDecipher);

      const startTime = performance.now();
      await encryptionService.decryptData(encryptionResult);
      const duration = performance.now() - startTime;

      expect(duration).toBeLessThan(10); // Less than 10ms requirement
    });
  });

  describe('Key Derivation', () => {
    beforeEach(async () => {
      await encryptionService.initialize();

      // Mock Argon2 key derivation
      (crypto.scrypt as any).mockImplementation(
        (REDACTED_SECRET, salt, keylen, options, callback) => {
          callback(null, Buffer.from('derived-key-32-bytes-long-test'));
        }
      );
    });

    it('should derive key using Argon2id', async () => {
      const REDACTED_SECRET = process.env.UNKNOWN;
      const salt = Buffer.from('test-salt-16-bytes');

      const derivedKey = await encryptionService.deriveKey(REDACTED_SECRET, salt);

      expect(derivedKey).toBeInstanceOf(Buffer);
      expect(derivedKey.length).toBe(32); // 256 bits
    });

    it('should use consistent salt for same input', async () => {
      const REDACTED_SECRET = process.env.UNKNOWN;

      const key1 = await encryptionService.deriveKey(
        REDACTED_SECRET,
        Buffer.from('same-salt')
      );
      const key2 = await encryptionService.deriveKey(
        REDACTED_SECRET,
        Buffer.from('same-salt')
      );

      expect(key1.equals(key2)).toBe(true);
    });
  });

  describe('Integrity Verification', () => {
    beforeEach(async () => {
      await encryptionService.initialize();

      const mockHash = {
        update: vi.fn().mockReturnThis(),
        digest: vi.fn().mockReturnValue(Buffer.from('computed-hash')),
      };

      const mockHmac = {
        update: vi.fn().mockReturnThis(),
        digest: vi.fn().mockReturnValue(Buffer.from('computed-hmac')),
      };

      (crypto.createHash as any).mockReturnValue(mockHash);
      (crypto.createHmac as any).mockReturnValue(mockHmac);
      (crypto.timingSafeEqual as any).mockReturnValue(true);
    });

    it('should generate data hash', async () => {
      const data = 'important data to hash';

      const hash = await encryptionService.generateHash(data);

      expect(hash).toBeTruthy();
      expect(crypto.createHash).toHaveBeenCalledWith('sha256');
    });

    it('should verify data integrity with HMAC', async () => {
      const data = 'data to verify';
      const key = 'verification-key';
      const expectedHmac = Buffer.from('computed-hmac');

      const isValid = await encryptionService.verifyIntegrity(
        data,
        expectedHmac,
        key
      );

      expect(isValid).toBe(true);
      expect(crypto.createHmac).toHaveBeenCalledWith('sha256', key);
    });

    it('should detect tampered data', async () => {
      (crypto.timingSafeEqual as any).mockReturnValue(false);

      const data = 'tampered data';
      const key = 'verification-key';
      const invalidHmac = Buffer.from('invalid-hmac');

      const isValid = await encryptionService.verifyIntegrity(
        data,
        invalidHmac,
        key
      );

      expect(isValid).toBe(false);
    });
  });

  describe('Error Handling', () => {
    beforeEach(async () => {
      await encryptionService.initialize();
    });

    it('should handle HSM unavailable', async () => {
      mockHSMService.isInitialized.mockReturnValue(false);

      await expect(
        encryptionService.generateKey('test', 'aes-256-gcm')
      ).rejects.toThrow('HSM not available');
    });

    it('should handle invalid encryption algorithm', async () => {
      await expect(
        encryptionService.encryptData('test', 'key', 'invalid-algorithm' as any)
      ).rejects.toThrow('Unsupported algorithm');
    });

    it('should handle corrupted encryption result', async () => {
      const corruptedResult: EncryptionResult = {
        ciphertext: 'invalid-base64-!@#$',
        keyId: 'key-1',
        algorithm: 'aes-256-gcm',
        iv: 'invalid-iv',
        authTag: 'invalid-tag',
      };

      await expect(
        encryptionService.decryptData(corruptedResult)
      ).rejects.toThrow();
    });
  });

  describe('Security Compliance', () => {
    it('should ensure 100% encryption coverage for sensitive fields', async () => {
      const sensitiveData = {
        username: 'john_doe',
        REDACTED_SECRET: process.env.UNKNOWN,
        ssn: '123-45-6789',
        creditCard: '4111-1111-1111-1111',
        email: 'john@example.com',
      };

      const fieldsToEncrypt = [
        {
          fieldName: 'REDACTED_SECRET',
          algorithm: 'aes-256-gcm' as const,
          keyId: process.env.UNKNOWN,
        },
        {
          fieldName: 'ssn',
          algorithm: 'aes-256-gcm' as const,
          keyId: 'pii-key',
        },
        {
          fieldName: 'creditCard',
          algorithm: 'aes-256-gcm' as const,
          keyId: 'pii-key',
        },
      ];

      // Mock field encryption
      vi.spyOn(encryptionService, 'encryptField').mockResolvedValue({
        ciphertext: 'encrypted-value',
        keyId: 'pii-key',
        algorithm: 'aes-256-gcm',
        iv: 'test-iv',
        authTag: 'test-tag',
      });

      const encryptedData = await encryptionService.encryptFields(
        sensitiveData,
        fieldsToEncrypt
      );

      // Verify sensitive fields are encrypted
      expect(typeof encryptedData.REDACTED_SECRET).toBe('object');
      expect(typeof encryptedData.ssn).toBe('object');
      expect(typeof encryptedData.creditCard).toBe('object');

      // Non-sensitive fields remain plain
      expect(encryptedData.username).toBe('john_doe');
      expect(encryptedData.email).toBe('john@example.com');
    });

    it('should use secure random number generation', async () => {
      await encryptionService.encryptData('test data');

      expect(crypto.randomBytes).toHaveBeenCalledWith(16); // IV length
    });

    it('should enforce minimum key sizes', async () => {
      await expect(
        encryptionService.generateKey('weak-key', 'aes-128-gcm')
      ).rejects.toThrow('Key size too small');
    });
  });
});
