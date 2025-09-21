/**
 * ClaudeProvider - Production-grade Anthropic Claude API integration
 *
 * Implements AgentProvider interface with:
 * - Configurable model IDs and parameters
 * - Robust error handling and retry logic
 * - Rate limiting and quota management
 * - Comprehensive logging and metrics
 * - Structured prompt engineering for different task types
 */

import {
  AgentProvider,
  AgentCapability,
  AgentProviderConfig,
  AgentExecutionError,
  AgentErrorCode,
} from './AgentProvider';
import {
  AgentTask,
  AgentResult,
  AgentTaskType,
  AgentResultStatus,
  EntityResult,
  SentimentResult,
  TrendResult,
} from '../types';

/**
 * Claude-specific configuration
 */
export interface ClaudeProviderConfig extends AgentProviderConfig {
  /** Anthropic API key */
  apiKey?: string;
  /** Claude model to use (claude-3-5-sonnet-20241022, claude-3-haiku-20240307, etc.) */
  model?: string;
  /** API base URL (defaults to Anthropic's official API) */
  baseUrl?: string;
  /** Maximum tokens for completion */
  maxTokens?: number;
  /** Temperature for randomness (0.0 - 1.0) */
  temperature?: number;
  /** Top-p sampling parameter */
  topP?: number;
  /** Custom system prompt override */
  systemPrompt?: string;
  /** Enable structured output mode */
  structuredOutput?: boolean;
  /** Retry configuration */
  retry?: {
    attempts: number;
    baseDelay: number;
    maxDelay: number;
    exponentialBase: number;
  };
  /** Rate limiting configuration */
  rateLimiting?: {
    tokensPerMinute: number;
    requestsPerMinute: number;
  };
}

/**
 * Claude API response structure
 */
interface ClaudeAPIResponse {
  id: string;
  type: 'message';
  role: 'assistant';
  content: Array<{
    type: 'text';
    text: string;
  }>;
  model: string;
  stop_reason: 'end_turn' | 'max_tokens' | 'stop_sequence';
  stop_sequence?: string;
  usage: {
    input_tokens: number;
    output_tokens: number;
  };
}

/**
 * Rate limiter for API calls
 */
class RateLimiter {
  private tokenBucket: number;
  private requestBucket: number;
  private lastRefill: number;
  private readonly tokensPerMinute: number;
  private readonly requestsPerMinute: number;

  constructor(tokensPerMinute: number, requestsPerMinute: number) {
    this.tokensPerMinute = tokensPerMinute;
    this.requestsPerMinute = requestsPerMinute;
    this.tokenBucket = tokensPerMinute;
    this.requestBucket = requestsPerMinute;
    this.lastRefill = Date.now();
  }

  async waitForCapacity(estimatedTokens: number): Promise<void> {
    this.refillBuckets();

    if (this.requestBucket < 1 || this.tokenBucket < estimatedTokens) {
      const delay = this.calculateDelay(estimatedTokens);
      await new Promise((resolve) => setTimeout(resolve, delay));
      return this.waitForCapacity(estimatedTokens);
    }

    this.requestBucket -= 1;
    this.tokenBucket -= estimatedTokens;
  }

  private refillBuckets(): void {
    const now = Date.now();
    const timePassed = now - this.lastRefill;
    const refillRatio = timePassed / 60000; // 1 minute

    this.tokenBucket = Math.min(
      this.tokensPerMinute,
      this.tokenBucket + this.tokensPerMinute * refillRatio
    );

    this.requestBucket = Math.min(
      this.requestsPerMinute,
      this.requestBucket + this.requestsPerMinute * refillRatio
    );

    this.lastRefill = now;
  }

  private calculateDelay(estimatedTokens: number): number {
    const tokenDelay = Math.max(
      0,
      ((estimatedTokens - this.tokenBucket) / this.tokensPerMinute) * 60000
    );
    const requestDelay = Math.max(0, ((1 - this.requestBucket) / this.requestsPerMinute) * 60000);
    return Math.max(tokenDelay, requestDelay);
  }
}

/**
 * ClaudeProvider implementation
 */
export class ClaudeProvider implements AgentProvider {
  public readonly name = 'ClaudeProvider';
  public readonly version = '1.0.0';
  public readonly capabilities: AgentCapability[] = [
    AgentCapability.TEXT_ANALYSIS,
    AgentCapability.SENTIMENT_ANALYSIS,
    AgentCapability.ENTITY_EXTRACTION,
    AgentCapability.TREND_DETECTION,
    AgentCapability.CONTENT_GENERATION,
    AgentCapability.DATA_SYNTHESIS,
    AgentCapability.REAL_TIME_PROCESSING,
  ];

