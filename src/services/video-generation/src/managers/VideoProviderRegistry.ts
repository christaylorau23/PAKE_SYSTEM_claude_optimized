/**
 * PAKE System - Video Provider Registry
 * Single Responsibility: Provider management and selection for video generation
 */

import { DIDProvider } from '../providers/DIDProvider';
import { HeyGenProvider } from '../providers/HeyGenProvider';
import { VideoGenerationRequest, VideoGenerationResponse } from '../types';

export interface VideoProvider {
  generateVideo(request: VideoGenerationRequest): Promise<VideoGenerationResponse>;
  isAvailable(): Promise<boolean>;
  getName(): string;
}

export interface VideoProviderRegistry {
  registerProvider(name: string, provider: VideoProvider): void;
  getProvider(name: string): VideoProvider | undefined;
  getAvailableProviders(): VideoProvider[];
  selectBestProvider(request: VideoGenerationRequest): Promise<VideoProvider>;
}

export class VideoProviderRegistryImpl implements VideoProviderRegistry {
  private providers: Map<string, VideoProvider> = new Map();

  constructor() {
    this.initializeDefaultProviders();
  }

  registerProvider(name: string, provider: VideoProvider): void {
    this.providers.set(name, provider);
  }

  getProvider(name: string): VideoProvider | undefined {
    return this.providers.get(name);
  }

  getAvailableProviders(): VideoProvider[] {
    return Array.from(this.providers.values());
  }

  async selectBestProvider(request: VideoGenerationRequest): Promise<VideoProvider> {
    // Check if specific provider is requested
    if (request.provider) {
      const provider = this.getProvider(request.provider);
      if (provider && await provider.isAvailable()) {
        return provider;
      }
    }

    // Select best available provider based on request characteristics
    const availableProviders = await this.getAvailableProviders();
    const available = await Promise.all(
      availableProviders.map(async (provider) => ({
        provider,
        available: await provider.isAvailable()
      }))
    );

    const workingProviders = available
      .filter(p => p.available)
      .map(p => p.provider);

    if (workingProviders.length === 0) {
      throw new Error('No video providers available');
    }

    // Simple selection logic - can be enhanced with more sophisticated algorithms
    return workingProviders[0];
  }

  private initializeDefaultProviders(): void {
    // Initialize default providers
    const didProvider = new DIDProvider();
    const heygenProvider = new HeyGenProvider();

    this.registerProvider('did', didProvider);
    this.registerProvider('heygen', heygenProvider);
  }
}
