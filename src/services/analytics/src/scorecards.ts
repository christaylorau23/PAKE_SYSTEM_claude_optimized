/**
 * PAKE System - Scorecards for Prompt Evaluation
 *
 * Comprehensive evaluation system with quantitative metrics for assessing
 * prompt performance, quality, safety, and business impact. Supports
 * custom scorecards and automated evaluation workflows.
 */

import { EventEmitter } from 'events';
import { createLogger, Logger } from '../../orchestrator/src/utils/logger';
import { metrics } from '../../orchestrator/src/utils/metrics';

export interface Scorecard {
  id: string;
  name: string;
  description: string;
  version: string;

  // Configuration
  config: ScorecardConfig;

  // Evaluation criteria
  criteria: EvaluationCriterion[];

  // Weighting and aggregation
  aggregation: AggregationConfig;

  // Metadata
  metadata: {
    createdAt: Date;
    updatedAt: Date;
    createdBy: string;
    tags: string[];
    domain: string; // general, technical, creative, business
    purpose: string; // quality, safety, performance, engagement
    isActive: boolean;
  };
}

export interface ScorecardConfig {
  // Evaluation settings
  evaluation: {
    timeout: number;
    retries: number;
    batchSize: number;
    parallelEvaluations: number;
  };

  // Quality thresholds
  thresholds: {
    excellent: number; // >= 0.9
    good: number; // >= 0.7
    acceptable: number; // >= 0.5
    poor: number; // < 0.5
  };

  // Normalization
  normalization: {
    method: 'minmax' | 'zscore' | 'none';
    outlierHandling: 'clip' | 'remove' | 'keep';
    missingValueStrategy: 'skip' | 'zero' | 'mean';
  };

  // Context requirements
  contextRequirements: {
    requiredFields: string[];
    optionalFields: string[];
  };
}

export interface EvaluationCriterion {
  id: string;
  name: string;
  description: string;
  category: CriterionCategory;

  // Evaluation method
  evaluator: EvaluatorConfig;

  // Scoring
  scoring: {
    scale: 'continuous' | 'discrete' | 'binary';
    range: [number, number];
    higherIsBetter: boolean;
    weight: number; // Relative importance (0-1)
  };

  // Quality checks
  validation: {
    required: boolean;
    minScore?: number;
    maxScore?: number;
    dependencies?: string[]; // Other criterion IDs
  };
}

export interface EvaluatorConfig {
  type: EvaluatorType;
  provider?: 'openai' | 'anthropic' | 'huggingface' | 'custom';
  model?: string;

  // Method-specific configuration
  config: {
    // Rule-based evaluators
    rules?: EvaluationRule[];

    // AI-based evaluators
    prompt?: string;
    temperature?: number;

    // Metric-based evaluators
    metric?: string;
    algorithm?: string;

    // Custom evaluators
    endpoint?: string;
    headers?: Record<string, string>;
  };
}

export interface EvaluationRule {
  id: string;
  condition: string; // JavaScript-like expression
  score: number;
  description: string;
  weight: number;
}

export interface AggregationConfig {
  method: 'weighted_average' | 'geometric_mean' | 'harmonic_mean' | 'custom';

  // Category-level aggregation
  categoryWeights: Record<CriterionCategory, number>;

  // Overall scoring
  overall: {
    includeAllCategories: boolean;
    requireMinimumScores: boolean;
    penaltyForMissing: number;
  };

  // Custom aggregation function (for 'custom' method)
  customFunction?: string;
}

export interface EvaluationResult {
  // Overall results
  overallScore: number;
  overallGrade: 'A' | 'B' | 'C' | 'D' | 'F';

  // Category scores
  categoryScores: Record<CriterionCategory, number>;

  // Individual criterion scores
  criterionScores: Map<string, CriterionResult>;

  // Quality indicators
  quality: {
    confidence: number; // Confidence in evaluation (0-1)
    completeness: number; // Percentage of criteria evaluated
    consistency: number; // Inter-evaluator agreement
    reliability: number; // Score stability across evaluations
  };

  // Metadata
  metadata: {
    scorecardId: string;
    scorecardVersion: string;
    evaluationId: string;
    timestamp: Date;
    processingTime: number;
    evaluatorVersions: Record<string, string>;
  };

  // Detailed feedback
  feedback: {
    strengths: string[];
    weaknesses: string[];
    suggestions: string[];
    criticalIssues: string[];
  };
}

export interface CriterionResult {
  criterionId: string;
  score: number;
  normalizedScore: number;
  confidence: number;

  // Details
  details: {
    rawValue?: any;
    explanation: string;
    evidence: string[];
    reasoning: string;
  };

