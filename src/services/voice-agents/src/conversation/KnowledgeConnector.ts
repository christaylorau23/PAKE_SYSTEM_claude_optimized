/**
 * PAKE System - Knowledge Vault Integration for Voice Agents
 * Real-time knowledge retrieval and context management for conversational AI
 */

import axios, { AxiosInstance } from 'axios';
import { EventEmitter } from 'events';
import { Logger } from '../utils/Logger';

export interface KnowledgeConnectorConfig {
  contextDepth: number; // Number of knowledge items to retrieve
  confidenceThreshold: number; // Minimum confidence for knowledge items
  realTimeSearchEnabled: boolean; // Enable real-time search during conversations
  cacheEnabled?: boolean; // Enable knowledge caching (default: true)
  cacheTtl?: number; // Cache TTL in seconds (default: 300)
  maxQueryLength?: number; // Max query length for search (default: 1000)
}

export interface KnowledgeItem {
  id: string;
  title: string;
  content: string;
  summary: string;
  tags: string[];
  category: string;
  confidence: number;
  relevanceScore: number;
  lastUpdated: Date;
  source: string;
  metadata: Record<string, any>;
}

export interface KnowledgeContext {
  summary: string;
  relevantItems: KnowledgeItem[];
  topicAreas: string[];
  suggestedResponses: string[];
  confidence: number;
  retrievedAt: Date;
}

export interface SearchQuery {
  text: string;
  categories?: string[];
  tags?: string[];
  minConfidence?: number;
  maxResults?: number;
  includeContent?: boolean;
}

export interface KnowledgeMetrics {
  totalQueries: number;
  cacheHits: number;
  cacheMisses: number;
  averageResponseTime: number;
  averageConfidence: number;
  lastQueryTime?: Date;
}

/**
 * KnowledgeConnector - Integrates voice agents with the PAKE knowledge vault
 * Provides real-time knowledge retrieval and context-aware conversation support
 */
export class KnowledgeConnector extends EventEmitter {
  private apiClient: AxiosInstance;
  private logger: Logger;
  private config: KnowledgeConnectorConfig;
  private knowledgeCache: Map<string, { data: any; expiry: number }> = new Map();
  private metrics: KnowledgeMetrics;

  constructor(config: KnowledgeConnectorConfig) {
    super();
    this.config = config;
    this.logger = new Logger('KnowledgeConnector');

    // Initialize metrics
    this.metrics = {
      totalQueries: 0,
      cacheHits: 0,
      cacheMisses: 0,
      averageResponseTime: 0,
      averageConfidence: 0,
    };

    // Initialize HTTP client for knowledge vault API
    this.apiClient = axios.create({
      baseURL: process.env.MCP_SERVER_URL || 'http://localhost:8000',
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'PAKE-VoiceAgent-KnowledgeConnector/1.0.0',
      },
    });

    this.setupInterceptors();
    this.startCacheCleanup();

