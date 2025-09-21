/**
 * PAKE System - Twitter/X Platform Provider
 * Handles Twitter API v2 integration for social media automation
 */

import { TwitterApi, TweetV2PostTweetResult, UserV2 } from 'twitter-api-v2';
import { EventEmitter } from 'events';
import FormData from 'form-data';
import {
  SocialMediaPost,
  PostContent,
  PlatformAnalytics,
  SocialPlatform,
  PlatformConfig,
  MediaAsset,
  PostStatus,
} from '../types';
import { Logger } from '../utils/Logger';

export class TwitterProvider extends EventEmitter {
  private client: TwitterApi;
  private readOnlyClient: TwitterApi;
  private logger: Logger;
  private config: PlatformConfig;
  private rateLimitState: Map<string, number> = new Map();

  constructor(config: PlatformConfig) {
    super();
    this.config = config;
    this.logger = new Logger('TwitterProvider');

    this.initializeClients();
  }

  /**
   * Publish post to Twitter
   */
  async publishPost(
    post: SocialMediaPost
  ): Promise<{ success: boolean; platformId?: string; error?: string }> {
    const timer = this.logger.timer('Twitter post publish');

    try {
      this.logger.info('Publishing post to Twitter', {
        postId: post.id,
        hasMedia:
          (post.content.images?.length || 0) +
            (post.content.videos?.length || 0) >
          0,
      });

      // Upload media first if present
      const mediaIds = await this.uploadMedia(post.content);

      // Prepare tweet content
      const tweetContent = this.prepareTweetContent(post.content);

      // Post tweet
      const tweetOptions: any = {
        text: tweetContent.text,
      };

      if (mediaIds.length > 0) {
        tweetOptions.media = { media_ids: mediaIds };
      }

      // Add poll if present
      if (post.content.poll) {
        tweetOptions.poll = {
          options: post.content.poll.options,
          duration_minutes: post.content.poll.duration
            ? post.content.poll.duration * 60
            : 1440, // 24 hours default
        };
      }

      // Add geo location if available
      if (post.metadata.location) {
        tweetOptions.geo = {
          place_id: post.metadata.location,
        };
      }

      const result: TweetV2PostTweetResult =
        await this.client.v2.tweet(tweetOptions);

      timer.end({ tweetId: result.data.id });
      this.emit('post-published', {
        platform: SocialPlatform.TWITTER,
        postId: post.id,
        platformId: result.data.id,
      });

      this.logger.info('Twitter post published successfully', {
        postId: post.id,
        tweetId: result.data.id,
      });

      return {
        success: true,
        platformId: result.data.id,
      };
    } catch (error) {
      timer.end({ error: error.message });
      this.logger.error('Failed to publish Twitter post', error, {
        postId: post.id,
      });

      return {
        success: false,
        error: this.handleTwitterError(error),
      };
    }
  }

  /**
   * Delete post from Twitter
   */
  async deletePost(platformId: string): Promise<boolean> {
    try {
      const result = await this.client.v2.deleteTweet(platformId);

      this.logger.info('Twitter post deleted', { tweetId: platformId });
      this.emit('post-deleted', {
        platform: SocialPlatform.TWITTER,
        platformId,
      });

      return result.data.deleted;
    } catch (error) {
      this.logger.error('Failed to delete Twitter post', error, {
        tweetId: platformId,
      });
      return false;
    }
  }

