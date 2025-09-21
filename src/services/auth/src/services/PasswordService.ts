/**
 * Password Service
 * Handles password validation, hashing, and policy enforcement
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

  // Common passwords list (top 1000 most common passwords)
  private readonly commonPasswords = new Set([
    'password',
    '123456',
    '123456789',
    'qwerty',
    'abc123',
    'password123',
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
    // Add more common passwords as needed
  ]);

  constructor(redis: RedisService, policy?: PasswordPolicy) {
    this.redis = redis;
    this.policy = policy || authConfig.security.passwordPolicy;
  }

  /**
   * Validate password against policy
   */
  async validatePassword(
    password: string,
    userId?: string
  ): Promise<PasswordValidationResult> {
    const errors: string[] = [];
    let score = 0;

    // Length validation
    if (password.length < this.policy.minLength) {
      errors.push(
        `Password must be at least ${this.policy.minLength} characters long`
      );
    } else {
      score += Math.min(password.length * 2, 20); // Max 20 points for length
    }

    if (password.length > this.policy.maxLength) {
      errors.push(
        `Password must not exceed ${this.policy.maxLength} characters`
      );
    }

    // Character requirements
    if (this.policy.requireUppercase && !/[A-Z]/.test(password)) {
      errors.push('Password must contain at least one uppercase letter');
    } else if (/[A-Z]/.test(password)) {
      score += 5;
    }

    if (this.policy.requireLowercase && !/[a-z]/.test(password)) {
      errors.push('Password must contain at least one lowercase letter');
    } else if (/[a-z]/.test(password)) {
      score += 5;
    }

    if (this.policy.requireNumbers && !/\d/.test(password)) {
      errors.push('Password must contain at least one number');
    } else if (/\d/.test(password)) {
      score += 5;
    }

    if (
      this.policy.requireSymbols &&
      !/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)
    ) {
      errors.push('Password must contain at least one special character');
    } else if (/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
      score += 10;
    }

    // Common password check
    if (this.policy.preventCommonPasswords && this.isCommonPassword(password)) {
      errors.push('Password is too common. Please choose a stronger password');
    } else {
      score += 10;
    }

    // Pattern checks
    if (this.hasRepeatingPattern(password)) {
      errors.push('Password contains repeating patterns');
      score -= 10;
    }

    if (this.hasSequentialPattern(password)) {
      errors.push('Password contains sequential patterns');
      score -= 10;
    }

    // Dictionary word check
    if (this.containsDictionaryWords(password)) {
      errors.push('Password contains common dictionary words');
      score -= 5;
    }

    // Password reuse check (if userId provided)
    if (userId && this.policy.preventReuse > 0) {
      const isReused = await this.checkPasswordReuse(userId, password);
      if (isReused) {
        errors.push(
          `Cannot reuse any of your last ${this.policy.preventReuse} passwords`
        );
      }
    }

    // Entropy calculation
    const entropy = this.calculateEntropy(password);
    if (entropy < 50) {
      errors.push('Password entropy too low. Use a more random password');
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
   * Hash password using Argon2
   */
  async hashPassword(password: string): Promise<string> {
    try {
      return await argon2.hash(password, {
        type: argon2.argon2id,
        memoryCost: 2 ** 16, // 64 MB
        timeCost: 3,
        parallelism: 1,
      });
    } catch (error) {
      this.logger.error('Failed to hash password', { error: error.message });
      throw new Error('Password hashing failed');
    }
  }

  /**
   * Verify password against hash
   */
  async verifyPassword(password: string, hash: string): Promise<boolean> {
    try {
      // Check if it's an Argon2 hash
      if (hash.startsWith('$argon2')) {
        return await argon2.verify(hash, password);
      }

      // Fallback to bcrypt for legacy passwords
      if (hash.startsWith('$2')) {
        return await bcrypt.compare(password, hash);
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
   * Check if password was used recently
   */
  async checkPasswordReuse(userId: string, password: string): Promise<boolean> {
    try {
      if (this.policy.preventReuse <= 0) {
        return false;
      }

      const historyKey = `password_history:${userId}`;
      const history = await this.redis.llen(historyKey);

      if (history === 0) {
        return false;
      }

      // Get recent password hashes
      const recentHashes = await this.redis.lrange(
        historyKey,
        0,
        this.policy.preventReuse - 1
      );

      for (const hash of recentHashes) {
        const isMatch = await this.verifyPassword(password, hash);
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
   * Add password hash to history
   */
  async addToPasswordHistory(
    userId: string,
    passwordHash: string
  ): Promise<void> {
    try {
      const historyKey = `password_history:${userId}`;

      // Add to front of list
      await this.redis.lpush(historyKey, passwordHash);

      // Trim to keep only the required number of passwords
      if (this.policy.preventReuse > 0) {
        await this.redis.ltrim(historyKey, 0, this.policy.preventReuse - 1);
      }

      // Set expiration (keep history for 1 year)
      await this.redis.expire(historyKey, 365 * 24 * 60 * 60);
    } catch (error) {
      this.logger.error('Failed to add to password history', {
        userId,
        error: error.message,
      });
    }
  }

  /**
   * Check if password needs to be changed based on age
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

      const { passwordUpdatedAt } = JSON.parse(userData);
      if (!passwordUpdatedAt) {
        return true; // No update timestamp, consider expired
      }

      const updateDate = new Date(passwordUpdatedAt);
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
   * Generate strong password
   */
  generateStrongPassword(length = 16): string {
    const lowercase = 'abcdefghijklmnopqrstuvwxyz';
    const uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    const numbers = '0123456789';
    const symbols = '!@#$%^&*()_+-=[]{}|;:,.<>?';

    let charset = lowercase;
    let password = '';

    // Ensure at least one character from each required category
    if (this.policy.requireUppercase) {
      password += uppercase[Math.floor(Math.random() * uppercase.length)];
      charset += uppercase;
    }

    if (this.policy.requireNumbers) {
      password += numbers[Math.floor(Math.random() * numbers.length)];
      charset += numbers;
    }

    if (this.policy.requireSymbols) {
      password += symbols[Math.floor(Math.random() * symbols.length)];
      charset += symbols;
    }

    // Fill remaining length
    for (let i = password.length; i < length; i++) {
      password += charset[Math.floor(Math.random() * charset.length)];
    }

    // Shuffle the password
    return password
      .split('')
      .sort(() => 0.5 - Math.random())
      .join('');
  }

  /**
   * Calculate password entropy
   */
  private calculateEntropy(password: string): number {
    let charset = 0;

    if (/[a-z]/.test(password)) charset += 26;
    if (/[A-Z]/.test(password)) charset += 26;
    if (/\d/.test(password)) charset += 10;
    if (/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) charset += 32;

    // Additional characters
    if (/[^a-zA-Z0-9!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password))
      charset += 32;

    return Math.log2(Math.pow(charset, password.length));
  }

  /**
   * Check if password is in common passwords list
   */
  private isCommonPassword(password: string): boolean {
    return this.commonPasswords.has(password.toLowerCase());
  }

  /**
   * Check for repeating patterns (e.g., 'aaa', '111')
   */
  private hasRepeatingPattern(password: string): boolean {
    // Check for 3+ consecutive identical characters
    return /(.)\1{2,}/.test(password);
  }

  /**
   * Check for sequential patterns (e.g., 'abc', '123')
   */
  private hasSequentialPattern(password: string): boolean {
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
          password.toLowerCase().includes(pattern) ||
          password.toLowerCase().includes(reversePattern)
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
  private containsDictionaryWords(password: string): boolean {
    const commonWords = [
      'password',
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

    const lowerPassword = password.toLowerCase();

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
   * Get password strength description
   */
  getPasswordStrengthDescription(score: number): string {
    if (score >= 80) return 'Very Strong';
    if (score >= 60) return 'Strong';
    if (score >= 40) return 'Medium';
    if (score >= 20) return 'Weak';
    return 'Very Weak';
  }

  /**
   * Get password requirements description
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
      requirements.push('Cannot be a common password');
    }

    if (this.policy.preventReuse > 0) {
      requirements.push(
        `Cannot reuse any of your last ${this.policy.preventReuse} passwords`
      );
    }

    if (this.policy.maxAge > 0) {
      requirements.push(`Must be changed every ${this.policy.maxAge} days`);
    }

    return requirements;
  }

  /**
   * Clean up expired password histories
   */
  async cleanupExpiredHistories(): Promise<number> {
    try {
      const keys = await this.redis.keys('password_history:*');
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
   * Migrate bcrypt hashes to Argon2 (call this during password verification)
   */
  async migrateLegacyHash(
    userId: string,
    password: string,
    oldHash: string
  ): Promise<boolean> {
    try {
      // Verify with bcrypt first
      const isValid = await bcrypt.compare(password, oldHash);
      if (!isValid) {
        return false;
      }

      // Hash with Argon2
      const newHash = await this.hashPassword(password);

      // Update user record
      const userData = await this.redis.get(`user:${userId}`);
      if (userData) {
        const user = JSON.parse(userData);
        user.passwordHash = newHash;
        user.passwordUpdatedAt = new Date();
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
