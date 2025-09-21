/**
 * PAKE System - Video Generation Storage Manager
 * Handles video file storage across multiple providers (local, AWS S3, MinIO)
 */

import fs from 'fs';
import path from 'path';
import { v4 as uuidv4 } from 'uuid';
import AWS from 'aws-sdk';
import * as Minio from 'minio';
import axios from 'axios';
import { EventEmitter } from 'events';
import { StorageConfig, UploadedAsset } from '../types';
import { Logger } from '../utils/Logger';

export class StorageManager extends EventEmitter {
  private logger: Logger;
  private config: StorageConfig;
  private s3?: AWS.S3;
  private minio?: Minio.Client;

  constructor(config: StorageConfig) {
    super();
    this.config = config;
    this.logger = new Logger('StorageManager');

    this.initializeStorage();
  }

  /**
   * Store video file and return access URL
   */
  async storeVideo(
    videoBuffer: Buffer,
    filename: string,
    metadata?: Record<string, any>
  ): Promise<UploadedAsset> {
    const timer = this.logger.timer('Video storage');
    const assetId = uuidv4();
    const sanitizedFilename = this.sanitizeFilename(filename);
    const finalFilename = `${assetId}-${sanitizedFilename}`;

    try {
      this.logger.info('Starting video storage', {
        filename: finalFilename,
        size: videoBuffer.length,
        provider: this.config.provider,
      });

      let asset: UploadedAsset;

      switch (this.config.provider) {
        case 'local':
          asset = await this.storeLocal(videoBuffer, finalFilename, metadata);
          break;
        case 'aws':
          asset = await this.storeAWS(videoBuffer, finalFilename, metadata);
          break;
        case 'minio':
          asset = await this.storeMinio(videoBuffer, finalFilename, metadata);
          break;
        default:
          throw new Error(
            `Unsupported storage provider: ${this.config.provider}`
          );
      }

      timer.end({ assetId, provider: this.config.provider });
      this.emit('video-stored', asset);

      return asset;
    } catch (error) {
      timer.end({ error: error.message });
      this.logger.error('Failed to store video', error, {
        filename: finalFilename,
      });
      throw error;
    }
  }

  /**
   * Store thumbnail image
   */
  async storeThumbnail(
    imageBuffer: Buffer,
    videoId: string,
    metadata?: Record<string, any>
  ): Promise<UploadedAsset> {
    const thumbnailFilename = `thumbnail-${videoId}.jpg`;
    return this.storeVideo(imageBuffer, thumbnailFilename, {
      ...metadata,
      type: 'thumbnail',
      videoId,
    });
  }

  /**
   * Download file from URL and store it
   */
  async storeFromUrl(
    url: string,
    filename: string,
    metadata?: Record<string, any>
  ): Promise<UploadedAsset> {
    const timer = this.logger.timer('Download and store from URL');

    try {
      this.logger.info('Downloading file from URL', { url, filename });

      const response = await axios.get(url, {
        responseType: 'arraybuffer',
        timeout: 300000, // 5 minutes timeout for large video downloads
        maxContentLength: this.config.maxFileSize,
      });

      const buffer = Buffer.from(response.data);

      timer.end({ downloadedSize: buffer.length });

      return await this.storeVideo(buffer, filename, {
        ...metadata,
        originalUrl: url,
        downloadedAt: new Date(),
      });
    } catch (error) {
      timer.end({ error: error.message });
      this.logger.error('Failed to download and store from URL', error, {
        url,
        filename,
      });
      throw error;
    }
  }

  /**
   * Get file stream for local files
   */
  getFileStream(assetId: string): fs.ReadStream | null {
    if (this.config.provider !== 'local') {
      this.logger.warn('File streams only available for local storage', {
        assetId,
      });
      return null;
    }

    try {
      const filePath = path.join(this.config.uploadPath, `${assetId}*`);
      // Note: This is simplified - in practice you'd need to find the exact filename
      return fs.createReadStream(filePath);
    } catch (error) {
      this.logger.error('Failed to create file stream', error, { assetId });
      return null;
    }
  }

  /**
   * Delete stored file
   */
  async deleteFile(assetId: string): Promise<boolean> {
    try {
      switch (this.config.provider) {
        case 'local':
          return await this.deleteLocal(assetId);
        case 'aws':
          return await this.deleteAWS(assetId);
        case 'minio':
          return await this.deleteMinio(assetId);
        default:
          throw new Error(
            `Unsupported storage provider: ${this.config.provider}`
          );
      }
    } catch (error) {
      this.logger.error('Failed to delete file', error, { assetId });
      return false;
    }
  }

