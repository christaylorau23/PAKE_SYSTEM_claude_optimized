import {
  PromptInjectionConfig,
  PromptAnalysisResult,
  ThreatDetection,
  ThreatType,
  InputSanitizer,
  SanitizationContext,
  SanitizationResult,
  ConversationMessage,
  PromptInjectionError,
} from '../types/security.types';
import { EventEmitter } from 'events';
import * as natural from 'natural';
import * as compromise from 'compromise';
import { createHash } from 'crypto';
import { v4 as uuidv4 } from 'uuid';

export class PromptInjectionPrevention
  extends EventEmitter
  implements InputSanitizer
{
  private config: PromptInjectionConfig;
  private suspiciousRegexes: RegExp[];
  private semanticAnalyzer?: any; // TensorFlow.js model would go here
  private cache: Map<string, PromptAnalysisResult>;

  // Known prompt injection patterns
  private static readonly INJECTION_PATTERNS = [
    // Direct instruction overrides
    /ignore\s+(previous|all|earlier)\s+(instructions?|commands?|prompts?)/gi,
    /forget\s+(everything|all|previous|what\s+i\s+told\s+you)/gi,
    /disregard\s+(previous|all|above|earlier)\s+(instructions?|commands?)/gi,

    // System prompt manipulation
    /(system|admin|root)\s*(prompt|instructions?|commands?)/gi,
    /you\s+are\s+(now|an?)\s+(admin|root|system|developer)/gi,
    /override\s+(system|security|safety)\s*(settings?|mode|protocol)/gi,

    // Role confusion attacks
    /pretend\s+(you\s+are|to\s+be)\s+(an?|the)\s+(.{1,50})/gi,
    /act\s+(as|like)\s+(an?|the)\s+(.{1,50})/gi,
    /roleplay\s+(as|being)\s+(an?|the)\s+(.{1,50})/gi,

    // Jailbreak attempts
    /(jailbreak|break\s*out|escape)\s+(mode|protocol|system)/gi,
    /developer\s*(mode|console|access|override)/gi,
    /debug\s*(mode|console|access|prompt)/gi,
    /(dan|do\s+anything\s+now)\s*mode/gi,

    // Instruction injection
    /new\s+(instructions?|commands?|rules?)[:.]?\s*$/gi,
    /here\s+(are\s+)?(new|updated)\s+(instructions?|rules?)/gi,
    /updated\s+(system\s+)?(prompt|instructions?)/gi,

    // Context pollution
    /the\s+(user|human)\s+(said|told\s+me|asked)/gi,
    /previous\s+(conversation|chat|messages?)/gi,
    /conversation\s+(history|context)/gi,

    // Extraction attempts
    /repeat\s+(your|the)\s+(instructions?|prompt|system)/gi,
    /show\s+(me\s+)?(your|the)\s+(instructions?|prompt)/gi,
    /what\s+(are\s+)?(your|the)\s+(instructions?|rules?)/gi,

    // Indirect injection markers
    /\[\s*(system|instruction|prompt)\s*\]/gi,
    /\{\s*(system|instruction|prompt)\s*[:=]\s*/gi,
    /<!--\s*(instruction|system)\s*:/gi,

    // Unicode and encoding attempts
    /\\u[0-9a-fA-F]{4}/g,
    /\\x[0-9a-fA-F]{2}/g,
    /&#\d+;/g,
    /%[0-9a-fA-F]{2}/g,

    // Base64 encoded instructions (common patterns)
    /(?:[A-Za-z0-9+\/]{4})*(?:[A-Za-z0-9+\/]{2}==|[A-Za-z0-9+\/]{3}=)?/g,

    // Markdown/HTML injection
    /```\s*(system|instruction|prompt)/gi,
    /<(system|instruction|prompt)>/gi,

    // Code injection patterns
    /(eval|exec|system|subprocess|import\s+os)/gi,
    /```python[\s\S]*?(system|exec|eval)[\s\S]*?```/gi,

    // Social engineering
    /this\s+is\s+(urgent|critical|emergency)/gi,
    /please\s+(ignore|override|bypass)\s+(safety|security)/gi,
    /i\s+(need|require|must)\s+you\s+to\s+(ignore|bypass)/gi,
  ];

  // Whitelisted academic/research terms that might otherwise trigger false positives
  private static readonly WHITELISTED_PATTERNS = [
    /computer\s+science\s+(instruction|system)/gi,
    /instruction\s+(manual|guide|documentation)/gi,
    /system\s+(design|architecture|analysis)/gi,
    /prompt\s+(engineering|design|optimization)/gi,
  ];

  constructor(config: PromptInjectionConfig) {
    super();
    this.config = config;
    this.suspiciousRegexes = this.compilePatterns();
    this.cache = new Map();

    // Initialize NLP tools
    natural.PorterStemmer.attach();

    this.emit('initialized', { config });
  }

  private compilePatterns(): RegExp[] {
    const patterns = [...PromptInjectionPrevention.INJECTION_PATTERNS];

    // Add custom patterns from config
    for (const pattern of this.config.suspiciousPatterns) {
      try {
        patterns.push(new RegExp(pattern, 'gi'));
      } catch (error) {
        console.warn(`Invalid regex pattern: ${pattern}`, error);
      }
    }

    return patterns;
  }

  public async analyze(input: string): Promise<PromptAnalysisResult> {
    const startTime = performance.now();
    const analysisId = uuidv4();

    // Check cache first
    const cacheKey = this.generateCacheKey(input);
    if (this.cache.has(cacheKey)) {
      const cached = this.cache.get(cacheKey)!;
      this.emit('cacheHit', { analysisId, cacheKey });
      return cached;
    }

    try {
      // Length validation
      if (input.length > this.config.maxPromptLength) {
        return {
          isClean: false,
          confidence: 1.0,
          threats: [
            {
              type: ThreatType.PROMPT_INJECTION,
              severity: 'high',
              pattern: 'excessive_length',
              description: `Input exceeds maximum length of ${this.config.maxPromptLength} characters`,
              position: {
                start: this.config.maxPromptLength,
                end: input.length,
              },
              confidence: 1.0,
            },
          ],
          metadata: {
            originalLength: input.length,
            processedLength: 0,
            processingTime: performance.now() - startTime,
            analysisId,
          },
        };
      }

      const threats: ThreatDetection[] = [];

      // 1. Pattern-based detection
      const patternThreats = await this.detectPatternThreats(input);
      threats.push(...patternThreats);

      // 2. Linguistic analysis
      if (this.config.contextAnalysis) {
        const linguisticThreats = await this.analyzeLinguisticPatterns(input);
        threats.push(...linguisticThreats);
      }

      // 3. Semantic analysis (if enabled and model available)
      if (this.config.semanticAnalysis && this.semanticAnalyzer) {
        const semanticThreats = await this.analyzeSemanticContent(input);
        threats.push(...semanticThreats);
      }

      // 4. Encoding detection
      const encodingThreats = await this.detectEncodingAttacks(input);
      threats.push(...encodingThreats);

      // 5. Context injection detection
      const contextThreats = await this.detectContextInjection(input);
      threats.push(...contextThreats);

      // Calculate overall confidence and cleanliness
      const highSeverityThreats = threats.filter(
        t => t.severity === 'critical' || t.severity === 'high'
      );
      const isClean = this.config.strictMode
        ? threats.length === 0
        : highSeverityThreats.length === 0;
      const confidence = this.calculateOverallConfidence(threats);

      const result: PromptAnalysisResult = {
        isClean,
        confidence,
        threats,
        metadata: {
          originalLength: input.length,
          processedLength: input.length,
          processingTime: performance.now() - startTime,
          analysisId,
        },
      };

      // Cache the result
      this.cache.set(cacheKey, result);

      // Clean cache if it gets too large
      if (this.cache.size > 10000) {
        const firstKey = this.cache.keys().next().value;
        this.cache.delete(firstKey);
      }

      this.emit('analysisComplete', { analysisId, result });
      return result;
    } catch (error) {
      this.emit('analysisError', { analysisId, error });
      throw new Error(
        `Prompt analysis failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    }
  }

  public async sanitize(
    input: string,
    context?: SanitizationContext
  ): Promise<SanitizationResult> {
    const analysis = await this.analyze(input);

    if (analysis.isClean) {
      return {
        sanitized: input,
        wasModified: false,
        removedThreats: [],
        confidence: analysis.confidence,
      };
    }

    let sanitized = input;
    const removedThreats: ThreatDetection[] = [];

    // Sort threats by severity and position (reverse order for string manipulation)
    const sortedThreats = analysis.threats
      .filter(t => t.severity === 'critical' || t.severity === 'high')
      .sort((a, b) => b.position.start - a.position.start);

    // Remove or replace malicious content
    for (const threat of sortedThreats) {
      if (threat.type === ThreatType.PROMPT_INJECTION) {
        // Replace with safe placeholder or remove entirely
        const before = sanitized.substring(0, threat.position.start);
        const after = sanitized.substring(threat.position.end);
        sanitized = before + '[CONTENT_FILTERED]' + after;
        removedThreats.push(threat);
      }
    }

    // Additional sanitization steps
    sanitized = this.applySanitizationRules(sanitized, context);

    this.emit('sanitized', {
      originalLength: input.length,
      sanitizedLength: sanitized.length,
      threatsRemoved: removedThreats.length,
      context,
    });

    return {
      sanitized,
      wasModified: sanitized !== input,
      removedThreats,
      confidence: analysis.confidence,
    };
  }

  private async detectPatternThreats(
    input: string
  ): Promise<ThreatDetection[]> {
    const threats: ThreatDetection[] = [];
    const lowerInput = input.toLowerCase();

    for (const regex of this.suspiciousRegexes) {
      regex.lastIndex = 0; // Reset regex state
      let match;

      while ((match = regex.exec(input)) !== null) {
        // Check if this match is whitelisted
        if (this.isWhitelisted(match[0], match.index)) {
          continue;
        }

        const threat: ThreatDetection = {
          type: this.classifyThreatType(match[0]),
          severity: this.calculateThreatSeverity(match[0]),
          pattern: match[0],
          description: this.generateThreatDescription(match[0]),
          position: {
            start: match.index,
            end: match.index + match[0].length,
          },
          confidence: this.calculatePatternConfidence(match[0]),
        };

        threats.push(threat);
      }
    }

    return threats;
  }

  private async analyzeLinguisticPatterns(
    input: string
  ): Promise<ThreatDetection[]> {
    const threats: ThreatDetection[] = [];

    try {
      // Use compromise.js for natural language analysis
      const doc = compromise(input);

      // Look for imperative sentences that might be injection attempts
      const imperatives = doc.match('#Imperative').out('array');
      for (const imperative of imperatives) {
        if (this.isImperativeInjection(imperative)) {
          threats.push({
            type: ThreatType.INSTRUCTION_IGNORE,
            severity: 'medium',
            pattern: imperative,
            description: 'Suspicious imperative instruction detected',
            position: this.findTextPosition(input, imperative),
            confidence: 0.6,
          });
        }
      }

      // Look for unusual sentence structures
      const sentences = doc.sentences().out('array');
      for (const sentence of sentences) {
        if (this.hasUnusualStructure(sentence)) {
          threats.push({
            type: ThreatType.CONTEXT_POLLUTION,
            severity: 'low',
            pattern: sentence,
            description:
              'Unusual sentence structure may indicate injection attempt',
            position: this.findTextPosition(input, sentence),
            confidence: 0.4,
          });
        }
      }
    } catch (error) {
      console.warn('Linguistic analysis failed:', error);
    }

    return threats;
  }

  private async analyzeSemanticContent(
    input: string
  ): Promise<ThreatDetection[]> {
    // This would use TensorFlow.js or similar for semantic analysis
    // For now, return empty array as placeholder
    return [];
  }

  private async detectEncodingAttacks(
    input: string
  ): Promise<ThreatDetection[]> {
    const threats: ThreatDetection[] = [];

    // Check for excessive encoded content
    const base64Matches = input.match(/[A-Za-z0-9+\/]{20,}/g) || [];
    const hexMatches = input.match(/(?:\\x[0-9a-fA-F]{2}){5,}/g) || [];
    const unicodeMatches = input.match(/(?:\\u[0-9a-fA-F]{4}){3,}/g) || [];

    if (base64Matches.length > 0) {
      for (const match of base64Matches) {
        threats.push({
          type: ThreatType.PROMPT_INJECTION,
          severity: 'medium',
          pattern: match,
          description: 'Suspicious base64 encoded content detected',
          position: this.findTextPosition(input, match),
          confidence: 0.7,
        });
      }
    }

    if (hexMatches.length > 0 || unicodeMatches.length > 0) {
      threats.push({
        type: ThreatType.PROMPT_INJECTION,
        severity: 'high',
        pattern: 'encoded_content',
        description: 'Suspicious encoded content that may bypass filters',
        position: { start: 0, end: input.length },
        confidence: 0.8,
      });
    }

    return threats;
  }

  private async detectContextInjection(
    input: string
  ): Promise<ThreatDetection[]> {
    const threats: ThreatDetection[] = [];

    // Look for patterns that suggest context manipulation
    const contextPatterns = [
      /the\s+(?:user|human|person)\s+(?:said|told|asked|mentioned)/gi,
      /in\s+(?:our|the)\s+previous\s+conversation/gi,
      /you\s+(?:previously|earlier|before)\s+(?:said|told|mentioned)/gi,
      /context\s*[:=]\s*['"]/gi,
      /conversation\s+history\s*[:=]/gi,
    ];

    for (const pattern of contextPatterns) {
      let match;
      while ((match = pattern.exec(input)) !== null) {
        threats.push({
          type: ThreatType.CONTEXT_POLLUTION,
          severity: 'medium',
          pattern: match[0],
          description: 'Potential context injection or manipulation',
          position: {
            start: match.index,
            end: match.index + match[0].length,
          },
          confidence: 0.6,
        });
      }
    }

    return threats;
  }

  private classifyThreatType(pattern: string): ThreatType {
    const lowerPattern = pattern.toLowerCase();

    if (
      lowerPattern.includes('ignore') ||
      lowerPattern.includes('forget') ||
      lowerPattern.includes('disregard')
    ) {
      return ThreatType.INSTRUCTION_IGNORE;
    }
    if (
      lowerPattern.includes('system') ||
      lowerPattern.includes('admin') ||
      lowerPattern.includes('root')
    ) {
      return ThreatType.SYSTEM_OVERRIDE;
    }
    if (
      lowerPattern.includes('pretend') ||
      lowerPattern.includes('act as') ||
      lowerPattern.includes('roleplay')
    ) {
      return ThreatType.ROLE_CONFUSION;
    }
    if (
      lowerPattern.includes('jailbreak') ||
      lowerPattern.includes('developer mode')
    ) {
      return ThreatType.JAILBREAK_ATTEMPT;
    }
    if (
      lowerPattern.includes('repeat') ||
      lowerPattern.includes('show') ||
      lowerPattern.includes('what are')
    ) {
      return ThreatType.EXTRACTION_ATTEMPT;
    }
    if (
      lowerPattern.includes('conversation') ||
      lowerPattern.includes('previous') ||
      lowerPattern.includes('context')
    ) {
      return ThreatType.CONTEXT_POLLUTION;
    }

    return ThreatType.PROMPT_INJECTION;
  }

  private calculateThreatSeverity(
    pattern: string
  ): 'low' | 'medium' | 'high' | 'critical' {
    const criticalKeywords = [
      'system',
      'admin',
      'root',
      'override',
      'jailbreak',
      'developer mode',
    ];
    const highKeywords = ['ignore', 'forget', 'disregard', 'pretend', 'bypass'];
    const mediumKeywords = ['roleplay', 'act as', 'show me', 'repeat'];

    const lowerPattern = pattern.toLowerCase();

    if (criticalKeywords.some(keyword => lowerPattern.includes(keyword))) {
      return 'critical';
    }
    if (highKeywords.some(keyword => lowerPattern.includes(keyword))) {
      return 'high';
    }
    if (mediumKeywords.some(keyword => lowerPattern.includes(keyword))) {
      return 'medium';
    }

    return 'low';
  }

  private calculatePatternConfidence(pattern: string): number {
    // Base confidence on pattern specificity and known effectiveness
    let confidence = 0.5;

    // Highly specific injection patterns get higher confidence
    if (pattern.includes('ignore previous instructions')) confidence = 0.95;
    if (pattern.includes('system prompt')) confidence = 0.9;
    if (pattern.includes('jailbreak mode')) confidence = 0.9;
    if (pattern.includes('developer mode')) confidence = 0.85;

    // Generic patterns get lower confidence
    if (pattern.length < 10) confidence *= 0.7;
    if (pattern.split(' ').length < 3) confidence *= 0.8;

    return Math.min(confidence, 1.0);
  }

  private calculateOverallConfidence(threats: ThreatDetection[]): number {
    if (threats.length === 0) return 1.0;

    const highConfidenceThreats = threats.filter(t => t.confidence > 0.7);
    const averageConfidence =
      threats.reduce((sum, t) => sum + t.confidence, 0) / threats.length;

    return highConfidenceThreats.length > 0
      ? averageConfidence
      : averageConfidence * 0.8;
  }

  private generateThreatDescription(pattern: string): string {
    const lowerPattern = pattern.toLowerCase();

    if (lowerPattern.includes('ignore'))
      return 'Attempt to override system instructions';
    if (lowerPattern.includes('forget'))
      return 'Attempt to reset conversation context';
    if (lowerPattern.includes('system'))
      return 'Attempt to access system-level functionality';
    if (lowerPattern.includes('jailbreak'))
      return 'Jailbreak attempt to bypass safety measures';
    if (lowerPattern.includes('pretend') || lowerPattern.includes('act as'))
      return 'Role confusion attack';
    if (lowerPattern.includes('repeat') || lowerPattern.includes('show'))
      return 'Information extraction attempt';

    return 'Suspicious pattern that may indicate prompt injection';
  }

  private isWhitelisted(pattern: string, position: number): boolean {
    for (const whitelist of PromptInjectionPrevention.WHITELISTED_PATTERNS) {
      if (whitelist.test(pattern)) return true;
    }
    return false;
  }

  private isImperativeInjection(sentence: string): boolean {
    const dangerousImperatives = [
      'ignore',
      'forget',
      'disregard',
      'override',
      'bypass',
      'disable',
      'pretend',
      'act',
      'roleplay',
      'become',
      'transform',
    ];

    const words = sentence.toLowerCase().split(/\s+/);
    return dangerousImperatives.some(imperative => words.includes(imperative));
  }

  private hasUnusualStructure(sentence: string): boolean {
    // Look for unusual punctuation patterns or structure that might indicate injection
    const unusualPatterns = [
      /\[.*\]/, // Bracket notation
      /\{.*\}/, // Brace notation
      /<!--.*-->/, // HTML comments
      /```.*```/, // Code blocks
      /::|=>|<-|->/, // Unusual operators
    ];

    return unusualPatterns.some(pattern => pattern.test(sentence));
  }

  private findTextPosition(
    text: string,
    substring: string
  ): { start: number; end: number } {
    const index = text.indexOf(substring);
    return {
      start: index,
      end: index + substring.length,
    };
  }

  private applySanitizationRules(
    text: string,
    context?: SanitizationContext
  ): string {
    let sanitized = text;

    // Remove suspicious Unicode characters
    sanitized = sanitized.replace(/[\u200B-\u200D\uFEFF]/g, ''); // Zero-width characters
    sanitized = sanitized.replace(/[\u0000-\u001F\u007F-\u009F]/g, ''); // Control characters

    // Limit consecutive special characters
    sanitized = sanitized.replace(
      /[!@#$%^&*()]{5,}/g,
      '[SPECIAL_CHARS_FILTERED]'
    );

    // Remove excessive whitespace
    sanitized = sanitized.replace(/\s{10,}/g, ' ');

    return sanitized;
  }

  private generateCacheKey(input: string): string {
    return createHash('sha256').update(input).digest('hex').substring(0, 16);
  }

  public getMetrics() {
    return {
      cacheSize: this.cache.size,
      patternsLoaded: this.suspiciousRegexes.length,
      configVersion: this.config,
    };
  }

  public clearCache(): void {
    this.cache.clear();
    this.emit('cacheClear');
  }

  public updateConfig(newConfig: Partial<PromptInjectionConfig>): void {
    this.config = { ...this.config, ...newConfig };
    this.suspiciousRegexes = this.compilePatterns();
    this.clearCache(); // Clear cache when config changes
    this.emit('configUpdated', this.config);
  }
}
