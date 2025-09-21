/**
 * Redis Service
 * Handles Redis connections and operations for session management and caching
 */

import Redis from 'redis';
import { redisConfig } from '../config/auth.config';
import { Logger } from '../utils/logger';

export class RedisService {
  private client: Redis.RedisClientType;
  private readonly logger = new Logger('RedisService');
  private isConnected = false;

  constructor() {
    this.client = Redis.createClient({
      socket: {
        host: redisConfig.host,
        port: redisConfig.port,
        reconnectStrategy: retries => Math.min(retries * 50, 1000),
      },
      REDACTED_SECRET: redisConfig.REDACTED_SECRET,
      database: redisConfig.db,
      commandsQueueMaxLength: 1000,
    });

    this.setupEventHandlers();
  }

  /**
   * Initialize Redis connection
   */
  async connect(): Promise<void> {
    try {
      if (!this.isConnected) {
        await this.client.connect();
        this.isConnected = true;
        this.logger.info('Redis connection established');
      }
    } catch (error) {
      this.logger.error('Failed to connect to Redis', { error: error.message });
      throw error;
    }
  }

  /**
   * Close Redis connection
   */
  async disconnect(): Promise<void> {
    try {
      if (this.isConnected) {
        await this.client.quit();
        this.isConnected = false;
        this.logger.info('Redis connection closed');
      }
    } catch (error) {
      this.logger.error('Error closing Redis connection', {
        error: error.message,
      });
    }
  }

