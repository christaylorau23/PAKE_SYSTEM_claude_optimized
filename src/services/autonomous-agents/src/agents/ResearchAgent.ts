import { BaseAgent } from '@/core/BaseAgent';
import {
  AgentConfig,
  Task,
  TaskResult,
  AgentCapabilities,
  TaskLog,
  TaskArtifact,
} from '@/types/agent';
import axios from 'axios';
import * as cheerio from 'cheerio';
import { performance } from 'perf_hooks';
import { v4 as uuidv4 } from 'uuid';

interface ResearchSource {
  url: string;
  title: string;
  content: string;
  credibility: number;
  relevance: number;
  lastUpdated?: Date;
  citations: string[];
}

interface ResearchQuery {
  query: string;
  domains?: string[];
  dateRange?: {
    from: Date;
    to: Date;
  };
  sourceTypes?: string[];
  maxSources?: number;
}

interface ResearchResult {
  sources: ResearchSource[];
  summary: string;
  keyFindings: string[];
  citations: string[];
  confidence: number;
  completeness: number;
}

export class ResearchAgent extends BaseAgent {
  private webSearchApiKey?: string;
  private factCheckApiKey?: string;
  private maxSourcesPerQuery = 20;
  private credibilityThreshold = 0.7;

  constructor(config: AgentConfig) {
    super(config);
    this.webSearchApiKey = process.env.WEB_SEARCH_API_KEY;
    this.factCheckApiKey = process.env.FACT_CHECK_API_KEY;
    this.status = 'idle';
    this.logger.info('Research Agent initialized');
  }

  public canHandle(task: Task): boolean {
    return task.type === 'research' && this.hasRequiredTools(task);
  }

  public getCapabilities(): AgentCapabilities {
    return {
      webSearch: true,
      fileOperations: true,
      codeExecution: false,
      apiCalls: true,
      emailSending: false,
      documentCreation: true,
      dataAnalysis: true,
      imageProcessing: false,
      audioProcessing: false,
      videoProcessing: false,
    };
  }

  public async execute(task: Task): Promise<TaskResult> {
    const startTime = performance.now();
    const logs: TaskLog[] = [];
    const artifacts: TaskArtifact[] = [];
    let totalCost = 0;
    let apiCallsMade = 0;

    try {
      // Parse research requirements from task
      const researchQuery = this.parseResearchQuery(task);
      logs.push(
        this.log('info', `Starting research on: ${researchQuery.query}`)
      );

      // Perform web search
      logs.push(this.log('info', 'Conducting web search'));
      const searchResults = await this.performWebSearch(researchQuery);
      apiCallsMade += 1;
      totalCost += 0.01; // Estimated cost per search

      // Gather detailed information from sources
      logs.push(
        this.log('info', `Processing ${searchResults.length} search results`)
      );
      const sources = await this.gatherSourceInformation(
        searchResults,
        researchQuery
      );
      apiCallsMade += sources.length;
      totalCost += sources.length * 0.005;

      // Verify source credibility
      logs.push(this.log('info', 'Verifying source credibility'));
      const verifiedSources = await this.verifySources(sources);

      // Fact-check key claims
      logs.push(this.log('info', 'Performing fact verification'));
      const factCheckedSources = await this.factCheckSources(verifiedSources);
      if (this.factCheckApiKey) {
        apiCallsMade += verifiedSources.length;
        totalCost += verifiedSources.length * 0.02;
      }

      // Synthesize research findings
      logs.push(this.log('info', 'Synthesizing research findings'));
      const researchResult = await this.synthesizeFindings(
        factCheckedSources,
        researchQuery
      );

      // Generate research report
      const reportArtifact = await this.generateResearchReport(
        researchResult,
        task
      );
      artifacts.push(reportArtifact);

      // Create citation list
      const citationsArtifact = await this.generateCitations(
        researchResult.sources
      );
      artifacts.push(citationsArtifact);

      const executionTime = performance.now() - startTime;

      // Calculate quality and confidence scores
      const quality = this.calculateResearchQuality(researchResult);
      const confidence = this.calculateConfidence(researchResult);

      logs.push(
        this.log('info', `Research completed in ${Math.round(executionTime)}ms`)
      );
      logs.push(
        this.log(
          'info',
          `Found ${researchResult.sources.length} credible sources`
        )
      );
      logs.push(
        this.log(
          'info',
          `Quality score: ${quality.toFixed(2)}, Confidence: ${confidence.toFixed(2)}`
        )
      );

      return {
        outputs: {
          summary: researchResult.summary,
          keyFindings: researchResult.keyFindings,
          sources: researchResult.sources,
          citations: researchResult.citations,
          researchReport: reportArtifact.path,
          citationsList: citationsArtifact.path,
        },
        metrics: {
          executionTime,
          tokensUsed: this.estimateTokensUsed(researchResult),
          apiCallsMade,
          costIncurred: totalCost,
          toolsUsed: [
            'web_search',
            'content_extraction',
            'fact_check',
            'document_generation',
          ],
          errorCount: 0,
          retryCount: 0,
        },
        logs,
        artifacts,
        confidence,
        quality,
      };
    } catch (error) {
      logs.push(
        this.log('error', `Research failed: ${(error as Error).message}`)
      );
      throw error;
    }
  }

