/**
 * PAKE System - APE (Automatic Prompt Experiments) Module
 *
 * A/B testing framework for prompts with automatic evaluation, metric tracking,
 * and intelligent promotion of best-performing prompts. Includes statistical
 * significance testing and experiment lifecycle management.
 */

import { EventEmitter } from 'events';
import { createLogger, Logger } from '../../orchestrator/src/utils/logger';
import { metrics } from '../../orchestrator/src/utils/metrics';
import { ScorecardEvaluator, EvaluationResult } from './scorecards';

export interface PromptExperiment {
  id: string;
  name: string;
  description: string;
  status: ExperimentStatus;

  // Experiment configuration
  config: ExperimentConfig;

  // Prompt variants
  variants: PromptVariant[];

  // Results and statistics
  results: ExperimentResults;

  // Metadata
  metadata: {
    createdAt: Date;
    updatedAt: Date;
    createdBy: string;
    tags: string[];
    hypothesis: string;
    targetMetric: string;
  };
}

export interface PromptVariant {
  id: string;
  name: string;
  prompt: string;
  systemPrompt?: string;
  parameters: {
    temperature: number;
    maxTokens: number;
    topP: number;
    frequencyPenalty: number;
    presencePenalty: number;
  };
  trafficAllocation: number; // Percentage of traffic (0-100)
  isControl: boolean;
  metadata: {
    generationMethod?: 'manual' | 'automated' | 'template';
    inspiration?: string;
    expectedImprovement?: string;
  };
}

export interface ExperimentConfig {
  // Statistical configuration
  statistical: {
    confidenceLevel: number; // 0.90, 0.95, 0.99
    minimumDetectableEffect: number; // Minimum effect size to detect
    power: number; // Statistical power (0.8, 0.9)
    alpha: number; // Significance level (0.05, 0.01)
  };

  // Sampling configuration
  sampling: {
    minSampleSize: number;
    maxSampleSize: number;
    sampleRatio: number[]; // Traffic split ratios
    stratification?: {
      enabled: boolean;
      dimensions: string[]; // user_type, platform, region, etc.
    };
  };

  // Duration and stopping rules
  duration: {
    maxDurationHours: number;
    minDurationHours: number;
    earlyStoppingEnabled: boolean;
    futilityStoppingEnabled: boolean;
  };

  // Evaluation configuration
  evaluation: {
    scorecardIds: string[];
    evaluationFrequency: 'realtime' | 'batch' | 'scheduled';
    batchSize: number;
    evaluationTimeout: number;
  };

  // Safety and guardrails
  safety: {
    maxErrorRate: number; // Stop if error rate exceeds this
    maxLatencyMs: number; // Stop if latency exceeds this
    contentFilters: string[]; // Content safety filters to apply
    rollbackThreshold: number; // Auto-rollback if performance degrades
  };
}

export interface ExperimentResults {
  // Overall status
  status: 'running' | 'completed' | 'stopped' | 'failed';
  startTime: Date;
  endTime?: Date;

  // Sample sizes
  totalSamples: number;
  variantSamples: Map<string, number>;

  // Performance metrics per variant
  variantMetrics: Map<string, VariantMetrics>;

  // Statistical analysis
  statisticalResults: {
    significanceTest: SignificanceTestResult;
    effectSize: number;
    confidence: number;
    recommendation: 'promote' | 'continue' | 'stop' | 'rollback';
    winner?: string; // Winning variant ID
  };

  // Quality metrics
  qualityMetrics: {
    overallQuality: number;
    errorRate: number;
    averageLatency: number;
    userSatisfaction: number;
  };
}

export interface VariantMetrics {
  variantId: string;
  sampleSize: number;

  // Performance metrics
  performance: {
    successRate: number;
    averageScore: number;
    scoreDistribution: number[];
    errorRate: number;
    averageLatency: number;
    throughput: number;
  };