  // Quality indicators
  quality: {
    valid: boolean;
    reliable: boolean;
    outlier: boolean;
  };

  // Execution info
  execution: {
    evaluatorType: EvaluatorType;
    processingTime: number;
    attempts: number;
    errors?: string[];
  };
}

export enum EvaluatorType {
  // Rule-based evaluators
  RULE_BASED = 'rule_based',
  REGEX_PATTERN = 'regex_pattern',
  LENGTH_CHECK = 'length_check',
  KEYWORD_MATCH = 'keyword_match',

  // AI-based evaluators
  LLM_JUDGE = 'llm_judge',
  LLM_COMPARISON = 'llm_comparison',
  LLM_RUBRIC = 'llm_rubric',

  // Metric-based evaluators
  SEMANTIC_SIMILARITY = 'semantic_similarity',
  SENTIMENT_ANALYSIS = 'sentiment_analysis',
  READABILITY = 'readability',
  TOXICITY_CHECK = 'toxicity_check',
  FACTUAL_ACCURACY = 'factual_accuracy',

  // Statistical evaluators
  STATISTICAL_TEST = 'statistical_test',
  DISTRIBUTION_CHECK = 'distribution_check',
  OUTLIER_DETECTION = 'outlier_detection',

  // Custom evaluators
  CUSTOM_API = 'custom_api',
  CUSTOM_FUNCTION = 'custom_function',
}

export enum CriterionCategory {
  QUALITY = 'quality',
  RELEVANCE = 'relevance',
  ACCURACY = 'accuracy',
  COHERENCE = 'coherence',
  CREATIVITY = 'creativity',
  SAFETY = 'safety',
  PERFORMANCE = 'performance',
  USABILITY = 'usability',
  BUSINESS = 'business',
}

/**
 * Comprehensive scorecard evaluation system
 */
export class ScorecardEvaluator extends EventEmitter {
  private readonly logger: Logger;

  // Registered scorecards
  private readonly scorecards = new Map<string, Scorecard>();

  // Evaluator instances
  private readonly evaluators = new Map<EvaluatorType, BaseEvaluator>();

  // Performance tracking
  private readonly evaluationStats = {
    totalEvaluations: 0,
    successfulEvaluations: 0,
    failedEvaluations: 0,
    averageProcessingTime: 0,
    averageScore: 0,
    scorecardUsage: new Map<string, number>(),
  };

  constructor() {
    super();

    this.logger = createLogger('ScorecardEvaluator');

    // Initialize built-in evaluators
    this.initializeEvaluators();

    // Create default scorecards
    this.createDefaultScorecards();

    this.logger.info('ScorecardEvaluator initialized');
  }

  /**
   * Register a new scorecard
   */
  registerScorecard(scorecard: Scorecard): void {
    this.validateScorecard(scorecard);

    this.scorecards.set(scorecard.id, scorecard);
    this.evaluationStats.scorecardUsage.set(scorecard.id, 0);

    this.logger.info('Scorecard registered', {
      id: scorecard.id,
      name: scorecard.name,
      criteriaCount: scorecard.criteria.length,
    });

    this.emit('scorecard:registered', { scorecard });
  }

  /**
   * Evaluate content using specified scorecards
   */
  async evaluate(
    content: string,
    options: {
      scorecardIds: string[];
      context?: Record<string, any>;
      reference?: string;
      customCriteria?: EvaluationCriterion[];
    }
  ): Promise<EvaluationResult> {
    const evaluationId = this.generateEvaluationId();
    const startTime = Date.now();

    try {
      // Validate inputs
      this.validateEvaluationInputs(content, options);

      // Get scorecards
      const scorecards = options.scorecardIds.map(id => {
        const scorecard = this.scorecards.get(id);
        if (!scorecard) {
          throw new Error(`Scorecard not found: ${id}`);
        }
        return scorecard;
      });

      // Combine all criteria from scorecards
      const allCriteria = this.combineScorecardsAndCustomCriteria(
        scorecards,
        options.customCriteria
      );

      // Evaluate all criteria
      const criterionResults = await this.evaluateAllCriteria(
        content,
        allCriteria,
        options.context,
        options.reference
      );

      // Aggregate results
      const aggregatedResult = this.aggregateResults(
        criterionResults,
        scorecards[0], // Use first scorecard's aggregation config
        evaluationId,
        startTime
      );

      // Update statistics
      this.updateEvaluationStats(
        true,
        Date.now() - startTime,
        aggregatedResult.overallScore
      );

      // Track usage
      options.scorecardIds.forEach(id => {
        const currentUsage = this.evaluationStats.scorecardUsage.get(id) || 0;
        this.evaluationStats.scorecardUsage.set(id, currentUsage + 1);
      });

      // Emit evaluation event
      this.emit('evaluation:completed', {
        evaluationId,
        result: aggregatedResult,
        scorecardIds: options.scorecardIds,
      });

      // Track metrics
      metrics.counter('scorecard_evaluations_total', {
        scorecard_ids: options.scorecardIds.join(','),
        grade: aggregatedResult.overallGrade,
        criteria_count: allCriteria.length.toString(),
      });

      metrics.histogram(
        'scorecard_evaluation_duration',
        Date.now() - startTime,
        'ms',
        {
          criteria_count: allCriteria.length.toString(),
        }
      );

      return aggregatedResult;
    } catch (error) {
      this.updateEvaluationStats(false, Date.now() - startTime, 0);

      this.logger.error('Evaluation failed', {
        evaluationId,
        error: error.message,
        scorecardIds: options.scorecardIds,
      });

      throw new Error(`Scorecard evaluation failed: ${error.message}`);
    }
  }