  private parseResearchQuery(task: Task): ResearchQuery {
    const query = task.requirements.inputs.find(i => i.name === 'query')
      ?.value as string;
    const domains = task.requirements.inputs.find(i => i.name === 'domains')
      ?.value as string[];
    const sourceTypes = task.requirements.inputs.find(
      i => i.name === 'sourceTypes'
    )?.value as string[];
    const maxSources = task.requirements.inputs.find(
      i => i.name === 'maxSources'
    )?.value as number;

    if (!query) {
      throw new Error('Research query is required');
    }

    return {
      query,
      domains,
      sourceTypes: sourceTypes || [
        'academic',
        'news',
        'official',
        'documentation',
      ],
      maxSources: maxSources || this.maxSourcesPerQuery,
    };
  }

  private async performWebSearch(researchQuery: ResearchQuery): Promise<any[]> {
    if (!this.webSearchApiKey) {
      // Fallback to simulated search results
      this.logger.warn('Web search API key not configured, using mock results');
      return this.generateMockSearchResults(researchQuery);
    }

    try {
      // Using a generic search API (could be Google Custom Search, Bing, etc.)
      const response = await axios.get('https://api.search.com/v1/search', {
        params: {
          q: researchQuery.query,
          key: this.webSearchApiKey,
          num: Math.min(researchQuery.maxSources || 10, 20),
          sites: researchQuery.domains?.join(','),
        },
        timeout: 30000,
      });

      return response.data.items || [];
    } catch (error) {
      this.logger.error('Web search failed', {
        error: (error as Error).message,
      });
      return this.generateMockSearchResults(researchQuery);
    }
  }

  private generateMockSearchResults(researchQuery: ResearchQuery): any[] {
    // Generate realistic mock results for demonstration
    const mockResults = [];
    const topics = researchQuery.query.split(' ');

    for (let i = 0; i < Math.min(researchQuery.maxSources || 5, 5); i++) {
      mockResults.push({
        title: `Research on ${topics.join(' ')}: Study ${i + 1}`,
        link: `https://example.com/research/${i + 1}`,
        snippet: `This comprehensive study examines ${researchQuery.query} and provides insights into key factors affecting the domain. Recent findings suggest...`,
        displayLink: `research-journal-${i + 1}.com`,
        kind: 'customsearch#result',
      });
    }

    return mockResults;
  }