  /**
   * Get post analytics
   */
  async getPostAnalytics(
    platformId: string
  ): Promise<PlatformAnalytics | null> {
    try {
      // Get tweet metrics
      const tweet = await this.readOnlyClient.v2.singleTweet(platformId, {
        'tweet.fields': [
          'public_metrics',
          'non_public_metrics',
          'organic_metrics',
          'promoted_metrics',
        ],
        expansions: ['author_id'],
      });

      if (!tweet.data) {
        return null;
      }

      const metrics = tweet.data.public_metrics;
      const nonPublicMetrics = tweet.data.non_public_metrics;
      const organicMetrics = tweet.data.organic_metrics;

      const analytics: PlatformAnalytics = {
        platform: SocialPlatform.TWITTER,
        postId: platformId,
        metrics: {
          impressions:
            organicMetrics?.impression_count || metrics?.impression_count || 0,
          reach:
            nonPublicMetrics?.impression_count ||
            metrics?.impression_count ||
            0,
          engagements: this.calculateEngagements(metrics),
          likes: metrics?.like_count || 0,
          shares: metrics?.retweet_count || 0,
          comments: metrics?.reply_count || 0,
          clicks: nonPublicMetrics?.url_link_clicks || 0,
          profileVisits: nonPublicMetrics?.user_profile_clicks || 0,
        },
        performance: this.calculatePerformanceScore(metrics, organicMetrics),
      };

      return analytics;
    } catch (error) {
      this.logger.error('Failed to get Twitter post analytics', error, {
        tweetId: platformId,
      });
      return null;
    }
  }

  /**
   * Get account analytics
   */
  async getAccountAnalytics(): Promise<any> {
    try {
      const user = await this.readOnlyClient.v2.me({
        'user.fields': ['public_metrics'],
      });

      return {
        platform: SocialPlatform.TWITTER,
        followers: user.data.public_metrics?.followers_count || 0,
        following: user.data.public_metrics?.following_count || 0,
        tweets: user.data.public_metrics?.tweet_count || 0,
        listed: user.data.public_metrics?.listed_count || 0,
      };
    } catch (error) {
      this.logger.error('Failed to get Twitter account analytics', error);
      return null;
    }
  }

  /**
   * Search for mentions
   */
  async searchMentions(username: string, sinceId?: string): Promise<any[]> {
    try {
      const query = `@${username} -is:retweet`;

      const tweets = await this.readOnlyClient.v2.search(query, {
        'tweet.fields': [
          'created_at',
          'author_id',
          'public_metrics',
          'context_annotations',
        ],
        'user.fields': ['username', 'name', 'profile_image_url'],
        expansions: ['author_id'],
        max_results: 100,
        ...(sinceId && { since_id: sinceId }),
      });

      return tweets.data?.data || [];
    } catch (error) {
      this.logger.error('Failed to search Twitter mentions', error, {
        username,
      });
      return [];
    }
  }

  /**
   * Get trending hashtags
   */
  async getTrendingHashtags(location?: string): Promise<string[]> {
    try {
      // Twitter API v2 doesn't have trends endpoint yet, using search for popular hashtags
      const trends = await this.readOnlyClient.v2.search('#', {
        'tweet.fields': ['public_metrics'],
        max_results: 100,
        sort_order: 'relevancy',
      });

      const hashtags = new Set<string>();

      trends.data?.data?.forEach(tweet => {
        const hashtagRegex = /#\w+/g;
        const matches = tweet.text.match(hashtagRegex);
        if (matches) {
          matches.forEach(hashtag => hashtags.add(hashtag.toLowerCase()));
        }
      });

      return Array.from(hashtags).slice(0, 20);
    } catch (error) {
      this.logger.error('Failed to get Twitter trending hashtags', error);
      return [];
    }
  }

  /**
   * Check platform health
   */
  async checkHealth(): Promise<{
    healthy: boolean;
    latency: number;
    error?: string;
  }> {
    const startTime = Date.now();

    try {
      await this.readOnlyClient.v2.me();

      return {
        healthy: true,
        latency: Date.now() - startTime,
      };
    } catch (error) {
      return {
        healthy: false,
        latency: Date.now() - startTime,
        error: error.message,
      };
    }
  }

  /**
   * Get platform limits
   */
  getPlatformLimits(): any {
    return {
      maxTextLength: 280,
      maxImages: 4,
      maxVideos: 1,
      maxHashtags: 2, // Recommended
      maxMentions: 10, // Recommended
      dailyPostLimit: 300,
      hourlyPostLimit: 300,
      imageFormats: ['jpg', 'jpeg', 'png', 'gif', 'webp'],
      videoFormats: ['mp4', 'mov'],
      maxImageSize: 5 * 1024 * 1024, // 5MB
      maxVideoSize: 512 * 1024 * 1024, // 512MB
      maxVideoDuration: 140, // seconds
    };
  }