  private readonly config: Required<ClaudeProviderConfig>;
  private readonly rateLimiter: RateLimiter;
  private disposed = false;
  private executionCount = 0;
  private totalTokensUsed = 0;

  constructor(config: ClaudeProviderConfig = {}) {
    this.config = {
      apiKey: config.apiKey || process.env.ANTHROPIC_API_KEY || '',
      model: config.model || 'claude-3-5-sonnet-20241022',
      baseUrl: config.baseUrl || 'https://api.anthropic.com',
      maxTokens: config.maxTokens || 4000,
      temperature: config.temperature || 0.7,
      topP: config.topP || 0.9,
      systemPrompt: config.systemPrompt || this.getDefaultSystemPrompt(),
      structuredOutput: config.structuredOutput ?? true,
      timeout: config.timeout || 60000,
      retries: config.retries || 3,
      concurrency: config.concurrency || 5,
      retry: config.retry || {
        attempts: 3,
        baseDelay: 1000,
        maxDelay: 10000,
        exponentialBase: 2,
      },
      rateLimiting: config.rateLimiting || {
        tokensPerMinute: 10000, // Conservative default
        requestsPerMinute: 50,
      },
      ...config,
    };

    if (!this.config.apiKey) {
      throw new Error(
        'Claude API key is required. Set ANTHROPIC_API_KEY environment variable or provide in config.'
      );
    }

    this.rateLimiter = new RateLimiter(
      this.config.rateLimiting.tokensPerMinute,
      this.config.rateLimiting.requestsPerMinute
    );
  }

  /**
   * Execute agent task using Claude API
   */
  async run(task: AgentTask): Promise<AgentResult> {
    if (this.disposed) {
      throw new AgentExecutionError(
        'Provider has been disposed',
        AgentErrorCode.PROVIDER_UNAVAILABLE,
        this.name,
        task
      );
    }

    const startTime = new Date().toISOString();
    const startTimestamp = Date.now();

    try {
      // Validate task input
      this.validateTask(task);

      // Generate structured prompt for task type
      const prompt = this.generatePrompt(task);
      const estimatedTokens = this.estimateTokens(prompt);

      // Wait for rate limiting capacity
      await this.rateLimiter.waitForCapacity(estimatedTokens);

      // Execute with retry logic
      const response = await this.executeWithRetry(prompt, task);

      // Parse and structure the response
      const output = await this.parseResponse(response, task);

      const endTime = new Date().toISOString();
      const duration = Date.now() - startTimestamp;

      // Update metrics
      this.executionCount++;
      this.totalTokensUsed += response.usage.input_tokens + response.usage.output_tokens;

      return {
        taskId: task.id,
        status: AgentResultStatus.SUCCESS,
        output,
        metadata: {
          provider: this.name,
          startTime,
          endTime,
          duration,
          confidence: this.calculateConfidence(response, task),
          usage: {
            tokens: response.usage.input_tokens + response.usage.output_tokens,
            apiCalls: 1,
            memoryMb: this.estimateMemoryUsage(),
          },
        },
      };
    } catch (error) {
      const endTime = new Date().toISOString();
      const duration = Date.now() - startTimestamp;

      if (error instanceof AgentExecutionError) {
        throw error;
      }

      // Convert unknown errors to AgentExecutionError
      const executionError = this.convertToExecutionError(error, task);

      return {
        taskId: task.id,
        status: AgentResultStatus.ERROR,
        output: {},
        metadata: {
          provider: this.name,
          startTime,
          endTime,
          duration,
          usage: {
            tokens: 0,
            apiCalls: 1,
            memoryMb: this.estimateMemoryUsage(),
          },
        },
        error: {
          code: executionError.code,
          message: executionError.message,
          details: { originalError: error instanceof Error ? error.message : String(error) },
        },
      };
    }
  }

  /**
   * Health check for Claude API
   */
  async healthCheck(): Promise<boolean> {
    if (this.disposed || !this.config.apiKey) {
      return false;
    }

    try {
      // Make a minimal API call to check connectivity
      const response = await this.makeAPICall('Hello', 'health_check', 10);
      return response !== null;
    } catch (error) {
      console.warn(`Claude health check failed: ${error}`);
      return false;
    }
  }

  /**
   * Dispose provider and clean up resources
   */
  async dispose(): Promise<void> {
    this.disposed = true;
  }

