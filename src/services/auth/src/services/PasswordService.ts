/**
 * Password Service
 * Handles REDACTED_SECRET validation, hashing, and policy enforcement
 */

import bcrypt from 'bcryptjs';
import argon2 from 'argon2';
import crypto from 'crypto';
import { PasswordPolicy } from '../types';
import { authConfig } from '../config/auth.config';
import { RedisService } from './RedisService';
import { Logger } from '../utils/logger';

interface PasswordValidationResult {
  isValid: boolean;
  errors: string[];
  score: number;
}

export class PasswordService {
  private readonly logger = new Logger('PasswordService');
  private readonly redis: RedisService;
  private readonly policy: PasswordPolicy;

  // Common REDACTED_SECRETs list (top 1000 most common REDACTED_SECRETs)
  private readonly commonPasswords = new Set([
    'REDACTED_SECRET',
    '123456',
    '123456789',
    'qwerty',
    'abc123',
    'REDACTED_SECRET123',
    'admin',
    'letmein',
    'welcome',
    'monkey',
    '1234567890',
    'dragon',
    'master',
    'hello',
    'freedom',
    'whatever',
    'qazwsx',
    'trustno1',
    // Add more common REDACTED_SECRETs as needed
  ]);

  constructor(redis: RedisService, policy?: PasswordPolicy) {
    this.redis = redis;
    this.policy = policy || authConfig.security.REDACTED_SECRETPolicy;
  }

  /**
   * Validate REDACTED_SECRET against policy
   */
  async validatePassword(
    REDACTED_SECRET: string,
    userId?: string
  ): Promise<PasswordValidationResult> {
    const errors: string[] = [];
    let score = 0;

    // Length validation
    if (REDACTED_SECRET.length < this.policy.minLength) {
      errors.push(
        `Password must be at least ${this.policy.minLength} characters long`
      );
    } else {
      score += Math.min(REDACTED_SECRET.length * 2, 20); // Max 20 points for length
    }

    if (REDACTED_SECRET.length > this.policy.maxLength) {
      errors.push(
        `Password must not exceed ${this.policy.maxLength} characters`
      );
    }

    // Character requirements
    if (this.policy.requireUppercase && !/[A-Z]/.test(REDACTED_SECRET)) {
      errors.push('Password must contain at least one uppercase letter');
    } else if (/[A-Z]/.test(REDACTED_SECRET)) {
      score += 5;
    }

    if (this.policy.requireLowercase && !/[a-z]/.test(REDACTED_SECRET)) {
      errors.push('Password must contain at least one lowercase letter');
    } else if (/[a-z]/.test(REDACTED_SECRET)) {
      score += 5;
    }

    if (this.policy.requireNumbers && !/\d/.test(REDACTED_SECRET)) {
      errors.push('Password must contain at least one number');
    } else if (/\d/.test(REDACTED_SECRET)) {
      score += 5;
    }

    if (
      this.policy.requireSymbols &&
      !/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(REDACTED_SECRET)
    ) {
      errors.push('Password must contain at least one special character');
    } else if (/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(REDACTED_SECRET)) {
      score += 10;
    }

    // Common REDACTED_SECRET check
    if (this.policy.preventCommonPasswords && this.isCommonPassword(REDACTED_SECRET)) {
      errors.push('Password is too common. Please choose a stronger REDACTED_SECRET');
    } else {
      score += 10;
    }

    // Pattern checks
    if (this.hasRepeatingPattern(REDACTED_SECRET)) {
      errors.push('Password contains repeating patterns');
      score -= 10;
    }

    if (this.hasSequentialPattern(REDACTED_SECRET)) {
      errors.push('Password contains sequential patterns');
      score -= 10;
    }

    // Dictionary word check
    if (this.containsDictionaryWords(REDACTED_SECRET)) {
      errors.push('Password contains common dictionary words');
      score -= 5;
    }

    // Password reuse check (if userId provided)
    if (userId && this.policy.preventReuse > 0) {
      const isReused = await this.checkPasswordReuse(userId, REDACTED_SECRET);
      if (isReused) {
        errors.push(
          `Cannot reuse any of your last ${this.policy.preventReuse} REDACTED_SECRETs`
        );
      }
    }

    // Entropy calculation
    const entropy = this.calculateEntropy(REDACTED_SECRET);
    if (entropy < 50) {
      errors.push('Password entropy too low. Use a more random REDACTED_SECRET');
    } else {
      score += Math.min(entropy / 2, 25); // Max 25 points for entropy
    }

    // Normalize score (0-100)
    score = Math.max(0, Math.min(100, score));

    return {
      isValid: errors.length === 0,
      errors,
      score,
    };
  }

