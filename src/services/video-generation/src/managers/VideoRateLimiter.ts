/**
 * PAKE System - Video Rate Limiter
 * Single Responsibility: Rate limiting for video generation requests
 */

import { RateLimiterMemory } from 'rate-limiter-flexible';

export interface VideoRateLimiter {
  checkLimit(userId: string): Promise<boolean>;
  consumeLimit(userId: string): Promise<boolean>;
  resetLimit(userId: string): void;
  getRemainingLimit(userId: string): Promise<number>;
}

export class VideoRateLimiterImpl implements VideoRateLimiter {
  private rateLimiter: RateLimiterMemory;
  private logger: any;

  constructor(logger: any, options?: any) {
    this.logger = logger;
    this.rateLimiter = new RateLimiterMemory({
      keyPrefix: 'video_gen',
      points: options?.points || 10, // Number of requests
      duration: options?.duration || 60, // Per 60 seconds
    });
  }

  async checkLimit(userId: string): Promise<boolean> {
    try {
      const result = await this.rateLimiter.get(userId);
      return result === null || result.remainingPoints > 0;
    } catch (error) {
      this.logger.error('Rate limit check failed', { userId, error: error.message });
      return true; // Allow on error
    }
  }

  async consumeLimit(userId: string): Promise<boolean> {
    try {
      await this.rateLimiter.consume(userId);
      return true;
    } catch (error) {
      this.logger.warn('Rate limit exceeded', { userId });
      return false;
    }
  }

  resetLimit(userId: string): void {
    this.rateLimiter.delete(userId);
    this.logger.info('Rate limit reset', { userId });
  }

  async getRemainingLimit(userId: string): Promise<number> {
    try {
      const result = await this.rateLimiter.get(userId);
      return result ? result.remainingPoints : this.rateLimiter.points;
    } catch (error) {
      this.logger.error('Failed to get remaining limit', { userId, error: error.message });
      return 0;
    }
  }
}
