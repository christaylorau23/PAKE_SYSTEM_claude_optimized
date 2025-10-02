/**
 * PAKE System - Video Storage Manager
 * Single Responsibility: Storage operations for video files
 */

import { VideoGenerationResponse, VideoStatus } from '../types';

export interface VideoStorage {
  storeVideo(videoId: string, videoData: Buffer, metadata: any): Promise<string>;
  retrieveVideo(videoId: string): Promise<Buffer | null>;
  deleteVideo(videoId: string): Promise<boolean>;
  getVideoMetadata(videoId: string): Promise<any>;
  listVideos(): Promise<string[]>;
}

export interface VideoStorageManager {
  storeVideo(videoId: string, videoData: Buffer, metadata: any): Promise<string>;
  retrieveVideo(videoId: string): Promise<Buffer | null>;
  deleteVideo(videoId: string): Promise<boolean>;
  getVideoMetadata(videoId: string): Promise<any>;
  listVideos(): Promise<string[]>;
  getStorageStats(): Promise<StorageStats>;
}

export interface StorageStats {
  totalVideos: number;
  totalSizeBytes: number;
  availableSpaceBytes: number;
  lastCleanup: Date;
}

export class VideoStorageManagerImpl implements VideoStorageManager {
  private storage: VideoStorage;
  private logger: any;

  constructor(storage: VideoStorage, logger: any) {
    this.storage = storage;
    this.logger = logger;
  }

  async storeVideo(videoId: string, videoData: Buffer, metadata: any): Promise<string> {
    try {
      this.logger.info('Storing video', { videoId, size: videoData.length });

      const storagePath = await this.storage.storeVideo(videoId, videoData, {
        ...metadata,
        storedAt: new Date(),
        size: videoData.length
      });

      this.logger.info('Video stored successfully', { videoId, path: storagePath });
      return storagePath;
    } catch (error) {
      this.logger.error('Failed to store video', { videoId, error: error.message });
      throw error;
    }
  }

  async retrieveVideo(videoId: string): Promise<Buffer | null> {
    try {
      this.logger.debug('Retrieving video', { videoId });
      return await this.storage.retrieveVideo(videoId);
    } catch (error) {
      this.logger.error('Failed to retrieve video', { videoId, error: error.message });
      return null;
    }
  }

  async deleteVideo(videoId: string): Promise<boolean> {
    try {
      this.logger.info('Deleting video', { videoId });
      const result = await this.storage.deleteVideo(videoId);
      this.logger.info('Video deleted', { videoId, success: result });
      return result;
    } catch (error) {
      this.logger.error('Failed to delete video', { videoId, error: error.message });
      return false;
    }
  }

  async getVideoMetadata(videoId: string): Promise<any> {
    try {
      return await this.storage.getVideoMetadata(videoId);
    } catch (error) {
      this.logger.error('Failed to get video metadata', { videoId, error: error.message });
      return null;
    }
  }

  async listVideos(): Promise<string[]> {
    try {
      return await this.storage.listVideos();
    } catch (error) {
      this.logger.error('Failed to list videos', { error: error.message });
      return [];
    }
  }

  async getStorageStats(): Promise<StorageStats> {
    try {
      const videos = await this.listVideos();
      let totalSize = 0;

      for (const videoId of videos) {
        const metadata = await this.getVideoMetadata(videoId);
        if (metadata?.size) {
          totalSize += metadata.size;
        }
      }

      return {
        totalVideos: videos.length,
        totalSizeBytes: totalSize,
        availableSpaceBytes: 0, // Would need filesystem info
        lastCleanup: new Date()
      };
    } catch (error) {
      this.logger.error('Failed to get storage stats', { error: error.message });
      return {
        totalVideos: 0,
        totalSizeBytes: 0,
        availableSpaceBytes: 0,
        lastCleanup: new Date()
      };
    }
  }
}
