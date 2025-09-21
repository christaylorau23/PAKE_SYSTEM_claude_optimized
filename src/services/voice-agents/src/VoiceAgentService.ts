/**
 * PAKE System - Main Voice Agent Service Controller
 * Orchestrates all voice agent components and provides HTTP API
 */

import express, { Router } from 'express';
import { VapiVoiceAgent, VoiceAgentConfig, VoiceCallRequest } from './agents/VapiVoiceAgent';
import { ConversationManager, ConversationManagerConfig } from './conversation/ConversationManager';
import { KnowledgeConnector, KnowledgeConnectorConfig } from './conversation/KnowledgeConnector';
import { Logger } from './utils/Logger';
import { RateLimiterMemory } from 'rate-limiter-flexible';
import Joi from 'joi';

export interface VoiceAgentServiceConfig {
  vapi: {
    apiKey: string;
    endpoint?: string;
  };
  voiceAgent: VoiceAgentConfig;
  conversation: ConversationManagerConfig;
  knowledge: KnowledgeConnectorConfig;
  rateLimit: {
    windowMs: number;
    maxRequests: number;
  };
}

/**
 * VoiceAgentService - Main service class that orchestrates all voice agent functionality
 * Provides HTTP API endpoints and manages component lifecycle
 */
export class VoiceAgentService {
  private logger: Logger;
  private config: VoiceAgentServiceConfig;
  private voiceAgent: VapiVoiceAgent;
  private conversationManager: ConversationManager;
  private knowledgeConnector: KnowledgeConnector;
  private router: Router;
  private rateLimiter: RateLimiterMemory;
  private initialized = false;

  constructor() {
    this.logger = new Logger('VoiceAgentService');
    this.config = this.loadConfiguration();
    this.router = express.Router();

    // Initialize rate limiter
    this.rateLimiter = new RateLimiterMemory({
      keyGenerator: (req) => req.ip,
      points: this.config.rateLimit.maxRequests,
      duration: this.config.rateLimit.windowMs / 1000,
    });

    this.setupComponents();
    this.setupRoutes();
  }

  /**
   * Initialize the service and all components
   */
  async initialize(): Promise<void> {
    if (this.initialized) {
      return;
    }

    try {
      this.logger.info('Initializing voice agent service');

      // Test knowledge vault connectivity
      const knowledgeConnected = await this.knowledgeConnector.testConnection();
      if (!knowledgeConnected) {
        this.logger.warn('Knowledge vault connection failed, some features may be limited');
      }

      this.initialized = true;
      this.logger.info('Voice agent service initialization complete');
    } catch (error) {
      this.logger.error('Failed to initialize voice agent service', error);
      throw error;
    }
  }

  /**
   * Check if service is ready to handle requests
   */
  async isReady(): Promise<boolean> {
    if (!this.initialized) {
      return false;
    }

    try {
      // Check if all critical components are operational
      const knowledgeReady = await this.knowledgeConnector.testConnection();
      return knowledgeReady; // Can be more sophisticated
    } catch (error) {
      this.logger.error('Readiness check failed', error);
      return false;
    }
  }

  /**
   * Check Redis connectivity
   */
  isRedisConnected(): boolean {
    // This would check the Redis connection status
    // For now, return true as a placeholder
    return true;
  }

  /**
   * Check knowledge vault connectivity
   */
  isKnowledgeVaultConnected(): boolean {
    // This would check the knowledge vault connection
    // For now, return true as a placeholder
    return true;
  }

  /**
   * Get service metrics
   */
  getMetrics(): any {
    return {
      service: 'voice-agents',
      uptime: process.uptime(),
      timestamp: new Date().toISOString(),
      voiceAgent: this.voiceAgent.getMetrics(),
      conversation: this.conversationManager.getMetrics(),
      knowledge: this.knowledgeConnector.getMetrics(),
      memory: {
        heapUsed: Math.round(process.memoryUsage().heapUsed / 1024 / 1024),
        heapTotal: Math.round(process.memoryUsage().heapTotal / 1024 / 1024),
        external: Math.round(process.memoryUsage().external / 1024 / 1024),
        rss: Math.round(process.memoryUsage().rss / 1024 / 1024),
      },
      cpu: process.cpuUsage(),
      nodejs: process.version,
    };
  }