  /**
   * Batch evaluate multiple contents
   */
  async evaluateBatch(
    contents: Array<{
      id: string;
      content: string;
      context?: Record<string, any>;
      reference?: string;
    }>,
    scorecardIds: string[]
  ): Promise<Map<string, EvaluationResult>> {
    const results = new Map<string, EvaluationResult>();

    this.logger.info('Starting batch evaluation', {
      contentCount: contents.length,
      scorecardIds,
    });

    // Process in batches to manage resource usage
    const batchSize = 10;
    for (let i = 0; i < contents.length; i += batchSize) {
      const batch = contents.slice(i, i + batchSize);

      const batchPromises = batch.map(async item => {
        try {
          const result = await this.evaluate(item.content, {
            scorecardIds,
            context: item.context,
            reference: item.reference,
          });

          return { id: item.id, result };
        } catch (error) {
          this.logger.warn('Batch evaluation item failed', {
            itemId: item.id,
            error: error.message,
          });
          return null;
        }
      });

      const batchResults = await Promise.all(batchPromises);

      batchResults.forEach(item => {
        if (item) {
          results.set(item.id, item.result);
        }
      });
    }

    this.logger.info('Batch evaluation completed', {
      inputCount: contents.length,
      outputCount: results.size,
      successRate: ((results.size / contents.length) * 100).toFixed(1) + '%',
    });

    return results;
  }

  /**
   * Get available scorecards
   */
  getScorecards(): Scorecard[] {
    return Array.from(this.scorecards.values())
      .filter(scorecard => scorecard.metadata.isActive)
      .sort((a, b) => a.name.localeCompare(b.name));
  }

  /**
   * Get scorecard by ID
   */
  getScorecard(id: string): Scorecard | null {
    return this.scorecards.get(id) || null;
  }

  /**
   * Get evaluation statistics
   */
  getEvaluationStats(): typeof this.evaluationStats & {
    successRate: number;
    averageGrade: string;
    mostUsedScorecard: string;
  } {
    const successRate =
      this.evaluationStats.totalEvaluations > 0
        ? this.evaluationStats.successfulEvaluations /
          this.evaluationStats.totalEvaluations
        : 0;

    const averageGrade = this.scoreToGrade(this.evaluationStats.averageScore);

    const mostUsedEntry = Array.from(
      this.evaluationStats.scorecardUsage.entries()
    ).sort((a, b) => b[1] - a[1])[0];
    const mostUsedScorecard = mostUsedEntry ? mostUsedEntry[0] : 'none';

    return {
      ...this.evaluationStats,
      successRate,
      averageGrade,
      mostUsedScorecard,
    };
  }

  // Private methods

  private initializeEvaluators(): void {
    // Register built-in evaluators
    this.evaluators.set(EvaluatorType.RULE_BASED, new RuleBasedEvaluator());
    this.evaluators.set(EvaluatorType.LENGTH_CHECK, new LengthEvaluator());
    this.evaluators.set(EvaluatorType.KEYWORD_MATCH, new KeywordEvaluator());
    this.evaluators.set(EvaluatorType.READABILITY, new ReadabilityEvaluator());
    this.evaluators.set(
      EvaluatorType.SENTIMENT_ANALYSIS,
      new SentimentEvaluator()
    );

    // AI-based evaluators would be initialized here
    // this.evaluators.set(EvaluatorType.LLM_JUDGE, new LLMJudgeEvaluator());
  }

