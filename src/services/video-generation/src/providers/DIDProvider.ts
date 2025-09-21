/**
 * PAKE System - D-ID Video Generation Provider
 * Handles integration with D-ID API for realistic avatar videos
 */

import axios, { AxiosInstance } from 'axios';
import FormData from 'form-data';
import { EventEmitter } from 'events';
import {
  VideoGenerationRequest,
  VideoGenerationResponse,
  VideoStatus,
  DIDConfig,
  VideoMetadata,
} from '../types';
import { Logger } from '../utils/Logger';

export class DIDProvider extends EventEmitter {
  private apiClient: AxiosInstance;
  private logger: Logger;
  private config: DIDConfig;

  constructor(config: DIDConfig) {
    super();
    this.config = config;
    this.logger = new Logger('DIDProvider');

    this.apiClient = axios.create({
      baseURL: config.endpoint,
      timeout: config.timeout,
      headers: {
        Authorization: `Basic ${config.apiKey}`,
        'Content-Type': 'application/json',
      },
    });

    this.setupRequestInterceptors();
    this.setupResponseInterceptors();
  }

  /**
   * Generate video using D-ID API
   */
  async generateVideo(
    request: VideoGenerationRequest
  ): Promise<VideoGenerationResponse> {
    const timer = this.logger.timer('DID video generation');

    try {
      this.logger.info('Starting D-ID video generation', {
        scriptLength: request.script.length,
        avatarId: request.avatarSettings.avatarId,
        voiceId: request.voiceSettings.voiceId,
      });

      // Create talk request
      const talkRequest = this.buildTalkRequest(request);
      const response = await this.apiClient.post('/talks', talkRequest);

      const videoId = response.data.id;
      this.logger.info('D-ID talk created successfully', { videoId });

      // Poll for completion
      const result = await this.pollForCompletion(videoId);

      timer.end({ videoId, status: result.status });
      this.emit('video-completed', result);

      return result;
    } catch (error) {
      timer.end({ error: error.message });
      this.logger.error('D-ID video generation failed', error);
      throw this.handleProviderError(error);
    }
  }

  /**
   * Get video status from D-ID
   */
  async getVideoStatus(videoId: string): Promise<VideoGenerationResponse> {
    try {
      const response = await this.apiClient.get(`/talks/${videoId}`);
      return this.mapDIDResponse(response.data);
    } catch (error) {
      this.logger.error('Failed to get D-ID video status', error, { videoId });
      throw this.handleProviderError(error);
    }
  }

  /**
   * Cancel video generation
   */
  async cancelVideo(videoId: string): Promise<void> {
    try {
      await this.apiClient.delete(`/talks/${videoId}`);
      this.logger.info('D-ID video generation cancelled', { videoId });
    } catch (error) {
      this.logger.error('Failed to cancel D-ID video', error, { videoId });
      throw this.handleProviderError(error);
    }
  }

  /**
   * Get available presenters/avatars
   */
  async getAvailableAvatars(): Promise<any[]> {
    try {
      const response = await this.apiClient.get('/presenters');
      return response.data.presenters || [];
    } catch (error) {
      this.logger.error('Failed to get D-ID presenters', error);
      throw this.handleProviderError(error);
    }
  }

  /**
   * Get available voices
   */
  async getAvailableVoices(): Promise<any[]> {
    try {
      const response = await this.apiClient.get('/voices');
      return response.data.voices || [];
    } catch (error) {
      this.logger.error('Failed to get D-ID voices', error);
      throw this.handleProviderError(error);
    }
  }

  /**
   * Upload custom avatar image
   */
  async uploadAvatar(imageBuffer: Buffer, filename: string): Promise<string> {
    try {
      const formData = new FormData();
      formData.append('image', imageBuffer, filename);

      const response = await this.apiClient.post('/presenters', formData, {
        headers: {
          ...formData.getHeaders(),
          Authorization: `Basic ${this.config.apiKey}`,
        },
      });

      const presenterId = response.data.id;
      this.logger.info('Custom avatar uploaded to D-ID', {
        presenterId,
        filename,
      });

      return presenterId;
    } catch (error) {
      this.logger.error('Failed to upload avatar to D-ID', error, { filename });
      throw this.handleProviderError(error);
    }
  }

  /**
   * Build D-ID talk request from our standard request
   */
  private buildTalkRequest(request: VideoGenerationRequest): any {
    const { script, voiceSettings, avatarSettings, videoSettings } = request;

    // Build presenter configuration
    const presenter = {
      type: avatarSettings.avatarType === 'uploaded' ? 'image' : 'talk',
      presenter_id: avatarSettings.avatarId,
      ...(avatarSettings.position && {
        crop: {
          type: 'rectangle',
          ...avatarSettings.position,
        },
      }),
    };

    // Build voice configuration
    const voice = {
      type: 'text',
      input: script,
      provider: {
        type: 'microsoft',
        voice_id: voiceSettings.voiceId,
        voice_config: {
          style: voiceSettings.emotion || 'general',
          rate: this.mapSpeedToRate(voiceSettings.speed || 1),
          pitch: voiceSettings.pitch || 0,
        },
      },
    };

    // Build video configuration
    const config = {
      result_format: videoSettings.format,
      fluent: true,
      pad_audio: 0.0,
      ...(videoSettings.resolution && {
        size: this.mapResolutionToSize(videoSettings.resolution),
      }),
      ...(videoSettings.watermark === false && {
        show_watermark: false,
      }),
    };

    // Build background if specified
    const background = this.buildBackgroundConfig(avatarSettings);

    return {
      presenter,
      script: voice,
      config,
      ...(background && { background }),
      ...(request.callbackUrl && {
        webhook: request.callbackUrl,
      }),
    };
  }

