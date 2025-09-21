/**
 * PAKE System - AI Content Generator
 * Generates social media content using OpenAI and Anthropic AI models
 */

import OpenAI from 'openai';
import Anthropic from '@anthropic-ai/sdk';
import { EventEmitter } from 'events';
import {
  AIContentRequest,
  PostContent,
  SocialPlatform,
  ContentTone,
  ContentLength,
  ContentType,
} from '../types';
import { Logger } from '../utils/Logger';

interface ContentPrompt {
  system: string;
  user: string;
}

interface GeneratedContent {
  text: string;
  hashtags: string[];
  tone: ContentTone;
  platforms: SocialPlatform[];
  confidence: number;
  alternatives?: string[];
}

export class AIContentGenerator extends EventEmitter {
  private openai?: OpenAI;
  private anthropic?: Anthropic;
  private logger: Logger;
  private config: any;

  // Platform-specific content guidelines
  private platformGuidelines = {
    [SocialPlatform.TWITTER]: {
      maxLength: 280,
      bestLength: 150,
      tone: 'conversational and engaging',
      features: ['hashtags', 'mentions', 'threads'],
      audience: 'broad, diverse, news-focused',
    },
    [SocialPlatform.LINKEDIN]: {
      maxLength: 3000,
      bestLength: 1500,
      tone: 'professional and thought-provoking',
      features: ['professional hashtags', 'industry insights'],
      audience: 'professionals, decision-makers',
    },
    [SocialPlatform.INSTAGRAM]: {
      maxLength: 2200,
      bestLength: 1000,
      tone: 'visual-first, lifestyle-oriented',
      features: ['hashtags', 'emojis', 'visual storytelling'],
      audience: 'younger demographics, visual-focused',
    },
    [SocialPlatform.FACEBOOK]: {
      maxLength: 63206,
      bestLength: 500,
      tone: 'community-focused and personal',
      features: ['longer content', 'community engagement'],
      audience: 'diverse age groups, community-oriented',
    },
  };

  constructor(config: any) {
    super();
    this.config = config;
    this.logger = new Logger('AIContentGenerator');

    this.initializeAIClients();
  }

  /**
   * Generate content using AI
   */
  async generateContent(request: AIContentRequest): Promise<GeneratedContent> {
    const timer = this.logger.timer('AI content generation');

    try {
      this.logger.info('Generating AI content', {
        contentType: request.contentType,
        platforms: request.platforms,
        tone: request.tone,
        length: request.length,
      });

      const prompt = this.buildPrompt(request);
      let content: GeneratedContent;

      // Try OpenAI first, fallback to Anthropic
      if (this.openai) {
        content = await this.generateWithOpenAI(prompt, request);
      } else if (this.anthropic) {
        content = await this.generateWithAnthropic(prompt, request);
      } else {
        throw new Error('No AI provider configured');
      }

      // Post-process content
      content = this.postProcessContent(content, request);

      timer.end({
        platform: request.platforms[0],
        contentLength: content.text.length,
        confidence: content.confidence,
      });

      this.emit('content-generated', { request, content });

      return content;
    } catch (error) {
      timer.end({ error: error.message });
      this.logger.error('AI content generation failed', error, {
        prompt: request.prompt.substring(0, 100),
      });
      throw error;
    }
  }