  private createDefaultScorecards(): void {
    // General Quality Scorecard
    const generalQualityScorecard: Scorecard = {
      id: 'general_quality',
      name: 'General Quality Assessment',
      description:
        'Comprehensive evaluation of content quality, relevance, and coherence',
      version: '1.0.0',
      config: this.getDefaultScorecardConfig(),
      criteria: [
        {
          id: 'relevance',
          name: 'Content Relevance',
          description: 'How well the content addresses the original request',
          category: CriterionCategory.RELEVANCE,
          evaluator: {
            type: EvaluatorType.KEYWORD_MATCH,
            config: {
              metric: 'semantic_overlap',
            },
          },
          scoring: {
            scale: 'continuous',
            range: [0, 1],
            higherIsBetter: true,
            weight: 0.25,
          },
          validation: {
            required: true,
            minScore: 0.3,
          },
        },
        {
          id: 'coherence',
          name: 'Content Coherence',
          description: 'Logical flow and structure of the content',
          category: CriterionCategory.COHERENCE,
          evaluator: {
            type: EvaluatorType.READABILITY,
            config: {
              algorithm: 'flesch_kincaid',
            },
          },
          scoring: {
            scale: 'continuous',
            range: [0, 1],
            higherIsBetter: true,
            weight: 0.2,
          },
          validation: {
            required: true,
          },
        },
        {
          id: 'completeness',
          name: 'Response Completeness',
          description: 'Whether the response fully addresses the request',
          category: CriterionCategory.QUALITY,
          evaluator: {
            type: EvaluatorType.LENGTH_CHECK,
            config: {
              metric: 'content_coverage',
            },
          },
          scoring: {
            scale: 'continuous',
            range: [0, 1],
            higherIsBetter: true,
            weight: 0.2,
          },
          validation: {
            required: true,
          },
        },
        {
          id: 'accuracy',
          name: 'Factual Accuracy',
          description: 'Correctness and reliability of information',
          category: CriterionCategory.ACCURACY,
          evaluator: {
            type: EvaluatorType.RULE_BASED,
            config: {
              rules: [
                {
                  id: 'no_false_claims',
                  condition:
                    'content.includes("false") || content.includes("incorrect")',
                  score: 0.3,
                  description: 'Contains potentially false information',
                  weight: 1.0,
                },
              ],
            },
          },
          scoring: {
            scale: 'continuous',
            range: [0, 1],
            higherIsBetter: true,
            weight: 0.25,
          },
          validation: {
            required: true,
            minScore: 0.5,
          },
        },
        {
          id: 'safety',
          name: 'Content Safety',
          description: 'Absence of harmful, toxic, or inappropriate content',
          category: CriterionCategory.SAFETY,
          evaluator: {
            type: EvaluatorType.SENTIMENT_ANALYSIS,
            config: {
              metric: 'toxicity_score',
            },
          },
          scoring: {
            scale: 'continuous',
            range: [0, 1],
            higherIsBetter: true,
            weight: 0.1,
          },
          validation: {
            required: true,
            minScore: 0.8,
          },
        },
      ],
      aggregation: {
        method: 'weighted_average',
        categoryWeights: {
          [CriterionCategory.QUALITY]: 0.3,
          [CriterionCategory.RELEVANCE]: 0.25,
          [CriterionCategory.ACCURACY]: 0.25,
          [CriterionCategory.COHERENCE]: 0.15,
          [CriterionCategory.SAFETY]: 0.05,
          [CriterionCategory.CREATIVITY]: 0,
          [CriterionCategory.PERFORMANCE]: 0,
          [CriterionCategory.USABILITY]: 0,
          [CriterionCategory.BUSINESS]: 0,
        },
        overall: {
          includeAllCategories: false,
          requireMinimumScores: true,
          penaltyForMissing: 0.1,
        },
      },
      metadata: {
        createdAt: new Date(),
        updatedAt: new Date(),
        createdBy: 'system',
        tags: ['general', 'quality', 'default'],
        domain: 'general',
        purpose: 'quality',
        isActive: true,
      },
    };

    this.registerScorecard(generalQualityScorecard);
  }

  private async evaluateAllCriteria(
    content: string,
    criteria: EvaluationCriterion[],
    context?: Record<string, any>,
    reference?: string
  ): Promise<Map<string, CriterionResult>> {
    const results = new Map<string, CriterionResult>();

    // Evaluate criteria in parallel where possible
    const evaluationPromises = criteria.map(async criterion => {
      try {
        const result = await this.evaluateCriterion(
          content,
          criterion,
          context,
          reference
        );
        return { criterionId: criterion.id, result };
      } catch (error) {
        this.logger.warn('Criterion evaluation failed', {
          criterionId: criterion.id,
          error: error.message,
        });
        return null;
      }
    });

    const evaluationResults = await Promise.all(evaluationPromises);

    evaluationResults.forEach(item => {
      if (item) {
        results.set(item.criterionId, item.result);
      }
    });

    return results;
  }