  /**
   * Initialize Twitter API clients
   */
  private initializeClients(): void {
    const { credentials } = this.config;

    if (!credentials.apiKey || !credentials.apiSecret) {
      throw new Error('Twitter API key and secret are required');
    }

    // Initialize bearer token client for read operations
    if (credentials.accessToken) {
      this.readOnlyClient = new TwitterApi(credentials.accessToken);
    }

    // Initialize OAuth 1.0a client for write operations
    if (credentials.accessToken && credentials.accessTokenSecret) {
      this.client = new TwitterApi({
        appKey: credentials.apiKey,
        appSecret: credentials.apiSecret,
        accessToken: credentials.accessToken,
        accessSecret: credentials.accessTokenSecret,
      });
    } else {
      throw new Error(
        'Twitter access token and secret are required for posting'
      );
    }

    this.logger.info('Twitter API clients initialized');
  }

  /**
   * Upload media to Twitter
   */
  private async uploadMedia(content: PostContent): Promise<string[]> {
    const mediaIds: string[] = [];

    try {
      // Upload images
      if (content.images && content.images.length > 0) {
        for (const image of content.images.slice(0, 4)) {
          // Max 4 images
          const mediaId = await this.uploadImageMedia(image);
          if (mediaId) {
            mediaIds.push(mediaId);
          }
        }
      }

      // Upload video (only 1 video allowed)
      if (content.videos && content.videos.length > 0) {
        const video = content.videos[0];
        const mediaId = await this.uploadVideoMedia(video);
        if (mediaId) {
          mediaIds.push(mediaId);
        }
      }

      return mediaIds;
    } catch (error) {
      this.logger.error('Failed to upload media to Twitter', error);
      return [];
    }
  }

  /**
   * Upload image media
   */
  private async uploadImageMedia(image: MediaAsset): Promise<string | null> {
    try {
      // Download image buffer
      const response = await fetch(image.url);
      const buffer = await response.arrayBuffer();

      const mediaId = await this.client.v1.uploadMedia(Buffer.from(buffer), {
        mimeType: this.getMimeType(image.url),
        additionalOwners: [],
        ...(image.altText && { altText: { text: image.altText } }),
      });

      this.logger.debug('Twitter image uploaded', {
        mediaId,
        imageId: image.id,
      });
      return mediaId;
    } catch (error) {
      this.logger.error('Failed to upload Twitter image', error, {
        imageId: image.id,
      });
      return null;
    }
  }

  /**
   * Upload video media
   */
  private async uploadVideoMedia(video: MediaAsset): Promise<string | null> {
    try {
      // Download video buffer
      const response = await fetch(video.url);
      const buffer = await response.arrayBuffer();

      const mediaId = await this.client.v1.uploadMedia(Buffer.from(buffer), {
        mimeType: this.getMimeType(video.url),
        type: 'video',
      });

      this.logger.debug('Twitter video uploaded', {
        mediaId,
        videoId: video.id,
      });
      return mediaId;
    } catch (error) {
      this.logger.error('Failed to upload Twitter video', error, {
        videoId: video.id,
      });
      return null;
    }
  }

  /**
   * Prepare tweet content with platform-specific formatting
   */
  private prepareTweetContent(content: PostContent): { text: string } {
    let text = content.text;

    // Add hashtags if present
    if (content.hashtags && content.hashtags.length > 0) {
      const hashtagText = content.hashtags
        .slice(0, 2) // Limit to 2 hashtags for better engagement
        .map(tag => (tag.startsWith('#') ? tag : `#${tag}`))
        .join(' ');
      text += ` ${hashtagText}`;
    }

    // Ensure text doesn't exceed Twitter's limit
    if (text.length > 280) {
      text = text.substring(0, 277) + '...';
    }

    return { text };
  }