  /**
   * Get file information
   */
  async getFileInfo(assetId: string): Promise<any> {
    try {
      switch (this.config.provider) {
        case 'local':
          return await this.getLocalFileInfo(assetId);
        case 'aws':
          return await this.getAWSFileInfo(assetId);
        case 'minio':
          return await this.getMinioFileInfo(assetId);
        default:
          throw new Error(
            `Unsupported storage provider: ${this.config.provider}`
          );
      }
    } catch (error) {
      this.logger.error('Failed to get file info', error, { assetId });
      return null;
    }
  }

  /**
   * Clean up expired files
   */
  async cleanupExpiredFiles(): Promise<number> {
    const timer = this.logger.timer('Cleanup expired files');
    const cleanedCount = 0;

    try {
      // Implementation depends on how you track expiration
      // This is a placeholder for the cleanup logic
      this.logger.info('Starting cleanup of expired files');

      timer.end({ cleanedCount });
      return cleanedCount;
    } catch (error) {
      timer.end({ error: error.message });
      this.logger.error('Failed to cleanup expired files', error);
      return 0;
    }
  }

  /**
   * Store file locally
   */
  private async storeLocal(
    buffer: Buffer,
    filename: string,
    metadata?: Record<string, any>
  ): Promise<UploadedAsset> {
    const uploadPath = this.config.uploadPath;

    // Ensure upload directory exists
    if (!fs.existsSync(uploadPath)) {
      fs.mkdirSync(uploadPath, { recursive: true });
    }

    const filePath = path.join(uploadPath, filename);

    // Write file
    fs.writeFileSync(filePath, buffer);

    // Generate access URL (assuming local server serves files)
    const baseUrl = process.env.PUBLIC_BASE_URL || 'http://localhost:9001';
    const url = `${baseUrl}/files/${filename}`;

    return {
      id: filename.split('-')[0], // Extract UUID
      filename,
      originalName: metadata?.originalName || filename,
      mimeType: this.getMimeType(filename),
      size: buffer.length,
      url,
      uploadedAt: new Date(),
      metadata: metadata || {},
    };
  }

  /**
   * Store file in AWS S3
   */
  private async storeAWS(
    buffer: Buffer,
    filename: string,
    metadata?: Record<string, any>
  ): Promise<UploadedAsset> {
    if (!this.s3) {
      throw new Error('AWS S3 not configured');
    }

    const params = {
      Bucket: this.config.bucket!,
      Key: `${this.config.uploadPath}/${filename}`,
      Body: buffer,
      ContentType: this.getMimeType(filename),
      Metadata: this.serializeMetadata(metadata || {}),
    };

    const result = await this.s3.upload(params).promise();

    return {
      id: filename.split('-')[0],
      filename,
      originalName: metadata?.originalName || filename,
      mimeType: this.getMimeType(filename),
      size: buffer.length,
      url: result.Location,
      uploadedAt: new Date(),
      metadata: metadata || {},
    };
  }