  private async evaluateCriterion(
    content: string,
    criterion: EvaluationCriterion,
    context?: Record<string, any>,
    reference?: string
  ): Promise<CriterionResult> {
    const startTime = Date.now();

    try {
      const evaluator = this.evaluators.get(criterion.evaluator.type);
      if (!evaluator) {
        throw new Error(`Evaluator not found: ${criterion.evaluator.type}`);
      }

      const rawResult = await evaluator.evaluate(
        content,
        criterion,
        context,
        reference
      );

      // Normalize score
      const normalizedScore = this.normalizeScore(
        rawResult.score,
        criterion.scoring.range
      );

      const processingTime = Date.now() - startTime;

      return {
        criterionId: criterion.id,
        score: rawResult.score,
        normalizedScore,
        confidence: rawResult.confidence,
        details: {
          rawValue: rawResult.rawValue,
          explanation: rawResult.explanation,
          evidence: rawResult.evidence,
          reasoning: rawResult.reasoning,
        },
        quality: {
          valid: this.validateCriterionResult(rawResult, criterion),
          reliable: rawResult.confidence >= 0.7,
          outlier: false, // Would implement outlier detection
        },
        execution: {
          evaluatorType: criterion.evaluator.type,
          processingTime,
          attempts: 1,
          errors: rawResult.errors,
        },
      };
    } catch (error) {
      return {
        criterionId: criterion.id,
        score: 0,
        normalizedScore: 0,
        confidence: 0,
        details: {
          explanation: `Evaluation failed: ${error.message}`,
          evidence: [],
          reasoning: 'Error during evaluation',
        },
        quality: {
          valid: false,
          reliable: false,
          outlier: false,
        },
        execution: {
          evaluatorType: criterion.evaluator.type,
          processingTime: Date.now() - startTime,
          attempts: 1,
          errors: [error.message],
        },
      };
    }
  }

  private aggregateResults(
    criterionResults: Map<string, CriterionResult>,
    scorecard: Scorecard,
    evaluationId: string,
    startTime: number
  ): EvaluationResult {
    // Calculate category scores
    const categoryScores: Record<CriterionCategory, number> = {} as any;
    const categoryCounts: Record<CriterionCategory, number> = {} as any;

    // Initialize categories
    Object.values(CriterionCategory).forEach(category => {
      categoryScores[category] = 0;
      categoryCounts[category] = 0;
    });

    // Aggregate by category
    for (const criterion of scorecard.criteria) {
      const result = criterionResults.get(criterion.id);
      if (result && result.quality.valid) {
        const weightedScore = result.normalizedScore * criterion.scoring.weight;
        categoryScores[criterion.category] += weightedScore;
        categoryCounts[criterion.category] += criterion.scoring.weight;
      }
    }

    // Normalize category scores
    Object.keys(categoryScores).forEach(category => {
      const cat = category as CriterionCategory;
      if (categoryCounts[cat] > 0) {
        categoryScores[cat] = categoryScores[cat] / categoryCounts[cat];
      }
    });

    // Calculate overall score using aggregation method
    const overallScore = this.calculateOverallScore(
      categoryScores,
      scorecard.aggregation
    );
    const overallGrade = this.scoreToGrade(overallScore);

    // Calculate quality metrics
    const validResults = Array.from(criterionResults.values()).filter(
      r => r.quality.valid
    );
    const averageConfidence =
      validResults.length > 0
        ? validResults.reduce((sum, r) => sum + r.confidence, 0) /
          validResults.length
        : 0;

    const completeness = validResults.length / scorecard.criteria.length;

    // Generate feedback
    const feedback = this.generateFeedback(
      criterionResults,
      scorecard.criteria,
      overallScore
    );

    return {
      overallScore,
      overallGrade,
      categoryScores,
      criterionScores: criterionResults,
      quality: {
        confidence: averageConfidence,
        completeness,
        consistency: 0.85, // Would calculate from multiple evaluations
        reliability: averageConfidence,
      },
      metadata: {
        scorecardId: scorecard.id,
        scorecardVersion: scorecard.version,
        evaluationId,
        timestamp: new Date(),
        processingTime: Date.now() - startTime,
        evaluatorVersions: this.getEvaluatorVersions(),
      },
      feedback,
    };
  }

