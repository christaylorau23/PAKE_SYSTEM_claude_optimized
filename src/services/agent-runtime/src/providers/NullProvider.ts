/**
 * NullProvider - Deterministic stubbed agent provider for testing and development
 *
 * This provider returns consistent, predictable results without external dependencies.
 * Useful for:
 * - Unit testing agent workflows
 * - Development when external services are unavailable
 * - Performance testing without I/O overhead
 * - Contract testing and API validation
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
 * NullProvider implementation with deterministic stubbed results
 */
export class NullProvider implements AgentProvider {
  public readonly name = 'NullProvider';
  public readonly version = '1.0.0';
  public readonly capabilities: AgentCapability[] = [
    AgentCapability.TEXT_ANALYSIS,
    AgentCapability.SENTIMENT_ANALYSIS,
    AgentCapability.ENTITY_EXTRACTION,
    AgentCapability.TREND_DETECTION,
    AgentCapability.CONTENT_GENERATION,
    AgentCapability.DATA_SYNTHESIS,
  ];

  private readonly config: AgentProviderConfig;
  private executionCount = 0;
  private disposed = false;

  constructor(config: AgentProviderConfig = {}) {
    this.config = {
      timeout: 1000,
      retries: 0,
      concurrency: 10,
      ...config,
    };
  }

  /**
   * Execute agent task with deterministic stubbed results
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
    this.executionCount++;

    // Simulate processing delay (deterministic based on task ID)
    const delay = this.calculateDeterministicDelay(task.id);
    await this.sleep(delay);

    const endTime = new Date().toISOString();
    const duration = delay;

    // Generate deterministic results based on task type and input
    const output = this.generateDeterministicOutput(task);

    return {
      taskId: task.id,
      status: AgentResultStatus.SUCCESS,
      output,
      metadata: {
        provider: this.name,
        startTime,
        endTime,
        duration,
        confidence: this.calculateDeterministicConfidence(task.id),
        usage: {
          tokens: this.calculateDeterministicTokens(task),
          apiCalls: 1,
          memoryMb: 128,
        },
      },
    };
  }

  /**
   * Health check - always returns true for null provider
   */
  async healthCheck(): Promise<boolean> {
    return !this.disposed;
  }

  /**
   * Dispose of provider resources
   */
  async dispose(): Promise<void> {
    this.disposed = true;
  }

  /**
   * Get execution statistics
   */
  getStats() {
    return {
      executionCount: this.executionCount,
      disposed: this.disposed,
      config: this.config,
    };
  }

  /**
   * Generate deterministic output based on task type
   */
  private generateDeterministicOutput(task: AgentTask): AgentResult['output'] {
    const hash = this.hashString(task.id);
    const contentHash = task.input.content ? this.hashString(task.input.content) : 0;

    switch (task.type) {
      case AgentTaskType.CONTENT_ANALYSIS:
        return {
          data: {
            wordCount: Math.abs(contentHash % 1000) + 100,
            readabilityScore: Math.abs(hash % 100) / 100,
            keyTopics: this.generateDeterministicTopics(hash),
            complexity: hash % 3 === 0 ? 'low' : hash % 3 === 1 ? 'medium' : 'high',
          },
        };

      case AgentTaskType.SENTIMENT_ANALYSIS:
        return {
          sentiment: this.generateDeterministicSentiment(hash),
        };

      case AgentTaskType.ENTITY_EXTRACTION:
        return {
          entities: this.generateDeterministicEntities(hash, task.input.content || ''),
        };

      case AgentTaskType.TREND_DETECTION:
        return {
          trends: this.generateDeterministicTrends(hash),
        };

      case AgentTaskType.CONTENT_SYNTHESIS:
        return {
          content: this.generateDeterministicContent(hash, task.input.content || ''),
          data: {
            synthesisMethod: 'extractive_summary',
            compressionRatio: (Math.abs(hash % 50) + 10) / 100,
          },
        };

      case AgentTaskType.DATA_PROCESSING:
        return {
          data: {
            recordsProcessed: Math.abs(hash % 10000) + 1000,
            transformations: Math.abs(hash % 5) + 1,
            dataQualityScore: (Math.abs(hash % 80) + 20) / 100,
            processingMethod: hash % 2 === 0 ? 'batch' : 'streaming',
          },
        };

      default:
        return {
          data: {
            message: 'Unknown task type processed',
            taskType: task.type,
            hash: hash.toString(),
          },
        };
    }
  }

  /**
   * Generate deterministic sentiment analysis result
   */
  private generateDeterministicSentiment(hash: number): SentimentResult {
    const score = ((hash % 200) - 100) / 100; // -1 to 1
    const label: SentimentResult['label'] =
      score > 0.1 ? 'positive' : score < -0.1 ? 'negative' : 'neutral';

    return {
      score,
      label,
      confidence: (Math.abs(hash % 40) + 60) / 100, // 0.6 to 1.0
      emotions: {
        joy: Math.max(0, score) * ((hash % 100) / 100),
        sadness: Math.max(0, -score) * ((hash % 100) / 100),
        anger: Math.abs(score) * ((hash % 50) / 100),
        surprise: (hash % 30) / 100,
      },
    };
  }

