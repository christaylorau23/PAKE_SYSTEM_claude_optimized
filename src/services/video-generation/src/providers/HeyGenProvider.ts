/**
 * PAKE System - HeyGen Video Generation Provider
 * Handles integration with HeyGen API for professional video creation
 */

import axios, { AxiosInstance } from 'axios';
import FormData from 'form-data';
import { EventEmitter } from 'events';
import {
  VideoGenerationRequest,
  VideoGenerationResponse,
  VideoStatus,
  HeyGenConfig,
  VideoMetadata,
} from '../types';
import { Logger } from '../utils/Logger';

export class HeyGenProvider extends EventEmitter {
  private apiClient: AxiosInstance;
  private logger: Logger;
  private config: HeyGenConfig;

  constructor(config: HeyGenConfig) {
    super();
    this.config = config;
    this.logger = new Logger('HeyGenProvider');

    this.apiClient = axios.create({
      baseURL: config.endpoint,
      timeout: config.timeout,
      headers: {
        'X-API-Key': config.apiKey,
        'Content-Type': 'application/json',
      },
    });

    this.setupRequestInterceptors();
    this.setupResponseInterceptors();
  }

  /**
   * Generate video using HeyGen API
   */
  async generateVideo(
    request: VideoGenerationRequest
  ): Promise<VideoGenerationResponse> {
    const timer = this.logger.timer('HeyGen video generation');

    try {
      this.logger.info('Starting HeyGen video generation', {
        scriptLength: request.script.length,
        avatarId: request.avatarSettings.avatarId,
        voiceId: request.voiceSettings.voiceId,
      });

      // Create video generation request
      const videoRequest = this.buildVideoRequest(request);
      const response = await this.apiClient.post(
        '/v2/video/generate',
        videoRequest
      );

      const videoId = response.data.data.video_id;
      this.logger.info('HeyGen video generation started', { videoId });

      // Poll for completion
      const result = await this.pollForCompletion(videoId);

      timer.end({ videoId, status: result.status });
      this.emit('video-completed', result);

      return result;
    } catch (error) {
      timer.end({ error: error.message });
      this.logger.error('HeyGen video generation failed', error);
      throw this.handleProviderError(error);
    }
  }

  /**
   * Get video status from HeyGen
   */
  async getVideoStatus(videoId: string): Promise<VideoGenerationResponse> {
    try {
      const response = await this.apiClient.get(
        `/v1/video_status.get?video_id=${videoId}`
      );
      return this.mapHeyGenResponse(response.data);
    } catch (error) {
      this.logger.error('Failed to get HeyGen video status', error, {
        videoId,
      });
      throw this.handleProviderError(error);
    }
  }

  /**
   * Cancel video generation (HeyGen doesn't support cancellation, but we track it)
   */
  async cancelVideo(videoId: string): Promise<void> {
    this.logger.warn('HeyGen does not support video cancellation', { videoId });
    // We can't actually cancel on HeyGen, but we track the request as cancelled locally
  }

  /**
   * Get available avatars from HeyGen
   */
  async getAvailableAvatars(): Promise<any[]> {
    try {
      const response = await this.apiClient.get('/v2/avatars');
      return response.data.data.avatars || [];
    } catch (error) {
      this.logger.error('Failed to get HeyGen avatars', error);
      throw this.handleProviderError(error);
    }
  }

  /**
   * Get available voices from HeyGen
   */
  async getAvailableVoices(): Promise<any[]> {
    try {
      const response = await this.apiClient.get('/v2/voices');
      return response.data.data.voices || [];
    } catch (error) {
      this.logger.error('Failed to get HeyGen voices', error);
      throw this.handleProviderError(error);
    }
  }

  /**
   * Get available templates from HeyGen
   */
  async getAvailableTemplates(): Promise<any[]> {
    try {
      const response = await this.apiClient.get('/v2/templates');
      return response.data.data.templates || [];
    } catch (error) {
      this.logger.error('Failed to get HeyGen templates', error);
      throw this.handleProviderError(error);
    }
  }

  /**
   * Upload custom avatar (instant avatar)
   */
  async uploadAvatar(imageBuffer: Buffer, filename: string): Promise<string> {
    try {
      // First, upload the image
      const formData = new FormData();
      formData.append('file', imageBuffer, filename);

      const uploadResponse = await this.apiClient.post(
        '/v1/asset.upload',
        formData,
        {
          headers: {
            ...formData.getHeaders(),
            'X-API-Key': this.config.apiKey,
          },
        }
      );

      const imageUrl = uploadResponse.data.data.url;

      // Create instant avatar
      const avatarResponse = await this.apiClient.post('/v2/avatars/instant', {
        image_url: imageUrl,
      });

      const avatarId = avatarResponse.data.data.avatar_id;
      this.logger.info('Custom avatar created on HeyGen', {
        avatarId,
        filename,
      });

      return avatarId;
    } catch (error) {
      this.logger.error('Failed to upload avatar to HeyGen', error, {
        filename,
      });
      throw this.handleProviderError(error);
    }
  }