  private calculateOverallScore(
    categoryScores: Record<CriterionCategory, number>,
    aggregation: AggregationConfig
  ): number {
    switch (aggregation.method) {
      case 'weighted_average':
        let weightedSum = 0;
        let totalWeight = 0;

        Object.entries(categoryScores).forEach(([category, score]) => {
          const weight =
            aggregation.categoryWeights[category as CriterionCategory] || 0;
          weightedSum += score * weight;
          totalWeight += weight;
        });

        return totalWeight > 0 ? weightedSum / totalWeight : 0;

      case 'geometric_mean':
        const nonZeroScores = Object.values(categoryScores).filter(s => s > 0);
        if (nonZeroScores.length === 0) return 0;

        const product = nonZeroScores.reduce((prod, score) => prod * score, 1);
        return Math.pow(product, 1 / nonZeroScores.length);

      case 'harmonic_mean':
        const validScores = Object.values(categoryScores).filter(s => s > 0);
        if (validScores.length === 0) return 0;

        const reciprocalSum = validScores.reduce(
          (sum, score) => sum + 1 / score,
          0
        );
        return validScores.length / reciprocalSum;

      default:
        // Default to weighted average
        return this.calculateOverallScore(categoryScores, {
          ...aggregation,
          method: 'weighted_average',
        });
    }
  }

  private scoreToGrade(score: number): 'A' | 'B' | 'C' | 'D' | 'F' {
    if (score >= 0.9) return 'A';
    if (score >= 0.8) return 'B';
    if (score >= 0.7) return 'C';
    if (score >= 0.6) return 'D';
    return 'F';
  }

  private generateFeedback(
    results: Map<string, CriterionResult>,
    criteria: EvaluationCriterion[],
    overallScore: number
  ): EvaluationResult['feedback'] {
    const feedback = {
      strengths: [] as string[],
      weaknesses: [] as string[],
      suggestions: [] as string[],
      criticalIssues: [] as string[],
    };

    // Analyze individual criteria
    for (const criterion of criteria) {
      const result = results.get(criterion.id);
      if (!result) continue;

      if (result.normalizedScore >= 0.8) {
        feedback.strengths.push(
          `Strong ${criterion.name.toLowerCase()}: ${result.details.explanation}`
        );
      } else if (result.normalizedScore <= 0.4) {
        feedback.weaknesses.push(
          `Weak ${criterion.name.toLowerCase()}: ${result.details.explanation}`
        );
        feedback.suggestions.push(
          `Improve ${criterion.name.toLowerCase()} by focusing on ${criterion.description.toLowerCase()}`
        );
      }

      if (
        criterion.validation.minScore &&
        result.normalizedScore < criterion.validation.minScore
      ) {
        feedback.criticalIssues.push(
          `${criterion.name} below minimum threshold (${result.normalizedScore.toFixed(2)} < ${criterion.validation.minScore})`
        );
      }
    }

    // Overall feedback
    if (overallScore >= 0.8) {
      feedback.strengths.push(
        'Overall high-quality response with strong performance across criteria'
      );
    } else if (overallScore <= 0.5) {
      feedback.suggestions.push(
        'Consider revising the approach to better meet the evaluation criteria'
      );
    }

    return feedback;
  }

  private normalizeScore(score: number, range: [number, number]): number {
    const [min, max] = range;
    return Math.max(0, Math.min(1, (score - min) / (max - min)));
  }

  private validateCriterionResult(
    result: any,
    criterion: EvaluationCriterion
  ): boolean {
    if (!result) return false;

    const score = result.score;
    if (typeof score !== 'number' || isNaN(score)) return false;

    const [min, max] = criterion.scoring.range;
    return score >= min && score <= max;
  }

  private validateScorecard(scorecard: Scorecard): void {
    if (!scorecard.id || !scorecard.name) {
      throw new Error('Scorecard must have id and name');
    }

    if (scorecard.criteria.length === 0) {
      throw new Error('Scorecard must have at least one criterion');
    }

    // Validate weight normalization
    const totalWeight = scorecard.criteria.reduce(
      (sum, criterion) => sum + criterion.scoring.weight,
      0
    );
    if (Math.abs(totalWeight - 1.0) > 0.01) {
      this.logger.warn('Scorecard weights do not sum to 1.0', {
        scorecardId: scorecard.id,
        totalWeight,
      });
    }
  }

  private validateEvaluationInputs(content: string, options: any): void {
    if (!content || typeof content !== 'string') {
      throw new Error('Content must be a non-empty string');
    }

    if (!options.scorecardIds || options.scorecardIds.length === 0) {
      throw new Error('At least one scorecard ID must be specified');
    }
  }

