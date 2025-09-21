/**
 * PAKE System - Conversation Context Manager
 * Manages conversation state, context persistence, and multi-turn dialogue memory
 */

import { EventEmitter } from 'events';
import Redis from 'ioredis';
import { Logger } from '../utils/Logger';

export interface ConversationManagerConfig {
  memoryTtl: number; // Context TTL in seconds
  maxContextLength: number; // Maximum context length in characters
  redisUrl?: string; // Redis connection URL
  persistenceEnabled?: boolean; // Enable conversation persistence
  compressionEnabled?: boolean; // Enable context compression
}

export interface ConversationSession {
  sessionId: string;
  userId: string;
  startedAt: Date;
  lastActiveAt: Date;
  totalMessages: number;
  context: ConversationContext;
  metadata: Record<string, unknown>;
}

export interface ConversationContext {
  userId: string;
  sessionId: string;
  previousMessages: Message[];
  knowledgeContext: string[];
  userPreferences: UserPreferences;
  conversationSummary: string;
  currentTopic: string;
  sentimentHistory: SentimentEntry[];
  metadata: Record<string, unknown>;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  audioUrl?: string;
  confidence?: number;
  sentiment?: string;
  intent?: string;
  metadata?: Record<string, any>;
}

export interface UserPreferences {
  voiceSpeed: number;
  voiceStyle: string;
  language: string;
  preferredTopics: string[];
  conversationStyle: 'formal' | 'casual' | 'technical';
  responseLength: 'brief' | 'detailed' | 'adaptive';
}

export interface SentimentEntry {
  timestamp: Date;
  sentiment: 'positive' | 'neutral' | 'negative';
  score: number;
  message: string;
}

export interface ConversationMetrics {
  activeSessions: number;
  totalSessions: number;
  averageSessionLength: number;
  memoryUsage: number;
  cacheHitRate: number;
}

/**
 * ConversationManager - Manages conversation state and context for voice agents
 * Provides persistent session management, context compression, and intelligent memory
 */
export class ConversationManager extends EventEmitter {
  private redis: Redis;
  private logger: Logger;
  private config: ConversationManagerConfig;
  private localCache: Map<string, ConversationSession> = new Map();
  private metrics: ConversationMetrics;
  private cleanupInterval?: NodeJS.Timeout;

  constructor(config: ConversationManagerConfig) {
    super();
    this.config = config;
    this.logger = new Logger('ConversationManager');

    // Initialize metrics
    this.metrics = {
      activeSessions: 0,
      totalSessions: 0,
      averageSessionLength: 0,
      memoryUsage: 0,
      cacheHitRate: 0,
    };

    // Initialize Redis for conversation persistence
    this.initializeRedis();

    // Start cleanup and monitoring
    this.startCleanupProcess();

    this.logger.info('Conversation manager initialized', {
      memoryTtl: config.memoryTtl,
      maxContextLength: config.maxContextLength,
      persistenceEnabled: config.persistenceEnabled,
    });
  }

  /**
   * Initialize Redis connection for persistence
   */
  private initializeRedis(): void {
    if (!this.config.persistenceEnabled) {
      return;
    }

    try {
      const redisUrl = this.config.redisUrl || process.env.REDIS_URL || 'redis://localhost:6379';
      this.redis = new Redis(redisUrl, {
        retryDelayOnFailover: 100,
        retryDelayOnClusterDown: 300,
        enableOfflineQueue: false,
        maxRetriesPerRequest: 3,
      });

      this.redis.on('connect', () => {
        this.logger.info('Connected to Redis for conversation persistence');
      });

      this.redis.on('error', (error) => {
        this.logger.error('Redis connection error', error);
      });
    } catch (error) {
      this.logger.error('Failed to initialize Redis', error);
      this.config.persistenceEnabled = false;
    }
  }