  /**
   * Get provider statistics
   */
  getStats() {
    return {
      executionCount: this.executionCount,
      totalTokensUsed: this.totalTokensUsed,
      avgTokensPerExecution:
        this.executionCount > 0 ? this.totalTokensUsed / this.executionCount : 0,
      disposed: this.disposed,
      config: {
        model: this.config.model,
        maxTokens: this.config.maxTokens,
        temperature: this.config.temperature,
      },
    };
  }

  /**
   * Validate task input
   */
  private validateTask(task: AgentTask): void {
    if (!task.input.content && !task.input.data) {
      throw new AgentExecutionError(
        'Task must have either content or data input',
        AgentErrorCode.INVALID_INPUT,
        this.name,
        task
      );
    }

    if (task.input.content && task.input.content.length > 100000) {
      throw new AgentExecutionError(
        'Content exceeds maximum length (100,000 characters)',
        AgentErrorCode.INVALID_INPUT,
        this.name,
        task
      );
    }
  }

  /**
   * Generate structured prompt based on task type
   */
  private generatePrompt(task: AgentTask): string {
    const content = task.input.content || JSON.stringify(task.input.data);

    switch (task.type) {
      case AgentTaskType.SENTIMENT_ANALYSIS:
        return this.generateSentimentPrompt(content, task);

      case AgentTaskType.ENTITY_EXTRACTION:
        return this.generateEntityPrompt(content, task);

      case AgentTaskType.TREND_DETECTION:
        return this.generateTrendPrompt(content, task);

      case AgentTaskType.CONTENT_ANALYSIS:
        return this.generateContentAnalysisPrompt(content, task);

      case AgentTaskType.CONTENT_SYNTHESIS:
        return this.generateSynthesisPrompt(content, task);

      case AgentTaskType.DATA_PROCESSING:
        return this.generateDataProcessingPrompt(content, task);

      default:
        return this.generateGenericPrompt(content, task);
    }
  }

  /**
   * Generate sentiment analysis prompt
   */
  private generateSentimentPrompt(content: string, task: AgentTask): string {
    const includeEmotions = task.config.parameters?.includeEmotions ?? true;

    return `<task>sentiment_analysis</task>

Analyze the sentiment of the following content and provide a structured JSON response.

<content>
${content}
</content>

Provide a JSON response with this exact structure:
{
  "sentiment": {
    "score": <number between -1 and 1, where -1 is very negative, 0 is neutral, 1 is very positive>,
    "label": "<positive|negative|neutral>",
    "confidence": <number between 0 and 1 indicating confidence in the analysis>${includeEmotions ? ',\n    "emotions": {\n      "joy": <0-1>,\n      "sadness": <0-1>,\n      "anger": <0-1>,\n      "fear": <0-1>,\n      "surprise": <0-1>,\n      "disgust": <0-1>\n    }' : ''}
  }
}

Consider context, tone, and nuanced language. For mixed sentiments, weight the overall emotional direction.`;
  }

  /**
   * Generate entity extraction prompt
   */
  private generateEntityPrompt(content: string, task: AgentTask): string {
    const entityTypes = task.config.parameters?.entityTypes || [
      'PERSON',
      'ORGANIZATION',
      'LOCATION',
      'DATE',
      'TIME',
      'MONEY',
      'PERCENT',
      'PRODUCT',
      'EVENT',
    ];

    return `<task>entity_extraction</task>

Extract named entities from the following content and provide a structured JSON response.

<content>
${content}
</content>

Extract entities of these types: ${entityTypes.join(', ')}

Provide a JSON response with this exact structure:
{
  "entities": [
    {
      "type": "<entity_type>",
      "value": "<entity_text>",
      "confidence": <0-1>,
      "span": {
        "start": <character_position>,
        "end": <character_position>
      },
      "metadata": {
        "context": "<surrounding_context>",
        "normalized": "<normalized_form_if_applicable>"
      }
    }
  ]
}

Only include entities you are confident about. Provide accurate character positions for spans.`;
  }

  /**
   * Generate trend detection prompt
   */
  private generateTrendPrompt(content: string, task: AgentTask): string {
    return `<task>trend_detection</task>

Analyze the following content for trends and provide a structured JSON response.

<content>
${content}
</content>

Identify significant trends, patterns, or emerging themes in the content.

Provide a JSON response with this exact structure:
{
  "trends": [
    {
      "topic": "<trend_topic>",
      "direction": "<up|down|stable>",
      "strength": <0-1>,
      "period": {
        "start": "<ISO_timestamp>",
        "end": "<ISO_timestamp>"
      },
      "evidence": "<supporting_evidence>",
      "confidence": <0-1>
    }
  ]
}

Focus on substantive trends with clear directional movement and supporting evidence.`;
  }