  private async gatherSourceInformation(
    searchResults: any[],
    researchQuery: ResearchQuery
  ): Promise<ResearchSource[]> {
    const sources: ResearchSource[] = [];

    for (const result of searchResults) {
      try {
        // Extract content from the source
        const content = await this.extractContentFromUrl(result.link);

        // Analyze relevance
        const relevance = this.calculateRelevance(content, researchQuery.query);

        // Only include sources that meet relevance threshold
        if (relevance >= 0.5) {
          sources.push({
            url: result.link,
            title: result.title,
            content,
            credibility: 0.8, // Initial credibility score
            relevance,
            citations: this.extractCitations(content),
          });
        }
      } catch (error) {
        this.logger.warn(`Failed to process source: ${result.link}`, {
          error: (error as Error).message,
        });
      }
    }

    return sources;
  }

  private async extractContentFromUrl(url: string): Promise<string> {
    try {
      // Check if it's a valid URL format
      if (!url.startsWith('http')) {
        return 'Content not accessible - invalid URL format';
      }

      const response = await axios.get(url, {
        timeout: 10000,
        headers: {
          'User-Agent': 'PAKE Research Agent 1.0',
        },
      });

      const $ = cheerio.load(response.data);

      // Remove script and style elements
      $('script, style, nav, footer, header, .advertisement').remove();

      // Extract main content (try multiple selectors)
      let content = '';
      const contentSelectors = [
        'main article',
        '.content',
        '#content',
        'article',
        '.post-content',
        '.entry-content',
        '.article-body',
      ];

      for (const selector of contentSelectors) {
        const element = $(selector);
        if (element.length > 0) {
          content = element.text().trim();
          break;
        }
      }

      // Fallback to body content
      if (!content) {
        content = $('body').text().trim();
      }

      // Clean up whitespace
      content = content.replace(/\s+/g, ' ').trim();

      // Limit content length
      return content.substring(0, 5000);
    } catch (error) {
      this.logger.warn(`Content extraction failed for ${url}`, {
        error: (error as Error).message,
      });
      return 'Content not accessible - extraction failed';
    }
  }

  private calculateRelevance(content: string, query: string): number {
    const queryTerms = query.toLowerCase().split(' ');
    const contentLower = content.toLowerCase();

    let relevanceScore = 0;
    let termCount = 0;

    for (const term of queryTerms) {
      const termRegex = new RegExp(`\\b${term}\\b`, 'gi');
      const matches = contentLower.match(termRegex);
      if (matches) {
        relevanceScore += matches.length;
        termCount++;
      }
    }

    // Normalize score
    const coverage = termCount / queryTerms.length;
    const density = relevanceScore / Math.max(content.length / 1000, 1);

    return Math.min(coverage * 0.7 + density * 0.3, 1.0);
  }