  /**
   * Calculate total engagements from Twitter metrics
   */
  private calculateEngagements(metrics: any): number {
    if (!metrics) return 0;

    return (
      (metrics.like_count || 0) +
      (metrics.retweet_count || 0) +
      (metrics.reply_count || 0) +
      (metrics.quote_count || 0)
    );
  }

  /**
   * Calculate performance score for a tweet
   */
  private calculatePerformanceScore(
    publicMetrics: any,
    organicMetrics: any
  ): any {
    if (!publicMetrics) {
      return { score: 0, category: 'poor', factors: {} };
    }

    const engagements = this.calculateEngagements(publicMetrics);
    const impressions =
      organicMetrics?.impression_count || publicMetrics.impression_count || 1;
    const engagementRate = (engagements / impressions) * 100;

    let score = 0;
    let category = 'poor';

    // Score based on engagement rate benchmarks
    if (engagementRate >= 3) {
      score = 90 + Math.min(10, (engagementRate - 3) * 2);
      category = 'excellent';
    } else if (engagementRate >= 1.5) {
      score = 70 + ((engagementRate - 1.5) / 1.5) * 20;
      category = 'good';
    } else if (engagementRate >= 0.5) {
      score = 40 + ((engagementRate - 0.5) / 1) * 30;
      category = 'fair';
    } else {
      score = engagementRate * 80; // 0-40 range
      category = 'poor';
    }

    return {
      score: Math.round(score),
      category,
      factors: {
        timing: this.calculateTimingScore(),
        content: this.calculateContentScore(publicMetrics),
        engagement: Math.round(engagementRate * 20), // 0-100 scale
        reach: Math.round(Math.min(100, (impressions / 1000) * 10)), // Reach score
      },
    };
  }

  /**
   * Calculate timing score (placeholder - would need historical data)
   */
  private calculateTimingScore(): number {
    const hour = new Date().getHours();

    // Best posting times for Twitter (general guidelines)
    if (
      (hour >= 9 && hour <= 10) ||
      (hour >= 12 && hour <= 15) ||
      (hour >= 17 && hour <= 18)
    ) {
      return 85;
    } else if ((hour >= 8 && hour <= 11) || (hour >= 16 && hour <= 19)) {
      return 70;
    } else {
      return 45;
    }
  }

  /**
   * Calculate content quality score based on metrics
   */
  private calculateContentScore(metrics: any): number {
    if (!metrics) return 50;

    const likes = metrics.like_count || 0;
    const retweets = metrics.retweet_count || 0;
    const replies = metrics.reply_count || 0;

    // Higher ratio of likes to total engagements suggests good content
    const totalEngagements = likes + retweets + replies;
    if (totalEngagements === 0) return 50;

    const likeRatio = likes / totalEngagements;
    const retweetRatio = retweets / totalEngagements;

    // Good content typically has higher like ratio
    return Math.round(50 + likeRatio * 30 + retweetRatio * 20);
  }

  /**
   * Get MIME type from URL
   */
  private getMimeType(url: string): string {
    const ext = url.split('.').pop()?.toLowerCase();

    switch (ext) {
      case 'jpg':
      case 'jpeg':
        return 'image/jpeg';
      case 'png':
        return 'image/png';
      case 'gif':
        return 'image/gif';
      case 'webp':
        return 'image/webp';
      case 'mp4':
        return 'video/mp4';
      case 'mov':
        return 'video/quicktime';
      default:
        return 'application/octet-stream';
    }
  }

  /**
   * Handle Twitter API errors
   */
  private handleTwitterError(error: any): string {
    if (error.code === 429) {
      return 'Rate limit exceeded. Please try again later.';
    }

    if (error.code === 401) {
      return 'Authentication failed. Check API credentials.';
    }

    if (error.code === 403) {
      return 'Forbidden. Check account permissions.';
    }

    if (error.data?.errors) {
      return error.data.errors.map((e: any) => e.message).join('; ');
    }

    return error.message || 'Unknown Twitter API error';
  }
}

export default TwitterProvider;