  /**
   * Store file in MinIO
   */
  private async storeMinio(
    buffer: Buffer,
    filename: string,
    metadata?: Record<string, any>
  ): Promise<UploadedAsset> {
    if (!this.minio) {
      throw new Error('MinIO not configured');
    }

    const objectName = `${this.config.uploadPath}/${filename}`;

    await this.minio.putObject(
      this.config.bucket!,
      objectName,
      buffer,
      buffer.length,
      {
        'Content-Type': this.getMimeType(filename),
        'x-amz-meta-uploaded-at': new Date().toISOString(),
        ...this.serializeMetadata(metadata || {}),
      }
    );

    // Generate presigned URL for access
    const url = await this.minio.presignedGetObject(
      this.config.bucket!,
      objectName,
      24 * 60 * 60 // 24 hours
    );

    return {
      id: filename.split('-')[0],
      filename,
      originalName: metadata?.originalName || filename,
      mimeType: this.getMimeType(filename),
      size: buffer.length,
      url,
      uploadedAt: new Date(),
      expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000), // 24 hours
      metadata: metadata || {},
    };
  }

  /**
   * Delete local file
   */
  private async deleteLocal(assetId: string): Promise<boolean> {
    try {
      const uploadPath = this.config.uploadPath;
      const files = fs.readdirSync(uploadPath);
      const targetFile = files.find(file => file.startsWith(assetId));

      if (targetFile) {
        fs.unlinkSync(path.join(uploadPath, targetFile));
        this.logger.info('Local file deleted', {
          assetId,
          filename: targetFile,
        });
        return true;
      }

      return false;
    } catch (error) {
      this.logger.error('Failed to delete local file', error, { assetId });
      return false;
    }
  }

  /**
   * Delete AWS S3 file
   */
  private async deleteAWS(assetId: string): Promise<boolean> {
    if (!this.s3) return false;

    try {
      // List objects to find the file
      const listParams = {
        Bucket: this.config.bucket!,
        Prefix: `${this.config.uploadPath}/${assetId}`,
      };

      const objects = await this.s3.listObjectsV2(listParams).promise();

      if (objects.Contents && objects.Contents.length > 0) {
        const deleteParams = {
          Bucket: this.config.bucket!,
          Key: objects.Contents[0].Key!,
        };

        await this.s3.deleteObject(deleteParams).promise();
        this.logger.info('AWS S3 file deleted', {
          assetId,
          key: objects.Contents[0].Key,
        });
        return true;
      }

      return false;
    } catch (error) {
      this.logger.error('Failed to delete AWS S3 file', error, { assetId });
      return false;
    }
  }

  /**
   * Delete MinIO file
   */
  private async deleteMinio(assetId: string): Promise<boolean> {
    if (!this.minio) return false;

    try {
      const objectName = `${this.config.uploadPath}/${assetId}`;
      await this.minio.removeObject(this.config.bucket!, objectName);
      this.logger.info('MinIO file deleted', { assetId, objectName });
      return true;
    } catch (error) {
      this.logger.error('Failed to delete MinIO file', error, { assetId });
      return false;
    }
  }

  /**
   * Initialize storage provider
   */
  private initializeStorage(): void {
    switch (this.config.provider) {
      case 'local':
        this.initializeLocal();
        break;
      case 'aws':
        this.initializeAWS();
        break;
      case 'minio':
        this.initializeMinio();
        break;
    }
  }

  private initializeLocal(): void {
    if (!fs.existsSync(this.config.uploadPath)) {
      fs.mkdirSync(this.config.uploadPath, { recursive: true });
    }
    this.logger.info('Local storage initialized', {
      uploadPath: this.config.uploadPath,
    });
  }

  private initializeAWS(): void {
    this.s3 = new AWS.S3({
      accessKeyId: this.config.accessKey,
      secretAccessKey: this.config.secretKey,
      region: this.config.region,
    });
    this.logger.info('AWS S3 storage initialized', {
      bucket: this.config.bucket,
    });
  }

  private initializeMinio(): void {
    this.minio = new Minio.Client({
      endPoint: this.config.endpoint!,
      accessKey: this.config.accessKey!,
      secretKey: this.config.secretKey!,
      useSSL: this.config.endpoint?.includes('https') || false,
    });
    this.logger.info('MinIO storage initialized', {
      endpoint: this.config.endpoint,
    });
  }

  /**
   * Get MIME type from filename
   */
  private getMimeType(filename: string): string {
    const ext = path.extname(filename).toLowerCase();

    switch (ext) {
      case '.mp4':
        return 'video/mp4';
      case '.mov':
        return 'video/quicktime';
      case '.avi':
        return 'video/x-msvideo';
      case '.jpg':
      case '.jpeg':
        return 'image/jpeg';
      case '.png':
        return 'image/png';
      case '.webp':
        return 'image/webp';
      default:
        return 'application/octet-stream';
    }
  }

  /**
   * Sanitize filename for safe storage
   */
  private sanitizeFilename(filename: string): string {
    return filename
      .replace(/[^a-zA-Z0-9.-]/g, '_')
      .replace(/_{2,}/g, '_')
      .toLowerCase();
  }

  /**
   * Serialize metadata for storage headers
   */
  private serializeMetadata(
    metadata: Record<string, any>
  ): Record<string, string> {
    const serialized: Record<string, string> = {};

    for (const [key, value] of Object.entries(metadata)) {
      serialized[`x-amz-meta-${key}`] =
        typeof value === 'object' ? JSON.stringify(value) : String(value);
    }

    return serialized;
  }

  /**
   * Get local file information
   */
  private async getLocalFileInfo(assetId: string): Promise<any> {
    const uploadPath = this.config.uploadPath;
    const files = fs.readdirSync(uploadPath);
    const targetFile = files.find(file => file.startsWith(assetId));

    if (!targetFile) return null;

    const stats = fs.statSync(path.join(uploadPath, targetFile));
    return {
      size: stats.size,
      modified: stats.mtime,
      created: stats.birthtime,
    };
  }

  /**
   * Get AWS file information
   */
  private async getAWSFileInfo(assetId: string): Promise<any> {
    if (!this.s3) return null;

    const listParams = {
      Bucket: this.config.bucket!,
      Prefix: `${this.config.uploadPath}/${assetId}`,
    };

    const result = await this.s3.listObjectsV2(listParams).promise();
    return result.Contents?.[0] || null;
  }

  /**
   * Get MinIO file information
   */
  private async getMinioFileInfo(assetId: string): Promise<any> {
    if (!this.minio) return null;

    try {
      const objectName = `${this.config.uploadPath}/${assetId}`;
      const stat = await this.minio.statObject(this.config.bucket!, objectName);
      return stat;
    } catch (error) {
      return null;
    }
  }
}

export default StorageManager;