    this.logger.info('Knowledge connector initialized', {
      contextDepth: config.contextDepth,
      confidenceThreshold: config.confidenceThreshold,
      realTimeSearchEnabled: config.realTimeSearchEnabled,
    });
  }

  /**
   * Get context summary for a specific knowledge base
   */
  async getContextSummary(knowledgeBaseId: string): Promise<string> {
    const startTime = Date.now();

    try {
      // Check cache first
      const cacheKey = `context-summary:${knowledgeBaseId}`;
      const cached = this.getCachedData(cacheKey);
      if (cached) {
        this.metrics.cacheHits++;
        return cached;
      }

      // Fetch from knowledge vault
      const response = await this.apiClient.get(`/api/knowledge/summary/${knowledgeBaseId}`);
      const summary = response.data.summary || 'No context available';

      // Cache the result
      this.setCachedData(cacheKey, summary);
      this.metrics.cacheMisses++;
      this.updateMetrics(startTime);

      this.logger.debug('Retrieved context summary', {
        knowledgeBaseId,
        summaryLength: summary.length,
        cached: false,
      });

      return summary;
    } catch (error) {
      this.logger.error('Failed to get context summary', {
        knowledgeBaseId,
        error: error.message,
      });

      // Return fallback context
      return `I have access to the PAKE knowledge base and can help with questions about stored information, documentation, and system capabilities.`;
    }
  }

  /**
   * Search for relevant knowledge context based on conversation content
   */
  async searchRelevantContext(queryText: string, knowledgeBaseId: string): Promise<string[]> {
    const startTime = Date.now();

    try {
      // Validate and clean query
      const cleanQuery = this.cleanAndValidateQuery(queryText);
      if (!cleanQuery) {
        return [];
      }

      // Check cache
      const cacheKey = `search:${Buffer.from(cleanQuery).toString('base64')}-${knowledgeBaseId}`;
      const cached = this.getCachedData(cacheKey);
      if (cached) {
        this.metrics.cacheHits++;
        return cached;
      }

      // Build search query
      const searchQuery: SearchQuery = {
        text: cleanQuery,
        minConfidence: this.config.confidenceThreshold,
        maxResults: this.config.contextDepth,
        includeContent: true,
      };

      // Execute search
      const response = await this.apiClient.post('/api/knowledge/search', {
        query: searchQuery,
        knowledgeBaseId,
      });

      const results = response.data.results || [];
      const contextItems = results
        .filter((item: any) => item.confidence >= this.config.confidenceThreshold)
        .slice(0, this.config.contextDepth)
        .map((item: any) => this.formatContextItem(item));

      // Cache results
      this.setCachedData(cacheKey, contextItems);
      this.metrics.cacheMisses++;
      this.updateMetrics(
        startTime,
        results.length > 0
          ? results.reduce((sum: number, r: any) => sum + r.confidence, 0) / results.length
          : 0
      );

      this.logger.debug('Retrieved relevant context', {
        queryLength: cleanQuery.length,
        resultsCount: contextItems.length,
        averageConfidence:
          results.length > 0
            ? results.reduce((sum: number, r: any) => sum + r.confidence, 0) / results.length
            : 0,
      });

      this.emit('context-retrieved', {
        query: cleanQuery,
        resultsCount: contextItems.length,
        knowledgeBaseId,
      });

      return contextItems;
    } catch (error) {
      this.logger.error('Failed to search relevant context', {
        query: queryText.substring(0, 100),
        error: error.message,
      });

      this.emit('search-error', {
        query: queryText.substring(0, 100),
        error: error.message,
        knowledgeBaseId,
      });

      return [];
    }
  }

  /**
   * Perform real-time knowledge search during conversation
   */
  async performRealTimeSearch(query: string, context: any = {}): Promise<KnowledgeContext> {
    const startTime = Date.now();

    try {
      if (!this.config.realTimeSearchEnabled) {
        throw new Error('Real-time search is disabled');
      }

      const cleanQuery = this.cleanAndValidateQuery(query);
      if (!cleanQuery) {
        throw new Error('Invalid query for real-time search');
      }

      // Enhanced search with context
      const searchQuery: SearchQuery = {
        text: cleanQuery,
        categories: context.preferredCategories,
        tags: context.relevantTags,
        minConfidence: this.config.confidenceThreshold,
        maxResults: this.config.contextDepth * 2, // Get more for better selection
        includeContent: true,
      };

      const response = await this.apiClient.post('/api/knowledge/real-time-search', {
        query: searchQuery,
        context,
        enhancedMode: true,
      });

      const results = response.data.results || [];
      const knowledgeItems: KnowledgeItem[] = results
        .filter((item: any) => item.confidence >= this.config.confidenceThreshold)
        .slice(0, this.config.contextDepth)
        .map((item: any) => this.mapToKnowledgeItem(item));

      // Generate context summary
      const knowledgeContext: KnowledgeContext = {
        summary: this.generateContextSummary(knowledgeItems),
        relevantItems: knowledgeItems,
        topicAreas: this.extractTopicAreas(knowledgeItems),
        suggestedResponses: this.generateSuggestedResponses(knowledgeItems, cleanQuery),
        confidence:
          knowledgeItems.length > 0
            ? knowledgeItems.reduce((sum, item) => sum + item.confidence, 0) / knowledgeItems.length
            : 0,
        retrievedAt: new Date(),
      };

      this.updateMetrics(startTime, knowledgeContext.confidence);

      this.logger.info('Real-time search completed', {
        query: cleanQuery.substring(0, 50),
        itemsFound: knowledgeItems.length,
        averageConfidence: knowledgeContext.confidence,
        responseTime: Date.now() - startTime,
      });

      this.emit('real-time-search', {
        query: cleanQuery,
        itemsFound: knowledgeItems.length,
        confidence: knowledgeContext.confidence,
      });

      return knowledgeContext;
    } catch (error) {
      this.logger.error('Real-time search failed', {
        query: query.substring(0, 100),
        error: error.message,
      });

      // Return empty context on error
      return {
        summary: 'No relevant information found',
        relevantItems: [],
        topicAreas: [],
        suggestedResponses: [],
        confidence: 0,
        retrievedAt: new Date(),
      };
    }
  }

  /**
   * Get knowledge base statistics and health
   */
  async getKnowledgeBaseHealth(knowledgeBaseId: string): Promise<{
    status: string;
    totalDocuments: number;
    avgConfidence: number;
    lastUpdated: Date;
    categories: string[];
  }> {
    try {
      const response = await this.apiClient.get(`/api/knowledge/health/${knowledgeBaseId}`);
      return response.data;
    } catch (error) {
      this.logger.error('Failed to get knowledge base health', error);
      return {
        status: 'unknown',
        totalDocuments: 0,
        avgConfidence: 0,
        lastUpdated: new Date(),
        categories: [],
      };
    }
  }

  /**
   * Clean and validate search query
   */
  private cleanAndValidateQuery(query: string): string {
    if (!query || typeof query !== 'string') {
      return '';
    }

    // Clean and normalize
    const cleaned = query
      .trim()
      .replace(/\s+/g, ' ')
      .replace(/[^\w\s\-.,!?]/g, ''); // Remove special chars except basic punctuation

    // Check length limits
    const maxLength = this.config.maxQueryLength || 1000;
    if (cleaned.length > maxLength) {
      return cleaned.substring(0, maxLength);
    }

    // Must have some meaningful content
    if (cleaned.length < 3) {
      return '';
    }

    return cleaned;
  }

  /**
   * Format context item for conversation use
   */
  private formatContextItem(item: any): string {
    const title = item.title || 'Untitled';
    const summary = item.summary || item.content?.substring(0, 200) || 'No summary available';
    const confidence = item.confidence || 0;

    return `${title} (confidence: ${(confidence * 100).toFixed(1)}%): ${summary}`;
  }

  /**
   * Map API response to KnowledgeItem
   */
  private mapToKnowledgeItem(item: any): KnowledgeItem {
    return {
      id: item.id || 'unknown',
      title: item.title || 'Untitled',
      content: item.content || '',
      summary: item.summary || item.content?.substring(0, 300) || '',
      tags: item.tags || [],
      category: item.category || 'General',
      confidence: item.confidence || 0,
      relevanceScore: item.relevanceScore || item.confidence || 0,
      lastUpdated: new Date(item.lastUpdated || Date.now()),
      source: item.source || 'Knowledge Vault',
      metadata: item.metadata || {},
    };
  }

  /**
   * Generate context summary from knowledge items
   */
  private generateContextSummary(items: KnowledgeItem[]): string {
    if (items.length === 0) {
      return 'No relevant knowledge found for this query.';
    }

    const topItems = items.slice(0, 3);
    const topics = topItems.map((item) => item.title).join(', ');
    const avgConfidence = items.reduce((sum, item) => sum + item.confidence, 0) / items.length;

    return `Found ${items.length} relevant knowledge items about: ${topics}. Average confidence: ${(avgConfidence * 100).toFixed(1)}%.`;
  }

  /**
   * Extract topic areas from knowledge items
   */
  private extractTopicAreas(items: KnowledgeItem[]): string[] {
    const topics = new Set<string>();

    items.forEach((item) => {
      // Add category
      if (item.category) topics.add(item.category);

      // Add tags
      item.tags.forEach((tag) => topics.add(tag));

      // Extract key terms from title
      const titleTerms = item.title
        .toLowerCase()
        .split(/\s+/)
        .filter((term) => term.length > 3)
        .slice(0, 2);
      titleTerms.forEach((term) => topics.add(term));
    });

    return Array.from(topics).slice(0, 10); // Limit to top 10 topics
  }

  /**
   * Generate suggested responses based on knowledge items
   */
  private generateSuggestedResponses(items: KnowledgeItem[], query: string): string[] {
    const suggestions: string[] = [];

    if (items.length === 0) {
      return [
        "I don't have specific information about that topic.",
        'Would you like me to search for related information?',
        "Could you provide more details about what you're looking for?",
      ];
    }

    // Generate suggestions based on content
    const topItem = items[0];
    suggestions.push(`Based on our knowledge base, ${topItem.summary}`);

    if (items.length > 1) {
      suggestions.push(`There are ${items.length} related topics I can tell you about.`);
    }

    // Suggest exploring related topics
    const relatedTopics = this.extractTopicAreas(items).slice(0, 3);
    if (relatedTopics.length > 0) {
      suggestions.push(`You might also be interested in: ${relatedTopics.join(', ')}.`);
    }

    return suggestions.slice(0, 3);
  }

  /**
   * Cache management
   */
  private getCachedData(key: string): any {
    if (!this.config.cacheEnabled) return null;

    const cached = this.knowledgeCache.get(key);
    if (cached && cached.expiry > Date.now()) {
      return cached.data;
    }

    // Remove expired entry
    if (cached) {
      this.knowledgeCache.delete(key);
    }

    return null;
  }

  private setCachedData(key: string, data: any): void {
    if (!this.config.cacheEnabled) return;

    const ttl = (this.config.cacheTtl || 300) * 1000; // Convert to milliseconds
    this.knowledgeCache.set(key, {
      data,
      expiry: Date.now() + ttl,
    });
  }

  /**
   * Update performance metrics
   */
  private updateMetrics(startTime: number, confidence?: number): void {
    this.metrics.totalQueries++;
    this.metrics.lastQueryTime = new Date();

    const responseTime = Date.now() - startTime;
    this.metrics.averageResponseTime =
      (this.metrics.averageResponseTime * (this.metrics.totalQueries - 1) + responseTime) /
      this.metrics.totalQueries;

    if (confidence !== undefined) {
      this.metrics.averageConfidence =
        (this.metrics.averageConfidence * (this.metrics.totalQueries - 1) + confidence) /
        this.metrics.totalQueries;
    }
  }

  /**
   * Setup HTTP interceptors
   */
  private setupInterceptors(): void {
    this.apiClient.interceptors.request.use(
      (config) => {
        this.logger.debug(`Knowledge API request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        this.logger.error('Knowledge API request error', error);
        return Promise.reject(error);
      }
    );

    this.apiClient.interceptors.response.use(
      (response) => {
        this.logger.debug(`Knowledge API response: ${response.status} for ${response.config.url}`);
        return response;
      },
      (error) => {
        this.logger.error('Knowledge API response error', {
          status: error.response?.status,
          message: error.message,
          url: error.config?.url,
        });
        return Promise.reject(error);
      }
    );
  }

  /**
   * Start cache cleanup interval
   */
  private startCacheCleanup(): void {
    setInterval(() => {
      const now = Date.now();
      let cleanedCount = 0;

      for (const [key, value] of this.knowledgeCache.entries()) {
        if (value.expiry <= now) {
          this.knowledgeCache.delete(key);
          cleanedCount++;
        }
      }

      if (cleanedCount > 0) {
        this.logger.debug(`Cleaned ${cleanedCount} expired cache entries`);
      }
    }, 60000); // Clean every minute
  }

  /**
   * Get performance metrics
   */
  getMetrics(): KnowledgeMetrics {
    return {
      ...this.metrics,
      cacheSize: this.knowledgeCache.size,
    };
  }

  /**
   * Clear cache
   */
  clearCache(): void {
    const size = this.knowledgeCache.size;
    this.knowledgeCache.clear();
    this.logger.info(`Cleared knowledge cache (${size} entries)`);
  }

  /**
   * Test knowledge base connectivity
   */
  async testConnection(): Promise<boolean> {
    try {
      const response = await this.apiClient.get('/api/knowledge/health');
      return response.status === 200;
    } catch (error) {
      this.logger.error('Knowledge base connection test failed', error);
      return false;
    }
  }

  /**
   * Cleanup resources
   */
  destroy(): void {
    this.knowledgeCache.clear();
    this.removeAllListeners();
    this.logger.info('Knowledge connector destroyed');
  }
}

export default KnowledgeConnector;
