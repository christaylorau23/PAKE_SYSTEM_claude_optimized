import {
  OutputValidationConfig,
  SecurityContext,
  ThreatDetection,
  ThreatType,
  AISecurityError,
} from '../types/security.types';
import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';
import * as natural from 'natural';
import * as sentiment from 'sentiment';
import NodeCache from 'node-cache';
import { createHash } from 'crypto';

interface FilteringRule {
  id: string;
  name: string;
  pattern: RegExp;
  severity: 'low' | 'medium' | 'high' | 'critical';
  action: 'flag' | 'sanitize' | 'block';
  category: string;
  description: string;
  enabled: boolean;
}

interface FilteringResult {
  isClean: boolean;
  filteredOutput: string;
  violations: OutputViolation[];
  confidence: number;
  metadata: {
    originalLength: number;
    filteredLength: number;
    rulesTriggered: number;
    processingTime: number;
    filterId: string;
  };
}

interface OutputViolation {
  ruleId: string;
  ruleName: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  category: string;
  description: string;
  matchedContent: string;
  position: { start: number; end: number };
  action: 'flag' | 'sanitize' | 'block';
  confidence: number;
}

interface ContentAnalysis {
  sentiment: number;
  toxicity: number;
  coherence: number;
  factuality: number;
  safety: number;
  appropriateness: number;
}

export class OutputFiltering extends EventEmitter {
  private config: OutputValidationConfig;
  private filteringRules: Map<string, FilteringRule>;
  private cache: NodeCache;
  private sentimentAnalyzer: any;
  private toxicityDetector?: any;