  /**
   * Get Express router with all API routes
   */
  getRouter(): Router {
    return this.router;
  }

  /**
   * Shutdown the service gracefully
   */
  async shutdown(): Promise<void> {
    this.logger.info('Starting voice agent service shutdown');

    try {
      // Shutdown voice agent (ends all active calls)
      await this.voiceAgent.shutdown();

      // Shutdown conversation manager
      await this.conversationManager.destroy();

      // Cleanup knowledge connector
      this.knowledgeConnector.destroy();

      this.initialized = false;
      this.logger.info('Voice agent service shutdown complete');
    } catch (error) {
      this.logger.error('Error during service shutdown', error);
      throw error;
    }
  }

  /**
   * Load service configuration from environment
   */
  private loadConfiguration(): VoiceAgentServiceConfig {
    const vapiApiKey = process.env.VAPI_API_KEY;
    if (!vapiApiKey) {
      throw new Error('VAPI_API_KEY environment variable is required');
    }

    return {
      vapi: {
        apiKey: vapiApiKey,
        endpoint: process.env.VAPI_API_ENDPOINT || 'https://api.vapi.ai',
      },
      voiceAgent: {
        voiceId: process.env.DEFAULT_VOICE_ID || 'en-US-Standard-A',
        knowledgeBaseId: process.env.DEFAULT_KNOWLEDGE_BASE_ID || 'default',
        responseTimeout: parseInt(process.env.VOICE_RESPONSE_TIMEOUT || '5000'),
        streamingLatency: parseInt(process.env.VOICE_STREAMING_LATENCY || '3'),
        qualityThreshold: parseFloat(process.env.VOICE_QUALITY_THRESHOLD || '0.8'),
        fallbackProvider: process.env.FALLBACK_PROVIDER || 'elevenlabs',
      },
      conversation: {
        memoryTtl: parseInt(process.env.CONVERSATION_MEMORY_TTL || '3600'),
        maxContextLength: 4000,
        redisUrl: process.env.REDIS_URL,
        persistenceEnabled: process.env.NODE_ENV === 'production',
      },
      knowledge: {
        contextDepth: parseInt(process.env.KNOWLEDGE_CONTEXT_DEPTH || '5'),
        confidenceThreshold: parseFloat(process.env.KNOWLEDGE_CONFIDENCE_THRESHOLD || '0.7'),
        realTimeSearchEnabled: process.env.REAL_TIME_SEARCH_ENABLED === 'true',
      },
      rateLimit: {
        windowMs: 60000, // 1 minute
        maxRequests: 100, // 100 requests per minute
      },
    };
  }

  /**
   * Setup service components
   */
  private setupComponents(): void {
    // Initialize knowledge connector
    this.knowledgeConnector = new KnowledgeConnector(this.config.knowledge);

    // Initialize conversation manager
    this.conversationManager = new ConversationManager(this.config.conversation);

    // Initialize voice agent
    this.voiceAgent = new VapiVoiceAgent(this.config.vapi.apiKey, this.config.voiceAgent);

    // Setup event handlers
    this.setupEventHandlers();
  }

  /**
   * Setup event handlers for component communication
   */
  private setupEventHandlers(): void {
    // Voice agent events
    this.voiceAgent.on('call-initiated', (data) => {
      this.logger.info('Voice call initiated', data);
    });

    this.voiceAgent.on('call-ended', (data) => {
      this.logger.info('Voice call ended', data);
    });

    this.voiceAgent.on('error', (error) => {
      this.logger.error('Voice agent error', error);
    });

    // Conversation manager events
    this.conversationManager.on('session-created', (data) => {
      this.logger.info('Conversation session created', data);
    });

    this.conversationManager.on('session-ended', (data) => {
      this.logger.info('Conversation session ended', data);
    });

    // Knowledge connector events
    this.knowledgeConnector.on('search-error', (data) => {
      this.logger.warn('Knowledge search error', data);
    });
  }