  /**
   * Generate content analysis prompt
   */
  private generateContentAnalysisPrompt(content: string, task: AgentTask): string {
    return `<task>content_analysis</task>

Perform comprehensive analysis of the following content and provide a structured JSON response.

<content>
${content}
</content>

Analyze the content for key insights, themes, quality metrics, and actionable information.

Provide a JSON response with this exact structure:
{
  "data": {
    "wordCount": <number>,
    "readabilityScore": <0-1>,
    "keyTopics": ["<topic1>", "<topic2>", ...],
    "complexity": "<low|medium|high>",
    "mainThemes": ["<theme1>", "<theme2>", ...],
    "qualityScore": <0-1>,
    "actionableInsights": ["<insight1>", "<insight2>", ...],
    "summary": "<brief_summary>"
  }
}

Provide practical, actionable insights based on the content analysis.`;
  }

  /**
   * Generate content synthesis prompt
   */
  private generateSynthesisPrompt(content: string, task: AgentTask): string {
    const synthesisType = task.config.parameters?.synthesisType || 'summary';
    const targetLength = task.config.parameters?.targetLength || 'medium';

    return `<task>content_synthesis</task>

Synthesize the following content into a ${synthesisType} of ${targetLength} length.

<content>
${content}
</content>

Create a ${synthesisType} that captures the essential information and key insights.

Provide a JSON response with this exact structure:
{
  "content": "<synthesized_content>",
  "data": {
    "synthesisMethod": "${synthesisType}",
    "compressionRatio": <original_length / synthesized_length>,
    "keyPointsRetained": <number>,
    "qualityScore": <0-1>
  }
}

Ensure the synthesized content maintains the core meaning while being concise and clear.`;
  }

  /**
   * Generate data processing prompt
   */
  private generateDataProcessingPrompt(content: string, task: AgentTask): string {
    return `<task>data_processing</task>

Process and analyze the following data structure and provide insights.

<data>
${content}
</data>

Analyze the data for patterns, anomalies, and key metrics.

Provide a JSON response with this exact structure:
{
  "data": {
    "recordsProcessed": <number>,
    "dataQualityScore": <0-1>,
    "patterns": ["<pattern1>", "<pattern2>", ...],
    "anomalies": ["<anomaly1>", "<anomaly2>", ...],
    "keyMetrics": {
      "<metric_name>": <value>,
      ...
    },
    "recommendations": ["<recommendation1>", "<recommendation2>", ...]
  }
}

Focus on actionable insights and data quality assessment.`;
  }

  /**
   * Generate generic prompt for unknown task types
   */
  private generateGenericPrompt(content: string, task: AgentTask): string {
    return `<task>general_analysis</task>

Analyze the following content and provide relevant insights based on the task type: ${task.type}

<content>
${content}
</content>

Provide a JSON response with insights relevant to the task type.

{
  "data": {
    "analysis": "<your_analysis>",
    "insights": ["<insight1>", "<insight2>", ...],
    "confidence": <0-1>
  }
}`;
  }

