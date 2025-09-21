/**
 * PAKE System - Vapi.ai Voice Agent Integration
 * Enterprise-grade voice agent with advanced error handling and knowledge integration
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import { EventEmitter } from 'events';
import { CircuitBreaker } from '../error-handling/CircuitBreaker';
import { KnowledgeConnector } from '../conversation/KnowledgeConnector';
import { ConversationManager } from '../conversation/ConversationManager';
import { VoiceMonitor } from '../monitoring/VoiceMonitor';
import { Logger } from '../utils/Logger';

// Type definitions for Vapi.ai integration
export interface VoiceAgentConfig {
  assistantId?: string;
  voiceId: string;
  knowledgeBaseId: string;
  systemPrompt?: string;
  responseTimeout: number;
  streamingLatency: number;
  qualityThreshold: number;
  fallbackProvider: string;
}

export interface ConversationContext {
  userId: string;
  sessionId: string;
  previousMessages: Message[];
  knowledgeContext: string[];
  userPreferences: UserPreferences;
  metadata: Record<string, any>;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  audioUrl?: string;
  confidence?: number;
  metadata?: Record<string, any>;
}

export interface UserPreferences {
  voiceSpeed: number;
  voiceStyle: string;
  language: string;
  preferredTopics: string[];
  conversationStyle: 'formal' | 'casual' | 'technical';
}

export interface VoiceCallRequest {
  phoneNumber?: string;
  assistantId: string;
  context: ConversationContext;
  webhookUrl?: string;
  maxDuration?: number;
}

export interface VoiceCallResponse {
  callId: string;
  status: 'initiated' | 'in-progress' | 'completed' | 'failed';
  duration?: number;
  transcript?: string;
  audioUrl?: string;
  cost?: number;
  metadata: Record<string, any>;
}

/**
 * VapiVoiceAgent - Core class for managing Vapi.ai voice agent interactions
 * Includes advanced error handling, circuit breaker patterns, and knowledge integration
 */
export class VapiVoiceAgent extends EventEmitter {
  private apiClient: AxiosInstance;
  private circuitBreaker: CircuitBreaker;
  private knowledgeConnector: KnowledgeConnector;
  private conversationManager: ConversationManager;
  private voiceMonitor: VoiceMonitor;
  private logger: Logger;
  private config: VoiceAgentConfig;
  private activeCalls: Map<string, VoiceCallResponse> = new Map();