  private combineScorecardsAndCustomCriteria(
    scorecards: Scorecard[],
    customCriteria?: EvaluationCriterion[]
  ): EvaluationCriterion[] {
    const allCriteria: EvaluationCriterion[] = [];

    // Add criteria from all scorecards
    scorecards.forEach(scorecard => {
      allCriteria.push(...scorecard.criteria);
    });

    // Add custom criteria
    if (customCriteria) {
      allCriteria.push(...customCriteria);
    }

    // Remove duplicates by ID
    const criteriaMap = new Map<string, EvaluationCriterion>();
    allCriteria.forEach(criterion => {
      criteriaMap.set(criterion.id, criterion);
    });

    return Array.from(criteriaMap.values());
  }

  private updateEvaluationStats(
    success: boolean,
    processingTime: number,
    score: number
  ): void {
    this.evaluationStats.totalEvaluations++;

    if (success) {
      this.evaluationStats.successfulEvaluations++;

      // Update running averages
      const n = this.evaluationStats.successfulEvaluations;
      this.evaluationStats.averageProcessingTime =
        (this.evaluationStats.averageProcessingTime * (n - 1) +
          processingTime) /
        n;
      this.evaluationStats.averageScore =
        (this.evaluationStats.averageScore * (n - 1) + score) / n;
    } else {
      this.evaluationStats.failedEvaluations++;
    }
  }

  private getEvaluatorVersions(): Record<string, string> {
    const versions: Record<string, string> = {};

    for (const [type, evaluator] of this.evaluators) {
      versions[type] = evaluator.version;
    }

    return versions;
  }

  private getDefaultScorecardConfig(): ScorecardConfig {
    return {
      evaluation: {
        timeout: 30000,
        retries: 3,
        batchSize: 10,
        parallelEvaluations: 5,
      },
      thresholds: {
        excellent: 0.9,
        good: 0.7,
        acceptable: 0.5,
        poor: 0.5,
      },
      normalization: {
        method: 'minmax',
        outlierHandling: 'clip',
        missingValueStrategy: 'skip',
      },
      contextRequirements: {
        requiredFields: [],
        optionalFields: ['domain', 'audience', 'purpose'],
      },
    };
  }

  private generateEvaluationId(): string {
    return `eval_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Cleanup resources
   */
  cleanup(): void {
    this.scorecards.clear();
    this.evaluators.clear();
    this.removeAllListeners();
  }
}

// Base evaluator interface
abstract class BaseEvaluator {
  abstract readonly version: string;

  abstract evaluate(
    content: string,
    criterion: EvaluationCriterion,
    context?: Record<string, any>,
    reference?: string
  ): Promise<{
    score: number;
    confidence: number;
    rawValue?: any;
    explanation: string;
    evidence: string[];
    reasoning: string;
    errors?: string[];
  }>;
}

// Simple evaluator implementations
class RuleBasedEvaluator extends BaseEvaluator {
  readonly version = '1.0.0';

  async evaluate(
    content: string,
    criterion: EvaluationCriterion
  ): Promise<any> {
    const rules = criterion.evaluator.config.rules || [];
    let totalScore = 0;
    let totalWeight = 0;
    const evidence: string[] = [];

    for (const rule of rules) {
      try {
        // Simple rule evaluation (would use a proper expression evaluator)
        const matches = eval(
          rule.condition.replace('content', `"${content.replace(/"/g, '\\"')}"`)
        );
        if (matches) {
          totalScore += rule.score * rule.weight;
          evidence.push(`Rule "${rule.description}" triggered`);
        }
        totalWeight += rule.weight;
      } catch (error) {
        // Skip invalid rules
      }
    }

    const finalScore = totalWeight > 0 ? totalScore / totalWeight : 0.5;

    return {
      score: finalScore,
      confidence: 0.8,
      explanation: `Evaluated ${rules.length} rules`,
      evidence,
      reasoning: 'Rule-based scoring with weighted aggregation',
    };
  }
}

class LengthEvaluator extends BaseEvaluator {
  readonly version = '1.0.0';

  async evaluate(content: string): Promise<any> {
    const length = content.length;

    // Score based on content length (optimal around 100-1000 characters)
    let score = 0;
    if (length < 50) {
      score = (length / 50) * 0.5; // Too short
    } else if (length <= 1000) {
      score = 0.5 + ((length - 50) / 950) * 0.5; // Optimal range
    } else {
      score = Math.max(0.1, 1.0 - (length - 1000) / 2000); // Too long
    }

    return {
      score,
      confidence: 0.9,
      rawValue: length,
      explanation: `Content length is ${length} characters`,
      evidence: [`Text contains ${length} characters`],
      reasoning: 'Length-based scoring with optimal range 50-1000 characters',
    };
  }
}

class KeywordEvaluator extends BaseEvaluator {
  readonly version = '1.0.0';

