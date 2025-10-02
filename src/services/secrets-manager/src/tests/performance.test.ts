import { describe, it, expect, beforeAll, afterAll, vi } from 'vitest';
import { SecretsManagerSDK } from '../services/SecretsManagerSDK';
import { EncryptionService } from '../services/EncryptionService';
import { VaultService } from '../services/VaultService';
import { HSMService } from '../services/HSMService';
import { SDKConfig, EncryptionConfig } from '../types/secrets.types';

// Mock external dependencies for consistent performance testing
vi.mock('node-vault');
vi.mock('crypto');
vi.mock('fs');

describe('Secrets Management Performance Tests', () => {
  let sdk: SecretsManagerSDK;
  let encryptionService: EncryptionService;
  let vaultService: VaultService;

  beforeAll(async () => {
    // Setup optimized configuration for performance testing
    const config: SDKConfig = {
      vault: {
        endpoint: 'https://vault-perf.example.com:8200',
        token: 'perf-test-token',
        engines: {
          kv: { name: 'secret', version: 2, path: 'secret/' },
          transit: { name: 'transit', path: 'transit/' },
        },
        auth: { method: 'token', token: 'perf-test-token' },
      },
      cache: {
        ttl: 600, // Longer TTL for performance testing
        maxSize: 10000,
        encryptCached: true,
      },
      retry: {
        maxAttempts: 1, // Reduce retries for faster testing
        baseDelay: 100,
        maxDelay: 1000,
      },
      validation: {
        enforceSchema: false, // Disable for performance
        allowedPaths: ['/*'], // Allow all paths
      },
    };

    const encryptionConfig: EncryptionConfig = {
      algorithms: {
        symmetric: 'aes-256-gcm',
        asymmetric: 'rsa-4096',
        hash: 'sha256',
        kdf: 'argon2id',
      },
      keys: {
        masterKeyId: 'perf-master-key',
        keyDerivationParams: {
          memory: 32 * 1024, // Reduced for performance
          iterations: 1,
          parallelism: 2,
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
        enabled: false, // Use mock for consistent performance
        provider: 'Mock',
        config: {},
      },
    };

    // Initialize services
    vaultService = new VaultService(config.vault);
    const hsmService = new HSMService(encryptionConfig.hsm, true);
    encryptionService = new EncryptionService(encryptionConfig, hsmService);
    sdk = new SecretsManagerSDK(config);

    // Mock all external calls for consistent performance measurement
    await mockExternalServices();

    await Promise.all([
      vaultService.authenticate(),
      encryptionService.initialize(),
      sdk.initialize(),
    ]);
  });

  afterAll(async () => {
    // Cleanup
  });

  async function mockExternalServices() {
    // Mock Vault client responses
    const mockVaultClient = {
      health: vi.fn().mockResolvedValue({ initialized: true, sealed: false }),
      read: vi.fn().mockResolvedValue({
        data: {
          data: { key: 'value' },
          metadata: { version: 1, created_time: '2023-01-01T00:00:00Z' },
        },
      }),
      write: vi.fn().mockResolvedValue({ data: { version: 1 } }),
      encrypt: vi
        .fn()
        .mockResolvedValue({ data: { ciphertext: 'vault:v1:encrypted' } }),
      decrypt: vi.fn().mockResolvedValue({
        data: { plaintext: Buffer.from('decrypted').toString('base64') },
      }),
    };

    // Mock crypto functions for consistent performance
    const mockCrypto = await import('crypto');
    (mockCrypto.randomBytes as any).mockReturnValue(
      Buffer.from('1234567890123456')
    );

    const mockCipher = {
      update: vi.fn().mockReturnValue(Buffer.from('encrypted')),
      final: vi.fn().mockReturnValue(Buffer.from('')),
      getAuthTag: vi.fn().mockReturnValue(Buffer.from('authTag')),
    };

    const mockDecipher = {
      setAuthTag: vi.fn(),
      update: vi.fn().mockReturnValue(Buffer.from('decrypted')),
      final: vi.fn().mockReturnValue(Buffer.from('')),
    };

    (mockCrypto.createCipher as any).mockReturnValue(mockCipher);
    (mockCrypto.createDecipher as any).mockReturnValue(mockDecipher);
  }

  describe('Secret Retrieval Performance', () => {
    it('should retrieve secret within 10ms requirement', async () => {
      const iterations = 100;
      const durations: number[] = [];

      for (let i = 0; i < iterations; i++) {
        const startTime = performance.now();
        await sdk.getSecret(`perf/test-${i}`);
        const duration = performance.now() - startTime;
        durations.push(duration);
      }

      const averageTime = durations.reduce((sum, d) => sum + d, 0) / iterations;
      const maxTime = Math.max(...durations);
      const p95Time = durations.sort((a, b) => a - b)[
        Math.floor(iterations * 0.95)
      ];

      console.log(`Secret Retrieval Performance:
        Average: ${averageTime.toFixed(2)}ms
        Maximum: ${maxTime.toFixed(2)}ms
        95th Percentile: ${p95Time.toFixed(2)}ms`);

      expect(averageTime).toBeLessThan(10);
      expect(p95Time).toBeLessThan(15);
      expect(maxTime).toBeLessThan(25);
    });

    it('should handle cache hits with <1ms response time', async () => {
      const secretPath = 'perf/cache-test';

      // Prime the cache
      await sdk.getSecret(secretPath);

      const iterations = 100;
      const durations: number[] = [];

      for (let i = 0; i < iterations; i++) {
        const startTime = performance.now();
        await sdk.getSecret(secretPath);
        const duration = performance.now() - startTime;
        durations.push(duration);
      }

      const averageTime = durations.reduce((sum, d) => sum + d, 0) / iterations;

      console.log(`Cache Hit Performance: ${averageTime.toFixed(2)}ms average`);

      expect(averageTime).toBeLessThan(1);
    });

    it('should maintain performance under concurrent load', async () => {
      const concurrentRequests = 50;
      const startTime = performance.now();

      const promises = Array.from({ length: concurrentRequests }, (_, i) =>
        sdk.getSecret(`perf/concurrent-${i}`)
      );

      await Promise.all(promises);

      const totalTime = performance.now() - startTime;
      const averageTime = totalTime / concurrentRequests;

      console.log(`Concurrent Load Performance:
        Total Time: ${totalTime.toFixed(2)}ms for ${concurrentRequests} requests
        Average Time per Request: ${averageTime.toFixed(2)}ms`);

      expect(averageTime).toBeLessThan(15);
      expect(totalTime).toBeLessThan(500); // Total time for all concurrent requests
    });
  });

  describe('Encryption Performance', () => {
    it('should encrypt data within 10ms requirement', async () => {
      const testData = 'sensitive data to encrypt'.repeat(10); // ~260 bytes
      const iterations = 100;
      const durations: number[] = [];

      for (let i = 0; i < iterations; i++) {
        const startTime = performance.now();
        await encryptionService.encryptData(testData);
        const duration = performance.now() - startTime;
        durations.push(duration);
      }

      const averageTime = durations.reduce((sum, d) => sum + d, 0) / iterations;
      const maxTime = Math.max(...durations);

      console.log(`Encryption Performance:
        Average: ${averageTime.toFixed(2)}ms
        Maximum: ${maxTime.toFixed(2)}ms`);

      expect(averageTime).toBeLessThan(10);
      expect(maxTime).toBeLessThan(20);
    });

    it('should decrypt data within 10ms requirement', async () => {
      const testData = 'sensitive data to decrypt'.repeat(10);

      // Pre-encrypt data for decryption test
      const encryptionResult = await encryptionService.encryptData(testData);

      const iterations = 100;
      const durations: number[] = [];

      for (let i = 0; i < iterations; i++) {
        const startTime = performance.now();
        await encryptionService.decryptData(encryptionResult);
        const duration = performance.now() - startTime;
        durations.push(duration);
      }

      const averageTime = durations.reduce((sum, d) => sum + d, 0) / iterations;
      const maxTime = Math.max(...durations);

      console.log(`Decryption Performance:
        Average: ${averageTime.toFixed(2)}ms
        Maximum: ${maxTime.toFixed(2)}ms`);

      expect(averageTime).toBeLessThan(10);
      expect(maxTime).toBeLessThan(20);
    });

    it('should handle large data encryption efficiently', async () => {
      const dataSizes = [1024, 10240, 102400]; // 1KB, 10KB, 100KB

      for (const size of dataSizes) {
        const largeData = 'x'.repeat(size);

        const startTime = performance.now();
        const encrypted = await encryptionService.encryptData(largeData);
        const encryptTime = performance.now() - startTime;

        const decryptStartTime = performance.now();
        const decrypted = await encryptionService.decryptData(encrypted);
        const decryptTime = performance.now() - decryptStartTime;

        console.log(`Large Data Performance (${size} bytes):
          Encryption: ${encryptTime.toFixed(2)}ms
          Decryption: ${decryptTime.toFixed(2)}ms`);

        // Performance should scale reasonably with data size
        expect(encryptTime).toBeLessThan(size / 100); // Rough scaling expectation
        expect(decryptTime).toBeLessThan(size / 100);
        expect(decrypted).toBe(largeData);
      }
    });

    it('should perform field-level encryption efficiently', async () => {
      const testObject = {
        id: '12345',
        name: 'John Doe',
        email: 'john@example.com',
        ssn: '123-45-6789',
        phone: '+1-555-0123',
        address: '123 Main St, City, State 12345',
        salary: 75000,
        notes: 'Additional notes about the employee'.repeat(10),
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
        {
          fieldName: 'phone',
          algorithm: 'aes-256-gcm' as const,
          keyId: 'pii-key',
        },
        {
          fieldName: 'notes',
          algorithm: 'aes-256-gcm' as const,
          keyId: 'pii-key',
        },
      ];

      const iterations = 50;
      const durations: number[] = [];

      for (let i = 0; i < iterations; i++) {
        const startTime = performance.now();
        await encryptionService.encryptFields(testObject, fieldsToEncrypt);
        const duration = performance.now() - startTime;
        durations.push(duration);
      }

      const averageTime = durations.reduce((sum, d) => sum + d, 0) / iterations;

      console.log(`Field-Level Encryption Performance:
        Average: ${averageTime.toFixed(2)}ms for ${fieldsToEncrypt.length} fields`);

      expect(averageTime).toBeLessThan(50); // Should be reasonable for multiple fields
    });
  });

  describe('Throughput Performance', () => {
    it('should handle high-volume secret operations', async () => {
      const operationCount = 1000;
      const batchSize = 100;
      const batches = Math.ceil(operationCount / batchSize);

      const startTime = performance.now();

      for (let batch = 0; batch < batches; batch++) {
        const batchPromises = Array.from(
          { length: Math.min(batchSize, operationCount - batch * batchSize) },
          (_, i) => {
            const index = batch * batchSize + i;
            return sdk.getSecret(`perf/volume-test-${index}`);
          }
        );

        await Promise.all(batchPromises);
      }

      const totalTime = performance.now() - startTime;
      const throughput = operationCount / (totalTime / 1000); // Operations per second

      console.log(`High-Volume Performance:
        Total Operations: ${operationCount}
        Total Time: ${totalTime.toFixed(2)}ms
        Throughput: ${throughput.toFixed(2)} operations/second`);

      expect(throughput).toBeGreaterThan(100); // Minimum 100 ops/sec
    });

    it('should maintain consistent performance over time', async () => {
      const testDuration = 10000; // 10 seconds
      const interval = 100; // Test every 100ms
      const iterations = testDuration / interval;

      const throughputSamples: number[] = [];

      for (let i = 0; i < iterations; i++) {
        const iterationStart = performance.now();

        // Perform operations for this interval
        const promises = Array.from({ length: 10 }, (_, j) =>
          sdk.getSecret(`perf/consistency-test-${i}-${j}`)
        );

        await Promise.all(promises);

        const iterationTime = performance.now() - iterationStart;
        const iterationThroughput = 10 / (iterationTime / 1000);
        throughputSamples.push(iterationThroughput);

        // Wait for next interval
        await new Promise(resolve =>
          setTimeout(resolve, Math.max(0, interval - iterationTime))
        );
      }

      const averageThroughput =
        throughputSamples.reduce((sum, t) => sum + t, 0) /
        throughputSamples.length;
      const minThroughput = Math.min(...throughputSamples);
      const maxThroughput = Math.max(...throughputSamples);
      const stdDev = Math.sqrt(
        throughputSamples.reduce(
          (sum, t) => sum + Math.pow(t - averageThroughput, 2),
          0
        ) / throughputSamples.length
      );

      console.log(`Performance Consistency over ${testDuration / 1000}s:
        Average Throughput: ${averageThroughput.toFixed(2)} ops/sec
        Min Throughput: ${minThroughput.toFixed(2)} ops/sec
        Max Throughput: ${maxThroughput.toFixed(2)} ops/sec
        Standard Deviation: ${stdDev.toFixed(2)}`);

      // Performance should be consistent (low standard deviation relative to mean)
      expect(stdDev / averageThroughput).toBeLessThan(0.3); // Less than 30% coefficient of variation
      expect(minThroughput).toBeGreaterThan(averageThroughput * 0.7); // Min should be at least 70% of average
    });
  });

  describe('Memory Performance', () => {
    it('should not leak memory during extended operation', async () => {
      const initialMemory = process.memoryUsage().heapUsed;

      // Perform many operations
      for (let i = 0; i < 1000; i++) {
        await sdk.getSecret(`perf/memory-test-${i % 100}`); // Reuse paths to test caching

        if (i % 100 === 0) {
          // Force garbage collection if available
          if (global.gc) {
            global.gc();
          }
        }
      }

      const finalMemory = process.memoryUsage().heapUsed;
      const memoryIncrease = finalMemory - initialMemory;
      const memoryIncreaseKB = memoryIncrease / 1024;

      console.log(`Memory Usage:
        Initial: ${(initialMemory / 1024 / 1024).toFixed(2)} MB
        Final: ${(finalMemory / 1024 / 1024).toFixed(2)} MB
        Increase: ${memoryIncreaseKB.toFixed(2)} KB`);

      // Memory increase should be reasonable (less than 10MB for this test)
      expect(memoryIncreaseKB).toBeLessThan(10240); // 10MB
    });

    it('should efficiently handle cache memory usage', async () => {
      const cacheSize = 1000;
      const secretSize = 1024; // 1KB per secret

      // Fill cache with secrets
      const secrets = Array.from({ length: cacheSize }, (_, i) => ({
        path: `perf/cache-memory-${i}`,
        data: 'x'.repeat(secretSize),
      }));

      const startMemory = process.memoryUsage().heapUsed;

      for (const secret of secrets) {
        await sdk.storeSecret(secret.path, { value: secret.data });
        await sdk.getSecret(secret.path); // Cache the secret
      }

      const endMemory = process.memoryUsage().heapUsed;
      const memoryUsed = endMemory - startMemory;
      const memoryPerSecret = memoryUsed / cacheSize;

      console.log(`Cache Memory Efficiency:
        Cached Secrets: ${cacheSize}
        Total Memory Used: ${(memoryUsed / 1024 / 1024).toFixed(2)} MB
        Memory per Secret: ${(memoryPerSecret / 1024).toFixed(2)} KB`);

      // Memory usage should be reasonable (accounting for overhead)
      expect(memoryPerSecret).toBeLessThan(secretSize * 3); // Allow for 3x overhead
    });
  });

  describe('Stress Testing', () => {
    it('should handle burst traffic without degradation', async () => {
      const burstSize = 200;
      const normalSize = 50;

      // Measure normal performance
      let startTime = performance.now();
      await Promise.all(
        Array.from({ length: normalSize }, (_, i) =>
          sdk.getSecret(`perf/normal-${i}`)
        )
      );
      const normalTime = performance.now() - startTime;
      const normalAverage = normalTime / normalSize;

      // Wait a bit
      await new Promise(resolve => setTimeout(resolve, 100));

      // Measure burst performance
      startTime = performance.now();
      await Promise.all(
        Array.from({ length: burstSize }, (_, i) =>
          sdk.getSecret(`perf/burst-${i}`)
        )
      );
      const burstTime = performance.now() - startTime;
      const burstAverage = burstTime / burstSize;

      console.log(`Burst Traffic Performance:
        Normal (${normalSize} ops): ${normalAverage.toFixed(2)}ms average
        Burst (${burstSize} ops): ${burstAverage.toFixed(2)}ms average
        Degradation: ${((burstAverage / normalAverage - 1) * 100).toFixed(1)}%`);

      // Performance degradation should be minimal (less than 50%)
      expect(burstAverage).toBeLessThan(normalAverage * 1.5);
    });

    it('should recover from temporary service disruption', async () => {
      // Measure baseline performance
      const baselineStart = performance.now();
      await sdk.getSecret('perf/baseline-test');
      const baselineTime = performance.now() - baselineStart;

      // Simulate service disruption
      const originalMethod = vaultService.getSecret;
      vaultService.getSecret = vi
        .fn()
        .mockRejectedValue(new Error('Service disruption'));

      // Wait for disruption to take effect
      await new Promise(resolve => setTimeout(resolve, 100));

      // Restore service
      vaultService.getSecret = originalMethod;

      // Measure recovery performance
      const recoveryStart = performance.now();
      await sdk.getSecret('perf/recovery-test');
      const recoveryTime = performance.now() - recoveryStart;

      console.log(`Service Recovery Performance:
        Baseline: ${baselineTime.toFixed(2)}ms
        Recovery: ${recoveryTime.toFixed(2)}ms`);

      // Recovery should be reasonably fast
      expect(recoveryTime).toBeLessThan(baselineTime * 2);
    });
  });
});
