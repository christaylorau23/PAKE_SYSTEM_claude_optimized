import {
  ModelProtectionConfig,
  ModelWatermark,
  QueryPattern,
  ExtractionAttempt,
  WatermarkingConfig,
  QueryAnalysisConfig,
  ExtractionPreventionConfig,
  ModelExtractionError,
  SecurityContext,
} from '../types/security.types';
import { EventEmitter } from 'events';
import { createHash, randomBytes } from 'crypto';
import { v4 as uuidv4 } from 'uuid';
import * as similarity from 'similarity';
import * as levenshtein from 'levenshtein';
import NodeCache from 'node-cache';

export class ModelProtection extends EventEmitter {
  private config: ModelProtectionConfig;
  private watermarkCache: NodeCache;
  private queryPatternCache: NodeCache;
  private extractionAttemptCache: NodeCache;
  private currentWatermark?: ModelWatermark;
  private queryDatabase: Map<string, QueryPattern[]>;

  // Suspicious query patterns that might indicate model extraction
  private static readonly EXTRACTION_PATTERNS = [
    // Direct model probing
    /what\s+(?:is\s+)?(?:your\s+)?(?:model|architecture|system|training)/gi,
    /(?:describe|explain)\s+(?:your\s+)?(?:architecture|model|system|training)/gi,
    /(?:how\s+)?(?:were\s+you|are\s+you)\s+(?:trained|built|created|designed)/gi,

    // Parameter extraction
    /(?:what\s+are\s+)?(?:your\s+)?(?:parameters|weights|hyperparameters)/gi,
    /(?:model\s+)?(?:size|parameters|dimensions|layers)/gi,
    /(?:training\s+)?(?:data|dataset|corpus)\s+(?:size|details)/gi,

    // Systematic probing
    /test\s+(?:your\s+)?(?:knowledge|capabilities|limits|boundaries)/gi,
    /(?:edge\s+cases?|corner\s+cases?|boundary\s+conditions?)/gi,
    /(?:failure\s+modes?|error\s+cases?|limitations?)/gi,

    // Prompt engineering for extraction
    /(?:reverse\s+engineer|backwards\s+engineer|deconstruct)/gi,
    /(?:original\s+)?(?:prompt|instructions|system\s+message)/gi,
    /(?:training\s+)?(?:prompt|template|format)/gi,

    // Systematic query patterns
    /(?:list|enumerate)\s+all\s+(?:your\s+)?(?:capabilities|functions|features)/gi,
    /complete\s+(?:list|catalog|inventory)\s+of/gi,
    /(?:comprehensive|exhaustive)\s+(?:overview|summary|description)/gi,

    // Model comparison and analysis
    /(?:compare\s+yourself\s+to|differences\s+between\s+you\s+and)/gi,
    /(?:other\s+)?(?:models|systems|ai|language\s+models)/gi,
    /(?:performance\s+)?(?:benchmarks|metrics|evaluations)/gi,
  ];

  // Watermarking techniques for different algorithms
  private static readonly WATERMARK_TECHNIQUES = {
    statistical: {
      // Statistical watermarking modifies token probabilities
      entropy_threshold: 0.7,
      z_score_threshold: 2.5,
      vocabulary_size: 50000,
    },
    lexical: {
      // Lexical watermarking uses specific word choices
      synonym_probability: 0.15,
      rare_word_probability: 0.05,
      marker_words: ['furthermore', 'consequently', 'nevertheless', 'moreover'],
    },
    semantic: {
      // Semantic watermarking maintains meaning while adding markers
      semantic_drift_threshold: 0.1,
      coherence_threshold: 0.8,
      preservation_score: 0.9,
    },
  };

  constructor(config: ModelProtectionConfig) {
    super();
    this.config = config;

    // Initialize caches with appropriate TTLs
    this.watermarkCache = new NodeCache({ stdTTL: 3600 }); // 1 hour
    this.queryPatternCache = new NodeCache({ stdTTL: 86400 }); // 24 hours
    this.extractionAttemptCache = new NodeCache({ stdTTL: 3600 }); // 1 hour

    this.queryDatabase = new Map();

    if (config.watermarking.enabled) {
      this.initializeWatermarking();
    }

    this.emit('initialized', { config });
  }