  /**
   * Setup HTTP API routes
   */
  private setupRoutes(): void {
    // Apply rate limiting to all routes
    this.router.use(async (req, res, next) => {
      try {
        await this.rateLimiter.consume(req.ip);
        next();
      } catch (rejRes) {
        res.status(429).json({
          error: 'Too Many Requests',
          message: 'Rate limit exceeded. Please try again later.',
          retryAfter: Math.round(rejRes.msBeforeNext / 1000) || 60,
        });
      }
    });

    // Request validation middleware
    const validate = (schema: Joi.ObjectSchema) => {
      return (req: express.Request, res: express.Response, next: express.NextFunction) => {
        const { error } = schema.validate(req.body);
        if (error) {
          res.status(400).json({
            error: 'Validation Error',
            message: error.details[0].message,
            details: error.details,
          });
          return;
        }
        next();
      };
    };

    // Voice Assistant Management
    this.router.post(
      '/assistants',
      validate(
        Joi.object({
          voiceId: Joi.string().optional(),
          knowledgeBaseId: Joi.string().optional(),
          systemPrompt: Joi.string().optional(),
        })
      ),
      async (req, res) => {
        try {
          const assistantId = await this.voiceAgent.createVoiceAssistant(req.body);
          res.status(201).json({ assistantId });
        } catch (error) {
          this.logger.error('Failed to create voice assistant', error);
          res.status(500).json({ error: 'Failed to create voice assistant' });
        }
      }
    );

    this.router.get('/assistants', async (req, res) => {
      try {
        const assistants = await this.voiceAgent.listAssistants();
        res.json({ assistants });
      } catch (error) {
        this.logger.error('Failed to list voice assistants', error);
        res.status(500).json({ error: 'Failed to list voice assistants' });
      }
    });

    // Voice Call Management
    this.router.post(
      '/calls',
      validate(
        Joi.object({
          assistantId: Joi.string().required(),
          phoneNumber: Joi.string().optional(),
          context: Joi.object({
            userId: Joi.string().required(),
            sessionId: Joi.string().optional(),
            userPreferences: Joi.object().optional(),
            metadata: Joi.object().optional(),
          }).required(),
          maxDuration: Joi.number().optional(),
          webhookUrl: Joi.string().uri().optional(),
        })
      ),
      async (req, res) => {
        try {
          // Create or get conversation session
          const session = await this.conversationManager.createSession(
            req.body.context.userId,
            req.body.context.sessionId
          );

          const callRequest: VoiceCallRequest = {
            assistantId: req.body.assistantId,
            phoneNumber: req.body.phoneNumber,
            context: {
              ...req.body.context,
              sessionId: session.sessionId,
              previousMessages: session.context.previousMessages,
              knowledgeContext: session.context.knowledgeContext,
              userPreferences: session.context.userPreferences,
            },
            maxDuration: req.body.maxDuration,
            webhookUrl: req.body.webhookUrl,
          };

          const callResponse = await this.voiceAgent.initiateCall(callRequest);
          res.status(201).json(callResponse);
        } catch (error) {
          this.logger.error('Failed to initiate voice call', error);
          res.status(500).json({ error: 'Failed to initiate voice call' });
        }
      }
    );

    this.router.get('/calls/:callId', async (req, res) => {
      try {
        const callStatus = await this.voiceAgent.getCallStatus(req.params.callId);
        res.json(callStatus);
      } catch (error) {
        this.logger.error('Failed to get call status', error, { callId: req.params.callId });
        res.status(500).json({ error: 'Failed to get call status' });
      }
    });

    this.router.patch(
      '/calls/:callId',
      validate(
        Joi.object({
          context: Joi.object().optional(),
          instructions: Joi.string().optional(),
        })
      ),
      async (req, res) => {
        try {
          await this.voiceAgent.updateCall(req.params.callId, req.body.context);
          res.json({ success: true });
        } catch (error) {
          this.logger.error('Failed to update call', error, { callId: req.params.callId });
          res.status(500).json({ error: 'Failed to update call' });
        }
      }
    );

    this.router.delete('/calls/:callId', async (req, res) => {
      try {
        const reason = (req.query.reason as string) || 'User ended call';
        const callResponse = await this.voiceAgent.endCall(req.params.callId, reason);
        res.json(callResponse);
      } catch (error) {
        this.logger.error('Failed to end call', error, { callId: req.params.callId });
        res.status(500).json({ error: 'Failed to end call' });
      }
    });

    // Knowledge Base Integration
    this.router.post(
      '/knowledge/search',
      validate(
        Joi.object({
          query: Joi.string().required(),
          knowledgeBaseId: Joi.string().optional(),
          context: Joi.object().optional(),
        })
      ),
      async (req, res) => {
        try {
          const knowledgeContext = await this.knowledgeConnector.performRealTimeSearch(
            req.body.query,
            req.body.context
          );
          res.json(knowledgeContext);
        } catch (error) {
          this.logger.error('Knowledge search failed', error);
          res.status(500).json({ error: 'Knowledge search failed' });
        }
      }
    );

    // Conversation Management
    this.router.get('/conversations/:sessionId', async (req, res) => {
      try {
        const context = await this.conversationManager.getContext(req.params.sessionId);
        if (!context) {
          res.status(404).json({ error: 'Conversation not found' });
          return;
        }
        res.json(context);
      } catch (error) {
        this.logger.error('Failed to get conversation context', error);
        res.status(500).json({ error: 'Failed to get conversation context' });
      }
    });

    this.router.post(
      '/conversations/:sessionId/messages',
      validate(
        Joi.object({
          role: Joi.string().valid('user', 'assistant', 'system').required(),
          content: Joi.string().required(),
          audioUrl: Joi.string().uri().optional(),
          confidence: Joi.number().min(0).max(1).optional(),
          metadata: Joi.object().optional(),
        })
      ),
      async (req, res) => {
        try {
          await this.conversationManager.addMessage(req.params.sessionId, req.body);
          res.status(201).json({ success: true });
        } catch (error) {
          this.logger.error('Failed to add message to conversation', error);
          res.status(500).json({ error: 'Failed to add message to conversation' });
        }
      }
    );

    this.router.delete('/conversations/:sessionId', async (req, res) => {
      try {
        const reason = (req.query.reason as string) || 'User ended conversation';
        await this.conversationManager.endSession(req.params.sessionId, reason);
        res.json({ success: true });
      } catch (error) {
        this.logger.error('Failed to end conversation session', error);
        res.status(500).json({ error: 'Failed to end conversation session' });
      }
    });

    // User Preferences Management
    this.router.put(
      '/users/:userId/preferences',
      validate(
        Joi.object({
          voiceSpeed: Joi.number().min(0.5).max(2.0).optional(),
          voiceStyle: Joi.string().optional(),
          language: Joi.string().optional(),
          preferredTopics: Joi.array().items(Joi.string()).optional(),
          conversationStyle: Joi.string().valid('formal', 'casual', 'technical').optional(),
          responseLength: Joi.string().valid('brief', 'detailed', 'adaptive').optional(),
        })
      ),
      async (req, res) => {
        try {
          await this.conversationManager.updateUserPreferences(req.params.userId, req.body);
          res.json({ success: true });
        } catch (error) {
          this.logger.error('Failed to update user preferences', error);
          res.status(500).json({ error: 'Failed to update user preferences' });
        }
      }
    );

    // Service Status and Monitoring
    this.router.get('/status', (req, res) => {
      res.json({
        service: 'voice-agents',
        status: 'operational',
        version: '1.0.0',
        components: {
          voiceAgent: 'operational',
          conversationManager: 'operational',
          knowledgeConnector: 'operational',
        },
        metrics: this.getMetrics(),
      });
    });
  }
}

export default VoiceAgentService;