  constructor(apiKey: string, config: VoiceAgentConfig) {
    super();
    this.config = config;
    this.logger = new Logger('VapiVoiceAgent');

    // Initialize HTTP client with timeout and retry configuration
    this.apiClient = axios.create({
      baseURL: process.env.VAPI_API_ENDPOINT || 'https://api.vapi.ai',
      timeout: config.responseTimeout,
      headers: {
        Authorization: `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
        'User-Agent': 'PAKE-System-VoiceAgent/1.0.0',
      },
    });

    // Initialize core components
    this.circuitBreaker = new CircuitBreaker({
      failureThreshold: parseInt(process.env.CIRCUIT_BREAKER_FAILURE_THRESHOLD || '5'),
      timeout: parseInt(process.env.CIRCUIT_BREAKER_TIMEOUT || '30000'),
      resetTimeout: parseInt(process.env.CIRCUIT_BREAKER_RESET_TIMEOUT || '60000'),
      name: 'VapiVoiceAgent',
    });

    this.knowledgeConnector = new KnowledgeConnector({
      contextDepth: parseInt(process.env.KNOWLEDGE_CONTEXT_DEPTH || '5'),
      confidenceThreshold: parseFloat(process.env.KNOWLEDGE_CONFIDENCE_THRESHOLD || '0.7'),
      realTimeSearchEnabled: process.env.REAL_TIME_SEARCH_ENABLED === 'true',
    });

    this.conversationManager = new ConversationManager({
      memoryTtl: parseInt(process.env.CONVERSATION_MEMORY_TTL || '3600'),
      maxContextLength: 4000,
    });

    this.voiceMonitor = new VoiceMonitor({
      qualityThreshold: config.qualityThreshold,
      latencyThreshold: 2000, // 2 seconds
    });

    this.setupEventHandlers();
    this.setupInterceptors();
  }

  /**
   * Create a new voice assistant with knowledge base integration
   */
  async createVoiceAssistant(config: Partial<VoiceAgentConfig> = {}): Promise<string> {
    const assistantConfig = { ...this.config, ...config };

    try {
      const systemPrompt = await this.generateSystemPrompt(assistantConfig.knowledgeBaseId);

      const response = await this.circuitBreaker.execute(async () => {
        return await this.apiClient.post('/assistants', {
          model: {
            provider: 'openai',
            model: 'gpt-4',
            temperature: 0.7,
            maxTokens: 2000,
            systemMessage: systemPrompt,
          },
          voice: {
            provider: 'elevenlabs',
            voiceId: assistantConfig.voiceId,
            optimizeStreamingLatency: assistantConfig.streamingLatency,
            stability: 0.8,
            similarityBoost: 0.8,
            style: 0.2,
          },
          transcriber: {
            provider: 'deepgram',
            model: 'nova-2-general',
            language: 'en-US',
            smartFormat: true,
            punctuate: true,
            diarize: false,
          },
          firstMessage: "Hello! I'm your AI assistant. How can I help you today?",
          recordingEnabled: true,
          endCallMessage: 'Thank you for the conversation. Have a great day!',
          voicemailDetection: {
            enabled: true,
            machineDetectionTimeout: 5000,
          },
        });
      });

      const assistantId = response.data.id;
      this.logger.info(`Created voice assistant: ${assistantId}`);

      this.emit('assistant-created', { assistantId, config: assistantConfig });
      return assistantId;
    } catch (error) {
      this.logger.error('Failed to create voice assistant', error);
      await this.handleError(error, 'createVoiceAssistant');
      throw error;
    }
  }

  /**
   * Initiate a voice call with context awareness
   */
  async initiateCall(request: VoiceCallRequest): Promise<VoiceCallResponse> {
    const startTime = Date.now();

    try {
      // Prepare context for the conversation
      const enhancedContext = await this.prepareConversationContext(request.context);

      // Execute the call through circuit breaker
      const response = await this.circuitBreaker.execute(async () => {
        return await this.apiClient.post('/calls', {
          assistantId: request.assistantId,
          phoneNumberId: request.phoneNumber,
          assistantOverrides: {
            variableValues: {
              userContext: JSON.stringify(enhancedContext),
              knowledgeContext: enhancedContext.knowledgeContext.join('\n'),
              userPreferences: JSON.stringify(enhancedContext.userPreferences),
              currentTime: new Date().toISOString(),
              sessionId: enhancedContext.sessionId,
            },
          },
          webhookUrl: request.webhookUrl,
          maxDurationSeconds: request.maxDuration || 1800, // 30 minutes default
        });
      });

      const callResponse: VoiceCallResponse = {
        callId: response.data.id,
        status: 'initiated',
        metadata: {
          initiatedAt: new Date().toISOString(),
          assistantId: request.assistantId,
          sessionId: enhancedContext.sessionId,
          requestLatency: Date.now() - startTime,
        },
      };

      // Track the active call
      this.activeCalls.set(callResponse.callId, callResponse);

      // Start monitoring the call
      this.voiceMonitor.startCallMonitoring(callResponse.callId, enhancedContext);

      this.logger.info(`Initiated voice call: ${callResponse.callId}`);
      this.emit('call-initiated', callResponse);

      return callResponse;
    } catch (error) {
      this.logger.error('Failed to initiate voice call', error);
      await this.handleError(error, 'initiateCall');

      // Return error response instead of throwing
      return {
        callId: `error-${Date.now()}`,
        status: 'failed',
        metadata: {
          error: error.message,
          timestamp: new Date().toISOString(),
          requestLatency: Date.now() - startTime,
        },
      };
    }
  }

  /**
   * Update an ongoing call with new context or instructions
   */
  async updateCall(callId: string, updates: Partial<ConversationContext>): Promise<void> {
    try {
      const call = this.activeCalls.get(callId);
      if (!call) {
        throw new Error(`Call ${callId} not found or not active`);
      }

      await this.circuitBreaker.execute(async () => {
        return await this.apiClient.patch(`/calls/${callId}`, {
          assistantOverrides: {
            variableValues: {
              updatedContext: JSON.stringify(updates),
              updateTimestamp: new Date().toISOString(),
            },
          },
        });
      });

      this.logger.info(`Updated call context: ${callId}`);
      this.emit('call-updated', { callId, updates });
    } catch (error) {
      this.logger.error(`Failed to update call ${callId}`, error);
      await this.handleError(error, 'updateCall');
      throw error;
    }
  }

  /**
   * End a voice call gracefully
   */
  async endCall(callId: string, reason?: string): Promise<VoiceCallResponse> {
    try {
      const response = await this.circuitBreaker.execute(async () => {
        return await this.apiClient.patch(`/calls/${callId}`, {
          status: 'ended',
          endCallMessage: reason || 'Thank you for the conversation. Goodbye!',
        });
      });

      const call =
        this.activeCalls.get(callId) ||
        ({
          callId,
          status: 'completed',
          metadata: {},
        } as VoiceCallResponse);

      call.status = 'completed';
      call.duration = response.data.duration;
      call.transcript = response.data.transcript;
      call.audioUrl = response.data.audioUrl;
      call.cost = response.data.cost;
      call.metadata.endedAt = new Date().toISOString();
      call.metadata.endReason = reason;

      // Stop monitoring and cleanup
      this.voiceMonitor.stopCallMonitoring(callId);
      this.activeCalls.delete(callId);

      this.logger.info(`Ended voice call: ${callId}, duration: ${call.duration}s`);
      this.emit('call-ended', call);

      return call;
    } catch (error) {
      this.logger.error(`Failed to end call ${callId}`, error);
      await this.handleError(error, 'endCall');
      throw error;
    }
  }

  /**
   * Get call status and metrics
   */
  async getCallStatus(callId: string): Promise<VoiceCallResponse> {
    try {
      const response = await this.circuitBreaker.execute(async () => {
        return await this.apiClient.get(`/calls/${callId}`);
      });

      const callData = response.data;
      const callResponse: VoiceCallResponse = {
        callId,
        status: callData.status,
        duration: callData.duration,
        transcript: callData.transcript,
        audioUrl: callData.audioUrl,
        cost: callData.cost,
        metadata: {
          ...callData.metadata,
          retrievedAt: new Date().toISOString(),
        },
      };

      // Update local tracking
      if (this.activeCalls.has(callId)) {
        this.activeCalls.set(callId, callResponse);
      }

      return callResponse;
    } catch (error) {
      this.logger.error(`Failed to get call status for ${callId}`, error);
      await this.handleError(error, 'getCallStatus');
      throw error;
    }
  }

  /**
   * List all active voice assistants
   */
  async listAssistants(): Promise<any[]> {
    try {
      const response = await this.circuitBreaker.execute(async () => {
        return await this.apiClient.get('/assistants');
      });

      return response.data.data || [];
    } catch (error) {
      this.logger.error('Failed to list assistants', error);
      await this.handleError(error, 'listAssistants');
      throw error;
    }
  }

  /**
   * Generate dynamic system prompt based on knowledge base context
   */
  private async generateSystemPrompt(knowledgeBaseId: string): Promise<string> {
    try {
      const knowledgeContext = await this.knowledgeConnector.getContextSummary(knowledgeBaseId);

      const systemPrompt = `You are a knowledgeable AI assistant for the PAKE System, an advanced Personal Autonomous Knowledge Engine.

KNOWLEDGE CONTEXT:
${knowledgeContext}

CORE CAPABILITIES:
- Access to comprehensive knowledge base with real-time search
- Contextual conversation memory and user preference awareness
- Integration with enterprise automation workflows
- Multi-modal content generation and processing

CONVERSATION GUIDELINES:
1. **Accuracy First**: Provide accurate, fact-based responses using the knowledge base
2. **Natural Communication**: Maintain conversational, engaging tone while being professional
3. **Context Awareness**: Remember conversation history and user preferences
4. **Helpful Guidance**: If uncertain, offer to search for more specific information
5. **Proactive Assistance**: Suggest related topics or actions when relevant
6. **Error Handling**: If technical issues occur, explain clearly and offer alternatives

RESPONSE FORMAT:
- Keep responses concise but comprehensive
- Use natural speech patterns for voice delivery
- Include relevant examples when helpful
- Ask clarifying questions when needed
- Provide actionable next steps when appropriate

KNOWLEDGE INTEGRATION:
- Search the knowledge base for current, accurate information
- Cross-reference multiple sources when possible
- Indicate confidence levels when uncertain
- Update user context based on conversation flow

Remember: You represent the PAKE System's AI capabilities. Be helpful, accurate, and engaging while maintaining professional standards.`;

      return systemPrompt;
    } catch (error) {
      this.logger.warn('Failed to generate dynamic system prompt, using fallback', error);
      return `You are a helpful AI assistant for the PAKE System. Provide accurate, conversational responses and ask clarifying questions when needed. If you don't know something, offer to find more information.`;
    }
  }

  /**
   * Prepare enhanced conversation context with knowledge integration
   */
  private async prepareConversationContext(
    context: ConversationContext
  ): Promise<ConversationContext> {
    try {
      // Get relevant knowledge context
      const knowledgeContext = await this.knowledgeConnector.searchRelevantContext(
        context.previousMessages.map((m) => m.content).join(' '),
        this.config.knowledgeBaseId
      );

      // Enhance context with knowledge and conversation history
      const enhancedContext: ConversationContext = {
        ...context,
        knowledgeContext: knowledgeContext.slice(
          0,
          parseInt(process.env.KNOWLEDGE_CONTEXT_DEPTH || '5')
        ),
        metadata: {
          ...context.metadata,
          enhancedAt: new Date().toISOString(),
          knowledgeContextCount: knowledgeContext.length,
        },
      };

      // Store context in conversation manager
      await this.conversationManager.storeContext(context.sessionId, enhancedContext);

      return enhancedContext;
    } catch (error) {
      this.logger.warn('Failed to enhance conversation context, using original', error);
      return context;
    }
  }

  /**
   * Advanced error handling with fallback strategies
   */
  private async handleError(error: any, operation: string): Promise<void> {
    const errorInfo = {
      operation,
      message: error.message,
      timestamp: new Date().toISOString(),
      code: error.code,
      status: error.response?.status,
    };

    // Log error details
    this.logger.error(`Voice agent error in ${operation}`, errorInfo);

    // Emit error event for monitoring
    this.emit('error', errorInfo);

    // Record error metrics
    this.voiceMonitor.recordError(operation, error);

    // Check if we should attempt fallback
    if (this.shouldUseFallback(error)) {
      await this.attemptFallback(operation, error);
    }
  }

  /**
   * Determine if fallback should be used based on error type
   */
  private shouldUseFallback(error: any): boolean {
    // Use fallback for API unavailability, rate limiting, or timeout errors
    return (
      error.code === 'ECONNRESET' ||
      error.code === 'ETIMEDOUT' ||
      error.response?.status === 429 ||
      error.response?.status === 503 ||
      error.response?.status === 502
    );
  }

  /**
   * Attempt fallback to alternative voice provider
   */
  private async attemptFallback(operation: string, originalError: any): Promise<void> {
    this.logger.info(`Attempting fallback for ${operation} due to: ${originalError.message}`);

    // Implementation would depend on fallback provider configuration
    // For now, just emit event for external handling
    this.emit('fallback-triggered', {
      operation,
      fallbackProvider: this.config.fallbackProvider,
      originalError: originalError.message,
      timestamp: new Date().toISOString(),
    });
  }

  /**
   * Setup HTTP request/response interceptors for monitoring and error handling
   */
  private setupInterceptors(): void {
    // Request interceptor for logging and metrics
    this.apiClient.interceptors.request.use(
      (config) => {
        this.logger.debug(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
        this.voiceMonitor.recordApiCall(config.method || 'unknown', config.url || 'unknown');
        return config;
      },
      (error) => {
        this.logger.error('API Request Error', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor for latency tracking
    this.apiClient.interceptors.response.use(
      (response) => {
        const latency = response.config.metadata?.requestStartTime
          ? Date.now() - response.config.metadata.requestStartTime
          : 0;

        this.voiceMonitor.recordApiLatency(response.config.url || 'unknown', latency);
        return response;
      },
      (error) => {
        this.logger.error('API Response Error', {
          status: error.response?.status,
          message: error.message,
          url: error.config?.url,
        });

        this.voiceMonitor.recordApiError(error.config?.url || 'unknown', error);
        return Promise.reject(error);
      }
    );
  }

  /**
   * Setup event handlers for component communication
   */
  private setupEventHandlers(): void {
    // Circuit breaker events
    this.circuitBreaker.on('open', () => {
      this.logger.warn('Circuit breaker opened - switching to fallback mode');
      this.emit('circuit-breaker-open');
    });

    this.circuitBreaker.on('half-open', () => {
      this.logger.info('Circuit breaker half-open - testing service recovery');
      this.emit('circuit-breaker-half-open');
    });

    this.circuitBreaker.on('closed', () => {
      this.logger.info('Circuit breaker closed - service recovered');
      this.emit('circuit-breaker-closed');
    });

    // Conversation manager events
    this.conversationManager.on('context-expired', (sessionId: string) => {
      this.logger.info(`Conversation context expired for session: ${sessionId}`);
      this.emit('session-expired', { sessionId });
    });

    // Voice monitor events
    this.voiceMonitor.on('quality-warning', (data: any) => {
      this.logger.warn('Voice quality warning', data);
      this.emit('quality-warning', data);
    });

    this.voiceMonitor.on('performance-alert', (data: any) => {
      this.logger.warn('Voice performance alert', data);
      this.emit('performance-alert', data);
    });
  }

  /**
   * Get comprehensive metrics and status information
   */
  getMetrics(): any {
    return {
      activeCalls: this.activeCalls.size,
      circuitBreakerStatus: this.circuitBreaker.getStatus(),
      voiceQuality: this.voiceMonitor.getQualityMetrics(),
      apiMetrics: this.voiceMonitor.getApiMetrics(),
      uptime: process.uptime(),
      timestamp: new Date().toISOString(),
    };
  }

  /**
   * Cleanup resources and stop monitoring
   */
  async shutdown(): Promise<void> {
    this.logger.info('Shutting down VapiVoiceAgent');

    // End all active calls
    for (const [callId, call] of this.activeCalls) {
      try {
        await this.endCall(callId, 'System shutdown');
      } catch (error) {
        this.logger.error(`Failed to end call ${callId} during shutdown`, error);
      }
    }

    // Cleanup resources
    this.voiceMonitor.stop();
    this.circuitBreaker.destroy();
    this.removeAllListeners();

    this.logger.info('VapiVoiceAgent shutdown complete');
  }
}

export default VapiVoiceAgent;
