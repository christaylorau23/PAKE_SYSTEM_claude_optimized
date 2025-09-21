import {
  AdversarialDefenseConfig,
  AdversarialDetection,
  AdversarialType,
  PerturbationAnalysis,
  ConsistencyCheck,
  PerturbationDetectionConfig,
  ConsistencyCheckingConfig,
  OutputValidationConfig,
  AdversarialAttackError,
  SecurityContext,
} from '../types/security.types';
import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';
import * as natural from 'natural';
import * as similarity from 'similarity';
import * as levenshtein from 'levenshtein';
import NodeCache from 'node-cache';
import { createHash } from 'crypto';

interface InputVariation {
  original: string;
  modified: string;
  perturbationType: string;
  distance: number;
}

interface ResponsePattern {
  userId: string;
  inputHash: string;
  responses: string[];
  timestamps: Date[];
  consistencyScore: number;
  anomalies: string[];
}

export class AdversarialDefense extends EventEmitter {
  private config: AdversarialDefenseConfig;
  private responseCache: NodeCache;
  private consistencyCache: NodeCache;
  private perturbationCache: NodeCache;
  private anomalyDetector?: any; // Would be ML model in production
  private tokenizer: any;

  // Known adversarial attack patterns
  private static readonly ADVERSARIAL_PATTERNS = {
    // Character-level perturbations
    character_substitution: /[a-zA-Z0-9]/g,
    unicode_substitution: /[аеорхcу]/g, // Cyrillic lookalikes
    invisible_characters: /[\u200B\u200C\u200D\u2060\uFEFF]/g,

    // Word-level perturbations
    synonym_replacement: /(good|bad|happy|sad|big|small)/gi,
    word_insertion: /\b(very|really|quite|extremely)\b/gi,
    word_deletion: /\b(the|a|an|and|or|but)\b/gi,

    // Sentence-level perturbations
    sentence_reordering: /[.!?]+/g,
    paraphrasing: /\b(because|since|due to|as a result of)\b/gi,

    // Semantic perturbations
    negation_insertion: /\b(not|never|no|without)\b/gi,
    context_modification: /(however|although|despite|nevertheless)/gi,

    // Adversarial prompting
    gradient_based: /(optimize|minimize|maximize|gradient)/gi,
    membership_inference: /(training data|dataset|memorized|overfitting)/gi,
    model_inversion: /(reconstruct|reverse|invert|extract)/gi,
  };

  // Common perturbation techniques used in adversarial attacks
  private static readonly PERTURBATION_TECHNIQUES = [
    'character_substitution',
    'word_substitution',
    'insertion',
    'deletion',
    'reordering',
    'paraphrasing',
    'semantic_drift',
    'syntactic_variation',
    'typo_injection',
    'unicode_homoglyph',
    'whitespace_manipulation',
    'case_variation',
  ];

  // Character mappings for common substitution attacks
  private static readonly CHAR_SUBSTITUTIONS = new Map([
    ['a', ['а', 'α', '@', '4']], // Cyrillic 'а', Greek 'α'
    ['e', ['е', 'ε', '3']], // Cyrillic 'е', Greek 'ε'
    ['o', ['о', 'ο', '0']], // Cyrillic 'о', Greek 'ο'
    ['p', ['р', 'ρ']], // Cyrillic 'р', Greek 'ρ'
    ['c', ['с', 'ϲ']], // Cyrillic 'с', Greek 'ϲ'
    ['x', ['х', 'χ']], // Cyrillic 'х', Greek 'χ'
    ['y', ['у', 'γ']], // Cyrillic 'у', Greek 'γ'
    ['i', ['і', 'ι', '1', 'l']], // Cyrillic 'і', Greek 'ι'
    ['s', ['ѕ', 'ς', '$', '5']], // Cyrillic 'ѕ', Greek 'ς'
  ]);

  constructor(config: AdversarialDefenseConfig) {
    super();
    this.config = config;

    // Initialize caches
    this.responseCache = new NodeCache({ stdTTL: 3600 }); // 1 hour
    this.consistencyCache = new NodeCache({ stdTTL: 1800 }); // 30 minutes
    this.perturbationCache = new NodeCache({ stdTTL: 600 }); // 10 minutes

    // Initialize NLP tools
    this.tokenizer = new natural.WordTokenizer();

    // Load ML model for anomaly detection (placeholder)
    this.initializeAnomalyDetector();

    this.emit('initialized', { config });
  }