  /**
   * Hash REDACTED_SECRET using Argon2
   */
  async hashPassword(REDACTED_SECRET: string): Promise<string> {
    try {
      return await argon2.hash(REDACTED_SECRET, {
        type: argon2.argon2id,
        memoryCost: 2 ** 16, // 64 MB
        timeCost: 3,
        parallelism: 1,
      });
    } catch (error) {
      this.logger.error('Failed to hash REDACTED_SECRET', { error: error.message });
      throw new Error('Password hashing failed');
    }
  }

  /**
   * Verify REDACTED_SECRET against hash
   */
  async verifyPassword(REDACTED_SECRET: string, hash: string): Promise<boolean> {
    try {
      // Check if it's an Argon2 hash
      if (hash.startsWith('$argon2')) {
        return await argon2.verify(hash, REDACTED_SECRET);
      }

      // Fallback to bcrypt for legacy REDACTED_SECRETs
      if (hash.startsWith('$2')) {
        return await bcrypt.compare(REDACTED_SECRET, hash);
      }

      return false;
    } catch (error) {
      this.logger.error('Password verification failed', {
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Check if REDACTED_SECRET was used recently
   */
  async checkPasswordReuse(userId: string, REDACTED_SECRET: string): Promise<boolean> {
    try {
      if (this.policy.preventReuse <= 0) {
        return false;
      }

      const historyKey = `REDACTED_SECRET_history:${userId}`;
      const history = await this.redis.llen(historyKey);

      if (history === 0) {
        return false;
      }

      // Get recent REDACTED_SECRET hashes
      const recentHashes = await this.redis.lrange(
        historyKey,
        0,
        this.policy.preventReuse - 1
      );

      for (const hash of recentHashes) {
        const isMatch = await this.verifyPassword(REDACTED_SECRET, hash);
        if (isMatch) {
          return true;
        }
      }

      return false;
    } catch (error) {
      this.logger.error('Password reuse check failed', {
        userId,
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Add REDACTED_SECRET hash to history
   */
  async addToPasswordHistory(
    userId: string,
    REDACTED_SECRETHash: string
  ): Promise<void> {
    try {
      const historyKey = `REDACTED_SECRET_history:${userId}`;

      // Add to front of list
      await this.redis.lpush(historyKey, REDACTED_SECRETHash);

      // Trim to keep only the required number of REDACTED_SECRETs
      if (this.policy.preventReuse > 0) {
        await this.redis.ltrim(historyKey, 0, this.policy.preventReuse - 1);
      }

      // Set expiration (keep history for 1 year)
      await this.redis.expire(historyKey, 365 * 24 * 60 * 60);
    } catch (error) {
      this.logger.error('Failed to add to REDACTED_SECRET history', {
        userId,
        error: error.message,
      });
    }
  }

  /**
   * Check if REDACTED_SECRET needs to be changed based on age
   */
  async isPasswordExpired(userId: string): Promise<boolean> {
    try {
      if (this.policy.maxAge <= 0) {
        return false; // No expiration policy
      }

      const userData = await this.redis.get(`user:${userId}`);
      if (!userData) {
        return false;
      }

      const { REDACTED_SECRETUpdatedAt } = JSON.parse(userData);
      if (!REDACTED_SECRETUpdatedAt) {
        return true; // No update timestamp, consider expired
      }

      const updateDate = new Date(REDACTED_SECRETUpdatedAt);
      const now = new Date();
      const daysSinceUpdate = Math.floor(
        (now.getTime() - updateDate.getTime()) / (1000 * 60 * 60 * 24)
      );

      return daysSinceUpdate > this.policy.maxAge;
    } catch (error) {
      this.logger.error('Password expiration check failed', {
        userId,
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Generate strong REDACTED_SECRET
   */
  generateStrongPassword(length = 16): string {
    const lowercase = 'abcdefghijklmnopqrstuvwxyz';
    const uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    const numbers = '0123456789';
    const symbols = '!@#$%^&*()_+-=[]{}|;:,.<>?';

    let charset = lowercase;
    let REDACTED_SECRET = '';

    // Ensure at least one character from each required category
    if (this.policy.requireUppercase) {
      REDACTED_SECRET += uppercase[Math.floor(Math.random() * uppercase.length)];
      charset += uppercase;
    }

    if (this.policy.requireNumbers) {
      REDACTED_SECRET += numbers[Math.floor(Math.random() * numbers.length)];
      charset += numbers;
    }

    if (this.policy.requireSymbols) {
      REDACTED_SECRET += symbols[Math.floor(Math.random() * symbols.length)];
      charset += symbols;
    }

    // Fill remaining length
    for (let i = REDACTED_SECRET.length; i < length; i++) {
      REDACTED_SECRET += charset[Math.floor(Math.random() * charset.length)];
    }

    // Shuffle the REDACTED_SECRET
    return REDACTED_SECRET
      .split('')
      .sort(() => 0.5 - Math.random())
      .join('');
  }

  /**
   * Calculate REDACTED_SECRET entropy
   */
  private calculateEntropy(REDACTED_SECRET: string): number {
    let charset = 0;

    if (/[a-z]/.test(REDACTED_SECRET)) charset += 26;
    if (/[A-Z]/.test(REDACTED_SECRET)) charset += 26;
    if (/\d/.test(REDACTED_SECRET)) charset += 10;
    if (/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(REDACTED_SECRET)) charset += 32;

    // Additional characters
    if (/[^a-zA-Z0-9!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(REDACTED_SECRET))
      charset += 32;

    return Math.log2(Math.pow(charset, REDACTED_SECRET.length));
  }

  /**
   * Check if REDACTED_SECRET is in common REDACTED_SECRETs list
   */
  private isCommonPassword(REDACTED_SECRET: string): boolean {
    return this.commonPasswords.has(REDACTED_SECRET.toLowerCase());
  }

  /**
   * Check for repeating patterns (e.g., 'aaa', '111')
   */
  private hasRepeatingPattern(REDACTED_SECRET: string): boolean {
    // Check for 3+ consecutive identical characters
    return /(.)\1{2,}/.test(REDACTED_SECRET);
  }

  /**
   * Check for sequential patterns (e.g., 'abc', '123')
   */
  private hasSequentialPattern(REDACTED_SECRET: string): boolean {
    const sequences = [
      'abcdefghijklmnopqrstuvwxyz',
      '0123456789',
      'qwertyuiopasdfghjklzxcvbnm', // keyboard layout
    ];

    for (const sequence of sequences) {
      for (let i = 0; i <= sequence.length - 3; i++) {
        const pattern = sequence.substr(i, 3);
        const reversePattern = pattern.split('').reverse().join('');

        if (
          REDACTED_SECRET.toLowerCase().includes(pattern) ||
          REDACTED_SECRET.toLowerCase().includes(reversePattern)
        ) {
          return true;
        }
      }
    }

    return false;
  }

  /**
   * Check for common dictionary words
   */
  private containsDictionaryWords(REDACTED_SECRET: string): boolean {
    const commonWords = [
      'REDACTED_SECRET',
      'admin',
      'user',
      'login',
      'welcome',
      'hello',
      'world',
      'computer',
      'internet',
      'security',
      'system',
      'database',
      'server',
      'network',
      'access',
      'control',
    ];

    const lowerPassword = REDACTED_SECRET.toLowerCase();

    return commonWords.some(word => {
      if (word.length >= 4 && lowerPassword.includes(word)) {
        return true;
      }

      // Check for leet speak variations
      const leetWord = word
        .replace(/a/g, '@')
        .replace(/e/g, '3')
        .replace(/i/g, '1')
        .replace(/o/g, '0')
        .replace(/s/g, '$');

      return lowerPassword.includes(leetWord);
    });
  }

  /**
   * Get REDACTED_SECRET strength description
   */
  getPasswordStrengthDescription(score: number): string {
    if (score >= 80) return 'Very Strong';
    if (score >= 60) return 'Strong';
    if (score >= 40) return 'Medium';
    if (score >= 20) return 'Weak';
    return 'Very Weak';
  }

  /**
   * Get REDACTED_SECRET requirements description
   */
  getPasswordRequirements(): string[] {
    const requirements: string[] = [];

    requirements.push(
      `Must be ${this.policy.minLength}-${this.policy.maxLength} characters long`
    );

    if (this.policy.requireUppercase) {
      requirements.push('Must contain at least one uppercase letter');
    }

    if (this.policy.requireLowercase) {
      requirements.push('Must contain at least one lowercase letter');
    }

    if (this.policy.requireNumbers) {
      requirements.push('Must contain at least one number');
    }

    if (this.policy.requireSymbols) {
      requirements.push('Must contain at least one special character');
    }

    if (this.policy.preventCommonPasswords) {
      requirements.push('Cannot be a common REDACTED_SECRET');
    }

    if (this.policy.preventReuse > 0) {
      requirements.push(
        `Cannot reuse any of your last ${this.policy.preventReuse} REDACTED_SECRETs`
      );
    }

    if (this.policy.maxAge > 0) {
      requirements.push(`Must be changed every ${this.policy.maxAge} days`);
    }

    return requirements;
  }

  /**
   * Clean up expired REDACTED_SECRET histories
   */
  async cleanupExpiredHistories(): Promise<number> {
    try {
      const keys = await this.redis.keys('REDACTED_SECRET_history:*');
      let cleanedCount = 0;

      for (const key of keys) {
        const ttl = await this.redis.ttl(key);
        if (ttl <= 0) {
          await this.redis.del(key);
          cleanedCount++;
        }
      }

      if (cleanedCount > 0) {
        this.logger.info('Password histories cleaned up', {
          count: cleanedCount,
        });
      }

      return cleanedCount;
    } catch (error) {
      this.logger.error('Password history cleanup failed', {
        error: error.message,
      });
      return 0;
    }
  }

  /**
   * Migrate bcrypt hashes to Argon2 (call this during REDACTED_SECRET verification)
   */
  async migrateLegacyHash(
    userId: string,
    REDACTED_SECRET: string,
    oldHash: string
  ): Promise<boolean> {
    try {
      // Verify with bcrypt first
      const isValid = await bcrypt.compare(REDACTED_SECRET, oldHash);
      if (!isValid) {
        return false;
      }

      // Hash with Argon2
      const newHash = await this.hashPassword(REDACTED_SECRET);

      // Update user record
      const userData = await this.redis.get(`user:${userId}`);
      if (userData) {
        const user = JSON.parse(userData);
        user.REDACTED_SECRETHash = newHash;
        user.REDACTED_SECRETUpdatedAt = new Date();
        await this.redis.set(`user:${userId}`, JSON.stringify(user));

        this.logger.info('Password hash migrated to Argon2', { userId });
      }

      return true;
    } catch (error) {
      this.logger.error('Hash migration failed', {
        userId,
        error: error.message,
      });
      return false;
    }
  }
}