  /**
   * Execute API call with retry logic
   */
  private async executeWithRetry(prompt: string, task: AgentTask): Promise<ClaudeAPIResponse> {
    let lastError: Error | null = null;

    for (let attempt = 0; attempt < this.config.retry.attempts; attempt++) {
      try {
        return await this.makeAPICall(prompt, task.id);
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));

        // Don't retry on certain error types
        if (this.isNonRetryableError(error)) {
          break;
        }

        // Calculate exponential backoff delay
        if (attempt < this.config.retry.attempts - 1) {
          const delay = Math.min(
            this.config.retry.baseDelay * Math.pow(this.config.retry.exponentialBase, attempt),
            this.config.retry.maxDelay
          );

          console.warn(
            `Claude API call failed (attempt ${attempt + 1}), retrying in ${delay}ms:`,
            error
          );
          await new Promise((resolve) => setTimeout(resolve, delay));
        }
      }
    }

    throw lastError || new Error('Max retry attempts exceeded');
  }

  /**
   * Make actual API call to Claude
   */
  private async makeAPICall(
    prompt: string,
    taskId: string,
    maxTokens?: number
  ): Promise<ClaudeAPIResponse> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

    try {
      const response = await fetch(`${this.config.baseUrl}/v1/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': this.config.apiKey,
          'anthropic-version': '2023-06-01',
        },
        body: JSON.stringify({
          model: this.config.model,
          max_tokens: maxTokens || this.config.maxTokens,
          temperature: this.config.temperature,
          top_p: this.config.topP,
          system: this.config.systemPrompt,
          messages: [
            {
              role: 'user',
              content: prompt,
            },
          ],
        }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Claude API error (${response.status}): ${errorText}`);
      }

      const result = await response.json();
      return result as ClaudeAPIResponse;
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof Error && error.name === 'AbortError') {
        throw new AgentExecutionError(
          'Claude API call timed out',
          AgentErrorCode.TIMEOUT,
          this.name
        );
      }

      throw error;
    }
  }

  /**
   * Parse Claude API response into structured output
   */
  private async parseResponse(
    response: ClaudeAPIResponse,
    task: AgentTask
  ): Promise<AgentResult['output']> {
    const content = response.content[0]?.text || '';

    if (this.config.structuredOutput) {
      try {
        // Try to extract JSON from the response
        const jsonMatch = content.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
          const parsed = JSON.parse(jsonMatch[0]);
          return parsed;
        }
      } catch (error) {
        console.warn('Failed to parse structured output from Claude response:', error);
      }
    }

    // Fallback to unstructured content
    return {
      content,
      data: {
        rawResponse: content,
        structured: false,
        model: response.model,
        stopReason: response.stop_reason,
      },
    };
  }

  /**
   * Calculate confidence score based on response characteristics
   */
  private calculateConfidence(response: ClaudeAPIResponse, task: AgentTask): number {
    let confidence = 0.8; // Base confidence for Claude

    // Adjust based on stop reason
    if (response.stop_reason === 'max_tokens') {
      confidence -= 0.2; // Penalize truncated responses
    }

    // Adjust based on response length
    const responseLength = response.content[0]?.text?.length || 0;
    if (responseLength < 50) {
      confidence -= 0.1; // Penalize very short responses
    }

    // Adjust based on structured output success
    if (this.config.structuredOutput) {
      const hasValidJson = /\{[\s\S]*\}/.test(response.content[0]?.text || '');
      if (!hasValidJson) {
        confidence -= 0.15;
      }
    }

    return Math.max(0.1, Math.min(1.0, confidence));
  }

  /**
   * Estimate token count for input text
   */
  private estimateTokens(text: string): number {
    // Rough estimation: ~4 characters per token for English text
    return Math.ceil(text.length / 4);
  }

  /**
   * Estimate memory usage for the operation
   */
  private estimateMemoryUsage(): number {
    return 256; // Base memory estimate in MB
  }

  /**
   * Check if error should not be retried
   */
  private isNonRetryableError(error: any): boolean {
    if (error instanceof AgentExecutionError) {
      return (
        error.code === AgentErrorCode.INVALID_INPUT ||
        error.code === AgentErrorCode.CONFIGURATION_ERROR
      );
    }

    // HTTP status codes that shouldn't be retried
    if (
      error.message?.includes('400') ||
      error.message?.includes('401') ||
      error.message?.includes('403')
    ) {
      return true;
    }

    return false;
  }

  /**
   * Convert unknown errors to AgentExecutionError
   */
  private convertToExecutionError(error: any, task?: AgentTask): AgentExecutionError {
    const message = error instanceof Error ? error.message : String(error);

    if (message.includes('timeout') || message.includes('AbortError')) {
      return new AgentExecutionError('Request timeout', AgentErrorCode.TIMEOUT, this.name, task);
    }

    if (message.includes('rate') || message.includes('quota')) {
      return new AgentExecutionError(
        'Rate limit exceeded',
        AgentErrorCode.QUOTA_EXCEEDED,
        this.name,
        task
      );
    }

    if (message.includes('401') || message.includes('403')) {
      return new AgentExecutionError(
        'Authentication failed',
        AgentErrorCode.CONFIGURATION_ERROR,
        this.name,
        task
      );
    }

    return new AgentExecutionError(
      `Claude API error: ${message}`,
      AgentErrorCode.INTERNAL_ERROR,
      this.name,
      task
    );
  }

  /**
   * Get default system prompt
   */
  private getDefaultSystemPrompt(): string {
    return `You are an AI assistant specialized in analyzing content and providing structured insights. 

Key principles:
1. Always provide responses in the exact JSON format requested
2. Be precise and accurate in your analysis
3. Include confidence scores when requested
4. Focus on actionable insights
5. Handle edge cases gracefully

When analyzing content:
- Consider context and nuance
- Provide specific, measurable insights where possible
- Include relevant metadata and supporting evidence
- Maintain objectivity and avoid bias

For structured output tasks, always wrap your JSON response in the exact format specified, ensuring valid JSON syntax.`;
  }
}
