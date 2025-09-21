/**
 * Core type definitions for Agent Runtime System
 */

/**
 * Agent task input structure
 */
export interface AgentTask {
  /** Unique task identifier */
  id: string;

  /** Task type/category */
  type: AgentTaskType;

  /** Input data for processing */
  input: {
    /** Raw text content to analyze */
    content?: string;
    /** Structured data payload */
    data?: Record<string, any>;
    /** File attachments or references */
    files?: string[];
  };

  /** Task configuration and parameters */
  config: {
    /** Maximum processing time in milliseconds */
    timeout?: number;
    /** Processing priority (1-10, higher = more important) */
    priority?: number;
    /** Additional parameters specific to task type */
    parameters?: Record<string, any>;
  };

  /** Task metadata */
  metadata: {
    /** Source system or user that created the task */
    source: string;
    /** Timestamp when task was created */
    createdAt: string;
    /** Correlation ID for request tracing */
    correlationId?: string;
    /** User context for the task */
    userId?: string;
  };
}

/**
 * Agent execution result structure
 */
export interface AgentResult {
  /** Task ID this result corresponds to */
  taskId: string;

  /** Execution status */
  status: AgentResultStatus;

  /** Processing outputs */
  output: {
    /** Primary result data */
    data?: Record<string, any>;
    /** Extracted entities from content */
    entities?: EntityResult[];
    /** Sentiment analysis results */
    sentiment?: SentimentResult;
    /** Trend analysis results */
    trends?: TrendResult[];
    /** Generated content or summaries */
    content?: string;
  };

  /** Execution metadata */
  metadata: {
    /** Provider that executed the task */
    provider: string;
    /** Processing start time */
    startTime: string;
    /** Processing end time */
    endTime: string;
    /** Processing duration in milliseconds */
    duration: number;
    /** Confidence score (0-1) */
    confidence?: number;
    /** Resource usage statistics */
    usage?: {
      tokens?: number;
      apiCalls?: number;
      memoryMb?: number;
    };
  };

  /** Error information (if status is ERROR) */
  error?: {
    code: string;
    message: string;
    details?: Record<string, any>;
  };
}

/**
 * Supported agent task types
 */
export enum AgentTaskType {
  CONTENT_ANALYSIS = 'content_analysis',
  SENTIMENT_ANALYSIS = 'sentiment_analysis',
  ENTITY_EXTRACTION = 'entity_extraction',
  TREND_DETECTION = 'trend_detection',
  CONTENT_SYNTHESIS = 'content_synthesis',
  DATA_PROCESSING = 'data_processing',
}

/**
 * Agent execution result status
 */
export enum AgentResultStatus {
  SUCCESS = 'success',
  ERROR = 'error',
  TIMEOUT = 'timeout',
  PARTIAL = 'partial',
}

/**
 * Entity extraction result
 */
export interface EntityResult {
  /** Entity type (PERSON, ORGANIZATION, LOCATION, etc.) */
  type: string;
  /** Entity value/name */
  value: string;
  /** Confidence score (0-1) */
  confidence: number;
  /** Position in source text */
  span?: {
    start: number;
    end: number;
  };
  /** Additional entity metadata */
  metadata?: Record<string, any>;
}

/**
 * Sentiment analysis result
 */
export interface SentimentResult {
  /** Overall sentiment score (-1 to 1, negative to positive) */
  score: number;
  /** Sentiment label (positive, negative, neutral) */
  label: 'positive' | 'negative' | 'neutral';
  /** Confidence in sentiment classification (0-1) */
  confidence: number;
  /** Detailed emotion analysis */
  emotions?: {
    [emotion: string]: number; // emotion name -> intensity (0-1)
  };
}

/**
 * Trend analysis result
 */
export interface TrendResult {
  /** Topic or keyword being tracked */
  topic: string;
  /** Trend direction (up, down, stable) */
  direction: 'up' | 'down' | 'stable';
  /** Trend strength (0-1) */
  strength: number;
  /** Time period for this trend */
  period: {
    start: string;
    end: string;
  };
  /** Supporting data points */
  dataPoints?: Array<{
    timestamp: string;
    value: number;
  }>;
}
