/**
 * PAKE System - Video Configuration Manager
 * Single Responsibility: Configuration management for video generation service
 */

import { ServiceConfig } from './types';

export interface VideoConfigManager {
  getConfig(): ServiceConfig;
  updateConfig(config: Partial<ServiceConfig>): void;
  validateConfig(config: ServiceConfig): boolean;
  getProviderConfig(provider: string): any;
}

export class VideoConfigManagerImpl implements VideoConfigManager {
  private config: ServiceConfig;

  constructor(initialConfig?: ServiceConfig) {
    this.config = initialConfig || this.loadDefaultConfig();
  }

  getConfig(): ServiceConfig {
    return { ...this.config };
  }

  updateConfig(config: Partial<ServiceConfig>): void {
    this.config = { ...this.config, ...config };
  }

  validateConfig(config: ServiceConfig): boolean {
    // Validate required fields
    if (!config.maxConcurrentJobs || config.maxConcurrentJobs <= 0) {
      return false;
    }
    if (!config.timeoutMs || config.timeoutMs <= 0) {
      return false;
    }
    return true;
  }

  getProviderConfig(provider: string): any {
    return this.config.providers?.[provider] || {};
  }

  private loadDefaultConfig(): ServiceConfig {
    return {
      maxConcurrentJobs: 5,
      timeoutMs: 300000,
      retryAttempts: 3,
      providers: {
        did: {
          apiKey: process.env.DID_API_KEY || '',
          baseUrl: 'https://api.d-id.com'
        },
        heygen: {
          apiKey: process.env.HEYGEN_API_KEY || '',
          baseUrl: 'https://api.heygen.com'
        }
      },
      storage: {
        type: 'local',
        path: './videos'
      },
      monitoring: {
        enabled: true,
        metricsInterval: 30000
      }
    };
  }
}