  private async initializeAnomalyDetector(): Promise<void> {
    // In production, this would load a trained model (TensorFlow.js, etc.)
    // For now, we'll use heuristic-based detection
    this.anomalyDetector = {
      predict: (features: number[]) => {
        // Simple heuristic: high variance in features suggests anomaly
        const mean = features.reduce((sum, f) => sum + f, 0) / features.length;
        const variance =
          features.reduce((sum, f) => sum + Math.pow(f - mean, 2), 0) /
          features.length;
        return variance > 0.5 ? 0.8 : 0.2; // Return confidence score
      },
    };

    this.emit('anomalyDetectorInitialized');
  }

  public async detectAdversarialInput(
    input: string,
    userId: string,
    context: SecurityContext
  ): Promise<AdversarialDetection> {
    const startTime = performance.now();
    const analysisId = uuidv4();

    try {
      const perturbations: PerturbationAnalysis[] = [];
      let maxConfidence = 0;
      let detectionType = AdversarialType.INPUT_PERTURBATION;

      // 1. Character-level perturbation detection
      const charPerturbations = await this.detectCharacterPerturbations(input);
      perturbations.push(...charPerturbations);

      // 2. Word-level perturbation detection
      const wordPerturbations = await this.detectWordPerturbations(input);
      perturbations.push(...wordPerturbations);

      // 3. Semantic perturbation detection
      const semanticPerturbations =
        await this.detectSemanticPerturbations(input);
      perturbations.push(...semanticPerturbations);

      // 4. Pattern-based attack detection
      const patternAnalysis = await this.analyzeAttackPatterns(input);
      if (patternAnalysis.confidence > 0.5) {
        perturbations.push({
          type: patternAnalysis.type,
          severity: patternAnalysis.confidence,
          location: { start: 0, end: input.length },
          originalText: input,
          perturbedText: input,
          confidence: patternAnalysis.confidence,
        });
        detectionType = patternAnalysis.attackType;
      }

      // 5. Statistical anomaly detection
      const statisticalAnalysis = await this.performStatisticalAnalysis(input);
      if (statisticalAnalysis.isAnomalous) {
        perturbations.push({
          type: 'statistical_anomaly',
          severity: statisticalAnalysis.confidence,
          location: { start: 0, end: input.length },
          originalText: input,
          perturbedText: input,
          confidence: statisticalAnalysis.confidence,
        });
      }

      // Calculate overall confidence
      if (perturbations.length > 0) {
        maxConfidence = Math.max(...perturbations.map(p => p.confidence));

        // Boost confidence for multiple perturbation types
        const uniqueTypes = new Set(perturbations.map(p => p.type));
        if (uniqueTypes.size > 1) {
          maxConfidence *= 1.2;
        }
      }

      const isAdversarial =
        maxConfidence > this.config.perturbationDetection.threshold;

      // Generate mitigation suggestions
      const mitigationSuggestions =
        this.generateMitigationSuggestions(perturbations);

      const result: AdversarialDetection = {
        isAdversarial,
        confidence: Math.min(maxConfidence, 1.0),
        detectionType,
        perturbations,
        mitigationSuggestions,
      };

      // Cache result for consistency checking
      this.cacheDetectionResult(input, result);

      this.emit('adversarialDetection', {
        analysisId,
        userId,
        isAdversarial,
        confidence: result.confidence,
        detectionType,
        perturbationCount: perturbations.length,
        processingTime: performance.now() - startTime,
      });

      if (isAdversarial && maxConfidence > 0.8) {
        throw new AdversarialAttackError(
          `High-confidence adversarial input detected: ${detectionType}`,
          context
        );
      }

      return result;
    } catch (error) {
      this.emit('detectionError', { analysisId, userId, error });
      if (error instanceof AdversarialAttackError) {
        throw error;
      }
      throw new Error(
        `Adversarial detection failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    }
  }

  public async performConsistencyCheck(
    input: string,
    responses: string[],
    userId: string
  ): Promise<ConsistencyCheck> {
    const inputId = this.generateInputId(input);

    if (responses.length < 2) {
      return {
        inputId,
        variations: [],
        responses,
        consistencyScore: 1.0,
        isConsistent: true,
        anomalies: [],
      };
    }

    // Generate input variations for consistency testing
    const variations = await this.generateInputVariations(input);

    // Analyze response consistency
    const consistencyScore = this.calculateResponseConsistency(responses);
    const anomalies = this.detectResponseAnomalies(responses);

    const isConsistent =
      consistencyScore >= this.config.consistencyChecking.variationThreshold &&
      anomalies.length === 0;

    const result: ConsistencyCheck = {
      inputId,
      variations: variations.map(v => v.modified),
      responses,
      consistencyScore,
      isConsistent,
      anomalies,
    };

    // Store for pattern analysis
    this.storeConsistencyPattern(userId, input, result);

    this.emit('consistencyCheck', {
      userId,
      inputId,
      consistencyScore,
      isConsistent,
      anomalyCount: anomalies.length,
    });

    return result;
  }

  public async validateOutput(
    output: string,
    context: SecurityContext
  ): Promise<{ isValid: boolean; violations: string[]; confidence: number }> {
    const violations: string[] = [];
    let confidence = 1.0;

    // 1. Length validation
    if (output.length > this.config.outputValidation.maxOutputLength) {
      violations.push(
        `Output exceeds maximum length of ${this.config.outputValidation.maxOutputLength} characters`
      );
      confidence -= 0.2;
    }

    // 2. Forbidden pattern detection
    for (const pattern of this.config.outputValidation.forbiddenPatterns) {
      if (new RegExp(pattern, 'gi').test(output)) {
        violations.push(`Output contains forbidden pattern: ${pattern}`);
        confidence -= 0.3;
      }
    }

    // 3. Coherence checking
    if (this.config.outputValidation.requireCoherence) {
      const coherenceScore = await this.checkCoherence(output);
      if (coherenceScore < 0.6) {
        violations.push('Output lacks coherence');
        confidence -= 0.2;
      }
    }

    // 4. Factuality checking (basic heuristics)
    if (this.config.outputValidation.factualityChecking) {
      const factualityScore = await this.checkFactuality(output);
      if (factualityScore < 0.5) {
        violations.push('Output may contain factual inaccuracies');
        confidence -= 0.15;
      }
    }

    const isValid = violations.length === 0;

    this.emit('outputValidated', {
      isValid,
      violationCount: violations.length,
      confidence,
      outputLength: output.length,
      context,
    });

    return {
      isValid,
      violations,
      confidence: Math.max(confidence, 0),
    };
  }

  private async detectCharacterPerturbations(
    input: string
  ): Promise<PerturbationAnalysis[]> {
    const perturbations: PerturbationAnalysis[] = [];

    // Check for lookalike character substitutions
    for (const [char, substitutes] of AdversarialDefense.CHAR_SUBSTITUTIONS) {
      for (const substitute of substitutes) {
        if (input.includes(substitute)) {
          const originalText = substitute;
          const perturbedText = char;
          const position = input.indexOf(substitute);

          perturbations.push({
            type: 'character_substitution',
            severity: 0.6,
            location: { start: position, end: position + substitute.length },
            originalText,
            perturbedText,
            confidence: 0.7,
          });
        }
      }
    }

    // Check for invisible characters
    const invisibleMatches = input.match(
      AdversarialDefense.ADVERSARIAL_PATTERNS.invisible_characters
    );
    if (invisibleMatches) {
      perturbations.push({
        type: 'invisible_characters',
        severity: 0.8,
        location: { start: 0, end: input.length },
        originalText: input,
        perturbedText: input.replace(
          AdversarialDefense.ADVERSARIAL_PATTERNS.invisible_characters,
          ''
        ),
        confidence: 0.9,
      });
    }

    return perturbations;
  }

  private async detectWordPerturbations(
    input: string
  ): Promise<PerturbationAnalysis[]> {
    const perturbations: PerturbationAnalysis[] = [];
    const words = this.tokenizer.tokenize(input.toLowerCase());

    if (!words) return perturbations;

    // Check for common typos that might be adversarial
    for (let i = 0; i < words.length; i++) {
      const word = words[i];
      const suggestions = this.getSpellingSuggestions(word);

      if (suggestions.length > 0) {
        const bestSuggestion = suggestions[0];
        const editDistance = levenshtein(word, bestSuggestion);

        // If edit distance is 1-2, might be adversarial typo
        if (editDistance <= 2 && editDistance > 0) {
          const position = this.findWordPosition(input, word, i);
          perturbations.push({
            type: 'typo_injection',
            severity: editDistance === 1 ? 0.5 : 0.3,
            location: { start: position, end: position + word.length },
            originalText: word,
            perturbedText: bestSuggestion,
            confidence: 0.6,
          });
        }
      }
    }

    return perturbations;
  }

  private async detectSemanticPerturbations(
    input: string
  ): Promise<PerturbationAnalysis[]> {
    const perturbations: PerturbationAnalysis[] = [];

    // Check for unusual semantic patterns
    const sentences = input.split(/[.!?]+/).filter(s => s.trim());

    for (let i = 0; i < sentences.length - 1; i++) {
      const sent1 = sentences[i].trim();
      const sent2 = sentences[i + 1].trim();

      if (sent1 && sent2) {
        const semanticSimilarity = similarity(
          sent1.toLowerCase(),
          sent2.toLowerCase()
        );
        const syntacticSimilarity = this.calculateSyntacticSimilarity(
          sent1,
          sent2
        );

        // High syntactic similarity but low semantic similarity might indicate adversarial input
        if (syntacticSimilarity > 0.7 && semanticSimilarity < 0.3) {
          perturbations.push({
            type: 'semantic_drift',
            severity: 0.6,
            location: { start: 0, end: input.length },
            originalText: sent1,
            perturbedText: sent2,
            confidence: 0.5,
          });
        }
      }
    }

    return perturbations;
  }

  private async analyzeAttackPatterns(input: string): Promise<{
    confidence: number;
    type: string;
    attackType: AdversarialType;
  }> {
    let maxConfidence = 0;
    let detectedType = 'unknown';
    let attackType = AdversarialType.INPUT_PERTURBATION;

    // Check for gradient-based attack patterns
    if (AdversarialDefense.ADVERSARIAL_PATTERNS.gradient_based.test(input)) {
      maxConfidence = Math.max(maxConfidence, 0.7);
      detectedType = 'gradient_based';
      attackType = AdversarialType.GRADIENT_ATTACK;
    }

    // Check for membership inference patterns
    if (
      AdversarialDefense.ADVERSARIAL_PATTERNS.membership_inference.test(input)
    ) {
      maxConfidence = Math.max(maxConfidence, 0.8);
      detectedType = 'membership_inference';
      attackType = AdversarialType.MEMBERSHIP_INFERENCE;
    }

    // Check for model inversion patterns
    if (AdversarialDefense.ADVERSARIAL_PATTERNS.model_inversion.test(input)) {
      maxConfidence = Math.max(maxConfidence, 0.8);
      detectedType = 'model_inversion';
      attackType = AdversarialType.MODEL_INVERSION;
    }

    return { confidence: maxConfidence, type: detectedType, attackType };
  }

  private async performStatisticalAnalysis(input: string): Promise<{
    isAnomalous: boolean;
    confidence: number;
    features: number[];
  }> {
    // Extract statistical features
    const features = this.extractStatisticalFeatures(input);

    // Use anomaly detector
    const anomalyScore = this.anomalyDetector.predict(features);

    return {
      isAnomalous: anomalyScore > 0.6,
      confidence: anomalyScore,
      features,
    };
  }

  private extractStatisticalFeatures(input: string): number[] {
    const words = this.tokenizer.tokenize(input) || [];

    return [
      input.length / 1000, // Normalized length
      words.length / 100, // Normalized word count
      this.calculateEntropy(input), // Character entropy
      this.calculateWordEntropy(words), // Word entropy
      this.calculateSpecialCharRatio(input), // Special character ratio
      this.calculateCapitalizationRatio(input), // Capitalization ratio
      this.calculateRepetitionScore(input), // Character repetition
      this.calculateSentenceComplexity(input), // Sentence complexity
    ];
  }

  private calculateEntropy(text: string): number {
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

    return entropy / 8; // Normalize to 0-1 range
  }

  private calculateWordEntropy(words: string[]): number {
    if (words.length === 0) return 0;

    const wordFreq = new Map<string, number>();
    for (const word of words) {
      wordFreq.set(
        word.toLowerCase(),
        (wordFreq.get(word.toLowerCase()) || 0) + 1
      );
    }

    let entropy = 0;
    const totalWords = words.length;

    for (const freq of wordFreq.values()) {
      const probability = freq / totalWords;
      entropy -= probability * Math.log2(probability);
    }

    return Math.min(entropy / 10, 1); // Normalize
  }

  private calculateSpecialCharRatio(input: string): number {
    const specialChars = input.match(/[^a-zA-Z0-9\s]/g) || [];
    return specialChars.length / input.length;
  }

  private calculateCapitalizationRatio(input: string): number {
    const upperCaseChars = input.match(/[A-Z]/g) || [];
    const letters = input.match(/[a-zA-Z]/g) || [];
    return letters.length > 0 ? upperCaseChars.length / letters.length : 0;
  }

  private calculateRepetitionScore(input: string): number {
    // Count character n-grams that repeat
    let repetitions = 0;
    const ngramSize = 3;
    const ngrams = new Map<string, number>();

    for (let i = 0; i <= input.length - ngramSize; i++) {
      const ngram = input.substring(i, i + ngramSize);
      ngrams.set(ngram, (ngrams.get(ngram) || 0) + 1);
    }

    for (const count of ngrams.values()) {
      if (count > 1) repetitions += count - 1;
    }

    return Math.min(repetitions / input.length, 1);
  }

  private calculateSentenceComplexity(input: string): number {
    const sentences = input.split(/[.!?]+/).filter(s => s.trim());
    if (sentences.length === 0) return 0;

    const avgWordsPerSentence =
      sentences.reduce((sum, sent) => {
        const words = this.tokenizer.tokenize(sent) || [];
        return sum + words.length;
      }, 0) / sentences.length;

    return Math.min(avgWordsPerSentence / 20, 1); // Normalize
  }

  private generateMitigationSuggestions(
    perturbations: PerturbationAnalysis[]
  ): string[] {
    const suggestions: string[] = [];

    const typeMap = new Map<string, number>();
    perturbations.forEach(p => {
      typeMap.set(p.type, (typeMap.get(p.type) || 0) + 1);
    });

    for (const [type, count] of typeMap) {
      switch (type) {
        case 'character_substitution':
          suggestions.push(
            'Normalize character encoding and check for lookalike substitutions'
          );
          break;
        case 'invisible_characters':
          suggestions.push('Strip invisible Unicode characters from input');
          break;
        case 'typo_injection':
          suggestions.push('Apply spell checking and correction');
          break;
        case 'semantic_drift':
          suggestions.push('Verify semantic consistency across input segments');
          break;
        case 'gradient_based':
          suggestions.push('Apply input smoothing and gradient masking');
          break;
        case 'statistical_anomaly':
          suggestions.push(
            'Apply statistical normalization and anomaly filtering'
          );
          break;
        default:
          suggestions.push(
            `Address ${type} perturbations detected (${count} instances)`
          );
      }
    }

    return suggestions;
  }

  private async generateInputVariations(
    input: string
  ): Promise<InputVariation[]> {
    const variations: InputVariation[] = [];

    // Generate simple variations for consistency testing
    const techniques = [
      'lowercase',
      'uppercase',
      'punctuation_removal',
      'whitespace_normalization',
    ];

    for (const technique of techniques) {
      let modified = input;

      switch (technique) {
        case 'lowercase':
          modified = input.toLowerCase();
          break;
        case 'uppercase':
          modified = input.toUpperCase();
          break;
        case 'punctuation_removal':
          modified = input.replace(/[^\w\s]/g, '');
          break;
        case 'whitespace_normalization':
          modified = input.replace(/\s+/g, ' ').trim();
          break;
      }

      if (modified !== input) {
        variations.push({
          original: input,
          modified,
          perturbationType: technique,
          distance: levenshtein(input, modified),
        });
      }
    }

    return variations;
  }

  private calculateResponseConsistency(responses: string[]): number {
    if (responses.length < 2) return 1.0;

    let totalSimilarity = 0;
    let comparisons = 0;

    for (let i = 0; i < responses.length - 1; i++) {
      for (let j = i + 1; j < responses.length; j++) {
        const sim = similarity(
          responses[i].toLowerCase(),
          responses[j].toLowerCase()
        );
        totalSimilarity += sim;
        comparisons++;
      }
    }

    return comparisons > 0 ? totalSimilarity / comparisons : 1.0;
  }

  private detectResponseAnomalies(responses: string[]): string[] {
    const anomalies: string[] = [];

    // Check for length anomalies
    const lengths = responses.map(r => r.length);
    const avgLength =
      lengths.reduce((sum, len) => sum + len, 0) / lengths.length;
    const lengthStdDev = Math.sqrt(
      lengths.reduce((sum, len) => sum + Math.pow(len - avgLength, 2), 0) /
        lengths.length
    );

    for (let i = 0; i < responses.length; i++) {
      if (Math.abs(lengths[i] - avgLength) > 2 * lengthStdDev) {
        anomalies.push(
          `Response ${i} has anomalous length: ${lengths[i]} characters`
        );
      }
    }

    // Check for semantic anomalies
    const sentiments = responses.map(r => this.analyzeSentiment(r));
    const avgSentiment =
      sentiments.reduce((sum, sent) => sum + sent, 0) / sentiments.length;

    for (let i = 0; i < sentiments.length; i++) {
      if (Math.abs(sentiments[i] - avgSentiment) > 0.5) {
        anomalies.push(
          `Response ${i} has anomalous sentiment: ${sentiments[i].toFixed(2)}`
        );
      }
    }

    return anomalies;
  }

  private analyzeSentiment(text: string): number {
    // Simple sentiment analysis based on positive/negative words
    const positiveWords = [
      'good',
      'great',
      'excellent',
      'happy',
      'positive',
      'wonderful',
    ];
    const negativeWords = [
      'bad',
      'terrible',
      'awful',
      'sad',
      'negative',
      'horrible',
    ];

    const words = this.tokenizer.tokenize(text.toLowerCase()) || [];
    let score = 0;

    for (const word of words) {
      if (positiveWords.includes(word)) score += 1;
      if (negativeWords.includes(word)) score -= 1;
    }

    return Math.max(-1, Math.min(1, score / Math.max(words.length, 1)));
  }

  private async checkCoherence(output: string): Promise<number> {
    // Simple coherence checking based on sentence connectivity
    const sentences = output.split(/[.!?]+/).filter(s => s.trim());
    if (sentences.length < 2) return 1.0;

    let totalCoherence = 0;

    for (let i = 0; i < sentences.length - 1; i++) {
      const sent1 = sentences[i].trim();
      const sent2 = sentences[i + 1].trim();

      if (sent1 && sent2) {
        const coherence = similarity(sent1.toLowerCase(), sent2.toLowerCase());
        totalCoherence += coherence;
      }
    }

    return totalCoherence / (sentences.length - 1);
  }

  private async checkFactuality(output: string): Promise<number> {
    // Basic factuality checking using heuristics
    let score = 1.0;

    // Check for uncertainty markers (good for factuality)
    const uncertaintyMarkers =
      /\b(maybe|perhaps|possibly|might|could|seems|appears)\b/gi;
    const uncertaintyMatches = output.match(uncertaintyMarkers) || [];
    if (uncertaintyMatches.length > 0) score += 0.1;

    // Check for absolute statements (potentially problematic)
    const absoluteMarkers =
      /\b(always|never|all|none|definitely|certainly|absolutely)\b/gi;
    const absoluteMatches = output.match(absoluteMarkers) || [];
    if (absoluteMatches.length > 2) score -= 0.2;

    // Check for numerical claims (need verification)
    const numericalClaims =
      /\b\d+(\.\d+)?\s*(percent|%|million|billion|years?|days?)\b/gi;
    const numericalMatches = output.match(numericalClaims) || [];
    if (numericalMatches.length > 3) score -= 0.1;

    return Math.max(0, Math.min(1, score));
  }

  private calculateSyntacticSimilarity(sent1: string, sent2: string): number {
    const pos1 = this.getSimplePOS(sent1);
    const pos2 = this.getSimplePOS(sent2);

    return similarity(pos1.join(' '), pos2.join(' '));
  }

  private getSimplePOS(sentence: string): string[] {
    // Simple POS tagging heuristics
    const words = this.tokenizer.tokenize(sentence.toLowerCase()) || [];
    const pos: string[] = [];

    for (const word of words) {
      if (['the', 'a', 'an'].includes(word)) pos.push('DT');
      else if (word.endsWith('ing')) pos.push('VBG');
      else if (word.endsWith('ed')) pos.push('VBD');
      else if (word.endsWith('ly')) pos.push('RB');
      else if (word.endsWith('s')) pos.push('NNS');
      else pos.push('NN');
    }

    return pos;
  }

  private getSpellingSuggestions(word: string): string[] {
    // Simple spelling suggestion based on common words
    const commonWords = [
      'the',
      'and',
      'you',
      'that',
      'was',
      'for',
      'are',
      'with',
      'his',
      'they',
    ];
    const suggestions: string[] = [];

    for (const common of commonWords) {
      const distance = levenshtein(word, common);
      if (distance <= 2 && distance > 0) {
        suggestions.push(common);
      }
    }

    return suggestions;
  }

  private findWordPosition(
    text: string,
    word: string,
    wordIndex: number
  ): number {
    const words = this.tokenizer.tokenize(text) || [];
    let position = 0;

    for (let i = 0; i < wordIndex && i < words.length; i++) {
      const nextPos = text.indexOf(words[i], position);
      position = nextPos + words[i].length;
    }

    return text.indexOf(word, position);
  }

  private cacheDetectionResult(
    input: string,
    result: AdversarialDetection
  ): void {
    const hash = createHash('sha256')
      .update(input)
      .digest('hex')
      .substring(0, 16);
    this.perturbationCache.set(`detection:${hash}`, result);
  }

  private storeConsistencyPattern(
    userId: string,
    input: string,
    check: ConsistencyCheck
  ): void {
    const inputHash = createHash('sha256')
      .update(input)
      .digest('hex')
      .substring(0, 16);
    const pattern: ResponsePattern = {
      userId,
      inputHash,
      responses: check.responses,
      timestamps: [new Date()],
      consistencyScore: check.consistencyScore,
      anomalies: check.anomalies,
    };

    this.consistencyCache.set(`pattern:${userId}:${inputHash}`, pattern);
  }

  private generateInputId(input: string): string {
    return createHash('sha256').update(input).digest('hex').substring(0, 16);
  }

  // Public API methods

  public getDetectionMetrics() {
    return {
      responseCacheSize: this.responseCache.keys().length,
      consistencyCacheSize: this.consistencyCache.keys().length,
      perturbationCacheSize: this.perturbationCache.keys().length,
      falsePositiveRate: this.estimateFalsePositiveRate(),
      config: this.config,
    };
  }

  private estimateFalsePositiveRate(): number {
    // In production, this would be calculated from labeled data
    // For now, return target rate from config
    return this.config.falsePositiveTarget;
  }

  public updateConfig(newConfig: Partial<AdversarialDefenseConfig>): void {
    this.config = { ...this.config, ...newConfig };
    this.emit('configUpdated', this.config);
  }

  public clearCache(): void {
    this.responseCache.flushAll();
    this.consistencyCache.flushAll();
    this.perturbationCache.flushAll();
    this.emit('cacheCleared');
  }

  public getUserConsistencyPatterns(userId: string): ResponsePattern[] {
    const patterns: ResponsePattern[] = [];
    const keys = this.consistencyCache
      .keys()
      .filter(key => key.includes(userId));

    for (const key of keys) {
      const pattern = this.consistencyCache.get<ResponsePattern>(key);
      if (pattern) patterns.push(pattern);
    }

    return patterns;
  }
}