  /**
   * Create or retrieve a conversation session
   */
  async createSession(userId: string, sessionId?: string): Promise<ConversationSession> {
    const finalSessionId = sessionId || this.generateSessionId(userId);

    try {
      // Check if session already exists
      let session = await this.getSession(finalSessionId);

      if (session) {
        // Update last active time
        session.lastActiveAt = new Date();
        await this.storeSession(session);

        this.logger.debug('Retrieved existing session', {
          sessionId: finalSessionId,
          userId,
          messageCount: session.totalMessages,
        });

        return session;
      }

      // Create new session
      session = {
        sessionId: finalSessionId,
        userId,
        startedAt: new Date(),
        lastActiveAt: new Date(),
        totalMessages: 0,
        context: {
          userId,
          sessionId: finalSessionId,
          previousMessages: [],
          knowledgeContext: [],
          userPreferences: await this.loadUserPreferences(userId),
          conversationSummary: '',
          currentTopic: '',
          sentimentHistory: [],
          metadata: {},
        },
        metadata: {
          createdBy: 'ConversationManager',
          version: '1.0.0',
        },
      };

      await this.storeSession(session);
      this.metrics.totalSessions++;
      this.metrics.activeSessions++;

      this.logger.info('Created new conversation session', {
        sessionId: finalSessionId,
        userId,
      });

      this.emit('session-created', { sessionId: finalSessionId, userId });
      return session;
    } catch (error) {
      this.logger.error('Failed to create conversation session', {
        userId,
        sessionId: finalSessionId,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Store conversation context
   */
  async storeContext(sessionId: string, context: ConversationContext): Promise<void> {
    try {
      let session = await this.getSession(sessionId);

      if (!session) {
        // Create session if it doesn't exist
        session = await this.createSession(context.userId, sessionId);
      }

      // Update context with compression if needed
      session.context = this.compressContextIfNeeded(context);
      session.lastActiveAt = new Date();

      await this.storeSession(session);

      this.logger.debug('Stored conversation context', {
        sessionId,
        messageCount: context.previousMessages.length,
        contextLength: JSON.stringify(context).length,
      });
    } catch (error) {
      this.logger.error('Failed to store conversation context', {
        sessionId,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Retrieve conversation context
   */
  async getContext(sessionId: string): Promise<ConversationContext | null> {
    try {
      const session = await this.getSession(sessionId);
      return session?.context || null;
    } catch (error) {
      this.logger.error('Failed to retrieve conversation context', {
        sessionId,
        error: error.message,
      });
      return null;
    }
  }

  /**
   * Add message to conversation
   */
  async addMessage(sessionId: string, message: Partial<Message>): Promise<void> {
    try {
      const session = await this.getSession(sessionId);
      if (!session) {
        throw new Error(`Session ${sessionId} not found`);
      }

      // Create complete message object
      const fullMessage: Message = {
        id: message.id || this.generateMessageId(),
        role: message.role || 'user',
        content: message.content || '',
        timestamp: message.timestamp || new Date(),
        audioUrl: message.audioUrl,
        confidence: message.confidence,
        sentiment: message.sentiment,
        intent: message.intent,
        metadata: message.metadata || {},
      };

      // Add to context
      session.context.previousMessages.push(fullMessage);
      session.totalMessages++;
      session.lastActiveAt = new Date();

      // Update sentiment history
      if (fullMessage.sentiment) {
        session.context.sentimentHistory.push({
          timestamp: fullMessage.timestamp,
          sentiment: fullMessage.sentiment as any,
          score: fullMessage.confidence || 0.5,
          message: fullMessage.content.substring(0, 100),
        });
      }

      // Update conversation summary and topic
      await this.updateConversationSummary(session);

      // Compress if context is getting too long
      session.context = this.compressContextIfNeeded(session.context);

      await this.storeSession(session);

      this.emit('message-added', {
        sessionId,
        messageId: fullMessage.id,
        role: fullMessage.role,
        totalMessages: session.totalMessages,
      });
    } catch (error) {
      this.logger.error('Failed to add message to conversation', {
        sessionId,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Update user preferences
   */
  async updateUserPreferences(
    userId: string,
    preferences: Partial<UserPreferences>
  ): Promise<void> {
    try {
      const currentPrefs = await this.loadUserPreferences(userId);
      const updatedPrefs = { ...currentPrefs, ...preferences };

      // Store in Redis if persistence is enabled
      if (this.config.persistenceEnabled && this.redis) {
        await this.redis.setex(
          `user-prefs:${userId}`,
          this.config.memoryTtl,
          JSON.stringify(updatedPrefs)
        );
      }

      // Update all active sessions for this user
      for (const [sessionId, session] of this.localCache.entries()) {
        if (session.userId === userId) {
          session.context.userPreferences = updatedPrefs;
          await this.storeSession(session);
        }
      }

      this.logger.info('Updated user preferences', { userId, preferences });
      this.emit('preferences-updated', { userId, preferences: updatedPrefs });
    } catch (error) {
      this.logger.error('Failed to update user preferences', {
        userId,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Get conversation summary for a session
   */
  async getConversationSummary(sessionId: string): Promise<string> {
    try {
      const session = await this.getSession(sessionId);
      return session?.context.conversationSummary || 'No conversation summary available';
    } catch (error) {
      this.logger.error('Failed to get conversation summary', {
        sessionId,
        error: error.message,
      });
      return 'Error retrieving conversation summary';
    }
  }

  /**
   * End a conversation session
   */
  async endSession(sessionId: string, reason?: string): Promise<void> {
    try {
      const session = await this.getSession(sessionId);
      if (!session) {
        this.logger.warn('Attempted to end non-existent session', { sessionId });
        return;
      }

      // Update session metadata
      session.metadata.endedAt = new Date();
      session.metadata.endReason = reason || 'User ended';
      session.metadata.duration = Date.now() - session.startedAt.getTime();

      // Store final state
      await this.storeSession(session);

      // Remove from local cache
      this.localCache.delete(sessionId);
      this.metrics.activeSessions = Math.max(0, this.metrics.activeSessions - 1);

      // Update average session length
      this.updateAverageSessionLength(session.metadata.duration);

      this.logger.info('Ended conversation session', {
        sessionId,
        userId: session.userId,
        duration: session.metadata.duration,
        totalMessages: session.totalMessages,
        reason,
      });

      this.emit('session-ended', {
        sessionId,
        userId: session.userId,
        duration: session.metadata.duration,
        totalMessages: session.totalMessages,
        reason,
      });
    } catch (error) {
      this.logger.error('Failed to end conversation session', {
        sessionId,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Get session from cache or storage
   */
  private async getSession(sessionId: string): Promise<ConversationSession | null> {
    try {
      // Check local cache first
      let session = this.localCache.get(sessionId);
      if (session) {
        return session;
      }

      // Check Redis if persistence is enabled
      if (this.config.persistenceEnabled && this.redis) {
        const sessionData = await this.redis.get(`session:${sessionId}`);
        if (sessionData) {
          session = JSON.parse(sessionData);

          // Convert date strings back to Date objects
          session.startedAt = new Date(session.startedAt);
          session.lastActiveAt = new Date(session.lastActiveAt);
          session.context.previousMessages = session.context.previousMessages.map((msg) => ({
            ...msg,
            timestamp: new Date(msg.timestamp),
          }));

          // Store in local cache
          this.localCache.set(sessionId, session);
          return session;
        }
      }

      return null;
    } catch (error) {
      this.logger.error('Failed to retrieve session', {
        sessionId,
        error: error.message,
      });
      return null;
    }
  }

  /**
   * Store session in cache and persistence
   */
  private async storeSession(session: ConversationSession): Promise<void> {
    try {
      // Store in local cache
      this.localCache.set(session.sessionId, session);

      // Store in Redis if persistence is enabled
      if (this.config.persistenceEnabled && this.redis) {
        await this.redis.setex(
          `session:${session.sessionId}`,
          this.config.memoryTtl,
          JSON.stringify(session)
        );
      }
    } catch (error) {
      this.logger.error('Failed to store session', {
        sessionId: session.sessionId,
        error: error.message,
      });
    }
  }

  /**
   * Load user preferences
   */
  private async loadUserPreferences(userId: string): Promise<UserPreferences> {
    const defaultPrefs: UserPreferences = {
      voiceSpeed: 1.0,
      voiceStyle: 'natural',
      language: 'en-US',
      preferredTopics: [],
      conversationStyle: 'casual',
      responseLength: 'adaptive',
    };

    try {
      if (this.config.persistenceEnabled && this.redis) {
        const prefs = await this.redis.get(`user-prefs:${userId}`);
        if (prefs) {
          return { ...defaultPrefs, ...JSON.parse(prefs) };
        }
      }
      return defaultPrefs;
    } catch (error) {
      this.logger.warn('Failed to load user preferences, using defaults', {
        userId,
        error: error.message,
      });
      return defaultPrefs;
    }
  }

  /**
   * Compress context if it exceeds maximum length
   */
  private compressContextIfNeeded(context: ConversationContext): ConversationContext {
    const contextStr = JSON.stringify(context);

    if (contextStr.length <= this.config.maxContextLength) {
      return context;
    }

    if (!this.config.compressionEnabled) {
      // Simple truncation if compression is disabled
      const messagesToKeep = Math.floor(context.previousMessages.length * 0.7);
      context.previousMessages = context.previousMessages.slice(-messagesToKeep);
      return context;
    }

    // Smart compression: keep recent messages and important ones
    const compressedContext = { ...context };

    // Keep last 50% of messages
    const recentMessageCount = Math.floor(context.previousMessages.length * 0.5);
    const recentMessages = context.previousMessages.slice(-recentMessageCount);

    // Keep important messages (high confidence, system messages)
    const importantMessages = context.previousMessages
      .filter(
        (msg) =>
          msg.role === 'system' ||
          (msg.confidence && msg.confidence > 0.8) ||
          msg.metadata?.important === true
      )
      .slice(0, 5); // Max 5 important messages

    // Combine and deduplicate
    const messageIds = new Set();
    compressedContext.previousMessages = [...importantMessages, ...recentMessages]
      .filter((msg) => {
        if (messageIds.has(msg.id)) return false;
        messageIds.add(msg.id);
        return true;
      })
      .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());

    // Compress knowledge context
    compressedContext.knowledgeContext = context.knowledgeContext.slice(0, 3);

    // Keep only recent sentiment history
    compressedContext.sentimentHistory = context.sentimentHistory.slice(-10);

    this.logger.debug('Compressed conversation context', {
      originalMessages: context.previousMessages.length,
      compressedMessages: compressedContext.previousMessages.length,
      originalLength: contextStr.length,
      compressedLength: JSON.stringify(compressedContext).length,
    });

    return compressedContext;
  }

  /**
   * Update conversation summary using recent messages
   */
  private async updateConversationSummary(session: ConversationSession): Promise<void> {
    try {
      const recentMessages = session.context.previousMessages.slice(-5);
      if (recentMessages.length === 0) return;

      // Simple summary generation (could be enhanced with AI)
      const topics = new Set<string>();
      recentMessages.forEach((msg) => {
        if (msg.intent) topics.add(msg.intent);
        // Extract key terms (simplified)
        const words = msg.content
          .toLowerCase()
          .split(/\s+/)
          .filter((word) => word.length > 4)
          .slice(0, 2);
        words.forEach((word) => topics.add(word));
      });

      const topicList = Array.from(topics).slice(0, 5);
      session.context.currentTopic = topicList[0] || 'general';
      session.context.conversationSummary = `Discussion about: ${topicList.join(', ')}`;
    } catch (error) {
      this.logger.warn('Failed to update conversation summary', error);
    }
  }

  /**
   * Generate unique session ID
   */
  private generateSessionId(userId: string): string {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2, 8);
    return `${userId}_${timestamp}_${random}`;
  }

  /**
   * Generate unique message ID
   */
  private generateMessageId(): string {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2, 8);
    return `msg_${timestamp}_${random}`;
  }

  /**
   * Update average session length metric
   */
  private updateAverageSessionLength(duration: number): void {
    const totalSessions = this.metrics.totalSessions;
    this.metrics.averageSessionLength =
      (this.metrics.averageSessionLength * (totalSessions - 1) + duration) / totalSessions;
  }

  /**
   * Start cleanup process for expired sessions
   */
  private startCleanupProcess(): void {
    this.cleanupInterval = setInterval(async () => {
      try {
        const now = Date.now();
        const expiredSessions: string[] = [];

        // Check local cache for expired sessions
        for (const [sessionId, session] of this.localCache.entries()) {
          const inactiveTime = now - session.lastActiveAt.getTime();
          if (inactiveTime > this.config.memoryTtl * 1000) {
            expiredSessions.push(sessionId);
          }
        }

        // Cleanup expired sessions
        for (const sessionId of expiredSessions) {
          const session = this.localCache.get(sessionId);
          if (session) {
            await this.endSession(sessionId, 'Session expired');
            this.emit('context-expired', sessionId);
          }
        }

        // Update memory usage metric
        this.metrics.memoryUsage = this.localCache.size;

        if (expiredSessions.length > 0) {
          this.logger.info(`Cleaned up ${expiredSessions.length} expired sessions`);
        }
      } catch (error) {
        this.logger.error('Error during session cleanup', error);
      }
    }, 60000); // Run cleanup every minute
  }

  /**
   * Get conversation metrics
   */
  getMetrics(): ConversationMetrics {
    return {
      ...this.metrics,
      activeSessions: this.localCache.size,
    };
  }

  /**
   * List active sessions
   */
  getActiveSessions(): string[] {
    return Array.from(this.localCache.keys());
  }

  /**
   * Get session info
   */
  async getSessionInfo(sessionId: string): Promise<any> {
    const session = await this.getSession(sessionId);
    if (!session) return null;

    return {
      sessionId: session.sessionId,
      userId: session.userId,
      startedAt: session.startedAt,
      lastActiveAt: session.lastActiveAt,
      totalMessages: session.totalMessages,
      currentTopic: session.context.currentTopic,
      conversationSummary: session.context.conversationSummary,
    };
  }

  /**
   * Cleanup resources
   */
  async destroy(): Promise<void> {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
    }

    // End all active sessions
    const sessionIds = Array.from(this.localCache.keys());
    for (const sessionId of sessionIds) {
      await this.endSession(sessionId, 'System shutdown');
    }

    // Close Redis connection
    if (this.redis) {
      await this.redis.quit();
    }

    this.removeAllListeners();
    this.logger.info('Conversation manager destroyed');
  }
}

export default ConversationManager;