  /**
   * Set a key-value pair
   */
  async set(key: string, value: string): Promise<void> {
    try {
      await this.client.set(this.prefixKey(key), value);
    } catch (error) {
      this.logger.error('Redis SET operation failed', {
        key,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Set a key-value pair with expiration
   */
  async setex(key: string, seconds: number, value: string): Promise<void> {
    try {
      await this.client.setEx(this.prefixKey(key), seconds, value);
    } catch (error) {
      this.logger.error('Redis SETEX operation failed', {
        key,
        seconds,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Get value by key
   */
  async get(key: string): Promise<string | null> {
    try {
      return await this.client.get(this.prefixKey(key));
    } catch (error) {
      this.logger.error('Redis GET operation failed', {
        key,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Delete key(s)
   */
  async del(...keys: string[]): Promise<number> {
    try {
      const prefixedKeys = keys.map(key => this.prefixKey(key));
      return await this.client.del(prefixedKeys);
    } catch (error) {
      this.logger.error('Redis DEL operation failed', {
        keys,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Check if key exists
   */
  async exists(key: string): Promise<number> {
    try {
      return await this.client.exists(this.prefixKey(key));
    } catch (error) {
      this.logger.error('Redis EXISTS operation failed', {
        key,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Set expiration on key
   */
  async expire(key: string, seconds: number): Promise<boolean> {
    try {
      return await this.client.expire(this.prefixKey(key), seconds);
    } catch (error) {
      this.logger.error('Redis EXPIRE operation failed', {
        key,
        seconds,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Get time to live for key
   */
  async ttl(key: string): Promise<number> {
    try {
      return await this.client.ttl(this.prefixKey(key));
    } catch (error) {
      this.logger.error('Redis TTL operation failed', {
        key,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Get keys matching pattern
   */
  async keys(pattern: string): Promise<string[]> {
    try {
      const keys = await this.client.keys(this.prefixKey(pattern));
      // Remove prefix from returned keys
      return keys.map(key => key.replace(redisConfig.keyPrefix, ''));
    } catch (error) {
      this.logger.error('Redis KEYS operation failed', {
        pattern,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Increment value
   */
  async incr(key: string): Promise<number> {
    try {
      return await this.client.incr(this.prefixKey(key));
    } catch (error) {
      this.logger.error('Redis INCR operation failed', {
        key,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Increment value by amount
   */
  async incrby(key: string, increment: number): Promise<number> {
    try {
      return await this.client.incrBy(this.prefixKey(key), increment);
    } catch (error) {
      this.logger.error('Redis INCRBY operation failed', {
        key,
        increment,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Hash operations
   */
  async hset(key: string, field: string, value: string): Promise<number> {
    try {
      return await this.client.hSet(this.prefixKey(key), field, value);
    } catch (error) {
      this.logger.error('Redis HSET operation failed', {
        key,
        field,
        error: error.message,
      });
      throw error;
    }
  }

  async hget(key: string, field: string): Promise<string | undefined> {
    try {
      return await this.client.hGet(this.prefixKey(key), field);
    } catch (error) {
      this.logger.error('Redis HGET operation failed', {
        key,
        field,
        error: error.message,
      });
      throw error;
    }
  }

  async hgetall(key: string): Promise<Record<string, string>> {
    try {
      return await this.client.hGetAll(this.prefixKey(key));
    } catch (error) {
      this.logger.error('Redis HGETALL operation failed', {
        key,
        error: error.message,
      });
      throw error;
    }
  }

  async hdel(key: string, ...fields: string[]): Promise<number> {
    try {
      return await this.client.hDel(this.prefixKey(key), fields);
    } catch (error) {
      this.logger.error('Redis HDEL operation failed', {
        key,
        fields,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Set operations
   */
  async sadd(key: string, ...members: string[]): Promise<number> {
    try {
      return await this.client.sAdd(this.prefixKey(key), members);
    } catch (error) {
      this.logger.error('Redis SADD operation failed', {
        key,
        members,
        error: error.message,
      });
      throw error;
    }
  }

  async srem(key: string, ...members: string[]): Promise<number> {
    try {
      return await this.client.sRem(this.prefixKey(key), members);
    } catch (error) {
      this.logger.error('Redis SREM operation failed', {
        key,
        members,
        error: error.message,
      });
      throw error;
    }
  }

  async smembers(key: string): Promise<string[]> {
    try {
      return await this.client.sMembers(this.prefixKey(key));
    } catch (error) {
      this.logger.error('Redis SMEMBERS operation failed', {
        key,
        error: error.message,
      });
      throw error;
    }
  }

  async sismember(key: string, member: string): Promise<boolean> {
    try {
      return await this.client.sIsMember(this.prefixKey(key), member);
    } catch (error) {
      this.logger.error('Redis SISMEMBER operation failed', {
        key,
        member,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * List operations
   */
  async lpush(key: string, ...elements: string[]): Promise<number> {
    try {
      return await this.client.lPush(this.prefixKey(key), elements);
    } catch (error) {
      this.logger.error('Redis LPUSH operation failed', {
        key,
        elements,
        error: error.message,
      });
      throw error;
    }
  }

  async rpush(key: string, ...elements: string[]): Promise<number> {
    try {
      return await this.client.rPush(this.prefixKey(key), elements);
    } catch (error) {
      this.logger.error('Redis RPUSH operation failed', {
        key,
        elements,
        error: error.message,
      });
      throw error;
    }
  }

  async lpop(key: string): Promise<string | null> {
    try {
      return await this.client.lPop(this.prefixKey(key));
    } catch (error) {
      this.logger.error('Redis LPOP operation failed', {
        key,
        error: error.message,
      });
      throw error;
    }
  }

  async llen(key: string): Promise<number> {
    try {
      return await this.client.lLen(this.prefixKey(key));
    } catch (error) {
      this.logger.error('Redis LLEN operation failed', {
        key,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Ping Redis server
   */
  async ping(): Promise<string> {
    try {
      return await this.client.ping();
    } catch (error) {
      this.logger.error('Redis PING failed', { error: error.message });
      throw error;
    }
  }

  /**
   * Flush database
   */
  async flushdb(): Promise<string> {
    try {
      return await this.client.flushDb();
    } catch (error) {
      this.logger.error('Redis FLUSHDB failed', { error: error.message });
      throw error;
    }
  }

  /**
   * Add key prefix
   */
  private prefixKey(key: string): string {
    return `${redisConfig.keyPrefix}${key}`;
  }

  /**
   * Setup Redis event handlers
   */
  private setupEventHandlers(): void {
    this.client.on('connect', () => {
      this.logger.info('Redis client connected');
    });

    this.client.on('ready', () => {
      this.logger.info('Redis client ready');
    });

    this.client.on('error', error => {
      this.logger.error('Redis client error', { error: error.message });
      this.isConnected = false;
    });

    this.client.on('end', () => {
      this.logger.info('Redis client connection ended');
      this.isConnected = false;
    });

    this.client.on('reconnecting', () => {
      this.logger.info('Redis client reconnecting');
    });
  }

  /**
   * Check if Redis is connected
   */
  isHealthy(): boolean {
    return this.isConnected && this.client.isOpen;
  }

  /**
   * Get client info
   */
  async info(): Promise<string> {
    try {
      return await this.client.info();
    } catch (error) {
      this.logger.error('Redis INFO failed', { error: error.message });
      throw error;
    }
  }
}