  /**
   * Generate deterministic entity extraction results
   */
  private generateDeterministicEntities(hash: number, content: string): EntityResult[] {
    const entities: EntityResult[] = [];
    const entityTypes = ['PERSON', 'ORGANIZATION', 'LOCATION', 'DATE', 'MONEY'];
    const entityCount = Math.abs(hash % 5) + 1;

    for (let i = 0; i < entityCount; i++) {
      const entityHash = hash + i * 1000;
      entities.push({
        type: entityTypes[entityHash % entityTypes.length],
        value: `Entity_${entityHash % 1000}`,
        confidence: (Math.abs(entityHash % 40) + 60) / 100,
        span: {
          start: Math.abs(entityHash % Math.max(1, content.length)),
          end: Math.abs(entityHash % Math.max(1, content.length)) + 10,
        },
        metadata: {
          source: 'null_provider',
          extractionMethod: 'deterministic',
        },
      });
    }

    return entities;
  }

  /**
   * Generate deterministic trend analysis results
   */
  private generateDeterministicTrends(hash: number): TrendResult[] {
    const trends: TrendResult[] = [];
    const topics = ['technology', 'market', 'social', 'environment', 'politics'];
    const trendCount = Math.abs(hash % 3) + 1;

    for (let i = 0; i < trendCount; i++) {
      const trendHash = hash + i * 2000;
      const direction: TrendResult['direction'] =
        trendHash % 3 === 0 ? 'up' : trendHash % 3 === 1 ? 'down' : 'stable';

      trends.push({
        topic: topics[trendHash % topics.length],
        direction,
        strength: (Math.abs(trendHash % 80) + 20) / 100,
        period: {
          start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
          end: new Date().toISOString(),
        },
        dataPoints: this.generateDeterministicDataPoints(trendHash),
      });
    }

    return trends;
  }

  /**
   * Generate deterministic data points for trends
   */
  private generateDeterministicDataPoints(hash: number) {
    const points = [];
    const pointCount = 7; // One week of daily data

    for (let i = 0; i < pointCount; i++) {
      const pointHash = hash + i * 100;
      points.push({
        timestamp: new Date(Date.now() - (pointCount - i) * 24 * 60 * 60 * 1000).toISOString(),
        value: Math.abs(pointHash % 100) / 100,
      });
    }

    return points;
  }

  /**
   * Generate deterministic topics
   */
  private generateDeterministicTopics(hash: number): string[] {
    const allTopics = [
      'artificial intelligence',
      'machine learning',
      'data analysis',
      'cloud computing',
      'cybersecurity',
      'blockchain',
      'automation',
      'digital transformation',
      'innovation',
      'sustainability',
    ];

    const topicCount = Math.abs(hash % 3) + 2;
    const topics: string[] = [];

    for (let i = 0; i < topicCount; i++) {
      const topicIndex = (hash + i * 1000) % allTopics.length;
      topics.push(allTopics[topicIndex]);
    }

    return [...new Set(topics)]; // Remove duplicates
  }

  /**
   * Generate deterministic content
   */
  private generateDeterministicContent(hash: number, originalContent: string): string {
    const templates = [
      'Analysis Summary: The content demonstrates {{topic}} with {{sentiment}} sentiment.',
      'Key Insights: {{count}} main themes identified focusing on {{topic}}.',
      'Executive Summary: {{topic}} analysis reveals {{sentiment}} trends with high confidence.',
      'Content Overview: Processed {{length}} characters revealing {{topic}} patterns.',
    ];

    const template = templates[hash % templates.length];
    const sentiment = hash % 3 === 0 ? 'positive' : hash % 3 === 1 ? 'negative' : 'neutral';
    const topic = this.generateDeterministicTopics(hash)[0] || 'general';

    return template
      .replace('{{topic}}', topic)
      .replace('{{sentiment}}', sentiment)
      .replace('{{count}}', (Math.abs(hash % 10) + 1).toString())
      .replace('{{length}}', originalContent.length.toString());
  }

  /**
   * Calculate deterministic processing delay
   */
  private calculateDeterministicDelay(taskId: string): number {
    const hash = this.hashString(taskId);
    return Math.abs(hash % 100) + 50; // 50-150ms delay
  }

  /**
   * Calculate deterministic confidence score
   */
  private calculateDeterministicConfidence(taskId: string): number {
    const hash = this.hashString(taskId);
    return (Math.abs(hash % 30) + 70) / 100; // 0.7 to 1.0
  }

  /**
   * Calculate deterministic token usage
   */
  private calculateDeterministicTokens(task: AgentTask): number {
    const contentLength = task.input.content?.length || 0;
    const hash = this.hashString(task.id);
    return Math.floor(contentLength / 4) + Math.abs(hash % 100) + 50;
  }

  /**
   * Simple string hashing function for deterministic results
   */
  private hashString(str: string): number {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return hash;
  }

  /**
   * Sleep utility for simulating processing time
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