  /**
   * Build HeyGen video request from our standard request
   */
  private buildVideoRequest(request: VideoGenerationRequest): any {
    const { script, voiceSettings, avatarSettings, videoSettings } = request;

    // Build video inputs (scenes)
    const videoInputs = [
      {
        character: {
          type: 'avatar',
          avatar_id: avatarSettings.avatarId,
          scale: avatarSettings.position?.scale || 1,
          offset: {
            x: avatarSettings.position?.x || 0,
            y: avatarSettings.position?.y || 0,
          },
        },
        voice: {
          type: 'text',
          input_text: script,
          voice_id: voiceSettings.voiceId,
          speed: voiceSettings.speed || 1,
          emotion: voiceSettings.emotion || 'Neutral',
        },
        background: this.buildBackgroundConfig(avatarSettings),
      },
    ];

    // Build video configuration
    const videoConfig = {
      dimension: this.mapResolutionToDimension(videoSettings.resolution),
      quality: this.mapQualityToHeyGen(videoSettings.quality),
      ratio: videoSettings.aspectRatio,
      ...(request.callbackUrl && {
        callback_id: request.metadata?.callbackId || Date.now().toString(),
        webhook_url: request.callbackUrl,
      }),
    };

    return {
      video_inputs: videoInputs,
      dimension: videoConfig.dimension,
      aspect_ratio: videoConfig.ratio,
      quality: videoConfig.quality,
      ...(this.config.templateId && {
        template_id: this.config.templateId,
      }),
      ...(request.callbackUrl && {
        callback_id: videoConfig.callback_id,
        webhook_url: videoConfig.webhook_url,
      }),
    };
  }

  /**
   * Build background configuration for HeyGen
   */
  private buildBackgroundConfig(avatarSettings: any): any {
    if (avatarSettings.backgroundType === 'color') {
      return {
        type: 'color',
        value: avatarSettings.backgroundValue || '#FFFFFF',
      };
    }

    if (avatarSettings.backgroundType === 'image') {
      return {
        type: 'image',
        url: avatarSettings.backgroundValue,
      };
    }

    // Default background
    return {
      type: 'color',
      value: '#FFFFFF',
    };
  }

  /**
   * Poll HeyGen API for video completion
   */
  private async pollForCompletion(
    videoId: string
  ): Promise<VideoGenerationResponse> {
    const maxAttempts = 120; // 20 minutes with 10-second intervals
    const pollInterval = 10000; // 10 seconds
    let attempts = 0;

    while (attempts < maxAttempts) {
      try {
        const response = await this.apiClient.get(
          `/v1/video_status.get?video_id=${videoId}`
        );
        const mappedResponse = this.mapHeyGenResponse(response.data);

        if (
          mappedResponse.status === VideoStatus.COMPLETED ||
          mappedResponse.status === VideoStatus.FAILED
        ) {
          return mappedResponse;
        }

        // Update processing status
        if (mappedResponse.status === VideoStatus.PROCESSING) {
          this.emit('video-progress', {
            videoId,
            status: VideoStatus.PROCESSING,
            progress: Math.min((attempts / maxAttempts) * 100, 95),
          });
        }

        attempts++;
        await this.delay(pollInterval);
      } catch (error) {
        this.logger.warn('Error during polling, retrying', error, {
          videoId,
          attempt: attempts,
        });
        attempts++;
        await this.delay(pollInterval);
      }
    }

    throw new Error(
      `Video generation timeout after ${(maxAttempts * pollInterval) / 1000} seconds`
    );
  }

  /**
   * Map HeyGen response to our standard format
   */
  private mapHeyGenResponse(heygenResponse: any): VideoGenerationResponse {
    const data = heygenResponse.data;
    const status = this.mapHeyGenStatus(data.status);

    const metadata: VideoMetadata = {
      provider: 'heygen',
      processingTime: data.duration ? data.duration * 1000 : undefined, // Convert to ms
      fileSize: data.file_size,
      dimensions: {
        width: data.width || 1920,
        height: data.height || 1080,
      },
      audioSettings: {
        voiceId: data.voice_id || 'unknown',
        language: data.language || 'en',
      },
      avatarUsed: {
        avatarId: data.avatar_id || 'unknown',
        avatarType: 'default' as any,
        backgroundType: 'default' as any,
      },
      estimatedCost: data.credit_cost,
      qualityScore: data.quality_score,
    };

    return {
      id: data.video_id,
      status,
      videoUrl: data.video_url,
      thumbnailUrl: data.thumbnail_url,
      duration: data.duration,
      createdAt: new Date(data.created_at * 1000), // HeyGen uses timestamps
      completedAt: data.completed_at
        ? new Date(data.completed_at * 1000)
        : undefined,
      error: data.error?.detail,
      metadata,
    };
  }