  async evaluate(
    content: string,
    criterion: EvaluationCriterion,
    context?: Record<string, any>
  ): Promise<any> {
    const keywords = context?.keywords || [];
    if (!keywords.length) {
      return {
        score: 0.5,
        confidence: 0.3,
        explanation: 'No keywords provided for matching',
        evidence: [],
        reasoning: 'Default score due to missing keywords',
      };
    }

    const contentLower = content.toLowerCase();
    const matches = keywords.filter((keyword: string) =>
      contentLower.includes(keyword.toLowerCase())
    );

    const score = matches.length / keywords.length;

    return {
      score,
      confidence: 0.8,
      rawValue: matches,
      explanation: `Found ${matches.length}/${keywords.length} keywords`,
      evidence: matches.map((keyword: string) => `Keyword "${keyword}" found`),
      reasoning: 'Keyword matching with ratio-based scoring',
    };
  }
}

class ReadabilityEvaluator extends BaseEvaluator {
  readonly version = '1.0.0';

  async evaluate(content: string): Promise<any> {
    // Simplified readability calculation (Flesch Reading Ease approximation)
    const sentences = content
      .split(/[.!?]+/)
      .filter(s => s.trim().length > 0).length;
    const words = content.split(/\s+/).filter(w => w.length > 0).length;
    const syllables = this.countSyllables(content);

    if (sentences === 0 || words === 0) {
      return {
        score: 0,
        confidence: 0.5,
        explanation: 'Unable to calculate readability for empty content',
        evidence: [],
        reasoning: 'No valid sentences or words found',
      };
    }

    const avgSentenceLength = words / sentences;
    const avgSyllablesPerWord = syllables / words;

    // Simplified Flesch Reading Ease formula
    const fleschScore =
      206.835 - 1.015 * avgSentenceLength - 84.6 * avgSyllablesPerWord;

    // Normalize to 0-1 range (Flesch scores typically range 0-100)
    const normalizedScore = Math.max(0, Math.min(1, fleschScore / 100));

    return {
      score: normalizedScore,
      confidence: 0.7,
      rawValue: {
        fleschScore,
        sentences,
        words,
        syllables,
        avgSentenceLength,
        avgSyllablesPerWord,
      },
      explanation: `Flesch Reading Ease score: ${fleschScore.toFixed(1)}`,
      evidence: [
        `${sentences} sentences`,
        `${words} words`,
        `Average ${avgSentenceLength.toFixed(1)} words per sentence`,
      ],
      reasoning: 'Flesch Reading Ease calculation for readability assessment',
    };
  }

  private countSyllables(text: string): number {
    // Simplified syllable counting
    return text
      .toLowerCase()
      .replace(/[^a-z]/g, '')
      .replace(/[aeiouy]+/g, 'V')
      .replace(/V+/g, 'V').length;
  }
}

class SentimentEvaluator extends BaseEvaluator {
  readonly version = '1.0.0';

  async evaluate(content: string): Promise<any> {
    // Simplified sentiment analysis
    const positiveWords = [
      'good',
      'great',
      'excellent',
      'amazing',
      'wonderful',
      'fantastic',
      'love',
      'like',
      'happy',
      'pleased',
    ];
    const negativeWords = [
      'bad',
      'terrible',
      'awful',
      'horrible',
      'hate',
      'dislike',
      'angry',
      'sad',
      'disappointed',
      'frustrated',
    ];

    const contentLower = content.toLowerCase();
    const words = contentLower.split(/\s+/);

    let positiveCount = 0;
    let negativeCount = 0;

    words.forEach(word => {
      if (positiveWords.includes(word)) positiveCount++;
      if (negativeWords.includes(word)) negativeCount++;
    });

    const totalSentimentWords = positiveCount + negativeCount;

    let sentimentScore = 0.5; // Neutral
    if (totalSentimentWords > 0) {
      sentimentScore = positiveCount / totalSentimentWords;
    }

    // For safety evaluation, we want high scores for positive/neutral sentiment
    const safetyScore =
      sentimentScore >= 0.3
        ? 1.0 - Math.abs(sentimentScore - 0.5) * 0.5
        : sentimentScore;

    return {
      score: safetyScore,
      confidence: totalSentimentWords > 0 ? 0.6 : 0.3,
      rawValue: {
        positive: positiveCount,
        negative: negativeCount,
        sentiment: sentimentScore,
      },
      explanation: `Sentiment: ${sentimentScore > 0.6 ? 'positive' : sentimentScore < 0.4 ? 'negative' : 'neutral'}`,
      evidence: [
        `${positiveCount} positive words`,
        `${negativeCount} negative words`,
      ],
      reasoning: 'Dictionary-based sentiment analysis for content safety',
    };
  }
}

export { ScorecardEvaluator };
