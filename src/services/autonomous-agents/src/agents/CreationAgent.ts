import { BaseAgent } from '@/core/BaseAgent';
import {
  AgentConfig,
  Task,
  TaskResult,
  AgentCapabilities,
  TaskLog,
  TaskArtifact,
} from '@/types/agent';
import { performance } from 'perf_hooks';
import { v4 as uuidv4 } from 'uuid';

interface CreationRequest {
  type: CreationType;
  specifications: CreationSpecs;
  content?: any;
  style?: StyleGuide;
  targetAudience?: string;
  constraints?: CreationConstraints;
}

type CreationType =
  | 'document'
  | 'presentation'
  | 'code'
  | 'design'
  | 'video_script'
  | 'marketing_copy'
  | 'technical_documentation'
  | 'blog_post'
  | 'email'
  | 'report';

interface CreationSpecs {
  title: string;
  description: string;
  requirements: string[];
  format: string;
  length?: number;
  sections?: SectionSpec[];
  features?: string[];
}

interface SectionSpec {
  name: string;
  description: string;
  minLength?: number;
  maxLength?: number;
  required: boolean;
  examples?: string[];
}

interface StyleGuide {
  tone: 'professional' | 'casual' | 'academic' | 'creative' | 'technical';
  voice: 'first_person' | 'third_person' | 'passive' | 'active';
  complexity: 'simple' | 'moderate' | 'complex' | 'expert';
  formatting: Formatting;
  branding?: BrandingGuidelines;
}

interface Formatting {
  headingStyle: 'numbered' | 'bullets' | 'plain';
  listStyle: 'bullets' | 'numbers' | 'dashes';
  codeStyle?: 'inline' | 'blocks' | 'highlighted';
  citations?: boolean;
  tableOfContents?: boolean;
}

interface BrandingGuidelines {
  colors: string[];
  fonts: string[];
  logo?: string;
  tagline?: string;
  keywords: string[];
}

interface CreationConstraints {
  maxLength: number;
  minLength: number;
  excludedContent: string[];
  requiredElements: string[];
  deadline?: Date;
  budget?: number;
}

interface CreationResult {
  type: CreationType;
  content: CreatedContent;
  metadata: ContentMetadata;
  quality: QualityMetrics;
  recommendations: string[];
  alternatives?: AlternativeVersion[];
}

interface CreatedContent {
  title: string;
  body: string;
  sections: ContentSection[];
  attachments?: Attachment[];
  formatting?: FormattingData;
}

interface ContentSection {
  name: string;
  content: string;
  wordCount: number;
  subsections?: ContentSection[];
}

interface Attachment {
  id: string;
  name: string;
  type: string;
  content: any;
  description: string;
}

interface FormattingData {
  styles: Record<string, any>;
  layout: any;
  assets: string[];
}

interface ContentMetadata {
  wordCount: number;
  readingTime: number; // minutes
  complexity: number; // 0-1
  keywords: string[];
  language: string;
  created: Date;
  version: string;
}

interface QualityMetrics {
  clarity: number; // 0-1
  coherence: number; // 0-1
  completeness: number; // 0-1
  accuracy: number; // 0-1
  engagement: number; // 0-1
  overall: number; // 0-1
}

interface AlternativeVersion {
  id: string;
  name: string;
  description: string;
  content: CreatedContent;
  metrics: QualityMetrics;
}

export class CreationAgent extends BaseAgent {
  private templateLibrary: Map<string, any> = new Map();
  private stylePresets: Map<string, StyleGuide> = new Map();
  private maxContentLength = 50000; // characters
  private qualityThreshold = 0.7;

  constructor(config: AgentConfig) {
    super(config);
    this.initializeTemplates();
    this.initializeStylePresets();
    this.status = 'idle';
    this.logger.info('Creation Agent initialized');
  }

  public canHandle(task: Task): boolean {
    return task.type === 'creation' && this.hasCreationCapabilities(task);
  }