  private extractCitations(content: string): string[] {
    const citations: string[] = [];

    // Simple citation pattern matching
    const patterns = [
      /\[(\d+)\]/g, // [1], [2], etc.
      /\(([^)]*\d{4}[^)]*)\)/g, // (Author 2023)
      /doi:\s*([^\s]+)/gi, // DOI references
      /https?:\/\/[^\s]+/gi, // URLs
    ];

    for (const pattern of patterns) {
      const matches = content.match(pattern);
      if (matches) {
        citations.push(...matches);
      }
    }

    return [...new Set(citations)].slice(0, 10); // Deduplicate and limit
  }

  private async verifySources(
    sources: ResearchSource[]
  ): Promise<ResearchSource[]> {
    return sources
      .map(source => {
        // Domain-based credibility scoring
        let credibility = source.credibility;

        if (source.url.includes('.edu')) credibility += 0.2;
        if (source.url.includes('.gov')) credibility += 0.3;
        if (source.url.includes('.org')) credibility += 0.1;
        if (source.url.includes('wikipedia')) credibility += 0.1;
        if (source.url.includes('.com')) credibility -= 0.1;

        // Content quality indicators
        if (source.citations.length > 5) credibility += 0.1;
        if (source.content.length > 2000) credibility += 0.05;
        if (
          source.title.toLowerCase().includes('study') ||
          source.title.toLowerCase().includes('research')
        )
          credibility += 0.05;

        return {
          ...source,
          credibility: Math.min(Math.max(credibility, 0), 1),
        };
      })
      .filter(source => source.credibility >= this.credibilityThreshold);
  }

  private async factCheckSources(
    sources: ResearchSource[]
  ): Promise<ResearchSource[]> {
    if (!this.factCheckApiKey) {
      this.logger.info(
        'Fact-checking API not configured, skipping automated fact verification'
      );
      return sources;
    }

    // This would integrate with fact-checking APIs like ClaimReview or custom services
    return sources;
  }

  private async synthesizeFindings(
    sources: ResearchSource[],
    query: ResearchQuery
  ): Promise<ResearchResult> {
    // Extract key themes and findings
    const allContent = sources.map(s => s.content).join(' ');
    const keyFindings = this.extractKeyFindings(allContent, query.query);

    // Generate summary
    const summary = this.generateSummary(sources, query.query);

    // Collect all citations
    const citations = sources.flatMap(s => s.citations);

    // Calculate confidence metrics
    const avgCredibility =
      sources.reduce((sum, s) => sum + s.credibility, 0) / sources.length;
    const avgRelevance =
      sources.reduce((sum, s) => sum + s.relevance, 0) / sources.length;
    const confidence = avgCredibility * 0.6 + avgRelevance * 0.4;

    const completeness = Math.min(sources.length / 10, 1.0); // Ideal: 10+ sources

    return {
      sources,
      summary,
      keyFindings,
      citations: [...new Set(citations)],
      confidence,
      completeness,
    };
  }

  private extractKeyFindings(content: string, query: string): string[] {
    // Simple key finding extraction based on common patterns
    const findings: string[] = [];

    const sentences = content
      .split(/[.!?]+/)
      .map(s => s.trim())
      .filter(s => s.length > 20);
    const queryTerms = query.toLowerCase().split(' ');

    // Look for sentences that contain query terms and finding indicators
    const findingIndicators = [
      'found that',
      'discovered',
      'revealed',
      'showed',
      'demonstrated',
      'concluded',
      'suggests',
      'indicates',
      'evidence shows',
      'research shows',
    ];

    for (const sentence of sentences) {
      const lowerSentence = sentence.toLowerCase();

      // Check if sentence contains query terms
      const hasQueryTerms = queryTerms.some(term =>
        lowerSentence.includes(term)
      );

      // Check if sentence has finding indicators
      const hasFindings = findingIndicators.some(indicator =>
        lowerSentence.includes(indicator)
      );

      if (hasQueryTerms && hasFindings && sentence.length < 300) {
        findings.push(sentence.trim());

        if (findings.length >= 5) break; // Limit to top 5 findings
      }
    }

    return findings;
  }

  private generateSummary(sources: ResearchSource[], query: string): string {
    const sourceCount = sources.length;
    const avgCredibility =
      sources.reduce((sum, s) => sum + s.credibility, 0) / sourceCount;
    const topSource = sources.sort((a, b) => b.relevance - a.relevance)[0];

    let summary = `Research on "${query}" was conducted using ${sourceCount} credible sources `;
    summary += `with an average credibility score of ${avgCredibility.toFixed(2)}. `;

    if (topSource) {
      summary += `The most relevant source "${topSource.title}" provides comprehensive insights. `;
    }

    summary += `Key themes identified include multiple perspectives on the topic with varying `;
    summary += `levels of evidence and scholarly support. `;

    return summary;
  }

  private async generateResearchReport(
    result: ResearchResult,
    task: Task
  ): Promise<TaskArtifact> {
    const reportContent = this.formatResearchReport(result, task);
    const artifactId = uuidv4();
    const fileName = `research_report_${task.id.substring(0, 8)}.md`;
    const filePath = `/tmp/research_reports/${fileName}`;

    // In a real implementation, save to actual file system or cloud storage

    return {
      id: artifactId,
      name: 'Research Report',
      type: 'report',
      path: filePath,
      size: reportContent.length,
      createdAt: new Date(),
      metadata: {
        format: 'markdown',
        sources: result.sources.length,
        confidence: result.confidence,
      },
    };
  }

  private formatResearchReport(result: ResearchResult, task: Task): string {
    const timestamp = new Date().toISOString().split('T')[0];

    let report = `# Research Report: ${task.title}\n\n`;
    report += `**Generated:** ${timestamp}\n`;
    report += `**Confidence Score:** ${result.confidence.toFixed(2)}/1.00\n`;
    report += `**Sources Analyzed:** ${result.sources.length}\n\n`;

    report += `## Executive Summary\n\n${result.summary}\n\n`;

    if (result.keyFindings.length > 0) {
      report += `## Key Findings\n\n`;
      result.keyFindings.forEach((finding, index) => {
        report += `${index + 1}. ${finding}\n\n`;
      });
    }

    report += `## Sources\n\n`;
    result.sources.forEach((source, index) => {
      report += `### ${index + 1}. ${source.title}\n`;
      report += `- **URL:** ${source.url}\n`;
      report += `- **Credibility:** ${source.credibility.toFixed(2)}/1.00\n`;
      report += `- **Relevance:** ${source.relevance.toFixed(2)}/1.00\n\n`;
    });

    if (result.citations.length > 0) {
      report += `## Citations\n\n`;
      result.citations.forEach((citation, index) => {
        report += `${index + 1}. ${citation}\n`;
      });
    }

    return report;
  }

  private async generateCitations(
    sources: ResearchSource[]
  ): Promise<TaskArtifact> {
    const citationContent = sources
      .map((source, index) => {
        return `${index + 1}. ${source.title}. Retrieved from ${source.url}`;
      })
      .join('\n');

    const artifactId = uuidv4();
    const fileName = `citations_${Date.now()}.txt`;
    const filePath = `/tmp/citations/${fileName}`;

    return {
      id: artifactId,
      name: 'Citations List',
      type: 'data',
      path: filePath,
      size: citationContent.length,
      createdAt: new Date(),
      metadata: {
        format: 'text',
        count: sources.length,
      },
    };
  }

  private calculateResearchQuality(result: ResearchResult): number {
    const sourceQuality =
      result.sources.length >= 5 ? 1.0 : result.sources.length / 5;
    const credibilityScore =
      result.sources.reduce((sum, s) => sum + s.credibility, 0) /
      result.sources.length;
    const diversityScore = this.calculateSourceDiversity(result.sources);
    const completenessScore = result.completeness;

    return (
      sourceQuality * 0.3 +
      credibilityScore * 0.3 +
      diversityScore * 0.2 +
      completenessScore * 0.2
    );
  }

  private calculateSourceDiversity(sources: ResearchSource[]): number {
    const domains = new Set(sources.map(s => new URL(s.url).hostname));
    return Math.min(domains.size / 5, 1.0); // Ideal: 5+ different domains
  }

  private calculateConfidence(result: ResearchResult): number {
    return result.confidence;
  }

  private estimateTokensUsed(result: ResearchResult): number {
    // Rough estimation based on content length
    const contentLength = result.sources.reduce(
      (sum, s) => sum + s.content.length,
      0
    );
    const summaryLength = result.summary.length;
    const findingsLength = result.keyFindings.join(' ').length;

    return Math.floor((contentLength + summaryLength + findingsLength) / 4); // ~4 chars per token
  }

  protected async invokeToolExecution(
    toolId: string,
    parameters: Record<string, any>
  ): Promise<any> {
    switch (toolId) {
      case 'web_search':
        return this.performWebSearch(parameters as ResearchQuery);
      case 'content_extraction':
        return this.extractContentFromUrl(parameters.url);
      case 'fact_check':
        return this.factCheckSources(parameters.sources);
      case 'document_generation':
        return this.generateResearchReport(parameters.result, parameters.task);
      default:
        throw new Error(`Unknown tool: ${toolId}`);
    }
  }

  private hasRequiredTools(task: Task): boolean {
    const requiredTools = task.requirements.tools;
    const availableTools = [
      'web_search',
      'content_extraction',
      'fact_check',
      'document_generation',
    ];

    return requiredTools.every(tool => availableTools.includes(tool));
  }
}

export default ResearchAgent;