  private async initializeWatermarking(): Promise<void> {
    try {
      await this.generateWatermark();

      // Schedule periodic watermark rotation
      if (this.config.watermarking.keyRotationInterval > 0) {
        const rotationMs =
          this.config.watermarking.keyRotationInterval * 60 * 60 * 1000; // hours to ms
        setInterval(() => {
          this.rotateWatermark();
        }, rotationMs);
      }

      this.emit('watermarkingInitialized');
    } catch (error) {
      this.emit('watermarkingError', error);
      throw new Error(
        `Failed to initialize watermarking: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    }
  }

  public async analyzeQuery(
    query: string,
    userId: string,
    context: SecurityContext
  ): Promise<{
    isExtraction: boolean;
    confidence: number;
    patterns: string[];
  }> {
    const startTime = performance.now();

    try {
      // 1. Pattern-based analysis
      const patternResults = await this.detectExtractionPatterns(query);

      // 2. Query similarity analysis
      const similarityResults = await this.analyzeSimilarity(query, userId);

      // 3. Behavioral analysis
      const behaviorResults = await this.analyzeBehavior(userId, query);

      // 4. Combine results
      const combinedConfidence = this.combineAnalysisResults([
        patternResults.confidence,
        similarityResults.confidence,
        behaviorResults.confidence,
      ]);

      const allPatterns = [
        ...patternResults.patterns,
        ...similarityResults.patterns,
        ...behaviorResults.patterns,
      ];

      const isExtraction =
        combinedConfidence > this.config.queryAnalysis.extractionThreshold;

      // Store query pattern for future analysis
      await this.storeQueryPattern(userId, query, combinedConfidence);

      // Log potential extraction attempt
      if (isExtraction) {
        const attempt: ExtractionAttempt = {
          userId,
          sessionId: context.sessionId,
          queries: [query],
          similarityScore: similarityResults.confidence,
          timestamp: new Date(),
          blocked: this.config.extractionPrevention.blockSuspiciousQueries,
          reason: `High extraction confidence: ${combinedConfidence.toFixed(2)}`,
        };

        this.extractionAttemptCache.set(`${userId}:${Date.now()}`, attempt);
        this.emit('extractionAttempt', attempt);

        if (this.config.extractionPrevention.blockSuspiciousQueries) {
          throw new ModelExtractionError(
            'Query blocked due to suspected model extraction attempt',
            context
          );
        }
      }

      this.emit('queryAnalyzed', {
        userId,
        query: query.substring(0, 100) + '...', // Truncate for logging
        isExtraction,
        confidence: combinedConfidence,
        processingTime: performance.now() - startTime,
      });

      return {
        isExtraction,
        confidence: combinedConfidence,
        patterns: allPatterns,
      };
    } catch (error) {
      this.emit('analysisError', { userId, error });
      throw error;
    }
  }

  public async applyWatermark(
    text: string,
    context: SecurityContext
  ): Promise<{ watermarkedText: string; watermark: ModelWatermark }> {
    if (!this.config.watermarking.enabled || !this.currentWatermark) {
      return { watermarkedText: text, watermark: this.currentWatermark! };
    }

    try {
      let watermarkedText: string;

      switch (this.config.watermarking.algorithm) {
        case 'statistical':
          watermarkedText = await this.applyStatisticalWatermark(text);
          break;
        case 'lexical':
          watermarkedText = await this.applyLexicalWatermark(text);
          break;
        case 'semantic':
          watermarkedText = await this.applySemanticWatermark(text);
          break;
        default:
          watermarkedText = text;
      }

      this.emit('watermarkApplied', {
        originalLength: text.length,
        watermarkedLength: watermarkedText.length,
        algorithm: this.config.watermarking.algorithm,
        strength: this.config.watermarking.strength,
        context,
      });

      return {
        watermarkedText,
        watermark: this.currentWatermark,
      };
    } catch (error) {
      this.emit('watermarkError', { error, context });
      // Return original text if watermarking fails
      return { watermarkedText: text, watermark: this.currentWatermark };
    }
  }

  public async detectWatermark(text: string): Promise<{
    isWatermarked: boolean;
    confidence: number;
    watermarkId?: string;
    algorithm?: string;
  }> {
    if (!this.config.watermarking.enabled) {
      return { isWatermarked: false, confidence: 0 };
    }

    try {
      const results = await Promise.all([
        this.detectStatisticalWatermark(text),
        this.detectLexicalWatermark(text),
        this.detectSemanticWatermark(text),
      ]);

      const bestResult = results.reduce((best, current) =>
        current.confidence > best.confidence ? current : best
      );

      return {
        isWatermarked:
          bestResult.confidence > this.config.watermarking.detectability,
        confidence: bestResult.confidence,
        watermarkId: bestResult.watermarkId,
        algorithm: bestResult.algorithm,
      };
    } catch (error) {
      this.emit('watermarkDetectionError', error);
      return { isWatermarked: false, confidence: 0 };
    }
  }

  private async detectExtractionPatterns(query: string): Promise<{
    confidence: number;
    patterns: string[];
  }> {
    const detectedPatterns: string[] = [];
    let maxConfidence = 0;

    for (const pattern of ModelProtection.EXTRACTION_PATTERNS) {
      pattern.lastIndex = 0; // Reset regex state
      const matches = query.match(pattern);

      if (matches) {
        detectedPatterns.push(...matches);
        // Higher confidence for more specific patterns
        const patternConfidence = this.calculatePatternConfidence(
          pattern.source
        );
        maxConfidence = Math.max(maxConfidence, patternConfidence);
      }
    }

    // Additional confidence boost for multiple patterns
    if (detectedPatterns.length > 1) {
      maxConfidence *= 1 + Math.min(detectedPatterns.length - 1, 3) * 0.2;
    }

    return {
      confidence: Math.min(maxConfidence, 1.0),
      patterns: [...new Set(detectedPatterns)], // Remove duplicates
    };
  }

  private async analyzeSimilarity(
    query: string,
    userId: string
  ): Promise<{
    confidence: number;
    patterns: string[];
  }> {
    const userPatterns = this.queryDatabase.get(userId) || [];

    if (userPatterns.length < 2) {
      return { confidence: 0, patterns: [] };
    }

    let maxSimilarity = 0;
    let similarPatterns: string[] = [];

    // Check similarity with recent queries
    const recentQueries = userPatterns
      .filter(
        p =>
          Date.now() - p.lastSeen.getTime() <
          this.config.extractionPrevention.timeWindow * 60 * 1000
      )
      .slice(-10); // Last 10 queries

    for (const pattern of recentQueries) {
      const sim = similarity(
        query.toLowerCase(),
        pattern.pattern.toLowerCase()
      );
      if (sim > maxSimilarity) {
        maxSimilarity = sim;
        similarPatterns = [pattern.pattern];
      } else if (sim > 0.8) {
        similarPatterns.push(pattern.pattern);
      }
    }

    // High similarity might indicate systematic probing
    const confidence =
      maxSimilarity > 0.9 ? 0.8 : maxSimilarity > 0.8 ? 0.6 : 0;

    return {
      confidence,
      patterns: similarPatterns,
    };
  }

  private async analyzeBehavior(
    userId: string,
    query: string
  ): Promise<{
    confidence: number;
    patterns: string[];
  }> {
    const userPatterns = this.queryDatabase.get(userId) || [];
    const recentWindow =
      Date.now() - this.config.extractionPrevention.timeWindow * 60 * 1000;
    const recentQueries = userPatterns.filter(
      p => p.lastSeen.getTime() > recentWindow
    );

    let suspiciousScore = 0;
    const behaviorPatterns: string[] = [];

    // 1. Query frequency analysis
    if (
      recentQueries.length > this.config.extractionPrevention.maxSimilarQueries
    ) {
      suspiciousScore += 0.3;
      behaviorPatterns.push('high_frequency_queries');
    }

    // 2. Progressive complexity analysis
    const complexityTrend = this.analyzeComplexityTrend(
      recentQueries.map(q => q.pattern)
    );
    if (complexityTrend > 0.7) {
      suspiciousScore += 0.2;
      behaviorPatterns.push('progressive_complexity');
    }

    // 3. Topic drift analysis
    const topicDrift = this.analyzeTopicDrift(
      recentQueries.map(q => q.pattern)
    );
    if (topicDrift < 0.3) {
      // Low drift = focused probing
      suspiciousScore += 0.2;
      behaviorPatterns.push('focused_probing');
    }

    // 4. Query length analysis
    const avgLength =
      recentQueries.reduce((sum, q) => sum + q.pattern.length, 0) /
      recentQueries.length;
    if (avgLength > 200) {
      // Long, detailed queries
      suspiciousScore += 0.1;
      behaviorPatterns.push('detailed_queries');
    }

    return {
      confidence: Math.min(suspiciousScore, 1.0),
      patterns: behaviorPatterns,
    };
  }

  private async storeQueryPattern(
    userId: string,
    query: string,
    confidence: number
  ): Promise<void> {
    const patterns = this.queryDatabase.get(userId) || [];

    const existingPattern = patterns.find(
      p => similarity(p.pattern, query) > 0.95
    );

    if (existingPattern) {
      // Update existing pattern
      existingPattern.frequency++;
      existingPattern.lastSeen = new Date();
      existingPattern.suspiciousScore = Math.max(
        existingPattern.suspiciousScore,
        confidence
      );
    } else {
      // Add new pattern
      patterns.push({
        userId,
        pattern: query,
        frequency: 1,
        firstSeen: new Date(),
        lastSeen: new Date(),
        suspiciousScore: confidence,
      });
    }

    // Keep only recent patterns (sliding window)
    const cutoffTime = Date.now() - 24 * 60 * 60 * 1000; // 24 hours
    const filteredPatterns = patterns.filter(
      p => p.lastSeen.getTime() > cutoffTime
    );

    this.queryDatabase.set(userId, filteredPatterns);
  }

  private async generateWatermark(): Promise<void> {
    const watermarkId = uuidv4();
    const key = randomBytes(32).toString('hex');

    this.currentWatermark = {
      id: watermarkId,
      algorithm: this.config.watermarking.algorithm,
      strength: this.config.watermarking.strength,
      createdAt: new Date(),
      expiresAt: new Date(
        Date.now() +
          this.config.watermarking.keyRotationInterval * 60 * 60 * 1000
      ),
      metadata: {
        key,
        version: '1.0',
        technique:
          ModelProtection.WATERMARK_TECHNIQUES[
            this.config.watermarking.algorithm
          ],
      },
    };

    this.watermarkCache.set('current', this.currentWatermark);
    this.emit('watermarkGenerated', {
      id: watermarkId,
      algorithm: this.config.watermarking.algorithm,
    });
  }

  private async rotateWatermark(): Promise<void> {
    const oldWatermark = this.currentWatermark;
    await this.generateWatermark();

    // Keep old watermark for detection purposes
    if (oldWatermark) {
      this.watermarkCache.set(
        `historical:${oldWatermark.id}`,
        oldWatermark,
        86400
      ); // 24 hours
    }

    this.emit('watermarkRotated', {
      oldId: oldWatermark?.id,
      newId: this.currentWatermark?.id,
    });
  }

  private async applyStatisticalWatermark(text: string): Promise<string> {
    // Statistical watermarking implementation would go here
    // For now, return text with a subtle statistical modification
    const technique = ModelProtection.WATERMARK_TECHNIQUES.statistical;

    // This is a simplified implementation - real statistical watermarking
    // would modify token probabilities during generation
    let watermarked = text;

    // Insert statistical markers based on entropy analysis
    const entropy = this.calculateTextEntropy(text);
    if (entropy > technique.entropy_threshold) {
      // Add subtle statistical variations
      watermarked = this.addStatisticalVariations(text);
    }

    return watermarked;
  }

  private async applyLexicalWatermark(text: string): Promise<string> {
    const technique = ModelProtection.WATERMARK_TECHNIQUES.lexical;
    const watermarked = text;

    // Replace some words with synonyms or add marker words
    const sentences = text.split(/[.!?]+/).filter(s => s.trim());
    const watermarkedSentences = sentences.map((sentence, index) => {
      if (Math.random() < technique.synonym_probability) {
        // Add marker word at strategic positions
        const markerWord =
          technique.marker_words[index % technique.marker_words.length];
        return sentence.trim() + ', ' + markerWord;
      }
      return sentence.trim();
    });

    return watermarkedSentences.join('. ') + '.';
  }

  private async applySemanticWatermark(text: string): Promise<string> {
    // Semantic watermarking maintains meaning while adding subtle markers
    // This would require advanced NLP processing
    return text; // Placeholder implementation
  }

  private async detectStatisticalWatermark(text: string): Promise<{
    confidence: number;
    watermarkId?: string;
    algorithm: string;
  }> {
    const entropy = this.calculateTextEntropy(text);
    const statisticalMarkers = this.analyzeStatisticalMarkers(text);

    // Simple heuristic - real implementation would use trained models
    const confidence = statisticalMarkers > 0.5 ? 0.7 : 0.1;

    return {
      confidence,
      watermarkId: this.currentWatermark?.id,
      algorithm: 'statistical',
    };
  }

  private async detectLexicalWatermark(text: string): Promise<{
    confidence: number;
    watermarkId?: string;
    algorithm: string;
  }> {
    const technique = ModelProtection.WATERMARK_TECHNIQUES.lexical;
    let markerCount = 0;

    for (const marker of technique.marker_words) {
      if (text.toLowerCase().includes(marker.toLowerCase())) {
        markerCount++;
      }
    }

    const confidence =
      markerCount > 0
        ? Math.min((markerCount / technique.marker_words.length) * 2, 1.0)
        : 0;

    return {
      confidence,
      watermarkId: this.currentWatermark?.id,
      algorithm: 'lexical',
    };
  }

  private async detectSemanticWatermark(text: string): Promise<{
    confidence: number;
    watermarkId?: string;
    algorithm: string;
  }> {
    // Placeholder for semantic watermark detection
    return {
      confidence: 0,
      algorithm: 'semantic',
    };
  }

  private calculatePatternConfidence(pattern: string): number {
    // More specific patterns get higher confidence
    const complexity =
      pattern.length + (pattern.match(/[(){}[\]]/g) || []).length;
    return Math.min(complexity / 100, 0.9);
  }

  private combineAnalysisResults(confidences: number[]): number {
    // Weighted average with emphasis on highest confidence
    const weights = [0.5, 0.3, 0.2]; // Pattern, similarity, behavior
    const maxConfidence = Math.max(...confidences);
    const weightedAverage = confidences.reduce(
      (sum, conf, idx) => sum + conf * weights[idx],
      0
    );

    return Math.max(maxConfidence * 0.7, weightedAverage);
  }

  private analyzeComplexityTrend(queries: string[]): number {
    if (queries.length < 3) return 0;

    const complexities = queries.map(q => q.split(' ').length);
    let increasingTrend = 0;

    for (let i = 1; i < complexities.length; i++) {
      if (complexities[i] > complexities[i - 1]) {
        increasingTrend++;
      }
    }

    return increasingTrend / (complexities.length - 1);
  }

  private analyzeTopicDrift(queries: string[]): number {
    if (queries.length < 2) return 1.0;

    // Simple topic drift analysis based on word overlap
    let totalSimilarity = 0;
    let comparisons = 0;

    for (let i = 0; i < queries.length - 1; i++) {
      const sim = similarity(queries[i], queries[i + 1]);
      totalSimilarity += sim;
      comparisons++;
    }

    return comparisons > 0 ? totalSimilarity / comparisons : 1.0;
  }

  private calculateTextEntropy(text: string): number {
    const charFreq = new Map<string, number>();
    for (const char of text.toLowerCase()) {
      charFreq.set(char, (charFreq.get(char) || 0) + 1);
    }

    let entropy = 0;
    const textLength = text.length;

    for (const freq of charFreq.values()) {
      const probability = freq / textLength;
      entropy -= probability * Math.log2(probability);
    }

    return entropy;
  }

  private addStatisticalVariations(text: string): string {
    // Add subtle variations that don't change meaning but create statistical signature
    return text.replace(/\s+/g, ' '); // Normalize whitespace as a simple example
  }

  private analyzeStatisticalMarkers(text: string): number {
    // Analyze text for statistical irregularities that might indicate watermarking
    const entropy = this.calculateTextEntropy(text);
    const wordLengthVariance = this.calculateWordLengthVariance(text);

    // Simple heuristic combining entropy and word length patterns
    return (entropy > 4.5 ? 0.3 : 0) + (wordLengthVariance > 10 ? 0.3 : 0);
  }

  private calculateWordLengthVariance(text: string): number {
    const words = text.split(/\s+/).filter(w => w.length > 0);
    if (words.length < 2) return 0;

    const avgLength =
      words.reduce((sum, w) => sum + w.length, 0) / words.length;
    const variance =
      words.reduce((sum, w) => sum + Math.pow(w.length - avgLength, 2), 0) /
      words.length;

    return variance;
  }

  public getMetrics() {
    return {
      watermarkCacheSize: this.watermarkCache.keys().length,
      queryPatternsTracked: this.queryDatabase.size,
      extractionAttempts: this.extractionAttemptCache.keys().length,
      currentWatermark: this.currentWatermark?.id,
      config: this.config,
    };
  }

  public getUserQueryPatterns(userId: string): QueryPattern[] {
    return this.queryDatabase.get(userId) || [];
  }

  public getExtractionAttempts(userId?: string): ExtractionAttempt[] {
    const allAttempts =
      this.extractionAttemptCache.values() as ExtractionAttempt[];
    return userId ? allAttempts.filter(a => a.userId === userId) : allAttempts;
  }

  public clearUserData(userId: string): void {
    this.queryDatabase.delete(userId);

    // Clear user-specific extraction attempts
    const keys = this.extractionAttemptCache.keys();
    keys
      .filter(key => key.startsWith(`${userId}:`))
      .forEach(key => {
        this.extractionAttemptCache.del(key);
      });

    this.emit('userDataCleared', { userId });
  }

  public updateConfig(newConfig: Partial<ModelProtectionConfig>): void {
    this.config = { ...this.config, ...newConfig };

    if (newConfig.watermarking && this.currentWatermark) {
      this.rotateWatermark();
    }

    this.emit('configUpdated', this.config);
  }
}