  // Quality metrics from scorecards
  quality: {
    averageQuality: number;
    relevanceScore: number;
    coherenceScore: number;
    creativityScore: number;
    accuracyScore: number;
    safetyScore: number;
  };

  // Business metrics
  business: {
    conversionRate?: number;
    engagementRate?: number;
    retentionRate?: number;
    userSatisfaction?: number;
  };

  // Statistical measures
  statistics: {
    mean: number;
    standardDeviation: number;
    confidenceInterval: [number, number];
    percentiles: Map<number, number>; // 50th, 90th, 95th, 99th
  };
}

export interface SignificanceTestResult {
  testType: 'ttest' | 'mannwhitney' | 'chi_square' | 'bayesian';
  pValue: number;
  isSignificant: boolean;
  effectSize: number;
  confidenceInterval: [number, number];
  degreesFreedom?: number;
  testStatistic: number;
}

export enum ExperimentStatus {
  DRAFT = 'draft',
  READY = 'ready',
  RUNNING = 'running',
  PAUSED = 'paused',
  COMPLETED = 'completed',
  STOPPED = 'stopped',
  FAILED = 'failed',
}

/**
 * APE engine for automatic prompt experimentation
 */
export class APEEngine extends EventEmitter {
  private readonly logger: Logger;
  private readonly scorecard: ScorecardEvaluator;

  // Active experiments
  private readonly activeExperiments = new Map<string, PromptExperiment>();

  // Experiment history and results
  private readonly experimentHistory = new Map<string, PromptExperiment>();

  // Traffic allocation tracking
  private readonly trafficAllocator = new TrafficAllocator();

  // Statistical analyzer
  private readonly statisticalAnalyzer = new StatisticalAnalyzer();

  // Performance tracking
  private readonly performanceStats = {
    totalExperiments: 0,
    activeExperiments: 0,
    completedExperiments: 0,
    promotedVariants: 0,
    averageExperimentDuration: 0,
    successRate: 0,
  };

  constructor(scorecard: ScorecardEvaluator) {
    super();

    this.logger = createLogger('APEEngine');
    this.scorecard = scorecard;

    // Start background tasks
    this.startMonitoringTasks();

    this.logger.info('APE Engine initialized');
  }

  /**
   * Create a new prompt experiment
   */
  async createExperiment(
    name: string,
    description: string,
    variants: Omit<PromptVariant, 'id'>[],
    config: Partial<ExperimentConfig> = {},
    metadata: Partial<PromptExperiment['metadata']> = {}
  ): Promise<PromptExperiment> {
    const experimentId = this.generateExperimentId();

    // Create variants with IDs
    const experimentVariants: PromptVariant[] = variants.map(
      (variant, index) => ({
        ...variant,
        id: `${experimentId}_variant_${index}`,
        trafficAllocation: variant.trafficAllocation || 100 / variants.length,
      })
    );

    // Validate traffic allocation
    this.validateTrafficAllocation(experimentVariants);

    const experiment: PromptExperiment = {
      id: experimentId,
      name,
      description,
      status: ExperimentStatus.DRAFT,
      config: this.mergeWithDefaultConfig(config),
      variants: experimentVariants,
      results: this.initializeResults(),
      metadata: {
        createdAt: new Date(),
        updatedAt: new Date(),
        createdBy: metadata.createdBy || 'system',
        tags: metadata.tags || [],
        hypothesis: metadata.hypothesis || '',
        targetMetric: metadata.targetMetric || 'overall_quality',
      },
    };

    // Store experiment
    this.activeExperiments.set(experimentId, experiment);
    this.performanceStats.totalExperiments++;

    this.logger.info('Experiment created', {
      experimentId,
      name,
      variantCount: variants.length,
      targetMetric: experiment.metadata.targetMetric,
    });

    // Emit event
    this.emit('experiment:created', { experiment });

    return experiment;
  }