  /**
   * Build background configuration
   */
  private buildBackgroundConfig(avatarSettings: any): any {
    if (avatarSettings.backgroundType === 'color') {
      return {
        type: 'color',
        color: avatarSettings.backgroundValue || '#FFFFFF',
      };
    }

    if (avatarSettings.backgroundType === 'image') {
      return {
        type: 'image',
        url: avatarSettings.backgroundValue,
      };
    }

    return null;
  }

  /**
   * Poll D-ID API for video completion
   */
  private async pollForCompletion(
    videoId: string
  ): Promise<VideoGenerationResponse> {
    const maxAttempts = 60; // 10 minutes with 10-second intervals
    const pollInterval = 10000; // 10 seconds
    let attempts = 0;

    while (attempts < maxAttempts) {
      try {
        const response = await this.apiClient.get(`/talks/${videoId}`);
        const mappedResponse = this.mapDIDResponse(response.data);

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
   * Map D-ID response to our standard format
   */
  private mapDIDResponse(didResponse: any): VideoGenerationResponse {
    const status = this.mapDIDStatus(didResponse.status);

    const metadata: VideoMetadata = {
      provider: 'did',
      processingTime:
        didResponse.created_at && didResponse.updated_at
          ? new Date(didResponse.updated_at).getTime() -
            new Date(didResponse.created_at).getTime()
          : undefined,
      dimensions: {
        width: didResponse.config?.size?.split('x')[0] || 512,
        height: didResponse.config?.size?.split('x')[1] || 512,
      },
      audioSettings: {
        voiceId: didResponse.script?.provider?.voice_id || 'unknown',
        language:
          didResponse.script?.provider?.voice_config?.language || 'en-US',
      },
      avatarUsed: {
        avatarId: didResponse.presenter?.presenter_id || 'unknown',
        avatarType: 'default' as any,
        backgroundType: 'default' as any,
      },
    };

    return {
      id: didResponse.id,
      status,
      videoUrl: didResponse.result_url,
      thumbnailUrl: didResponse.thumbnail_url,
      duration: didResponse.audio_duration,
      createdAt: new Date(didResponse.created_at),
      completedAt: didResponse.updated_at
        ? new Date(didResponse.updated_at)
        : undefined,
      error: didResponse.error?.description,
      metadata,
    };
  }

  /**
   * Map D-ID status to our standard status
   */
  private mapDIDStatus(didStatus: string): VideoStatus {
    switch (didStatus.toLowerCase()) {
      case 'created':
      case 'submitted':
        return VideoStatus.PENDING;
      case 'started':
      case 'processing':
        return VideoStatus.PROCESSING;
      case 'done':
      case 'completed':
        return VideoStatus.COMPLETED;
      case 'error':
      case 'failed':
        return VideoStatus.FAILED;
      case 'rejected':
        return VideoStatus.CANCELLED;
      default:
        return VideoStatus.PENDING;
    }
  }

  /**
   * Map speed value to D-ID rate format
   */
  private mapSpeedToRate(speed: number): string {
    if (speed <= 0.5) return 'x-slow';
    if (speed <= 0.75) return 'slow';
    if (speed <= 1.25) return 'medium';
    if (speed <= 1.5) return 'fast';
    return 'x-fast';
  }

  /**
   * Map resolution to D-ID size format
   */
  private mapResolutionToSize(resolution: string): string {
    switch (resolution) {
      case '720p':
        return '1280x720';
      case '1080p':
        return '1920x1080';
      case '4k':
        return '3840x2160';
      default:
        return '1280x720';
    }
  }

  /**
   * Setup request interceptors
   */
  private setupRequestInterceptors(): void {
    this.apiClient.interceptors.request.use(
      config => {
        this.logger.debug('D-ID API request', {
          method: config.method?.toUpperCase(),
          url: config.url,
          hasData: !!config.data,
        });
        return config;
      },
      error => {
        this.logger.error('D-ID API request error', error);
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
        this.logger.debug('D-ID API response', {
          status: response.status,
          url: response.config.url,
        });
        return response;
      },
      error => {
        this.logger.error('D-ID API response error', {
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
      error.message || 'D-ID provider error'
    ) as any;
    providerError.code = error.response?.status || 'PROVIDER_ERROR';
    providerError.statusCode = error.response?.status || 500;
    providerError.provider = 'did';
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
      await this.apiClient.get('/presenters?limit=1');
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
   * Get usage statistics
   */
  async getUsageStats(): Promise<any> {
    try {
      const response = await this.apiClient.get('/credits');
      return {
        creditsRemaining: response.data.remaining_credits,
        creditsUsed: response.data.used_credits,
        billingPeriod: response.data.billing_period,
      };
    } catch (error) {
      this.logger.error('Failed to get D-ID usage stats', error);
      return null;
    }
  }
}

export default DIDProvider;