  // Comprehensive content filtering rules
  private static readonly DEFAULT_RULES: Partial<FilteringRule>[] = [
    // Security and Privacy
    {
      name: 'Personal Information',
      pattern:
        /\b(?:ssn|social\s+security|credit\s+card|passport|driver'?s?\s+license)\b.*?\b\d+\b/gi,
      severity: 'critical',
      action: 'block',
      category: 'privacy',
      description:
        'Blocks output containing personal identification information',
    },
    {
      name: 'Financial Information',
      pattern:
        /\b(?:account\s+number|routing\s+number|bank\s+account|credit\s+card)\b.*?\b\d{4,}\b/gi,
      severity: 'critical',
      action: 'block',
      category: 'privacy',
      description: 'Blocks financial account information',
    },
    {
      name: 'Email Addresses',
      pattern: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/gi,
      severity: 'medium',
      action: 'sanitize',
      category: 'privacy',
      description: 'Sanitizes email addresses',
    },
    {
      name: 'Phone Numbers',
      pattern:
        /\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b/gi,
      severity: 'medium',
      action: 'sanitize',
      category: 'privacy',
      description: 'Sanitizes phone numbers',
    },
    {
      name: 'IP Addresses',
      pattern:
        /\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b/gi,
      severity: 'medium',
      action: 'sanitize',
      category: 'privacy',
      description: 'Sanitizes IP addresses',
    },

    // Harmful Content
    {
      name: 'Hate Speech',
      pattern:
        /\b(?:hate|despise|detest)\b.*?\b(?:race|religion|gender|sexuality|ethnicity)\b/gi,
      severity: 'critical',
      action: 'block',
      category: 'harmful',
      description: 'Blocks hate speech content',
    },
    {
      name: 'Violence Incitement',
      pattern:
        /\b(?:kill|murder|harm|attack|destroy|eliminate)\b.*?\b(?:person|people|group|individual)\b/gi,
      severity: 'critical',
      action: 'block',
      category: 'harmful',
      description: 'Blocks content inciting violence',
    },
    {
      name: 'Self-Harm Content',
      pattern:
        /\b(?:suicide|self-harm|self-injury|cut\s+yourself|end\s+your\s+life)\b/gi,
      severity: 'critical',
      action: 'block',
      category: 'harmful',
      description: 'Blocks self-harm related content',
    },

    // Inappropriate Content
    {
      name: 'Sexual Content',
      pattern:
        /\b(?:explicit|graphic|sexual|pornographic|erotic)\b.*?\b(?:content|material|images?|videos?)\b/gi,
      severity: 'high',
      action: 'block',
      category: 'inappropriate',
      description: 'Blocks explicit sexual content',
    },
    {
      name: 'Drug-Related Content',
      pattern:
        /\b(?:how\s+to\s+(?:make|produce|synthesize)|instructions?\s+for)\b.*?\b(?:drugs?|narcotics?|methamphetamine|cocaine|heroin)\b/gi,
      severity: 'high',
      action: 'block',
      category: 'inappropriate',
      description: 'Blocks drug manufacturing instructions',
    },

    // Misinformation and Conspiracy
    {
      name: 'Medical Misinformation',
      pattern:
        /\b(?:cure|treatment|miracle\s+cure)\b.*?\b(?:cancer|diabetes|covid|hiv|aids)\b.*?\b(?:guaranteed|100%\s+effective|instant)\b/gi,
      severity: 'high',
      action: 'flag',
      category: 'misinformation',
      description: 'Flags potential medical misinformation',
    },
    {
      name: 'Conspiracy Theories',
      pattern:
        /\b(?:conspiracy|cover-up|government\s+lies|fake\s+news)\b.*?\b(?:truth|evidence|proof|facts?)\b/gi,
      severity: 'medium',
      action: 'flag',
      category: 'misinformation',
      description: 'Flags conspiracy theory content',
    },

    // Legal and Ethical Issues
    {
      name: 'Copyright Violation',
      pattern:
        /\b(?:pirated?|cracked?|illegal\s+download|torrent)\b.*?\b(?:software|movie|music|book|content)\b/gi,
      severity: 'high',
      action: 'block',
      category: 'legal',
      description: 'Blocks copyright violation content',
    },
    {
      name: 'Illegal Activities',
      pattern:
        /\b(?:how\s+to\s+(?:hack|break\s+into|steal)|instructions?\s+for)\b.*?\b(?:illegal|unlawful|criminal)\b/gi,
      severity: 'critical',
      action: 'block',
      category: 'legal',
      description: 'Blocks illegal activity instructions',
    },

    // Professional and Academic Integrity
    {
      name: 'Plagiarism',
      pattern:
        /\b(?:copy|paste|plagiarize|steal)\b.*?\b(?:work|essay|paper|assignment|homework)\b/gi,
      severity: 'high',
      action: 'flag',
      category: 'integrity',
      description: 'Flags potential plagiarism guidance',
    },
    {
      name: 'Academic Dishonesty',
      pattern:
        /\b(?:cheat|cheating|exam\s+answers?|test\s+solutions?)\b.*?\b(?:help|assistance|answers?)\b/gi,
      severity: 'high',
      action: 'flag',
      category: 'integrity',
      description: 'Flags academic dishonesty content',
    },

    // System Security
    {
      name: 'Malicious Code',
      pattern:
        /\b(?:malware|virus|trojan|ransomware|keylogger)\b.*?\b(?:code|script|program)\b/gi,
      severity: 'critical',
      action: 'block',
      category: 'security',
      description: 'Blocks malicious code content',
    },
    {
      name: 'System Exploitation',
      pattern:
        /\b(?:exploit|vulnerability|backdoor|shell\s+access)\b.*?\b(?:system|server|network)\b/gi,
      severity: 'critical',
      action: 'block',
      category: 'security',
      description: 'Blocks system exploitation content',
    },

    // Quality and Coherence
    {
      name: 'Excessive Repetition',
      pattern: /\b(\w+)(?:\s+\1){4,}\b/gi,
      severity: 'medium',
      action: 'sanitize',
      category: 'quality',
      description: 'Sanitizes excessive word repetition',
    },
    {
      name: 'Gibberish Content',
      pattern: /\b[bcdfghjklmnpqrstvwxyz]{6,}\b/gi,
      severity: 'medium',
      action: 'flag',
      category: 'quality',
      description: 'Flags potentially gibberish content',
    },

    // Bias and Fairness
    {
      name: 'Gender Bias',
      pattern:
        /\b(?:men|women|male|female)\s+are\s+(?:better|worse|superior|inferior)\b/gi,
      severity: 'medium',
      action: 'flag',
      category: 'bias',
      description: 'Flags potential gender bias',
    },
    {
      name: 'Racial Bias',
      pattern:
        /\b(?:race|ethnicity|nationality)\b.*?\b(?:superior|inferior|better|worse)\b/gi,
      severity: 'high',
      action: 'flag',
      category: 'bias',
      description: 'Flags potential racial bias',
    },
  ];

  // Replacement patterns for sanitization
  private static readonly SANITIZATION_REPLACEMENTS = new Map([
    ['email', '[EMAIL_REDACTED]'],
    ['phone', '[PHONE_REDACTED]'],
    ['ip', '[IP_REDACTED]'],
    ['ssn', '[SSN_REDACTED]'],
    ['credit_card', '[CARD_REDACTED]'],
    ['repetition', '[CONTENT_CLEANED]'],
    ['profanity', '[CONTENT_FILTERED]'],
  ]);

  constructor(config: OutputValidationConfig) {
    super();
    this.config = config;
    this.filteringRules = new Map();
    this.cache = new NodeCache({ stdTTL: 1800 }); // 30 minutes

    // Initialize NLP tools
    this.sentimentAnalyzer = new sentiment();

    // Load default filtering rules
    this.loadDefaultRules();

    // Initialize toxicity detector (placeholder)
    this.initializeToxicityDetector();

    this.emit('initialized', {
      config,
      rulesLoaded: this.filteringRules.size,
    });
  }

  private loadDefaultRules(): void {
    OutputFiltering.DEFAULT_RULES.forEach((ruleConfig, index) => {
      const rule: FilteringRule = {
        id: uuidv4(),
        enabled: true,
        ...(ruleConfig as FilteringRule),
      };
      this.filteringRules.set(rule.id, rule);
    });
  }

  private async initializeToxicityDetector(): Promise<void> {
    // In production, this would load a toxicity detection model
    this.toxicityDetector = {
      predict: (text: string) => {
        // Simple heuristic-based toxicity detection
        const toxicWords = ['hate', 'kill', 'stupid', 'idiot', 'moron'];
        const words = text.toLowerCase().split(/\s+/);
        const toxicCount = words.filter(word =>
          toxicWords.includes(word)
        ).length;
        return Math.min((toxicCount / words.length) * 10, 1);
      },
    };
  }

  public async filterOutput(
    output: string,
    context: SecurityContext
  ): Promise<FilteringResult> {
    const startTime = performance.now();
    const filterId = uuidv4();

    try {
      // Check cache first
      const cacheKey = this.generateCacheKey(output);
      const cached = this.cache.get<FilteringResult>(cacheKey);
      if (cached) {
        this.emit('cacheHit', { filterId, cacheKey });
        return cached;
      }

      const violations: OutputViolation[] = [];
      let filteredOutput = output;
      let rulesTriggered = 0;

      // Apply all enabled filtering rules
      for (const rule of this.filteringRules.values()) {
        if (!rule.enabled) continue;

        const ruleViolations = await this.applyRule(rule, filteredOutput);
        if (ruleViolations.length > 0) {
          violations.push(...ruleViolations);
          rulesTriggered++;

          // Apply sanitization/blocking based on rule actions
          filteredOutput = await this.applyRuleActions(
            filteredOutput,
            ruleViolations
          );
        }
      }

      // Additional content analysis
      const contentAnalysis = await this.analyzeContent(output);
      const additionalViolations = this.generateAnalysisViolations(
        contentAnalysis,
        output
      );
      violations.push(...additionalViolations);

      // Calculate overall confidence
      const confidence = this.calculateFilteringConfidence(
        violations,
        contentAnalysis
      );

      // Determine if output is clean
      const criticalViolations = violations.filter(
        v => v.severity === 'critical'
      );
      const highViolations = violations.filter(v => v.severity === 'high');
      const isClean =
        criticalViolations.length === 0 &&
        (this.config.requireCoherence ? contentAnalysis.coherence > 0.6 : true);

      const result: FilteringResult = {
        isClean,
        filteredOutput: isClean
          ? filteredOutput
          : this.generateSafeAlternative(output, violations),
        violations,
        confidence,
        metadata: {
          originalLength: output.length,
          filteredLength: filteredOutput.length,
          rulesTriggered,
          processingTime: performance.now() - startTime,
          filterId,
        },
      };

      // Cache the result
      this.cache.set(cacheKey, result);

      this.emit('outputFiltered', {
        filterId,
        isClean,
        violationCount: violations.length,
        severityBreakdown: this.getViolationSeverityBreakdown(violations),
        confidence,
        context,
      });

      // Throw error for critical violations if configured to block
      const blockingViolations = violations.filter(v => v.action === 'block');
      if (blockingViolations.length > 0) {
        throw new AISecurityError(
          `Output blocked due to ${blockingViolations.length} critical violations`,
          'OUTPUT_BLOCKED',
          context
        );
      }

      return result;
    } catch (error) {
      this.emit('filteringError', { filterId, error, context });
      throw error;
    }
  }

  private async applyRule(
    rule: FilteringRule,
    text: string
  ): Promise<OutputViolation[]> {
    const violations: OutputViolation[] = [];
    let match;

    // Reset regex state
    rule.pattern.lastIndex = 0;

    while ((match = rule.pattern.exec(text)) !== null) {
      violations.push({
        ruleId: rule.id,
        ruleName: rule.name,
        severity: rule.severity,
        category: rule.category,
        description: rule.description,
        matchedContent: match[0],
        position: {
          start: match.index,
          end: match.index + match[0].length,
        },
        action: rule.action,
        confidence: this.calculateRuleConfidence(rule, match[0]),
      });
    }

    return violations;
  }

  private async applyRuleActions(
    text: string,
    violations: OutputViolation[]
  ): Promise<string> {
    let modifiedText = text;

    // Sort violations by position (reverse order for string manipulation)
    const sortedViolations = violations
      .filter(v => v.action === 'sanitize')
      .sort((a, b) => b.position.start - a.position.start);

    for (const violation of sortedViolations) {
      const replacement = this.getReplacementText(violation);
      const before = modifiedText.substring(0, violation.position.start);
      const after = modifiedText.substring(violation.position.end);
      modifiedText = before + replacement + after;
    }

    return modifiedText;
  }

  private async analyzeContent(text: string): Promise<ContentAnalysis> {
    const analysis: ContentAnalysis = {
      sentiment: this.analyzeSentiment(text),
      toxicity: this.analyzeToxicity(text),
      coherence: await this.analyzeCoherence(text),
      factuality: await this.analyzeFactuality(text),
      safety: this.analyzeSafety(text),
      appropriateness: this.analyzeAppropriateness(text),
    };

    return analysis;
  }

  private analyzeSentiment(text: string): number {
    const result = this.sentimentAnalyzer.analyze(text);
    // Normalize to -1 to 1 scale
    return Math.max(
      -1,
      Math.min(1, result.score / Math.max(result.tokens.length, 1))
    );
  }

  private analyzeToxicity(text: string): number {
    if (this.toxicityDetector) {
      return this.toxicityDetector.predict(text);
    }
    return 0;
  }

  private async analyzeCoherence(text: string): Promise<number> {
    // Simple coherence analysis based on sentence connectivity
    const sentences = text.split(/[.!?]+/).filter(s => s.trim());
    if (sentences.length < 2) return 1.0;

    let coherenceScore = 0;
    for (let i = 0; i < sentences.length - 1; i++) {
      const sent1 = sentences[i].trim().toLowerCase();
      const sent2 = sentences[i + 1].trim().toLowerCase();

      if (sent1 && sent2) {
        // Simple word overlap as coherence measure
        const words1 = new Set(sent1.split(/\s+/));
        const words2 = new Set(sent2.split(/\s+/));
        const intersection = new Set([...words1].filter(x => words2.has(x)));
        const union = new Set([...words1, ...words2]);

        coherenceScore += intersection.size / union.size;
      }
    }

    return coherenceScore / (sentences.length - 1);
  }

  private async analyzeFactuality(text: string): Promise<number> {
    let factualityScore = 0.5; // Neutral baseline

    // Check for uncertainty markers (good for factuality)
    const uncertaintyMarkers =
      /\b(maybe|perhaps|possibly|might|could|seems|likely)\b/gi;
    const uncertaintyCount = (text.match(uncertaintyMarkers) || []).length;
    factualityScore += Math.min(uncertaintyCount * 0.05, 0.2);

    // Check for absolute claims (potentially problematic)
    const absoluteMarkers =
      /\b(always|never|all|none|definitely|certainly|absolutely|guaranteed)\b/gi;
    const absoluteCount = (text.match(absoluteMarkers) || []).length;
    factualityScore -= Math.min(absoluteCount * 0.1, 0.3);

    // Check for source references (good for factuality)
    const sourceMarkers =
      /\b(according to|research shows|study found|experts say|data indicates)\b/gi;
    const sourceCount = (text.match(sourceMarkers) || []).length;
    factualityScore += Math.min(sourceCount * 0.1, 0.2);

    return Math.max(0, Math.min(1, factualityScore));
  }

  private analyzeSafety(text: string): number {
    let safetyScore = 1.0; // Start with safe assumption

    // Check for dangerous instruction patterns
    const dangerousPatterns = [
      /\b(?:how\s+to\s+(?:make|build|create))\b.*?\b(?:bomb|explosive|weapon)\b/gi,
      /\b(?:instructions?\s+for)\b.*?\b(?:harmful|dangerous|illegal)\b/gi,
      /\b(?:recipe\s+for)\b.*?\b(?:poison|toxin|drug)\b/gi,
    ];

    for (const pattern of dangerousPatterns) {
      if (pattern.test(text)) {
        safetyScore -= 0.5;
      }
    }

    return Math.max(0, safetyScore);
  }

  private analyzeAppropriateness(text: string): number {
    let appropriatenessScore = 1.0;

    // Check for inappropriate language
    const inappropriatePatterns = [
      /\b(?:explicit|graphic|vulgar|obscene)\b/gi,
      /\b(?:sexual|erotic|pornographic)\b/gi,
      /\b(?:violent|gruesome|disturbing)\b/gi,
    ];

    for (const pattern of inappropriatePatterns) {
      const matches = text.match(pattern) || [];
      appropriatenessScore -= matches.length * 0.2;
    }

    return Math.max(0, appropriatenessScore);
  }

  private generateAnalysisViolations(
    analysis: ContentAnalysis,
    text: string
  ): OutputViolation[] {
    const violations: OutputViolation[] = [];

    // Toxicity violation
    if (analysis.toxicity > 0.7) {
      violations.push({
        ruleId: 'analysis_toxicity',
        ruleName: 'High Toxicity Content',
        severity: 'high',
        category: 'harmful',
        description: `Content has high toxicity score: ${analysis.toxicity.toFixed(2)}`,
        matchedContent: text.substring(0, 100) + '...',
        position: { start: 0, end: text.length },
        action: 'flag',
        confidence: analysis.toxicity,
      });
    }

    // Safety violation
    if (analysis.safety < 0.3) {
      violations.push({
        ruleId: 'analysis_safety',
        ruleName: 'Safety Concerns',
        severity: 'critical',
        category: 'harmful',
        description: `Content has safety concerns: ${analysis.safety.toFixed(2)}`,
        matchedContent: text.substring(0, 100) + '...',
        position: { start: 0, end: text.length },
        action: 'block',
        confidence: 1 - analysis.safety,
      });
    }

    // Coherence violation
    if (this.config.requireCoherence && analysis.coherence < 0.4) {
      violations.push({
        ruleId: 'analysis_coherence',
        ruleName: 'Low Coherence',
        severity: 'medium',
        category: 'quality',
        description: `Content lacks coherence: ${analysis.coherence.toFixed(2)}`,
        matchedContent: text.substring(0, 100) + '...',
        position: { start: 0, end: text.length },
        action: 'flag',
        confidence: 1 - analysis.coherence,
      });
    }

    // Appropriateness violation
    if (analysis.appropriateness < 0.5) {
      violations.push({
        ruleId: 'analysis_appropriateness',
        ruleName: 'Inappropriate Content',
        severity: 'high',
        category: 'inappropriate',
        description: `Content may be inappropriate: ${analysis.appropriateness.toFixed(2)}`,
        matchedContent: text.substring(0, 100) + '...',
        position: { start: 0, end: text.length },
        action: 'flag',
        confidence: 1 - analysis.appropriateness,
      });
    }

    return violations;
  }

  private calculateRuleConfidence(
    rule: FilteringRule,
    matchedContent: string
  ): number {
    let confidence = 0.7; // Base confidence

    // Adjust based on rule severity
    switch (rule.severity) {
      case 'critical':
        confidence = 0.9;
        break;
      case 'high':
        confidence = 0.8;
        break;
      case 'medium':
        confidence = 0.7;
        break;
      case 'low':
        confidence = 0.6;
        break;
    }

    // Adjust based on match length (longer matches generally more reliable)
    if (matchedContent.length > 20) confidence += 0.1;
    if (matchedContent.length > 50) confidence += 0.1;

    return Math.min(confidence, 1.0);
  }

  private calculateFilteringConfidence(
    violations: OutputViolation[],
    analysis: ContentAnalysis
  ): number {
    if (violations.length === 0) return 1.0;

    const violationConfidences = violations.map(v => v.confidence);
    const avgViolationConfidence =
      violationConfidences.reduce((sum, conf) => sum + conf, 0) /
      violationConfidences.length;

    // Combine violation confidence with content analysis
    const analysisConfidence =
      (1 - analysis.toxicity) * 0.3 +
      analysis.safety * 0.3 +
      analysis.appropriateness * 0.2 +
      analysis.coherence * 0.2;

    return avgViolationConfidence * 0.7 + (1 - analysisConfidence) * 0.3;
  }

  private getReplacementText(violation: OutputViolation): string {
    // Determine replacement based on category
    const category = violation.category.toLowerCase();

    if (violation.matchedContent.includes('@')) {
      return (
        OutputFiltering.SANITIZATION_REPLACEMENTS.get('email') || '[REDACTED]'
      );
    }

    if (/\d{3}[-.\s]?\d{3}[-.\s]?\d{4}/.test(violation.matchedContent)) {
      return (
        OutputFiltering.SANITIZATION_REPLACEMENTS.get('phone') || '[REDACTED]'
      );
    }

    if (/\d+\.\d+\.\d+\.\d+/.test(violation.matchedContent)) {
      return (
        OutputFiltering.SANITIZATION_REPLACEMENTS.get('ip') || '[REDACTED]'
      );
    }

    // Default replacements by category
    const categoryReplacements = new Map([
      ['privacy', '[PERSONAL_INFO_REDACTED]'],
      ['harmful', '[HARMFUL_CONTENT_REMOVED]'],
      ['inappropriate', '[INAPPROPRIATE_CONTENT_FILTERED]'],
      ['security', '[SECURITY_CONTENT_BLOCKED]'],
      ['quality', '[CONTENT_IMPROVED]'],
      ['bias', '[CONTENT_REVIEWED]'],
    ]);

    return categoryReplacements.get(category) || '[CONTENT_FILTERED]';
  }

  private generateSafeAlternative(
    originalOutput: string,
    violations: OutputViolation[]
  ): string {
    // Generate a safe, generic response when blocking content
    const severityMap = new Map<string, number>();
    violations.forEach(v => {
      severityMap.set(v.severity, (severityMap.get(v.severity) || 0) + 1);
    });

    if (severityMap.get('critical') || 0 > 0) {
      return "I cannot provide that information as it may contain harmful or inappropriate content. Please rephrase your request in a way that doesn't involve potentially dangerous topics.";
    }

    if (severityMap.get('high') || 0 > 0) {
      return "I've detected some content that may not be appropriate. Please let me know if you'd like me to provide information on this topic in a different way.";
    }

    return "I've filtered some content from my response to ensure it meets safety guidelines. The remaining information should be helpful and appropriate.";
  }

  private getViolationSeverityBreakdown(
    violations: OutputViolation[]
  ): Record<string, number> {
    const breakdown = { critical: 0, high: 0, medium: 0, low: 0 };
    violations.forEach(v => {
      breakdown[v.severity]++;
    });
    return breakdown;
  }

  private generateCacheKey(text: string): string {
    return createHash('sha256').update(text).digest('hex').substring(0, 16);
  }

  // Public API methods

  public addRule(rule: Omit<FilteringRule, 'id'>): string {
    const fullRule: FilteringRule = {
      id: uuidv4(),
      ...rule,
    };

    this.filteringRules.set(fullRule.id, fullRule);
    this.emit('ruleAdded', { ruleId: fullRule.id, ruleName: rule.name });

    return fullRule.id;
  }

  public updateRule(ruleId: string, updates: Partial<FilteringRule>): boolean {
    const existingRule = this.filteringRules.get(ruleId);
    if (!existingRule) return false;

    const updatedRule = { ...existingRule, ...updates, id: ruleId };
    this.filteringRules.set(ruleId, updatedRule);

    this.emit('ruleUpdated', { ruleId, updates });
    return true;
  }

  public deleteRule(ruleId: string): boolean {
    const deleted = this.filteringRules.delete(ruleId);
    if (deleted) {
      this.emit('ruleDeleted', { ruleId });
    }
    return deleted;
  }

  public enableRule(ruleId: string): boolean {
    return this.updateRule(ruleId, { enabled: true });
  }

  public disableRule(ruleId: string): boolean {
    return this.updateRule(ruleId, { enabled: false });
  }

  public getRules(): FilteringRule[] {
    return Array.from(this.filteringRules.values());
  }

  public getRule(ruleId: string): FilteringRule | undefined {
    return this.filteringRules.get(ruleId);
  }

  public getRulesByCategory(category: string): FilteringRule[] {
    return Array.from(this.filteringRules.values()).filter(
      rule => rule.category.toLowerCase() === category.toLowerCase()
    );
  }

  public testRule(ruleId: string, testText: string): OutputViolation[] {
    const rule = this.filteringRules.get(ruleId);
    if (!rule) return [];

    const violations: OutputViolation[] = [];
    let match;

    rule.pattern.lastIndex = 0;
    while ((match = rule.pattern.exec(testText)) !== null) {
      violations.push({
        ruleId: rule.id,
        ruleName: rule.name,
        severity: rule.severity,
        category: rule.category,
        description: rule.description,
        matchedContent: match[0],
        position: {
          start: match.index,
          end: match.index + match[0].length,
        },
        action: rule.action,
        confidence: this.calculateRuleConfidence(rule, match[0]),
      });
    }

    return violations;
  }

  public getMetrics() {
    return {
      totalRules: this.filteringRules.size,
      enabledRules: Array.from(this.filteringRules.values()).filter(
        r => r.enabled
      ).length,
      cacheSize: this.cache.keys().length,
      rulesByCategory: this.getRuleDistribution(),
      config: this.config,
    };
  }

  private getRuleDistribution(): Record<string, number> {
    const distribution: Record<string, number> = {};

    for (const rule of this.filteringRules.values()) {
      distribution[rule.category] = (distribution[rule.category] || 0) + 1;
    }

    return distribution;
  }

  public clearCache(): void {
    this.cache.flushAll();
    this.emit('cacheCleared');
  }

  public updateConfig(newConfig: Partial<OutputValidationConfig>): void {
    this.config = { ...this.config, ...newConfig };
    this.clearCache(); // Clear cache when config changes
    this.emit('configUpdated', this.config);
  }

  public exportRules(): FilteringRule[] {
    return Array.from(this.filteringRules.values());
  }

  public importRules(rules: FilteringRule[]): number {
    let importedCount = 0;

    for (const rule of rules) {
      try {
        // Validate rule structure
        if (rule.name && rule.pattern && rule.severity) {
          this.filteringRules.set(rule.id || uuidv4(), {
            id: rule.id || uuidv4(),
            ...rule,
          });
          importedCount++;
        }
      } catch (error) {
        console.warn(`Failed to import rule: ${rule.name}`, error);
      }
    }

    this.emit('rulesImported', { count: importedCount });
    return importedCount;
  }
}