  /**
   * Map HeyGen status to our standard status
   */
  private mapHeyGenStatus(heygenStatus: string): VideoStatus {
    switch (heygenStatus.toLowerCase()) {
      case 'pending':
      case 'queued':
        return VideoStatus.PENDING;
      case 'processing':
      case 'generating':
        return VideoStatus.PROCESSING;
      case 'completed':
      case 'success':
        return VideoStatus.COMPLETED;
      case 'failed':
      case 'error':
        return VideoStatus.FAILED;
      case 'cancelled':
        return VideoStatus.CANCELLED;
      default:
        return VideoStatus.PENDING;
    }
  }

  /**
   * Map resolution to HeyGen dimension format
   */
  private mapResolutionToDimension(resolution: string): any {
    switch (resolution) {
      case '720p':
        return { width: 1280, height: 720 };
      case '1080p':
        return { width: 1920, height: 1080 };
      case '4k':
        return { width: 3840, height: 2160 };
      default:
        return { width: 1920, height: 1080 };
    }
  }

  /**
   * Map quality setting to HeyGen format
   */
  private mapQualityToHeyGen(quality: string): string {
    switch (quality.toLowerCase()) {
      case 'low':
        return 'draft';
      case 'medium':
        return 'standard';
      case 'high':
        return 'high';
      case 'ultra':
        return 'premium';
      default:
        return 'standard';
    }
  }

  /**
   * Setup request interceptors
   */
  private setupRequestInterceptors(): void {
    this.apiClient.interceptors.request.use(
      config => {
        this.logger.debug('HeyGen API request', {
          method: config.method?.toUpperCase(),
          url: config.url,
          hasData: !!config.data,
        });
        return config;
      },
      error => {
        this.logger.error('HeyGen API request error', error);
        return Promise.reject(error);
      }
    );
  }

  /**
   * Setup response interceptors
   */
  private setupResponseInterceptors(): void {
    this.apiClient.interceptors.response.use(
      response => {
        this.logger.debug('HeyGen API response', {
          status: response.status,
          url: response.config.url,
          hasData: !!response.data,
        });
        return response;
      },
      error => {
        this.logger.error('HeyGen API response error', {
          status: error.response?.status,
          statusText: error.response?.statusText,
          data: error.response?.data,
        });
        return Promise.reject(error);
      }
    );
  }

  /**
   * Handle provider-specific errors
   */
  private handleProviderError(error: any): Error {
    const providerError = new Error(
      error.message || 'HeyGen provider error'
    ) as any;
    providerError.code =
      error.response?.data?.code || error.response?.status || 'PROVIDER_ERROR';
    providerError.statusCode = error.response?.status || 500;
    providerError.provider = 'heygen';
    providerError.details = error.response?.data;

    return providerError;
  }

  /**
   * Utility delay function
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Get provider health status
   */
  async getHealthStatus(): Promise<{
    healthy: boolean;
    latency: number;
    error?: string;
  }> {
    const startTime = Date.now();

    try {
      await this.apiClient.get('/v2/avatars?limit=1');
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
   * Get usage statistics and quota information
   */
  async getUsageStats(): Promise<any> {
    try {
      const response = await this.apiClient.get('/v2/user/remaining_quota');
      return {
        creditsRemaining: response.data.data.remaining_quota,
        creditType: response.data.data.quota_type,
        resetDate: response.data.data.reset_date,
      };
    } catch (error) {
      this.logger.error('Failed to get HeyGen usage stats', error);
      return null;
    }
  }

  /**
   * Generate video from template
   */
  async generateFromTemplate(
    templateId: string,
    variables: Record<string, string>,
    voiceSettings?: any
  ): Promise<VideoGenerationResponse> {
    try {
      const templateRequest = {
        template_id: templateId,
        variables,
        ...(voiceSettings && { voice: voiceSettings }),
      };

      const response = await this.apiClient.post(
        '/v2/video/template',
        templateRequest
      );
      const videoId = response.data.data.video_id;

      this.logger.info('HeyGen template video started', {
        videoId,
        templateId,
      });

      return await this.pollForCompletion(videoId);
    } catch (error) {
      this.logger.error(
        'Failed to generate video from HeyGen template',
        error,
        { templateId }
      );
      throw this.handleProviderError(error);
    }
  }
}

export default HeyGenProvider;