  /**
   * Generate prompt variants automatically
   */
  async generateVariants(
    basePrompt: string,
    count: number = 3,
    strategies: VariantGenerationStrategy[] = [
      'temperature',
      'rephrase',
      'structure',
    ]
  ): Promise<Omit<PromptVariant, 'id'>[]> {
    const variants: Omit<PromptVariant, 'id'>[] = [];

    // Add control variant (original)
    variants.push({
      name: 'Control',
      prompt: basePrompt,
      parameters: {
        temperature: 0.7,
        maxTokens: 1000,
        topP: 1.0,
        frequencyPenalty: 0.0,
        presencePenalty: 0.0,
      },
      trafficAllocation: 100 / (count + 1),
      isControl: true,
      metadata: {
        generationMethod: 'manual',
        inspiration: 'Original baseline prompt',
      },
    });

    // Generate variants using different strategies
    for (let i = 0; i < count; i++) {
      const strategy = strategies[i % strategies.length];
      const variant = await this.generateVariantByStrategy(
        basePrompt,
        strategy,
        i
      );
      variants.push(variant);
    }

    this.logger.info('Generated prompt variants', {
      basePromptLength: basePrompt.length,
      variantCount: variants.length,
      strategies,
    });

    return variants;
  }

  /**
   * Start an experiment
   */
  async startExperiment(experimentId: string): Promise<void> {
    const experiment = this.activeExperiments.get(experimentId);
    if (!experiment) {
      throw new Error(`Experiment not found: ${experimentId}`);
    }

    if (
      experiment.status !== ExperimentStatus.DRAFT &&
      experiment.status !== ExperimentStatus.READY
    ) {
      throw new Error(
        `Cannot start experiment in status: ${experiment.status}`
      );
    }

    try {
      // Validate experiment configuration
      await this.validateExperiment(experiment);

      // Initialize traffic allocation
      this.trafficAllocator.initializeExperiment(experiment);

      // Update status
      experiment.status = ExperimentStatus.RUNNING;
      experiment.results.startTime = new Date();
      experiment.metadata.updatedAt = new Date();

      this.performanceStats.activeExperiments++;

      this.logger.info('Experiment started', {
        experimentId,
        variantCount: experiment.variants.length,
        targetMetric: experiment.metadata.targetMetric,
      });

      // Emit event
      this.emit('experiment:started', { experiment });
    } catch (error) {
      experiment.status = ExperimentStatus.FAILED;
      this.logger.error('Failed to start experiment', {
        experimentId,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Evaluate a prompt variant and record results
   */
  async evaluatePrompt(
    experimentId: string,
    input: any,
    context: Record<string, any> = {}
  ): Promise<{
    variantId: string;
    result: EvaluationResult;
    recommendation?: 'promote' | 'continue' | 'stop';
  }> {
    const experiment = this.activeExperiments.get(experimentId);
    if (!experiment || experiment.status !== ExperimentStatus.RUNNING) {
      throw new Error(`Experiment not available: ${experimentId}`);
    }

    const startTime = Date.now();

    try {
      // Select variant using traffic allocation
      const selectedVariant = this.trafficAllocator.selectVariant(
        experiment,
        context
      );

      // Generate response using selected variant
      const response = await this.executePrompt(
        selectedVariant,
        input,
        context
      );

      // Evaluate response using scorecards
      const evaluation = await this.scorecard.evaluate(response, {
        scorecardIds: experiment.config.evaluation.scorecardIds,
        context: {
          ...context,
          experimentId,
          variantId: selectedVariant.id,
          prompt: selectedVariant.prompt,
        },
      });

      const processingTime = Date.now() - startTime;

      // Record results
      await this.recordEvaluationResult(
        experiment,
        selectedVariant.id,
        evaluation,
        processingTime
      );

      // Check for statistical significance and early stopping
      const recommendation = await this.checkExperimentStatus(experiment);

      // Emit evaluation event
      this.emit('evaluation:completed', {
        experimentId,
        variantId: selectedVariant.id,
        evaluation,
        recommendation,
      });

      return {
        variantId: selectedVariant.id,
        result: evaluation,
        recommendation,
      };
    } catch (error) {
      this.logger.error('Prompt evaluation failed', {
        experimentId,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Stop an experiment and analyze results
   */
  async stopExperiment(
    experimentId: string,
    reason: string = 'manual'
  ): Promise<ExperimentResults> {
    const experiment = this.activeExperiments.get(experimentId);
    if (!experiment) {
      throw new Error(`Experiment not found: ${experimentId}`);
    }

    try {
      // Perform final statistical analysis
      const finalAnalysis = await this.performFinalAnalysis(experiment);

      // Update experiment status
      experiment.status = ExperimentStatus.COMPLETED;
      experiment.results.endTime = new Date();
      experiment.results.statisticalResults = finalAnalysis;
      experiment.metadata.updatedAt = new Date();

      // Move to history
      this.experimentHistory.set(experimentId, experiment);
      this.activeExperiments.delete(experimentId);

      // Update stats
      this.performanceStats.activeExperiments--;
      this.performanceStats.completedExperiments++;

      if (finalAnalysis.recommendation === 'promote') {
        this.performanceStats.promotedVariants++;

        // Auto-promote winning variant if configured
        if (finalAnalysis.winner) {
          await this.promoteVariant(experimentId, finalAnalysis.winner);
        }
      }

      this.logger.info('Experiment completed', {
        experimentId,
        reason,
        duration:
          experiment.results.endTime.getTime() -
          experiment.results.startTime.getTime(),
        winner: finalAnalysis.winner,
        recommendation: finalAnalysis.recommendation,
      });

      // Emit completion event
      this.emit('experiment:completed', {
        experiment,
        results: experiment.results,
        reason,
      });

      return experiment.results;
    } catch (error) {
      experiment.status = ExperimentStatus.FAILED;
      this.logger.error('Failed to stop experiment', {
        experimentId,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Get experiment results and statistics
   */
  getExperimentResults(experimentId: string): ExperimentResults | null {
    const experiment =
      this.activeExperiments.get(experimentId) ||
      this.experimentHistory.get(experimentId);
    return experiment ? experiment.results : null;
  }

  /**
   * Get all active experiments
   */
  getActiveExperiments(): PromptExperiment[] {
    return Array.from(this.activeExperiments.values());
  }

  /**
   * Get experiment history
   */
  getExperimentHistory(limit: number = 50): PromptExperiment[] {
    return Array.from(this.experimentHistory.values())
      .sort(
        (a, b) =>
          b.metadata.updatedAt.getTime() - a.metadata.updatedAt.getTime()
      )
      .slice(0, limit);
  }

  /**
   * Get performance statistics
   */
  getPerformanceStats(): typeof this.performanceStats & {
    averageSuccessRate: number;
    experimentsPerDay: number;
  } {
    const totalExperiments = this.performanceStats.totalExperiments;
    const successRate =
      totalExperiments > 0
        ? this.performanceStats.promotedVariants / totalExperiments
        : 0;

    // Calculate experiments per day (last 30 days)
    const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
    const recentExperiments = Array.from(
      this.experimentHistory.values()
    ).filter(exp => exp.metadata.createdAt >= thirtyDaysAgo);
    const experimentsPerDay = recentExperiments.length / 30;

    return {
      ...this.performanceStats,
      averageSuccessRate: successRate,
      experimentsPerDay,
    };
  }

  // Private methods

  private async generateVariantByStrategy(
    basePrompt: string,
    strategy: VariantGenerationStrategy,
    index: number
  ): Promise<Omit<PromptVariant, 'id'>> {
    const variant: Omit<PromptVariant, 'id'> = {
      name: `Variant ${index + 1} (${strategy})`,
      prompt: basePrompt,
      parameters: {
        temperature: 0.7,
        maxTokens: 1000,
        topP: 1.0,
        frequencyPenalty: 0.0,
        presencePenalty: 0.0,
      },
      trafficAllocation: 0, // Will be set by caller
      isControl: false,
      metadata: {
        generationMethod: 'automated',
        inspiration: `Generated using ${strategy} strategy`,
      },
    };

    switch (strategy) {
      case 'temperature':
        variant.parameters.temperature = 0.3 + index * 0.3; // 0.3, 0.6, 0.9
        variant.metadata.expectedImprovement =
          'Varied creativity and randomness';
        break;

      case 'rephrase':
        variant.prompt = await this.rephrasePrompt(basePrompt, index);
        variant.metadata.expectedImprovement =
          'Improved clarity and specificity';
        break;

      case 'structure':
        variant.prompt = await this.restructurePrompt(basePrompt, index);
        variant.metadata.expectedImprovement = 'Better organization and flow';
        break;

      case 'examples':
        variant.prompt = await this.addExamples(basePrompt, index);
        variant.metadata.expectedImprovement =
          'Enhanced understanding through examples';
        break;

      case 'constraints':
        variant.prompt = await this.addConstraints(basePrompt, index);
        variant.metadata.expectedImprovement =
          'More focused and controlled output';
        break;
    }

    return variant;
  }

  private async rephrasePrompt(
    basePrompt: string,
    index: number
  ): Promise<string> {
    // Simple rephrasing strategies
    const strategies = [
      (prompt: string) =>
        `Please ${prompt.replace(/^[A-Z]/, c => c.toLowerCase())}`,
      (prompt: string) =>
        `I need you to ${prompt.replace(/^[A-Z]/, c => c.toLowerCase())}`,
      (prompt: string) =>
        `Your task is to ${prompt.replace(/^[A-Z]/, c => c.toLowerCase())}`,
    ];

    return strategies[index % strategies.length](basePrompt);
  }

  private async restructurePrompt(
    basePrompt: string,
    index: number
  ): Promise<string> {
    // Simple restructuring strategies
    const structures = [
      (prompt: string) =>
        `Task: ${prompt}\n\nRequirements:\n- Be clear and concise\n- Provide accurate information`,
      (prompt: string) =>
        `Context: You are an expert assistant.\n\nInstruction: ${prompt}\n\nFormat: Provide a well-structured response.`,
      (prompt: string) =>
        `Objective: ${prompt}\n\nApproach:\n1. Analyze the request\n2. Provide comprehensive response\n3. Ensure quality and accuracy`,
    ];

    return structures[index % structures.length](basePrompt);
  }

  private async addExamples(
    basePrompt: string,
    index: number
  ): Promise<string> {
    // Add example-based enhancement
    const examples = [
      '\n\nFor example, if asked about weather, provide current conditions and forecast.',
      '\n\nExample: When explaining concepts, use analogies and real-world applications.',
      '\n\nSample approach: Break complex topics into digestible steps with clear explanations.',
    ];

    return basePrompt + examples[index % examples.length];
  }

  private async addConstraints(
    basePrompt: string,
    index: number
  ): Promise<string> {
    // Add constraint-based enhancement
    const constraints = [
      '\n\nConstraints: Keep response under 200 words and focus on key points.',
      '\n\nGuidelines: Use professional tone and cite sources when applicable.',
      '\n\nLimitations: Avoid speculation and stick to factual information.',
    ];

    return basePrompt + constraints[index % constraints.length];
  }

  private async executePrompt(
    variant: PromptVariant,
    input: any,
    context: Record<string, any>
  ): Promise<string> {
    // This would integrate with actual LLM providers
    // For now, simulate response generation
    const response = `Response to "${input}" using variant "${variant.name}" with prompt: "${variant.prompt.substring(0, 50)}..."`;

    // Simulate processing time based on parameters
    const delay = variant.parameters.temperature * 100 + Math.random() * 200;
    await new Promise(resolve => setTimeout(resolve, delay));

    return response;
  }

  private async recordEvaluationResult(
    experiment: PromptExperiment,
    variantId: string,
    evaluation: EvaluationResult,
    processingTime: number
  ): Promise<void> {
    // Update experiment results
    experiment.results.totalSamples++;

    const currentSamples =
      experiment.results.variantSamples.get(variantId) || 0;
    experiment.results.variantSamples.set(variantId, currentSamples + 1);

    // Update variant metrics
    let variantMetrics = experiment.results.variantMetrics.get(variantId);
    if (!variantMetrics) {
      variantMetrics = this.initializeVariantMetrics(variantId);
      experiment.results.variantMetrics.set(variantId, variantMetrics);
    }

    // Update metrics with new evaluation
    this.updateVariantMetrics(variantMetrics, evaluation, processingTime);

    // Track metrics
    metrics.counter('ape_evaluations_total', {
      experiment_id: experiment.id,
      variant_id: variantId,
      quality_tier:
        evaluation.overallScore >= 0.8
          ? 'high'
          : evaluation.overallScore >= 0.6
            ? 'medium'
            : 'low',
    });

    metrics.histogram(
      'ape_evaluation_score',
      evaluation.overallScore,
      undefined,
      {
        experiment_id: experiment.id,
        variant_id: variantId,
      }
    );
  }

  private async checkExperimentStatus(
    experiment: PromptExperiment
  ): Promise<'promote' | 'continue' | 'stop' | undefined> {
    // Check minimum sample requirements
    if (
      experiment.results.totalSamples < experiment.config.sampling.minSampleSize
    ) {
      return 'continue';
    }

    // Check duration limits
    const runningTime = Date.now() - experiment.results.startTime.getTime();
    const maxDuration =
      experiment.config.duration.maxDurationHours * 60 * 60 * 1000;

    if (runningTime >= maxDuration) {
      return 'stop';
    }

    // Perform statistical analysis
    const analysis =
      await this.statisticalAnalyzer.analyzeExperiment(experiment);

    // Early stopping based on statistical significance
    if (
      experiment.config.duration.earlyStoppingEnabled &&
      analysis.isSignificant &&
      runningTime >=
        experiment.config.duration.minDurationHours * 60 * 60 * 1000
    ) {
      return analysis.effectSize > 0 ? 'promote' : 'stop';
    }

    return 'continue';
  }

  private async performFinalAnalysis(
    experiment: PromptExperiment
  ): Promise<ExperimentResults['statisticalResults']> {
    return await this.statisticalAnalyzer.performFinalAnalysis(experiment);
  }

  private async promoteVariant(
    experimentId: string,
    variantId: string
  ): Promise<void> {
    this.logger.info('Promoting winning variant', { experimentId, variantId });

    // Emit promotion event
    this.emit('variant:promoted', { experimentId, variantId });

    // In a real system, this would update production configurations
  }

  private validateTrafficAllocation(variants: PromptVariant[]): void {
    const totalAllocation = variants.reduce(
      (sum, variant) => sum + variant.trafficAllocation,
      0
    );

    if (Math.abs(totalAllocation - 100) > 0.01) {
      throw new Error(
        `Traffic allocation must sum to 100%, got ${totalAllocation}%`
      );
    }
  }

  private async validateExperiment(
    experiment: PromptExperiment
  ): Promise<void> {
    if (experiment.variants.length < 2) {
      throw new Error('Experiment must have at least 2 variants');
    }

    const controlVariants = experiment.variants.filter(v => v.isControl);
    if (controlVariants.length !== 1) {
      throw new Error('Experiment must have exactly one control variant');
    }

    if (experiment.config.evaluation.scorecardIds.length === 0) {
      throw new Error(
        'Experiment must specify at least one scorecard for evaluation'
      );
    }
  }

  private startMonitoringTasks(): void {
    // Monitor active experiments
    setInterval(() => {
      this.monitorActiveExperiments();
    }, 60000); // Every minute

    // Clean up old experiments
    setInterval(() => {
      this.cleanupOldExperiments();
    }, 3600000); // Every hour
  }

  private async monitorActiveExperiments(): Promise<void> {
    for (const [experimentId, experiment] of this.activeExperiments) {
      try {
        const recommendation = await this.checkExperimentStatus(experiment);

        if (recommendation === 'stop' || recommendation === 'promote') {
          await this.stopExperiment(experimentId, `auto_${recommendation}`);
        }
      } catch (error) {
        this.logger.error('Error monitoring experiment', {
          experimentId,
          error: error.message,
        });
      }
    }
  }

  private cleanupOldExperiments(): void {
    const cutoffTime = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000); // 30 days

    for (const [experimentId, experiment] of this.experimentHistory) {
      if (experiment.metadata.updatedAt < cutoffTime) {
        this.experimentHistory.delete(experimentId);
      }
    }
  }

  private generateExperimentId(): string {
    return `exp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private mergeWithDefaultConfig(
    config: Partial<ExperimentConfig>
  ): ExperimentConfig {
    return {
      statistical: {
        confidenceLevel: 0.95,
        minimumDetectableEffect: 0.05,
        power: 0.8,
        alpha: 0.05,
        ...config.statistical,
      },
      sampling: {
        minSampleSize: 100,
        maxSampleSize: 10000,
        sampleRatio: [50, 50], // 50/50 split by default
        ...config.sampling,
      },
      duration: {
        maxDurationHours: 168, // 7 days
        minDurationHours: 24, // 1 day
        earlyStoppingEnabled: true,
        futilityStoppingEnabled: true,
        ...config.duration,
      },
      evaluation: {
        scorecardIds: [],
        evaluationFrequency: 'realtime',
        batchSize: 10,
        evaluationTimeout: 30000,
        ...config.evaluation,
      },
      safety: {
        maxErrorRate: 0.05,
        maxLatencyMs: 10000,
        contentFilters: [],
        rollbackThreshold: 0.1,
        ...config.safety,
      },
      ...config,
    };
  }

  private initializeResults(): ExperimentResults {
    return {
      status: 'running',
      startTime: new Date(),
      totalSamples: 0,
      variantSamples: new Map(),
      variantMetrics: new Map(),
      statisticalResults: {
        significanceTest: {
          testType: 'ttest',
          pValue: 1.0,
          isSignificant: false,
          effectSize: 0,
          confidenceInterval: [0, 0],
          testStatistic: 0,
        },
        effectSize: 0,
        confidence: 0,
        recommendation: 'continue',
      },
      qualityMetrics: {
        overallQuality: 0,
        errorRate: 0,
        averageLatency: 0,
        userSatisfaction: 0,
      },
    };
  }

  private initializeVariantMetrics(variantId: string): VariantMetrics {
    return {
      variantId,
      sampleSize: 0,
      performance: {
        successRate: 0,
        averageScore: 0,
        scoreDistribution: [],
        errorRate: 0,
        averageLatency: 0,
        throughput: 0,
      },
      quality: {
        averageQuality: 0,
        relevanceScore: 0,
        coherenceScore: 0,
        creativityScore: 0,
        accuracyScore: 0,
        safetyScore: 0,
      },
      business: {},
      statistics: {
        mean: 0,
        standardDeviation: 0,
        confidenceInterval: [0, 0],
        percentiles: new Map(),
      },
    };
  }

  private updateVariantMetrics(
    metrics: VariantMetrics,
    evaluation: EvaluationResult,
    processingTime: number
  ): void {
    const n = metrics.sampleSize;
    const newN = n + 1;

    // Update sample size
    metrics.sampleSize = newN;

    // Update running averages
    metrics.performance.averageScore =
      (metrics.performance.averageScore * n + evaluation.overallScore) / newN;
    metrics.performance.averageLatency =
      (metrics.performance.averageLatency * n + processingTime) / newN;
    metrics.performance.successRate =
      evaluation.overallScore >= 0.6
        ? (metrics.performance.successRate * n + 1) / newN
        : (metrics.performance.successRate * n) / newN;

    // Update quality metrics
    metrics.quality.averageQuality =
      (metrics.quality.averageQuality * n + evaluation.overallScore) / newN;

    // Update distribution
    metrics.performance.scoreDistribution.push(evaluation.overallScore);

    // Calculate statistics
    metrics.statistics.mean = metrics.performance.averageScore;
    if (newN > 1) {
      const variance =
        metrics.performance.scoreDistribution.reduce(
          (sum, score) => sum + Math.pow(score - metrics.statistics.mean, 2),
          0
        ) /
        (newN - 1);
      metrics.statistics.standardDeviation = Math.sqrt(variance);
    }
  }

  /**
   * Cleanup resources
   */
  cleanup(): void {
    this.activeExperiments.clear();
    this.experimentHistory.clear();
    this.removeAllListeners();
  }
}

// Supporting classes

class TrafficAllocator {
  initializeExperiment(experiment: PromptExperiment): void {
    // Validate and normalize traffic allocation
  }

  selectVariant(
    experiment: PromptExperiment,
    context: Record<string, any>
  ): PromptVariant {
    // Simple random selection based on traffic allocation
    const random = Math.random() * 100;
    let cumulative = 0;

    for (const variant of experiment.variants) {
      cumulative += variant.trafficAllocation;
      if (random <= cumulative) {
        return variant;
      }
    }

    return experiment.variants[0]; // Fallback
  }
}

class StatisticalAnalyzer {
  async analyzeExperiment(
    experiment: PromptExperiment
  ): Promise<SignificanceTestResult> {
    // Simplified statistical analysis
    const variants = Array.from(experiment.results.variantMetrics.values());
    if (variants.length < 2) {
      return {
        testType: 'ttest',
        pValue: 1.0,
        isSignificant: false,
        effectSize: 0,
        confidenceInterval: [0, 0],
        testStatistic: 0,
      };
    }

    // Simple t-test simulation
    const [control, treatment] = variants;
    const effectSize =
      treatment.performance.averageScore - control.performance.averageScore;
    const pooledStdDev = Math.sqrt(
      (control.statistics.standardDeviation ** 2 +
        treatment.statistics.standardDeviation ** 2) /
        2
    );

    const tStatistic =
      effectSize /
      (pooledStdDev *
        Math.sqrt(2 / Math.min(control.sampleSize, treatment.sampleSize)));
    const pValue = Math.abs(tStatistic) > 1.96 ? 0.04 : 0.06; // Simplified

    return {
      testType: 'ttest',
      pValue,
      isSignificant: pValue < 0.05,
      effectSize: Math.abs(effectSize),
      confidenceInterval: [
        effectSize - 1.96 * pooledStdDev,
        effectSize + 1.96 * pooledStdDev,
      ],
      testStatistic: tStatistic,
    };
  }

  async performFinalAnalysis(
    experiment: PromptExperiment
  ): Promise<ExperimentResults['statisticalResults']> {
    const significanceTest = await this.analyzeExperiment(experiment);

    // Determine winner and recommendation
    const variants = Array.from(
      experiment.results.variantMetrics.values()
    ).sort((a, b) => b.performance.averageScore - a.performance.averageScore);

    const winner = variants[0]?.variantId;
    const recommendation =
      significanceTest.isSignificant && significanceTest.effectSize > 0.05
        ? 'promote'
        : 'stop';

    return {
      significanceTest,
      effectSize: significanceTest.effectSize,
      confidence: 1 - significanceTest.pValue,
      recommendation,
      winner,
    };
  }
}

type VariantGenerationStrategy =
  | 'temperature'
  | 'rephrase'
  | 'structure'
  | 'examples'
  | 'constraints';

export { APEEngine };