  /**
   * Generate multiple content variations
   */
  async generateVariations(
    request: AIContentRequest,
    count: number = 3
  ): Promise<GeneratedContent[]> {
    const variations: GeneratedContent[] = [];

    try {
      this.logger.info('Generating content variations', {
        count,
        contentType: request.contentType,
      });

      for (let i = 0; i < count; i++) {
        const variationRequest = {
          ...request,
          prompt: `${request.prompt} (Variation ${i + 1}: Create a different approach)`,
        };

        const content = await this.generateContent(variationRequest);
        variations.push(content);

        // Small delay to avoid rate limits
        if (i < count - 1) {
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      }

      this.logger.info('Content variations generated', {
        count: variations.length,
      });
      return variations;
    } catch (error) {
      this.logger.error('Failed to generate content variations', error);
      return variations;
    }
  }

  /**
   * Optimize content for specific platform
   */
  async optimizeForPlatform(
    content: string,
    platform: SocialPlatform
  ): Promise<PostContent> {
    try {
      const guidelines = this.platformGuidelines[platform];

      const optimizationPrompt = `
        Optimize this social media content for ${platform}:
        
        Original content: "${content}"
        
        Platform guidelines:
        - Max length: ${guidelines.maxLength} characters
        - Best length: ${guidelines.bestLength} characters
        - Tone: ${guidelines.tone}
        - Audience: ${guidelines.audience}
        
        Provide:
        1. Optimized text
        2. Relevant hashtags (3-5 for Twitter, 5-10 for Instagram, 3-5 for LinkedIn)
        3. Any platform-specific formatting
        
        Return as JSON: {
          "text": "optimized content",
          "hashtags": ["hashtag1", "hashtag2"],
          "mentions": [],
          "formatting_notes": "any special formatting"
        }
      `;

      let optimizedResult: any;

      if (this.openai) {
        const response = await this.openai.chat.completions.create({
          model: this.config.ai.openai.model || 'gpt-4',
          messages: [
            {
              role: 'system',
              content: 'You are a social media optimization expert.',
            },
            { role: 'user', content: optimizationPrompt },
          ],
          temperature: 0.7,
          max_tokens: 500,
        });

        optimizedResult = JSON.parse(
          response.choices[0].message.content || '{}'
        );
      } else if (this.anthropic) {
        const response = await this.anthropic.messages.create({
          model: this.config.ai.anthropic.model || 'claude-3-sonnet-20240229',
          max_tokens: 500,
          messages: [{ role: 'user', content: optimizationPrompt }],
        });

        optimizedResult = JSON.parse(response.content[0].text || '{}');
      } else {
        throw new Error('No AI provider available for optimization');
      }

      return {
        text: optimizedResult.text || content,
        hashtags: optimizedResult.hashtags || [],
        mentions: optimizedResult.mentions || [],
        links: [],
      };
    } catch (error) {
      this.logger.error('Failed to optimize content for platform', error, {
        platform,
      });

      // Return basic optimization as fallback
      return {
        text: content.substring(0, this.platformGuidelines[platform].maxLength),
        hashtags: [],
        mentions: [],
        links: [],
      };
    }
  }

  /**
   * Generate hashtags for content
   */
  async generateHashtags(
    content: string,
    platform: SocialPlatform,
    count: number = 5
  ): Promise<string[]> {
    try {
      const hashtagPrompt = `
        Generate ${count} relevant hashtags for this ${platform} post:
        
        Content: "${content}"
        
        Requirements:
        - Relevant to the content topic
        - Popular but not overly generic
        - Mix of broad and specific tags
        - Appropriate for ${platform} audience
        - No spaces, proper capitalization
        
        Return only the hashtags as a JSON array (without # symbol):
        ["hashtag1", "hashtag2", "hashtag3"]
      `;

      let hashtags: string[] = [];

      if (this.openai) {
        const response = await this.openai.chat.completions.create({
          model: this.config.ai.openai.model || 'gpt-4',
          messages: [
            {
              role: 'system',
              content: 'You are a social media hashtag expert.',
            },
            { role: 'user', content: hashtagPrompt },
          ],
          temperature: 0.8,
          max_tokens: 200,
        });

        hashtags = JSON.parse(response.choices[0].message.content || '[]');
      } else if (this.anthropic) {
        const response = await this.anthropic.messages.create({
          model: this.config.ai.anthropic.model || 'claude-3-sonnet-20240229',
          max_tokens: 200,
          messages: [{ role: 'user', content: hashtagPrompt }],
        });

        hashtags = JSON.parse(response.content[0].text || '[]');
      }

      // Ensure hashtags don't have # prefix and are valid
      return hashtags
        .map(tag => tag.replace('#', '').trim())
        .filter(tag => tag.length > 0 && tag.length <= 100)
        .slice(0, count);
    } catch (error) {
      this.logger.error('Failed to generate hashtags', error);
      return [];
    }
  }

  /**
   * Analyze content sentiment and appropriateness
   */
  async analyzeContent(content: string): Promise<{
    sentiment: 'positive' | 'neutral' | 'negative';
    appropriateness: number; // 0-100
    topics: string[];
    suggestions: string[];
  }> {
    try {
      const analysisPrompt = `
        Analyze this social media content:
        
        Content: "${content}"
        
        Provide analysis as JSON:
        {
          "sentiment": "positive|neutral|negative",
          "appropriateness": 0-100,
          "topics": ["topic1", "topic2"],
          "suggestions": ["improvement1", "improvement2"]
        }
        
        Consider:
        - Overall tone and sentiment
        - Appropriateness for public social media
        - Main topics/themes
        - Suggestions for improvement
      `;

      if (this.openai) {
        const response = await this.openai.chat.completions.create({
          model: this.config.ai.openai.model || 'gpt-4',
          messages: [
            {
              role: 'system',
              content: 'You are a social media content analyst.',
            },
            { role: 'user', content: analysisPrompt },
          ],
          temperature: 0.3,
          max_tokens: 300,
        });

        return JSON.parse(response.choices[0].message.content || '{}');
      } else if (this.anthropic) {
        const response = await this.anthropic.messages.create({
          model: this.config.ai.anthropic.model || 'claude-3-sonnet-20240229',
          max_tokens: 300,
          messages: [{ role: 'user', content: analysisPrompt }],
        });

        return JSON.parse(response.content[0].text || '{}');
      }

      return {
        sentiment: 'neutral',
        appropriateness: 70,
        topics: [],
        suggestions: [],
      };
    } catch (error) {
      this.logger.error('Failed to analyze content', error);
      return {
        sentiment: 'neutral',
        appropriateness: 70,
        topics: [],
        suggestions: [],
      };
    }
  }

  /**
   * Initialize AI clients
   */
  private initializeAIClients(): void {
    if (this.config.ai?.openai?.apiKey) {
      this.openai = new OpenAI({
        apiKey: this.config.ai.openai.apiKey,
      });
      this.logger.info('OpenAI client initialized');
    }

    if (this.config.ai?.anthropic?.apiKey) {
      this.anthropic = new Anthropic({
        apiKey: this.config.ai.anthropic.apiKey,
      });
      this.logger.info('Anthropic client initialized');
    }

    if (!this.openai && !this.anthropic) {
      this.logger.warn('No AI providers configured');
    }
  }

  /**
   * Build comprehensive prompt for AI generation
   */
  private buildPrompt(request: AIContentRequest): ContentPrompt {
    const platformGuidelines = request.platforms.map(
      p => this.platformGuidelines[p]
    );
    const maxLength = Math.min(...platformGuidelines.map(g => g.maxLength));

    const system = `
      You are an expert social media content creator specializing in ${request.platforms.join(', ')} content.
      
      Your expertise includes:
      - Understanding platform-specific best practices
      - Creating engaging, authentic content
      - Optimizing for audience engagement
      - Following current social media trends
      
      Content Guidelines:
      - Tone: ${request.tone}
      - Length: ${request.length} (max ${maxLength} characters)
      - Type: ${request.contentType}
      - Target audience: ${request.targetAudience || 'general'}
      
      Always create content that is:
      - Authentic and engaging
      - Platform-appropriate
      - Error-free and well-formatted
      - Respectful and inclusive
    `;

    const contextSection = request.context
      ? `\nContext: ${request.context}`
      : '';
    const keywordSection = request.keywords
      ? `\nKeywords to include: ${request.keywords.join(', ')}`
      : '';
    const hashtagInstruction = request.includeHashtags
      ? '\nInclude relevant hashtags.'
      : '';
    const emojiInstruction = request.includeEmojis
      ? '\nUse emojis appropriately to enhance engagement.'
      : '';

    const user = `
      Create ${request.length} social media content for ${request.platforms.join(' and ')}:
      
      Topic/Prompt: ${request.prompt}${contextSection}${keywordSection}
      
      Requirements:
      - Tone: ${request.tone}
      - Content type: ${request.contentType}
      - Make it ${this.getLengthDescription(request.length)}${hashtagInstruction}${emojiInstruction}
      
      Provide the content ready to post, engaging and optimized for the specified platform(s).
    `;

    return { system, user };
  }

  /**
   * Generate content using OpenAI
   */
  private async generateWithOpenAI(
    prompt: ContentPrompt,
    request: AIContentRequest
  ): Promise<GeneratedContent> {
    const response = await this.openai!.chat.completions.create({
      model: this.config.ai.openai.model || 'gpt-4',
      messages: [
        { role: 'system', content: prompt.system },
        { role: 'user', content: prompt.user },
      ],
      temperature: this.getTemperatureForTone(request.tone),
      max_tokens: this.getMaxTokensForLength(request.length),
      presence_penalty: 0.1,
      frequency_penalty: 0.1,
    });

    const content = response.choices[0].message.content || '';

    return {
      text: content,
      hashtags: this.extractHashtags(content),
      tone: request.tone,
      platforms: request.platforms,
      confidence: this.calculateConfidence(response),
    };
  }

  /**
   * Generate content using Anthropic
   */
  private async generateWithAnthropic(
    prompt: ContentPrompt,
    request: AIContentRequest
  ): Promise<GeneratedContent> {
    const response = await this.anthropic!.messages.create({
      model: this.config.ai.anthropic.model || 'claude-3-sonnet-20240229',
      max_tokens: this.getMaxTokensForLength(request.length),
      messages: [
        { role: 'user', content: `${prompt.system}\n\n${prompt.user}` },
      ],
    });

    const content = response.content[0].text || '';

    return {
      text: content,
      hashtags: this.extractHashtags(content),
      tone: request.tone,
      platforms: request.platforms,
      confidence: 85, // Anthropic doesn't provide confidence scores
    };
  }

  /**
   * Post-process generated content
   */
  private postProcessContent(
    content: GeneratedContent,
    request: AIContentRequest
  ): GeneratedContent {
    // Clean up text
    content.text = content.text.trim();

    // Ensure hashtags are properly formatted
    content.hashtags = content.hashtags.map(tag =>
      tag.startsWith('#') ? tag.substring(1) : tag
    );

    // Remove duplicate hashtags
    content.hashtags = [...new Set(content.hashtags)];

    // Limit hashtags based on platform
    const maxHashtags = request.platforms.includes(SocialPlatform.INSTAGRAM)
      ? 10
      : 5;
    content.hashtags = content.hashtags.slice(0, maxHashtags);

    // Validate content length for platforms
    const maxLength = Math.min(
      ...request.platforms.map(p => this.platformGuidelines[p].maxLength)
    );

    if (content.text.length > maxLength) {
      content.text = content.text.substring(0, maxLength - 3) + '...';
    }

    return content;
  }

  /**
   * Extract hashtags from content
   */
  private extractHashtags(content: string): string[] {
    const hashtagRegex = /#\w+/g;
    const matches = content.match(hashtagRegex) || [];
    return matches.map(tag => tag.substring(1)); // Remove # prefix
  }

  /**
   * Get temperature setting based on tone
   */
  private getTemperatureForTone(tone: ContentTone): number {
    switch (tone) {
      case ContentTone.PROFESSIONAL:
        return 0.3;
      case ContentTone.EDUCATIONAL:
        return 0.4;
      case ContentTone.CASUAL:
        return 0.7;
      case ContentTone.HUMOROUS:
        return 0.8;
      case ContentTone.INSPIRATIONAL:
        return 0.6;
      default:
        return 0.5;
    }
  }

  /**
   * Get max tokens based on content length
   */
  private getMaxTokensForLength(length: ContentLength): number {
    switch (length) {
      case ContentLength.SHORT:
        return 150;
      case ContentLength.MEDIUM:
        return 300;
      case ContentLength.LONG:
        return 500;
      default:
        return 300;
    }
  }

  /**
   * Get length description for prompts
   */
  private getLengthDescription(length: ContentLength): string {
    switch (length) {
      case ContentLength.SHORT:
        return 'concise and punchy';
      case ContentLength.MEDIUM:
        return 'moderately detailed';
      case ContentLength.LONG:
        return 'comprehensive and detailed';
      default:
        return 'appropriately sized';
    }
  }

  /**
   * Calculate confidence score from OpenAI response
   */
  private calculateConfidence(response: any): number {
    // This is a simplified confidence calculation
    // In practice, you might use logprobs or other metrics
    const choice = response.choices[0];

    if (choice.finish_reason === 'stop') {
      return 90;
    } else if (choice.finish_reason === 'length') {
      return 75;
    } else {
      return 60;
    }
  }
}

export default AIContentGenerator;