  public getCapabilities(): AgentCapabilities {
    return {
      webSearch: true,
      fileOperations: true,
      codeExecution: true,
      apiCalls: true,
      emailSending: false,
      documentCreation: true,
      dataAnalysis: false,
      imageProcessing: true,
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
      // Parse creation request
      const creationRequest = this.parseCreationRequest(task);
      logs.push(
        this.log(
          'info',
          `Starting ${creationRequest.type} creation: ${creationRequest.specifications.title}`
        )
      );

      // Validate requirements
      this.validateCreationRequest(creationRequest);
      logs.push(this.log('info', 'Requirements validation passed'));

      // Research and gather information if needed
      let researchData = {};
      if (this.requiresResearch(creationRequest)) {
        logs.push(this.log('info', 'Gathering background information'));
        researchData = await this.gatherResearchData(creationRequest);
        apiCallsMade += 2;
        totalCost += 0.03;
      }

      // Create content outline
      logs.push(this.log('info', 'Creating content outline'));
      const outline = await this.createContentOutline(
        creationRequest,
        researchData
      );

      // Generate primary content
      logs.push(this.log('info', 'Generating primary content'));
      const primaryContent = await this.generateContent(
        creationRequest,
        outline,
        researchData
      );
      apiCallsMade += 3;
      totalCost += 0.15;

      // Apply styling and formatting
      logs.push(this.log('info', 'Applying styling and formatting'));
      const styledContent = await this.applyStyleAndFormatting(
        primaryContent,
        creationRequest.style
      );

      // Generate alternatives if requested
      const alternatives = [];
      if (task.requirements.outputs.some(o => o.name === 'alternatives')) {
        logs.push(this.log('info', 'Generating alternative versions'));
        const altVersions = await this.generateAlternativeVersions(
          creationRequest,
          outline,
          researchData
        );
        alternatives.push(...altVersions);
        apiCallsMade += altVersions.length;
        totalCost += altVersions.length * 0.1;
      }

      // Quality assessment
      logs.push(this.log('info', 'Performing quality assessment'));
      const qualityMetrics = await this.assessContentQuality(
        styledContent,
        creationRequest
      );

      // Create final result
      const creationResult: CreationResult = {
        type: creationRequest.type,
        content: styledContent,
        metadata: this.generateContentMetadata(styledContent),
        quality: qualityMetrics,
        recommendations: this.generateRecommendations(
          styledContent,
          qualityMetrics
        ),
        alternatives: alternatives.length > 0 ? alternatives : undefined,
      };

      // Generate artifacts
      const mainArtifact = await this.createContentArtifact(
        creationResult,
        task
      );
      artifacts.push(mainArtifact);

      // Create style guide artifact if custom styles were used
      if (creationRequest.style?.branding) {
        const styleArtifact = await this.createStyleGuideArtifact(
          creationRequest.style
        );
        artifacts.push(styleArtifact);
      }

      // Create alternatives artifacts
      for (const alt of alternatives) {
        const altArtifact = await this.createAlternativeArtifact(alt);
        artifacts.push(altArtifact);
      }

      const executionTime = performance.now() - startTime;
      const quality = this.calculateOverallQuality(creationResult);
      const confidence = this.calculateConfidence(creationResult);

      logs.push(
        this.log(
          'info',
          `Content creation completed in ${Math.round(executionTime)}ms`
        )
      );
      logs.push(
        this.log('info', `Generated ${creationResult.content.wordCount} words`)
      );
      logs.push(
        this.log(
          'info',
          `Quality score: ${quality.toFixed(2)}, Confidence: ${confidence.toFixed(2)}`
        )
      );

      return {
        outputs: {
          contentType: creationResult.type,
          title: creationResult.content.title,
          content: creationResult.content.body,
          sections: creationResult.content.sections,
          metadata: creationResult.metadata,
          quality: creationResult.quality,
          recommendations: creationResult.recommendations,
          mainDocument: mainArtifact.path,
          alternatives: alternatives.map(alt => alt.id),
          wordCount: creationResult.content.wordCount,
          readingTime: creationResult.metadata.readingTime,
        },
        metrics: {
          executionTime,
          tokensUsed: this.estimateTokensUsed(creationResult),
          apiCallsMade,
          costIncurred: totalCost,
          toolsUsed: [
            'content_generation',
            'style_formatting',
            'quality_assessment',
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
        this.log(
          'error',
          `Content creation failed: ${(error as Error).message}`
        )
      );
      throw error;
    }
  }

  private parseCreationRequest(task: Task): CreationRequest {
    const creationType = task.requirements.inputs.find(
      i => i.name === 'creationType'
    )?.value as CreationType;
    const specifications = task.requirements.inputs.find(
      i => i.name === 'specifications'
    )?.value;
    const style = task.requirements.inputs.find(i => i.name === 'style')?.value;
    const targetAudience = task.requirements.inputs.find(
      i => i.name === 'targetAudience'
    )?.value;
    const constraints = task.requirements.inputs.find(
      i => i.name === 'constraints'
    )?.value;
    const content = task.requirements.inputs.find(
      i => i.name === 'sourceContent'
    )?.value;

    if (!creationType) {
      throw new Error('Creation type is required');
    }

    if (!specifications) {
      throw new Error('Content specifications are required');
    }

    return {
      type: creationType,
      specifications,
      content,
      style: style || this.getDefaultStyleGuide(creationType),
      targetAudience,
      constraints: {
        maxLength: this.maxContentLength,
        minLength: 100,
        excludedContent: [],
        requiredElements: [],
        ...constraints,
      },
    };
  }

  private validateCreationRequest(request: CreationRequest): void {
    // Validate specifications
    if (!request.specifications.title) {
      throw new Error('Content title is required');
    }

    if (!request.specifications.description) {
      throw new Error('Content description is required');
    }

    // Validate constraints
    if (request.constraints) {
      if (request.constraints.maxLength < request.constraints.minLength) {
        throw new Error('Maximum length cannot be less than minimum length');
      }

      if (
        request.constraints.deadline &&
        request.constraints.deadline < new Date()
      ) {
        throw new Error('Deadline cannot be in the past');
      }
    }

    // Validate sections if specified
    if (request.specifications.sections) {
      for (const section of request.specifications.sections) {
        if (!section.name || !section.description) {
          throw new Error('Section name and description are required');
        }
      }
    }
  }

  private requiresResearch(request: CreationRequest): boolean {
    const researchTypes = ['technical_documentation', 'blog_post', 'report'];
    return (
      researchTypes.includes(request.type) ||
      request.specifications.requirements.some(req =>
        req.toLowerCase().includes('research')
      )
    );
  }

  private async gatherResearchData(request: CreationRequest): Promise<any> {
    const researchData = {
      keywords: this.extractKeywords(request.specifications.description),
      facts: [],
      references: [],
      trends: [],
      statistics: [],
    };

    // Simulate research gathering
    if (request.type === 'technical_documentation') {
      researchData.facts = [
        'Latest industry standards and best practices',
        'Common implementation patterns',
        'Performance considerations',
        'Security requirements',
      ];
    } else if (request.type === 'blog_post') {
      researchData.trends = [
        'Current market trends',
        'Popular discussion topics',
        'Relevant case studies',
        'Expert opinions',
      ];
    } else if (request.type === 'report') {
      researchData.statistics = [
        'Market size and growth rates',
        'Key performance indicators',
        'Comparative analysis data',
        'Industry benchmarks',
      ];
    }

    return researchData;
  }

  private async createContentOutline(
    request: CreationRequest,
    researchData: any
  ): Promise<any> {
    const outline = {
      title: request.specifications.title,
      introduction: {
        purpose: 'Introduce the topic and set expectations',
        keyPoints: [],
        length: 100,
      },
      sections: [],
      conclusion: {
        purpose: 'Summarize key points and provide next steps',
        keyPoints: [],
        length: 100,
      },
    };

    // Generate sections based on specifications
    if (request.specifications.sections) {
      outline.sections = request.specifications.sections.map(section => ({
        name: section.name,
        description: section.description,
        keyPoints: this.generateKeyPoints(section, researchData),
        subsections: [],
        estimatedLength: section.minLength || 200,
      }));
    } else {
      // Create default sections based on content type
      outline.sections = this.generateDefaultSections(
        request.type,
        researchData
      );
    }

    return outline;
  }

  private generateKeyPoints(section: SectionSpec, researchData: any): string[] {
    // Extract relevant information from research data
    const keyPoints = [];

    if (researchData.facts && researchData.facts.length > 0) {
      keyPoints.push(...researchData.facts.slice(0, 2));
    }

    if (section.examples && section.examples.length > 0) {
      keyPoints.push(`Examples: ${section.examples.join(', ')}`);
    }

    keyPoints.push(`Key aspect: ${section.description}`);

    return keyPoints.slice(0, 4); // Limit to 4 key points per section
  }

  private generateDefaultSections(
    type: CreationType,
    researchData: any
  ): any[] {
    const sectionTemplates = {
      document: [
        { name: 'Overview', purpose: 'Provide high-level summary' },
        { name: 'Details', purpose: 'Present main content' },
        { name: 'Implementation', purpose: 'Explain practical application' },
      ],
      presentation: [
        { name: 'Problem Statement', purpose: 'Define the challenge' },
        { name: 'Solution Overview', purpose: 'Present the approach' },
        { name: 'Benefits', purpose: 'Highlight advantages' },
        { name: 'Next Steps', purpose: 'Define action items' },
      ],
      blog_post: [
        { name: 'Hook', purpose: 'Engage reader interest' },
        { name: 'Context', purpose: 'Provide background' },
        { name: 'Main Content', purpose: 'Deliver core message' },
        { name: 'Takeaways', purpose: 'Summarize key points' },
      ],
      technical_documentation: [
        { name: 'Prerequisites', purpose: 'List requirements' },
        { name: 'Setup', purpose: 'Installation and configuration' },
        { name: 'Usage', purpose: 'How to use the system' },
        { name: 'Examples', purpose: 'Practical demonstrations' },
        { name: 'Troubleshooting', purpose: 'Common issues and solutions' },
      ],
    };

    const template = sectionTemplates[type] || sectionTemplates.document;

    return template.map(section => ({
      name: section.name,
      description: section.purpose,
      keyPoints: this.generateSectionKeyPoints(section.name, researchData),
      estimatedLength: 300,
    }));
  }

  private generateSectionKeyPoints(
    sectionName: string,
    researchData: any
  ): string[] {
    const keyPoints = [];

    // Add research-based key points
    if (researchData.facts) keyPoints.push(...researchData.facts.slice(0, 1));
    if (researchData.trends) keyPoints.push(...researchData.trends.slice(0, 1));
    if (researchData.statistics)
      keyPoints.push(...researchData.statistics.slice(0, 1));

    // Add section-specific points
    keyPoints.push(`Core concept for ${sectionName.toLowerCase()}`);
    keyPoints.push(`Important considerations for ${sectionName.toLowerCase()}`);

    return keyPoints.slice(0, 3);
  }

  private async generateContent(
    request: CreationRequest,
    outline: any,
    researchData: any
  ): Promise<CreatedContent> {
    const content: CreatedContent = {
      title: outline.title,
      body: '',
      sections: [],
    };

    // Generate introduction
    const introduction = this.generateIntroduction(
      request,
      outline,
      researchData
    );
    content.body += introduction + '\n\n';

    // Generate sections
    for (const sectionOutline of outline.sections) {
      const section = await this.generateSection(
        sectionOutline,
        request,
        researchData
      );
      content.sections.push(section);
      content.body += `## ${section.name}\n\n${section.content}\n\n`;
    }

    // Generate conclusion
    const conclusion = this.generateConclusion(request, outline, researchData);
    content.body += '## Conclusion\n\n' + conclusion + '\n';

    return content;
  }

  private generateIntroduction(
    request: CreationRequest,
    outline: any,
    researchData: any
  ): string {
    let intro = `# ${outline.title}\n\n`;

    intro += `This ${request.type.replace('_', ' ')} provides comprehensive information about ${request.specifications.title.toLowerCase()}. `;
    intro += `${request.specifications.description} `;

    if (request.targetAudience) {
      intro += `This content is specifically designed for ${request.targetAudience}. `;
    }

    if (outline.sections.length > 0) {
      intro += `We will cover the following key areas: `;
      intro +=
        outline.sections.map((s: any) => s.name.toLowerCase()).join(', ') +
        '. ';
    }

    intro += `Let's begin exploring these important concepts.`;

    return intro;
  }

  private async generateSection(
    sectionOutline: any,
    request: CreationRequest,
    researchData: any
  ): Promise<ContentSection> {
    let sectionContent = `${sectionOutline.description}\n\n`;

    // Add key points
    if (sectionOutline.keyPoints && sectionOutline.keyPoints.length > 0) {
      sectionContent += `Key considerations include:\n\n`;
      sectionOutline.keyPoints.forEach((point: string, index: number) => {
        sectionContent += `${index + 1}. ${point}\n`;
      });
      sectionContent += '\n';
    }

    // Add detailed content based on section type
    sectionContent += this.generateDetailedSectionContent(
      sectionOutline,
      request,
      researchData
    );

    // Add examples if applicable
    if (this.shouldIncludeExamples(request.type, sectionOutline.name)) {
      sectionContent += '\n### Examples\n\n';
      sectionContent += this.generateExamples(sectionOutline, request);
    }

    return {
      name: sectionOutline.name,
      content: sectionContent,
      wordCount: this.countWords(sectionContent),
    };
  }

  private generateDetailedSectionContent(
    sectionOutline: any,
    request: CreationRequest,
    researchData: any
  ): string {
    let content = '';

    // Generate content based on section name and type
    if (sectionOutline.name.toLowerCase().includes('overview')) {
      content += `This section provides a comprehensive overview of the key concepts and principles. `;
      content += `Understanding these fundamentals is crucial for successful implementation and application.`;
    } else if (
      sectionOutline.name.toLowerCase().includes('setup') ||
      sectionOutline.name.toLowerCase().includes('installation')
    ) {
      content += `Follow these steps to set up your environment:\n\n`;
      content += `1. Verify system requirements\n`;
      content += `2. Download necessary components\n`;
      content += `3. Configure settings\n`;
      content += `4. Test the installation\n\n`;
      content += `Each step is important for ensuring proper functionality.`;
    } else if (
      sectionOutline.name.toLowerCase().includes('implementation') ||
      sectionOutline.name.toLowerCase().includes('usage')
    ) {
      content += `The implementation process involves several key steps and considerations. `;
      content += `Best practices recommend following a systematic approach to ensure optimal results. `;
      content += `Common patterns and proven methodologies can significantly improve outcomes.`;
    } else {
      // Generic content generation
      content += `This section addresses important aspects of ${sectionOutline.name.toLowerCase()}. `;
      content += `Multiple factors contribute to success in this area, including proper planning, `;
      content += `attention to detail, and adherence to established guidelines. `;
      content += `Regular review and adjustment help maintain effectiveness over time.`;
    }

    return content;
  }

  private shouldIncludeExamples(
    type: CreationType,
    sectionName: string
  ): boolean {
    const exampleSections = ['usage', 'implementation', 'examples', 'setup'];
    const exampleTypes = ['technical_documentation', 'code', 'document'];

    return (
      exampleTypes.includes(type) ||
      exampleSections.some(sec => sectionName.toLowerCase().includes(sec))
    );
  }

  private generateExamples(
    sectionOutline: any,
    request: CreationRequest
  ): string {
    let examples = '';

    if (request.type === 'technical_documentation' || request.type === 'code') {
      examples += '```\n';
      examples += '// Example implementation\n';
      examples += 'function example() {\n';
      examples +=
        '    // Code specific to ' + sectionOutline.name.toLowerCase() + '\n';
      examples += '    return result;\n';
      examples += '}\n';
      examples += '```\n\n';
    }

    examples += `Example scenario: When working with ${sectionOutline.name.toLowerCase()}, `;
    examples += `consider this practical application that demonstrates the key principles in action.`;

    return examples;
  }

  private generateConclusion(
    request: CreationRequest,
    outline: any,
    researchData: any
  ): string {
    let conclusion = `In summary, this ${request.type.replace('_', ' ')} has covered the essential aspects of ${request.specifications.title.toLowerCase()}. `;

    if (outline.sections.length > 0) {
      conclusion += `We explored ${outline.sections.length} key areas, including `;
      conclusion += outline.sections
        .slice(0, 3)
        .map((s: any) => s.name.toLowerCase())
        .join(', ');
      if (outline.sections.length > 3) {
        conclusion += ` and ${outline.sections.length - 3} other important topics`;
      }
      conclusion += '. ';
    }

    conclusion += `The information presented provides a solid foundation for understanding and implementing these concepts. `;
    conclusion += `For continued success, consider regular review of these materials and stay updated with latest developments in the field.`;

    return conclusion;
  }

  private async applyStyleAndFormatting(
    content: CreatedContent,
    style?: StyleGuide
  ): Promise<CreatedContent> {
    if (!style) {
      return content;
    }

    let formattedBody = content.body;

    // Apply tone adjustments
    if (style.tone === 'professional') {
      formattedBody = this.adjustTone(formattedBody, 'professional');
    } else if (style.tone === 'casual') {
      formattedBody = this.adjustTone(formattedBody, 'casual');
    } else if (style.tone === 'academic') {
      formattedBody = this.adjustTone(formattedBody, 'academic');
    }

    // Apply formatting
    if (style.formatting) {
      formattedBody = this.applyFormatting(formattedBody, style.formatting);
    }

    return {
      ...content,
      body: formattedBody,
      formatting: {
        styles: { tone: style.tone, voice: style.voice },
        layout: style.formatting,
        assets: style.branding?.colors || [],
      },
    };
  }

  private adjustTone(content: string, tone: string): string {
    // Simplified tone adjustment - in practice would use NLP techniques
    switch (tone) {
      case 'professional':
        return content
          .replace(/\b(very|really|super)\b/gi, 'significantly')
          .replace(/\b(awesome|great|cool)\b/gi, 'excellent')
          .replace(/\b(stuff|things)\b/gi, 'elements');
      case 'casual':
        return content
          .replace(/\bsignificantly\b/gi, 'really')
          .replace(/\bexcellent\b/gi, 'great')
          .replace(/\belements\b/gi, 'things');
      case 'academic':
        return content
          .replace(/\b(shows|proves)\b/gi, 'demonstrates')
          .replace(/\b(big|large)\b/gi, 'substantial')
          .replace(/\b(help|helps)\b/gi, 'facilitate');
      default:
        return content;
    }
  }

  private applyFormatting(content: string, formatting: Formatting): string {
    let formatted = content;

    // Apply heading styles
    if (formatting.headingStyle === 'numbered') {
      formatted = this.addNumberedHeadings(formatted);
    }

    // Apply list formatting
    if (formatting.listStyle === 'bullets') {
      formatted = formatted.replace(/^\d+\.\s/gm, '• ');
    } else if (formatting.listStyle === 'dashes') {
      formatted = formatted.replace(/^\d+\.\s/gm, '- ');
    }

    // Add table of contents if requested
    if (formatting.tableOfContents) {
      const toc = this.generateTableOfContents(formatted);
      formatted = toc + '\n\n' + formatted;
    }

    return formatted;
  }

  private addNumberedHeadings(content: string): string {
    const lines = content.split('\n');
    let sectionNumber = 1;
    let subsectionNumber = 1;

    return lines
      .map(line => {
        if (line.startsWith('## ') && !line.includes('Conclusion')) {
          return `## ${sectionNumber++}. ${line.substring(3)}`;
        } else if (line.startsWith('### ')) {
          return `### ${sectionNumber - 1}.${subsectionNumber++} ${line.substring(4)}`;
        }
        return line;
      })
      .join('\n');
  }

  private generateTableOfContents(content: string): string {
    const lines = content.split('\n');
    const headings = lines.filter(line => line.match(/^#+\s/));

    let toc = '## Table of Contents\n\n';
    headings.forEach(heading => {
      const level = heading.match(/^#+/)?.[0].length || 0;
      const title = heading.replace(/^#+\s/, '');
      const indent = '  '.repeat(Math.max(0, level - 2));
      toc += `${indent}- ${title}\n`;
    });

    return toc;
  }

  private async generateAlternativeVersions(
    request: CreationRequest,
    outline: any,
    researchData: any
  ): Promise<AlternativeVersion[]> {
    const alternatives: AlternativeVersion[] = [];

    // Create a shorter version
    const shortVersion = await this.createShortVersion(
      request,
      outline,
      researchData
    );
    alternatives.push({
      id: uuidv4(),
      name: 'Concise Version',
      description: 'A shorter, more focused version emphasizing key points',
      content: shortVersion,
      metrics: await this.assessContentQuality(shortVersion, request),
    });

    // Create a more detailed version if the original wasn't comprehensive
    if (request.constraints && request.constraints.maxLength > 5000) {
      const detailedVersion = await this.createDetailedVersion(
        request,
        outline,
        researchData
      );
      alternatives.push({
        id: uuidv4(),
        name: 'Comprehensive Version',
        description: 'An expanded version with additional details and examples',
        content: detailedVersion,
        metrics: await this.assessContentQuality(detailedVersion, request),
      });
    }

    return alternatives;
  }

  private async createShortVersion(
    request: CreationRequest,
    outline: any,
    researchData: any
  ): Promise<CreatedContent> {
    // Create abbreviated version with key points only
    const shortOutline = {
      ...outline,
      sections: outline.sections
        .slice(0, Math.min(3, outline.sections.length))
        .map((section: any) => ({
          ...section,
          keyPoints: section.keyPoints?.slice(0, 2),
          estimatedLength: Math.floor(section.estimatedLength * 0.6),
        })),
    };

    return await this.generateContent(request, shortOutline, researchData);
  }

  private async createDetailedVersion(
    request: CreationRequest,
    outline: any,
    researchData: any
  ): Promise<CreatedContent> {
    // Create expanded version with more sections and details
    const detailedOutline = {
      ...outline,
      sections: [
        ...outline.sections,
        {
          name: 'Additional Considerations',
          description: 'Extended analysis and additional perspectives',
          keyPoints: [
            'Advanced techniques',
            'Industry best practices',
            'Future considerations',
          ],
          estimatedLength: 400,
        },
        {
          name: 'Frequently Asked Questions',
          description: 'Common questions and detailed answers',
          keyPoints: [
            'Implementation challenges',
            'Performance optimization',
            'Troubleshooting tips',
          ],
          estimatedLength: 500,
        },
      ],
    };

    return await this.generateContent(request, detailedOutline, researchData);
  }

  private async assessContentQuality(
    content: CreatedContent,
    request: CreationRequest
  ): Promise<QualityMetrics> {
    const wordCount = content.wordCount || this.countWords(content.body);
    const targetLength = request.constraints?.maxLength || 2000;

    // Calculate quality metrics
    const clarity = this.assessClarity(content.body);
    const coherence = this.assessCoherence(content.sections);
    const completeness = this.assessCompleteness(
      content,
      request.specifications
    );
    const accuracy = 0.85; // Would use fact-checking in real implementation
    const engagement = this.assessEngagement(content.body);
    const overall =
      (clarity + coherence + completeness + accuracy + engagement) / 5;

    return {
      clarity,
      coherence,
      completeness,
      accuracy,
      engagement,
      overall,
    };
  }

  private assessClarity(content: string): number {
    // Simple clarity assessment based on sentence length and complexity
    const sentences = content.split(/[.!?]+/).filter(s => s.trim().length > 0);
    const avgSentenceLength =
      sentences.reduce((sum, s) => sum + s.split(' ').length, 0) /
      sentences.length;

    // Optimal sentence length is around 15-20 words
    const lengthScore = Math.max(
      0,
      1 - Math.abs(avgSentenceLength - 17.5) / 17.5
    );

    // Check for readability indicators
    const complexWords = content.match(/\b\w{7,}\b/g)?.length || 0;
    const totalWords = this.countWords(content);
    const complexityScore = Math.max(0, 1 - (complexWords / totalWords) * 2);

    return (lengthScore + complexityScore) / 2;
  }

  private assessCoherence(sections: ContentSection[]): number {
    if (sections.length === 0) return 0.5;

    // Check logical flow between sections
    const coherenceScore = 1.0;

    // Penalize sections that are too short or too long relative to others
    const wordCounts = sections.map(s => s.wordCount);
    const avgWordCount =
      wordCounts.reduce((sum, count) => sum + count, 0) / wordCounts.length;

    const variability =
      wordCounts.reduce(
        (sum, count) => sum + Math.abs(count - avgWordCount),
        0
      ) / wordCounts.length;
    const variabilityScore = Math.max(0, 1 - variability / avgWordCount);

    return variabilityScore * 0.8 + 0.2; // Base coherence score
  }

  private assessCompleteness(
    content: CreatedContent,
    specifications: CreationSpecs
  ): number {
    let completenessScore = 0.5; // Base score

    // Check if all required sections are present
    if (specifications.sections) {
      const requiredSections = specifications.sections.filter(s => s.required);
      const presentSections = content.sections.map(s => s.name.toLowerCase());

      const matchedSections = requiredSections.filter(req =>
        presentSections.some(present =>
          present.includes(req.name.toLowerCase())
        )
      );

      completenessScore = matchedSections.length / requiredSections.length;
    } else {
      // Check basic completeness
      const hasIntro =
        content.body.toLowerCase().includes('introduction') ||
        content.body.startsWith('# ');
      const hasConclusion =
        content.body.toLowerCase().includes('conclusion') ||
        content.body.toLowerCase().includes('summary');
      const hasSections = content.sections.length > 0;

      completenessScore =
        (hasIntro ? 0.3 : 0) +
        (hasConclusion ? 0.3 : 0) +
        (hasSections ? 0.4 : 0);
    }

    return completenessScore;
  }

  private assessEngagement(content: string): number {
    let engagementScore = 0.5; // Base score

    // Check for engaging elements
    if (content.includes('?')) engagementScore += 0.1; // Questions engage readers
    if (content.match(/\b(you|your)\b/gi)) engagementScore += 0.1; // Direct address
    if (content.includes('Example')) engagementScore += 0.1; // Examples are engaging
    if (content.match(/\b(imagine|consider|think|remember)\b/gi))
      engagementScore += 0.1; // Engaging language
    if (content.includes('```')) engagementScore += 0.1; // Code examples

    return Math.min(engagementScore, 1.0);
  }

  private generateRecommendations(
    content: CreatedContent,
    quality: QualityMetrics
  ): string[] {
    const recommendations: string[] = [];

    if (quality.clarity < 0.7) {
      recommendations.push(
        'Consider simplifying complex sentences and using more common vocabulary'
      );
    }

    if (quality.coherence < 0.7) {
      recommendations.push(
        'Review section organization and add transitional sentences between sections'
      );
    }

    if (quality.completeness < 0.8) {
      recommendations.push(
        'Add more comprehensive coverage of the specified topics'
      );
    }

    if (quality.engagement < 0.6) {
      recommendations.push(
        'Include more examples, questions, or interactive elements to increase engagement'
      );
    }

    const wordCount = content.wordCount || this.countWords(content.body);
    if (wordCount < 500) {
      recommendations.push(
        'Consider expanding the content with more detailed explanations'
      );
    } else if (wordCount > 5000) {
      recommendations.push(
        'Consider breaking the content into smaller, more digestible sections'
      );
    }

    if (recommendations.length === 0) {
      recommendations.push(
        'Content meets quality standards - consider minor refinements based on audience feedback'
      );
    }

    return recommendations;
  }

  private generateContentMetadata(content: CreatedContent): ContentMetadata {
    const wordCount = this.countWords(content.body);
    const readingTime = Math.ceil(wordCount / 200); // 200 words per minute average

    return {
      wordCount,
      readingTime,
      complexity: this.calculateComplexity(content.body),
      keywords: this.extractKeywords(content.body),
      language: 'en', // Would detect language in real implementation
      created: new Date(),
      version: '1.0',
    };
  }

  private countWords(text: string): number {
    return text
      .trim()
      .split(/\s+/)
      .filter(word => word.length > 0).length;
  }

  private calculateComplexity(text: string): number {
    const words = text.split(/\s+/);
    const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 0);

    if (sentences.length === 0) return 0;

    const avgWordsPerSentence = words.length / sentences.length;
    const complexWords = words.filter(word => word.length > 6).length;
    const complexWordRatio = complexWords / words.length;

    // Simple complexity score based on sentence length and word complexity
    return Math.min((avgWordsPerSentence / 20 + complexWordRatio) / 2, 1);
  }

  private extractKeywords(text: string): string[] {
    const words = text
      .toLowerCase()
      .replace(/[^\w\s]/g, '')
      .split(/\s+/)
      .filter(word => word.length > 3);

    const wordFreq: Record<string, number> = {};
    words.forEach(word => {
      wordFreq[word] = (wordFreq[word] || 0) + 1;
    });

    return Object.entries(wordFreq)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 10)
      .map(([word]) => word);
  }

  // Artifact creation methods
  private async createContentArtifact(
    result: CreationResult,
    task: Task
  ): Promise<TaskArtifact> {
    const content = this.formatFinalContent(result);
    const artifactId = uuidv4();
    const extension = this.getFileExtension(result.type);
    const fileName = `${task.id.substring(0, 8)}_content.${extension}`;
    const filePath = `/tmp/created_content/${fileName}`;

    return {
      id: artifactId,
      name: result.content.title,
      type: 'file',
      path: filePath,
      size: content.length,
      createdAt: new Date(),
      metadata: {
        contentType: result.type,
        wordCount: result.content.wordCount,
        quality: result.quality.overall,
        format: extension,
      },
    };
  }

  private formatFinalContent(result: CreationResult): string {
    let formatted = result.content.body;

    // Add metadata header for certain formats
    if (result.type === 'technical_documentation' || result.type === 'report') {
      const metadata = `---
title: ${result.content.title}
created: ${result.metadata.created.toISOString()}
word_count: ${result.metadata.wordCount}
reading_time: ${result.metadata.readingTime} minutes
quality_score: ${result.quality.overall.toFixed(2)}
---

`;
      formatted = metadata + formatted;
    }

    return formatted;
  }

  private getFileExtension(type: CreationType): string {
    const extensions: Record<CreationType, string> = {
      document: 'md',
      presentation: 'md',
      code: 'js',
      design: 'html',
      video_script: 'txt',
      marketing_copy: 'md',
      technical_documentation: 'md',
      blog_post: 'md',
      email: 'html',
      report: 'md',
    };

    return extensions[type] || 'txt';
  }

  private async createStyleGuideArtifact(
    style: StyleGuide
  ): Promise<TaskArtifact> {
    const styleGuideContent = JSON.stringify(style, null, 2);
    const artifactId = uuidv4();
    const fileName = `style_guide_${Date.now()}.json`;
    const filePath = `/tmp/style_guides/${fileName}`;

    return {
      id: artifactId,
      name: 'Style Guide',
      type: 'data',
      path: filePath,
      size: styleGuideContent.length,
      createdAt: new Date(),
      metadata: {
        format: 'json',
        tone: style.tone,
        complexity: style.complexity,
      },
    };
  }

  private async createAlternativeArtifact(
    alternative: AlternativeVersion
  ): Promise<TaskArtifact> {
    const content = alternative.content.body;
    const artifactId = uuidv4();
    const fileName = `alternative_${alternative.id.substring(0, 8)}.md`;
    const filePath = `/tmp/alternatives/${fileName}`;

    return {
      id: artifactId,
      name: alternative.name,
      type: 'file',
      path: filePath,
      size: content.length,
      createdAt: new Date(),
      metadata: {
        alternativeId: alternative.id,
        wordCount: alternative.content.wordCount,
        quality: alternative.metrics.overall,
      },
    };
  }

  // Helper methods
  private initializeTemplates(): void {
    // Load content templates for different creation types
    // This would typically load from a template database or file system
    this.templateLibrary.set('technical_documentation', {
      structure: [
        'prerequisites',
        'setup',
        'usage',
        'examples',
        'troubleshooting',
      ],
      minSections: 3,
      recommendedLength: 2000,
    });

    this.templateLibrary.set('blog_post', {
      structure: ['hook', 'context', 'main_content', 'takeaways'],
      minSections: 3,
      recommendedLength: 1200,
    });
  }

  private initializeStylePresets(): void {
    // Initialize common style presets
    this.stylePresets.set('professional', {
      tone: 'professional',
      voice: 'third_person',
      complexity: 'moderate',
      formatting: {
        headingStyle: 'plain',
        listStyle: 'bullets',
        citations: true,
        tableOfContents: true,
      },
    });

    this.stylePresets.set('casual', {
      tone: 'casual',
      voice: 'first_person',
      complexity: 'simple',
      formatting: {
        headingStyle: 'plain',
        listStyle: 'dashes',
        citations: false,
        tableOfContents: false,
      },
    });
  }

  private getDefaultStyleGuide(type: CreationType): StyleGuide {
    const styleMap: Record<CreationType, string> = {
      technical_documentation: 'professional',
      report: 'professional',
      blog_post: 'casual',
      email: 'casual',
      marketing_copy: 'casual',
      document: 'professional',
      presentation: 'professional',
      code: 'professional',
      design: 'casual',
      video_script: 'casual',
    };

    const presetName = styleMap[type] || 'professional';
    return (
      this.stylePresets.get(presetName) ||
      this.stylePresets.get('professional')!
    );
  }

  private calculateOverallQuality(result: CreationResult): number {
    return result.quality.overall;
  }

  private calculateConfidence(result: CreationResult): number {
    // Base confidence on quality metrics and completeness
    const qualityConfidence = result.quality.overall;
    const completenessConfidence = result.quality.completeness;
    const consistencyConfidence =
      result.content.sections.length > 0 ? 0.9 : 0.7;

    return (
      qualityConfidence * 0.5 +
      completenessConfidence * 0.3 +
      consistencyConfidence * 0.2
    );
  }

  private estimateTokensUsed(result: CreationResult): number {
    const contentLength = result.content.body.length;
    const metadataLength = JSON.stringify(result.metadata).length;

    return Math.floor((contentLength + metadataLength) / 4); // ~4 chars per token
  }

  protected async invokeToolExecution(
    toolId: string,
    parameters: Record<string, any>
  ): Promise<any> {
    switch (toolId) {
      case 'content_generation':
        return this.generateContent(
          parameters.request,
          parameters.outline,
          parameters.research
        );
      case 'style_formatting':
        return this.applyStyleAndFormatting(
          parameters.content,
          parameters.style
        );
      case 'quality_assessment':
        return this.assessContentQuality(
          parameters.content,
          parameters.request
        );
      default:
        throw new Error(`Unknown tool: ${toolId}`);
    }
  }

  private hasCreationCapabilities(task: Task): boolean {
    const requiredCapabilities = ['documentCreation'];
    const capabilities = this.getCapabilities();

    return requiredCapabilities.every(
      cap => capabilities[cap as keyof AgentCapabilities]
    );
  }
}

export default CreationAgent;
